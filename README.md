# Learning Guide · 学习讨论室（LiveKit 迷你产品）

围绕一门学习主题的多人音视频小组讨论室：账户、房间、等候室审批、三种角色权限、群聊、举手与焦点发言、屏幕共享、服务端踢人、房间结束后的 LLM 讨论纪要。

> 当前状态：**r001~r010 与 r009.5 已全部合入 `main`（`96b1153`；`round-r001-done` … `round-r010-done`、`round-r009.5-done` 齐）**；当前进行 **r011（补正轮）**：欠账补正 + 三处授权例外（满员自动拒待批申请 / 邀请码入口与未登录闭环 / worker 健康上报），见 `docs/00-requirements/r011-debt-backfill.md`。三条页面：房间列表 `/` → 交流页 `/rooms/:id/live`（专注感）→ 等待室 `/rooms/:id/wait`（温暖感）；**原「房间管理页」已删除**（治理动作只在交流页抽屉；ADR-0012 / redirect-06）。
> r001 已落地（**当时口径**）：数据层与种子、账户会话、建房 / 列表 / 详情 / 加入申请 / 批准 / 拒绝 / 撤回 / 离开 / 结束、前端 5 页与左侧边栏外壳、真实 HTTP 冒烟。证据：`pytest` 72 项、冒烟 22 项、前端类型检查与构建全绿、9 步浏览器实操（需求单 §3.1 的 E1~E10）；轮次档案见 `docs/rounds/r001-skeleton/`。
> r002 设计入口：需求单 `docs/00-requirements/r002-livekit-room.md`、总设计增量 `docs/01-architecture/r002-realtime-architecture.md`、模块页 `docs/02-modules/r002-livekit.md` 与 `r002-livekit-features.md`。

## 项目地图

| 位置 | 内容 |
| --- | --- |
| `docs/00-project/global-roadmap.md` | 项目级规划：终点、里程碑与验收点 |
| `docs/rounds/` | 轮次档案（`rNNN-*/`：design / changes / review / CR） |
| `docs/00-requirements/` | 需求单（`rNNN-*.md`）与变更记录 |
| `docs/01-architecture/` | 总体架构、模块图、数据流 |
| `docs/02-modules/` | 每个模块一份：设计 + 实现 |
| `docs/03-decisions/` | ADR：为什么这么设计、改了什么约定 |
| `docs/04-style/` | 风格指南：命名 / 提交约定 + 前端设计系统（色板、排版、动效令牌、图标与可达性） |
| `docs/glossary.md` | 术语表 |
| `AGENTS.md` | 给 AI 的项目规则（禁区、验证命令、提交规范） |

## 已定选型

- **数据库**：PostgreSQL（本机 17.11，库 `learning_guide`，角色 `lg_app`）
- **前端**：React 18 + Vite + TypeScript + TanStack Query，图标统一 Lucide（设计规范见 `docs/04-style/global-style.md`）
- **后端**：Python 3.11 + FastAPI + psycopg3，conda 环境 `learningguide`
- **数据层**：手写 SQL + 轻量版本表；**实时音视频**：LiveKit Cloud 为主、自建留档；**纪要**：DeepSeek
- **交付物**：zip + GitHub 仓库 + npm 包（发布细则待定）

## 工程说明

- 实施节奏、里程碑与验收证据：`docs/00-project/global-roadmap.md`；各轮需求单索引：`docs/00-requirements/README.md`；轮次档案：`docs/rounds/`
- 需求单与逐条验收：`docs/00-requirements/`
- 提交前检查命令、禁区与提交规范：`AGENTS.md`
- 视觉资产：`frontend/public/thinker.webp` —— 罗丹《思想者》，克利夫兰艺术博物馆藏品照（Wikimedia Commons，CC0），处理方式见 `docs/03-decisions/r001-adr-0010-visual-assets.md`

## 怎么跑（本机）

前置：本机 PostgreSQL 17.11 服务在跑、库与角色已建（见 `docs/tutorials/r001-postgres-setup.md`，含建表授权步骤）、
conda 环境 `learningguide` 已就绪、仓库根 `.env` 已填（`DATABASE_URL` / `SESSION_SECRET`）。

```bash
# ① 初始化数据库（可重复执行；--reset 会清空重建）
conda activate learningguide
python backend/scripts/db_init.py --reset --seed
# 期望输出：schema_migrations 12 / 若干演示账号与房间 / invites 0 / chat_messages 若干
# 演示账号（口令均为 demo1234）：host@example.com、mod@example.com、part@example.com
# 演示超管（r012，口令同 demo1234）：admin@example.com —— 隐身进任意房 + 管理后台入口（侧栏，仅它可见）

# ② 后端（开发）
cd backend && python -m uvicorn app.main:app --reload --port 8000
# 自检：curl http://127.0.0.1:8000/api/auth/me  → {"ok":true,"data":{"user":null}}

# ③ 前端（开发，Vite 代理 /api → 8000，浏览器只看到 localhost:5173 一个源）
cd frontend && npm install && npm run dev
# 打开 http://localhost:5173
# 或一键启动（Windows，起后端 8000 + 前端 5173）：dev.bat        # 自检：dev.bat check   停止：dev.bat stop

# ④ 演示形态（单进程同源）：先把 .env 的 APP_ENV 改成 demo，再构建并只起后端
cd frontend && npm run build
cd backend && python -m uvicorn app.main:app --port 8000
# 打开 http://127.0.0.1:8000

# ⑤ 验证
python backend/scripts/smoke.py --base-url http://127.0.0.1:8000   # 真实 HTTP 全链路，末尾打印 PASS n/n
pytest backend/tests -q                                            # 174 项（含 r002 治理/容量、r008 纪要/邀请、r009 焦点、r010 转写、r011 满员自动拒/心跳、r012 身份与在线；2026-09-20 实测）
```

- **地址口径（r011 redirect-03 实测）**：后端一律用 `127.0.0.1:8000`（写成 `localhost:8000` 时每次请求会多等约 **2 秒** —— 实测 2070ms vs 6ms：uvicorn 只绑 IPv4，而 Windows 上 `localhost` 先解析到 `::1`，被拒后才回退）；前端一律用 `localhost:5173`（浏览器安全上下文要 `localhost`，且 Vite 只监听回环 `::1`）。
- 冒烟脚本会写入两个随机邮箱账号与一个房间；跑完可再执行一次 `db_init --reset --seed` 恢复演示数据。
- r002 需要额外的实时凭据：`.env` 里的 `LIVEKIT_MODE` / `LIVEKIT_URL` / `LIVEKIT_API_KEY` / `LIVEKIT_API_SECRET`（Cloud 或自建二选一）；**键名与形状见上，值只放本机 `.env`**。第一次跑请看教程一：`docs/tutorials/r002-livekit-setup.md`；演示与排查看教程二：`docs/tutorials/r002-livekit-demo.md`
- 依赖版本：后端见 `backend/requirements*.txt`（conda `learningguide` 的 pip freeze）；前端见 `frontend/package.json`（npm 走 npmmirror）。
- 密钥与连接串只放本机 `.env`（不入库）；示例见 `.env.example`，键表见架构页 §5。

## 两个浏览器演示完整路径（约 6 分钟）

> 两个窗口都用**不同账号**（一个房主、一个参与者），窗口并排；建议用无痕窗口避免共用 Cookie。

1. **房主**：浏览器 A 打开 http://localhost:5173 → 右上「创建房间」→ 选主题（14 个预设中的任意，如「西方哲学史」）+ 标题 + 简介 → 创建。
2. **参与者**：浏览器 B 打开首页 → 找到刚才那间房 → 「申请加入」（提交后落到**等候室**，显示「已提交 · 等待房主批准 · 进入房间」三步时间线）。
3. **房主**：在房间交流页打开右侧抽屉 → 「成员」tab → 待批申请处点**批准** → B 端**自动进入**交流页（不需要手动点）。
4. **看两端同步**：A 界面状态条与 B 端的「N / 容量 成员」**秒级一致**（实测 0.23~0.46 秒）；A 静音后 B 端该成员格上出现「已静音」小图标。
5. **能力演示**：B 举手（A 端成员列表可见「✋」）→ A 端「给焦点」（该成员画面放大，底部出现「某某正在发言」；焦点按钮按角色分流：房主「取得焦点」/ 协管「申请焦点」/ 参与者「举手」）→ B 开**屏幕共享**（共享画面顶掉焦点格，停止后恢复）→ 在「讨论」tab 发两条消息（两端实时 + 落库）。A 端还可「退出焦点」把主区还原。
6. **语音转写（r010）**：**先起第三个进程** `agents.bat`（零配额联调：`set AGENT_STT=fake && agents.bat`；真识别直接 `agents.bat`，消耗免费档额度）→ 然后再**建房**进房（派单只发生在建房时）→ 控制坞出现「**转写：开启**」（实测约 13 秒；之前显示「未开启」是正常的）→ 开麦说中文 → 抽屉「讨论」出现**转写气泡**（先淡色「识别中…」，定稿后成正式气泡）。关掉麦克风即不参与转写。
7. **限时邀请**：A 端抽屉「邀请」tab → 选 30 秒 + 1 次 → 生成 → 复制链接 → 浏览器 C（无痕）打开该链接 → **直接进房**（跳过等候室），A 端消息列表出现「XX 通过邀请链接加入」。
8. **接管与结束**：A 端「踢人」可把某人移出（服务端 LiveKit 真断开，非前端假踢）；点**结束房间** → 房间转只读，成员全部退出。
9. **讨论纪要**：回到房间列表 → 切到「已结束」→ 卡片上点「**讨论纪要**」→「生成讨论纪要」→ 几秒后出现 Markdown 正文（实测 6.0 秒 / 632 字：主题与背景 / 讨论要点 / 分歧与未决 / 待办 / 一句话总结）→ 再点「重新生成」覆盖同一份；转写内容也会作为素材交给纪要模型。
10. **验证命令**（可选）：`python backend/scripts/smoke.py --base-url http://127.0.0.1:8000`（含「生成限时邀请码 / 凭码加入 / 生成讨论纪要」三步）。
