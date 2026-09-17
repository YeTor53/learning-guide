# Learning Guide · 学习讨论室（LiveKit 迷你产品）

围绕一门学习主题的多人音视频小组讨论室：账户、房间、等候室审批、三种角色权限、群聊、举手与焦点发言、屏幕共享、服务端踢人、房间结束后的 LLM 讨论纪要。

> 当前状态：**r001 文档待批准**（总设计 + 需求单均已重写，`status: draft`），尚未进入实现。

## 项目地图

| 位置 | 内容 |
| --- | --- |
| `docs/00-project/global-roadmap.md` | 项目级规划：起点 / 终局 / 里程碑（草稿，待批准） |
| `docs/00-requirements/` | 每轮需求单（`rNNN-*.md`）与变更记录 |
| `docs/01-architecture/` | 总体架构、模块图、数据流 |
| `docs/02-modules/` | 每个模块一份：设计 + 实现 |
| `docs/03-decisions/` | ADR：为什么这么设计、改了什么约定 |
| `docs/04-style/` | 风格指南 |
| `docs/glossary.md` | 术语表 |
| `AGENTS.md` | 给 AI 的项目规则（禁区、验证命令、提交规范） |

## 当前轮次

`r001`（里程碑 M1：骨架 · 账户 · 房间）—— **总设计与需求单均已重写完成，`status: draft` 待批准**（产出顺序见 `docs/00-project/global-roadmap.md` §8）。

已定：题目 A / 位置 / 数据库 PostgreSQL（本机安装，17.11 已就绪）/ 前端 React + 后端 Python（FastAPI）/ 数据层=手写 SQL + 轻量版本表 / LiveKit=Cloud 为主 + 自建留档 / 纪要=DeepSeek / 加分项=增量项 / 运行环境=conda 环境 `learningguide`（ADR-0006）/ 提交物 = zip + GitHub 仓库 + npm 包（细则 P11 **暂缓**）。

- 总设计（本轮，待批准）：`docs/01-architecture/r001-app-architecture.md`
- 需求单（本轮，待批准）：`docs/00-requirements/r001-skeleton-accounts-rooms.md`
- 模块功能设计：`docs/02-modules/r001-rooms-features.md`；模块实现设计：`docs/02-modules/r001-rooms.md`
- 决策记录：`docs/03-decisions/`（ADR-0001~0006）
- 归档（非本轮）：`docs/99-archive/`（房间 M2/M3 能力、纪要 M4）

## 怎么跑

（cp-r001-4 回填完整步骤，当前占位）

- 后端运行环境：conda 环境 `learningguide`（Python 3.11.16，见 `docs/03-decisions/r001-adr-0006-python-env-conda.md`）
  `conda activate learningguide`；或在 PyCharm 里选该环境作解释器
- 本机 PostgreSQL 17.11（服务 `postgresql-x64-17`），库 `learning_guide`、角色 `lg_app`
- 密钥与连接串放本机 `.env`（不入库）；示例见 `.env.example`

