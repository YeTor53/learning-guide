---
title: r011 变更登记 03：响应延迟收敛（一个此前没被发现的未完成项）
description: 你 2026-09-20「轮询时间是不是太长了，感觉响应很慢」的取证、实测数字、改动清单与前后对比。
type: reference
status: confirmed
owner: 陀梓皓
updated: 2026-09-20
---

<!-- overview -->
来源：你 2026-09-20 原话「**轮询时间是不是太长了，感觉响应很慢，找找可能的原因**」，并在看到清单后选 **③（基础设施 + 前端轮询一起改）**，同时定性为「**r011 的重定向，是未发现的未完成项**」——即它不是新功能，而是前面几轮留下的、此前没人发现的手感欠账。

## 1. 取证（改前实测）

| 面 | 事实 | 出处 |
| --- | --- | --- |
| 硬延迟（每次请求 +2 秒） | `http://localhost:8000/api/auth/me` 中位 **2070ms**（2070/2066）；`http://127.0.0.1:8000/api/auth/me` 中位 **6ms**（6/2/1/18）；`http://[::1]:8000/...` 直接拒连。原因：uvicorn 只绑 `127.0.0.1`（netstat 实测），Windows 上 `localhost` 先试 `::1` 被拒再回退 IPv4 | 本轮实测 |
| 双栈可行性 | 探针：uvicorn `--host ::` 时 `[::1]` 可连、`127.0.0.1` **拒连**（Windows 默认 `IPV6_V6ONLY=1`）→ **不能**改绑 `::`（会让 Vite 代理与全部脚本的 `127.0.0.1` 失效） | 本轮探针（端口 8123，用完即停） |
| 轮询兜底延迟 | 焦点申请列表 **8 秒**（`useFocusRequests.ts`）；房主端待批申请 **5 秒**（`RoomLivePage.tsx`）；等待室获批→进房 **5 + 1.5 秒**（`useWaitingRoom.ts` / `WaitingPage.tsx`）；名册兜底 **30 秒**（`useRosterSync.ts`）；转写芯片 **5 秒**（`useTranscription.ts`） | 代码常量 |
| 观感放大器 | `refetchOnWindowFocus: false`（切回窗口不刷新）；房间列表**完全无自动刷新**；`retry: 1`（失败再等约 1 秒） | `main.tsx`、`useRooms.ts` |
| 正常路径并不慢 | 动作→别端：`lg.roster` DataChannel 广播触发 invalidate（秒级）；请求经 Vite 代理中位 **3ms**（`localhost:5173/api/auth/me`） | `RoomLivePage.tsx:257-269`、本轮实测 |

## 2. 定性

**L0/L1 手感欠账**（不动接口、数据模型、权限语义）：属 r011 补正轮范围，按「未发现的未完成项」处理，不新开轮次。

## 3. 改动清单（cp-8）

| 文件 | 现在 → 改成 | 依据 |
| --- | --- | --- |
| `frontend/src/hooks/useFocusRequests.ts` | 兜底轮询 8s → **3s** | 降低协管申请的最坏可见延迟 |
| `frontend/src/pages/RoomLivePage.tsx` | 待批申请兜底轮询 5s → **3s** | 同上（正常路径仍走广播） |
| `frontend/src/hooks/useWaitingRoom.ts` | 等待室轮询 5s → **2s**（+ 1.5s 跳转 = 最坏 3.5s） | 获批→进房的等待感 |
| `frontend/src/hooks/useRosterSync.ts` | 名册兜底 30s → **10s** | 广播丢失时的自愈时间 |
| `frontend/src/main.tsx` | `refetchOnWindowFocus: false` → **true** | 切回窗口立即刷新 |
| `frontend/src/hooks/useRooms.ts` | 无刷新 → **5s 轮询** | 房间列表此前要手动刷才看到新房/已结束 |
| `README.md` / `AGENTS.md` / `dev.bat` | 加「地址口径」说明：后端一律 `127.0.0.1:8000`，前端一律 `localhost:5173`；dev.bat 启动后打印一行提示 | 杜绝 `localhost:8000` 的 2 秒陷阱 |
| `docs/rounds/r011-debt-backfill/manual-verification.md` | 新增 **MV-12**（响应速度核对） | 取证 |

## 4. 未做（如实）

- **不改 uvicorn 绑定**：探针已证明 Windows 上绑 `::` 会让 `127.0.0.1:8000` 失效（Vite 代理与全部脚本都依赖它），得不偿失；改为「文档与脚本统一 127.0.0.1」。
- **不引 SSE**：全服大屏聊天（r012）会做 `GET /api/events`；本轮只把轮询收敛到手感可接受，不新增通道。
- 转写芯片仍 5 秒轮询（worker 本身 5 秒上报，再缩短没有收益）。
