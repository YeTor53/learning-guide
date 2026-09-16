---
title: 风格指南
description: 命名、提交与文档的 Do / Don't 约定。
type: reference
status: draft
owner: 陀梓皓
updated: 2026-09-16
---

<!-- overview -->
起量阶段的极简风格约定；规则改动走小提交并在本页留痕。

| 项 | Do | Don't |
| --- | --- | --- |
| 文档文件名 | 带轮次：`rNNN-短名.md`；项目级用 `global-` 前缀 | `新建文档.md`、`design2.md` |
| 文档页类 | 一页一类：concept / task / tutorial / reference | 参考页讲概念、概念页列参数 |
| 事实来源 | 一个概念只在一处讲，别处链接 | 同一张表抄两处 |
| 提交信息 | `type(scope): ≤50字 [Req: rNNN]` | `update`、`fix bug` |
| 提交粒度 | 一个逻辑增量一次提交 | 混多个不相关改动 |
| 密钥 | 只进 `.env`（本地）/ `.env.example`（占位） | 写进代码、文档、截图 |
| 代码注释 | 说明为什么这么做 | 复述代码在做什么 |
| 文档内容 | 本项目方案与决策 | 外部出处、研究笔记、外部案例对照 |

## What's next

M1 落地后补：目录与模块命名约定、API 路径与响应信封约定。
