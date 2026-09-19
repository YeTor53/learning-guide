"""`rooms` / `room_members` / `join_requests` / `chat_messages` 的参数化 SQL 绑定。

设计事实源：docs/02-modules/r001-rooms.md §6.3（签名即契约）；表定义见同页 §3
纪律：本层只做 SQL 与行映射（→ dataclass），不写业务判断、不开事务、不做多语句编排。
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Sequence

from psycopg import Connection

ROOM_FIELDS = ("id", "host_id", "topic", "topic_label", "title", "description", "status", "capacity", "room_code", "created_at", "ended_at")
MEMBER_FIELDS = ("id", "room_id", "user_id", "role", "status", "exit_reason", "joined_at", "left_at")
REQUEST_FIELDS = ("id", "room_id", "user_id", "status", "message", "created_at", "decided_at", "decided_by")
MESSAGE_FIELDS = ("id", "room_id", "user_id", "body", "kind", "created_at")


def _columns(fields: tuple[str, ...], alias: str) -> str:
    """给列名加表别名——JOIN 查询里 `id` 之类会歧义，统一按别名拼。"""
    return ", ".join(f"{alias}.{field}" for field in fields)


ROOM_COLUMNS = _columns(ROOM_FIELDS, "r")  # 房间查询统一 `FROM rooms r`
MEMBER_COLUMNS = _columns(MEMBER_FIELDS, "m")
REQUEST_COLUMNS = _columns(REQUEST_FIELDS, "r")
MESSAGE_COLUMNS = _columns(MESSAGE_FIELDS, "g")


@dataclass(frozen=True)
class NewRoom:
    id: str
    host_id: str
    topic: str
    topic_label: str
    title: str
    description: str
    capacity: int
    room_code: str


@dataclass(frozen=True)
class RoomRow:
    id: str
    host_id: str
    topic: str
    topic_label: str
    title: str
    description: str
    status: str
    capacity: int
    room_code: str
    created_at: datetime
    ended_at: Optional[datetime]


@dataclass(frozen=True)
class RoomWithHost:
    """列表/详情用：房间行 + 房主显示名（一次 JOIN 取回，避免 N+1）。"""

    room: RoomRow
    host_name: str


@dataclass(frozen=True)
class RoomFilter:
    status: Optional[str] = None          # active / ended / None(=all)
    topic: Optional[str] = None
    mine_user_id: Optional[str] = None    # mine=1 时传当前用户
    limit: int = 20
    offset: int = 0


@dataclass(frozen=True)
class NewMember:
    id: str
    room_id: str
    user_id: str
    role: str


@dataclass(frozen=True)
class MemberRow:
    id: str
    room_id: str
    user_id: str
    role: str
    status: str
    exit_reason: Optional[str]
    joined_at: datetime
    left_at: Optional[datetime]


@dataclass(frozen=True)
class MemberRowWithName:
    member: MemberRow
    display_name: str


@dataclass(frozen=True)
class NewMessage:
    """写一条消息（r005 起用于房间事件：`kind='system'`）。"""

    id: str
    room_id: str
    user_id: str
    body: str
    kind: str = "system"


@dataclass(frozen=True)
class NewJoinRequest:
    id: str
    room_id: str
    user_id: str
    message: str


@dataclass(frozen=True)
class JoinRequestRow:
    id: str
    room_id: str
    user_id: str
    status: str
    message: str
    created_at: datetime
    decided_at: Optional[datetime]
    decided_by: Optional[str]


@dataclass(frozen=True)
class JoinRequestRowWithName:
    request: JoinRequestRow
    display_name: str


@dataclass(frozen=True)
class MessageRow:
    id: str
    room_id: str
    user_id: str
    body: str
    kind: str
    created_at: datetime


@dataclass(frozen=True)
class MessageRowWithName:
    message: MessageRow
    display_name: str


def _room(row: tuple) -> RoomRow:
    return RoomRow(row[0], row[1], row[2], row[3], row[4], row[5], row[6], row[7], row[8], row[9], row[10])


def _member(row: tuple) -> MemberRow:
    return MemberRow(row[0], row[1], row[2], row[3], row[4], row[5], row[6], row[7])


def _request(row: tuple) -> JoinRequestRow:
    return JoinRequestRow(row[0], row[1], row[2], row[3], row[4], row[5], row[6], row[7])


def _message(row: tuple) -> MessageRow:
    return MessageRow(row[0], row[1], row[2], row[3], row[4], row[5])


# ---------------- rooms ----------------

def insert_room(conn: Connection, row: NewRoom) -> None:
    conn.execute(
        """INSERT INTO rooms (id, host_id, topic, topic_label, title, description, capacity, room_code)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
        (row.id, row.host_id, row.topic, row.topic_label, row.title, row.description, row.capacity, row.room_code),
    )


def lock_room(conn: Connection, room_id: str) -> Optional[RoomRow]:
    """房间级互斥：批准 / 拒绝 / 离开 / 结束共用这一个锁点。"""
    row = conn.execute(
        f"SELECT {', '.join(ROOM_FIELDS)} FROM rooms WHERE id = %s FOR UPDATE", (room_id,)
    ).fetchone()
    return _room(row) if row else None


def get_room(conn: Connection, room_id: str) -> Optional[RoomWithHost]:
    row = conn.execute(
        f"""SELECT {ROOM_COLUMNS}, u.display_name FROM rooms r JOIN users u ON u.id = r.host_id
            WHERE r.id = %s""",
        (room_id,),
    ).fetchone()
    return RoomWithHost(_room(row[:11]), row[11]) if row else None


def _list_where(f: RoomFilter) -> tuple[str, list]:
    clauses: list[str] = []
    params: list = []
    if f.status:
        clauses.append("r.status = %s")
        params.append(f.status)
    if f.topic:
        clauses.append("r.topic = %s")
        params.append(f.topic)
    if f.mine_user_id:
        clauses.append(
            "(r.host_id = %s"
            " OR EXISTS (SELECT 1 FROM room_members m WHERE m.room_id = r.id AND m.user_id = %s)"
            " OR EXISTS (SELECT 1 FROM join_requests j WHERE j.room_id = r.id AND j.user_id = %s AND j.status = 'pending'))"
        )
        params.extend([f.mine_user_id, f.mine_user_id, f.mine_user_id])
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    return where, params


def list_rooms(conn: Connection, f: RoomFilter) -> tuple[list[RoomWithHost], int]:
    """列表 + 总数；排序：进行中优先，其次创建时间倒序（功能页 F-01）。"""
    where, params = _list_where(f)
    total = conn.execute(f"SELECT count(*) FROM rooms r {where}", params).fetchone()[0]
    rows = conn.execute(
        f"""SELECT {ROOM_COLUMNS}, u.display_name FROM rooms r JOIN users u ON u.id = r.host_id
            {where}
            ORDER BY (r.status = 'active') DESC, r.created_at DESC, r.id DESC
            LIMIT %s OFFSET %s""",
        [*params, f.limit, f.offset],
    ).fetchall()
    return [RoomWithHost(_room(row[:11]), row[11]) for row in rows], total


def room_aggregates(conn: Connection, room_ids: Sequence[str]) -> dict[str, tuple[int, int]]:
    """批量取 (活跃成员数, 待批申请数)，避免列表 N+1。"""
    if not room_ids:
        return {}
    members = dict(
        conn.execute(
            """SELECT room_id, count(*) FROM room_members
               WHERE status = 'active' AND room_id = ANY(%s) GROUP BY room_id""",
            (list(room_ids),),
        ).fetchall()
    )
    pending = dict(
        conn.execute(
            """SELECT room_id, count(*) FROM join_requests
               WHERE status = 'pending' AND room_id = ANY(%s) GROUP BY room_id""",
            (list(room_ids),),
        ).fetchall()
    )
    return {rid: (members.get(rid, 0), pending.get(rid, 0)) for rid in room_ids}


def my_active_roles(conn: Connection, user_id: str, room_ids: Sequence[str]) -> dict[str, str]:
    """我在这些房间里的活跃角色（`room_id → role`）。"""
    if not room_ids:
        return {}
    rows = conn.execute(
        """SELECT room_id, role FROM room_members
           WHERE status = 'active' AND user_id = %s AND room_id = ANY(%s)""",
        (user_id, list(room_ids)),
    ).fetchall()
    return {row[0]: row[1] for row in rows}


def my_pending_requests(conn: Connection, user_id: str, room_ids: Sequence[str]) -> set[str]:
    """我在这些房间里处于待批状态的房间 id 集合。"""
    if not room_ids:
        return set()
    rows = conn.execute(
        """SELECT room_id FROM join_requests
           WHERE status = 'pending' AND user_id = %s AND room_id = ANY(%s)""",
        (user_id, list(room_ids)),
    ).fetchall()
    return {row[0] for row in rows}


def update_room_ended(conn: Connection, room_id: str, at: datetime) -> None:
    conn.execute("UPDATE rooms SET status = 'ended', ended_at = %s WHERE id = %s", (at, room_id))


def update_room_host(conn: Connection, room_id: str, host_id: str) -> None:
    conn.execute("UPDATE rooms SET host_id = %s WHERE id = %s", (host_id, room_id))


# ---------------- room_members ----------------

def insert_member(conn: Connection, row: NewMember) -> None:
    conn.execute(
        "INSERT INTO room_members (id, room_id, user_id, role) VALUES (%s, %s, %s, %s)",
        (row.id, row.room_id, row.user_id, row.role),
    )


def get_active_member(conn: Connection, room_id: str, user_id: str) -> Optional[MemberRow]:
    row = conn.execute(
        f"SELECT {MEMBER_COLUMNS} FROM room_members m WHERE m.room_id = %s AND m.user_id = %s AND m.status = 'active'",
        (room_id, user_id),
    ).fetchone()
    return _member(row) if row else None


def insert_message(conn: Connection, message: NewMessage) -> None:
    """插入一条消息；`kind='system'` 用于房间事件留痕（与状态变更同事务调用）。"""
    conn.execute(
        """INSERT INTO chat_messages (id, room_id, user_id, body, kind)
           VALUES (%s, %s, %s, %s, %s)""",
        (message.id, message.room_id, message.user_id, message.body, message.kind),
    )


def get_display_name(conn: Connection, user_id: str) -> Optional[str]:
    """取用户显示名（房间事件文案里要点名，而成员行不带名字）。"""
    row = conn.execute("SELECT display_name FROM users WHERE id = %s", (user_id,)).fetchone()
    return row[0] if row else None


def count_active_members(conn: Connection, room_id: str) -> int:
    return conn.execute(
        "SELECT count(*) FROM room_members WHERE room_id = %s AND status = 'active'", (room_id,)
    ).fetchone()[0]


def list_members(conn: Connection, room_id: str, include_inactive: bool = False) -> list[MemberRowWithName]:
    """成员列表；`include_inactive=True` 时含历史成员与退出原因（房间结束后的追溯视图）。"""
    condition = "" if include_inactive else "AND m.status = 'active'"
    rows = conn.execute(
        f"""SELECT {MEMBER_COLUMNS}, u.display_name FROM room_members m JOIN users u ON u.id = m.user_id
            WHERE m.room_id = %s {condition}
            ORDER BY (m.status = 'active') DESC, m.joined_at ASC, m.id ASC""",
        (room_id,),
    ).fetchall()
    return [MemberRowWithName(_member(row[:8]), row[8]) for row in rows]


def deactivate_member(conn: Connection, room_id: str, user_id: str, reason: str, at: datetime) -> None:
    conn.execute(
        """UPDATE room_members SET status = 'inactive', exit_reason = %s, left_at = %s
           WHERE room_id = %s AND user_id = %s AND status = 'active'""",
        (reason, at, room_id, user_id),
    )


def update_member_role(conn: Connection, room_id: str, user_id: str, role: str) -> None:
    conn.execute(
        "UPDATE room_members SET role = %s WHERE room_id = %s AND user_id = %s AND status = 'active'",
        (role, room_id, user_id),
    )


def count_active_hosts(conn: Connection, room_id: str) -> int:
    """活跃 Host 数量（并发移交 / 角色变更后的不变量断言；R-6 部分唯一索引兜底）。"""
    return conn.execute(
        "SELECT count(*) FROM room_members WHERE room_id = %s AND status = 'active' AND role = 'host'", (room_id,)
    ).fetchone()[0]


def deactivate_all_members(conn: Connection, room_id: str, at: datetime) -> int:
    cur = conn.execute(
        """UPDATE room_members SET status = 'inactive', exit_reason = 'room_ended', left_at = %s
           WHERE room_id = %s AND status = 'active'""",
        (at, room_id),
    )
    return cur.rowcount


# ---------------- join_requests ----------------

def insert_join_request(conn: Connection, row: NewJoinRequest) -> None:
    conn.execute(
        "INSERT INTO join_requests (id, room_id, user_id, message) VALUES (%s, %s, %s, %s)",
        (row.id, row.room_id, row.user_id, row.message),
    )


def get_join_request(conn: Connection, request_id: str) -> Optional[JoinRequestRow]:
    row = conn.execute(f"SELECT {REQUEST_COLUMNS} FROM join_requests r WHERE r.id = %s", (request_id,)).fetchone()
    return _request(row) if row else None


def get_pending_request(conn: Connection, room_id: str, user_id: str) -> Optional[JoinRequestRow]:
    row = conn.execute(
        f"SELECT {REQUEST_COLUMNS} FROM join_requests r WHERE r.room_id = %s AND r.user_id = %s AND r.status = 'pending'",
        (room_id, user_id),
    ).fetchone()
    return _request(row) if row else None


def list_join_requests(conn: Connection, room_id: str, status: Optional[str] = None) -> list[JoinRequestRowWithName]:
    condition = "AND r.status = %s" if status else ""
    params = [room_id, status] if status else [room_id]
    rows = conn.execute(
        f"""SELECT {REQUEST_COLUMNS}, u.display_name FROM join_requests r JOIN users u ON u.id = r.user_id
            WHERE r.room_id = %s {condition}
            ORDER BY (r.status = 'pending') DESC, r.created_at ASC, r.id ASC""",
        params,
    ).fetchall()
    return [JoinRequestRowWithName(_request(row[:8]), row[8]) for row in rows]


def decide_join_request(conn: Connection, request_id: str, status: str, decided_by: Optional[str], at: datetime) -> None:
    conn.execute(
        "UPDATE join_requests SET status = %s, decided_at = %s, decided_by = %s WHERE id = %s",
        (status, at, decided_by, request_id),
    )


def withdraw_join_request(conn: Connection, request_id: str, at: datetime, by: str) -> None:
    """申请人撤回：置 `withdrawn` 并落 `decided_at`（`decided_by` 记为本人）。"""
    conn.execute(
        "UPDATE join_requests SET status = 'withdrawn', decided_at = %s, decided_by = %s WHERE id = %s",
        (at, by, request_id),
    )


def cancel_pending_requests(conn: Connection, room_id: str, at: datetime) -> int:
    """房间结束时的连带动作：待批申请置 `cancelled`（`decided_by=NULL` 表示系统）。"""
    cur = conn.execute(
        """UPDATE join_requests SET status = 'cancelled', decided_at = %s, decided_by = NULL
           WHERE room_id = %s AND status = 'pending'""",
        (at, room_id),
    )
    return cur.rowcount


# ---------------- chat_messages ----------------

def list_recent_messages(conn: Connection, room_id: str, limit: int) -> list[MessageRowWithName]:
    """详情页最近消息（升序返回，前端直接按时间顺序渲染）。"""
    rows = conn.execute(
        f"""SELECT * FROM (
              SELECT {MESSAGE_COLUMNS}, u.display_name FROM chat_messages g JOIN users u ON u.id = g.user_id
              WHERE g.room_id = %s ORDER BY g.created_at DESC LIMIT %s
            ) recent ORDER BY recent.created_at ASC""",
        (room_id, limit),
    ).fetchall()
    return [MessageRowWithName(_message(row[:6]), row[6]) for row in rows]
