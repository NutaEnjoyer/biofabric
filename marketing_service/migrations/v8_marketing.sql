--  ERP-Биофабрика — Маркетинг
--  Файл: v8_marketing.sql
--  База: PostgreSQL 13+
--  Требует: v1_core_schema.sql (ядро), v2_ook_docflow.sql (ООК)
--  Назначение: контент-план, посты, каналы, рубрики/форматы, whitelist источников,
--              клиппинги, статусная модель, календарь и аналитические VIEW.
--  Хранение контента постов: ГИБРИД — каноничный текст в БД (mk_post_contents),
--              опционально документ ООК, помеченный биндингом (v_mk_post_docs).
--  Идемпотентность: да
--

BEGIN;

-- ------------------------------------------------
-- 1) Справочники: направления, каналы, рубрики, форматы, статусы
-- ------------------------------------------------
CREATE TABLE IF NOT EXISTS mk_directions (
    direction_id BIGSERIAL PRIMARY KEY,
    name         TEXT NOT NULL UNIQUE,
    description  TEXT
);
COMMENT ON TABLE mk_directions IS 'Направления бизнеса/контент-потоки для контент-плана.';

CREATE TABLE IF NOT EXISTS mk_channels (
    channel_id BIGSERIAL PRIMARY KEY,
    name       TEXT NOT NULL UNIQUE,          -- 'website','blog','linkedin','instagram','telegram', ...
    description TEXT
);
COMMENT ON TABLE mk_channels IS 'Каналы публикаций.';

CREATE TABLE IF NOT EXISTS mk_topics (
    topic_id   BIGSERIAL PRIMARY KEY,
    name       TEXT NOT NULL UNIQUE,
    description TEXT
);
COMMENT ON TABLE mk_topics IS 'Рубрики/тематики контента.';

CREATE TABLE IF NOT EXISTS mk_formats (
    format_id  BIGSERIAL PRIMARY KEY,
    name       TEXT NOT NULL UNIQUE,          -- 'text','news','infographic','video','case','press'
    description TEXT
);
COMMENT ON TABLE mk_formats IS 'Форматы контента.';

CREATE TABLE IF NOT EXISTS mk_post_statuses (
    status_code  TEXT PRIMARY KEY,            -- 'draft','in_progress','approved','scheduled','published','archived'
    display_name TEXT NOT NULL
);
COMMENT ON TABLE mk_post_statuses IS 'Статусы подготовки/жизненного цикла постов.';

INSERT INTO mk_post_statuses(status_code, display_name)
SELECT v.status_code, v.display_name
FROM (VALUES
  ('draft','Черновик'),
  ('in_progress','В работе'),
  ('approved','Утверждён'),
  ('scheduled','Запланирован'),
  ('published','Опубликован'),
  ('archived','Архив')
) AS v(status_code, display_name)
LEFT JOIN mk_post_statuses s ON s.status_code = v.status_code
WHERE s.status_code IS NULL;

-- ------------------------------------------------
-- 2) Задачи генерации контент-плана (ИИ)
-- ------------------------------------------------
CREATE TABLE IF NOT EXISTS mk_plan_jobs (
    job_id       BIGSERIAL PRIMARY KEY,
    period_start DATE NOT NULL,
    period_end   DATE NOT NULL,
    direction_id BIGINT REFERENCES mk_directions(direction_id) ON DELETE SET NULL,
    audience     TEXT,                       -- описание ЦА
    goals        TEXT,                       -- цели публикаций
    tone         TEXT,                       -- tone of voice
    status       TEXT NOT NULL DEFAULT 'pending',   -- 'pending','running','done','failed'
    created_by   BIGINT REFERENCES app_users(user_id),
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at  TIMESTAMPTZ
);
COMMENT ON TABLE mk_plan_jobs IS 'Задачи на ИИ-генерацию контент-плана (период/направление/ЦА/цели/тон).';

-- ------------------------------------------------
-- 3) Посты (метаданные) + связь с документами ООК (опционально)
-- ------------------------------------------------
CREATE TABLE IF NOT EXISTS mk_posts (
    post_id      BIGSERIAL PRIMARY KEY,
    title        TEXT,
    direction_id BIGINT REFERENCES mk_directions(direction_id) ON DELETE SET NULL,
    topic_id     BIGINT REFERENCES mk_topics(topic_id) ON DELETE SET NULL,
    format_id    BIGINT REFERENCES mk_formats(format_id) ON DELETE SET NULL,
    channel_id   BIGINT REFERENCES mk_channels(channel_id) ON DELETE SET NULL,
    audience     TEXT,
    goals        TEXT,
    tone         TEXT,
    status_code  TEXT NOT NULL REFERENCES mk_post_statuses(status_code),
    planned_for  DATE,
    planned_time TIME,
    document_id  BIGINT REFERENCES documents(document_id), -- опционально: документ ООК для «богатого» документооборота
    approved_at  TIMESTAMPTZ,
    published_at TIMESTAMPTZ,
    external_url TEXT,
    created_by   BIGINT REFERENCES app_users(user_id),
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at   TIMESTAMPTZ
);
COMMENT ON TABLE mk_posts IS 'Карточка публикации: атрибуты календаря/статуса; документ ООК — опционально.';

-- ------------------------------------------------
-- 5) Whitelist источников и клиппинги (внешние материалы)
-- ------------------------------------------------
CREATE TABLE IF NOT EXISTS mk_sources (
    source_id   BIGSERIAL PRIMARY KEY,
    name        TEXT NOT NULL,
    url         TEXT NOT NULL,
    kind        TEXT,                         -- 'rss','site','media'
    approved    BOOLEAN NOT NULL DEFAULT TRUE,
    UNIQUE (url)
);
COMMENT ON TABLE mk_sources IS 'Разрешённые внешние источники (whitelist) для сбора отраслевого контента.';

CREATE TABLE IF NOT EXISTS mk_clippings (
    clipping_id BIGSERIAL PRIMARY KEY,
    source_id   BIGINT REFERENCES mk_sources(source_id) ON DELETE SET NULL,
    url         TEXT NOT NULL,
    title       TEXT,
    fetched_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    document_id BIGINT REFERENCES documents(document_id),  -- рерайт/конспект в ООК (если сделан)
    UNIQUE (url)
);
COMMENT ON TABLE mk_clippings IS 'Собранные материалы из внешних источников; при рерайте — документ в ООК.';

CREATE INDEX IF NOT EXISTS idx_mk_posts_status     ON mk_posts(status_code);
CREATE INDEX IF NOT EXISTS idx_mk_posts_calendar   ON mk_posts(planned_for);
CREATE INDEX IF NOT EXISTS idx_mk_posts_channel    ON mk_posts(channel_id);
CREATE INDEX IF NOT EXISTS idx_mk_posts_direction  ON mk_posts(direction_id);

-- ------------------------------------------------
-- 4) [ГИБРИД] Каноничный контент поста в БД
-- ------------------------------------------------
CREATE TABLE IF NOT EXISTS mk_post_contents (
    content_id         BIGSERIAL PRIMARY KEY,
    post_id            BIGINT NOT NULL UNIQUE REFERENCES mk_posts(post_id) ON DELETE CASCADE,
    body_md            TEXT NOT NULL,                  -- основной текст (Markdown/HTML — по договорённости)
    hashtags           TEXT[],                         -- #теги
    extras             JSONB,                          -- мета: варианты заголовков, CTA, SEO, медиа и пр.
    generated_by       TEXT NOT NULL DEFAULT 'manual', -- 'ai','rewrite','manual'
    source_clipping_id BIGINT REFERENCES mk_clippings(clipping_id),
    updated_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);
COMMENT ON TABLE mk_post_contents IS 'Каноничный текст/хэштеги поста (SQL-поиск/аналитика); ООК-документ — опционален.';

CREATE INDEX IF NOT EXISTS idx_mk_post_contents_updated_at ON mk_post_contents(updated_at DESC);
CREATE INDEX IF NOT EXISTS gin_mk_post_contents_hashtags  ON mk_post_contents USING GIN (hashtags);
CREATE INDEX IF NOT EXISTS gin_mk_post_contents_extras    ON mk_post_contents USING GIN (extras);



-- ------------------------------------------------
-- 6) VIEW: только «постовые» документы ООК (чистая выборка)
-- ------------------------------------------------
CREATE OR REPLACE VIEW v_mk_post_docs AS
SELECT
    d.document_id,
    b.object_id      AS post_id,
    d.title,
    d.created_at,
    d.created_at AS updated_at,
    d.created_by AS author_user_id
FROM document_bindings b
JOIN documents d ON d.document_id = b.document_id
WHERE b.object_type = 'mk_post';


-- ------------------------------------------------
-- 7) Аналитические VIEW (план/распределение/нагрузка/гепы/дедлайны)
-- ------------------------------------------------
CREATE OR REPLACE VIEW v_mk_plan_summary AS
SELECT
  date_trunc('day', p.planned_for::timestamp) AS day,
  c.name AS channel,
  p.status_code,
  count(*) AS posts
FROM mk_posts p
LEFT JOIN mk_channels c ON c.channel_id = p.channel_id
WHERE p.planned_for IS NOT NULL
GROUP BY 1,2,3
ORDER BY 1,2,3;

CREATE OR REPLACE VIEW v_mk_distribution_by_topic AS
SELECT t.name AS topic, p.status_code, count(*) AS posts
FROM mk_posts p
LEFT JOIN mk_topics t ON t.topic_id = p.topic_id
GROUP BY 1,2
ORDER BY 1,2;

CREATE OR REPLACE VIEW v_mk_distribution_by_format AS
SELECT f.name AS format, p.status_code, count(*) AS posts
FROM mk_posts p
LEFT JOIN mk_formats f ON f.format_id = p.format_id
GROUP BY 1,2
ORDER BY 1,2;

CREATE OR REPLACE VIEW v_mk_distribution_by_channel AS
SELECT c.name AS channel, p.status_code, count(*) AS posts
FROM mk_posts p
LEFT JOIN mk_channels c ON c.channel_id = p.channel_id
GROUP BY 1,2
ORDER BY 1,2;

CREATE OR REPLACE VIEW v_mk_calendar_density AS
SELECT p.planned_for AS day, count(*) AS posts_planned
FROM mk_posts p
WHERE p.planned_for IS NOT NULL
GROUP BY 1
ORDER BY 1;

CREATE OR REPLACE VIEW v_mk_upcoming_week_gaps AS
WITH days AS (
  SELECT generate_series(CURRENT_DATE, CURRENT_DATE + INTERVAL '6 days', INTERVAL '1 day')::date AS d
),
day_channel AS (
  SELECT d.d, c.channel_id, c.name AS channel
  FROM days d CROSS JOIN mk_channels c
),
plan AS (
  SELECT p.planned_for::date AS d, p.channel_id, count(*) AS cnt
  FROM mk_posts p
  WHERE p.planned_for BETWEEN CURRENT_DATE AND CURRENT_DATE + INTERVAL '6 days'
  GROUP BY 1,2
)
SELECT dc.d AS day, dc.channel, coalesce(pl.cnt, 0) AS planned_posts
FROM day_channel dc
LEFT JOIN plan pl ON pl.d = dc.d AND pl.channel_id = dc.channel_id
WHERE coalesce(pl.cnt, 0) = 0
ORDER BY 1,2;

CREATE OR REPLACE VIEW v_mk_posts_due_3d AS
SELECT p.*
FROM mk_posts p
WHERE p.status_code IN ('approved','scheduled')
  AND p.planned_for IS NOT NULL
  AND p.planned_for <= CURRENT_DATE + INTERVAL '3 days';

-- ------------------------------------------------
-- 8) Базовые справочники (seed data)
-- ------------------------------------------------
INSERT INTO mk_directions(name) VALUES ('Основное') ON CONFLICT (name) DO NOTHING;

INSERT INTO mk_channels(name) VALUES
    ('Telegram'), ('ВКонтакте'), ('Сайт') ON CONFLICT (name) DO NOTHING;

INSERT INTO mk_topics(name) VALUES
    ('Новости'), ('Имиджевые'), ('Продуктовые') ON CONFLICT (name) DO NOTHING;

INSERT INTO mk_formats(name) VALUES
    ('Пост'), ('История'), ('Статья'), ('Рассылка') ON CONFLICT (name) DO NOTHING;

-- ------------------------------------------------
-- 9) Фиксация применения миграции
-- ------------------------------------------------
INSERT INTO schema_migrations(version, description)
SELECT 'v8_marketing',
       'Маркетинг: план/посты/справочники/источники; гибрид-контент (mk_post_contents + опциональный ООК), вьюха v_mk_post_docs, аналитические VIEW.'
WHERE NOT EXISTS (SELECT 1 FROM schema_migrations WHERE version = 'v8_marketing');

COMMIT;


