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

## 7. CRUD 速度的实测与折算（2026-09-17）

### 7.1 成本结构：速度差别到底差在哪

| 成本项 | 手写 SQL | SQLAlchemy Core | ORM | 说明 |
| --- | --- | --- | --- | --- |
| 驱动往返（DBAPI + 网络/进程） | 相同 | 相同 | 相同 | 同一驱动、同一语句，写法不改变这部分 |
| **语句条数（N+1）** | 可控 | 可控 | **最容易踩**（关系遍历/懒加载） | 本项目列表页已固化用聚合查询（`room_aggregates`），与写法无关地把这项压掉 |
| **行 → 对象映射** | 自己写（实测 +0.3~0.5 µs/行） | 轻（Row） | **重**（`populate_state`：身份映射 + 实例化 + 属性事件） | SQLAlchemy 官方性能 FAQ 把「把行转成映射对象的复杂度 + CPython 开销」列为 ORM 慢的主因，并建议"只取需要的列"或 `Bundle` |
| 写路径簿记 | 无 | 无 | unit-of-work / flush | 官方 FAQ 专列一节「inserting 400,000 rows with the ORM and it's really slow」 |
| 预编译语句/缓存 | `psycopg` 可开 prepared statements | 同 | 同 | 三者都能吃到同一层优化 |

### 7.2 本机实测（SQLite 内存库，5 次取最快，纯 Python 侧）

| 操作 | 耗时 |
| --- | --- |
| ① 批量插入 `executemany`（单事务） | **1.19 µs/行** |
| ② 逐行 `execute` 插入（单事务） | **2.28 µs/行**（≈ ①的 1.9 倍：语句次数比语句成本更贵） |
| ③ 单行查主键 → tuple | **2.69 µs/次** |
| ④ 单行查主键 → 手写 dataclass 映射 | **3.16 µs/次**（映射 +0.45 µs） |
| ⑤ 列表取 5000 行 → tuple | **0.70 µs/行** |
| ⑥ 列表取 5000 行 → dataclass 映射 | **1.03 µs/行**（映射 +0.30 µs） |
| ⑦ 批量 UPDATE（`executemany`） | **1.22 µs/行** |
| ⑧ 聚合查询 GROUP BY（50 组） | **2.0 µs/次** |

读法：手写 SQL + 手写映射的代价是**亚微秒到 1 µs 级/行**；把 5000 行映射一遍约 1.5 ms。
注意这是**纯 Python 侧**成本（SQLite 在进程内，不含网络往返）；真实 PostgreSQL 单语句还要加 localhost 往返（量级 10⁻¹ ms，装好库后实测，见 §7.4）。

### 7.3 折算到本项目：速度不构成决策依据

- **单请求语句数**：详情页 3~5 条、列表页 2 条（列表 + 批量聚合）、批准/结束 3~6 条（含行锁与批量 UPDATE）。
- **数据规模**：房间数十、成员 ≤8、消息每房数百、纪要每房 1 行。最大的一条列表查询也是"几十行 × 聚合"。
- 即使 ORM 在映射与 flush 上比手写慢数倍，落到本项目是**每请求亚毫秒以内的差异**；而本项目真正的耗时在 **LLM 调用（秒级）**与**音视频（不经过业务库）**，演示与面试都感知不到 CRUD 速度差。
- 真正会拖慢系统的两条风险与 ORM 无关，且已被固化：**N+1 查询**（列表页强制用聚合查询）与**缺索引**（`rooms(status, created_at)`、`room_members(room_id, role) WHERE active`、`chat_messages(room_id, created_at DESC)` 等已写进房间设计页 §3）。
- 结论：**P10 的决策依据是 ADR-0005 §2 的那些维度**（题面显性、可审查、精细 SQL 表达力、依赖、面试叙事），不是速度。

### 7.4 待实测（需要环境；两项都可补）

1. 本机无 SQLAlchemy：可用 `uv` 建**临时 venv** 装 `sqlalchemy`，跑同一套 CRUD 的三方对比（手写 / Core / ORM），全程不影响项目环境 —— 需用户授权（涉及下载安装）。
2. 本机无 PostgreSQL（P9=A 待执行）：库装好后在**真库**上跑 8 人房间规模的真实脚本，测单请求端到端耗时（含往返），产出一张"本项目真实语句"的性能表。

## 6. 待拍板

| 编号 | 事项 | 选项 | 建议值 |
| --- | --- | --- | --- |
| P10 | 数据访问层与迁移 | A 手写 SQL + 版本表 / B SQLAlchemy Core + Alembic / C ORM + Alembic / D 手写 + Alembic 迁移 | **A** |

## 变更记录

- 2026-09-17 建立（proposed，待拍板）。
- 2026-09-17 追加 §7：CRUD 速度的成本结构、本机实测数字与折算结论（速度不是决策依据；待装环境后补真库对比）。
