---
redirect: r004-01
status: proposed
raised_at: 2026-09-19（r004 cp-7 之后、待合并前）
decided_by: 待批
---
# redirect r004-01：用户要求「设计一整套测试流程，要求全覆盖」

## 1. 用户原话 / 现象

> 为我设计一整套测试流程，要求全覆盖

## 2. 比对依据（三比）

- **本轮已批准需求单/设计/验收**：`docs/00-requirements/r004-room-extras.md` §2 边界（M3 五项能力 + 两项界面缺陷 + 还债）与 §5 验收 E1~E23 —— **判定：无**。本轮只有「每轮跑哪些命令」的验收，没有「测试体系/流程」这一交付物。
- **roadmap / backlog**：`docs/00-project/global-roadmap.md` §3 里程碑 M1~M4 与 §9 遗留台账 —— **判定：无**（M5 加分项里只有断线恢复/录制转写/Compose/管理后台/录屏，不含测试体系）。
- **当前产物实况**（实测，2026-09-19）：
  - 后端：`backend/tests/` 11 个文件（10 个用例文件 + `conftest.py` + `helpers.py`，约 1,750 行）；`pytest backend/tests -q` → **105 passed**；`smoke.py` → **PASS 36/36**；`db_init.py` 可应用 `003`+`004`。
  - 前端：**没有测试框架**（`frontend/package.json` 只有 dev/build/preview/typecheck；无 vitest/jest）；类型与构建门禁 = `tsc --noEmit` + `vite build`。
  - 端到端：**只有我临时跑的手法**（base conda 的 Python Playwright 多上下文 + API 登录 + `window.__lgRoom`），**脚本未入库** → 不可重复、不可交接。
  - 非功能：断线三段式只完成 E18a（注入级）；E18b 未做、E18c 待演练；容量/性能/并发无固定用例。
  - CI：**无**（仓库无 `.github/`）；门禁全靠人跑 `AGENTS.md` 的 `<check>`。
  - 已发现的规则漂移：`AGENTS.md` §「r002 起新增的验证命令」仍写 `95 项` / `PASS 22/22`（现为 105 / 36），**数字硬编码在规则文件里会持续漂移**。

## 3. 定性

- **结论：C（后续工作）** —— 已批准文档里没有这条，且与 r004 验收不冲突；属「本轮范围外、本来就该排在后面」。
- **依据**：第 2 节「本轮已批准需求单/设计/验收：无」+「roadmap/backlog：无」。
- **规模判断**：要动**新依赖**（前端测试框架、覆盖率工具）、新目录（`e2e/`）、新脚本（`verify.bat`）、并会给每轮验收加一层固定门禁 —— 超过「顺手加几个用例」的量级，**建议独立成轮 r005-test-harness**（5 个 cp），不在 r004 里塞。
- **本轮处置**：r004 照常收尾（等你合并 + 打 `round-r004-done`），本单只做登记。

## 4. 需求单口径

- r004 需求单**不改任何条款与验收**（E1~E23 保持现状；E18b/E18c 的未闭合状态照旧在 `review.md` 里）。
- 新增登记：本单 + `docs/99-archive/r005-ahead-test-process.md`（r005 构思页，`status: backlog`）+ roadmap §9 台账一行。
- r005 需求单草案要点（已写进构思页）：目的 = 把「每轮怎么测、测到什么程度算过」变成可执行、可交接、可复现的一整套流程；边界 = 只做测试与门禁，不改产品行为；验收 = 一键 `verify.bat` 全绿 + 覆盖度量达标 + E2E 脚本入库可复跑 + 测试手册落地；覆盖矩阵 = 需求单/design/e2e 目录/verify 脚本/测试手册教学页。

## 5. 冲突项清单

| 冲突点 | 依据 | 处置 | 影响的文档与代码 |
| --- | --- | --- | --- |
| 引前端测试框架（vitest 等）与覆盖率工具 = **新增依赖** | `AGENTS.md` 禁区「不擅自增删依赖…需要时先在需求单登记并获批准」 | 登记进 r005 需求单，逐项标「新增依赖」并附 ADR；未批前不装 | `frontend/package.json`、`backend/requirements-dev.txt`、`docs/03-decisions/` |
| E2E 若上 CI 需 LiveKit 凭据（secrets） | `AGENTS.md` 禁区「密钥永不入库」+ 「实时凭据只在 `.env`」 | CI 只跑不依赖凭据的部分（后端 + 类型 + 构建）；E2E 留在本机 `verify.bat full` | `.github/workflows/`（若采纳） |
| `AGENTS.md` 里硬编码的用例数已漂移（95/22 → 105/36） | `AGENTS.md` §「r002 起新增的验证命令」 vs 实测 | r005 修：规则文件只写命令，数字由脚本输出（或去掉数字） | `AGENTS.md` |
| 我之前跑 E2E 的脚本是临时文件、未入库 | 无（事实） | r005 把手法固化成 `e2e/` 脚本（含固定测试房间与账号 fixture） | 新目录 `e2e/` |
| 演示库被验证写脏（多间测试房间 + `cp4-*`/`cp6-*`/`cp7*` 账号） | 实测（`room_af43e343f766fb76` 等） | r005 cp-1 做「测试用房与账号」fixture，与演示库解耦；现有残留按你一句话处理 | 数据库、`.env`、seed 脚本 |

## 6. 复用清单

| 已落地增量 | SHA | 对应文档页 | 新结论下是否仍有效 |
| --- | --- | --- | --- |
| 后端 105 个 pytest 用例（schema / 服务 / 接口 / 并发 / 令牌 / r004 扩展） | `a0edc1f` 等 | `docs/02-modules/r004-room-extras.md` §7 | **仍有效**，作为 T2/T3 层底座 |
| `smoke.py`（36 条真实 HTTP 冒烟，含 r002 四步 + r004 三步） | `857cf18`、`4fe8ca3` | 同页 §11 | **仍有效**，作为 T3 的活服务探针 |
| 双浏览器 Playwright 手法（多上下文 + API 登录 + `window.__lgRoom` 注入） | `151c2c0`、`4fe8ca3` | `docs/tutorials/r002-livekit-dev-guide.md` §8 | **仍有效**，r005 直接固化成脚本 |
| `test_schema.py` 的「迁移清单 + 计数表 + DDL 逐字对账」思路 | r001/r002 | `docs/02-modules/r001-rooms.md` | **仍有效**，扩成 T4 约束负例 |
| `reconnect-drill.bat`（物理断网演练载体） | `4fe8ca3` | review.md E18c | **仍有效**，作为 T6 非功能的人工段 |
| `dev.bat check/start/stop` | `857cf18` | `docs/tutorials/r002-livekit-setup.md` | **仍有效**，`verify.bat` 复用其就绪探针 |

## 7. 处置

- **C**：登记到 `docs/99-archive/r005-ahead-test-process.md`（`status: backlog`，含七层模型、用例编号、证据等级、环境矩阵、门禁管线、5 个 cp 分期、8 条待拍板）+ roadmap §9 台账一行。
- 本轮 r004 照常走完（等你合并 + `round-r004-done`）。
- 待你批复：确认「独立成轮 r005」还是「只登记不做」，以及构思页里的 Q1~Q8。

## 8. 结论（用户一次批复）

- 批复原文：（待填）
- 落地提交 SHA：（待填）
