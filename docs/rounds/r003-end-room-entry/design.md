---
title: r003 设计：房主结束房间入口（+ r002 收官回填）
description: r003 的契约面清单、逐文件函数级改动、视觉与教学契约、覆盖矩阵落地方式与回退方案（阶段 1，待批后才动代码）。
type: concept
status: draft
owner: 陀梓皓
updated: 2026-09-19
---

<!-- overview -->
本页是 r003 的设计方案（怎么做）。需求与验收见 `docs/00-requirements/r003-end-room-entry.md`；来由与定级见 `docs/rounds/r002-livekit/redirect-07.md`（confirmed-A，L3）。**未获「按设计做」不写代码。**

## 1. 本轮两个增量（顺序不可换）

1. `cp-r003-1` **r002 收官回填**（纯文档）：上一轮欠的文档债先还 —— 见 §5。
2. `cp-r003-2` **房主结束房间入口**（代码 + 文档同提交）：见 §2~§4。
3. `cp-r003-3` **取证与收官**：真机双端复看 + 教学页实跑 + 审查报告。

## 2. 契约面清单（CR 定级基准物）

| 面 | 本轮是否变 | 具体 |
| --- | --- | --- |
| 对外可见面（界面元素） | **变（L3）** | 交流页控制坞离场组：房主位置 `离开`（disabled）→ `结束房间`（可点、危险色）；新增自绘确认框；非房主不变 |
| 对外可见面（命令/接口/配置） | 不变 | 复用 `POST /api/rooms/{room_id}/end`（r001 起存在）；不新增接口、不新增 `.env` 键 |
| 数据模型 | 不变 | 无 schema 变更、无迁移；库侧连带动作复用 r001 `end_room` |
| 模块边界与依赖 | 不变 | 前端 2 文件 + 1 样式表；后端 0；无新增依赖 |
| 验收标准与示范动作 | **变（L3）** | 示范动作由「抽屉里点结束房间」改为「控制坞点结束房间」；其余验收沿用 r002 |
| 回退方案 | 变更 | `git revert` cp-r003-2 的提交即可（无迁移、无数据变更、无外部配置），回退后回到 r002 现状 |
| 视觉契约 | 变 | 新 class `.live-ctrl-end` + 两个令牌 `--live-end-border` / `--live-end-hover`（见 §3.3） |

## 3. 逐文件改动（到函数级）

### 3.1 `frontend/src/components/live/DeviceBar.tsx`（修改）

**Props 变化**（新增 4 项；`onRequestLeave` 三件套保留给非房主）：

```ts
/** 是否房主：房主的离场按钮改为「结束房间」（可点、危险色、二次确认）。 */
isHost: boolean                                  // 保留，语义改为「显示结束房间」
/** 房主结束房间的确认态（由父组件持有，便于 Esc 取消）。 */
confirmingEnd: boolean                           // 新增
onRequestEnd: () => void                         // 新增
onConfirmEnd: () => void                         // 新增
onCancelEnd: () => void                          // 新增
```

**渲染分支**（`return` 内离场组 `live-dock-group`，现 L104-126）：

```tsx
{isHost ? (
  confirmingEnd ? (
    <div className="live-dock-confirm" role="dialog" aria-modal="false" aria-label="确认结束房间">
      <span className="live-ctrl-text">
        结束这个房间？所有人将被移出、需重新申请才能进；房间转为只读，历史仍可查。
      </span>
      <button className="btn btn-danger btn-sm" onClick={onConfirmEnd}>结束房间</button>
      <button className="btn btn-ghost btn-sm" onClick={onCancelEnd}>取消（Esc）</button>
    </div>
  ) : (
    <button
      className="live-ctrl live-ctrl-end"
      onClick={onRequestEnd}
      disabled={disabled}
      title="结束房间：所有人被移出、房间转为只读（不绑定快捷键）"
    >
      <PhoneOff {...ICON} />
      <span className="live-ctrl-text">结束房间</span>
    </button>
  )
) : confirmingLeave ? (
  /* 现有「确认离开」分支，原样保留 */
) : (
  /* 现有「离开」按钮，原样保留 */
)}
```

**职责**：只做呈现与回调，不持有结束逻辑、不发请求（与现有 `onRequestLeave` 同构）。
**import 增**：`PhoneOff`（来自 `lucide-react`，与现有 `DoorOpen` 同一处）。
**不变**：快捷键 `M` / `V` 不涉及离场；`disabled` 语义（重连中禁用）沿用。

### 3.2 `frontend/src/pages/RoomLivePage.tsx`（修改）

**新增状态**：`const [confirmingEnd, setConfirmingEnd] = useState(false)`

**Esc 链**（现 L131-141）：插入一级，顺序为「先取消最近的破坏性确认」：

```ts
if (confirmingLeave) setConfirmingLeave(false)
else if (confirmingEnd) setConfirmingEnd(false)      // 新增
else if (confirmingBack) setConfirmingBack(false)
else if (drawerOpen) setDrawerOpen(false)
```

依赖数组同步加 `confirmingEnd`。

**新增处理器 `doEnd`**（放在 `doLeave` 之后）：

```ts
/** 房主结束房间：成功后断开并回列表；失败保留连接与房间状态，只给提示。 */
const doEnd = async () => {
  setConfirmingEnd(false)
  try {
    await roomsApi.end(id)                 // POST /api/rooms/{id}/end（r001 起存在）
    await connection.disconnect()
    navigate('/')                          // 列表页该卡片显示「已结束」
  } catch (error) {
    setNotice(error instanceof ApiError ? error.message : '操作失败，请重试')
  }
}
```

**职责边界**：`doEnd` 只做「一次请求 + 成功后的离场 + 失败提示」；权限、库侧连带动作、LiveKit 房间删除全在后端（零改动）。
**保留不变**：`doLeave` 的房主分支（L200-203）作为其他路径的兜底；`refresh()` 逻辑不动。

**DeviceBar 调用处**（现 L424-437）追加 4 个 props：`confirmingEnd` / `onRequestEnd` / `onConfirmEnd` / `onCancelEnd`（回调分别 `setConfirmingEnd(true)` / `void doEnd()` / `setConfirmingEnd(false)`）。

### 3.3 `frontend/src/styles/global.css`（修改）

**新增令牌**（放在 `:root` 的 live 段，现 L590 附近，单点可调）：

```css
--live-end-border: rgba(255, 107, 107, 0.55);  /* 结束房间按钮描边 */
--live-end-hover:  rgba(255, 107, 107, 0.18);  /* hover 底色 */
```

**新增 class**（紧跟现有 `.live-ctrl-leave`，现 L958-959）：

```css
/* 房主唯一的危险动作：比「离开」更强的描边与对比，仍不做填充（避免引诱误点） */
.live-ctrl-end { color: #ffd0d0; border-color: var(--live-end-border); }
.live-ctrl-end:hover:not(:disabled) { background: var(--live-end-hover); color: #fff; }
```

不新增动效（沿用 `.live-ctrl` 的 `--t-fast` 过渡）。

### 3.4 不动的文件（明确登记，避免审查时误判为漏改）

- `backend/**`：0 改动（`routers/rooms.py:119` / `services/rooms.py:397` 原样复用）。
- `frontend/src/components/live/RoomSidePanel.tsx`：不加第二入口（口径 Q1）。
- `frontend/src/api/rooms.ts`：`roomsApi.end` 已在（L145），不改。

## 4. 视觉契约（frontend-visual-gate 口径）

| 项 | 取值 | 可调点 |
| --- | --- | --- |
| 图标 | Lucide `PhoneOff`（`size=18`、`strokeWidth=1.75`，与其余控制项一致） | `DeviceBar.tsx` 一处 import + 一处标签；备选 `CircleStop` |
| 色彩 | 复用 `--danger`（`#ff6b6b`）族；新增 `--live-end-border` / `--live-end-hover` | `global.css` `:root` 两行 |
| 版式 | 与「离开」同尺寸同位置（控制坞右端、分隔线右侧），只提对比不提体积 | `DeviceBar.tsx` 离场组、`.live-ctrl-end` |
| 动效 | 无新增；hover 过渡沿用既有令牌 | — |
| 硬条款 | 零 emoji；单一图标库 Lucide；文案禁内部词；**不用原生弹窗** | 阶段 3 视觉对账（扫描 + 截图） |
| 界面口径 | 风格基调、用户群、参考物沿用 r002 交流页（专注感 / 暗色 / Awwwards 级）；本轮不引入新风格 | 无 |

## 5. r002 收官回填（cp-r003-1）怎么做

纯文档增量，逐项对照实测，不引入新结论：

| 动作 | 文件 | 内容 |
| --- | --- | --- |
| 审查报告定稿 | `docs/rounds/r002-livekit/review.md` | §1 验收对账按实测填（`pytest 95 passed` / `smoke 22-22` / `tsc` / `build` / 四项浏览器实测 / 未做项）；§2 规则核对；§3 两轴文档对账；§4 口径对账；§5 CR 与重定向对账（含 redirect-03 悬空、redirect-02 G2/G3 待批）；§6 两栏处置清单；§7 合并指引标「已由人执行（`7f2e994` + tag `round-r002-done`）」 |
| 需求单转状态 | `docs/00-requirements/r002-livekit-room.md` | `status: draft` → `closed`；变更记录补一行「收官（2026-09-18）＋本轮回填（2026-09-19）」 |
| 索引表 | `docs/00-requirements/README.md` | r002 行：`closed` + 完成 tag `round-r002-done`（`main` = `b8783d2`）；r001 行的 `main` SHA 也改为当前实测值 |
| roadmap 矛盾 | `docs/00-project/global-roadmap.md` | §3 M2 回填注改为「已完成」；§7 第 2/3 条改为「r002 已收官，下一轮 = M3」；§9 台账新增「房主缺结束房间入口」一行并标「已由 r003 闭合（redirect-07）」 |
| 清理 | `docs/99-archive/end_room` | 删除 0 字节空文件 |

## 6. 教学契约（人可见的使用面）

- **场景一句话**：讨论到点后，房主在房间底部控制坞点「结束房间」，这场讨论正式收尾 —— 所有人被移出，房间转为只读。
- **入口 / 命令名**：交流页 `/rooms/:id/live` → 控制坞右侧「结束房间」（**仅房主**可见；其他人看到的是「离开」）。
- **输入**：一次点击 + 二次确认（`Esc` 可取消）。
- **输出**：房间 `status=ended`；成员 `inactive/room_ended`；待批申请 `cancelled`；LiveKit 房间被删除（`livekitApplied`）；所有端断开并显示「房间已结束，仅可查看历史内容」；房主回到房间列表。
- **一次典型使用动作（=验收示范）**：房主点「结束房间」→ 确认 → 自己回到列表看到「已结束」；另一浏览器 3 秒内断开。
- **开发者视角要改哪里**：`DeviceBar.tsx`（按钮与确认态）、`RoomLivePage.tsx`（`doEnd` + Esc 链）、`global.css`（两个令牌 + 一个 class）。
- **扩展点（预埋）**：① 若要在抽屉加第二入口 → 给 `RoomSidePanel` 加 `onEnd`，复用同一个 `doEnd`；② 若要「结束后留在只读页」→ 只改 `doEnd` 末尾的 `navigate` 目标一行；③ 若图标要换 → 一处 import + 一处标签。

## 7. 覆盖矩阵落地方式（每格何时由 planned 变 landed）

| 页面 | 何时写 | 谁承载事实 |
| --- | --- | --- |
| 需求单 / design / 索引表 | 阶段 1（本提交） | 本轮方案与验收 |
| `r002-livekit-features.md`（§4.2 按钮矩阵 / §4.5 条④ / §4.9 / §6 第 10 步） | cp-r003-2（与代码同提交） | 交互入口与按钮事实 |
| `r002-livekit.md` 变更记录 | cp-r003-2 | 实现事实与文件清单 |
| `global-style.md` 令牌表 + §12.1 | cp-r003-2 | 视觉事实 |
| `tutorials/r002-livekit-demo.md` 第 9 步 / `setup.md` 第 11 行 | cp-r003-3（跑通后写） | 使用者教学（实跑输出为准） |
| `rounds/r003-end-room-entry/{changes,review}.md` | cp-r003-3 | 本轮过程与决策 |

## 8. 风险与对策

| 风险 | 对策 |
| --- | --- |
| 结束接口失败（Cloud 不可达 / 网络） | 库侧仍 `ended`（ADR-0011 条 5）；前端按错误码给提示且**不断开**，避免「人在房间但房间已结束」的假象 |
| 误触 | 二次确认 + `Esc` 可取消 + 不绑快捷键 + 只有房主可见 |
| 真机取证需要你的 dev 服务与账号 | 我不另起端口、不反复 build；验收时用你开着的 `5173` + `8000` 与两个演示账号 |
| 文档夹带 | r002 回填只写实测事实，不引入新结论；不把 M3/M4 内容塞进来 |

## 9. 本轮设计变更记录

| 日期 | CR | 级别 | 摘要 | 结论 |
| --- | --- | --- | --- | --- |
| （实现期追加） | | | | |
