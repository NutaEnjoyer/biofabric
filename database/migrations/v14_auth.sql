-- ERP-Биофабрика — v14: авторизация и управление пользователями
-- Добавляет: password_hash, username в app_users
--            роли всех модулей в справочник roles
-- Администратор (admin@biofabric.ru) создаётся при старте auth_service.

BEGIN;

-- -----------------------------------------------
-- 1) Расширить app_users
-- -----------------------------------------------
ALTER TABLE app_users ADD COLUMN IF NOT EXISTS username      TEXT UNIQUE;
ALTER TABLE app_users ADD COLUMN IF NOT EXISTS password_hash TEXT;

-- -----------------------------------------------
-- 2) Засеять роли всех модулей
-- -----------------------------------------------
INSERT INTO roles (role_code, name) VALUES
  -- Юридический
  ('legal_admin',       'Юрист (Администратор)'),
  ('legal_user',        'Юрист'),
  ('legal_viewer',      'Юрист (Наблюдатель)'),
  -- ОКС
  ('oks_admin',         'ОКС (Администратор)'),
  ('oks_responsible',   'ОКС (Ответственный)'),
  ('oks_initiator',     'ОКС (Инициатор)'),
  ('oks_viewer',        'ОКС (Наблюдатель)'),
  -- Маркетинг
  ('author',            'Маркетинг (Автор)'),
  ('reviewer',          'Маркетинг (Ревьюер)'),
  ('approver',          'Маркетинг (Согласователь)'),
  ('publisher',         'Маркетинг (Публикатор)')
ON CONFLICT (role_code) DO NOTHING;

-- -----------------------------------------------
-- 3) Фиксация миграции
-- -----------------------------------------------
INSERT INTO schema_migrations (version, description)
SELECT 'v14_auth',
       'Авторизация: password_hash/username в app_users, роли всех модулей.'
WHERE NOT EXISTS (SELECT 1 FROM schema_migrations WHERE version = 'v14_auth');

COMMIT;
