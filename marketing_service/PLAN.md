# План доработки marketing_service

> Дата: 2026-02-11
> Статус: в работе
> Основание: анализ ТЗ (`ТЗ маркетинг-4.docx`) + аудит кода

---

## Структура плана

Работы разбиты на 5 фаз по убыванию приоритета.
Каждый пункт — отдельный чекпоинт: сделал → поставил ✅.

```
Фаза 1 — Критические баги       → сервис сломан до их устранения
Фаза 2 — Недостающие поля       → данные теряются на уровне API
Фаза 3 — Аналитический API      → VIEW есть в БД, эндпоинтов нет
Фаза 4 — Уведомления            → требование ТЗ п.9
Фаза 5 — RBAC + plan_jobs       → архитектурная полнота
```

---

## Фаза 1 — Критические баги (сервис не запустится)

### 1.1 — Лишние отступы на уровне модуля (IndentationError)

**Проблема:** несколько файлов имеют весь код с отступом 4 пробела
на уровне модуля — Python выдаёт `IndentationError` при импорте.

**Затронутые файлы:**
- `marketing/api/router_posts.py` — весь файл с отступом
- `marketing/api/router_calendar.py` — весь файл с отступом
- `marketing/api/deps.py` — весь файл с отступом
- `marketing/services/publishing.py` — весь файл с отступом
- `marketing/repositories/sources_repo.py` — весь файл с отступом
- `marketing/repositories/calendar_repo.py` — весь файл с отступом
- `marketing/services/posts.py` — весь файл с отступом
- `marketing/security/rbac.py` — весь файл с отступом

**Действие:** убрать лишний отступ в каждом файле (сдвинуть содержимое к нулевому уровню).

- [x] router_posts.py — убрать отступ
- [x] router_calendar.py — убрать отступ
- [x] deps.py — убрать отступ
- [x] publishing.py — убрать отступ
- [x] sources_repo.py — убрать отступ
- [x] calendar_repo.py — убрать отступ
- [x] posts.py (services) — убрать отступ
- [x] rbac.py — убрать отступ

---

### 1.2 — Несоответствие имён колонок БД в posts_repo.py

**Проблема А:** колонка статуса в `mk_posts` называется `status_code`, а в коде везде используется `status`.

| Место | Что написано | Как должно быть |
|---|---|---|
| `create_draft_post` | `"status": "draft"` | `"status_code": "draft"` |
| `set_status` | `.values(status=status)` | `.values(status_code=status)` |

**Проблема Б:** контент поста в `mk_post_contents` хранится в колонке `body_md` (NOT NULL),
а в коде используется несуществующее поле `text`. Колонки `title` в `mk_post_contents` нет совсем.

| Место | Что написано | Как должно быть |
|---|---|---|
| `create_draft_post` | `{"title": ..., "text": ...}` | `{"body_md": data.get("text") or ""}` |
| `update_post` | `content_fields["text"] = data["text"]` | `content_fields["body_md"] = data["text"]` |

**Проблема В:** в `router_posts.py → publish_now` читается `row.get("text")` — нужно `row.get("body_md")`.

**Действия:**
- [x] `posts_repo.py` — заменить `"status"` на `"status_code"` во всех `.values()`
- [x] `posts_repo.py` — заменить `"text"` на `"body_md"` в insert/update `mk_post_contents`
- [x] `posts_repo.py` — убрать `"title"` из insert в `mk_post_contents` (поля нет)
- [x] `posts_repo.py` — `title` писать только в `mk_posts` (там колонка есть)
- [x] `router_posts.py` — исправить `row.get("text")` → `row.get("body_md")`

---

### 1.3 — Фильтрация meta_fields в update_post не обновляет title

**Проблема:** `update_post` фильтрует поля для `mk_posts` как `{"channel_id","format_id","topic_id","direction_id","planned_for"}` — поле `title` сюда не входит,
хотя в `mk_posts` оно есть. Заголовок нельзя обновить через PATCH.

**Действие:**
- [x] `posts_repo.py` — добавить `"title"` в `meta_fields` для обновления `mk_posts`

---

### 1.4 — Проверка запуска (smoke test)

После фаз 1.1–1.3 сервис должен стартовать без ошибок.

- [ ] Запустить `uvicorn marketing.app:app --reload` — нет ошибок импорта
- [ ] `GET /docs` — Swagger открывается
- [ ] `POST /v1/marketing/posts` с тестовыми данными — нет 500

---

## Фаза 2 — Недостающие поля в API

### 2.1 — audience, goals, tone в PostCreate/PostUpdate

**Проблема:** в `mk_posts` есть поля `audience TEXT`, `goals TEXT`, `tone TEXT` (требование ТЗ п.5 «Уточнение целевой аудитории и ключевых сообщений»), но в Pydantic-схемах они отсутствуют — нельзя передать через API.

**Действия:**
- [x] `dto_posts.py` — добавить в `PostCreate`: `audience`, `goals`, `tone` (Optional[str])
- [x] `dto_posts.py` — добавить в `PostUpdate`: `audience`, `goals`, `tone` (Optional[str])
- [x] `dto_posts.py` — добавить в `PostRead`: `audience`, `goals`, `tone`
- [x] `posts_repo.py → create_draft_post` — добавить эти поля в INSERT `mk_posts`
- [x] `posts_repo.py → update_post` — добавить `audience`, `goals`, `tone` в `meta_fields`

---

### 2.2 — hashtags в PostCreate/PostUpdate

**Проблема:** `mk_post_contents` имеет `hashtags TEXT[]` — ТЗ п.6 «Предлагает ключевые теги и хэштеги». В API поля нет, хэштеги не сохраняются.

**Действия:**
- [x] `dto_posts.py` — добавить в `PostCreate` и `PostUpdate`: `hashtags: Optional[List[str]] = None`
- [x] `posts_repo.py → create_draft_post` — добавить `hashtags` в INSERT `mk_post_contents`
- [x] `posts_repo.py → update_post` — добавить `hashtags` в content_fields

---

### 2.3 — document_ids в PostCreate не обрабатываются

**Проблема:** `PostCreate` принимает `document_ids: List[int]`, но в `create_draft` они игнорируются — `DocumentsService.bind()` не вызывается.

**Действия:**
- [x] `router_posts.py → create_post` — получить `get_core` через Depends
- [x] После создания поста вызвать `DocumentsService(core).bind("mk_post", str(pid), doc_id)` для каждого id из `document_ids`

---

## Фаза 3 — Аналитический API

**Проблема:** в БД созданы 6 аналитических VIEW (ТЗ п.7–8), но ни одного API-эндпоинта для них нет.

### VIEW в БД и соответствующие эндпоинты:

| VIEW | Эндпоинт | Описание |
|---|---|---|
| `v_mk_plan_summary` | `GET /v1/marketing/analytics/summary` | Число постов по дням/каналам/статусам |
| `v_mk_distribution_by_topic` | `GET /v1/marketing/analytics/by-topic` | Распределение по рубрикам |
| `v_mk_distribution_by_format` | `GET /v1/marketing/analytics/by-format` | Распределение по форматам |
| `v_mk_distribution_by_channel` | `GET /v1/marketing/analytics/by-channel` | Распределение по каналам |
| `v_mk_calendar_density` | `GET /v1/marketing/analytics/density` | Насыщенность сетки по дням |
| `v_mk_upcoming_week_gaps` | `GET /v1/marketing/analytics/gaps` | Дни без контента на ближайшую неделю |

### Чекпоинты:
- [x] Создать `marketing/repositories/analytics_repo.py` — методы по одному на каждую VIEW
- [x] Создать `marketing/api/router_analytics.py` — 6 GET-эндпоинтов
- [x] `app.py` — зарегистрировать `router_analytics` с prefix `/v1/marketing`

---

## Фаза 4 — Уведомления

**Основание:** ТЗ п.9 — 4 типа уведомлений.

### 4.1 — Архитектура уведомлений

Стратегия: интерфейсные уведомления отправляем через `CoreClient` (ядро уже имеет `/v1/core/notifications`). Мессенджер-пуш — через Telegram-бота (токен уже в config).

- [x] `core_client/client.py` — добавить метод `notify(user_id, event_type, message, meta)`
- [x] Создать `marketing/services/notifier.py` — обёртка с именованными методами для каждого события

### 4.2 — Реализация 4 событий

| # | Событие | Триггер | Канал |
|---|---|---|---|
| N1 | Не хватает контента на неделю | `GET /analytics/gaps` вернул > 0 пустых дней | Интерфейс (push) |
| N2 | Пост сформирован ИИ | После `POST /ai/plan` и `POST /ai/ideas` | Интерфейс (системное) |
| N3 | Приближается дата публикации | Пост в статусе `approved/scheduled`, date <= now+3d | Мессенджер (push) |
| N4 | Пост утверждён | При переводе статуса в `approved` | Интерфейс (push) |

- [x] N1: вызов `notifier.content_gap_warning()` в `router_analytics.py → gaps` (если список не пуст)
- [x] N2: вызов `notifier.ai_post_created(post_ids)` в `router_ai.py` после генерации
- [x] N3: создать `services/deadline_checker.py` — функция `notify_upcoming_posts(db, core)`, вызываемая из `POST /analytics/notify-upcoming`
- [x] N4: вызов `notifier.post_approved(post_id, created_by)` в `router_posts.py → set_status` при status == "approved"
- [x] `router_posts.py` — добавить Depends для `get_user` туда, где нужно знать автора для уведомлений

---

## Фаза 5 — RBAC + mk_plan_jobs

### 5.1 — Подключить RBAC в роутерах

**Проблема:** `can()` определена в `rbac.py`, импортируется в `deps.py`, но ни в одном роутере не вызывается — права не проверяются.

**Действия:**
- [x] `deps.py` — реализовать `get_user()` с чтением JWT из Core (или оставить заглушку с ролями из токена)
- [x] `router_posts.py` — добавить `Depends(get_user)` и вызов `can(user, "create_post", "post")` в create_post
- [x] `router_posts.py` — проверять `can(user, "approve", "post")` при переводе в `approved` (через N4)
- [x] `router_posts.py` — проверять `can(user, "publish", "post")` в `publish_now`

### 5.2 — API для mk_plan_jobs

**Проблема:** таблица `mk_plan_jobs` (постановка задач на ИИ-генерацию с ЦА/целями/тоном — ТЗ п.1,5) существует в БД, но нет никакого API.

**Действия:**
- [x] Создать `marketing/repositories/plan_jobs_repo.py` — create, get, list
- [x] Создать `marketing/schemas/dto_plan_jobs.py` — PlanJobCreate, PlanJobRead
- [x] Создать `marketing/api/router_plan_jobs.py` — `POST /plan-jobs`, `GET /plan-jobs`, `GET /plan-jobs/{id}`
- [x] Связать: при создании job с direction_id/audience/goals/tone — запускать `AIPlanService.generate_from_prompt()`
- [x] `app.py` — зарегистрировать router

---

## Вне плана (backlog)

Следующие пункты **не в ТЗ MVP**, реализуются после приёмки:

- Реальная LLM-интеграция (замена заглушек в `ai_plan.py`, `ai_sources.py`)
- Парсер источников (RSS/URL-скрейпер) для `/sources/fetch`
- Рерайт материалов (ТЗ п.1 — упомянут как желаемый)
- Автоматическое расписание публикаций (ТЗ явно указывает ручную публикацию в MVP)
- Тесты (unit + integration) для новых эндпоинтов

---

## Сводная таблица чекпоинтов

| Фаза | Задача | Статус |
|---|---|---|
| 1.1 | Убрать отступы в 8 файлах | ✅ |
| 1.2 | Исправить status_code и body_md в posts_repo | ✅ |
| 1.3 | Добавить title в meta_fields | ✅ |
| 1.4 | Smoke test: сервис стартует, POST /posts работает | ⬜ ждёт БД |
| 2.1 | audience / goals / tone в схемах и репо | ✅ |
| 2.2 | hashtags в схемах и репо | ✅ |
| 2.3 | document_ids обрабатываются при создании поста | ✅ |
| 3 | analytics_repo.py + router_analytics.py (6 эндпоинтов) | ✅ |
| 4.1 | notify() в CoreClient + notifier.py | ✅ |
| 4.2 | N1–N4 уведомления подключены к триггерам | ✅ |
| 5.1 | RBAC вызывается в роутерах | ✅ |
| 5.2 | router_plan_jobs.py + репо + схемы | ✅ |
