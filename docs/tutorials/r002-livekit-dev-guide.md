---
title: r002 开发者教学：怎么改这个实时房间
description: 给接手改代码的人：模块地图、Token 策略怎么换、怎么加一个自定义能力、怎么调实时链路与打桩、两页的情绪令牌改哪里、验证命令与实测坑。
type: tutorial
status: approved
owner: 陀梓皓
updated: 2026-09-19
rounds: [r002, r003]
---

<!-- overview -->
这份文档面向**改代码的人**（使用者怎么用见 `docs/tutorials/r002-livekit-demo.md`，环境怎么起见 `r002-livekit-setup.md`）。
目标：让新接手的人在 30 分钟内知道「改哪一行会有什么后果」，不需要读完整套设计文档。事实源仍是 `docs/02-modules/r002-livekit.md`（实现）与 `r002-livekit-features.md`（功能）。

## 1. 前提

- conda 环境 `learningguide`（ADR-0006），仓库根 `.env` 已填 `DATABASE_URL` / `SESSION_SECRET` / `LIVEKIT_*` 四项。
- dev 服务由你自己起（前端 `5173`、后端 `8000`），本仓的约定是**不另起端口、不反复 build**；只有验收时才 `npm run build` 一次。
- 密钥纪律（AGENTS 禁区）：`LIVEKIT_API_SECRET` 只允许存在于 `.env` 与服务端进程；代码、前端产物、日志、错误响应、文档里都不许出现。

## 2. 模块地图（改哪里）

| 面 | 文件 | 职责 | 注意 |
| --- | --- | --- | --- |
| 后端 · LiveKit 出口 | `backend/app/services/livekit.py`（120 行） | **唯一**接触 `LIVEKIT_*` 的模块：`issue_token` / `remove_participant` / `delete_room` / `list_participant_identities` | 只读 `Settings`、不 import repositories、不做权限判断；网络调用一律在事件循环内构造 `LiveKitAPI` |
| 后端 · 业务与权限 | `backend/app/services/rooms.py` | 角色矩阵、库事务、`end_room`（r001 三件事 + r002 的 `delete_room`） | 权限判断只在这里；外部调用在**事务提交后**（ADR-0011 条 4） |
| 后端 · 接口 | `backend/app/api/routers/rooms.py` | `POST /rooms/{id}/token`、`/end`、`/members/{uid}/kick`、`/role`、`/transfer-host`、`/leave` | 薄层：解析 + 调 service + 封套 |
| 后端 · 配置 | `backend/app/config.py` | `livekit_mode` / `livekit_token_ttl_seconds`（cloud 3600、self 300）/ `room_capacity` / 超时 | 启动必填校验 `validate_startup` |
| 前端 · 房内页 | `frontend/src/pages/RoomLivePage.tsx`（441 行） | 组页面：状态条、舞台、抽屉、控制坞、四类确认框、`Esc` 退路 | 房内所有交互的总装配点 |
| 前端 · 控制坞 | `frontend/src/components/live/DeviceBar.tsx` | 设备组（麦克风/摄像头/电平/快捷键）+ 离场组（**房主=结束房间**，其他人=离开） | 只做呈现与回调，不发请求 |
| 前端 · 管理抽屉 | `frontend/src/components/live/RoomSidePanel.tsx` | 活跃/非活跃成员、移出、设为协管、移交房主、待处理申请、房间码 | 按角色隐藏；服务端仍会拦越权 |
| 前端 · 连接/设备 hooks | `hooks/useRoomConnection.ts`（连接状态机 + SDK 断开归因）、`useRoomToken.ts`（每次现签）、`useLocalDeviceState.ts`（设备状态保持）、`useOnlineIdentities.ts`、`useChromeIdle.ts`、`useMicLevel.ts`、`useActiveSpeaker.ts` | 实时状态 | 归因优先取 SDK 的 `DisconnectReason` |
| 样式令牌 | `frontend/src/styles/global.css` | 色板/间距/动效 + `--live-*`（交流页）+ `--wait-*`（等待页） | 调观感先改这里，再改组件 |

## 3. 怎么换 Token 策略

Token 是**纯本地签名**（不联网），签发点在 `backend/app/services/livekit.py:29` 的 `issue_token`：

```python
grants = api.VideoGrants(room_join=True, room=room_name, can_publish=True,
                         can_subscribe=True, can_publish_data=True,
                         room_admin=(role == "host"))
api.AccessToken(key, secret).with_identity(user_id).with_name(display_name) \
   .with_grants(grants) \
   .with_room_config(api.RoomConfiguration(max_participants=capacity)) \
   .with_ttl(timedelta(seconds=ttl))
```

- **想改 TTL**：改 `config.py` 的 `livekit_token_ttl_seconds`（按模式派生：cloud 3600 秒 / self 300 秒，ADR-0011 条 3）；下限 60 秒（握手耗时 + 授权弹窗 + 时钟偏差，见 ADR-0011 条 3 的补充）。前端 `useRoomToken.ts` 的 `staleTime: 0` / `gcTime: 0` 保证**每次连接都现签**，别改成缓存。
- **想改谁有管理权**：`room_admin=(role == "host")` 一行；协管没有平台级管理权，治理动作一律走我们自己的接口。
- **想改容量兜底**：`RoomConfiguration(max_participants=capacity)` 取 `settings.room_capacity`；应用层的容量校验在 `rooms.py`（按**在场**在**取票时**拦，ADR-0012）。两处口径必须一致，否则会出现「票里说 8、库里说 8、行为不一致」。
- **改完必须动测试**：`backend/tests/test_livekit_token.py` 直接解 JWT 断言 `identity` / `name` / `video.room` / `roomJoin` / `roomAdmin` / `max_participants` / `exp-iat`；改契约不改测试 = 红。

## 4. 怎么自助加一个自定义能力（以「举手」为例）

固定五个落点，缺一个就算没做完（`AGENTS.md` 硬规矩 6：文档与代码同一次提交）：

1. **库**：`backend/app/db/sql/00X_xxx.sql`（前进式迁移 + 版本表；本地可用 `python backend/scripts/db_init.py --reset --seed` 重建）。
2. **服务**：`app/services/rooms.py` 加函数（先 `SELECT … FOR UPDATE` 锁房间行，再判角色，再写库）；需要通知平台的，提交后调 `services/livekit.py`。
3. **接口**：`app/api/routers/rooms.py` 加路由（返回 `ok(...)` 封套；错误用 `AppError` + 稳定 error code，不要发明自由文本）。
4. **前端**：`api/rooms.ts` 加调用 → `RoomLivePage.tsx` 加 handler → 组件里加按钮（图标只从 Lucide 取，禁 emoji）→ 状态文案沿用风格指南的词表。
5. **文档 + 测试**：功能页（行为与文案）、实现页（接口与函数级事实）、`docs/rounds/rNNN-*/changes.md` 一行；测试至少两条（成功 + 越权/边界），LiveKit 相关一律**打桩**。

## 5. 怎么调实时链路与打桩

- **先取一张票看看**（后端 dev 跑着、已登录的浏览器里）：

```bash
curl -s -X POST http://127.0.0.1:8000/api/rooms/<room_id>/token --cookie "lg_session=<值>"
# 拿 data.token 去 https://jwt.io 或本地 base64 解 payload，看 video.room / roomAdmin / max_participants / exp
```

- **看真实断开原因**：`hooks/useRoomConnection.ts` 把 SDK 的 `DisconnectReason` 映射成文案（`PARTICIPANT_REMOVED` → 「你已被移出房间」、`ROOM_DELETED` → 「房间已结束」、`DUPLICATE_IDENTITY` → 「同一账号已在别处进入本房间」）。排查「为什么我掉线了」先在 Network/Console 找这个 code，别猜。
- **在场取证**：`services/livekit.list_participant_identities(room_name)` 直接问平台「现在谁在里面」（只用于排障；前端在场由 SDK 事件驱动）。
- **打桩方式**（`backend/tests/test_rooms_members_api.py` 的写法）：`monkeypatch.setattr(livekit_service, "remove_participant", lambda *a, **k: True)`；要验「外部失败不回滚」，就打成抛异常 → 接口仍 200、响应 `livekitApplied=false`、库内状态已改（ADR-0011 条 4）。
- **数据库用例是真实 PG**：`backend/tests/conftest.py` 用「整用例包在必定回滚的事务里」（`conn.transaction(force_rollback=True)`）+ `TestClient` 覆盖 `db_conn` 依赖，所以跑测试**不会污染种子数据**；`.env` 缺 `DATABASE_URL` 或 PG 没起时，需要库的用例会 skip 并打印原因。

## 6. 两页的情绪令牌改哪里

| 页 | 情绪 | 令牌（`frontend/src/styles/global.css` `:root`） | 改了会怎样 |
| --- | --- | --- | --- |
| 交流页 `/rooms/:id/live` | 专注感 | `--live-focus-dim`（非焦点格降饱和）、`--live-focus-brightness`、`--live-chrome-idle-seconds`（静默淡出秒数）、`--live-chrome-idle-opacity`、`--live-chrome`（状态条高度）、`--live-surface`、`--live-vignette`、`--live-tint`、`--live-focus-max-height`、`--live-rail-width`、`--live-stage-gap`、`--live-tile-radius` | 专注强弱与「界面退场」节奏全在这里；`--live-chrome-idle-seconds` 必须与 `RoomLivePage.tsx` 的 `CHROME_IDLE_SECONDS`（30）一致，否则 CSS 与 JS 两套节奏 |
| 等待页 `/rooms/:id/wait` | 温暖感 | `--wait-warm` / `--wait-warm-soft` / `--wait-breathe-duration`（呼吸光周期）、`--wait-autoenter-delay`（获批后自动进入的等待） | 暖色浓度与呼吸节奏；`prefers-reduced-motion` 下呼吸与位移必须静止（只留不透明度变化） |

通用：色板语义 `--warn` / `--danger` / `--ok`，间距 `--s-*`，动效 `--t-fast` / `--t-slow` / `--ease`；**新加令牌就写进 `docs/04-style/global-style.md` 的令牌表**，否则下一个人找不到。

## 7. 验证命令（提交前）

```bash
python backend/scripts/db_init.py --reset --seed     # 期望打印各表行数（会清空重建，慎用）
pytest backend/tests -q                              # 当前 95 passed（r001 基线 72 + r002 23）
cd frontend && npx tsc --noEmit && npm run build     # 类型 + 构建
python backend/scripts/smoke.py --base-url http://127.0.0.1:8000   # 真实 HTTP 全链路，末尾 PASS n/n
git grep -nE "API_SECRET|API_KEY" -- backend/app frontend/src       # 除 config.py 变量名外应无命中
```

## 8. 实测踩过的坑（照抄结论即可）

1. `LiveKitAPI(...)` **必须在运行中的事件循环里构造**（它初始化 `aiohttp.ClientSession`），在循环外构造会 `RuntimeError: no running event loop`；`services/livekit.py` 的 `_run` 统一用 `asyncio.run` 包一层。
2. 踢人时要**显式**传 `identity.revoke_token_ts = int(time.time())`（cloud 模式）：撤销按 Token 的 `nbf` 判定，默认截止带 1 分钟缓冲，不传会出现「人断了、旧票还能连回来」。
3. LiveKit **没有「入房授权钩子」**：平台只认票。要拦人，只能在「签发侧」拦 + cloud 侧撤销（`revoke_token_ts`）；自建模式只能靠短 TTL（ADR-0011 条 10）。
4. `self` 模式下绕开页面直连会出现「幽灵房」（平台里有房、库里没有），不影响库与演示；cloud 模式因撤销而拒绝（实现页 §8.13）。
5. 外部调用失败**不回滚业务状态**是刻意的（ADR-0011 条 4）：库侧动作已完成、响应里用 `livekitApplied=false` 如实告知，前端文案要区分这两态。
6. `pytest` 依赖真实 PostgreSQL；PG 没起或 `.env` 缺 `DATABASE_URL` 时相关用例会 **skip**（不是失败）——看到 skip 先查环境，别当成绿。

## 7. 加一个「房内能力」（r004 之后的最短路径）

r004 的四个能力（群聊 / 举手 / 焦点 / 共享）走的是同一条流水线，照抄即可：

1. **库**：写迁移 `backend/app/db/sql/00N_*.sql`（幂等、可重跑；**不要在文件里写 `BEGIN/COMMIT`**——事务由 `migrate.run_migrations` 统一负责，写了会让迁移悄悄中止且不记版本）；
2. **仓储**：SQL 放 `backend/app/repositories/`（参数化、只做 SQL、不开事务）；
3. **服务**：`backend/app/services/` 里写「校验 → 事务（`lock_room`）→ 返回快照」；
4. **路由**：`backend/app/api/routers/` 挂薄壳，返回统一信封（`ok(...)`）；在 `main.py` 注册；
5. **前端实时层**：`frontend/src/hooks/useDataChannel.ts` 里加一个 topic，写一个状态 hook（**HTTP 落库是唯一真相，通道只做加速**，见 ADR-0013）；进房与重连都 `refresh()` 一次；
6. **前端界面**：涉及「谁被放大」的改动只改 `components/live/stageLayout.ts`（纯函数），组件只渲染它的结果；
7. **验收**：后端补 pytest 用例 + `backend/scripts/smoke.py` 加两步；前端用 Playwright 双上下文跑一遍（见下）。

## 8. 双浏览器验收（本机自动跑，不需要两个人）

本机 base conda 的 Python 带 Playwright（`C:\ProgramData\miniconda3\python.exe`），可以直接开多个浏览器上下文：

```python
from playwright.sync_api import sync_playwright
with sync_playwright() as pw:
    br = pw.chromium.launch(headless=True, args=["--use-fake-ui-for-media-stream", "--use-fake-device-for-media-stream",
                                                 "--auto-select-desktop-capture-source=Entire screen"])
    ctx = br.new_context(viewport={"width": 1440, "height": 900}, permissions=["microphone", "camera"])
    ctx.request.post("http://localhost:5173/api/auth/login", data=json.dumps({"email": "...", "password": "..."}),
                     headers={"Content-Type": "application/json"})   # 会话 Cookie 直接进 context
    page = ctx.new_page(); page.goto("http://localhost:5173/rooms/<id>/live")
    page.wait_for_function("() => window.__lgRoom && window.__lgRoom.state === 'connected'")
```

要点与坑（都踩过）：

- **登录用 API**（`ctx.request.post`）比填表单稳，且 Cookie 与浏览器上下文共享；
- **等异步结果别用 Promise**：`evaluate_handle` 等一个可能永不 resolve 的 Promise 会无超时卡死；改成「发布 + 轮询 window 上的变量」；
- **屏幕共享在无头下也能测**：加 `--auto-select-desktop-capture-source=Entire screen`；
- **竖屏/窄屏量测**：`page.set_viewport_size({...})`；但**量测前先关抽屉**，否则抽屉占走 360px，缩格会挤成一列，看起来像布局 bug；
- **`window.__lgRoom`** 只在 `import.meta.env.DEV` 挂载，可用于：注入 `activeSpeakersChanged`（验优先级）、`disconnected` 加数值枚举（验归因文案）、以及观察 `state`；
- **归因枚举是数字**：`PARTICIPANT_REMOVED=4`、`ROOM_DELETED=5`、`DUPLICATE_IDENTITY=2`、`CLIENT_INITIATED=1`（传字符串名字不会命中映射）；
- **Playwright 的网络离线模拟不能替代真断网**：`ctx.set_offline(True)` 不会在 8 秒窗口内让 SDK 进入重连态（实测恢复后才判定），要验真实断网得用 `reconnect-drill.bat` 手动断 Wi-Fi。

## 9. 容量口径与「留痕 + 抛错」的事务陷阱（r005）

**口径**：房间人数 = 本库 `room_members.status='active'` 计数；LiveKit 不参与人数判定（ADR-0016 取代 ADR-0012 的 D1/D2/D3/D5）。

**判定点**：`request_join`（满 → 拒）、`approve_join_request`（满 → 拒）、`issue_room_token`（不查 LiveKit、在册即放行）。三处都在 `lock_room` 之后、同一事务里判。

**陷阱（真踩过）**：`db_conn` 是 psycopg_pool 的 `with connection()` —— **请求内抛异常 = 整条请求事务回滚**。
所以「写一条留痕 → 再抛 409」的写法里，留痕会被回滚掉（实测：409 有了、库里没有那条消息）。
两条正解：

1. **让请求正常返回**：service 返回一个结果标记（如 `RoomFullNotice`），路由层用 `fail(code, message, status)` 返回错误信封 —— 事务正常提交，留痕保住（r005 采用这条）；
2. 若确实要在抛错的同时留痕，就必须换一条**独立连接**（`get_conn()`）去写，并接受它不在请求事务里（本仓未采用）。

反面写法（别写）：在 service 里 `conn.commit()` —— 在测试夹具的外层 `Transaction` 上下文里会直接 `ProgrammingError: Explicit commit() forbidden within a Transaction context`。

**前端口径**：列表卡、交流页状态条、准入判定三处都用「在册 / 容量」；在场标记（在房间里/不在房间）只属于成员抽屉。
