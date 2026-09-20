-- r009 · 协管焦点申请（ADR-0021 D2）
-- 口径（用户 2026-09-19）：协管想得焦点需**另一个非本人的**管理身份批准；房主可直接取得焦点（不走此表）。
CREATE TABLE IF NOT EXISTS focus_requests (
  id TEXT PRIMARY KEY,
  room_id TEXT NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,
  requester_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  status TEXT NOT NULL CHECK (status IN ('pending', 'approved', 'rejected', 'cancelled')),
  decided_by TEXT REFERENCES users(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
  decided_at TIMESTAMPTZ
);

-- 同一房间同一个人同时只能有一条待批申请（并发点两次 → 幂等拿到同一条）
CREATE UNIQUE INDEX IF NOT EXISTS ux_focus_requests_pending
  ON focus_requests (room_id, requester_id) WHERE status = 'pending';

CREATE INDEX IF NOT EXISTS ix_focus_requests_room_status ON focus_requests (room_id, status);
