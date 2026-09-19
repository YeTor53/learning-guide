-- r004（M3）房内扩展能力：举手与焦点
-- 设计事实源：docs/rounds/r004-room-extras/design.md §3；接口 §4；函数 §5

-- 举手：一次举手一行；lowered_* 为空表示「正在举手」（部分唯一索引保证幂等）
CREATE TABLE IF NOT EXISTS room_hand_raises (
  id             TEXT PRIMARY KEY,
  room_id        TEXT NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,
  user_id        TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  raised_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  lowered_at     TIMESTAMPTZ NULL,
  lowered_by     TEXT NULL,                 -- 操作人 user_id；房间结束为 'system'
  lowered_reason TEXT NULL CHECK (lowered_reason IN ('self','other','room_ended')),
  CHECK ((lowered_at IS NULL) = (lowered_reason IS NULL))
);

-- 同一人在同一房间只能有一条活跃举手（重复举手幂等）
CREATE UNIQUE INDEX IF NOT EXISTS uq_room_hand_active
  ON room_hand_raises (room_id, user_id) WHERE lowered_at IS NULL;

-- 快照查询：按房间取活跃举手，按举手时间升序
CREATE INDEX IF NOT EXISTS ix_room_hand_active
  ON room_hand_raises (room_id, raised_at) WHERE lowered_at IS NULL;

-- 焦点：事件流（一行一次设置/取消）；subject 为空表示「取消焦点」
CREATE TABLE IF NOT EXISTS room_focus (
  id              TEXT PRIMARY KEY,
  room_id         TEXT NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,
  subject_user_id TEXT NULL REFERENCES users(id) ON DELETE SET NULL,
  actor_user_id   TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 当前焦点 = 最新一行
CREATE INDEX IF NOT EXISTS ix_room_focus_time ON room_focus (room_id, created_at DESC);
