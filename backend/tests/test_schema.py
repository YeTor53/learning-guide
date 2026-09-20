"""数据层断言：迁移文件、DDL 与文档一致性、约束真的挡得住非法数据。

设计事实源：docs/02-modules/r001-rooms.md §3（DDL）与 §9（验证矩阵）
说明：需要数据库的用例在没有 .env / 数据库连不上时会被跳过（见 conftest.py），
      判据以 `python backend/scripts/db_init.py --reset --seed` 的真实输出为准。
"""
from __future__ import annotations

from pathlib import Path

import pytest
from psycopg import errors as pg_errors

from app.db.migrate import COUNTED_TABLES, SQL_DIR, split_statements, sql_files

REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_DOC = REPO_ROOT / "docs" / "02-modules" / "r001-rooms.md"
SCHEMA_SQL = SQL_DIR / "001_schema.sql"


def _ddl_block_from_doc() -> str:
    """取模块页 §3 里 ```sql 代码块的内容（DDL 的单一事实源）。"""
    lines = MODULE_DOC.read_text(encoding="utf-8").splitlines()
    start = next(i for i, line in enumerate(lines) if line.strip() == "```sql")
    end = next(i for i, line in enumerate(lines) if i > start and line.strip() == "```")
    return "\n".join(lines[start + 1 : end])


def _normalize(statements: list[str]) -> list[str]:
    return [" ".join(s.split()).rstrip(";").strip() for s in statements]


# ---------- 纯函数（不需要数据库） ----------

def test_sql_files_are_ordered() -> None:
    """迁移按序号执行；新增迁移必须追加在末尾（003_ = R-6 活跃 Host 唯一索引；004_ = r004 举手与焦点；
    005_ = r005 时间戳默认改语句级；006_ = r007 主题扩容；007_ = r008 纪要；008_ = r009 焦点申请；
    009_ = r010 转写段）。"""
    names = [p.stem for p in sql_files()]
    assert names == [
        "001_schema",
        "002_seed",
        "003_r002_host_uniqueness",
        "004_r004_realtime_extras",
        "005_r005_statement_timestamps",
        "006_r007_topic_taxonomy",
        "007_r008_session_summaries",
        "008_r009_focus_requests",
        "009_r010_transcripts",
    ], names


def test_split_statements_handles_comments_and_literals() -> None:
    sql = """
    -- 行注释里的分号 ; 不算语句结束
    CREATE TABLE a (id TEXT); /* 块注释 ; 也一样 */
    INSERT INTO a VALUES ('分号 ; 在字符串里');
    INSERT INTO a VALUES ('转义 '' 引号');
    CREATE FUNCTION f() RETURNS void AS $body$ BEGIN; -- 内部
    END; $body$ LANGUAGE plpgsql;
    """
    statements = _normalize(split_statements(sql))
    assert len(statements) == 4, statements
    assert statements[0].startswith("CREATE TABLE a")
    assert "分号 ; 在字符串里" in statements[1]
    assert "转义 '' 引号" in statements[2]
    assert statements[3].startswith("CREATE FUNCTION f()")


def test_schema_sql_matches_design_page_verbatim() -> None:
    """001_schema.sql 与模块页 §3 的 DDL 逐字一致（去注释后逐条比较）。"""
    assert _normalize(split_statements(SCHEMA_SQL.read_text(encoding="utf-8"))) == _normalize(
        split_statements(_ddl_block_from_doc())
    )


def test_counted_tables_cover_business_tables() -> None:
    assert COUNTED_TABLES == (
        "schema_migrations",
        "users",
        "rooms",
        "room_members",
        "join_requests",
        "invites",
        "chat_messages",
        "room_hand_raises",
        "room_focus",
    "session_summaries",
    "transcripts",
    )


# ---------- 数据库断言（需要 .env + 本机 PostgreSQL） ----------
#
# 每个用例最多制造一次预期失败，并把它放在用例最后一步：
# 单条语句报错会让当前事务进入 aborted 状态，之后再执行语句只会得到
# InFailedSqlTransaction —— 需要"失败后继续"的语义时，拆成两个用例。

@pytest.fixture()
def room_ctx(db):
    """建一个用户 + 一个房间，返回 (user_id, room_id) 便于各约束用例复用。"""
    db.execute("INSERT INTO users (id, email, display_name, password_hash) VALUES ('u_1', 'u1@example.com', '甲', 'x')")
    db.execute("INSERT INTO users (id, email, display_name, password_hash) VALUES ('u_2', 'u2@example.com', '乙', 'x')")
    db.execute(
        """INSERT INTO rooms (id, host_id, topic, topic_label, title, capacity, room_code)
           VALUES ('r_1', 'u_1', 'custom', '主题', '标题', 8, 'C00001')"""
    )
    return "u_1", "u_2", "r_1"


def test_tables_exist(db) -> None:
    rows = db.execute(
        "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
    ).fetchall()
    existing = {row[0] for row in rows}
    assert set(COUNTED_TABLES) <= existing, sorted(set(COUNTED_TABLES) - existing)


def test_key_columns_exist(db) -> None:
    expected = {
        "users": {"id", "email", "display_name", "password_hash", "created_at"},
        "rooms": {"id", "host_id", "topic", "topic_label", "title", "description", "status", "capacity", "room_code", "created_at", "ended_at"},
        "room_members": {"id", "room_id", "user_id", "role", "status", "exit_reason", "joined_at", "left_at"},
        "join_requests": {"id", "room_id", "user_id", "status", "message", "created_at", "decided_at", "decided_by"},
        "chat_messages": {"id", "room_id", "user_id", "body", "kind", "created_at"},
        "invites": {"id", "room_id", "code", "created_by", "expires_at", "max_uses", "used_count", "created_at"},
    }
    for table, columns in expected.items():
        rows = db.execute(
            "SELECT column_name FROM information_schema.columns WHERE table_name = %s", (table,)
        ).fetchall()
        present = {row[0] for row in rows}
        assert columns <= present, (table, sorted(columns - present))


def test_email_unique_is_case_insensitive(db) -> None:
    db.execute(
        "INSERT INTO users (id, email, display_name, password_hash) VALUES ('u_a', 'A@Example.com', '甲', 'x')"
    )
    with pytest.raises(pg_errors.UniqueViolation):
        db.execute(
            "INSERT INTO users (id, email, display_name, password_hash) VALUES ('u_b', 'a@example.com', '乙', 'x')"
        )


def test_rooms_check_rejects_active_with_ended_at(db, room_ctx) -> None:
    with pytest.raises(pg_errors.CheckViolation):
        db.execute(
            """INSERT INTO rooms (id, host_id, topic, topic_label, title, status, capacity, room_code, ended_at)
               VALUES ('r_bad', 'u_1', 'custom', '主题', '标题', 'active', 8, 'C00002', now())"""
        )


def test_rooms_check_rejects_ended_without_ended_at(db, room_ctx) -> None:
    with pytest.raises(pg_errors.CheckViolation):
        db.execute(
            """INSERT INTO rooms (id, host_id, topic, topic_label, title, status, capacity, room_code)
               VALUES ('r_bad2', 'u_1', 'custom', '主题', '标题', 'ended', 8, 'C00003')"""
        )


def test_rooms_check_rejects_capacity_over_eight(db, room_ctx) -> None:
    with pytest.raises(pg_errors.CheckViolation):
        db.execute(
            """INSERT INTO rooms (id, host_id, topic, topic_label, title, capacity, room_code)
               VALUES ('r_bad3', 'u_1', 'custom', '主题', '标题', 9, 'C00004')"""
        )


def test_member_active_cannot_carry_exit_reason(db, room_ctx) -> None:
    with pytest.raises(pg_errors.CheckViolation):
        db.execute(
            """INSERT INTO room_members (id, room_id, user_id, role, status, exit_reason)
               VALUES ('mem_bad', 'r_1', 'u_1', 'participant', 'active', 'self_leave')"""
        )


def test_member_inactive_requires_reason_and_left_at(db, room_ctx) -> None:
    with pytest.raises(pg_errors.CheckViolation):
        db.execute(
            """INSERT INTO room_members (id, room_id, user_id, role, status)
               VALUES ('mem_bad2', 'r_1', 'u_1', 'participant', 'inactive')"""
        )


def test_active_member_partial_unique_index(db, room_ctx) -> None:
    db.execute("INSERT INTO room_members (id, room_id, user_id, role) VALUES ('mem_1', 'r_1', 'u_2', 'participant')")
    with pytest.raises(pg_errors.UniqueViolation):
        db.execute("INSERT INTO room_members (id, room_id, user_id, role) VALUES ('mem_2', 'r_1', 'u_2', 'host')")


def test_member_can_rejoin_after_leaving(db, room_ctx) -> None:
    db.execute("INSERT INTO room_members (id, room_id, user_id, role) VALUES ('mem_1', 'r_1', 'u_2', 'participant')")
    db.execute(
        """UPDATE room_members SET status = 'inactive', exit_reason = 'self_leave', left_at = now()
           WHERE id = 'mem_1'"""
    )
    db.execute("INSERT INTO room_members (id, room_id, user_id, role) VALUES ('mem_2', 'r_1', 'u_2', 'participant')")
    active = db.execute("SELECT count(*) FROM room_members WHERE room_id = 'r_1' AND status = 'active'").fetchone()[0]
    assert active == 1


def test_pending_join_request_partial_unique_index(db, room_ctx) -> None:
    db.execute("INSERT INTO join_requests (id, room_id, user_id) VALUES ('req_1', 'r_1', 'u_2')")
    with pytest.raises(pg_errors.UniqueViolation):
        db.execute("INSERT INTO join_requests (id, room_id, user_id) VALUES ('req_2', 'r_1', 'u_2')")


def test_join_request_can_resubmit_after_rejection(db, room_ctx) -> None:
    db.execute("INSERT INTO join_requests (id, room_id, user_id) VALUES ('req_1', 'r_1', 'u_2')")
    db.execute(
        """UPDATE join_requests SET status = 'rejected', decided_at = now(), decided_by = 'u_1'
           WHERE id = 'req_1'"""
    )
    db.execute("INSERT INTO join_requests (id, room_id, user_id) VALUES ('req_2', 'r_1', 'u_2')")
    # 只统计本用例的房间/用户：库里还有种子数据（room_demo_* 下有 2 条 pending）
    pending = db.execute(
        "SELECT count(*) FROM join_requests WHERE room_id = 'r_1' AND user_id = 'u_2' AND status = 'pending'"
    ).fetchone()[0]
    assert pending == 1


def test_pending_join_request_cannot_carry_decided_at(db, room_ctx) -> None:
    with pytest.raises(pg_errors.CheckViolation):
        db.execute(
            """INSERT INTO join_requests (id, room_id, user_id, status, decided_at)
               VALUES ('req_bad', 'r_1', 'u_2', 'pending', now())"""
        )


def test_foreign_keys_are_enforced(db, room_ctx) -> None:
    with pytest.raises(pg_errors.ForeignKeyViolation):
        db.execute(
            """INSERT INTO rooms (id, host_id, topic, topic_label, title, capacity, room_code)
               VALUES ('r_fk', 'usr_does_not_exist', 'custom', '主题', '标题', 8, 'C00005')"""
        )


# ---------- r002：R-6 活跃 Host 唯一（003 迁移） ----------

def test_one_active_host_partial_unique_index(db, room_ctx) -> None:
    """同一房间不能出现两个活跃 Host（库级兜底，应用层另有 count_active_hosts 断言）。"""
    db.execute("INSERT INTO room_members (id, room_id, user_id, role) VALUES ('mem_h1', 'r_1', 'u_1', 'host')")
    with pytest.raises(pg_errors.UniqueViolation):
        db.execute("INSERT INTO room_members (id, room_id, user_id, role) VALUES ('mem_h2', 'r_1', 'u_2', 'host')")


def test_inactive_hosts_do_not_conflict(db, room_ctx) -> None:
    """历史 Host 可以并存（部分索引只覆盖 active），否则房间结束后没法追溯。"""
    db.execute(
        """INSERT INTO room_members (id, room_id, user_id, role, status, exit_reason, left_at)
           VALUES ('mem_h1', 'r_1', 'u_1', 'host', 'inactive', 'room_ended', now())"""
    )
    db.execute(
        """INSERT INTO room_members (id, room_id, user_id, role, status, exit_reason, left_at)
           VALUES ('mem_h2', 'r_1', 'u_2', 'host', 'inactive', 'room_ended', now())"""
    )
    hosts = db.execute("SELECT count(*) FROM room_members WHERE room_id = 'r_1' AND role = 'host'").fetchone()[0]
    assert hosts == 2
