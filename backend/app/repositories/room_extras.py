"""`room_hand_raises` / `room_focus` / 群聊消息的参数化 SQL（r004 / M3）。

设计事实源：docs/rounds/r004-room-extras/design.md §3（数据模型）、§4（接口）、§5（函数级）
纪律：与 `repositories/rooms.py` 同层——只做 SQL 与行映射，不写业务判断、不开事务。
分层说明：设计里只点名了 service 与 router；SQL 按既有分层落在这里（见实现页 §5）。
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from psycopg import Connection

HAND_FIELDS = ("id", "room_id", "user_id", "raised_at", "lowered_at", "lowered_by", "lowered_reason")
FOCUS_FIELDS = ("id", "room_id", "subject_user_id", "actor_user_id", "created_at")
MESSAGE_FIELDS = ("id", "room_id", "user_id", "body", "kind", "created_at")


@dataclass(frozen=True)
class NewMessage:
    id: str
    room_id: str
    user_id: str
    body: str
    kind: str = "chat"


@dataclass(frozen=True)
class MessageRowWithName:
    message: tuple  # (id, room_id, user_id, body, kind, created_at)
    display_name: str


@dataclass(frozen=True)
class HandRowWithName:
    id: str
    room_id: str
    user_id: str
    display_name: str
    raised_at: datetime


@dataclass(frozen=True)
class FocusRowWithName:
    id: str
    room_id: str
    subject_user_id: Optional[str]
    subject_name: Optional[str]
    actor_user_id: str
    created_at: datetime


# ---------------- 群聊消息 ----------------

def insert_message(conn: Connection, row: NewMessage) -> None:
    conn.execute(
        """INSERT INTO chat_messages (id, room_id, user_id, body, kind)
           VALUES (%s, %s, %s, %s, %s)""",
        (row.id, row.room_id, row.user_id, row.body, row.kind),
    )


def list_messages(conn: Connection, room_id: str, before: Optional[datetime], limit: int) -> list[MessageRowWithName]:
    """按时间倒序取最近 `limit` 条；`before` 非空时只取更早的（分页）。"""
    sql = (
        "SELECT g.id, g.room_id, g.user_id, g.body, g.kind, g.created_at, u.display_name"
        "  FROM chat_messages g JOIN users u ON u.id = g.user_id"
        " WHERE g.room_id = %s"
    )
    params: list = [room_id]
    if before is not None:
        sql += " AND g.created_at < %s"
        params.append(before)
    sql += " ORDER BY g.created_at DESC, g.id DESC LIMIT %s"
    params.append(limit)
    rows = conn.execute(sql, tuple(params)).fetchall()
    return [MessageRowWithName(message=tuple(row[:6]), display_name=row[6]) for row in rows]


def get_message_time(conn: Connection, room_id: str, message_id: str) -> Optional[datetime]:
    """分页游标：取该消息在**本房间内**的时间戳（不存在返回 None）。"""
    row = conn.execute(
        "SELECT created_at FROM chat_messages WHERE room_id = %s AND id = %s", (room_id, message_id)
    ).fetchone()
    return row[0] if row else None


# ---------------- 举手 ----------------

def list_active_hands(conn: Connection, room_id: str) -> list[HandRowWithName]:
    rows = conn.execute(
        """SELECT h.id, h.room_id, h.user_id, u.display_name, h.raised_at
             FROM room_hand_raises h JOIN users u ON u.id = h.user_id
            WHERE h.room_id = %s AND h.lowered_at IS NULL
            ORDER BY h.raised_at ASC, h.id ASC""",
        (room_id,),
    ).fetchall()
    return [HandRowWithName(row[0], row[1], row[2], row[3], row[4]) for row in rows]


def insert_hand(conn: Connection, hand_id: str, room_id: str, user_id: str) -> bool:
    """举手；已在举则不动（部分唯一索引 + ON CONFLICT 保证幂等）。返回是否新插入。"""
    row = conn.execute(
        """INSERT INTO room_hand_raises (id, room_id, user_id) VALUES (%s, %s, %s)
           ON CONFLICT (room_id, user_id) WHERE lowered_at IS NULL DO NOTHING
           RETURNING id""",
        (hand_id, room_id, user_id),
    ).fetchone()
    return row is not None


def lower_hand(conn: Connection, room_id: str, user_id: str, by: str, reason: str) -> bool:
    """把某人的活跃举手置为放下。返回是否有行被改（无活跃举手时 False）。"""
    row = conn.execute(
        """UPDATE room_hand_raises SET lowered_at = now(), lowered_by = %s, lowered_reason = %s
            WHERE room_id = %s AND user_id = %s AND lowered_at IS NULL
           RETURNING id""",
        (by, reason, room_id, user_id),
    ).fetchone()
    return row is not None


def lower_all_hands(conn: Connection, room_id: str) -> int:
    """房间结束时清空全部活跃举手（`end_room` 的连带动作之一）。"""
    rows = conn.execute(
        """UPDATE room_hand_raises SET lowered_at = now(), lowered_by = 'system', lowered_reason = 'room_ended'
            WHERE room_id = %s AND lowered_at IS NULL
           RETURNING id""",
        (room_id,),
    ).fetchall()
    return len(rows)


# ---------------- 焦点 ----------------

def insert_focus(conn: Connection, focus_id: str, room_id: str, subject_user_id: Optional[str], actor_user_id: str) -> None:
    """写一条焦点事件；`subject_user_id=None` 表示取消焦点。"""
    conn.execute(
        "INSERT INTO room_focus (id, room_id, subject_user_id, actor_user_id) VALUES (%s, %s, %s, %s)",
        (focus_id, room_id, subject_user_id, actor_user_id),
    )


def latest_focus(conn: Connection, room_id: str) -> Optional[FocusRowWithName]:
    """当前焦点（最新一行）；`subject_name` 由 LEFT JOIN 取（人可能已离开）。"""
    row = conn.execute(
        """SELECT f.id, f.room_id, f.subject_user_id, u.display_name, f.actor_user_id, f.created_at
             FROM room_focus f LEFT JOIN users u ON u.id = f.subject_user_id
            WHERE f.room_id = %s
            ORDER BY f.created_at DESC, f.id DESC LIMIT 1""",
        (room_id,),
    ).fetchone()
    return FocusRowWithName(row[0], row[1], row[2], row[3], row[4], row[5]) if row else None
