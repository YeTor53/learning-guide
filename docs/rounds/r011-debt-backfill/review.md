---
title: r011 审查报告：欠账补正 + 三处授权例外 + 焦点规则收窄
description: E1~E11 逐条证据（2026-09-20 实跑数字）、规则/文档对账、人工取证清单、两栏清单与合并指引。
type: reference
status: draft
owner: 陀梓皓
updated: 2026-09-20
---

<!-- overview -->
**定稿**：cp-r011-7。需求单 `docs/00-requirements/r011-debt-backfill.md`；设计 `docs/rounds/r011-debt-backfill/design.md`；变更登记 `redirect-02.md`（说话不获焦点）；人工剧本 `manual-verification.md`（MV-1~MV-11）。

## 1. 验收对账

| # | 条目 | 证据（数字出处） | 结论 |
| --- | --- | --- | --- |
| E1 | A 组 4 类回填落地 | cp-2（`fe336e2`/`4f361eb`：README / AGENTS / 覆盖页重写）、cp-3（`a7d00e9`：r002 36 条 + r005 8 条 + r006 数字 + r010 矩阵）、cp-1（索引与 roadmap） | **通过** |
| E2 | r002 §4 36 条逐条有状态 | 36 条全部 `[x]` 或 `[~]`（32 勾 / 4 转剧本），每行带依据 | **通过** |
| E3 | r005 §5 8 条逐条有状态 | 8 条全部处理（7 勾 / 1 转 MV-10） | **通过** |
| E4 | 满员自动拒 | 用例 3 条（`test_room_full_auto_reject.py`：批量 rejected + 汇总系统消息、批准路径清理不被回滚、pending 列表清空）+ smoke 47/47 含新检查「满员时待批申请被自动拒绝留痕」；**真机肉眼**见 MV-9 步 4（未跑 → 部分） | **通过（用例+脚本）／真机未跑** |
| E5 | 邀请码入口 + `returnTo` 闭环 | 代码：`NavBar.tsx`（顶栏常驻入口）、`JoinByCodePage.tsx`（未登录→登录→回来自动加入，`useRef` 防重复）；`tsc`+`build` 绿；**人工**见 MV-9 步 1/2（未跑） | **通过（代码）／真机未跑** |
| E6 | worker 健康上报 | 用例 3 条（`test_stt_heartbeat.py`：错/缺令牌 401、本房与全局状态、无心跳为 null）；`/openapi.json` 端点 **34** 个（+2：`POST /stt/heartbeat`、`GET /rooms/{id}/stt-status`）；**人工**见 MV-9 步 5（未跑） | **通过（用例）／真机未跑** |
| E7 | `STT_MODE=off` 用例 | 2 条（`test_transcript_segments.py`：off 不派单、状态如实报 off） | **通过** |
| E8 | 门禁四项在最终树复跑 | `pytest backend/tests -q` → **164 passed**（51.06s）；`smoke.py` → **PASS 47/47**；`npx tsc --noEmit` → **exit 0**；`npm run build` → **exit 0**（2010 modules，4.00s） | **通过** |
| E9 | 文档 = 代码（无 `planned` 残留） | 本轮新增/回填页 `planned` 命中 **0**；`docs` 全量 60 处命中均为**已收官轮次的历史记录**（r003 覆盖矩阵「当时计划」等，按复验纪律不回改）；断链扫描 145 页 → 真死链 1 处（`docs/README.md` 的 `](*.md)` 通配符假阳性） | **通过** |
| E10 | 剧本交付 | `manual-verification.md`：MV-1~MV-11（MV-5 已作废并注明原因），每项含前置/步骤/判据/回填位/耗时 + 汇总表 | **通过（交付物）** |
| E11 | 焦点规则 = 共享 > 手动焦点 > 自己（说话不参与） | 代码：`LiveStage.tsx` 焦点判定已无说话者档；`hooks/useStableSpeaker.ts` 已删（零引用）；`tsc`/`build` 绿；**人工**见 MV-11（未跑） | **通过（代码）／真机未跑** |

## 2. 规则核对（AGENTS.md / 本轮纪律）

| 项 | 结论 |
| --- | --- |
| 每处改动挂在 `rNNN` | 通过：所有提交带 `[Req: r011]`（r012 登记单为 `[Req: r012]`） |
| 一次提交一个逻辑增量 | 通过：cp-1/1b/2(×2)/3/4/5/6/6b/7，各自单一主题 |
| `git add` 只写具体路径 | **有瑕疵**：cp-6 一次 `git add` 与已 stage 的删除（`git rm`）混用导致整条 add 失败，只提交了删除 → 已用 cp-6b 补交（未 amend、未 rebase） |
| 历史 append-only | 通过：无 amend / 无 rebase / 无 reset |
| 密钥不入库 | 通过：心跳令牌用 `SESSION_SECRET` 的 HMAC，不落库、不入库；`.env` 仍未入库 |
| 补正轮只修不改（含授权的例外） | 通过：四处例外（满员自动拒 / 邀请码入口与闭环 / worker 上报 / 焦点收窄）在需求单 §1 与 `redirect-02.md` 均有你的原话依据 |

## 3. 文档对账

| 面 | 结论 |
| --- | --- |
| 项目级 | README（状态/数字/演示 10 步）、AGENTS.md（数字 + 容量口径）、覆盖页（整页重写去重）、需求索引（r011 行 + r005~r010 转「已合并」）、roadmap §7 第 10~13 条与 §9 两行 | 全部回填 |
| 轮次 | 需求单 + design + changes（cp 台账/门禁/逐处改动）+ review（本页）+ redirect-02 + 人工剧本 | 齐 |
| 模块轴 | `02-modules/r009-focus-system{,-features}.md` 变更记录已加（转写与容量的模块页在 r010/r005 轮已建） | 通过 |
| 教学页 | `docs/tutorials/r011-invite-entry-and-capacity.md`（新增，C 使用者）；D 开发者页不适用（理由见覆盖矩阵） | 通过 |
| 快照 | `docs/README.md` §6 追加 r011 快照（145 页，保留 r010 的 137 页快照） | 通过 |

## 4. 人工取证（未跑，如实）

| 项 | 状态 |
| --- | --- |
| MV-1 断线重连与设备保持（含 `reconnect-drill.bat`） | **未取证**（需你操作） |
| MV-2 服务端强停共享 / MV-3 共享中说话不夺焦点（共享侧） | **未取证** |
| MV-4 声波电平数字 / MV-5（已作废）/ MV-6 未配密钥提示 | **未取证** |
| MV-7 真机转写（真 Inference）+ `STT_MODE=off` 可视化 | **未取证**（消耗免费档额度） |
| MV-8 reduced-motion / MV-9 本轮新行为 / MV-10 视觉与交互 / MV-11 说话不夺焦点 | **未取证**（MV-9/MV-11 需 cp-4/cp-6 已落地的界面） |

> 口径：人工项**没有留痕就算未取证**，不和「代码写了」混为一谈（AGENTS.md 硬规矩 7）。

## 5. 两栏处置清单

**本轮已落地可保留**
1. 文档回填：README / AGENTS / 覆盖页 / 需求索引 / roadmap（§7 第 10~13 条、§9 两行）/ r002 36 条 + r005 8 条验收清单回勾（cp-1~cp-3）。
2. 满员自动拒待批申请：`reject_pending_requests` + `_auto_reject_pending`（两处调用点，批准路径「先提交后抛错」）+ 等待页文案 + smoke 新检查（cp-4）。
3. 邀请码入口与未登录闭环：顶栏常驻入口 + `/join` 自动提交 + 教学页（cp-4）。
4. worker 健康上报：`POST /stt/heartbeat`（HMAC）+ `/rooms/{id}/stt-status` + worker 心跳循环 + 芯片「最后心跳」提示（cp-5）。
5. 焦点规则收窄：说话不再获得焦点（删说话者档与 `useStableSpeaker` 死代码）+ ADR-0014 变更记录 + 模块页/教学页同步（cp-6/6b）。
6. 用例 +8（自动拒 3 / 心跳 3 / off 2），既有满员用例按新语义更新；smoke 由 46 → **47** 步（新增自动拒留痕检查）。

**未闭合 / 如实说明**

| # | 项 | 状态 | 处置建议 |
| --- | --- | --- | --- |
| ① | MV-1~MV-11 全部人工项 | 未取证 | 你按剧本跑并回填汇总表，我再把相关 `[~]` 转 `[x]` |
| ② | `STT_MODE=off` 的端到端「无气泡、库内不新增」 | 只验了不派单与状态上报 | MV-7 步 4 |
| ③ | 心跳为**进程内存态**（后端重启即清空） | 设计如此（零迁移） | 多进程/多机部署时再考虑 `stt_agents` 表（design §7 Q1 备选②） |
| ④ | `GET /api/stt/status` 仍返回 `segmentSeconds=8`（B 路径残留字段） | 前端未使用 | 改契约属 L3 → 待你批（r010 未闭合 ⑨ 仍在） |
| ⑤ | 邀请码入口的「注册后回跳」未经真机 | 代码同 `LoginPage` 既有 returnTo 口径 | MV-9 步 2 |
| ⑥ | `cancel_pending_requests`（结束房间 → `cancelled`）在 smoke 中不再被覆盖 | 已被「满员自动拒」抢先；服务层用例仍在（`test_rooms_service.py:256`、`test_rooms_api.py:144`） | 无需动 |

## 6. 合并指引（由人执行）

```
git checkout main
git merge --no-ff req/r011-debt-backfill
git tag -a round-r011-done -m "r011 完成（欠账补正 + 三处授权例外 + 焦点规则收窄）"
```
合并后复验：`pytest backend/tests -q` → `python backend/scripts/smoke.py --base-url http://127.0.0.1:8000` → `cd frontend && npx tsc --noEmit && npm run build`。
演示前置不变：第三个进程 `agents.bat`（零配额 `set AGENT_STT=fake && agents.bat`）→ `dev.bat`。
