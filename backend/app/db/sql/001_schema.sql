-- 001_schema.sql — r001 全部业务表（PostgreSQL 15+）
-- 设计事实源：docs/02-modules/r001-rooms.md §3（本文件与该节 DDL 逐字一致，改动须同步该页）
-- 执行方式：由 app/db/migrate.py 按文件名顺序在单事务内执行，不要手改库

-- 001_schema.sql（逐字落库；PostgreSQL 15+）
CREATE TABLE IF NOT EXISTS schema_migrations (
  version    TEXT PRIMARY KEY,
  applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS users (
  id            TEXT PRIMARY KEY,
  email         TEXT NOT NULL,
  display_name  TEXT NOT NULL CHECK (char_length(display_name) BETWEEN 1 AND 32),
  password_hash TEXT NOT NULL,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX IF NOT EXISTS ux_users_email_lower ON users (lower(email));

CREATE TABLE IF NOT EXISTS rooms (
  id          TEXT PRIMARY KEY,
  host_id     TEXT NOT NULL REFERENCES users(id),
  topic       TEXT NOT NULL CHECK (topic IN ('epicureanism','math-biology','german-history','custom')),
  topic_label TEXT NOT NULL CHECK (char_length(topic_label) BETWEEN 1 AND 32),
  title       TEXT NOT NULL CHECK (char_length(title) BETWEEN 1 AND 80),
  description TEXT NOT NULL DEFAULT '' CHECK (char_length(description) <= 500),
  status      TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','ended')),
  capacity    SMALLINT NOT NULL DEFAULT 8 CHECK (capacity BETWEEN 2 AND 8),
  room_code   TEXT NOT NULL UNIQUE,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  ended_at    TIMESTAMPTZ,
  CHECK ((status = 'active' AND ended_at IS NULL) OR (status = 'ended' AND ended_at IS NOT NULL))
);
CREATE INDEX IF NOT EXISTS ix_rooms_status_created ON rooms (status, created_at DESC);
CREATE INDEX IF NOT EXISTS ix_rooms_topic ON rooms (topic, status);

CREATE TABLE IF NOT EXISTS room_members (
  id          TEXT PRIMARY KEY,
  room_id     TEXT NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,
  user_id     TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  role        TEXT NOT NULL CHECK (role IN ('host','moderator','participant')),
  status      TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','inactive')),
  exit_reason TEXT CHECK (exit_reason IN ('self_leave','kicked','room_ended')),
  joined_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  left_at     TIMESTAMPTZ,
  CHECK ((status = 'active'   AND exit_reason IS NULL     AND left_at IS NULL)
      OR (status = 'inactive' AND exit_reason IS NOT NULL AND left_at IS NOT NULL))
);
CREATE UNIQUE INDEX IF NOT EXISTS ux_room_members_active
  ON room_members (room_id, user_id) WHERE status = 'active';
CREATE INDEX IF NOT EXISTS ix_room_members_room_active ON room_members (room_id, role) WHERE status = 'active';

CREATE TABLE IF NOT EXISTS join_requests (
  id         TEXT PRIMARY KEY,
  room_id    TEXT NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,
  user_id    TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  status     TEXT NOT NULL DEFAULT 'pending'
             CHECK (status IN ('pending','approved','rejected','withdrawn','cancelled')),
  message    TEXT NOT NULL DEFAULT '' CHECK (char_length(message) <= 200),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  decided_at TIMESTAMPTZ,
  decided_by TEXT REFERENCES users(id),
  CHECK ((status = 'pending' AND decided_at IS NULL) OR (status <> 'pending' AND decided_at IS NOT NULL))
);
CREATE UNIQUE INDEX IF NOT EXISTS ux_join_requests_pending
  ON join_requests (room_id, user_id) WHERE status = 'pending';

CREATE TABLE IF NOT EXISTS invites (
  id         TEXT PRIMARY KEY,
  room_id    TEXT NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,
  code       TEXT NOT NULL UNIQUE,
  created_by TEXT NOT NULL REFERENCES users(id),
  expires_at TIMESTAMPTZ NOT NULL,
  max_uses   SMALLINT NOT NULL DEFAULT 8 CHECK (max_uses BETWEEN 1 AND 8),
  used_count SMALLINT NOT NULL DEFAULT 0 CHECK (used_count >= 0),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_invites_room ON invites (room_id, expires_at DESC);

CREATE TABLE IF NOT EXISTS chat_messages (
  id         TEXT PRIMARY KEY,
  room_id    TEXT NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,
  user_id    TEXT NOT NULL REFERENCES users(id),
  body       TEXT NOT NULL CHECK (char_length(body) BETWEEN 1 AND 2000),
  kind       TEXT NOT NULL DEFAULT 'chat' CHECK (kind IN ('chat','system')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_chat_messages_room_time ON chat_messages (room_id, created_at DESC);
