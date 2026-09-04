# 执行记录

## 最新状态：Docker 迁移后的真实验收

- Docker 数据盘已实际迁至 D 盘；Ubuntu 集成已启用，没有安装第二套 Engine。
- Python 3.13.15、Node 24.18.0、uv 0.11.28、PostgreSQL 17.11 镜像已拉取，明确版本及 registry SHA256 已保存到 `infra/postgres/images.lock.env`。
- 项目容器以 1000:1000 运行，4 CPU / 6 GiB；数据库 2 CPU / 2 GiB。端口仅发布到 127.0.0.1；未挂载 Docker socket 或 Windows 用户目录。
- 容器内依赖安装成功；19 项后端测试通过，默认跳过的真实 PostgreSQL 测试另行执行并通过；前端 4 项测试和生产构建通过；基础设施安全测试 6 项通过。
- PostgreSQL 验收覆盖账号/会话/CSRF/限速、非超级用户和跨库权限隔离、历史编辑、SSE 重放与检查点跨连接恢复。新增了已打开 SSE 连接在退出后失效的回归测试。
- 备份恢复到新库后，账号、会话、历史和检查点等 12 张表的记录数及内容摘要一致。
- 重建项目和 PostgreSQL 容器，重新挂载原命名卷后，以上数据保持一致。独立第二项目客户端在旅行助手停止时仍可查询。
- 正常停服脚本已经实测：先让后端/Vite 退出，日志出现 server.stopped，再停容器；前端端口关闭。
- 后端 health 为 healthy，storage_ready/auth_configured 为 true；Windows 的 127.0.0.1 可访问前端、后端及前端登录代理。localhost 的 IPv6 路径超时，推荐统一使用 127.0.0.1。
- 数据库和配置备份已写入 D 盘，备份目录 Windows 权限限定当前用户和 SYSTEM；Linux 配置目录 700、凭据 600。
- VS Code 官方 Dev Containers 扩展已安装。原 Windows 项目和 main 保持原样。
- 此前提交已经成功推送到 `codex/local-dev-environment`，之前的 GitHub 连接错误已解除。

**最终关闭与重启验收已通过（2026-09-04，用户当次明确授权）。**

- 先确认全部活跃规划为 0，记录四个本地数据库的表内容摘要；完成关闭前、正常停服后的数据库及配置备份。
- 后端/Vite 正常退出，容器全部停止，再退出 Docker Desktop、执行 wsl --shutdown。Ubuntu 与 docker-desktop 均为 Stopped；5173、8000、15432 的 TCP 连接均失败，符合预期。
- 使用 Docker Desktop 官方 CLI 重启，再恢复共享 PostgreSQL、项目容器、前端和后端。
- 四个数据库共 36 张业务/账号/会话/检查点及迁移表的记录数和内容摘要，与关机前完全一致（第二项目空库为 0 张）。
- Windows 访问前端与登录代理均 HTTP 200；后端 health=healthy，storage_ready/auth_configured=true，数据库端口重新可达。
- Ollama 的自启动按用户后续要求已禁用；此次 Ubuntu 重启后验证为 disabled / inactive，没有随环境启动。
- 全程未删除数据卷，未调用真实模型或地图 API；项目现处于运行状态。

Windows 的未签名 UNC PowerShell 快捷脚本被当前执行策略拦截，因此本次通过已验证的 Linux 管理入口及 Docker/WSL 命令分步完成，没有更改执行策略。日常手册已补充相同的分步操作方式。真实模型生成一条行程仍由用户主动验收。

## 以下为首次实施时的历史记录

本次实现以 `LOCAL_DEV_PLAN.md` 完整计划为准。本文件仅记录执行状态，不替代或压缩计划。

- 原 Windows 工作区保留，Linux 主工作区：`/home/kyle/dev/projects/langgraph-trip-planner`。
- 原 Docker 数据盘与设置、WSL 配置已备份到 `D:\DevBackups\setup-20260904`；数据盘 SHA256 校验一致。
- WSL 防火墙已恢复开启，未修改镜像网络与全局资源上限。
- Linux 直连 GitHub 超时，改为从原工作区完整克隆 Git 历史，并恢复 GitHub origin；没有复制依赖或密钥入 Git。
- 待用户通过 Docker Desktop 官方界面迁移数据盘到 D 盘并启动引擎。
- 尚未完成：容器运行、真实 PostgreSQL 验收、全部关闭与重启演练。

## 已写入的实现（待容器联调）

- 非 root 开发容器、Python 3.13 / Node 24 / uv 版本配置，独立共享 PostgreSQL Compose。
- 镜像固定脚本要求真实 registry digest；尚未拉取成功，所以未伪造摘要、未生成镜像锁。
- 本地 Argon2id 账号、7 天 Cookie 会话、来源/CSRF 检查、持久化登录限速和 SSE 会话撤销检查。
- 前端替换 Supabase 登录，删除 GitHub 入口，保留历史、进度、结果展示；依赖锁已更新。
- 开始/单项目停止/确认后全部关闭脚本；备份校验、14 份轮换、新库恢复；真实 PostgreSQL 专用验收入口。
- 完整原计划和中文操作手册已保存，旧 Supabase 文档标记历史用途。

## 实际验证结果

- Python 源码/测试/迁移/管理脚本 compileall：通过。
- PowerShell 脚本语法、Bash 脚本语法：通过。
- 两套 Compose 的静态配置校验：通过（不等于服务启动）。
- Login.vue 使用原项目已有编译器的 SFC 编译：通过；没有复制依赖到新项目。
- 基础设施安全单元测试：6 项通过；覆盖配置不覆盖、名称校验、取消、备份失败阻止关闭、既有库拒绝覆盖、镜像锁拒绝隐式升级。
- 新后端/前端整套测试与生产构建：尚未执行，需容器；没有在 Windows 新装依赖来绕过隔离要求。
- npm 锁审计：现有间接依赖 fflate 存在 1 个 moderate 告警；当前功能不导入压缩包。未运行不加审查的 audit fix。

## 当前外部阻塞

Docker Desktop 启动操作被当前工具策略拒绝；原生窗口控制入口不可用。需要用户打开 Docker Desktop，通过官方界面完成 D 盘迁移。Docker Hub 直连超时，待引擎正常联网后再执行 pin-images。

尚未创建/迁移真实本地数据库，尚未执行容器重建、备份恢复演练、全部关闭重启。Ubuntu 因工作区操作处于运行状态；Ollama 未被卸载或强行停止。

## Git 保存状态

代码已按后端账号、前端会话、开发环境、文档拆分提交到本地分支 `codex/local-dev-environment`，提交前通过本地凭据对照扫描。原 Windows 工作区和 main 均未改动。

GitHub push 两次均返回 Connection was reset；GitHub 连接器也未能访问该仓库。因此远程推送尚未成功，不能在 GitHub 上查看本轮改动。网络恢复后推送同一分支，不强推、不覆盖 main：

```bash
git push -u origin codex/local-dev-environment
```
