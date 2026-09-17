# Learning Guide · 学习讨论室（LiveKit 迷你产品）

围绕一门学习主题的多人音视频小组讨论室：账户、房间、等候室审批、三种角色权限、群聊、举手与焦点发言、屏幕共享、服务端踢人、房间结束后的 LLM 讨论纪要。

> 当前状态：**r001 已实现完毕，待人工复核与合并**（cp-r001-1..4 全部完成：数据层 / 账户 / 房间与申请 / 前端页面与冒烟，`pytest` 72 项 + `smoke.py` 22 项全绿）。

## 项目地图

| 位置 | 内容 |
| --- | --- |
| `docs/00-project/global-roadmap.md` | 项目级规划：起点 / 终局 / 里程碑（草稿，待批准） |
| `docs/00-requirements/` | 每轮需求单（`rNNN-*.md`）与变更记录 |
| `docs/01-architecture/` | 总体架构、模块图、数据流 |
| `docs/02-modules/` | 每个模块一份：设计 + 实现 |
| `docs/03-decisions/` | ADR：为什么这么设计、改了什么约定 |
| `docs/04-style/` | 风格指南：命名 / 提交约定 + 前端设计系统（色板、排版、动效令牌、图标与可达性） |
| `docs/glossary.md` | 术语表 |
| `AGENTS.md` | 给 AI 的项目规则（禁区、验证命令、提交规范） |

## 当前轮次

`r001`（里程碑 M1：骨架 · 账户 · 房间）—— **实现已完成**（cp-r001-1..4，分支 `req/r001-skeleton`）：数据层与种子、注册登录会话、建房/列表/详情/申请/批准/拒绝/撤回/离开/结束、前端 5 页与真实 HTTP 冒烟。整体 `status: draft`，待人工复核后由人 `merge --no-ff` 并打 `round-r001-done`。

已定：题目 A / 位置 / 数据库 PostgreSQL（本机安装，17.11 已就绪）/ 前端 React + 后端 Python（FastAPI）/ 数据层=手写 SQL + 轻量版本表 / LiveKit=Cloud 为主 + 自建留档 / 纪要=DeepSeek / 加分项=增量项 / 运行环境=conda 环境 `learningguide`（ADR-0006）/ 提交物 = zip + GitHub 仓库 + npm 包（细则 P11 **暂缓**）。

- 总设计（本轮，待批准）：`docs/01-architecture/r001-app-architecture.md`
- 需求单（本轮，待批准）：`docs/00-requirements/r001-skeleton-accounts-rooms.md`
- 房间模块：功能设计 `docs/02-modules/r001-rooms-features.md`；实现设计 `docs/02-modules/r001-rooms.md`
- 账户模块：功能设计 `docs/02-modules/r001-accounts-features.md`；实现设计 `docs/02-modules/r001-accounts.md`
- 决策记录：`docs/03-decisions/`（ADR-0001~0006）
- 归档（非本轮）：`docs/99-archive/`（房间 M2/M3 能力、纪要 M4）

## 怎么跑（本机，r001）

前置：本机 PostgreSQL 17.11 服务在跑、库与角色已建（见 `docs/tutorials/r001-postgres-setup.md`，含 §4b 的建表授权）、
conda 环境 `learningguide` 已就绪、仓库根 `.env` 已填（`DATABASE_URL` / `SESSION_SECRET`）。

```bash
# ① 初始化数据库（可重复执行；--reset 会清空重建）
conda activate learningguide
python backend/scripts/db_init.py --reset --seed
# 期望输出：schema_migrations 2 / users 3 / rooms 3 / room_members 6 / join_requests 3 / invites 0 / chat_messages 12
# 演示账号（口令均为 demo1234）：host@example.com、mod@example.com、part@example.com

# ② 后端（开发）
cd backend && python -m uvicorn app.main:app --reload --port 8000
# 自检：curl http://127.0.0.1:8000/api/auth/me  → {"ok":true,"data":{"user":null}}

# ③ 前端（开发，Vite 代理 /api → 8000，浏览器只看到 localhost:5173 一个源）
cd frontend && npm install && npm run dev
# 打开 http://localhost:5173

# ④ 演示形态（单进程同源）：先把 .env 的 APP_ENV 改成 demo，再构建并只起后端
cd frontend && npm run build
cd backend && python -m uvicorn app.main:app --port 8000
# 打开 http://127.0.0.1:8000

# ⑤ 验证
python backend/scripts/smoke.py --base-url http://127.0.0.1:8000   # 真实 HTTP 全链路，末尾打印 PASS n/n
pytest backend/tests -q                                            # 72 项
```

- 冒烟脚本会写入两个随机邮箱账号与一个房间；跑完可再执行一次 `db_init --reset --seed` 恢复演示数据。
- 依赖版本：后端见 `backend/requirements*.txt`（conda `learningguide` 的 pip freeze）；前端见 `frontend/package.json`（npm 走 npmmirror）。
- 密钥与连接串只放本机 `.env`（不入库）；示例见 `.env.example`，键表见架构页 §5。

