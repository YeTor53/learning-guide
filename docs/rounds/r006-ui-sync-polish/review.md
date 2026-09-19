---
title: r006 审查报告（阶段 3）
description: E1~E10 逐条证据、规则/文档/视觉对账、两栏处置清单与合并指引（待 cp-5 定稿）。
type: reference
status: draft
owner: 陀梓皓
updated: 2026-09-19
---

<!-- overview -->
状态：**骨架**（cp-5 定稿）。需求见 `docs/00-requirements/r006-ui-sync-polish.md`。

## 1. 验收对账

| 条目 | 实现位置 | 证据 | 结论 |
| --- | --- | --- | --- |
| E1 | `ParticipantTile.tsx` + `hooks/useMicStates.ts` | 双浏览器：A 未静音 → 两端无徽标；A 静音 → B 侧出现；取消 → 消失；反向（B 静音 → A 侧出现）同样成立 | **通过** |
| E2 | 同上 | 两人均**未开摄像头**，徽标仍只随麦克风变化（不再挂在 `!showVideo` 上） | **通过** |
| E3 | `hooks/useRosterSync.ts` + `RoomLivePage.tsx` | A 界面批准第三人 → B 端 `2/8 → 3/8` 用时 **0.23 / 0.46 秒**（两次独立复现）；改前 5 秒仍不变、只认 F5 | **通过** |
| E4 | 同上（`['live-room-requests', id]` 同批失效） | B（协管）门牌「待批 1」清空用时 **1.46 秒**（原 5 秒轮询） | **通过** |
| E5 | 30 秒兜底 + 聚焦/可见性触发 | 纯 API 改库（无任何端广播）：**聚焦触发 0.22 秒**；不聚焦时 **30 秒轮询 9.8 秒**（相位决定）拉平到 `4/8` | **通过** |
| E6 | `components/SidebarUserCard.tsx` | 默认无邮箱/id（仅头像+名字，`.side-pop` 不存在、`aria-expanded=false`）；点击展开（`role=dialog`）；键盘 `Shift+Tab` 聚焦自动展开；`Esc`、点外部关闭；窄屏 900×1000 浮窗 `popTop=150/popBottom=399/vh=1000` 在视口内 | **通过** |
| E7 | `content/philosophy.ts` | 12 条真实语录；刷新后同日同句；`cite` = 作者（如「—— 加缪」） | **通过**（+ 人工看文案） |
| E8 | `styles/global.css`（`.hero` 的 `--thinker-top`） | 页顶 `scrollY=0`：图版上沿 **60 → 110px（下移 50px ≈ 图版高 10%）**；竖屏 194 → 240（46px） | **通过** |
| E9 | 静态扫描 + 量测 | 全仓 `alert/confirm` **0 处**；筛选条仍由 r004 cp-3 保证在首屏（本轮未动该区域） | **通过** |
| E10 | 四条门禁 | `pytest` **111 passed** / `smoke` **PASS 40/40** / `tsc --noEmit` exit 0 / `npm run build` exit 0 | **通过** |
| E11 | `components/QuoteLine.tsx` + 8 处插入点 | 首页 hero（庄子）/ 未登录侧边栏（加缪）/ 新建房间页 / 讨论空态（「认识你自己」）/ 成员空态（罗素）各显示不同语句且同日稳定；功能文本全部保留。**如实**：`stage-empty` 仅在没有轨道时才可见 | **通过**（含一条如实说明） |

## 2. 前端优化清点（你提「看一遍前面提的有什么要优化的」）

| 项 | 出处 | 处置 |
| --- | --- | --- |
| 操作反馈用浏览器原生弹窗（8 处，观感掉价） | roadmap §9（你 2026-09-18 提） | **已不复存在**：承载页面 `RoomDetailPage.tsx` 已删（批准/拒绝入口迁到房内抽屉），全仓 `alert/confirm` **0 处**（cp-4 复核并关闭该行） |
| 首页筛选工具栏落在首屏之外 | roadmap §9（你 2026-09-18 提） | **已修**（r004 cp-3：`toolbar.top` 639 → 101），本轮 E9 防回归 |
| 侧边栏「宽小于长」样式出错 | roadmap §9（r004 cp-3 修） | 已修，**仍待你真机复看**（若现象不同发我竖屏截图） |
| 麦克风图标不同步 | 你 2026-09-19 报 | 本轮 cp-1 修（E1/E2） |
| 两端人数/待批显示不一致 | 你 2026-09-19 报 | 本轮 cp-2 修（E3/E4/E5） |
| 「共享中有人说话不夺焦点」未单独实测 | r004 review 遗留 | 本轮 cp-5 补实测 |
| 竖屏横条模式的尺寸未量测 | r004 review 遗留 | 本轮 cp-5 补量测 |
| 举手/焦点/共享进消息列表 | r005 review 遗留 | 不做（如需另开轮次） |
| 服务端强停他人共享 | r004 review 遗留 | 不做（协作式已生效） |

## 3. 规则核对（AGENTS.md）

| 规则 | 核对 | 结论 |
| --- | --- | --- |
| 未批不实现；改动挂 `rNNN` | Q1~Q7 批复回读在需求单 §2；提交信息带 `[Req: r006]` | **通过** |
| 一次提交一个逻辑增量 | cp-0 / cp-1+2 / cp-3+4 / 修正 / cp-6 / cp-5 共 6 个提交 | **通过** |
| 零新依赖、不改端口 | `package.json` 与后端依赖零变化；8000/5173 不变 | **通过** |
| 密钥不入库 | 本轮未引入任何凭据 | **通过** |
| 文档与代码同提交 | 每个 cp 提交都带文档 | **通过** |
| 行为变更记 ADR + 模块变更记录 | 新增 ADR-0017（D1~D4）+ 模块实现页/功能页/台账 | **通过** |
| 后端零改动 | 本轮只动 `frontend/`；唯一后端改动是**用例健壮性**（`test_list_rooms_filters_and_aggregates` 不再依赖数据量） | **通过** |

## 4. 文档对账

| 项 | 结论 |
| --- | --- |
| 模块轴 | 实现页 `02-modules/r006-ui-sync-polish.md`、功能页 `…-features.md`、ADR-0017 | **齐** |
| 轮次轴 | `rounds/r006-ui-sync-polish/{design,changes,review,redirect-01}.md` | **齐**（review 定稿） |
| 索引 | 需求索引行、模块 README、docs/README、roadmap §9 均已回填 | **齐** |

## 5. 视觉对账

| 组 | 方式 | 结果 |
| --- | --- | --- |
| 浮窗 | 真机截图 `sidebar-pop.png` / `narrow-pop.png` | 暗底卡片 + 圆角 + 阴影 + 左细线引文，与既有材质一致 |
| 语录行 | 真机截图 `quotes-*.png` | 衬线小字 + 作者，未抢功能文案层级 |
| 麦徽标 | `B-after-A-mute.png` / `A-after-B-mute.png` | 危险色小图标，位于格子信息条右端，不遮姓名 |
| 图版 | `hero-1440.png` / `hero-780.png` | 下移后仍不出容器、不压内容 |
| 零 emoji / 单一图标库 | 扫描 | 仅 Lucide（`MicOff` / `ChevronUp` / `LogOut`） |
| 动效 | `--t-base` + `prefers-reduced-motion` | 浮窗进出 240ms；降级时 `animation: none` |

## 6. 两栏处置清单

**已落地可保留（提议保留）**

1. 麦徽标改真实麦克风状态（修掉 r002 起「图标挂在摄像头上」的实现偏差），两端秒级一致。
2. `lg.roster` 同步 + 四个刷新触发点：人数由「只认 F5」变成 0.23~0.46 秒；待批徽标 1.46 秒。
3. 个人信息浮窗（点击 / 键盘 focus 展开）+ 每日一句哲学语句；语录池铺到 8 处解释性文案（**只增不替**）。
4. 图版初始位置下移 50px（竖屏 46px），单点令牌可调。
5. 顺手修：`.gitignore` 未锚定 `data/` 吞掉新文件（语录池移出 `src/data/`）；`onFocus` 与 `onClick` 互相抵消；用例不再依赖「本页条数 = total」；补完 r004 竖屏横条量测。

**未闭合项 / 如实说明**

| # | 项 | 状态 |
| --- | --- | --- |
| 1 | 交流页空态（`stage-empty`）那句 | 仅在没有任何轨道时渲染（空态自身性质）；想常驻一句就说一声 |
| 2 | 「共享中有人说话不夺焦点」 | 仍未单独实测（r004 欠账） |
| 3 | r004 E18b（本地 livekit-server 停 8 秒） | 未做；E18c 等你跑 `reconnect-drill.bat` |
| 4 | 演示库数据量 | 房间数已超列表默认页长（20）→ 用例已修；是否 `db_init --reset --seed` 还原仍等你一句话 |
| 5 | 语录池 12 条 | 想加/换只改 `content/philosophy.ts` |

## 7. 合并指引（由人执行）

```bash
git checkout main
git merge --no-ff req/r006-ui-sync-polish
git tag -a round-r006-done -m "r006 完成（界面同步与优化）"
```

合并后复验：`pytest backend/tests -q` → `python backend/scripts/smoke.py` → `cd frontend && npx tsc --noEmit && npm run build`。
