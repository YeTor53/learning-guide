---
title: 教学页索引（受众与适用轮次）
description: 四页教学页分别给谁看、覆盖到哪一轮、按什么顺序读。只描述现状，不定义规约。
type: reference
status: active
owner: 陀梓皓
updated: 2026-09-19
---

<!-- overview -->
本目录的页分两类受众：**使用者**（怎么跑、怎么演示）与**开发者**（怎么改、怎么扩展）。本页给阅读入口；内容事实源仍是 `02-modules/` 与 `01-architecture/`。

| 页 | 受众 | 覆盖 | 一句话 |
| --- | --- | --- | --- |
| `r001-postgres-setup.md` | 开发者 / 部署 | r001 | 本机 PostgreSQL 与数据库初始化（`db_init.py`、迁移、种子） |
| `r002-livekit-setup.md` | 使用者 / 部署 | r002 | LiveKit 两种模式（Cloud / 自建）与 `.env` 配置、启动服务 |
| `r002-livekit-demo.md` | 使用者 / 演示 | r002 + r003 | 九步演示脚本（含第 9 步走控制坞「结束房间」的新入口） |
| `r002-livekit-dev-guide.md` | 开发者 | r002 + r003 | 模块地图、Token 策略替换、自助加能力五步、打桩与排障、6 个实测坑 |

**顺序建议**：首次跑起来 → `r002-livekit-setup.md`；做演示 → `r002-livekit-demo.md`；动手改代码 → `r002-livekit-dev-guide.md`；换机器/重装数据库 → `r001-postgres-setup.md`。

**尚未覆盖**：M3（r004）的使用者教程与开发者补节在 r004 的 cp-7 产出后加入本目录。
