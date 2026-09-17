---
title: r001-ADR-0003 LiveKit 来源复评（Cloud 托管 vs 本机自建）
description: 把 LiveKit Cloud 的事实与自建逐项对比，作为 P3′ 的拍板依据；本文不改动 ADR-0001 的既定决定。
type: adr
status: proposed
owner: 陀梓皓
updated: 2026-09-16
---

<!-- overview -->
用户在决定自建（ADR-0001）之后要求了解 LiveKit Cloud，故做一次来源复评。本文只提供事实、对比与建议，**待用户拍板**；未拍板前 ADR-0001（自建）仍然有效。

## 事实（2026-09-16 实测，取自 LiveKit 官方文档与定价页，链接见文末权威源）

**LiveKit Cloud 是什么**
- 托管版 LiveKit：开源的 WebRTC SFU（`livekit-server`）由官方托管，叠加托管 Agent 部署、内置模型推理、电话（SIP/号码）、可观测性与仪表盘。
- 项目形态：控制台 `cloud.livekit.io` 建项目 → 得到项目 URL（`wss://<子域>.livekit.cloud`）+ API Key/Secret 一对；可用 `lk` CLI 管理。
- 区域：亚太组为日本、新加坡两处；支持区域端点（如 `<子域>.japan.rtc.livekit.cloud`）把流量钉到指定区域。

**免费 Build 计划（$0/月，无需信用卡）**
| 项 | 额度 |
| --- | --- |
| WebRTC 分钟 | 5,000 分钟/月 |
| 并发连接 | 100 |
| 下行流量 | 50 GB |
| 超额行为 | 免费项目的额度是**硬上限**：用尽后新请求失败，不产生费用 |

**自建（本机）**
- 开发模式一条命令：`livekit-server --dev`（内置 devkey/secret，默认绑 `127.0.0.1:7880`；对外需 `--bind 0.0.0.0`）。
- 生产自建需自行配 SSL、负载均衡、TURN；Egress/Ingress/SIP 是独立服务，需单独部署。

**鉴权与管控（两种来源共用的应用层 API）**
- 客户端凭 Access Token 连接，Token 是 JWT，用 API Secret 签名，内含参与者 identity、房间名、TTL 与 grants（`roomJoin`、`canPublish`、`canPublishData`、`canPublishSources` 等）。
- Python 服务端：`livekit-api` 包，`api.AccessToken(...).with_identity(...).with_grants(api.VideoGrants(...)).to_jwt()`；房间/参与者管控走 `api.LiveKitAPI`。
- **房间人数上限**可写进 Token 的 `RoomConfiguration.max_participants` → 由 LiveKit 侧硬限，正好给题面「单房间 8 人」做兜底。
- **踢人/撤销**：`RemoveParticipant`，可带 `revoke_token_ts` 拒绝其重入。

**关键差异（直接影响我们的踢人设计）**
| | Cloud | 自建 |
| --- | --- | --- |
| 移除参与者/改权限后，已签发的 Token | 立即失效（可拒绝重入） | **不会失效**，需靠短 TTL 兜底 |
| 无需注册账号即可演示 | ✗（需项目 + Key/Secret） | ✓ |
| 依赖外部服务可达性 | ✓ 依赖 | ✗ 不依赖 |
| 评审复现成本 | 低（评审自己有网即可） | 需本机起服务（已随仓库给命令） |

## 选项与建议

| 选项 | 内容 | 建议 |
| --- | --- | --- |
| P3′-A | 改用 LiveKit Cloud（Build 免费） | **建议**：额度过剩（双浏览器演示按参与者分钟计），运营成本为零；踢人能真正"失效 Token"，更贴题面「移除 Token 权限并强制断开」；区域可选亚太。 |
| P3′-B | 维持自建（ADR-0001） | 零外部依赖、演示不依赖网络；代价是踢人只能"断开 + 短 TTL"，且需自管进程与端口。 |
| P3′-C | Cloud 为主 + 自建脚本留档 | 交付里给一条本地自建命令作降级方案；多出一点文档与配置成本。 |

## 讨论（2026-09-16，pin 在三个真实分叉点上）

### 1. P3 实际在决定什么

不是"云还是本地"这种表面问题，只有三件事真正被它决定：

1. **演示形态的上限**：只能本机开几个浏览器，还是能让手机/另一台电脑真加入。
2. **「踢人」的证据质量**：能不能让一个已签发的 Token 立即失效、拒绝重入。
3. **失败面与复现成本**：演示当天依赖外网与账号，还是依赖本机进程。

### 2. 决定取舍的事实（实测）

- **Token 可撤销性（差异最大的一条）**：Cloud 上 `RemoveParticipant`（可带 `revoke_token_ts`）能让已签发 Token 立即失效并拒绝重入；自建下移除参与者或改权限**不会**让已签发 Token 失效，只能靠短 TTL 兜底 + 拒绝再签发。
- **真设备演示（隐藏门槛）**：浏览器只在 `https` 或 `localhost` 下允许采集麦克风/摄像头/屏幕。自建默认 `127.0.0.1:7880`（`--bind 0.0.0.0` 才能被局域网访问），要让手机/别的电脑加入就得额外给自建服务配 TLS（自签/mkcert/HTTPS 代理）；Cloud 自带 TLS，给个链接对方就能进。
- **自建要开的端口**：`7880`(TCP, API/WebSocket)、`7881`(TCP, ICE/TCP 兜底)、`7882`(UDP, ICE mux；或改用 `50000-60000` 端口段)；TURN `5349/3478` 可选。Windows 首次运行会有防火墙授权弹窗。
- **Webhook 回调方向相反**：`room_started / room_finished / participant_joined / participant_left` 等事件两种来源都有；Cloud 由云端 POST 到你填的 URL（本地开发需要一个公网可达地址/隧道），自建可直接回调本机服务。
- **LiveKit 房间的空置超时与应用层房间是两回事**：LiveKit 房间可在最后一个参与者离开若干时间后自动关闭（`room_finished`），但那只是"有没有人在房里"；我们应用层的 `rooms.status`（`active/ended`）仍由 Host 显式结束决定，两者不要混为一谈（对应派生相位 `active.idle` / `active.in_session`）。
- **切换成本≈0（重要）**：两者的 Token 签发与管控 API 是同一套（Python `livekit-api`：`AccessToken` / `LiveKitAPI`），差别只在 `LIVEKIT_URL / API_KEY / API_SECRET` 三个环境变量与"谁起进程"。所以 P3 不是一次性赌注，可以「主 + 备」。

### 3. 三种形态的代价

| 形态 | 演示形态上限 | 踢人证据 | 失败面 | 额外工夫 |
| --- | --- | --- | --- | --- |
| A Cloud 单跑 | 本机 + 真设备（给链接即可） | Token 立即失效（最强） | 依赖外网可达 + 需注册账号 | 注册约 5 分钟；无本机进程 |
| B 自建单跑 | 本机多浏览器；真设备需额外配 TLS | 断开 + 短 TTL（说法弱一档） | 零外网依赖；依赖本机进程与端口 | 首轮实测必须做（Windows 原生二进制未曾实跑）+ 进程管理脚本 |
| C Cloud 主 + 自建留档（建议） | 同 A | 同 A | 外网不通时可切 `localhost` 降级 | 多一份启动脚本与一段降级说明（成本很小） |

### 4. 倾向与理由

倾向 **C（Cloud 为主 + 自建脚本留档）**：

1. 同一套 SDK，切换只是三个环境变量，成本近零，但把"演示当天网络/账号出问题"这个最大单点风险对冲掉。
2. 题面那句「移除参与者 Token 权限并强制断开（不可只做前端假踢）」在 Cloud 上能做到"Token 真失效"，面试追问实现与边界时最好解释。
3. 免费额度（5,000 WebRTC 分钟/100 并发）远超作业需要；超额是失败而非计费。
4. 真设备入镜（手机扫码进房）对"多人讨论室"演示的说服力明显强于三个浏览器标签页。

若更看重"零外部依赖、完全自己掌控"，**B 也完全站得住**，代价是踢人只能讲"断开 + 短 TTL"，真设备演示要额外配 TLS。

### 5. 需要用户确认的前提（决定取舍）

1. 演示形态：只在本机开几个浏览器就够，还是要手机/另一台设备真加入？
2. 能否接受演示环节依赖外网 + 注册一个 LiveKit Cloud 账号（免费、无需信用卡）？
3. 有没有"必须完全离线可演示"的硬要求（例如现场无网或不希望注册/登录外部平台）？

## 影响

- 选 A 时：`.env` 的 `LIVEKIT_URL/API_KEY/API_SECRET` 改为 Cloud 项目值；设计说明里写清"为何用托管"与免费额度边界（超额失败而非计费）。
- 选 B 时：维持 ADR-0001，另在设计说明写"自建下 Token 无法撤销，靠短 TTL + 拒绝签发新 Token"。
- 无论哪种，**Key/Secret 只进本地 `.env`**，不入库、不进前端，验收时用检索命令取证。

## 权威源

- LiveKit Cloud 介绍与自建对比：`https://docs.livekit.io/intro/cloud.md`
- 配额与限制：`https://docs.livekit.io/deploy/admin/quotas-and-limits.md`
- 定价与计划矩阵：`https://livekit.com/pricing.md`
- 访问令牌与 grants：`https://docs.livekit.io/frontends/authentication/tokens.md`
- 本地自建：`https://docs.livekit.io/transport/self-hosting/local.md`
- 区域与端点：`https://docs.livekit.io/deploy/admin/regions/endpoints.md`

## 变更记录

- 2026-09-16 建立（proposed，待拍板）。
