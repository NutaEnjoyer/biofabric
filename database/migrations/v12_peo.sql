--  ERP-Биофабрика — ПЭО (Планово-экономический отдел)
--  Файл: v12_peo.sql
--  База: PostgreSQL 13+
--  Требует: v1_core_schema.sql (ядро), v2_ook_docflow.sql (ООК),
--           HR/Закупки/Контрагенты при наличии (FK мягкие/опц.).
--  Назначение: продажи/COGS/транспорт, экспорт, ФОТ, бенчмарки,
--              сырьё (рынок), спецодежда, СМС, метрология, контрагенты,
--              документы-основания. Показатели считаем во VIEW.
--  Идемпотентность: да

BEGIN;

-- ------------------------------------------------
-- 0) Общие справочники/ссылки
-- ------------------------------------------------
CREATE TABLE IF NOT EXISTS peo_okpd2 (
    code   TEXT PRIMARY KEY,        -- напр. '10.89.19.000'
    name   TEXT NOT NULL
);
COMMENT ON TABLE peo_okpd2 IS 'ОКПД2 для номенклатуры (опционально).';

CREATE TABLE IF NOT EXISTS peo_items (
    item_id   BIGSERIAL PRIMARY KEY,
    code      TEXT UNIQUE,          -- код номенклатуры из 1С
    name      TEXT NOT NULL,
    okpd2_code TEXT REFERENCES peo_okpd2(code),
    is_active BOOLEAN NOT NULL DEFAULT TRUE
);
COMMENT ON TABLE peo_items IS 'Каталог номенклатуры (минимальный, может заполняться из 1С).';

-- ------------------------------------------------
-- 1) Продажи и себестоимость (RUB), экспорт
-- ------------------------------------------------
CREATE TABLE IF NOT EXISTS peo_sales (
    sale_id        BIGSERIAL PRIMARY KEY,
    sale_date      DATE NOT NULL,
    item_id        BIGINT REFERENCES peo_items(item_id) ON DELETE SET NULL,
    item_code      TEXT,                       -- если item_id пока не сопоставлен
    customer_id    BIGINT,                     -- REFERENCES peo_counterparties(counterparty_id) опционально
    customer_name  TEXT,
    customer_country TEXT,                     -- для детектора экспорта
    quantity       NUMERIC(18,6),
    revenue_rub    NUMERIC(18,2) NOT NULL,     -- выручка (RUB)
    cogs_rub       NUMERIC(18,2) NOT NULL,     -- себестоимость (RUB)
    warehouse_code TEXT,                       -- код склада из 1С (инфо)
    is_export      BOOLEAN,                    -- флаг экспорта из 1С, если есть
    basis_ref      TEXT,                       -- короткая ссылка на документ-основание (опц.)
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);
COMMENT ON TABLE peo_sales IS 'Продажи и себестоимость по номенклатуре (данные из 1С). Валюта: RUB.';

-- ------------------------------------------------
-- 2) Транспортные расходы
-- ------------------------------------------------
CREATE TABLE IF NOT EXISTS peo_transport_costs (
    tc_id          BIGSERIAL PRIMARY KEY,
    tc_date        DATE NOT NULL,
    route          TEXT NOT NULL,              -- маршрут из 1С
    transport_type TEXT NOT NULL,              -- тип транспорта из 1С
    cargo_type     TEXT NOT NULL,              -- вид груза из 1С
    amount_rub     NUMERIC(18,2) NOT NULL,     -- сумма (RUB)
    related_sale_id BIGINT REFERENCES peo_sales(sale_id) ON DELETE SET NULL,  -- если известна связь
    basis_ref      TEXT,                       -- короткий «ярлык» основания (опц.)
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);
COMMENT ON TABLE peo_transport_costs IS 'Транспортные расходы (из 1С) с обязательными реквизитами.';

-- ------------------------------------------------
-- 3) Документы-основания (ООК, с ролями)
-- ------------------------------------------------
CREATE TABLE IF NOT EXISTS peo_doc_links (
    link_id     BIGSERIAL PRIMARY KEY,
    object_type TEXT NOT NULL,         -- 'sale','transport','raw_market','ppe','sms','meter','counterparty'
    object_id   BIGINT NOT NULL,
    document_id BIGINT NOT NULL REFERENCES documents(document_id) ON DELETE CASCADE,
    doc_role    TEXT NOT NULL,         -- 'waybill','invoice','act','contract','other'
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_peo_doc_links_obj ON peo_doc_links(object_type, object_id);

-- ------------------------------------------------
-- 4) ФОТ (по сотрудникам, без грейдов)
-- ------------------------------------------------
CREATE TABLE IF NOT EXISTS peo_payroll (
    payroll_id   BIGSERIAL PRIMARY KEY,
    month_start  DATE NOT NULL,             -- первый день месяца
    employee_id  BIGINT,                    -- REFERENCES hr_employees(employee_id) опц.
    employee_name TEXT,
    department_id BIGINT,                   -- REFERENCES core_departments(department_id) опц.
    position_text TEXT,
    base_salary_rub NUMERIC(18,2) NOT NULL DEFAULT 0,
    bonus_rub       NUMERIC(18,2) NOT NULL DEFAULT 0,
    extra_rub       NUMERIC(18,2) NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_peo_payroll_month ON peo_payroll(month_start);

-- Benchmarks зарплат (hh.ru и др.)
CREATE TABLE IF NOT EXISTS peo_salary_benchmarks (
    bench_id     BIGSERIAL PRIMARY KEY,
    source       TEXT NOT NULL,           -- 'hh','analyst_report', ...
    region       TEXT,
    position_text TEXT NOT NULL,
    period_start DATE NOT NULL,
    period_end   DATE,
    p10_rub      NUMERIC(18,2),
    p50_rub      NUMERIC(18,2),
    p90_rub      NUMERIC(18,2),
    notes        JSONB
);
COMMENT ON TABLE peo_salary_benchmarks IS 'Рыночные уровни зарплат по источникам/регионам/периодам.';

-- ------------------------------------------------
-- 5) Сырьё: рыночные цены (отдельно от закупок)
-- ------------------------------------------------
CREATE TABLE IF NOT EXISTS peo_raw_market_prices (
    price_id     BIGSERIAL PRIMARY KEY,
    material_name TEXT NOT NULL,
    unit_text     TEXT NOT NULL,            -- строковая единица (по договорённости)
    price_rub     NUMERIC(18,4) NOT NULL,
    valid_from    DATE NOT NULL,
    valid_to      DATE,
    source        TEXT,                     -- источник котировки
    notes         JSONB
);
CREATE INDEX IF NOT EXISTS idx_peo_raw_market_prices_valid ON peo_raw_market_prices(valid_from, valid_to);

-- ------------------------------------------------
-- 6) Спецодежда (PPE) и СМС (санитарные/расходные)
-- ------------------------------------------------
CREATE TABLE IF NOT EXISTS peo_ppe_ledger (
    entry_id      BIGSERIAL PRIMARY KEY,
    entry_date    DATE NOT NULL,
    item_name     TEXT NOT NULL,
    qty           NUMERIC(18,4) NOT NULL,
    amount_rub    NUMERIC(18,2) NOT NULL,
    employee_id   BIGINT,                    -- FK → hr_employees (опц.)
    department_id BIGINT,                    -- FK → core_departments (опц.)
    reason_text   TEXT,                      -- причина/замена — текст
    note          TEXT,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (employee_id IS NOT NULL OR department_id IS NOT NULL)
);
COMMENT ON TABLE peo_ppe_ledger IS 'Учёт спецодежды на сотрудника и/или подразделение.';

CREATE TABLE IF NOT EXISTS peo_sms_ledger (
    entry_id      BIGSERIAL PRIMARY KEY,
    entry_date    DATE NOT NULL,
    item_name     TEXT NOT NULL,
    qty           NUMERIC(18,4) NOT NULL,
    amount_rub    NUMERIC(18,2) NOT NULL,
    employee_id   BIGINT,                    -- FK → hr_employees (опц.)
    department_id BIGINT,                    -- FK → core_departments (опц.)
    note          TEXT,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (employee_id IS NOT NULL OR department_id IS NOT NULL)
);
COMMENT ON TABLE peo_sms_ledger IS 'Учёт санитарных и расходных средств (на сотрудника/подразделение).';

-- ------------------------------------------------
-- 7) Метрология: приборы, статусы, поверки (история)
-- ------------------------------------------------
CREATE TABLE IF NOT EXISTS peo_meter_statuses (
    status_code  TEXT PRIMARY KEY,          -- 'in_service','calibrating','faulty','decommissioned'
    display_name TEXT NOT NULL
);
INSERT INTO peo_meter_statuses(status_code, display_name)
SELECT v.code, v.name
FROM (VALUES
  ('in_service','В эксплуатации'),
  ('calibrating','На поверке'),
  ('faulty','Неисправен'),
  ('decommissioned','Списан')
) AS v(code, name)
LEFT JOIN peo_meter_statuses s ON s.status_code = v.code
WHERE s.status_code IS NULL;

CREATE TABLE IF NOT EXISTS peo_meters (
    meter_id     BIGSERIAL PRIMARY KEY,
    inventory_no TEXT UNIQUE,
    name         TEXT NOT NULL,
    model        TEXT,
    serial_no    TEXT,
    location     TEXT,
    status_code  TEXT NOT NULL REFERENCES peo_meter_statuses(status_code),
    last_calibration_date DATE,
    next_calibration_date DATE,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS peo_meter_calibrations (
    calib_id     BIGSERIAL PRIMARY KEY,
    meter_id     BIGINT NOT NULL REFERENCES peo_meters(meter_id) ON DELETE CASCADE,
    calib_date   DATE NOT NULL,
    result       TEXT NOT NULL,               -- 'pass'/'fail'/текст
    certificate_no TEXT,
    next_due_date  DATE,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
COMMENT ON TABLE peo_meter_calibrations IS 'История поверок приборов.';

-- ------------------------------------------------
-- 8) Контрагенты и проверки
-- ------------------------------------------------
CREATE TABLE IF NOT EXISTS peo_counterparties (
    counterparty_id BIGSERIAL PRIMARY KEY,
    name            TEXT NOT NULL,
    inn             TEXT,                     -- ИНН
    ogrn            TEXT,
    kpp             TEXT,
    country         TEXT,
    okved_text      TEXT,                     -- ОКВЭД строкой (без собственного справочника)
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Снимок последней проверки (без истории; историю можно добавить отдельно)
CREATE TABLE IF NOT EXISTS peo_counterparty_snapshot (
    counterparty_id BIGINT PRIMARY KEY REFERENCES peo_counterparties(counterparty_id) ON DELETE CASCADE,
    checked_at      TIMESTAMPTZ,
    status_text     TEXT,                     -- 'valid','warning','blocked' и т.п.
    source          TEXT,                     -- кто проверял: 'fis','spark','manual'
    okved_text      TEXT,                     -- дублируем при проверке
    notes           JSONB
);
COMMENT ON TABLE peo_counterparty_snapshot IS 'Текущее состояние проверки контрагента (без истории).';

-- ------------------------------------------------
-- 9) VIEW: аналитика ПЭО
-- ------------------------------------------------
-- Экспорт определяем как явный флаг ИЛИ по стране контрагента ≠ 'RU'
CREATE OR REPLACE VIEW v_peo_exports_detected AS
SELECT
  sale_id, sale_date, COALESCE(is_export, (customer_country IS NOT NULL AND upper(customer_country) <> 'RU')) AS is_export_detected
FROM peo_sales;

-- Маржинальность по месяцам (RUB)
CREATE OR REPLACE VIEW v_peo_profitability_month AS
SELECT
  date_trunc('month', sale_date)::date AS month_start,
  SUM(revenue_rub) AS revenue_rub,
  SUM(cogs_rub)    AS cogs_rub,
  SUM(revenue_rub - cogs_rub) AS gross_margin_rub,
  SUM(revenue_rub - cogs_rub) / NULLIF(SUM(revenue_rub),0) AS gross_margin_pct
FROM peo_sales
GROUP BY 1
ORDER BY 1;

-- Маржинальность по позициям
CREATE OR REPLACE VIEW v_peo_profitability_by_item AS
SELECT
  COALESCE(i.name, s.item_code) AS item,
  SUM(s.revenue_rub) AS revenue_rub,
  SUM(s.cogs_rub)    AS cogs_rub,
  SUM(s.revenue_rub - s.cogs_rub) AS gross_margin_rub
FROM peo_sales s
LEFT JOIN peo_items i ON i.item_id = s.item_id
GROUP BY COALESCE(i.name, s.item_code)
ORDER BY 4 DESC;

-- Маржинальность по подразделениям (через ФОТ)
CREATE OR REPLACE VIEW v_peo_profitability_by_dept AS
WITH sales AS (
  SELECT date_trunc('month', sale_date)::date AS month_start, SUM(revenue_rub - cogs_rub) AS gm_rub
  FROM peo_sales
  GROUP BY 1
),
payroll AS (
  SELECT month_start, SUM(base_salary_rub + bonus_rub + extra_rub) AS payroll_rub
  FROM peo_payroll
  GROUP BY 1
)
SELECT
  s.month_start,
  s.gm_rub,
  COALESCE(p.payroll_rub,0) AS payroll_rub,
  s.gm_rub - COALESCE(p.payroll_rub,0) AS op_result_rub
FROM sales s
LEFT JOIN payroll p ON p.month_start = s.month_start
ORDER BY 1;

-- Сопоставление транспортных расходов к продажам (индикативно)
CREATE OR REPLACE VIEW v_peo_transport_share AS
SELECT
  date_trunc('month', s.sale_date)::date AS month_start,
  SUM(tc.amount_rub) AS transport_rub,
  SUM(s.revenue_rub) AS revenue_rub,
  SUM(tc.amount_rub) / NULLIF(SUM(s.revenue_rub),0) AS transport_share
FROM peo_sales s
LEFT JOIN peo_transport_costs tc ON tc.related_sale_id = s.sale_id
GROUP BY 1
ORDER BY 1;

-- Средний уровень зарплат vs бенчмарки (по позиции и региону; грубо)
CREATE OR REPLACE VIEW v_peo_salary_vs_benchmark AS
SELECT
  p.month_start,
  COALESCE(p.position_text,'(n/a)') AS position,
  b.region,
  AVG(p.base_salary_rub + p.bonus_rub + p.extra_rub) AS avg_payroll_rub,
  AVG(b.p50_rub) FILTER (WHERE b.period_end IS NULL OR b.period_end >= p.month_start) AS bench_p50_rub
FROM peo_payroll p
LEFT JOIN peo_salary_benchmarks b
  ON b.position_text = p.position_text
GROUP BY 1,2,3
ORDER BY 1;

-- ------------------------------------------------
-- 10) Фиксация применения миграции
-- ------------------------------------------------
INSERT INTO schema_migrations(version, description)
SELECT 'v12_peo',
       'ПЭО: продажи/COGS (RUB), транспорт, документы-основания, ФОТ, бенчмарки, рынок сырья, PPE/SMS, метрология (статусы+история), контрагенты (снимок), аналитические VIEW.'
WHERE NOT EXISTS (SELECT 1 FROM schema_migrations WHERE version = 'v12_peo');

COMMIT;


