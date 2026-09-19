---
title: r005 构思页：一整套测试流程（全覆盖）
description: 把「每轮怎么测、测到什么程度算过」变成可执行可交接的七层流程：分层与用例编号、证据等级、环境与数据隔离、一键门禁管线、覆盖度量与防漂移、5 个 cp 分期、8 条待拍板项。
type: reference
status: backlog
owner: 陀梓皓
updated: 2026-09-19
---

<!-- overview -->
本页是**构思页**（`status: backlog`），不是已批准设计。来源：你对 r004 的追加要求「为我设计一整套测试流程，要求全覆盖」（定性见 `docs/rounds/r004-room-extras/redirect-01.md`：C 后续工作，建议独立成轮 **r005-test-harness**）。
批准方式：答完本页 §8 的 Q1~Q8 → 我按批复写 r005 需求单 + design.md（届时 `git mv` 本页进 `docs/02-modules/` 或 `docs/00-project/`），**未批不动代码、不装依赖**。

## 1. 现状盘点（2026-09-19 实测）

| 层 | 现有资产 | 实测数字 | 缺口 |
| --- | --- | --- | --- |
| 静态门禁 | `<check>`：`tsc --noEmit`、`vite build`、`git grep` 密钥、`git status` | 全绿 | 无 lint（后端无 ruff/black）；迁移幂等没进 `<check>` |
| 后端单元/服务 | `backend/tests/` 10 个用例文件 + `conftest.py`(92) + `helpers.py`(32) | `pytest -q` → **105 passed** | 无覆盖率统计；边界/负例不全；无表驱动 |
| 接口契约 | `test_rooms_api` / `test_rooms_members_api` / `test_room_extras_api` / `smoke.py` | smoke → **PASS 36/36** | 无「角色 × 房间状态 × 端点」完整矩阵；无错误码总表对账；无 OpenAPI 快照 |
| 数据层 | `test_schema.py`（迁移清单 + 计数表 + DDL 逐字对账）、`test_rooms_concurrency.py` | 全绿 | 无约束负例（部分唯一索引 / CHECK / 外键）|
| 前端单元 | **无框架**（`package.json` 无 vitest/jest） | — | `stageLayout` 这类纯函数无任何自动化用例 |
| 端到端 | **只有我临时跑的手法**（Python Playwright 多上下文 + API 登录 + `window.__lgRoom`） | r004 期间实测通过 | 脚本**未入库** → 不可复跑、不可交接 |
| 非功能 | 断线：E18a 注入级已做；`reconnect-drill.bat` 人工载体 | E18b 未做 / E18c 待演练 | 容量（8 人满员）、性能、并发、降级无固定用例 |
| 文档对账 | 阶段 3 的人工对账（术语/链接/矩阵/教学页实跑） | r004 已做一次 | 无脚本；`AGENTS.md` 里硬编码的 `95 项` / `PASS 22/22` 已漂移（现 105 / 36）|

## 2. 目标与「全覆盖」的定义

**目标**：任何一次改动，都能用一条命令回答三个问题 —— ① 坏了没有（回归）② 坏在哪个面（定位）③ 这次到底测到了什么（覆盖）。
**全覆盖**（建议口径，见 Q1）= 下面七层**每层都有固定用例、固定命令、固定证据格式**，且**每一条需求单验收项（E 编号）都能指到至少一条用例（T 编号）**：

```
T0 静态门禁  类型/构建/密钥/迁移幂等/工作区干净
T1 单元      纯函数与工具（前后端）
T2 服务层    真 PG、事务回滚：规则、权限、幂等、并发
T3 接口契约  真实 HTTP：状态码 × 错误码 × 信封 × 分页 × OpenAPI
T4 数据层    迁移序列/索引/约束负例/seed 一致
T5 前端单元  纯函数与 hooks（stageLayout、消息合并、快照收敛）
T6 端到端    双浏览器真机：能力矩阵 / 断线三段式 / 降级 / 容量 / 性能
T7 文档交付  术语/链接/覆盖矩阵/教学页实跑/规则文件无漂移数字
```

## 3. 用例编号与互链（防「测了但不知道测的是哪条需求」）

- 编号：`T<层>-<模块>-<两位序号>`，如 `T3-rooms-04`、`T6-focus-02`、`T7-docs-01`。
- 每个需求单验收项 `E<n>` 必须在用例文件里以注释/用例名标注所对应的 `E` 编号；反向在 `review.md` 里列 `E → T` 映射表。
- 铁律：**E 没有 T = 本轮不通过**（自动检查：`verify.py --audit-e-cov` 扫 `docs/00-requirements/rNNN-*.md` 的 `- [x] E..` 与 `e2e/`、`backend/tests/` 里的 `E<n>` 标注，缺一条报错）。

## 4. 证据等级（沿用 r004 §10.2 的三段式并细化，禁止低报为高）

| 级别 | 含义 | 例 |
| --- | --- | --- |
| S | 静态（类型/构建/扫描） | `tsc --noEmit` |
| U | 单元（无 IO） | `computeStageLayout` 的阶梯断言 |
| I | 接口（真实 HTTP，库真读写、事务回滚） | `pytest` 接口层、`smoke.py` |
| J | 注入级（SDK 事件注入，非真断） | `emit('disconnected', 5)` → 文案 |
| N | 真实（真网络条件/真信号中断/真并发） | 双浏览器真实收发、信号级掉线 |
| P | 物理（人工动作，如断 Wi-Fi） | `reconnect-drill.bat` 演练 |

规则：`review.md` 每条验收必须写级别；J 不得写成 N；P 未做就写「未做」。

## 5. 环境与数据隔离（现在缺，导致演示库被写脏）

| 环境 | 用途 | 数据 |
| --- | --- | --- |
| `E1` 测试库（`learningguide_test`） | T2/T3/T4 自动用例 | 用例内事务回滚，跑完库干净 |
| `E2` 演示库（`learningguide`） | 手工演示 / `smoke.py` | seed 数据；**E2E 不再用它** |
| `E3` 隔离房间 fixture | T6 | 固定账号 + **每次新建房间**，结束即弃（房间是一次性讨论，ADR-0012） |
| `E4` 实时服务两态 | T6 | `LIVEKIT_MODE=self` 走本地（可断） / 云端（主路径） |
| `E5` CI（若批） | T0/T1/T3 子集 | 无凭据，不跑 T6 |

配套：`.env` 增 `TEST_*`（账号/库名，**仅 `.env.example` 入库**，凭据不入库）；`backend/scripts/cleanup_test_data.py`（按前缀清 `cp7*`/`e2e-*` 账号与测试房间）。

## 6. 分层用例设计（文件级）

### T0 静态门禁
`verify.py static`：`tsc --noEmit`、`vite build`、`git grep` 密钥、`compileall`、**迁移幂等**（连跑两次 `db_init.py`，第二次必须「本次应用版本：无」）、`git status --porcelain` 为空。

### T1/T2 后端单元与服务层（`backend/tests/`）
- `test_role_rules.py`：角色规则表驱动（`ROLE_RULES`）—— 谁能做什么，逐条断言服务函数返回值/异常。
- `test_room_extras_service.py`：消息/举手/焦点服务的边界（trim、500 字边界、非法游标、目标不在册、重复举手幂等）。
- `test_concurrency.py`（扩 `test_rooms_concurrency.py`）：两连接并发「举手 + 结束」「踢人 + 取票」「两个焦点设置」→ 断言锁与最终态。
- 覆盖率（Q2）：`pytest --cov=backend/app --cov-report=json`，阈值按 Q2 批复执行。

### T3 接口契约层（`backend/tests/`）
- `test_permission_matrix.py`：**表驱动** `ROLE × ROOM_STATE × ENDPOINT`（5 角色 × 2 状态 × 24 端点 ≈ 240 例，用参数化合并成 ~60 断言组）：期望 `(status, error.code)`；对账 `docs/01-architecture/r001-app-architecture.md` 的**错误码总表**。
- `test_envelope_pagination.py`：信封 `ok/data/error{code,message}`、分页 `before/limit` 边界（0/1/50/100/101）、时间正序、幂等重放。
- `test_openapi_contract.py`：`/openapi.json` 与 `backend/tests/snapshots/openapi.json` 逐字比对（对外面漂移即失败，改了必须显式更新快照并在 review 里说明）。

### T4 数据层（`backend/tests/`）
- `test_constraints.py`：部分唯一索引（同房双活跃举手 / 双活跃 host）、`CHECK ((lowered_at IS NULL) = (lowered_reason IS NULL))`、外键、`rooms.ended_at` 与 `status` 联动。
- `test_migrations.py`（扩 `test_schema.py`）：迁移序列、幂等、`schema_migrations` 版本记账、`COUNTED_TABLES` 与实际表一致。

### T5 前端单元（`frontend/tests/`，方案见 Q3）
- `stageLayout.test.mjs`：优先级四态（共享 > 手动焦点 > 说话者 > 自己）、失效回落、`k=0..7` 阶梯列数、竖屏转横条、`metrics` 数值。
- `chatMerge.test.mjs`：按 id 去重、按时间排序、`before` 分页合并、`pending/retry`。
- `snapshotConverge.test.mjs`：`at` 收敛（旧快照不覆盖新的）。
- 运行：`node --test frontend/tests/`（零新依赖方案：用 vite 自带的 esbuild 先把 `.ts` 打包成临时 `.mjs`）。

### T6 端到端（`e2e/tests/`，Python + Playwright，真 LiveKit）
| 文件 | 场景 | 级别 |
| --- | --- | --- |
| `test_chat.py` | 双端收发 / 刷新与库一致 / 分页 / 失败重发 | N |
| `test_hands.py` | 举手幂等 / 自己放下 / 房主放下他人 / 刷新恢复 | N |
| `test_focus.py` | 双端同步 / 取消 / 离线保留 / 失效回落 / 易手不重挂载 | N |
| `test_share.py` | 共享占焦点格 / 自己停 / 房主「请求停止」 | N |
| `test_governance.py` | 申请-批准-踢人-移交-结束的完整链路（含 403/409） | N |
| `test_layout.py` | 阶梯 2/4/6/8 + 窄屏 720×1024 / 900×600 / 1258×566 | N |
| `test_motion.py` | `reduced_motion=reduce` 全部动效退化 | N |
| `test_disconnect.py` | 归因四态注入（J）+ 信号级断（N）+ 人工演练清单输出（P） | J/N/P |
| `test_capacity.py` | 8 人满员（第 9 人取票 409） | N |
| `test_perf.py` | 首屏 DOM 就绪 ≤ 2s、`/messages` p95 ≤ 300ms（本机基线） | N |

配套 fixtures：`two_browsers`（两个 context + API 登录）、`room_fixture`（新建房间 + 8 个固定账号自动批准）、`lg`（页面句柄 + `__lgRoom` 就绪等待）、`report`（JSON/JUnit 落 `e2e/report/`）。

### T7 文档交付对账
`verify.py audit`：术语表命中、内部链接有效、覆盖矩阵无 `planned`、教学页示例命令与代码一致（跑一遍）、**规则文件不含漂移数字**（`AGENTS.md` 里的用例数改成命令或不写数字）、`E → T` 映射齐。

## 7. 一键门禁管线

```bash
verify.bat quick     # T0+T1+T2+T3+T4+T5：目标 < 90s，日常提交前
verify.bat full      # quick + T6 全部（含 8 人 E2E）：目标 < 6min，合并前
verify.bat e2e chat  # 只跑某个 E2E 文件，改哪儿跑哪儿
verify.bat audit     # T7 文档对账
```
- 实现：`backend/scripts/verify.py`（子命令 + 汇总 JSON + 非 0 退出码）+ `verify.bat`（GBK+CRLF，包装 conda 与 npm，遵循既有 bat 规范）。
- 输出：`e2e/report/verify-<时间>.json`（每层 pass/fail/耗时/证据行），`review.md` 只引路径与关键数字，**不手抄总数**（防漂移）。
- 与现有纪律的关系：`<check>` 保留为最小集，`verify.bat quick` 是它的超集；合并前跑 `full`。

## 8. 待拍板项（Q1~Q8；数字选项，带建议值）

| 编号 | 问题 | 选项 | 建议 |
| --- | --- | --- | --- |
| Q1 | 「全覆盖」到哪一层？ | ① 五层（T0~T4）② 七层（+T5 前端单元、T7 文档对账）③ 七层 + 安全/性能预算 | **③**（T6 里已含性能与容量） |
| Q2 | 覆盖率口径 | ① 只统计不设阈值 ② 全局行覆盖 ≥ 80% ③ 仅「本轮改动文件」≥ 90% + 关键模块（services/repositories）≥ 85%，不设全局阈值 | **③** |
| Q3 | 前端单元测试方案 | ① 引 `vitest`（新依赖，需 ADR）② 零新依赖：vite 自带 esbuild 打包 → `node --test` ③ 不做前端单元，只靠 E2E | **②** |
| Q4 | E2E 载体 | ① 入库 `e2e/`（Python + Playwright 脚本 + 固定 fixture）② 保持临时脚本不入库 ③ 改用 JS 版 `@playwright/test`（新依赖） | **①** |
| Q5 | CI | ① 不上 CI（本机 `verify.bat` 为唯一门禁）② GitHub Actions 只跑 `quick`（无凭据）③ Actions 全量含 E2E（要 LiveKit secrets） | **②** |
| Q6 | 测试数据 | ① 专用测试库 + 固定账号 + 每次新建房间（可重复）② 每轮临时建/清 ③ 就用演示库 | **①** |
| Q7 | 轮次归属 | ① 独立成轮 `r005-test-harness`（5 个 cp）② 拆成后端/前端两轮 ③ 只登记不做 | **①** |
| Q8 | 配套设施 | ① 新增「测试手册」开发者教学页 + 修 `AGENTS.md`（数字改命令）+ 补 ADR（依赖决策）② 只写 design ③ 并入现有 dev-guide | **①** |

## 9. cp 分期（批准后按此拆，每步一提交）

| cp | 内容 | 产出 |
| --- | --- | --- |
| cp-1 | 基建与隔离：`e2e/` 目录、`pytest.ini`、`.env.example` 的 `TEST_*`、固定账号与测试房间 fixture、`cleanup_test_data.py`、`verify.py/.bat` 骨架（先跑通 quick） | 一条命令能跑现有全部门禁 |
| cp-2 | 后端加厚：权限矩阵表驱动、约束负例、并发三例、OpenAPI 快照、覆盖率统计 + 阈值 | T2/T3/T4 达标，E→T 映射表初版 |
| cp-3 | 前端单元：esbuild 打包器 + `node --test` 三个用例文件 | T5 达标 |
| cp-4 | E2E 场景矩阵与非功能：10 个 E2E 文件、断线三段式（注入 + 信号级 + 人工清单）、降级、容量、性能 | T6 达标，`verify.bat full` < 6min |
| cp-5 | 文档与收口：测试手册教学页、`AGENTS.md` 数字纠正 + 「测试门禁」段、需求单/design/覆盖矩阵、review 定稿 | T7 达标 |

## 10. 风险与明确不做

- **风险 1**：E2E 依赖真 LiveKit Cloud（网络 + 额度）→ 对策：`LIVEKIT_MODE=stub` 下 `quick` 仍全绿，`full` 才连云端。
- **风险 2**：8 人满员用例会占满演示库房间成员表 → 对策：E3 隔离房间 + 跑完清理。
- **风险 3**：覆盖率阈值可能逼出「为覆盖而覆盖」的空用例 → 对策：只对改动文件与关键模块设阈值（Q2=③）。
- **明确不做**：不改产品行为、不加「将来会用到」的测试框架、不做视觉像素比对（另属 `frontend-visual-gate`）、不在 CI 里存密钥、不为覆盖率重构生产代码。
