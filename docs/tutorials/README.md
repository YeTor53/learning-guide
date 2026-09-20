---
title: 教学页索引（受众与适用轮次）
description: 四页教学页分别给谁看、覆盖到哪一轮、按什么顺序读。只描述现状，不定义规约。
type: reference
status: active
owner: 陀梓皓
updated: 2026-09-20
---

<!-- overview -->
本目录的页分两类受众：**使用者**（怎么跑、怎么演示）与**开发者**（怎么改、怎么扩展）。本页给阅读入口；内容事实源仍是 `02-modules/` 与 `01-architecture/`。

| 页 | 受众 | 覆盖 | 一句话 |
| --- | --- | --- | --- |
| `r001-postgres-setup.md` | 开发者 / 部署 | r001 | 本机 PostgreSQL 与数据库初始化（`db_init.py`、迁移、种子） |
| `r002-livekit-setup.md` | 使用者 / 部署 | r002 | LiveKit 两种模式（Cloud / 自建）与 `.env` 配置、启动服务 |
| `r002-livekit-demo.md` | 使用者 / 演示 | r002 + r003 | 九步演示脚本（含第 9 步走控制坞「结束房间」的新入口） |
| `r002-livekit-dev-guide.md` | 开发者 | r002 + r003 | 模块地图、Token 策略替换、自助加能力五步、打桩与排障、6 个实测坑 |
| `r004-room-extras-demo.md` | 使用者 | r004（M3） | 房内四件事怎么用（群聊 / 举手 / 焦点 / 共享）+ 两人对练脚本 + 排查表 |
| `r005-capacity-and-events.md` | 使用者 | r005 | 上限数的是「名额」不是在线人数、房间事件系统消息读法 |
| `r009.5-r008-r009-user-guide.md` | 使用者 / 演示 | r008 + r009（+ r009.5 补正） | 讨论纪要怎么出、限时邀请怎么发、焦点怎么给与退（含实测数字） |
| `r010-transcription-user-guide.md` | 使用者 / 演示 | r010 | 说的话怎么变成文字并进纪要；演示前要起哪个进程、免费档限制 |
| `r009.5-stage-motion-verify-dev.md` | 开发者 | r009 + r009.5 | 几何/动效两个校验脚本怎么跑、令牌改哪里、判据与三条踩坑 |
| `r012-admin-and-global-chat.md` | 使用者 / 演示 | r012 | 管理后台怎么用（四分区 + 三动作）、大屏怎么用、隐身在两端长什么样 |
| `r012-superadmin-dev-guide.md` | 开发者 | r012 | 加一个管理动作 / 加一类 SSE 通知各改哪几处、隐身三道拦线、四个实测坑 |
**顺序建议**：首次跑起来 → `r002-livekit-setup.md`；做演示 → `r002-livekit-demo.md`；动手改代码 → `r002-livekit-dev-guide.md`；换机器/重装数据库 → `r001-postgres-setup.md`。

**尚未覆盖（2026-09-20 r009.5 清点）**：r006（界面同步与优化）、r007（主题与首屏）两轮的**使用者 / 开发者教学页仍缺**——r009.5 只补了 r008/r009 两轮（见 `docs/00-requirements/r009.5-debt-backfill.md` §2），该缺口登记在 `docs/README.md` §5 与 roadmap §9。
