---
title: r008 实现页：讨论纪要 + 限时邀请
description: 纪要（素材→LLM→落库、失败留痕）与限时邀请（6 位码、最长 1 分钟、凭码直接进）的决定性事实源，含实现期踩坑与验证数字。
type: reference
status: draft
owner: 陀梓皓
updated: 2026-09-19
---

<!-- overview -->
需求与验收见 `docs/00-requirements/r008-assignment-gaps.md`；设计见 `docs/rounds/r008-assignment-gaps/design.md`；决定见 ADR-0018（纪要）/ADR-0019（邀请）。语音转文字已移至 r010。

## 1. 讨论纪要（`session_summaries`）

| 面 | 位置 | 要点 |
| --- | --- | --- |
| 表 | 迁移 `007_r008_session_summaries.sql` | 一间房一份（`ux_session_summaries_room`）、`status ready/failed`、时间戳 `clock_timestamp()`（语句级） |
| 服务 | `services/summary.py` | `build_summary_input`（复用 `rooms.get_room_detail` 组装房间+成员+最近 200 条消息）、`render_messages`（system 写死「不编造」要求）、`generate_summary`、`get_summary`、`call_llm` |
| 唯一 LLM 出口 | `call_llm`（aiohttp，60s） | 未配置 → `LlmNotConfigured`；非 200/空内容 → `LlmError`；`client=` 可注入打桩 |
| 失败语义 | 三分支 | 未配密钥 **503 `LLM_NOT_CONFIGURED` 且不落库**；调用失败 **502 `SUMMARY_FAILED` + 落 `failed` 行记 error**；成功 `ready` |
| 路由 | `api/routers/summary.py` | `POST/GET /api/rooms/{id}/summary`（生成仅 Host/Moderator；查看限成员/管理身份） |
| 前端 | `pages/RoomSummaryPage.tsx`（`/rooms/:id/summary`） | 已结束房间卡「讨论纪要」入口；正文 `pre-wrap`；未配密钥给**明确指引**；错误提示走显式状态（避免依赖 `mutation.error` 引用） |
| 权限细节 | `RoomVO.my_role_any` | **房间结束后成员行变 `inactive` → `myRole` 为空**，前端判断不出权限；新增只读字段保留历史身份（后端 `assert_manager_role` 本就支持结束态追溯） |

## 2. 限时邀请（`invites`）

| 面 | 位置 | 要点 |
| --- | --- | --- |
| 配置 | `app/config.py` | `INVITE_TTL_MAX_SECONDS`（默认 60，启动期校验 10~86400）——「最长 1 分钟」是一个数 |
| 服务 | `services/invites.py` | `create_invite`（Host/Moderator、房间 active、ttl 10~上限、max_uses 1~50；6 位小写码 + 唯一索引 + savepoint 重试 3 次）、`accept_invite`、`list_invites` |
| 校验顺序（**踩坑**） | `accept_invite` | 必须「码有效且房间在用 → **已在册优先幂等放行** → 再查过期/用尽」；最初把幂等放最后，导致老成员再点链接被「邀请已用完」挡住（用例实测 400 → 修正） |
| 加入语义 | 直接成为在册成员 | 跳过等候室（邀请=房主已同意）；**满员仍 409 `ROOM_FULL`**；写系统消息「X 通过邀请链接加入」 |
| 路由 | `api/routers/invites.py` | `POST/GET /api/rooms/{id}/invites`、`POST /api/invites/{code}/accept`（幂等 200） |
| 前端 | `components/live/InvitePanel.tsx` + `pages/JoinByCodePage.tsx` | 抽屉第三 tab「邀请」（仅管理身份）：30/60 秒与次数、生成、复制 `/join?code=`、每秒倒计时；凭码页预填 + 加入后直接进交流页 |

## 3. 验证数字（2026-09-19）

| 项 | 结果 |
| --- | --- |
| 纪要真机 | 房主在已结束房间生成 → **6.0 秒 / 632 字 / 五节齐全**；素材只有系统消息时模型写「未展开、不能代为补写、记为无记录」（反编造生效）；按钮随后变「重新生成」 |
| 邀请真机 | 抽屉「邀请」tab → 生成码 `zqddjt`（**29 秒后过期 · 已用 0/1**）→ 客人 `/join?code=` 预填 → 加入直接进房 → 成员数 1→2 且系统消息「客人乙 通过邀请链接加入」 |
| 用例 | `pytest` **124 passed**（新增纪要 6 条 + 邀请 5 条） |
| 冒烟 | `smoke` **PASS 46/46**（新增：建房（邀请房）/生成邀请码 6 位/凭码加入 201/再点幂等 200/生成纪要 ready（实测 559 字）/查看纪要） |
| 前端 | `tsc` / `build` exit 0 |

## 4. 遗留与边界（如实）

1. 「结束后自动生成纪要」没做：按设计只在结束页/详情页**一键生成**（避免外部调用失败污染结束流程）；如要自动，建议加一条后台任务。
2 纪要无版本历史：覆盖式重生（ADR-0018 已写明取舍）。
3. 邀请码只有 6 位（=房间码字符集），有效期极短（≤60 秒）时碰撞概率可忽略；如要更长码改 `security/ids.py` 一处。
4. uvicorn `--reload` 在 Windows 上偶发自崩（`os.kill` SystemError）——与产品代码无关，影响的是开发体验；本机起服务请用 `dev.bat` 或去掉 `--reload`。

## 变更记录

| 日期 | 轮次 | 变更 | 依据 |
| --- | --- | --- | --- |
| 2026-09-20 | r013 `cp-5` | 结束房**回看页**（`/rooms/:id/replay`）：时间线（聊天+系统消息+转写）/ 纪要 / 成员三段只读；列表页 ended 房卡新增「回看」（原「讨论纪要」保留）。可见性沿用本模块既有口径（成员/历史成员/房主/协管） | r013 需求单 E7~E9；`test_replay_access.py` + 真机 |

| 日期 | 轮次 | 改了什么 | 回链 |
| --- | --- | --- | --- |
| 2026-09-20 | r009.5 | 补正（无行为变更）：r008 讨论纪要（LLM）· 限时邀请（≤1 分钟、6 位码、凭码直接进） 的台账/审查回填、轮次号与死链纠错、索引回填；实现页所述行为未改 | `docs/rounds/r009.5-debt-backfill/`；`docs/00-requirements/r009.5-debt-backfill.md` |
