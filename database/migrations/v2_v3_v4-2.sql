--  ERP-Биофабрика — ООК (Документооборот по шаблонам) — LEAN
--  Файл:v2_v3_v4-2.sql
--  Требует: v1_core_schema.sql
--  Изменения: УДАЛЁНА модель хранения содержимого полей документа.
--             Проверка заполненности — через OnlyOffice API (на лету).

BEGIN;

-- 1) Статусы документов/шаблонов
CREATE TABLE IF NOT EXISTS doc_statuses (
    status_code  TEXT PRIMARY KEY,              -- 'draft','active','archived'
    display_name TEXT NOT NULL
);
INSERT INTO doc_statuses(status_code, display_name)
SELECT v.status_code, v.display_name
FROM (VALUES
  ('draft','В разработке'),
  ('active','Активный'),
  ('archived','Архив')
) AS v(status_code, display_name)
LEFT JOIN doc_statuses s ON s.status_code = v.status_code
WHERE s.status_code IS NULL;

-- 2) Шаблоны .docx + метаданные + ACL
CREATE TABLE IF NOT EXISTS document_templates (
    template_id BIGSERIAL PRIMARY KEY,
    name        TEXT NOT NULL,
    file_path   TEXT NOT NULL,                  -- URI в DMS/OnlyOffice
    status_code TEXT NOT NULL REFERENCES doc_statuses(status_code),
    description TEXT,
    mime_type   TEXT,
    file_size   BIGINT,
    sha256      TEXT,
    created_by  BIGINT REFERENCES app_users(user_id),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (name, status_code)
);

CREATE TABLE IF NOT EXISTS template_acl_roles (
  acl_id       BIGSERIAL PRIMARY KEY,
  template_id  BIGINT NOT NULL REFERENCES document_templates(template_id) ON DELETE CASCADE,
  role_id      BIGINT NOT NULL REFERENCES roles(role_id) ON DELETE CASCADE,
  perm_read    BOOLEAN NOT NULL DEFAULT TRUE,
  perm_comment BOOLEAN NOT NULL DEFAULT FALSE,
  perm_edit    BOOLEAN NOT NULL DEFAULT FALSE,
  perm_sign    BOOLEAN NOT NULL DEFAULT FALSE,
  perm_manage  BOOLEAN NOT NULL DEFAULT FALSE,
  UNIQUE (template_id, role_id)
);

CREATE TABLE IF NOT EXISTS template_acl_users (
  acl_id       BIGSERIAL PRIMARY KEY,
  template_id  BIGINT NOT NULL REFERENCES document_templates(template_id) ON DELETE CASCADE,
  user_id      BIGINT NOT NULL REFERENCES app_users(user_id) ON DELETE CASCADE,
  perm_read    BOOLEAN NOT NULL DEFAULT TRUE,
  perm_comment BOOLEAN NOT NULL DEFAULT FALSE,
  perm_edit    BOOLEAN NOT NULL DEFAULT FALSE,
  perm_sign    BOOLEAN NOT NULL DEFAULT FALSE,
  perm_manage  BOOLEAN NOT NULL DEFAULT FALSE,
  UNIQUE (template_id, user_id)
);

-- 3) Метки (структура полей) + их позиции + ACL на поле
CREATE TABLE IF NOT EXISTS document_fields (
    field_id    BIGSERIAL PRIMARY KEY,
    template_id BIGINT NOT NULL REFERENCES document_templates(template_id) ON DELETE CASCADE,
    field_name  TEXT   NOT NULL,                -- имя метки (без скобок)
    is_required BOOLEAN NOT NULL DEFAULT FALSE, -- обязательность для бизнес-процесса
    ook_comment TEXT,
    UNIQUE (template_id, field_name)
);

CREATE TABLE IF NOT EXISTS document_field_positions (
  position_id BIGSERIAL PRIMARY KEY,
  field_id    BIGINT NOT NULL REFERENCES document_fields(field_id) ON DELETE CASCADE,
  page_no     INTEGER,
  paragraph_no INTEGER,
  anchor_id   TEXT,
  selector    TEXT
);

CREATE TABLE IF NOT EXISTS document_field_acl_roles (
  acl_id    BIGSERIAL PRIMARY KEY,
  field_id  BIGINT NOT NULL REFERENCES document_fields(field_id) ON DELETE CASCADE,
  role_id   BIGINT NOT NULL REFERENCES roles(role_id) ON DELETE CASCADE,
  perm_fill BOOLEAN NOT NULL DEFAULT TRUE,
  UNIQUE (field_id, role_id)
);

CREATE TABLE IF NOT EXISTS document_field_acl_users (
  acl_id    BIGSERIAL PRIMARY KEY,
  field_id  BIGINT NOT NULL REFERENCES document_fields(field_id) ON DELETE CASCADE,
  user_id   BIGINT NOT NULL REFERENCES app_users(user_id) ON DELETE CASCADE,
  perm_fill BOOLEAN NOT NULL DEFAULT TRUE,
  UNIQUE (field_id, user_id)
);

-- 4) Документы (экземпляры), версии, подписи, активность
CREATE TABLE IF NOT EXISTS documents (
    document_id BIGSERIAL PRIMARY KEY,
    template_id BIGINT REFERENCES document_templates(template_id),
    title       TEXT,
    file_path   TEXT,                            -- актуальная ревизия в DMS/OnlyOffice
    status_code TEXT NOT NULL REFERENCES doc_statuses(status_code),
    description TEXT,
    mime_type   TEXT,
    file_size   BIGINT,
    sha256      TEXT,
    created_by  BIGINT REFERENCES app_users(user_id),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS document_versions (
    version_id  BIGSERIAL PRIMARY KEY,
    document_id BIGINT NOT NULL REFERENCES documents(document_id) ON DELETE CASCADE,
    version_no  INTEGER NOT NULL,
    file_path   TEXT NOT NULL,
    modified_by BIGINT REFERENCES app_users(user_id),
    modified_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (document_id, version_no)
);

CREATE TABLE IF NOT EXISTS document_signatures (
    signature_id BIGSERIAL PRIMARY KEY,
    document_id  BIGINT NOT NULL REFERENCES documents(document_id) ON DELETE CASCADE,
    signed_by    BIGINT NOT NULL REFERENCES app_users(user_id),
    signed_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    method       TEXT NOT NULL DEFAULT 'in_app'
);

CREATE TABLE IF NOT EXISTS document_activity_log (
    log_id      BIGSERIAL PRIMARY KEY,
    document_id BIGINT REFERENCES documents(document_id) ON DELETE CASCADE,
    action      TEXT  NOT NULL,                  -- create/open/edit/save/request_signature/sign
    user_id     BIGINT REFERENCES app_users(user_id),
    details     JSONB,
    ts          TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 5) Импорт архивов
CREATE TABLE IF NOT EXISTS imported_documents (
    imported_id   BIGSERIAL PRIMARY KEY,
    source_system TEXT,
    original_path TEXT NOT NULL,
    stored_path   TEXT NOT NULL,
    imported_by   BIGINT REFERENCES app_users(user_id),
    imported_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    linked_doc_id BIGINT REFERENCES documents(document_id)
);

-- 6) Привязка документов к бизнес-объектам (досье)
CREATE TABLE IF NOT EXISTS document_bindings (
  binding_id   BIGSERIAL PRIMARY KEY,
  document_id  BIGINT NOT NULL REFERENCES documents(document_id) ON DELETE CASCADE,
  object_type  TEXT   NOT NULL,                 -- 'production_batch', ...
  object_id    BIGINT NOT NULL,                 -- ID объекта в его таблице
  purpose      TEXT,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (document_id, object_type, object_id, purpose)
);

-- 7) Индексы
CREATE INDEX IF NOT EXISTS idx_docs_status       ON documents(status_code);
CREATE INDEX IF NOT EXISTS idx_docs_template     ON documents(template_id, status_code);
CREATE INDEX IF NOT EXISTS idx_docver_doc_no     ON document_versions(document_id, version_no DESC);
CREATE INDEX IF NOT EXISTS idx_doclog_doc_time   ON document_activity_log(document_id, ts DESC);
CREATE INDEX IF NOT EXISTS idx_doc_bind_object   ON document_bindings(object_type, object_id);
CREATE INDEX IF NOT EXISTS idx_doc_bind_document ON document_bindings(document_id);

-- 8) Сиды (минимум)
INSERT INTO app_users(full_name, email)
SELECT 'ООК Ответственный', 'ook@company.local'
WHERE NOT EXISTS (SELECT 1 FROM app_users WHERE email = 'ook@company.local');

INSERT INTO document_templates(name, file_path, status_code, created_by)
SELECT 'СОП_Общий_шаблон', '/dms/templates/sop_common.docx', 'active', u.user_id
FROM app_users u
WHERE u.email = 'ook@company.local'
  AND NOT EXISTS (
      SELECT 1 FROM document_templates WHERE name='СОП_Общий_шаблон' AND status_code='active'
  );

INSERT INTO schema_migrations(version, description)
SELECT 'v2_ook_docflow_lean',
       'ООК LEAN: без хранения содержимого полей; структура меток/ACL/версии/подписи/биндинги.'
WHERE NOT EXISTS (SELECT 1 FROM schema_migrations WHERE version = 'v2_ook_docflow_lean');

COMMIT;

-- =====================================================================
--  ERP-Биофабрика — ЦПВБП (Цех производства)
--  Файл: v4_cpvbp.sql
--  Требует: v1_core_schema.sql (+ v2 OOK для документов при необходимости)
--  Смысл: справочник оборудования, серии, статусы, интервалы работы на оборудовании,
--         привязка к SCADA (ядру), «белый список» полей для ИИ и датасет ИИ.
-- =====================================================================

BEGIN;

-- 1) Оборудование
CREATE TABLE IF NOT EXISTS equipment (
  equipment_id BIGSERIAL PRIMARY KEY,
  code TEXT UNIQUE NOT NULL,     -- "FERM-01"
  name TEXT NOT NULL,            -- "Ферментер 1"
  section TEXT,                  -- участок/цех
  description TEXT
);

-- 2) Статусы серий
CREATE TABLE IF NOT EXISTS batch_statuses (
  status_code  TEXT PRIMARY KEY,            -- planned/in_progress/paused/completed/qc_ready/released/rejected/archived
  display_name TEXT NOT NULL
);
INSERT INTO batch_statuses(status_code, display_name)
SELECT v.status_code, v.display_name
FROM (VALUES
  ('planned','Запланирована'),
  ('in_progress','В работе'),
  ('paused','Пауза'),
  ('completed','Завершена'),
  ('qc_ready','На контроле качества'),
  ('released','Выпущена'),
  ('rejected','Забракована'),
  ('archived','Архив')
) AS v(status_code, display_name)
LEFT JOIN batch_statuses s ON s.status_code = v.status_code
WHERE s.status_code IS NULL;

-- 3) Серии производства
CREATE TABLE IF NOT EXISTS production_batches (
  batch_id     BIGSERIAL PRIMARY KEY,
  batch_code   TEXT UNIQUE NOT NULL,     -- внешний номер серии
  product_code TEXT NOT NULL,            -- код/артикул препарата
  status_code  TEXT NOT NULL REFERENCES batch_statuses(status_code),
  started_at   TIMESTAMPTZ,
  finished_at  TIMESTAMPTZ,
  created_by   BIGINT REFERENCES app_users(user_id),
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_batches_status ON production_batches(status_code);

-- 4) Интервалы работы серии на оборудовании (для привязки SCADA по времени)
CREATE TABLE IF NOT EXISTS batch_equipment_spans (
  span_id      BIGSERIAL PRIMARY KEY,
  batch_id     BIGINT NOT NULL REFERENCES production_batches(batch_id) ON DELETE CASCADE,
  equipment_id BIGINT NOT NULL REFERENCES equipment(equipment_id),
  span_start   TIMESTAMPTZ NOT NULL,
  span_end     TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_batch_spans_batch_eq ON batch_equipment_spans(batch_id, equipment_id, span_start);

-- 5) Прямая привязка измерений ядра к серии (опционально, для материализации)
CREATE TABLE IF NOT EXISTS batch_scada_records (
  link_id   BIGSERIAL PRIMARY KEY,
  batch_id  BIGINT NOT NULL REFERENCES production_batches(batch_id) ON DELETE CASCADE,
  record_id BIGINT NOT NULL REFERENCES data_records(record_id) ON DELETE CASCADE,
  UNIQUE (batch_id, record_id)
);

-- 6) Связка ядра с оборудованием (аддитивное поле в ядре)
ALTER TABLE data_records
  ADD COLUMN IF NOT EXISTS equipment_id BIGINT REFERENCES equipment(equipment_id);
CREATE INDEX IF NOT EXISTS idx_records_equipment_ts ON data_records(equipment_id, ts DESC);

-- 7) Белый список полей документов для ИИ + датасет ИИ
CREATE TABLE IF NOT EXISTS ai_capture_fields (
  capture_id  BIGSERIAL PRIMARY KEY,
  template_id BIGINT NOT NULL REFERENCES document_templates(template_id) ON DELETE CASCADE,
  field_id    BIGINT NOT NULL REFERENCES document_fields(field_id) ON DELETE CASCADE,
  is_enabled  BOOLEAN NOT NULL DEFAULT TRUE,
  pii_level   SMALLINT NOT NULL DEFAULT 0,    -- 0..3
  retention_policy_id BIGINT REFERENCES retention_policies(retention_policy_id),
  UNIQUE (template_id, field_id)
);

CREATE TABLE IF NOT EXISTS doc_ai_dataset (
  row_id      BIGSERIAL PRIMARY KEY,
  document_id BIGINT NOT NULL REFERENCES documents(document_id) ON DELETE CASCADE,
  batch_id    BIGINT REFERENCES production_batches(batch_id),
  field_name  TEXT NOT NULL,
  field_value TEXT,
  context     JSONB,                           -- версия шаблона, статус, этап и т.п.
  captured_by BIGINT REFERENCES app_users(user_id),
  captured_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_ai_dataset_batch ON doc_ai_dataset(batch_id);

-- 8) Сиды
INSERT INTO equipment(code, name)
SELECT v.code, v.name
FROM (VALUES ('FERM-01','Ферментер 1'), ('FERM-02','Ферментер 2')) AS v(code, name)
LEFT JOIN equipment e ON e.code = v.code
WHERE e.code IS NULL;

INSERT INTO schema_migrations(version, description)
SELECT 'v4_cpvbp',
       'Цех: оборудование, серии, статусы, интервалы работы на оборудовании, SCADA-мост, AI-сбор (селективно).'
WHERE NOT EXISTS (SELECT 1 FROM schema_migrations WHERE version = 'v4_cpvbp');

COMMIT;


--- =====================================================================
--  ERP-Биофабрика — ОВБК (Лаборатория контроля качества)
--  Файл: v3_ovbk.sql
--  Требует: v1_core_schema.sql + v2_ook_docflow.sql + v4_cpvbp.sql (серии)
--  Изменения: прямая ссылка на серию batch_id; интервалы времени; OOS через триггер
-- =====================================================================

BEGIN;

-- 1) Стадии контроля и статусы протоколов
CREATE TABLE IF NOT EXISTS lab_stages (
  stage_code   TEXT PRIMARY KEY,
  display_name TEXT NOT NULL
);
INSERT INTO lab_stages(stage_code, display_name)
SELECT v.stage_code, v.display_name
FROM (VALUES
  ('incoming','Входной контроль сырья'),
  ('in_process','Промежуточный контроль'),
  ('outgoing','Исходящий контроль')
) AS v(stage_code, display_name)
LEFT JOIN lab_stages s ON s.stage_code = v.stage_code
WHERE s.stage_code IS NULL;

CREATE TABLE IF NOT EXISTS lab_protocol_statuses (
  status_code  TEXT PRIMARY KEY,
  display_name TEXT NOT NULL
);
INSERT INTO lab_protocol_statuses(status_code, display_name)
SELECT v.status_code, v.display_name
FROM (VALUES
  ('in_work','В работе'),
  ('awaiting_sign','На подписи'),
  ('ready','Готов'),
  ('archived','Архив')
) AS v(status_code, display_name)
LEFT JOIN lab_protocol_statuses s ON s.status_code = v.status_code
WHERE s.status_code IS NULL;

-- 2) Типы анализов и параметры
CREATE TABLE IF NOT EXISTS lab_analysis_types (
  analysis_type_id BIGSERIAL PRIMARY KEY,
  code        TEXT NOT NULL UNIQUE,
  name        TEXT NOT NULL,
  description TEXT
);

CREATE TABLE IF NOT EXISTS lab_parameters (
  parameter_id BIGSERIAL PRIMARY KEY,
  analysis_type_id BIGINT NOT NULL REFERENCES lab_analysis_types(analysis_type_id) ON DELETE CASCADE,
  code        TEXT NOT NULL,
  name        TEXT NOT NULL,
  type_id     BIGINT REFERENCES data_types(type_id),
  unit_id     BIGINT REFERENCES units(unit_id),
  is_numeric  BOOLEAN NOT NULL DEFAULT TRUE,
  UNIQUE (analysis_type_id, code)
);

-- 3) Спецификации
CREATE TABLE IF NOT EXISTS lab_specs (
  spec_id       BIGSERIAL PRIMARY KEY,
  parameter_id  BIGINT NOT NULL REFERENCES lab_parameters(parameter_id) ON DELETE CASCADE,
  stage_code    TEXT   NOT NULL REFERENCES lab_stages(stage_code),
  object_type   TEXT,
  object_code   TEXT,
  valid_from    DATE   NOT NULL DEFAULT CURRENT_DATE,
  valid_to      DATE,
  min_value     DOUBLE PRECISION,
  max_value     DOUBLE PRECISION,
  regex_pattern TEXT,
  comment       TEXT
);
CREATE INDEX IF NOT EXISTS idx_lab_specs_param_stage ON lab_specs(parameter_id, stage_code);

-- 4) Образцы, привязанные к серии
CREATE TABLE IF NOT EXISTS lab_samples (
  sample_id   BIGSERIAL PRIMARY KEY,
  batch_id    BIGINT NOT NULL REFERENCES production_batches(batch_id) ON DELETE RESTRICT,
  stage_code  TEXT NOT NULL REFERENCES lab_stages(stage_code),
  sample_code TEXT,
  taken_at    TIMESTAMPTZ,
  taken_by    BIGINT REFERENCES app_users(user_id),
  note        TEXT,
  UNIQUE (batch_id, stage_code, sample_code)
);
CREATE INDEX IF NOT EXISTS idx_lab_samples_batch ON lab_samples(batch_id);

-- 5) Протоколы (обёртка вокруг документа ООК)
CREATE TABLE IF NOT EXISTS lab_protocols (
  protocol_id   BIGSERIAL PRIMARY KEY,
  document_id   BIGINT NOT NULL REFERENCES documents(document_id) ON DELETE CASCADE,
  batch_id      BIGINT NOT NULL REFERENCES production_batches(batch_id) ON DELETE RESTRICT,
  sample_id     BIGINT REFERENCES lab_samples(sample_id) ON DELETE SET NULL,
  status_code   TEXT NOT NULL REFERENCES lab_protocol_statuses(status_code),
  stage_code    TEXT NOT NULL REFERENCES lab_stages(stage_code),
  created_by    BIGINT REFERENCES app_users(user_id),
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (document_id)
);
CREATE INDEX IF NOT EXISTS idx_lab_protocols_batch ON lab_protocols(batch_id);

-- 6) Маппинг меток шаблона к параметрам
CREATE TABLE IF NOT EXISTS lab_template_field_map (
  map_id       BIGSERIAL PRIMARY KEY,
  template_id  BIGINT NOT NULL REFERENCES document_templates(template_id) ON DELETE CASCADE,
  field_id     BIGINT NOT NULL REFERENCES document_fields(field_id) ON DELETE CASCADE,
  parameter_id BIGINT NOT NULL REFERENCES lab_parameters(parameter_id) ON DELETE CASCADE,
  UNIQUE (template_id, field_id)
);

-- 7) Результаты анализов (is_out_of_spec — обычное поле, считаем триггером)
CREATE TABLE IF NOT EXISTS lab_results (
  result_id      BIGSERIAL PRIMARY KEY,
  protocol_id    BIGINT NOT NULL REFERENCES lab_protocols(protocol_id) ON DELETE CASCADE,
  parameter_id   BIGINT NOT NULL REFERENCES lab_parameters(parameter_id) ON DELETE CASCADE,
  value_num      DOUBLE PRECISION,
  value_text     TEXT,
  unit_id        BIGINT REFERENCES units(unit_id),
  interval_start TIMESTAMPTZ,
  interval_end   TIMESTAMPTZ,
  source         TEXT NOT NULL DEFAULT 'manual',  -- 'manual'/'scada'/'import'
  created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
  is_out_of_spec BOOLEAN,
  CHECK (value_num IS NOT NULL OR value_text IS NOT NULL)
);
CREATE INDEX IF NOT EXISTS idx_lab_results_protocol ON lab_results(protocol_id);
CREATE INDEX IF NOT EXISTS idx_lab_results_param    ON lab_results(parameter_id);

-- 7a) Функция вычисления OOS
CREATE OR REPLACE FUNCTION compute_lab_oos(p_param BIGINT, p_protocol BIGINT, p_value DOUBLE PRECISION)
RETURNS BOOLEAN
LANGUAGE sql
AS $$
  SELECT CASE
           WHEN p_value IS NULL THEN NULL
           ELSE (
             SELECT (p_value < COALESCE(s.min_value, -1e309)
                     OR p_value > COALESCE(s.max_value,  1e309))
             FROM lab_specs s
             JOIN lab_protocols p ON p.protocol_id = p_protocol
             WHERE s.parameter_id = p_param
               AND s.stage_code   = p.stage_code
               AND (s.valid_to IS NULL OR s.valid_to >= CURRENT_DATE)
               AND s.valid_from <= CURRENT_DATE
             ORDER BY s.valid_from DESC
             LIMIT 1
           )
         END;
$$;

-- 7b) Триггер для автоматического пересчёта
CREATE OR REPLACE FUNCTION trg_lab_results_oos()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  IF NEW.value_num IS NULL THEN
    NEW.is_out_of_spec := NULL;
  ELSE
    SELECT compute_lab_oos(NEW.parameter_id, NEW.protocol_id, NEW.value_num)
      INTO NEW.is_out_of_spec;
  END IF;
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS set_oos ON lab_results;
CREATE TRIGGER set_oos
BEFORE INSERT OR UPDATE OF value_num, parameter_id, protocol_id
ON lab_results
FOR EACH ROW
EXECUTE FUNCTION trg_lab_results_oos();

-- 7c) Связка результатов с ядром
CREATE TABLE IF NOT EXISTS lab_result_records (
  link_id    BIGSERIAL PRIMARY KEY,
  result_id  BIGINT NOT NULL REFERENCES lab_results(result_id) ON DELETE CASCADE,
  record_id  BIGINT NOT NULL REFERENCES data_records(record_id) ON DELETE CASCADE,
  UNIQUE (result_id, record_id)
);

-- 8) Вьюха: результаты вне допусков
CREATE OR REPLACE VIEW v_ovbk_out_of_spec AS
SELECT
  p.protocol_id,
  p.batch_id,
  p.stage_code,
  r.parameter_id,
  r.value_num,
  r.unit_id,
  r.is_out_of_spec,
  r.created_at
FROM lab_results r
JOIN lab_protocols p ON p.protocol_id = r.protocol_id
WHERE r.is_out_of_spec = TRUE;

-- 9) Сиды (минимум примеров)
INSERT INTO lab_analysis_types(code, name)
SELECT v.code, v.name
FROM (VALUES ('PROTEIN','Белок'), ('MOISTURE','Влажность')) AS v(code, name)
LEFT JOIN lab_analysis_types t ON t.code = v.code
WHERE t.code IS NULL;

INSERT INTO schema_migrations(version, description)
SELECT 'v3_ovbk_fk_batch',
       'ОВБК: FK batch_id; интервалы; OOS-триггер.'
WHERE NOT EXISTS (SELECT 1 FROM schema_migrations WHERE version = 'v3_ovbk_fk_batch');

COMMIT;

