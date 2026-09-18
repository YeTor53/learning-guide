---
title: r002 总设计增量（实时链路 · LiveKit 接入）
description: r002（M2）在 r001 总设计之上新增的运行时拓扑、实时链路时序、配置与错误码增量、验证矩阵增量与环境准备。
type: reference
status: draft
owner: 陀梓皓
updated: 2026-09-18
---

<!-- overview -->
本页只写 r002（M2）**相对 r001 的架构增量**：运行时拓扑新增的一段、实时链路时序、配置与验证矩阵增量、要你手工做的两件事。
r001 已批准的总设计（分层与依赖规则、目录树、数据层机制、会话与鉴权、接口信封、错误码基线、环境准备）见 `docs/01-architecture/r001-app-architecture.md`，**本页不复制其内容**，冲突时以本页为准并回填 r001 页「变更记录」。
本轮范围见需求单 `docs/00-requirements/r002-livekit-room.md`；模块级函数签名见 `docs/02-modules/r002-livekit.md`。

## 1. 运行时拓扑（r002 新增的一段）

```
浏览器 A（React SPA）
  │  /api/*            ── Vite dev proxy / 演示形态同源
  ▼
FastAPI（uvicorn :8000）
  │  api → services(rooms, livekit) → repositories → psycopg 池 ──> PostgreSQL（本机 :5432）
  │                                                       services/livekit.py 是唯一出口 ↓
  │  ① 签 JWT（本地，不联网）                    ② Room Service（联网）：
  ▼                                               RemoveParticipant / DeleteRoom / ListParticipants
返回 Token 给浏览器
  ▼
浏览器 ── WebRTC（wss / UDP）──> LiveKit Cloud（Build 免费；区域可钉亚太）
        ← 音视频、屏幕共享（M3）、数据通道（M3）
```

要点：

1. **音视频不经我们的后端**：媒体流在浏览器与 LiveKit Cloud 之间直连（SFU），后端只负责「签发准入凭证」与「管控动作」。
2. **Key/Secret 只在后端**：`AccessToken` 由 `services/livekit.py` 用服务端密钥本地签名；前端只拿到 Token + `wss://` 地址（AGENTS 禁区，验收有检索命令）。
3. **可降级**：同一条链路（同一套 SDK 与 API）把 `LIVEKIT_URL/KEY/SECRET` 换成自建 `livekit-server`（`ws://127.0.0.1:7880`、`LIVEKIT_MODE=self`）即成离线形态，代价是踢人只能靠短 TTL（ADR-0001/0003）。
4. 新增一段「外部依赖」：Cloud 不可达时**房间的业务功能（列表/详情/申请/批准/离开/结束）照常可用**，只有「进房与踢人」不可用（失败面隔离，见 §7）。

## 2. 实时链路时序（三条主链）

进房（申请 → 获批 → 连上）

```
B: POST /api/rooms/{id}/join-requests          201 申请 pending
A: POST /api/join-requests/{rid}/approve       200 成员 active（r001 已有；容量在此拦截）
B: GET  /api/rooms/{id}                        200 出现「进入房间」（我是活跃成员）
B: POST /api/rooms/{id}/token                  200 {token, url, role, ttlSeconds}   ← service 内校验成员+房间 active
B: new Room().connect(url, token)              LiveKit 侧建立连接（max_participants 兜底）
B: 前端按 identity 与库成员求交                侧栏「在线」标记；其余成员灰显
```

踢人（承诺：库先落地，再去断线；断线失败不回滚）

```
A: POST /api/rooms/{id}/members/{uid}/kick
   └─ with conn.transaction(): lock_room → 权限/状态校验 → deactivate_member('kicked')
   └─ 事务提交（此时库真相已确定：该成员 inactive/kicked）
   └─ livekit.remove_participant(room, uid, revoke_token_ts=now)   ← Cloud：旧 Token 立即失效
   └─ 200 {livekitApplied: true|false}
被踢者：LiveKit 断开 → 前端 Disconnected(reason=PARTICIPANT_REMOVED) → 「你已被移出房间」（原因取 SDK，取 Token 兜底）
```

结束房间（r001 的三件事 + 本轮新增的第四件）

```
A: POST /api/rooms/{id}/end
   └─ 事务：rooms.ended + 成员 inactive/room_ended + pending 申请 cancelled（r001，不变）
   └─ 事务提交后：livekit.delete_room(room)   ← 强制断开全部连接（失败只记日志）
所有人：Disconnected(reason=ROOM_DELETED) → 「房间已结束」（原因取 SDK，取 Token 兜底）
```

重连（网络抖动 / 短时断网；`redirect-01` 承诺）

```
客户端：网络中断
  ├─ 抖动轻微 → SDK 静默做 ICE restart（通常几乎无感，界面不打断）
  └─ 需要全量重连 → 事件序列：
       Reconnecting（房内页显示「正在重连…」，不退出页面）
       → 对其他成员表现为该成员「离开又回来」（ParticipantDisconnected → ParticipantConnected）
       → 本地已发布的轨道被重新发布（LocalTrackPublished）
       → Reconnected（界面回到「已连接」，重新发布/恢复设备状态）
  └─ 重连彻底失败 → Disconnected(reason) → 按上面「踢人/结束」同一套归因出提示
库侧：**全程不变**（不写 room_members、不产生 inactive；成员身份始终以库为准）
```

## 3. 配置增量（`.env`）

| 键 | r001 状态 | r002 要求 | 说明 |
| --- | --- | --- | --- |
| `LIVEKIT_URL` / `LIVEKIT_API_KEY` / `LIVEKIT_API_SECRET` | 允许为空 | **必填**，缺一启动即 `CONFIG_MISSING`（只报键名） | Cloud 项目值；`API_SECRET` 仅服务端进程可见 |
| `LIVEKIT_MODE` | 占位 `cloud` | `cloud` / `self` 二选一 | 决定 `revoke_token_ts` 与 Token TTL（`cloud` 3600s / `self` 300s） |
| `ROOM_CAPACITY` | 已有（默认 8，≤8） | 不变 | 演示满员可用 2~3 人的房间；Token 内 `max_participants` 取同一值 |

- 推理型配置不新增环境变量：`livekit_token_ttl_seconds`、`livekit_timeout_seconds` 由 `LIVEKIT_MODE` 在 `config.py` 内推出（改口径只改一处）。
- 校验规则与实现位置见 `docs/02-modules/r002-livekit.md` §6.1。

## 4. 分层与依赖方向（r002 增量）

| 规则 | 内容 |
| --- | --- |
| 唯一出口 | 只有 `app/services/livekit.py` 可 import `livekit` 包、可读 `LIVEKIT_*`；其余模块一律不许（`api` 层更不许） |
| 依赖方向 | `services/rooms.py → services/livekit.py`、`services/* → repositories/*`；**禁止** `livekit.py → repositories`（它只收参数、不查库、不判权限） |
| 外部调用时机 | 一律在**事务提交之后**（架构页 §10 的既有约定）；外部失败不回滚业务状态、不改响应语义（只在响应里如实带 `livekitApplied`） |
| 同步边界 | 后端是同步 `def` 路由；`livekit-api` 的 async 调用收敛在 `services/livekit.py` 的 `_run()` 一处，带超时 |
| 数据归属 | 「谁有资格进房」由 PostgreSQL 决定；「此刻谁连着」由 LiveKit 决定，两者不互相写入（实现页 §2） |

> 本节与 §2 的约定已固定为 ADR：`docs/03-decisions/r002-adr-0011-realtime-presence-model.md`（9 条：双事实源、identity 唯一、Token 无状态、外部调用在提交后、断线归因、重连分层、唯一出口、上限口径）。

## 5. 接口与错误码增量

- 新增 4 条路由（清单见 `docs/02-modules/r002-livekit.md` §5），全部沿用 `{ok, data}` / `{ok:false, error:{code, message}}` 信封。
- **不新增错误码**：复用 `UNAUTHORIZED` / `FORBIDDEN` / `NOT_MEMBER` / `ROOM_ENDED` / `ROOM_FULL` / `VALIDATION` / `CONFIG_MISSING`。理由：LiveKit 侧的失败不改变 HTTP 语义（库已按真相落地），以响应字段 `livekitApplied` + 前端文案表达「已移出但实时断开可能延迟」。
- 前端错误分流沿用 r001 口径（ADR-0009）：401 → 去登录并回跳；409 业务码 → 用服务端 message；网络/5xx → 「服务暂时不可用」+ 重试。

## 6. 验证矩阵增量（叠加到 r001 §11）

| 层 | 命令 / 动作 | 判据 |
| --- | --- | --- |
| Token 契约 | `pytest backend/tests/test_livekit_token.py -q` | JWT 解码后 grants/room/max_participants/TTL 全部符合；不需要网络 |
| 权限与外部失败 | `pytest backend/tests/test_rooms_members_api.py -q` | 非成员 403、已结束 409、协管互踢 403、踢房主 403、踢自己 400；外部调用打桩：成功/异常两条路径都不改变已经落地的库状态 |
| 冒烟 | `python backend/scripts/smoke.py` | 追加「取 Token 200 → 非成员 403 → 踢人后 403 → 结束后 409」四步，末尾 `PASS n/n` |
| 密钥 | `git grep -nE "API_SECRET|API_KEY" -- backend/app frontend/src`；构建后 `git grep` 或检索 `frontend/dist` | 除 `config.py` 变量名外无命中；前端产物内无 Secret |
| 实时（人工） | 双浏览器 + 可选手机扫 Cloud 链接 | 功能页 §6 的 11 步全部可复现，含满员拒绝、踢人真断开、结束房间广播断开 |
| 断网重连（人工） | 双浏览器进房后，一端断网 5~10 秒再恢复 | 自动回到房间（无需点按钮）、声画恢复；期间「正在重连…」可见；库侧 `room_members` 无新记录；关摄像头者回来仍关闭 |
| 降级（人工/排障） | 把 `LIVEKIT_*` 指向自建 `livekit-server --dev` | 进房/踢人可用（区别：踢人靠短 TTL，旧 Token 在 TTL 内可重入——如实写进设计说明） |

## 7. 失败与边界（架构级）

| 情形 | 表现 | 依据 |
| --- | --- | --- |
| Cloud 不可达（进房） | 房内页错误卡片 + 重试；房间列表/详情/申请/批准/离开/结束不受影响 | 失败面隔离（§1 第 4 条） |
| Cloud 不可达（踢人/删房） | 库按真相落地；响应 `livekitApplied=false`；日志留证；前端提示「实时断开可能延迟」 | 「外部调用在提交后」约定 |
| 启动期缺 `LIVEKIT_*` | 进程启动失败，报错只报键名 | 不允许默认密钥兜底（r001 §5 规则） |
| 额度用尽（Build 免费） | 连接被拒，前端显示通用实时错误；超额是**失败而非计费** | ADR-0003 |
| 局域网/真设备演示 | 浏览器只在 `https` 或 `localhost` 允许采集；Cloud 自带 TLS，手机扫链接即可进 | ADR-0003 |
| 演示形态 Cookie | `APP_ENV=demo` 时 Cookie 带 `Secure`，脚本客户端不回传（坑已记 r001）；实时演示建议 dev 形态或 `localhost` | r001 实测 |
| 重复身份（同账号在第二个窗口进入同一房间） | 后进连接把先进连接踢掉（`DisconnectReason.DUPLICATE_IDENTITY`），先进窗口显示「同一账号已在别处进入本房间」；不做真双开 | 官方 SDK 行为（`redirect-01` C-2 修正 r002 原 FQ-8 口径） |
| 异常退出（未调 `disconnect()`） | LiveKit 侧该参与者在约 15 秒后消失；库侧仍算成员（离线显示），房主可移出清位 | 官方文档；与本页 §4「外部调用在提交后」同一套哲学：库是身份事实源 |

## 8. 环境准备与人工步骤（需你操作）

| 步骤 | 动作 | 负责人 |
| --- | --- | --- |
| 装后端依赖 | 在 conda 环境 `learningguide` 下 `pip install livekit-api`（走已配镜像源） | **需你批准**（AGENTS 禁区：不擅自增删依赖） |
| 装前端依赖 | `cd frontend && npm install livekit-client @livekit/components-react`（npmmirror） | **需你批准** |
| 建 Cloud 项目 | `cloud.livekit.io` 注册 → 新建项目（Build 免费）→ 抄下 `wss://<子域>.livekit.cloud` 与 API Key/Secret | **你操作**（约 5 分钟） |
| 填 `.env` | 把三项写进仓库根 `.env`（`LIVEKIT_MODE=cloud`） | **你操作**（agent 不接触明文，不回显、不入库） |
| 自建降级（可选，演示前备用） | 下载 `livekit_1.13.7_windows_amd64.zip` 解压 → `livekit-server --dev` → `.env` 指向 `ws://127.0.0.1:7880`、`LIVEKIT_MODE=self` | 届时由 agent 给命令，你点运行 |

## 9. 与 r001 架构页的关系

- r001 页继续作为**基线与长期机制**的事实源（分层、数据层、会话、信封、错误码基线、PostgreSQL 环境）。
- 本页是**本轮增量**：新增一段拓扑、三条时序、配置必填项、外部调用纪律、验证矩阵追加。
- 两份都不重复描述同一件事；出现冲突时以本页为准，并在 r001 页「变更记录」留一行指针（本轮收官时执行）。

## 10. 变更记录

- 2026-09-18 建立（`status: draft`）。
- 2026-09-18 按 `redirect-01`（用户批复「设计进行」）增补：§2 新增「重连」时序一段；踢人/结束两条链路的断线归因改为 **SDK `DisconnectReason` 优先、取 Token 兜底**；§6 验证矩阵加「断网重连（人工）」；§7 加「重复身份」与「异常退出 15 秒」两行。

## What's next

1. 用户复核本页（重点：§1 拓扑、§2 三条时序、§3 配置必填、§4 唯一出口与外部调用时机、§6 验证矩阵、§8 需你操作的两项）。
2. 通过后按需求单 §10 的 cp 表推进；实现期若发现与本页不符，走设计变更闸门（CR）而不是就地改。
