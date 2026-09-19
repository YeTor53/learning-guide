---
title: r003 审查报告（阶段 3 定稿）
description: r003 的验收对账（V1~V11 逐条证据）、规则核对、两轴文档对账、重定向与 CR 对账、视觉对账、两栏处置清单与合并指引。
type: reference
status: approved
owner: 陀梓皓
updated: 2026-09-19
---

<!-- overview -->
阶段 3 的产物，2026-09-19 由 `cp-r003-3` 定稿。结论口径：**已过**（有可复现命令/真机实测）/ **未取证**（只能人工真跑，进 §6 未闭合清单）/ **欠账**（本轮已偿还或已登记）。

## 1. 验收对账（需求单 §4 逐条）

| 条目 | 实现位置 | 证据（2026-09-19 真机实测） | 结论 |
| --- | --- | --- | --- |
| V1 房主控制坞是危险色「结束房间」且可点 | `DeviceBar.tsx:104-124` | 房间 `room_14c610ea328bce80`（房主 `host@example.com`）：`.live-ctrl-end` 文案「结束房间」；`color=rgb(255,208,208)`、`borderTopColor=rgba(255,107,107,0.55)`（= `--live-end-border`）；**`.live-ctrl-leave` 不存在**（房主没有「离开」）；截图 1 | 已过 |
| V2 点击出确认框、`Esc` 可取消且无副作用 | `DeviceBar.tsx:106-114` + `RoomLivePage.tsx:132-143` | 点击后坞内出现「结束这个房间？所有人将被移出、需重新申请才能进；房间转为只读，历史仍可查。」+「结束房间」/「取消（Esc）」；按 `Esc` → 确认行消失、按钮恢复、状态条仍 `已连接`（`00:18`）；截图 2 | 已过 |
| V3 确认后房主被断开并回列表；卡片「已结束」无动作 | `RoomLivePage.tsx:doEnd` | 确认后状态条 `已断开` + 「房间已结束」，URL 变为 `/`；列表「已结束」筛选下该卡片 `已结束`、`0/8`，`article` 内按钮与链接数 = **0**；截图 3 | 已过 |
| V4 另一浏览器 3 秒内断开并显示「房间已结束」 | 后端 `end_room`（未改） | **接口 + 平台两级证据**：① 成员取票 `POST /api/rooms/{id}/token` → **409 `ROOM_ENDED`**；② 直接问 LiveKit `ListRooms` → **房间列表为空**（结束前该房间正处于连接中）→ `delete_room` 真删；**未做第二个浏览器的肉眼版**（见 §6） | 部分（接口级已过） |
| V5 非房主仍是「离开」，行为不变 | `DeviceBar.tsx:126-137` | 以 `part@example.com` 进 `room_6026ed81aee50a24`：`.live-ctrl-end` 不存在，`.live-ctrl-leave` 文案「离开」、`title="离开房间（不绑定快捷键）"`；点它 → 确认行「离开后要重新申请才能进来，确定吗？」 | 已过 |
| V6 库侧三件事 + `livekitApplied` | 后端（未改） | SQL：`rooms.status='ended'`、`ended_at` 非空；`room_members` 房主 1 行 `inactive / room_ended`；`join_requests` 0 行（本房间无 `pending`，故「pending→cancelled」由单测覆盖，未在本房间取证）。`livekitApplied` 两种取值实测：有人连过的房间 → 平台房间确已消失；从未连接的房间（`room_464ae4dfdc6e3ae9`）→ **false**（平台侧本无此房间，`delete_room` 如实报失败，ADR-0011 条 5） | 已过（附条由单测覆盖） |
| V7 越权：非房主调 `POST /end` | 后端（未改） | `part@example.com` 对活跃房间 `POST /api/rooms/room_d80fe9ff594f7f17/end` → **403 `FORBIDDEN`** | 已过 |
| V8 质量门禁 | — | `npx tsc --noEmit` 退出码 0；`npm run build` 成功（1977 modules，`index-*.css` 29.58 kB / `index-*.js` 902.90 kB）；`pytest backend/tests -q` → **95 passed**（后端零改动） | 已过 |
| V9 零 emoji / 单一图标库 | `DeviceBar.tsx` | 本增量唯一新图标 `PhoneOff` 来自 `lucide-react`；`frontend/src` 扫描无 emoji 命中 | 已过 |
| V10 文档对账（10 处） | — | 功能页 §3 F-16 / §4.2 按钮矩阵 / §4.5 条④ / §4.9 / §6 第 10 步 / §8 变更记录；实现页 §11；风格指南 §12.1；`demo.md` 第 9 步 + 新增实测记录；`setup.md` 第 11 行 + `dev.bat` 一行；README「怎么跑」——全部与代码一致，示例按实跑写 | 已过 |
| V11 r002 收官回填 | — | `review.md` 无「待核/待实现后填」残留；需求单 `closed`；索引表 r002 行已改；roadmap §3/§7 三处矛盾已消；开发者教学页 `r002-livekit-dev-guide.md` 已补交 | 已过 |

## 2. 规则核对（AGENTS.md / 风格指南）

| 规则 | 核对方式 | 结论 |
| --- | --- | --- |
| 未批不实现；每处改动挂在 `rNNN` | 提交信息 `[Req: r003]`；设计批准发生在「ab按现在，直接开始」之后 | 已过 |
| 一次提交一个逻辑增量 | `c2021c4` 阶段1 文档 → `9f37557` cp-1 → `ed9abd2` cp-2 → `541a185` dev.bat → `0403daf` .gitattributes → cp-3 | 已过 |
| `git add` 具体路径；append-only（禁 amend/rebase/squash） | 全程按路径 add；无 amend/rebase | 已过 |
| 密钥不入库 | `git grep -nE "API_SECRET\|API_KEY" -- backend/app frontend/src` 仅 `config.py` 变量名；`frontend/dist` 扫描无命中；`.env` 未被跟踪 | 已过 |
| 改端口/依赖/目录结构须先批 | 无新增依赖、未改端口；新增文件 = `dev.bat`（用户要求，登记 `redirect-01`） | 已过 |
| 零 emoji / 单一图标库 / 文案用动词短语 | 见 V9；新文案「结束房间」「结束这个房间？」沿用风格指南词表 | 已过 |
| 文档与代码同一次提交 | cp-2 与 cp-3 的代码与文档同提交；`dev.bat` 与其 README/单证同提交 | 已过 |
| 教学页示例实跑后才写 | 教学页第 9 步与实测记录按本轮真机输出改写 | 已过 |

## 3. 文档对账（两轴 + 四件套 + 覆盖矩阵）

| 项 | 结论 |
| --- | --- |
| 设计页 | `docs/rounds/r003-end-room-entry/design.md`（阶段 1，含契约面清单、函数级改动、视觉与教学契约） |
| 模块轴 | `docs/02-modules/r002-livekit-features.md`（F-16 / 按钮矩阵 / 防呆 / §4.9 / 演示脚本）与 `r002-livekit.md`（§11）已按实现回填 |
| 使用者教学页 | `docs/tutorials/r002-livekit-setup.md`（含 `dev.bat` 入口）与 `r002-livekit-demo.md`（第 9 步 + §4 实测记录） |
| 开发者教学页 | `docs/tutorials/r002-livekit-dev-guide.md`（cp-r003-1 补交；含本轮控制坞改动位置） |
| 轮次轴 | `docs/rounds/r003-end-room-entry/`：`design.md` / `changes.md` / `review.md` / `redirect-01.md` 齐 |
| 索引 | `docs/00-requirements/README.md` r003 行已加并转 `in progress`；r002 行已回填 |
| 覆盖矩阵 | 需求单 §6 无 `planned` 残留（逐格核对：阶段 1 落地项 + cp-1/2/3 落地项） |
| 双轴互链 | 模块页「变更记录」有本轮两行并回链轮次目录；`changes.md` 逐 cp 记文件×锚点 |

## 4. 重定向与 CR 对账

| 单号 | 类型 | 级别 | 结论 | 落地 |
| --- | --- | --- | --- | --- |
| `r002-07` | 重定向（实现偏差 A + 入口位置变更） | L3 | confirmed-A（用户「这个加入003，开始003」） | `ed9abd2` |
| `r003-01` | 重定向（新增开发工具脚本） | C 追加 | confirmed-C（用户「写个一键启动环境的脚本」） | `541a185` |
| 本轮 CR 单 | — | — | **无 CR**：实现期只发生一次 L1 实现细节调整（确认行按钮折行 → `white-space: nowrap`，见 §5），按 2.0 不入 CR，记 `changes.md` | — |

- 滑行检查：`design.md` 的「本轮设计变更记录」为空与 git log 一致（无未登记的对外变化）——已过。

## 5. 视觉对账（界面类项目）

| 组 | 方式 | 结果 |
| --- | --- | --- |
| 令牌扫描 | `git grep -n -- "--live-end"` | 命中 3 处：`global.css` 两行定义 + `.live-ctrl-end` 使用（实测渲染值 `rgba(255,107,107,0.55)` 与令牌一致） |
| 零 emoji / 单一图标库 | `frontend/src` 扫描 | 无 emoji；新图标 `PhoneOff` ∈ lucide-react |
| 桌面截图 | 真机 `localhost:5173`（视口 1265×566） | 截图 1（房主控制坞）/ 截图 2（确认框）/ 截图 3（列表「已结束」卡片） |
| 几何量测 | `getComputedStyle` + `clientHeight/scrollWidth` | 确认行按钮 `white-space: nowrap`、单行高 34px、`scrollWidth == clientWidth`（不溢出） |
| 降级复测 | 未做（`prefers-reduced-motion` 对本增量无新增动效） | 本增量**不新增任何动效**，故无降级面 |
| L1 实现细节调整 | 窄视口下确认行按钮文案被折成两行（截图 2 可见「结束房 间」） → `.live-dock-confirm .btn { white-space: nowrap }` | 改后复测：`nowrap` 生效、单行；构建产物内可见该规则 |

## 6. 留给用户的两栏处置清单

**本轮已落地且可保留的增量**

| 增量 | 提交 | 文档页 |
| --- | --- | --- |
| r003 需求单 + 设计（阶段 1 文档先行） | `c2021c4` | `docs/00-requirements/r003-end-room-entry.md`、`rounds/r003-end-room-entry/design.md` |
| r002 收官回填（review 定稿 / 需求单 closed / 矩阵 landed / 索引与 roadmap 回填 / 开发者教学页补交 / 清 0 字节文件） | `9f37557`（tag `cp-r003-1`） | `docs/rounds/r002-livekit/review.md` 等 6 处 |
| 房主「结束房间」入口落回控制坞（含文档同提交） | `ed9abd2`（tag `cp-r003-2`） | 功能页 / 实现页 / 风格指南 / 轮次 changes |
| `dev.bat` 一键启动环境（自检 / 启动 / 停止） | `541a185` | README「怎么跑」、`redirect-01.md` |
| `.gitattributes` 固定 `*.bat` 为 CRLF | `0403daf` | 自身（批处理对 LF 敏感） |
| 确认行按钮不折行（L1） | `cp-r003-3` | `changes.md` 一行 |

**未闭合项 / 半成品**（各带「若判为 C 或 D 时的处置」）

| 项 | 现状 | 若判 C（后续） | 若判 D（改方向） |
| --- | --- | --- | --- |
| 双浏览器人工全流程（含本轮 V4 的肉眼版） | 本轮用接口 + 平台两极证据替代 | 演示日按 `demo.md` 九步一次走完并勾选 | 演示脚本作废，改为录屏验收 |
| 断网重连 / 设备状态保持 / reduced-motion 降级无实测留痕（r002 遗留） | 代码在，未肉眼验 | 演示日或 M3 首轮补 | — |
| `smoke.py` 未加 r002 四步（`PASS 22/22` 是 r001 项） | 已知 | M3 首轮补四步（≈30 行） | 由单测覆盖，放弃脚本项 |
| `cp-r002-1` / `cp-r002-5` 未打 tag | 建议 `7b95a6b` / `cbd9caf` | 补打（一行命令） | 接受现状并注明 |
| `redirect-03` 原生弹窗替换（仍 proposed） | 现存 0 处 | M3 或交付前单独轮 | 作废该单 |
| `ended` 房间回看载体 | 列表无入口 | M4 纪要页 `/rooms/:id/summary` | 改列表页只读面板 |
| 侧边栏「宽 < 高」样式缺陷 | 未复现未归因 | 复现后单独修 | 判定不可复现则移出台账 |
| 首页筛选条落在首屏外 | 4 个候选修法已写 | 交付前选一个（推荐 A：上移顶栏下方） | 不改，写明取舍 |
| 本次取证产生的测试房间 | 3 个已结束房间（`room_14c610…` / `room_464ae4…` / `room_6026ed…`）+ 1 个活跃房间，在演示库里 | 用 `python backend/scripts/db_init.py --reset --seed` 恢复演示数据（会清空现有房间） | 保留 |

## 7. 合并指引（由人执行，AGENTS 硬规矩 4）

```bash
git checkout main
git merge --no-ff req/r003-end-room-entry
git tag -a round-r003-done -m "r003 完成（房主结束房间入口 + r002 收官回填 + dev.bat）"
```

合并后复验：`npx tsc --noEmit` → `npm run build` → `pytest backend/tests -q`（95 passed）→ `dev.bat check` → 真机 V1/V2/V3/V5。
