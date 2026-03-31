--  ERP-Биофабрика — ОКС (Объекты капитального строительства)
--  Файл: v13_oks.sql
--  База: PostgreSQL 13+
--  Требует: v1_core_schema.sql (ядро), v2_ook_docflow.sql (ООК),
--           peo_counterparties (опц. для подрядчиков)
--  Принципы: иерархия этапов, план одна активная версия + история (SCD2),
--            факт отдельными строками, статусы общие, документы ОКС
--            с ролями/статусами и ссылкой на ООК, конфиг оповещений,
--            специальные VIEW (Gantt, бюджеты, просрочки).
--  Идемпотентность: да

BEGIN;

-- ------------------------------------------------
-- 0) Общие статусы
-- ------------------------------------------------
CREATE TABLE IF NOT EXISTS oks_statuses (
  status_code  TEXT PRIMARY KEY,     -- 'planned','in_progress','suspended','completed'
  display_name TEXT NOT NULL
);
INSERT INTO oks_statuses(status_code, display_name)
SELECT v.code, v.name FROM (VALUES
  ('planned','Планируется'),
  ('in_progress','В работе'),
  ('suspended','Приостановлен'),
  ('completed','Завершён')
) AS v(code,name)
LEFT JOIN oks_statuses s ON s.status_code=v.code
WHERE s.status_code IS NULL;

-- ------------------------------------------------
-- 1) Объекты ОКС
-- ------------------------------------------------
CREATE TABLE IF NOT EXISTS oks_objects (
  object_id          BIGSERIAL PRIMARY KEY,
  code               TEXT UNIQUE,                -- внутренний код/шифр
  name               TEXT NOT NULL,
  status_code        TEXT NOT NULL REFERENCES oks_statuses(status_code),
  owner_user_id      BIGINT REFERENCES app_users(user_id),
  department_id      BIGINT,                     -- REFERENCES core_departments(department_id) опц.
  planned_start      DATE,
  planned_end        DATE,
  actual_start       DATE,
  actual_end         DATE,
  external_object_id TEXT,                       -- опц. ID из внешней системы (1С и пр.)
  created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at         TIMESTAMPTZ
);
COMMENT ON TABLE oks_objects IS 'Карточки объектов капитального строительства.';

-- ------------------------------------------------
-- 2) Этапы (иерархия до 2–3 уровней)
-- ------------------------------------------------
CREATE TABLE IF NOT EXISTS oks_stages (
  stage_id            BIGSERIAL PRIMARY KEY,
  object_id           BIGINT NOT NULL REFERENCES oks_objects(object_id) ON DELETE CASCADE,
  parent_stage_id     BIGINT REFERENCES oks_stages(stage_id) ON DELETE SET NULL,
  name                TEXT NOT NULL,
  status_code         TEXT NOT NULL REFERENCES oks_statuses(status_code),
  stage_owner_user_id BIGINT REFERENCES app_users(user_id),
  planned_start       DATE,
  planned_end         DATE,
  actual_start        DATE,
  actual_end          DATE,
  is_completed        BOOLEAN NOT NULL DEFAULT FALSE,
  completed_at        DATE,
  has_issue           BOOLEAN NOT NULL DEFAULT FALSE,
  suspend_reason_text TEXT,
  external_stage_id   TEXT,                      -- опц. ID из внешней системы
  created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at          TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_oks_stages_object ON oks_stages(object_id);
CREATE INDEX IF NOT EXISTS idx_oks_stages_parent ON oks_stages(parent_stage_id);

-- Соисполнители этапа (пользователи)
CREATE TABLE IF NOT EXISTS oks_stage_coexecutors (
  link_id   BIGSERIAL PRIMARY KEY,
  stage_id  BIGINT NOT NULL REFERENCES oks_stages(stage_id) ON DELETE CASCADE,
  user_id   BIGINT NOT NULL REFERENCES app_users(user_id),
  UNIQUE(stage_id, user_id)
);

-- Подрядчики этапа (контрагенты из ПЭО, опционально)
CREATE TABLE IF NOT EXISTS oks_stage_contractors (
  link_id        BIGSERIAL PRIMARY KEY,
  stage_id       BIGINT NOT NULL REFERENCES oks_stages(stage_id) ON DELETE CASCADE,
  counterparty_id BIGINT,  -- REFERENCES peo_counterparties(counterparty_id)
  name_text      TEXT,     -- если реестр контрагентов не используется
  UNIQUE(stage_id, counterparty_id, name_text)
);

-- ------------------------------------------------
-- 3) Шаблоны этапов (быстрое разворачивание)
-- ------------------------------------------------
CREATE TABLE IF NOT EXISTS oks_stage_templates (
  template_id BIGSERIAL PRIMARY KEY,
  code        TEXT UNIQUE,
  name        TEXT NOT NULL,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS oks_stage_template_items (
  item_id     BIGSERIAL PRIMARY KEY,
  template_id BIGINT NOT NULL REFERENCES oks_stage_templates(template_id) ON DELETE CASCADE,
  parent_item_id BIGINT REFERENCES oks_stage_template_items(item_id) ON DELETE SET NULL,
  name        TEXT NOT NULL,
  order_no    INT
);

-- ------------------------------------------------
-- 4) План (одна активная версия + история правок)
--     SCD2 по планам: каждая правка = новая версия с периодом действия
-- ------------------------------------------------
CREATE TABLE IF NOT EXISTS oks_stage_plan_versions (
  plan_version_id BIGSERIAL PRIMARY KEY,
  stage_id        BIGINT NOT NULL REFERENCES oks_stages(stage_id) ON DELETE CASCADE,
  version_no      INT NOT NULL,                         -- 1..N
  valid_from      TIMESTAMPTZ NOT NULL DEFAULT now(),
  valid_to        TIMESTAMPTZ,                          -- NULL = текущая версия
  -- Плановые сроки
  plan_start      DATE,
  plan_end        DATE,
  -- Плановые суммы (RUB) c НДС
  amount_net_rub  NUMERIC(18,2),                        -- без НДС
  vat_rate_pct    NUMERIC(5,2),                         -- напр. 0/10/20
  amount_vat_rub  NUMERIC(18,2),
  amount_gross_rub NUMERIC(18,2),                       -- с НДС
  -- Причина/комментарий правки
  reason_text     TEXT,
  author_user_id  BIGINT REFERENCES app_users(user_id)
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_oks_stage_plan_versions ON oks_stage_plan_versions(stage_id, version_no);

-- ------------------------------------------------
-- 5) Факт (RUB), отдельными строками
-- ------------------------------------------------
CREATE TABLE IF NOT EXISTS oks_stage_facts (
  fact_id        BIGSERIAL PRIMARY KEY,
  stage_id       BIGINT NOT NULL REFERENCES oks_stages(stage_id) ON DELETE CASCADE,
  fact_date      DATE NOT NULL,
  amount_net_rub NUMERIC(18,2) NOT NULL DEFAULT 0,
  vat_rate_pct   NUMERIC(5,2),
  amount_vat_rub NUMERIC(18,2) NOT NULL DEFAULT 0,
  amount_gross_rub NUMERIC(18,2) NOT NULL DEFAULT 0,
  basis_text     TEXT,                                   -- короткая ссылка/основание
  created_by     BIGINT REFERENCES app_users(user_id),
  created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_oks_stage_facts_stage_date ON oks_stage_facts(stage_id, fact_date);

-- ------------------------------------------------
-- 6) Комментарии (фид)
-- ------------------------------------------------
CREATE TABLE IF NOT EXISTS oks_comments (
  comment_id  BIGSERIAL PRIMARY KEY,
  object_id   BIGINT REFERENCES oks_objects(object_id) ON DELETE CASCADE,
  stage_id    BIGINT REFERENCES oks_stages(stage_id) ON DELETE CASCADE,
  author_id   BIGINT REFERENCES app_users(user_id),
  text        TEXT NOT NULL,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  CHECK (object_id IS NOT NULL OR stage_id IS NOT NULL)
);

-- ------------------------------------------------
-- 7) Документы ОКС (карточка + ссылка на файл в ООК)
-- ------------------------------------------------
CREATE TABLE IF NOT EXISTS oks_documents (
  oks_doc_id    BIGSERIAL PRIMARY KEY,
  document_id   BIGINT NOT NULL REFERENCES documents(document_id) ON DELETE CASCADE,  -- файл в ООК
  doc_type      TEXT NOT NULL,        -- 'order','memo','act','spec','drawing','tz','contract','scan_archive','other'
  doc_status    TEXT NOT NULL,        -- 'draft','review','approved'
  bind_object_type TEXT NOT NULL,     -- 'object','stage','comment'
  bind_object_id   BIGINT NOT NULL,   -- id соответствующей сущности
  created_by    BIGINT REFERENCES app_users(user_id),
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_oks_documents_bind ON oks_documents(bind_object_type, bind_object_id);
COMMENT ON TABLE oks_documents IS 'Карточки документов ОКС (логика) + ссылка на физический файл в ООК.';

-- ------------------------------------------------
-- 8) Конфигурация оповещений (пороги)
-- ------------------------------------------------
CREATE TABLE IF NOT EXISTS oks_notification_rules (
  rule_code   TEXT PRIMARY KEY,     -- 'overdue_stage_10d','overdue_stage_5d','stale_object'
  is_enabled  BOOLEAN NOT NULL DEFAULT TRUE,
  threshold_days INT NOT NULL,      -- для 'stale_object' = X; для overdue = число дней просрочки
  note        TEXT
);
INSERT INTO oks_notification_rules(rule_code, is_enabled, threshold_days, note)
SELECT v.code, TRUE, v.days, v.note
FROM (VALUES
  ('overdue_stage_10d', 10, 'Просрочка этапа ≥ 10 дней'),
  ('overdue_stage_5d',   5, 'Просрочка этапа ≥ 5 дней'),
  ('stale_object',      14, 'Объект не обновлялся ≥ X дней')
) AS v(code, days, note)
LEFT JOIN oks_notification_rules r ON r.rule_code=v.code
WHERE r.rule_code IS NULL;

-- ------------------------------------------------
-- 9) VIEW для фронта/аналитики
-- ------------------------------------------------

-- 9.1 Gantt-view: данные для диаграммы Ганта по этапам
CREATE OR REPLACE VIEW v_oks_gantt AS
SELECT
  s.stage_id,
  s.object_id,
  s.parent_stage_id,
  s.name,
  s.status_code,
  -- план берём из текущей версии плана (valid_to IS NULL) если есть, иначе поля из s.*
  COALESCE(p.plan_start, s.planned_start) AS plan_start,
  COALESCE(p.plan_end,   s.planned_end)   AS plan_end,
  s.actual_start,
  s.actual_end,
  s.is_completed,
  CASE WHEN s.is_completed THEN false
       WHEN COALESCE(p.plan_end, s.planned_end) IS NOT NULL
            AND CURRENT_DATE > COALESCE(p.plan_end, s.planned_end)
            THEN true ELSE false END AS is_overdue
FROM oks_stages s
LEFT JOIN oks_stage_plan_versions p
  ON p.stage_id = s.stage_id AND p.valid_to IS NULL;

-- 9.2 План vs факт по бюджету (на уровне этапов и объектов)
CREATE OR REPLACE VIEW v_oks_budget_plan_vs_fact AS
WITH plan_agg AS (
  SELECT stage_id,
         SUM(COALESCE(amount_net_rub,0)) AS plan_net_rub,
         SUM(COALESCE(amount_vat_rub,0)) AS plan_vat_rub,
         SUM(COALESCE(amount_gross_rub,0)) AS plan_gross_rub
  FROM oks_stage_plan_versions
  WHERE valid_to IS NULL
  GROUP BY stage_id
),
fact_agg AS (
  SELECT stage_id,
         SUM(amount_net_rub) AS fact_net_rub,
         SUM(amount_vat_rub) AS fact_vat_rub,
         SUM(amount_gross_rub) AS fact_gross_rub
  FROM oks_stage_facts
  GROUP BY stage_id
)
SELECT
  s.object_id,
  s.stage_id,
  COALESCE(p.plan_net_rub,0) AS plan_net_rub,
  COALESCE(f.fact_net_rub,0) AS fact_net_rub,
  COALESCE(p.plan_gross_rub,0) AS plan_gross_rub,
  COALESCE(f.fact_gross_rub,0) AS fact_gross_rub,
  COALESCE(f.fact_gross_rub,0) - COALESCE(p.plan_gross_rub,0) AS delta_gross_rub
FROM oks_stages s
LEFT JOIN plan_agg p ON p.stage_id=s.stage_id
LEFT JOIN fact_agg f ON f.stage_id=s.stage_id;

-- 9.3 Просроченные этапы по ответственным
CREATE OR REPLACE VIEW v_oks_overdue_by_owner AS
SELECT
  s.stage_owner_user_id,
  COUNT(*) AS overdue_cnt
FROM v_oks_gantt g
JOIN oks_stages s ON s.stage_id=g.stage_id
WHERE g.is_overdue = true AND s.is_completed = false
GROUP BY s.stage_owner_user_id;

-- ------------------------------------------------
-- 9b) Иерархия объектов и инициатор (доп. поля)
-- ------------------------------------------------
ALTER TABLE oks_objects ADD COLUMN IF NOT EXISTS parent_object_id BIGINT REFERENCES oks_objects(object_id);
ALTER TABLE oks_objects ADD COLUMN IF NOT EXISTS initiator_user_id BIGINT REFERENCES app_users(user_id);
ALTER TABLE oks_objects ADD COLUMN IF NOT EXISTS description TEXT;
ALTER TABLE oks_objects ADD COLUMN IF NOT EXISTS object_type TEXT;
CREATE INDEX IF NOT EXISTS idx_oks_objects_parent ON oks_objects(parent_object_id);

-- ------------------------------------------------
-- 10) Фиксация применения миграции
-- ------------------------------------------------
INSERT INTO schema_migrations(version, description)
SELECT 'v13_oks',
       'ОКС: объекты, этапы (иерархия), шаблоны, планы (SCD2) с НДС, факты, комментарии, документы ОКС с ссылкой на ООК, конфиг оповещений, VIEW (Gantt, бюджеты, просрочки).'
WHERE NOT EXISTS (SELECT 1 FROM schema_migrations WHERE version='v13_oks');

COMMIT;



