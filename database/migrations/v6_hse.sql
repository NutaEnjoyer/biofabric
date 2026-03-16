--  ERP-Биофабрика — Охрана труда (HSE)
--  Файл: v6_hse.sql
--  База: PostgreSQL 13+
--  Требует: v1_core_schema.sql (ядро), v2_ook_docflow.sql (ООК)
--  Назначение: НПА (нормативные акты), штатное расписание (подразделения/должности),
--              сотрудники (из 1С), реестр инструкций по охране труда и их статусы.
--  Lean: содержимое DOCX-инструкций не дублируем; связь через document_bindings.
--  Принято: утверждает конкретный app_user; единый valid_until; опц. кэш НПА;
--           таблица hse_instruction_acts (многие-ко-многим); fired_at у сотрудников.
--  Идемпотентность: да


BEGIN;

-- ------------------------------------------------
-- 1) НПА: источники и акты
-- ------------------------------------------------
CREATE TABLE IF NOT EXISTS hse_regulatory_sources (
    source_id   BIGSERIAL PRIMARY KEY,
    name        TEXT NOT NULL,                -- "Гарант","КонсультантПлюс", ...
    base_url    TEXT,
    UNIQUE (name)
);
COMMENT ON TABLE hse_regulatory_sources IS 'Источники НПА (провайдеры нормативных актов).';

CREATE TABLE IF NOT EXISTS hse_regulatory_acts (
    act_id      BIGSERIAL PRIMARY KEY,
    source_id   BIGINT REFERENCES hse_regulatory_sources(source_id) ON DELETE SET NULL,
    external_id TEXT,                         -- ID/ключ во внешнем источнике
    title       TEXT NOT NULL,
    version_tag TEXT,                         -- редакция/дата версии
    received_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    content     JSONB,                        -- опц.: кэш текста/структуры (NULL, если не кэшируем)
    UNIQUE (source_id, external_id)
);
COMMENT ON TABLE hse_regulatory_acts IS 'Нормативно-правовые акты: метаданные и (опционально) локальный кэш содержимого.';

-- ------------------------------------------------
-- 2) Штатное расписание и сотрудники
-- ------------------------------------------------
CREATE TABLE IF NOT EXISTS hse_org_units (
    org_unit_id BIGSERIAL PRIMARY KEY,
    name        TEXT NOT NULL,
    parent_id   BIGINT REFERENCES hse_org_units(org_unit_id) ON DELETE SET NULL,
    UNIQUE (name, parent_id)
);
COMMENT ON TABLE hse_org_units IS 'Подразделения предприятия (иерархия).';

CREATE TABLE IF NOT EXISTS hse_positions (
    position_id BIGSERIAL PRIMARY KEY,
    name        TEXT NOT NULL UNIQUE
);
COMMENT ON TABLE hse_positions IS 'Должности (каталог; все позиции заводим здесь).';

CREATE TABLE IF NOT EXISTS hse_employees (
    employee_id BIGSERIAL PRIMARY KEY,
    onec_id     TEXT UNIQUE,                  -- внешний ID из 1С
    full_name   TEXT NOT NULL,
    position_id BIGINT REFERENCES hse_positions(position_id),
    org_unit_id BIGINT REFERENCES hse_org_units(org_unit_id),
    hired_at    DATE,                         -- дата приёма
    fired_at    DATE                          -- дата увольнения (NULL = активен)
);
COMMENT ON TABLE hse_employees IS 'Сотрудники: ФИО, должность, подразделение, даты приёма/увольнения.';

-- Импорт из 1С: стейджинг
CREATE TABLE IF NOT EXISTS hse_staff_import_jobs (
    job_id     BIGSERIAL PRIMARY KEY,
    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at TIMESTAMPTZ,
    status     TEXT NOT NULL DEFAULT 'pending', -- 'pending','running','done','failed'
    error      TEXT
);
COMMENT ON TABLE hse_staff_import_jobs IS 'Задачи импорта кадровых данных из 1С (жизненный цикл и ошибки).';

CREATE TABLE IF NOT EXISTS hse_staff_import_rows (
    row_id     BIGSERIAL PRIMARY KEY,
    job_id     BIGINT NOT NULL REFERENCES hse_staff_import_jobs(job_id) ON DELETE CASCADE,
    raw_payload JSONB,                        -- сырые данные из 1С
    parsed      JSONB,
    matched_employee_id BIGINT REFERENCES hse_employees(employee_id),
    status     TEXT NOT NULL DEFAULT 'new',   -- 'new','matched','conflict','error'
    error      TEXT
);
COMMENT ON TABLE hse_staff_import_rows IS 'Строки импорта из 1С: парсинг и сопоставление с сотрудниками.';

-- ------------------------------------------------
-- 3) Связь должностей с НПА (для генерации инструкций)
-- ------------------------------------------------
CREATE TABLE IF NOT EXISTS hse_position_act_map (
    map_id      BIGSERIAL PRIMARY KEY,
    position_id BIGINT NOT NULL REFERENCES hse_positions(position_id) ON DELETE CASCADE,
    act_id      BIGINT NOT NULL REFERENCES hse_regulatory_acts(act_id) ON DELETE CASCADE,
    relevance   TEXT,                         -- комментарий/основание/область применения
    UNIQUE (position_id, act_id)
);
COMMENT ON TABLE hse_position_act_map IS 'Связь должности с НПА, на базе которых готовится инструкция.';

-- ------------------------------------------------
-- 4) Статусы и реестр инструкций
-- ------------------------------------------------
CREATE TABLE IF NOT EXISTS hse_instruction_statuses (
    status_code  TEXT PRIMARY KEY,            -- 'draft','pending_approval','approved','needs_update','cancelled'
    display_name TEXT NOT NULL
);
COMMENT ON TABLE hse_instruction_statuses IS 'Статусы инструкций по охране труда.';

INSERT INTO hse_instruction_statuses(status_code, display_name)
SELECT v.status_code, v.display_name
FROM (VALUES
  ('draft','Черновик'),
  ('pending_approval','Ожидает утверждения'),
  ('approved','Утверждена'),
  ('needs_update','Требует обновления'),
  ('cancelled','Отменена')
) AS v(status_code, display_name)
LEFT JOIN hse_instruction_statuses s ON s.status_code = v.status_code
WHERE s.status_code IS NULL;

CREATE TABLE IF NOT EXISTS hse_instructions (
    instruction_id   BIGSERIAL PRIMARY KEY,
    employee_id      BIGINT NOT NULL REFERENCES hse_employees(employee_id) ON DELETE CASCADE,
    position_id      BIGINT REFERENCES hse_positions(position_id), -- фиксируем должность на момент создания
    status_code      TEXT   NOT NULL REFERENCES hse_instruction_statuses(status_code),
    document_id      BIGINT REFERENCES documents(document_id),     -- файл в ООК
    approver_user_id BIGINT REFERENCES app_users(user_id),         -- кто утвердил (конкретный пользователь)
    generated_from   JSONB,                                       -- общий контекст генерации (набор act_id и др.)
    generated_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    approved_at      TIMESTAMPTZ,
    valid_until      DATE,                                        -- срок актуальности/переподтверждения
    notes            TEXT
);
COMMENT ON TABLE hse_instructions IS 'Реестр инструкций: сотрудник, документ (ООК), статусы, ответственный и сроки.';

CREATE INDEX IF NOT EXISTS idx_hse_instr_status    ON hse_instructions(status_code);
CREATE INDEX IF NOT EXISTS idx_hse_instr_valid     ON hse_instructions(valid_until);
CREATE INDEX IF NOT EXISTS idx_hse_instr_employee  ON hse_instructions(employee_id);

-- Нормализованная трассировка «инструкция ↔ НПА» (многие-ко-многим)
CREATE TABLE IF NOT EXISTS hse_instruction_acts (
    instruction_id BIGINT NOT NULL REFERENCES hse_instructions(instruction_id) ON DELETE CASCADE,
    act_id         BIGINT NOT NULL REFERENCES hse_regulatory_acts(act_id) ON DELETE CASCADE,
    act_version_tag TEXT,                      -- версия НПА, по которой сформирована инструкция
    PRIMARY KEY (instruction_id, act_id)
);
COMMENT ON TABLE hse_instruction_acts IS 'Аудит: какие НПА (и их версии) легли в основу конкретной инструкции.';

-- ------------------------------------------------
-- 5) Представления для контроля (для UI и/или оповещений)
-- ------------------------------------------------
-- Активные сотрудники (без fired_at) без утверждённой актуальной инструкции
CREATE OR REPLACE VIEW v_hse_without_instruction AS
SELECT e.*
FROM hse_employees e
LEFT JOIN LATERAL (
    SELECT 1
    FROM hse_instructions i
    WHERE i.employee_id = e.employee_id
      AND i.status_code = 'approved'
      AND (i.valid_until IS NULL OR i.valid_until >= CURRENT_DATE)
    LIMIT 1
) ok ON TRUE
WHERE e.fired_at IS NULL
  AND ok IS NULL;

-- Инструкции, срок актуальности которых истекает в 30 дней (акцент для UI-виджетов/дашбордов)
CREATE OR REPLACE VIEW v_hse_instructions_expiring_30d AS
SELECT i.*, (i.valid_until - CURRENT_DATE) AS days_left
FROM hse_instructions i
WHERE i.valid_until IS NOT NULL
  AND i.valid_until <= CURRENT_DATE + INTERVAL '30 days'
  AND i.status_code = 'approved';

-- ------------------------------------------------
-- 6) Связка с ООК (lean)
-- ------------------------------------------------
-- Документы создаются/версируются в ООК; связь инструкция ↔ документ
-- осуществляется через document_bindings(object_type='hse_instruction', object_id=instruction_id).
-- Отдельных таблиц под содержимое DOCX не создаём.

-- ------------------------------------------------
-- 7) Фиксация применения миграции
-- ------------------------------------------------
INSERT INTO schema_migrations(version, description)
SELECT 'v6_hse',
       'Охрана труда: НПА, штатка, сотрудники (1С), реестр инструкций, статусы, m2m инструкция↔НПА, fired_at, вьюхи контроля.'
WHERE NOT EXISTS (SELECT 1 FROM schema_migrations WHERE version = 'v6_hse');

COMMIT;


