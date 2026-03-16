# Quarantine Animals Module (FastAPI)

Назначение: учет поголовья в разрезе вида, направления (subsidiary/vivarium), пола, возрастных/весовых категорий, групп/когорт; операции поступления/выбытия/выдачи/перемещения/корректировок; импорт CSV; отчеты; workflow-утверждение.

## Быстрый старт
```bash
cp .env.example .env
# отредактируйте DATABASE_URL
poetry install
uvicorn quarantine.app:app --reload
```

## API корневой префикс
- `/v1/quarantine`

## Основные эндпоинты
- `POST /operations` — создать операцию (intake/withdrawal/issue_for_control/movement/adjustment)
- `POST /adjustment` — alias на создание корректировки
- `POST /import` — загрузка CSV (Excel сохраняйте в CSV-UTF8)
- `GET  /reports/monthly-summary` — свод за месяц
- `GET  /health` — проверка живости

## Статусы
- draft -> current -> archived (архивация 1-го числа месяца джобой)
