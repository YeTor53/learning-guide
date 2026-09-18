---
title: r001 轮次档案 · 设计
description: r001 的设计入口与轮内设计变更记录（事实源在架构页与模块页，本页只做轮次轴索引）。
type: reference
status: closed
owner: 陀梓皓
updated: 2026-09-18
---

<!-- overview -->
本页是 r001 的**轮次轴**档案（长期事实源不在这里，避免双源）：

| 内容 | 事实源 |
| --- | --- |
| 目的 / 边界 / 验收 / 影响面 / 文档产出 | `docs/00-requirements/r001-skeleton-accounts-rooms.md` |
| 总体架构、分层、目录、接口信封、会话、验证矩阵 | `docs/01-architecture/r001-app-architecture.md` |
| 房间业务规则与函数路径 | `docs/02-modules/r001-rooms.md`（实现）+ `r001-rooms-features.md`（功能） |
| 账户 | `docs/02-modules/r001-accounts.md` + `r001-accounts-features.md` |
| 决策 | `docs/03-decisions/`（ADR-0002~0010；其中 0007 的入口与位次被 0009 修订） |
| 设计规范（视觉 / 文案 / 动效 / 资产） | `docs/04-style/global-style.md` |
| 环境与运行 | `docs/tutorials/r001-postgres-setup.md` + `README.md`「怎么跑」 |

## 本轮设计变更记录（轮内发生、已归档的变更）

| 日期 | 变更 | 归档处 |
| --- | --- | --- |
| 2026-09-17 | 栈由「Next.js + SQLite」改为「React + Python + PostgreSQL」 | ADR-0002 |
| 2026-09-17 | 数据访问与迁移方式定为手写 SQL + 轻量版本表 | ADR-0005 |
| 2026-09-17 | 运行环境定为本机 conda 环境 `learningguide` | ADR-0006 |
| 2026-09-17 | 导航形态：顶部导航 → 左侧边栏 | ADR-0007 |
| 2026-09-17 | 视觉体系：Lucide 图标、界面禁 emoji、Awwwards 级动效与排版 | ADR-0008 |
| 2026-09-17 | 登录入口回到顶栏右上角、个人信息移到侧边栏左下角；错误呈现三分流 | ADR-0009 |
| 2026-09-18 | 首屏《思想者》图版：素材来源、许可与处理管线 | ADR-0010 |
| 2026-09-18 | 图版位移四次修订（虚拟上下界 → 固定容器内滑动 → 容器底锚到「创建房间」行上方 + 幅度 0.35） | ADR-0010 修订记录 |

## What's next

下一轮（r002 = M2）的设计入口：轮次设计 `docs/rounds/r002-livekit/design.md`；模块页 `docs/02-modules/r002-livekit.md` 与 `r002-livekit-features.md`；总设计增量 `docs/01-architecture/r002-realtime-architecture.md`。
