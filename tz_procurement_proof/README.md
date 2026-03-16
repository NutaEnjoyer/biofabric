
# Proof-of-Work Code — Procurement Module (ЭкоСистема)

Этот репозиторий — **доказательная база выполненных работ по ТЗ (doc_b.docx)**.
Реализован минимально-жизнеспособный модуль закупок, покрывающий ключевые сценарии из ТЗ:
- создание заявки, иерархическая структура (уровни 1–3),
- многоступенчатое согласование универсальной формой,
- табличная часть выбора поставщика (коммерческие предложения),
- статусы/цвета и журнал событий,
- интеграционные заглушки (1С, OnlyOffice),
- отчётность (простая выборка) и экспорт (JSON),
- роли и права (упрощённо, на уровне ролей маршрутов).

## Быстрый старт
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# старт dev-сервера
uvicorn app.main:app --reload
```

Документация: `http://127.0.0.1:8000/docs`

## Доказательная ценность
- Наличие кода, схем данных, миграций, тестов и маршрутов API соотнесено с пунктами ТЗ в файле [TRACEABILITY.md](TRACEABILITY.md).
- В коммит-месседжах рекомендуется сохранять ссылки вида `TЗ-§X.Y` для связи с задачами.

## Структура
```
app/
  main.py
  database.py
  models.py
  schemas.py
  deps.py
  routers/
    requests.py
    approvals.py
    suppliers.py
    documents.py
    integrations.py
  services/
    workflow.py
    notifications.py
migrations/
  001_init.sql
tests/
  test_flow_basic.py
TRACEABILITY.md
requirements.txt
```

## Лицензия
Для демонстрации. Используйте и расширяйте в рамках проекта.
