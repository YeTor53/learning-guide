---
title: 术语表
description: 本项目的统一叫法，文档与代码都用这里的词。
type: reference
status: draft
owner: 陀梓皓
updated: 2026-09-16
---

<!-- overview -->
统一术语，避免同一件事在文档、代码、对话里三种叫法。

| 术语 | 含义 |
| --- | --- |
| 学习主题（topic） | 房间绑定的学习方向，如伊壁鸠鲁主义、数理生物学、德国史模拟 |
| 房间（room） | 一次讨论的容器，绑定一个主题，有标题与简介，单房间上限 8 人 |
| 等候室（waiting room） | 进入正式讨论前的审批环节：申请人提交申请，房主批准后才进入 |
| 加入申请（join request） | 某人申请进入某房间的记录，状态为待批 / 已批准 / 已拒绝 |
| 角色（role） | Host（房主）、Moderator（协管）、Participant（成员）三种 |
| 举手（hand raise） | 参与者举手示意，实时同步、列表展示（如 `David ✋`），协管/房主可替他人放下 |
| 焦点发言（focus speaker） | 房主/协管指定的重点发言人，其画面放大；取消后恢复 |
| 邀请（invite） | 限时邀请链接或房间码，带过期时间 |
| 踢人（kick） | 服务端通过 LiveKit Server API / Room Service 移除参与者并强制断开 |
| 纪要（summary） | 房间结束后生成的讨论纪要，入库存于 `session_summaries`，房间详情页可查看 |
| 冒烟脚本（smoke） | 一条命令跑通「创建用户 → 建房 → 签发 Token → 写聊天 → 生成纪要」的验证脚本 |
