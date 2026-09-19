---
redirect: r003-01
status: confirmed-C
raised_at: ed9abd2（2026-09-19）
decided_by: 用户 2026-09-19「写个一键启动环境的脚本」（直接祈使句 = 该项授权并追加到当前任务）
---
# redirect r003-01：一键启动环境的脚本

- **用户原话**：「写个一键启动环境的脚本」（2026-09-19）
- **影响**：新增仓库根 `dev.bat`（启动/停止/自检三合一）；README「怎么跑」加一行入口；**不改端口、不改依赖、不读不回显任何密钥**；已产出的 cp-r003-1/2 不受影响（还没改什么别的）
- **处置**：C 追加到当前任务（r003 照旧推进）；脚本与它的文档同一次提交。设计口径见本单 §4 与 `dev.bat` 头部注释。
- **待批**：已按用户指令落地；如需调整（比如开机自启、改端口、加 PowerShell 版）另行出单。

## 4. 落地口径（已实现）

| 项 | 取值 |
| --- | --- |
| 用法 | `dev.bat`（启动）· `dev.bat check`（自检）· `dev.bat stop`（按端口停进程） |
| 端口 | 后端 `8000`（uvicorn --reload，cwd=backend）· 前端 `5173`（Vite，cwd=frontend，`/api` 代理到 8000） |
| 解释器 | 优先环境变量 `LG_PY` → conda 环境 `learningguide`（`C:\ProgramData\miniconda3\envs\learningguide\python.exe`）→ PATH 里的 `python` |
| 自检项 | Python / npm / 仓库根 `.env` / PostgreSQL 服务 `postgresql-x64-17` / 两个端口占用 |
| 就绪探针 | 后端 `http://127.0.0.1:8000/api/auth/me`；**前端 `http://localhost:5173/`**（Vite 默认只监听 IPv6 回环 `::1`，用 `127.0.0.1` 探不到——实测 000 vs 200） |
| 编码 | `GBK` + CRLF（中文 Windows 控制台默认代码页 936；最初用 UTF-8 写会被读成乱码并破坏批处理解析——实测报错） |
