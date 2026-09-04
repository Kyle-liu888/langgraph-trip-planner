# 架构设计

## 设计目标

1. LangGraph业务节点不依赖DeepSeek、OpenAI或其他具体供应商。
2. 外部数据采集、模型生成和确定性校验职责分离。
3. 模型失败、JSON失败和业务规则失败都能在图状态中被观察和处理。
4. 测试可以注入Fake Chat Model和Stub Context Builder，不消耗真实API。

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

## 模型网关

`ModelFactory`把环境变量转换为LangChain `BaseChatModel`：

```text
LLM_PROVIDER + LLM_MODEL + LLM_BASE_URL
                    │
                    ▼
             init_chat_model
                    │
                    ▼
              BaseChatModel
```

`openai_compatible`会映射到OpenAI集成并保留自定义`base_url`。其他provider名称直接传给LangChain，因此新增已安装的集成通常不需要修改图代码。

## 结构化输出兼容

不同供应商支持的结构化能力不同，调用层按配置选择：

```text
json_schema → function_calling → json_mode → prompt JSON parser
```

默认顺序是保守的供应商能力提示。显式设置`LLM_STRUCTURED_OUTPUT_MODE`可以锁定策略。只有能力不支持或解析失败时才降级；普通网络和认证错误不会被误判成能力问题。

## 可观测性

API响应的`metadata`可包含：

- provider / model
- structured_strategy
- attempts / selected_attempt / candidate_count
- rerank_score
- usage（供应商返回时）

不暴露供应商原始 response_metadata；运行日志不记录完整 Prompt、JWT、密钥和模型原文。

## 持久化、账号和进度

- Supabase Auth 负责邮箱/GitHub 登录。前端用 publishable key；后端通过固定项目 JWKS 验证用户 JWT，绝不采信请求中的 user_id。
- `trips` 保存请求、最终结果、状态、版本；`trip_runs` 保存每次执行；`trip_events` 保存可重放事件；`daily_usage` 保存每日额度。
- 业务表启用 RLS 且没有面向浏览器的访问策略。FastAPI 使用可信数据库 owner 连接，所有资源查询同时过滤行程 ID 与已认证用户 ID。
- `planner_internal` 私有 schema 存放 LangGraph PostgreSQL checkpointer。可序列化状态只含普通字典/列表；模型对象和凭据只存在 runtime 中。
- `POST /api/trips` 校验幂等键、活跃任务和额度，提交业务事务后创建独立 asyncio Task。浏览器关闭不会取消任务。
- 节点/模型埋点通过 LangGraph custom stream 产生安全事件；后端先落库，SSE 再按事件 ID 发送。浏览器重连携带 Last-Event-ID，不重复创建任务。
- 服务启动时将上次遗留的 queued/running 任务标记 interrupted；用户手动恢复才继续执行同一 thread_id。最新检查点已完成但业务结果未写入时，直接保存结果而不重复调用模型。
- 运行状态为 queued / running / completed / fallback / failed / interrupted；fallback 有独立警告，不能当作正常模型成功。
- 版本号 revision 防止结果被两个编辑页面静默覆盖。删除行程会删除业务记录及检查点，不返还已使用额度。

本地版仅支持单后端进程，持有数据库会话 advisory lock，防止第二进程误判正在运行的任务。任务不是分布式队列；数据库连接断开可能需要重启后端再恢复。外部 API 无法保证 exactly-once，中断中的模型调用恢复时可能再次计费。

日志位于 backend/logs/app.log、error.log，并输出到控制台。HTTP 请求关联 request_id，后台执行关联 trip_id / run_id，节点记录 node / attempt / elapsed_ms。异常保留类型和代码栈位置，不记录包含用户输入的完整异常正文。业务数据库和检查点本身仍会保存行程内容。

完整本地配置与测试边界见 [SUPABASE_LOCAL_SETUP.md](SUPABASE_LOCAL_SETUP.md)。
