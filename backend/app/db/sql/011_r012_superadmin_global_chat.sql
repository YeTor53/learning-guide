-- 011_r012_superadmin_global_chat.sql — r012：超管身份 / 在册旁路 / 全服大屏聊天 / 管理审计
-- 设计事实源：docs/rounds/r012-superadmin-console/design.md §1（改动须同步 docs/02-modules/r012-superadmin-console.md）
-- 说明：全部为**新增**列/表，旧代码不读它们即可继续工作（回退友好，见 design §8）。

-- Q1①：超管身份落在 users（单列，零新表）
ALTER TABLE users ADD COLUMN IF NOT EXISTS role TEXT NOT NULL DEFAULT 'user'
  CHECK (role IN ('user','superadmin'));

-- Q14②：在线口径 = 前端定时上报的心跳时间（写入点：POST /api/presence）
ALTER TABLE users ADD COLUMN IF NOT EXISTS last_seen_at TIMESTAMPTZ;
CREATE INDEX IF NOT EXISTS ix_users_last_seen ON users (last_seen_at DESC);

-- Q2①：超管不写 room_members；进出记旁路表（天然隐身、天然不占人数）
CREATE TABLE IF NOT EXISTS room_visits (
  id         TEXT PRIMARY KEY,
  room_id    TEXT NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,
  user_id    TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  entered_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
  left_at    TIMESTAMPTZ,
  hidden     BOOLEAN NOT NULL DEFAULT true
);
CREATE UNIQUE INDEX IF NOT EXISTS ux_room_visits_open
  ON room_visits (room_id, user_id) WHERE left_at IS NULL;

-- C 组：全服大屏聊天（不复用 room_id NOT NULL 的 chat_messages）
CREATE TABLE IF NOT EXISTS global_messages (
  id         TEXT PRIMARY KEY,
  user_id    TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  body       TEXT NOT NULL CHECK (char_length(body) BETWEEN 1 AND 500),
  created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);
CREATE INDEX IF NOT EXISTS ix_global_messages_time ON global_messages (created_at DESC);
-- 限流走库计数（重启不放大额度）：按 (user_id, created_at) 建索引
CREATE INDEX IF NOT EXISTS ix_global_messages_user_time ON global_messages (user_id, created_at DESC);

-- Q7①：管理动作审计（**故意不 FK 到 rooms**：删房后流水仍在，target_id 允许悬空）
CREATE TABLE IF NOT EXISTS admin_audit (
  id          TEXT PRIMARY KEY,
  actor_id    TEXT REFERENCES users(id) ON DELETE SET NULL,
  action      TEXT NOT NULL,
  target_type TEXT NOT NULL CHECK (target_type IN ('room','user','summary')),
  target_id   TEXT NOT NULL,
  detail      JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);
CREATE INDEX IF NOT EXISTS ix_admin_audit_time ON admin_audit (created_at DESC);
