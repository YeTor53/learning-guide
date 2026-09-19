---
title: r004 审查报告（阶段 3 用）
description: r004 的验收对账、规则核对、两轴文档对账、CR 与重定向对账、视觉对账、两栏处置清单与合并指引（收官时定稿）。
type: reference
status: draft
owner: 陀梓皓
updated: 2026-09-19
---

<!-- overview -->
阶段 3 的产物：对照需求单 §5 的 **A/B/C/D 四组（E1~E23，编号稳定）** 逐条给证据、规则核对、两轴文档对账、CR 与重定向对账、视觉对账，并给用户两栏处置清单。**收官前本页为骨架。**

## 1. 验收对账（需求单 §5 的 A/B/C/D 四组）

| 条目 | 实现位置 | 证据 | 结论 |
| --- | --- | --- | --- |
| A 组 E1~E6（后端接口与连带） | `db/sql/004_*`、`repositories/room_extras.py`、`services/{messages,hands,focus}.py`、`api/routers/room_extras.py`、`services/rooms.py:end_room` 连带 | `pytest` **105 passed**（+10）；`smoke` **29/29**；`db_init` 应用 003+004（`schema_migrations=4`）；活服务探针 9/9（201/200/409 与 trim、幂等、快照、留痕齐）；实现页 §7 逐条对账 | **通过**（E1~E6 全绿） |
| B 组 E7（tsc / build） | 前端实时层 cp-5 | `tsc` exit 0；`build` exit 0（1978 模块）；产物 `__lgRoom` 0 命中 | **通过** |
| B 组 E8~E14（双浏览器功能与优先级） | `stageLayout.ts`、`LiveStage`、`ChatPanel`/`MessageBubble`/`FocusBadge`、`RoomSidePanel`、`DeviceBar`、`RoomLivePage`、`global.css` | Playwright 双上下文 + 三个额外成员上下文实测：群聊双端逐字一致、刷新与库一致（3=3）、举手/焦点双端一致、共享徽标与 3px 上缘线、协作式停共享生效、5 人时 rail=double 且缩格恒 176×99、reduced-motion 生效 | **通过**（E12 的「共享中说话不夺焦点」与竖屏横条量测留 cp-7） |
| B 组 E18a（事件注入级） | `hooks/useRoomConnection.ts` 的事件接线 | 注入 `disconnected` 数值枚举：`4 PARTICIPANT_REMOVED` → 「你已被移出房间」、`5 ROOM_DELETED` → 「房间已结束」、`2 DUPLICATE_IDENTITY` → 「同一账号已在别处进入本房间」、`1 CLIENT_INITIATED` → 无提示（自己离开不打扰）；说话者用 `activeSpeakersChanged` 注入验证优先级（见 §1 E22 行） | **通过**（事件注入级，已标明等级） |
| B 组 E18b（真实中断级） | 未做到 | 试了两种真断手段都不成立：① Playwright `set_offline` 在 8 秒断网窗口内**没有**让 SDK 进入重连态（恢复后才判定），恢复后落到「已断开」而非自动回房 ② 本地自建 `livekit-server` 未搭（本轮不做）。**结论：E18b 未完成**，不拿注入级冒充 | **未做到（如实）** |
| B 组 E18c（物理断网 8 秒） | 载体已交付：仓库根 `reconnect-drill.bat`（GBK+CRLF，双窗口对练提示 + 8 秒倒计时 + 四项回填清单；不碰系统设置） | **需你点两下 Wi-Fi**：双击 `reconnect-drill.bat` → 关 Wi-Fi 8 秒 → 开回来 → 把四项观察回填本行 | **待你演练** |
| 顺带修的真缺陷 | `hooks/useRoomConnection.ts` | 原先只接 `Reconnecting/Reconnected`，**信号级中断（WS 掉线）不进 `reconnecting`** → 断网时状态条仍显示「已连接」、按钮不禁用（与 r002 §8.9 契约不符）。补 `RoomEvent.SignalReconnecting` → `reconnecting`（SDK 文档口径：该事件后续由 `Reconnected` 收尾） | **已修**（离线模拟下该事件未在窗口内触发，故「断网 1~3 秒可见」仍需 E18c 实测） |
| C 组 E15（两项界面缺陷） | `RoomsPage.tsx`（工具栏上移）、`App.tsx`+`SideBar.tsx`+`hooks/useNarrowStrip.ts`、`global.css`（竖屏块 + 窄屏一行） | `toolbar.top 639 → 101`（视口 1258×566，`bottom=146 ≤ 522` 口径）；竖屏/窄屏 700×1000、820×1180、1000×1200 三档实拍（改前/改后）；`scrollWidth 1243 ≤ 1258` 无横向溢出；tsc exit 0、build exit 0 | **通过**（竖屏为视觉证据，待你真机复看） |
| C 组 E21 尺寸阶梯 | `components/live/stageLayout.ts` + `global.css` 的四种 rail 模式 | 同一房间逐档加到 2/4/6/8 人（新房 `room_af43e343f766fb76`，抽屉关闭，1440×900）：1 格 176×99 / 3 格 176×99 / 5 格 176×99 双列 / 7 格 176×99 三列；焦点格 1156×650 → 1156×650 → 1016×572 → 828×466；四档均 `overflow=0`（截图 `ladderB-2/4/6/8.png`）。**口径折算**：E21 原写「2/4/6/8 人 → 列数 1/2/2/3」，按 design §7.4 的 k（在线的非焦点人数：1/3/5/7）折算应为 1/1/2/3，实测与 design 一致；需求单措辞按人数粗写，以实现页与 design 为准 | **通过** |
| C 组 E22 焦点易手 | `stageLayout.ts`（一次性算出）+ `global.css` 过渡 | `.live-focus-slot` 计算过渡时长 **0.24s / 0.24s**；给第 1 位成员焦点 → 再切给第 2 位，`window.__node.isConnected` 两次均为 **true**（DOM 未重挂载）；8 人时给「阶梯成员1」焦点 → **对端徽标「焦点 · 你」**、对端状态条「焦点 阶梯成员1」、本端「焦点 · 阶梯成员1」（截图 `focusB-8people.png` / `focusB-member1.png`） | **通过** |
| C 组 E23 窄屏与竖屏 | `stageLayout.ts` 的 `portrait` 分支 + `.live-stage-strip` | 720×1024（8 人在线）：`live-stage-strip` + `live-rail-strip`，7 格分 3 行（rail 672×321），焦点格 **672×378（≥320 ✓）**，`overflow=0`；900×600：strip，rail 852×210（2 行），焦点格 **622×350**，`overflow=0`；对照 1258×566：非竖屏且挤得下 → `triple`（焦点格 562 ≥ 480 ✓）。**过程记录**：第一次量测忘关抽屉（抽屉占 360px）→ 缩格挤成 1 列、焦点掉到 280px，看着像布局 bug；关掉抽屉复测正常，已写进开发者教学页的坑清单 | **通过** |
| D 组 E16 pytest | `backend/tests/test_room_extras_api.py`（10 个用例） | `conda run -n learningguide python -m pytest backend/tests -q` → **105 passed**（r003 基线 95 + 本轮 10） | **通过** |
| D 组 E17 smoke | `backend/scripts/smoke.py`（补 r004 三步） | 实测 **PASS 36/36**（原 29/29 → 新增：发消息 201 且 trim、空消息 400、拉消息含新条、举手两次仍 1 条、自己放下清空、房主设焦点回传 subject、取消焦点为空） | **通过** |
| D 组 E19 文档对账 | 全轮文档 | 功能页 F-18~F-22 / 实现页 §1~§11 / 架构增量页（cp-1）/ ADR-0013/0014/0015 / 教学页两篇 / README / roadmap / 索引 / 术语表 / 风格指南 §12.3 全部与代码一致；覆盖矩阵无 `planned` 残留（见 design §13 更新） | **通过** |
| D 组 E20 r003 收官回填 | cp-2 | 索引表 r003 行转 `closed`、需求单转 `closed`、roadmap §7 标完成 + §9 台账（合并提交 `694caeb`、cp tag 1/2/3） | **通过** |

## 2. 规则核对（AGENTS.md / 风格指南）

| 规则 | 核对方式 | 结论 |
| --- | --- | --- |
| 未批不实现；每处改动挂 `rNNN` | 7 个提交全部带 `[Req: r004]`；每个 cp 都等用户批复后才开工 | **通过** |
| 一次提交一个逻辑增量；`git add` 具体路径；append-only | `git log`：cp-2~cp-7 各一个提交，`git add` 只列具体文件；已收官页只追加指路行 | **通过** |
| 零新依赖、不改端口与运行形态 | `package.json` / `requirements*.txt` 无变化；`dev.bat` 未改（端口仍 8000/5173） | **通过** |
| 密钥不入库 | `git grep -nE "sk-|LIVEKIT_API_SECRET|password"` 仅命中用例里的演示口令与文档占位 | **通过** |
| 文档与代码同一次提交 | 每个 cp 的提交都含对应文档（实现页 / 功能页 / 需求单 / changes / review） | **通过** |
| 零 emoji / 单一图标库 Lucide | 新增组件只用 `lucide-react`（Crosshair / MonitorUp / Hand），无 emoji | **通过** |

## 3. 文档对账（两轴 + 四件套 + 覆盖矩阵）

| 项 | 结论 |
| --- | --- |
| 模块轴：设计页（design）/ 模块页（实现页 `r004-room-extras.md` + 功能页 `r004-room-extras-features.md`）/ 使用者教学页（`tutorials/r004-room-extras-demo.md`）/ 开发者教学页（`tutorials/r002-livekit-dev-guide.md` 补 §7~§8） | **齐** |
| 轮次轴：`docs/rounds/r004-room-extras/` 三件套 + 架构增量页 + ADR-0013/0014/0015 | **齐** |
| 索引 + 模块页变更记录 + 术语表 | `docs/00-requirements/README.md` r004 行、实现页 §8、功能页变更、术语表 4 条 | **齐** |
| 覆盖矩阵无 `planned` 残留 | design §13 已更新为实际状态 | **齐** |

## 4. 重定向与 CR 对账

| 单号 | 类型 | 级别 | 结论 | 落地 |
| --- | --- | --- | --- | --- |
| cp-4-1~cp-4-5 | 实现期变更 | L1/L2 | 已采纳（见 design §14） | 实现页 §1/§3/§6 |
| cp-7-1 | 实现期变更 | L2 | `useRoomConnection` 补 `RoomEvent.SignalReconnecting` → `reconnecting`（修「信号级掉线时 UI 不显示重连」） | `frontend/src/hooks/useRoomConnection.ts` |
| 未决 | 待实测 | — | 服务端强停共享（design §6.1）本轮按协作式实现；若后续要强停需另开轮次 | 功能页 F-21 / design §6.2 |

- CR 预期候选：design §6.1 的「服务端强停共享」实测结果（若降级影响对外可见面 → 补 CR）；焦点优先级若被推翻 → ADR-0014 变更。
- 滑行检查：`design.md` §14 与本表、与 `git log` 三方互核。

## 5. 视觉对账（界面类项目）

| 组 | 方式 | 结果 |
| --- | --- | --- |
| 令牌扫描 | `git grep` 令牌名 | 定义在 `global.css`（`:root`，14 项）与风格指南 §12.3；组件只引用不硬编码色值 | **通过** |
| 零 emoji / 单一图标库 | `frontend/src` 扫描 | 新组件仅用 Lucide 图标 | **通过** |
| 桌面 + 窄屏截图 | Playwright 真机（5173/8000） | `ladderB-2/4/6/8.png`、`narrowB-720x1024.png`、`narrowB-900x600.png`、`focusB-8people.png`、`run-A-focus.png`、`share-3px-line.png`（`%TEMP%\lg_cp6`、`%TEMP%\lg_cp7`） | **通过** |
| 动效降级 | `reduced_motion=reduce` 模拟 | 焦点格 `::before` 与聊天气泡 `animation-name = none`；cp-3 的 hero/窄屏降级沿用 | **通过** |
| 几何量测 | 缩格恒 176×99（四档实测）；共享格上缘线 3px；焦点/共享徽标高 24px 级；控制坞新按钮沿用既有尺寸 | **通过**（徽标高度为设计值，未单独量测） |

## 6. 留给用户的两栏处置清单

**本轮已落地可保留的增量（提议保留）**

1. 后端：迁移 `004`（举手/焦点两表）+ 三条 service + 8 条路由 + `end_room` 连带清举手（`pytest` 105 全绿、`smoke` 36/36）。
2. 迁移工具修复：`split_statements` 过滤事务控制语句，修掉 `003_` 迁移「建了索引不记版本、每次迁移都中止」的遗留问题。
3. 前端实时层与界面：Data Channel 加速层（ADR-0013）、四个状态 hook、`stageLayout` 单一布局事实源、讨论区、抽屉双 tab、控制坞举手/共享、§8.9 令牌全表。
4. 两项界面缺陷修复（cp-3）：首页筛选条进首屏、窄屏侧边栏折叠状态穿越断点的问题 + ADR-0015。
5. 文档：实现页 / 功能页 / 三份 ADR / 使用者与开发者教学页 / 风格指南 §12.3 / 术语表。
6. `reconnect-drill.bat`：把「物理断网 8 秒」这一条验收变成你双击即可完成的事。

**未闭合项 / 半成品（如实）**

| # | 项 | 状态 |
| --- | --- | --- |
| 1 | E18b 真实中断级（本地 `livekit-server` 停机 8 秒） | **未做**：本轮两种自动化真断手段都不成立（见 E18b 行），不冒充 |
| 2 | E18c 物理断网 8 秒 + 设备保持 | **待你演练**：双击 `reconnect-drill.bat` 后回填四项 |
| 3 | 「共享中说话不夺焦点」 | 未单独实测（测试环境无人出声）；已由 `computeStageLayout` 的优先级保证，建议真机点一次 |
| 4 | 服务端强停共享 | 本轮协作式；强停方案待实测（design §6.2），要强停需另开轮次 |
| 5 | 断线后的举手/焦点恢复、未读跨页持久化、共享录制、群聊编辑/撤回 | 明确不在 M3 范围，候选 M5 |
| 6 | 演示库残留 | 本轮验证写入了多间测试房间与 `cp4-*`/`cp6-*`/`cp7*` 账号；要还原就 `python backend/scripts/db_init.py --reset --seed`（会清掉你的房间，请先确认） |

## 7. 合并指引（由人执行，AGENTS 硬规矩 4）

```bash
git checkout main
git merge --no-ff req/r004-room-extras
git tag -a round-r004-done -m "r004 完成（M3 房内扩展能力 · 群聊/举手/焦点/共享 + 界面缺陷与还债）"
```

合并后复验：`dev.bat check` → `pytest backend/tests -q` → `python backend/scripts/smoke.py` → `cd frontend && npx tsc --noEmit && npm run build` → 真机 E8~E14。
