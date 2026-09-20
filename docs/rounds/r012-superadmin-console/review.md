---
title: r012 审查报告（骨架，cp-7 定稿）
description: r012 的验收逐条对账、规则核对、覆盖矩阵对账、视觉对账五组、重定向对账与两栏处置清单；cp-1 建骨架。
type: reference
status: draft
owner: 陀梓皓
updated: 2026-09-20
---

<!-- overview -->
本页 cp-1 只立**表头与判据位**（防止「先实现、事后补理由」）；cp-7 按实测逐格填，未取证一律写「未取证 + 原因」，禁空口「已实现」。
审查两轴：模块轴（设计页/模块页/使用者教学页/开发者教学页）+ 轮次轴（本目录 design/changes/review/CR/redirect）。

## 1. 验收逐条对账（E1~E12）

| # | 条目 | 实现位置 | 证据（命令输出 / 用例名 / 截图） | 结论 |
| --- | --- | --- | --- | --- |
| E1 | 超管身份落地 | `backend/app/db/sql/011_*.sql`、`012_*.sql`；`services/roles.py`；`repositories/users.py`；`schemas/auth.py::UserVO.role`；`scripts/grant_superadmin.py` | `db_init.py --seed` → `schema_migrations 12` + `room_visits/global_messages/admin_audit`；`grant_superadmin --email host@example.com` → `user → superadmin（影响 1 行）`、`--revoke` → 反向；`/api/auth/me` 返回 `role`（用例 `test_superadmin_identity.py` 6 条） | cp-2 通过（cp-3 起进入隐身与旁路，届时复核） |
| E2 | 隐身进房 | `services/rooms.py::issue_room_token`（超管分支）+ `repositories/rooms.py`（`room_visits` 读写）+ `services/livekit.py::issue_token` | 用例：JWT `hidden=True`；`room_visits` 恰好一条开启记录；房间详情 `memberCount` 不变、成员列表无超管 | 后端侧通过；**真机 2 浏览器待 cp-7** |
| E3 | 房主能力 | `assert_room_role`/`assert_manager_role` 超管旁路（`services/rooms.py`） | 用例 `test_superadmin_kicks_and_ends_other_peoples_room`（踢人 + 结束他人房间 200、`livekitApplied` 打桩为真、房内系统消息留下）+ `test_superadmin_sees_pending_requests_of_foreign_room`（待批可见且列表 200） | 通过（后端）；真机复核待 cp-7 |
| E4 | 不计入人数 | 超管不写 `room_members`（`room_visits` 旁路） | 用例 `test_superadmin_enters_full_room_while_stranger_cannot`：在册 8/8 时超管取票 200 且 `memberCount` 恒 8；既有满员用例（409 `ROOM_FULL`）全绿未回归 | 通过 |
| E5 | 管理后台三列表 | `backend/app/repositories/admin.py`、`services/admin.py`、`routers/admin.py` | 用例 `test_admin_api.py` 9 条：房间列表（房主名/人数/待批/纪要状态、`q` 过滤、`status` 过滤、`limit/offset` 分页）、用户列表（角色/心跳/`online_only=1` 过滤）、纪要列表（房间标题/字数）、审计初始为空 | cp-4 通过（真机页面待 cp-6） |
| E6 | 管理后台动作 + 审计 | `services/admin.py::end_room/delete_room/regenerate_summary` + `repositories/admin.py::insert_audit/get_room_snapshot` | 用例：结束他人房间 200 且 `room.end` 审计 + 房内「房间已结束」；硬删 200（`deleted/livekitApplied`）、房间行消失、消息级联删、审计 `detail.snapshot` 保留标题与消息数；重生纪要 201 + `room.summary_regenerate` 审计；未知房间 404 且不写审计 | cp-4 通过（后台页面交互待 cp-6） |
| E7 | 大屏聊天（500 字 / 限流 / 落库） | `backend/app/repositories/global_chat.py`、`services/global_chat.py`、`api/routers/global_chat.py`、`schemas/global_chat.py` | 用例：未登录可读/不可发（401）；正序返回 + `before_id` 游标；`authorOnline` 随心跳变化；空串/501 字 400、500 字 201；限流第 N+1 条 429 且落库条数 == 上限 | cp-5 通过（真机面板待 cp-6/7） |
| E8 | SSE 通道与兜底 | `backend/app/services/events.py`、`api/routers/events.py` | 用例：路由在 `/api/events`；响应头 `text/event-stream`/`no-store`/`X-Accel-Buffering: no`；首帧 `retry: 3000`；publish → `event: notify` + `{"type","payload"}`；`encode_sse(None)` 为 `: ping`；订阅上限 503；发言后发布会推事件 | cp-5 通过（前端 EventSource + 30 秒轮询兜底待 cp-6/7 真机） |
| E9 | 管理动作留痕 | 房内系统消息（`services/rooms.py::_system_message`）+ `admin_audit`（`services/admin.py::_audit`） | 用例：超管结束/踢人在房内留下「房间已结束」「被移出房间」；后台三动作各写一条审计（含删除后仍保留的快照） | cp-4/cp-5 通过；「超管平时不留痕」的真机截图待 cp-7 |
| E10 | 超管音频不进转写 | `agents/transcriber.py::_maybe_start`（`lg-role` 跳过）+ Token 无发布权限 | 代码事实：超管 Token `canPublish=False`（无音频轨 → worker 的 `_has_audio` 已挡）+ `lg-role` 双保险；pytest 182 无回归 | 代码侧通过；真机（超管开麦 → 无转写）待 cp-7 |
| E11 | 门禁与视觉对账 | — | cp-6 实测：`tsc --noEmit` exit 0、`npm run build` exit 0（2022 modules）；令牌扫描 0 命中（本轮 17 个改动文件，排除 `global.css` 参数区）、emoji 0、单一图标库 0 违规 | **部分**：pytest/真机/五组视觉证据在 cp-7 补齐 |
| E12 | 文档 = 代码 | 教学页 `tutorials/r012-admin-and-global-chat.md`（使用者）+ `tutorials/r012-superadmin-dev-guide.md`（开发者）；功能页 `02-modules/r012-superadmin-console-features.md`；实现页 §6 前端；`04-style` §12.4 | 教学两页与功能页已落，索引 `tutorials/README.md` 已加两行 | 进行中（cp-7 定稿并跑教学页示例） |
| E13 | 超管只管理、不发布 | Token 侧：`services/rooms.py::issue_room_token` 超管分支；界面侧：`RoomLivePage`（cp-6） | 用例断言 `canPublish=False`/`canPublishData=False`/`roomAdmin` 非真 | 后端侧通过；界面「无设备控件」待 cp-6 + cp-7 截图 |
| E14 | 在线心跳 | `backend/app/api/routers/presence.py`、`services/presence.py`、`config.py::presence_online_seconds`；`frontend/src/hooks/usePresenceBeat.ts`、`api/presence.ts`、`App.tsx` | 用例 `test_presence_api.py` 4 条（未登录 401 / 上报后 `last_seen_at` 前进且计入 `online_user_ids` / 600 秒前的心跳判离线 / 纯函数窗口）；`pytest` 174 passed | cp-2 通过（真机数字待 cp-7：浏览器 Network 里 60 秒一次的 `/api/presence`） |

## 2. 规则核对（AGENTS.md / docs/04-style/）

| 项 | 结论 | 证据 |
| --- | --- | --- |
| 未获批准的规划不做实现 | 通过 | cp-1/cp-1b/cp-1c 全是文档；第一处代码在用户 2026-09-20 回「开始」之后的 cp-2 |
| 一次提交 = 一个逻辑增量、`[Req: r012]` | 通过（cp-2） | `git log --oneline` 每行带 `[Req: r012]`；cp-2 = 身份 + 在线口径一个增量 |
| `git add` 只写具体路径 | 待填 | — |
| 密钥不入库 / Secret 不进前端产物 | 待填（cp-7 复跑扫描） | cp-2 未引入任何密钥字面量；提权脚本只打印邮箱/角色/行数（不打印任何凭据） |
| 未新增依赖 | 通过（cp-2） | `git diff --stat -- frontend/package.json backend/requirements.txt backend/requirements-dev.txt backend/requirements-agents.txt` = 空 |
| 界面硬条款（单一图标库 / 零 emoji / 禁内部词） | 待填 | 令牌与 emoji 扫描命令输出 |

## 3. 覆盖矩阵对账（无 `planned` 残留）

| 件套 | 路径 | 状态 |
| --- | --- | --- |
| 需求单 | `docs/00-requirements/r012-superadmin-console.md` | 本轮 |
| 设计页 | `docs/rounds/r012-superadmin-console/design.md` | 本轮 |
| 模块·实现页 | `docs/02-modules/r012-superadmin-console.md` | 首版 landed（cp-2：身份 + 在线），其余随 cp 补齐 |
| 模块·功能页 | `docs/02-modules/r012-superadmin-console-features.md` | landed（cp-6） |
| 使用者教学页 | `docs/tutorials/r012-admin-and-global-chat.md` | landed（cp-6） |
| 开发者教学页 | `docs/tutorials/r012-superadmin-dev-guide.md` | landed（cp-6） |
| ADR | `docs/03-decisions/ADR-0024-superadmin-invisible-bypass.md`、`ADR-0025-global-chat-and-sse.md` | 两个都已 landed（cp-2 / cp-5） |

## 4. 视觉对账（五组，缺一不通过）

| 项 | 命令 / 做法 | 实测 | 结论 |
| --- | --- | --- | --- |
| 令牌扫描 | `grep -rnE '#[0-9a-fA-F]{3,8}\|(padding\|margin\|gap\|font-size\|border-radius): *[0-9]+px' frontend/src --include='*.css' --include='*.tsx' \| grep -v global.css` | 待填（目标 0 行） | 待填 |
| 动效实测 | 读 `element.style.transform` / `getComputedStyle` 的过渡时长 | 待填 | 待填 |
| 降级复测 | 模拟 `prefers-reduced-motion: reduce` 后重测 | 待填 | 待填 |
| 截图 | 桌面 1440×900 + 窄屏 375×812 | 待填（`shots/`） | 待填 |
| 零 emoji / 单一图标库 | `grep -rnP '[\x{1F300}-\x{1FAFF}\x{2600}-\x{27BF}]' frontend/src`、`grep -rn 'react-icons\|@heroicons\|fontawesome\|feather' frontend/src` | 待填（目标 0） | 待填 |
| 几何量测 | `document.documentElement.scrollWidth === clientWidth`（后台表格不横向溢出） | 待填 | 待填 |

## 5. 重定向对账（vibecoding 8.1/8.2）

| 消息序号 | 首行回执分类 | 单号 | 单内状态 | 结论 |
| --- | --- | --- | --- | --- |
| 1 | 新轮次设计请求 | —（`redirect-01` 已登记，本 cp-1 出设计） | `redirect-01` status: proposed | 通过（grep `changes.md` 台账） |
| 2 | 澄清回答（W2，答 `ASK-r012-1` Q1~Q18） | —（无需确认单：白名单 W2） | 需求单 §10.1 已落批复 + 原话 | 通过：Q4/Q8 追加口径（只管理不发布音视频）、Q11=2、Q12=2、Q14=2 均已在 design 落地 |

## 6. 给用户处置的两栏（审查时填）

**本轮已落地可保留的增量**（各带 SHA 与文档页）：待 cp-7 填。

**未闭合 CR / 半成品清单**（含「若判为 C/D 如何处置」）：待 cp-7 填。

## 7. 合并指引（人执行）

1. 先合 r011（若尚未合）：`git checkout main && git merge --no-ff req/r011-debt-backfill`。
2. 再合 r012：`git merge --no-ff req/r012-superadmin-console`；打 tag `round-r012-done`。
3. 合并后复跑门禁四项，把数字回填本页 §1 与 `changes.md` §3。

## 8. 变更记录

| 日期 | 版本 | 改了什么 | 依据 |
| --- | --- | --- | --- |
| 2026-09-20 | 骨架（cp-1） | 建页：验收对账表 + 规则核对 + 矩阵对账 + 视觉五组 + 重定向对账 + 两栏位 + 合并指引 | 需求单 §4/§8；vibecoding 阶段 3 |
