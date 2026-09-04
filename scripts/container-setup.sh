#!/usr/bin/env bash
set -euo pipefail
cd /workspace/backend
uv sync --locked --group dev
cd /workspace/frontend
npm ci
echo '依赖已就绪。请分别运行 VS Code 的后端、前端任务；迁移需先运行数据库迁移任务。'
