--  ERP-Биофабрика — Карантинирование животных
--  Файл: v10_quarantine_animals.sql
--  База: PostgreSQL 13+
--  Требует: v1_core_schema.sql (ядро), v2_ook_docflow.sql (для хранения исходных файлов импорта)
--  Назначение: виды/срезы (возраст/масса), направления, группы-каталог и динамические когорты,
--              журнал операций (агрегаты), статусы, аналитические VIEW, импорт (с хранением файла).
--  Принципы: накопительный ввод; допускается одновременное наличие возраста и массы для вида;
--            группировка через каталог и когорты; оповещения — только в UI.
--  Идемпотентность: да


BEGIN;

-- ------------------------------------------------
-- 1) Виды и срезы (возраст/масса)
-- ------------------------------------------------
CREATE TABLE IF NOT EXISTS qa_species (
    species_id   BIGSERIAL PRIMARY KEY,
    name         TEXT NOT NULL UNIQUE,
    code         TEXT UNIQUE,
    has_age_categories BOOLEAN NOT NULL DEFAULT FALSE,
    has_mass_bins     BOOLEAN NOT NULL DEFAULT FALSE
);
COMMENT ON TABLE qa_species IS 'Справочник видов; флаги, требуются ли возрастные/весовые срезы.';

CREATE TABLE IF NOT EXISTS qa_age_categories (
    age_cat_id   BIGSERIAL PRIMARY KEY,
    species_id   BIGINT NOT NULL REFERENCES qa_species(species_id) ON DELETE CASCADE,
    name         TEXT NOT NULL,
    min_age_days INT,
    max_age_days INT,
    UNIQUE (species_id, name)
);
COMMENT ON TABLE qa_age_categories IS 'Возрастные категории; применимы, если у вида has_age_categories=TRUE.';

CREATE TABLE IF NOT EXISTS qa_mass_bins (
    mass_bin_id  BIGSERIAL PRIMARY KEY,
    species_id   BIGINT NOT NULL REFERENCES qa_species(species_id) ON DELETE CASCADE,
    name         TEXT NOT NULL,
    min_grams    INT,
    max_grams    INT,
    UNIQUE (species_id, name)
);
COMMENT ON TABLE qa_mass_bins IS 'Весовые диапазоны; применимы, если у вида has_mass_bins=TRUE.';

-- ------------------------------------------------
-- 2) Направления, группы-каталог и динамические когорты
-- ------------------------------------------------
CREATE TABLE IF NOT EXISTS qa_directions (
    direction_id BIGSERIAL PRIMARY KEY,
    code         TEXT NOT NULL UNIQUE,    -- 'subsidiary','vivarium'
    name         TEXT NOT NULL
);
COMMENT ON TABLE qa_directions IS 'Направления учёта: подсобное хозяйство / виварий.';

INSERT INTO qa_directions(code, name)
SELECT v.code, v.name
FROM (VALUES ('subsidiary','Подсобное хозяйство'), ('vivarium','Виварий')) AS v(code, name)
LEFT JOIN qa_directions d ON d.code = v.code
WHERE d.code IS NULL;

-- Каталог групп (устойчивые «типы/категории» групп для вида/направления)
CREATE TABLE IF NOT EXISTS qa_groups (
    group_id     BIGSERIAL PRIMARY KEY,
    direction_id BIGINT NOT NULL REFERENCES qa_directions(direction_id) ON DELETE CASCADE,
    species_id   BIGINT REFERENCES qa_species(species_id) ON DELETE SET NULL,
    name         TEXT NOT NULL,
    UNIQUE (direction_id, species_id, name)
);
COMMENT ON TABLE qa_groups IS 'Каталог (референсные) группы для вида/направления.';

-- Динамические когорты (живые группы учёта — меняются во времени)
CREATE TABLE IF NOT EXISTS qa_cohorts (
    cohort_id    BIGSERIAL PRIMARY KEY,
    direction_id BIGINT NOT NULL REFERENCES qa_directions(direction_id) ON DELETE CASCADE,
    species_id   BIGINT REFERENCES qa_species(species_id) ON DELETE SET NULL,
    label        TEXT NOT NULL,           -- произвольное имя когорты
    status_tag   TEXT,                    -- опц.: «карантин», «наблюдение», «основная» и т.п.
    is_active    BOOLEAN NOT NULL DEFAULT TRUE,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (direction_id, species_id, label)
);
COMMENT ON TABLE qa_cohorts IS 'Динамические группы учёта (когорты) с произвольным статус-тегом.';

-- ------------------------------------------------
-- 3) Статусы записей и типы операций
-- ------------------------------------------------
CREATE TABLE IF NOT EXISTS qa_record_statuses (
    status_code  TEXT PRIMARY KEY,        -- 'in_process','current','archived'
    display_name TEXT NOT NULL
);
COMMENT ON TABLE qa_record_statuses IS 'Статусы строк журнала: в обработке / актуальная / архивная.';

INSERT INTO qa_record_statuses(status_code, display_name)
SELECT v.status_code, v.display_name
FROM (VALUES
  ('in_process','В обработке'),
  ('current','Актуальная'),
  ('archived','Архивная')
) AS v(status_code, display_name)
LEFT JOIN qa_record_statuses s ON s.status_code = v.status_code
WHERE s.status_code IS NULL;

CREATE TABLE IF NOT EXISTS qa_entry_types (
    entry_type TEXT PRIMARY KEY           -- 'intake','withdrawal','movement_in','movement_out','adjustment','issue_for_control'
);
COMMENT ON TABLE qa_entry_types IS 'Типы операций (приход/расход/перемещения/корректировки/выдача на контроль).';

INSERT INTO qa_entry_types(entry_type)
SELECT v.entry_type
FROM (VALUES
  ('intake'),
  ('withdrawal'),
  ('movement_in'),
  ('movement_out'),
  ('adjustment'),
  ('issue_for_control')
) AS v(entry_type)
LEFT JOIN qa_entry_types t ON t.entry_type = v.entry_type
WHERE t.entry_type IS NULL;

-- ------------------------------------------------
-- 4) Журнал операций (накопительный, агрегаты)
-- ------------------------------------------------
CREATE TABLE IF NOT EXISTS qa_ledger (
    entry_id     BIGSERIAL PRIMARY KEY,
    entry_date   DATE NOT NULL,
    entry_type   TEXT NOT NULL REFERENCES qa_entry_types(entry_type),
    status_code  TEXT NOT NULL REFERENCES qa_record_statuses(status_code),
    species_id   BIGINT NOT NULL REFERENCES qa_species(species_id),
    direction_id BIGINT NOT NULL REFERENCES qa_directions(direction_id),
    group_id     BIGINT REFERENCES qa_groups(group_id),      -- каталог-группа (если применимо)
    cohort_id    BIGINT REFERENCES qa_cohorts(cohort_id),    -- динамическая когорта (если применимо)
    sex          CHAR(1) CHECK (sex IN ('M','F','U')) DEFAULT 'U',
    age_cat_id   BIGINT REFERENCES qa_age_categories(age_cat_id),
    mass_bin_id  BIGINT REFERENCES qa_mass_bins(mass_bin_id),
    quantity     INTEGER NOT NULL CHECK (quantity > 0),      -- строго положительное
    purpose_text TEXT,                                       -- произвольное назначение/задача при выдаче (пока текст)
    transfer_key UUID,                                       -- связывает пары movement_out/movement_in
    note         TEXT,
    created_by   BIGINT REFERENCES app_users(user_id),
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
COMMENT ON TABLE qa_ledger IS 'Накопительный журнал агрегатных операций (приход/расход/перемещения/корректировки).';

CREATE INDEX IF NOT EXISTS idx_qa_ledger_date        ON qa_ledger(entry_date);
CREATE INDEX IF NOT EXISTS idx_qa_ledger_species_dir ON qa_ledger(species_id, direction_id);
CREATE INDEX IF NOT EXISTS idx_qa_ledger_group       ON qa_ledger(group_id);
CREATE INDEX IF NOT EXISTS idx_qa_ledger_cohort      ON qa_ledger(cohort_id);
CREATE INDEX IF NOT EXISTS idx_qa_ledger_transfer    ON qa_ledger(transfer_key);

-- ------------------------------------------------
-- 5) Импорт Excel/CSV (staging) + хранение исходного файла
-- ------------------------------------------------
CREATE TABLE IF NOT EXISTS qa_import_jobs (
    job_id      BIGSERIAL PRIMARY KEY,
    started_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at TIMESTAMPTZ,
    source      TEXT NOT NULL DEFAULT 'excel',           -- 'excel','csv'
    status      TEXT NOT NULL DEFAULT 'pending',         -- 'pending','running','done','failed'
    error       TEXT,
    document_id BIGINT REFERENCES documents(document_id) -- исходный файл импорта в ООК
);
COMMENT ON TABLE qa_import_jobs IS 'Задачи импорта Excel/CSV с привязкой исходного файла (документ).';

CREATE TABLE IF NOT EXISTS qa_import_rows (
    row_id      BIGSERIAL PRIMARY KEY,
    job_id      BIGINT NOT NULL REFERENCES qa_import_jobs(job_id) ON DELETE CASCADE,
    raw_payload JSONB,                                    -- как есть (после чтения файла)
    parsed      JSONB,                                    -- распарсенная структура
    status      TEXT NOT NULL DEFAULT 'new',              -- 'new','parsed','mapped','error'
    error       TEXT
);
COMMENT ON TABLE qa_import_rows IS 'Staging строк импортируемого файла (сырой JSON + парсинг).';

-- ------------------------------------------------
-- 6) Аналитические VIEW
-- ------------------------------------------------
-- Остатки по видам/направлениям/группам/когортам с учётом знака операции
CREATE OR REPLACE VIEW v_qa_stock_by_species_dir AS
WITH signed AS (
  SELECT
    species_id, direction_id, group_id, cohort_id, sex, age_cat_id, mass_bin_id,
    CASE entry_type
      WHEN 'intake'           THEN quantity
      WHEN 'movement_in'      THEN quantity
      WHEN 'adjustment'       THEN quantity
      WHEN 'withdrawal'       THEN -quantity
      WHEN 'movement_out'     THEN -quantity
      WHEN 'issue_for_control'THEN -quantity
      ELSE 0
    END AS delta
  FROM qa_ledger
  WHERE status_code = 'current'
)
SELECT
  species_id, direction_id, group_id, cohort_id, sex, age_cat_id, mass_bin_id,
  SUM(delta) AS qty
FROM signed
GROUP BY species_id, direction_id, group_id, cohort_id, sex, age_cat_id, mass_bin_id;

-- Пол
CREATE OR REPLACE VIEW v_qa_sex_breakdown AS
SELECT species_id, direction_id, sex, SUM(qty) AS qty
FROM v_qa_stock_by_species_dir
GROUP BY species_id, direction_id, sex;

-- Возраст
CREATE OR REPLACE VIEW v_qa_age_breakdown AS
SELECT species_id, direction_id, age_cat_id, SUM(qty) AS qty
FROM v_qa_stock_by_species_dir
WHERE age_cat_id IS NOT NULL
GROUP BY species_id, direction_id, age_cat_id;

-- Масса
CREATE OR REPLACE VIEW v_qa_mass_breakdown AS
SELECT species_id, direction_id, mass_bin_id, SUM(qty) AS qty
FROM v_qa_stock_by_species_dir
WHERE mass_bin_id IS NOT NULL
GROUP BY species_id, direction_id, mass_bin_id;

-- Назначения (по актуальным операциям)
CREATE OR REPLACE VIEW v_qa_purpose_text_stats AS
SELECT species_id, direction_id, purpose_text, SUM(quantity) AS cnt
FROM qa_ledger
WHERE status_code = 'current' AND purpose_text IS NOT NULL AND trim(purpose_text) <> ''
GROUP BY species_id, direction_id, purpose_text;

-- Динамика (помесячно, по направлениям)
CREATE OR REPLACE VIEW v_qa_monthly_totals AS
SELECT date_trunc('month', entry_date)::date AS month_start,
       species_id, direction_id,
       SUM(CASE WHEN entry_type IN ('intake','movement_in','adjustment') THEN quantity ELSE 0 END) AS in_qty,
       SUM(CASE WHEN entry_type IN ('withdrawal','movement_out','issue_for_control') THEN quantity ELSE 0 END) AS out_qty
FROM qa_ledger
WHERE status_code IN ('current','archived')
GROUP BY 1, species_id, direction_id
ORDER BY 1;

-- Перемещения (пары IN/OUT) в разрезе месяцев
CREATE OR REPLACE VIEW v_qa_movements_stats AS
SELECT date_trunc('month', entry_date)::date AS month_start,
       species_id,
       COUNT(*) FILTER (WHERE entry_type IN ('movement_in','movement_out'))/2 AS moves,
       SUM(quantity) FILTER (WHERE entry_type = 'movement_in')  AS qty_in,
       SUM(quantity) FILTER (WHERE entry_type = 'movement_out') AS qty_out
FROM qa_ledger
WHERE status_code IN ('current','archived')
GROUP BY 1, species_id
ORDER BY 1;

-- ------------------------------------------------
-- 7) Фиксация миграции
-- ------------------------------------------------
INSERT INTO schema_migrations(version, description)
SELECT 'v10_quarantine_animals',
       'Карантинирование животных: виды/возраст/масса; направления; группы-каталог и когорты; журнал агрегатов; статусы; VIEW; импорт с хранением файла.'
WHERE NOT EXISTS (SELECT 1 FROM schema_migrations WHERE version = 'v10_quarantine_animals');

COMMIT;

