---
title: r001 总体设计（架构页）
description: r001（M1：骨架·账户·房间）的总体架构：分层、目录、配置、数据层机制、会话与鉴权、接口约定、验证矩阵与环境准备。
type: reference
status: draft
owner: 陀梓皓
updated: 2026-09-17
---

<!-- overview -->
本页是 r001 的**总设计**：技术栈落地形态、分层与依赖规则、目录树、跨模块机制（配置/数据层/会话/接口信封/错误码）、验证矩阵与环境准备。
本页**取代 2026-09-16 版**（Next.js + SQLite 初稿，因 ADR-0002 栈变更作废）。
分工（避免双源）：业务规则与业务函数签名 → `docs/02-modules/r001-rooms.md`（实现）与 `r001-rooms-features.md`（功能）；项目方向与里程碑 → `docs/00-project/global-roadmap.md`；纪要（M4）→ `docs/99-archive/r001-ahead-m4-summaries*.md`。
已定前置：P5=PostgreSQL、P6=React 前端 + Python 后端、P9=本机安装 PostgreSQL、P10=A（FastAPI + 手写 SQL + 轻量版本表）、P3′=C（LiveKit Cloud 为主 + 自建脚本留档）、P4=DeepSeek。

## 1. 系统架构与运行拓扑（r001）

```
浏览器 (React SPA, Vite dev :5173)
   │  /api/*  ← Vite dev proxy 转发（开发期同源，见 §6）
   ▼
FastAPI (uvicorn, 127.0.0.1:8000)
   │  api 层：路由 + 依赖注入 + 信封
   │  services 层：业务规则（唯一写库入口，事务边界）
   │  repositories 层：参数化 SQL 绑定
   ▼
psycopg 3 连接池 ──> PostgreSQL（本机服务, :5432, 库 learning_guide）
```

- **单机两进程**（前端 dev server + 后端 API）+ 本机 PostgreSQL 服务；无外部基础设施依赖。
- M2 起加入 **LiveKit Cloud**（服务端签 Token、RoomService 管控），只由 `services/livekit.py` 访问，密钥只在后端；自建 `livekit-server` 脚本作为离线降级路径（ADR-0001/0003）。
- M4 起加入 **DeepSeek**（OpenAI 兼容 HTTP），只由 `app/llm/client.py` 访问。

## 2. 技术栈落地形态（r001）

| 层 | 选型 | 落地形态与理由 |
| --- | --- | --- |
| 后端框架 | FastAPI + uvicorn | 同步 `def` 路由（FastAPI 会在线程池执行）：本作业规模不需要 async，避免 async 驱动/同步池混用的心智负担；OpenAPI 自动生成可作为接口事实源 |
| 数据库驱动 | `psycopg` 3（`psycopg[binary,pool]`） | 同步连接池，最少概念；SQL 全手写（ADR-0005） |
| 迁移 | 自研 `app/db/migrate.py` + `schema_migrations` 版本表 | 前进式：按文件名顺序执行未应用版本；开发期 `--reset` 全量重建 |
| 配置 | `python-dotenv` + `app/config.py` | 全仓**只有 `config.py` 读 `process.env`**；缺关键项启动即失败（不静默兜底） |
| 前端 | React + TypeScript + Vite | SPA；`react-router-dom` 路由；`@tanstack/react-query` 负责取数/缓存/轮询 |
| 前端样式 | 单文件 CSS + CSS Modules | 不引 UI 框架，控制体量与风格争议 |
| 实时（M2） | `@livekit/components-react` + `livekit-client` | 基于 SDK/Components 自实现，不用 LiveKit Meet 默认页 |
| 测试 | pytest + FastAPI `TestClient`（httpx） | 服务层与接口层分开测；schema 与约束用断言验证 |
| 运行/部署 | 开发：Vite dev + uvicorn `--reload`；演示：uvicorn 直接托管 `frontend/dist`（同源） | 演示一条命令起后端即可；Compose 属 M5 加分项 |

新增依赖（**安装前需用户批准**）：后端 `fastapi`、`uvicorn[standard]`、`psycopg[binary,pool]`、`python-dotenv`；开发用 `pytest`、`httpx`。前端 `react`、`react-dom`、`react-router-dom`、`@tanstack/react-query`；开发用 `vite`、`typescript`、`@vitejs/plugin-react`、`@types/react`、`@types/react-dom`。

## 3. 分层与依赖规则（硬约束）

| 层 | 允许做的事 | 禁止 |
| --- | --- | --- |
| `api/`（路由、依赖、信封） | 解析请求 → 取依赖（连接、当前用户）→ 调 service → 用信封返回 | 写 SQL；写业务判断；直接 import `repositories` |
| `services/` | 业务规则、权限判定、事务边界、外部服务编排 | 接触 FastAPI/HTTP 对象（`Request/Response/HTTPException`）；读 `process.env`（除 `llm`/`livekit` 客户端模块） |
| `repositories/` | 参数化 SQL、行映射（→ dict/dataclass） | 业务判断；开事务；多语句编排 |
| `db/` | 连接池、迁移、种子、SQL 文件 | 业务语义 |
| `security/` | 口令哈希、会话签名、ID 生成 | 业务规则 |

依赖方向单向：`api → services → repositories → db`；`security` 可被 `services`/`api` 使用；反向依赖与跨层跳（`api → repositories`）视为违规，审查阶段按 diff 核对。

## 4. 目录树（r001 落地）

```
LearningGuide-LiveKit/
├─ README.md  AGENTS.md  .env.example  .gitignore  .gitattributes
├─ backend/
│  ├─ requirements.txt           # 运行依赖（固定主版本）
│  ├─ requirements-dev.txt       # pytest / httpx
│  ├─ .venv/                     # 项目内虚拟环境（.gitignore）
│  ├─ app/
│  │  ├─ main.py                 # create_app()：装配路由/异常处理/静态托管/生命周期
│  │  ├─ config.py               # 唯一的进程环境读取处
│  │  ├─ api/
│  │  │  ├─ deps.py              # db_conn / current_user / current_user_optional
│  │  │  ├─ envelope.py          # ok()/fail()/ERR 常量
│  │  │  ├─ errors.py            # AppError + 全局异常处理器
│  │  │  └─ routers/{auth.py,rooms.py}
│  │  ├─ services/{auth.py,rooms.py}
│  │  ├─ repositories/{users.py,rooms.py}
│  │  ├─ db/
│  │  │  ├─ pool.py              # 连接池生命周期
│  │  │  ├─ migrate.py           # run_migrations/reset_schema/seed/table_counts
│  │  │  └─ sql/{001_schema.sql,002_seed.sql}
│  │  ├─ security/{password.py,session.py,ids.py}
│  │  ├─ schemas/{common.py,auth.py,rooms.py}
│  │  └─ llm/client.py           # M4；r001 仅占位（不接线）
│  ├─ scripts/{db_init.py,smoke.py}
│  └─ tests/{conftest.py,test_schema.py,test_auth_service.py,test_rooms_service.py,test_rooms_api.py}
├─ frontend/
│  ├─ package.json  tsconfig.json  vite.config.ts  index.html
│  └─ src/
│     ├─ main.tsx  App.tsx  styles/global.css
│     ├─ api/{http.ts,auth.ts,rooms.ts}
│     ├─ hooks/{useSession.ts,useRooms.ts,useRoomDetail.ts}
│     ├─ pages/{RoomsPage.tsx,NewRoomPage.tsx,RoomDetailPage.tsx,LoginPage.tsx,RegisterPage.tsx}
│     └─ components/{NavBar.tsx,RoomCard.tsx,RoomForm.tsx,JoinRequestList.tsx,MemberList.tsx,LoginForm.tsx,RegisterForm.tsx}
└─ docs/…（已建）
```

## 5. 配置与环境变量

`.env`（本地，不入库）字段；`.env.example` 只放占位值：

| 键 | 必填 | 说明 |
| --- | --- | --- |
| `DATABASE_URL` | 是 | `postgresql://lg_app:<密码>@127.0.0.1:5432/learning_guide` |
| `SESSION_SECRET` | 是 | 会话 Cookie 签名密钥（随机 32 字节 hex）；缺失启动失败 |
| `APP_ENV` | 否 | `dev` / `demo`（影响 Cookie 的 `Secure`、静态托管开关） |
| `CORS_ORIGINS` | 否 | 仅在前后端不同源时使用（开发走 Vite 代理时不需要） |
| `LIVEKIT_URL` / `LIVEKIT_API_KEY` / `LIVEKIT_API_SECRET` | M2 起 | Cloud 项目值（或自建 `ws://127.0.0.1:7880`）；**仅后端可读** |
| `LIVEKIT_MODE` | M2 起 | `cloud` / `self`（决定踢人用 `revoke_token_ts` 还是短 TTL，见 ADR-0003） |
| `LLM_BASE_URL` / `LLM_API_KEY` / `LLM_MODEL` | M4 起 | DeepSeek：`https://api.deepseek.com/v1`、`deepseek-chat` |
| `ROOM_CAPACITY` | 否 | 默认 8（题面硬要求，仅允许 ≤8） |

规则：`.env` 永不入库；日志与错误响应不得回显任何 Secret 或 DSN 密码；`require_env()` 缺失即抛 `CONFIG_MISSING` 并让进程退出（不允许"默认密钥"）。

## 6. 会话、鉴权与跨域

- **会话形态**：服务端签发 **HMAC 签名 Cookie**（`lg_session`），payload 仅 `{uid, exp}`（7 天），用标准库 `hmac`/`hashlib`/`base64` 实现，零依赖；Cookie 属性 `HttpOnly`、`SameSite=Lax`、`Path=/`，`APP_ENV=demo` 时加 `Secure`。
- **登出**：清除 Cookie（无服务端吊销——如实写进设计说明的「安全与取舍」）。
- **跨域**（ADR-0002 提出的新问题）——用**同源策略**解决，而不是放开 CORS：
  - 开发：Vite `server.proxy` 把 `/api` 转发到 `http://127.0.0.1:8000` → 浏览器只看到 `localhost:5173` 一个源，Cookie 照常；
  - 演示/交付：uvicorn 挂载 `frontend/dist` 静态文件并对未匹配路径回退 `index.html` → 单源单进程。
  - `CORS_ORIGINS` 仅在确有跨源需要时才配置（并提供 `allow_credentials=True` 的说明）。
- **鉴权判定**：`require_user()` 未登录抛 `UNAUTHORIZED(401)`；业务级权限（房主/协管/成员）一律在 `services/rooms.py` 判定，前端按钮可见性只是提示，不作为安全边界。

## 7. 数据层机制

- **一次建全**：`001_schema.sql` 建全部业务表（含 `session_migrations` 版本表；表定义以模块页为单一事实源：房间相关见 `r001-rooms.md` §3，纪要表见归档页）。
- **迁移执行**：`run_migrations(conn)` 读取 `sql/*.sql`（文件名序），已在 `schema_migrations` 的版本跳过，其余在**单事务**内逐语句执行（PostgreSQL 支持事务性 DDL）。
- **开发重建**：`reset_schema(conn)` 仅在显式 `--reset` 时 DROP；`seed(conn)` 用 `ON CONFLICT DO NOTHING` 保证幂等。
- **连接池**：进程级 `ConnectionPool(min_size=1, max_size=8)`；每请求借一条连接（`autocommit=False`），只读函数不开显式事务，写函数在 service 内 `with conn.transaction():`。
- **并发与一致性**（约定，细节见模块页）：房间级互斥 `SELECT ... FROM rooms WHERE id=%s FOR UPDATE`；重复申请靠部分唯一索引兜底并映射为 409；幂等 upsert 用于纪要（M4）。
- **禁止**：字符串拼 SQL、跨层直接查表、在路由里开事务。

## 8. 接口约定

- 前缀 `/api`；JSON 请求与响应；所有响应统一信封：

```json
{ "ok": true,  "data": { ... } }
{ "ok": false, "error": { "code": "ROOM_FULL", "message": "房间已满（上限 8 人）" } }
```

- 状态码语义：201 创建成功；200 成功；400 `VALIDATION`；401 `UNAUTHORIZED`/`INVALID_CREDENTIALS`；403 `FORBIDDEN`；404 `NOT_FOUND`；409 冲突族；500 `CONFIG_MISSING`/`INTERNAL`；502（M4 `SUMMARY_FAILED`）。
- 分页：`?limit=&offset=`，响应含 `total`；列表默认 20 条、上限 100。
- 幂等：GET 幂等；写操作以"唯一索引 + 锁"保证重复请求得到 409/200 的确定结果，不做前端去重依赖。
- 错误码总表（r001）：`VALIDATION`、`UNAUTHORIZED`、`INVALID_CREDENTIALS`、`FORBIDDEN`、`NOT_FOUND`、`EMAIL_TAKEN`、`ALREADY_MEMBER`、`ALREADY_PENDING`、`CONFLICT`、`NOT_MEMBER`、`HOST_CANNOT_LEAVE`、`ROOM_ENDED`、`ROOM_FULL`、`CONFIG_MISSING`、`INTERNAL`（M2 增 `INVITE_INVALID`；M4 增 `SUMMARY_FAILED`、`LLM_NOT_CONFIGURED`）。
- **接口事实源**：路由表写在各模块页（房间见 `r001-rooms.md` §5）；FastAPI 自动生成的 OpenAPI（`/openapi.json`、`/docs`）作为实现期对照，不手抄字段。

## 9. 跨模块骨架的函数级实现路径

（业务函数在模块页；本节只列骨架层，签名即契约）

### 9.1 `app/config.py`

| 函数 | 签名 | 职责 / 返回 |
| --- | --- | --- |
| `require_env` | `(name: str, default: str \| None = None) -> str` | 读单个环境变量；无默认值且缺失 → `AppError('CONFIG_MISSING', status=500)` |
| `load_settings` | `() -> Settings` | 读 `.env`（`python-dotenv`）并组装 `Settings`；进程内缓存 |
| `Settings`（dataclass） | `database_url, session_secret, app_env, cors_origins, room_capacity, livekit_url, livekit_api_key, livekit_api_secret, livekit_mode, llm_base_url, llm_api_key, llm_model` | 启动期唯一配置对象；`livekit_*`/`llm_*` 在 r001 允许为空 |
| `validate_startup` | `(s: Settings) -> None` | 校验必填与取值（`APP_ENV ∈ {dev,demo}`、`room_capacity ≤ 8`）；失败即抛 `CONFIG_MISSING` |

### 9.2 `app/main.py`

| 函数 | 签名 | 职责 / 返回 |
| --- | --- | --- |
| `create_app` | `() -> FastAPI` | 装配：`lifespan`（连接池初始化/关闭 + `validate_startup`）、`register_error_handlers`、`register_routers`、可选 `mount_spa` |
| `register_routers` | `(app: FastAPI) -> None` | `include_router(auth_router, prefix='/api')`、`include_router(rooms_router, prefix='/api')` |
| `mount_spa` | `(app: FastAPI, dist_dir: str) -> None` | `APP_ENV=demo` 时挂载 `frontend/dist` 静态资源 + SPA fallback 到 `index.html` |
| `lifespan`（内部） | `async (app) -> AsyncIterator[None]` | 启动：`validate_startup` + `init_pool`；关闭：`close_pool` |

### 9.3 `app/db/pool.py` · `app/db/migrate.py`

| 函数 | 签名 | 职责 / 返回 |
| --- | --- | --- |
| `init_pool` | `(dsn: str, min_size: int = 1, max_size: int = 8) -> None` | 建 `psycopg_pool.ConnectionPool`，进程内单例 |
| `get_conn` | `() -> Iterator[Connection]` | 上下文管理器：借/还连接（异常回滚） |
| `close_pool` | `() -> None` | 关池 |
| `run_migrations` | `(conn: Connection) -> list[str]` | 依次执行 `sql/*.sql`，跳过已记版本；返回本次应用的版本名 |
| `reset_schema` | `(conn: Connection) -> None` | DROP 全部业务表（仅 `--reset`） |
| `seed` | `(conn: Connection) -> dict[str, int]` | 执行 `002_seed.sql`（幂等），返回各表行数 |
| `table_counts` | `(conn: Connection) -> dict[str, int]` | 各表 `count(*)`（`db_init` 的证据输出） |

### 9.4 `app/security/*`

| 函数 | 签名 | 职责 / 返回 |
| --- | --- | --- |
| `hash_password` | `(plain: str) -> str` | `hashlib.scrypt`，输出 `scrypt$N$r$p$salt$hash`（标准库） |
| `verify_password` | `(plain: str, stored: str) -> bool` | 解析并 `hmac.compare_digest` 比对；格式非法返回 False |
| `sign_session` | `(uid: str, exp: int, secret: str) -> str` | `base64url(json).base64url(hmac_sha256)` |
| `read_session` | `(token: str, secret: str) -> str \| None` | 验签 + 过期校验 → `uid` 或 None |
| `set_session_cookie` | `(resp: Response, uid: str, secret: str, secure: bool) -> None` | 写 `lg_session`（HttpOnly/SameSite=Lax/Path=/，7 天） |
| `clear_session_cookie` | `(resp: Response) -> None` | 清 Cookie |
| `current_user` | `(request: Request, conn: Connection) -> UserVO \| None` | 读 Cookie → 验签 → 查库 |
| `new_id` | `(prefix: str) -> str`  / `new_code` | `usr_`/`room_`… ；6 位房间码（剔除易混字符） |

### 9.5 `app/api/*`

| 函数 | 签名 | 职责 / 返回 |
| --- | --- | --- |
| `ok` | `(data: Any, status: int = 200) -> JSONResponse` | `{ok:true,data}` |
| `fail` | `(code: str, message: str, status: int = 400) -> JSONResponse` | `{ok:false,error}` |
| `AppError` | `class(code: str, message: str, status: int)` | 业务错误载体 |
| `register_error_handlers` | `(app: FastAPI) -> None` | `AppError` → 信封；`RequestValidationError` → 400 `VALIDATION`；其他 → 500 `INTERNAL`（不回显内部细节） |
| `db_conn`（依赖） | `() -> Iterator[Connection]` | `with get_conn() as conn: yield conn` |
| `current_user_optional`（依赖） | `(request: Request, conn = Depends(db_conn)) -> UserVO \| None` | 可选登录态 |
| `current_user`（依赖） | `(...) -> UserVO` | 未登录抛 `UNAUTHORIZED` |
| 路由函数（r001 共 13 个） | `register` / `login` / `logout` / `me`；`list_rooms` / `create_room` / `get_room` / `create_join_request` / `list_join_requests` / `approve_request` / `reject_request` / `leave_room` / `end_room` | 每个 5~15 行：取依赖 → 调 service → 信封 |

### 9.6 `scripts/db_init.py` · `scripts/smoke.py`

| 入口 | 行为 |
| --- | --- |
| `python scripts/db_init.py --reset --seed` | 迁移 + 种子 + 打印 `table_counts()`（真输出即验收证据） |
| `python scripts/smoke.py --base-url http://127.0.0.1:8000` | 走真实 HTTP 的 M1 链路：注册两账号 → 登录 → A 建房 → 列表含新房间 → B 申请 → A 批准 → 详情成员=2 → B 离开 → A 结束房间 → 校验 `ended`/成员 `inactive(room_ended)`/申请 `cancelled`；每步打印状态码与关键字段，失败非 0 退出 |

### 9.7 `frontend/src/*`（骨架层）

| 文件 | 导出 | 职责 |
| --- | --- | --- |
| `api/http.ts` | `request<T>(path, init?)`、`class ApiError{code,message,status}` | 拼 baseURL（`/api`）、`credentials:'include'`、解析信封、`ok=false` 抛 `ApiError` |
| `api/auth.ts` | `register(body)`、`login(body)`、`logout()`、`me()` | 认证接口封装 |
| `hooks/useSession.ts` | `useSession()` → `{user, isLoading, login, logout, register}` | 会话状态（`react-query` 缓存 `['me']`） |
| `vite.config.ts` | `server.proxy['/api'] → http://127.0.0.1:8000` | 开发期同源（解决 Cookie/跨域） |
| `App.tsx` | `<Routes>` 5 条路由（`/`、`/login`、`/register`、`/rooms/new`、`/rooms/:id`） | 路由与布局 |

## 10. 请求生命周期与事务边界

```
HTTP 请求 → 路由（解析 + 依赖注入：连接、当前用户）
        → service（校验规则 → 必要时 with conn.transaction(): 锁行/写库）
        → repository（参数化 SQL）
        → service 组装 VO → 路由用 ok()/fail() 返回
```

- 事务：写操作在 service 内单事务完成；只读不开事务；外部调用（LiveKit/M4 的 LLM）在**事务提交后**执行，失败不回滚已提交的业务状态。
- 异常：`AppError` 直接映射；未预期异常记日志（含 request id）并返回 500 `INTERNAL`，不回显栈与 DSN。

## 11. 验证矩阵（r001 `<check>`）

| 层 | 命令 | 判据 |
| --- | --- | --- |
| 依赖 | `pip install -r backend/requirements.txt -r backend/requirements-dev.txt` | 安装成功（需用户批准） |
| 数据 | `python backend/scripts/db_init.py --reset --seed` | 打印各表行数（`users≥3`、`rooms≥3`） |
| schema 断言 | `pytest backend/tests/test_schema.py -q` | 表/列/约束存在；部分唯一索引真挡住重复 pending；CHECK 真挡住非法状态 |
| 服务层 | `pytest backend/tests/test_rooms_service.py backend/tests/test_auth_service.py -q` | 规则用例全绿（容量、结束连带动作、Host 不可离开等） |
| 接口层 | `pytest backend/tests/test_rooms_api.py -q` | 信封形状、状态码与错误码矩阵 |
| 冒烟 | `python backend/scripts/smoke.py` | 每步状态码符合预期，末尾 `PASS n/n` |
| 前端类型 | `cd frontend && npx tsc --noEmit` | 无错误 |
| 前端构建 | `cd frontend && npm run build` | 产出 `dist/` |
| 手工 | 双浏览器 | 按房间功能页 §6 的 9 步脚本走通 |
| 安全 | `git grep -nE "API_SECRET|API_KEY" -- backend/app frontend/src` | 除 `config.py` 的变量名外无命中；`.env` 未入库 |
| 文档 | 对照本页 §4/§9 与实际文件 | 目录与函数名一致；验收清单逐条勾选 |

## 12. 环境准备（P9=A：本机安装 PostgreSQL）

| 步骤 | 命令 / 动作 | 负责人 |
| --- | --- | --- |
| 装 PostgreSQL | `winget install PostgreSQL.PostgreSQL.17`（或图形安装包 / 官方免安装 zip） | **需用户批准**（下载约 300MB） |
| 建库建角色 | `CREATE ROLE lg_app LOGIN PASSWORD '…';` `CREATE DATABASE learning_guide OWNER lg_app;` | 装好后由 agent 执行（需授权） |
| 后端依赖 | `python -m venv backend/.venv` + `pip install -r …` | 需用户批准 |
| 前端依赖 | `cd frontend && npm install` | 需用户批准 |
| `.env` | 复制 `.env.example` → `.env` 并填 `DATABASE_URL`、`SESSION_SECRET`（随机生成） | agent 生成占位、用户确认 |
| LiveKit Cloud | 注册 → 建项目 → 抄 `LIVEKIT_URL/API_KEY/API_SECRET` 进 `.env` | **用户操作**（M2 前完成即可） |
| LLM Key | DeepSeek Key 进 `.env` | 用户操作（M4 前完成即可） |

## 13. 失败与边界（架构级）

| 情况 | 期望行为 |
| --- | --- |
| `.env` 缺必填项 | 启动失败并打印缺哪一项（`CONFIG_MISSING`），不允许默认值兜底 |
| 数据库未启动/DSN 错误 | 启动探测失败即退出并给可读提示；运行期 `OperationalError` → 500 `INTERNAL`（日志留详情） |
| 迁移未跑 | `GET /api/rooms` 返回 500 并在日志提示"请先执行 db_init"（不做自动迁移，避免误建） |
| 前端未构建（`APP_ENV=demo`） | 静态目录缺失时给出明确日志，API 仍可用 |
| 非受信来源跨源请求 | 默认不放开 CORS；需要时用 `CORS_ORIGINS` 显式列白名单（并说明 credentials 语义） |
| Cookie 缺失/过期 | 401 `UNAUTHORIZED`（业务路由）或 `{user:null}`（`/api/auth/me`） |
| 并发写同一房间 | 行锁串行化；冲突语义见模块页 §8（409 而非 500） |
| 密钥泄漏面 | 日志、错误响应、前端产物三处均不含 Secret；验证矩阵有对应检索命令 |

## 14. 未决与分支

| 编号 | 事项 | 状态 | 影响 |
| --- | --- | --- | --- |
| P11 | 提交物细则（npm 发布对象 / 仓库公开性 / zip 主次） | 待拍板 | 只影响 §4 目录（是否新增包目录）与 README「交付」章节，不阻塞 r001 实现 |
| — | 会话方案最终形态（Cookie 签名） | 本文已定（§6），如改为 `jose`/Bearer 需改 §6 与前端 `http.ts` | 影响安全叙事与代码量 |
| — | PostgreSQL 安装方式（winget / 图形 / 免安装 zip） | 待用户选 | 影响 §12 步骤 1 的命令 |

## What's next

1. 用户复核本页（重点：§2 选型落地、§3 分层规则、§6 会话与跨源、§9 骨架函数签名、§11 验证矩阵、§12 环境准备）。
2. 通过后：重写 `docs/00-requirements/r001-skeleton-accounts-rooms.md`（r001 需求单，含验收清单）→ 与之配套的模块页（房间两份已就绪）一并转 `approved`。
3. 再开实现：分支 `req/r001-skeleton`，按 `cp-r001-1`（骨架与数据层）→ `cp-r001-2`（账户）→ `cp-r001-3`（房间与申请）→ `cp-r001-4`（前端页面与冒烟）推进；每 cp 一提交一 tag。
