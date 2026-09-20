"""M1 全链路冒烟：走真实 HTTP 把「注册 → 建房 → 申请 → 批准 → 离开 → 再次申请 → 结束房间 → 只读」跑一遍。

用法（先启动后端）：
  python backend/scripts/db_init.py --reset --seed      # 可选：先恢复演示数据
  python -m uvicorn app.main:app --port 8000            # 在 backend/ 下启动
  python backend/scripts/smoke.py --base-url http://127.0.0.1:8000

设计事实源：docs/01-architecture/r001-app-architecture.md §9.6；docs/02-modules/r001-rooms.md §6.8
判据：每步状态码与关键字段符合预期，末尾打印 `PASS n/n`；任一步不符即以非 0 退出。
 r002 补步（2026-09-19）：成员取 Token 200 / 非成员取 Token 403 / 踢人后取 Token 403 / 结束后取 Token 409。
 r012 补步（2026-09-20）：演示超管登录 → 普通账号调管理后台 403 → 超管三列表 200 → 超管取票（隐身/禁发布 claims）→ 大屏发言与读取 → 心跳上报。
注意：① 脚本会向库里写入两个账号与一个房间（每次邮箱随机），跑完可用 db_init --reset --seed 恢复演示数据；
      ② 本脚本要求后端以 `APP_ENV=dev`（默认）运行：`APP_ENV=demo` 时会话 Cookie 带 Secure，脚本客户端不会回传，
         会出现「注册成功但下一步 401」——这是设计如此（演示形态用浏览器访问不受影响）。
"""
from __future__ import annotations

import argparse
import base64
import json
import sys
import uuid
from typing import Any

import httpx

PASSWORD = "smoke-pass-123"
FAILURES: list[str] = []
CHECKS = 0


def check(step: str, condition: bool, detail: str) -> None:
    global CHECKS
    CHECKS += 1
    mark = "OK " if condition else "FAIL"
    print(f"[{mark}] {step} — {detail}")
    if not condition:
        FAILURES.append(step)


def body(response: httpx.Response) -> dict[str, Any]:
    try:
        return response.json()
    except ValueError:
        return {}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Learning Guide 学习讨论室 M1 冒烟")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    args = parser.parse_args(argv)
    base = args.base_url.rstrip("/")

    host = httpx.Client(base_url=base, timeout=15.0)
    guest = httpx.Client(base_url=base, timeout=15.0)
    suffix = uuid.uuid4().hex[:8]

    try:
        health = host.get("/api/auth/me")
        check("后端可达", health.status_code == 200, f"GET /api/auth/me → {health.status_code}")
        if health.status_code != 200:
            print("\n后端没起来？先执行：cd backend && python -m uvicorn app.main:app --port 8000")
            return 1

        # 1) 注册两个账号（注册即登录）
        a = host.post("/api/auth/register", json={"email": f"smoke-a-{suffix}@example.com", "displayName": "冒烟房主", "password": PASSWORD})
        host_id = body(a).get("data", {}).get("user", {}).get("id", "")
        check("注册房主", a.status_code == 201 and bool(host_id), f"→ {a.status_code} user={body(a).get('data', {}).get('user', {}).get('displayName')}")

        b = guest.post("/api/auth/register", json={"email": f"smoke-b-{suffix}@example.com", "displayName": "冒烟申请人", "password": PASSWORD})
        check("注册申请人", b.status_code == 201, f"→ {b.status_code}")

        # 2) 建房
        created = host.post("/api/rooms", json={"topic": "custom", "topicLabel": "冒烟主题", "title": f"冒烟房间 {suffix}", "description": "由 smoke.py 创建"})
        room = body(created).get("data", {})
        check("建房", created.status_code == 201 and room.get("myRole") == "host", f"→ {created.status_code} roomCode={room.get('roomCode')} myRole={room.get('myRole')}")
        room_id = room.get("id", "")
        if not room_id:
            if created.status_code == 401 and a.status_code == 201:
                print(
                    "\n[HINT] 注册成功但后续请求 401：后端跑在 APP_ENV=demo 时，会话 Cookie 带 Secure 属性，"
                    "浏览器对 http://127.0.0.1 视为安全上下文可用，但脚本客户端不会回传。"
                    "请用 APP_ENV=dev（默认）的后端跑本脚本，或改用 https。"
                )
            print("\n建房失败，后面步骤无法继续")
            return 1

        # 3) 列表里能看到
        listed = host.get("/api/rooms", params={"status": "active", "limit": 100})
        ids = [item["id"] for item in body(listed).get("data", {}).get("rooms", [])]
        check("列表含新房间", listed.status_code == 200 and room_id in ids, f"→ {listed.status_code} 命中={room_id in ids}")

        # 4) 申请人提交申请
        req = guest.post(f"/api/rooms/{room_id}/join-requests", json={"message": "冒烟申请"})
        request_id = body(req).get("data", {}).get("id", "")
        check("提交申请", req.status_code == 201 and request_id, f"→ {req.status_code} id={request_id}")
        dup = guest.post(f"/api/rooms/{room_id}/join-requests", json={})
        check("重复申请被拒", dup.status_code == 409 and body(dup).get("error", {}).get("code") == "ALREADY_PENDING", f"→ {dup.status_code} {body(dup).get('error', {}).get('code')}")

        # 5) 房主看申请并批准
        pending = host.get(f"/api/rooms/{room_id}/join-requests", params={"status": "pending"})
        check("房主可见待批申请", pending.status_code == 200 and len(body(pending).get("data", {}).get("requests", [])) == 1, f"→ {pending.status_code} 条数={len(body(pending).get('data', {}).get('requests', []))}")

        approved = host.post(f"/api/join-requests/{request_id}/approve")
        check("批准申请", approved.status_code == 200 and body(approved).get("data", {}).get("member", {}).get("role") == "participant", f"→ {approved.status_code}")

        # 5b) r002：成员取 Token → 200（LiveKit 签发；url/token 由服务端按模式注入）
        tok = guest.post(f"/api/rooms/{room_id}/token")
        tk = body(tok).get("data", {})
        check("成员取 Token → 200", tok.status_code == 200 and bool(tk.get("token")), f"→ {tok.status_code} token长度={len(tk.get('token') or '')}")

        # 5c) r002：非成员取 Token → 403（第三个账号，从未加入；与未登录的 401 区分）
        outsider = httpx.Client(base_url=base, timeout=15.0)
        c = outsider.post("/api/auth/register", json={"email": f"smoke-c-{suffix}@example.com", "displayName": "冒烟路人", "password": PASSWORD})
        c_user_id = body(c).get("data", {}).get("user", {}).get("id", "")
        check("注册路人", c.status_code == 201 and bool(c_user_id), f"→ {c.status_code} id={c_user_id}")
        deny = outsider.post(f"/api/rooms/{room_id}/token")
        check("非成员取 Token → 403", deny.status_code == 403 and body(deny).get("error", {}).get("code") == "NOT_MEMBER", f"→ {deny.status_code} {body(deny).get('error', {}).get('code')}")

        # 5d) r002：路人申请 → 批准 → 房主踢出 → 取 Token 403（同时验证踢人如实回传 LiveKit 结果）
        req_c = outsider.post(f"/api/rooms/{room_id}/join-requests", json={"message": "路人申请"})
        rid_c = body(req_c).get("data", {}).get("id", "")
        host.post(f"/api/join-requests/{rid_c}/approve")
        kicked = host.delete(f"/api/rooms/{room_id}/members/{c_user_id}")
        kick_data = body(kicked).get("data", {})
        check("房主踢人 → 200 且回传 LiveKit 结果", kicked.status_code == 200 and "livekitApplied" in kick_data, f"→ {kicked.status_code} livekitApplied={kick_data.get('livekitApplied')}")
        after_kick = outsider.post(f"/api/rooms/{room_id}/token")
        check("被移出后取 Token → 403", after_kick.status_code == 403, f"→ {after_kick.status_code} {body(after_kick).get('error', {}).get('code')}")
        detail = host.get(f"/api/rooms/{room_id}")
        info = body(detail).get("data", {})
        check("详情成员数=2", detail.status_code == 200 and info.get("room", {}).get("memberCount") == 2, f"→ {detail.status_code} memberCount={info.get('room', {}).get('memberCount')}")
        check("待批数对房主可见为 0", info.get("room", {}).get("pendingCount") == 0, f"pendingCount={info.get('room', {}).get('pendingCount')}")

        # 6) 申请人离开 → 再次申请（留一条 pending，供结束房间时验证 cancelled）
        left = guest.post(f"/api/rooms/{room_id}/leave")
        check("成员离开", left.status_code == 200, f"→ {left.status_code}")
        again = guest.post(f"/api/rooms/{room_id}/join-requests", json={})
        check("离开后可再申请", again.status_code == 201, f"→ {again.status_code}")

        # 7) 非成员看不到申请列表（此处用未登录的新 client 验证 401）
        anonymous = httpx.Client(base_url=base, timeout=15.0)
        anon = anonymous.get(f"/api/rooms/{room_id}/join-requests")
        check("未登录看申请列表 → 401", anon.status_code == 401, f"→ {anon.status_code} {body(anon).get('error', {}).get('code')}")

        # 8) 房主不能直接离开
        host_leave = host.post(f"/api/rooms/{room_id}/leave")
        check("房主拒绝离开", host_leave.status_code == 409 and body(host_leave).get("error", {}).get("code") == "HOST_CANNOT_LEAVE", f"→ {host_leave.status_code} {body(host_leave).get('error', {}).get('code')}")

        # 8b) r004：群聊消息（HTTP 落库 = 唯一真相；ADR-0013）
        sent = host.post(f"/api/rooms/{room_id}/messages", json={"body": "  冒烟：今天先聊这一段  "})
        sent_message = body(sent).get("data", {}).get("message", {})
        check(
            "发消息 → 201 且正文 trim",
            sent.status_code == 201 and sent_message.get("body") == "冒烟：今天先聊这一段",
            f"→ {sent.status_code} body={sent_message.get('body')!r}",
        )
        blank = host.post(f"/api/rooms/{room_id}/messages", json={"body": "   "})
        check("空消息 → 400", blank.status_code == 400, f"→ {blank.status_code} {body(blank).get('error', {}).get('code')}")
        listed = body(host.get(f"/api/rooms/{room_id}/messages?limit=50")).get("data", {}).get("messages", [])
        check("拉消息 → 含刚发的那条", any(item.get("body") == "冒烟：今天先聊这一段" for item in listed), f"→ {len(listed)} 条")

        # 8c) r004：举手（幂等 → 自己放下 → 房主放下他人）
        host.post(f"/api/rooms/{room_id}/hand-raise")
        twice = host.post(f"/api/rooms/{room_id}/hand-raise")
        hands_snapshot = body(twice).get("data", {}).get("hands", [])
        check(
            "举手两次 → 快照仍只有 1 条",
            twice.status_code == 200 and len(hands_snapshot) == 1,
            f"→ {twice.status_code} {len(hands_snapshot)} 条",
        )
        own = host.delete(f"/api/rooms/{room_id}/hand-raise")
        check("自己放下手 → 快照清空", body(own).get("data", {}).get("hands") == [], f"→ {own.status_code}")

        # 8d) r004：焦点（房主指定 → 取消）
        set_focus = host.post(f"/api/rooms/{room_id}/focus", json={"userId": host_id})
        focus_vo = body(set_focus).get("data", {}).get("focus", {})
        check(
            "房主设焦点 → 200 且回传 subject",
            set_focus.status_code == 200 and focus_vo.get("subjectUserId") == host_id,
            f"→ {set_focus.status_code} subject={focus_vo.get('subjectUserId')}",
        )
        clear_focus = host.post(f"/api/rooms/{room_id}/focus", json={"userId": None})
        check(
            "取消焦点 → subject 为空",
            clear_focus.status_code == 200 and body(clear_focus).get("data", {}).get("focus", {}).get("subjectUserId") is None,
            f"→ {clear_focus.status_code}",
        )

        # 8e) r005：容量按**在册成员**（满员 → 第 9 人申请 409 + 系统消息留痕）
        fillers = []
        for i in range(7):  # 房主在册 1 → 填 7 个到满员（此前申请人已离开）
            filler = httpx.Client(base_url=base, timeout=15.0)
            email = f"smoke-fill{i}-{suffix}@example.com"
            reg = filler.post("/api/auth/register", json={"email": email, "displayName": f"冒烟填位{i+1}", "password": PASSWORD})
            assert reg.status_code == 201, reg.text
            req = filler.post(f"/api/rooms/{room_id}/join-requests", json={"message": "填位"})
            assert req.status_code == 201, req.text
            host.post(f"/api/join-requests/{req.json()['data']['id']}/approve")
            fillers.append(filler)
        filled = body(host.get(f"/api/rooms/{room_id}")).get("data", {})
        check(
            "填满到 8 人（在册 = 容量）",
            filled.get("room", {}).get("memberCount") == 8,
            f"→ memberCount={filled.get('room', {}).get('memberCount')} capacity={filled.get('room', {}).get('capacity')}",
        )
        ninth = httpx.Client(base_url=base, timeout=15.0)
        ninth.post("/api/auth/register", json={"email": f"smoke-9th-{suffix}@example.com", "displayName": "冒烟第九人", "password": PASSWORD})
        denied = ninth.post(f"/api/rooms/{room_id}/join-requests", json={"message": "还有位吗"})
        check(
            "满员时第 9 人申请 → 409 ROOM_FULL",
            denied.status_code == 409 and body(denied).get("error", {}).get("code") == "ROOM_FULL",
            f"→ {denied.status_code} {body(denied).get('error', {}).get('code')}",
        )
        events = [m["body"] for m in body(host.get(f"/api/rooms/{room_id}/messages?limit=80")).get("data", {}).get("messages", []) if m.get("kind") == "system"]
        check(
            "满员拒绝留痕（系统消息）",
            any("房间已满" in e for e in events),
            f"→ 系统消息 {len(events)} 条，含满员拒绝={'房间已满' in '|'.join(events)}",
        )
        check(
            "满员时待批申请被自动拒绝留痕（r011）",
            any("自动拒绝" in e for e in events),
            f"→ 系统消息 {len(events)} 条，含自动拒绝={'自动拒绝' in '|'.join(events)}",
        )
        check(
            "加入/离开/被移出也留痕",
            any("加入了房间" in e for e in events) and any("离开了房间" in e for e in events) and any("被移出房间" in e for e in events),
            f"→ 样例 {events[:3]}",
        )

        # 9) 结束房间
        ended = host.post(f"/api/rooms/{room_id}/end")
        check("结束房间", ended.status_code == 200 and body(ended).get("data", {}).get("status") == "ended", f"→ {ended.status_code} status={body(ended).get('data', {}).get('status')}")

        after = body(host.get(f"/api/rooms/{room_id}")).get("data", {})
        members = after.get("members", [])
        statuses = {m["displayName"]: (m["status"], m["exitReason"]) for m in members}
        check("成员全部 inactive", all(s == "inactive" for s, _ in statuses.values()), f"{statuses}")
        check("房主退出原因=room_ended", statuses.get("冒烟房主") == ("inactive", "room_ended"), f"{statuses.get('冒烟房主')}")
        check("申请人退出原因=self_leave", statuses.get("冒烟申请人") == ("inactive", "self_leave"), f"{statuses.get('冒烟申请人')}")
        check("被移出者退出原因=kicked", statuses.get("冒烟路人") == ("inactive", "kicked"), f"{statuses.get('冒烟路人')}")

        requests_after = body(host.get(f"/api/rooms/{room_id}/join-requests")).get("data", {}).get("requests", [])
        statuses_req = sorted(item["status"] for item in requests_after)
        # r011 口径变更：满员那一刻，该房**待批申请已被自动拒绝**（上面 8e 填满到 8 人触发），
        # 所以结束房间时已无 pending 可供置 `cancelled` —— 断言改为「出现过 rejected」，
        # `cancelled` 路径仍由 `test_rooms_service.py` 的服务层用例覆盖。
        check("申请状态含 rejected（r011 满员自动拒）", "rejected" in statuses_req, f"{statuses_req}")

        blocked = guest.post(f"/api/rooms/{room_id}/join-requests", json={})
        check("结束后不能再申请", blocked.status_code == 409 and body(blocked).get("error", {}).get("code") == "ROOM_ENDED", f"→ {blocked.status_code} {body(blocked).get('error', {}).get('code')}")

        ended_token = guest.post(f"/api/rooms/{room_id}/token")
        check("结束后取 Token → 409", ended_token.status_code == 409 and body(ended_token).get("error", {}).get("code") == "ROOM_ENDED", f"→ {ended_token.status_code} {body(ended_token).get('error', {}).get('code')}")

        readonly = body(guest.get(f"/api/rooms/{room_id}")).get("data", {})
        check("结束后仍可只读查看", readonly.get("room", {}).get("status") == "ended" and len(readonly.get("messages", [])) >= 0, f"status={readonly.get('room', {}).get('status')}")


        # 10) r008：限时邀请（作业必做「可生成限时邀请链接或房间码（需设置过期时间）」）
        inv_created = host.post(
            "/api/rooms",
            json={"topic": "custom", "topicLabel": "冒烟邀请", "title": f"冒烟邀请房 {suffix}", "description": ""},
        )
        inv_room_id = body(inv_created).get("data", {}).get("id")
        check("建房（邀请房）", inv_created.status_code == 201 and bool(inv_room_id), f"→ {inv_created.status_code}")

        invite = host.post(f"/api/rooms/{inv_room_id}/invites", json={"ttlSeconds": 30, "maxUses": 1})
        invite_code = body(invite).get("data", {}).get("code", "")
        check(
            "生成限时邀请码 → 6 位",
            invite.status_code == 201 and len(invite_code) == 6,
            f"→ {invite.status_code} code={invite_code} ttl={body(invite).get('data', {}).get('expiresAt')}",
        )

        outsider_join = outsider.post(f"/api/offline" if False else f"/api/invites/{invite_code}/accept")
        check(
            "凭码直接加入 → 201",
            outsider_join.status_code == 201 and body(outsider_join).get("data", {}).get("created") is True,
            f"→ {outsider_join.status_code} created={body(outsider_join).get('data', {}).get('created')}",
        )
        idempotent = outsider.post(f"/api/invites/{invite_code}/accept")
        check(
            "已在册再点 → 200 幂等",
            idempotent.status_code == 200 and body(idempotent).get("data", {}).get("created") is False,
            f"→ {idempotent.status_code} created={body(idempotent).get('data', {}).get('created')}",
        )

        # 11) r008：讨论纪要（作业必做「会后产出」）——两分支如实断言
        host.post(f"/api/rooms/{inv_room_id}/end")
        summary = host.post(f"/api/rooms/{inv_room_id}/summary")
        if summary.status_code == 201:
            summary_status = body(summary).get("data", {}).get("status")
            check(
                "生成讨论纪要 → ready（LLM 已配置）",
                summary_status == "ready" and len(body(summary).get("data", {}).get("content", "")) > 50,
                f"→ {summary.status_code} status={summary_status} 字数={len(body(summary).get('data', {}).get('content', ''))}",
            )
        else:
            check(
                "生成讨论纪要 → 503 LLM_NOT_CONFIGURED（未配密钥时的如实分支）",
                summary.status_code == 503 and body(summary).get("error", {}).get("code") == "LLM_NOT_CONFIGURED",
                f"→ {summary.status_code} {body(summary).get('error', {}).get('code')}",
            )
        summary_view = host.get(f"/api/rooms/{inv_room_id}/summary")
        check(
            "查看讨论纪要 → 200",
            summary_view.status_code == 200 and "summary" in body(summary_view).get("data", {}),
            f"→ {summary_view.status_code} 有纪要={body(summary_view).get('data', {}).get('summary') is not None}",
        )

        # 12) r012：超管身份 / 管理后台 / 全服大屏（真机 HTTP，不打桩）
        admin = httpx.Client(base_url=base, timeout=15.0)
        try:
            login = admin.post("/api/auth/login", json={"email": "admin@example.com", "password": "demo1234"})
            if login.status_code == 200:
                check(
                    "演示超管登录 → role=superadmin",
                    body(login).get("data", {}).get("user", {}).get("role") == "superadmin",
                    f"→ {login.status_code} role={body(login).get('data', {}).get('user', {}).get('role')}",
                )
                forbidden = host.get("/api/admin/rooms")
                check(
                    "普通账号调管理后台 → 403",
                    forbidden.status_code == 403,
                    f"→ {forbidden.status_code} {body(forbidden).get('error', {}).get('code')}",
                )
                listed = admin.get("/api/admin/rooms?limit=5")
                check(
                    "超管看房间列表 → 200 且有数据",
                    listed.status_code == 200 and len(body(listed).get("data", {}).get("items", [])) >= 1,
                    f"→ {listed.status_code} 本页 {len(body(listed).get('data', {}).get('items', []))} 条 / 共 {body(listed).get('data', {}).get('total')}",
                )
                for endpoint in ("users", "summaries", "audit"):
                    one = admin.get(f"/api/admin/{endpoint}?limit=1")
                    check(f"超管看{endpoint}列表 → 200", one.status_code == 200, f"→ {one.status_code}")

                # 取票必须挑**进行中**的房：前面两个房都已结束（结束房对谁都是 409，超管也不例外）
                live_room = body(host.post("/api/rooms", json={"topic": "custom", "topicLabel": "冒烟主题", "title": f"冒烟超管房 {suffix}", "description": "由 smoke.py 创建（超管取票用）"})).get("data", {})
                token_resp = admin.post(f"/api/rooms/{live_room.get('id')}/token")
                claims = {}
                if token_resp.status_code == 200:
                    payload = body(token_resp).get("data", {}).get("token", "").split(".")[1]
                    payload += "=" * (-len(payload) % 4)
                    claims = json.loads(base64.urlsafe_b64decode(payload))
                check(
                    "超管对他人房取票 → 隐身且禁止发布",
                    token_resp.status_code == 200
                    and claims.get("video", {}).get("hidden") is True
                    and claims.get("video", {}).get("canPublish") is False
                    and claims.get("video", {}).get("canPublishData") is False
                    and claims.get("attributes", {}).get("lg-role") == "superadmin",
                    f"→ {token_resp.status_code} hidden={claims.get('video', {}).get('hidden')} "
                    f"canPublish={claims.get('video', {}).get('canPublish')} lg-role={claims.get('attributes', {}).get('lg-role')}",
                )

                said = admin.post("/api/global-messages", json={"body": f"冒烟大屏 {suffix}"})
                messages = admin.get("/api/global-messages?limit=20")
                bodies = [item.get("body") for item in body(messages).get("data", {}).get("items", [])]
                check(
                    "大屏发言并读回 → 201 且列表含该条",
                    said.status_code == 201 and f"冒烟大屏 {suffix}" in bodies,
                    f"→ {said.status_code} 列表 {len(bodies)} 条",
                )
                # 真的「没带会话」的客户端（脚本里的 guest 客户端在第 1 步就注册登录了）
                anon = httpx.Client(base_url=base, timeout=15.0)
                try:
                    guest_try = anon.post("/api/global-messages", json={"body": "游客不该能发"})
                    check(
                        "未登录发大屏 → 401",
                        guest_try.status_code == 401,
                        f"→ {guest_try.status_code} {body(guest_try).get('error', {}).get('code')}",
                    )
                    anon_read = anon.get("/api/global-messages")
                    check(
                        "未登录读大屏 → 200（公开面）",
                        anon_read.status_code == 200,
                        f"→ {anon_read.status_code} 可见 {len(body(anon_read).get('data', {}).get('items', []))} 条",
                    )
                finally:
                    anon.close()
                beat = admin.post("/api/presence")
                check(
                    "在线心跳 → 200 带 lastSeenAt",
                    beat.status_code == 200 and bool(body(beat).get("data", {}).get("lastSeenAt")),
                    f"→ {beat.status_code} lastSeenAt={str(body(beat).get('data', {}).get('lastSeenAt'))[:19]}",
                )
            else:
                check(
                    "演示超管登录（需先 db_init --seed 写入 admin@example.com）",
                    False,
                    f"→ {login.status_code}（先执行 python backend/scripts/db_init.py --seed）",
                )
        finally:
            admin.close()

    except httpx.HTTPError as exc:
        print(f"[FAIL] 网络错误：{type(exc).__name__}: {exc}")
        return 1
    finally:
        host.close()
        guest.close()
        try:
            outsider.close()
        except NameError:  # 未走到 5c 就失败时未定义
            pass

    total = CHECKS
    if FAILURES:
        print(f"\nFAIL {len(FAILURES)}/{total} — 失败项：{', '.join(FAILURES)}")
        return 1
    print(f"\nPASS {total}/{total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
