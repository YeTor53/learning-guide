---
title: r002 审查报告（阶段 3 定稿）
description: r002 的验收对账、规则核对、两轴文档对账、口径对账、CR 与重定向对账、两栏处置清单，以及收官事实与本次回填说明。
type: reference
status: approved
owner: 陀梓皓
updated: 2026-09-19
---

<!-- overview -->
阶段 3 的产物（**2026-09-19 由 r003 `cp-r003-1` 定稿**）：对照需求单逐条给证据、对照 `AGENTS.md` 与 `docs/04-style/` 核对规则、两轴文档对账、口径对账、CR 与重定向对账，并给用户两栏处置清单。
结论口径：**已过**（有可复现命令或实测记录）/ **未取证**（只能人工真跑，列入未闭合项）/ **欠账**（本轮已偿还或明确登记）。

## 1. 验收对账（需求单 §4 逐条）

| 验收块 | 证据 | 结论 |
| --- | --- | --- |
| 后端 · Token 契约（`test_livekit_token.py`：identity / name / video.room / roomJoin / roomAdmin 仅 Host / max_participants / TTL） | 需求单 §4.1 记录：`pytest backend/tests -q` → **95 passed**（r001 基线 72 + r002 23），含该文件的契约断言 | 已过（自动化） |
| 后端 · `POST /rooms/{id}/token` 四态（200 / 403 `NOT_MEMBER` / 409 `ROOM_ENDED` / 401） | 同上，`tests/test_rooms_members_api.py` 与 `test_rooms_api.py` 覆盖 | 已过（自动化） |
| 后端 · 签名不产生外呼（打桩后仍 200） | 同上（LiveKit 一律打桩，测试不联网） | 已过（自动化） |
| 后端 · 踢人 + 权限矩阵（协管互踢 403 / 踢房主 403 / 踢自己 400 / 非管理者 403） | `tests/test_rooms_members_api.py`（r002 新增 9 项之一） | 已过（自动化） |
| 后端 · 外部调用失败不回滚（`livekitApplied=false`，库内已改） | 同上（打桩抛异常用例） | 已过（自动化） |
| 后端 · 任命协管 / 移交房主（含活跃 Host 唯一并发断言） | `test_rooms_members_api.py` + `test_rooms_concurrency.py` + 迁移 `003_r002_host_uniqueness.sql` | 已过（自动化） |
| 后端 · 结束房间（r001 三件事 + 提交后调 `delete_room`，打桩断言被调用一次） | 同上；库侧连带动作另由 `smoke.py` 全链路覆盖 | 已过（自动化） |
| 后端 · 密钥检索（`git grep` 除 `config.py` 外无命中；`frontend/dist` 无 Secret） | **2026-09-19 实跑**：`git grep -nE "API_SECRET\|API_KEY" -- backend/app frontend/src` 仅 `backend/app/config.py`（:106/:128/:129/:132 变量名）；`frontend/dist` 扫描无命中；`.env` 未被 git 跟踪 | 已过（本轮实测） |
| 前端 · `tsc --noEmit` + `npm run build` | 需求单 §4.1 记录：全绿（构建产物不含已删页面） | 已过（2026-09-18 记录） |
| 前端 · 房内页四态 / 错误文案取自服务端 | 需求单 §4.1 记录：`/rooms/{id}` 重定向回列表、未知路径 404 卡片带出口 | 已过（部分为记录） |
| 前端 · 断开归因取 SDK `DisconnectReason` | 实现于 `hooks/useRoomConnection.ts`；浏览器实测记录：状态条 `已连接`、另开账号申请 5 秒内出现徽标与「门口有 1 位在等」 | 已过（自动化 + 实测记录） |
| 前端 · 断网重连（自动回房、显示「正在重连…」） | 需求单 §4.1 未做清单与 roadmap §9 台账：**未走人工断网复看** | **未取证** → 未闭合 §6 |
| 前端 · 设备状态保持（重连后仍关摄像头） | 同上（`useLocalDeviceState` 已实现，待实测 C-3） | **未取证** → 未闭合 §6 |
| 三页与情绪取向（交流页专注态 / 等待页温暖态） | 需求单 §4.1 记录：等待室暖色卡片 + 三步时间线 + 房间信息；双人同屏单焦点 + 右侧降权缩格截图 | 已过（实测记录） |
| 三页 · `prefers-reduced-motion` 降级 | 代码已实现（`--wait-breathe-duration` 降级、界面退场不位移）；**无实测截图** | 部分 → 未闭合 §6 |
| 页面收敛（`/rooms/:id` 消失、卡片四态动作、治理只在抽屉、建房直进交流页） | 需求单 §4.1 记录 + `redirect-06` 落地清单（tsc/build/浏览器复看） | 已过（实测记录） |
| 等候排队（申请不校验容量 / 批准不校验 / 取票时 409 `ROOM_FULL` / 批准即自动进入 / 有人离场后取票成功） | 单测覆盖容量与 409；浏览器实测记录「申请 5 秒内徽标 + 状态条提示」 | 部分（「批准即自动进入」与「离场后重进」未逐条留痕）→ 未闭合 §6 |
| 端到端人工 11 步（功能页 §6：声画互通 / 第 N+1 人拒绝 / 踢人真断 / 结束广播断开 / 移交互换按钮集） | 未走（脚本已备：`docs/tutorials/r002-livekit-demo.md` 九步/十一步版） | **未取证** → 未闭合 §6 |
| 冒烟 `smoke.py` 含 r002 四步 + `PASS n/n` | 实测 `PASS 22/22`，但**是 r001 的 22 项**：r002 四步未加（需求单 §4.1 自记） | 部分 → 未闭合 §6 |
| 教学页两页落地（使用者 `r002-livekit-demo.md`、开发者 `r002-livekit-dev-guide.md`） | 使用者页（另加 `r002-livekit-setup.md`）已落地；**开发者教学页当时未交付** | **欠账** → 本轮 `cp-r003-1` 已偿还（`docs/tutorials/r002-livekit-dev-guide.md`） |
| 覆盖矩阵无 `planned` 残留；README / AGENTS / roadmap 已回填 | 矩阵当时留 4 行 `planned`（B/C/D/F′）；README r002 行仍写 draft；roadmap §3/§7 三处矛盾 | **欠账** → 本轮 `cp-r003-1` 已偿还 |
| `git status --porcelain` 为空；每 cp 一提交一 tag | 工作区收官时干净；但 **`cp-r002-1` / `cp-r002-5` 未打 tag**（只有 2/3/4） | 欠账（未闭合 §6，待用户定：补打或接受） |

## 2. 规则核对（AGENTS.md / 风格指南）

| 规则 | 核对方式 | 结论 |
| --- | --- | --- |
| 未获批准不实现；每处改动挂在 `rNNN` | `git log` 内所有提交带 `[Req: r002]` | 已过 |
| 一次提交 = 一个逻辑增量；`git add` 具体路径；append-only | `c189a87..b8783d2` 共 40 个提交，无 amend/rebase/squash（`git log --graph` 单调） | 已过 |
| 分支与 tag 命名（`req/r002-livekit` / `cp-r002-N` / `round-r002-done`） | tag 实测：`cp-r002-2/3/4` + `round-r002-done`；**缺 `cp-r002-1`、`cp-r002-5`** | 部分（见 §6） |
| 合并由人执行（硬规矩 4） | `7f2e994 merge: r002 …`（`--no-ff`），`round-r002-done` 已打；`main` = `b8783d2` | 已过 |
| 密钥不入库 | 见 §1 密钥检索行 | 已过 |
| 文档与代码同一次提交 | 逐提交 diff：功能/实现/风格/教学页均随对应代码提交（`cbd9caf` 集中补文档，属收官提交，非后补） | 已过（有一处例外：开发者教学页漏写，见 §1） |
| 零 emoji / 单一图标库 Lucide / 文案用动词短语 | 代码扫描无 emoji、图标全部来自 `lucide-react` | 已过 |
| 界面硬条款（不用原生弹窗） | `redirect-03` 定死 r002 内新增交互用站内提示；实测 r001 遗留的 8 处原生弹窗仍在 `RoomDetailPage.tsx`（该文件已删）→ 现存量 0 | 已过（顺带被删除清掉） |

## 3. 文档对账（两轴 + 四件套 + 覆盖矩阵）

| 项 | 结论 |
| --- | --- |
| 设计页 | `docs/01-architecture/r002-realtime-architecture.md` 已落地 |
| 模块设计 + 实现同步页 | `docs/02-modules/r002-livekit.md`（变更记录 2026-09-18 三条）、`r002-livekit-features.md`（§8 变更记录）已随实现回填 |
| 使用者教学页 | `docs/tutorials/r002-livekit-setup.md`（从零跑起来）+ `r002-livekit-demo.md`（九步演示）→ 已落地 |
| 开发者教学页 | **本轮补齐**：`docs/tutorials/r002-livekit-dev-guide.md`（模块地图 / Token 策略 / 自助加能力 / 打桩排障 / 情绪令牌 / 实测坑） |
| 轮次轴 | `docs/rounds/r002-livekit/`：`design.md`、`changes.md`、`review.md`（本页）、`redirect-01..06` 齐；**新增 `redirect-07`**（房主缺结束入口，2026-09-19） |
| 索引 | `docs/00-requirements/README.md` r002 行已改为 `closed` + 完成 tag（本轮回填）；r003 行已加 |
| 覆盖矩阵 | 原 4 行 `planned`（B/C/D/F′）本轮全部转 `landed`（见需求单 §8） |
| 双轴互链 | 模块页「变更记录」有 r002 三条并回链轮次目录；轮次 `changes.md` 逐 cp 记录文件×锚点 |

## 4. 口径对账（外部服务）

- **Token 字段**：`video.room` / `roomJoin` / `roomAdmin` / `roomConfig.max_participants` 全部来自 LiveKit 官方 SDK 的 `VideoGrants` / `RoomConfiguration`，实现未自拟字段名（`services/livekit.py:48-63`），并由 `test_livekit_token.py` 解 JWT 断言 —— 已过。
- **撤销语义**：cloud 模式踢人显式传 `revoke_token_ts`（官方语义：按 Token `nbf` 判定，默认带 1 分钟缓冲），实现见 `services/livekit.py:95-98` —— 已过。
- **密钥口径**：`LIVEKIT_API_SECRET` 仅存在于 `.env` 与服务端进程；仓库、前端源码、前端产物、文档零命中（§1 检索行）—— 已过。
- **平台能力边界（如实登记）**：LiveKit 无「入房授权钩子」，应用层封禁名单做不了闭环（ADR-0011 条 10），已登记 backlog。

## 5. CR 与重定向对账

| 单号 | 类型 | 级别 | 结论 | 落地 |
| --- | --- | --- | --- | --- |
| `redirect-01` | 重定向（范围变更） | 按 L3 看待 | confirmed-C：断线重连 + 设备状态保持并入 r002 | `a818bf9` |
| `redirect-02` | 重定向（缺口记账） | — | superseded-G1（等候态升级为等待页，并入 `redirect-04`）；**G2（跨页通知）/ G3（队列）仍待批** | 未闭合 §6 |
| `redirect-03` | 重定向（提示口径） | — | **仍 `proposed`**（原生弹窗 8 处替换时机待你定）；r002 内新增交互已按「站内提示」口径定死 | 未闭合 §6 |
| `redirect-04` | 重定向（页面职责三分 + 情绪取向） | 按 L3 看待 | confirmed-B：`/rooms/:id/wait` + 交流页专注感落地 | `b041ac1` 起、`ab6f617` 完成 |
| `redirect-05` | 重定向（房间生命周期模型） | 按 L3 看待 | confirmed-A：房间 = 一场讨论（ADR-0012） | `5e4f02c` |
| `redirect-06` | 重定向（管理页去留） | 按 L3 看待 | confirmed-delete：删除 `/rooms/:id`（用户「删了吧」） | `ca73ad8`（**由此引出 `redirect-07` 的入口缺口**） |
| `redirect-07` | 重定向（实现偏差 A + 入口位置变更） | L3 | confirmed-A（2026-09-19），并入新轮次 `r003` | 见 `docs/rounds/r003-end-room-entry/changes.md` |

- 未闭合 CR：**无**（r002 期内未产生 CR 单：设计变更均以重定向单形式沉淀）。
- 滑行检查：`design.md`「本轮设计变更记录」与 `git log` 互核一致，diff 内无未登记的对外变化 —— 已过。

## 6. 留给用户的两栏处置清单

**本轮（r002）已落地且可保留的增量**（带 SHA 与文档页）

| 增量 | SHA | 文档页 |
| --- | --- | --- |
| LiveKit 接入模块 + Token 契约 + 配置必填 | `6875f0a` | `docs/02-modules/r002-livekit.md` §6 |
| 后端实时能力（取票 / 踢人 / 角色 / 移交 / 结束房间）+ 迁移 `003_r002_host_uniqueness.sql` + 偿还 r001 两条测试欠账 | `b91d0dd` | 同上 §5/§8 |
| 交流页（专注感：单焦点舞台 / 界面退场 / 零装饰）+ 控制坞重设计 | `1954e14`、`04b6903` | 功能页 §3 F-16、§4.5、风格指南 §12.1 |
| 等待室（温暖感）+ 申请/批准/取票三段口径 | `ab6f617` | 功能页 §4.7、ADR-0012 |
| 删除房间管理页（口径收敛） | `ca73ad8` | 术语表、功能页 §4.9、redirect-06 |
| 教学两页（使用者）+ 收官回填 | `cbd9caf` | `docs/tutorials/r002-livekit-{setup,demo}.md` |

**未闭合项 / 半成品**（各带「若判为 C 或 D 时的处置」）

| 未闭合项 | 现状 | 若判 C（后续工作） | 若判 D（方向变更） |
| --- | --- | --- | --- |
| 双浏览器人工 11 步演示未走 | 脚本已备（`docs/tutorials/r002-livekit-demo.md`） | 演示日一次跑完并勾选需求单 §4 | 演示脚本作废，重写验收方式 |
| 断网重连 / 设备保持 / reduced-motion 降级无实测留痕 | 代码已实现 | 归入 M3 首轮的人工验收一并走（或演示日补） | — |
| 「批准即自动进入 / 离场后取票成功」未逐条留痕 | 代码已实现，单测部分覆盖 | 同上 | — |
| `smoke.py` 未加 r002 四步（现 `PASS 22/22` 是 r001 项） | 已知 | M3 首轮补四步（成本约 30 行） | 若放弃脚本验收，改由单测覆盖即可 |
| `cp-r002-1` / `cp-r002-5` 未打 tag | 提交存在（建议 `7b95a6b` / `cbd9caf`） | 补打两个 tag（一行命令，不动历史） | 接受现状，在索引表注明「本轮 cp tag 不全」 |
| `redirect-03` 原生弹窗替换（仍 proposed） | 现有 0 处（文件已删），M3 起新增交互按站内提示口径 | M3 或交付前单独一轮 | 作废该单 |
| `redirect-02` 的 G2（跨页通知）/ G3（等候队列） | 记账 | M5（需推送通道） | 放弃，写明理由 |
| `ended` 房间回看载体（`redirect-06` 引出） | 列表页 `ended` 卡片无入口 | M4 纪要页 `/rooms/:id/summary` 承接 | 改为列表页只读面板 |
| 侧边栏「宽 < 高」样式缺陷 | 未复现、未归因 | 复现后单独修（先按视口 720×1024 实测） | 若判定为不可复现，从台账移除并写明 |
| 首页筛选条落在首屏之外（工具条） | 现象已确认，4 个候选修法已写 | 交付前选一个（推荐 A：筛选条上移到顶栏下方） | 不改，写明取舍 |

## 7. 收官事实（实测）

| 项 | 值 |
| --- | --- |
| 分支 | `req/r002-livekit`（保留，未删） |
| 合并提交 | `7f2e994`（`merge --no-ff`，由人执行） |
| 完成 tag | `round-r002-done` |
| `main` HEAD（收官后） | `b8783d2` |
| cp tag | `cp-r002-2` = `b91d0dd`、`cp-r002-3` = `1954e14`、`cp-r002-4` = `ab6f617`；**缺 1 / 5** |
| 变更规模 | 59 文件，+4059 / −449（含删除 `RoomDetailPage.tsx`） |
| 自动化证据 | `pytest 95 passed`、`smoke PASS 22/22`（r001 项）、`tsc` 全绿、`npm run build` 成功 |

## 8. 本次回填说明（2026-09-19，由 r003 `cp-r003-1` 执行）

- 本页原为骨架（`status: draft`，多行「待核」），现按**实测与仓库既有记录**定稿；凡无实测留痕的项如实标「未取证」并进 §6 未闭合清单，**不预勾未实测项**。
- 同一增量内一并处理：需求单转 `closed`、覆盖矩阵 4 行 `planned` → `landed`、索引表 r002 行回填、roadmap §3/§7 三处矛盾修正、开发者教学页补齐、删除 0 字节空文件 `docs/99-archive/end_room`。
- 触发依据：`docs/rounds/r002-livekit/redirect-07.md`（用户 2026-09-19「这个加入003，开始003」——r002 收官欠账并入 r003 首个增量偿还）。
