---
title: r003 需求单：房主结束房间入口（+ r002 收官回填）
description: 把房主「结束房间」入口落回交流页（由 redirect-07 确认的 L3 变更），同轮先偿还 r002 收官文档欠账；含边界、验收、影响面、风险、覆盖矩阵与实施顺序（cp-r003-1..3）。
type: requirement
status: draft
owner: 陀梓皓
updated: 2026-09-19
---

<!-- overview -->
本页只写「这一轮做成什么、怎么算做完、按什么顺序做」。怎么做见轮次设计 `docs/rounds/r003-end-room-entry/design.md`；来由见 `docs/rounds/r002-livekit/redirect-07.md`（confirmed-A，L3）。
上一轮 `r002` 代码已合入 `main` 并打 `round-r002-done`，但**收官文档欠账未清**（见 §2 第 1 项），本轮第一个增量先还它。

## 1. 目的

让房主在交流页有**唯一、明确、二次确认**的结束房间入口，终结「既不能离开、也无处结束」的死路：`r002` 删除房间管理页时，把当时唯一的「结束房间」按钮一起删掉了，而房内的抽屉与控制坞都没补回落点 —— 已批准文档（功能页角色能力矩阵 / F-16 防呆清单 / 演示脚本 / demo 教程）都写了这个入口存在。后端接口 `POST /api/rooms/{id}/end` 一直可用，缺的只是前端入口。

顺带（用户 2026-09-19「这个加入003」授权）：把 `r002` 的收官文档欠账在本轮第一个增量内还清，让 r002 的档案成为可追溯的最终真相。

## 2. 边界

**做**

1. **r002 收官回填（cp-r003-1，纯 docs）**：`docs/rounds/r002-livekit/review.md` 按实测证据定稿（验收对账 / 规则核对 / 两轴文档对账 / 口径对账 / CR 与重定向对账 / 未闭合清单）；`docs/00-requirements/r002-livekit-room.md` frontmatter 转 `closed`；`docs/00-requirements/README.md` 的 r002 行改为 closed + 完成 tag；`docs/00-project/global-roadmap.md` 三处矛盾（§3 M2 回填注、§7 第 2/3 条）修正；删除 0 字节空文件 `docs/99-archive/end_room`。
2. **房主结束房间入口（cp-r003-2，代码 + 文档同提交）**：控制坞（`DeviceBar`）离场组 —— 房主位置由 disabled 的「离开」改为危险色「结束房间」；点击出自绘确认框（Esc 可取消）；确认后调 `POST /api/rooms/{id}/end` → 断开本地连接 → 回房间列表。
3. **取证与收官（cp-r003-3）**：真机双端复看 + 教学页示例实跑 + 审查报告。

**不做**

- 不在抽屉（`RoomSidePanel`）加第二个结束入口；
- 后端零改动（接口、权限、库侧连带动作全部复用 r001/r002 已验收实现）；
- 不做「结束后房主留在只读页」新视图（M4 纪要页再谈）；
- 不动 8 处原生弹窗（`redirect-03` 仍为 proposed，本轮只保证不新增原生弹窗）；
- 不碰 M3 的房内能力（群聊 / 举手 / 焦点 / 屏幕共享）；
- 不改 `r001` 的历史页面（F-09 的「入口=详情页」按取代关系在 r002 功能页标注）。

## 3. 已定口径（本轮）

| 编号 | 口径 | 依据 |
| --- | --- | --- |
| Q1 | 入口只有一处：交流页控制坞离场组，仅房主可见 | redirect-07 §4；被你 2026-09-19 批准 |
| Q2 | 房主按钮文案「结束房间」，危险色描边，图标 `PhoneOff`（Lucide） | design §3 视觉契约 |
| Q3 | 二次确认用**自绘**确认框（复用现有 `live-confirm` 模式），**不用**原生 `window.confirm` | redirect-03 口径（站内提示）；本处为其首个落地 |
| Q4 | 确认文案三条后果：所有人被移出、需重新申请才能进；房间转为只读、历史仍可查；**后续版本**会生成一份讨论纪要 | 功能页 F-09 文案 + 纪要属 M4 的事实 |
| Q5 | 确认后：回房间列表（卡片显示「已结束」），自己也被断开 | 与其他端一致的收束经验 |
| Q6 | `connecting` / `reconnecting` 时禁用该按钮 | F-16 防呆清单条③ |
| Q7 | 房主仍不能「离开」（防呆分支保留） | r001 FQ-2（已决：必须先结束或移交） |
| Q8 | 轮次命名 `r003-end-room-entry`／分支 `req/r003-end-room-entry`／`cp-r003-N`／收尾 `round-r003-done` | AGENTS 硬规矩 4 |

## 4. 验收清单（逐条给证据；勾选处必须引编号证据）

- [x] V1 房主视角：控制坞右侧是危险色「结束房间」且**可点**（原「离开」不再出现）—— 见 `review.md` §1 V1（截图 1 + 实测 `color=rgb(255,208,208)` / 边框 `rgba(255,107,107,0.55)`，`.live-ctrl-leave` 不存在）
- [x] V2 点击出确认框，`Esc` 可取消、取消后房间与连接均无变化 —— 见 `review.md` §1 V2（截图 2；Esc 后仍 `已连接`）
- [x] V3 确认后：房主被断开并回到房间列表，该卡片状态「已结束」且无动作 —— 见 `review.md` §1 V3（截图 3；`article` 内按钮/链接数 = 0）
- [x] V4 另一浏览器（同房间成员）3 秒内断开并显示「房间已结束，仅可查看历史内容」 —— **接口 + 平台两级证据**（取票 409 `ROOM_ENDED`；LiveKit `ListRooms` 为空），肉眼版列未闭合（`review.md` §1 V4 / §6）
- [x] V5 非房主视角按钮仍是「离开」，行为不变（离开=回列表、需重新申请才能再进） —— 见 `review.md` §1 V5（`part@example.com` 实测）
- [x] V6 库侧三件事 + 实时断开 —— 见 `review.md` §1 V6（SQL 实测；本房间无 `pending` 故该条由单测覆盖；`livekitApplied` 两种取值实测含 false 的成因）
- [x] V7 越权路径：非房主调 `POST /rooms/{id}/end` → **403 `FORBIDDEN`**（见 `review.md` §1 V7）
- [x] V8 质量门禁：`tsc` 退出码 0、`npm run build` 成功（1977 modules）、`pytest -q` → **95 passed**
- [x] V9 零 emoji / 单一图标库：新增图标 `PhoneOff` ∈ lucide-react；扫描无 emoji
- [x] V10 文档对账：功能页 §3 F-16 / §4.2 / §4.5 条④ / §4.9 / §6 第 10 步 / §8 变更记录；实现页 §11；风格指南 §12.1；`demo.md` 第 9 步 + 实测记录；`setup.md` 第 11 行；README —— 均与代码一致，教学示例按本轮真机输出写
- [x] V11 r002 收官回填：review.md 定稿无残留、需求单 `closed`、索引表已改、roadmap 三处矛盾已消、开发者教学页已补交

## 5. 影响面

- **代码**：`frontend/src/components/live/DeviceBar.tsx`、`frontend/src/pages/RoomLivePage.tsx`、`frontend/src/styles/global.css`（令牌 + 一个新 class）。后端 0 文件。
- **文档**：见 §6 覆盖矩阵（10 个文件）。
- **依赖 / 环境 / 数据库**：无新增依赖、无迁移、无端口变更。
- **对既有验收的影响**：r001 的 E9/E10 与 r002 的演示脚本第 9/10 步动作入口变化 → 在 r002 功能页与教学页就地更新口径（不改历史页结论）。

## 6. 文档产出清单（覆盖矩阵）

| 文档 | 类 | 承载内容 | 状态 |
| --- | --- | --- | --- |
| `docs/00-requirements/r003-end-room-entry.md`（本页） | 契约 | 目的 / 边界 / 口径 / 验收 / 覆盖矩阵 | landed |
| `docs/rounds/r003-end-room-entry/design.md` | 契约 | 契约面清单、逐文件函数级改动、视觉与教学契约、回退 | landed |
| `docs/rounds/r003-end-room-entry/changes.md` | 轮次 | 文件 × 模块 × 页面锚点 + cp 台账 + 用户消息台账 | planned |
| `docs/rounds/r003-end-room-entry/review.md` | 轮次 | 阶段 3 对账报告 + 两栏处置清单 | planned |
| `docs/00-requirements/README.md` | 索引 | 新增 r003 行；r002 行转 closed | landed |
| `docs/00-requirements/r002-livekit-room.md` | 契约 | frontmatter 转 closed + 收官变更记录 | planned（cp-r003-1） |
| `docs/rounds/r002-livekit/review.md` | 轮次 | 按实测证据定稿（清掉「待核」） | planned（cp-r003-1） |
| `docs/00-project/global-roadmap.md` | 项目 | §3 M2 回填注 / §7 第 2/3 条 三处矛盾修正；§9 台账「缺结束入口」标已闭合 | planned（cp-r003-1） |
| `docs/02-modules/r002-livekit-features.md` | 模块（功能） | §4.2 按钮矩阵、§4.5 防呆条④、§4.9 分工、§6 第 10 步 | planned（cp-r003-2） |
| `docs/02-modules/r002-livekit.md` | 模块（实现） | 变更记录一行 + 路由/交互点回填 | planned（cp-r003-2） |
| `docs/04-style/global-style.md` | 风格 | 令牌表新增 `--live-end-*`；§12.1 离场段一句 | planned（cp-r003-2） |
| `docs/tutorials/r002-livekit-demo.md` / `r002-livekit-setup.md` | 教学（使用者） | 第 9 步改走控制坞；两处入口描述同步 | planned（cp-r003-3） |
| `docs/glossary.md` | 术语 | 无新增术语（「结束房间」沿用既有词条） | landed |

## 7. 风险与不确定

- **真机取证依赖你本机的 dev 服务与账号**（`5173` + `8000`、`host@example.com` / `part@example.com`，口令 `demo1234`）；我不另起端口、不反复 build。
- **LiveKit Cloud 可达性**：`end` 会调 `delete_room`；若 Cloud 不可达，后端按 ADR-0011 条 5 记 `livekitApplied=false`，库侧仍 `ended`。验收时如实记录该字段，不把「库侧结束」说成「实时也断开」。
- **误触风险**：房主只有一个危险动作且需二次确认 + 不绑快捷键；确认框 Esc 可退（沿用 F-16 防呆）。
- **不确定项**：`PhoneOff` 图标是否合你眼缘（备选 `CircleStop`，改一行 import + 一处标签）；确认框是否该显示「有人还在房间里」的提示（当前不做，若要另议）。

## 8. 实施顺序（cp 表）

| cp | 内容 | 验证门禁 |
| --- | --- | --- |
| `cp-r003-1` | r002 收官回填（§2 第 1 项，纯 docs） | 文档自检（无「待核」残留 / 索引与 roadmap 一致）+ `git status` 干净 |
| `cp-r003-2` | 房主结束房间入口（代码 + 文档同提交） | `npx tsc --noEmit` + `npm run build` + `pytest backend/tests -q`（95 passed） |
| `cp-r003-3`（**完成 2026-09-19**） | 真机取证 + 教学页实跑 + 审查报告 | V1~V11 逐条有证据（见 `review.md` §1；V4 为接口+平台级） |

## 9. 变更记录

| 日期 | 轮次 | 变更 | 依据 |
| --- | --- | --- | --- |
| 2026-09-19 | r003 | 建轮：需求单与轮次设计（阶段 1） | 用户「这个加入003，开始003」；redirect-07 confirmed-A |
| 2026-09-19 | r003 | 追加：`dev.bat` 一键启动环境（redirect-01，C 追加） | 用户「写个一键启动环境的脚本」 |
| 2026-09-19 | r003 | 收官：cp-r003-1/2/3 完成，验收 V1~V11 逐条取证 | 用户「ab按现在，直接开始」 |
