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

`r001`（里程碑 M1：骨架 · 账户 · 房间）—— 需求单与设计页已起草，`status: draft`，待复核拍板（含设计页 §11 的 R1~R5）。此前初始化轮次（建仓 + 文档树 + 规划草稿）已提交。

- 需求单：`docs/00-requirements/r001-skeleton-accounts-rooms.md`
- 设计页：`docs/01-architecture/r001-app-architecture.md`

## 怎么跑

M1 落地后回填：环境变量（`.env.example` → `.env`）、安装、启动命令、两个浏览器演示完整路径。
