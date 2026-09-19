---
title: r004 变更记录（changes）
description: r004 的文件 × 模块 × 页面锚点台账、cp 进度、用户消息台账与无文档变更登记。
type: reference
status: draft
owner: 陀梓皓
updated: 2026-09-19
---

<!-- overview -->
一轮一行地记「改了什么、落到哪份文档的哪个锚点、验证证据是什么」。代码与文档必须同一次提交落地。

## 1. cp 台账

| cp | 内容 | 状态 | 提交 SHA | 证据 |
| --- | --- | --- | --- | --- |
| cp-r004-1 | 阶段 1 文档先行（需求单 + 设计 + 架构增量 + ADR-0013/0014 + 档案骨架 + 索引行） | 完成 2026-09-19 | 见本提交 | 你批「按设计做」 |
| cp-r004-2 | r003 收官回填 + 文档工程体检与三页导览 + 元数据修正 + `smoke.py` 补 r002 四步 | **完成 2026-09-19** | 见本轮 docs 提交 | 索引表 r003 转 closed；需求单 r003 转 closed；roadmap §7/§9 回填；`smoke.py` 实测 **PASS 29/29**（原 22/22，新增 7 项：成员取票 200 / 非成员 403 / 踢人 200+livekitApplied=True / 被移出后 403 / 被移出者 exit_reason=kicked / 结束后取票 409 / 已含结束 409） |
| cp-r004-3 | 界面缺陷两项（侧边栏竖屏 + 筛选条上移）+ ADR-0015 | **完成 2026-09-19** | 见本轮 cp-3 提交 | 见下方「cp-3 证据」 |
| cp-r004-4 | 迁移 004 + 消息/举手/焦点接口 + `end_room` 连带 + 单测 | planned | — | `pytest` 全绿 |
| cp-r004-5 | 前端实时层（`useDataChannel` + 四 hooks + `roomExtras` API） | planned | — | `tsc` 全绿 |
| cp-r004-6 | 前端界面（抽屉双 tab / 举手 / 焦点 / 共享 / 优先级 / 视觉） | planned | — | 双浏览器 E8~E14 |
| cp-r004-7 | 取证 + 教学页 + 审查报告 + 收官 | planned | — | E16~E20 |

## 2. 文件 × 模块 × 文档锚点

| 文件 | 模块 | 改什么 | 落的文档锚点 | 状态 |
| --- | --- | --- | --- | --- |
| `docs/00-requirements/r004-room-extras.md` | 契约 | 需求 / 口径 / 验收 / 覆盖矩阵 | 自身 | landed（cp-1） |
| `docs/rounds/r004-room-extras/design.md` | 契约 | 函数级设计 / 协议 / 优先级 | 自身 | landed（cp-1） |
| `docs/01-architecture/r004-realtime-extras-architecture.md` | 设计 | 通道与真相源的分层与时序 | 自身 | landed（cp-1） |
| `docs/03-decisions/r004-adr-0013-*.md` / `r004-adr-0014-*.md` | 决策 | 通道真相源 / 焦点优先级 | 自身 | landed（cp-1） |
| `docs/03-decisions/r004-adr-0015-home-first-screen.md` | 决策 | 首屏优先级 / 竖屏 hero 收敛 / 窄屏侧边栏 | 自身 | landed（cp-3） |
| `backend/app/db/sql/004_r004_realtime_extras.sql` | 数据层 | `room_hand_raises` + `room_focus` | 实现页 §3 | planned（cp-4） |
| `backend/app/services/{messages,hands,focus}.py` | 后端 | 三组能力的服务函数 | 实现页 §5 | planned（cp-4） |
| `backend/app/api/routers/room_extras.py` | 后端 | 8 个路由 | 实现页 §4 | planned（cp-4） |
| `backend/app/services/rooms.py` | 后端 | `end_room` 连带清举手 | 实现页 §3 | planned（cp-4） |
| `backend/tests/test_room_extras_api.py` | 测试 | E1~E6 用例 | 实现页 §9 | planned（cp-4） |
| `frontend/src/hooks/{useDataChannel,useChatMessages,useHandRaise,useRoomFocus,useScreenShare}.ts` | 前端 | 实时层 | 实现页 §5.5 | planned（cp-5） |
| `frontend/src/api/roomExtras.ts` | 前端 | HTTP 封装 | 实现页 §4 | planned（cp-5） |
| `frontend/src/components/live/{ChatPanel,MessageBubble,FocusBadge}.tsx` | 前端 | 新组件 | 功能页 F-18~F-21 | planned（cp-6） |
| `frontend/src/components/live/{RoomSidePanel,DeviceBar,LiveStage}.tsx`、`pages/RoomLivePage.tsx` | 前端 | 抽屉双 tab / 新按钮 / 优先级 / 装配 | 功能页 §4.2 按钮矩阵 | planned（cp-6） |
| `frontend/src/pages/RoomsPage.tsx` | 前端 | 工具栏 DOM 上移到 hero 之前 | 功能页 §4.1 指路 + ADR-0015 | landed（cp-3） |
| `frontend/src/App.tsx` + `components/SideBar.tsx` + `hooks/useNarrowStrip.ts`（新） | 前端 | 窄屏忽略折叠 + 隐藏折叠按钮 | ADR-0015 §3/§4 | landed（cp-3） |
| `frontend/src/styles/global.css` | 风格 | 3 个令牌 + 2 处动效；**cp-3** 另加 hero 上内边距 32→16、工具栏下边距 20、竖屏块、窄屏横向条一行 | 风格指南 §12.1 | cp-3 landed（令牌待 cp-6） |
| `backend/scripts/smoke.py` | 脚本 | r002 四步**已补**（实测 29/29）；r004 三步待 cp-7 | README / AGENTS `<check>`；证据见本表 cp-r004-2 行 | landed（cp-2） |
| `docs/tutorials/r004-room-extras.md` + `r002-livekit-dev-guide.md` 补节 | 教学 | 使用者 + 开发者 | 自身 | planned（cp-7） |
| `README.md` / `AGENTS.md` / `global-roadmap.md` / `00-requirements/README.md` / `glossary.md` | 项目级 | 状态、命令、台账、术语 | 自身 | planned（散在 cp-2/6/7） |

## 2.1 cp-3 证据（两项界面缺陷）

**复现手段（本轮新增能力）**：`playwright screenshot --viewport-size="W,H" --wait-for-timeout=2500 URL out.png`
—— 它能给出**任意视口**的真实截图（我原先的抓取浏览器固定 1258×566，无法看竖屏）。截图目录：`C:\Users\Administrator\AppData\Local\Temp\lg_cp3\`

| 视口 | 改前 | 改后 | 结论 |
| --- | --- | --- | --- |
| 1258×566（我抓取） | 首屏内**没有**筛选条（roadmap §9 实测 `toolbar.top=639`，需下滚 73px） | `toolbar.top=101` / `bottom=146`；`hero.top=170`；`stats.top=517`；`scrollWidth=1243 ≤ 1258` | 筛选条完整进首屏（口径 `≤522`） |
| 700×1000（竖屏） | `before-700x1000.png`：横向条只剩图标、行为居中内边距、仍显示「收起侧边栏」；hero 占满首屏 | `after2-700x1000.png`：标签齐全、无折叠按钮、横向条压成一行；筛选条在首屏；无横向溢出 | 缺陷消失 |
| 820×1180 | — | `after2-820x1180.png`：横向条一行（导航左 / 个人信息右）、筛选条一行含「创建房间」 | 通过 |
| 1000×1200（宽 >900 的竖屏） | `portrait-1000x1200.png`：264px 竖列正常 | 同左（未受本次改动影响） | 通过 |

**归因（有依据，非猜测）**：窄屏（≤900px）下侧边栏是横向条，而 `SideBar` 在 `collapsed` 为真时**不渲染** label（React 条件渲染，CSS 的 `.sidebar.collapsed .side-item .label { display: inline }` 救不回来）→ 横向条只剩三个图标 + `.sidebar.collapsed .side-item { justify-content: center; padding: 10px 0 }` 的居中内边距 → 观感即「样式出错」；叠加「横向条下折叠按钮无意义」。修法 = 窄屏按展开渲染 + 隐藏按钮。

**未做到的（如实）**：竖屏/窄屏的数字量测缺 JS 求值通道（`playwright screenshot` 只能截图），因此那一档是**视觉证据**而非数值证据；且我手上没有你当时看到的那张截图，若你看到的现象与「折叠状态穿越断点」不同，请把竖屏截图发我，我再对齐。

## 3. 用户消息台账（首行回执的核对凭据）

| 序号 | 日期 | 用户原话摘要 | 回执分类 | 单号 |
| --- | --- | --- | --- | --- |
| 1 | 2026-09-19 | 「r004」 | 新方向 · 开轮请求（需澄清） | — |
| 2 | 2026-09-19 | 「我合并了的。1 1 1 1 1 1 2 1 1」 | 批准（W1/W2：r003 已合并 + 答 Q1~Q9，含 Q7 改口并进本轮） | r004 需求单 §3 |
| 3 | 2026-09-19 | 「1 1 1 思考现在可能的一次对话内，各个人象征的框的大小的变换」 | 批准（U7~U9）+ 设计补充（布局动力学） | design §7.3~§7.8、需求单 U11~U14 |
| 4 | 2026-09-19 | 「等一下，你的文档写的开始混乱了，解决这个先」 | 重定向（文档工程整理，非功能） | 本表 §4 + `docs/README.md` |
| 5 | 2026-09-19 | 「是用来分析这个问题的会话的…我会优化skill给出这部分的规范，你负责重新整理文档」 | 澄清（不改规约，只整理；另纳入其 ADR 文件） | 本轮 docs 提交、`global-adr-0002` |
| 6 | 2026-09-19 | 「做吧」 | 批准（元数据修正 + 漂移核实 + 纳入 ADR + cp-2 收尾） | 本表 §1 |
| 7 | 2026-09-19 | 「2」 | 批准（cp-3：先按代码分析改，事后复看） | 本表 §2.1 |

## 4. 无文档变更的提交 / 文档整理记录

| 日期 | 事项 | 说明 |
| --- | --- | --- |
| 2026-09-19 | **`smoke.py` 补 r002 四步**（cp-2） | 新增：成员取 Token 200 / 非成员（第三个账号）403 / 房主踢人 200 且回传 `livekitApplied` / 被移出后取 Token 403 / 被移出者 `exit_reason=kicked` / 结束后取 Token 409。实测 `PASS 29/29`（原 22/22） |
| 2026-09-19 | **元数据修正（经批准）** | r002 `design.md` 补 front matter；`redirect-06.md` 的 status 规范化为 `confirmed-delete`（原话移入 `decision_note`）；r002 架构页 / 两个模块页 / r002 `changes.md` 的 `draft` → `closed`。**正文一字未改** |
| 2026-09-19 | **核实并关闭一条疑似漂移** | 「`test_schema.py` 的 DDL 事实源页停更」经实测排除：`pytest ... -k "design_page or counted_tables or ordered"` → **3 passed**（该页与 `001_schema.sql` 仍逐字一致，`003_` 迁移记在 r002 页面），仅 `updated` 日期偏旧，不回改 |
| 2026-09-19 | **文档工程整理与体检（L1，无行为变化）** | 新建三页导览：`docs/README.md`（目录地图 / 目标指路 / 架构与 ADR 一览 / 轮次档案现状 / backlog / 实测清点与已知不一致 7 条）、`docs/02-modules/README.md`（模块 → 轮次页 → 当前真相页）、`docs/tutorials/README.md`（受众索引）；同时完成 r003 收官回填（需求单转 closed、索引表 r003 行、roadmap §7 完成与开 r004、§9 新增两行登记「已收官页元数据 3 项」与「test_schema DDL 源页漂移」）。三页导览**只描述现状与指路，不引入新规约**（命名与落位口径由 owner 规范统一） |
| 2026-09-19 | **文档整理（L1，无行为变化）** | 阶段 1 文档经三轮追加后出现结构问题，本轮一次性整理：① 需求单 §4 的 U 口径 16 条混作一表、验收 E 编号两段拼接 → 改 U 四组 + 验收 A/B/C/D 四组，并声明 E 编号不再变更；② design 小节号错乱（原 `### 7.5` 夹在 §7 与 §8 之间，§8 又用 8.0~8.9 另一套记法）→ §7 改「舞台结构与布局动力学」7.1~7.8、§8 重排 8.1~8.11；③ 两张令牌表并存（原 7.5.5 与 8.7）→ 合并为 design §8.9 **唯一来源**；④ 函数名两套（`pickFocusTile` / `computeStageLayout`）→ 统一 `computeStageLayout`；⑤ 跨页引用过期（design §6.3→§6.2、§7.5.x→§7.3~§7.8、§8→§8.1~§8.11、§10.1→§10.2）→ 全量修正；⑥ 新增 design §0 导航与「单一事实源」表；⑦ 补齐 design §8.6「举手与聊天的样式」（原标题名不副实）；⑧ 需求单 §6 影响面与 design §5 的文件口径对齐 |
| 2026-09-19 | 提交 `fc65e23` 的提交信息不实（由 `ac77c31` 更正） | 该提交信息写了「design §7.5」，实际只落了需求单（脚本漏写盘）；按 append-only 不回改历史，正文由 `ac77c31` 补齐 |

（实现期若某步确实无对外行为变化，在此另起一行并说明原因。）
