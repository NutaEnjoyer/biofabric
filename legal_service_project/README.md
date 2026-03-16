# Legal Service (Юристы)

**Модуль юридической службы ERP-Биофабрика**

**Префикс API:** `/v1/legal`
**Связь с Core:** workflow / notifications / jobs / audit / calendar_deadlines — используем таблицы ядра.

## Запуск

```bash
cp .env.example .env
uvicorn legal.app:app --reload --port 8001
```

Swagger UI: http://localhost:8001/docs
ReDoc: http://localhost:8001/redoc

## Структура проекта

```
legal_service_project/
├── legal/
│   ├── api/
│   │   ├── deps.py           # FastAPI зависимости (DB, Service)
│   │   └── router_requests.py # HTTP-эндпоинты
│   ├── repositories/
│   │   └── requests_repo.py   # SQL-запросы к БД
│   ├── services/
│   │   └── requests.py        # Бизнес-логика
│   ├── schemas/
│   │   └── dto_requests.py    # Pydantic DTO
│   ├── app.py                 # FastAPI приложение
│   └── db.py                  # Подключение к PostgreSQL
├── migrations/
│   └── 0001_legal_subject_tables.sql
├── schema/
│   └── schema.sql             # Справочник структуры БД
└── tests/
```

## API Endpoints

### Health
| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/healthz` | Проверка жизни сервиса |
| GET | `/readyz` | Проверка готовности (включая БД) |

### Договоры
| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/v1/legal/contracts` | Список договоров |
| GET | `/v1/legal/contracts/{id}` | Получить договор |
| POST | `/v1/legal/contracts/{id}/workflow/bind` | Привязать к workflow |
| POST | `/v1/legal/contracts/{id}/sync-deadlines` | Синхронизировать дедлайны |
| POST | `/v1/legal/contracts/mark-overdue` | Пометить просроченные |
| GET | `/v1/legal/contracts/without-guarantee` | Договоры без гарантии |
| GET | `/v1/legal/contracts/{id}/validate-parties` | Валидация сторон |

### KPI
| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/v1/legal/kpi/guarantee-share` | Доля с гарантией |
| GET | `/v1/legal/kpi/issues` | Сводка рисков и отклонений |

### Интеграции
| Метод | Путь | Описание |
|-------|------|----------|
| POST | `/v1/legal/eis/enqueue` | Поставить в очередь ЕИС |
| POST | `/v1/legal/import/1c/stage` | Импорт из 1С (staging) |
| POST | `/v1/legal/import/1c/upsert/{id}` | Импорт из 1С (upsert) |

### Уведомления
| Метод | Путь | Описание |
|-------|------|----------|
| POST | `/v1/legal/notifications/send` | Отправить по шаблону |

## Реализованные функции (из ТЗ)

1. **Привязка к workflow** — создание workflow_instance для согласования договора
2. **Пометка просроченных** — автоматическая смена статуса на 'overdue'
3. **KPI: доля с гарантией** — процент договоров с активной банковской гарантией
4. **Сводка нарушений** — агрегация рисков и отклонений от шаблона
5. **Валидация сторон** — проверка наличия customer/supplier
6. **Реестр без гарантии** — список договоров без активной гарантии
7. **Уведомления** — отправка через notifications_outbox
8. **ЕИС** — постановка в очередь экспорта
9. **Импорт 1С** — staging + upsert по contract_no
10. **Синхронизация дедлайнов** — создание записей в calendar_deadlines

## Зависимости от ядра

Модуль использует следующие таблицы из Core:
- `app_users` — пользователи
- `workflow_definitions`, `workflow_instances` — маршруты согласования
- `calendar_deadlines` — дедлайны
- `jobs` — фоновые задачи
- `notifications_outbox`, `notification_templates` — уведомления

## Схема БД

Основные таблицы (из `v5_legal.sql`):
- `contracts` — реестр договоров
- `contract_statuses` — статусы жизненного цикла
- `contract_types` — типы договоров
- `contract_parties` — стороны (customer/supplier/guarantor/other)
- `contract_risks` — выявленные риски
- `contract_template_deviations` — отклонения от шаблона
- `bank_guarantees` — банковские гарантии
- `bank_guarantee_statuses` — статусы гарантий

Интеграционные таблицы (из `v6_legal_delta.sql`):
- `eis_export_queue` — очередь экспорта в ЕИС
- `eis_export_log` — лог обмена
- `import_contracts_1c` — staging импорта из 1С

## Переменные окружения

```env
DATABASE_URL=postgresql://user:password@localhost:5432/biofabric
```

## Тесты

```bash
pytest tests/ -v
```
