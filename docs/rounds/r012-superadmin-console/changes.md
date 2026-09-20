---
title: r012 变更台账（cp 逐格记录）
description: r012（超管 · 管理后台 · 全服大屏聊天）的提交台账、门禁数字、用户消息回执台账与实测留痕位；cp-1 建骨架，逐 cp 追加。
type: reference
status: draft
owner: 陀梓皓
updated: 2026-09-20
---

<!-- overview -->
本页与实现**同提交**逐行追加（AGENTS.md 硬规矩 6：文档与代码同一次提交）。cp-1 建骨架，此后每个 cp 追加一行并填门禁数字。
分支 `req/r012-superadmin-console`；基点 = `req/r011-debt-backfill` @ `ab8edb5`（cp-7）。tag 逐个 cp 打 `cp-r012-N`。

## 1. cp 台账

| cp | 提交 | 内容 | 门禁数字（pytest / smoke / tsc+build） | 依据 |
| --- | --- | --- | --- | --- |
| cp-r012-1 | 本次提交 | 阶段 1 文档：需求单 + design + changes/review 骨架 + 轮次索引行 + `redirect-01` 指针 | 不适用（纯文档，未跑门禁；代码门禁从 cp-2 起） | 需求单 §9 |
| cp-r012-1b | 本次提交 | 阶段 1 批复登记：Q1~Q18 落地（需求单 §10.1）+ 按批改写 design（只管理不发布音视频 / 右侧 Copilot 式面板 / 前端短轮询心跳）+ 把 r011 收尾提交 `cp-8`/`cp-8b` merge 进本分支（`e0c6598`） | 不适用（纯文档） | 需求单 §10.1 |
| cp-r012-2 | | 迁移 011 + 身份（`role`/`last_seen_at`）+ 在线心跳（`POST /api/presence` + `usePresenceBeat`）+ 提权脚本/seed 超管 + ADR-0024 + 模块实现页首版 | | E1/E14 |
| cp-r012-3 | | 超管隐身进房（hidden Token + `room_visits` + 旁路校验收敛）+ 用例 | | E2/E3/E4/E10 |
| cp-r012-4 | | 管理后台后端（三列表 + 三动作 + 审计）+ 用例 | | E5/E6 |
| cp-r012-5 | | 大屏聊天 + SSE 后端 + 限流 + ADR-0025 + 用例 | | E7/E8 |
| cp-r012-6 | | 前端 `/admin` + 大屏面板 + 入口 + 超管视角 + 视觉参数区 + 教学两页 + 模块功能页 | | E5/E9/E12 |
| cp-r012-7 | | 门禁复跑 + 真机取证 + 视觉对账 + 文档回填 + review 定稿 | | E11/E12 |

## 2. 用户消息台账（vibecoding 8.1 判据：每条用户消息一行回执）

| # | 用户原话摘要 | 回执分类 | 单号 | 处置 |
| --- | --- | --- | --- | --- |
| 1 | 「设计LearnGuide项目的r012」 | 新轮次设计请求（沿用已登记 `redirect-01`） | — | 出阶段 1 文档（cp-1）+ `ASK-r012-1` 待批 |
| 2 | 「1 1 1 1 1 1 1 1（…超管不能说话和视频，只能管理！） 1 1 2（右侧的侧栏打开窗口，像编译器里的 coplit） 2（只 admin 可见） 1 2（短轮询） 1 1 1 1」 | 澄清回答（W2，答 `ASK-r012-1` 全 18 项） | — | 批复落需求单 §10.1 + 按批改 design（cp-1b）；两条口径补充记入 Q4/Q8 行 |

## 3. 实测数字与留痕（逐 cp 追加，禁占位）

| 项 | 命令 / 做法 | 实测 | 时间 |
| --- | --- | --- | --- |
| 阶段 1 文档落盘 | `ls docs/rounds/r012-superadmin-console` | 4 个文件：`design.md` / `changes.md` / `review.md` / `redirect-01.md`（+ 需求单 1 个）；cp-1 `0192e25`、cp-1b（本次） | 2026-09-20 |
| 迁移 011 后表/列 | `python backend/scripts/db_init.py --reset --seed` 输出行数 | 待填（cp-2） | |
| 门禁四项 | `pytest backend/tests -q` / `smoke.py` / `tsc --noEmit` / `npm run build` | 待填（cp-7；基线 r011：pytest 164 / smoke 47-47 / tsc·build exit 0） | |
| 隐身真机 | 2 浏览器：成员列表 / 舞台 / 人数 | 待填（cp-3） | |
| SSE 真机 | `curl -N http://127.0.0.1:8000/api/events` + 另一客户端发大屏消息 | 待填（cp-5） | |

## 4. 变更记录

| 日期 | 版本 | 改了什么 | 依据 |
| --- | --- | --- | --- |
| 2026-09-20 | 骨架（cp-1） | 建页：cp 台账骨架 + 用户消息台账 + 实测留痕位 | 需求单 §9；vibecoding 8.1 判据 |
| 2026-09-20 | cp-1b | 登记阶段 1 批复（Q1~Q18）与两条补充口径；cp 台账加 cp-1b 行、台账加用户消息 #2；并入 r011 `cp-8`/`cp-8b` | 用户 2026-09-20 批复 |
