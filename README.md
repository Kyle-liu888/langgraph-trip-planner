# LangGraph Trip Planner

一个模型无关的智能旅行规划作品集项目。后端使用 LangChain 统一不同模型供应商，通过 LangGraph 编排高德数据采集、提示构造、结构化生成、业务校验、重试、候选重排和兜底流程；前端使用 Vue 3 展示行程、预算、天气和地图。

本项目只有在线推理，不包含模型后训练、训练数据、LoRA 权重或本地训练服务。

## 主要能力

- 支持 DeepSeek、OpenAI、Claude、Gemini、Ollama、Azure OpenAI、OpenAI-compatible API，以及其他已安装的 LangChain Chat Model 集成。
- 从高德与本地候选表获取景点、酒店、餐厅和天气，减少模型自由编造。
- 使用统一 `TripPlan` Pydantic Schema，并按模型能力在 JSON Schema、工具调用、JSON Mode 和提示词 JSON 之间降级。
- LangGraph 显式管理失败重试、校验反馈、多候选 Rerank 和确定性 fallback。
- 返回供应商、模型、结构化策略、尝试次数和 Token usage 等可观测元数据。
- Vue 页面展示每日行程、地图、天气与预算，并支持导出。

## 界面预览

<img src="docs/images/trip-request.png" alt="旅行请求填写界面" width="720">

<img src="docs/images/trip-plan-result.png" alt="旅行计划结果界面" width="720">

## 架构

```text
Vue 3
  → FastAPI /api/trip/plan
  → LangGraph StateGraph
      → collect_context     高德景点/餐饮/酒店/天气
      → build_prompt        压缩 PlannerContext
      → generate_candidate  LangChain BaseChatModel
      → validate_candidate  Schema + 日期 + POI + 业务规则
      ↘ retry               带校验错误重新生成
      → select_best         多候选确定性 Rerank
      ↘ fallback            达到上限后的确定性兜底
  → TripPlan + model_metadata
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
uv run python run.py
```

编辑 `backend/.env`：

```env
LLM_PROVIDER=deepseek
LLM_MODEL=deepseek-chat
LLM_API_KEY=your-llm-api-key
LLM_BASE_URL=https://api.deepseek.com

AMAP_API_KEY=your-amap-web-service-key
HOST=0.0.0.0
PORT=8000
CORS_ORIGINS=http://localhost:5173
```

访问：

- API 文档：`http://localhost:8000/docs`
- 健康检查：`http://localhost:8000/health`
- 模型和图检查：`http://localhost:8000/api/trip/health`

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
npm run build
```

当前测试不调用真实模型或高德API，覆盖模型供应商映射、LangGraph重试/兜底和FastAPI响应契约。

## API

- `POST /api/trip/plan`：生成旅行计划
- `GET /api/trip/health`：检查模型和LangGraph配置
- `GET /api/map/poi`：搜索POI
- `GET /api/map/weather`：查询天气
- `POST /api/map/route`：规划路线
- `GET /api/poi/detail/{poi_id}`：获取POI详情
- `GET /api/poi/photo`：获取景点图片

## 安全

- 所有密钥只放在本地或部署平台环境变量中。
- `.env`、虚拟环境、`node_modules`、日志和缓存均被Git忽略。
- 公开部署前应增加限流、调用预算、错误脱敏，并将CORS限制为实际前端域名。

## 数据来源

- [高德开放平台](https://lbs.amap.com/)
- [Unsplash](https://unsplash.com/developers)
