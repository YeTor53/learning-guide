---
title: r002 变更与进度记录
description: r002 逐 cp 的文件清单、验证证据与文档落点（实现期逐条追加）。
type: reference
status: draft
owner: 陀梓皓
updated: 2026-09-18
---

<!-- overview -->
本页按 cp 追加：动了哪些文件、跑了什么验证、证据原样（贴命令与输出摘要）、对应文档页面锚点。
验证未全绿不打 tag；工作区带脏状态不许开下一个 cp。

## cp 计划（见需求单 §10）

| cp | 内容 | 状态 |
| --- | --- | --- |
| cp-r002-1 | 文档先行：需求单 + 总设计增量 + 模块两页 + 归档归位 + 索引/README/roadmap 同步 | **进行中（本批，待批）** |
| cp-r002-2 | 后端：config 必填 + `services/livekit.py` + rooms/repositories/schemas/routers 增量 + 用例 + r001 两条测试欠账 +（R-6）索引迁移 | 未开始 |
| cp-r002-3 | 房间管理页口径调整 + 交流页（专注感）：4 组件 + 4 hooks + `api/livekit.ts` + 路由 + 专注态令牌 | 未开始 |
| cp-r002-4 | 等待页（温暖感）：`/rooms/:id/wait` + 轮询与获批自动进入 + 暖色令牌与呼吸动效 | 未开始 |
| cp-r002-5 | 冒烟四步 + 教学页两篇 + README/AGENTS/roadmap 回填 + 需求单勾选与证据表 | 未开始 |

## 文档落点（矩阵对应）

| 文档 | 本轮落点 | 状态 |
| --- | --- | --- |
| 需求单 | `docs/00-requirements/r002-livekit-room.md` | 建立（draft） |
| 设计页（总设计增量） | `docs/01-architecture/r002-realtime-architecture.md` | 建立（draft） |
| 模块实现页 | `docs/02-modules/r002-livekit.md` | 建立（draft，实现回填随 cp-2/3） |
| 模块功能页 | `docs/02-modules/r002-livekit-features.md` | 建立（draft） |
| 使用者教学页 | `docs/tutorials/r002-livekit-demo.md` | planned（跑通后写） |
| 开发者教学页 | `docs/tutorials/r002-livekit-dev-guide.md` | planned（跑通后写） |
| 决策记录 | `docs/03-decisions/r002-adr-0011-realtime-presence-model.md`（9 条约定 + 5 条被否方案） | 建立（proposed，随设计一起批） |
| 重定向确认单 | `docs/rounds/r002-livekit/redirect-01.md` | confirmed-C（批复「设计进行」，结论已落地） |
| 索引/项目级 | `docs/00-requirements/README.md`、`README.md`、`AGENTS.md`、`global-roadmap.md` | 索引行本批；其余随 cp/收官 |

## 逐 cp 记录（实现期追加）

### cp-r002-1（文档先行）

- 文件：`docs/00-requirements/r002-livekit-room.md`、`docs/01-architecture/r002-realtime-architecture.md`、`docs/02-modules/r002-livekit.md`、`docs/02-modules/r002-livekit-features.md`、`docs/99-archive/r002-ahead-invites.md`、`docs/rounds/r002-livekit/{design,changes,review}.md`；改 `docs/00-requirements/README.md`、`README.md`、`docs/00-project/global-roadmap.md`、`docs/02-modules/r001-rooms*.md`、`docs/00-requirements/r001-*.md`、`docs/rounds/r001-skeleton/{design,review}.md`（旧归档路径指针同步）。
- 验证（实测输出）：
  - front matter 解析：8 个新建/改写页全部通过；代码围栏成对（另修掉 r001 功能页 1 处未闭合围栏）。
  - 全库内部链接扫描：仅剩 2 个**有意**的 planned 链接（`docs/tutorials/r002-livekit-demo.md`、`r002-livekit-dev-guide.md`，随 cp-r002-4 落地），其余全部解析成功；顺手修掉风格指南里 1 处 ADR 占位路径。
  - `git grep -n "r001-ahead-m2-m3-rooms"`：无命中（历史迁移注记已改写为叙述式，避免假装是活链接）。
- 提交：`603049e`（归档页 `git mv` 重命名）→ `d1b62df`（内容与同步，17 文件 +1004/-102）。
  - 说明：首次 `git add` 因列表中含「已被重命名、工作区已不存在」的旧路径而整批失败，只提交了 `git mv` 那一步；故本 cp 落为两次提交（重命名 / 内容），**未使用 `amend`**（AGENTS 硬规矩 5：历史 append-only）。
- 状态：工作区只剩未跟踪的 `frontend/.vite/`（Vite 缓存；是否加进 `.gitignore` 待你一句话）。

## 重定向 / CR 台账

| 单号 | 类型 | 触发 | 定性 | 状态 | 结论 |
| --- | --- | --- | --- | --- | --- |
| `redirect-04.md` | 用户新意见（页面职责三分与两种情绪取向） | 设计待批阶段，用户提「房间页当管理页，再设计交流页和等待页（专注感/温暖感）」+「这项加入 r002 任务中」 | B（本轮设计未做到位）+ 页面职责口径调整（按 L3 看待） | **confirmed-B** | 三页职责与路由、交流页 6 条专注要点、等待页 6 条温暖要点、参数单点可调；调研笔记放 `G:\Documents\r002-交流页与等待页-设计调研.md`（不入仓库） |
| `redirect-03.md` | 用户新意见（原生弹窗掉价） | 设计待批阶段，用户提「已批准的控制台消息太掉价了吧，记账」 | C（现有 8 处）+ r002 提示口径定死（按 L2 看待） | **proposed（待你一次批复）** | 实测 8 处全在 `RoomDetailPage.tsx`（:108/:114/:118/:119/:124/:129/:221/:222）；建议：旧的不改只记账，r002 内一律站内 toast + 自绘 `ConfirmDialog`，两个新组件并入 cp-r002-3 |
| `redirect-02.md` | 用户新意见（等候室是否没设计） | 设计待批阶段，用户问「等待间是否没有设计」 | C（G1/G2/G3 都未设计）+ G1 提前做（按 L3 看待） | **proposed（待你一次批复）** | 覆盖地图：审批链路 r001 已批准已实现（F-04/F-05 + 9 步实操）；缺口三块——G1「等候态」（提交后无等候区、批准不自动进房）· G2 批准后无通知（只有 5s 轮询）· G3 等待队列/满员排队。建议：G1 进本轮（无后端改动，只加前端等候态与自动进入），G2/G3 只记账 |
| `redirect-01.md` | 用户新意见（断线重连与状态保持） | 设计待批阶段，用户问「断线重连，状态保持有码」 | C（后续工作）+ 其中「连接层/设备层」属提前做＝范围变更（按 L3 看待） | **confirmed-C（2026-09-18 批复「设计进行」）** | 断线重连（连接层）+ 设备状态保持（设备层）进 r002；业务状态恢复留 M3/M5 ①；C-1 断线归因改用 SDK reason、C-2 同账号双开改为「后进踢掉先进 + 提示」、C-3 重连后本地轨道恢复行为待 cp-r002-3 实测 |

### cp-r002-2（后端，进行中）

**已完成（提交见下方证据）**

| 文件 | 内容 |
| --- | --- |
| `backend/app/config.py` | `VALID_LIVEKIT_MODES` / `LIVEKIT_TOKEN_TTL_SECONDS = {cloud:3600, self:300}` / `DEFAULT_LIVEKIT_TIMEOUT_SECONDS = 10`；`Settings` 新增派生属性 `livekit_token_ttl_seconds`、`livekit_timeout_seconds`；`validate_startup` 追加：`LIVEKIT_MODE ∈ {cloud,self}`、三项必填（只报键名）、URL 必须 `ws(s)://` |
| `backend/app/services/livekit.py`（新增） | `issue_token`（纯本地签名）/ `remove_participant`（cloud 传显式 `revoke_token_ts`）/ `delete_room` / `list_participant_identities` / `_run`（循环内构造 LiveKitAPI + 超时 + 失败只记日志） |
| `backend/tests/test_livekit_token.py`（新增 9 项） | Token 契约（grants/roomConfig/TTL 按模式派生/显式覆盖/验签/secret 不出现在 token）+ 配置校验（三项缺失、模式非法、URL 非法、派生项单点） |

**实测证据（2026-09-18）**

- `pytest backend/tests -q` → **81 passed**（r001 基线 72 + 本步 9），rc 0
- 真机（Cloud，`.env` 已填）：`issue_token` ✓ 长度 448；`list_participant_identities("room_demo_epicurus")` → `[]`（房间不存在，上游 404 被 `_run` 记日志降级）；`remove_participant(...)` → `True`（传了 `revoke_token_ts`，官方行为：房间/参与者不存在也返回成功）
- 依赖：`livekit-api 1.2.1`（→ `livekit-protocol 1.1.27`、`aiohttp 3.14.3`、`protobuf 7.36.1`、`PyJWT 2.14.0`）；前端 `livekit-client 2.22.3` + `@livekit/components-react 2.9.24`，`npx tsc --noEmit` 全绿
- 实现期发现（已回填设计）：① `LiveKitAPI.__init__` 需在事件循环内调用（否则 `RuntimeError: no running event loop`）→ `_api()` 同步工厂作废，改为 `_run(call)` 包一层；② 本版 SDK 的移除请求类名是 `livekit.protocol.room.RoomParticipantIdentity`；③ Token 用 `nbf`/`exp`（无 `iat`），TTL 断言应为 `exp - nbf`

**第二步（cp-r002-2 完成，本提交）**

| 文件 | 内容 |
| --- | --- |
| `backend/app/services/rooms.py` | 新增 `issue_room_token`（拦截顺序 401→404→409 `ROOM_ENDED`→403 `NOT_MEMBER`；本地签票）/ `kick_member`（Host 任意、Moderator 只能踢普通成员；库侧 `inactive/kicked` 先落，外部移除在提交后）/ `set_member_role`（仅 Host，仅 moderator⇄participant）/ `transfer_host`（事务内改双方角色 + `rooms.host_id` + 不变量断言 `count_active_hosts == 1`）；`end_room` 追加「事务提交后 `delete_room`」并回填 `livekitApplied`；新增 `_safe_livekit` 兜底 |
| `backend/app/repositories/rooms.py` | `update_room_host` / `update_member_role` / `count_active_hosts` |
| `backend/app/schemas/rooms.py` | `RoomVO.livekit_applied`（仅触达外部服务的响应带）、`RoomTokenVO`、`RoleIn`、`TransferHostIn`、`KickResult`、`TransferHostResult` |
| `backend/app/api/routers/rooms.py` | 新增 4 条：`POST /rooms/{id}/token`、`DELETE /rooms/{id}/members/{uid}`、`PATCH /rooms/{id}/members/{uid}/role`、`POST /rooms/{id}/transfer-host` |
| `backend/app/db/sql/003_r002_host_uniqueness.sql` | R-6：活跃 Host 唯一部分唯一索引（幂等；已应用到本机库） |
| `backend/tests/test_rooms_members_api.py`（新增 9 项） | Token 三态 + grants 按角色、踢人（成功/外部失败/权限矩阵）、角色守卫、移交、结束房间 `livekitApplied` |
| `backend/tests/test_schema.py`（+2、改 1） | 迁移清单加 003；R-6 两个方向断言（两个活跃 Host 拒绝 / 历史 Host 可并存） |
| `backend/tests/test_rooms_api.py`（+2） | 偿还 r001 两条欠账：列表分页、房间码冲突重试 |
| `backend/requirements.txt` | 追加 `livekit-api` / `livekit-protocol` / `aiohttp`（+其依赖）/ `protobuf` / `PyJWT` / `types-protobuf` |

**实测证据**：`pytest backend/tests -q` → **94 passed**（r001 基线 72 + 本轮 22），rc 0；`003` 迁移幂等且索引已在库中（`ux_room_members_one_active_host ... WHERE status='active' AND role='host'`）；接口层用例全程打桩（`app.services.livekit.*`），无真实外呼。

**cp-r002-2 判据核对**：pytest 全绿且含新增断言 ✅；迁移可重复执行 ✅；打桩下不产生真实外呼 ✅。

### cp-r002-3（房间管理页口径 + 交流页，完成）

| 文件 | 内容 |
| --- | --- |
| `src/api/livekit.ts`（新增） | `issueToken` / `kickMember` / `setMemberRole` / `transferHost` 四个调用 |
| `src/hooks/useRoomToken.ts`、`useRoomConnection.ts`、`useLocalDeviceState.ts`、`useChromeIdle.ts`（新增） | 取票 query（`staleTime: 0`）；连接状态机 `idle→connecting→connected⇄reconnecting→closed` 与 `DisconnectReason` 归因；设备状态记忆与重连重放；静默退场计时 |
| `src/hooks/useActiveSpeaker.ts`、`useOnlineIdentities.ts`（新增） | 说话者（单焦点）；在场 identity（抽屉「在线 / 离线」） |
| `src/components/live/{LiveStage,ParticipantTile,DeviceBar,RoomSidePanel}.tsx`（新增） | 单焦点舞台 + 窄缩格；格子（画面/头像块 + 姓名 + 角色徽标）；只图标 + tooltip 的控制条；默认收起的管理抽屉（成员 + 待批申请 + 房间信息 + 管理动作） |
| `src/pages/RoomLivePage.tsx`（新增） | 交流页：44px 状态条（标题 · 人数 · 房间码 · 连接徽标 · 抽屉开关）+ 舞台 + 悬浮控制条 + 焦点态；准入分流（401 登录 / 403 回管理页 / 409 已结束）；`livekitApplied=false` 时如实提示 |
| `src/pages/RoomDetailPage.tsx` | 口径改「房间管理页」+ 活跃成员看到「进入房间」（→ `/rooms/:id/live`）；展示从交流页回跳的提示 |
| `src/App.tsx` | 新增 `/rooms/:id/live` 路由；**交流页隐藏全局侧边栏与外层容器** |
| `src/styles/global.css` | 新增 r002 令牌（`--live-*`）与交流页样式、通用小组件（`.kicker/.panel/.icon-btn/.alert-warn/.spin/.member-row`）；`prefers-reduced-motion` 下降级 |

**实测证据（2026-09-18）**

- `npx tsc --noEmit` 全绿；`npm run build` 成功（`dist` 产出，bundle 900 KB——livekit-client 体积所致，属已知项）
- **真机端到端（浏览器，连 LiveKit Cloud）**：以 `host@example.com` 登录 → 打开 `/rooms/room_demo_epicurus/live` → 状态条显示「哲学共读… · 2 / 8 · HK7M2Q · 已连接」；舞台渲染 1 个焦点格（摄像头关 → 姓名首字头像块 + 房主徽标 + 麦关图标）；底部三个圆形控制按钮（麦克风 / 摄像头 / 离开）；`document.querySelectorAll('canvas').length === 0`（零装饰成立）；交流页底色 `rgb(5,6,10)`；全局侧边栏未渲染

**控制坞重设计（用户反馈「3 个按钮有点诡异」后）**

- 问题（用户视角 + 复看截图确认）：三个等形圆按钮并排，① 形状尺寸相同 → 「离开」与「静音」一样容易误触；② 只有颜色没有文字 → 状态不可读；③ 与全局侧边栏无关联的悬浮药丸像通用视频通话 chrome，和「专注感」方向相反；④ 提示文案原本压在控制条上。
- 改法：`DeviceBar` 重写为**控制坞**——左组设备（`[麦克风 + 三段电平]` `[摄像头 + 已开/已关]`）、中间分隔线、右组离场（描边、二次确认、不绑快捷键）；tooltip 带快捷键；`M`/`V`/`Esc`；关闭态用危险色 + 文字双表达；重连中禁用；房主「离开」禁用并说明原因；`.live-main` 加 76px 底内边距避免压住格子。
- 新增 `hooks/useMicLevel.ts`（≈12fps 采样 `localParticipant.audioLevel`，平滑下落）。
- 实测：`tsc --noEmit` 全绿；浏览器复看（host 连上 Cloud，状态条「已连接」）：控制坞显示 `麦克风[电平] | 摄像头 已关 | 离开`，提示行「M 静音 · V 摄像头 · 静默 30 秒后界面淡出」在其上方无重叠。

**其余按钮的功能设计（用户「思考其他按钮功能设计，然后保留」后）**

- 产出 `docs/02-modules/r002-livekit-features.md` **§4.6 按钮设计决策表**：把交流页/管理页现存与候选按钮逐条过一遍（功能是否必要 → 放哪 → 怎么展示 → 怎么提示 → 怎么防呆），结论分「保留 / 改 / 不做」三态；M3 能力（屏幕共享、举手、焦点、聊天）与 backlog（邀请、静音所有人、锁定房间）明确**不做且不留灰位**。
- 落地改动：① 抽屉成员行的裸图标 → 文字按钮（`移出` / `设为协管`·`取消协管`），**移交房主**收进「更多」菜单并写全「移交房主给 XXX」；② 抽屉新增显式「收起 ×」；③ 房间信息新增**复制房间码**（成功后文字变「已复制」）；④ 断开提示条的「重新进入」改「重新连接」；⑤ 抽屉宽度 320 → 380px + 行内按钮 `nowrap`（首版实测文字被挤成两行「取消协 / 管」，已修）。
- 实测：`tsc --noEmit` 全绿；浏览器复看（host 连上 Cloud、抽屉打开）：成员行 `陈慕 [协管] 离线 …… 移出 | 取消协管 | ⋯` 单行不换行，名称单行，抽屉头部有「成员与管理 + ×」，待处理申请显示空态「暂无待处理申请」。

**未完成（继续）**：等待页（cp-r002-4）、`403 → 等待页` 的分流改写、管理抽屉里的 toast/自绘 modal（等 `redirect-03` 批复）、两页的人工验收（cp-r002-5 演示脚本）。

## 无文档变更的提交（若有）

（实现期若某步确实无对外行为变化，在此登记一行并说明原因。）
