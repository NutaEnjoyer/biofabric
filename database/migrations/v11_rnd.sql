--  ERP-Биофабрика — R&D (Исследования и разработки)
--  Файл: v11_rnd.sql
--  База: PostgreSQL 13+
--  Требует: v1_core_schema.sql (ядро), v2_ook_docflow.sql (ООК),
--           ОВБК/SCADA-модули из принятых версий.
--  Назначение: штаммы (SCD2), классификаторы, единицы, связь с ОВБК и SCADA,
--              опыты (типы/роли/результаты), документы (с ролями), аналитические VIEW.
--  Идемпотентность: да


BEGIN;

-- ------------------------------------------------
-- 0) Общие статусы
-- ------------------------------------------------
CREATE TABLE IF NOT EXISTS rd_common_statuses (
    status_code  TEXT PRIMARY KEY,          -- 'draft','under_review','active','archived'
    display_name TEXT NOT NULL
);
INSERT INTO rd_common_statuses(status_code, display_name)
SELECT v.status_code, v.display_name
FROM (VALUES
  ('draft','Черновик'),
  ('under_review','На проверке'),
  ('active','Активный'),
  ('archived','Архивный')
) AS v(status_code, display_name)
LEFT JOIN rd_common_statuses s ON s.status_code = v.status_code
WHERE s.status_code IS NULL;

-- ------------------------------------------------
-- 1) Справочники: единицы, принадлежность, микробиологические типы
-- ------------------------------------------------
CREATE TABLE IF NOT EXISTS rd_units (
    unit_id   BIGSERIAL PRIMARY KEY,
    code      TEXT NOT NULL UNIQUE,         -- 'mL','CFU','vial','aliquot','g','mg'
    name      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS rd_belongings (
    belonging_code TEXT PRIMARY KEY,        -- 'storage','production'
    display_name   TEXT NOT NULL
);
INSERT INTO rd_belongings(belonging_code, display_name)
SELECT v.code, v.name
FROM (VALUES
  ('storage','Хранение'),
  ('production','Производство')
) AS v(code, name)
LEFT JOIN rd_belongings b ON b.belonging_code = v.code
WHERE b.belonging_code IS NULL;

CREATE TABLE IF NOT EXISTS rd_microbe_types (
    type_id BIGSERIAL PRIMARY KEY,
    name    TEXT NOT NULL UNIQUE            -- бактерии/вирусы/грибы/др.
);

CREATE TABLE IF NOT EXISTS rd_microbe_subtypes (
    subtype_id BIGSERIAL PRIMARY KEY,
    type_id    BIGINT NOT NULL REFERENCES rd_microbe_types(type_id) ON DELETE CASCADE,
    name       TEXT NOT NULL,
    UNIQUE (type_id, name)
);

-- ------------------------------------------------
-- 2) Штаммы: паспорт + версии (SCD2)
-- ------------------------------------------------
CREATE TABLE IF NOT EXISTS rd_strains (
    strain_id          BIGSERIAL PRIMARY KEY,
    code               TEXT UNIQUE,         -- внутренний код/паспорт (опц.)
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by         BIGINT REFERENCES app_users(user_id),
    current_version_id BIGINT               -- для ускорения выборок (заполняется приложением)
);
COMMENT ON TABLE rd_strains IS 'Паспорт штамма (уникальный ID).';

CREATE TABLE IF NOT EXISTS rd_strain_versions (
    version_id    BIGSERIAL PRIMARY KEY,
    strain_id     BIGINT NOT NULL REFERENCES rd_strains(strain_id) ON DELETE CASCADE,
    version_no    INT    NOT NULL,                     -- 1..N
    valid_from    TIMESTAMPTZ NOT NULL DEFAULT now(),
    valid_to      TIMESTAMPTZ,                         -- NULL = текущая
    status_code   TEXT NOT NULL REFERENCES rd_common_statuses(status_code),

    -- Классификация и принадлежность
    type_id       BIGINT REFERENCES rd_microbe_types(type_id),
    subtype_id    BIGINT REFERENCES rd_microbe_subtypes(subtype_id),
    belonging_code TEXT REFERENCES rd_belongings(belonging_code),

    -- Кол-во и единицы
    amount        NUMERIC(18,6),                       -- опц.
    unit_id       BIGINT REFERENCES rd_units(unit_id),

    -- Основные атрибуты карточки (примерный набор, расширяемый аддитивно)
    name          TEXT,                                -- назначаемое имя/обозначение
    origin        TEXT,                                -- происхождение
    genotype      TEXT,
    phenotype     TEXT,
    storage_cond  TEXT,                                -- условия хранения
    notes         JSONB,                               -- прочие атрибуты (гибко)

    -- Трассировка
    author_id     BIGINT REFERENCES app_users(user_id),
    reason        TEXT                                 -- причина изменения (версионирования)
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_rd_strain_versions ON rd_strain_versions(strain_id, version_no);
CREATE INDEX IF NOT EXISTS idx_rd_strain_versions_period ON rd_strain_versions(strain_id, valid_from, valid_to);

-- ------------------------------------------------
-- 3) Связь с ОВБК (лаборатория качества)
-- ------------------------------------------------
-- Привязки штамма к лабораторным объектам (не меняем схему ЛКК)
CREATE TABLE IF NOT EXISTS rd_strain_lab_refs (
    link_id        BIGSERIAL PRIMARY KEY,
    strain_id      BIGINT NOT NULL REFERENCES rd_strains(strain_id) ON DELETE CASCADE,
    lab_sample_id  BIGINT,     -- REFERENCES lab_samples(sample_id)
    lab_protocol_id BIGINT,    -- REFERENCES lab_protocols(document_id) или отдельный PK
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);
COMMENT ON TABLE rd_strain_lab_refs IS 'Связи штаммов с пробами/протоколами ОВБК.';

-- ------------------------------------------------
-- 4) Связь с SCADA (универсальная модель)
-- ------------------------------------------------
CREATE TABLE IF NOT EXISTS rd_strain_scada_links (
    link_id        BIGSERIAL PRIMARY KEY,
    strain_id      BIGINT NOT NULL REFERENCES rd_strains(strain_id) ON DELETE CASCADE,
    data_type_id   BIGINT,        -- REFERENCES scada.data_types(data_type_id)
    data_record_id BIGINT,        -- REFERENCES scada.data_records(record_id)
    agg_json       JSONB,         -- агрегаты по опыту: min/max/avg/σ, окна и т.д.
    note           TEXT,
    UNIQUE (strain_id, data_type_id, data_record_id)
);
COMMENT ON TABLE rd_strain_scada_links IS 'R&D-ссылки на SCADA-типы/записи + агрегаты (по whitelist-тегам).';

-- ------------------------------------------------
-- 5) Документы (ООК) с ролями на связи
-- ------------------------------------------------
CREATE TABLE IF NOT EXISTS rd_doc_links (
    link_id      BIGSERIAL PRIMARY KEY,
    object_type  TEXT NOT NULL,         -- 'rd_strain','rd_experiment','rd_regulation'
    object_id    BIGINT NOT NULL,
    document_id  BIGINT NOT NULL REFERENCES documents(document_id) ON DELETE CASCADE,
    doc_role     TEXT NOT NULL,         -- 'regulation','instruction','method','result','other'
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_rd_doc_links_obj ON rd_doc_links(object_type, object_id);

-- ------------------------------------------------
-- 6) Опыты: типы, карточки, штаммы-участники, результаты
-- ------------------------------------------------
CREATE TABLE IF NOT EXISTS rd_experiment_types (
    type_id BIGSERIAL PRIMARY KEY,
    code    TEXT NOT NULL UNIQUE,        -- 'fermentation','stability','selection',...
    name    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS rd_experiments (
    experiment_id BIGSERIAL PRIMARY KEY,
    type_id       BIGINT NOT NULL REFERENCES rd_experiment_types(type_id),
    title         TEXT NOT NULL,
    status_code   TEXT NOT NULL REFERENCES rd_common_statuses(status_code),
    started_at    TIMESTAMPTZ,
    ended_at      TIMESTAMPTZ,
    performed_per_regulation BOOLEAN,    -- соответствие регламенту (галка)
    created_by    BIGINT REFERENCES app_users(user_id),
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    notes         JSONB
);

-- Штаммы в опыте (M:N) + роли
CREATE TABLE IF NOT EXISTS rd_experiment_strains (
    link_id      BIGSERIAL PRIMARY KEY,
    experiment_id BIGINT NOT NULL REFERENCES rd_experiments(experiment_id) ON DELETE CASCADE,
    strain_id     BIGINT NOT NULL REFERENCES rd_strains(strain_id) ON DELETE CASCADE,
    role_code     TEXT NOT NULL,         -- 'main','control','aux'
    UNIQUE (experiment_id, strain_id, role_code)
);

-- Результаты опытов: структурированные KPI
CREATE TABLE IF NOT EXISTS rd_result_kpis (
    kpi_id   BIGSERIAL PRIMARY KEY,
    code     TEXT NOT NULL UNIQUE,       -- 'yield','titer','growth_rate','purity'
    name     TEXT NOT NULL,
    unit_id  BIGINT REFERENCES rd_units(unit_id)
);

CREATE TABLE IF NOT EXISTS rd_experiment_results (
    result_id     BIGSERIAL PRIMARY KEY,
    experiment_id BIGINT NOT NULL REFERENCES rd_experiments(experiment_id) ON DELETE CASCADE,
    kpi_id        BIGINT NOT NULL REFERENCES rd_result_kpis(kpi_id),
    measured_at   TIMESTAMPTZ,
    value_num     NUMERIC(18,6),         -- основное числовое значение
    value_text    TEXT,                  -- если показатель текстовый/категориальный
    notes         JSONB
);
CREATE INDEX IF NOT EXISTS idx_rd_experiment_results_exp ON rd_experiment_results(experiment_id);
CREATE INDEX IF NOT EXISTS idx_rd_experiment_results_kpi ON rd_experiment_results(kpi_id);

-- ------------------------------------------------
-- 7) VIEW: аналитика и эксплуатационные выборки
-- ------------------------------------------------
-- Актуальные версии штаммов (на текущий момент)
CREATE OR REPLACE VIEW v_rd_strains_current AS
SELECT v.*
FROM rd_strain_versions v
JOIN rd_strains s ON s.strain_id = v.strain_id
WHERE v.valid_to IS NULL;

-- Состояние штамма на дату (пример — на вчера)
-- (для произвольной даты используйте параметризованный запрос с BETWEEN valid_from AND COALESCE(valid_to,'+infinity'))
CREATE OR REPLACE VIEW v_rd_strains_asof_yesterday AS
SELECT v.*
FROM rd_strain_versions v
WHERE v.valid_from <= (CURRENT_DATE - INTERVAL '1 day')
  AND COALESCE(v.valid_to, 'infinity') > (CURRENT_DATE - INTERVAL '1 day');

-- Количество версий на штамм
CREATE OR REPLACE VIEW v_rd_strain_version_counts AS
SELECT strain_id, COUNT(*) AS versions_count
FROM rd_strain_versions
GROUP BY strain_id;

-- Распределение штаммов по типам/статусам (текущие)
CREATE OR REPLACE VIEW v_rd_strains_by_type_status AS
SELECT v.type_id, v.status_code, COUNT(*) AS cnt
FROM v_rd_strains_current v
GROUP BY v.type_id, v.status_code;

-- Соответствие регламентам по опытам (есть ли регламент и флаг соответствия)
CREATE OR REPLACE VIEW v_rd_experiments_regulatory AS
SELECT e.experiment_id,
       COALESCE(MAX(CASE WHEN dl.doc_role='regulation' THEN 1 ELSE 0 END),0) AS has_regulation_doc,
       COALESCE(e.performed_per_regulation,false) AS performed_per_regulation
FROM rd_experiments e
LEFT JOIN rd_doc_links dl ON dl.object_type='rd_experiment' AND dl.object_id=e.experiment_id
GROUP BY e.experiment_id, e.performed_per_regulation;

-- Результативность опытов: последние значения KPI
CREATE OR REPLACE VIEW v_rd_experiment_last_kpis AS
SELECT r1.*
FROM rd_experiment_results r1
JOIN (
  SELECT experiment_id, kpi_id, MAX(measured_at) AS max_ts
  FROM rd_experiment_results
  GROUP BY experiment_id, kpi_id
) z ON z.experiment_id=r1.experiment_id AND z.kpi_id=r1.kpi_id AND z.max_ts=r1.measured_at;

-- Частота SCADA-ссылок по штаммам (как прокси объёма данных)
CREATE OR REPLACE VIEW v_rd_scada_links_by_strain AS
SELECT strain_id,
       COUNT(*) AS link_count,
       COUNT(*) FILTER (WHERE data_record_id IS NOT NULL) AS direct_records,
       COUNT(*) FILTER (WHERE data_record_id IS NULL AND data_type_id IS NOT NULL) AS by_type_only
FROM rd_strain_scada_links
GROUP BY strain_id;

-- ------------------------------------------------
-- 8) Фиксация применения миграции
-- ------------------------------------------------
INSERT INTO schema_migrations(version, description)
SELECT 'v11_rnd',
       'R&D: штаммы SCD2 (версии), единицы, типы/подтипы, принадлежность; связи с ОВБК и SCADA; опыты/роли/результаты; документы с ролями; аналитические VIEW.'
WHERE NOT EXISTS (SELECT 1 FROM schema_migrations WHERE version = 'v11_rnd');

COMMIT;


