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

**交流页专注感加强（用户追问「这个音视频页的专注感呢」后）**

- 自评第一版：`单焦点 + 界面退场 + 零装饰` 只做到「减少干扰」，实测观感是**一块空黑 + 一个巨字**，读作"空"而不是"专注"。
- 补的四件事（写入功能页 §4.7「专注感的四个来源」）：① 暗角 + 顶部主题色光带 + 焦点格内发光 + 非焦点格改**右侧竖排**降权；② 头像改主题色渐变圆块，无摄像头时也能读，**说话给三圈渐隐声波**；③ 进房欢迎胶囊（3.2s 自动退场，建立启动边界）；④ 状态条右侧安静的**在房时长**（`00:12`，tabular-nums，不做倒计时）；反向要求：不加背景动画、不加装饰图层、不弹成功提示。
- 实测：`tsc --noEmit` 全绿；浏览器复看（host 连上 Cloud）：舞台出现暗角与顶部光带、焦点格上缘强调线、头像圆块带柔光、状态条右侧显示 `00:02` 计时、欢迎胶囊出现后自动淡出。
- **待双人验收**（cp-r002-5 双浏览器）：单焦点切换（说话者主格放大 / 其余降权）与声波脉冲需要第二个人说话才能看到，本轮单人无法自证。

**焦点格限幅 + 屏幕共享预留（用户报「开摄像头后焦点窗口过大」）**

- **真问题修复**：焦点格原为 `flex: 1`（无限撑大）。改为**按比例限幅居中**：`aspect-ratio: 16/9` + `max-height: calc(100vh - 250px)` + `object-fit: contain`（新增 `--live-focus-ratio`、`--live-focus-max-height`），舞台改 `align-items/justify-content: center`。任何窗口尺寸下焦点格都不再超过可视区。
- **屏幕共享（本轮不做，为 M3 铺路）**：功能页新增 §4.8「屏幕共享：可行性与布局预留」——焦点优先级已落为 **屏幕共享 > 说话者 > 自己**（`useTracks` 已同时订阅 `ScreenShare`），Token 的 `canPublish=true` 已允许发布共享轨（后端零改动）；共享的防呆要求与风险、M3 成本估算一并写入。

**抽屉与管理页的分工澄清 + 返回入口（用户追问后）**

- 用户指出两点：①「成员与管理」与管理页疑似冲突；②**没有返回管理页的方法**（此前只有房间标题是隐式链接，发现性为零）。
- 新增功能页 §4.9「管理抽屉与房间管理页的分工」：判定规则 = 在交流页点一下能做完的事不要求跳页（跳页 = 组件卸载 = 断开讨论）；「同一份信息两处维护」一律留在管理页。据此**删掉抽屉里的主题/简介段**（与管理页重复），只留一行「房间码 + 复制」。
- 状态条左侧新增**「← 房间管理」文字按钮**；**已连接/重连中点击先弹确认**（告知会断开当前讨论），未连接直接返回；`Esc` 可取消确认。
- 文档：功能页 §3 F-16 状态条规格同步、§4.6 按钮表新增该行。
- 实测：`tsc --noEmit` 全绿；浏览器复看状态条出现「← 房间管理」并承载返回动作。

**成员按「在不在房间内」分类（用户 2026-09-18 定）**

- 口径：**活跃 = 此刻在房间里**（LiveKit 在场）；**非活跃 = 不在房间内**（离线 / 已离开 / 被移出 / 房间结束）。与库里 `room_members.status` 的「成员身份」口径分开，写入术语表两条 + ADR-0011 条 **1a**（两套口径同源不同义，禁止混用成「成员数 = 在场数」）。
- 抽屉改为两组面板：`活跃（在房间里）· N` / `非活跃（不在房间内）· M`，行内 chip 标注「在房间里 / 不在房间」，副行只在**已不是成员**时写退出原因（原来 chip 与副行重复说同一件事，已去重）。
- 状态条人数改**在场口径**：`0 / 8 在房间`（第一版显示的是成员数 2/8，而房里只有 1 人，自相矛盾——用户指出的正是这个）。
- 顺手修：访客（未连接）时舞台不再渲染无名占位格，改为「还没有连上实时服务」空态。
- 实测：`tsc --noEmit` 全绿；浏览器复看抽屉两组面板与状态条「0 / 8 在房间」文案正确。

**未完成（继续）**：等待页（cp-r002-4）、`403 → 等待页` 的分流改写、管理抽屉里的 toast/自绘 modal（等 `redirect-03` 批复）、两页的人工验收（cp-r002-5 演示脚本）。

| `redirect-05.md` | 用户新意见（房间是否过度持久化） | 实现期，用户提「这样房间是不是更持久化了，跟初衷相互违背……这种持久化的方案和一次性会议式的方案都想一下，然后对比」 | A（**本轮口径变更**，按 L3 看待：动容量规则与验收表述；不改 schema） | **proposed（待批复）** | 定位 4 处病灶（容量按名册、界面主角错位、"成员"用词、房间不老化）；对比「一次性讨论（A）/ 常设小组（B）/ 现状混合（C）」；建议 A，列出 A-1~A-4 改动与 4 条待拍板口径 |

### cp-r002-4（等待室 + 申请/批准/取票三段口径落地，完成）

| 文件 | 内容 |
| --- | --- |
| `backend/app/services/rooms.py` | 删 `request_join` 与 `approve_join_request` 的容量拦截（ADR-0012 修订 D2/D3）；`issue_room_token` 增**在场口径**容量闸（D5）：`在场（不含自己）>= capacity` → 409 `ROOM_FULL`；LiveKit 查询失败降级放行，由 Token `max_participants` 兜底 |
| `backend/tests/test_rooms_service.py` | 两条用例改为新口径：`test_request_join_allowed_when_full`、`test_approve_allowed_when_full` |
| `backend/tests/test_rooms_concurrency.py` | 并发用例改为「同一申请并发批准只成功一次」（`CONFLICT` + `ok`），不再断言容量拦截 |
| `backend/tests/test_rooms_members_api.py` | 目标口径用例**转正**（原 xfail 去掉）：申请可提交 → 批准不拦 → 取票满员 409 → 有人离场后取票 200 |
| `src/hooks/useWaitingRoom.ts`、`src/components/WaitTimeline.tsx`、`src/pages/WaitingPage.tsx`（新增） | 等待室：状态机 + 三步时间线 + 温暖感卡片；**获批自动进入**（1.5s）不点按钮；失败/结束停留数秒**自动回主界面** |
| `src/pages/RoomDetailPage.tsx` | 按钮口径：在册成员「回到讨论」（重进）、待批者「去等待室」、申请成功**直接跳等待室**（加入流程无手动步骤） |
| `src/pages/RoomLivePage.tsx` | 403 `NOT_MEMBER` → 送等待室（不再当错误）；`ROOM_FULL` → 显示服务端原因 4 秒后自动回主界面 |
| `src/App.tsx` | 新增 `/rooms/:id/wait` 路由（等待室保留全局侧边栏） |
| `src/styles/global.css` | 等待室样式与温暖令牌（`--wait-warm` / `--wait-warm-soft` / `--wait-breathe-duration` / `--wait-autoenter-delay`）；`prefers-reduced-motion` 下呼吸光静止 |

**实测证据（2026-09-18）**

- `pytest backend/tests -q` → **95 passed**（含转正用例；r001 基线 72）
- `npx tsc --noEmit` 全绿
- 浏览器复看 `/rooms/room_demo_epicurus/wait`（访客态）：暖色卡片 + 三步时间线 + 房间信息（主题 / 房主 / 上限 8 人）+ 短句「这个房间还需要先申请」+ 操作「重新申请 / 回房间页」；未申请时时间线为中性色（不误点亮暖色）

**未完成（继续）**：cp-r002-5 冒烟 + 两篇教学页 + README/AGENTS/roadmap 回填 + 双浏览器人工验收（含单焦点切换、声波、踢人真断、满员第 N+1 人被拒、重连）。

| `docs/00-project/global-roadmap.md` | 遗留台账新增「侧边栏在宽小于长时样式出错」 | 实现期（你 2026-09-18 要求「加入代办」） | 仅登记，不改代码 | **登记中（未复现、未归因）** | 写明触发条件（视口宽 < 高）、未复现原因、复现与验收方式；不写猜测原因 |

**房内管理入口与申请可见性（你 2026-09-18 提三条）**

1. **「成员与管理」不明显** → 由裸图标改为**带文字按钮**；有待处理申请时改成**强调色填充 + 数量徽标**（`live-toggle-badge`）。
2. **音视频内看不到申请**（**真 bug**）→ 根因：`RoomLivePage` 里 `requests` 误取自 `detail.data.messages`（群聊消息）并强转 `as never`，抽屉里永远显示「暂无待处理申请」。改为独立查询 `GET /rooms/{id}/join-requests`（管理者才启用，5 秒轮询），批准/拒绝后立即失效重取。
3. **新申请没有通知** → ① 抽屉关着时状态条下方出现 `门口有 N 位在等房主批准 [去处理]`；② 新申请到达时按钮脉冲一次（2.4 秒，`prefers-reduced-motion` 下不动）；③ 抽屉区块标题显示 `待处理申请 · N`。**不弹窗、不 toast**（等 redirect-03 批复）。

**实测证据（真实浏览器，host 连上 Cloud，房间 `劳动与生产 XTFLN4`）**

- 另开账号提交申请后 5 秒内：`document.querySelector('.live-toggle-badge').textContent === "1"`、按钮带 `has-pending`、`.live-notice` 存在且含 1 个「去处理」按钮
- 同屏截图还顺带取到**双人现场**：房主格为主（上缘强调线 + 声波位）· 右侧竖排缩格里「陈慕（成员）」已降饱和降亮 → **单焦点 + 降权布局在真机上成立**（此前标为「待双人验收」，现已有截图证据；正式验收仍在 cp-r002-5 的演示脚本里走一遍）

| `redirect-06.md` | 用户新意见（管理页是否该移除 / 门口页的必要性） | 实现期，你提「思考管理页是否该移除，太重型了」→ 追问「这个门口页存在的必要性是什么」 | B′（**保留路由、降级为「房间信息 + 回访页」**；先成文待批） | **proposed（待批复，已按追问修订）** | 盘点：该页五项内容里三项与房内抽屉重叠（重型的来源），但「只读回访」与「未在册者落脚点」删不掉 → 四选项对比；**必要性复核后修正**：分享落点=弱、申请前了解房间=不成立（列表卡片 + 等待室已覆盖）、只有 `ended` 回访成立 → 不叫门口页，而是把 `/rooms/:id` 降级为「房间信息 + 回访页」；治理只在抽屉、发现只在列表、等待只在等待室；不删路由是因为要动 r001 已验收的 5 处演示点位 |

**删除房间管理页（`redirect-06` confirmed-delete，你 2026-09-18「删了吧」）**

| 面 | 改动 |
| --- | --- |
| 代码 | 删 `frontend/src/pages/RoomDetailPage.tsx`；`App.tsx` 去掉 `/rooms/:id` 路由（5 条：`/`、`/login`、`/register`、`/rooms/new`、`/rooms/:id/live`、`/rooms/:id/wait`）；`RoomCard` 重写动作区（在册「回到讨论」/ 待批「去等待室」/ 未申请「申请加入」→ 直接落等待室 / 已结束无动作，并把标题上的外链 `<Link to="/rooms/:id">` 去掉）；`NewRoomPage` 建房成功直接进交流页；交流页「← 房间管理」改「← 房间列表」（断开确认文案同步）；等待页「回房间页」改「回房间列表」 |
| 文档 | 术语表（删「房间管理页」、加「房间列表页」）；需求单 Q10b + 验收 4 条 + 变更记录；功能页页面口径/F-13/入口/§4.9/演示脚本第 13 步；实现页页面清单/路由/分流行/验证矩阵；风格指南页面表；架构页与 r001 需求单各追一行；`redirect-02/04/design` 顶部加追记（不改写历史结论）；`redirect-06` 转 confirmed-delete |
| 后端 | **0 改动**（所有接口保留，只是调用点变化）；`pytest 95 passed` 不变 |
| 收尾 | 旧分享链接 `/rooms/:id` 不再落空页 → 路由级 `<Navigate to="/" replace />` 重定向回列表；无匹配路由的兜底 404 给「回列表」出口；`NavBar` 面包屑细分（`/rooms/:id/live` → 房间交流、`/rooms/:id/wait` → 房间等待室，其余 `/rooms/*` → 房间） |
| 实测 | `npx tsc --noEmit` 全绿、`npm run build` 成功（构建产物不含已删页面）；浏览器复看：旧 URL `/rooms/room_d80fe9ff594f7f17` 落到房间列表（面包屑「房间列表」），列表页卡片出现「申请加入」按钮且标题不再是外链 |

## 无文档变更的提交（若有）

（实现期若某步确实无对外行为变化，在此登记一行并说明原因。）
