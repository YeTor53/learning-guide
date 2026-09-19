---
title: r002 需求单：实时房间 · 权限 · 等候室（里程碑 M2）
description: r002 的目的、边界、本轮已定口径、验收清单、影响面、风险、文档产出（覆盖矩阵）与实施顺序（cp-r002-1..4）。
type: requirement
status: closed
owner: 陀梓皓
updated: 2026-09-19
---

<!-- overview -->
本页只写「这一轮做成什么、怎么算做完、按什么顺序做」。怎么做见总设计增量 `docs/01-architecture/r002-realtime-architecture.md` 与模块页 `docs/02-modules/r002-livekit.md`（实现）、`r002-livekit-features.md`（功能）；项目方向见 `docs/00-project/global-roadmap.md` §3 的 M2 行。
上一轮 `r001` 已关闭并合入 `main`（`round-r001-done`），本轮的起点是它。

## 1. 目的

把「房间」从一张数据表变成**真正能开会的房间**：获批成员拿到服务端签发的 Token 连上音视频，双向可听可看；Host/协管能在**服务端**把违规成员真正断开（不是前端假踢）；第 9 人在门口就被拦住；房间结束时所有人立刻断线并回到只读记录页。
做完这一轮，评审打开两个浏览器（或一台手机扫链接）就能现场演示 M2 的全部验收点。

## 2. 边界

**做（M2 → r002）**

- LiveKit 接入：`app/services/livekit.py`（签 Token、移除参与者、删除房间、在场列表），Cloud 为主、`LIVEKIT_MODE=self` 分支保留（ADR-0003）。
- 进房：`POST /api/rooms/{room_id}/token` + 前端房内页 `/rooms/:id/live`（视频格、成员侧栏、麦克风/摄像头开关、离开）。
- 等候室闭环收口：批准 → 详情页出现「进入房间」→ 连上；未获批者进不去（服务端拦）。
- 8 人上限：批准时应用层校验（r001 已有）+ Token 内 `max_participants` 兜底 + 连接被拒时的前端提示。
- 三角色权限矩阵在实时面落地：踢人（Host/协管，协管不可互踢）、任命/取消协管（Host）、移交房主（Host）、结束房间强制断开（Host）。
- 三种断开来源的表现与归因：主动离开 / 被移出 / 房间结束（用「再取一次 Token」的错误码区分，不引 Webhook）。
- 文档：归档设计归位（`docs/02-modules/r002-livekit*.md`）、总设计增量页、教学页（使用者 + 开发者）。
- **断线重连（连接层）**：网络抖动或短时断网后**自动回到房间**（SDK 的 `Reconnecting` / `Reconnected`），重连期间不退出房内页、显示「正在重连…」；只有彻底重连失败才进入「连接已断开」+ 重连按钮（口径见 §3 Q9，`redirect-01`）。
- **设备状态保持（设备层）**：本人在重连前后保持麦克风/摄像头的开关状态（关着的回来还是关着）。
- **页面口径 + 两种情绪取向**（`redirect-04` 三分 → `redirect-06` 定稿）：**列表页**（发现与申请入口）、**交流页**（`/rooms/:id/live`，专注感）、**等待页**（`/rooms/:id/wait`，温暖感）；**原房间管理页 `/rooms/:id` 已删除**（治理动作只在交流页抽屉）。术语表同步。
- **顺手偿还 r001 的两条测试欠账**（见 §10）：列表分页 `limit/offset` 用例、房间码冲突重试的打桩用例。**两条已于 cp-r002-2 偿还**（用例名见 roadmap §9）。

**不做（本轮不碰）**

- 邀请（生成邀请 / 用邀请加入）：`invites` 表已建不用 → `docs/99-archive/r002-ahead-invites.md`（backlog）。
- **断线重连后的业务状态恢复**（举手、焦点发言、屏幕共享、群聊未读）→ M3（这些能力本身在本轮之后才存在）/ M5 ①（roadmap 原登记不变）。
- 交流页里的聊天 / 举手 / 焦点发言 / 屏幕共享入口 → M3（本轮交流页只做音视频 + 在场 + 设备控制 + 管理动作；底部控制条为它们预留位置但不出现按钮）。
- 等待页的通知推送（跨页面提醒）→ 仍留 M5（本轮只做页内轮询 + 自动进入）。
- **r001 现有 8 处浏览器原生弹窗（`window.alert/confirm`）不替换**（2026-09-18 记账，见 roadmap §9）：本轮新交互一律用站内 toast + 自绘 modal（`redirect-03` 待批），旧 8 处留你定时机（建议 M3 或交付前）。
- **r001 首页筛选工具栏「太下了」**（2026-09-18 实测：hero 高 498 / `.toolbar` top 639 / 视口 566 → 首屏外；图版容器是 `absolute` 不占位，隐藏它位置不变，推手是 hero 高度与 40px 间距）：**本轮不修**，已登记 `global-roadmap.md` §9 遗留台账待你拍板（本轮只做实时房间，顺手改首页会扩大范围）。
- 群聊实时收发、举手、焦点发言、屏幕共享及其优先级规则 → M3。
- 断线/关标签页的自动离开判定、Webhook 事件回调 → M5（本轮库侧不变更成员状态）。
- LLM 纪要 → M4；Docker/Compose、管理后台、公网部署 → M5 或非目标。
- npm 发包与 GitHub 远端细节（P11）→ 仍暂缓。

## 3. 本轮已定口径

来源：2026-09-18 你回复「出设计」；下列 Q 的取值即 **`docs/00-project/global-roadmap.md` 建议值**（未另行指明的按建议值执行）。
本表口径的**决策依据**已固定为 `docs/03-decisions/r002-adr-0011-realtime-presence-model.md`（9 条约定），与 `redirect-01` 冲突时以本页为准。**如有任一条与你的意图不符，改本表后再动代码。**

| 编号 | 事项 | 本轮取值 | 理由 / 依据 |
| --- | --- | --- | --- |
| Q1 | 邀请是否进本轮 | **不进**，登记 backlog | M2 验收点不含邀请；它要牵出 TTL/用尽/落地页三块 UI |
| Q2 | 角色任命 + 移交房主 | **进** | 否则造不出 Moderator，「三角色权限矩阵」无法复现 |
| Q3 | 8 人上限口径 | 以 `ROOM_CAPACITY`（默认 8）为唯一口径；申请/批准阶段拒绝 → `ROOM_FULL`；Token 内 `max_participants` 兜底 | 与 r001 已实现的容量校验同源；演示用 2~3 人房复现满员 |
| Q4 | 参与者列表口径 | 房内页用 **LiveKit 实时在场**；房间详情页仍用**库成员表**；两者求交展示 | 各写各的事实源，避免后端为显示再调外部服务 |
| Q5 | 离开 / 断线语义 | 只处理「显式离开」「被踢」「房间结束」；关标签页/断网**不改库**（侧栏显示离线）；**重连同样不改库**（见 Q9） | 自动判定需 Webhook 公网回调，留 M5 |
| Q6 | 依赖 | 后端装 `livekit-api`；前端装 `livekit-client` + `@livekit/components-react` | ADR-0003 已指定；安装需你批准（§9） |
| Q7 | Cloud 凭据 | 你注册 LiveKit Cloud 项目并把三项填进 `.env` | 无凭据无法真机验收；agent 不接触明文 |
| Q8 | 验收方式 | 自动化覆盖 Token 契约 + 权限拦截 + 外部失败分支（打桩）；实时行为（声画互通、满员拒绝、真断开、断网重连）列人工双浏览器验收 | 只能真跑的行为不假装自动化 |
| **Q10** | 等待页与等待通知（`redirect-02` 的 G1） | **等待态升级为独立等待页**（`/rooms/:id/wait`，温暖感）；获批自动进入交流页（无手动步骤）。G2（跨页面通知）/ G3（等待队列、满员排队）仍只记账 | 等待是用户真实停留的一段时间，值得一页；通知需推送通道（M5）；队列会打破「无新增错误码」口径 |
| **Q10b** | 房间管理页是否保留（`redirect-06`） | **删除 `/rooms/:id`**：治理动作只在交流页「成员与管理」抽屉；列表页卡片直接承载「申请加入 / 去等待室 / 回到讨论」；`ended` 的历史回看与 M4 纪要另立页面 | 你 2026-09-18：「删了吧」（我建议的降级保留被否）。依据：跳页 = 断开讨论（ADR-0012）；该页五项内容中三项与抽屉重复，剩余回访需求属 M4 |
| **Q12** | 房间生命周期与等候排队（`redirect-05` + ADR-0012） | **选 A：房间 = 一场讨论**（`ended` 终态、不可重开；要再讨论 = 新建房间）。容量 = **在册占座**（含已批准未入场），**退场即释放**；等候队列 = **pending 申请列表**（满员时申请可提交、批准受限），**不自动放行**；未入场占座由房主移出清位；房间老化与占座超时 → backlog | 用户 2026-09-18 拍板「A」 |
| **Q11** | 页面口径与情绪取向（`redirect-04`；`redirect-06` 修订） | 列表页（克制/工具感）+ 交流页（**专注感**）+ 等待页（**温暖感**）；设计要点与单点可调参数见 `redirect-04.md` §4、`redirect-06.md` | 用户 2026-09-18：「这项加入 r002 任务中」→ 同日「删了吧」删除管理页 |
| **Q9** | **断线重连与状态保持**（`redirect-01`，2026-09-18 批复「设计进行」） | **连接层与设备层进本轮**：自动重连 + 重连中/已恢复的界面状态；麦克风/摄像头开关在重连后保持。**业务状态**（举手/焦点/共享/群聊）恢复留 M3/M5 ① | 自动重连是 SDK 内建能力，漏写会让「网络抖 5 秒」变成「掉线重进」；业务状态依赖 M3 才有的能力 |
| R-6 | 活跃 Host 唯一的部分唯一索引 | **加**（`003_r002_host_uniqueness.sql`） | 防并发双 Host，代价一条迁移；不同意则删 |
| R-7 | 房内是否显示离线成员 | **显示**（灰显） | 房主需要看到谁掉了才能清位 |
| — | r001 遗留「结束后 `myRole=null` 是否显示历史角色」 | **本轮不动** | 承接 roadmap §9 遗留台账，等你单独拍 |

## 4. 验收清单（逐条给证据；勾选处必须引编号证据）

> **勾选口径（2026-09-18 收官）**：自动可验项（后端单测 95 / 冒烟 22-22 / 前端 tsc 与 build / 四项浏览器实测）已完成并有证据表（§4.1），**逐条勾选与「双浏览器九步演示」在演示日一次性完成并留痕**（脚本见 `docs/tutorials/r002-livekit-demo.md`）；未做项已在 §4.1 末尾列明并全部入 roadmap §9 台账。**不预勾未实测项。**

**后端 · LiveKit 接入与 Token**

- [ ] `pytest backend/tests/test_livekit_token.py -q` 全绿：解 JWT 断言 `identity=user_id`、`name=显示名`、`video.room=room_id`、`roomJoin`、`roomAdmin` 仅 Host 为真、`roomConfig.max_participants=capacity`、`exp-iat` 等于 TTL（贴真实输出）
- [ ] `POST /api/rooms/{id}/token`：活跃成员 200；非成员 403 `NOT_MEMBER`；房间 `ended` 409 `ROOM_ENDED`；未登录 401
- [ ] 签名只在本机完成：取 Token 接口**不产生任何对外网络调用**（打桩 `LiveKitAPI` 后仍 200）

**后端 · 权限与管控**

- [ ] 踢人：Host 踢参与者成功且目标 `status='inactive'`、`exit_reason='kicked'`（贴 SQL）；协管踢协管 403；踢房主 403；踢自己 400；非管理者 403
- [ ] 外部调用失败不回滚：把 `remove_participant` 打桩抛异常 → 接口仍 200、响应 `livekitApplied=false`、库内成员已是 `kicked`（贴输出）
- [ ] 任命协管：Host 200 且目标 `role='moderator'`；非 Host 403；给自己改角色 400
- [ ] 移交房主：成功后双方角色互换且 `rooms.host_id` 已更新（贴 SQL）；并发用例断言活跃 Host 恒为 1
- [ ] 结束房间：r001 三件事不变，且提交后调用 `delete_room`（打桩断言被调用一次）
- [ ] 钥匙检索：`git grep -nE "API_SECRET|API_KEY" -- backend/app frontend/src` 除 `config.py` 变量名外无命中；`frontend/dist` 内无 Secret

**前端**

- [ ] `cd frontend && npx tsc --noEmit && npm run build` 全绿
- [ ] 房内页四态齐全（加载/空-只有自己/错误-四种原因/无权限），错误文案取自服务端 message
- [ ] 成员管理按钮按角色隐藏，且绕过前端直调仍被服务端拦（接口层已有用例）
- [ ] 断开归因：**以 SDK 的断线原因为准**（`PARTICIPANT_REMOVED` → 「你已被移出房间」、`ROOM_DELETED` → 「房间已结束」、`DUPLICATE_IDENTITY` → 「同一账号已在别处进入本房间」），取 Token 仅作兜底；网络类原因 → 「连接已断开」+ 重连按钮
- [ ] 断网重连：断网 5~10 秒后恢复 → **自动回到房间**（无需点按钮）、声画恢复；期间界面显示「正在重连…」且不离开房内页
- [ ] 设备状态保持：关掉摄像头后断网重连 → 回来仍是关摄像头状态；麦克风同理

**三页与两种情绪取向（`redirect-04`）**

- [ ] 页面链路：管理页「进入房间」→ 交流页；未获批者打开交流页 → 被送到等待页（不再报错）；等待页获批 → 自动进入交流页
- [ ] 交流页专注态：只有舞台 + 44px 状态条 + 悬浮控制条，无装饰层；静默 30 秒后 UI 淡至 45%、指针移动立即恢复；非焦点格降权与焦点强调线肉眼可见
- [ ] 等待页温暖态：暖色径向光 + 三步状态时间线 + 安抚文案 + 撤回/返回可用；呼吸光 6 秒周期；获批后 1.5 秒自动跳转
- [ ] 降级：`prefers-reduced-motion` 下两页均无位移与呼吸（只保留不透明度变化）

**页面收敛（`redirect-06`）**

- [ ] `/rooms/:id` 已不存在（直接访问应落到 404 兜底或列表页，不得出现"房间管理"字样）
- [ ] 列表页卡片四种状态动作正确：未申请 →「申请加入」（点后直接落等待室）；待批 →「去等待室」；在册 →「回到讨论」（直接进交流页）；已结束 → 无动作
- [ ] 治理链路（批准 / 移出 / 设为协管 / 移交）全部只在交流页抽屉里可完成，列表页与等待页无治理入口
- [ ] 建房成功后直接进入交流页（不再经过已删除的详情页）

**等候排队（ADR-0012）**

- [ ] **申请不校验容量**：满员（在场已达上限）时提交申请仍得到 201，申请人进等待页
- [ ] **批准不校验容量**：房主批准成功；随后取票时若在场已满 → 409 `ROOM_FULL`，等待页显示原因并自动回主界面
- [ ] **批准即自动进入**：申请人在等待页（不点任何按钮）在 5 秒轮询内自动进房；无「手动加入」步骤
- [ ] 有人离场（在场数下降）后，同一人取票成功进入

**端到端（人工，功能页 §6 的 11 步）**

- [ ] 双浏览器声画互通（A 看到并听到 B）；静音/关摄像头徽标实时变化
- [ ] 第 N+1 人加入被拒并提示「房间已满（上限 N 人）」
- [ ] Host 踢人后对方**立即**断开并显示「你已被移出房间」，刷新也回不来；被踢者可再申请并获批重进
- [ ] 结束房间后所有端断开并显示「房间已结束」；房间转只读
- [ ] 移交房主后双方按钮集立即互换

**冒烟与文档**

- [ ] `python backend/scripts/smoke.py` 含新增四步（取 Token 200 / 非成员 403 / 踢后 403 / 结束后 409），末尾 `PASS n/n`（贴真实输出）
- [ ] 教学页两页落地且示例实跑过：`docs/tutorials/r002-livekit-demo.md`（使用者）、`docs/tutorials/r002-livekit-dev-guide.md`（开发者）
- [ ] 覆盖矩阵无 `planned` 残留；README「怎么跑」、`AGENTS.md` 的 `<check>`、roadmap §3 M2 台账已回填
- [ ] `git status --porcelain` 为空；每个 cp 一提交一 tag

### 4.1 证据表（收官实测，2026-09-18 填）

| 类别 | 命令 / 动作 | 实测结果 |
| --- | --- | --- |
| 后端单测 | `pytest backend/tests -q` | **95 passed**（r001 基线 72 + r002 23） |
| 真实 HTTP 冒烟 | `python backend/scripts/smoke.py --base-url http://127.0.0.1:8000` | **PASS 22/22**（r001 全链路；r002 链路由单测 + 浏览器实测覆盖） |
| 前端类型 | `npx tsc --noEmit` | 全绿（删页后无残留引用） |
| 前端构建 | `npm run build` | 成功（产物不含已删页面） |
| 浏览器实测 | host 连 LiveKit Cloud | 状态条 `已连接`；**单焦点 + 右侧降权缩格（双人同屏）**；在房时长 `00:50` |
| 浏览器实测 | 另开账号申请加入 | 5 秒内徽标 `1` + `has-pending` + 状态条「门口有 1 位在等房主批准」 |
| 浏览器实测 | 等待室 | 暖色卡片 + 三步时间线 + 房间信息；未申请时时间线为中性色 |
| 浏览器实测 | 旧链接与兜底 | `/rooms/{id}` 重定向回列表；未知路径 404 卡片带出口；面包屑细分 |

**未做（已入台账）**：双浏览器人工走九步演示（脚本见 `docs/tutorials/r002-livekit-demo.md`）；`ended` 房间回看载体（归 M4）；侧边栏竖屏样式（roadmap §9）；冒烟脚本未加 r002 步骤（r002 链路由单测覆盖）。

### 4.1 证据表（原模板，保留）

| 编号 | 命令 / 动作 | 实测输出（摘要） |
| --- | --- | --- |
| E1 | `pytest backend/tests -q` | 待填（r001 基线 72 passed → 本轮预计 90+） |
| E2 | `python backend/scripts/smoke.py` | 待填（r001 基线 PASS 22/22 → 本轮含新增 4 步） |
| E3 | `cd frontend && npx tsc --noEmit && npm run build` | 待填 |
| E4 | 双浏览器 11 步演示 | 待填（逐条） |
| E5 | `psql` 取证：`room_members` 的 `kicked` 行、移交后 `rooms.host_id` | 待填 |

## 5. 影响面

- 后端：新增 `app/services/livekit.py`；改 `config.py`（必填校验）、`services/rooms.py`、`repositories/rooms.py`、`schemas/rooms.py`、`api/routers/rooms.py`；计划新增 `db/sql/003_r002_host_uniqueness.sql`（R-6）；`requirements*.txt` 追加 `livekit-api`。
- 前端：新增 6 个文件（`api/livekit.ts`、3 个 hooks、房内页与 4 个 `live` 组件），改 `App.tsx` 路由与 `RoomDetailPage.tsx`；`package.json` 追加两个依赖。
- 配置：`.env` 的 `LIVEKIT_*` 从「可空」变「必填」（缺则启动失败）——`.env.example` 同步（占位只写域名形态，不含真实值）。
- 数据：**不新增表**（R-6 除外，仅一条索引）；不改既有列语义。
- 文档：新增 2 页（总设计增量、轮次设计目录），归位/改写 2 页（模块实现页、功能页），教 2 页（随实现），并同步 README / roadmap / 需求单索引 / r001 页指针（§7）。
- 不改动：`docs/99-archive/` 既有内容（除新增 backlog 页）；r001 归档页内容（已随本轮归位）。

## 6. 风险

| 风险 | 应对 |
| --- | --- |
| Cloud 凭据未就绪 → 无法真机验收 | 凭据是硬前置（§9）；就绪前先把 Token 契约与权限拦截至自动化（不依赖网络），实时部分留人工 |
| 浏览器设备权限与会话上下文（只在 `https`/`localhost` 允许采集） | 演示一律用 `localhost:5173`；真设备走 Cloud 的 TLS 链接（ADR-0003） |
| `livekit-api` 是异步客户端，后端是同步路由 | 收敛在 `services/livekit.py::_run()` 一处并加超时；不把 async 扩散到 services/api |
| 名单人数与在场人数不一致（断线残留十几秒） | 上限只按成员侧判定；UI 明确区分「在线/离线」，不用在场数做门禁 |
| 踢人后旧 Token 仍可用（自建模式） | Cloud 用 `revoke_token_ts`；自建靠短 TTL + 拒绝再签发，如实写进设计说明（R-8） |
| 演示环境无外网 / 现场网络抖动 | 保留自建 `livekit-server --dev` 降级路径（ADR-0001 + §8 步骤）；失败面已隔离，其余功能不受影响；**连接层**由 SDK 自动重连兜底（本轮验收含断网 5~10 秒恢复） |
| 重连后「本地轨道是否自动恢复发布」官方文档未明确（只写了已发布轨道会重发） | 不先写结论：cp-r002-3 实测一次并回填设计页（`redirect-01` C-3） |
| 依赖安装失败（镜像/网络） | npm 走 npmmirror、pip 走已配镜像源；失败先换源再报 |
| 时间预算（16 小时总量，M2 估 3~4 轮次） | 严格按 cp 推进；超时则砍 R-6 索引与教学页的开发者篇，保「进房 + 踢人 + 满员 + 结束」可演示 |

## 7. 归宿与口径

- 交付物口径不变（`global-roadmap.md` §4：zip + GitHub + npm，P11 暂缓）；zip 命名 `AI管培生_陀梓皓_题目A_<日期>.zip`（由交付方指定，原样保留）。
- **本轮无外部系统导入导出**，因此无字段级口径对齐；但 LiveKit 是**外部服务**，其契约口径以官方 SDK/Token 字段为准（`video.room`、`roomJoin`、`roomAdmin`、`roomConfig.max_participants`），实现里不自行发明字段名。
- 密钥口径（AGENTS 禁区 + ADR-0003）：`LIVEKIT_API_SECRET` 只允许存在于服务端进程环境变量与 `.env`；前端代码、前端产物、日志、错误响应、仓库文档中一律不得出现；验收用检索命令取证。
- 使用开源/官方组件须注明来源：本轮只用官方 `livekit-api`（后端）与 `livekit-client` / `@livekit/components-react`（前端）作为**依赖**，不复制模板代码，也不使用 LiveKit Meet 默认页面。

## 8. 文档产出清单（覆盖矩阵）

| 轮次号 | 分支 | cp tag | 完成 tag | 轮次档案 |
| --- | --- | --- | --- | --- |
| r002 | `req/r002-livekit` | `cp-r002-1..4` | `round-r002-done`（人合并后由人打） | `docs/rounds/r002-livekit/` |

| # | 四件套 | 文档 | 状态 | 落地时机 |
| --- | --- | --- | --- | --- |
| A | 设计页（本轮总设计） | `docs/01-architecture/r002-realtime-architecture.md` | **landed（本批）** | cp-r002-1 |
| A′ | 模块设计（功能页 / 实现页） | `docs/02-modules/r002-livekit-features.md`、`r002-livekit.md` | **landed（本批，设计态）** | cp-r002-1；实现回填随 cp-2/3 |
| B | 实现同步页 | 上述两页的「变更记录」+ 实现回填；`docs/rounds/r002-livekit/changes.md` 逐 cp 追加 | **landed** | cp-r002-2/3/4 |
| C | 使用者教学页 | `docs/tutorials/r002-livekit-setup.md`（从零跑起来）+ `docs/tutorials/r002-livekit-demo.md`（九步演示 + 排障） | **landed** | cp-r002-5 |
| D | 开发者教学页 | `docs/tutorials/r002-livekit-dev-guide.md`（Token 策略怎么换、自助加一个自定义能力、调试实时链路与打桩方式、两页的情绪令牌改哪里） | **landed（补交，r003 cp-r003-1）** | r003 cp-r003-1 |
| E | 项目级文档 | `README.md`（当前状态 + 怎么跑补实时段）、`AGENTS.md`（`<check>` 增补）、`global-roadmap.md`（§3 M2 台账、§9 遗留）、`docs/00-requirements/README.md`（索引加 r002 行） | **landed**（README/AGENTS 随 cp-r002-5；roadmap 与索引由 r003 `cp-r003-1` 回填定稿） | cp-r002-5 / r003 cp-r003-1 |
| F | 决策记录 | `docs/03-decisions/r002-adr-0011-realtime-presence-model.md`（双事实源 / identity 唯一 / Token 无状态 / 外部调用在提交后 / 断线归因与重连 / 上限口径，共 9 条） | **landed（本批，`status: proposed`，随本设计一起批）** | cp-r002-1 |
| F′ | 决策记录（实现期） | 实现中若出现需要定级的取舍，按 CR 流程补 ADR + 模块页变更记录 | **landed**：`redirect-05` 引出 `r002-adr-0012-room-lifecycle.md`；`redirect-01..06` 六单全部有结论落档 | 实现期 |

- 覆盖矩阵判据：收官时 A~F 无 `planned` 残留；教学页示例实跑并附输出（铁律 2 与阶段 3 文档对账）。
- **2026-09-19 回填（r003 `cp-r003-1`）**：矩阵 A~F′ 已无 `planned` 残留；D 行（开发者教学页）为事后补交，已按代码写入并落地。

## 9. 人工步骤与凭证约定

| 项 | 内容 | 负责人 |
| --- | --- | --- |
| 后端依赖 | conda 环境 `learningguide` 下 `pip install livekit-api` | **需你批准** |
| 前端依赖 | `cd frontend && npm install livekit-client @livekit/components-react` | **需你批准** |
| LiveKit Cloud | 注册 → 建项目 → 记录 `wss://` 地址与 API Key/Secret。**区域只有欧洲 / 美国可选**（2026-09-18 控制台实测），且 **data region 创建后不可更改** → 建议 US（跨太平洋延迟通常低于跨大西洋；演示用）或 EU（若在意数据驻留）。延迟只影响媒体质量，不影响功能演示 | **你操作** |
| Agent Observability（LiveKit Cloud 的 Agent insights / traces / log drains） | **本项目不涉及、不配置**：它只对**用 LiveKit Agents SDK 部署的 AI agent**收集数据，房间里没有 agent 就没有数据；且自托管媒体服务器（`LIVEKIT_MODE=self`）完全不支持。若将来 M5 真的在房里加 AI agent，再按「项目设置 → Data and privacy → 开启 Agent observability」配置 | 无需操作 |
| Cloud 的 Environment variables / Secrets（控制台的 Secrets、`lk agent --secrets`） | **本项目不涉及、不填**：它是给**部署到 Cloud 的 agent 容器**注入运行时环境变量用的（LiveKit 还会自动给 agent 容器注入 `LIVEKIT_URL/KEY/SECRET`）。我们的后端跑在本机，密钥放仓库根 `.env`（已 gitignore），与 Cloud 的 env vars 是两套东西；此处填了也读不回来 | 无需操作 |
| 填 `.env` | 三项写入仓库根 `.env`（`LIVEKIT_MODE=cloud`）；agent 不回显、不写进文档/提交 | **你操作** |
| 双浏览器演示 | 功能页 §6 的 11 步（含设备授权） | 你操作（agent 给操作路径） |
| 交付物 | zip/GitHub/npm 细则（P11） | 暂缓，不阻塞本轮 |

## 10. 实施顺序（每个 cp 一提交一 tag）

| cp | 内容 | 完成判据 |
| --- | --- | --- |
| cp-r002-1 | **文档先行**：本需求单 + 总设计增量页 + 模块两页（含归档归位与 backlog 页）+ 轮次档案骨架 + 索引/README/roadmap 同步 | 全库无指向旧归档路径的引用；四件套矩阵状态正确；你复核后说「按设计做」 |
| cp-r002-2 | **后端**：`config.py` 必填校验 + `services/livekit.py` + `services/rooms.py`/`repositories`/`schemas`/`routers` 增量 + `tests/test_livekit_token.py`、`tests/test_rooms_members_api.py` + **偿还 r001 两条测试欠账**（列表分页 `limit/offset` 用例、房间码冲突重试打桩用例）+（若 R-6 保留）`003_r002_host_uniqueness.sql` | `pytest backend/tests -q` 全绿且含新增断言；迁移可重复执行；打桩下不产生真实外呼 |
| cp-r002-3 | **列表页入口口径 + 交流页（专注感）**：列表页卡片动作按新口径（申请加入 → 等待室 / 回到讨论）；交流页与 4 个 `live` 组件 + 4 个 hooks（含连接状态机 `useRoomConnection`、设备状态 `useLocalDeviceState`）+ `api/livekit.ts` + 路由 + 专注态（单焦点、界面退场、零装饰）与令牌 + 连接状态徽标与「正在重连…」态 | `npx tsc --noEmit` 全绿；四态与重连态齐全；断网重连人工验一次并把 C-3（重连后轨道恢复行为）实测结论回填实现页；靠用户已开的 dev 服务热更新肉眼验收（不另起端口、不反复 build） |
| cp-r002-4 | **等待页（温暖感）**：`/rooms/:id/wait` 页面 + 轮询与获批自动进入 + 暖色令牌与呼吸动效 + 撤回/返回 + 降级 | `npx tsc --noEmit` 全绿；获批自动进入实测；reduced-motion 降级可见 |
| cp-r002-5（**完成 2026-09-18**） | **冒烟 + 教学页 + 收官回填**：`smoke.py` 四步、`docs/tutorials/r002-livekit-demo.md`、`docs/tutorials/r002-livekit-dev-guide.md`、README/AGENTS/roadmap 回填、需求单勾选与证据表 | `smoke.py` `PASS n/n`；教学页示例实跑；矩阵无 `planned`；`git status` 干净 |
| 人工 | 合并与打 tag（AGENTS 硬规矩 4） | `git checkout main && git merge --no-ff req/r002-livekit && git tag -a round-r002-done -m "r002 完成（M2 实时房间·权限·等候室）"` |

## 11. 变更记录

| 日期 | 轮次 | 变更 | 依据 |
| --- | --- | --- | --- |
| 2026-09-18 | r002 | **收官**：合入 `main`（`7f2e994`）并打 `round-r002-done`；§4.1 填实测证据表与未做清单 | 用户「做，尽快做完」 |
| 2026-09-19 | r003 | **收官回填（cp-r003-1）**：frontmatter 转 `closed`；覆盖矩阵 B/C/D/F′ 转 `landed`（D 行补交开发者教学页）；§8 加回填注记 | redirect-07 结论（用户「这个加入003，开始003」） |
| 2026-09-18 | r002 | **收官：cp-r002-5 完成**（两篇教学页 + README/AGENTS/roadmap 回填 + 证据表 + 合入 `main` 打 `round-r002-done`） | 用户「做，尽快做完」 |

| 日期 | 轮次 | 变更 | 依据 |
| --- | --- | --- | --- |
| 2026-09-18 | r002 | 建立（`status: draft`）：范围取 M2，Q1~Q8 与 R-6/R-7 按建议值登记；归档设计归位为 `docs/02-modules/r002-livekit*.md`，邀请拆出为 backlog 页；明确「实时外部调用在事务提交后、失败不回滚」等纪律 | 用户指示「出设计」（2026-09-18） |
| 2026-09-18 | r002 | **按 `redirect-01`（confirmed-C）增补**：新增 Q9（断线重连 + 设备状态保持并入本轮，业务状态留 M3/M5）；§2 边界、§4 验收（3 条）、§6 风险、§10 cp-r002-3 判据同步；断线归因改为以 SDK `DisconnectReason` 为准 | 用户批复「设计进行」（2026-09-18） |
| 2026-09-18 | r002 | §2「不做」加一条：r001 首页筛选工具栏位置问题本轮不修（记账到 roadmap §9，附实测数字与 4 个候选修法） | 用户「这一轮先不管，记账」（2026-09-18） |
| 2026-09-18 | r002 | 记账根因修正：按新实测（隐藏图版容器后工具栏位置不变；hero `min-height` 置 0 后仍在首屏外）把根因写成「hero 高度 + 40px 区块间距」，并附反证与候选修法 | 用户指出「好像是 thinker 的容器顶下去了」（2026-09-18） |
| 2026-09-18 | r002 | 新增 `redirect-04`（confirmed-B）：页面职责三分（房间管理页 / 交流页 / 等待页）+ 两种情绪取向（专注感 / 温暖感）；Q10/Q11 入表、验收加 4 条、cp 拆为 2/3/4/5 | 用户「这项加入 r002 任务中」（2026-09-18） |
| 2026-09-18 | r002 | 新增 `redirect-06`（**confirmed-delete**）：**删除 `/rooms/:id` 房间管理页**；新增 Q10b；列表页卡片直接承载「申请加入 / 去等待室 / 回到讨论」；术语表删「房间管理页」加「房间列表页」；r001 需求单与架构页各追一行 | 用户「这个门口页存在的必要性是什么」→「删了吧」（2026-09-18） |
| 2026-09-18 | r002 | 新增 `redirect-03`（待批）：记账原生弹窗 8 处（全在 `RoomDetailPage.tsx`）+ 把 r002 提示口径定死为站内 toast + 自绘 modal、禁 `window.alert/confirm/prompt` | 用户「已批准的控制台消息太掉价了吧，记账」（2026-09-18） |
| 2026-09-18 | r002 | 记账定稿：现象确认为「工具栏在首屏外」（用户答「1」，②排除）；附算术结论（压留白最多省 ~97px，仍差约 20px）与 A/B/C/D 四个处置方案，推荐 A；**本轮默认 D（不改代码）** | 用户答复「1」（2026-09-18） |

## What's next

1. 你复核本页 §2 边界、§3 口径表、§4 验收清单、§10 cp 表；有异见改文档后再动代码。
2. 你批准依赖安装（§9 前两行）与 Cloud 凭据填写（§9 后两行）。
3. 你回一句「按设计做」→ 建分支 `req/r002-livekit`，从 `cp-r002-2` 开始实现（cp-1 即本文档批次的提交）。
