-- Legal Service — предметные таблицы модуля
-- Требует: database/v5_legal.sql (базовые таблицы contracts, bank_guarantees и др.)
-- Этот файл содержит ТОЛЬКО дополнительные таблицы, специфичные для сервиса.
-- Основные таблицы (contracts, contract_parties, contract_risks и т.д.)
-- определены в v5_legal.sql и применяются централизованно.

BEGIN;

-- 1) Привязка договора к workflow (если ещё не создана в v5_legal.sql)
CREATE TABLE IF NOT EXISTS contract_workflow_bind (
    contract_id    BIGINT PRIMARY KEY REFERENCES contracts(contract_id) ON DELETE CASCADE,
    wf_instance_id BIGINT NOT NULL REFERENCES workflow_instances(id) ON DELETE CASCADE,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);
COMMENT ON TABLE contract_workflow_bind IS 'Связь договора с инстансом workflow согласования.';

-- 2) ЕИС: очередь экспорта
CREATE TABLE IF NOT EXISTS eis_export_queue (
    queue_id     BIGSERIAL PRIMARY KEY,
    contract_id  BIGINT NOT NULL REFERENCES contracts(contract_id) ON DELETE CASCADE,
    payload_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    status       TEXT NOT NULL DEFAULT 'pending',  -- pending|sent|failed
    last_error   TEXT NULL,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
COMMENT ON TABLE eis_export_queue IS 'Очередь экспорта договоров в ЕИС.';

CREATE INDEX IF NOT EXISTS idx_eis_export_queue_status ON eis_export_queue(status);

-- 3) ЕИС: лог обмена
CREATE TABLE IF NOT EXISTS eis_export_log (
    log_id        BIGSERIAL PRIMARY KEY,
    queue_id      BIGINT NOT NULL REFERENCES eis_export_queue(queue_id) ON DELETE CASCADE,
    status        INT NOT NULL,
    response_json JSONB,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
COMMENT ON TABLE eis_export_log IS 'Журнал обмена с ЕИС.';

-- 4) Импорт из 1С: стейджинг
CREATE TABLE IF NOT EXISTS import_contracts_1c (
    id           BIGSERIAL PRIMARY KEY,
    payload_json JSONB NOT NULL,
    received_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
COMMENT ON TABLE import_contracts_1c IS 'Стейджинг импортированных из 1С договоров (REST).';

COMMIT;
