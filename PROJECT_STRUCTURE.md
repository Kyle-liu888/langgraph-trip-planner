# 项目目录

```text
langgraph-trip-planner/
├── backend/
│   ├── app/
│   │   ├── api/          # FastAPI 应用与路由
│   │   ├── graph/        # State、Runtime、节点、边、Prompt
│   │   ├── llm/          # 模型配置、工厂、能力与结构化输出
│   │   ├── models/       # TripRequest / TripPlan Schema
│   │   ├── planner/      # POI、预算、日期、校验与 Rerank
│   │   └── services/     # 应用服务、高德与图片服务
│   ├── tests/            # 无真实 API 的单元测试
│   ├── pyproject.toml    # uv 项目及可选供应商依赖
│   └── uv.lock           # 可复现依赖锁
├── frontend/             # Vue 3 作品集界面
├── docs/                 # 架构说明与项目截图
└── README.md
```

本地 `.env`、`.venv`、`node_modules`、构建产物、缓存和日志不进入Git。
