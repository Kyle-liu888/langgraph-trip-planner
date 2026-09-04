# LangGraph Trip Planner

一个模型无关的智能旅行规划作品集项目。后端使用 LangChain 统一不同模型供应商，通过 LangGraph 编排高德数据采集、提示构造、结构化生成、业务校验、重试、候选重排和兜底流程；前端使用 Vue 3 展示行程、预算、天气和地图。

本项目只有在线推理，不包含模型后训练、训练数据、LoRA 权重或本地训练服务。

当前本地功能版已增加 Supabase 登录、持久化历史与检查点恢复、SSE 节点进度、轮转日志。**首次运行请先完成 [Supabase 本地配置指南](docs/SUPABASE_LOCAL_SETUP.md)**；未配置数据库时后端会显示 degraded。本轮不涉及网站部署或付费服务。

## 主要能力

- 支持 DeepSeek、OpenAI、Claude、Gemini、Ollama、Azure OpenAI、OpenAI-compatible API，以及其他已安装的 LangChain Chat Model 集成。
- 从高德与本地候选表获取景点、酒店、餐厅和天气，减少模型自由编造。
- 使用统一 `TripPlan` Pydantic Schema，并按模型能力在 JSON Schema、工具调用、JSON Mode 和提示词 JSON 之间降级。
- LangGraph 显式管理失败重试、校验反馈、多候选 Rerank 和确定性 fallback。
- 返回供应商、模型、结构化策略、尝试次数和 Token usage 等可观测元数据。
- Vue 页面展示每日行程、地图、天气与预算，并支持导出。
- 邮箱/GitHub 登录；账号侧边栏支持历史、新增、重命名、删除，编辑结果保存到数据库。
- SSE 展示真实 LangGraph 节点和模型调用状态；断线重放，刷新不重复发起规划。
- Supabase PostgreSQL Checkpointer 支持中断后手动恢复，日志可按请求/行程/运行编号定位。

## 原有表单与结果界面预览

下方为原有截图，不含本轮新增的账号侧边栏和实时进度面板。

<img src="docs/images/trip-request.png" alt="旅行请求填写界面" width="720">

<img src="docs/images/trip-plan-result.png" alt="旅行计划结果界面" width="720">

## 架构

```text
Vue 3
  → Supabase Auth 登录，携带 access token
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

## Windows 快速开始

### 1. 后端

```powershell
cd backend
Copy-Item .env.example .env
uv sync
uv run alembic upgrade head
uv run python run.py
```

先编辑 `backend/.env` 再运行上述迁移和启动命令（已有 `.env` 时不要覆盖它）：

```env
LLM_PROVIDER=deepseek
LLM_MODEL=deepseek-chat
LLM_API_KEY=your-llm-api-key
LLM_BASE_URL=https://api.deepseek.com

AMAP_API_KEY=your-amap-web-service-key
HOST=0.0.0.0
PORT=8000
CORS_ORIGINS=http://localhost:5173
SUPABASE_URL=https://PROJECT_REF.supabase.co
DATABASE_URL=postgresql://postgres.PROJECT_REF:URL_ENCODED_PASSWORD@SESSION_POOLER_HOST:5432/postgres?sslmode=require
```

访问：

- API 文档：`http://localhost:8000/docs`
- 健康检查：`http://localhost:8000/health`
- 日志：`backend/logs/app.log` 和 `backend/logs/error.log`

### 2. 前端

```powershell
cd frontend
Copy-Item .env.example .env
npm ci
npm run dev
```

编辑 `frontend/.env`：

```env
VITE_API_BASE_URL=http://localhost:8000
VITE_AMAP_WEB_KEY=your-amap-web-key
VITE_AMAP_WEB_JS_KEY=your-amap-web-js-key
VITE_SUPABASE_URL=https://PROJECT_REF.supabase.co
VITE_SUPABASE_PUBLISHABLE_KEY=your_publishable_key
```

访问 `http://localhost:5173`。

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

当前测试不调用真实模型或高德 API，覆盖供应商映射、重试/兜底、持久化重开恢复、SSE 重放/重连、权限隔离、额度、编辑版本冲突和安全日志。真实 Supabase 联调仍需填写自己的配置。

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
