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
