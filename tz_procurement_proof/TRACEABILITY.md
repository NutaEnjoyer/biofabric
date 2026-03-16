
# TRACEABILITY — соответствие ТЗ (doc_b.docx) и кода

## 1. Процессы и статусы
- **Статусы** (§4 Цветовая схема): `app/models.py: StatusEnum, STATUS_COLOR`
- **Смена статуса** (§2, §3, §4): `app/services/workflow.py:set_status`, `PATCH /requests/{id}/status`

## 2. Журнал заявок и уровни
- **Создание/просмотр заявки** (§1, §4, уровни 1–3): `POST /requests`, `GET /requests`, `GET /requests/{id}`; модели `ProcurementRequest`, `RequestItem`

## 3. Универсальная форма согласования
- **Согласование** (§5): `POST /approvals` + модели `Approval`, `ApprovalDecisionEnum`

## 4. Табличная часть выбора поставщика
- **КП** (§6): `POST /suppliers/quotes`, `GET /suppliers/quotes/{request_id}`; модель `SupplierQuote`

## 5. Документы и шаблоны
- **Документы** (§9): `POST /documents`, `GET /documents/{request_id}`; модель `Document`

## 6. Интеграции
- **1С** (§8): заглушка вебхука `POST /integrations/1c/webhook/stock-received/{request_id}` -> перевод в `Исполнена`

## 7. Отчётность/экспорт
- **Поиск/фильтры по статусу** (§11): `GET /requests?status=...` (JSON-экспорт по сути)

## 8. Роли и права
- **Роли** (§7): перечислены в `RoleEnum`; для PoC роли упрощены, маршрутизация решений в `approvals.py`

## 9. Нефункциональные требования
- **Синхронизация справочников, обмен по событиям** (§13): отражено в структурах `Event` и моделях-справочниках (упрощённо).
