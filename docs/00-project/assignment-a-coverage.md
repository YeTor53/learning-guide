---
title: 面试作业「题目 A」覆盖情况（对照 G:\Downloads\设计-r003-api接入.docx）
description: 逐条核对作业必做/加分/交付物与仓库现状，附证据指路、缺口与建议下一步。
type: reference
status: proposed
owner: 陀梓皓
updated: 2026-09-19
---

<!-- overview -->
作业原文：`G:\Downloads\设计-r003-api接入.docx`（题目 A = Learning Guide 学习讨论室 / LiveKit Mini-Product；时限 4 天 ≈16 小时）。本页只做**对照与指路**，不改规范。

## 1. 结论（2026-09-19）

- **必做：15 / 15 条完成**（2026-09-19：**纪要链路与限时邀请均已落地并真机取证**）。
- **加分：0 / 5 条完成**（「断线重连后举手/焦点恢复」为**部分**：状态落库 + 重连/聚焦刷新 + 30 秒兜底已做，本地真断演练未做）。
- **交付物：3 / 4 项齐**；缺「使用的 AI 工具与模型列表」。
- 另有两处**文档漂移**需修：README 写「`pytest` 95 项 / `schema_migrations` 2 / 示例主题 3 个」，现为 **113 项 / 迁移 6 个 / 主题 14 个**。

## 2. 必做逐条

| 作业要求 | 状态 | 证据 |
| --- | --- | --- |
| 注册 / 登录 / 登出；未登录不可创建或加入房间 | **完成** | r001（`api/routers/auth.py`、`pages/{LoginPage,RegisterPage}.tsx`、未登录走 `require_login`）；登出在侧边栏个人信息浮窗 |
| 房间：创建（主题/标题/简介）、列表、详情、加入申请、批准/拒绝、离开、结束 | **完成** | r001/r002；`api/routers/rooms.py` 13 路由；`services/rooms.py`；`smoke` 40/40 |
| **邀请：限时邀请链接或房间码（需过期时间）** | **完成（r008，2026-09-19）** | `services/invites.py` + `POST/GET /rooms/{id}/invites` + `POST /invites/{code}/accept`；**有效期最长 1 分钟**（`INVITE_TTL_MAX_SECONDS` 单点可调）、6 位码、幂等、满员仍 409；前端抽屉「邀请」tab + `/join?code=`；真机两窗口验证通过 |
| LiveKit：加入 / 麦克风 / 摄像头 / 参与者视频 / 参与者列表 / 离开；服务端签发 Token；Secret 不入前端与仓库 | **完成** | r002；`services/livekit.py`（`issue_token`）；`.env` 未入库，前端只拿短期 token |
| 屏幕共享；共享时主区域，停止后恢复 | **完成** | r004；`stageLayout.ts` + ADR-0014（共享 > 手动焦点 > 说话者 > 自己） |
| 文字群聊：实时收发 + 持久化 + 按房间拉最近消息 | **完成** | r004；`chat_messages` 表 + `services/messages.py` + DataChannel `lg.chat` + HTTP 落库（唯一真相） |
| 举手：实时同步 + 列表展示 + 协管/房主可放下他人举手 | **完成** | r004；`services/hands.py`（`lower_hand` by other）+ 路由「房主/协管放下他人的举手」+ 抽屉可见 |
| 焦点发言：指定焦点、画面放大、取消恢复、**与共享并存的优先级规则** | **完成** | r004；`services/focus.py`、`FocusBadge`，ADR-0014 写明优先级并按规则实现 |
| 服务端管控：LiveKit Server API 真踢人（非前端假踢） | **完成** | r002；`livekit.remove_participant` + `services/rooms.kick_member` + `livekit_applied` 如实标记 |
| **会后产出：结束后自动/一键生成讨论纪要（LLM API）并落库、详情页可查看** | **完成（r008，2026-09-19）** | 迁移 `007_r008_session_summaries` + `services/summary.py`（唯一 LLM 出口，失败留痕）+ `POST/GET /rooms/{id}/summary` + 前端纪要页（`/rooms/{id}/summary`，已结束后卡片入口）；真机生成 **6.0 秒 / 632 字 / 不编造** |
| 数据层：可运行 Schema + 迁移/初始化；至少含 users / rooms / room_members / join_requests / chat_messages / **session_summaries** | **完成** | 六张必备表齐（+ `room_hand_raises` / `room_focus` / `invites`），迁移 **7 个** |
| 种子数据：一键演示账号 + 示例房间 + 历史消息 | **完成** | `002_seed.sql` + `db_init --reset --seed`（3 演示账号 / 3 房间 / 历史消息） |
| 基础自动化验证（≥1 API/集成测试或冒烟：创建用户→建房→签发 Token→写聊天→**生成纪要**） | **完成** | `pytest` **124 passed**；`smoke` **PASS 46/46**，新增「生成限时邀请码 / 凭码加入 / 生成讨论纪要（实测 559 字 → ready）/ 查看纪要」步骤 |
| 设计说明：架构 / 权限矩阵 / 表结构 / 两个自定义能力 / 等候室与踢人 / **纪要生成链路** / 失败与边界 / 安全 / 未完成项 | **完成** | 见下方「设计说明对照表」 |
| README：环境变量 / 安装 / 启动 / 两浏览器演示路径 | **完成** | README 已补「**两个浏览器演示完整路径（9 步）**」；数字漂移已修（迁移 7 / `pytest` 124）；`.env.example` 增 `INVITE_TTL_MAX_SECONDS` |

## 3. 加分项

| 加分项 | 状态 | 说明 |
| --- | --- | --- |
| 断线重连后举手/焦点状态恢复 | **部分** | 状态在库 + DataChannel 名册广播 + 重连/聚焦刷新 + 30 秒兜底（r006 cp-2）；E18b（本地 livekit-server 停 8 秒真断）未做 |
| 房间录制 / 旁路录音转写后生成纪要 | **未做** | —— |
| Docker Compose 一键启动或公网部署 | **未做** | 现为本机 `dev.bat`（起 8000 + 5173） |
| 简单管理后台（房间/用户/纪要） | **未做** | —— |
| 演示录屏 3–5 分钟 | **未做** | 需人录 |

## 4. 交付物

| 交付物 | 状态 |
| --- | --- |
| 源代码 / Git 仓库链接 | **齐**（本仓；`dev.bat` 一键起） |
| 设计说明 + README + 环境变量示例（无真实密钥） | **齐**（`.env.example` 无真实值；`.env` 未入库） |
| 测试或冒烟脚本运行说明 | **齐**（README §⑤ 验证 + `backend/scripts/smoke.py`） |
| 使用的 AI 工具与模型列表 | **缺**（提交时需列：Claude Code / Codex / Cursor 等 + 模型） |

## 5. 建议下一步（排序建议）

| 优先级 | 内容 | 为什么 |
| --- | --- | --- |
| P0 | **LLM 纪要链路**：迁移建 `session_summaries` → `services/summary.py`（输入聊天记录 + 参与者 + 主题，调 OpenAI 兼容接口）→ 路由（结束房间自动 / 手动一键）→ 前端房间详情（结束后可查看）→ 冒烟补「生成纪要」一步 → 设计说明补「纪要生成链路」 | **必做**，且是唯一需要新外部依赖的必做项；也决定「失败与边界/未完成项」怎么写 |
| P0 | **限时邀请**：`invites` 表已就绪 → 生成/校验路由（`expires_at` 过期、`max_uses` 用尽）→ 前端「复制邀请链接」与 `/join?code=` 入口 → 用例（过期 / 用尽 / 无效码） | **必做**，表已建好，工作量可控 |
| P1 | README 两处漂移（`pytest` 113、迁移 6、主题 14）+ 「两浏览器演示路径」单列一节 | 评审复现用 |
| P1 | 「使用的 AI 工具与模型列表」文件（`docs/00-project/ai-tools-and-models.md`） | 交付物 |
| P2 | 加分：Docker Compose 一键启动（成本中等、评审观感好） | 加分 |
| P2 | 你提的焦点/举手/均分布局/麦克风悬浮键改造（r008 候选，见 `docs/rounds/r008-*/`） | 体验增强，非作业必做 |

## 6. 变更记录

| 日期 | 版本 | 改了什么 | 依据 |
| --- | --- | --- | --- |
| 2026-09-19 | v1 | 建页：按作业原文逐条核对必做/加分/交付物，标注缺口与建议排序 | 你要求「看一遍 docx 确认题目一完成度」 |

## 5. 设计说明对照表（作业要求 ↔ 本仓文档）

| 作业要求的章节 | 本仓对应文档 |
| --- | --- |
| 架构 | `docs/01-architecture/r001-app-architecture.md`（分层、路由、错误信封、安全边界） |
| 权限矩阵 | `docs/02-modules/r002-livekit-features.md` + `docs/rounds/r004-room-extras/design.md`（三角色 × 动作） |
| 表结构 | `docs/02-modules/r001-rooms.md`（DDL）+ 各轮实现页（004/005/006/007） |
| LiveKit 与两个自定义能力（举手 / 焦点） | `docs/02-modules/r002-livekit.md`、`docs/02-modules/r004-room-extras.md`、ADR-0014（焦点与共享优先级） |
| 等候室与踢人流程 | `docs/02-modules/r002-livekit-features.md`（F-17 等候室）、ADR-0011（Token 无状态 / 外部调用在提交后 / 唯一出口） |
| 纪要生成链路 | `docs/02-modules/r008-assignment-gaps.md` §1、ADR-0018、`docs/rounds/r008-assignment-gaps/design.md` §2.5 |
| 失败与边界情况 | 各轮 design 的「失败与边界」表（r008 §4）+ review 的「未闭合项」 |
| 安全 | `docs/01-architecture/r001-app-architecture.md` §5/§13（密钥只在本机 `.env`、Secret 不进前端、错误不回显内部细节） |
| 未完成项 | 各轮 review「未闭合项」+ 本页 §7 |

## 6. 交付物

| 交付物 | 状态 |
| --- | --- |
| 源代码 / Git 仓库链接 | 齐 |
| 设计说明 + README + 环境变量示例（无真实密钥） | 齐（`.env` 未入库；`.env.example` 仅键名） |
| 测试或冒烟脚本运行说明 | 齐（README §⑤ + smoke 46 步） |
| **使用的 AI 工具与模型列表** | **待你填**：模板已建 `docs/00-project/ai-tools-and-models.md` |

## 7. 加分项现状

| 加分项 | 状态 |
| --- | --- |
| 断线重连后举手/焦点状态恢复 | **部分**（状态落库 + 广播 + 聚焦刷新 + 30 秒兜底；本地真断演练未做） |
| 房间录制 / 旁路录音转写后生成纪要 | **规划中**：整体作为 r009（默认开启 + 并入文字对话 + 含管理信息 + 先出 STT 获取方案） |
| Docker Compose 一键启动 / 公网部署 | 未做 |
| 简单管理后台 | 未做 |
| 演示录屏 3–5 分钟 | 未做（需人录） |
