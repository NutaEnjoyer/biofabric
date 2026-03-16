-- Начальные данные модуля «Карантинирование животных»
-- Виды, возрастные и весовые категории, типовые группы вивария

BEGIN;

-- ------------------------------------------------
-- Виды животных
-- ------------------------------------------------
INSERT INTO qa_species (name, code, has_age_categories, has_mass_bins)
SELECT v.name, v.code, v.has_age, v.has_mass
FROM (VALUES
    ('Мышь',           'mouse',       TRUE,  TRUE),
    ('Крыса',          'rat',         TRUE,  TRUE),
    ('Кролик',         'rabbit',      TRUE,  TRUE),
    ('Морская свинка', 'guinea_pig',  TRUE,  FALSE),
    ('Хомяк',          'hamster',     FALSE, FALSE),
    ('Кошка',          'cat',         FALSE, FALSE),
    ('Собака',         'dog',         FALSE, FALSE)
) AS v(name, code, has_age, has_mass)
WHERE NOT EXISTS (SELECT 1 FROM qa_species WHERE code = v.code);

-- ------------------------------------------------
-- Возрастные категории
-- ------------------------------------------------

-- Мышь
INSERT INTO qa_age_categories (species_id, name, min_age_days, max_age_days)
SELECT s.species_id, v.name, v.min_d, v.max_d
FROM (VALUES
    ('Новорождённые',  0,   21),
    ('Молодняк',      22,   60),
    ('Взрослые',      61,  365),
    ('Старые',       366, NULL)
) AS v(name, min_d, max_d)
JOIN qa_species s ON s.code = 'mouse'
WHERE NOT EXISTS (
    SELECT 1 FROM qa_age_categories WHERE species_id = s.species_id AND name = v.name
);

-- Крыса
INSERT INTO qa_age_categories (species_id, name, min_age_days, max_age_days)
SELECT s.species_id, v.name, v.min_d, v.max_d
FROM (VALUES
    ('Новорождённые',  0,   21),
    ('Молодняк',      22,   90),
    ('Взрослые',      91,  365),
    ('Старые',       366, NULL)
) AS v(name, min_d, max_d)
JOIN qa_species s ON s.code = 'rat'
WHERE NOT EXISTS (
    SELECT 1 FROM qa_age_categories WHERE species_id = s.species_id AND name = v.name
);

-- Кролик
INSERT INTO qa_age_categories (species_id, name, min_age_days, max_age_days)
SELECT s.species_id, v.name, v.min_d, v.max_d
FROM (VALUES
    ('Крольчата',   0,   60),
    ('Молодняк',   61,  180),
    ('Взрослые',  181,  730),
    ('Старые',    731, NULL)
) AS v(name, min_d, max_d)
JOIN qa_species s ON s.code = 'rabbit'
WHERE NOT EXISTS (
    SELECT 1 FROM qa_age_categories WHERE species_id = s.species_id AND name = v.name
);

-- Морская свинка
INSERT INTO qa_age_categories (species_id, name, min_age_days, max_age_days)
SELECT s.species_id, v.name, v.min_d, v.max_d
FROM (VALUES
    ('Новорождённые',  0,   21),
    ('Молодняк',      22,   90),
    ('Взрослые',      91,  365)
) AS v(name, min_d, max_d)
JOIN qa_species s ON s.code = 'guinea_pig'
WHERE NOT EXISTS (
    SELECT 1 FROM qa_age_categories WHERE species_id = s.species_id AND name = v.name
);

-- ------------------------------------------------
-- Весовые категории
-- ------------------------------------------------

-- Мышь (граммы)
INSERT INTO qa_mass_bins (species_id, name, min_grams, max_grams)
SELECT s.species_id, v.name, v.min_g, v.max_g
FROM (VALUES
    ('до 10 г',    0,  10),
    ('10–20 г',   10,  20),
    ('20–30 г',   20,  30),
    ('свыше 30 г',30, NULL)
) AS v(name, min_g, max_g)
JOIN qa_species s ON s.code = 'mouse'
WHERE NOT EXISTS (
    SELECT 1 FROM qa_mass_bins WHERE species_id = s.species_id AND name = v.name
);

-- Крыса (граммы)
INSERT INTO qa_mass_bins (species_id, name, min_grams, max_grams)
SELECT s.species_id, v.name, v.min_g, v.max_g
FROM (VALUES
    ('до 100 г',    0,  100),
    ('100–200 г', 100,  200),
    ('200–350 г', 200,  350),
    ('свыше 350 г',350, NULL)
) AS v(name, min_g, max_g)
JOIN qa_species s ON s.code = 'rat'
WHERE NOT EXISTS (
    SELECT 1 FROM qa_mass_bins WHERE species_id = s.species_id AND name = v.name
);

-- Кролик (граммы)
INSERT INTO qa_mass_bins (species_id, name, min_grams, max_grams)
SELECT s.species_id, v.name, v.min_g, v.max_g
FROM (VALUES
    ('до 1 кг',      0,    1000),
    ('1–2 кг',    1000,    2000),
    ('2–3 кг',    2000,    3000),
    ('свыше 3 кг',3000,    NULL)
) AS v(name, min_g, max_g)
JOIN qa_species s ON s.code = 'rabbit'
WHERE NOT EXISTS (
    SELECT 1 FROM qa_mass_bins WHERE species_id = s.species_id AND name = v.name
);

-- ------------------------------------------------
-- Типовые группы вивария
-- ------------------------------------------------
INSERT INTO qa_groups (direction_id, species_id, name)
SELECT d.direction_id, s.species_id, v.name
FROM (VALUES
    ('vivarium', 'mouse',      'Группа А'),
    ('vivarium', 'mouse',      'Группа Б'),
    ('vivarium', 'rat',        'Группа А'),
    ('vivarium', 'rat',        'Группа Б'),
    ('vivarium', 'rabbit',     'Группа А'),
    ('vivarium', 'guinea_pig', 'Группа А'),
    ('vivarium', 'hamster',    'Группа А')
) AS v(dir_code, sp_code, name)
JOIN qa_directions d ON d.code = v.dir_code
JOIN qa_species    s ON s.code = v.sp_code
WHERE NOT EXISTS (
    SELECT 1 FROM qa_groups
    WHERE direction_id = d.direction_id
      AND species_id   = s.species_id
      AND name         = v.name
);

-- Группы подсобного хозяйства (без привязки к виду)
INSERT INTO qa_groups (direction_id, species_id, name)
SELECT d.direction_id, NULL, v.name
FROM (VALUES
    ('subsidiary', 'Основное стадо'),
    ('subsidiary', 'Ремонтное стадо'),
    ('subsidiary', 'Откорм')
) AS v(dir_code, name)
JOIN qa_directions d ON d.code = v.dir_code
WHERE NOT EXISTS (
    SELECT 1 FROM qa_groups
    WHERE direction_id = d.direction_id
      AND species_id IS NULL
      AND name = v.name
);

-- ------------------------------------------------
-- Фиксация
-- ------------------------------------------------
INSERT INTO schema_migrations(version, description)
SELECT 'v10b_quarantine_seed',
       'Начальные данные карантина: виды животных, возрастные/весовые категории, группы.'
WHERE NOT EXISTS (SELECT 1 FROM schema_migrations WHERE version = 'v10b_quarantine_seed');

COMMIT;
