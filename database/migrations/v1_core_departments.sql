--  ERP-Биофабрика — Общие справочники (Core)
--  Файл: v1_core_departments.sql
--  База: PostgreSQL 13+
--  Требует: v1_core_schema.sql
--  Назначение: единый справочник подразделений для всех модулей
--  Примечание: hse_org_units из v6_hse.sql — дубль для HSE-модуля;
--              core_departments — канонический источник для всей системы.
--  Идемпотентность: да

BEGIN;

-- ------------------------------------------------
-- 1) Подразделения (иерархия)
-- ------------------------------------------------
CREATE TABLE IF NOT EXISTS core_departments (
    department_id BIGSERIAL PRIMARY KEY,
    code          TEXT UNIQUE,                       -- код подразделения (из 1С или внутренний)
    name          TEXT NOT NULL,
    parent_id     BIGINT REFERENCES core_departments(department_id) ON DELETE SET NULL,
    head_user_id  BIGINT REFERENCES app_users(user_id), -- руководитель
    is_active     BOOLEAN NOT NULL DEFAULT TRUE,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (name, parent_id)
);
COMMENT ON TABLE core_departments IS 'Единый справочник подразделений предприятия (иерархия).';

CREATE INDEX IF NOT EXISTS idx_core_departments_parent ON core_departments(parent_id);
CREATE INDEX IF NOT EXISTS idx_core_departments_head ON core_departments(head_user_id);

-- ------------------------------------------------
-- 2) VIEW: плоский список с путём
-- ------------------------------------------------
CREATE OR REPLACE VIEW v_core_departments_tree AS
WITH RECURSIVE tree AS (
    SELECT
        department_id,
        code,
        name,
        parent_id,
        head_user_id,
        is_active,
        name::TEXT AS path,
        1 AS level
    FROM core_departments
    WHERE parent_id IS NULL

    UNION ALL

    SELECT
        d.department_id,
        d.code,
        d.name,
        d.parent_id,
        d.head_user_id,
        d.is_active,
        (t.path || ' > ' || d.name)::TEXT AS path,
        t.level + 1
    FROM core_departments d
    JOIN tree t ON d.parent_id = t.department_id
)
SELECT * FROM tree ORDER BY path;

-- ------------------------------------------------
-- 3) Синхронизация с hse_org_units (опционально)
--    Если HSE-модуль уже использует hse_org_units,
--    можно создать VIEW для совместимости.
-- ------------------------------------------------
-- CREATE OR REPLACE VIEW hse_org_units_compat AS
-- SELECT department_id AS org_unit_id, name, parent_id
-- FROM core_departments;

-- ------------------------------------------------
-- 4) Фиксация применения миграции
-- ------------------------------------------------
INSERT INTO schema_migrations(version, description)
SELECT 'v1_core_departments',
       'Ядро: единый справочник подразделений (core_departments) с иерархией и VIEW дерева.'
WHERE NOT EXISTS (SELECT 1 FROM schema_migrations WHERE version = 'v1_core_departments');

COMMIT;
