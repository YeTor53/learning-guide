-- 012_r012_seed_superadmin.sql — r012 演示超管账号（幂等；口令口径同其它演示账号 demo1234）
-- 设计事实源：docs/rounds/r012-superadmin-console/design.md §2.5
-- 重复执行会把该账号的角色重置为 superadmin（演示账号口径）；正式提权/降权用 backend/scripts/grant_superadmin.py。
INSERT INTO users (id, email, display_name, password_hash, role, created_at) VALUES
  ('usr_demo_admin', 'admin@example.com', '平台管理员',
   'scrypt$16384$8$1$FXOTtCXRZvuWn9VoD_as2g$mgIWDnxex3QH1QjvhqRGP8mDkDMYdHRhZbpnmKka7CU',
   'superadmin', '2026-09-14 09:15:00+08')
ON CONFLICT (id) DO UPDATE SET role = EXCLUDED.role;
