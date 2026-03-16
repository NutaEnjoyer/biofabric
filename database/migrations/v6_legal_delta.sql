--  ERP-Биофабрика — Юристы: расширения и автоматизация
--  Файл: v6_legal_delta.sql
--  База: PostgreSQL 13+
--  Требует: v5_legal.sql (базовые таблицы), v1_core_schema_delta.sql (workflow, jobs, deadlines)
--  Назначение: workflow согласования, триггеры дедлайнов, ЕИС-интеграция, импорт 1С,
--              шаблоны уведомлений, функции-утилиты.
--  Идемпотентность: да

BEGIN;

-- ------------------------------------------------
-- 1) Workflow "contract_approval" v2
--    (draft → ai_check → legal → accountant → director → approved)
--    + возврат в draft на любом этапе
-- ------------------------------------------------
INSERT INTO workflow_definitions(code, version, config_json, is_active)
SELECT 'contract_approval', 2,
       '{
          "steps":["draft","ai_check","legal_review","accountant_review","director_sign","approved"],
          "transitions":{
            "submit":"draft->ai_check",
            "ai_pass":"ai_check->legal_review",
            "legal_approve":"legal_review->accountant_review",
            "acc_approve":"accountant_review->director_sign",
            "sign":"director_sign->approved",

            "request_changes_from_ai":"ai_check->draft",
            "request_changes_from_legal":"legal_review->draft",
            "request_changes_from_acc":"accountant_review->draft",
            "request_changes_from_dir":"director_sign->draft"
          }
        }'::jsonb, TRUE
WHERE NOT EXISTS (
  SELECT 1 FROM workflow_definitions WHERE code='contract_approval' AND version=2
);

-- ------------------------------------------------
-- 2) Триггер: синхронизация дедлайнов по датам договора
-- ------------------------------------------------
CREATE OR REPLACE FUNCTION sync_contract_deadlines()
RETURNS TRIGGER AS $$
BEGIN
  -- Удаляем старые дедлайны по этому договору
  DELETE FROM calendar_deadlines
   WHERE entity_type = 'contract'
     AND entity_id = NEW.contract_id::text
     AND kind IN ('contract_execution_due','contract_payment_due','contract_end');

  -- Срок исполнения обязательств
  IF NEW.performance_due IS NOT NULL THEN
    INSERT INTO calendar_deadlines(entity_type, entity_id, due_at, kind, title, description, responsible_user_id, status)
    VALUES ('contract', NEW.contract_id::text, NEW.performance_due, 'contract_execution_due',
            'Срок исполнения договора', 'Контроль выполнения обязательств', NEW.initiator_user_id, 'pending');
  END IF;

  -- Срок оплаты
  IF NEW.payment_due IS NOT NULL THEN
    INSERT INTO calendar_deadlines(entity_type, entity_id, due_at, kind, title, description, responsible_user_id, status)
    VALUES ('contract', NEW.contract_id::text, NEW.payment_due, 'contract_payment_due',
            'Срок оплаты по договору', 'Контроль оплаты', NEW.initiator_user_id, 'pending');
  END IF;

  -- Дата окончания договора
  IF NEW.end_date IS NOT NULL THEN
    INSERT INTO calendar_deadlines(entity_type, entity_id, due_at, kind, title, description, responsible_user_id, status)
    VALUES ('contract', NEW.contract_id::text, NEW.end_date, 'contract_end',
            'Дата окончания договора', 'Проверить пролонгацию', NEW.initiator_user_id, 'pending');
  END IF;

  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_contract_deadlines_insupd ON contracts;
CREATE TRIGGER trg_contract_deadlines_insupd
AFTER INSERT OR UPDATE OF performance_due, payment_due, end_date, initiator_user_id
ON contracts
FOR EACH ROW EXECUTE FUNCTION sync_contract_deadlines();

-- ------------------------------------------------
-- 3) Функция: пометить просроченные договоры
-- ------------------------------------------------
CREATE OR REPLACE FUNCTION mark_contract_overdue()
RETURNS INTEGER AS $$
DECLARE
  affected INTEGER;
BEGIN
  UPDATE contracts
     SET status_code = 'overdue',
         updated_at = now()
   WHERE end_date IS NOT NULL
     AND end_date < CURRENT_DATE
     AND status_code NOT IN ('completed','terminated','archived','overdue');
  GET DIAGNOSTICS affected = ROW_COUNT;
  RETURN affected;
END;
$$ LANGUAGE plpgsql;

-- ------------------------------------------------
-- 4) ЕИС: очередь экспорта и лог (если не созданы в v5)
-- ------------------------------------------------
CREATE TABLE IF NOT EXISTS eis_export_queue (
  queue_id     BIGSERIAL PRIMARY KEY,
  contract_id  BIGINT NOT NULL REFERENCES contracts(contract_id) ON DELETE CASCADE,
  payload_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  status       TEXT NOT NULL DEFAULT 'pending',  -- pending|sent|failed
  last_error   TEXT NULL,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS eis_export_log (
  log_id        BIGSERIAL PRIMARY KEY,
  queue_id      BIGINT NOT NULL REFERENCES eis_export_queue(queue_id) ON DELETE CASCADE,
  status        INT NOT NULL,
  response_json JSONB,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Эндпоинт-заглушка для ЕИС
INSERT INTO integration_endpoints(type, name, base_url, creds_json, is_active)
SELECT 'eis', 'eis_stub', 'https://eis.stub/api', '{}', FALSE
WHERE NOT EXISTS (SELECT 1 FROM integration_endpoints WHERE type='eis' AND name='eis_stub');

-- Функция постановки в очередь отправки
CREATE OR REPLACE FUNCTION enqueue_eis_send(p_queue_id BIGINT)
RETURNS UUID AS $$
DECLARE v_id UUID := gen_random_uuid();
BEGIN
  INSERT INTO jobs(id, type, payload_json, run_at, status, attempts, idempotency_key)
  VALUES (v_id, 'send_eis_contract', jsonb_build_object('queue_id', p_queue_id), now(), 'pending', 0, 'eis:'||p_queue_id::text);
  RETURN v_id;
END;
$$ LANGUAGE plpgsql;

-- ------------------------------------------------
-- 5) Импорт из 1С: стейджинг
-- ------------------------------------------------
CREATE TABLE IF NOT EXISTS import_contracts_1c (
  id           BIGSERIAL PRIMARY KEY,
  payload_json JSONB NOT NULL,
  received_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
COMMENT ON TABLE import_contracts_1c IS 'Стейджинг импортированных из 1С договоров (REST).';

-- ------------------------------------------------
-- 6) Шаблоны уведомлений для модуля
-- ------------------------------------------------
INSERT INTO notification_templates(code, channel, subject_tpl, body_tpl, locale, is_active)
SELECT v.code, v.channel, v.subject, v.body, 'ru', TRUE
FROM (VALUES
  ('contract_new_for_review','email','Новый договор на проверку','Договор {{contract_no}} ожидает проверки.'),
  ('contract_execution_due','messenger',NULL,'Срок исполнения по договору {{contract_no}} приближается: {{due_at}}.'),
  ('contract_term_expiring','email','Истекает срок договора','Срок договора {{contract_no}} истекает {{end_date}}.'),
  ('contract_approved','email','Договор утверждён','Договор {{contract_no}} успешно утверждён.'),
  ('contract_rejected','email','Договор отклонён','Договор {{contract_no}} отклонён. Причина: {{reason}}.')
) AS v(code, channel, subject, body)
LEFT JOIN notification_templates t ON t.code = v.code
WHERE t.id IS NULL;

-- ------------------------------------------------
-- 7) Функция аудита действий с договором
-- ------------------------------------------------
CREATE OR REPLACE FUNCTION audit_contract_action(
  p_action TEXT,
  p_contract_id BIGINT,
  p_actor BIGINT,
  p_diff JSONB
)
RETURNS VOID AS $$
BEGIN
  INSERT INTO audit_log(actor_user_id, actor_system, action, resource, resource_id, diff_json, correlation_id, created_at)
  VALUES (p_actor, NULL, p_action, 'contract', p_contract_id::text, p_diff, NULL, now());
END;
$$ LANGUAGE plpgsql;

-- ------------------------------------------------
-- 8) Фиксация применения миграции
-- ------------------------------------------------
INSERT INTO schema_migrations(version, description)
SELECT 'v6_legal_delta',
       'Юристы (delta): workflow v2, триггер дедлайнов, ЕИС-очередь, импорт 1С, шаблоны уведомлений, функции аудита.'
WHERE NOT EXISTS (SELECT 1 FROM schema_migrations WHERE version = 'v6_legal_delta');

COMMIT;
