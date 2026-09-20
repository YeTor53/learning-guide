---
title: r009.5 审查报告：欠账补正
description: E1~E12 逐条证据、规则/文档对账、两栏清单与合并指引（cp-5 定稿）。
type: reference
status: draft
owner: 陀梓皓
updated: 2026-09-20
---

<!-- overview -->
骨架（cp-1）；定稿在 cp-5。需求单 `docs/00-requirements/r009.5-debt-backfill.md`，设计 `design.md`，数字出处 `changes.md`。

## 1. 验收对账

| # | 条目 | 证据 | 结论 |
| --- | --- | --- | --- |
| E1 | cp tag 补齐（0/1a/1b/2a/2b/3a/3b/5 + cp-r010-0） | 待填 | planned |
| E2 | r009 台账无「进行中」残留；cp-4 写明无独立提交 | 待填 | planned |
| E3 | r009 review 无 planned 残留，E0~E12 全覆盖 + 合并顺序 | 待填 | planned |
| E4 | r008 review 四处纠错 | 待填 | planned |
| E5 | `git grep` 两处死链 0 命中 | 待填 | planned |
| E6 | `.env.example` 含 `STT_*` 三键 | 待填 | planned |
| E7 | `stageLayout` 0 命中 + tsc/build 绿 | 待填 | planned |
| E8 | 索引 / docs README / roadmap 回填 | 待填 | planned |
| E9 | E0 动效真机量测 | 待填 | planned |
| E10 | E11 声波证据 + 截图落盘 | 待填 | planned |
| E11 | 门禁四项全绿 | 待填 | planned |
| E12 | 两页教学页 + 使用者页实跑 | 待填 | planned |

## 2. 规则核对（AGENTS.md / 本轮铁律）

| 规则 | 核对 | 结论 |
| --- | --- | --- |
| 未批不动代码 | 需求单 §8 有你 2026-09-20 授权；本轮唯一代码改动为删零引用文件 | 待填 |
| 一次提交一个逻辑增量 | cp-1~cp-5 五个提交计划 | 待填 |
| `git add` 只写具体路径 | 逐次核对 | 待填 |
| 历史 append-only | 本轮无 amend/rebase/reset；tag 只新增 | 待填 |
| 密钥不入库 | 只动 `.env.example` 键名，无真值 | 待填 |
| 不改历史迁移 | 本轮无迁移改动 | 待填 |
| 文档与代码同提交 | 每 cp 均含文档 | 待填 |
| 不擅自增删依赖/改端口/改目录结构 | 取证脚本用本机已装 Playwright；未新增目录（落在既有 `frontend/scripts/`） | 待填 |

## 3. 文档对账（两轴 + 四件套 + 覆盖矩阵）

| 项 | 结论 |
| --- | --- |
| 覆盖矩阵（需求单 §6） | 待填（cp-5 后应无 planned 残留） |
| 轮次轴 | `docs/rounds/r009.5-debt-backfill/{design,changes,review}.md` |
| 模块轴 | r005~r009 五页「变更记录」追加行 |
| 索引轴 | 需求索引 + `docs/README.md` + roadmap |
| 教学页实跑 | 待填（使用者页步骤复跑输出） |

## 4. 视觉对账（本轮仅补截图，不新增视觉元素）

| 组 | 方式 | 结果 |
| --- | --- | --- |
| 声波 UI | `%TEMP%\lg_r009.5\mic-wave.png` | 待填 |
| 零 emoji / 单一图标库 | 扫描（本轮无新图标） | 待填 |
| 令牌未新增 | `:root` 令牌段对比（`--stage-*` / `--hand-blink-*` / `--mic-pulse-*` / `--tile-fit` 未变） | 待填 |

## 5. 两栏处置清单

**本轮已落地可保留**

1. 待填（cp-5）

**未闭合 / 如实说明**

| # | 项 | 状态 |
| --- | --- | --- |
| 1 | E11 声波数值序列 | 未取证（不发布假麦）→ 顺延 r011 |
| 2 | r008 E5「未配密钥提示」真机 | 未取证（需改 `.env`）→ 如实标注 |
| 3 | `cancel_pending` 接事件 | 保留函数，r011 接 |
| 4 | r006/r007 教学页缺口 | 登记 `docs/README.md` §5 与 roadmap §9，本轮不做 |
| 5 | r010 真机转写取证 | 等你的 `STT_*` 三键 |

## 6. 合并指引（由人执行）

```bash
# 前置：r005 → r006 → r007 → r008 → r009 依次合并（均未合并，须按序）
git checkout main
git merge --no-ff req/r010-transcription   # r005~r010 的内容随链带入
git merge --no-ff req/r009.5-debt-backfill # 本轮（从 r010 HEAD 开出）
git tag -a round-r009.5-done -m "r009.5 完成（r008/r009 欠账补正）"
```

合并后复验：`pytest backend/tests -q` → `python backend/scripts/smoke.py --base-url http://127.0.0.1:8000` → `cd frontend && npx tsc --noEmit && npm run build`。
（按序合并的具体命令以 r010 收官时的口径为准；本页给的是本轮位置。）
