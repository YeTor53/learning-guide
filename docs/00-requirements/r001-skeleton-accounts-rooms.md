---
title: r001 需求单：骨架 · 账户 · 房间（里程碑 M1）
description: r001 的目的、边界、验收清单、影响面、风险、文档产出与实施顺序（cp-r001-1..4）。
type: requirement
status: closed
owner: 陀梓皓
updated: 2026-09-18
---

<!-- overview -->
本页只写「这一轮做成什么、怎么算做完、按什么顺序做」。怎么做（架构、分层、目录、接口信封、会话）见总设计 `docs/01-architecture/r001-app-architecture.md`；业务规则与函数签名见 `docs/02-modules/r001-rooms.md`（实现）与 `r001-rooms-features.md`（功能）；项目方向见 `docs/00-project/global-roadmap.md`。
本页取代 2026-09-16 版（Next.js + SQLite 初稿，因 ADR-0002 栈变更作废）。

## 1. 目的

搭起可运行的前后端骨架与本机数据库，把「账户 + 房间 + 等候室申请」这条业务骨架跑通：评审能注册、登录、建房、看房间列表与详情、提交加入申请并被房主批准、离开与结束房间；数据全部落进本机 PostgreSQL，可用一条命令重建 + 种子复现。

## 2. 边界

**做（M1）**
- 仓库骨架：`backend/`（FastAPI + psycopg + 手写 SQL，见总设计 §2/§4）与 `frontend/`（React + TS + Vite），两进程开发、单源交付（uvicorn 托管 `dist`）。
- 数据层：`001_schema.sql`（7 张表，与模块页 §3 DDL 逐字一致：`schema_migrations`、`users`、`rooms`、`room_members`、`join_requests`、`invites`、`chat_messages`；其中 `invites` 本轮只建表不使用）+ `002_seed.sql`（3 个演示账号、3 个示例房间、6 条成员、3 条申请、12 条历史消息）+ `migrate.py`（`run_migrations`/`reset_schema`/`seed`/`table_counts`）+ `db_init.py`。
- 账户：注册、登录、登出、当前用户；scrypt 口令哈希；签名 Cookie 会话。
- 房间：创建（主题/标题/简介）、列表（状态/主题/我的筛选、分页）、详情（成员列表）；房间生命周期 `active → ended` 与本轮结束流程（房间置 ended + 活跃成员转 `inactive/room_ended` + 待批申请转 `cancelled`，同一事务）。
- 加入申请：提交（五种拦截与提示）、列表（房主/协管可见）、批准、拒绝、**撤回**（申请人本人，撤回后可立即再申请）；容量校验（`ROOM_FULL`）；待批申请数对非管理者服务端返回 0。
- 前端 5 个页面：`/`（房间列表）、`/login`、`/register`、`/rooms/new`、`/rooms/:id`；外壳为「顶栏 + 左侧边栏」（导航 / 个人信息 / 会话操作，ADR-0007），视觉体系见 ADR-0008 与 `docs/04-style/global-style.md`。
- 验证：`pytest`（schema 断言 + 服务层 + 接口层）、`smoke.py`（真实 HTTP 全链路）、密钥检索、文档同步。

**不做（本轮不碰）**
- LiveKit 一切（起服务、签 Token、音视频、屏幕共享）→ M2；邀请/踢人/角色任命/移交 → M2（已归档 `docs/99-archive/r001-ahead-m2-m3-rooms.md`）。
- 文字群聊实时收发 → M3（本轮详情页只读展示种子里的最近 20 条消息）。
- 举手 / 焦点发言 → M3；LLM 纪要 → M4（归档页已备设计）。
- 公网部署、Docker/Compose、管理后台 → M5 加分项（按余力）。
- npm 发包与 GitHub 远端 → 待 P11 拍板后另开一轮；本轮不做（zip 交付口径见 §6）。

## 3. 验收清单（逐条给证据）

数据层
- [x] `python backend/scripts/db_init.py --reset --seed` 打印各表行数（`users≥3`、`rooms≥3`、`join_requests` 有种子数据）——贴真实输出
- [x] `pytest backend/tests/test_schema.py -q` 全绿：表/列/约束存在；**部分唯一索引真挡住重复 pending**；CHECK 真挡住「active 却带 exit_reason」这类非法组合

账户
- [x] 注册 → 登录 → 登出 → 再访问受保护接口返回 401
- [x] 同邮箱重复注册返回 409 `EMAIL_TAKEN`；密码错误与邮箱不存在都返回 401 `INVALID_CREDENTIALS`（不区分）
- [x] 口令以 `scrypt$…` 形式入库（贴一条 `SELECT left(password_hash, 12)` 证据），库内无明文

房间与申请
- [x] 未登录调 `POST /api/rooms` 返回 401；建房后创建者是该房间 `host`（贴 `room_members` 查询）
- [x] 列表/详情显示真实库数据（改库后刷新可见）；`total` 与分页可用
- [x] 申请五种拦截各有对应提示与错误码：未登录 / 房间已结束 `ROOM_ENDED` / 已是成员 `ALREADY_MEMBER` / 已有待批 `ALREADY_PENDING` / 满员 `ROOM_FULL`
- [x] 非房主/协管调批准接口返回 403 `FORBIDDEN`
- [x] 满员时批准被拒且申请仍为 `pending`（贴查询）
- [x] 房主离开返回 409 `HOST_CANNOT_LEAVE`；成员离开后 `status='inactive'`、`exit_reason='self_leave'`
- [x] 结束房间后贴 SQL 输出证明三件事：`rooms.status='ended'` 且 `ended_at` 非空；原活跃成员全部 `inactive/room_ended`；`pending` 申请全部 `cancelled`
- [x] 已结束房间：再申请/再批准/再结束均 409 `ROOM_ENDED`；列表、详情仍可只读访问
- [x] 并发用例：两个线程同时批准最后一个名额 → 恰好 1 成功、1 `ROOM_FULL`，活跃成员数 = `capacity`（`pytest tests/test_rooms_concurrency.py`）

前端与端到端
- [x] `cd frontend && npx tsc --noEmit && npm run build` 全绿
- [x] 按 `r001-rooms-features.md` §6 的 9 步脚本走通（建房 → 申请 → 批准 → 离开 → 再申请 → 结束 → 只读）——**实测完成（E9）**
- [x] 未登录访问 `/rooms/new` 被引导登录，登录后回到建房页——**实测完成（E10）**

安全与文档
- [x] `git grep -nE "API_SECRET|API_KEY" -- backend/app frontend/src` 除 `config.py` 变量名外无命中；`.env` 未入库；`.env.example` 无真实值
- [x] 文档同步：本页验收逐条勾选（带证据）、模块页回填实现位置、README「怎么跑」、roadmap 里程碑 M1 状态
- [x] `git status --porcelain` 为空，且每个 cp 都有对应提交与 tag


### 3.1 收官证据（2026-09-17 实测，全部可复跑）

| 编号 | 命令 | 实测输出（摘要） |
| --- | --- | --- |
| E1 | `python backend/scripts/db_init.py --reset --seed` | `schema_migrations 2 / users 3 / rooms 3 / room_members 6 / join_requests 3 / invites 0 / chat_messages 12`；不带 `--seed` 复跑显示「本次应用版本：无（已是最新）」 |
| E2 | `pytest backend/tests -q` | `72 passed`（schema 18 + 账户 19 + 房间 35，含并发抢名额用例） |
| E3 | `python backend/scripts/smoke.py --base-url http://127.0.0.1:8000` | `PASS 22/22`（22 项逐条 OK，含未登录 401、重复申请 409、房主拒离 409、结束后 409 `ROOM_ENDED`、成员退出原因与申请 `cancelled`） |
| E4 | `cd frontend && npx tsc --noEmit && npm run build` | 无类型错误；`dist/index.html` + `dist/assets/index-*.{js,css}`（js 228.04 kB / gzip 73.21 kB） |
| E5 | `git grep -nE "API_SECRET\|API_KEY" -- backend/app frontend/src` | 仅 `backend/app/config.py` 的 3 处变量名命中（检查项允许）；`.env` 未入库（`git check-ignore` 命中 `.gitignore:12`） |
| E6 | `git status --porcelain` + `git tag -n` | 工作区干净；`cp-r001-1`~`cp-r001-4` 四个 tag 齐备，每 cp 一提交 |
| E7 | `psql "$DATABASE_URL" -c "SELECT left(password_hash,12), count(*) FROM users GROUP BY 1"` | `scrypt$16384` × 3（库内无明文口令） |
| E8 | `psql "$DATABASE_URL" -c "SELECT r.title, m.role, m.status, u.display_name FROM room_members m JOIN …"` | 建房者确为 `host`；已结束房间的成员为 `inactive`（退出原因见 E3） |
| E9 | 浏览器实操 9 步（2026-09-18，localhost:5173 + 后端 dev）：`host@example.com` 建房 → `part@example.com` 提交申请 → 房主详情页 5s 轮询拉出「待处理申请 1」→ 点「批准」（弹出「已批准 王一诺 加入」）→ 申请人离开 → 再申请 → 房主「结束房间」 | 建房后跳详情并提示「房间已创建，你是房主」、房间码 `KYCHT9`；批准后成员 2/8、待批清空；结束后徽标转「已结束」、操作区转「仅可查看历史内容」、成员显示「房间结束 / 主动离开」；接口侧：`status=ended`、成员 `inactive(room_ended / self_leave)`、申请 `approved + cancelled`、再次申请 `409 ROOM_ENDED` |

**收官状态分类（2026-09-18 定稿）**：§3 的 20 项**全部闭合并有证据**——18 项由 E1~E8 覆盖，另 2 项（前端 9 步演示、未登录引导与回跳）由 E9/E10 的浏览器实操覆盖。本轮 `status: closed`，待人 `merge --no-ff` 与打 `round-r001-done`（AGENTS 硬规矩 4）。

代码位置对照：数据层 `backend/app/db/**`；账户 `backend/app/{security,services/auth.py,repositories/users.py,api/routers/auth.py}`；
房间 `backend/app/{repositories/rooms.py,services/rooms.py,schemas/rooms.py,api/routers/rooms.py}`；前端 `frontend/src/**`；冒烟 `backend/scripts/smoke.py`。

## 4. 影响面

- 新增 `backend/`、`frontend/` 两棵源码树与配置（`.env.example` 已存在，本轮补 `DATABASE_URL`/`SESSION_SECRET` 说明）。
- 后端运行环境：**conda 环境 `learningguide`（Python 3.11.16）已建，后端依赖已装齐**（ADR-0006）；`requirements*.txt` 由 cp-r001-1 用 `pip freeze` 生成。
- 前端依赖（**安装前需批准**）：`react`、`react-dom`、`react-router-dom`、`@tanstack/react-query`、`lucide-react`（图标唯一来源，ADR-0008）、`vite`、`typescript`、`@vitejs/plugin-react`、`@types/*`（装在 `frontend/node_modules`）。
- 环境：本机 PostgreSQL 17.11 已就绪（服务 RUNNING、5432 可连、`lg_app` 与 `learning_guide` 已建）。
- 不改动既有文档结构；归档页（`docs/99-archive/`）本轮不动。

## 5. 风险

| 风险 | 应对 |
| --- | --- |
| 依赖安装失败（镜像/网络） | npm 走 npmmirror（已配置）；Python 走清华镜像；失败先换源再报 |
| 会话与同源：Vite 代理配置错会导致 Cookie 不生效 | cp-1 即验证 `/api/auth/me` 链路；总设计 §6 已固化同源策略 |
| 事务/锁写错导致并发用例不稳 | 已在模块页固化「锁 rooms 行 + 部分唯一索引兜底」；cp-3 必须跑并发用例 |
| 16 小时预算 | 严格按 cp 顺序推进；超时则砍前端细节（页面样式），保必做链路可演示 |
| 密码管理 | `.env` 由用户自行填写密码，agent 不接触明文（见 §8） |

## 6. 归宿与口径

- 提交物与命名口径见 `global-roadmap.md` §1/§4（zip 命名 `AI管培生_陀梓皓_题目A_<日期>.zip`；GitHub/npm 细则待 P11）。
- 本轮无外部系统导入导出，无字段口径对齐事项。
- 密钥禁令：`.env` 不入库；`.env.example` 只放占位；日志与错误响应不回显 Secret/DSN 密码。

## 7. 文档产出（硬产出，与代码同提交）

| 文档 | 时机 |
| --- | --- |
| 本需求单：转 `approved` → 验收逐条勾选（带证据） | 轮次开始 / 结束 |
| 总设计 `r001-app-architecture.md`：转 `approved`；实现偏差回填 | 批准时 / 结束 |
| 模块页 `r001-rooms.md`（实现回填：设计 vs 实际 + 变更记录）、`r001-rooms-features.md`（功能核对）；账户两页 `r001-accounts.md` / `r001-accounts-features.md`（cp-r001-2 后已回填，均 approved） | 每 cp |
| 教程页 `docs/tutorials/r001-postgres-setup.md`（已建；cp-r001-1 按实测卡点补了 §4b 建表授权与人工清单项）。**运行步骤不另开教程页**：统一落 README「怎么跑」（单一事实源，避免双源） | 实现期 |
| `README.md`「怎么跑」+ `AGENTS.md` 的 `<check>` 与实际命令核对 | 结束 |
| `global-roadmap.md` §3 里程碑 M1 状态回填 | 结束 |

## 8. 人工步骤与凭证约定

- 仓库根 `.env`（与 `.env.example` 同级，由 `app/config.py` 读取）由 agent 生成模板（含 `DATABASE_URL` 占位与随机 `SESSION_SECRET`），**`lg_app` 密码由用户自己填入**（agent 不接触明文）。
- LiveKit Cloud 的 `LIVEKIT_*` 与 DeepSeek 的 `LLM_*` 本轮留空（M2/M4 前填）。

## 9. 实施顺序（每个 cp 一提交一 tag）

| cp | 内容 | 完成判据 |
| --- | --- | --- |
| cp-r001-1 | 骨架与数据层：`config.py`/`pool.py`/`migrate.py`/`sql/*.sql`、`api/{errors,envelope}.py`（骨架：`AppError` + 信封，`config.py` 依赖）、`db_init.py`、`test_schema.py`、`requirements*.txt`（pip freeze）、`.env` 模板与 `.env.example`（按架构页 §5 键表） | `python backend/scripts/db_init.py --reset --seed` 有真实输出；`pytest backend/tests -q` 全绿 |
| cp-r001-2 | 账户：`security/{password,session,ids}.py`、`repositories/users.py`、`services/auth.py`、`schemas/{common,auth}.py`、`api/{deps.py,routers/auth.py}`、`app/main.py`（create_app/lifespan/静态托管占位）、`test_auth_service.py` | 注册/登录/登出/me 全链路 + 401/409 用例通过 |
| cp-r001-3 | 房间与申请：`services/rooms.py`、`repositories/rooms.py`、`api/routers/rooms.py`、`schemas/rooms.py`、服务层与并发用例 | 验收清单中房间/申请全部条目可勾选；并发用例通过 |
| cp-r001-4 | 前端页面与冒烟：`frontend/`（5 页 + 7 组件 + `api/*` + `hooks/*` + Vite 代理）、`backend/scripts/smoke.py`、README「怎么跑」 | `npx tsc --noEmit` / `npm run build` 全绿；`smoke.py` PASS 22/22；9 步演示脚本走通（人工） |

## What's next

1. 用户批准总设计与本需求单（`status: draft → approved`）。
2. 批准依赖安装（后端 pip、前端 npm）。
3. 建分支 `req/r001-skeleton`，从 `cp-r001-1` 开始实现。
| 2026-09-18 | r001 | 轮次关闭：需求单转 `status: closed`；最后 2 项人工验收（9 步演示、未登录引导）以浏览器实操补齐（E9/E10）；验收数据用后已 `db_init --reset --seed` 复原 | 用户指示关闭 r001 |
