# 项目目录

## 先分清主机与容器路径

当前主工作区在 WSL2 Ubuntu：`~/dev/projects/langgraph-trip-planner`（本机用户为 `kyle`）。同一份代码挂载到开发容器的 `/workspace`；这不是两份需要手动同步的源码。旧 Windows 项目仅保留，不是当前服务读取的主源码。

共享数据库配置在 Ubuntu 的 `~/dev/infra/postgres`，凭据在 `~/dev/config`；PostgreSQL 数据位于独立 Docker 命名卷，逻辑备份位于 D 盘独立目录。不要把“删除项目容器”和“删除数据库卷”混为一谈。详细路径及备份操作见[本地开发手册](docs/LOCAL_DEV_GUIDE.md)。

## 目录总览

```text
langgraph-trip-planner/
├── .devcontainer/        # 项目开发容器、非 root 运行环境
├── .vscode/tasks.json    # 容器内迁移、前后端启动、测试任务
├── compose.prod.yaml    # 独立生产栈：web、backend、postgres 和 migrate
├── deploy/              # Dockerfile、Caddy、配置模板与运维命令
│   └── portal/          # 个人作品集首页，按钮进入 /trips/new
├── infra/               # 共享服务模板和项目环境配置
├── scripts/             # 环境管理、备份恢复、停止与安全检查
├── backend/
│   ├── app/
│   │   ├── api/          # FastAPI 应用与路由
│   │   ├── auth.py       # 不透明会话、Origin 与 CSRF 校验
│   │   ├── database.py   # 账号、会话、行程、运行、事件、额度表
│   │   ├── config.py     # 环境配置与默认值（不是私有配置内容）
│   │   ├── production.py # 生产迁移入口、单 Uvicorn 进程监督与退出
│   │   ├── observability.py # 脱敏轮转日志、节点埋点、进度事件
│   │   ├── graph/        # State、Runtime、节点、边、Prompt
│   │   ├── llm/          # 模型配置、工厂、能力与结构化输出
│   │   ├── models/       # TripRequest / TripPlan Schema
│   │   ├── planner/      # POI、预算、日期、校验与 Rerank
│   │   └── services/     # 任务管理、高德、照片和实用信息
│   ├── migrations/       # Alembic 业务表迁移
│   ├── tests/            # 模拟测试、显式启用的真实 PostgreSQL 验收
│   ├── run.py            # 后端启动入口
│   ├── logs/             # 运行时生成，不进入 Git
│   ├── pyproject.toml    # uv 项目及可选供应商依赖
│   └── uv.lock           # 可复现依赖锁
├── frontend/
│   ├── src/
│   │   ├── main.ts       # 应用挂载、路由与登录守卫
│   │   ├── App.vue       # 全局布局与账号侧栏入口
│   │   ├── views/        # 登录、新建、运行详情、结果页
│   │   ├── components/   # 历史侧栏、景点信息和视觉组件
│   │   ├── stores/       # Pinia 账号与历史状态
│   │   ├── services/     # HTTP、认证、SSE、图片和攻略入口
│   │   ├── styles/       # 全局设计变量和 Ant Design Vue 主题
│   │   └── types/        # 行程类型；展示查询类型另在对应 service 中
│   ├── vite.config.ts    # 5173 前端及 /api、/health 到后端的代理
│   ├── package.json      # dev / test / build 命令
│   └── package-lock.json # 前端依赖锁
├── docs/                 # 启动、架构、功能维护与验收文档
└── README.md
```

## 从功能找到源码

| 想看或修改什么 | 关键文件 | 职责边界 |
| --- | --- | --- |
| 注册、登录、退出 | `backend/app/api/routes/auth.py`、`backend/app/auth.py`；`frontend/src/views/Login.vue`、`frontend/src/services/auth.ts`、`frontend/src/stores/auth.ts` | 本地邮箱标识＋密码、Cookie 会话和 CSRF；不是 Supabase/OAuth |
| 填写需求与开始规划 | `frontend/src/views/Home.vue`、`frontend/src/services/destination.ts`、`frontend/src/services/trips.ts`；`backend/app/api/routes/trips.py` | 校验城市、提交请求、携带幂等键；页面不直接调用模型 |
| 历史、新增、重命名、删除 | `frontend/src/components/HistorySidebar.vue`、`frontend/src/stores/trips.ts`；`backend/app/api/routes/trips.py`、`backend/app/services/run_manager.py` | 当前账号资源过滤和持久化；删除包含关联事件与检查点 |
| 执行任务与恢复 | `backend/app/services/run_manager.py`、`backend/app/services/trip_planner_service.py`、`backend/app/api/main.py` | 单进程后台任务、额度、状态、PostgreSQL Checkpointer |
| LangGraph 流程 | `backend/app/graph/` 下的 `builder.py`、`nodes.py`、`state.py`、`runtime.py` | 6 个节点及条件边；可序列化状态和模型实例分离 |
| 模型接入与超时 | `backend/app/llm/` 下的 `config.py`、`factory.py`、`capabilities.py`、`structured.py`、`progress.py` | 模型构建、结构化兼容、等待／接收进度；没有训练逻辑 |
| 提示词与候选资料 | `backend/app/graph/prompts.py`、`backend/app/planner/context.py`、`backend/app/planner/compact.py` | 收集外部数据、压缩上下文，不把展示攻略送给模型 |
| 预算、规则和重排 | `backend/app/planner/` 下的 `output.py`、`pricing.py`、`rerank.py`、`dates.py`、`destination.py` | 确定性规则和评分，不是训练过的 Reranker |
| 实时进度与诊断 | `backend/app/observability.py`、`backend/app/api/routes/trips.py`；`frontend/src/services/progress.ts`、`frontend/src/services/progressText.ts`、`frontend/src/views/TripDetail.vue` | SSE 事件落库重放、请求／运行编号、耗时及错误类型 |
| 结果、编辑保存和导出 | `frontend/src/views/Result.vue`、`frontend/src/views/TripDetail.vue`、`frontend/src/services/trips.ts`；`backend/app/api/routes/trips.py` | 完成后带 revision 保存，冲突不静默覆盖 |
| 景点图片 | `backend/app/services/poi_photo_service.py`、`backend/app/api/routes/poi.py`；`frontend/src/services/photos.ts` | 核验高德地点身份，无照片时占位，不混入泛风景图 |
| 开放时间、预约和攻略 | `backend/app/services/visit_info_service.py`、`backend/app/services/official_visit_sources.json`；`frontend/src/services/visitInfo.ts`、`frontend/src/components/AttractionVisitInfo.vue` | 结果页独立查询、人工核验登记表、可信外链，不改规划模型 |
| 高德地图与路线 | `backend/app/services/amap_service.py`、`backend/app/api/routes/map.py`；`frontend/src/views/Result.vue` | 后端 Web 服务与浏览器地图 SDK 各自使用对应配置 |
| 主题与响应式布局 | `frontend/src/styles/theme.css`、`frontend/src/styles/theme.ts`、`frontend/src/App.vue` 及各页面组件 | 统一主题；修改时保留表单、认证、SSE 和保存行为 |
| 数据库结构 | `backend/app/database.py`、`backend/migrations/versions/` | 业务表由 Alembic 维护，检查点表由 PostgreSQL Saver setup 管理 |
| 云端发布、健康检查与备份 | `compose.prod.yaml`、`deploy/manage.sh`、`backend/app/production.py`、`backend/app/api/main.py` | 三个常驻容器，失败退出、就绪检查、手动备份；不是多机高可用 |
| 个人入口与网站路由 | `deploy/portal/index.html`、`deploy/Caddyfile`、`deploy/web.Dockerfile` | 静态首页与 Vue 项目共享 web 容器；API/SSE 同源反向代理 |
| HTTP 提交兼容 | `frontend/src/services/idempotency.ts`、`frontend/src/views/Home.vue` | HTTP 缺少 randomUUID 时用 getRandomValues 生成 UUID v4 |
| 日常环境管理 | `scripts/dev.py`、`scripts/container-setup.sh`、`.vscode/tasks.json` | 环境启动不等于前后端已启动；共享数据库独立启停 |

上表路径除特别注明均从仓库根目录开始。前端测试与组件相邻，后端测试集中在 `backend/tests/`。如果改的是 UI，不要顺带调整模型流程或数据库表；如果改了数据库结构，需新增迁移并验证原有历史兼容。

## 文档维护入口

- 线上访问、配置与运维：[CLOUD_DEPLOYMENT.md](docs/CLOUD_DEPLOYMENT.md)。
- 新人启动：[LOCAL_DEV_GUIDE.md](docs/LOCAL_DEV_GUIDE.md)。
- 技术流程与恢复边界：[ARCHITECTURE.md](docs/ARCHITECTURE.md)。
- 面试讲解：[INTERVIEW_GUIDE.md](docs/INTERVIEW_GUIDE.md)。
- 浏览器测试及实际结果：[BROWSER_ACCEPTANCE.md](docs/BROWSER_ACCEPTANCE.md)。
- 页面主题：[UI_DESIGN.md](docs/UI_DESIGN.md)。
- 图片与官方来源：[POI_PHOTOS.md](docs/POI_PHOTOS.md)、[VISIT_INFO.md](docs/VISIT_INFO.md)。

`docs/SUPABASE_LOCAL_SETUP.md` 明确标为已停用，只保留旧方案背景；`docs/LOCAL_DEV_EXECUTION.md` 记录各日期的历史实施结果，不能把旧测试数字当作当前结果。

本地 `.env`、`.venv`、`node_modules`、构建产物、缓存和日志不进入Git。
