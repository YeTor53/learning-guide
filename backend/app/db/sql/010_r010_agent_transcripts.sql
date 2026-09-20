-- r010 · 换轨（ADR-0023）：转写改由 Agents worker 识别，前端回传**最终稿文本段**落库
-- 幂等键：官方 TranscriptionSegment.id（前端上报的 externalId）；同一段被多端冗余上报也只落一行（谁先到谁落）
ALTER TABLE transcripts ADD COLUMN IF NOT EXISTS external_id TEXT;

-- 注意：不用部分索引——PostgreSQL 的 ON CONFLICT 推断对部分索引要求带谓词，全量唯一索引更简单；
-- NULL 在唯一索引里互不冲突，故 B 路径（无 external_id）的历史/新行不受影响。
CREATE UNIQUE INDEX IF NOT EXISTS ux_transcripts_external ON transcripts (room_id, external_id);

-- A 路径没有"本端分段序号"；B 路径仍会填
ALTER TABLE transcripts ALTER COLUMN segment_index DROP NOT NULL;
