---
title: r012 变更台账（cp 逐格记录）
description: r012（超管 · 管理后台 · 全服大屏聊天）的提交台账、门禁数字、用户消息回执台账与实测留痕位；cp-1 建骨架，逐 cp 追加。
type: reference
status: draft
owner: 陀梓皓
updated: 2026-09-20
---

<!-- overview -->
本页与实现**同提交**逐行追加（AGENTS.md 硬规矩 6：文档与代码同一次提交）。cp-1 建骨架，此后每个 cp 追加一行并填门禁数字。
分支 `req/r012-superadmin-console`；基点 = `req/r011-debt-backfill` @ `ab8edb5`（cp-7）。tag 逐个 cp 打 `cp-r012-N`。

## 1. cp 台账

| cp | 提交 | 内容 | 门禁数字（pytest / smoke / tsc+build） | 依据 |
| --- | --- | --- | --- | --- |
| cp-r012-1 | 本次提交 | 阶段 1 文档：需求单 + design + changes/review 骨架 + 轮次索引行 + `redirect-01` 指针 | 不适用（纯文档，未跑门禁；代码门禁从 cp-2 起） | 需求单 §9 |
| cp-r012-1b | 本次提交 | 阶段 1 批复登记：Q1~Q18 落地（需求单 §10.1）+ 按批改写 design（只管理不发布音视频 / 右侧 Copilot 式面板 / 前端短轮询心跳）+ 把 r011 收尾提交 `cp-8`/`cp-8b` merge 进本分支（`e0c6598`） | 不适用（纯文档） | 需求单 §10.1 |
| cp-r012-2 | 本次提交 | 迁移 011（身份/旁路/大屏/审计五对象）+ 012（演示超管）+ 身份（`users.role` + `UserVO.role` + `roles.py`）+ 在线心跳（`POST /api/presence` + `presence.py` + `usePresenceBeat` + `PRESENCE_ONLINE_SECONDS`）+ 提权脚本 `grant_superadmin.py` + ADR-0024 + 模块实现页首版 | pytest **174 passed**（+10）/ smoke 未跑（本轮 cp-7 统一跑）/ `tsc --noEmit` exit 0 | E1/E14 |
| cp-r012-3 | | 超管隐身进房（hidden Token + `room_visits` + 旁路校验收敛）+ 用例 | | E2/E3/E4/E10 |
| cp-r012-3 | 本次提交 | 超管隐身进房与旁路治理：`issue_token(hidden/attributes/can_publish*)`、`room_visits` 读写、`assert_room_role`/`assert_manager_role` 两处旁路、`effective_role`、离开/结束收口、worker 跳过超管、用例 8 条 | pytest **182 passed** / tsc 未跑（本轮未动前端） | E2/E3/E4/E10/E13（后端侧） |
| cp-r012-4 | | 管理后台后端（三列表 + 三动作 + 审计）+ 用例 | | E5/E6 |
| cp-r012-4 | 本次提交 | 管理后台后端：`repositories/admin.py` + `services/admin.py` + `schemas/admin.py` + `routers/admin.py` + `deps.current_superadmin` + 三列表/三动作/审计 + 用例 9 条 | pytest **191 passed** / tsc 未跑（未动前端） | E5/E6 |
| cp-r012-5 | | 大屏聊天 + SSE 后端 + 限流 + ADR-0025 + 用例 | | E7/E8 |
| cp-r012-5 | 本次提交 | 全服大屏聊天（`global_messages` + 服务/仓储/路由 + 限流 429`RATE_LIMITED`）+ SSE 通知通道（`GET /api/events` + 进程内 pub/sub + 6 项可调配置）+ ADR-0025 + 用例 9 条 | pytest **200 passed** / tsc 未跑（未动前端） | E7/E8 |
| cp-r012-6 | | 前端 `/admin` + 大屏面板 + 入口 + 超管视角 + 视觉参数区 + 教学两页 + 模块功能页 | | E5/E9/E12 |
| cp-r012-6 | 本次提交 | 前端落地：`api/{admin,globalChat}.ts`、`hooks/{useAdmin,useGlobalChat,useEventStream}.ts`、`GlobalChatDrawer`、`components/admin/` 四表、`AdminPage`、`/admin` 路由、顶栏「大屏」开关、侧栏「管理后台」（仅超管）、超管交流页视角（无设备控件 / `publishDevices=false` / `excludeIdentity`）、`ViewerRole` 类型、`global.css` r012 参数区 + 教学两页 + 功能页 + 04-style 条目 | `tsc --noEmit` exit 0；`npm run build` exit 0（2022 modules，`dist/assets/index-C8HitVdF.js` 984.19 kB / gzip 278.09 kB）；令牌扫描 0 命中 / emoji 0 / 单一图标库 0 违规 | E5/E9/E12/E13（界面侧） |
| cp-r012-7 | 本次提交 | 门禁复跑（`pytest` 200 / `tsc` 0 / `build` 0）+ 真机取证 5 项 + 三张截图入档 + 视觉对账五组 + review 定稿 + 索引/需求单/roadmap 回填 | 见 §3 实测 | E11/E12 |

## 2. 用户消息台账（vibecoding 8.1 判据：每条用户消息一行回执）

| # | 用户原话摘要 | 回执分类 | 单号 | 处置 |
| --- | --- | --- | --- | --- |
| 1 | 「设计LearnGuide项目的r012」 | 新轮次设计请求（沿用已登记 `redirect-01`） | — | 出阶段 1 文档（cp-1）+ `ASK-r012-1` 待批 |
| 2 | 「1 1 1 1 1 1 1 1（…超管不能说话和视频，只能管理！） 1 1 2（右侧的侧栏打开窗口，像编译器里的 coplit） 2（只 admin 可见） 1 2（短轮询） 1 1 1 1」 | 澄清回答（W2，答 `ASK-r012-1` 全 18 项） | — | 批复落需求单 §10.1 + 按批改 design（cp-1b）；两条口径补充记入 Q4/Q8 行 |

## 3. 实测数字与留痕（逐 cp 追加，禁占位）

| 项 | 命令 / 做法 | 实测 | 时间 |
| --- | --- | --- | --- |
| 阶段 1 文档落盘 | `ls docs/rounds/r012-superadmin-console` | 4 个文件：`design.md` / `changes.md` / `review.md` / `redirect-01.md`（+ 需求单 1 个）；cp-1 `0192e25`、cp-1b（本次） | 2026-09-20 |
| 迁移应用 | `python backend/scripts/db_init.py --seed`（**不 reset**，沿用 r011 口径「演示库开发结束后统一清」） | `[migrate] 本次应用版本：011_r012_superadmin_global_chat, 012_r012_seed_superadmin`；`schema_migrations 12`；新表 `room_visits / global_messages / admin_audit` 各 0 行 | 2026-09-20 |
| 演示超管 | `db_init.py --seed` 后查库 | `usr_demo_admin / admin@example.com / 平台管理员 / role=superadmin`（last_seen_at 初始 NULL） | 2026-09-20 |
| 提权脚本 | `python backend/scripts/grant_superadmin.py --email host@example.com` → `--revoke`；再试不存在的邮箱 | `user → superadmin（影响 1 行；id=usr_demo_host）` / `superadmin → user（影响 1 行；id=usr_demo_host）` / 退出码 2 `找不到账号：nobody@example.com` | 2026-09-20 |
| 门禁四项（cp-7） | `pytest backend/tests -q` / `npx tsc --noEmit` / `npm run build` / `smoke.py --base-url http://127.0.0.1:8000` | **201 passed**（49.17s）/ `tsc` exit 0 / `build` exit 0（2022 modules，`dist/assets/index-C8HitVdF.js` 984.19 kB / gzip 278.09 kB）/ smoke **PASS 58/58**（r011 时 47/47，本轮 +11 步：超管登录、普通账号 403、四列表、超管取票 claims、大屏发与读、未登录 401、未登录可读、心跳） | 2026-09-20 |
| 缺陷 · SSE 广播跨线程 | 真机取证时把 8000 卡死（进程在、CPU 0%、`/api/auth/me` 8s 超时）；定位到同步端点在线程池里直接 `queue.put_nowait`，订阅者正 `await queue.get()` 时跨线程唤醒等待者会破坏事件循环 | 修法：`Subscriber` 记住订阅时的循环 + `publish` 走 `loop.call_soon_threadsafe(_offer, …)`；新增回归用例 1 条；真机复验：SSE 挂起中连发 3 条 → 3 帧到达且服务端 0.02s 仍响应。卡死的后端进程由助手精确按 PID 停掉并以**无窗口且不带 `--reload`**的方式重启（PID 10404），前端 5173 未动 | 2026-09-20 |
| 用例 · 数据隔离 | 真机消息落库后 `test_global_chat.py` 有 4 条用例失败（断言全表内容） | 加 autouse 夹具：每个用例前**在测试事务里**清空 `global_messages`（`db` 是 `force_rollback`，不外泄）；修后单文件 10 passed / 全量 201 passed | 2026-09-20 |
| 真机 · 管理后台 | 浏览器打 `http://localhost:5173/admin`（超管登录） | 房间分区「共 136 条」、8 列表头、四分区 tab、动作按钮与分页正常；截图 `%TEMP%\lg_r012\cp7-admin-rooms.png` | 2026-09-20 |
| 真机 · 右侧大屏面板 | 顶栏「大屏」开合 + `getComputedStyle` | 展开态 `transform: matrix(1,0,0,1,0,0)`、宽 **360px**（= `--gc-w`）、`left=867/1243`；收起态 `matrix(1,0,0,1,376,0)`（= 360 + `--gc-offset` 16）与 `transition-duration: 0.24s`；收起时 `aria-hidden=true` + `visibility:hidden`；页面 `scrollWidth == clientWidth == 1243`（无横向溢出） | 2026-09-20 |
| 真机 · 跨客户端 SSE | host@example.com 经 HTTP 发一条 → 浏览器面板**未刷新**即出现 | 面板行：`林泽宇 17:04 来自另一个客户端（host）的消息`；面板标题「1 人在线」+ 1 个绿点 | 2026-09-20 |
| 缺陷 · 交流页「大屏」按钮无动作（cp-8） | 交流页设计上不挂大屏面板，但顶栏按钮照渲染 → 点了没反应（界面口径禁「有反馈无动作」） | 修：`App.tsx` 在交流页不传 `onToggleChat`；CDP 真机复核：交流页 `hasChatBtn=false / drawerMounted=false`，列表页 `true`；`tsc`/`build` 仍绿 | 2026-09-20 |
| 真机 · 超管只读视角 | 超管进**他人房间**（非成员）`/rooms/room_beb67510a8d00b64/live` | 顶部提示「管理视角：你以隐身方式在场…不发布音视频，只做管理。」；控制坞仅 `管理视角 · 隐身` + `离开` + `结束房间`，**无**麦克风/摄像头/共享/举手控件；舞台 0 格；截图 `%TEMP%\lg_r012\cp7-superadmin-room.png` | 2026-09-20 |
| 真机 · 应用内取票 claims | 浏览器内 `POST /api/rooms/{id}/token` | `status 200`；JWT：`hidden=true`、`canPublish=false`、`canPublishData=false`、`roomAdmin` 非真、`attributes={'lg-role':'superadmin'}`、`room` = 目标房、`url` = 项目 LiveKit Cloud 地址 | 2026-09-20 |
| 已知环境限制 | 工具浏览器内 LiveKit 媒体连接未建立（徽标「未连接」，控制台 0 个 JS 错误） | 已由 cp-7b 用 CDP 起真 Chrome 绕过（真 Chrome 里徽标=已连接）；原登记在 review §6 未闭合 ①/② | 2026-09-20 |
| 真机 · 超管隐身交叉验证（cp-7b） | `python backend/scripts/verify_r012_superadmin_invisible.py`（两个隔离 Chrome，9222 成员 / 9223 超管） | **PASS 17/17**。成员端：舞台 `1 格不变`（`tileNames=['林泽宇']`）、在册 `2 / 8 成员` 前后一致、成员抽屉（长度 116）无「平台管理员」。超管端：徽标 `已连接`、chip `管理视角 · 隐身`、dock `['管理视角 · 隐身','离开','结束房间']`、mic/cam/share/hand 全 false | 2026-09-20 |
| 真机 · LiveKit 服务端权限（cp-7b） | `list_participants(room_beb67510a8d00b64)` | `usr_demo_host`: hidden=false / canPublish=true；`usr_demo_admin`: **hidden=true / canPublish=false / canPublishData=false / attributes={'lg-role':'superadmin'} / tracks=[]**（媒体层也发不出去） | 2026-09-20 |
| 真机 · 动效降级（cp-7b） | CDP `Emulation.setEmulatedMedia(prefers-reduced-motion=reduce)` | 常规 `transform, opacity` / **0.24s**（收起 `translateX(376px)`、展开 `0`）；reduce 下 `none` / `1e-06s`，`matchMedia(...)`=true，收起 200ms 内到位、再开 150ms 内到位 | 2026-09-20 |
| 副作用与收尾（cp-7b） | 脚本自身 | 该房新增 1 条超管 `room_visits`（hidden=true）→ 脚本用 `close_room_visit` 自动关闭；`room_members` 仍 host+mod（在册 2）；两个 Chrome 一律 `Browser.close`（未用 taskkill）；成员在无麦无头浏览器中 `tracks=[]`（**未发布任何音频**，不污染转写） | 2026-09-20 |
| 用例（cp-2） | `pytest backend/tests -q` | **174 passed**（r011 基线 164；新增 10 条：`test_presence_api.py` 4 + `test_superadmin_identity.py` 6）42.83s | 2026-09-20 |
| 用例（cp-3） | `pytest backend/tests -q` | **182 passed**（新增 8 条：`test_superadmin_room_access.py`）45.03s | 2026-09-20 |
| 用例（cp-4） | `pytest backend/tests -q` | **191 passed**（新增 9 条：`test_admin_api.py`）48.57s | 2026-09-20 |
| 用例（cp-5） | `pytest backend/tests -q` | **200 passed**（新增 9 条：`test_global_chat.py`）49.30s | 2026-09-20 |
| SSE 帧 | 直接驱动响应生成器断言 | 首帧 `retry: 3000`；事件帧 `id: 1` / `event: notify` / `data: {"type":"global_message","payload":{"id":"gmsg_test"}}`；保活帧 `: ping`；响应头含 `X-Accel-Buffering: no` | 2026-09-20 |
| 限流 | 用例：窗口内连发至上限 + 1 条 | 第 N+1 条 429 `RATE_LIMITED`；窗口内落库条数 == 上限（限流不落库） | 2026-09-20 |
| 卡壳与修正 | 首版 SSE 用例走 `TestClient.stream()`：流永不结束 → 用例挂死、pytest 280 秒超时 | 改为**直接驱动 `StreamingResponse.body_iterator`**（订阅后再 publish），1.37s 通过；教训：**永不结束的流不许走 TestClient 收尾** | 2026-09-20 |
| 鉴权矩阵 | 用例：房主与游客打四读三写 | 四读 403 / 三写 403 / 未登录清理 Cookie 后 401 | 2026-09-20 |
| 删房 | 用例：删前插一条消息，删后查库 | `{deleted: true, livekitApplied: true}`（LiveKit 打桩）；`rooms` 行消失、`get /api/rooms/{id}` 404、该房 `chat_messages` 计数 0、审计里 `detail.snapshot.title/messageCount` 仍在 | 2026-09-20 |
| 超管 Token claims | 用例解 JWT 断言 | `hidden=True` / `canPublish=False` / `canPublishData=False` / `roomAdmin` 非真 / `attributes={'lg-role':'superadmin'}` / `maxParticipants=房间容量` | 2026-09-20 |
| 满员房 | 用例：房主 + 7 成员（在册 8） | 超管取票 200 且 `memberCount` 恒 8；路人 403 `NOT_MEMBER` | 2026-09-20 |
| 前端类型 | `cd frontend && npx tsc --noEmit` | exit 0 | 2026-09-20 |
| 前端构建 | `cd frontend && npm run build` | exit 0（`tsc --noEmit && vite build`；2011 modules，`dist/assets/index-DB_GFgTm.js` 962.81 kB / gzip 272.75 kB） | 2026-09-20 |
| 密钥扫描 | `git grep -nE "API_SECRET|API_KEY" -- backend/app frontend/src` | 命中 8 行，**全部为键名/变量名**（`config.py` 6 处变量名 + `stt.py:82`、`summary.py:103` 报错文案 + `RoomSummaryPage.tsx:96` 提示文案），**本轮新增命中 0**、无任何密钥值 | 2026-09-20 |
| 未新增依赖 | `git diff --stat -- frontend/package.json backend/requirements*.txt` | 空 | 2026-09-20 |
| 门禁四项 | `pytest backend/tests -q` / `smoke.py` / `tsc --noEmit` / `npm run build` | 待填（cp-7；基线 r011：pytest 164 / smoke 47-47 / tsc·build exit 0） | |
| 隐身真机 | 2 浏览器：成员列表 / 舞台 / 人数 | 待填（cp-3） | |
| SSE 真机 | `curl -N http://127.0.0.1:8000/api/events` + 另一客户端发大屏消息 | 待填（cp-5） | |

## 4. 变更记录

| 日期 | 版本 | 改了什么 | 依据 |
| --- | --- | --- | --- |
| 2026-09-20 | 骨架（cp-1） | 建页：cp 台账骨架 + 用户消息台账 + 实测留痕位 | 需求单 §9；vibecoding 8.1 判据 |
| 2026-09-20 | cp-1b | 登记阶段 1 批复（Q1~Q18）与两条补充口径；cp 台账加 cp-1b 行、台账加用户消息 #2；并入 r011 `cp-8`/`cp-8b` | 用户 2026-09-20 批复 |
| 2026-09-20 | cp-2 | 迁移 011/012 + 身份 + 在线心跳 + 提权脚本 + ADR-0024 + 模块实现页首版；用例 174 passed、tsc 0；`roles.py`「角色判据唯一入口」随本 cp 提前落地（提权脚本要用，属 cp-3 计划的同一模块） | 需求单 §9 cp-2、§10.1（Q1/Q14/Q15）；ADR-0024 |
| 2026-09-20 | cp-3 | 超管隐身进房（hidden/只读 Token + `room_visits`）+ 两处旁路收敛 + `effective_role` + worker 跳过超管；用例 182 passed | 需求单 §9 cp-3、§10.1（Q2/Q3/Q4/Q8）、ADR-0024 D2~D5 |
| 2026-09-20 | cp-4 | 管理后台后端（三列表 + 三动作 + 审计 + 鉴权依赖）；用例 191 passed；查询参数定 snake_case（与既有 `mine=` 同口径，design §3.3 同步修正） | 需求单 §9 cp-4、§10.1（Q5/Q6/Q7/Q16）、ADR-0024 D6 |
| 2026-09-20 | cp-5 | 大屏聊天 + SSE 通知通道 + 限流 + ADR-0025；用例 200 passed；SSE 载荷口径定案（`type`+`payload` 同帧） | 需求单 §9 cp-5、§10.1（Q11/Q13/Q14）、ADR-0025 |
| 2026-09-20 | 交接 | 另一会话在 `NavBar.tsx` / `SideBar.tsx` 的未提交改动（邀请码入口移入侧边栏，属 r011）由本分支先落盘为独立提交，再在其上做 cp-6，避免两份改动混进同一个提交 | 用户 2026-09-20 选择「现在就一并改」 |
| 2026-09-20 | cp-6 | 前端落地（见 cp 台账行）+ 教学两页 + 功能页 + 04-style §12.4；`tsc`/`build` 绿、令牌与 emoji 扫描 0 命中 | 需求单 §9 cp-6、§10.1（Q11/Q12/Q13/Q14）、design §5/§9 |
| 缺陷 · SSE 订阅把连接池攥死（cp-8b） | 台本逐项自检时发现：后端日志 46 次 500，全是 `psycopg_pool.PoolTimeout: couldn't get a connection after 30.00 sec`。根因 —— `/api/events` 依赖 `current_user_optional`（DB 依赖），而流永不结束、依赖清理在响应之后跑 → 每个订阅者永久占用连接池（max 8）一条连接 | 真机复现（真 HTTP）：9 条 SSE 挂着时普通请求 **30.02s → 500**×3，关流立刻 200；修法：SSE 路由去掉 DB 依赖（只推公开最小通知、未登录可订阅）；修复后 12 条流挂着普通请求仍 **200 / 0.02s**、admin 登录 **200 / 0.09s**。守卫：`test_events_route_must_not_depend_on_db`（依赖树 + 池占用）+ smoke 新增「挂 9 条 SSE 仍畅通」一步。后端按 PID 重启（无窗口、不带 `--reload`，新 PID 21748） | 2026-09-20 |
| 缺陷 · 系统消息不实时进房内讨论流（cp-8c） | 台本逐项自检发现：房主批准 / 邀请码加入 / 移出成员后，系统消息已入库但房主讨论抽屉 20 秒不出现，切 tab、关开抽屉都无效，**只有 F5 才出现**（真机、页面 visible+focused） | 根因：`useChatMessages` 只在进房/重连拉库，之后靠 DataChannel 增量合并，而**系统消息是服务端写的、没有任何客户端广播它**（聊天消息由发送方广播所以能到）。修法（前端两处）：① `refresh()` 拉到近 30 秒新出现的系统消息就复用 chat topic 补广播（按 id 去重、已知 id 不重播）；② 治理动作后 `refreshRoster()` 连带 `chat.refresh()`。证据：`verify-runbook-flow.py` 真浏览器跑台本 S2→S8 **16/18 → PASS 18/18**（S3/S7 由 FAIL 转 OK）；`tsc`/`build` 绿 | 2026-09-20 |
| 自检脚本两处健壮性修正（cp-8c） | ① 自检脚本因**未聚焦的窗口会暂停轮询**（`refetchIntervalInBackground: false`）误判系统消息 → 脚本补 CDP 聚焦模拟；② `verify-runbook-ui.py` 的成员 tab 断言依赖「房里有别人」，房间选择改为优先选成员 ≥ 2 的房；成员行与后台表格改为「等条件成立再断言」 | 真机复核：`verify-runbook-ui.py` **PASS 28/28**、`verify-runbook-flow.py` **PASS 18/18** | 2026-09-20 |
| 真机执行「删除房间」（cp-8c） | 台本 S10 讲「删除是硬删、台上不点」，故改在台下真跑一次：超管 `DELETE /api/admin/rooms/room_e173e7b8e77416e2` → `200 {deleted: true, livekitApplied: false}`，`admin_audit` 落一条 `room.delete`（操作人「平台管理员」）；删除后列表里该房消失 | 真机实测（顺带清掉我自建的调试房） | 2026-09-20 |
| 2026-09-20 | cp-8c | 台本行为流自检：新增 `frontend/scripts/verify-runbook-flow.py`（真浏览器跑 S2→S8 + 大屏跨端，18 条判据）＋ 修掉「系统消息只有 F5 才出现」 | 你 2026-09-20「台本所有涉及的项目」；Q1=1/Q2=1 |
| 2026-09-20 | cp-8b | 台本逐项自检：新增 `frontend/scripts/verify-runbook-ui.py`（按角色核对台本点名的按钮与文案）＋ 顺带揪出并修掉 SSE 占满连接池的缺陷（46 次 500 的根因）＋ 冒烟 59/59、pytest 202 | 你 2026-09-20「再检查测试一遍」「台本所有涉及的项目」 |
| 2026-09-20 | cp-8 | 演示台本并入 r012（`docs/00-project/demo-runbook.md` v3：时间轴 6 分 35 秒 + §1.1 三分钟取舍表 + S10 管理后台 + S11 超管隐身/大屏 + 按钮速查 8 行 + 兜底 5 行 + 录屏分镜 3 行 + 附录数字 201 / 58 / 17）＋ 修「交流页『大屏』按钮点了没反应」 | 你 2026-09-20「设计台本」+「3 1 1」；台本 v3；CDP 真机复核 | E11/E12（交付物） |
| 2026-09-20 | cp-7b | 未闭合 ①② 闭合：新增可复跑真机交叉验证脚本 + 两隔离 Chrome（CDP）取证 + LiveKit 服务端权限证据 + reduced-motion 强制模拟；review §1/§4/§4.1/§6 更新 | `verify_r012_superadmin_invisible.py` → **PASS 17/17**（Chrome 152 / CDP 1.3） | E2/E13/E11 |
| 2026-09-20 | cp-7 | 门禁复跑（pytest 200）+ 真机取证（后台 136 条 / 面板开合实测 / 跨客户端 SSE / 超管只读视角 / 应用内取票 claims）+ 三张截图 + 视觉五组 + review 定稿 + 索引与 roadmap 回填 | 需求单 §9 cp-7；review §1/§4 |
| 2026-09-20 | cp-4b | **补交**：`services/presence.py::online_since()`——cp-4 提交时漏登记该文件，导致 `GET /api/admin/users?online_only=1` 在 cp-4 树里引用了不存在的函数（本地工作区有、提交里没有）。教训记在此：**冷启动核对**（提交后 `git status` 必须为空，本轮 cp-4 曾遗留一个未登记的已改文件） | cp-4 自审发现 |
