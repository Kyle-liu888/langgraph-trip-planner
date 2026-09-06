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

如果这台电脑已经完成环境迁移、以前成功打开过网页，直接看下一节「日常运行：一步一步」，不必重复安装 Docker 或创建数据库。

1. 打开 Docker Desktop，确认 WSL2 后端及 Ubuntu 集成开启。不要在 Ubuntu 再装一套 Docker Engine。
2. 数据盘在 C 盘时，通过 Settings → Resources → Advanced → Disk image location 迁移到 D 盘。先退出容器工作、备份数据盘；不要手动移动运行中的 VHDX。此次原盘和机器设置备份在 `D:\DevBackups\setup-20260904`。
3. VS Code 安装官方 WSL 和 Dev Containers 扩展（编辑器扩展不是项目全局运行时）。
4. 在 Ubuntu 终端进入新项目，先生成缺少的本地配置文件：

```bash
cd ~/dev/projects/langgraph-trip-planner
python3 scripts/dev.py setup
```

5. **首次新机器：填写外置配置，再启动。** `setup` 只从仓库的 `.env.example` 复制模板，不会生成模型／高德 Key，也不会验证供应商账户权限。示例里的 `your-...` 不能直接使用。用编辑器打开下面的本地文件，填写自己的配置；不要把完整文件、Key 或截图发到聊天和 GitHub。

| 本地文件 | 必须确认的字段 | 填写原则 |
| --- | --- | --- |
| `~/dev/config/trip-backend.env` | `LLM_PROVIDER`、`LLM_MODEL`、`LLM_API_KEY` | 选择同一家供应商、账户可调用的模型 ID 和对应密钥；切换可选供应商前按 README 安装对应集成 |
| 同上 | `LLM_BASE_URL` | 使用该供应商指定的接口地址；支持默认地址的集成可留空，但不要保留另一家地址，OpenAI-compatible 服务需填写自己的兼容地址 |
| 同上 | `AMAP_API_KEY` | 后端高德 Web 服务 Key，用于景点、天气等请求，不是浏览器 JS API Key |
| `~/dev/config/trip-frontend.env` | `VITE_AMAP_WEB_JS_KEY` | 浏览器地图 SDK 对应的高德 Web 端 JS API Key；缺失或权限不符会影响地图展示 |
| 同上 | `VITE_API_BASE_URL` | 当前开发容器使用空值，让浏览器通过 Vite `/api` 代理访问后端，不填公网服务地址 |

`DATABASE_URL` 由下一步 `start` 创建专用数据库账号后注入，不需要手填管理员密码。`CORS_ORIGINS`、`HOST`、`PORT` 和前端代理地址由开发容器配置固定。前端模板中的旧 `VITE_AMAP_WEB_KEY` 当前没有被页面代码使用；Unsplash 字段也不是当前景点图片链路的必需配置，可保持空值。超时、日志、额度等其余字段先沿用模板；这里无需配置 Supabase 或 GitHub 登录。

6. 配置填好后，在同一个 Ubuntu 项目目录继续：

```bash
python3 scripts/dev.py pin-images
python3 scripts/dev.py start
```

`setup` 不覆盖已有密钥。`pin-images` 拉取明确版本并读取注册表摘要，生成不可变锁；已有锁时拒绝自动更新，此时跳过 `pin-images`，不要为重复启动删除锁文件。拉取镜像需要网络能访问 Docker Hub/GHCR；无法拉取时先修复 Docker 的正常网络／代理设置，不关闭系统防火墙、不换不明镜像。

首次 `start` 启动共享数据库、创建旅行助手专用账号、构建非 root 项目容器，再在容器内执行 `uv sync --locked` 和 `npm ci`。配置未改且项目容器已运行时，它会跳过项目重建和依赖重装。Python/Node 依赖在命名卷内，既不复制 Windows 依赖，也不全局安装到 Ubuntu。

现有模型/地图配置在 `~/dev/config/trip-backend.env`，地图前端配置在 `trip-frontend.env`。应用数据库地址由脚本生成到 `trip-database.env` 并注入容器，优先于旧后端文件里的同名值。管理员密码不挂载到应用容器。

然后用 VS Code 打开 Linux 文件夹，执行 **Dev Containers: Reopen in Container**。在“终端 → 运行任务”按顺序执行：

1. **数据库迁移**：创建账号、会话、历史等表。第一次运行或 schema 更新后必须做；不会自动删除历史。
2. **启动后端（含日志）**：开始提供登录、规划和历史接口。
3. **启动前端**：打开用户界面。

浏览器使用 `http://127.0.0.1:5173`。这台电脑的 localhost IPv6 路径可能超时，IPv4 回环地址已验证正常。前后端任务分开，方便看到各自日志。不要把 localhost 和 127.0.0.1 混用；Cookie 按主机隔离。端口只发布在本机回环地址，容器内部监听 0.0.0.0 是为了让端口映射可达，不代表公开到互联网。

## 日常开始与结束

### 日常运行：一步一步

本节针对已经初始化过的环境。前端、后端和数据库是三个部分：数据库保存账号和行程；后端提供接口并运行规划；前端是浏览器里的操作页面。只打开网页或只启动容器，不等于三者已经全部可用。

1. **Windows：打开 Docker Desktop，等待引擎运行。** 它负责启动项目和 PostgreSQL 容器；不用在 Windows 激活 Python 虚拟环境。
2. **Windows PowerShell：进入 Ubuntu。**

   ```powershell
   wsl -d Ubuntu
   ```

3. **Ubuntu 终端：进入 Linux 主工作区并启动容器。**

   ```bash
   cd ~/dev/projects/langgraph-trip-planner
   python3 scripts/dev.py start
   python3 scripts/dev.py status
   code .
   ```

   按 `start` → `status` 顺序操作即可。配置未改时，`start` 可重复执行来确保容器运行：已有项目容器会直接跳过重建与依赖重装；共享数据库也会被检查并确保启动。它不会替你常驻运行前后端。

   `status` 只列出容器和活跃规划数量，不代表前后端进程一定在运行。若后面的前后端任务已在终端运行，或对应网页／健康地址已经可达，就跳过重复启动那个进程。不要重复的是第 6、7 步的 `uv run`／`npm run dev`，不是上面的环境检查；不要为了执行这套步骤强行停止正在规划的任务。

4. **VS Code：连接项目容器。** 按 Ctrl+Shift+P，执行 `Dev Containers: Reopen in Container`。新终端的项目路径应为 `/workspace`，不是 `C:\\Users\\...`，也不是 Ubuntu 主机的 `~/dev/projects/...`。
5. **容器内：更新数据库表结构。** 首次启动、拉取含迁移的代码后必须运行；重复执行只会应用尚未完成的迁移。可使用“终端 → 运行任务 → 数据库迁移”，或：

   ```bash
   cd /workspace/backend
   uv run --locked alembic upgrade head
   ```

6. **容器终端 A：启动后端，保持该终端运行。**

   ```bash
   cd /workspace/backend
   uv run --locked python run.py
   ```

7. **容器终端 B：启动前端，保持该终端运行。**

   ```bash
   cd /workspace/frontend
   npm run dev -- --host 0.0.0.0 --strictPort
   ```

8. **Windows 浏览器：打开 [旅行助手](http://127.0.0.1:5173)。** 首次使用需要注册本地账号。已有行程可直接打开，不必再点击“开始规划行程”。

   后端检查地址为 [健康状态](http://127.0.0.1:8000/health)。除了能打开，还要看 JSON 中 `status` 为 `healthy`、`storage_ready` 为 `true`；HTTP 200 也可能返回 `degraded`。该接口表示初始化状态，不是每次实时探测数据库。

不要在 Windows 旧项目文件夹运行上述 `uv`、`npm` 命令。不要重复执行 `npm ci` 来启动界面：它是重装锁定依赖的命令，启动命令是 `npm run dev`。

### 停止哪个范围

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

`EndAll` 会先显示所有容器、任务数和 WSL 发行版。输入 `END ALL`，再输入 Linux 管理器要求的 `STOP ALL` 才继续：先备份 → 正常停止应用 → 再备份最终状态 → 停数据库 → 退出 Docker → 关闭全部 WSL。这会停止其他项目的 WSL 工作，不能在它们需要继续运行时使用。任一次备份失败就暂停，不执行后续关闭。

关闭 VS Code/浏览器不会自动停止规划或整套环境。所有关闭操作均不删除数据卷，不执行 prune。不要自行运行 `docker compose down -v`。

### Windows 快捷脚本被签名策略拦截时

这台电脑实测会拒绝直接运行 WSL UNC 路径下未签名的 PowerShell 脚本。无需降低执行策略；使用以下分步方式即可。

开始：打开 Docker Desktop；在 Ubuntu 中运行本页的 `python3 scripts/dev.py start`，再通过 VS Code 分别启动前后端任务。

结束：先在 Ubuntu 中运行下面的命令，查看所有容器/任务并输入 `STOP ALL` 确认。命令必须成功完成，备份失败时不要继续：

```bash
cd ~/dev/projects/langgraph-trip-planner
python3 scripts/dev.py stop-containers
```

确认已显示容器停止、数据卷保留之后，在 Windows PowerShell 执行：

```powershell
docker desktop stop
if ($LASTEXITCODE -ne 0) { throw 'Docker 未正常退出，暂停 WSL 关闭。' }
wsl --shutdown
wsl --list --verbose
```

这组步骤已在本机完成关闭/重启验收。最后应看到 Ubuntu 与 docker-desktop 都是 Stopped。下次打开 Docker 并启动项目后，数据仍会保留。

## 日志、进度与本地账号

- 控制台输出真实节点、模型调用开始/结束、耗时及错误类型。
- 文件日志位于 Linux 项目 `backend/logs/app.log` 和 `error.log`，每个文件 10 MiB、保留 5 个轮转文件。
- 前端 SSE 展示正在执行的 LangGraph 节点、生成次数和连接状态。断线只重订阅，不重新提交；过期重新登录后从历史打开。
- 已完成行程的详细事件收在“查看规划记录”中；运行中的节点直接显示。只有 `failed`（失败）或 `interrupted`（中断）状态显示“从检查点继续规划”按钮；正常完成或 `fallback`（兜底结果）不会显示。记录是程序执行状态，不是模型内部思考。
- 注册邮箱只是本地账号标识，不发验证邮件、不代表邮箱所有权已验证。密码使用 Argon2id；7 天会话只把哈希存入数据库，退出即撤销。
- 修改请求必须来自配置允许的 Origin，并携带当前页面获取的 CSRF token；登录/注册也有 CSRF 检查。
- 登录/注册共用 15 分钟窗口：单邮箱最多 10 次，单来源 IP 最多 60 次；计数持久化，不随重启清空。
- 暂无忘记密码邮件与 GitHub 登录，也没有默认账号或匿名绕过。
- 原始提示词、会话令牌、密钥不写运行日志；检查点本身包含用户行程条件，备份也应当视作隐私数据。

### 什么时候能继续规划

恢复前先确保后端和数据库已就绪、当前账号有权访问该行程，并排除日志里的 Key、网络或数据库故障；仅重连 SSE 不会解决这些问题。

- 后端只接受失败／中断行程，且要求原请求是具体城市、检查点图版本兼容、未超过恢复次数上限（代码默认 3 次）、同账号没有其他排队／运行中的行程、服务不处于关闭过程。按钮出现不代表这些条件都已满足，未满足会显示具体错误。
- 能读到已有检查点时，沿用同一个行程的 `thread_id` 恢复未完成节点；若检查点已完成、只差历史结果写入，则直接补写结果。**如果还没有保存任何检查点，程序会从原始请求重新开始**，不是从模型正文中间继续。
- 检查点数据库不可访问时无法读取状态，需要先修复连接；图版本不兼容、恢复次数已用完或原请求目的地不合要求时，按提示检查配置后新建行程。已删除行程不能通过这个按钮找回，只能另走数据库备份恢复流程。
- 中断中的节点和从头重跑都可能再次请求模型／地图并产生费用；不要为了测试按钮反复恢复真实行程。接口受理恢复会增加该行程的恢复次数。

## 后续项目共用 PostgreSQL

```bash
python3 scripts/dev.py new-db my_project
```

它创建 `my_project` 数据库与 `my_project_app` 非超级用户，角色属性为 `NOCREATEDB`、`NOCREATEROLE`、`NOREPLICATION`、`NOBYPASSRLS`。其中 `NOBYPASSRLS` 表示没有跨表通用的 RLS 绕过特权，**不取消表 owner 对自己表默认绕过 RLS 的行为**；应用使用本项目 owner，账号之间的行程隔离仍依靠后端会话认证和用户 ID 查询过滤，不能只靠这个角色属性。配置写在 `~/dev/config/my_project-database.env`。已有名称不覆盖；失败的初始化保留 pending 配置以供检查，不擅自删除半成品数据库。

其他项目容器接入 `local-dev` Docker 网络，使用 `postgres:5432` 和自己的账号。Windows 数据库客户端可使用 `127.0.0.1:15432`；不能把管理员凭据给应用。各库撤销 PUBLIC 连接权限。

## 备份与恢复

```bash
python3 scripts/dev.py backup
python3 scripts/dev.py restore /mnt/d/DevBackups/postgres/trip/<时间>.dump trip_restore_check
```

备份使用 pg_dump 自定义格式，成功读取目录后才完成文件并生成 SHA256；每库最多 14 个已完成备份。备份失败留下 .partial 供排查，不轮换旧备份。恢复要求校验和匹配并创建全新数据库/账号，使用事务恢复；原库不覆盖。恢复后需验证账号、行程、检查点再考虑切换连接。D 盘和原盘仍在同一台电脑，不能防硬盘损坏。

## 测试和验收

已完成的实际结果以执行记录顶部为准。配置也会备份到 D 盘 `DevBackups/config`，含密码与 API 密钥，必须限制目录访问；这台电脑已设置为仅当前用户和 SYSTEM。其他电脑首次使用时也应限制 Windows 备份目录权限，不要把备份发到 GitHub。

容器内的“后端测试”“前端测试与构建”任务不调用真实模型或地图 API。`scripts/test_dev.py` 用模拟 Docker 验证危险操作的保护。

Ubuntu 主机运行：

```bash
python3 scripts/dev.py verify-postgres
python3 scripts/dev.py backup
```

真实 PostgreSQL 验收会创建两个独立 `test_*` 数据库，验证非超级用户/跨库连接隔离，运行本地账号、历史编辑、SSE 重放、检查点跨连接恢复测试。测试数据库保留，脚本不自动删除。独立测试文件默认跳过，不提供数据库不能算通过。

还必须人工/辅助完成：恢复到新库演练、重建容器但保留命名卷、停止旅行助手时第二项目仍可连接，以及经确认的全部关闭/重启数据验证。不要把源码语法检查等同于这些验收。最后一条真实行程由你主动提交，不自动消费 API 额度。

## 常见故障

排查时先记录页面上的错误、发生时间和行程编号；不要贴出密码、Cookie、完整环境文件或含 Key 的请求地址。

在 Ubuntu 主工作区查看文件日志：

```bash
cd ~/dev/projects/langgraph-trip-planner
tail -n 80 backend/logs/error.log
tail -f backend/logs/app.log
```

按 Ctrl+C 只结束 `tail` 查看，不会结束后端。若日志文件尚未生成，先确认后端确实启动过。

- `storage.startup_failed` / degraded：确认 PostgreSQL 健康和迁移已执行，查看日志 stage；不要贴出完整 .env。
- `Network Error`：确认前端、后端任务都在运行；默认前端走 Vite /api 代理，端口固定不自动递增。
- 403 CSRF/Origin：统一访问主机名，刷新页面；允许来源需是完整 URL，不要设通配符。
- Windows 的 python 找不到：新流程在开发容器内使用 uv，不依赖 Windows 的 python 命令。
- 端口冲突：脚本报告并停止，不强杀其他项目。
- 数据库大版本升级：另开备份/恢复兼容性任务，不直接改成 latest。

完整浏览器验收与模拟服务边界见 [浏览器验收记录](BROWSER_ACCEPTANCE.md)；讲解项目时可参考 [面试讲解指南](INTERVIEW_GUIDE.md)。
