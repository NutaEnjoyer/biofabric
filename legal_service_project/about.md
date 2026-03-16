Что внутри (папки и назначение)
.env.example — переменные окружения (только DATABASE_URL).
pyproject.toml — зависимости (FastAPI, psycopg3, pydantic, dotenv).
README_procurement.md — как запустить, префикс модульного API (/v1/legal), связь с Core.
migrations/0001_legal_subject_tables.sql — ТОЛЬКО предметные таблицы модуля. Ядро не трогаем (в файле примеры-комментарии).
schema/ — снапшот DDL предметных таблиц, маппинг таблица→сущность, entity types и инварианты.
tests/ — заглушка для автотестов.
legal/ — код модуля: FastAPI, репозитории (SQL), сервисы (бизнес-логика), API-ручки, общая утилитка.
Полная детализация функций (что делает каждая, ТЗ → БД → поведение)
Ниже описываю ключевые функции модуля. В коде у каждой — такие же комментарии «TЗ:», «DB:», «Core:», чтобы разработчик видел трассировку.
1) Привязка договора к маршруту согласования
Функция: RequestsService.bind_workflow() → RequestsRepo.bind_workflow()
TЗ:
Привязать договор к активной дефиниции workflow contract_approval.
Создать workflow_instances c entity_type='contract', entity_id = <contract_id> (строкой), state='draft'.
Записать/обновить связь в contract_workflow_bind (по contract_id). Если уже привязан — вернуть already_bound.
DB:
workflow_definitions(id, code='contract_approval', is_active, version)
workflow_instances(id, definition_id, entity_type, entity_id, state, context_json)
contract_workflow_bind(contract_id PK, wf_instance_id)
Поведение:
Проверка существования договора.
Поиск активной дефиниции (последняя по версии).
Если связь уже есть — вернуть (wf_instance_id, "already_bound").
Иначе создать workflow_instances и upsert в contract_workflow_bind.
Возврат (wf_instance_id, "bound").
2) Пометить просроченные договоры
Функция: RequestsService.mark_overdue() → RequestsRepo.mark_overdue()
TЗ:
Если end_date < now() (и не NULL) и статус не completed|terminated|overdue, то присвоить status_code='overdue'.
Запуск ручной (кнопка/API).
DB: contracts(contract_id, end_date, status_code)
Поведение:
Один массовый UPDATE; вернуть число затронутых строк.
По желанию добавим ночной job (не включено, т.к. ты просил «по кнопке»).
3) KPI «Доля договоров с активной гарантией»
Функция: RequestsService.guarantee_share() → RequestsRepo.get_guarantee_share()
TЗ:
На «сейчас»: среди всех contracts, у скольких есть bank_guarantees.status='active'.
DB:
contracts(contract_id)
bank_guarantees(contract_id, status)
Поведение:
Два счётчика: общего количества договоров и договоров с активной гарантией.
Возвращается {with_guarantee, total, pct} (pct до двух знаков, 0 если total=0).
4) «Сводка нарушений и исключений»
Функция: RequestsService.issues(min_severity) → RequestsRepo.get_issues(min_severity)
TЗ:
Агрегировать по каждому договору количество записей:
contract_risks (COUNT), с опциональным фильтром по severity >= min_severity;
contract_template_deviations (COUNT).
Вернуть для всех договоров, даже без записей (нулевые значения).
DB:
contracts, contract_risks(severity), contract_template_deviations
Поведение:
Два CTE (risks и deviations) с GROUP BY contract_id; затем LEFT JOIN к contracts.
Результат: [{contract_id, risks_cnt, deviations_cnt}, ...].
Если нужен учёт «серьёзности» в итоговом балле — добавим отдельное поле (сумма severity/веса).
5) Валидатор сторон договора
Функция: RequestsService.validate_parties(contract_id) → RequestsRepo.validate_parties(contract_id)
TЗ:
Проверить, что роли сторон только из набора: customer|supplier|guarantor|other.
Обязательно наличие customer и supplier.
DB: contract_parties(contract_id, role_code, legal_entity_id)
Поведение:
Возвращает список проблем: ["unsupported_role_in_contract_parties", "missing_customer", "missing_supplier"].
Используется фронтом/интеграцией для подсветки/блокировки перехода по workflow.
6) Реестр договоров без активной гарантии
Функция: RequestsService.without_guarantee() → RequestsRepo.list_without_active_guarantee()
TЗ:
Список договоров, у которых нет активной гарантии.
DB: contracts, bank_guarantees(status)
Поведение:
NOT EXISTS подзапрос; возвращает [{contract_id, contract_no}] (можно расширить полями по надобности).
7) Уведомления (режим шаблонов)
Функция: RequestsService.send_template(template_code, to, payload) → RequestsRepo.send_notification_template(...)
TЗ:
Писать в notifications_outbox поля template_code, to_json, payload_json, status='pending'.
Старые поля event_id, channel_id оставляем как заглушку (0), контракт ядра договоримся позже.
DB: notifications_outbox(template_code, to_json, payload_json, status, updated_at, ...)
Поведение:
Запись уходит в outbox, далее воркер ядра отправляет (email/telegram по шаблону).
Возвращает outbox_id.
Ошибки отправки разруливает воркер ядра; из модуля можно только смотреть статус.
8) ЕИС: постановка в очередь + job
Функция: RequestsService.eis_enqueue(contract_id, payload) → RequestsRepo.enqueue_eis(...)
TЗ:
Ошибки считаем фатальными, автоповторов нет. Отправка — только вручную повторно.
Модуль ставит запись в eis_export_queue(status='pending') и создаёт jobs(type='send_eis_contract') с payload {"queue_id": ...}.
Дальше внешний воркер по типу job выполняет фактическую отправку (эндпоинт ЕИС сейчас отсутствует → заглушка на уровне endpoint-конфига).
DB: eis_export_queue, jobs
Поведение:
Возвращает {queue_id, job_id}.
Повторная постановка — по пользовательскому действию (кнопка/ручка) после анализа ошибки.
9) Импорт из 1С (REST, через staging)
Функции:
RequestsService.import_1c_stage(payload) → RequestsRepo.stage_1c(payload)
RequestsService.import_1c_upsert(stage_id) → RequestsRepo.upsert_contract_from_1c(stage_id)
TЗ:
Сначала сохраняем входной JSON целиком в import_contracts_1c(payload_json) → получаем stage_id.
Затем по stage_id выполняем апсерт договора по ключу (contract_no, entity_id) (и date валидацией):
Если найден — обновляем amount_total/currency при наличии.
Если не найден — создаём новую запись.
DB: import_contracts_1c, contracts(contract_no, entity_id, amount_total, currency)
Поведение:
Возвращаем stage_id и затем contract_id.
Если нет требуемых полей в payload → ошибка (400).
10) Синхронизация дедлайнов
Функция: RequestsService.sync_deadlines(contract_id) → RequestsRepo.sync_deadlines_for_contract(...)
TЗ:
Удалить старые дедлайны данного договора по entity_type='contract'.
Прочитать performance_due, payment_due, end_date, initiator_user_id из contracts.
Вставить по одному дедлайну на каждое НЕ-NULL поле (execution_due, payment_due, end).
DB: calendar_deadlines(entity_type, entity_id, due_at, kind, title, description, responsible_user_id, status)
Поведение:
Возвращает количество созданных записей.
Используется как «ручная синхронизация» (эндпоинт), может быть повешено на триггер/джоб позже.
 код
Логика/оркестрация: legal/services/requests.py
SQL/маппинг: legal/repositories/requests_repo.py
HTTP-ручки: legal/api/router_requests.py
Коннект к БД: legal/db.py
Модели запросов/ответов: legal/schemas/*.py
