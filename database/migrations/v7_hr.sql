--  ERP-Биофабрика — HR-модуль
--  Файл: v7_hr.sql
--  База: PostgreSQL 13+
--  Требует: v1_core_schema.sql (ядро), v2_ook_docflow.sql (ООК)
--  Назначение: вакансии (hh), кандидаты, отклики, ИИ-оценки, опросники,
--              интервью, история взаимодействий, экспорт в 1С.
--  Lean: резюме-файлы не храним; только структурированный JSON из источников.
--  Идемпотентность: да


BEGIN;

-- ------------------------------------------------
-- 0) Справочники/статусы
-- ------------------------------------------------
CREATE TABLE IF NOT EXISTS hr_candidate_statuses (
    status_code  TEXT PRIMARY KEY,            -- 'new','ai_scored','pending_hr','hr_confirmed','hired','archived'
    display_name TEXT NOT NULL
);
COMMENT ON TABLE hr_candidate_statuses IS 'Статусы кандидатов по процессу подбора.';

INSERT INTO hr_candidate_statuses(status_code, display_name)
SELECT v.status_code, v.display_name
FROM (VALUES
  ('new','Новый — получен отклик'),
  ('ai_scored','Оценён ИИ'),
  ('pending_hr','В ожидании решения (HR)'),
  ('hr_confirmed','Подтверждён HR — рекомендован к собеседованию'),
  ('hired','Принят — оформлен'),
  ('archived','Архив — не прошёл/отказался/закрыт')
) AS v(status_code, display_name)
LEFT JOIN hr_candidate_statuses s ON s.status_code = v.status_code
WHERE s.status_code IS NULL;

-- ------------------------------------------------
-- 1) Вакансии и кандидаты
-- ------------------------------------------------
CREATE TABLE IF NOT EXISTS hr_vacancies (
    vacancy_id   BIGSERIAL PRIMARY KEY,
    src          TEXT NOT NULL DEFAULT 'hh',  -- источник ('hh','manual', ...)
    external_id  TEXT,                        -- ID в hh
    title        TEXT NOT NULL,
    department   TEXT,
    description  TEXT,
    requirements TEXT,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (src, external_id)
);
COMMENT ON TABLE hr_vacancies IS 'Вакансии (импорт из hh или заведены вручную).';

CREATE TABLE IF NOT EXISTS hr_candidates (
    candidate_id BIGSERIAL PRIMARY KEY,
    full_name    TEXT NOT NULL,
    email        TEXT,                        -- используем как уникальный идентификатор (если есть)
    phone        TEXT,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (email)
);
COMMENT ON TABLE hr_candidates IS 'Кандидаты (без хранения файлов резюме). Уникальность по email.';

-- Подозрительные дубли: одно ФИО и совпадающий email/телефон у разных id
CREATE OR REPLACE VIEW v_hr_possible_duplicates AS
SELECT c1.candidate_id AS id1, c2.candidate_id AS id2, c1.full_name, c1.email, c1.phone
FROM hr_candidates c1
JOIN hr_candidates c2
  ON c1.candidate_id < c2.candidate_id
 AND (lower(coalesce(c1.email,'')) <> '' AND lower(c1.email) = lower(c2.email)
      OR (c1.phone IS NOT NULL AND c1.phone <> '' AND c1.phone = c2.phone))
 AND lower(c1.full_name) = lower(c2.full_name);

-- ------------------------------------------------
-- 2) Отклики/заявки кандидатов на вакансии
-- ------------------------------------------------
CREATE TABLE IF NOT EXISTS hr_applications (
    application_id BIGSERIAL PRIMARY KEY,
    vacancy_id     BIGINT NOT NULL REFERENCES hr_vacancies(vacancy_id) ON DELETE CASCADE,
    candidate_id   BIGINT NOT NULL REFERENCES hr_candidates(candidate_id) ON DELETE CASCADE,
    status_code    TEXT   NOT NULL REFERENCES hr_candidate_statuses(status_code),
    source         TEXT   NOT NULL DEFAULT 'hh',       -- источник отклика ('hh','manual')
    external_id    TEXT,                               -- id отклика в hh
    applied_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (vacancy_id, candidate_id)
);
COMMENT ON TABLE hr_applications IS 'Отклики/заявки кандидатов на конкретные вакансии (статусы по процессу).';

CREATE INDEX IF NOT EXISTS idx_hr_applications_vacancy   ON hr_applications(vacancy_id);
CREATE INDEX IF NOT EXISTS idx_hr_applications_status    ON hr_applications(status_code);
CREATE INDEX IF NOT EXISTS idx_hr_applications_candidate ON hr_applications(candidate_id);

-- ------------------------------------------------
-- 3) Резюме (парсинг) и ИИ-оценки
-- ------------------------------------------------
CREATE TABLE IF NOT EXISTS hr_resume_parsed (
    resume_id     BIGSERIAL PRIMARY KEY,
    candidate_id  BIGINT NOT NULL REFERENCES hr_candidates(candidate_id) ON DELETE CASCADE,
    source        TEXT   NOT NULL DEFAULT 'hh',        -- 'hh','manual'
    external_id   TEXT,                                -- id резюме в источнике
    resume_json   JSONB NOT NULL,                      -- структурированный разбор резюме (lean)
    received_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
COMMENT ON TABLE hr_resume_parsed IS 'Структурированный разбор резюме (JSONB), без хранения файлов.';

CREATE INDEX IF NOT EXISTS idx_hr_resume_candidate ON hr_resume_parsed(candidate_id);

CREATE TABLE IF NOT EXISTS hr_ai_assessments (
    assessment_id     BIGSERIAL PRIMARY KEY,
    candidate_id      BIGINT REFERENCES hr_candidates(candidate_id) ON DELETE CASCADE,
    application_id    BIGINT REFERENCES hr_applications(application_id) ON DELETE CASCADE,
    survey_instance_id BIGINT,                            -- ссылка на прохождение опроса (см. ниже)
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    summary           TEXT,                               -- краткий вывод
    competencies      JSONB,                              -- оценка по компетенциям
    risks             JSONB,                              -- выявленные риски
    recommendations   JSONB,                              -- рекомендации
    score             NUMERIC(5,2)                        -- итоговый балл/рейтинг (0..100, например)
);
COMMENT ON TABLE hr_ai_assessments IS 'Результаты ИИ-анализа кандидата: summary, компетенции, риски, рекомендации, балл.';

CREATE INDEX IF NOT EXISTS idx_hr_ai_assessments_candidate  ON hr_ai_assessments(candidate_id);
CREATE INDEX IF NOT EXISTS idx_hr_ai_assessments_application ON hr_ai_assessments(application_id);

-- ------------------------------------------------
-- 4) Опросы/анкеты: шаблоны, вопросы, инстансы и ответы
-- ------------------------------------------------
CREATE TABLE IF NOT EXISTS hr_surveys (
    survey_id   BIGSERIAL PRIMARY KEY,
    name        TEXT NOT NULL,
    description TEXT
);
COMMENT ON TABLE hr_surveys IS 'Шаблоны опросов (анкеты) для вакансий.';

CREATE TABLE IF NOT EXISTS hr_survey_questions (
    question_id BIGSERIAL PRIMARY KEY,
    survey_id   BIGINT NOT NULL REFERENCES hr_surveys(survey_id) ON DELETE CASCADE,
    ord         INT NOT NULL,
    kind        TEXT NOT NULL DEFAULT 'text',           -- 'text','choice','scale','code','file' (файл не храним)
    text        TEXT NOT NULL,
    required    BOOLEAN NOT NULL DEFAULT TRUE
);
COMMENT ON TABLE hr_survey_questions IS 'Вопросы опроса: порядок, тип, обязательность.';

CREATE UNIQUE INDEX IF NOT EXISTS ux_hr_survey_questions ON hr_survey_questions(survey_id, ord);

-- Привязка шаблона опроса к вакансии (версионируем через created_at)
CREATE TABLE IF NOT EXISTS hr_vacancy_surveys (
    vacancy_survey_id BIGSERIAL PRIMARY KEY,
    vacancy_id        BIGINT NOT NULL REFERENCES hr_vacancies(vacancy_id) ON DELETE CASCADE,
    survey_id         BIGINT NOT NULL REFERENCES hr_surveys(survey_id),
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);
COMMENT ON TABLE hr_vacancy_surveys IS 'Какие опросы используются по конкретной вакансии (история версий).';

-- Инстанс опроса для конкретного кандидата
CREATE TABLE IF NOT EXISTS hr_survey_instances (
    survey_instance_id BIGSERIAL PRIMARY KEY,
    vacancy_id         BIGINT NOT NULL REFERENCES hr_vacancies(vacancy_id) ON DELETE CASCADE,
    candidate_id       BIGINT NOT NULL REFERENCES hr_candidates(candidate_id) ON DELETE CASCADE,
    survey_id          BIGINT NOT NULL REFERENCES hr_surveys(survey_id),
    started_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    submitted_at       TIMESTAMPTZ,
    UNIQUE (vacancy_id, candidate_id, survey_id)
);
COMMENT ON TABLE hr_survey_instances IS 'Прохождение опроса кандидатом под вакансию.';

CREATE INDEX IF NOT EXISTS idx_hr_survey_instances_vac_cand ON hr_survey_instances(vacancy_id, candidate_id);

-- Ответы кандидата
CREATE TABLE IF NOT EXISTS hr_answers (
    answer_id          BIGSERIAL PRIMARY KEY,
    survey_instance_id BIGINT NOT NULL REFERENCES hr_survey_instances(survey_instance_id) ON DELETE CASCADE,
    question_id        BIGINT NOT NULL REFERENCES hr_survey_questions(question_id),
    answer_text        TEXT,
    answer_json        JSONB,                              -- для сложных типов/множественного выбора
    answered_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (survey_instance_id, question_id)
);
COMMENT ON TABLE hr_answers IS 'Ответы кандидата на вопросы опроса (текст/JSON).';

-- ------------------------------------------------
-- 5) Интервью (по желанию HR — без опроса или после)
-- ------------------------------------------------
CREATE TABLE IF NOT EXISTS hr_interviews (
    interview_id        BIGSERIAL PRIMARY KEY,
    application_id      BIGINT NOT NULL REFERENCES hr_applications(application_id) ON DELETE CASCADE,
    scheduled_at        TIMESTAMPTZ,
    interviewer_user_id BIGINT REFERENCES app_users(user_id),
    outcome             TEXT,                              -- результат/статус интервью
    notes               TEXT
);
COMMENT ON TABLE hr_interviews IS 'Очные/онлайн собеседования по заявке кандидата.';

CREATE INDEX IF NOT EXISTS idx_hr_interviews_application ON hr_interviews(application_id);

CREATE TABLE IF NOT EXISTS hr_interview_questions (
    interview_question_id BIGSERIAL PRIMARY KEY,
    interview_id          BIGINT NOT NULL REFERENCES hr_interviews(interview_id) ON DELETE CASCADE,
    ord                   INT NOT NULL,
    text                  TEXT NOT NULL,
    generated_by          TEXT NOT NULL DEFAULT 'ai'       -- 'ai' / 'manual'
);
COMMENT ON TABLE hr_interview_questions IS 'Индивидуальные вопросы к интервью (может генерировать ИИ).';

CREATE UNIQUE INDEX IF NOT EXISTS ux_hr_interview_questions ON hr_interview_questions(interview_id, ord);

-- ------------------------------------------------
-- 6) История взаимодействий (таймлайн)
-- ------------------------------------------------
CREATE TABLE IF NOT EXISTS hr_timeline_events (
    event_id       BIGSERIAL PRIMARY KEY,
    candidate_id   BIGINT NOT NULL REFERENCES hr_candidates(candidate_id) ON DELETE CASCADE,
    application_id BIGINT REFERENCES hr_applications(application_id) ON DELETE CASCADE,
    occurred_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    kind           TEXT NOT NULL,                           -- 'resume_received','ai_scored','survey_sent','survey_submitted','interview_scheduled','status_changed','note','exported_1c'
    payload        JSONB
);
COMMENT ON TABLE hr_timeline_events IS 'Лента событий по кандидату/заявке (вся история взаимодействий).';

CREATE INDEX IF NOT EXISTS idx_hr_timeline_candidate ON hr_timeline_events(candidate_id);
CREATE INDEX IF NOT EXISTS idx_hr_timeline_kind      ON hr_timeline_events(kind);

-- ------------------------------------------------
-- 7) Экспорт в 1С при найме (очередь/лог)
-- ------------------------------------------------
CREATE TABLE IF NOT EXISTS hr_export_1c_queue (
    queue_id       BIGSERIAL PRIMARY KEY,
    application_id BIGINT NOT NULL REFERENCES hr_applications(application_id) ON DELETE CASCADE,
    payload        JSONB,                                   -- пакет для 1С (lean)
    status         TEXT NOT NULL DEFAULT 'pending',         -- 'pending','sent','error','ack'
    last_error     TEXT,
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);
COMMENT ON TABLE hr_export_1c_queue IS 'Очередь экспорта данных принятого кандидата в 1С.';

CREATE INDEX IF NOT EXISTS idx_hr_export1c_status ON hr_export_1c_queue(status, updated_at DESC);

CREATE TABLE IF NOT EXISTS hr_export_1c_log (
    log_id      BIGSERIAL PRIMARY KEY,
    queue_id    BIGINT NOT NULL REFERENCES hr_export_1c_queue(queue_id) ON DELETE CASCADE,
    ts          TIMESTAMPTZ NOT NULL DEFAULT now(),
    direction   TEXT NOT NULL,                            -- 'request','response'
    payload     JSONB,
    http_status INT,
    error       TEXT
);
COMMENT ON TABLE hr_export_1c_log IS 'Журнал обмена с 1С по экспорту принятых кандидатов.';

-- ------------------------------------------------
-- 8) Вьюхи для контроля/аналитики
-- ------------------------------------------------
-- Кандидаты с ИИ-оценкой, ожидающие решения HR
CREATE OR REPLACE VIEW v_hr_ai_ready AS
SELECT a.application_id, a.vacancy_id, a.candidate_id, max(x.created_at) AS last_assessed_at
FROM hr_applications a
JOIN hr_ai_assessments x ON x.application_id = a.application_id
WHERE a.status_code = 'ai_scored'
GROUP BY a.application_id, a.vacancy_id, a.candidate_id;

-- Кандидаты без опроса под вакансию (если опрос требуется)
CREATE OR REPLACE VIEW v_hr_without_survey AS
SELECT a.application_id, a.vacancy_id, a.candidate_id
FROM hr_applications a
LEFT JOIN LATERAL (
    SELECT 1 FROM hr_survey_instances si
    WHERE si.vacancy_id = a.vacancy_id AND si.candidate_id = a.candidate_id
    LIMIT 1
) s ON TRUE
WHERE s IS NULL;

-- Сводка по вакансии: число откликов и средний балл ИИ
CREATE OR REPLACE VIEW v_hr_vacancy_stats AS
SELECT v.vacancy_id,
       count(a.application_id) AS applications,
       avg(x.score) AS avg_score
FROM hr_vacancies v
LEFT JOIN hr_applications a ON a.vacancy_id = v.vacancy_id
LEFT JOIN LATERAL (
    SELECT score FROM hr_ai_assessments x
    WHERE x.application_id = a.application_id
    ORDER BY x.created_at DESC LIMIT 1
) x ON TRUE
GROUP BY v.vacancy_id;

-- Рейтинг кандидатов под вакансию (по последнему ИИ-баллу)
CREATE OR REPLACE VIEW v_hr_vacancy_ranking AS
WITH last_assessment AS (
    SELECT
        a.application_id,
        a.vacancy_id,
        a.candidate_id,
        (
            SELECT x.score
            FROM hr_ai_assessments x
            WHERE x.application_id = a.application_id
            ORDER BY x.created_at DESC
            LIMIT 1
        ) AS last_score,
        (
            SELECT x.created_at
            FROM hr_ai_assessments x
            WHERE x.application_id = a.application_id
            ORDER BY x.created_at DESC
            LIMIT 1
        ) AS assessed_at
    FROM hr_applications a
),
scored AS (
    SELECT
        vacancy_id,
        candidate_id,
        application_id,
        last_score,
        assessed_at,
        CASE
            WHEN last_score IS NULL                          THEN 'no_score'
            WHEN last_score >= 80                            THEN 'strong_fit'
            WHEN last_score >= 60 AND last_score < 80        THEN 'medium_fit'
            ELSE 'low_fit'
        END AS fit_band
    FROM last_assessment
)
SELECT
    s.vacancy_id,
    s.candidate_id,
    s.application_id,
    s.last_score,
    s.assessed_at,
    s.fit_band,
    RANK()       OVER (PARTITION BY s.vacancy_id ORDER BY s.last_score DESC NULLS LAST)  AS rank_in_vacancy,
    DENSE_RANK() OVER (PARTITION BY s.vacancy_id ORDER BY s.last_score DESC NULLS LAST)  AS dense_rank_in_vacancy
FROM scored s;

-- ------------------------------------------------
-- 9) Импорт из hh: стейджинг
-- ------------------------------------------------
CREATE TABLE IF NOT EXISTS hr_hh_import_jobs (
    job_id     BIGSERIAL PRIMARY KEY,
    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at TIMESTAMPTZ,
    kind       TEXT NOT NULL,                               -- 'vacancies','responses','resumes'
    status     TEXT NOT NULL DEFAULT 'pending',             -- 'pending','running','done','failed'
    error      TEXT
);
COMMENT ON TABLE hr_hh_import_jobs IS 'Задачи импорта с hh.ru (вакансии, отклики, резюме).';

CREATE TABLE IF NOT EXISTS hr_hh_import_items (
    item_id     BIGSERIAL PRIMARY KEY,
    job_id      BIGINT NOT NULL REFERENCES hr_hh_import_jobs(job_id) ON DELETE CASCADE,
    external_id TEXT,
    payload     JSONB,                                      -- сырой объект из API hh
    mapped_to   JSONB,                                      -- нормализованный вид
    status      TEXT NOT NULL DEFAULT 'new',                -- 'new','mapped','conflict','error'
    error       TEXT
);
COMMENT ON TABLE hr_hh_import_items IS 'Строки импорта hh.ru (сырые данные, маппинг, статус).';

-- ------------------------------------------------
-- 10) Фиксация применения миграции
-- ------------------------------------------------
INSERT INTO schema_migrations(version, description)
SELECT 'v7_hr',
       'HR: вакансии/кандидаты/отклики (hh), парсинг резюме (JSON), ИИ-оценки, опросы/ответы, интервью, таймлайн, экспорт в 1С, рейтинг по score.'
WHERE NOT EXISTS (SELECT 1 FROM schema_migrations WHERE version = 'v7_hr');

COMMIT;






