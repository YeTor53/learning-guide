"""M1 全链路冒烟：走真实 HTTP 把「注册 → 建房 → 申请 → 批准 → 离开 → 再次申请 → 结束房间 → 只读」跑一遍。

用法（先启动后端）：
  python backend/scripts/db_init.py --reset --seed      # 可选：先恢复演示数据
  python -m uvicorn app.main:app --port 8000            # 在 backend/ 下启动
  python backend/scripts/smoke.py --base-url http://127.0.0.1:8000

设计事实源：docs/01-architecture/r001-app-architecture.md §9.6；docs/02-modules/r001-rooms.md §6.8
判据：每步状态码与关键字段符合预期，末尾打印 `PASS n/n`；任一步不符即以非 0 退出。
 r002 补步（2026-09-19）：成员取 Token 200 / 非成员取 Token 403 / 踢人后取 Token 403 / 结束后取 Token 409。
注意：① 脚本会向库里写入两个账号与一个房间（每次邮箱随机），跑完可用 db_init --reset --seed 恢复演示数据；
      ② 本脚本要求后端以 `APP_ENV=dev`（默认）运行：`APP_ENV=demo` 时会话 Cookie 带 Secure，脚本客户端不会回传，
         会出现「注册成功但下一步 401」——这是设计如此（演示形态用浏览器访问不受影响）。
"""
from __future__ import annotations

import argparse
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
        check("申请状态含 cancelled", "cancelled" in statuses_req, f"{statuses_req}")

        blocked = guest.post(f"/api/rooms/{room_id}/join-requests", json={})
        check("结束后不能再申请", blocked.status_code == 409 and body(blocked).get("error", {}).get("code") == "ROOM_ENDED", f"→ {blocked.status_code} {body(blocked).get('error', {}).get('code')}")

        ended_token = guest.post(f"/api/rooms/{room_id}/token")
        check("结束后取 Token → 409", ended_token.status_code == 409 and body(ended_token).get("error", {}).get("code") == "ROOM_ENDED", f"→ {ended_token.status_code} {body(ended_token).get('error', {}).get('code')}")

        readonly = body(guest.get(f"/api/rooms/{room_id}")).get("data", {})
        check("结束后仍可只读查看", readonly.get("room", {}).get("status") == "ended" and len(readonly.get("messages", [])) >= 0, f"status={readonly.get('room', {}).get('status')}")

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
