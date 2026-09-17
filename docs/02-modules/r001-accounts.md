---
title: r001 账户功能详细设计（模块页）
description: 账户模块的接口契约、逐文件函数签名与职责、会话与口令机制、并发边界、验证矩阵与实现偏差。
type: reference
status: approved
owner: 陀梓皓
updated: 2026-09-17
---

<!-- overview -->
本页是**账户模块实现层**的单一事实源：接口、数据结构、函数签名、并发与边界、验证矩阵。
**行为与文案**（做什么、看到什么、拦截顺序）见 `docs/02-modules/r001-accounts-features.md`，本页不复制。
结果信封与错误码总表见 `docs/01-architecture/r001-app-architecture.md` §8；分层规则见同页 §3。
> 本页在 cp-r001-2 之后**按已交付代码回填**（文档 = 代码真相）：§3 的签名与 §7 的用例清单都以仓库实际文件为准。

## 1. 范围与里程碑归属

| 项 | 里程碑 | 本页是否给到实现级 |
| --- | --- | --- |
| 注册 / 登录 / 登出 / 当前用户 | M1 | ✅ |
| 会话 Cookie 的签发与校验 | M1 | ✅ |
| 邮箱验证、找回密码、服务端吊销会话 | 不做（M5 候选） | 明确不做 |

## 2. 数据模型

`users` 表定义以房间模块页 §3（DDL 单一事实源）为准，本模块只用到以下字段与约束：

| 字段 | 用途 | 约束 |
| --- | --- | --- |
| `id` | 主键 | `TEXT`，应用生成 `usr_<16 hex>` |
| `email` | 登录标识 | 非空；唯一索引 `ux_users_email_lower`（大小写不敏感） |
| `display_name` | 展示名 | 1~32 字 |
| `password_hash` | 口令材料 | 非空；`scrypt$N$r$p$salt$hash`，**永不出响应** |
| `created_at` | 注册时间 | `TIMESTAMPTZ` |

## 3. 接口契约（r001 四条）

| 方法与路径 | 请求体 | 成功响应 | 失败 |
| --- | --- | --- | --- |
| `POST /api/auth/register` | `{email, display_name, password}` | `201`，`data.user` = UserVO，并下发会话 Cookie | `400 VALIDATION`；`409 EMAIL_TAKEN` |
| `POST /api/auth/login` | `{email, password}` | `200`，`data.user` = UserVO，并下发会话 Cookie | `400 VALIDATION`；`401 INVALID_CREDENTIALS` |
| `POST /api/auth/logout` | — | `200`，`data.user = null`，清 Cookie | —（幂等，未登录调用也返回 200） |
| `GET /api/auth/me` | — | `200`，`data.user` = UserVO 或 `null` | —（未登录不报 401，前端首屏用它判断状态） |

- `UserVO` = `{id, email, display_name, created_at}`；任何响应都不得包含 `password_hash`（有用例断言）。
- 会话 Cookie：名 `lg_session`，值 = `base64url(JSON{uid, exp}) + "." + base64url(HMAC-SHA256)`，属性 `HttpOnly`、`SameSite=Lax`、`Path=/`、`Max-Age=7 天`，`APP_ENV=demo` 时加 `Secure`。
- 规则：登录与注册共用「邮箱先去空白再小写」的规范化；口令错误与邮箱不存在返回**同一条** `INVALID_CREDENTIALS`。

## 4. 逐文件实现（签名 + 职责）

### 4.1 `app/security/password.py`

| 函数 | 签名 | 职责 / 返回 |
| --- | --- | --- |
| `hash_password` | `(plain: str) -> str` | 随机 16 字节 salt，`hashlib.scrypt(n=16384, r=8, p=1, dklen=32)` → `scrypt$N$r$p$salt$hash`（base64url 无填充） |
| `verify_password` | `(plain: str, stored: str) -> bool` | 解析存储串并 `hmac.compare_digest` 比对；格式/参数不符返回 `False`（不抛异常） |
| `dummy_verify` | `(plain: str) -> None` | 邮箱不存在时消耗同量级时间，抗账号枚举 |

### 4.2 `app/security/session.py`

| 函数 | 签名 | 职责 / 返回 |
| --- | --- | --- |
| `sign_session` | `(uid: str, exp: int, secret: str) -> str` | 生成签名票据 |
| `read_session` | `(token: str, secret: str) -> str \| None` | 验签 + 过期校验 → `uid`；任何异常返回 `None` |
| `session_exp` | `(now: int \| None = None) -> int` | `now + 7 天`（秒） |
| `set_session_cookie` | `(response: Response, uid: str, secret: str, secure: bool, now: int \| None = None) -> None` | 写 `lg_session`（属性见 §3） |
| `clear_session_cookie` | `(response: Response) -> None` | 清 Cookie（登出） |

### 4.3 `app/security/ids.py`

| 函数 | 签名 | 职责 / 返回 |
| --- | --- | --- |
| `new_id` | `(prefix: str) -> str` | `f"{prefix}_{secrets.token_hex(8)}"` |
| `new_code` | `() -> str` | 6 位房间码，字符集 `ABCDEFGHJKLMNPQRSTUVWXYZ23456789`（剔除 `0/O/1/I`） |

### 4.4 `app/repositories/users.py`

| 函数 | 签名 | 职责 / 返回 |
| --- | --- | --- |
| `insert_user` | `(conn, user_id: str, email: str, display_name: str, password_hash: str) -> None` | 写一行 `users` |
| `get_user_by_id` | `(conn, user_id: str) -> UserRow \| None` | 会话恢复用 |
| `get_user_by_email` | `(conn, email: str) -> UserRow \| None` | `lower(email) = lower(%s)`，与唯一索引同口径 |

`UserRow`（frozen dataclass）= `id, email, display_name, password_hash, created_at`；只在本层与 service 层出现。

### 4.5 `app/services/auth.py`（唯一写库入口，事务边界在本层）

| 函数 | 签名 | 职责 / 返回 |
| --- | --- | --- |
| `to_vo` | `(row: UserRow) -> UserVO` | 库行 → VO 的唯一转换点（防止 `password_hash` 外泄） |
| `register` | `(conn, data: RegisterIn) -> UserVO` | 事务内：邮箱查重 → 生成 `usr_` id → 写库；`UniqueViolation` 兜底并发 → `EMAIL_TAKEN(409)` |
| `login` | `(conn, data: LoginIn) -> UserVO` | 查邮箱 → 不存在则 `dummy_verify` 后抛 `INVALID_CREDENTIALS(401)`；口令不符同样抛该错误 |
| `get_user` | `(conn, user_id: str) -> UserVO \| None` | Cookie → 用户（不存在返回 `None`） |

### 4.6 `app/schemas/common.py` · `app/schemas/auth.py`

| 对象 | 说明 |
| --- | --- |
| `normalize_email` / `validate_email` | 去空白 + 小写 + 基础格式校验（不引第三方 `email-validator`） |
| `Page` / `LimitOffset` | 列表分页元信息与查询参数（`limit` 默认 20、上限 100），房间模块复用 |
| `RegisterIn` | `email`、`display_name`(1~32，去空白非空)、`password`(8~128) |
| `LoginIn` | `email`、`password` |
| `UserVO` | `id, email, display_name, created_at` |

### 4.7 `app/api/deps.py` · `app/api/routers/auth.py` · `app/main.py`

| 文件 | 函数 | 职责 |
| --- | --- | --- |
| `api/deps.py` | `db_conn()` | 每请求借一条连接（`with get_conn() as conn: yield conn`） |
| `api/deps.py` | `current_user_optional(request, conn)` | 读 Cookie → `read_session` 验签 → 查库 → `UserVO \| None` |
| `api/deps.py` | `current_user(user=Depends(current_user_optional))` | 未登录抛 `UNAUTHORIZED(401)` |
| `api/routers/auth.py` | `register` / `login` / `logout` / `me` | 取依赖 → 调 service → 信封；register/login 成功时写入会话 Cookie |
| `app/main.py` | `create_app()` | 装配 `lifespan`（`validate_startup` + `init_pool` / `close_pool`）、`register_error_handlers`、`register_routers`、`APP_ENV=demo` 时 `mount_spa` |
| `app/main.py` | `register_routers(app)` | `include_router(auth_router, prefix='/api')` |
| `app/main.py` | `mount_spa(app, dist_dir)` | 托管 `frontend/dist`（静态资源 + 未知路径回退 `index.html`） |

## 5. 并发、边界与失败

| 场景 | 处理 |
| --- | --- |
| 并发注册同一邮箱 | 先查后插 + `ux_users_email_lower` 唯一索引兜底；`UniqueViolation` → `409 EMAIL_TAKEN` |
| Cookie 缺失 / 过期 / 被篡改 | `/me` 返回 `200 {user: null}`；受保护接口 `401 UNAUTHORIZED`（有用例覆盖篡改） |
| 用户已删但 Cookie 仍在 | 查库拿不到行 → 视为未登录（不 500） |
| 账号枚举 | 邮箱不存在也执行一次同参数 `scrypt` 校验，且响应文案与口令错误一致 |
| 登出 | 只清 Cookie，无服务端吊销（如实登记在「安全与取舍」；M5 若要真吊销需加会话表） |
| 口令材料泄漏面 | 仅在 `users.password_hash`；日志、错误响应、前端产物均不得出现（`git grep` 检查项） |

## 6. 验证矩阵

| 层 | 用例 | 判据 |
| --- | --- | --- |
| 纯函数 | `test_password_hash_roundtrip` / `test_password_hash_uses_random_salt` / `test_verify_password_rejects_malformed_hash` | 哈希前缀 `scrypt$16384$8$1$`；同口令两次哈希不同；非法格式返回 `False` |
| 纯函数 | `test_session_sign_and_read_roundtrip` / `test_session_expiry` | 换密钥、篡改、过期一律 `None` |
| 服务层 | `test_register_writes_scrypt_hash_and_returns_vo` / `test_register_normalizes_email_case` / `test_register_duplicate_email_case_insensitive` | 库内是 `scrypt$` 且无明文；大小写归一；重复 → `EMAIL_TAKEN(409)` |
| 服务层 | `test_login_with_seed_demo_account` | 种子账号 `host@example.com` / `demo1234` 可登录（同时校验种子哈希与代码同口径） |
| 服务层 | `test_login_rejects_wrong_password_and_unknown_email` / `test_get_user_returns_none_for_unknown_id` | 两条路径都 `INVALID_CREDENTIALS(401)`；未知 id 返回 `None` |
| 接口层 | `test_register_endpoint_sets_cookie_and_me_returns_user` | 201 + 下发 Cookie；`/me` 返回同一用户；响应串里不含 `password` |
| 接口层 | `test_register_endpoint_duplicate_returns_409` / `test_register_endpoint_validation_error_envelope` | 409 `EMAIL_TAKEN`；400 `VALIDATION` |
| 接口层 | `test_login_endpoint_and_logout` / `test_me_without_cookie_returns_null_user` | 登录 200、错口令 401；未登录 `/me` = `{user: null}` |
| 接口层 | `test_protected_route_requires_login` / `test_protected_route_allows_logged_in_user` / `test_protected_route_rejects_tampered_session_cookie` | 401 / 200 / 401（测试用最小受保护路由，生产代码不加假路由） |

跑法：`pytest backend/tests -q`（r001 全量 37 项：schema 18 + 账户 19）。接口层用例通过依赖覆盖把 `db_conn` 指向「必定回滚」的事务，写入不污染种子数据。

## 7. 实现偏差（设计 vs 实际）

| 项 | 设计页 §9.4 原写法 | 实际落地 | 原因 |
| --- | --- | --- | --- |
| `current_user` 的位置 | 列在 `security/*` | 落在 `api/deps.py`；`security/session.py` 只留纯函数 | 放 security 会导致 `security → repositories` 反向依赖，违反架构页 §3 依赖方向 |
| `schemas/common.py` | 架构页 §4 目录树有该文件，cp 清单漏列 | 已新增（邮箱规范化、分页模型） | 注册/登录两处规范化口径不能双源 |
| `app/main.py` | 架构页 §9.2 已定义 | cp-r001-2 即落地（含模块级 `app = create_app()`，供 `uvicorn app.main:app`） | 接口层用例需要 `create_app`，与房间模块共用装配 |

## 8. 变更记录

| 日期 | 轮次 | 变更 | 原因 |
| --- | --- | --- | --- |
| 2026-09-17 | r001 | 新建本页（实现级契约首次成文） | 账户模块此前只有架构页 §9.4 的零散签名，cp-r001-2 交付后按代码回填，避免接口契约无事实源 |

## What's next

1. 前端 `/login`、`/register`、`useSession` 于 cp-r001-4 落地；落地后回填 §3 契约与实际调用是否一致。
2. 功能层待定项（`r001-accounts-features.md` §7 的 FQ-A1/A3）若改口径，同步改本页 §3 与 §5。
