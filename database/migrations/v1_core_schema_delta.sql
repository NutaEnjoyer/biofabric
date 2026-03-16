BEGIN;

-- =====================================================================
-- 0) Аудит действий (ядро пишет сюда все значимые операции)
-- =====================================================================
CREATE TABLE IF NOT EXISTS audit_log (
  id             BIGSERIAL PRIMARY KEY,
  actor_user_id  BIGINT NULL REFERENCES app_users(user_id),
  actor_system   TEXT   NULL,                                   -- 'system:onlyoffice_webhook', 'system:workflow_api', ...
  action         TEXT   NOT NULL,                               -- 'workflow.create', 'workflow.advance', ...
  resource       TEXT   NOT NULL,                               -- 'workflow_instance', 'document', ...
  resource_id    TEXT   NOT NULL,                               -- ID сущности в её домене
  diff_json      JSONB  NULL,                                   -- что изменилось
  correlation_id TEXT   NULL,                                   -- X-Correlation-Id
  created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_audit_created_at ON audit_log(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_resource   ON audit_log(resource, resource_id);

COMMENT ON TABLE audit_log IS 'Единый аудит действий (пользователь или системный актор).';


-- =====================================================================
-- 1) Workflow (линейные маршруты согласований + история)
-- =====================================================================
CREATE TABLE IF NOT EXISTS workflow_definitions (
  id          BIGSERIAL PRIMARY KEY,
  code        TEXT    NOT NULL,          -- 'procurement_request', 'contract_approval', ...
  version     INT     NOT NULL,
  config_json JSONB   NOT NULL,          -- { "steps": ["draft","review","approved"] }
  is_active   BOOLEAN NOT NULL DEFAULT TRUE
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_wf_def_code_ver
  ON workflow_definitions(code, version);

CREATE TABLE IF NOT EXISTS workflow_instances (
  id            BIGSERIAL PRIMARY KEY,
  definition_id BIGINT  NOT NULL REFERENCES workflow_definitions(id),
  entity_type   TEXT    NOT NULL,        -- 'proc_request', 'contract', ...
  entity_id     TEXT    NOT NULL,        -- 'REQ-1001', 'C-42', ...
  state         TEXT    NOT NULL,        -- текущий шаг
  context_json  JSONB   NOT NULL DEFAULT '{}'::jsonb,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_wf_inst_entity
  ON workflow_instances(entity_type, entity_id);

CREATE TABLE IF NOT EXISTS workflow_history (
  id            BIGSERIAL PRIMARY KEY,
  instance_id   BIGINT  NOT NULL REFERENCES workflow_instances(id) ON DELETE CASCADE,
  actor_user_id BIGINT  NULL  REFERENCES app_users(user_id),
  action        TEXT    NOT NULL,        -- 'approve' | 'reject' | ...
  comment       TEXT    NULL,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_wf_hist_instance
  ON workflow_history(instance_id);


-- =====================================================================
-- 2) Уведомления — шаблоны + расширение outbox без поломки существующей схемы
-- =====================================================================
-- 2.1 Шаблоны (ядро)
CREATE TABLE IF NOT EXISTS notification_templates (
  id          BIGSERIAL PRIMARY KEY,
  code        TEXT    NOT NULL UNIQUE,           -- 'contract_expire', ...
  channel     TEXT    NOT NULL,                  -- 'email' | 'telegram' | ...
  subject_tpl TEXT    NULL,                      -- тема (для email)
  body_tpl    TEXT    NOT NULL,                  -- тело
  locale      TEXT    NOT NULL DEFAULT 'ru',
  is_active   BOOLEAN NOT NULL DEFAULT TRUE
);

-- 2.2 Расширение существующего notifications_outbox (из v1) для режима "шаблонов":
--     Добавляем nullable-колонки под шаблонный режим ядра.
--     Делаем event_id и channel_id nullable для поддержки режима шаблонов.
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM information_schema.columns
    WHERE table_name='notifications_outbox' AND column_name='template_code'
  ) THEN
    -- Делаем старые колонки nullable для режима шаблонов
    ALTER TABLE notifications_outbox
      ALTER COLUMN event_id DROP NOT NULL,
      ALTER COLUMN channel_id DROP NOT NULL;

    -- Добавляем колонки для шаблонного режима
    ALTER TABLE notifications_outbox
      ADD COLUMN template_code TEXT NULL,
      ADD COLUMN to_json       JSONB NULL,
      ADD COLUMN payload_json  JSONB NULL;

    -- Индексы под новый режим
    CREATE INDEX IF NOT EXISTS idx_notif_outbox_template
      ON notifications_outbox(template_code);
    CREATE INDEX IF NOT EXISTS idx_notif_outbox_status
      ON notifications_outbox(status);

    -- РЕЖИМ A (старый): event_id NOT NULL AND channel_id NOT NULL
    -- РЕЖИМ B (ядро):   template_code NOT NULL AND to_json NOT NULL
  END IF;
END$$;

COMMENT ON COLUMN notifications_outbox.template_code IS 'Код шаблона (режим ядра).';
COMMENT ON COLUMN notifications_outbox.to_json       IS 'Список получателей (["boss@...","..."]).';
COMMENT ON COLUMN notifications_outbox.payload_json  IS 'Данные для подстановки в шаблон.';


-- =====================================================================
-- 3) Очередь задач / планировщик
-- =====================================================================
CREATE TABLE IF NOT EXISTS jobs (
  id               UUID    PRIMARY KEY,
  type             TEXT    NOT NULL,                 -- 'send_notifications', 'sync_1c', ...
  payload_json     JSONB   NOT NULL DEFAULT '{}'::jsonb,
  run_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
  status           TEXT    NOT NULL DEFAULT 'pending',  -- 'pending'|'processing'|'done'|'failed'|'canceled'
  attempts         INT     NOT NULL DEFAULT 0,
  last_error       TEXT    NULL,
  idempotency_key  TEXT    NULL,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_jobs_run_at    ON jobs(run_at ASC);
CREATE INDEX IF NOT EXISTS idx_jobs_status    ON jobs(status);
CREATE INDEX IF NOT EXISTS idx_jobs_idem_key  ON jobs(idempotency_key);


-- =====================================================================
-- 4) Интеграции и прокси (ИИ/внешние API) + журнал
-- =====================================================================
CREATE TABLE IF NOT EXISTS integration_endpoints (
  id          BIGSERIAL PRIMARY KEY,
  type        TEXT    NOT NULL,                   -- 'onlyoffice'|'headhunter'|'1c'|...
  name        TEXT    NOT NULL,                   -- произвольный псевдоним
  base_url    TEXT    NOT NULL,
  creds_json  JSONB   NOT NULL DEFAULT '{}'::jsonb,
  is_active   BOOLEAN NOT NULL DEFAULT TRUE,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS integration_logs (
  id           BIGSERIAL PRIMARY KEY,
  endpoint_id  BIGINT  NOT NULL REFERENCES integration_endpoints(id) ON DELETE CASCADE,
  request_meta JSONB   NOT NULL DEFAULT '{}'::jsonb,  -- headers/url/verb/body_size и т.п.
  status       INT     NOT NULL,
  latency_ms   INT     NULL,
  error_code   TEXT    NULL,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_int_logs_ep ON integration_logs(endpoint_id);

-- Прокси-эндпоинты (для провайдеров ИИ и др. внешних API)
CREATE TABLE IF NOT EXISTS proxy_endpoints (
  id          BIGSERIAL PRIMARY KEY,
  name        TEXT    NOT NULL,
  type        TEXT    NOT NULL,                   -- 'openai'|'anthropic'|'huggingface'|...
  host        TEXT    NOT NULL,
  port        INT     NOT NULL,
  protocol    TEXT    NOT NULL DEFAULT 'https',
  auth_json   JSONB   NOT NULL DEFAULT '{}'::jsonb,  -- токены/ключи/логин
  is_active   BOOLEAN NOT NULL DEFAULT TRUE,
  health      TEXT    NOT NULL DEFAULT 'unknown',
  last_check_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS routing_policies (
  id            BIGSERIAL PRIMARY KEY,
  provider      TEXT    NOT NULL,                 -- 'openai','anthropic', ...
  rules_json    JSONB   NOT NULL DEFAULT '{}'::jsonb,  -- правила маршрутизации
  failover_order JSONB  NOT NULL DEFAULT '[]'::jsonb,  -- порядок резервов
  rate_limit_json JSONB NOT NULL DEFAULT '{}'::jsonb,  -- квоты/лимиты
  is_active     BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS proxy_logs (
  id           BIGSERIAL PRIMARY KEY,
  provider     TEXT    NOT NULL,
  endpoint_id  BIGINT  NULL REFERENCES proxy_endpoints(id) ON DELETE SET NULL,
  request_meta JSONB   NOT NULL DEFAULT '{}'::jsonb,
  status       INT     NOT NULL,
  latency_ms   INT     NULL,
  error_code   TEXT    NULL,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_proxy_logs_provider ON proxy_logs(provider);


-- =====================================================================
-- 5) Универсальные комментарии/теги (для любых сущностей)
-- =====================================================================
CREATE TABLE IF NOT EXISTS comments (
  id            BIGSERIAL PRIMARY KEY,
  entity_type   TEXT    NOT NULL,
  entity_id     TEXT    NOT NULL,
  author_user_id BIGINT NULL REFERENCES app_users(user_id),
  body          TEXT    NOT NULL,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_comments_entity
  ON comments(entity_type, entity_id);

CREATE TABLE IF NOT EXISTS entity_tags (
  id           BIGSERIAL PRIMARY KEY,
  entity_type  TEXT    NOT NULL,
  entity_id    TEXT    NOT NULL,
  tag          TEXT    NOT NULL,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_entity_tag
  ON entity_tags(entity_type, entity_id, tag);


-- =====================================================================
-- 6) Ключевые даты/сроки (дедлайны)
-- =====================================================================
CREATE TABLE IF NOT EXISTS calendar_deadlines (
  id                   BIGSERIAL PRIMARY KEY,
  entity_type          TEXT    NOT NULL,
  entity_id            TEXT    NOT NULL,
  due_at               TIMESTAMPTZ NOT NULL,
  kind                 TEXT    NOT NULL,          -- 'contract_renewal','milestone', ...
  title                TEXT    NOT NULL,
  description          TEXT    NULL,
  responsible_user_id  BIGINT  NULL REFERENCES app_users(user_id),
  status               TEXT    NOT NULL DEFAULT 'pending',  -- 'pending'|'done'|'overdue'...
  created_at           TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_deadlines_due
  ON calendar_deadlines(due_at ASC);
CREATE INDEX IF NOT EXISTS idx_deadlines_entity
  ON calendar_deadlines(entity_type, entity_id);


-- =====================================================================
-- 7) Фиксация миграции-дельты
-- =====================================================================
INSERT INTO schema_migrations(version, description)
SELECT 'v1_core_schema_delta_2025-10-27',
       'Ядро: аудит, workflow, шаблоны уведомлений, расширение notifications_outbox, jobs, интеграции/прокси, комментарии/теги, дедлайны.'
WHERE NOT EXISTS (
  SELECT 1 FROM schema_migrations WHERE version='v1_core_schema_delta_2025-10-27'
);

COMMIT;

