--  ERP-Биофабрика — Закупки
--  Файл: v9_procurement
--  База: PostgreSQL 13+
--  Требует: v1_core_schema.sql (ядро), v2_ook_docflow.sql (ООК)
--  Назначение: заявки на закупку, маршруты согласования, заказы, ТТК,
--              интеграция с 1С, аналитика и отчётность.
--  Идемпотентность: да


BEGIN;

-- ------------------------------------------------
-- 1) Статусы заявок
-- ------------------------------------------------
CREATE TABLE IF NOT EXISTS purch_request_statuses (
    status_code  TEXT PRIMARY KEY,
    display_name TEXT NOT NULL
);
COMMENT ON TABLE purch_request_statuses IS 'Статусы заявок на закупку.';

INSERT INTO purch_request_statuses(status_code, display_name)
SELECT v.status_code, v.display_name
FROM (VALUES
  ('draft','Черновик'),
  ('under_review','На проверке'),
  ('under_approval','На согласовании'),
  ('returned','На доработке'),
  ('approved','Утверждена'),
  ('ordering','В закупке'),
  ('done','Выполнена'),
  ('rejected','Отклонена')
) AS v(status_code, display_name)
LEFT JOIN purch_request_statuses s ON s.status_code = v.status_code
WHERE s.status_code IS NULL;

-- ------------------------------------------------
-- 2) Заявки на закупку (карточка)
-- ------------------------------------------------
CREATE TABLE IF NOT EXISTS purch_requests (
    request_id    BIGSERIAL PRIMARY KEY,
    title         TEXT NOT NULL,
    description   TEXT,
    initiator_id  BIGINT REFERENCES app_users(user_id),
    department    TEXT,
    status_code   TEXT NOT NULL REFERENCES purch_request_statuses(status_code),
    justification TEXT,
    document_id   BIGINT REFERENCES documents(document_id),
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ,
    approved_at   TIMESTAMPTZ,
    rejected_at   TIMESTAMPTZ
);
COMMENT ON TABLE purch_requests IS 'Заявки на закупку (инициатор, обоснование, статус, ссылки на документы).';

-- ------------------------------------------------
-- 8) ТТК (продукты и компоненты)
-- ------------------------------------------------
CREATE TABLE IF NOT EXISTS purch_ttk_products (
    product_id  BIGSERIAL PRIMARY KEY,
    name        TEXT NOT NULL,
    base_volume NUMERIC(14,3) NOT NULL,
    UNIQUE(name)
);
COMMENT ON TABLE purch_ttk_products IS 'Продукция из ТТК.';

CREATE TABLE IF NOT EXISTS purch_ttk_components (
    component_id BIGSERIAL PRIMARY KEY,
    product_id   BIGINT NOT NULL REFERENCES purch_ttk_products(product_id) ON DELETE CASCADE,
    name         TEXT NOT NULL,
    norm_qty     NUMERIC(14,3) NOT NULL,
    unit         TEXT NOT NULL
);
COMMENT ON TABLE purch_ttk_components IS 'Компоненты продукции по нормам расхода (ТТК).';

-- ------------------------------------------------
-- 3) Позиции заявки
-- ------------------------------------------------
CREATE TABLE IF NOT EXISTS purch_request_items (
    item_id       BIGSERIAL PRIMARY KEY,
    request_id    BIGINT NOT NULL REFERENCES purch_requests(request_id) ON DELETE CASCADE,
    name          TEXT NOT NULL,
    description   TEXT,
    quantity      NUMERIC(14,3) NOT NULL,
    unit          TEXT NOT NULL,
    deadline      DATE,
    est_unit_price NUMERIC(14,2),
    currency      CHAR(3),
    ttk_component_id BIGINT REFERENCES purch_ttk_components(component_id),
    UNIQUE (request_id, name)
);
COMMENT ON TABLE purch_request_items IS 'Позиции внутри заявки (товары, сырьё, услуги).';

-- ------------------------------------------------
-- 4) История и комментарии
-- ------------------------------------------------
CREATE TABLE IF NOT EXISTS purch_request_history (
    history_id   BIGSERIAL PRIMARY KEY,
    request_id   BIGINT NOT NULL REFERENCES purch_requests(request_id) ON DELETE CASCADE,
    status_code  TEXT NOT NULL REFERENCES purch_request_statuses(status_code),
    changed_by   BIGINT REFERENCES app_users(user_id),
    changed_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
COMMENT ON TABLE purch_request_history IS 'История изменения статусов заявки.';

CREATE TABLE IF NOT EXISTS purch_request_comments (
    comment_id   BIGSERIAL PRIMARY KEY,
    request_id   BIGINT NOT NULL REFERENCES purch_requests(request_id) ON DELETE CASCADE,
    author_id    BIGINT REFERENCES app_users(user_id),
    text         TEXT NOT NULL,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
COMMENT ON TABLE purch_request_comments IS 'Комментарии при возвратах или обсуждении заявки.';

-- ------------------------------------------------
-- 5) Документы к заявке (типы)
-- ------------------------------------------------
CREATE TABLE IF NOT EXISTS purch_request_docs (
    link_id     BIGSERIAL PRIMARY KEY,
    request_id  BIGINT NOT NULL REFERENCES purch_requests(request_id) ON DELETE CASCADE,
    document_id BIGINT NOT NULL REFERENCES documents(document_id) ON DELETE CASCADE,
    doc_role    TEXT NOT NULL,       -- 'rfq','quote','spec','drawing','contract','invoice','other'
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (request_id, document_id, doc_role)
);
COMMENT ON TABLE purch_request_docs IS 'Документы, прикреплённые к заявке (роль: КП, спецификация, договор и т.п.).';

-- ------------------------------------------------
-- 6) Заказы и интеграция с 1С
-- ------------------------------------------------
CREATE TABLE IF NOT EXISTS purch_orders (
    order_id     BIGSERIAL PRIMARY KEY,
    request_id   BIGINT REFERENCES purch_requests(request_id) ON DELETE SET NULL,
    supplier     TEXT,
    contract_no  TEXT,
    amount       NUMERIC(14,2),
    status       TEXT,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
COMMENT ON TABLE purch_orders IS 'Заказы поставщикам, сформированные на основе заявок.';

-- Импорт из 1С (staging)
CREATE TABLE IF NOT EXISTS purch_1c_import_jobs (
    job_id      BIGSERIAL PRIMARY KEY,
    started_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at TIMESTAMPTZ,
    kind        TEXT NOT NULL,
    status      TEXT NOT NULL DEFAULT 'pending',
    error       TEXT
);
COMMENT ON TABLE purch_1c_import_jobs IS 'Staging: задачи импорта из 1С (остатки, заказы, оплаты, отгрузки).';

CREATE TABLE IF NOT EXISTS purch_1c_import_rows (
    row_id      BIGSERIAL PRIMARY KEY,
    job_id      BIGINT NOT NULL REFERENCES purch_1c_import_jobs(job_id) ON DELETE CASCADE,
    payload     JSONB,
    parsed      JSONB,
    status      TEXT NOT NULL DEFAULT 'new',
    error       TEXT
);
COMMENT ON TABLE purch_1c_import_rows IS 'Staging: строки импорта из 1С (сырой JSON + парсинг).';

-- Экспорт в 1С
CREATE TABLE IF NOT EXISTS purch_1c_export_queue (
    queue_id    BIGSERIAL PRIMARY KEY,
    request_id  BIGINT REFERENCES purch_requests(request_id) ON DELETE CASCADE,
    payload     JSONB,
    status      TEXT NOT NULL DEFAULT 'pending',
    last_error  TEXT,
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
COMMENT ON TABLE purch_1c_export_queue IS 'Очередь экспорта утверждённых заявок в 1С.';

CREATE TABLE IF NOT EXISTS purch_1c_export_log (
    log_id      BIGSERIAL PRIMARY KEY,
    queue_id    BIGINT NOT NULL REFERENCES purch_1c_export_queue(queue_id) ON DELETE CASCADE,
    ts          TIMESTAMPTZ NOT NULL DEFAULT now(),
    direction   TEXT NOT NULL,
    payload     JSONB,
    http_status INT,
    error       TEXT
);
COMMENT ON TABLE purch_1c_export_log IS 'Журнал обмена с 1С по заявкам.';

-- ------------------------------------------------
-- 7) AI-подсказки
-- ------------------------------------------------
CREATE TABLE IF NOT EXISTS purch_ai_suggestions (
    suggestion_id BIGSERIAL PRIMARY KEY,
    request_id    BIGINT NOT NULL REFERENCES purch_requests(request_id) ON DELETE CASCADE,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    suggestion    TEXT NOT NULL,
    score         NUMERIC(5,2)
);
COMMENT ON TABLE purch_ai_suggestions IS 'Подсказки ИИ по формулировке обоснований в заявках.';


-- ------------------------------------------------
-- 9) Аналитические VIEW
-- ------------------------------------------------
-- Статусы
CREATE OR REPLACE VIEW v_purch_requests_by_status AS
SELECT status_code, count(*) AS cnt
FROM purch_requests
GROUP BY status_code;

-- Среднее время согласования
CREATE OR REPLACE VIEW v_purch_avg_approval_time AS
SELECT avg(EXTRACT(EPOCH FROM (approved_at - created_at))/3600) AS avg_hours
FROM purch_requests
WHERE approved_at IS NOT NULL;

-- Доля возвратов
CREATE OR REPLACE VIEW v_purch_return_rate AS
SELECT count(*) FILTER (WHERE status_code='returned')::decimal / count(*) AS return_ratio
FROM purch_requests;

-- Сводка по департаментам
CREATE OR REPLACE VIEW v_purch_requests_summary AS
SELECT department, status_code, count(*) AS cnt
FROM purch_requests
GROUP BY department, status_code;

-- Суммы заявок (оценка)
CREATE OR REPLACE VIEW v_purch_request_costs AS
SELECT
    r.request_id,
    sum(COALESCE(i.est_unit_price,0) * i.quantity) AS est_amount,
    max(i.currency) AS currency
FROM purch_requests r
LEFT JOIN purch_request_items i ON i.request_id = r.request_id
GROUP BY r.request_id;

-- Суммы заказов (факт)
CREATE OR REPLACE VIEW v_purch_order_costs AS
SELECT
    o.order_id,
    o.request_id,
    o.amount AS order_amount
FROM purch_orders o;

-- Среднее кол-во итераций согласования
CREATE OR REPLACE VIEW v_purch_approval_iterations AS
WITH steps AS (
  SELECT request_id, count(*) AS transitions
  FROM purch_request_history
  GROUP BY request_id
)
SELECT avg(transitions)::numeric(10,2) AS avg_transitions_overall FROM steps;

-- ------------------------------------------------
-- 10) Фиксация миграции
-- ------------------------------------------------
INSERT INTO schema_migrations(version, description)
SELECT 'v9_procurement',
       'Закупки: заявки, позиции, статусы, история, комментарии, документы с ролями, заказы, интеграция с 1С (staging), AI-подсказки, ТТК, суммы, аналитические VIEW.'
WHERE NOT EXISTS (SELECT 1 FROM schema_migrations WHERE version = 'v9_procurement');

COMMIT;


