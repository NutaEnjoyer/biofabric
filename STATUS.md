# Статус готовности сервисов BioFabric ERP

> Дата анализа: 2026-03-16
> Обновлено: 2026-03-31 (LLM OpenAI для Legal/Marketing, TG/VK через env, Core API реальные записи в БД, новый модуль OKS)
> Основание: анализ кода + ТЗ (new_tz.txt, PLAN.md, TRACEABILITY.md)

---

## 1. Legal Service (`legal_service_project`)

### ✅ Готово

| Функция                                                                    | Эндпоинт / файл                              |
|----------------------------------------------------------------------------|----------------------------------------------|
| Реестр договоров с индикаторами (source, guarantee, deviations, overdue)   | `GET /contracts`                             |
| Карточка договора с расширенными данными (риски, интеграция, ЕИС)          | `GET /contracts/{id}`                        |
| Пометка просроченных договоров                                             | `POST /contracts/mark-overdue`               |
| Реестр договоров без гарантии                                              | `GET /contracts/without-guarantee`           |
| KPI: доля договоров с активной гарантией                                   | `GET /kpi/guarantee-share`                   |
| Сводка рисков и отклонений (фильтр по severity)                            | `GET /kpi/issues`                            |
| Валидация сторон договора (customer, supplier)                             | `GET /contracts/{id}/validate-parties`       |
| Таймлайн: история изменений договора                                       | `GET /contracts/{id}/timeline`               |
| Синхронизация дедлайнов (performance_due, payment_due, end_date)           | `POST /contracts/{id}/sync-deadlines`        |
| ЕИС: постановка в очередь (eis_export_queue + job)                         | `POST /eis/enqueue`                          |
| Импорт из 1С: staging                                                      | `POST /import/1c/stage`                      |
| Импорт из 1С: upsert договора по contract_no                               | `POST /import/1c/upsert/{stage_id}`          |
| Исходящая отправка в 1С (идемпотентная, очередь)                           | `POST /contracts/{id}/send-to-1c`            |
| Три независимых статуса (бизнес / 1С / ЕИС)                                | модели БД                                    |
| ИИ-анализ: запуск и получение результата                                   | `POST/GET /contracts/{id}/ai-analysis`       |
| Уведомления через outbox (template_code, email/TG)                         | `POST /notifications/send`                   |
| Привязка договора к workflow согласования                                  | `POST /contracts/{id}/workflow/bind`         |
| Core API (межсервисные стабы: notify, workflow, audit, docs)               | `router_core.py`                             |

### ✅ Дополнительно реализовано (2026-03-16)

| Функция                                                              | Файл                                            |
|----------------------------------------------------------------------|-------------------------------------------------|
| RBAC: матрица прав (viewer / user / admin), `require()` dependency   | `legal/security/rbac.py`, `legal/api/deps.py`   |
| RBAC-проверки на всех эндпоинтах (view / edit / import / 1С / ЕИС)   | `legal/api/router_requests.py`                  |
| Аутентификация через заголовки X-User-Id / X-User-Roles              | `legal/api/deps.py → get_user()`                |
| Фронтенд: цветовые индикаторы в реестре, карточка договора           | `frontend/src/pages/Contracts.tsx`              |
| Фронтенд: скелетоны, toast, блоки ИИ/таймлайн/интеграция/дедлайны    | `frontend/src/pages/ContractDetail.tsx`         |

### ✅ Дополнительно реализовано (2026-03-29)

| Функция                                                              | Файл                                            |
|----------------------------------------------------------------------|------------------------------------------------|
| ИИ-анализ договора через OpenAI (заключение 3–5 предложений)         | `requests_repo.py`, `_llm_analysis_summary()`  |
| Fallback на структурный текст при недоступности OpenAI               | `requests_repo.py`, `_fallback_summary()`      |
| `OPENAI_API_KEY` / `OPENAI_MODEL` в конфиге и docker-compose         | `legal/config.py`, `docker-compose.yml`        |

### ✅ Дополнительно реализовано (2026-03-29, итерация 2)

| Функция                                                              | Файл                                            |
|----------------------------------------------------------------------|------------------------------------------------|
| `POST /notifications/send` → запись в `notifications_outbox`         | `legal/api/router_core.py`                      |
| `POST /workflow/advance` → обновление `workflow_instances` + history | `legal/api/router_core.py`                      |
| `POST /docs/bind` → запись в `document_bindings`                     | `legal/api/router_core.py`                      |
| `POST /audit/log` → запись в `audit_log`                             | `legal/api/router_core.py`                      |
| Fallback на logger при любой ошибке БД                               | `legal/api/router_core.py`                      |

### ❌ Не готово / Требует доработки

| Проблема | Комментарий                          |
|----------|--------------------------------------|
| Тесты    | Только `test_placeholder.py` — пусто |

---

## 2. Marketing Service (`marketing_service`)

### ✅ Готово

| Функция                                                                                     | Эндпоинт / файл                              |
|---------------------------------------------------------------------------------------------|----------------------------------------------|
| CRUD постов (create, read, update, list по периоду)                                         | `router_posts.py`                            |
| Workflow статусов: draft → in_review → approved → published → archived                      | `POST /posts/{id}/status/{status}`           |
| Назначение даты публикации                                                                  | `POST /posts/{id}/date`                      |
| Замена поста в плане (drag из корзины идей)                                                 | `POST /posts/replace`                        |
| Ручная публикация в TG/VK с сохранением URL                                                 | `POST /posts/{id}/publish`                   |
| Атрибут источника поста (manual / ai_generated / external_source / archive)                 | схемы + БД                                   |
| Поля audience, goals, tone, hashtags                                                        | `dto_posts.py` + репо                        |
| ИИ: генерация контент-плана по промту                                                       | `POST /ai/plan`                              |
| ИИ: идеи из источников                                                                      | `POST /ai/ideas`                             |
| ИИ: генерация текста поста                                                                  | `POST /posts/{id}/ai/generate-text`          |
| ИИ: рерайт поста под стиль                                                                  | `POST /posts/{id}/ai/rewrite`                |
| Задачи на генерацию контент-плана (plan_jobs)                                               | `POST/GET /plan-jobs`                        |
| Календарь (по периоду)                                                                      | `GET /calendar`                              |
| Корзина идей (посты без даты)                                                               | `GET /ideas`                                 |
| Источники контента (TG/URL/RSS) — CRUD                                                      | `router_sources.py`                          |
| Аналитика: сводка, рубрики, форматы, каналы, насыщенность, пробелы, предупреждения          | `router_analytics.py` (7 эндпоинтов)         |
| Уведомления N1–N4 (пробел в сетке, ИИ создал пост, приближается дата, пост утверждён)       | `notifier.py` + триггеры в роутерах          |
| RBAC: проверки прав create / update / publish / approve                                     | `can()` в роутерах                           |
| Привязка документов ООК к посту                                                             | `DocumentsService.bind()`                    |

### ❌ Не готово / Требует доработки

| Проблема                     | Комментарий                                                                  |
|------------------------------|------------------------------------------------------------------------------|
| Парсер внешних источников    | `POST /sources/fetch` возвращает `{}` — RSS/TG-скрейпер не реализован        |
| Smoke test                   | п.1.4 в PLAN.md — ждёт БД                                                    |
| Тесты                        | `test_smoke.py` — только заготовка                                           |

---

## 3. Quarantine Animals Service (`quarantine_animals_service`)

### ✅ Готово

| Функция                                                                                          | Эндпоинт / файл               |
|--------------------------------------------------------------------------------------------------|-------------------------------|
| Создание операций учёта: opening_balance, intake, withdrawal, issue_for_control, movement, adjustment | `POST /operations`        |
| Автоматическое создание пары записей для перемещения (movement_out + movement_in)                | `ops_service.py`              |
| Валидация quantity (> 0; для adjustment ≠ 0)                                                     | `dto_ops.py`                  |
| Проверка открытости периода (нельзя вводить за закрытые периоды)                                 | `ops_service.py`              |
| Подтверждение записи руководителем (draft → current)                                             | `PATCH /operations/{id}/confirm` |
| Справочники: виды, направления, возрастные категории, весовые категории, группы, когорты         | `router_refs.py`              |
| Импорт CSV с валидацией обязательных колонок                                                     | `POST /import`                |
| Экспорт CSV за период                                                                            | `GET /export/csv`             |
| Отчёт: ежемесячный свод (intake / withdrawal / movement / adjustment / closing_balance)          | `GET /reports/monthly-summary`|
| Панель сводки: поголовье, разбивка по направлениям, дельта к прошлому месяцу (↑↓)                | `GET /reports/dashboard`      |
| Динамика численности по месяцам (по видам / направлениям / total)                                | `GET /reports/dynamics`       |
| История операций (таймлайн) по виду и направлению                                                | `GET /reports/history`        |
| Виварий: группы как визуальные блоки с поголовьем                                                | `GET /reports/vivarium-groups`|
| Статусы записей: in_process / current / archived                                                 | модели БД                     |
| Поля: пол, возрастная/весовая категория, группа, когорта, назначение                             | `dto_ops.py`                  |

### ✅ Дополнительно реализовано (2026-03-16)

| Функция                                                                      | Файл                                                               |
|------------------------------------------------------------------------------|--------------------------------------------------------------------|
| Архивация записи: `current → archived`                                       | `PATCH /operations/{id}/archive`                                   |
| Массовая архивация месяца                                                    | `POST /operations/archive-month?period_month=...`                  |
| Создание когорты                                                             | `POST /cohorts`                                                    |
| Деактивация когорты                                                          | `PATCH /cohorts/{id}/deactivate`                                   |
| GET /cohorts: параметр show_inactive для просмотра всех когорт               | `router_refs.py`                                                   |
| Уведомления через Core Service: сохранение, перемещение, ошибка валидации    | `core_client/client.py`, `router_ops.py`, `router_import.py`       |
| Аудит подтверждения записи через Core                                        | `router_ops.py → confirm`                                          |

### ❌ Не готово / Требует доработки

| Проблема | Комментарий                        |
|----------|------------------------------------|
| Тесты    | `test_smoke.py` — только заготовка |

---

## 4. Procurement Service (`tz_procurement_proof`)

### ✅ Готово

| Функция                                                              | Эндпоинт / файл                                         |
|----------------------------------------------------------------------|---------------------------------------------------------|
| CRUD заявок с позициями (номенклатура, тех.задание, срок, количество)| `POST/GET /requests`                                    |
| Смена статуса заявки                                                 | `PATCH /requests/{id}/status`                           |
| Согласование (Директор, Юротдел → in_progress)                       | `POST /approvals`                                       |
| Коммерческие предложения поставщиков (КП)                            | `POST/GET /suppliers/quotes`                            |
| Документы по заявке                                                  | `POST/GET /documents`                                   |
| Входящий webhook от 1С (поступление товара → done)                   | `POST /integrations/1c/webhook/stock-received/{id}`     |
| Журнал событий (Event) для каждой заявки                             | `models.py`                                             |
| Фильтрация заявок по статусу                                         | `GET /requests?status=...`                              |
| Цветовая схема статусов (StatusEnum + STATUS_COLOR)                  | `models.py`                                             |

### ✅ Дополнительно реализовано (2026-03-16)

| Функция                                                                      | Файл                                              |
|------------------------------------------------------------------------------|---------------------------------------------------|
| Выбор победителя КП: `POST /suppliers/quotes/{id}/select`                    | `routers/suppliers.py`                            |
| Флаг `is_selected` на SupplierQuote, снятие с остальных КП                   | `models.py`, `schemas.py`                         |
| Исходящая интеграция 1С: `POST /integrations/1c/send/{id}` (idempotent)      | `routers/integrations.py`                         |
| Статус `onec_status` на заявке (not_sent / queued / sent / error)            | `models.py`, `schemas.py`                         |
| Отчёт по статусам: `GET /reports/summary`                                    | `routers/reports.py`                              |
| Экспорт заявок в CSV: `GET /reports/export/csv`                              | `routers/reports.py`                              |
| Уведомления через Core Service (httpx): создание заявки, смена статуса, согласование, 1С | `services/notifications.py`          |

### ✅ Дополнительно реализовано (2026-03-16, итерация 2)

| Функция                                                                        | Файл                          |
|--------------------------------------------------------------------------------|-------------------------------|
| RBAC через заголовки X-User-Id / X-User-Role, `CurrentUser.require_role()`     | `deps.py`                     |
| Роль-проверки на create/list/get/status заявок                                 | `routers/requests.py`         |
| Роль-проверки на согласование (Директор, Юротдел, Начальник ОЗ)                | `routers/approvals.py`        |
| Роль-проверки на документы                                                     | `routers/documents.py`        |
| Синхронизация пользователей: `POST /sync/users/upsert`                         | `routers/sync.py`             |
| Деактивация пользователя: `POST /sync/users/deactivate/{email}`                | `routers/sync.py`             |
| Просмотр локальной копии справочника: `GET /sync/users`                        | `routers/sync.py`             |
| Маппинг ролей Core → Procurement (8 ролей)                                     | `routers/sync.py → ROLE_MAP`  |
| Event nullable request_id для системных событий (sync, аудит)                  | `models.py`                   |

### ❌ Не готово / Требует доработки

| Проблема | Комментарий                                                               |
|----------|---------------------------------------------------------------------------|
| Тесты    | `test_flow_basic.py` — базовый flow-тест (единственный из всех сервисов)  |

---

## Сводная таблица

| Сервис          | Бизнес-логика    | ИИ / Интеграции                        | Уведомления        | RBAC                | Тесты       |
|-----------------|------------------|----------------------------------------|--------------------|---------------------|-------------|
| **Legal**       | ✅ Полная        | ✅ LLM (OpenAI + fallback)             | ✅ Outbox          | ✅ Реализован       | ❌ Пусто    |
| **Marketing**   | ⚠️ Парсер нет    | ✅ LLM (OpenAI + fallback), TG/VK      | ✅ N1–N4           | ✅ Проверки есть   | ❌ Заготовка|
| **Quarantine**  | ✅ Полная        | —                                      | ✅ Подключены      | ⚠️ Минимальный    | ❌ Заготовка |
| **Procurement** | ✅ Полная        | ✅ Вход + исходящая очередь            | ✅ Core Service    | ✅ Реализован     | ⚠️ Базовый  |
| **OKS**         | ✅ Полная        | —                                      | ✅ Правила в БД    | ✅ 4 роли           | ⚠️ Заготовка|

---

## 5. OKS Service (`oks_service`) — новый модуль

### ✅ Реализовано (2026-03-31)

| Функция                                                         | Эндпоинт / файл                              |
|-----------------------------------------------------------------|----------------------------------------------|
| CRUD объектов ОКС с иерархией (parent_object_id)                | `GET/POST /v1/oks/objects`                   |
| Карточка объекта + дочерние объекты + счётчики                  | `GET /v1/oks/objects/{id}`                   |
| Запрет удаления объекта с дочерними                             | `DELETE /v1/oks/objects/{id}` → 409          |
| CRUD этапов с признаком просрочки (is_overdue)                  | `GET/POST /v1/oks/objects/{id}/stages`       |
| Обновление и удаление этапов                                    | `PATCH/DELETE /v1/oks/stages/{id}`           |
| Документы: создание в documents + oks_documents (транзакция)    | `POST /v1/oks/objects/{id}/documents`        |
| Обновление статуса документа (draft/review/approved)            | `PATCH /v1/oks/documents/{id}`               |
| Комментарии к объектам и этапам                                 | `GET/POST /v1/oks/objects/{id}/comments`     |
| Сводная аналитика (статусы, просрочки, stale)                   | `GET /v1/oks/analytics/summary`              |
| Список просроченных этапов с кол-вом дней                       | `GET /v1/oks/analytics/overdue`              |
| Предупреждение: этапы в пределах 10 дней до срока               | `GET /v1/oks/analytics/upcoming`             |
| RBAC: oks_admin, oks_responsible, oks_initiator, oks_viewer     | `oks/security/rbac.py`                       |
| DB-схема: parent_object_id, initiator_user_id в oks_objects     | `database/migrations/v13_oks.sql`            |
| Docker: порт 8104 → 8005                                        | `docker-compose.yml`                         |

### ❌ Не реализовано в OKS

| Проблема                     | Комментарий                                                                  |
|------------------------------|------------------------------------------------------------------------------|
| Push/email уведомления       | Правила хранятся в БД, но отправка не реализована (нет воркера)              |
| Тесты                        | `test_smoke.py` — только заготовка                                           |
| Интеграция с 1С              | Факты по бюджету вносятся вручную, авто-синхронизации нет                    |
