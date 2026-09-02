# 项目目录索引

当前仓库只包含使用在线 DeepSeek/OpenAI-compatible API 的旅行助手应用。

| 路径 | 用途 |
| --- | --- |
| `backend/` | FastAPI、Planner Agent、PlannerContext、预算规则和外部服务 |
| `frontend/` | Vue 旅行助手界面 |
| `docs/` | 项目截图 |

```text
backend/app/
├── agents/       # Prompt、Planner 查询和行程生成
├── api/          # FastAPI 应用与路由
├── models/       # TripRequest / TripPlan Schema
├── planner/      # 候选、预算、日期、输出校验和 Rerank
└── services/     # DeepSeek、高德和图片服务
```

本地 `.env`、虚拟环境、Node 依赖、缓存和日志由 `.gitignore` 排除。
