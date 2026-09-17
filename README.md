# Learning Guide · 学习讨论室（LiveKit 迷你产品）

围绕一门学习主题的多人音视频小组讨论室：账户、房间、等候室审批、三种角色权限、群聊、举手与焦点发言、屏幕共享、服务端踢人、房间结束后的 LLM 讨论纪要。

> 当前状态：**初始化**（仓库骨架 + 文档树 + 项目规划草稿，待批准）。尚未进入实现。

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

`r001`（里程碑 M1：骨架 · 账户 · 房间）—— **总设计已重写完成，`status: draft` 待复核**；需求单待按总设计重写（顺序见 `docs/00-project/global-roadmap.md` §8）。

已定：题目 A / 位置 / 数据库 PostgreSQL（本机安装）/ 前端 React + 后端 Python（FastAPI）/ 数据层=手写 SQL + 轻量版本表 / LiveKit=Cloud 为主 + 自建留档 / 纪要=DeepSeek / 加分项=增量项 / 提交物 = zip + GitHub 仓库 + npm 包（细则待 P11）。

- 总设计（本轮，待复核）：`docs/01-architecture/r001-app-architecture.md`
- 需求单：`docs/00-requirements/r001-skeleton-accounts-rooms.md`（superseded，待重写）
- 模块功能设计：`docs/02-modules/r001-rooms-features.md`；模块实现设计：`docs/02-modules/r001-rooms.md`
- 决策记录：`docs/03-decisions/`（ADR-0001~0005）
- 归档（非本轮）：`docs/99-archive/`（房间 M2/M3 能力、纪要 M4）

## 怎么跑

M1 落地后回填：环境变量（`.env.example` → `.env`）、安装、启动命令、两个浏览器演示完整路径。
