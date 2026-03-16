# Conventions

- Все PK — BIGSERIAL/BIGINT.
- FK ON DELETE RESTRICT (если не оговорено иначе).
- Идемпотентные миграции.
- Индексы на поля фильтрации: planned_for, channel_id, topic_id, status_id.
- Вьюхи для календаря/аналитики используются только для чтения.
