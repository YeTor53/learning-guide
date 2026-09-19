---
title: ADR-0002 文档规约归一（两套口径冲突的裁决）
description: 本仓文档同时落在两套互斥的目录与命名口径下，本页记录冲突实测、影响、三个候选方案与代价，待拍板。
type: reference
status: proposed
owner: 陀梓皓
updated: 2026-09-19
---

<!-- overview -->
本页是「文档工程口径」的裁决单：**未拍板，改动任何现有文件前须先批准**。
相关：`AGENTS.md` §文档纪律、`docs/00-project/global-roadmap.md`、`docs/02-modules/`、`docs/tutorials/`。

## 1. 现象（2026-09-19 实测）

- 全库 grep `05-tutorials` / `06-dev-guide`：**0 命中**；`-features.md` 引用 54 处、`tutorials/` 引用 37 处。
- `docs/` 共 64 个文件：rounds 21 / 03-decisions 15 / 02-modules 7 / 00-requirements 6 / 01-architecture 4 /
  99-archive 4 / tutorials 4 / 00-project 1 / 04-style 1 / glossary 1。
- 本仓按「甲」产出全套文档（r001、r002 已 closed，r003 in progress，r004 已按甲写好 planned 路径），
  同时「乙」（编号目录 + 05-tutorials/06-dev-guide + 文件名不带轮次号）是本项目工作流引用的另一套通用规约。

## 2. 两套口径对照（互斥，不是风格差异）

| 条目 | 甲：现行口径（AGENTS.md §文档纪律） | 乙：编号目录口径 |
| --- | --- | --- |
| 教学页落位 | `docs/tutorials/`（使用者与开发者混装，4 页） | `docs/05-tutorials/`（使用者）+ `docs/06-dev-guide/`（开发者） |
| 模块页粒度 | 每轮新建一对：`rNNN-<模块>.md` + `rNNN-<模块>-features.md` | 每模块单页（设计 + 实现 + 变更记录） |
| 文件名 | 必带 `rNNN-` / `global-` 前缀 | 不带轮次号（轮次由目录 + 索引表 + front matter 承载） |
| 覆盖矩阵 D 列 | 指向 `docs/tutorials/` 下的开发者页 | 指向 `docs/06-dev-guide/` |

## 3. 影响（为什么必须裁）

1. **同一仓库同时「合规」与「欠账」**：按乙，r002 的开发者教学未落在 `06-dev-guide/` = 四件套缺一 → 需求单不许 closed；
   按甲，`docs/tutorials/r002-livekit-dev-guide.md` 已 landed。审查结论取决于 agent 读了哪套规约。
2. **模块事实源分裂**：房间模块现有 `r001-rooms.md` / `r001-rooms-features.md` / `r002-livekit.md` /
   `r002-livekit-features.md` 四页，r004 后 5 页，「按模块名一步到位」做不到。
3. **旧页与代码漂移**：`backend/tests/test_schema.py:17` 以 `docs/02-modules/r001-rooms.md` 为 DDL 事实源，
   而该页 `updated` 停在 2026-09-17。
4. **改名成本已固化**：AGENTS.md 明文要求轮次前缀（L35），任何全库改名都要连带改 AGENTS.md、测试断言与 90+ 处引用。

## 4. 候选方案与代价

**方案 A（最小；建议）**：甲为体、乙为魂，不动任何现有文件。
① 新增 `docs/02-modules/README.md`：模块 → 各轮页 → 当前真相页（治分裂）；
② 新增 `docs/tutorials/README.md` 受众索引，教学页 front matter 增 `audience: user|dev`（等价拿到乙的分受众收益）；
③ rounds/、需求单索引、覆盖矩阵照乙继续（本仓已在做）。
代价：新增 2 个文件；口径分歧在本 ADR 里写死「以 AGENTS.md 为准」。

**方案 B（归一到乙）**：`git mv` tutorials → 05-tutorials/06-dev-guide（4 页）；02-modules 合并为单页
（房间 4 → 1 页 + 变更记录）；改 AGENTS.md L35；全库引用同步（-features 54 处 / tutorials 37 处）；
改 `test_schema.py` 路径；历史轮次页只加「路径已迁」映射表，正文不改。
代价：动 60+ 文件、90+ 引用，须独立成一轮；与 2026-09-14「改名必全库同步」的教训同风险，须脚本改名 + 断链扫描。

**方案 C（归一到甲）**：改通用规约（去掉 05/06 与「文件名不带轮次号」），本仓不动。
代价：需先核其他项目（DockingAssistant = 页类 4 页 + `docs/README.md`；automatic_crawler = 编号目录），
否则新造双源；放弃「文件名稳定不断链」的收益。

## 5. 待拍板项

| 编号 | 事项 | 选项 | 建议值 | 影响 |
| --- | --- | --- | --- | --- |
| Q1 | 口径归一走向 | A 最小 / B 归一到乙 / C 归一到甲 | **A** | 决定是否动 60+ 文件 |
| Q2 | 若选 B，何时做 | r004 的 cp-8 / 独立 r005 | 独立 r005 | 影响 r004 交付节奏 |
| Q3 | 通用规约是否同步修（防复发） | 同步修 / 只改本仓 | **同步修** | 不改则下次接续仍会飘 |

## 6. 裁决（转 accepted 时填）

选定方案 / 生效范围（仅新文件 or 全库）/ 落地轮次 / 是否同步通用规约。

## 7. 落地动作（批准后才执行）

- 第一步：`AGENTS.md` §文档纪律 增一行「文档落位与命名以本 ADR 为准」。
- 选 A：两份 README 的逐字稿随批准一并评审，通过后落盘。
- 选 B：先出改名映射表（旧路径 → 新路径）+ 引用同步清单，dry-run 断链扫描为 0 再生效。
- 选 C：先出通用规约的逐字改动稿。

## What's next

- 本页 `status: proposed`；未获批前不改动 `docs/` 下任何现有文件。
