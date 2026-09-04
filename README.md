# LangGraph Trip Planner

一个模型无关的智能旅行规划作品集项目。后端使用 LangChain 统一不同模型供应商，通过 LangGraph 编排高德数据采集、提示构造、结构化生成、业务校验、重试、候选重排和兜底流程；前端使用 Vue 3 展示行程、预算、天气和地图。

本项目只有在线推理，不包含模型后训练、训练数据、LoRA 权重或本地训练服务。

本分支迁移到 **Ubuntu + 非 root 开发容器 + 共享本地 PostgreSQL**，使用本地账号，不再依赖 Supabase。保留历史、检查点恢复、SSE 节点进度和轮转日志。**首次运行请看 [本地隔离开发手册](docs/LOCAL_DEV_GUIDE.md)**，完成状态见 [执行记录](docs/LOCAL_DEV_EXECUTION.md)。本轮不涉及部署或付费服务；外部模型/地图 API 费用另计。

## 主要能力

- 支持 DeepSeek、OpenAI、Claude、Gemini、Ollama、Azure OpenAI、OpenAI-compatible API，以及其他已安装的 LangChain Chat Model 集成。
- 从高德与本地候选表获取景点、酒店、餐厅和天气，减少模型自由编造。
- 使用统一 `TripPlan` Pydantic Schema，并按模型能力在 JSON Schema、工具调用、JSON Mode 和提示词 JSON 之间降级。
- LangGraph 显式管理失败重试、校验反馈、多候选 Rerank 和确定性 fallback。
- 返回供应商、模型、结构化策略、尝试次数和 Token usage 等可观测元数据。
- Vue 页面展示每日行程、地图、天气与预算，并支持导出。
- 本地邮箱标识＋密码登录；账号侧边栏支持历史、新增、重命名、删除，编辑结果保存到本地数据库。
- SSE 展示真实 LangGraph 节点和模型调用状态；断线重放，刷新不重复发起规划。
- 本地 PostgreSQL Checkpointer 支持中断后手动恢复，日志可按请求/行程/运行编号定位。

## 原有表单与结果界面预览

下方为原有截图，不含本轮新增的账号侧边栏和实时进度面板。

<img src="docs/images/trip-request.png" alt="旅行请求填写界面" width="720">

<img src="docs/images/trip-plan-result.png" alt="旅行计划结果界面" width="720">

## 架构

```text
Vue 3
  → 本地账号登录，携带 HttpOnly Cookie（修改请求额外带 CSRF）
  → FastAPI POST /api/trips（立即返回行程 ID）
  → GET /api/trips/{id}/events（SSE 实时进度与重放）
  → 后台 RunManager + PostgreSQL 业务表
  → LangGraph StateGraph
      → collect_context     高德景点/餐饮/酒店/天气
      → build_prompt        压缩 PlannerContext
      → generate_candidate  LangChain BaseChatModel
      → validate_candidate  Schema + 日期 + POI + 业务规则
      ↘ retry               带校验错误重新生成
      → select_best         多候选确定性 Rerank
      ↘ fallback            达到上限后的确定性兜底
  → PostgreSQL Checkpointer 保存节点状态
  → TripPlan + model_metadata 写入历史行程
```

模型对象和外部服务通过 LangGraph runtime context 注入，图节点不导入任何供应商专用模型类。详细设计见 [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)。

## 技术栈

- 后端：Python 3.11+、FastAPI、LangChain、LangGraph、Pydantic、httpx、uv
- 默认模型集成：`langchain-deepseek`、`langchain-openai`
- 可选模型集成：Anthropic、Google GenAI、Ollama
- 前端：Vue 3、TypeScript、Vite、Ant Design Vue、高德地图 Web JS API
- 测试：pytest、LangChain Fake Chat Model

## 本地隔离环境快速开始

先在 Docker Desktop 中开启 Ubuntu 集成，按手册备份并确认数据盘位置。在 Ubuntu 终端执行：

```bash
cd ~/dev/projects/langgraph-trip-planner
python3 scripts/dev.py setup
python3 scripts/dev.py pin-images  # 仅首次；固定明确版本及注册表摘要
python3 scripts/dev.py start
```

密钥在 `~/dev/config/trip-backend.env`、`trip-frontend.env`；专用数据库密码自动生成，不提交 Git。

VS Code 打开 Linux 项目后选择 **Reopen in Container**，分别运行“数据库迁移”“启动后端（含日志）”“启动前端”任务。Python 3.13、Node 24、uv 及依赖仅在项目容器中，不复制 Windows 的 .venv/node_modules。

- 界面：`http://127.0.0.1:5173`
- 健康检查：`http://127.0.0.1:8000/health`
- API 文档：`http://127.0.0.1:8000/docs`
- 日志：Linux 项目 `backend/logs/app.log` 和 `error.log`
- 只关项目：`python3 scripts/dev.py stop-trip`；结束全部开发使用需确认的 Windows 脚本，详见手册。

## 切换模型

切换模型只修改后端环境变量，不修改LangGraph节点：

```env
# OpenAI
LLM_PROVIDER=openai
LLM_MODEL=gpt-4.1-mini

# Claude（先执行 uv sync --extra anthropic）
LLM_PROVIDER=anthropic
LLM_MODEL=your-claude-model

# Gemini（先执行 uv sync --extra google）
LLM_PROVIDER=google_genai
LLM_MODEL=your-gemini-model

# Ollama（先执行 uv sync --extra ollama）
LLM_PROVIDER=ollama
LLM_MODEL=qwen3:8b
LLM_BASE_URL=http://localhost:11434

# 任意 OpenAI-compatible 服务
LLM_PROVIDER=openai_compatible
LLM_MODEL=provider-model-name
LLM_BASE_URL=https://provider.example.com/v1
```

供应商私有参数可以通过JSON传入：

```env
LLM_MODEL_KWARGS={"region_name":"ap-southeast-1"}
```

## 测试与构建

```powershell
cd backend
uv run pytest

cd ..\frontend
npm test
npm run build
```

以上测试在开发容器内执行，不调用真实模型或高德 API。真实 PostgreSQL 验收另运行 `python3 scripts/dev.py verify-postgres`（Ubuntu 主机），不提供测试数据库时对应测试会明确跳过。已验证和待验证项目见执行记录。

## API

- `POST /api/trips`：创建后台行程任务，要求 Bearer token 和 `X-Idempotency-Key` UUID
- `GET /api/trips`、`GET /api/trips/{id}`：自己的历史列表与详情
- `GET /api/trips/{id}/events`：SSE 进度，支持 `Last-Event-ID`
- `POST /api/trips/{id}/resume`：从持久化检查点手动继续
- `PATCH /api/trips/{id}`、`DELETE /api/trips/{id}`：重命名、删除
- `PUT /api/trips/{id}/plan`：带 revision 的编辑保存
- `GET /api/me/usage`：当前用户当天额度与活跃任务
- 旧 `POST /api/trip/plan` 已返回 410，不能绕过账号和额度创建任务
- `GET /api/map/poi`：搜索POI
- `GET /api/map/weather`：查询天气
- `POST /api/map/route`：规划路线
- `GET /api/poi/detail/{poi_id}`：获取POI详情
- `GET /api/poi/photo`：获取景点图片

## 安全

- 所有密钥只放在本地或部署平台环境变量中。
- `.env`、虚拟环境、`node_modules`、日志和缓存均被Git忽略。
- 所有业务接口验证 Supabase JWT；数据库业务表启用 RLS，无浏览器直连策略；检查点保存在私有 schema。
- 当前仅面向本地单进程运行，不是上线部署方案。新增部署前仍需独立审视全站限流、预算、备份、监控和域名/CORS。

## 数据来源

- [高德开放平台](https://lbs.amap.com/)
- [Unsplash](https://unsplash.com/developers)
