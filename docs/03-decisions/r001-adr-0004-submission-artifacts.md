---
title: r001-ADR-0004 提交物形态变更：加 GitHub 远程仓库与 npm 包
description: 用户 2026-09-17 指示提交方式在 zip 之外增加 GitHub 远程仓库与 npm 发布；细则待 P11 拍板。
type: adr
status: proposed
owner: 陀梓皓
updated: 2026-09-17
---

<!-- overview -->
原 P8（2026-09-16 拍板）为"仅 zip、不建远端仓库"。2026-09-17 用户改为：**提交方式会加远程仓库 + GitHub + npm**。本 ADR 记录改动、本机实测前提与待定细则（P11），未拍板前不建远端、不发包。

## 背景

- 题面交付物写的是「源代码或 Git 仓库链接」，因此 GitHub 链接本身合规；`zip` 命名口径（`AI管培生_陀梓皓_题目A_<日期>.zip`）仍是硬要求。
- npm 发布超出题面必做范围，属额外展示项，须明确"发布什么"，否则会挤占 16 小时预算（ADR-0002 已把栈改为 React + Python）。

## 本机实测前提（2026-09-17）

| 项 | 实测结果 | 影响 |
| --- | --- | --- |
| `gh` CLI | 未安装 | 建远端/推送可纯 `git` 完成，非阻塞；要 PR/Release 自动化再装 |
| 仓库远端 | 当前无 remote | 需新建 GitHub 仓库并 `git remote add` |
| Windows 凭据管理器 | 未发现 github 条目记录 | GitHub 推送凭据是否可用需**实地推一次**验证（本机系统证书库曾损坏，HTTPS 推送需留意） |
| npm 登录态 | `npm whoami --registry=https://registry.npmjs.org/` → **401**（配置里有 `_authToken` 但已失效） | **发包前必须重新登录/换 token**，否则 publish 必失败 |
| npm 默认源 | `registry.npmmirror.com` | 安装走镜像可以；**发布必须显式指 `registry.npmjs.org`** |
| 候选包名 | `learningguide-livekit`、`learning-guide-livekit`、`lg-discussion-room`、`@yetor53/livekit-study-room` 均**未被占用** | 包名可选，待定 |

## 待定细则（P11）

1. **npm 发布对象**（关键，决定工作量）：
   - ① 把两个自定义 LiveKit 能力（举手 + 焦点发言）抽成可复用包：React hooks + 类型 + 纯函数，主项目以依赖方式引入；
   - ② 只把前端或某个工具函数发成包（价值低）；
   - ③ 不发包，仅"用 npm 管理依赖/脚本"（则 P8 实际未变，仅加 GitHub）。
2. **GitHub 仓库**：公开 / 私有；仓库名（建议 `LearningGuide-LiveKit`）；是否用同一仓库承载全部交付物。
3. **zip 与远端的关系**：zip 仍是主交付、仓库为补充（建议）；或改为"仓库链接为主 + zip 仅存档"。

## 影响

- 公开仓库 ⇒ README 与设计说明要按"对外可读"标准写（本就是交付物），且**密钥禁令升级**：`.env` 永不入库、CI/日志不得回显 Secret。
- 发包 ⇒ 多出 `package.json` 元数据（name/version/license/repository/files/publishConfig）、独立 README、版本与 tag 规范；发布走 `v*` tag 触发或手动 `npm publish`。
- 若最终选 P11-①，主项目的"自定义能力"必须**从包里引入**而非各写一份（否则双源）。

## 后果与待办

- 用户拍板 P11 → 写入 roadmap §4/§5 → 重写 r001 设计页时把"仓库与发包"纳入验证矩阵（如 `npm pack --dry-run`、`npm view <pkg> version` 取证）。
- 发包前先解决 npm 登录（401）；推送前先实测 GitHub 凭据。

## 变更记录

- 2026-09-17 建立（proposed，待拍板 P11）。
