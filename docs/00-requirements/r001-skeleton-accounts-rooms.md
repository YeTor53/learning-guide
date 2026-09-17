---
title: r001 骨架 · 账户 · 房间（里程碑 M1）
description: M1 需求单：前后端骨架、SQL schema 与种子数据、注册/登录/登出、房间创建/列表/详情、加入申请的结构与流转。
type: requirement
status: draft
owner: 陀梓皓
updated: 2026-09-16
---

<!-- overview -->
本页只写「这一轮要做成什么、怎么算做完」；怎么做（表结构、函数、接口）见 `docs/01-architecture/r001-app-architecture.md`。项目方向、里程碑与已决事项见 `docs/00-project/global-roadmap.md`（不在此处重复）。

## 1. 目的

搭出可运行的前后端骨架与数据层，把「账户 + 房间」这条业务骨架跑通：让评审能注册、登录、建房、看到房间列表与详情、提交加入申请并被批准，且数据全部落进 SQLite、可用一条命令重建。

## 2. 边界

**做**
- 仓库骨架：Next.js 16（App Router）+ TypeScript 一体仓，`npm run dev` 起全栈。
- 数据层：手写 `schema.sql`（全部 7 张业务表一次建好，含索引/约束）+ `seed.sql`（演示账号、示例房间、历史消息、一条已结束房间的纪要）+ 初始化脚本，一条命令可 `--reset --seed`。
- 账户：注册、登录、登出、当前用户查询；密码 scrypt 加盐哈希；会话走 HttpOnly 签名 Cookie。
- 房间：创建（主题/标题/简介）、列表、详情；房间码生成；加入申请（提交/列表/批准/拒绝）；离开房间；结束房间。
- 权限骨架：三角色数据模型 + 服务端校验函数（Host 才能批申请/结束房间；Moderator/Host 才能看申请列表）。
- 冒烟脚本（M1 阶段）：`register → login → 建房 → 列表 → 申请 → 批准 → 离开` 走真实 HTTP。

**不做（本轮明确不碰）**
- LiveKit 相关一切（起服务、签 Token、音视频、屏幕共享、举手、焦点）→ M2/M3。
- 文字群聊实时收发与拉取、LLM 纪要生成 → M3/M4（本轮只建表、只留种子里的历史消息）。
- 邀请链接/邀请码的生成与校验 API → M2（本轮只建 `invites` 表、只实现房间码生成函数）。
- 踢人、8 人上限拒绝提示 → M2（本轮建房时写入 `capacity`，不做人数校验的对外行为）。
- 公网部署、Docker Compose、录制、管理后台（→ M5 加分项，按时间取舍）。

## 3. 验收清单

- [ ] `node scripts/db-init.mjs --reset --seed` 一条命令重建库并打印每张表的行数（真实输出）。
- [ ] `npx tsc --noEmit` 通过。
- [ ] `node scripts/smoke.mjs` 全绿，打印每步的 HTTP 状态与关键字段。
- [ ] 未登录访问 `/rooms/new` 被引导到登录页；未登录调 `POST /api/rooms` 返回 401。
- [ ] 注册 → 登录 → 登出 → 再访问受保护页面需重新登录。
- [ ] 建房后 `/rooms` 列表与 `/rooms/<id>` 详情显示的是库里的真实数据（改库后刷新页面可见变化）。
- [ ] 加入申请：同一人对同一房间重复提交返回 409（不产生第二条 pending）；非 Host/Moderator 调批准接口返回 403。
- [ ] 结束房间后该房间不可再提交申请（返回 409），列表状态显示为已结束。
- [ ] 安全检索：`git grep -n "LIVEKIT_API_SECRET\|LIVEKIT_API_KEY"` 在 `src/` 下无命中代码（仅 `.env.example` 占位）。
- [ ] 文档已更新：本页状态、`docs/01-architecture/r001-app-architecture.md`、`docs/02-modules/` 对应模块页、README 当前轮次。

## 4. 影响面

- 新增仓库骨架与源码树（`src/`、`scripts/`），不改动既有文件（当前仓库只有文档）。
- 新增依赖：`next`、`react`、`react-dom`、`typescript`、`@types/*`（LiveKit 相关依赖推迟到 M2 加）。
- 不涉及数据库迁移工具（手写 SQL + 版本表），不涉及外部服务。

## 5. 风险

- `node:sqlite` 是实验性 API：本轮先用它（零安装），若在 Next 的 Node runtime 里不可用则改 `better-sqlite3`（接口差异封装在 `src/db/client.ts` 内）。
- 依赖安装走 npmmirror：Next 16 的原生二进制（`@next/swc-win32-x64-msvc`）若取不到，需切官方 registry 重装（见设计页 §12）。
- 16 小时预算偏紧：本轮若超时，优先保证「骨架 + 账户 + 房间列表/详情 + 申请批准」可演示，房间码/离开/结束可延后到 M2 的第一轮。

## 6. 归宿与口径

- 产物归宿与命名口径见 `docs/00-project/global-roadmap.md` §1（单一事实源，不在此重复）。
- 本轮无外部系统导入导出，无字段口径对齐事项。
- 密钥禁令：`.env` 不入库；`.env.example` 只放占位值。

## 7. 文档产出（硬产出，与本轮代码同提交）

| 文档 | 时机 |
| --- | --- |
| 本需求单（转 approved、验收逐条勾选） | 轮次开始与结束 |
| `docs/01-architecture/r001-app-architecture.md`（转 approved） | 设计批准时 |
| `docs/02-modules/r001-data-layer.md`、`r001-auth.md`、`r001-rooms.md`（职责/接口/关键逻辑/变更记录） | 每 cp 落一页 |
| `README.md`（怎么跑 / 环境变量 / 演示路径回填）、`docs/00-project/global-roadmap.md`（里程碑 M1 状态回填） | 轮次结束 |

## 8. 关联

- 里程碑：M1（`global-roadmap.md` §3）
- 设计页：`docs/01-architecture/r001-app-architecture.md`
- 决策：`docs/03-decisions/global-adr-0001-selfhosted-livekit.md`（M2 生效，本轮不涉及）

## What's next

设计页待批准（P5/P6 与设计页 §11 的 R1~R5 一起拍板）→ 转 approved → 开 `req/r001-*` 分支，按 cp-r001-1..N 增量实现。
