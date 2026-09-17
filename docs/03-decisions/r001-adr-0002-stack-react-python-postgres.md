---
title: r001-ADR-0002 技术栈变更：React 前端 + Python 后端 + PostgreSQL
description: 用户拍板的前后端分离栈，取代 r001 设计页初稿的 Next.js 一体仓 + SQLite。
type: adr
status: accepted
owner: 陀梓皓
updated: 2026-09-16
---

<!-- overview -->
记录栈变更：为什么放弃已起草的 Next.js 一体仓 + SQLite，改成 React 前端 + Python 后端 + PostgreSQL，以及它对已写文档的影响。

## 背景

- 2026-09-16 用户拍板：**前端 React、后端 Python、数据库 PostgreSQL**。
- 此前 `docs/01-architecture/r001-app-architecture.md` 与 `docs/00-requirements/r001-skeleton-accounts-rooms.md` 是按「Next.js 16 一体仓 + SQLite」起草的（P5/P6 的建议值），本 ADR 生效后这两页的方案部分作废。

## 决策

| 层 | 决定 | 待定项 |
| --- | --- | --- |
| 前端 | React + TypeScript | 构建工具（建议 Vite）、UI 组件库（建议轻量自绘或最小依赖） |
| 后端 | Python | Web 框架（建议 FastAPI）、是否异步 |
| 数据库 | PostgreSQL | 落地方式（本机安装 / Docker / 仅交 compose）、驱动与迁移工具 |

## 理由

1. 用户拍板，且 Python 后端与用户既有开发习惯（本机 Python 3.11 环境、PyCharm 工作流）一致。
2. PostgreSQL 是交付要求技术建议里的**优先项**，SQLite 只是"可接受"。
3. 前后端分离更贴合交付要求「完整前端、服务端、SQL 设计」的分述，也方便用 Python 生态处理纪要生成（LLM SDK 在 Python 侧更顺）。
4. 为 M5 加分项（Docker Compose 一键启动、管理后台）留出自然的部署形态。

## 被否的替代方案

- **Next.js 16 一体仓 + SQLite**（r001 设计页初稿）：与用户拍板的栈不符；SQLite 让「PostgreSQL 优先」落空。已作废，不改写为兼容双栈（避免双源与双份维护）。
- **React + Python 但保留 SQLite**：不符拍板；且 PostgreSQL 的并发/约束语义与交付要求要求的数据层更匹配。
- **Python 后端 + Next.js 前端**：多一层 SSR 复杂度，本项目是交互型 SPA + API，收益为零。

## 影响（逐项，重写设计页时按此执行）

1. **文档重写**：`r001-app-architecture.md` 的 §2 目录树、§4 生命周期（存储态约束的 SQL 语法）、§5 API 契约（信封可保留，改成 Python 侧实现）、§6 函数级路径（改 Python 函数签名）、§7 认证会话、§9 验证矩阵、§10 待验证假设全部重写；`r001` 需求单的边界/风险条目同步。
2. **启动形态**：从「单命令 `npm run dev`」变成「前端 dev server + 后端 API 服务」两进程（或用 Compose 一条命令；本机暂无 Docker，见 P9）。
3. **会话与跨域（新增风险）**：前后端分离后本地是两个来源（如 `http://localhost:5173` 与 `http://127.0.0.1:8000`），Cookie 会话需要 CORS + `credentials` + SameSite 调整，或改为 Bearer Token。**这是栈变更带来的真实新增问题**，重写设计时必须在「安全与取舍」里定死一种并写明代价。
4. **数据层**：交付要求要求「可运行的 SQL Schema + 迁移或初始化脚本」→ 仍坚持**手写 SQL** 为准，Python 侧只做执行与参数绑定；迁移工具与驱动见 P10。
5. **Python 依赖安装**：需独立虚拟环境（不污染本机现有环境），安装前需用户批准（本轮尚不安装）。
6. **作废条目**：`node:sqlite` 实验性风险、Next 原生二进制取包风险等条目随本 ADR 作废。

## 后果与待办

- **重写时机**：等 P3′（LiveKit 来源）、P9（PostgreSQL 落地）、P10（框架/迁移）拍板后**一次重写**，避免二次返工。
- **验证矩阵**要换成 Python 侧命令（如 `pytest`、`python -m scripts.db_init`、`curl` 冒烟）。
- 待用户批准后才能安装依赖（FastAPI、psycopg、迁移工具等）。

## 变更记录

- 2026-09-16 建立：用户拍板 React + Python + PostgreSQL，作废 r001 设计页的 Next.js + SQLite 方案。
