--  ERP-Биофабрика — Юристы (Legal)
--  Файл: v5_legal.sql
--  База: PostgreSQL 13+
--  Требует: v1_core_schema.sql (ядро), v1_core_schema_delta.sql (workflow, deadlines),
--           v2_ook_docflow.sql (документы)
--  Назначение: договоры, стороны, риски, отклонения от шаблона, банковские гарантии,
--              привязка к workflow, статусы жизненного цикла.
--  Идемпотентность: да

BEGIN;

-- ------------------------------------------------
-- 1) Статусы договоров
-- ------------------------------------------------
CREATE TABLE IF NOT EXISTS contract_statuses (
    status_code  TEXT PRIMARY KEY,
    display_name TEXT NOT NULL
);
COMMENT ON TABLE contract_statuses IS 'Статусы жизненного цикла договоров.';

INSERT INTO contract_statuses(status_code, display_name)
SELECT v.status_code, v.display_name
FROM (VALUES
  ('draft','Черновик'),
  ('ai_check','На проверке ИИ'),
  ('legal_review','На проверке юристом'),
  ('accountant_review','На проверке бухгалтером'),
  ('director_sign','На подписи директора'),
  ('approved','Утверждён'),
  ('active','Действует'),
  ('completed','Исполнен'),
  ('terminated','Расторгнут'),
  ('overdue','Просрочен'),
  ('archived','Архив')
) AS v(status_code, display_name)
LEFT JOIN contract_statuses s ON s.status_code = v.status_code
WHERE s.status_code IS NULL;

-- ------------------------------------------------
-- 2) Типы договоров
-- ------------------------------------------------
CREATE TABLE IF NOT EXISTS contract_types (
    type_code    TEXT PRIMARY KEY,
    display_name TEXT NOT NULL
);
COMMENT ON TABLE contract_types IS 'Типы/виды договоров.';

INSERT INTO contract_types(type_code, display_name)
SELECT v.type_code, v.display_name
FROM (VALUES
  ('supply','Поставка'),
  ('service','Услуги'),
  ('lease','Аренда'),
  ('license','Лицензионный'),
  ('agency','Агентский'),
  ('loan','Займ'),
  ('other','Прочее')
) AS v(type_code, display_name)
LEFT JOIN contract_types t ON t.type_code = v.type_code
WHERE t.type_code IS NULL;

-- ------------------------------------------------
-- 3) Договоры (основная таблица)
-- ------------------------------------------------
CREATE TABLE IF NOT EXISTS contracts (
    contract_id      BIGSERIAL PRIMARY KEY,
    contract_no      TEXT UNIQUE NOT NULL,           -- уникальный номер договора
    title            TEXT NOT NULL,                  -- наименование/предмет
    type_code        TEXT REFERENCES contract_types(type_code),
    status_code      TEXT NOT NULL REFERENCES contract_statuses(status_code),

    -- Даты
    sign_date        DATE,                           -- дата подписания
    start_date       DATE,                           -- дата начала действия
    end_date         DATE,                           -- дата окончания
    performance_due  DATE,                           -- срок исполнения обязательств
    payment_due      DATE,                           -- срок оплаты

    -- Суммы
    amount_total     NUMERIC(18,2),                  -- общая сумма
    currency         TEXT DEFAULT 'RUB',             -- валюта (ISO 4217)

    -- Ответственные
    initiator_user_id BIGINT REFERENCES app_users(user_id),  -- инициатор
    responsible_user_id BIGINT REFERENCES app_users(user_id), -- ответственный
    org_unit_id      BIGINT,                         -- подразделение-владелец (опц. FK на hse_org_units)

    -- Связи
    document_id      BIGINT REFERENCES documents(document_id), -- основной документ в ООК
    parent_contract_id BIGINT REFERENCES contracts(contract_id), -- родительский договор (для ДС)

    -- Мета
    description      TEXT,
    notes            JSONB,
    created_by       BIGINT REFERENCES app_users(user_id),
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at       TIMESTAMPTZ
);
COMMENT ON TABLE contracts IS 'Реестр договоров: основные реквизиты, суммы, сроки, ответственные.';

CREATE INDEX IF NOT EXISTS idx_contracts_status ON contracts(status_code);
CREATE INDEX IF NOT EXISTS idx_contracts_type ON contracts(type_code);
CREATE INDEX IF NOT EXISTS idx_contracts_end_date ON contracts(end_date);
CREATE INDEX IF NOT EXISTS idx_contracts_initiator ON contracts(initiator_user_id);
CREATE INDEX IF NOT EXISTS idx_contracts_responsible ON contracts(responsible_user_id);

-- ------------------------------------------------
-- 4) Стороны договора
-- ------------------------------------------------
CREATE TABLE IF NOT EXISTS contract_parties (
    party_id        BIGSERIAL PRIMARY KEY,
    contract_id     BIGINT NOT NULL REFERENCES contracts(contract_id) ON DELETE CASCADE,
    role_code       TEXT NOT NULL CHECK (role_code IN ('customer','supplier','guarantor','other')),

    -- Реквизиты стороны
    name            TEXT NOT NULL,                   -- наименование организации/ФИО
    inn             TEXT,                            -- ИНН
    kpp             TEXT,                            -- КПП
    ogrn            TEXT,                            -- ОГРН/ОГРНИП
    address         TEXT,                            -- юридический адрес
    bank_details    JSONB,                           -- банковские реквизиты
    contact_person  TEXT,                            -- контактное лицо
    contact_email   TEXT,
    contact_phone   TEXT,

    -- Связь с контрагентом из ПЭО (опционально)
    counterparty_id BIGINT,                          -- REFERENCES peo_counterparties(counterparty_id)

    is_primary      BOOLEAN NOT NULL DEFAULT FALSE,  -- основная сторона по роли
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),

    UNIQUE (contract_id, role_code, inn)
);
COMMENT ON TABLE contract_parties IS 'Стороны договора: заказчик, поставщик, гарант и др.';

CREATE INDEX IF NOT EXISTS idx_contract_parties_contract ON contract_parties(contract_id);
CREATE INDEX IF NOT EXISTS idx_contract_parties_inn ON contract_parties(inn);

-- ------------------------------------------------
-- 5) Риски по договорам
-- ------------------------------------------------
CREATE TABLE IF NOT EXISTS contract_risk_types (
    risk_type_code TEXT PRIMARY KEY,
    display_name   TEXT NOT NULL
);
COMMENT ON TABLE contract_risk_types IS 'Типы рисков по договорам.';

INSERT INTO contract_risk_types(risk_type_code, display_name)
SELECT v.code, v.name
FROM (VALUES
  ('legal','Юридический'),
  ('financial','Финансовый'),
  ('operational','Операционный'),
  ('reputational','Репутационный'),
  ('compliance','Комплаенс'),
  ('other','Прочий')
) AS v(code, name)
LEFT JOIN contract_risk_types t ON t.risk_type_code = v.code
WHERE t.risk_type_code IS NULL;

CREATE TABLE IF NOT EXISTS contract_risks (
    risk_id         BIGSERIAL PRIMARY KEY,
    contract_id     BIGINT NOT NULL REFERENCES contracts(contract_id) ON DELETE CASCADE,
    risk_type_code  TEXT NOT NULL REFERENCES contract_risk_types(risk_type_code),
    severity        SMALLINT NOT NULL CHECK (severity BETWEEN 1 AND 5), -- 1=низкий, 5=критический
    description     TEXT NOT NULL,
    mitigation      TEXT,                            -- меры снижения риска
    identified_by   BIGINT REFERENCES app_users(user_id),
    identified_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    resolved_at     TIMESTAMPTZ,
    resolution_note TEXT
);
COMMENT ON TABLE contract_risks IS 'Выявленные риски по договорам.';

CREATE INDEX IF NOT EXISTS idx_contract_risks_contract ON contract_risks(contract_id);
CREATE INDEX IF NOT EXISTS idx_contract_risks_severity ON contract_risks(severity DESC);

-- ------------------------------------------------
-- 6) Отклонения от шаблона
-- ------------------------------------------------
CREATE TABLE IF NOT EXISTS contract_template_deviations (
    deviation_id    BIGSERIAL PRIMARY KEY,
    contract_id     BIGINT NOT NULL REFERENCES contracts(contract_id) ON DELETE CASCADE,
    template_id     BIGINT REFERENCES document_templates(template_id), -- от какого шаблона
    field_name      TEXT NOT NULL,                   -- название поля/раздела
    expected_value  TEXT,                            -- ожидаемое значение
    actual_value    TEXT,                            -- фактическое значение
    deviation_type  TEXT NOT NULL DEFAULT 'change',  -- 'change','addition','removal'
    justification   TEXT,                            -- обоснование отклонения
    approved_by     BIGINT REFERENCES app_users(user_id),
    approved_at     TIMESTAMPTZ,
    created_by      BIGINT REFERENCES app_users(user_id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
COMMENT ON TABLE contract_template_deviations IS 'Отклонения от типового шаблона договора.';

CREATE INDEX IF NOT EXISTS idx_contract_deviations_contract ON contract_template_deviations(contract_id);

-- ------------------------------------------------
-- 7) Банковские гарантии
-- ------------------------------------------------
CREATE TABLE IF NOT EXISTS bank_guarantee_statuses (
    status_code  TEXT PRIMARY KEY,
    display_name TEXT NOT NULL
);

INSERT INTO bank_guarantee_statuses(status_code, display_name)
SELECT v.code, v.name
FROM (VALUES
  ('pending','Ожидает получения'),
  ('active','Действует'),
  ('expired','Истекла'),
  ('claimed','Востребована'),
  ('returned','Возвращена'),
  ('cancelled','Аннулирована')
) AS v(code, name)
LEFT JOIN bank_guarantee_statuses s ON s.status_code = v.code
WHERE s.status_code IS NULL;

CREATE TABLE IF NOT EXISTS bank_guarantees (
    guarantee_id    BIGSERIAL PRIMARY KEY,
    contract_id     BIGINT NOT NULL REFERENCES contracts(contract_id) ON DELETE CASCADE,
    guarantee_no    TEXT,                            -- номер гарантии
    bank_name       TEXT NOT NULL,                   -- наименование банка
    bank_bik        TEXT,                            -- БИК банка
    amount          NUMERIC(18,2) NOT NULL,          -- сумма гарантии
    currency        TEXT DEFAULT 'RUB',
    issue_date      DATE,                            -- дата выдачи
    valid_from      DATE NOT NULL,                   -- начало действия
    valid_to        DATE NOT NULL,                   -- окончание действия
    status          TEXT NOT NULL REFERENCES bank_guarantee_statuses(status_code),
    purpose         TEXT,                            -- назначение (обеспечение исполнения, аванс и т.д.)
    document_id     BIGINT REFERENCES documents(document_id), -- скан гарантии в ООК
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ
);
COMMENT ON TABLE bank_guarantees IS 'Банковские гарантии по договорам.';

CREATE INDEX IF NOT EXISTS idx_bank_guarantees_contract ON bank_guarantees(contract_id);
CREATE INDEX IF NOT EXISTS idx_bank_guarantees_status ON bank_guarantees(status);
CREATE INDEX IF NOT EXISTS idx_bank_guarantees_valid_to ON bank_guarantees(valid_to);

-- ------------------------------------------------
-- 8) Привязка договора к workflow
-- ------------------------------------------------
CREATE TABLE IF NOT EXISTS contract_workflow_bind (
    contract_id    BIGINT PRIMARY KEY REFERENCES contracts(contract_id) ON DELETE CASCADE,
    wf_instance_id BIGINT NOT NULL REFERENCES workflow_instances(id) ON DELETE CASCADE,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);
COMMENT ON TABLE contract_workflow_bind IS 'Связь договора с инстансом workflow согласования.';

-- ------------------------------------------------
-- 9) Документы к договору (дополнительные, кроме основного)
-- ------------------------------------------------
CREATE TABLE IF NOT EXISTS contract_documents (
    link_id       BIGSERIAL PRIMARY KEY,
    contract_id   BIGINT NOT NULL REFERENCES contracts(contract_id) ON DELETE CASCADE,
    document_id   BIGINT NOT NULL REFERENCES documents(document_id) ON DELETE CASCADE,
    doc_role      TEXT NOT NULL,                     -- 'amendment','annex','protocol','act','invoice','other'
    description   TEXT,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (contract_id, document_id, doc_role)
);
COMMENT ON TABLE contract_documents IS 'Дополнительные документы к договору (ДС, приложения, акты).';

CREATE INDEX IF NOT EXISTS idx_contract_documents_contract ON contract_documents(contract_id);

-- ------------------------------------------------
-- 10) История изменений договора
-- ------------------------------------------------
CREATE TABLE IF NOT EXISTS contract_history (
    history_id    BIGSERIAL PRIMARY KEY,
    contract_id   BIGINT NOT NULL REFERENCES contracts(contract_id) ON DELETE CASCADE,
    field_name    TEXT NOT NULL,
    old_value     TEXT,
    new_value     TEXT,
    changed_by    BIGINT REFERENCES app_users(user_id),
    changed_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    reason        TEXT
);
COMMENT ON TABLE contract_history IS 'История изменений полей договора.';

CREATE INDEX IF NOT EXISTS idx_contract_history_contract ON contract_history(contract_id, changed_at DESC);

-- ------------------------------------------------
-- 11) VIEW: аналитика и контроль
-- ------------------------------------------------

-- Договоры с активной гарантией
CREATE OR REPLACE VIEW v_contracts_with_guarantee AS
SELECT
  COUNT(DISTINCT c.contract_id) FILTER (WHERE EXISTS (
    SELECT 1 FROM bank_guarantees bg
    WHERE bg.contract_id = c.contract_id AND bg.status = 'active'
  )) AS with_guarantee,
  COUNT(DISTINCT c.contract_id) AS total,
  CASE WHEN COUNT(DISTINCT c.contract_id) = 0 THEN 0
       ELSE ROUND(100.0 * COUNT(DISTINCT c.contract_id) FILTER (WHERE EXISTS (
              SELECT 1 FROM bank_guarantees bg
              WHERE bg.contract_id = c.contract_id AND bg.status = 'active'
            )) / COUNT(DISTINCT c.contract_id), 2)
  END AS pct
FROM contracts c;

-- Просроченные договоры
CREATE OR REPLACE VIEW v_contracts_overdue AS
SELECT c.contract_id, c.contract_no, c.title, c.end_date, c.status_code
FROM contracts c
WHERE c.end_date IS NOT NULL
  AND c.end_date < CURRENT_DATE
  AND c.status_code NOT IN ('completed','terminated','archived','overdue');

-- Сводка нарушений/рисков
CREATE OR REPLACE VIEW v_contracts_issues AS
SELECT
  c.contract_id,
  c.contract_no,
  COALESCE(r.risks_cnt, 0)      AS risks_cnt,
  COALESCE(d.deviations_cnt, 0) AS deviations_cnt
FROM contracts c
LEFT JOIN (
  SELECT contract_id, COUNT(*) AS risks_cnt
  FROM contract_risks
  WHERE resolved_at IS NULL
  GROUP BY contract_id
) r ON r.contract_id = c.contract_id
LEFT JOIN (
  SELECT contract_id, COUNT(*) AS deviations_cnt
  FROM contract_template_deviations
  WHERE approved_at IS NULL
  GROUP BY contract_id
) d ON d.contract_id = c.contract_id;

-- Договоры без активной гарантии
CREATE OR REPLACE VIEW v_contracts_without_guarantee AS
SELECT c.contract_id, c.contract_no, c.title
FROM contracts c
WHERE NOT EXISTS (
  SELECT 1 FROM bank_guarantees bg
  WHERE bg.contract_id = c.contract_id AND bg.status = 'active'
);

-- Договоры по статусам
CREATE OR REPLACE VIEW v_contracts_by_status AS
SELECT status_code, COUNT(*) AS cnt
FROM contracts
GROUP BY status_code;

-- Истекающие гарантии (30 дней)
CREATE OR REPLACE VIEW v_bank_guarantees_expiring_30d AS
SELECT bg.*, c.contract_no
FROM bank_guarantees bg
JOIN contracts c ON c.contract_id = bg.contract_id
WHERE bg.status = 'active'
  AND bg.valid_to <= CURRENT_DATE + INTERVAL '30 days'
  AND bg.valid_to >= CURRENT_DATE;

-- ------------------------------------------------
-- 12) Фиксация применения миграции
-- ------------------------------------------------
INSERT INTO schema_migrations(version, description)
SELECT 'v5_legal',
       'Юристы: договоры, типы, статусы, стороны, риски, отклонения от шаблона, банковские гарантии, привязка к workflow, документы, история, аналитические VIEW.'
WHERE NOT EXISTS (SELECT 1 FROM schema_migrations WHERE version = 'v5_legal');

COMMIT;
