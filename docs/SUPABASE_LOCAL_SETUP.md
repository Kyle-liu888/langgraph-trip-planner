# 本地运行：账号、历史行程、日志与实时进度

本轮不做部署、不买云服务器、不创建付费服务。前后端仍在你的电脑上运行；账号和行程数据库放在你选择区域的 Supabase 云端，因此需要联网。

截至 2026-09-04，Supabase Free 为 $0/月，每项目数据库 500 MB，闲置一周可能暂停。不要升级套餐或启用付费附加功能。模型 API、地图服务和自选邮件服务的费用另算。额度及规则以 [Supabase 价格页](https://supabase.com/pricing) 为准。

## 1. 准备你自己的 Supabase 项目

在 Supabase 控制台选择 Free 组织并创建一个专用项目。记下数据库密码，不要把密码或连接字符串发进聊天、截图、GitHub。

需要四处配置：

| 文件 | 变量 | 从哪里获取 |
| --- | --- | --- |
| backend/.env | DATABASE_URL | Connect → Session pooler → URI，替换数据库密码 |
| backend/.env | SUPABASE_URL | 项目 URL，形如 https://项目标识.supabase.co |
| frontend/.env | VITE_SUPABASE_URL | 同一个项目 URL |
| frontend/.env | VITE_SUPABASE_PUBLISHABLE_KEY | 项目的 publishable key（允许公开），不是 secret / service_role key |

后端连接示例（不是可直接使用的凭据）：

```dotenv
DATABASE_URL=postgresql://postgres.PROJECT_REF:URL_ENCODED_PASSWORD@SESSION_POOLER_HOST:5432/postgres?sslmode=require
SUPABASE_URL=https://PROJECT_REF.supabase.co
```

为什么选 Session pooler：你的电脑可能只有 IPv4，而免费项目直接连接通常要求 IPv6。Session pooler 可以供本地常驻后端连接。请复制自己项目的真实主机名，不要猜。不能用 6543 transaction pooler：本项目持有会话级锁并要求连接会话稳定。详见 [官方连接说明](https://supabase.com/docs/guides/database/connecting-to-postgres)。

密码包含 @、#、%、/ 等字符时要进行 URL 编码。`sslmode=require` 加密连接；更严格的证书校验可根据控制台证书配置 `verify-full`。保留你原有的模型、高德、Unsplash 配置，不要用示例文件覆盖已有 `.env`。

## 2. 配置登录

### 邮箱密码

在 Authentication 中启用 Email provider。URL Configuration 中设置：

- Site URL：`http://localhost:5173`
- Redirect URLs：`http://localhost:5173/auth/callback`

保持邮箱确认开启；在注册后收到的确认邮件中点击链接。Supabase 默认邮件服务只面向项目团队授权邮箱、限额很低；给普通用户发确认邮件需配置自己的 SMTP。没有邮件服务时，可以先用下面的 GitHub 登录验证流程，不要把“没收到邮件”当成前端成功。参考 [官方 SMTP 说明](https://supabase.com/docs/guides/auth/auth-smtp)。

### GitHub

1. 在 GitHub 的 Developer settings 创建 OAuth App。
2. Homepage URL 填 `http://localhost:5173`。
3. Authorization callback URL 填 **Supabase GitHub provider 页面给出的回调地址**，通常是 `https://PROJECT_REF.supabase.co/auth/v1/callback`，不是本地前端地址。
4. 把 GitHub Client ID / Client Secret 填入 Supabase GitHub provider 并启用。Secret 不放前端或仓库。
5. 登录完成后 Supabase 会再跳转回本地 `/auth/callback`。

参考 [官方 GitHub 登录说明](https://supabase.com/docs/guides/auth/social-login/auth-github)。

### 签名方式

后端通过 JWKS 验证 Supabase access token 的签名、issuer、audience、过期时间和用户身份。项目必须使用 ES256 或 RS256 非对称签名；旧 HS256 项目需要先迁移签名密钥，再重新登录。项目地址必须在前后端完全一致。参考 [JWT Signing Keys](https://supabase.com/docs/guides/auth/signing-keys)。

## 3. 建表并启动后端

在项目根目录打开 PowerShell：

```powershell
cd backend
uv sync --frozen
uv run alembic upgrade head
uv run python run.py
```

- `uv sync`：依赖安装到当前项目的 `backend/.venv`，不会要求全局 Python。
- `alembic upgrade head`：在已配置的数据库中创建行程、运行、事件、额度表，以及私有检查点 schema；可重复运行。应使用专用项目的数据库 owner 连接。
- `run.py`：启动 FastAPI。第一次启动会初始化 LangGraph 检查点表。Windows 入口已选择兼容 psycopg 的 Selector 事件循环，请用这个入口。

查看 `http://localhost:8000/health`。`storage_ready=true` 才表示启动时成功接上数据库。`degraded` 表示后端进程启动了，但持久化不可用，不是已经跑通。该接口不是完整的实时数据库连通性探针。

## 4. 启动前端

另开一个终端：

```powershell
cd frontend
npm ci
npm run dev
```

环境变量建议 `VITE_API_BASE_URL=` 留空，让 Vite 代理 `/api` 到 8000。修改 `.env` 后需要重启对应服务。打开 `http://localhost:5173`，登录后左侧显示账号和历史，点击“新增行程”创建。

如果 `npm ci` 提示 esbuild.exe EPERM，先关闭**这个项目**的 Vite/build 进程再安装；不要全局杀掉所有 Node 进程。

## 5. 实际使用和恢复

1. 提交行程 → 返回行程编号，页面开始订阅 SSE。
2. 可见采集资料、整理条件、模型生成、校验、选择结果等真实节点；模型调用显示轮次和耗时。这里不是模型内部思维链。
3. 刷新或关闭页面 → 后台任务继续，重新打开历史会读取原任务，不会再次提交模型调用。
4. 后端停止或超时 → 行程显示“已中断”或“失败”。重启后点击“从检查点继续规划”，复用同一 LangGraph thread_id。
5. 已完成节点不会重复执行；中断中的节点需要重跑，尤其模型请求可能再次收费。恢复不是从一句话中间接着生成，也不能保证外部 API 恰好调用一次。
6. 正常结果和兜底结果分别标记。兜底不是模型生成成功；可以查看执行记录定位失败，再新建行程。
7. 编辑结果后点保存会写入数据库。两个页面同时编辑同一版本时，后保存者会收到冲突提示，需刷新后重做修改。

默认每账号每天最多新建 3 次（北京时间重置），每账号同时 1 个活跃行程，全服务并行 2 个，失败/中断最多恢复 3 次。可在后端 `.env` 调整；它们是安全上限，不代表免费 API。删除行程不会返还次数。

本版使用一个后端进程持有任务，数据库会话锁阻止同一个数据库启动第二个规划进程。不要使用多 worker。数据库暂时断开导致失败时，修好连接并重启后端，再手动恢复；不要误认为浏览器 SSE 重连能修复数据库。

## 6. 日志在哪

- 终端：启动后端的 PowerShell 实时显示。
- `backend/logs/app.log`：应用、HTTP 请求、节点、模型调用、重试、结束状态。
- `backend/logs/error.log`：ERROR 级别错误及不含敏感正文的调用栈。
- 两类文件各 10 MiB 轮转、保留 5 个备份。配置 `LOG_FORMAT=json` 可使用 JSON 日志。

实时查看：

```powershell
Get-Content .\backend\logs\app.log -Tail 60 -Wait
```

日志可用 `request_id`（请求）、`trip_id`（行程）、`run_id`（本次执行）关联。记录异常类型和代码位置，不输出完整 Prompt、模型原文、JWT 或密钥。模型错误会有 `model.failed`，数据校验错误会有 `validation.failed`，不能只看 error.log 判断有没有问题。

检查点需要保存请求、上下文和生成状态，因此**云数据库仍含行程内容**，只是日志不记录这些正文。业务表启用 RLS 且不开放浏览器读写；前端经后端鉴权访问。检查点放 `planner_internal` 私有 schema，不要把它加入 Supabase Data API 的 exposed schemas。JWT 退出后已有 access token 通常直到过期才失效；不要将 token 分享给别人。

当前没有自动历史过期删除；检查点和事件会占数据库容量。可以在侧边栏确认删除不再需要的行程，连同执行事件、运行记录、检查点一并删除且不可恢复。业务历史不会因为刷新或重启丢失。

## 7. 验证与已知边界

```powershell
cd backend
uv run --frozen pytest
cd ..\frontend
npm test
npm run build
```

离线测试使用 fake 模型、测试专用 SQLite 业务库与真实 SQLite checkpointer，覆盖持久化重开恢复、取消、SSE 顺序/重放/鉴权、账号隔离、额度、版本冲突、JWT 签名和日志脱敏；不会消耗真实模型或高德额度。

真实 Supabase 迁移、PostgreSQL checkpointer、邮箱投递、GitHub OAuth 和真实模型完整行程，必须在填好你的配置后联调；离线测试通过不等于这些外部服务已验收。没有配置时前端显示配置提示，后端处于 degraded 状态，不存在匿名绕过或模拟登录开关。
