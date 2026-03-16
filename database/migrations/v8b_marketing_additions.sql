-- v8b: Маркетинг — дополнения по новому ТЗ
-- source_code на постах (прозрачность данных, ТЗ п.1)

ALTER TABLE mk_posts
  ADD COLUMN IF NOT EXISTS source_code TEXT NOT NULL DEFAULT 'manual';

COMMENT ON COLUMN mk_posts.source_code IS
  'Источник поста: manual | ai_generated | external_source | archive';

-- Индекс для фильтрации по источнику
CREATE INDEX IF NOT EXISTS idx_mk_posts_source_code ON mk_posts (source_code);
