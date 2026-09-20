---
title: r011 台账（changes）：cp 切分、门禁数字与逐处改动
description: 本轮每处改动的「现在 → 改成 → 依据」与四项门禁实测数字；cp-1 为阶段 1 文档。
type: reference
status: draft
owner: 陀梓皓
updated: 2026-09-20
---

<!-- overview -->
行号基准 `main` = `96b1153`。数字标注「本轮实测」或「历史（引 changes/提交）」。

## 1. cp 台账

| cp | 内容 | 状态 | 提交 | 验收点 |
| --- | --- | --- | --- | --- |
| cp-r011-1 | 阶段 1 文档：需求单 + design（逐文件清单）+ 人工剧本（MV-1~MV-9）+ 台账/审查骨架 + 需求索引行 | **完成 2026-09-20** | 见 cp-1 提交 | 文档先行 |
| cp-r011-2 | A 组项目级活页：README 状态与数字 + 演示路径补转写/焦点步；AGENTS.md 数字与容量口径；覆盖页整页重写去重 | **完成 2026-09-20**（2 提交：`fe336e2`、`4f361eb`） | 见 cp-2 提交 | E1 |
| cp-r011-3 | A 组轮次台账与验收清单回勾：r002 §4 **36 条**（[x] 32 / [~] 4 转 MV-1/MV-8/MV-10）、r005 §5 **8 条**（[x] 7 / [~] 1）、r006 语录数字口径注、r010 §6 矩阵补回归脚本、人工剧本加 MV-10 | **完成 2026-09-20** | 见 cp-3 提交 | E1/E2/E3/E9/E10 |
| cp-r011-4 | B 组功能增量：满员自动拒待批申请（批量 `rejected` + 汇总系统消息）+ 邀请码入口（顶栏常驻）与未登录 `returnTo` 闭环 + 等待页文案 + 使用者教学页 | **完成 2026-09-20** | 见 cp-4 提交 | E4/E5 |
| cp-r011-5 | B 组 worker 健康上报 + C 组用例（`STT_MODE=off`、满员自动拒） | 待做 | — | E6/E7 |
| cp-r011-6 | 门禁与取证收官：四项门禁 + 索引/矩阵回填 + review 定稿 | 待做 | — | E8/E9 |

## 2. 门禁数字

| cp | pytest | smoke | tsc --noEmit | npm run build |
| --- | --- | --- | --- | --- |
| cp-0（进入本轮前，历史） | 156 passed（r010 review §5b） | 46/46（历史） | exit 0（历史） | exit 0（历史） |
| cp-1/1b（纯文档） | 未跑（无代码改动） | 未跑 | 未跑 | 未跑 |
| cp-2/3（纯文档） | 未跑（无代码改动） | 未跑 | 未跑 | 未跑 |
| cp-6（收官，待填） |  |  |  |  |

## 3. 逐处改动（现在 → 改成 → 依据）

（cp-2 起逐格填写；格式：`文件` → 现在是什么 → 改成什么 → 依据）

## 3.1 cp-3 回勾统计（实测）

| 文件 | 条目 | [x] | [~] 转人工剧本 |
| --- | --- | --- | --- |
| `docs/00-requirements/r002-livekit-room.md` §4 | 36 | 31 | 5（MV-1 ×2、MV-8、MV-10 ×2，另有 3 条按新口径标注） |
| `docs/00-requirements/r005-fix-capacity.md` §5 | 8 | 7 | 1（MV-10） |

## 3.2 cp-4 逐处改动（本轮实测）

| 文件 | 现在 → 改成 | 依据 |
| --- | --- | --- |
| `backend/app/repositories/rooms.py` | 新增 `reject_pending_requests(conn, room_id, decided_by, at)`：批量把该房 `pending` 申请置 `rejected` 并返回行数（与 `cancel_pending_requests` 的区别是状态语义为「被拒」） | r011 B1 |
| `backend/app/services/rooms.py` | 新增 `_auto_reject_pending(conn, room, actor)`：批量拒绝 + 一条汇总系统消息（0 条不写）；`request_join` 满员分支调用；`approve_join_request` 满员分支改为「**先提交清理、出事务后再抛 409**」（原实现 raise 会回滚，清理会作废） | r011 B1 + design §5 边界 |
| `frontend/src/pages/WaitingPage.tsx` | rejected 文案补「或房间已满被系统自动拒绝」 | r011 B1 |
| `frontend/src/components/NavBar.tsx` | `top-actions` 增常驻 `邀请码加入` → `/join`（未登录也可见） | r011 B2 |
| `frontend/src/pages/JoinByCodePage.tsx` | 未登录时主按钮改「去登录并加入」（跳 `/login?returnTo=/join?code=…&auto=1`）；带 `auto=1` 回来在登录后**自动加入一次**（`useRef` 防重复） | r011 B2 |
| `docs/tutorials/r011-invite-entry-and-capacity.md` | 新增使用者教学页（两条入口路径 / 未登录闭环 / 满员口径） | 覆盖矩阵 C 件套 |

## 4. 未做 / 如实说明

- 本轮**不含** r012（超管 / 管理后台 / 全服大屏聊天）、部署与录屏、录制的实现。
- 演示库残留按你口径「开发结束后统一清」，本轮只登记不执行。
- 人工剧本 MV-1~MV-9 由你执行；未跑之前本轮相关验收条目一律标「未取证」。

## 5. 分支与交接

| 项 | 值 |
| --- | --- |
| 分支 | `req/r011-debt-backfill`（从 `main` = `96b1153` 开出） |
| 进入本轮前的 `main` | `96b1153`（`round-r010-done`；r005~r010 + r009.5 均已合并、tag 齐） |
| 合并顺序 | 本轮从最新 main 开出 → 合入时无前置未合并轮次 |
