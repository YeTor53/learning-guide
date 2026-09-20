---
title: r012 审查报告（骨架，cp-7 定稿）
description: r012 的验收逐条对账、规则核对、覆盖矩阵对账、视觉对账五组、重定向对账与两栏处置清单；cp-1 建骨架。
type: reference
status: draft
owner: 陀梓皓
updated: 2026-09-20
---

<!-- overview -->
本页 cp-1 只立**表头与判据位**（防止「先实现、事后补理由」）；cp-7 按实测逐格填，未取证一律写「未取证 + 原因」，禁空口「已实现」。
审查两轴：模块轴（设计页/模块页/使用者教学页/开发者教学页）+ 轮次轴（本目录 design/changes/review/CR/redirect）。

## 1. 验收逐条对账（E1~E12）

| # | 条目 | 实现位置 | 证据（命令输出 / 用例名 / 截图） | 结论 |
| --- | --- | --- | --- | --- |
| E1 | 超管身份落地 | 待填 | 待填 | 待填 |
| E2 | 隐身进房 | 待填 | 待填 | 待填 |
| E3 | 房主能力 | 待填 | 待填 | 待填 |
| E4 | 不计入人数 | 待填 | 待填 | 待填 |
| E5 | 管理后台三列表 | 待填 | 待填 | 待填 |
| E6 | 管理后台动作 + 审计 | 待填 | 待填 | 待填 |
| E7 | 大屏聊天（500 字 / 限流 / 落库） | 待填 | 待填 | 待填 |
| E8 | SSE 通道与兜底 | 待填 | 待填 | 待填 |
| E9 | 管理动作留痕 | 待填 | 待填 | 待填 |
| E10 | 超管音频不进转写 | 待填 | 待填 | 待填 |
| E11 | 门禁与视觉对账 | 待填 | 待填 | 待填 |
| E12 | 文档 = 代码 | 待填 | 待填 | 待填 |

## 2. 规则核对（AGENTS.md / docs/04-style/）

| 项 | 结论 | 证据 |
| --- | --- | --- |
| 未获批准的规划不做实现 | 待填 | 本页 cp-1 至用户批准前无代码提交 |
| 一次提交 = 一个逻辑增量、`[Req: r012]` | 待填 | git log |
| `git add` 只写具体路径 | 待填 | — |
| 密钥不入库 / Secret 不进前端产物 | 待填 | `git grep -nE "API_SECRET|API_KEY" -- backend/app frontend/src` |
| 未新增依赖 | 待填 | `git diff --stat package.json requirements*.txt` |
| 界面硬条款（单一图标库 / 零 emoji / 禁内部词） | 待填 | 令牌与 emoji 扫描命令输出 |

## 3. 覆盖矩阵对账（无 `planned` 残留）

| 件套 | 路径 | 状态 |
| --- | --- | --- |
| 需求单 | `docs/00-requirements/r012-superadmin-console.md` | 本轮 |
| 设计页 | `docs/rounds/r012-superadmin-console/design.md` | 本轮 |
| 模块·实现页 | `docs/02-modules/r012-superadmin-console.md` | planned |
| 模块·功能页 | `docs/02-modules/r012-superadmin-console-features.md` | planned |
| 使用者教学页 | `docs/tutorials/r012-admin-and-global-chat.md` | planned |
| 开发者教学页 | `docs/tutorials/r012-superadmin-dev-guide.md` | planned |
| ADR | `docs/03-decisions/ADR-0024-superadmin-invisible-bypass.md`、`ADR-0025-global-chat-and-sse.md` | planned |

## 4. 视觉对账（五组，缺一不通过）

| 项 | 命令 / 做法 | 实测 | 结论 |
| --- | --- | --- | --- |
| 令牌扫描 | `grep -rnE '#[0-9a-fA-F]{3,8}\|(padding\|margin\|gap\|font-size\|border-radius): *[0-9]+px' frontend/src --include='*.css' --include='*.tsx' \| grep -v global.css` | 待填（目标 0 行） | 待填 |
| 动效实测 | 读 `element.style.transform` / `getComputedStyle` 的过渡时长 | 待填 | 待填 |
| 降级复测 | 模拟 `prefers-reduced-motion: reduce` 后重测 | 待填 | 待填 |
| 截图 | 桌面 1440×900 + 窄屏 375×812 | 待填（`shots/`） | 待填 |
| 零 emoji / 单一图标库 | `grep -rnP '[\x{1F300}-\x{1FAFF}\x{2600}-\x{27BF}]' frontend/src`、`grep -rn 'react-icons\|@heroicons\|fontawesome\|feather' frontend/src` | 待填（目标 0） | 待填 |
| 几何量测 | `document.documentElement.scrollWidth === clientWidth`（后台表格不横向溢出） | 待填 | 待填 |

## 5. 重定向对账（vibecoding 8.1/8.2）

| 消息序号 | 首行回执分类 | 单号 | 单内状态 | 结论 |
| --- | --- | --- | --- | --- |
| 1 | 新轮次设计请求 | —（`redirect-01` 已登记，本 cp-1 出设计） | `redirect-01` status: proposed | 通过（grep `changes.md` 台账） |
| 2 | 澄清回答（W2，答 `ASK-r012-1` Q1~Q18） | —（无需确认单：白名单 W2） | 需求单 §10.1 已落批复 + 原话 | 通过：Q4/Q8 追加口径（只管理不发布音视频）、Q11=2、Q12=2、Q14=2 均已在 design 落地 |

## 6. 给用户处置的两栏（审查时填）

**本轮已落地可保留的增量**（各带 SHA 与文档页）：待 cp-7 填。

**未闭合 CR / 半成品清单**（含「若判为 C/D 如何处置」）：待 cp-7 填。

## 7. 合并指引（人执行）

1. 先合 r011（若尚未合）：`git checkout main && git merge --no-ff req/r011-debt-backfill`。
2. 再合 r012：`git merge --no-ff req/r012-superadmin-console`；打 tag `round-r012-done`。
3. 合并后复跑门禁四项，把数字回填本页 §1 与 `changes.md` §3。

## 8. 变更记录

| 日期 | 版本 | 改了什么 | 依据 |
| --- | --- | --- | --- |
| 2026-09-20 | 骨架（cp-1） | 建页：验收对账表 + 规则核对 + 矩阵对账 + 视觉五组 + 重定向对账 + 两栏位 + 合并指引 | 需求单 §4/§8；vibecoding 阶段 3 |
