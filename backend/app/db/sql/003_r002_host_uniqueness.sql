-- 003_r002_host_uniqueness.sql —— r002 · R-6：活跃 Host 唯一（部分唯一索引）
-- 设计事实源：docs/02-modules/r002-livekit.md §3、docs/00-requirements/r002-livekit-room.md §7 R-6
-- 目的：并发「移交房主」也造不出双 Host（应用层另有 count_active_hosts 不变量断言，这里是库级兜底）
-- 可重复执行（幂等）。
BEGIN;

CREATE UNIQUE INDEX IF NOT EXISTS ux_room_members_one_active_host
    ON room_members (room_id)
    WHERE status = 'active' AND role = 'host';

COMMIT;
