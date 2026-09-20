-- r010 · 语音转文字片段（ADR-0022 路径 B：本端麦克风采集 → 自有后端 STT → 只落最终稿）
-- 口径（用户 2026-09-19 + r010 需求单）：默认开启、说的话并入「文字对话」、与成员进出等管理信息同流；
--   只落最终稿（final 字段保留以对齐官方 TranscriptionSegment 契约）；音频不落盘、不存原始音频。
CREATE TABLE IF NOT EXISTS transcripts (
  id            TEXT PRIMARY KEY,
  room_id       TEXT NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,
  speaker_id    TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  segment_index INTEGER NOT NULL CHECK (segment_index >= 0),
  text          TEXT NOT NULL CHECK (length(text) > 0),
  language      TEXT NOT NULL DEFAULT 'zh',
  started_at    TIMESTAMPTZ NOT NULL,
  duration_ms   INTEGER NOT NULL CHECK (duration_ms > 0),
  final         BOOLEAN NOT NULL DEFAULT TRUE,
  provider      TEXT NOT NULL DEFAULT '',
  model         TEXT NOT NULL DEFAULT '',
  created_at    TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);

-- 同一人同一段重传 → 幂等（不新增行；客户端重试不会产生重复转写）
CREATE UNIQUE INDEX IF NOT EXISTS ux_transcripts_segment ON transcripts (room_id, speaker_id, segment_index);

-- 三源合一的排序键
CREATE INDEX IF NOT EXISTS ix_transcripts_room_time ON transcripts (room_id, started_at);
