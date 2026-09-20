"""`/api/admin/*` 的只读查询与两处写操作（参数化 SQL；不写业务判断、不开事务）。

设计事实源：docs/rounds/r012-superadmin-console/design.md §3.1。
- 三个列表一次 JOIN 出全（房主名 / 在册人数 / 待批数 / 纪要状态），避免 N+1；
- `admin_audit` **故意不 FK 到 rooms**（删房后流水仍在）；
- 过滤条件集中在本文件，service 只做鉴权与审计。
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import NamedTuple, Optional

from psycopg import Connection
from psycopg.types.json import Jsonb


class AdminRoomFilter(NamedTuple):
    status: Optional[str] = None      # active / ended / None(=all)
    q: Optional[str] = None           # 标题 / 房间码 / 房主名 模糊
    limit: int = 20
    offset: int = 0


class AdminUserFilter(NamedTuple):
    q: Optional[str] = None           # 邮箱 / 显示名 模糊
    online_since: Optional[datetime] = None   # 只列最近心跳不早于它的用户（在线）
    limit: int = 20
    offset: int = 0


class AdminSummaryFilter(NamedTuple):
    status: Optional[str] = None      # ready / failed
    limit: int = 20
    offset: int = 0


class AdminAuditFilter(NamedTuple):
    action: Optional[str] = None
    limit: int = 20
    offset: int = 0


@dataclass(frozen=True)
class AdminRoomRow:
    id: str
    title: str
    topic_label: str
    status: str
    capacity: int
    room_code: str
    host_id: str
    host_name: str
    member_count: int
    pending_count: int
    summary_status: Optional[str]
    created_at: datetime
    ended_at: Optional[datetime]


@dataclass(frozen=True)
class AdminUserRow:
    id: str
    email: str
    display_name: str
    role: str
    created_at: datetime
    last_seen_at: Optional[datetime]
    active_rooms: int
    message_count: int
    global_message_count: int


@dataclass(frozen=True)
class AdminSummaryRow:
    id: str
    room_id: str
    room_title: str
    status: str
    provider: str
    model: str
    content_length: int
    error: Optional[str]
    created_by: Optional[str]
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class AdminAuditRow:
    id: str
    actor_id: Optional[str]
    actor_name: Optional[str]
    action: str
    target_type: str
    target_id: str
    detail: dict
    created_at: datetime


@dataclass(frozen=True)
class NewAudit:
    id: str
    actor_id: Optional[str]
    action: str
    target_type: str
    target_id: str
    detail: dict
    created_at: datetime


def _like(value: str) -> str:
    """模糊匹配串（转义 % 与 _，避免用户输入当通配符）。"""
    escaped = value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def _room_where(f: AdminRoomFilter) -> tuple[str, list]:
    clauses: list[str] = []
    params: list = []
    if f.status:
        clauses.append("r.status = %s")
        params.append(f.status)
    if f.q:
        clauses.append("(r.title ILIKE %s OR r.room_code ILIKE %s OR u.display_name ILIKE %s)")
        params.extend([_like(f.q)] * 3)
    return (f"WHERE {' AND '.join(clauses)}" if clauses else ""), params


def list_rooms_page(conn: Connection, f: AdminRoomFilter) -> tuple[list[AdminRoomRow], int]:
    where, params = _room_where(f)
    total = conn.execute(
        f"""SELECT count(*) FROM rooms r JOIN users u ON u.id = r.host_id {where}""",
        tuple(params),
    ).fetchone()[0]
    rows = conn.execute(
        f"""SELECT r.id, r.title, r.topic_label, r.status, r.capacity, r.room_code,
                   r.host_id, u.display_name,
                   (SELECT count(*) FROM room_members m WHERE m.room_id = r.id AND m.status = 'active'),
                   (SELECT count(*) FROM join_requests j WHERE j.room_id = r.id AND j.status = 'pending'),
                   s.status, r.created_at, r.ended_at
            FROM rooms r
            JOIN users u ON u.id = r.host_id
            LEFT JOIN session_summaries s ON s.room_id = r.id
            {where}
            ORDER BY (r.status = 'active') DESC, r.created_at DESC, r.id DESC
            LIMIT %s OFFSET %s""",
        tuple(params + [f.limit, f.offset]),
    ).fetchall()
    return [
        AdminRoomRow(
            id=row[0], title=row[1], topic_label=row[2], status=row[3], capacity=row[4], room_code=row[5],
            host_id=row[6], host_name=row[7], member_count=row[8], pending_count=row[9],
            summary_status=row[10], created_at=row[11], ended_at=row[12],
        )
        for row in rows
    ], total


def list_users_page(conn: Connection, f: AdminUserFilter) -> tuple[list[AdminUserRow], int]:
    clauses: list[str] = []
    params: list = []
    if f.q:
        clauses.append("(u.email ILIKE %s OR u.display_name ILIKE %s)")
        params.extend([_like(f.q)] * 2)
    if f.online_since is not None:
        clauses.append("u.last_seen_at IS NOT NULL AND u.last_seen_at >= %s")
        params.append(f.online_since)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    total = conn.execute(f"SELECT count(*) FROM users u {where}", tuple(params)).fetchone()[0]
    rows = conn.execute(
        f"""SELECT u.id, u.email, u.display_name, u.role, u.created_at, u.last_seen_at,
                   (SELECT count(*) FROM room_members m WHERE m.user_id = u.id AND m.status = 'active'),
                   (SELECT count(*) FROM chat_messages c WHERE c.user_id = u.id),
                   (SELECT count(*) FROM global_messages g WHERE g.user_id = u.id)
            FROM users u
            {where}
            ORDER BY u.created_at DESC, u.id DESC
            LIMIT %s OFFSET %s""",
        tuple(params + [f.limit, f.offset]),
    ).fetchall()
    return [
        AdminUserRow(
            id=row[0], email=row[1], display_name=row[2], role=row[3], created_at=row[4],
            last_seen_at=row[5], active_rooms=row[6], message_count=row[7], global_message_count=row[8],
        )
        for row in rows
    ], total


def list_summaries_page(conn: Connection, f: AdminSummaryFilter) -> tuple[list[AdminSummaryRow], int]:
    where = "WHERE s.status = %s" if f.status else ""
    params: list = [f.status] if f.status else []
    total = conn.execute(f"SELECT count(*) FROM session_summaries s {where}", tuple(params)).fetchone()[0]
    rows = conn.execute(
        f"""SELECT s.id, s.room_id, r.title, s.status, s.provider, s.model,
                   char_length(coalesce(s.content, '')) , s.error, s.created_by, s.created_at, s.updated_at
            FROM session_summaries s
            JOIN rooms r ON r.id = s.room_id
            {where}
            ORDER BY s.updated_at DESC, s.id DESC
            LIMIT %s OFFSET %s""",
        tuple(params + [f.limit, f.offset]),
    ).fetchall()
    return [
        AdminSummaryRow(
            id=row[0], room_id=row[1], room_title=row[2], status=row[3], provider=row[4], model=row[5],
            content_length=row[6], error=row[7], created_by=row[8], created_at=row[9], updated_at=row[10],
        )
        for row in rows
    ], total


def list_audit_page(conn: Connection, f: AdminAuditFilter) -> tuple[list[AdminAuditRow], int]:
    where = "WHERE a.action = %s" if f.action else ""
    params: list = [f.action] if f.action else []
    total = conn.execute(f"SELECT count(*) FROM admin_audit a {where}", tuple(params)).fetchone()[0]
    rows = conn.execute(
        f"""SELECT a.id, a.actor_id, u.display_name, a.action, a.target_type, a.target_id, a.detail, a.created_at
            FROM admin_audit a
            LEFT JOIN users u ON u.id = a.actor_id
            {where}
            ORDER BY a.created_at DESC, a.id DESC
            LIMIT %s OFFSET %s""",
        tuple(params + [f.limit, f.offset]),
    ).fetchall()
    return [
        AdminAuditRow(
            id=row[0], actor_id=row[1], actor_name=row[2], action=row[3], target_type=row[4],
            target_id=row[5], detail=row[6] or {}, created_at=row[7],
        )
        for row in rows
    ], total


def insert_audit(conn: Connection, row: NewAudit) -> None:
    """写一条管理动作流水（与业务动作同一个事务：有动作必有流水）。"""
    conn.execute(
        """INSERT INTO admin_audit (id, actor_id, action, target_type, target_id, detail, created_at)
           VALUES (%s, %s, %s, %s, %s, %s, %s)""",
        (row.id, row.actor_id, row.action, row.target_type, row.target_id, Jsonb(row.detail), row.created_at),
    )


def get_room_snapshot(conn: Connection, room_id: str) -> Optional[dict]:
    """删房前的快照（写进审计 detail：删完就查不到了）。"""
    row = conn.execute(
        """SELECT r.title, r.topic_label, r.status, r.host_id, u.display_name,
                  (SELECT count(*) FROM room_members m WHERE m.room_id = r.id),
                  (SELECT count(*) FROM chat_messages c WHERE c.room_id = r.id),
                  (SELECT count(*) FROM session_summaries s WHERE s.room_id = r.id)
           FROM rooms r JOIN users u ON u.id = r.host_id
           WHERE r.id = %s""",
        (room_id,),
    ).fetchone()
    if row is None:
        return None
    return {
        "title": row[0], "topicLabel": row[1], "status": row[2], "hostId": row[3], "hostName": row[4],
        "memberCount": row[5], "messageCount": row[6], "summaryCount": row[7],
    }


def delete_room(conn: Connection, room_id: str) -> int:
    """硬删房间（成员/申请/邀请/消息/举手/焦点/纪要/转写靠 FK CASCADE 一并删）；返回影响行数。"""
    cursor = conn.execute("DELETE FROM rooms WHERE id = %s", (room_id,))
    return cursor.rowcount
