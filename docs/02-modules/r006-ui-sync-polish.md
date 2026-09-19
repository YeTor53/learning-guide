---
title: r006 实现页：界面同步与优化
description: 麦徽标真实状态源、lg.roster 同步机制、个人信息浮窗与语录池、图版位置令牌；含实测数字与踩坑。
type: reference
status: draft
owner: 陀梓皓
updated: 2026-09-19
---

<!-- overview -->
口径裁定见 `docs/03-decisions/r006-adr-0017-ui-polish-decisions.md`；需求见 `docs/00-requirements/r006-ui-sync-polish.md`；设计与实测表见 `docs/rounds/r006-ui-sync-polish/{design,changes,review}.md`。后端零改动。

## 1. 麦徽标（`components/live/ParticipantTile.tsx` + `hooks/useMicStates.ts`）

- 状态源：`participant.isMicrophoneEnabled`（远端由 LiveKit 同步，实测 `true → false` 正确）。
- **重渲染**：`useTracks` 只在轨道**集合**变化时重渲染，静音不算集合变化 → 新增 `hooks/useMicStates.ts`（`identity → isMicrophoneEnabled`），订阅 10 个事件（`TrackMuted/TrackUnmuted/TrackPublished/TrackUnpublished/TrackSubscribed/TrackUnsubscribed/ParticipantConnected/ParticipantDisconnected/LocalTrackPublished/LocalTrackUnpublished`）。
- 呈现：静音时 `.live-tile-mic`（`MicOff` 图标 + `title/aria-label="麦克风已静音"`），**只图标不加文字**；未静音不出现。
- 坑：prop 名叫 `micMuted`，而状态表里存的是 `isMicrophoneEnabled` → 传参处必须取反（cp-1 实测把徽标做成了反向）。

## 2. 名册/待批同步（`hooks/useRosterSync.ts` + `pages/RoomLivePage.tsx`）

- `useDataChannel` 增 topic `lg.roster`（`{v,at,actorIdentity}`）；本端动作后 `broadcastRoster()`，别端收到即重取。
- 四条路：① 广播 ② 进房/重连成功 ③ 窗口 `focus` / `visibilitychange` ④ 30 秒可见性感知兜底轮询。
- 重取键：`['live-room', id]`（人数/容量/名册）+ `['live-room-requests', id]`（待批，原本 5 秒轮询，现在秒级）。
- 口径不变：**HTTP 落库是唯一真相**，`lg.roster` 只是加速（ADR-0013 沿用）。

## 3. 个人信息浮窗（`components/SidebarUserCard.tsx`）

- 默认只一行（头像 + 名字 + 折角）；点击或**键盘** `focus`（`:focus-visible`）展开 `role="dialog"` 浮窗；`Esc` / 点击外部关闭。
- 浮窗内容：名字 + 邮箱 + `加入于` + **今日一句哲学语句** + 登出；账号 ID 不再展示（放 `title`）。
- 坑：`onFocus` 与 `onClick` 会**互相抵消**（鼠标点击先 focus 打开、click 再取反 → 点了打不开）；只在 `:focus-visible` 时用 focus 打开才正确。
- 窄屏（横向条）：浮窗改为向下弹，实测 900×1000 完整在视口内。

## 4. 哲学语句池（`content/philosophy.ts` + `components/QuoteLine.tsx`）

- **只收真实语录**（12 条，中文译句 + 作者），单文件可替换。
- `pickDailyQuote()`（浮窗「今日一句」）与 `pickQuoteFor(slot, date)`（各处解释性文案：`hash(slot)+年内天数` 取模）。
- `<QuoteLine slot="…" />`：**只增不替**，功能文本原样保留。已铺：首页 hero、首页未登录空态、侧边栏未登录块、新建房间页、等待页、交流页空态、抽屉讨论/成员空态。
- **目录命名坑**：仓库 `.gitignore` 第 23 行是**未锚定**的 `data/` → 任何层级的 `data` 目录都被忽略。最初放在 `frontend/src/data/` 的语录池**没进版本库**（新克隆会编译失败）→ 改放 `frontend/src/content/`。**前端不要用 `data/` 作目录名**。

## 5. 图版初始位置（`styles/global.css`）

- `--thinker-top`：`-110px → -60px`（窄屏 `-92px → -46px`）→ 页顶未滚动时图版上沿 **60 → 110px（下移 50px ≈ 图版可视高 503px 的 10%）**；竖屏 46px。
- 变量定义在 `.hero` 上（不在 `:root`）——**调参要改 `.hero` 的令牌**，在 `documentElement` 上覆盖无效（cp-4 实测踩到）。
- 容器底仍锚「创建房间」行上方，行程自动缩短，`overflow: clip` 保证不出容器。

## 6. 验证数字（2026-09-19）

| 项 | 结果 |
| --- | --- |
| 麦徽标 | A 未静音两端无徽标 / A 静音 → B 侧出现 / 取消 → 消失 / 反向同样（双向各一次） |
| 人数同步 | A 界面批准 → B 端 **0.23~0.46 秒**（改前 5 秒仍不变，只认 F5） |
| 待批同步 | B（协管）徽标 **1.46 秒**清空（原 5 秒轮询） |
| 兜底 | 纯 API 改库（无广播）：聚焦触发 **0.22 秒**；30 秒轮询 **9.8 秒**（相位决定）拉平 |
| 浮窗 | 默认无邮箱/id；点击 / 键盘 Tab 展开；`Esc`、点外部关闭；窄屏向下弹在视口内 |
| 语录 | 同槽位同日稳定；各槽位错开（hero=庄子 / 未登录侧边栏=加缪 / 讨论空态=「认识你自己」 / 成员空态=罗素） |
| 图版 | 桌面下移 50px、竖屏 46px |
| 门禁 | `pytest` **111 passed** / `smoke` **PASS 40/40** / `tsc` + `build` exit 0 |

## 7. 遗留

1. `stage-empty` 那句只在「房间没有任何轨道」时可见（已有摄像头占位轨时不渲染空态），属空态本身的性质，非缺陷。
2. 「共享中有人说话不夺焦点」仍未单独实测（r004 起的欠账，本轮未做）。
3. r004 的 E18b（本地 livekit-server 停 8 秒真断）仍未做；E18c 断网演练等你跑 `reconnect-drill.bat`。
4. 演示库房间数已超过列表默认页长（20）→ 相关用例已改为显式页长（cp-5）。
