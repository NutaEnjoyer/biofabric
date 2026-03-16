-- Аддитивные таблицы ядра. Корректируйте имена/схему при применении.
CREATE TABLE IF NOT EXISTS audit_log(
  id BIGSERIAL PRIMARY KEY,
  actor_user_id BIGINT NULL,
  actor_system TEXT NULL,
  action TEXT NOT NULL,
  resource TEXT NOT NULL,
  resource_id TEXT NOT NULL,
  diff_json JSONB NULL,
  correlation_id TEXT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS workflow_definitions(
  id BIGSERIAL PRIMARY KEY,
  code TEXT NOT NULL,
  version INT NOT NULL,
  config_json JSONB NOT NULL,
  is_active BOOLEAN NOT NULL DEFAULT TRUE
);
CREATE TABLE IF NOT EXISTS workflow_instances(
  id BIGSERIAL PRIMARY KEY,
  definition_id BIGINT NOT NULL REFERENCES workflow_definitions(id),
  entity_type TEXT NOT NULL,
  entity_id TEXT NOT NULL,
  state TEXT NOT NULL,
  context_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMP NOT NULL DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS workflow_history(
  id BIGSERIAL PRIMARY KEY,
  instance_id BIGINT NOT NULL REFERENCES workflow_instances(id),
  actor_user_id BIGINT NULL,
  action TEXT NOT NULL,
  comment TEXT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS notification_templates(
  id BIGSERIAL PRIMARY KEY,
  code TEXT UNIQUE NOT NULL,
  channel TEXT NOT NULL,
  subject_tpl TEXT NULL,
  body_tpl TEXT NOT NULL,
  locale TEXT NOT NULL DEFAULT 'ru',
  is_active BOOLEAN NOT NULL DEFAULT TRUE
);
CREATE TABLE IF NOT EXISTS jobs(
  id UUID PRIMARY KEY,
  type TEXT NOT NULL,
  payload_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  run_at TIMESTAMP NOT NULL DEFAULT NOW(),
  status TEXT NOT NULL,
  attempts INT NOT NULL DEFAULT 0,
  last_error TEXT NULL,
  idempotency_key TEXT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS integration_endpoints(
  id BIGSERIAL PRIMARY KEY,
  type TEXT NOT NULL,
  name TEXT NOT NULL,
  base_url TEXT NOT NULL,
  creds_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMP NOT NULL DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS integration_logs(
  id BIGSERIAL PRIMARY KEY,
  endpoint_id BIGINT NOT NULL REFERENCES integration_endpoints(id),
  request_meta JSONB NOT NULL DEFAULT '{}'::jsonb,
  status INT NOT NULL,
  latency_ms INT NULL,
  error_code TEXT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS proxy_endpoints(
  id BIGSERIAL PRIMARY KEY,
  name TEXT NOT NULL,
  type TEXT NOT NULL,
  host TEXT NOT NULL,
  port INT NOT NULL,
  protocol TEXT NOT NULL DEFAULT 'https',
  auth_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  health TEXT NOT NULL DEFAULT 'unknown',
  last_check_at TIMESTAMP NOT NULL DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS routing_policies(
  id BIGSERIAL PRIMARY KEY,
  provider TEXT NOT NULL,
  rules_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  failover_order JSONB NOT NULL DEFAULT '[]'::jsonb,
  rate_limit_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  is_active BOOLEAN NOT NULL DEFAULT TRUE
);
CREATE TABLE IF NOT EXISTS proxy_logs(
  id BIGSERIAL PRIMARY KEY,
  provider TEXT NOT NULL,
  endpoint_id BIGINT NULL REFERENCES proxy_endpoints(id),
  request_meta JSONB NOT NULL DEFAULT '{}'::jsonb,
  status INT NOT NULL,
  latency_ms INT NULL,
  error_code TEXT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS comments(
  id BIGSERIAL PRIMARY KEY,
  entity_type TEXT NOT NULL,
  entity_id TEXT NOT NULL,
  author_user_id BIGINT NULL,
  body TEXT NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS entity_tags(
  id BIGSERIAL PRIMARY KEY,
  entity_type TEXT NOT NULL,
  entity_id TEXT NOT NULL,
  tag TEXT NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS calendar_deadlines(
  id BIGSERIAL PRIMARY KEY,
  entity_type TEXT NOT NULL,
  entity_id TEXT NOT NULL,
  due_at TIMESTAMP NOT NULL,
  kind TEXT NOT NULL,
  title TEXT NOT NULL,
  description TEXT NULL,
  responsible_user_id BIGINT NULL,
  status TEXT NOT NULL DEFAULT 'pending',
  created_at TIMESTAMP NOT NULL DEFAULT NOW()
);
