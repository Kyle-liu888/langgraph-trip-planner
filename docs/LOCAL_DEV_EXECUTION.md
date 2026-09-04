# 执行记录

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
