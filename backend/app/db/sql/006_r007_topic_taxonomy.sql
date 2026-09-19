-- 006_r007_topic_taxonomy.sql —— r007：主题白名单扩容（3 个原有项保持在前 3 位）
-- 背景：主题清单被 001_schema.sql 的 CHECK 约束锁死；本轮新增 10 个主题（少 AI、补哲学/历史/数学），
--       必须重建成约束才能写入。**不改历史迁移文件**（AGENTS 硬规矩）。
-- 顺序即展示顺序：前 3 项为用户指定保留的原有主题，最后一项为「自定义」。
-- 幂等：DROP IF EXISTS + ADD 可重复执行。
ALTER TABLE rooms DROP CONSTRAINT IF EXISTS rooms_topic_check;
ALTER TABLE rooms ADD CONSTRAINT rooms_topic_check CHECK (topic IN (
  'epicureanism',
  'math-biology',
  'german-history',
  'philosophy-history',
  'chinese-philosophy',
  'ethics',
  'modern-history',
  'ancient-china',
  'mathematical-analysis',
  'linear-algebra',
  'probability-statistics',
  'number-theory',
  'machine-learning',
  'custom'
));
