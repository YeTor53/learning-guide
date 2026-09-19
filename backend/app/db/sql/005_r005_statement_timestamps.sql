-- 005_r005_statement_timestamps.sql —— r005：把「默认时间戳」从 now() 改为 clock_timestamp()
-- 背景（实测）：Postgres 的 now() = **事务开始时间**，同一事务里插入的多行会拿到**完全相同**的时间戳；
--   于是「按 created_at 排序」在这些行之间退化为随机（消息顺序、当前焦点、举手顺序都会受影响）。
--   r005 的用例抓到了这一点（房间事件系统消息与普通消息在同一事务里写）。
-- 口径：这些表的时间列语义 = 「这一行是什么时候写进去的」，所以用 clock_timestamp()（语句级）。
-- 幂等：ALTER ... SET DEFAULT 可重复执行；不改写已有数据。
BEGIN;

ALTER TABLE chat_messages    ALTER COLUMN created_at SET DEFAULT clock_timestamp();
ALTER TABLE room_focus       ALTER COLUMN created_at SET DEFAULT clock_timestamp();
ALTER TABLE room_hand_raises ALTER COLUMN raised_at  SET DEFAULT clock_timestamp();
ALTER TABLE room_members     ALTER COLUMN joined_at  SET DEFAULT clock_timestamp();
ALTER TABLE join_requests    ALTER COLUMN created_at SET DEFAULT clock_timestamp();
ALTER TABLE rooms            ALTER COLUMN created_at SET DEFAULT clock_timestamp();

COMMIT;
