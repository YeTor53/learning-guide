---
title: r013 变更台账
description: 演示就绪五项（焦点修复 / 强停共享取证 / worker 自愈 / 结束房回看 / 大屏进抽屉）的逐 cp 提交、用户消息与决策登记。
type: reference
status: draft
owner: 陀梓皓
updated: 2026-09-20
rounds: [r013]
---

<!-- overview -->
一个提交 = 一个逻辑增量；提交信息 `type(scope): ≤50字 [Req: r013]`。

## 1. cp 提交台账

| cp | 提交 | 内容 | 测试/证据 | 文档 |
| --- | --- | --- | --- | --- |
| cp-r013-1 | 文档先行 | 需求单（含断线方案 §10.5）+ 逐文件函数级设计 + 台账骨架 | 不适用（纯文档） | 需求单、design |
| cp-r013-16 | 本次提交 | **根因修复「一直断链」**：摘掉 `livekit-client` 每次 connect 无条件挂的 `window.addEventListener('freeze', onPageLeave)`（= 浏览器一冻结就 disconnect）；`pagehide/beforeunload` 保留（关标签仍立即离开）。另：房间页控制坞与抽屉 tab 全改纯图标（状态点 + tooltip，cp-15） | 真机：派发 freeze 4 次不断；CDP 冻结 4 秒解冻后 10 秒自回；**离屏 hidden 静止 60 秒全程已连接**（修前 5 秒掉且不自愈）。tsc/build 绿；台本 UI 自检 30→29/30（余 1 条为脚本口径未对齐，专用脚本 17/17 通过） | 需求单 §10.9 |
| cp-r013-14 | 本次提交 | 口径升级「界面不管怎样都不许断开」：连接层除真终态外一律 `reconnecting`（不再落 closed）、重连失败也保持；页面层不限次数自愈（票现签、退避≤4s、visibilitychange/resume/5s 兜底、连接对象入 ref 修「effect 被反复 cleanup 掐死循环」）；`connect()` 失败不再打「已断开」 | 真机连续 4 次掐断：**从未出现「已断开」**，恢复 7.3/7.9/7.9/11.0 秒；tsc/build 绿。已知边界：同实例重连需等 SDK 结算（7~11s），换实例的改法试过、把初次连接带坏已回退 | 需求单 §10.8 |
| cp-r013-13 | 本次提交 | 修 `agents.bat`（你实测报错）：① 文件曾是「双 CR + UTF-8」，cmd 按 GBK 读会把中文注释拆出来当命令执行 → 改为 **GBK + 标准 CRLF**；② `lg_agents` 环境**没装 python-dotenv**，worker 不会自己读 `.env` → 脚本改为先把 `.env` 注入环境变量再启动（原症状：`ValueError: ws_url is required` + 退出-重启循环）；③ 启动打印注入自检（只报「有没有」，不回显值） | 实测：worker `registered worker {"agent_name":"learning-guide-transcriber","region":"Japan"}` | 台本 §0、本表 |
| cp-r013-12 | 本次提交 | 演示库清理：删 **169 间**测试房 + **593 个**脚本账号 + 大屏测试消息与残留举手/访问；新增可复跑 `backend/scripts/clean_demo_junk.py`（默认干跑、`--yes` 真删、`--keep-users`）；台本 §0/§6 改用该脚本并纠正「演示前 `--reset`」旧指引 | 清后：房 8（3 间 seed + 5 间你的演示房）/ 账号 4 / 成员 17 / 聊天 16 / 大屏 0 / 审计 1 | 台本 §0 §6、本表 |
| cp-r013-11 | 本次提交 | 修「隐藏就断链」：① 连接层识别 `freeze`/`pagehide`（SDK 无条件挂钩导致的静默断开）→ 正确归因 + `autoDisconnected`；② 页面层回到可见自动重连（3 次退避）+ 失败走「重新连接」banner；③ `demo-window.bat` 加抗冻结/抗节流开关 | 确定性冻结→解冻后 **4.5 秒自回「已连接」**；带开关离屏 **45 秒**全程「已连接」；tsc/build 绿 | 需求单 §10.7、台本 §3.5 |
| cp-r013-9 | 本次提交 | 断线道具**首选方案**：`demo-firewall-cut.bat` + `backend/scripts/demo_firewall_cut.py`（临时防火墙拦 LiveKit 出网 N 秒，`try/finally` 删规则 + `--remove` 兜底 + `--status` 自检）；netsh 输出按 GBK 解码修乱码；台本 §3.5 改为首选防火墙法、进程冻结降为备选；需求单 §10.6 补实测表与前提 | 干净基线：断中 1.0/3.0 秒进「正在重连…」，恢复后 5~6 秒回「已连接」，举手保持，规则无残留 | 台本 §3.5、需求单 §10.6 |
| cp-r013-8 | 本次提交 | ③ 的**现场道具**（你点名要的）：`demo-window.bat`（受控演示窗口：固定 profile + 固定调试端口）+ `demo-disconnect.bat` + `backend/scripts/demo_disconnect.py`（点一下 → 只冻该窗口的网络服务子进程 N 秒 → 自动恢复）；台本新增 §3.5，需求单新增 §10.6（三次实测表 + 边界 + 不可用手段） | 12 秒冻结：恢复后 ~1.5 秒「正在重连…」→ ~4.5 秒「已连接」+ 举手保持；10 秒那次未自愈（已写进兜底）；CDP 离线手段实测不可用 | 台本 §3.5、需求单 §10.6 |
| cp-r013-7 | 本次提交 | 收官：台本 UI 自检脚本加「第四个 tab」与「回看页两段（只读）」判据（28→**30**）；超管隐身脚本等待窗口 8→20 秒并登记并发抖动；review 定稿（E11/E12 + 未闭合 5 条）；模块页/roadmap/索引/教学页回填 | `pytest 212` / `smoke 59-59` / `tsc·build 绿` / 台本 UI 30-30 / 行为流 18-18 / 隐身 17-17 / 焦点 8-8 / 强停 0.5 秒 | 4 处模块页 + roadmap + 索引 2 处 + 2 教学页 |
| cp-r013-6 | 本次提交 | E 项：大屏并入交流页抽屉——`GlobalChatPanel`（面板本体，`variant=drawer|embedded`）+ `GlobalChatDrawer`（只剩壳与 Esc）+ `RoomSidePanel` 第四个 tab「大屏」+ `.gc-panel-embedded` 样式；顶栏按钮在交流页仍不渲染（入口改为 tab）。**口径变更**：改写 r012「交流页不挂大屏」——在 r012 需求单 §10.1 与 changes 各加一行指路（不改历史结论） | `tsc`/`build` 绿；真机：4 tab、embedded 面板可发、**跨端 0.5 秒内不刷新可见**、切回讨论正常、交流页顶栏无按钮 | r012 需求单 §10.1 / r012 changes、`docs/02-modules/r012-superadmin-console.md`、台本 v5 |
| cp-r013-5 | 本次提交 | D 项：结束房只读回看页——新增 `pages/ReplayPage.tsx` + `hooks/useReplay.ts`（复用三条既有只读接口）、`App.tsx` 路由 `/rooms/:id/replay`、`RoomCard` 结束房卡新增「回看」按钮、`global.css` 回看样式；**后端零改动**（既有可见性口径本就是「成员/历史成员/房主/协管」）。修一处自身文案缺陷：JSX 里写了 markdown 星号会原样显示 | 用例 **+4**（`test_replay_access.py`：成员 200 / 房主 200 / 超管 200 / 非成员 403 / 未登录 401）→ `pytest 212 passed`；`tsc`/`build` 绿；真机：房主回看三段齐全（时间线 2 行、成员 2 行）、新账号 403 提示、列表「已结束」筛选下点「回看」跳 `/replay` | r008 模块页变更记录 |
| cp-r013-4 | 本次提交 | C 项：worker 自愈与可观测——新增纯函数 `backend/agents/retry.py`；`transcriber.entrypoint` 的连接段改为**有限重试（3 次 / 2+4 秒退避）**，彻底失败时上报原因并以**退出码 2** 退出（不再裸崩）；心跳带 `lastError`，后端 `/rooms/{id}/stt-status` 透出，控制坞芯片 hover 可见 | 用例 **+6**（`test_connect_retry.py` 5 条 + `test_stt_heartbeat.py` 1 条）→ `pytest 208 passed`；`tsc`/`build` 绿；真机：芯片 title 出现/清除「最后错误」各一次 | r010 模块页变更记录、roadmap §9 |
| cp-r013-3 | 本次提交 | B 项：新增 `frontend/scripts/verify-screen-force-stop.py`；真机取证「A 不点停止、直接关标签」→ B 端清格 | **两次实测均 0.5 秒**清格、宫格恢复 1 格；实现无需改动（`useScreenShare` 既有 `TrackUnpublished`/`ParticipantDisconnected` 重扫就够）；**边界**：手段=WS 正常关闭，网络级硬断未测 | `docs/02-modules/r004-room-extras.md` §11 遗留 4 回填 |
| cp-r013-2 | 本次提交 | A 项：新增 `frontend/scripts/verify-focus-three-way.py`（三隔离 Chrome 真跑三人档「给焦点」）；**在当前代码不复现** r009.5 登记的现象 | **PASS 8/8 ×3 次**（三端 `mode=focus`、焦点格各 1、焦点 identity 三端一致）；顺带实测：举手传播到另两端 **2.0 秒**、服务端 1 条；脚本自身踩坑三条已写进头部注释（禁用按钮点击无效 / CDP keepalive ping 超时 / 各端排序「本地优先」不能比首项） | `docs/02-modules/r009-focus-system.md`、roadmap §9 |

## 2. 缺陷与例外登记

（待填）

## 3. 用户消息与决策

| 日期 | 消息/决策 | 落点 |
| --- | --- | --- |
| 2026-09-20 | 「把到 6 的都做了，然后这个断线的测试给我个方案」→ 按编号回读：① 焦点 ② worker ③ 断线（只要方案）④ 强停共享 ⑤ 回看页 ⑥ 大屏进抽屉 | 需求单 §1、§10.5 |

## 4. 变更记录

| 日期 | cp | 变更 | 依据 |
| --- | --- | --- | --- |
| 2026-09-20 | cp-1 | 建台账 | 需求单 v1 |
| 2026-09-20 | cp-15b | 图标化收尾：`verify_r012_superadmin_invisible.py` 改读超管芯片的 `title`（图标化后 chip 无文字，原判据按 `textContent` 会假失败）；实测 17/17 | cp-15 图标化 + 自检脚本对齐 |
| 2026-09-20 | cp-18 | 交付说明页 v2：新增 §2.1「时间投入与取舍」（总制作 ≈ 12 小时；**演示录屏因时间来不及未做**，分镜/脚本/道具齐备仅缺录制剪辑）；`ai-tools-and-models.md` §3 小时数已填、checklist 同步 | 你「加入解释，演示视频时间来不及没做，总制作时间约12小时」 |
| 2026-09-20 | cp-17 | 交付文档：新建项目级交付说明页 `docs/00-project/global-delivery.md`（作业题目 A 交付物四项对照 + 提交口径 + 起服务与演示 + 设计说明导读 + 证据索引 + 已知边界 + checklist）；同时在根 README、`docs/README.md`、roadmap §1 指路 | 你「写交付文档（用来交付面试作业，题目一）」 |
| 2026-09-20 | cp-9 | ③ 首选道具（防火墙真断）交付并实测通过（含「两端必须先已连接」前提）；同步登记「降级客户端放弃重连」观察 | 实测 |
| 2026-09-20 | cp-8 | ③ 现场道具交付（受控窗口 + 一键断/恢复）+ 三次实测与边界；CDP 离线手段判定不可用；删掉未验证通过的本地代理尝试（不留在仓库） | 实测 |
| 2026-09-20 | cp-7 | 收官：门禁与五份真机脚本全绿；未闭合 5 条（FFI 根因 / 网络级硬断 / 断线验收待批 / 脚本并发抖动 / 演示库残留） | 全部命令输出 |
| 2026-09-20 | cp-6 | E 项结论：大屏两壳（抽屉 / 抽屉内 tab），单例数据源；r012 口径变更已指路 | 真机 |
| 2026-09-20 | cp-5 | D 项结论：回看页三段 + 入口 + 权限（用例 4 条 / 真机三条）；后端无改动 | 实测 |
| 2026-09-20 | cp-4 | C 项结论：自愈（重试 + 退出码 2）+ 可观测（lastError 到芯片）；**FFI panic 根因未修**（需升级 `livekit-agents`，你未批） | 用例 + 真机 |
| 2026-09-20 | cp-3 | B 项结论：强停共享 0.5 秒清格（标签关闭路径），无需改码；网络级硬断未测并写明 | `verify-screen-force-stop.py` 实测 |
| 2026-09-20 | cp-2 | A 项结论：不复现 + 脚本固化为回归门禁；台账登记三条脚本踩坑 | `verify-focus-three-way.py` 实测 |
