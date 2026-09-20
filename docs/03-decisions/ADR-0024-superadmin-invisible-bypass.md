---
title: ADR-0024 超管隐身（hidden Token + 在册旁路）与旁路校验收敛；容量口径仍按在册成员
description: 超管身份落在 users.role、不写 room_members 改记 room_visits、Token 关发布权限、旁路只改两个权限函数；以及在册/容量不变量的表述。
type: reference
status: accepted
owner: 陀梓皓
updated: 2026-09-20
---

<!-- overview -->
背景：r012 要一类「能进任何房间（含满员）、能行使任一房间房主能力、但对其他参与者不可见、不计入人数」的平台身份。用户 2026-09-20 口述原话见 `docs/rounds/r012-superadmin-console/redirect-01.md` §1；按编号批复见需求单 §10.1（Q1=1 / Q2=1 / Q3=1 / Q4=1＋补充 / Q8=1＋补充）。本 ADR 记录这次口径；**与既有裁决的关系：ADR-0016（容量按本库在册成员）继续有效**，本 ADR 只补充「超管不属于在册成员」。

## 事实（实测）
1. `livekit-api==1.2.1` 的 `VideoGrants` 含 `hidden` 字段，注释原文「participant is not visible to other participants」；`AccessToken.with_attributes(dict[str, str])` 存在（`site-packages/livekit/api/access_token.py`，2026-09-20 实测）。
2. 迁移 011 应用后：`users.role` / `users.last_seen_at` 落库，`room_visits` / `global_messages` / `admin_audit` 建表；`db_init.py --seed` 打印 `schema_migrations 12`。
3. 权限地基实测只有两个函数：`services/rooms.py::assert_room_role`（踢人/改角色/移交/结束）与 `assert_manager_role`（看待批申请/纪要可见性）；其余治理动作全走它们。

## 决定
### D1 超管身份 = `users.role`（单列，不做独立表、不做 .env 白名单）
理由：判定点少（一处查询即得），不引入 join；`.env` 白名单做不到"改权限即生效"且会与"身份属于数据"混层。

### D2 隐身 = 两条一起用：**不写 `room_members`**（改记 `room_visits`） + **Token 带 `hidden=True`**
理由：`room_members` 是本库权限/人数/成员列表的唯一来源，不写它 → 成员列表、人数、待批可见性天然不含超管（应用层隐身）；`hidden` 让 LiveKit 侧其他参与者**根本看不到**他（传输层隐身）。两者缺一都会露馅。

### D3 超管**不发布音视频**（Token `can_publish=False`、`can_publish_data=False`，界面不渲染设备控件）
理由（用户原话）：「音频是靠 livekit 的，为了节约额度，超管不能说话和视频，只能管理」。副作用一并接受：超管没有音频轨 → 转写 worker 的 `_has_audio` 判据自然跳过；再加 `attributes={'lg-role': 'superadmin'}` 作双保险。

### D4 旁路校验**只在两个函数里开口**，判据唯一入口 `services/roles.py`
`assert_room_role` / `assert_manager_role` 见超管即放行（房间不存在仍 404）；超管拿到的是一个**不落库的虚拟成员行**（`role='host'`，仅用于满足既有调用点的读取需求）。禁止在各调用点散加 `if is_superadmin`。

### D5 容量口径：**在册 = `room_members(status='active')`，超管不在其中**
因此 ADR-0016 的不变量「在册数 ≤ 容量」在超管在场时依旧成立，无需为超管改容量判定；反过来说，**超管不被计入「人数」**正是"不写 `room_members`"的自然结果，不需要额外排除逻辑。

### D6 管理动作留痕：`admin_audit`（不 FK 到 `rooms`）+ 房内系统消息
理由：删房后流水必须还在 → `target_id` 允许悬空（快照写进 `detail`）；房内系统消息署名「管理员」（Q3=1），不暴露超管账号身份。

## 用户批复（2026-09-20）
- 原话（Q4/Q8 补充）：「音频是靠 livekit 的，为了节约额度，超管不能说话和视频，只能管理！」
- 原话（Q3=1）：成员列表 / 舞台 / 在线口径都不出现，管理动作产生的消息署名「管理员」。

## 备选与否决
| 备选 | 否决理由 |
| --- | --- |
| 独立表 `super_admins` | 每次角色判定多一次 join；本项目只有一个额外角色，收益不足 |
| `.env` 白名单邮箱 | 改权限要重启进程；且身份属于数据（可审计），不该藏在进程环境里 |
| 写 `room_members` 但在计数与列表里排除超管 | 排除点会散落到所有查询（列表/人数/待批/名册/前端），漏一处就是"隐身失败" |
| 只靠前端过滤超管（不加 `hidden`） | 其他客户端仍能从 LiveKit 参与者列表看到他，隐身只剩一半 |
| 让超管照常开麦、只在转写侧过滤 | 与「节约额度」的原始要求相反（音视频本身计费） |

## 落地与验证（cp-3 实测）

| 主张 | 证据（可复跑） |
| --- | --- |
| D2 隐身（应用层） | 用例 `test_superadmin_token_is_hidden_readonly_and_records_visit`：超管取票后 `room_visits` 有且只有一条开着的记录；房间详情 `memberCount == 1`、成员列表里没有他 |
| D2 隐身（传输层） | 同一用例解 JWT：`video.hidden is True`、`attributes == {'lg-role': 'superadmin'}` |
| D3 不发布 | 同一用例：`video.canPublish is False`、`video.canPublishData is False`、`roomAdmin` 非真 |
| D5 不占人数 | 用例 `test_superadmin_enters_full_room_while_stranger_cannot`：满员房（在册 = 8）超管取票 200、取票前后 `memberCount` 恒为 8；路人 403 `NOT_MEMBER` |
| D4 旁路治理 | 用例 `test_superadmin_kicks_and_ends_other_peoples_room`：超管踢人与结束**他人**房间均 200，且房内留下「被移出房间」「房间已结束」系统消息；`test_plain_participant_still_cannot_govern`：普通参与者同动作仍 403 |
| 真机待办 | 2 浏览器验证「另一端 participants / 舞台 / 名册看不到超管」属人工/真机项，登记在 cp-7（E2） |

## 落地与验证 · 补充（cp-7b 真机）

`backend/scripts/verify_r012_superadmin_invisible.py`（PASS 17/17）在**真 Chrome** 里复核了「隐身」的两层：

- 界面层：成员端舞台格数、在册人数、成员抽屉在超管进房前后**完全不变**，抽屉里没有「平台管理员」；
- **媒体层（决定性的那一层）**：LiveKit 服务端 `list_participants` 显示超管 `hidden=true`、`canPublish=false`、
  `canPublishData=false`、`attributes={'lg-role':'superadmin'}`、`tracks=[]`——即使绕过前端也发不出音视频、也不会出现在别人的参与者列表里。

## 影响面
- 代码：`services/roles.py`（新增）、`services/rooms.py`（两处旁路 + 取票分支，cp-3）、`services/livekit.py::issue_token`（新增 `hidden`/`attributes`/`can_publish*` 参数，cp-3）、`agents/transcriber.py`（跳过超管，cp-3）。
- 文档：`docs/02-modules/r012-superadmin-console.md`（模块页）、需求单 §1/§10.1、`docs/04-style/global-style.md`（管理视角标识的文案口径，cp-6）。
- 无迁移回退风险：011 全为新增列/表，回退（revert）后旧代码照常工作。
