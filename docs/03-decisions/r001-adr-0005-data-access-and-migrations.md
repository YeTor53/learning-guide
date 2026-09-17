---
title: r001-ADR-0005 数据访问层与迁移方式（手写 SQL vs SQLAlchemy/各类 ORM）
description: P10 的讨论与建议：手写 SQL + 轻量版本表（含与 SQLAlchemy Core/ORM+Alembic 的逐维度对比与代价）。
type: adr
status: proposed
owner: 陀梓皓
updated: 2026-09-17
---

<!-- overview -->
P10 决定「后端怎么碰数据库、怎么做迁移」。本文给逐维度对比、三种组合的代价与建议；**待用户拍板**。
前置已定：P5=PostgreSQL、P6=Python 后端、P9=本机安装 PostgreSQL。约束：题面要求「可运行的 SQL Schema + 迁移或初始化脚本」，交付需可复核，面试会追问取舍，单人 16 小时预算。

## 1. 候选

| 代号 | 方案 | 一句话 |
| --- | --- | --- |
| A | **手写 SQL + 轻量版本表** | SQL 写在 `app/db/sql/*.sql`，`migrate.py` 按文件名顺序执行并记 `schema_migrations`；查询用参数化 SQL + 行映射函数 |
| B | SQLAlchemy Core + Alembic | 用表达式构造器写查询，迁移交给 Alembic |
| C | SQLAlchemy ORM + Alembic | 定义模型类，CRUD 走 ORM，迁移 autogenerate |
| D | 折中：查询手写 + 迁移用 Alembic（原生 SQL 版本） | SQL 仍是手写，只把「迁移器」换成 Alembic |

## 2. 逐维度对比

| 维度 | A 手写 SQL | B Core | C ORM + Alembic | 本项目谁更优 |
| --- | --- | --- | --- | --- |
| 题面「SQL 设计」是否显性 | SQL 就是交付物本身 | SQL 被表达式包裹，需额外交 DDL | 需额外交 DDL（或从模型导出） | **A/D** |
| 可审查性（评审逐行读） | 逐行可读，`EXPLAIN` 直用 | 需脑内翻译成 SQL | 需读模型 + 猜生成 SQL | **A/D** |
| 精细 SQL 表达力（本项目真用到） | 部分唯一索引、`FOR UPDATE` 房间级互斥、`ON CONFLICT` upsert、批量 UPDATE 都最自然 | 多数可表达，方言特性要绕 | 上述几项在 ORM 里最别扭（要 raw SQL 逃逸） | **A/D** |
| 类型安全 / 重构 | 运行时才知列名错 → 需测试兜底 | 构造期报错 | 构造期报错 | B/C |
| 迁移能力 | 版本表 + 顺序执行；**无 downgrade** | Alembic 全套（含 downgrade） | Alembic 全套 | B/C（A 用 `--reset` 重建补偿） |
| 样板量 | 每条语句手绑参数 + 映射（可用 `row_factory` → dataclass 降低） | 少些样板 | 最少样板 | C |
| 调试可解释性 | 日志即 SQL | 需开 `echo` | 需开 `echo`，且有身份映射缓存等概念 | **A/D** |
| 注入安全 | 参数化即可（本项目禁止拼 SQL，写进 AGENTS） | 天然参数化 | 天然参数化 | 平 |
| 人的学习成本 | 只要会 SQL | 多一层构造器 API | 多一层 ORM 概念与坑 | **A** |
| 与 FastAPI 契合 | 任意（依赖注入 + 连接池） | 好 | 好 | 平 |
| 面试叙事 | 能直接讲清「为什么手写」与代价 | 能讲，但要解释表达式层的必要性 | 需解释「为什么在需要精细 SQL 的项目里上 ORM」 | **A** |
| 新增依赖 | 0（仅 `psycopg`） | +sqlalchemy | +sqlalchemy +alembic | **A** |

## 3. 三种组合的代价清单

| 方案 | 得到的 | 付出的 |
| --- | --- | --- |
| A（建议） | 交付物里 SQL 是主角；并发与约束写法直接；零额外依赖；目录与验证极简 | 无编译期检查（用 pytest 断言表/列/约束存在与行为补偿）；无 downgrade（开发期 `--reset` 重建）；手绑参数有样板 |
| B/C | 类型安全、迁移成熟、CRUD 快 | 多两层概念与依赖；SQL 被包起来，反而要额外交一份 DDL 才能满足题面；本项目的锁/部分唯一索引/批量 UPDATE 是 ORM 最不擅长的部分 |
| D | SQL 仍可读，同时拿到 Alembic 的版本管理（含 downgrade） | 要装 `alembic` 并维护 `env.py`；迁移以「原生 SQL 版本文件」写，等于 A 的写法 + 一层工具 |

## 4. 建议

**A：手写 SQL + 轻量版本表**（FastAPI + `psycopg` 连接池）。理由：

1. 题面明确要「可运行的 SQL Schema」，手写 SQL 让交付物本身就是答案，不需要额外导出 DDL；
2. 本项目 SQL 里恰有一批手写才自然的写法：部分唯一索引防重复申请、`SELECT … FOR UPDATE` 做房间级互斥、`ON CONFLICT` 单行 upsert 纪要、结束房间的批量 UPDATE；
3. 单人 16 小时，少一层框架概念就少一类踩坑（ORM 的会话/身份映射/懒加载在并发脚本里很费时）；
4. 面试追问「为什么不用 ORM」时有清晰、可辩护的答案（见上表与代价清单）。

**代价与补偿**：① 用 pytest 断言 schema 与约束行为（表/列存在、部分唯一索引真的挡住重复 pending、CHECK 真的挡住非法转移）；② SQL 常量集中放 `app/db/sql/queries/*.sql` 或用模块级常量，避免散落拼接；③ 迁移只做「前进」：`schema_migrations` 记版本 + `--reset` 全量重建，交付口径写明是「初始化脚本 + 版本表」。

**升级路径**：若后期迁移变复杂（多环境、需回滚），按 D 换成 Alembic（查询层不动）。

## 5. 影响

- 目录：`backend/app/db/sql/001_schema.sql`、`002_seed.sql`；`app/db/pool.py`；`app/db/migrate.py`（`run_migrations / reset_schema / seed / table_counts`）；`app/repositories/*.py`（SQL 绑定）。
- 验证：`python scripts/db_init.py --reset --seed` 打印各表行数；`pytest tests/test_schema.py` 断言 schema 与约束。
- 依赖：`psycopg[binary,pool]`、`fastapi`、`uvicorn`、`pydantic`（安装前需用户批准）。

## 6. 待拍板

| 编号 | 事项 | 选项 | 建议值 |
| --- | --- | --- | --- |
| P10 | 数据访问层与迁移 | A 手写 SQL + 版本表 / B SQLAlchemy Core + Alembic / C ORM + Alembic / D 手写 + Alembic 迁移 | **A** |

## 变更记录

- 2026-09-17 建立（proposed，待拍板）。
