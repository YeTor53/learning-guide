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
| cp-r004-2 | r003 收官回填 + `smoke.py` 补 r002 四步 | planned | — | 索引表 r003 转 closed；smoke `PASS n/n` |
| cp-r004-3 | 界面缺陷两项（侧边栏竖屏 + 筛选条上移）+ ADR-0015 | planned | — | 720×1024 / 1258×566 截图对比 |
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
| `docs/03-decisions/r004-adr-0015-home-first-screen.md` | 决策 | 首页首屏口径（筛选条上移） | 自身 | planned（cp-3） |
| `backend/app/db/sql/004_r004_realtime_extras.sql` | 数据层 | `room_hand_raises` + `room_focus` | 实现页 §3 | planned（cp-4） |
| `backend/app/services/{messages,hands,focus}.py` | 后端 | 三组能力的服务函数 | 实现页 §5 | planned（cp-4） |
| `backend/app/api/routers/room_extras.py` | 后端 | 8 个路由 | 实现页 §4 | planned（cp-4） |
| `backend/app/services/rooms.py` | 后端 | `end_room` 连带清举手 | 实现页 §3 | planned（cp-4） |
| `backend/tests/test_room_extras_api.py` | 测试 | E1~E6 用例 | 实现页 §9 | planned（cp-4） |
| `frontend/src/hooks/{useDataChannel,useChatMessages,useHandRaise,useRoomFocus,useScreenShare}.ts` | 前端 | 实时层 | 实现页 §5.5 | planned（cp-5） |
| `frontend/src/api/roomExtras.ts` | 前端 | HTTP 封装 | 实现页 §4 | planned（cp-5） |
| `frontend/src/components/live/{ChatPanel,MessageBubble,FocusBadge}.tsx` | 前端 | 新组件 | 功能页 F-18~F-21 | planned（cp-6） |
| `frontend/src/components/live/{RoomSidePanel,DeviceBar,LiveStage}.tsx`、`pages/RoomLivePage.tsx` | 前端 | 抽屉双 tab / 新按钮 / 优先级 / 装配 | 功能页 §4.2 按钮矩阵 | planned（cp-6） |
| `frontend/src/styles/global.css` | 风格 | 3 个令牌 + 2 处动效 | 风格指南 §12.1 | planned（cp-6） |
| `backend/scripts/smoke.py` | 脚本 | 补 r002 四步 + r004 三步 | README / AGENTS `<check>` | planned（cp-2/7） |
| `docs/tutorials/r004-room-extras.md` + `r002-livekit-dev-guide.md` 补节 | 教学 | 使用者 + 开发者 | 自身 | planned（cp-7） |
| `README.md` / `AGENTS.md` / `global-roadmap.md` / `00-requirements/README.md` / `glossary.md` | 项目级 | 状态、命令、台账、术语 | 自身 | planned（散在 cp-2/6/7） |

## 3. 用户消息台账（首行回执的核对凭据）

| 序号 | 日期 | 用户原话摘要 | 回执分类 | 单号 |
| --- | --- | --- | --- | --- |
| 1 | 2026-09-19 | 「r004」 | 新方向 · 开轮请求（需澄清） | — |
| 2 | 2026-09-19 | 「我合并了的。1 1 1 1 1 1 2 1 1」 | 批准（W1/W2：r003 已合并 + 答 Q1~Q9，含 Q7 改口并进本轮） | r004 需求单 §3 |

## 4. 无文档变更的提交（若有）

（实现期若某步确实无对外行为变化，在此登记一行并说明原因。）
