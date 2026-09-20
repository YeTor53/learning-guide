-- 007_r008_session_summaries.sql —— r008：讨论纪要（作业必做「会后产出」+ 数据层清单里的 session_summaries）
-- 一间房一份（room_id 唯一索引，重复生成 = 覆盖写，created_at 保留首次、updated_at 前进）
-- 时间戳用 clock_timestamp()（语句级，见 005 的教训：now() 是事务级，同事务多行会打平）
CREATE TABLE IF NOT EXISTS session_summaries (
  id           TEXT PRIMARY KEY,
  room_id      TEXT NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,
  status       TEXT NOT NULL CHECK (status IN ('ready','failed')),
  provider     TEXT NOT NULL DEFAULT '',
  model        TEXT NOT NULL DEFAULT '',
  input_digest TEXT NOT NULL DEFAULT '',
  content      TEXT NOT NULL DEFAULT '',
  error        TEXT,
  created_by   TEXT REFERENCES users(id),
  created_at   TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
  updated_at   TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);
CREATE UNIQUE INDEX IF NOT EXISTS ux_session_summaries_room ON session_summaries (room_id);
