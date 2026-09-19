---
title: r003 变更记录（changes）
description: r003 的文件 × 模块 × 页面锚点台账、cp 进度、用户消息台账与无文档变更登记。
type: reference
status: draft
owner: 陀梓皓
updated: 2026-09-19
---

<!-- overview -->
一轮一行地记「改了什么、落到哪份文档的哪个锚点、验证证据是什么」。代码与文档必须同一次提交落地。

## 1. cp 台账

| cp | 内容 | 状态 | 提交 SHA | 证据 |
| --- | --- | --- | --- | --- |
| cp-r003-1 | r002 收官回填（纯 docs） | planned | — | — |
| cp-r003-2 | 房主结束房间入口（DeviceBar + RoomLivePage + css + 文档） | planned | — | — |
| cp-r003-3 | 真机取证 + 教学页实跑 + 审查报告 | planned | — | — |

## 2. 文件 × 模块 × 文档锚点

| 文件 | 模块 | 改什么 | 落的文档锚点 | 状态 |
| --- | --- | --- | --- | --- |
| `frontend/src/components/live/DeviceBar.tsx` | 交流页 · 控制坞 | 离场组房主分支：`离开`（disabled）→ `结束房间` + 确认态；新增 4 个 props | 功能页 §4.2 / §4.5 条④；实现页变更记录 | planned |
| `frontend/src/pages/RoomLivePage.tsx` | 交流页 | 新增 `confirmingEnd` 状态、`doEnd` 处理器、Esc 链插一级、DeviceBar 传参 | 功能页 §4.9；实现页变更记录 | planned |
| `frontend/src/styles/global.css` | 视觉体系 | 新增 `--live-end-border` / `--live-end-hover` 与 `.live-ctrl-end` | 风格指南令牌表 + §12.1 | planned |
| `docs/rounds/r002-livekit/review.md` | 轮次（r002） | 按实测定稿 | 自身 | planned |
| `docs/00-requirements/r002-livekit-room.md` | 契约（r002） | `status: closed` + 变更记录一行 | 自身 | planned |
| `docs/00-requirements/README.md` | 索引 | r003 行（已加）、r002 行转 closed | 自身 | partial（r003 行已 landed） |
| `docs/00-project/global-roadmap.md` | 项目 | §3 / §7 三处矛盾修正；§9 台账一行 | 自身 | planned |
| `docs/02-modules/r002-livekit-features.md` | 模块（功能） | §4.2 / §4.5 / §4.9 / §6 第 10 步 | 自身 | planned |
| `docs/02-modules/r002-livekit.md` | 模块（实现） | 变更记录一行 | 自身 | planned |
| `docs/04-style/global-style.md` | 风格 | 令牌表 + §12.1 一句 | 自身 | planned |
| `docs/tutorials/r002-livekit-demo.md` | 教学（使用者） | 第 9 步改走控制坞 | 自身 | planned |
| `docs/tutorials/r002-livekit-setup.md` | 教学（使用者） | 第 11 行入口描述同步 | 自身 | planned |

## 3. 用户消息台账（首行回执的核对凭据）

| 序号 | 日期 | 用户原话摘要 | 回执分类 | 单号 |
| --- | --- | --- | --- | --- |
| 1 | 2026-09-19 | 「读档LearningGuide」（只读，无新要求） | 只读读档（免单） | — |
| 2 | 2026-09-19 | 「我写了个txt」＋「在项目文档你放待办的地方」 | 补充事实（定位请求，免单） | — |
| 3 | 2026-09-19 | 「具体就是这个项目现在没有结束房间的按钮了，让房主的退出按钮变成结束房间按钮」 | 重定向 | r002-07（confirmed-A） |
| 4 | 2026-09-19 | 「这个加入003，开始003」 | 批准（W1：含「开始」口令 + 一轮范围决定） | r002-07 §8 |

## 4. 无文档变更的提交（若有）

（实现期若某步确实无对外行为变化，在此登记一行并说明原因。）
