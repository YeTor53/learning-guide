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
| E1 | `components/live/ParticipantTile.tsx` | 待测 | planned |
| E2 | 同上（不依赖摄像头） | 待测 | planned |
| E3 | `hooks/useDataChannel.ts` + `pages/RoomLivePage.tsx` | 待测 | planned |
| E4 | 同上（门牌徽标同批） | 待测 | planned |
| E5 | 30 秒兜底轮询（注入：不广播） | 待测 | planned |
| E6 | `components/SideBar.tsx` | 待测 | planned |
| E7 | `data/philosophy.ts` | 待测（+ 人工看文案） | planned |
| E8 | `styles/global.css`（`--thinker-top`） | 待测（DOM 量测 + 截图） | planned |
| E9 | 全仓静态扫描 + `toolbar.top` | 待测 | planned |
| E10 | 四条门禁 | 待测 | planned |

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

## 3~6. 规则/文档/视觉对账 + 两栏清单 + 合并指引

> cp-5 定稿时补齐（合并命令：`git checkout main && git merge --no-ff req/r006-ui-sync-polish && git tag -a round-r006-done -m "..."`）。
