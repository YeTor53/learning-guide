---
title: 把学习讨论室跑起来（r002 · 实时房间）
audience: 第一次拿到这份代码的人
time: 15 分钟
---

# 教程一：从零把学习讨论室跑起来（含实时音视频）

## 0. 你会得到什么

- 本机跑通：房间列表 → 申请加入 → 房主在**交流页抽屉**里批准 → 申请人**自动进入**音视频房间 → 房主移出/授权 → 结束房间
- 三条页面：`/`（房间列表）、`/rooms/:id/live`（交流页）、`/rooms/:id/wait`（等待室）

## 1. 前置

| 项 | 版本 | 说明 |
| --- | --- | --- |
| PostgreSQL | 17.x，库 `learning_guide`，角色 `lg_app` | 建库授权步骤见 `docs/tutorials/r001-postgres-setup.md` |
| conda 环境 | `learningguide`（Python 3.11） | 后端依赖在该环境里 |
| Node | 18+ | 前端 Vite |
| LiveKit | Cloud 项目 **或** 自建 `livekit-server` | 二选一，见第 2 步 |

## 2. 实时服务的两种接法（只改环境变量）

`.env`（仓库根，已 gitignore；**密钥只放这里，不贴聊天、不进仓库**）：

```bash
LIVEKIT_MODE=cloud          # cloud | self
LIVEKIT_URL=wss://<你的子域>.livekit.cloud
LIVEKIT_API_KEY=<API Key>
LIVEKIT_API_SECRET=<API Secret>
ROOM_CAPACITY=8             # 单房间座位上限（唯一口径）
```

- **Cloud**：`cloud.livekit.io` 建项目（邮箱注册即可，Build 免费无信用卡）→ Settings → Keys 抄 Key/Secret（Secret 只显示一次）→ Settings → Project 抄 `wss://` 地址。区域只有 EU / US 且**创建后不可改**，演示建议 US（跨太平洋延迟通常更低）。
- **自建**：下载 `livekit-server` 1.13.x Windows 包，`livekit-server --dev`（自带 `devkey`/`secret`），`.env` 写 `LIVEKIT_MODE=self`、`LIVEKIT_URL=ws://127.0.0.1:7880`。自建下「踢人」只能断开 + 短 TTL（300 秒），Cloud 能立即作废旧票。
- Token 的 `max_participants` 与「座位口径」的关系：应用层在**取票时**按在场人数拦（`ROOM_FULL`），Token 侧只是兜底。

## 3. 起后端

```bash
conda activate learningguide
python backend/scripts/db_init.py --reset --seed     # 可重复；--reset 会清空重建
# 期望输出：schema_migrations 3 / users 3 / rooms 3 / room_members 6 / join_requests 3
cd backend && python -m uvicorn app.main:app --reload --port 8000
curl http://127.0.0.1:8000/api/auth/me              # {"ok":true,"data":{"user":null}}
```

演示账号（口令均为 `demo1234`）：`host@example.com`（林泽宇，房主）、`mod@example.com`（陈慕，协管）、`part@example.com`（王一诺，参与者）。

## 4. 起前端

```bash
cd frontend && npm install && npm run dev      # http://localhost:5173，Vite 代理 /api → 8000
```

## 5. 一分钟自检

```bash
pytest backend/tests -q                                   # 期望 95 passed
python backend/scripts/smoke.py --base-url http://127.0.0.1:8000   # 期望 PASS 22/22
cd frontend && npx tsc --noEmit && npm run build           # 类型与构建
```

浏览器：登录 `host@example.com` → 列表页点卡片「回到讨论」→ 状态条右侧应显示 `已连接`。

## 6. 常见坑（都实测踩过）

| 现象 | 原因 | 处理 |
| --- | --- | --- |
| 后端启动即报 `no running event loop` | `LiveKitAPI` 必须在事件循环内构造 | 已在 `services/livekit.py` 用 `_run()` 包住，勿改回同步工厂 |
| 踢人后对方还能重连（Cloud） | Cloud 撤销按 token `nbf` 判定，**默认带 1 分钟缓冲** | 我们显式传 `revoke_token_ts=now`；自建只能靠短 TTL（3600→300 秒） |
| 交流页 `未连接` 且无提示 | `.env` 三项未填 / `LIVEKIT_MODE` 与实际不符 | 后端启动时已做必填与 `ws(s)://` 校验，看后端日志键名 |
| 麦克风/摄像头点不动 | 浏览器未授权设备或页面未聚焦 | 先点一次页面再授权；重连后设备状态会自动重放 |
| `db_init --reset` 后手工房间没了 | `--reset` 会清空重建 | 演示前跑一次即可，不要在演示中途跑 |
