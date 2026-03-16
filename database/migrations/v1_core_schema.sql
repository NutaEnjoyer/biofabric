BEGIN;

-- 0) schema_migrations
CREATE TABLE IF NOT EXISTS schema_migrations (
    version      TEXT PRIMARY KEY,
    description  TEXT NOT NULL,
    applied_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
COMMENT ON TABLE schema_migrations IS 'Журнал применённых миграций схемы БД.';
COMMENT ON COLUMN schema_migrations.version     IS 'Уникальный идентификатор версии миграции.';
COMMENT ON COLUMN schema_migrations.description IS 'Краткое описание миграции.';
COMMENT ON COLUMN schema_migrations.applied_at  IS 'Метка времени применения.';

-- 1) users & roles
CREATE TABLE IF NOT EXISTS app_users (
    user_id     BIGSERIAL PRIMARY KEY,
    full_name   TEXT        NOT NULL,
    email       TEXT UNIQUE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
COMMENT ON TABLE app_users IS 'Пользователи экосистемы.';
COMMENT ON COLUMN app_users.full_name  IS 'ФИО пользователя.';
COMMENT ON COLUMN app_users.email      IS 'Уникальный e-mail, если используется.';
COMMENT ON COLUMN app_users.created_at IS 'Дата/время создания записи.';

CREATE TABLE IF NOT EXISTS roles (
    role_id     BIGSERIAL PRIMARY KEY,
    role_code   TEXT NOT NULL UNIQUE,
    name        TEXT NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
COMMENT ON TABLE roles IS 'Справочник ролей доступа.';
COMMENT ON COLUMN roles.role_code IS 'Код роли (машиночитаемый).';
COMMENT ON COLUMN roles.name     IS 'Человеко-читаемое имя роли.';

CREATE TABLE IF NOT EXISTS user_roles (
    user_id  BIGINT NOT NULL REFERENCES app_users(user_id) ON DELETE CASCADE,
    role_id  BIGINT NOT NULL REFERENCES roles(role_id)     ON DELETE CASCADE,
    PRIMARY KEY (user_id, role_id)
);
COMMENT ON TABLE user_roles IS 'Многие-ко-многим: пользователи ↔ роли.';

-- 2) units & conversions
CREATE TABLE IF NOT EXISTS units (
    unit_id    BIGSERIAL PRIMARY KEY,
    name       TEXT NOT NULL,
    symbol     TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (name, symbol)
);
COMMENT ON TABLE units IS 'Единицы измерения.';
COMMENT ON COLUMN units.name   IS 'Полное наименование единицы.';
COMMENT ON COLUMN units.symbol IS 'Символ/краткое обозначение.';

CREATE TABLE IF NOT EXISTS unit_conversions (
    conversion_id BIGSERIAL PRIMARY KEY,
    from_unit_id  BIGINT NOT NULL REFERENCES units(unit_id),
    to_unit_id    BIGINT NOT NULL REFERENCES units(unit_id),
    formula       TEXT   NOT NULL,
    UNIQUE (from_unit_id, to_unit_id),
    CHECK (from_unit_id <> to_unit_id)
);
COMMENT ON TABLE unit_conversions IS 'Правила преобразования единиц.';
COMMENT ON COLUMN unit_conversions.formula IS 'Формула конвертации; x — исходное значение.';

-- 3) data types (meta)
CREATE TABLE IF NOT EXISTS data_types (
    type_id     BIGSERIAL PRIMARY KEY,
    name        TEXT NOT NULL UNIQUE,
    description TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
COMMENT ON TABLE data_types IS 'Типы данных (что измеряем/храним).';
COMMENT ON COLUMN data_types.name IS 'Уникальное наименование типа данных.';

-- где/в каком контексте используется тип
CREATE TABLE IF NOT EXISTS type_contexts (
    type_context_id BIGSERIAL PRIMARY KEY,
    type_id         BIGINT NOT NULL REFERENCES data_types(type_id) ON DELETE CASCADE,
    location        TEXT,
    equipment       TEXT,
    frequency_sec   INTEGER,
    UNIQUE (type_id, location, equipment)
);
COMMENT ON TABLE type_contexts IS 'Контексты применения типа данных: локация/оборудование/частота.';

-- валидация
CREATE TABLE IF NOT EXISTS type_validation_rules (
    validation_id BIGSERIAL PRIMARY KEY,
    type_id       BIGINT NOT NULL REFERENCES data_types(type_id) ON DELETE CASCADE,
    min_value     DOUBLE PRECISION,
    max_value     DOUBLE PRECISION,
    regex_pattern TEXT,
    custom_fn     TEXT
);
COMMENT ON TABLE type_validation_rules IS 'Правила валидации для типов данных.';

-- расчётные правила
CREATE TABLE IF NOT EXISTS type_calculation_rules (
    calc_id      BIGSERIAL PRIMARY KEY,
    type_id      BIGINT NOT NULL REFERENCES data_types(type_id) ON DELETE CASCADE,
    formula      TEXT   NOT NULL,
    dependencies JSONB
);
COMMENT ON TABLE type_calculation_rules IS 'Расчётные формулы для типов данных.';

-- политики агрегирования
CREATE TABLE IF NOT EXISTS type_aggregate_policies (
    aggregate_id BIGSERIAL PRIMARY KEY,
    type_id      BIGINT NOT NULL REFERENCES data_types(type_id) ON DELETE CASCADE,
    method       TEXT   NOT NULL CHECK (method IN ('sum','avg','min','max','count')),
    interval     TEXT   NOT NULL
);
COMMENT ON TABLE type_aggregate_policies IS 'Политики агрегирования ряда значений для типа.';

-- retention (общие)
CREATE TABLE IF NOT EXISTS retention_policies (
    retention_policy_id BIGSERIAL PRIMARY KEY,
    name             TEXT     NOT NULL UNIQUE,
    retention_period INTERVAL NOT NULL,
    deletion_method  TEXT     NOT NULL CHECK (deletion_method IN ('soft_delete','hard_delete','archive')),
    description      TEXT
);
COMMENT ON TABLE retention_policies IS 'Политики хранения данных.';

CREATE TABLE IF NOT EXISTS type_retention (
    type_id             BIGINT NOT NULL REFERENCES data_types(type_id) ON DELETE CASCADE,
    retention_policy_id BIGINT NOT NULL REFERENCES retention_policies(retention_policy_id),
    PRIMARY KEY (type_id, retention_policy_id)
);
COMMENT ON TABLE type_retention IS 'Назначение политики хранения на тип данных.';

-- теги типов
CREATE TABLE IF NOT EXISTS type_tags (
    tag_id   BIGSERIAL PRIMARY KEY,
    type_id  BIGINT NOT NULL REFERENCES data_types(type_id) ON DELETE CASCADE,
    tag_name TEXT   NOT NULL,
    color    TEXT,
    UNIQUE (type_id, tag_name)
);
COMMENT ON TABLE type_tags IS 'Классификация типов данных (теги).';

-- источники типа
CREATE TABLE IF NOT EXISTS type_sources (
    source_id     BIGSERIAL PRIMARY KEY,
    type_id       BIGINT NOT NULL REFERENCES data_types(type_id) ON DELETE CASCADE,
    system_name   TEXT   NOT NULL,
    data_point_id TEXT
);
COMMENT ON TABLE type_sources IS 'Источники поступления данных для типа.';

-- связи типов
CREATE TABLE IF NOT EXISTS type_links (
    link_id         BIGSERIAL PRIMARY KEY,
    parent_type_id  BIGINT NOT NULL REFERENCES data_types(type_id) ON DELETE CASCADE,
    child_type_id   BIGINT NOT NULL REFERENCES data_types(type_id) ON DELETE CASCADE,
    link_type       TEXT   NOT NULL,
    CHECK (parent_type_id <> child_type_id)
);
COMMENT ON TABLE type_links IS 'Граф зависимостей между типами данных.';

-- доступ к типу (RBAC)
CREATE TABLE IF NOT EXISTS type_access_policies (
    policy_id  BIGSERIAL PRIMARY KEY,
    type_id    BIGINT NOT NULL REFERENCES data_types(type_id) ON DELETE CASCADE,
    role_id    BIGINT NOT NULL REFERENCES roles(role_id)      ON DELETE CASCADE,
    permission TEXT   NOT NULL CHECK (permission IN ('read','write','manage','owner')),
    UNIQUE (type_id, role_id)
);
COMMENT ON TABLE type_access_policies IS 'Права ролей на тип данных.';

-- 4) records (факты)
CREATE TABLE IF NOT EXISTS data_records (
    record_id  BIGSERIAL PRIMARY KEY,
    type_id    BIGINT      NOT NULL REFERENCES data_types(type_id) ON DELETE CASCADE,
    ts         TIMESTAMPTZ NOT NULL,
    num_val    DOUBLE PRECISION,
    text_val   TEXT,
    json_val   JSONB,
    unit_id    BIGINT REFERENCES units(unit_id),
    CHECK (num_val IS NOT NULL OR text_val IS NOT NULL OR json_val IS NOT NULL)
);
COMMENT ON TABLE data_records IS 'Конкретные значения по типам данных.';
COMMENT ON COLUMN data_records.ts IS 'Временная метка значения.';

CREATE INDEX IF NOT EXISTS idx_records_type_ts ON data_records(type_id, ts DESC);
CREATE INDEX IF NOT EXISTS idx_records_ts       ON data_records(ts DESC);

CREATE TABLE IF NOT EXISTS record_contexts (
    record_context_id BIGSERIAL PRIMARY KEY,
    record_id         BIGINT NOT NULL REFERENCES data_records(record_id) ON DELETE CASCADE,
    location          TEXT,
    user_id           BIGINT REFERENCES app_users(user_id),
    device            TEXT
);
COMMENT ON TABLE record_contexts IS 'Контекст появления записи: локация, пользователь, устройство.';

CREATE TABLE IF NOT EXISTS record_subvalues (
    subvalue_id BIGSERIAL PRIMARY KEY,
    record_id   BIGINT NOT NULL REFERENCES data_records(record_id) ON DELETE CASCADE,
    component   TEXT   NOT NULL,
    num_val     DOUBLE PRECISION,
    text_val    TEXT,
    json_val    JSONB
);
COMMENT ON TABLE record_subvalues IS 'Составные (вложенные) значения записи.';

CREATE TABLE IF NOT EXISTS record_origins (
    origin_id   BIGSERIAL PRIMARY KEY,
    record_id   BIGINT NOT NULL REFERENCES data_records(record_id) ON DELETE CASCADE,
    source_type TEXT   NOT NULL,
    source_info TEXT
);
COMMENT ON TABLE record_origins IS 'Происхождение значения (тип источника, детали).';

CREATE TABLE IF NOT EXISTS record_change_log (
    change_id    BIGSERIAL PRIMARY KEY,
    record_id    BIGINT NOT NULL REFERENCES data_records(record_id) ON DELETE CASCADE,
    old_val      JSONB,
    new_val      JSONB,
    modified_by  BIGINT REFERENCES app_users(user_id),
    modified_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
COMMENT ON TABLE record_change_log IS 'Журнал правок значений (до/после).';

CREATE TABLE IF NOT EXISTS record_access_log (
    access_id   BIGSERIAL PRIMARY KEY,
    record_id   BIGINT NOT NULL REFERENCES data_records(record_id) ON DELETE CASCADE,
    user_id     BIGINT REFERENCES app_users(user_id),
    action      TEXT   NOT NULL,
    accessed_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
COMMENT ON TABLE record_access_log IS 'Журнал обращений к значениям (аудит чтения/экспорта).';

CREATE TABLE IF NOT EXISTS record_retention (
    record_id           BIGINT PRIMARY KEY REFERENCES data_records(record_id) ON DELETE CASCADE,
    retention_policy_id BIGINT NOT NULL REFERENCES retention_policies(retention_policy_id)
);
COMMENT ON TABLE record_retention IS 'Индивидуальная политика хранения для записи.';

CREATE TABLE IF NOT EXISTS record_type_links (
    link_id         BIGSERIAL PRIMARY KEY,
    record_id       BIGINT NOT NULL REFERENCES data_records(record_id) ON DELETE CASCADE,
    related_type_id BIGINT NOT NULL REFERENCES data_types(type_id) ON DELETE CASCADE,
    link_type       TEXT   NOT NULL
);
COMMENT ON TABLE record_type_links IS 'Привязка записи к семантике связей типов.';

-- 5) alerts/notifications
CREATE TABLE IF NOT EXISTS alert_rules (
    rule_id     BIGSERIAL PRIMARY KEY,
    type_id     BIGINT NOT NULL REFERENCES data_types(type_id) ON DELETE CASCADE,
    condition   TEXT   NOT NULL,
    priority    SMALLINT NOT NULL CHECK (priority BETWEEN 1 AND 5),
    message_tpl TEXT   NOT NULL
);
COMMENT ON TABLE alert_rules IS 'Правила срабатывания оповещений на уровне типа.';

CREATE TABLE IF NOT EXISTS alert_rule_actions (
    action_id   BIGSERIAL PRIMARY KEY,
    rule_id     BIGINT NOT NULL REFERENCES alert_rules(rule_id) ON DELETE CASCADE,
    action_type TEXT  NOT NULL,
    parameters  JSONB
);
COMMENT ON TABLE alert_rule_actions IS 'Действия, выполняемые при срабатывании правила.';

CREATE TABLE IF NOT EXISTS alert_events (
    event_id     BIGSERIAL PRIMARY KEY,
    rule_id      BIGINT NOT NULL REFERENCES alert_rules(rule_id) ON DELETE CASCADE,
    record_id    BIGINT     REFERENCES data_records(record_id) ON DELETE SET NULL,
    triggered_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    payload      JSONB
);
COMMENT ON TABLE alert_events IS 'Факты срабатывания правил (привязка к записи).';

CREATE TABLE IF NOT EXISTS notification_channels (
    channel_id  BIGSERIAL PRIMARY KEY,
    kind        TEXT NOT NULL CHECK (kind IN ('email','messenger','sms','ui')),
    destination TEXT NOT NULL
);
COMMENT ON TABLE notification_channels IS 'Каналы уведомлений (тип и адрес назначения).';

CREATE TABLE IF NOT EXISTS alert_rule_channels (
    arc_id     BIGSERIAL PRIMARY KEY,
    rule_id    BIGINT NOT NULL REFERENCES alert_rules(rule_id) ON DELETE CASCADE,
    channel_id BIGINT NOT NULL REFERENCES notification_channels(channel_id) ON DELETE CASCADE,
    UNIQUE (rule_id, channel_id)
);
COMMENT ON TABLE alert_rule_channels IS 'Назначение каналов уведомлений правилам оповещения.';

CREATE TABLE IF NOT EXISTS notifications_outbox (
    outbox_id  BIGSERIAL PRIMARY KEY,
    event_id   BIGINT NOT NULL REFERENCES alert_events(event_id) ON DELETE CASCADE,
    channel_id BIGINT NOT NULL REFERENCES notification_channels(channel_id),
    status     TEXT   NOT NULL CHECK (status IN ('pending','sent','failed')),
    last_error TEXT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
COMMENT ON TABLE notifications_outbox IS 'Журнал отправки уведомлений (outbox-паттерн).';

-- 6) seeds
INSERT INTO roles(role_code, name)
SELECT v.role_code, v.name
FROM (VALUES
   ('admin','Администратор'),
   ('editor','Редактор'),
   ('viewer','Наблюдатель')
) AS v(role_code, name)
LEFT JOIN roles r ON r.role_code = v.role_code
WHERE r.role_code IS NULL;

INSERT INTO units(name, symbol)
SELECT v.name, v.symbol
FROM (VALUES
   ('градус Цельсия','°C'),
   ('проценты','%'),
   ('штука','шт')
) AS v(name, symbol)
LEFT JOIN units u ON u.name = v.name AND u.symbol = v.symbol
WHERE u.unit_id IS NULL;

INSERT INTO notification_channels(kind, destination)
SELECT v.kind, v.destination
FROM (VALUES
   ('email','ook@company.local')
) AS v(kind, destination)
LEFT JOIN notification_channels c ON c.kind = v.kind AND c.destination = v.destination
WHERE c.channel_id IS NULL;

INSERT INTO schema_migrations(version, description)
SELECT 'v1_core_schema', 'Базовая схема: пользователи/роли, единицы/конверсии, типы/записи, политики хранения, оповещения.'
WHERE NOT EXISTS (SELECT 1 FROM schema_migrations WHERE version = 'v1_core_schema');

COMMIT;

