---
title: r001 教程：本机装 PostgreSQL 并建好项目库（含 Stack Builder 处置）
description: 从 EDB 安装向导逐页选择到建角色建库、连接自检与写入 .env 的手工步骤清单。
type: tutorial
status: draft
owner: 陀梓皓
updated: 2026-09-17
---

<!-- overview -->
目标：在这台 Windows 机器上装好 PostgreSQL 17，建出本项目要用的**角色**与**库**，直到 `DATABASE_URL` 能连通。
对应总设计 §12 环境准备第 1~2 步（P9=A 本机安装）。涉及你的手动步骤都在 §6 的清单里，逐条可勾选。

## 1. 安装向导逐页怎么选

| 向导页 | 怎么选 | 说明 |
| --- | --- | --- |
| Installation Directory | 默认 `C:\Program Files\PostgreSQL\17` | 无需改 |
| Select Components | **PostgreSQL Server ✓**、**pgAdmin 4 ✓**、**Command Line Tools ✓**、**Stack Builder ✗** | pgAdmin 用来图形化建库、看表（强烈建议）；Stack Builder 见 §2，可不勾 |
| Data Directory | 默认 | — |
| **Password** | **自己设一个强密码并记住** | 这是 `postgres` 超级用户密码，§4 建角色/库要用；**不要发给我** |
| Port | `5432`（若提示被占用，记下实际端口） | 我的脚本会按你给的端口写 `.env` |
| Locale | 默认 | 中文字符由库级 `ENCODING 'UTF8'` 保证 |
| 最后一步「Launch Stack Builder at exit?」 | **取消勾选**（已进去就点 Cancel） | 见 §2 |

## 2. Stack Builder 是什么，为什么不用选

- 官方定义（EDB 文档）：Stack Builder 是一个**图形化工具，用来下载安装"补充模块"**（modules）到已安装的 PostgreSQL 上，它会自动解析依赖；**需要联网**；安装完成后也可随时从开始菜单 `PostgreSQL > Application Stack Builder` 打开。
- 界面：先选「安装源」（例如 *PostgreSQL 17 on x86-64 Windows*），再在树形列表里按类别勾选模块（已装的会标 `(installed)`）。
- **本项目的结论：一个都不勾，直接 Cancel。** 理由：
  - 我们用的驱动是 `psycopg` 3（Python 包，自带 libpq 支持），**不需要** ODBC / JDBC / Npgsql（那是别的语言的驱动）；
  - 没有地理数据 → 不需要 PostGIS；没有定时任务 → 不需要 pgAgent；应用侧连接池用 `psycopg_pool`（进程内），不需要 pgBouncer 这种中间件；
  - 不需要逻辑复制（SLONY）、不需要额外扩展。
- 误装了也无害：这些模块是独立安装的，可单独卸载，不影响 PostgreSQL 服务本身。
- 唯一"可能有用"的图形工具是 **pgAdmin 4**，它在**主安装向导的 Select Components 里**（不在 Stack Builder 里），建议勾上。

## 3. 装完自检（三条命令）

```powershell
# ① 服务是否在跑（名字形如 postgresql-x64-17）
Get-Service postgresql*          # 或： sc query postgresql-x64-17

# ② psql 是否可用（本机此前没有 psql；不在 PATH 就用全路径）
& "C:\Program Files\PostgreSQL\17\bin\psql.exe" --version

# ③ 连接自检（会提示输入 postgres 密码）
& "C:\Program Files\PostgreSQL\17\bin\psql.exe" -U postgres -h 127.0.0.1 -p 5432 -c "select version();"
```

## 4. 建角色与建库（你手动执行，最低门槛：pgAdmin 图形界面）

打开 **pgAdmin 4** → 连接本机的 PostgreSQL 17（会用 §1 设的密码）→ 右键服务器 → **Query Tool** → 粘贴执行：

```sql
-- 1) 建应用角色（把 <你自己设的密码> 换成一个强密码，这个密码稍后要写进本机 .env）
CREATE ROLE lg_app LOGIN PASSWORD '<你自己设的密码>';

-- 2) 建项目库并归该角色所有（UTF8 保证中文正常）
CREATE DATABASE learning_guide OWNER lg_app ENCODING 'UTF8' TEMPLATE template0;
```

验证（同窗口执行）：

```sql
SELECT datname, pg_encoding_to_char(encoding) AS enc FROM pg_database WHERE datname = 'learning_guide';
SELECT rolname, rolcanlogin FROM pg_roles WHERE rolname = 'lg_app';
```

再用应用角色连一次（PowerShell，验证密码与权限）：

```powershell
& "C:\Program Files\PostgreSQL\17\bin\psql.exe" "postgresql://lg_app:<你自己设的密码>@127.0.0.1:5432/learning_guide" -c "select current_user, current_database();"
```

## 5. 写进本机 `.env`（等后端骨架落地时由我生成，你只需确认）

```
DATABASE_URL=postgresql://lg_app:<你自己设的密码>@127.0.0.1:5432/learning_guide
SESSION_SECRET=<我会用随机值生成>
```

`.env` 已在 `.gitignore` 里，**永不入库**；`.env.example` 里只放占位符。

## 6. 人工处理清单（勾选式）

- [ ] 安装向导 Select Components 页：勾 Server + pgAdmin 4 + Command Line Tools，不勾 Stack Builder
- [ ] Password 页：设好 superuser 密码并记住（不要发给我）
- [ ] 若被问 "Launch Stack Builder at exit?"：取消勾选；若已打开 Stack Builder：直接 Cancel（不勾任何模块）
- [ ] §3 的三条自检命令都有正常输出（服务在跑、psql 有版本、能连上）
- [ ] §4 的两条 SQL 执行成功，两条验证查询有结果
- [ ] 用 `lg_app` 连接测试返回一行 `current_user = lg_app`
- [ ] 告诉我三件事：**端口**（默认 5432？）、**pgAdmin 能否打开**、**是否愿意让我执行建库脚本**（不愿意的话就按 §4 自己跑）

## 7. 常见坑

| 现象 | 原因与处理 |
| --- | --- |
| `psql` 提示不是内部命令 | 安装目录未进 PATH：用全路径，或把 `C:\Program Files\PostgreSQL\17\bin` 加进 PATH 后**重开终端** |
| 安装后当前终端仍找不到新命令 | 环境变量刷新需要新终端窗口 |
| 连接报 `password authentication failed` | 默认 `pg_hba.conf` 用 `scram-sha-256`（密码认证）；确认密码无空格/引号问题 |
| 端口被占用（安装时提示换端口） | 记下实际端口，本教程所有命令与 `.env` 都用该端口 |
| 服务没启动 | 服务管理器里启动 `postgresql-x64-17`；后端报 `OperationalError` 时先查服务 |
| 中文乱码 | 建库时必须带 `ENCODING 'UTF8'`（§4 已含） |
| **`CREATE DATABASE 无法在事务块中运行`（SQL state 25001）** | pgAdmin 的 Query Tool **Auto-commit 默认关闭** → 语句被包在事务里，而 `CREATE DATABASE` 按 PostgreSQL 规定不允许在事务块内执行（与 SQL 写法无关）。两条解法：① Query Tool 工具栏把 **Auto-commit** 打开，再**单独**执行这一条；② 改用 psql（默认自动提交）：`psql -U postgres -h 127.0.0.1 -p 5432 -c "CREATE DATABASE ..."` 或 `createdb -U postgres -O lg_app -E UTF8 -T template0 learning_guide`。同类的"不能进事务块"语句还有 `CREATE INDEX CONCURRENTLY`、`VACUUM`、`ALTER SYSTEM` |
| Query Tool 是灰的/点不动 | pgAdmin 的 Query Tool 走 Tools 菜单或对象浏览器**某些节点的右键菜单**（官方文档口径）；必须先**连上服务器**（双击 `Servers > PostgreSQL 17` 输密码）并在树里选到 **数据库或更下面的节点**（如 `Databases > postgres`）|

## What's next

装好并在 §6 打勾后：我按 §4 的角色/库执行迁移与种子（`python backend/scripts/db_init.py --reset --seed`，待骨架落地），并回填 README「怎么跑」。
