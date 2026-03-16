# Frontend Legal Module — Task Tracker

## Статусы
- [ ] — Не начато
- [~] — В работе
- [x] — Готово

---

## 1. Инициализация проекта
- [x] Создать React + TypeScript + Vite
- [x] Настроить Tailwind CSS
- [x] Установить зависимости (react-query, lucide-react, react-router)
- [x] Настроить структуру папок
- [x] Настроить API client (axios/fetch)

## 2. Layout & Навигация
- [x] Sidebar компонент
- [x] Header компонент (встроен в Sidebar)
- [x] Роутинг (react-router-dom)
- [x] Общий Layout wrapper

## 3. UI Kit (базовые компоненты)
- [x] Button (primary, secondary, danger)
- [x] Input, Select
- [x] Card (метрика, контейнер)
- [x] Table (с сортировкой)
- [x] Badge (статусы)
- [x] Modal
- [ ] Toast/Notification (inline alerts сделаны)

## 4. Страницы

### 4.1 Dashboard
- [x] KPI карточки (guarantee-share, issues count)
- [x] Быстрые действия

### 4.2 Договоры (Contracts)
- [x] Таблица договоров (GET /contracts)
- [x] Фильтр по статусу
- [x] Карточка договора (GET /contracts/{id})
- [x] Кнопка "Запустить согласование" (POST /workflow/bind)
- [x] Кнопка "Синхронизировать дедлайны" (POST /sync-deadlines)
- [x] Кнопка "Проверить стороны" (GET /validate-parties)
- [x] Список без гарантии (GET /without-guarantee)
- [x] Кнопка "Пометить просроченные" (POST /mark-overdue)

### 4.3 KPI & Риски
- [x] Доля с гарантией (GET /kpi/guarantee-share)
- [x] Таблица рисков (GET /kpi/issues)
- [x] Фильтр по severity

### 4.4 Интеграции
- [x] ЕИС: форма отправки (POST /eis/enqueue)
- [x] 1С: загрузка JSON (POST /import/1c/stage)
- [x] 1С: применить импорт (POST /import/1c/upsert/{id})

### 4.5 Уведомления
- [x] Форма отправки (POST /notifications/send)
- [x] Выбор шаблона, получателей

## 5. API интеграция
- [x] Типы TypeScript для всех DTO
- [x] React Query hooks для каждого эндпоинта
- [x] Обработка ошибок
- [x] Loading states

## 6. Финализация
- [ ] Адаптив (responsive)
- [x] Dockerfile для frontend
- [x] Обновить docker-compose.yml
- [ ] Тестирование всех эндпоинтов

---

## Прогресс

| Раздел | Статус | Прогресс |
|--------|--------|----------|
| Инициализация | ✅ | 5/5 |
| Layout | ✅ | 4/4 |
| UI Kit | ✅ | 6/7 |
| Dashboard | ✅ | 2/2 |
| Договоры | ✅ | 8/8 |
| KPI & Риски | ✅ | 3/3 |
| Интеграции | ✅ | 3/3 |
| Уведомления | ✅ | 2/2 |
| API | ✅ | 4/4 |
| Финализация | 🔄 | 2/4 |

**Общий прогресс: 39/42 задач (93%)**
