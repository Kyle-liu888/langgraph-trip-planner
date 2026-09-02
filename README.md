# HelloAgents Trip Planner

一个使用 DeepSeek/OpenAI-compatible API 与高德地图数据的智能旅行助手。后端将用户请求、人数、预算、住宿、天气、景点、酒店和餐饮候选编译成 `PlannerContext`，再由在线大模型生成结构化 `TripPlan JSON`。

本版本只包含在线应用，不包含模型后训练、训练数据、模型权重或本地模型服务。

## 功能

- 根据城市、日期、同行人数、预算、交通、住宿和兴趣生成多日行程。
- 从高德与本地候选表获取景点、酒店、餐厅和天气，减少自由编造。
- 显式处理酒店晚数、同行人数、门票、餐饮和交通预算。
- 对模型输出执行 JSON 解析、Pydantic 校验、失败重试和可选多候选 Rerank。
- 在 Vue 页面展示每日行程、预算、天气和地图，并支持导出。

## 界面预览

<img src="docs/images/trip-request.png" alt="旅行请求填写界面" width="720">

<img src="docs/images/trip-plan-result.png" alt="旅行计划结果界面" width="720">

## 技术栈

- 后端：FastAPI、HelloAgents `SimpleAgent`、Pydantic、高德地图 API
- 模型：DeepSeek 或其他 OpenAI-compatible 在线 LLM
- 前端：Vue 3、TypeScript、Vite、Ant Design Vue、高德地图 Web JS API

## 目录结构

```text
helloagents-trip-planner/
├── backend/
│   ├── app/
│   │   ├── agents/          # Planner Agent 和 Prompt
│   │   ├── api/             # FastAPI 路由
│   │   ├── models/          # 请求与 TripPlan Schema
│   │   ├── planner/         # PlannerContext、预算、候选和输出校验
│   │   └── services/        # LLM、高德和图片服务
│   ├── requirements.txt
│   └── run.py
├── frontend/                # Vue Web 应用
├── docs/images/             # 展示截图
├── PROJECT_STRUCTURE.md
└── README.md
```

## Windows 快速开始

前置条件：Node.js 22 或兼容版本、`uv`、DeepSeek API Key、高德 Web 服务 Key，以及用于前端地图的高德 Web JS Key。

### 1. 安装后端依赖

在项目根目录运行：

```powershell
uv python install 3.11
uv venv .venv --python 3.11
uv pip install --python .\.venv\Scripts\python.exe -r .\backend\requirements.txt
Copy-Item .\backend\.env.example .\backend\.env
```

编辑 `backend/.env`：

```env
LLM_MODEL_ID=your-deepseek-model
LLM_API_KEY=your-deepseek-api-key
LLM_BASE_URL=your-deepseek-openai-compatible-base-url
LLM_TIMEOUT=120

HOST=0.0.0.0
PORT=7000
CORS_ORIGINS=http://localhost:5173
LOG_LEVEL=INFO

AMAP_API_KEY=your-amap-web-service-key
UNSPLASH_ACCESS_KEY=
UNSPLASH_SECRET_KEY=
```

模型名称和接口地址以 DeepSeek 控制台为准。不要提交真实 `.env`。

启动后端：

```powershell
cd backend
..\.venv\Scripts\python.exe run.py
```

- API 文档：`http://localhost:7000/docs`
- 健康检查：`http://localhost:7000/health`

### 2. 启动前端

另开一个 PowerShell：

```powershell
cd frontend
Copy-Item .env.example .env
npm ci
npm run dev
```

编辑 `frontend/.env`，开发环境的 API 地址可以留空：

```env
VITE_API_BASE_URL=
VITE_AMAP_WEB_KEY=your-amap-web-key
VITE_AMAP_WEB_JS_KEY=your-amap-web-js-key
```

访问 `http://localhost:5173`。

## 在线运行流程

```text
Vue 表单
  -> FastAPI 请求校验
  -> 高德与本地候选表
  -> PlannerContext
  -> DeepSeek 生成 TripPlan JSON
  -> JSON/Schema/业务规则校验
  -> 可选多候选 Rerank
  -> 前端行程、预算和地图
```

## API

- `POST /api/trip/plan`：生成旅行计划
- `GET /api/trip/health`：检查 Planner 服务
- `GET /api/map/poi`：搜索 POI
- `GET /api/map/weather`：查询天气
- `POST /api/map/route`：规划路线
- `GET /api/poi/detail/{poi_id}`：获取 POI 详情
- `GET /api/poi/photo`：获取景点图片

## 安全

- DeepSeek、高德和 Unsplash 密钥只放在本地或部署平台的环境变量中。
- 不要将 `backend/.env`、`frontend/.env`、日志或缓存提交到公开仓库。
- 公开部署时将 `CORS_ORIGINS` 设置为实际前端域名。

## 致谢

- [HelloAgents](https://github.com/datawhalechina/Hello-Agents)
- [高德地图开放平台](https://lbs.amap.com/)
- [amap-mcp-server](https://github.com/sugarforever/amap-mcp-server)
