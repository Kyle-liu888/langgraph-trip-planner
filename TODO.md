# Roadmap

- [x] 增加SSE流式进度，让前端显示当前LangGraph节点。
- [x] 接入持久化Checkpointer，支持恢复和历史行程。
- [x] 接入可核验的景点开放时间、预约和实时票价来源。
- [x] 为公开Demo增加IP限流、缓存、调用额度与超时取消。
- [x] 增加Docker、CI和云端部署配置。
- [ ] 增加LangSmith/OpenTelemetry可选追踪。


# 启动本地服务

你重构后的项目在 **WSL 的 `/home/kyle/dev/projects/langgraph-trip-planner`**。按下面步骤启动即可，建议使用 VS Code。

1. **在 Windows 打开 Docker Desktop**，等待启动完成。

2. **打开 PowerShell，进入 Ubuntu：**

   ```powershell
   wsl -d Ubuntu
   ```

3. **在 Ubuntu 中进入项目并启动容器：**

   ```bash
   cd ~/dev/projects/langgraph-trip-planner
   python3 scripts/dev.py start
   ```

   这一步启动数据库和开发容器。日常使用不需要重新安装环境或执行初始化命令。

4. **用 VS Code 打开项目：**

   ```bash
   code .
   ```

   在 VS Code 中按 `Ctrl + Shift + P`，搜索并执行：

   ```text
   Dev Containers: Reopen in Container
   ```

   等待连接完成。此时 VS Code 的终端就在项目开发容器中。

5. **启动后端。**

   在 VS Code 顶部选择：

   **终端 → 运行任务 → 启动后端（含日志）**

   保持这个任务运行。打开[后端健康检查](http://127.0.0.1:8000/health)，应看到 `"status": "healthy"`。

6. **启动前端。**

   再选择：

   **终端 → 运行任务 → 启动前端**

   然后打开：[旅行助手](http://127.0.0.1:5173)。

   已有本地账号直接登录，没有就注册。数据库之前已经迁移完成，正常情况下不需要再次迁移。

如果提示端口被占用，先打开上述两个链接检查，可能服务已经启动，不要重复运行。

注意区分两个终端：**`scripts/dev.py start` 在 Ubuntu 中执行；前后端启动任务在 VS Code 开发容器中执行。** 不要进入桌面旧项目运行，也不需要激活 Windows 的 `.venv`。


我检查了这个目录当前的 **19 个 Skill**，并结合你的项目代码做了筛选。结论：**最值得关注的是 `frontend-design`、`webapp-testing` 和 `doc-coauthoring`，不用全部安装。**

这些 Skill 主要是“帮助开发工作的操作指南”，不是装上后就会自动增加网站功能。

## 现在最有用的

| Skill | 对当前项目的具体用途 | 建议 |
|---|---|---|
| [frontend-design](https://github.com/anthropics/skills/blob/main/skills/frontend-design/SKILL.md) | 设计页面布局、配色、字体、移动端适配和交互细节 | **已安装，继续使用**，刚才的美化就是用它完成的 |
| [webapp-testing](https://github.com/anthropics/skills/blob/main/skills/webapp-testing/SKILL.md) | 用真实浏览器测试注册登录、历史行程、编辑、导航；检查截图和浏览器日志 | **最值得下一步补充** |
| [doc-coauthoring](https://github.com/anthropics/skills/blob/main/skills/doc-coauthoring/SKILL.md) | 整理 README、启动教程、架构设计、功能说明和面试讲解材料 | **推荐补充** |

为什么测试和文档值得优先做：

- **测试方面**：当前已有 47 项前端测试，但主要是 Vitest＋jsdom＋模拟服务。还没有项目内可重复运行的完整浏览器端到端测试。`webapp-testing` 有助于补这层，不过需要适配当前开发容器和 SSE，不能原样照搬全部示例。
- **文档方面**：发现 [README](<//wsl.localhost/Ubuntu/home/kyle/dev/projects/langgraph-trip-planner/README.md:129>) 仍有 Bearer token、Supabase JWT 的旧说明，实际已经改成本地 Cookie 会话＋CSRF。这类不一致很适合借助文档工作流整理。

## 有明确需求时再用

| Skill | 适用场景 | 当前是否必要 |
|---|---|---|
| [mcp-builder](https://github.com/anthropics/skills/blob/main/skills/mcp-builder/SKILL.md) | 把高德查询、景点信息等封装成可供多个 AI 应用复用的 MCP 工具 | 暂不需要。当前项目直接调用高德 HTTP API，不必为用 Skill 而改架构 |
| [skill-creator](https://github.com/anthropics/skills/blob/main/skills/skill-creator/SKILL.md) | 创建你的项目专用 Skill，固化“在容器运行、检查日志、模拟测试、检查密钥”等流程 | 后续开发多个项目时有价值；当前环境已有同类能力 |
| [theme-factory](https://github.com/anthropics/skills/blob/main/skills/theme-factory/SKILL.md) | 为页面、项目介绍和演示材料统一颜色与字体 | 可选。已有主题不需要重新套模板 |
| [canvas-design](https://github.com/anthropics/skills/blob/main/skills/canvas-design/SKILL.md) | 制作项目封面、宣传海报、静态视觉作品 | 准备作品集时再考虑，不是交互页面开发工具 |

另外，文档制作类也可能用上：

- [pptx](https://github.com/anthropics/skills/tree/main/skills/pptx)：项目面试演示。
- [docx](https://github.com/anthropics/skills/tree/main/skills/docx)：项目说明书、操作手册。
- [pdf](https://github.com/anthropics/skills/tree/main/skills/pdf)：制作或检查 PDF 行程、项目介绍。
- [xlsx](https://github.com/anthropics/skills/tree/main/skills/xlsx)：预算表、测试结果、模型耗时与成本分析。

**你当前环境已有这些方向的同类能力，不必重复安装。** 网站现有 PDF 导出也不会因为安装 Skill 自动升级，仍需单独实现。

## 暂不建议安装的

- [web-artifacts-builder](https://github.com/anthropics/skills/blob/main/skills/web-artifacts-builder/SKILL.md)：主要面向 React＋Tailwind＋shadcn/ui 的独立 HTML 作品，与你现有 Vue＋Ant Design Vue 不匹配。
- [brand-guidelines](https://github.com/anthropics/skills/blob/main/skills/brand-guidelines/SKILL.md)：套用的是 **Anthropic 品牌规范**，不是为你设计个人品牌。
- [claude-api](https://github.com/anthropics/skills/blob/main/skills/claude-api/SKILL.md)：主要针对 Claude/Anthropic SDK；目前保持多模型兼容即可，不需要因此切换模型。
- `algorithmic-art`、`slack-gif-creator`：偏艺术动画、Slack 动图，与旅行规划核心功能关系不大。
- `internal-comms`、`academy-guide`、`discernment-nudge`：偏内部沟通、Claude 学习资源和反思提示，当前优先级低。

**我的建议：保留 `frontend-design`，下一步优先考虑 `webapp-testing` 和 `doc-coauthoring`。** 本次只做了检查，没有安装新 Skill，也没有修改项目。