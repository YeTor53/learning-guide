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
| cp-r004-2 | r003 收官回填 + 文档工程体检与三页导览 + 元数据修正 + `smoke.py` 补 r002 四步 | **完成 2026-09-19** | 提交范围 `8c650cd..857cf18`（其后 `81b9f06` 纳入 ADR、`f9be57b`/`063b707` 文档整理为附带文档提交） | 索引表 r003 转 closed；需求单 r003 转 closed；roadmap §7/§9 回填；`smoke.py` 实测 **PASS 29/29**（原 22/22，新增 7 项：成员取票 200 / 非成员 403 / 踢人 200+livekitApplied=True / 被移出后 403 / 被移出者 exit_reason=kicked / 结束后取票 409 / 已含结束 409） |
| cp-r004-3 | 界面缺陷两项（侧边栏竖屏 + 筛选条上移）+ ADR-0015 | **完成 2026-09-19** | 见本轮 cp-3 提交 | 见下方「cp-3 证据」 |
| cp-r004-4 | 迁移 004 + 消息/举手/焦点接口 + `end_room` 连带 + 单测 | **完成 2026-09-19** | 见本轮 cp-4 提交 | `pytest` **105 passed**（基线 95 + 新增 10）；`smoke` 29/29；`db_init` 应用 003+004；活服务探针 9 项全通过（见 §2.2） |
| cp-r004-5 | 前端实时层（`useDataChannel` + 四 hooks + `roomExtras` API + dev-only 调试句柄） | **完成 2026-09-19** | 见本轮 cp-5 提交 | `tsc`/`build` exit 0；双浏览器数据通道双向收发实测；`__lgRoom` 生产产物 0 命中（见 §2.3） |
| cp-r004-6 | 前端界面（抽屉双 tab / 举手 / 焦点 / 共享 / 优先级 / 视觉 + 令牌落库） | **完成 2026-09-19** | 见本轮 cp-6 提交 | 双浏览器 E8~E14 实测（见 §2.4） |
| cp-r004-7 | 取证 + 教学页 + 审查报告 + 收官 | **完成 2026-09-19** | 见本轮 cp-7 提交 | `smoke` **36/36**；E21~E23 量测齐；E18b 未做（如实）；E18c 交你演练（见 §2.5） |

## 2. 文件 × 模块 × 文档锚点

| 文件 | 模块 | 改什么 | 落的文档锚点 | 状态 |
| --- | --- | --- | --- | --- |
| `docs/00-requirements/r004-room-extras.md` | 契约 | 需求 / 口径 / 验收 / 覆盖矩阵 | 自身 | landed（cp-1） |
| `docs/rounds/r004-room-extras/design.md` | 契约 | 函数级设计 / 协议 / 优先级 | 自身 | landed（cp-1） |
| `docs/01-architecture/r004-realtime-extras-architecture.md` | 设计 | 通道与真相源的分层与时序 | 自身 | landed（cp-1） |
| `docs/03-decisions/r004-adr-0013-*.md` / `r004-adr-0014-*.md` | 决策 | 通道真相源 / 焦点优先级 | 自身 | landed（cp-1） |
| `docs/03-decisions/r004-adr-0015-home-first-screen.md` | 决策 | 首屏优先级 / 竖屏 hero 收敛 / 窄屏侧边栏 | 自身 | landed（cp-3） |
| `backend/app/db/sql/004_r004_realtime_extras.sql` | 数据层 | `room_hand_raises` + `room_focus` + 3 索引 | 实现页 §2 | landed（cp-4） |
| `backend/app/services/{messages,hands,focus}.py`（新） | 后端 | 三组能力的服务函数 | 实现页 §4 | landed（cp-4） |
| `backend/app/repositories/room_extras.py`（新） | 后端 | 三个能力的参数化 SQL + 行映射（**设计未点名，按既有分层补**） | 实现页 §1 | landed（cp-4） |
| `backend/app/db/migrate.py` | 数据层 | 计数表加两张新表；`split_statements` 过滤 `BEGIN/COMMIT`（修 003 迁移中止的遗留问题） | 实现页 §6 | landed（cp-4） |
| `backend/app/api/routers/room_extras.py`（新） | 后端 | 8 个路由 + `main.py` 注册 | 实现页 §3 | landed（cp-4） |
| `backend/app/services/rooms.py` | 后端 | `end_room` 连带清举手 | 实现页 §3 | planned（cp-4） |
| `backend/tests/test_room_extras_api.py`（新）+ `test_schema.py`（同步迁移清单与计数表） | 测试 | E1~E6 共 10 个用例 | 实现页 §7 | landed（cp-4） |
| `frontend/src/hooks/{useDataChannel,useChatMessages,useHandRaise,useRoomFocus,useScreenShare}.ts`（新） | 前端 | 实时层：topic 订阅/发布 + 三个状态 hook + 共享派生 | 实现页 §9 | landed（cp-5） |
| `frontend/src/api/roomExtras.ts`（新） | 前端 | 8 个 HTTP 封装 + Hand/Focus 类型 | 实现页 §9.1 | landed（cp-5） |
| `frontend/src/hooks/useRoomConnection.ts`（改动） | 前端 | dev-only `window.__lgRoom`（U15） | 实现页 §9.1 | landed（cp-5） |
| `frontend/src/api/roomExtras.ts` | 前端 | HTTP 封装 | 实现页 §4 | planned（cp-5） |
| `frontend/src/components/live/{ChatPanel,MessageBubble,FocusBadge}.tsx`（新）+ `stageLayout.ts`（新） | 前端 | 讨论区 / 单条消息 / 徽标 / **唯一**的布局派生函数 | 功能页 F-18~F-22、实现页 §10 | landed（cp-6） |
| `frontend/src/components/live/{RoomSidePanel,DeviceBar,LiveStage,ParticipantTile}.tsx`、`pages/RoomLivePage.tsx` | 前端 | 双 tab / 举手与共享按钮 / 按 `computeStageLayout` 渲染 / 状态条指示与未读 / 装配 | 功能页「按钮矩阵」 | landed（cp-6） |
| `frontend/src/pages/RoomsPage.tsx` | 前端 | 工具栏 DOM 上移到 hero 之前 | 功能页 §4.1 指路 + ADR-0015 | landed（cp-3） |
| `frontend/src/App.tsx` + `components/SideBar.tsx` + `hooks/useNarrowStrip.ts`（新） | 前端 | 窄屏忽略折叠 + 隐藏折叠按钮 | ADR-0015 §3/§4 | landed（cp-3） |
| `frontend/src/styles/global.css` | 风格 | **cp-6**：§8.9 令牌全表（14 项）+ `.chip-focus`/`.chip-share` + 缩格固定尺寸与四种模式 + 聊天/举手样式 + `::before` 上缘线（2px/共享 3px）+ reduced-motion 扩展 | 风格指南 §12.3 | landed（cp-6） |
| `backend/scripts/smoke.py` | 脚本 | r002 四步**已补**（实测 29/29）；r004 三步待 cp-7 | README / AGENTS `<check>`；证据见本表 cp-r004-2 行 | landed（cp-2） |
| `docs/tutorials/r004-room-extras-demo.md` + `r002-livekit-dev-guide.md` 补节 | 教学 | 使用者 + 开发者 | 自身 | planned（cp-7） |
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

## 2.2 cp-4 证据（数据层与后端）

**测试**：`conda run -n learningguide python -m pytest backend/tests -q` → **105 passed**（r003 基线 95 + 本轮新增 10；`test_room_extras_api.py` 覆盖 E1~E6）；`python backend/scripts/smoke.py --base-url http://127.0.0.1:8000` → **PASS 29/29**（无回归）。

**迁移**：`python backend/scripts/db_init.py`（不加 `--reset`）→ `本次应用版本：003_r002_host_uniqueness, 004_r004_realtime_extras`；`counts` 中 `room_hand_raises 0 / room_focus 0`、`schema_migrations 4`。

**活服务探针**（对正在跑的后端 `127.0.0.1:8000`，走真实 HTTP；脚本临时生成、跑完删除）：

| 步骤 | 结果 |
| --- | --- |
| 注册房主 / 建房 | 201 / 201 |
| 成员发消息（`"  cp4 真机探针消息  "`） | 201，落库正文被 trim 成 `cp4 真机探针消息` |
| 房主拉消息 | 200，能取到该条 |
| 成员举手（连发两次） | 200，快照 `len=1`（幂等） |
| 房主放下他人的举手 | 200，快照变空 |
| 房主设焦点 | 200，`subjectName=cp4成员`、`actorUserId` 留痕 |
| 取消焦点 | `subjectUserId=null` |
| 结束房间 | 200 |
| 结束后再发消息 | 409 `ROOM_ENDED` |

**未做到的（如实）**：数据库里的库级并发（两个连接同时举手）没有单独造（部分唯一索引已由 `test_schema`-style 约束用例与事务锁覆盖）；房内实时广播属于 cp-5/6。

## 2.3 cp-5 证据（前端实时层）

**构建**：`npx tsc --noEmit` exit 0；`npm run build` exit 0（1978 模块，CSS 29.89 kB / JS 903.25 kB）。产物扫描：`dist/assets/index-*.js` 里 `__lgRoom` 出现 **0 次**（U15「只在 DEV 挂载」成立）。

**双浏览器真机（本次新解锁的验证手段）**：用 base conda 的 Python + Playwright（`C:\ProgramData\miniconda3\python.exe`，`sync_playwright`）开**两个真实浏览器上下文**，通过 API 登录 `host@example.com` / `part@example.com` 后各自进入同一房间页 `room_6026ed81aee50a24`：

| 检查 | 结果 |
| --- | --- |
| 两端 `window.__lgRoom.state` | `connected`（dev 句柄可用 ✓） |
| A 看到的远程参与者 | `["usr_demo_part"]` |
| A 在 `lg.chat` 发布 `{v:1,message:{id:"probe-1",body:"A→B 探针"}}` | **B 收到**：`topic=lg.chat`、`from=usr_demo_host`、正文逐字一致 |
| B 反向发布 | **A 收到**（同款 payload，`from=usr_demo_part`） |
| 同源 HTTP（Cookie 会话） | `POST /api/rooms/{id}/messages` → **201**；`GET …/messages` → **200**，能回读刚发的那条 |
| 截图 | `C:\Users\Administrator\AppData\Local\Temp\lg_cp5\ctx-A-host.png`、`ctx-B-part.png` |

**说明（如实）**：`lg.hands` / `lg.focus` / `lg.screen.stop` 三条 topic 的双端实测放在 cp-6（那时界面才有按钮）；本次只验证了通道本身与 `lg.chat` 的完整往返。上一轮那次 265 秒无输出是我探针脚本的 bug（用 `evaluate_handle` 等一个可能永不 resolve 的 Promise，没设超时），已改成「发布 + 轮询 `window.__log`」的有界写法。

**顺带**：这次也验证了「HTTP 落库 + 广播加速」这条链路的两条腿都能在真实浏览器里跑通。

## 2.4 cp-6 证据（前端界面，双浏览器真机）

**手段**：Playwright 两个上下文（host / part）+ 三个额外成员上下文，全部通过 API 登录并进入同一房间「r003 权限对照房间」；截图在 `%TEMP%\lg_cp6\`。

| 检查 | 实测结果 |
| --- | --- |
| 群聊双端（UI 发送） | A 点「发送」→ A 列表出现该条；B 端 1 秒内收到；诊断跑里 A/B 两端正文数组**逐字相同**（`["cp5 探针消息","cp6 双浏览器消息：你好","诊断消息-1"]`） |
| 群聊裸通道 | A 用 `__lgRoom` 直接发 `lg.chat` → B 的监听收到同款 JSON（topic 字段正确） |
| 举手双端 | B 点「举手」→ 按钮变「放下手」；A 端「正在举手：王一诺」+「放下 王一诺」；A 替他人放下后两端回到未举手 |
| 焦点双端 | A 给 B 焦点 → A 徽标「焦点 · 王一诺」、B 徽标「焦点 · 你」、A 状态条「焦点 王一诺」；取消后徽标数 0 |
| 共享 + 上缘线 | B 共享 → A 徽标「共享 · 王一诺」、状态条「共享 王一诺」、共享格 `::before` 高度 **3px**、颜色 `rgb(124,240,196)` |
| 停他人共享（协作式） | A 点「请求停止共享」→ B 端按钮回「共享屏幕」、A 端徽标数 0、B 端提示「房主请求你停止共享屏幕（已为你停止）」 |
| 刷新与库一致 | 库 3 条 vs 刷新后页面 3 条，内容数组完全相同 |
| 布局阶梯（5 人） | rail 类名 `live-rail-double`、缩格 4 个且每个 **176×99**、焦点格 1016×572 |
| 降级 | `reduced_motion=reduce` 焦点格 `::before` 与聊天气泡 `animation-name = none` |
| tsc / build | 均 exit 0（1988 模块） |

**本次修掉的一个真 bug**：上缘线原先用 `@keyframes` 动 `box-shadow`，而动画填充值优先级高于静态声明 → 共享格的 3px 永远不生效（实测只 2px）。改为 `::before` 画线（动画只做 `scaleX + opacity`）后实测 3px。

**未做到（如实）**：① 「共享中有人说话不夺焦点」没单独实测（测试环境无人出声；该断言由 `computeStageLayout` 的优先级保证，列入 cp-7 人工项）② 竖屏/满员的**横条**模式只做了 `railMode='strip'` 的代码路径与设计表格对齐，尚未在竖屏下量测数字 ③ 共享用的是无头 Chromium 的自动桌面捕获（`--auto-select-desktop-capture-source=Entire screen`），**你真机点一次**才算最终确认。

## 2.5 cp-7 证据（取证 / 教学页 / 收官）

**E17 smoke 补 r004 三步**：`smoke.py` 新增发消息（201 + trim）、空消息 400、拉消息含新条、举手两次仍 1 条、自己放下清空、房主设焦点回传 subject、取消焦点为空 → 实测 **PASS 36/36**（原 29/29）。

**E21 尺寸阶梯（新房 `room_af43e343f766fb76`，抽屉关闭，1440×900）**

| 在房间人数 | rail 模式 | 缩格 | 缩格尺寸 | 焦点格 | 横向溢出 |
| --- | --- | --- | --- | --- | --- |
| 2 | `live-rail-single` | 1 | 176×99 | 1156×650 | 0 |
| 4 | `live-rail-single` | 3 | 176×99 | 1156×650 | 0 |
| 6 | `live-rail-double` | 5（2 列） | 176×99 | 1016×572 | 0 |
| 8 | `live-rail-triple` | 7（3 列） | 176×99 | 828×466 | 0 |

口径折算：E21 原写「2/4/6/8 人 → 1/2/2/3 列」，按 design §7.4 的 k（非焦点在线人数 1/3/5/7）折算为 1/1/2/3，实测与 design 一致。

**E23 窄屏与竖屏（8 人在线）**

| 视口 | 模式 | 缩格条 | 焦点格 | 溢出 |
| --- | --- | --- | --- | --- |
| 720×1024 | `live-stage-strip` | 672×321（7 格分 3 行） | **672×378**（≥320 ✓） | 0 |
| 900×600 | `live-stage-strip` | 852×210（7 格分 2 行） | **622×350** | 0 |
| 1258×566（对照：非竖屏、挤得下） | `triple` | 552×321 | 562（≥480 ✓） | 0 |

**E22 焦点易手**：过渡时长 **0.24s / 0.24s**；两次切换焦点后 `window.__node.isConnected` 均为 `true`（DOM 未重挂载）；8 人时对端（阶梯成员1）拿到「焦点 · 你」+ 状态条「焦点 阶梯成员1」。

**E18a 归因（事件注入级）**：数值枚举 4/5/2 → 「你已被移出房间」/「房间已结束」/「同一账号已在别处进入本房间」；1（自己发起）→ 无提示。

**E18b/C 与一个真缺陷**：`set_offline` 8 秒在无头下**不能**让 SDK 在窗口内进入重连态（恢复后才判定并落到「已断开」）→ E18b **未做到**、不冒充；E18c 交 `reconnect-drill.bat` 由你真机演练。过程中发现真缺陷并已修：`useRoomConnection` 原先只接 `Reconnecting`，**信号级掉线不进重连态**（断网时状态条仍「已连接」、按钮不禁用，与 r002 §8.9 契约不符）→ 补 `RoomEvent.SignalReconnecting`。

**记录一个测试方法坑**：窄屏量测第一次忘关抽屉 → 抽屉占 360px，缩格挤成一列、焦点掉到 280px，看着像布局 bug；关掉抽屉复测正常。已写进开发者教学页的坑清单。

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
| 8 | 2026-09-19 | 「继续」 | 批准（cp-4：按设计实现数据层与后端） | 本表 §2.2 + design §14 的 cp-4-1~4-5 |
| 9 | 2026-09-19 | 「继续」 | 批准（cp-5：前端实时层） | 本表 §2.3 |
| 10 | 2026-09-19 | 「不管」 | 免单（否决两项附带提议：skill patch 与 memory） | 回复已跳过 |
| 11 | 2026-09-19 | （承接上条）继续 cp-6 | 批准（cp-6：前端界面与样式） | 本表 §2.4 |
| 12 | 2026-09-19 | 「做」 | 批准（cp-7：取证 / 教学页 / 收官） | 本表 §2.5 |

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
