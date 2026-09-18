---
title: r002 变更与进度记录
description: r002 逐 cp 的文件清单、验证证据与文档落点（实现期逐条追加）。
type: reference
status: draft
owner: 陀梓皓
updated: 2026-09-18
---

<!-- overview -->
本页按 cp 追加：动了哪些文件、跑了什么验证、证据原样（贴命令与输出摘要）、对应文档页面锚点。
验证未全绿不打 tag；工作区带脏状态不许开下一个 cp。

## cp 计划（见需求单 §10）

| cp | 内容 | 状态 |
| --- | --- | --- |
| cp-r002-1 | 文档先行：需求单 + 总设计增量 + 模块两页 + 归档归位 + 索引/README/roadmap 同步 | **进行中（本批，待批）** |
| cp-r002-2 | 后端：config 必填 + `services/livekit.py` + rooms/repositories/schemas/routers 增量 + 用例 + r001 两条测试欠账 +（R-6）索引迁移 | 未开始 |
| cp-r002-3 | 前端：房内页 + 4 组件 + 3 hooks + `api/livekit.ts` + 路由/入口 + 样式 | 未开始 |
| cp-r002-4 | 冒烟四步 + 教学页两篇 + README/AGENTS/roadmap 回填 + 需求单勾选与证据表 | 未开始 |

## 文档落点（矩阵对应）

| 文档 | 本轮落点 | 状态 |
| --- | --- | --- |
| 需求单 | `docs/00-requirements/r002-livekit-room.md` | 建立（draft） |
| 设计页（总设计增量） | `docs/01-architecture/r002-realtime-architecture.md` | 建立（draft） |
| 模块实现页 | `docs/02-modules/r002-livekit.md` | 建立（draft，实现回填随 cp-2/3） |
| 模块功能页 | `docs/02-modules/r002-livekit-features.md` | 建立（draft） |
| 使用者教学页 | `docs/tutorials/r002-livekit-demo.md` | planned（跑通后写） |
| 开发者教学页 | `docs/tutorials/r002-livekit-dev-guide.md` | planned（跑通后写） |
| 决策记录 | `docs/03-decisions/r002-adr-0011-realtime-presence-model.md`（9 条约定 + 5 条被否方案） | 建立（proposed，随设计一起批） |
| 重定向确认单 | `docs/rounds/r002-livekit/redirect-01.md` | confirmed-C（批复「设计进行」，结论已落地） |
| 索引/项目级 | `docs/00-requirements/README.md`、`README.md`、`AGENTS.md`、`global-roadmap.md` | 索引行本批；其余随 cp/收官 |

## 逐 cp 记录（实现期追加）

### cp-r002-1（文档先行）

- 文件：`docs/00-requirements/r002-livekit-room.md`、`docs/01-architecture/r002-realtime-architecture.md`、`docs/02-modules/r002-livekit.md`、`docs/02-modules/r002-livekit-features.md`、`docs/99-archive/r002-ahead-invites.md`、`docs/rounds/r002-livekit/{design,changes,review}.md`；改 `docs/00-requirements/README.md`、`README.md`、`docs/00-project/global-roadmap.md`、`docs/02-modules/r001-rooms*.md`、`docs/00-requirements/r001-*.md`、`docs/rounds/r001-skeleton/{design,review}.md`（旧归档路径指针同步）。
- 验证（实测输出）：
  - front matter 解析：8 个新建/改写页全部通过；代码围栏成对（另修掉 r001 功能页 1 处未闭合围栏）。
  - 全库内部链接扫描：仅剩 2 个**有意**的 planned 链接（`docs/tutorials/r002-livekit-demo.md`、`r002-livekit-dev-guide.md`，随 cp-r002-4 落地），其余全部解析成功；顺手修掉风格指南里 1 处 ADR 占位路径。
  - `git grep -n "r001-ahead-m2-m3-rooms"`：无命中（历史迁移注记已改写为叙述式，避免假装是活链接）。
- 提交：`603049e`（归档页 `git mv` 重命名）→ `d1b62df`（内容与同步，17 文件 +1004/-102）。
  - 说明：首次 `git add` 因列表中含「已被重命名、工作区已不存在」的旧路径而整批失败，只提交了 `git mv` 那一步；故本 cp 落为两次提交（重命名 / 内容），**未使用 `amend`**（AGENTS 硬规矩 5：历史 append-only）。
- 状态：工作区只剩未跟踪的 `frontend/.vite/`（Vite 缓存；是否加进 `.gitignore` 待你一句话）。

## 重定向 / CR 台账

| 单号 | 类型 | 触发 | 定性 | 状态 | 结论 |
| --- | --- | --- | --- | --- | --- |
| `redirect-01.md` | 用户新意见（断线重连与状态保持） | 设计待批阶段，用户问「断线重连，状态保持有码」 | C（后续工作）+ 其中「连接层/设备层」属提前做＝范围变更（按 L3 看待） | **confirmed-C（2026-09-18 批复「设计进行」）** | 断线重连（连接层）+ 设备状态保持（设备层）进 r002；业务状态恢复留 M3/M5 ①；C-1 断线归因改用 SDK reason、C-2 同账号双开改为「后进踢掉先进 + 提示」、C-3 重连后本地轨道恢复行为待 cp-r002-3 实测 |

## 无文档变更的提交（若有）

（实现期若某步确实无对外行为变化，在此登记一行并说明原因。）
