# 本地隔离开发操作手册

> 实施状态请先看 [执行记录](LOCAL_DEV_EXECUTION.md)。配置已写入不等于真实容器验收通过；未通过的项目不会标记完成。完整、不删减的原计划见 [LOCAL_DEV_PLAN.md](LOCAL_DEV_PLAN.md)。

## 这些东西分别在哪里

- Windows 只打开 Docker Desktop、VS Code 和浏览器；本次不在 Windows 安装 Python、Node 或 PostgreSQL。
- Ubuntu 的 `~/dev/projects/langgraph-trip-planner` 是新主工作区，旧 Windows 项目完整保留。
- `~/dev/infra/postgres` 是共享数据库配置，独立于旅行助手容器。
- `~/dev/config` 保存密钥、管理员密码与各项目独立数据库账号；目录 700，凭据文件 600，不进 Git。
- PostgreSQL 17 数据在 Docker 命名卷 `local-dev-postgres-17-data`，不是项目文件夹。D 盘备份在 `D:\DevBackups\postgres`。
- 前端通过后端取数据，不知道数据库密码。模型和高德仍需联网，也仍可能计费。

## 首次准备

1. 打开 Docker Desktop，确认 WSL2 后端及 Ubuntu 集成开启。不要在 Ubuntu 再装一套 Docker Engine。
2. 数据盘在 C 盘时，通过 Settings → Resources → Advanced → Disk image location 迁移到 D 盘。先退出容器工作、备份数据盘；不要手动移动运行中的 VHDX。此次原盘和机器设置备份在 `D:\DevBackups\setup-20260904`。
3. VS Code 安装官方 WSL 和 Dev Containers 扩展（编辑器扩展不是项目全局运行时）。
4. 在 Ubuntu 终端进入新项目，执行：

```bash
cd ~/dev/projects/langgraph-trip-planner
python3 scripts/dev.py setup
python3 scripts/dev.py pin-images
python3 scripts/dev.py start
```

`setup` 只创建缺少的配置，不覆盖已有密钥。`pin-images` 拉取明确版本并读取注册表摘要，生成不可变锁；已有锁时拒绝自动更新。此时网络必须能访问 Docker Hub/GHCR。无法拉取时先修复 Docker 的正常网络/代理设置，不关闭系统防火墙、不换不明镜像。

`start` 启动共享数据库、创建旅行助手专用账号、构建非 root 项目容器，再在容器内执行 `uv sync --locked` 和 `npm ci`。Python/Node 依赖在命名卷内，既不复制 Windows 依赖，也不全局安装到 Ubuntu。

现有模型/地图配置在 `~/dev/config/trip-backend.env`，地图前端配置在 `trip-frontend.env`。应用数据库地址由脚本生成到 `trip-database.env` 并注入容器，优先于旧后端文件里的同名值。管理员密码不挂载到应用容器。

然后用 VS Code 打开 Linux 文件夹，执行 **Dev Containers: Reopen in Container**。在“终端 → 运行任务”按顺序执行：

1. **数据库迁移**：创建账号、会话、历史等表。第一次运行或 schema 更新后必须做；不会自动删除历史。
2. **启动后端（含日志）**：开始提供登录、规划和历史接口。
3. **启动前端**：打开用户界面。

浏览器使用 `http://localhost:5173`。前后端任务分开，方便看到各自日志。不要把 localhost 和 127.0.0.1 混用；Cookie 按主机隔离。端口只发布在本机回环地址，容器内部监听 0.0.0.0 是为了让端口映射可达，不代表公开到互联网。

## 日常开始与结束

Ubuntu 内：

```bash
python3 scripts/dev.py start        # 启动环境；前后端仍由明确任务启动
python3 scripts/dev.py status       # 列出容器与各数据库的活跃规划数
python3 scripts/dev.py stop-trip    # 只停旅行助手，保留共享 PostgreSQL
```

Windows PowerShell 可调用 Linux 工作区的 `scripts/windows-dev.ps1`：

```powershell
# 把下面路径中的 <Linux用户名> 换为自己的用户名（这台电脑是 kyle）
& "\\wsl.localhost\Ubuntu\home\<Linux用户名>\dev\projects\langgraph-trip-planner\scripts\windows-dev.ps1" -Action Start
# -Action StopTrip / Status / EndAll
```

`EndAll` 会先显示所有容器、任务数和 WSL 发行版。输入 `END ALL`，再输入 Linux 管理器要求的 `STOP ALL` 才继续：先备份 → 正常停止应用 → 再备份最终状态 → 停数据库 → 退出 Docker → 关闭全部 WSL。会停止 Ollama 和其他 WSL 工作，不能在它们需要继续运行时使用。任一次备份失败就暂停，不执行后续关闭。

关闭 VS Code/浏览器不会自动停止规划或整套环境。所有关闭操作均不删除数据卷，不执行 prune。不要自行运行 `docker compose down -v`。

## 日志、进度与本地账号

- 控制台输出真实节点、模型调用开始/结束、耗时及错误类型。
- 文件日志位于 Linux 项目 `backend/logs/app.log` 和 `error.log`，每个文件 10 MiB、保留 5 个轮转文件。
- 前端 SSE 展示正在执行的 LangGraph 节点、生成次数和连接状态。断线只重订阅，不重新提交；过期重新登录后从历史打开。
- 注册邮箱只是本地账号标识，不发验证邮件、不代表邮箱所有权已验证。密码使用 Argon2id；7 天会话只把哈希存入数据库，退出即撤销。
- 修改请求必须来自配置允许的 Origin，并携带当前页面获取的 CSRF token；登录/注册也有 CSRF 检查。
- 登录/注册共用 15 分钟窗口：单邮箱最多 10 次，单来源 IP 最多 60 次；计数持久化，不随重启清空。
- 暂无忘记密码邮件与 GitHub 登录，也没有默认账号或匿名绕过。
- 原始提示词、会话令牌、密钥不写运行日志；检查点本身包含用户行程条件，备份也应当视作隐私数据。

## 后续项目共用 PostgreSQL

```bash
python3 scripts/dev.py new-db my_project
```

它创建 `my_project` 数据库与 `my_project_app` 非超级用户，禁止建库、建角色、复制及绕过 RLS。配置写在 `~/dev/config/my_project-database.env`。已有名称不覆盖；失败的初始化保留 pending 配置以供检查，不擅自删除半成品数据库。

其他项目容器接入 `local-dev` Docker 网络，使用 `postgres:5432` 和自己的账号。Windows 数据库客户端可使用 `127.0.0.1:15432`；不能把管理员凭据给应用。各库撤销 PUBLIC 连接权限。

## 备份与恢复

```bash
python3 scripts/dev.py backup
python3 scripts/dev.py restore /mnt/d/DevBackups/postgres/trip/<时间>.dump trip_restore_check
```

备份使用 pg_dump 自定义格式，成功读取目录后才完成文件并生成 SHA256；每库最多 14 个已完成备份。备份失败留下 .partial 供排查，不轮换旧备份。恢复要求校验和匹配并创建全新数据库/账号，使用事务恢复；原库不覆盖。恢复后需验证账号、行程、检查点再考虑切换连接。D 盘和原盘仍在同一台电脑，不能防硬盘损坏。

## 测试和验收

容器内的“后端测试”“前端测试与构建”任务不调用真实模型或地图 API。`scripts/test_dev.py` 用模拟 Docker 验证危险操作的保护。

Ubuntu 主机运行：

```bash
python3 scripts/dev.py verify-postgres
python3 scripts/dev.py backup
```

真实 PostgreSQL 验收会创建两个独立 `test_*` 数据库，验证非超级用户/跨库连接隔离，运行本地账号、历史编辑、SSE 重放、检查点跨连接恢复测试。测试数据库保留，脚本不自动删除。独立测试文件默认跳过，不提供数据库不能算通过。

还必须人工/辅助完成：恢复到新库演练、重建容器但保留命名卷、停止旅行助手时第二项目仍可连接，以及经确认的全部关闭/重启数据验证。不要把源码语法检查等同于这些验收。最后一条真实行程由你主动提交，不自动消费 API 额度。

## 常见故障

- `storage.startup_failed` / degraded：确认 PostgreSQL 健康和迁移已执行，查看日志 stage；不要贴出完整 .env。
- `Network Error`：确认前端、后端任务都在运行；默认前端走 Vite /api 代理，端口固定不自动递增。
- 403 CSRF/Origin：统一访问主机名，刷新页面；允许来源需是完整 URL，不要设通配符。
- Windows 的 python 找不到：新流程在开发容器内使用 uv，不依赖 Windows 的 python 命令。
- 端口冲突：脚本报告并停止，不强杀其他项目。
- 数据库大版本升级：另开备份/恢复兼容性任务，不直接改成 latest。
