---
title: r001 轮次档案 · 增量清单
description: r001 的逐增量提交与验证证据（按 checkpoint 排列）。
type: reference
status: closed
owner: 陀梓皓
updated: 2026-09-18
---

<!-- overview -->
分支 `req/r001-skeleton`；每行 = 一个逻辑增量，提交与 tag 以 `git log` / `git tag` 实际输出为准。

| # | 增量 | 主要文件 | 验证证据 |
| --- | --- | --- | --- |
| cp-r001-1 | 骨架与数据层：迁移 / 种子 / 连接池 / 配置 / 信封 / 错误码 | `backend/app/**`、`backend/scripts/db_init.py` | `db_init` 打印 7 表行数；`pytest` 18 passed |
| cp-r001-2 | 账户：scrypt 口令 + 签名 Cookie + 注册 / 登录 / 登出 / me | `backend/app/{security,services/auth.py,api/routers/auth.py}` | `pytest` 37 passed（含 401 / 409） |
| cp-r001-3 | 房间与申请：建房 / 列表 / 详情 / 申请 / 批准 / 拒绝 / 离开 / 结束 | `backend/app/{repositories,services,schemas,api/routers}/rooms*` | `pytest` 68 passed（含并发抢名额） |
| 撤回与严格 0 | 补 `POST /api/join-requests/{id}/withdraw`；`pendingCount` 对非管理者服务端返回 0 | 同上 | `pytest` 72 passed |
| cp-r001-4 | 前端 5 页 + 冒烟脚本 + README「怎么跑」 | `frontend/src/**`、`backend/scripts/smoke.py` | `tsc` + `build` 全绿；`smoke.py` PASS 22/22 |
| cp-r001-5 | 左侧边栏 + 视觉体系（Lucide、禁 emoji、Canvas 流场、动效令牌） | `components/SideBar.tsx`、`FlowField.tsx`、`styles/global.css` | 浏览器实测；界面零 emoji（自检） |
| cp-r001-6 | 修 401 被误报为「连不上后端」；登录入口回右上角、个人信息移左下；错误三分流 | `NavBar.tsx`、`SideBar.tsx`、`RoomsPage.tsx`、`RoomDetailPage.tsx` | dev 环境实测（`hasLoginPanel=true`、`hasBackendErr=false`） |
| cp-r001-7 | 界面 / README / docs 去「题目 / 考核 / 轮次」内部词汇 + 文案规范 | 前端文案、`README.md`、docs 11 个文件 | 浏览器断言零命中（唯一命中是房间码字符串） |
| cp-r001-8 | 首屏《思想者》图版 + ADR-0010 与图像资产规范 | `components/ThinkerStatue.tsx`、`public/thinker.webp` | 实测加载 780×949；视差数值核对 |
| cp-r001-9~12 | 图版镜像 + 放大 25%；位移改为固定容器内滑动（容器底锚到「创建房间」行上方 20px，行程 188px，幅度 0.35 单点可调） | 同上 + `global.css` 参数区 | 逐次实测：容器顶 -9、高 628、空隙 20、`scrollY×0.35` 位移、无横向溢出 |
| cp-r001-13 | 轮次关闭：需求单转 closed；轮次档案与索引补齐；最后 2 项人工验收以浏览器实操补齐 | `docs/**` | 需求单 §3.1 的 E9 / E10 |

**说明**：图版位移的四次修订过程与「怎样都不会动」的两个根因（页面缺最小高度导致窗口够高时不滚动；`prefers-reduced-motion` 曾完全跳过绑定）记在 ADR-0010 修订记录与 `docs/04-style/global-style.md` §11。
