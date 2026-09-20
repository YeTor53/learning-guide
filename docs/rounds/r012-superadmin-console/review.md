---
title: r012 审查报告（定稿）
description: r012 的验收逐条对账（E1~E14 带实现位置与证据）、规则核对、覆盖矩阵、视觉对账五组、重定向对账与两栏处置清单、合并指引。
type: reference
status: draft
owner: 陀梓皓
updated: 2026-09-20
---

<!-- overview -->
分支 `req/r012-superadmin-console`（含 r011 全部提交）；实现 cp-1 ~ cp-7。本页只写**可复跑的判据**；未取证的一律标注原因，禁「已实现」空口。
门禁基线：`pytest backend/tests -q` → **200 passed**；`npx tsc --noEmit` exit 0；`npm run build` exit 0；迁移 `011` / `012` 已应用（`schema_migrations 12`）。

## 1. 验收逐条对账（E1~E14）

| # | 条目 | 实现位置 | 证据 | 结论 |
| --- | --- | --- | --- | --- |
| E1 | 超管身份落地 | `backend/app/db/sql/011_r012_superadmin_global_chat.sql`、`012_r012_seed_superadmin.sql`；`services/roles.py`；`repositories/users.py`；`schemas/auth.py::UserVO.role`；`scripts/grant_superadmin.py` | `db_init --seed` → `schema_migrations 12`、三张新表 0 行；`grant_superadmin --email host@example.com` → `user → superadmin（影响 1 行）`、`--revoke` → 反向；`/api/auth/me` 返回 `role`（用例 6 条）；真机登录后顶栏显示「平台管理员」 | **通过** |
| E2 | 隐身进房 | `services/rooms.py::issue_room_token`（超管分支）+ `services/livekit.py::issue_token`（hidden/attributes） | 用例：JWT `hidden=True`、`attributes={'lg-role':'superadmin'}`；`room_visits` 一条开启记录；房间详情 `memberCount` 不变、成员列表无超管。真机（应用内取票）：`status 200`，claims = hidden `true` / canPublish `false` / canPublishData `false` / roomAdmin 非真 / room 命中目标房。**真机交叉验证（cp-7b，可复跑）**：`python backend/scripts/verify_r012_superadmin_invisible.py` → **PASS 17/17**（两隔离 Chrome 152 / CDP 1.3，各登一个账号进同一间房）：成员端舞台 **1 格不变**（`tileNames=['林泽宇']`）、在册 **`2 / 8 成员` 前后一致**、成员抽屉（长度 116）**无「平台管理员」**；超管端徽标 **已连接**、chip「管理视角 · 隐身」、控制坞 `['管理视角 · 隐身','离开','结束房间']`、mic/cam/share/hand 全 false；**LiveKit 服务端** `list_participants`：`usr_demo_host` hidden=false/canPublish=true，`usr_demo_admin` **hidden=true / canPublish=false / canPublishData=false / attributes={'lg-role':'superadmin'} / tracks=[]**；该房 `room_members` 仍只有 host+mod（在册 2），超管只有一条 `room_visits`（hidden=true，脚本跑完自动 `close_room_visit` 关闭） | **通过（后端 + 应用内取票 + 双浏览器交叉验证 + LiveKit 服务端权限）** |
| E3 | 房主能力 | `assert_room_role` / `assert_manager_role` 两处超管旁路 | 用例：超管踢人与结束**他人**房间 200、房内系统消息落库、LiveKit 调用打桩命中；普通参与者同动作仍 403；超管可见他人房待批且列表 200 | **通过** |
| E4 | 不计入人数 | 超管不写 `room_members`（`room_visits` 旁路） | 用例：在册 8/8 时超管取票 200、取票前后 `memberCount` 恒 8；既有满员 409 用例全绿（未回归） | **通过** |
| E5 | 管理后台三列表 | `repositories/admin.py`、`services/admin.py`、`routers/admin.py` | 用例 9 条（三列表 + 审计 + 过滤 + 分页 + 鉴权矩阵）；真机 `/admin` 房间分区显示 **共 136 条**、表头 8 列与四分区 tab 正常（截图 `%TEMP%\lg_r012\cp7-admin-rooms.png`） | **通过** |
| E6 | 管理后台动作 + 审计 | `services/admin.py::end_room/delete_room/regenerate_summary` + `repositories/admin.py::insert_audit/get_room_snapshot` | 用例：结束他人房 200 + `room.end` 审计 + 房内「房间已结束」；硬删 200（`deleted/livekitApplied`）、房间行消失、消息级联 0、审计 `detail.snapshot.title/messageCount` 保留；重生纪要 201 + `room.summary_regenerate`；未知房 404 且不写审计 | **通过**（真机点击同一路径的界面在 cp-6 截图可见；未在真机上执行破坏性动作，避免污染你正在用的演示库） |
| E7 | 大屏聊天 | `repositories/global_chat.py`、`services/global_chat.py`、`routers/global_chat.py` | 用例：未登录可读 / 不可发（401）；正序 + `before_id` 游标；`authorOnline` 随心跳变；空串与 501 字 400、500 字 201；第 N+1 条 429 且落库条数 == 上限。真机：面板内发出一条并即时上屏（输入框计数归 0），在线点 1 个 | **通过** |
| E8 | SSE 通道与兜底 | `services/events.py`、`routers/events.py`、`hooks/useEventStream.ts` | 用例：路由存在、`text/event-stream` + `no-store` + `X-Accel-Buffering: no`、首帧 `retry: 3000`、publish → `event: notify` + `{type,payload}`、`: ping` 编码、订阅上限 503、**跨线程广播（新增回归用例）**。**真机跨客户端**：另一账号（host@example.com）经 HTTP 发言 → 浏览器面板**未刷新**即出现该条（SSE → invalidate → HTTP 拉真相）；修缺陷后复验：SSE 挂起中连发 3 条 → 3 帧到达且 `/api/auth/me` 仍 **0.02s** 返回 | **通过（含 cp-7 修缺陷后复验）** |
| E9 | 管理动作留痕 | 房内系统消息 + `admin_audit` | 用例断言同上；管理动作消息在房内聊天栏落库（`kind='system'`） | **通过** |
| E10 | 超管音频不进转写 | `agents/transcriber.py::_maybe_start`（`lg-role` 跳过）+ Token 无发布权限 | 代码事实 + 用例：超管 Token `canPublish=false`（无音频轨 → worker 的 `_has_audio` 已挡），`lg-role` 为双保险 | **代码侧通过**；真机（超管开麦 → 无转写）因「超管根本无发布权限」而**不可发生**，故不设真机项 |
| E11 | 门禁与视觉对账 | — | 台本逐项自检（cp-8b/8c）：`verify-runbook-ui.py` **PASS 28/28**（四角色文案控件）、`verify-runbook-flow.py` **PASS 18/18**（真浏览器跑 S2→S8 + 大屏跨端）；`pytest` **202 passed**；`tsc --noEmit` exit 0；`npm run build` exit 0（2022 modules，JS 984.19 kB / gzip 278.09 kB）；视觉五组见 §4 | **通过（视觉五组见 §4，其中降级复测为静态核对）** |
| E12 | 文档 = 代码 | 需求单 / design / changes / review；模块实现页 + 功能页；教学两页；`04-style` §12.4；ADR-0024/0025 | 覆盖矩阵无 `planned` 残留（§3）；教学两页已落并有索引行 | **通过** |
| E13 | 超管只管理、不发布 | `issue_room_token` 超管分支；`DeviceBar.superadminMode`；`useLocalDeviceState(publishDevices=false)` | 应用内取票 claims：`canPublish=false` / `canPublishData=false` / `roomAdmin` 非真；真机交流页：控制坞只有「管理视角 · 隐身」+「离开 / 结束房间」，**无**麦克风 / 摄像头 / 共享 / 举手控件（截图 `%TEMP%\lg_r012\cp7-superadmin-room.png`）；**LiveKit 服务端**该参与者 `canPublish=false / canPublishData=false / hidden=true / tracks=[]`——媒体层也发不出去 | **通过** |
| E14 | 在线心跳 | `routers/presence.py`、`services/presence.py`、`hooks/usePresenceBeat.ts` | 用例 4 条（未登录 401 / 上报后 `last_seen_at` 前进且计入 `online_user_ids` / 600 秒前的判离线 / 纯函数窗口）；真机：面板「1 人在线」与绿点随心跳正确显示 | **通过** |

## 2. 规则核对（AGENTS.md / docs/04-style/）

| 项 | 结论 | 证据 |
| --- | --- | --- |
| 未获批准的规划不做实现 | 通过 | cp-1/cp-1b/cp-1c 全为文档；第一行代码在用户回「开始」之后的 cp-2 |
| 一次提交 = 一个逻辑增量、`[Req: rNNN]` | 通过 | `git log --oneline` 每行带 `[Req: r012]`（交接提交标 `[Req: r011]`） |
| `git add` 只写具体路径 | 通过 | 每次提交逐路径 `git add -- <paths>`；工作区其它会话的在制品未被卷入 |
| 无 amend / rebase | 通过 | cp-4 漏登记文件时用 **cp-4b 补交**而不是 amend |
| 密钥不入库 / Secret 不进前端产物 | 通过 | `git grep -nE "API_SECRET|API_KEY" -- backend/app frontend/src` 命中 8 行**全为键名/变量名/文案**（config.py 变量名 + stt/summary 报错文案 + 纪要页提示），本轮新增 0 |
| 未新增依赖 | 通过 | `git diff --stat -- frontend/package.json backend/requirements*.txt` = 空 |
| 界面硬条款（单一图标库 / 零 emoji / 禁内部词） | 通过 | emoji 扫描 0；图标库扫描 0；新增界面文案无「轮次/里程碑/cp-NNN」等内部词（人工核对 `GlobalChatDrawer` / `AdminPage` / 表格组件） |
| 观察：并行会话的改动 | 已登记 | 另一会话在 `NavBar.tsx` / `SideBar.tsx` 的未提交改动，先落为独立交接提交 `fa7b7d1`（`[Req: r011]`），再在其上做 cp-6 |

## 3. 覆盖矩阵对账（无 `planned` 残留）

| 件套 | 路径 | 状态 |
| --- | --- | --- |
| 需求单 | `docs/00-requirements/r012-superadmin-console.md` | 本轮（cp-1，§10.1 批复） |
| 设计页 | `docs/rounds/r012-superadmin-console/design.md` | 本轮（cp-1 v1，cp-1b v2） |
| 台账 | `docs/rounds/r012-superadmin-console/changes.md` | cp-1 起逐格填 |
| 审查 | 本页 | 定稿（cp-7） |
| 模块·实现页 | `docs/02-modules/r012-superadmin-console.md` | landed（cp-2 → cp-6 五次追加） |
| 模块·功能页 | `docs/02-modules/r012-superadmin-console-features.md` | landed（cp-6） |
| 使用者教学页 | `docs/tutorials/r012-admin-and-global-chat.md` | landed（cp-6） |
| 开发者教学页 | `docs/tutorials/r012-superadmin-dev-guide.md` | landed（cp-6） |
| ADR | `docs/03-decisions/ADR-0024-superadmin-invisible-bypass.md`、`ADR-0025-global-chat-and-sse.md` | 两个均 landed（cp-2 / cp-5） |
| 风格条目 | `docs/04-style/global-style.md` §12.4 | landed（cp-6） |
| 轮次索引 | `docs/00-requirements/README.md` r012 行 | 已加（cp-1） |

## 4. 视觉对账（五组 + 实测数字）

| 项 | 命令 / 做法 | 实测 | 结论 |
| --- | --- | --- | --- |
| 令牌扫描 | 对 cp-6 涉及的 17 个前端文件正则扫 `#hex` / `padding|margin|gap|font-size|border-radius: Npx`（排除 `global.css` 参数区） | **命中 0** | 通过 |
| 动效实测 | 真机读 `getComputedStyle`：收起态 `transform: matrix(1,0,0,1,376,0)`、展开态 `matrix(1,0,0,1,0,0)`、`transition-property: transform, opacity`、`transition-duration: 0.24s` | 位移 376px = 面板宽 360（`--gc-w`）+ 偏移 16（`--gc-offset`），**与算式一致**；时长 0.24s = `--t-base` | 通过 |
| 降级复测 | CDP `Emulation.setEmulatedMedia(prefers-reduced-motion=reduce)` 真机强制模拟（`verify_r012_superadmin_invisible.py` 第 ⑤ 步） | 常规：`transition-property: transform, opacity` / **0.24s**，收起态 `translateX(376px)`、展开态 `0`；强制 reduce 后：`transition-property: **none**` / `1e-06s`，`matchMedia('(prefers-reduced-motion: reduce)')` = **true**，点击收起后 **200ms 内**已到位、再点开后 **150ms 内**已到位（无位移过渡） | **通过（真机强制模拟）** |
| 截图 | 桌面（工具浏览器 1243×约 1000） | 3 张落 `%TEMP%\lg_r012\`：`cp7-admin-rooms.png`、`cp7-admin-with-global-panel.png`、`cp7-superadmin-room.png`（**截图按仓库惯例不入库**，与 r004~r010 的 `%TEMP%\lg_rXXX` 一致） | 通过 |
| 零 emoji / 单一图标库 | `git grep` emoji 区间 / `react-icons|@heroicons|fontawesome|feather` | 均 **0 命中** | 通过 |
| 几何量测 | `document.documentElement.scrollWidth === clientWidth`；后台表格容器 `scrollWidth/clientWidth` | 页面 1243/1243；表格容器 1070/1070（**无横向溢出**）；面板展开时主内容未被遮挡（面板 `position: fixed` 右侧） | 通过 |

### 4.0 台本逐项自检（cp-8b/8c，三份脚本）

| 脚本 | 覆盖 | 实测 |
| --- | --- | --- |
| `backend/scripts/verify_r012_superadmin_invisible.py` | 超管隐身交叉验证（两隔离 Chrome + LiveKit 服务端参与者权限）+ reduced-motion 强制模拟 | **PASS 17/17** |
| `frontend/scripts/verify-runbook-ui.py` | 台本点名的**按钮与文案**：未登录 / 房主 / 参与者 / 超管四角色（含后台八列表头、三动作、删除二次确认、超管只读控制坞） | **PASS 28/28** |
| `frontend/scripts/verify-runbook-flow.py` | 台本**行为流**：建房 → 申请 → 批准自动进房 → 群聊 → 举手给焦点 → 邀请码 → 移出 → 结束 → 大屏跨端 | **PASS 18/18** |

台本自检顺带修掉 3 个真缺陷：交流页「大屏」按钮无动作（cp-8）、**SSE 订阅占满连接池**（cp-8b，9 条流打满整站）、
**系统消息只有 F5 才出现**（cp-8c）。另用超管 `DELETE /api/admin/rooms/{id}` 真机删掉一个测试房：返回 `{deleted: true, livekitApplied: false}` 且 `admin_audit` 落一条 `room.delete`（E10 的删除动作由此获得真实执行证据）。

## 4.1 真机交叉验证怎么复跑（cp-7b 新增）

一条命令（先 `dev.bat` 起 8000 + 5173）：

```
python backend/scripts/verify_r012_superadmin_invisible.py            # 全跑：隐身交叉验证 + reduced-motion
python backend/scripts/verify_r012_superadmin_invisible.py --skip-media --keep-chrome   # 只验隐身 / 保留浏览器排障
```

脚本自己做的事：起两个**隔离** Chrome（`--user-data-dir` 在 `%TEMP%\lg_r012_verify\`，`--mute-audio`，不碰你正在用的浏览器）→
成员端（`host@example.com`）进房取基线 → 超管端（`admin@example.com`）进同一间房 → 成员端复看（舞台格数 / 在册人数 / 成员抽屉）→
**LiveKit 服务端 API** 读参与者权限 → CDP 强制 reduced-motion 量测 → 关掉自己造的 `room_visits` → `Browser.close` 两个浏览器。
判据 17 条，末尾打印 `PASS n/n`；任一条不符非 0 退出。零新依赖（`websockets` 环境已有 + 本机 Chrome）。

## 5. 重定向对账（vibecoding 8.1/8.2）

| 消息序号 | 用户原话摘要 | 首行回执分类 | 单号 | 处置 |
| --- | --- | --- | --- | --- |
| 1 | 「设计LearnGuide项目的r012」 | 新轮次设计请求 | —（沿用 `redirect-01`） | 出阶段 1 文档（cp-1）+ `ASK-r012-1` |
| 2 | 18 位数字 + 「…超管不能说话和视频，只能管理！」「右侧的侧栏…coplit」「只 admin 可见」「短轮询」 | 澄清回答（W2） | — | 批复落需求单 §10.1；按批改写设计（cp-1b/1c） |
| 3 | 「开始」 | 批准（W1） | — | 从 cp-2 起实现 |
| 4 | 「？」 | 补充事实/状态问询（W3） | — | 回报「SSE 用例挂死 280 秒」并当场改为驱动响应生成器（cp-5 台账已记） |
| 5 | 「2」 | 批准（W1，选方案 2） | — | 先落盘并行会话的未提交改动（`fa7b7d1`）再做 cp-6 |

无悬空 `proposed` 单据；`redirect-01` 的 Q1~Q8 已由 `ASK-r012-1` 统一收口并全部落地。

## 6. 两栏处置清单（交你复核）

**A. 本轮已落地、可保留的增量**

| 增量 | 提交 | 文档页 |
| --- | --- | --- |
| 阶段 1 文档 + 批复登记 | `0192e25` / `7ef754d` / `059bb40` | 需求单、design |
| 迁移 011/012 + 身份 + 在线心跳 | `1dddb98`（+ `13e5834` 补交） | 实现页 §1/§2、ADR-0024 |
| 超管隐身进房 + 旁路治理 | `6051756` | 实现页 §3、ADR-0024 |
| 管理后台后端 | `6051756`（同提交） | 实现页 §4 |
| 大屏聊天 + SSE | `2e84ab5` | 实现页 §5、ADR-0025 |
| 前端（后台页 / 右侧大屏 / 超管视角 / 教学两页） | `a10c5a7` | 实现页 §6、功能页、教学两页、04-style §12.4 |
| （并行会话的 r011 前端改动，随本分支落盘） | `fa7b7d1` | r011 侧文档 |

**B. 未闭合清单（含若判 C/D 时的处置）**

| # | 未闭合项 | 原因 | 建议处置 |
| --- | --- | --- | --- |
| ~~①~~ | ~~超管隐身的双浏览器交叉验证~~ | **已闭合（cp-7b）**：改用 CDP 起两个隔离 Chrome（各自 `--user-data-dir`），成员端 DOM + LiveKit 服务端 API 双侧取证 | 证据见 §1 E2 与 §4.1；复跑一条命令，`PASS 17/17` |
| ~~②~~ | ~~`prefers-reduced-motion` 强制模拟~~ | **已闭合（cp-7b）**：CDP `Emulation.setEmulatedMedia` 可精确强制该偏好（原来的工具浏览器不支持，被误当成「做不了」） | 量测数字见 §4；同一脚本第 ⑤ 步 |
| ③ | 大屏面板在**交流页不挂** | 设计决定（交流页已有右抽屉，避免双抽屉）；需求单 §10.1 已写明「要的话说一声」 | 若要，改成既有抽屉的第四个 tab（小增量，走 L1/L2） |
| ④ | 演示库残留 | 你 2026-09-20 口径「开发结束后统一清」 | 收工后执行一次 `db_init --reset --seed`（会重建 `admin@example.com` 超管） |
| ⑤ | SSE 单进程限制（多进程会漏事件） | ADR-0025 D4 已如实登记 | 上 Docker/多副本前先换 Redis pub/sub（登记为后续轮次候选） |
| ⑨ | ~~系统消息不实时进房内讨论流~~ | **已闭合（cp-8c）**：真机实测「批准/邀请码加入/移出后系统消息已入库但抽屉 20 秒不出现，只有 F5 才出现」→ 根因是系统消息无人广播（发送方广播只覆盖聊天消息）。修法：`useChatMessages.refresh()` 对近 30 秒新出现的系统消息补广播 + 治理动作后连带 `chat.refresh()`；`verify-runbook-flow.py` 16/18 → **PASS 18/18** | 台本逐项自检发现（台本 S3/S7/S8 判据原本不成立） |
| ⑧ | ~~SSE 订阅占满数据库连接池~~ | **已闭合（cp-8b）**：真机复现「9 条流 → 普通接口 30 秒后 500（`PoolTimeout`）」，修掉 SSE 路由的 DB 依赖；修复后 12 条流挂着仍 200 / 0.02s。守卫：`test_events_route_must_not_depend_on_db` + smoke 一步 | 台本逐项自检时发现（后端日志 46 次 500） |
| ⑦ | ~~交流页顶栏「大屏」按钮点了没反应~~ | **已闭合（cp-8）**：交流页按设计不挂大屏面板，但按钮照渲染 → 有反馈无动作。修法：`App.tsx` 在交流页不传 `onToggleChat`；CDP 真机复核（交流页 `hasChatBtn=false`、列表页 `true`） | 台本 S11 写这段时发现；`tsc`/`build` 绿 |
| ⑥ | ~~跨线程广播卡死事件循环~~ | **已在 cp-7 修复**（真机踩到：订阅者挂起时同步端点直接 `put_nowait` → 8000 整机无响应） | 修法见 ADR-0025 D6 + 实现页 §5.1；回归用例 `test_publish_from_sync_endpoint_thread_wakes_waiting_subscriber`；真机复验通过 |

## 7. 合并指引（人执行）

1. 先合 r011（若尚未合并）：`git checkout main && git merge --no-ff req/r011-debt-backfill` → 打 `round-r011-done`。
2. 再合 r012：`git merge --no-ff req/r012-superadmin-console` → 打 `round-r012-done`（本分支已含 r011 全部提交，先合 r011 可让第二步成为快进式合并）。
3. 合并后复跑门禁四项（`pytest` / `smoke` / `tsc` / `build`），把数字回填本页 §1 与 `changes.md` §3。
4. 合并前建议先跑一次教学页 §3 的双浏览器隐身脚本（未闭合 ①）。

## 8. 变更记录

| 日期 | 版本 | 改了什么 | 依据 |
| --- | --- | --- | --- |
| 2026-09-20 | 骨架（cp-1） | 建页：验收对账表 + 规则核对 + 矩阵对账 + 视觉五组 + 重定向对账 + 两栏位 + 合并指引 | 需求单 §4/§8 |
| 2026-09-20 | 定稿补跑（cp-7b） | 未闭合 ①② 用 CDP 真机取证闭合：新增可复跑脚本 `backend/scripts/verify_r012_superadmin_invisible.py`（17 条判据，PASS 17/17），E2/E13 补 LiveKit 服务端权限证据，§4 降级复测从「静态核对」升为「真机强制模拟」，新增 §4.1 复跑方法 | 你 2026-09-20「1」放行 |
| 2026-09-20 | 定稿（cp-7） | 逐格填 E1~E14 证据（用例 + 真机数字 + 三张截图）、规则核对、矩阵落地、视觉五组实测、重定向对账（5 条用户消息）、两栏清单与合并指引 | 本轮 cp-2~cp-7 实跑输出 |
