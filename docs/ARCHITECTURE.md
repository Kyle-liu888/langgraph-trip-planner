# 架构设计

本文解释当前本地账号分支的真实实现，供维护代码和讲解设计取舍使用。日常启动看[本地隔离开发手册](LOCAL_DEV_GUIDE.md)，源码定位看[项目目录](../PROJECT_STRUCTURE.md)。这里的“智能”来自已接入模型的在线推理，不包含后训练、LoRA 或模型权重部署。

## 设计目标

1. LangGraph 节点统一依赖 BaseChatModel，不在图内实例化供应商专用模型类；少量能力差异通过配置处理。
2. 外部数据采集、模型生成和确定性校验职责分离。
3. 模型失败、JSON失败和业务规则失败都能在图状态中被观察和处理。
4. 测试可以注入Fake Chat Model和Stub Context Builder，不消耗真实API。

## 运行边界与一趟请求

Windows 提供 Docker Desktop、编辑器和浏览器；代码在 WSL2 Ubuntu 文件系统。一个非 root 项目容器运行 Python 3.13 后端和 Node 24 前端，共享的 PostgreSQL 17 使用独立容器、数据卷及项目专用账号。

```text
浏览器 Vue 页面（127.0.0.1:5173）
  ├─ Cookie + CSRF → Vite /api 代理 → FastAPI（8000）
  │                                  ├─ 本地 accounts / login_sessions
  │                                  └─ POST /api/trips → 202 + 行程 ID
  │                                                        │
  │                                  RunManager 后台任务 ←─┘
  │                                    ├─ LangGraph → 高德 / 在线模型
  │                                    ├─ PostgreSQL 业务记录及事件
  │                                    └─ planner_internal 检查点
  ├─ GET /api/trips/{id}/events ← 已落库的 SSE 节点与调用事件
  └─ GET /api/trips/{id} ← 行程结果，再异步加载图片和实用信息
```

前端不直连数据库、不持有后端模型 Key。API、数据库和页面仅发布本机回环端口；容器内部监听 `0.0.0.0` 是端口转发的需要，不是公网部署。

## LangGraph状态机

```text
START
  │
  ▼
collect_context ── 高德/本地候选采集
  │
  ▼
build_prompt ───── PlannerContext压缩与提示构造
  │
  ▼
generate_candidate ── BaseChatModel + 结构化策略
  │
  ▼
validate_candidate ── Pydantic、日期、餐饮、酒店、POI规则
  │
  ├─ 未达到上限/候选数 ───────────────┐
  │                                   │
  │                                   ▼
  │                         generate_candidate
  │
  ├─ 有合法候选 → select_best_candidate → END
  │
  └─ 无合法候选且达到上限 → create_fallback → END
```

`PlannerState`只保存一次运行中会变化的数据。模型对象、配置、上下文构造器等依赖放在`PlannerRuntime`，通过LangGraph runtime context注入。

图中只有 6 个业务节点，定义见 `backend/app/graph/builder.py` 和 `nodes.py`。`retry`、`select`、`fallback` 是条件边的返回值，不是另外三个节点。

- `collect_context`：从高德和本地候选表获取景点、餐饮、酒店、天气，形成上下文。
- `build_prompt`：压缩重复信息并构造请求提示，不修改模型权重。
- `generate_candidate`：唯一调用规划模型的节点，要求返回结构化候选行程；重试会带校验反馈。
- `validate_candidate`：用 Pydantic 和确定性规则检查日期、目的地、POI、住宿与餐饮等约束。
- `select_best_candidate`：按照候选命中、预算关系和多样性等规则评分选优，不是另一个训练过的 Reranker 模型。
- `create_fallback`：多次尝试仍无合法候选时返回基础兜底，页面明确标记为兜底结果，不冒充模型成功。

开启 Rerank 时会争取获得配置数量的合法候选；达到尝试上限但已有合法候选时仍会选优。关闭 Rerank 时，首个合法候选即可进入选择节点。

## 模型网关

`backend/app/llm/factory.py` 的 `create_chat_model` 把配置转换为 LangChain `BaseChatModel`：

```text
LLM_PROVIDER + LLM_MODEL + LLM_BASE_URL
                    │
                    ▼
             init_chat_model
                    │
                    ▼
              BaseChatModel
```

`openai_compatible` 会映射到 OpenAI 集成并保留自定义 `base_url`。其他 provider 标识交给 LangChain。新增已安装且参数兼容的集成通常不需要修改图代码，但必须验证具体模型的认证方式、请求参数、结构化输出和流式行为；“可扩展”不等于所有供应商已经实测。

默认依赖包含 `langchain-deepseek`、`langchain-openai`；Anthropic、Google GenAI 等是可选依赖。模型 ID、Key 和地址是一组配置，切换时不能只换名称。项目不要求启动本地大模型服务。

## 结构化输出兼容

`backend/app/llm/capabilities.py` 给出保守的自动策略顺序，不是所有模型都依次使用同一套模式：

| provider | 自动策略 |
| --- | --- |
| `openai` / `azure_openai` | JSON Schema → 工具调用 → JSON Mode → 提示词 JSON 解析 |
| `deepseek` / `openai_compatible` | JSON Mode → 提示词 JSON 解析 |
| `anthropic` | 工具调用 → 提示词 JSON 解析 |
| `google_genai` | JSON Schema → 工具调用 → 提示词 JSON 解析 |
| 未知 provider | 提示词 JSON 解析 |

显式设置 `LLM_STRUCTURED_OUTPUT_MODE` 会锁定单一策略。调用层识别的能力异常或显式结构化解析异常可以触发兼容策略降级；普通网络、认证等异常交给生成节点和图处理，不把它们当作“模型不支持 JSON”。业务规则校验始终是独立节点。

## 超时与模型进度

以下是 `backend/app/config.py` 的代码默认值，实际运行可能由私有环境配置覆盖：

| 配置 | 默认值 | 含义 |
| --- | --- | --- |
| `LLM_TIMEOUT` | 180 秒 | 单个结构化策略的模型调用时间上限 |
| `LLM_MAX_RETRIES` | 0 | 模型 SDK 内部自动重试次数，与图重试不同 |
| `LLM_STREAMING` | true | 对支持该选项的集成启用流式接收 |
| `LLM_PROGRESS_INTERVAL` | 10 秒 | 等待模型时的进度反馈间隔 |
| `PLANNER_REQUEST_TIMEOUT` | 600 秒 | 一次后台执行的整体时间预算 |
| `PLANNER_MAX_ATTEMPTS` | 3 | 生成候选的最大轮数 |
| `PLANNER_RERANK_CANDIDATE_COUNT` | 3 | 开启重排时争取获得的合法候选数量 |

同一图轮次可能因结构化策略降级而发生多个模型调用，所以不能把“3 次尝试”理解为绝对只有 3 次 HTTP 请求。整体时间预算不足时，即便某个单次调用还没超时，也可能先结束整趟任务。

`LLM_THINKING_MODE` 只有在相应供应商逻辑支持时才生效；当前 DeepSeek 节点可发送明确的启用／禁用参数，默认 `auto` 不强行覆盖供应商行为。进度只展示节点、耗时和收到的正文／推理字符数量，不向前端传递模型内部思维正文。收到响应但正文仍为零，不等于已经生成可解析的行程。

## 可观测性

API响应的`metadata`可包含：

- provider / model
- structured_strategy
- attempts / selected_attempt / candidate_count
- rerank_score
- usage（供应商返回时，为最近一次成功调用所记录的数据，不是所有尝试累计费用）

不暴露供应商原始 response_metadata；运行日志不记录完整提示词、会话令牌、密钥和模型正文。

## 持久化、账号和进度

- 本地 accounts 表保存邮箱标识与 Argon2id 密码哈希；login_sessions 只保存不透明会话令牌的 SHA256 和到期时间。前端使用 HttpOnly/SameSite Cookie，后端从会话查用户，绝不采信输入的 user_id。
- GET /api/auth/session 提供 CSRF 信息；登录前用 HttpOnly Cookie 双重提交校验，登录后用会话派生 token 校验。所有修改请求必须通过严格 Origin 检查；auth_attempts 持久化限速。
- 退出立即删除服务端会话，SSE 每批重新检查撤销/到期，并在退出时唤醒等待连接。会话过期只要求重新登录，不重新提交规划。
- `trips` 保存请求、最终结果、状态、版本；`trip_runs` 保存每次执行；`trip_events` 保存可重放事件；`daily_usage` 保存每日额度。
- 业务表启用 RLS 且没有面向浏览器的访问策略。FastAPI 使用本项目数据库 owner（不是 PostgreSQL 超级用户）连接；owner 默认绕过自己表的 RLS，用户隔离依赖所有资源查询同时过滤行程 ID 与已认证用户 ID，不能声称是 RLS 自动识别本地用户。
- `planner_internal` 私有 schema 存放 LangGraph PostgreSQL checkpointer。状态使用字典、列表、字符串、数值等可序列化数据；模型对象和凭据只存在 runtime 中。
- `POST /api/trips` 校验幂等键、活跃任务和额度，提交业务事务后创建独立 asyncio Task。浏览器关闭不会取消任务。
- 节点/模型埋点通过 LangGraph custom stream 产生安全事件；后端先落库，SSE 再按事件 ID 发送。浏览器重连携带 Last-Event-ID，不重复创建任务。
- 服务启动时将上次遗留的 queued/running 任务标记 interrupted；用户手动恢复才继续执行同一 thread_id。最新检查点已完成但业务结果未写入时，直接保存结果而不重复调用模型。
- 运行状态为 queued / running / completed / fallback / failed / interrupted；fallback 有独立警告，不能当作正常模型成功。
- 版本号 revision 防止结果被两个编辑页面静默覆盖。删除行程会删除业务记录及检查点，不返还已使用额度。

本地版仅支持单后端进程，持有数据库会话 advisory lock，防止第二进程误判正在运行的任务。任务不是分布式队列；数据库连接断开可能需要重启后端再恢复。外部 API 无法保证 exactly-once，中断中的模型调用恢复时可能再次计费。

日志位于 backend/logs/app.log、error.log，并输出到控制台。HTTP 请求关联 request_id，后台执行关联 trip_id / run_id，节点记录 node / attempt / elapsed_ms。异常保留类型和代码栈位置，不记录包含用户输入的完整异常正文。业务数据库和检查点本身仍会保存行程内容。

两类日志各按 10 MiB 轮转、保留 5 个备份，`LOG_FORMAT=json` 可切换结构化日志。`model.failed`、`validation.failed` 等事件可能是 WARNING，只看 `error.log` 会漏掉它们。`/health` 报告启动时建立的运行管理器是否就绪，不是每次实时执行数据库探针。

## 结果页数据与可信程度

图片、开放时间和攻略入口在行程加载后独立查询，不进入 `TripPlan`、规划上下文或 Checkpointer，不改变行程排序和预算算法。旧行程无需重新生成；编辑地点身份后重新匹配，不复用旧地点的信息。

- 图片：高德 POI ID、城市、名称和坐标匹配后才展示对应照片。无匹配或无照片时显示占位状态，不用 Unsplash 风景图冒充实景。
- 开放时间：高德 POI 2.0 字段仅供参考；查询时间不是上游数据更新时间，今日时间不套用于未来游玩日期。规划本身未自动排除闭馆日期。
- 预约和价格政策：独立登记表只维护已人工核验的官方入口与核验日期；没有来源时明确告知，不让模型猜网址。
- 价格：门票为预算估算，零估算不代表确认免费；不查询实时余票或执行预约。
- 攻略：链接到平台入口或明确标注的搜索入口，不抓取笔记、评论或账号数据，也不表示内容已审核。

接口有超时、缓存与并发限制，来源查询失败不阻塞图片、地图和攻略入口。具体字段、权限降级和登记表维护见 [VISIT_INFO.md](VISIT_INFO.md)、[POI_PHOTOS.md](POI_PHOTOS.md)。

## 验证边界与维护顺序

默认 pytest 使用模拟模型、地图响应及测试数据库；真实 PostgreSQL 验收必须显式提供专用 `test_*` 数据库，未提供时相应测试跳过。Vitest 检查前端组件和状态逻辑；真实浏览器检查另见[浏览器验收记录](BROWSER_ACCEPTANCE.md)，隔离测试服务不等于正式 PostgreSQL 或真实 API 已验收。

修改时建议按职责定位：规划规则改 `planner/`，模型兼容改 `llm/`，流程和状态改 `graph/`，认证及持久化改路由／服务与迁移；展示数据只改对应查询服务和结果组件。每次保留模拟测试，再按风险选择真实数据库或浏览器验收，不自动消费真实模型额度。

完整本地配置、备份和启动方式见[本地隔离开发手册](LOCAL_DEV_GUIDE.md)。旧 `SUPABASE_LOCAL_SETUP.md` 只保留历史背景，不适用于当前启动流程。未来公网部署、多进程调度、邮件验证、实时票务都属于新范围，不是当前已实现能力。
