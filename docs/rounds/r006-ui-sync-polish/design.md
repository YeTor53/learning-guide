---
title: r006 设计：界面同步与优化（函数级）
description: 五个改动面的逐文件函数级设计：麦徽标、lg.roster 同步、个人信息浮窗、语录池、图版位置令牌；含事件流、数据形状、验收映射与非目标。
type: reference
status: draft
owner: 陀梓皓
updated: 2026-09-19
---

<!-- overview -->
需求与验收见 `docs/00-requirements/r006-ui-sync-polish.md`；口径裁定见 `docs/03-decisions/r006-adr-0017-ui-polish-decisions.md`。

## 1. 改动面总览

| 面 | 文件 | 一句话 |
| --- | --- | --- |
| ① 麦徽标 | `components/live/ParticipantTile.tsx`、`components/live/LiveStage.tsx` | 徽标改由**真实麦克风状态**驱动，静音事件触发重渲染 |
| ② 两端同步 | `hooks/useDataChannel.ts`、`pages/RoomLivePage.tsx` | 新增 `lg.roster` 广播 + 三个刷新触发点（聚焦/可见性、进房与重连、30 秒兜底） |
| ③ 个人信息浮窗 | `components/SideBar.tsx`、`styles/global.css` | 默认只一行（头像+名字）；点击 / 键盘 focus 才展开浮窗 |
| ④ 哲学语句 | `data/philosophy.ts`（新） | 12 条真实语录的池 + `pickDailyQuote()`（同日稳定） |
| ⑤ 图版位置 | `styles/global.css` | `--thinker-top` 由 `-110px` 改 `-60px`（窄屏 `-92px → -46px`） |

## 2. ① 麦徽标（`ParticipantTile`）

```ts
// 现状（错）：图标挂在「有没有画面」上 —— 没人开摄像头 → 所有人的格子恒显「麦克风未开」
{!showVideo && <MicOff aria-label="麦克风未开" />}

// 改后：
const micOff = !participant.isMicrophoneEnabled      // 远端由 LiveKit 同步（实测 true→false 正确）
...
<div className="live-tile-bar">
  <span className="live-tile-name">{name}</span>
  {role && <span className={`chip …`}>{ROLE_LABEL[role]}</span>}
  {micOff && <span className="live-tile-mic" title="麦克风已静音" aria-label="麦克风已静音"><MicOff {...ICON} /></span>}
</div>
```

- `showVideo` 与头像块逻辑**不变**（那是「有没有画面」，与麦克风无关）。
- **重渲染来源（必须先实测哪条能触发，再定稿）**：
  - 首选 `useIsMuted(participant, Track.Source.Microphone)`（`@livekit/components-react`，自带订阅）；
  - 回退方案：`LiveStage` 订阅 `RoomEvent.TrackMuted` / `TrackUnmuted` / `TrackPublished` / `TrackUnpublished` 维护一个 `tick` state，作为 props 传进 `ParticipantTile`。
- 静音徽标**只图标**（Q2=2），文字只出现在 `title` 与 `aria-label`（Q1=1：不静音就不显示）。

## 3. ② 两端同步（`lg.roster`）

### 3.1 通道

```ts
// hooks/useDataChannel.ts
export const CHANNEL_TOPIC = { chat: 'lg.chat', hands: 'lg.hands', focus: 'lg.focus',
                               screenStop: 'lg.screen.stop', roster: 'lg.roster' } as const
export interface RosterSignal { at: number; actorIdentity: string }
```

- **广播**：`publishSnapshot(room, CHANNEL_TOPIC.roster, { at: Date.now(), actorIdentity: room.localParticipant.identity })`
- **订阅**：`useDataChannel<RosterSignal>(room, CHANNEL_TOPIC.roster, onSignal)`，与 r004 同一条可靠通道、同一套 JSON 约定。
- 语义边界（沿用 ADR-0013）：**HTTP 落库仍是唯一真相**，`lg.roster` 只是「有人改了名册/待批，赶紧重取」的加速信号；信号丢了有兜底（§3.3）。

### 3.2 广播点（动作端）

`RoomLivePage.tsx` 里**已有** `refresh()` 的动作回调，全部追加一次广播（一处 helper）：

| 动作 | 现有回调 | 追加 |
| --- | --- | --- |
| 批准 / 拒绝申请 | `refresh()` + 待批查询失效 | `broadcastRoster()` |
| 踢人 / 设协管 / 取消协管 | `refresh()` | `broadcastRoster()` |
| 移交房主 | `refresh()` | `broadcastRoster()` |
| 结束房间 | `refresh()` | `broadcastRoster()` |

### 3.3 收端刷新（三个触发点）

1. **收到 `lg.roster`** → `invalidateQueries(['live-room', id])` + `invalidateQueries(['join-requests', id])`（人数、上限、待批数、名册一起更新）；
2. **关键时刻**：`window` 的 `focus` 事件与 `document` 的 `visibilitychange`（变为可见时）；以及连接状态变为 `connected`（进房/重连成功）；
3. **30 秒兜底轮询**：房内页 `setInterval(30_000)`；仅当 `document.visibilityState === 'visible'` 时才真正取，页面不可见则跳过（不浪费请求）。

## 4. ③ 个人信息浮窗（`SideBar`）

```ts
interface Props { user: UserVO; collapsed: boolean; onLogout: () => void }
function SidebarUserCard({ user, collapsed, onLogout }: Props)   // SideBar 内部子组件
```

- **收起态**：只显示头像（保持现状的紧凑）。
- **展开态默认**：一行按钮 `.side-user-btn`（头像 + 名字 + 右上小箭头），**不再直接展示** 邮箱 / id / 注册日期；
- **打开**：`onClick` 切换；`onFocus`（键盘 Tab 进入时）也打开 —— 对应你的「点击或 focus 后才展示」；`aria-haspopup="dialog"`、`aria-expanded`。
- **关闭**：`Esc`、`pointerdown` 落在浮窗与按钮之外、登出。
- **浮窗内容**（`role="dialog"` `aria-label="个人信息"`）：
  1. 头像 + 名字（大字）+ 邮箱（小字）；
  2. `加入于 YYYY/MM/DD`（由 `user.createdAt` 本地化；原「账号 ID」不再展示，改为整个卡片 `title`）；
  3. **哲学语句**：`<blockquote class="side-pop-quote">` + `<cite>作者</cite>`；
  4. 「登出」按钮（沿用既有 logout mutation 与二次确认口径）。
- 浮窗定位：`position: absolute; bottom: calc(100% + 8px); left: 8px; width: 268px`（侧边栏内不溢出；窄屏横向条模式下改为向下弹出，见 §6）。

## 5. ④ 哲学语句池（`data/philosophy.ts`）

```ts
export interface PhilosophyQuote { text: string; author: string }
export const PHILOSOPHY_QUOTES: readonly PhilosophyQuote[]   // 12 条真实语录（中文译句 + 作者）
export function pickDailyQuote(date?: Date): PhilosophyQuote  // 按 UTC+8 的「年内第几天」取模；同日稳定、跨天变化
```

- **只收真实语录**（可查证的哲学/思想名句，附作者），不写自造句子；池子是本仓唯一来源，替换只改这一个文件。
- 「每日一句」而非「每次随机」：同日多端/多次打开看到同一句（可复现、可截图取证），跨天才变。

### 5.1 铺开与替换（cp-6 起，cp-7 按 redirect-02 批复定稿）

组件 `components/QuoteLine.tsx`（`<QuoteLine scene="…" />`）：衬线小字 + 作者 + 左侧细线。

**口径（2026-09-19 批复）**：**替换**引导性解释文字（引导改由视觉与操作入口承担）；保留状态事实与功能文案；短语按**场景**取、**每次进入随机**；只写作者。

| 场景 | 标签组 | 用在哪 |
| --- | --- | --- |
| `hero` | 求知 + 自省 + 诗意 | 首页主视觉 |
| `learn` | 求知 + 科学 | 登录页 / 注册页 / 新建房间页 |
| `patience` | 耐心 | 等待页（待批、读取中） |
| `meet` | 相遇 + 求知 | 空房间 / 空消息 / 空成员 / 交流页空态 |
| `self` | 自省 | 侧边栏未登录、需登录空态、筛选空态、个人信息浮窗 |
| `farewell` | 告别 + 诗意 | 404 页、被拒/撤回的等待页 |

池子 46 条、标签 7 组（求知/科学/耐心/相遇/自省/诗意/告别）；`pickQuote(scene, random?)` 纯函数便于用例固定取值；
`QuoteLine` 在挂载时取一次 —— 每次进入页面换新（实测首页连刷 8 次得 8 种）。

**替换清单**（A 段，共 11 处）：首页 hero 副标题段 · 首页未登录空态说明 · 首页与筛选空态的引导句 · 「我的房间」需登录说明 · 侧边栏未登录说明 · 新建房间页房主职责说明 · 等待页两条操作引导 · 登录页抒情段 · 注册页抒情段 · 404 页说明（并删掉内部话）。

**视觉/操作引导代偿**（E12）：首页空态就地主按钮「创建房间」；「请先登录」保留「去登录」；筛选空态保留「清空筛选」；等待页进度由 `WaitTimeline` 承担；顶栏保留登录入口；404 保留「回房间列表」。

## 6. ⑤ 图版初始位置（`global.css`）

```css
:root { --thinker-top: -60px; }      /* 由 -110px 下移 ≈ 容器高 10%（50px）；初始位置 = 未滚动时图版上沿 */
@media (max-width: 900px) { .hero { --thinker-top: -46px; } }   /* 窄屏由 -92px 同比例下移 */
```

- 下移只改「容器顶」这一个锚点；容器底仍锚在「创建房间」行上方（`--thinker-gap`），因此**可滑动行程自动缩短**，图版依旧不出容器（`overflow: clip`）。
- 单点可调：只改这两个数即可继续微调；`AMPLITUDE` 仍在 `ThinkerStatue.tsx`。

## 7. 验收映射

| 验收 | 证据 |
| --- | --- |
| E1/E2 | 双浏览器（A/B 各一变向）读 `.live-tile` 的麦徽标节点 + `participant.isMicrophoneEnabled` 对照 |
| E3/E4/E5 | A 端界面批准 → 计时读 B 端状态条与门牌徽标；E5 用「不广播」注入后等 30 秒兜底 |
| E6/E7 | 真机开合 + 关键属性断言 + 语录在同一日期两次读取一致 |
| E8 | 同视口、同滚动位置下 `getBoundingClientRect().top` 的前后对比（差 ≈ +50px）+ 截图 |
| E9 | `git grep` 计数 `alert/confirm` = 0；`toolbar.top ≤ 视口高` |
| E10 | 四条门禁命令 |

## 8. 非目标

- 后端零改动（无接口、无迁移）；成员抽屉不加麦标；状态条不加在场数；不做「静音他人」这类服务端权限能力；不改 LiveKit 承载参数。

## 9. 变更记录

| 日期 | 版本 | 改了什么 | 依据 |
| --- | --- | --- | --- |
| 2026-09-19 | cp-0 | 建页：五面函数级设计 + 事件流 + 语录口径 + 验收映射 | 你的批复 Q1~Q7 + 三项前端优化 |
