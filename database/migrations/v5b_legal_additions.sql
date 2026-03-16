-- ERP-Биофабрика — Legal Service
-- Файл: v5b_legal_additions.sql
-- Назначение: Источник договора, статус исходящей интеграции с 1С, ИИ-анализ
-- Идемпотентность: да

BEGIN;

-- ------------------------------------------------
-- 1) Источник договора и статус исходящей интеграции с 1С
-- ------------------------------------------------
ALTER TABLE contracts ADD COLUMN IF NOT EXISTS source_code TEXT NOT NULL DEFAULT 'manual';
ALTER TABLE contracts ADD COLUMN IF NOT EXISTS integration_1c_status TEXT NOT NULL DEFAULT 'not_sent';
ALTER TABLE contracts ADD COLUMN IF NOT EXISTS integration_1c_error TEXT;
ALTER TABLE contracts ADD COLUMN IF NOT EXISTS integration_1c_sent_at TIMESTAMPTZ;

COMMENT ON COLUMN contracts.source_code IS 'Источник договора: manual | 1c_import';
COMMENT ON COLUMN contracts.integration_1c_status IS 'Статус исходящей интеграции с 1С: not_sent | queued | sent | error';
COMMENT ON COLUMN contracts.integration_1c_error IS 'Текст ошибки интеграции с 1С (если статус error)';
COMMENT ON COLUMN contracts.integration_1c_sent_at IS 'Дата успешной отправки в 1С';

-- ------------------------------------------------
-- 2) Таблица ИИ-анализов договоров
-- ------------------------------------------------
CREATE TABLE IF NOT EXISTS contract_analyses (
    analysis_id       BIGSERIAL PRIMARY KEY,
    contract_id       BIGINT NOT NULL REFERENCES contracts(contract_id) ON DELETE CASCADE,
    status            TEXT NOT NULL DEFAULT 'pending',
                      -- pending | running | done | needs_rerun
    analyzed_by       BIGINT REFERENCES app_users(user_id),
    analyzed_at       TIMESTAMPTZ,
    document_version  TEXT,
    deviations_count  INT NOT NULL DEFAULT 0,
    has_critical_risk BOOLEAN NOT NULL DEFAULT FALSE,
    summary_text      TEXT,
    details_json      JSONB,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at        TIMESTAMPTZ
);

COMMENT ON TABLE contract_analyses IS 'История ИИ-анализов договоров. Статусы: pending|running|done|needs_rerun.';

CREATE INDEX IF NOT EXISTS idx_contract_analyses_contract
    ON contract_analyses(contract_id, created_at DESC);

-- ------------------------------------------------
-- 3) Фиксация применения миграции
-- ------------------------------------------------
INSERT INTO schema_migrations(version, description)
SELECT 'v5b_legal_additions',
       'Legal: source_code + integration_1c_status на contracts, таблица contract_analyses для ИИ-анализа.'
WHERE NOT EXISTS (SELECT 1 FROM schema_migrations WHERE version = 'v5b_legal_additions');

COMMIT;
