---
title: r001-ADR-0008 视觉体系：Lucide 图标、禁 emoji、Awwwards 级动效与排版
description: 用户 2026-09-17 指定的设计标准（对标 Awwwards/FWA/CSS Design Awards 每日最佳）与执行边界：图标库、禁 emoji、动效与可达性。
type: adr
status: accepted
owner: 陀梓皓
updated: 2026-09-17
---

## 背景

用户 2026-09-17 指定前端设计标准：

> 统一使用 Lucide 图标，界面全程禁止使用表情符号；对标 Awwwards 顶级网站水准（Awwwards / FWA / CSS Design Awards 每日最佳同等品质）；把浏览器视作交互式艺术画布，追求先锋视觉、实验性排版、流畅物理动效与冲击力强的文字版式；融合代码与渲染逻辑，做出突破常规的沉浸式体验。

原 r001 风格指南只写「不引 UI 框架、单文件 CSS、控制体量与风格争议」，与上述标准不匹配。

## 决策

1. **图标**：全站统一 `lucide-react`（唯一图标来源）；**界面代码中禁止任何 emoji**（含按钮、状态、空态、提示、加载），状态与动作一律用图标 + 文字表达。
2. **设计语言**：暗色编辑风（ink/paper 对比）+ 单一强调色 + 细网格与噪点质感；排版以**大字号显示体 + 紧字距 + 混排衬线斜体**制造冲击力，正文保持高可读性。
3. **动效**：字块逐字入场、卡片指针跟随聚光与轻微倾斜、列表阶梯入场、数字/状态切换的弹性过渡、路由切换（View Transitions API，能力探测后渐进增强）；统一动效令牌（时长 120/240/420ms，缓动 `cubic-bezier(.2,.8,.2,1)`）。
4. **渲染逻辑**：首页 hero 之后叠一层 Canvas 流场背景（2D，无第三方依赖，`devicePixelRatio` 适配，页面不可见时暂停），作为「代码即画面」的落地；不使用 WebGL/3D 库，控制体积与离线可用性。
5. **可达性与性能边界（不可突破）**：尊重 `prefers-reduced-motion`（关闭位移/流转动效，仅保留淡入）；键盘可见焦点环不裁掉；不做自定义鼠标指针（会伤可用性）；首屏 JS 体积不因动效显著增加（不引动画库）。
6. **字体**：不引外部 webfont（本机证书库损坏 + 离线演示要求），用系统字体栈（`Segoe UI Variable` / `-apple-system` / 思源黑体回退）+ 可变字重、字距、行高与字号对比来达成版式张力。

## 被否的替代方案

| 方案 | 为什么否掉 |
| --- | --- |
| 引入 Tailwind / UI 组件库 | 与「单文件 CSS、控制体量」的原风格约定冲突；且会掩盖版式细节 |
| 引入 Framer Motion / GSAP 做动效 | 首屏体积与依赖面明显上升；本项目动效可用 CSS + 少量 rAF 达成 |
| 引入 three.js / WebGL 场景 | 体积大、离线与老旧集显风险高；2D Canvas 已能满足「渲染即画面」的诉求 |
| 自定义鼠标指针 / 隐藏滚动条 | Awwwards 常见但伤可用性，与 §5 的可达性边界冲突 |
| 下载 webfont 自托管 | 本机取字体的网络与证书风险高，离线演示不可靠 |

## 影响与待办

- 新增前端依赖 `lucide-react`（登记在需求单 §2 影响面）。
- 重写 `docs/04-style/global-style.md` 为设计规范（色板 / 排版 / 间距 / 动效令牌 / 图标 / 禁 emoji / 可达性）。
- 代码：`frontend/src/styles/global.css` 重写为设计系统；组件层用 Lucide 图标替换全部 emoji；新增 `frontend/src/components/FlowField.tsx`（Canvas 背景）。
- 验收：`npx tsc --noEmit` + `npm run build` 全绿；浏览器实测（demo 形态）截图核对；`grep` 确认界面代码零 emoji；`prefers-reduced-motion` 下动效降级可用。
