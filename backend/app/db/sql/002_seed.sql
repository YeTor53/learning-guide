-- 002_seed.sql — 演示种子数据（固定 ID + ON CONFLICT DO NOTHING，幂等可重复执行）
-- 设计事实源：docs/02-modules/r001-rooms.md §6（3 个演示账号 / 3 个示例房间 / 12 条历史消息 / 1 个已结束房间）
-- 演示账号口令一律 demo1234（哈希口径见 app/security/password.py：scrypt$N$r$p$salt$hash；仅演示数据）

INSERT INTO users (id, email, display_name, password_hash, created_at) VALUES
  ('usr_demo_host', 'host@example.com', '林泽宇', 'scrypt$16384$8$1$FXOTtCXRZvuWn9VoD_as2g$mgIWDnxex3QH1QjvhqRGP8mDkDMYdHRhZbpnmKka7CU', '2026-09-14 09:00:00+08'),
  ('usr_demo_mod',  'mod@example.com',  '陈慕',   'scrypt$16384$8$1$FXOTtCXRZvuWn9VoD_as2g$mgIWDnxex3QH1QjvhqRGP8mDkDMYdHRhZbpnmKka7CU', '2026-09-14 09:05:00+08'),
  ('usr_demo_part', 'part@example.com', '王一诺', 'scrypt$16384$8$1$FXOTtCXRZvuWn9VoD_as2g$mgIWDnxex3QH1QjvhqRGP8mDkDMYdHRhZbpnmKka7CU', '2026-09-14 09:10:00+08')
ON CONFLICT DO NOTHING;

INSERT INTO rooms (id, host_id, topic, topic_label, title, description, status, capacity, room_code, created_at, ended_at) VALUES
  ('room_demo_epicurus', 'usr_demo_host', 'epicureanism', '哲学', '哲学共读：伊壁鸠鲁的欲望清单',
   '每周一次，先读文本再讨论；本周议题是欲望的三分法。', 'active', 8, 'HK7M2Q', '2026-09-14 10:00:00+08', NULL),
  ('room_demo_mathbio', 'usr_demo_mod', 'math-biology', '生物学', '群体遗传学：哈代-温伯格与漂变',
   '面向跨专业同学，从概率模型讲起。', 'active', 6, 'RT4XW9', '2026-09-15 14:30:00+08', NULL),
  ('room_demo_history', 'usr_demo_host', 'german-history', '世界史', '魏玛共和国到第三帝国',
   '已结束的示例房间，用于演示结束后只读形态。', 'ended', 4, 'BQ6NP3', '2026-09-10 19:00:00+08', '2026-09-15 21:00:00+08')
ON CONFLICT DO NOTHING;

INSERT INTO room_members (id, room_id, user_id, role, status, exit_reason, joined_at, left_at) VALUES
  ('mem_0001', 'room_demo_epicurus', 'usr_demo_host', 'host',        'active',   NULL,         '2026-09-14 10:00:00+08', NULL),
  ('mem_0002', 'room_demo_epicurus', 'usr_demo_mod',  'moderator',   'active',   NULL,         '2026-09-14 10:20:00+08', NULL),
  ('mem_0003', 'room_demo_mathbio',  'usr_demo_mod',  'host',        'active',   NULL,         '2026-09-15 14:30:00+08', NULL),
  ('mem_0004', 'room_demo_mathbio',  'usr_demo_part', 'participant', 'active',   NULL,         '2026-09-15 14:40:00+08', NULL),
  ('mem_0005', 'room_demo_history',  'usr_demo_host', 'host',        'inactive', 'room_ended', '2026-09-10 19:00:00+08', '2026-09-15 21:00:00+08'),
  ('mem_0006', 'room_demo_history',  'usr_demo_mod',  'participant', 'inactive', 'room_ended', '2026-09-10 19:10:00+08', '2026-09-15 21:00:00+08')
ON CONFLICT DO NOTHING;

INSERT INTO join_requests (id, room_id, user_id, status, message, created_at, decided_at, decided_by) VALUES
  ('req_0001', 'room_demo_epicurus', 'usr_demo_part', 'pending',  '读过前三章，想参加本周的讨论。', '2026-09-16 09:00:00+08', NULL, NULL),
  ('req_0002', 'room_demo_mathbio',  'usr_demo_host', 'pending',  '想补一下群体遗传学的概率部分。', '2026-09-16 09:30:00+08', NULL, NULL),
  ('req_0003', 'room_demo_history',  'usr_demo_part', 'rejected', '对魏玛共和国很感兴趣。', '2026-09-11 08:00:00+08', '2026-09-11 09:00:00+08', 'usr_demo_host')
ON CONFLICT DO NOTHING;

INSERT INTO chat_messages (id, room_id, user_id, body, kind, created_at) VALUES
  ('msg_0001', 'room_demo_epicurus', 'usr_demo_host', '今天从欲望的三分法开始：自然且必要、自然但不必要、既不自然也不必要。', 'chat', '2026-09-15 19:00:10+08'),
  ('msg_0002', 'room_demo_epicurus', 'usr_demo_mod',  '那「学习」算哪一类？我总觉得它必要，但有人说是后天养成的。', 'chat', '2026-09-15 19:01:20+08'),
  ('msg_0003', 'room_demo_epicurus', 'usr_demo_host', '我会把它放在「自然且必要」，因为它去掉的是无知带来的恐惧。', 'chat', '2026-09-15 19:02:05+08'),
  ('msg_0004', 'room_demo_epicurus', 'usr_demo_mod',  '那名声和权力就是第三类了？', 'chat', '2026-09-15 19:03:40+08'),
  ('msg_0005', 'room_demo_epicurus', 'usr_demo_host', '对，而且它们没有自然上限，所以永远填不满。', 'chat', '2026-09-15 19:05:00+08'),
  ('msg_0006', 'room_demo_epicurus', 'usr_demo_mod',  '友谊在这一套里为什么被算作最大的快乐？', 'chat', '2026-09-15 19:06:30+08'),
  ('msg_0007', 'room_demo_epicurus', 'usr_demo_host', '因为它是唯一既自然又必要、还能互相加固的快乐。', 'chat', '2026-09-15 19:08:10+08'),
  ('msg_0008', 'room_demo_epicurus', 'usr_demo_mod',  '下次我想接着讲「死亡与我无关」这条论证。', 'chat', '2026-09-15 19:10:00+08'),
  ('msg_0009', 'room_demo_mathbio',  'usr_demo_mod',  '开场：为什么小种群里漂变比选择更强？', 'chat', '2026-09-16 14:00:00+08'),
  ('msg_0010', 'room_demo_mathbio',  'usr_demo_part', '因为有效群体大小 Ne 小，抽样误差大？', 'chat', '2026-09-16 14:01:15+08'),
  ('msg_0011', 'room_demo_mathbio',  'usr_demo_mod',  '对，写一下 p 的方差和 1/(2Ne) 的关系。', 'chat', '2026-09-16 14:02:30+08'),
  ('msg_0012', 'room_demo_mathbio',  'usr_demo_part', '推到一半卡住了，回去补概率论。', 'chat', '2026-09-16 14:05:00+08')
ON CONFLICT DO NOTHING;
