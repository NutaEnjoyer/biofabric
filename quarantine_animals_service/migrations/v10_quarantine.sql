-- Миграция предметных таблиц модуля Quarantine Animals

CREATE TABLE IF NOT EXISTS qa_species (
    id SERIAL PRIMARY KEY,
    code TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    has_age_bins BOOLEAN NOT NULL DEFAULT FALSE,
    has_mass_bins BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS qa_directions (
    id SERIAL PRIMARY KEY,
    code TEXT UNIQUE NOT NULL CHECK (code IN ('subsidiary','vivarium')),
    name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS qa_age_bins (
    id SERIAL PRIMARY KEY,
    species_id INT NOT NULL REFERENCES qa_species(id) ON DELETE CASCADE,
    code TEXT NOT NULL,
    label TEXT NOT NULL,
    UNIQUE(species_id, code)
);

CREATE TABLE IF NOT EXISTS qa_mass_bins (
    id SERIAL PRIMARY KEY,
    species_id INT NOT NULL REFERENCES qa_species(id) ON DELETE CASCADE,
    code TEXT NOT NULL,
    label TEXT NOT NULL,
    UNIQUE(species_id, code)
);

CREATE TABLE IF NOT EXISTS qa_groups (
    id SERIAL PRIMARY KEY,
    code TEXT UNIQUE NOT NULL,
    label TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS qa_cohorts (
    id SERIAL PRIMARY KEY,
    code TEXT UNIQUE NOT NULL,
    label TEXT NOT NULL,
    status_tag TEXT
);

-- Журнал операций (ledger)
-- status_code: 'draft', 'current', 'archived'
CREATE TABLE IF NOT EXISTS qa_ledger (
    id BIGSERIAL PRIMARY KEY,
    op_date DATE NOT NULL,
    period_month CHAR(7) NOT NULL, -- YYYY-MM
    op_type TEXT NOT NULL CHECK (op_type IN ('opening_balance','intake','withdrawal','issue_for_control','movement_out','movement_in','adjustment')),
    status_code TEXT NOT NULL DEFAULT 'draft' CHECK (status_code IN ('draft','current','archived')),

    species_id INT NOT NULL REFERENCES qa_species(id),
    direction_id INT NOT NULL REFERENCES qa_directions(id),

    quantity INT NOT NULL,

    sex TEXT,
    age_bin_id INT REFERENCES qa_age_bins(id),
    mass_bin_id INT REFERENCES qa_mass_bins(id),

    group_id INT REFERENCES qa_groups(id),
    cohort_id INT REFERENCES qa_cohorts(id),

    transfer_key TEXT,
    transfer_side TEXT CHECK (transfer_side IN ('out','in')),

    purpose_text TEXT,
    reason TEXT,
    adjusts_period CHAR(7),

    created_at TIMESTAMP NOT NULL DEFAULT now(),
    created_by TEXT,
    approved_at TIMESTAMP,
    approved_by TEXT
);

CREATE INDEX IF NOT EXISTS idx_qa_ledger_period ON qa_ledger(period_month);
CREATE INDEX IF NOT EXISTS idx_qa_ledger_status ON qa_ledger(status_code);
CREATE INDEX IF NOT EXISTS idx_qa_ledger_transfer ON qa_ledger(transfer_key);

-- Импорт: job + строки
CREATE TABLE IF NOT EXISTS qa_import_jobs (
    id BIGSERIAL PRIMARY KEY,
    import_batch_id TEXT,
    filename TEXT,
    uploaded_at TIMESTAMP NOT NULL DEFAULT now(),
    uploaded_by TEXT,
    status TEXT NOT NULL DEFAULT 'received' CHECK (status IN ('received','parsed','validated','applied','failed')),
    error_text TEXT,
    raw_file_oid OID
);

CREATE TABLE IF NOT EXISTS qa_import_rows (
    id BIGSERIAL PRIMARY KEY,
    job_id BIGINT NOT NULL REFERENCES qa_import_jobs(id) ON DELETE CASCADE,
    line_number INT,
    raw_json JSONB NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','error','applied','skipped')),
    error_text TEXT,
    created_ledger_ids BIGINT[]
);
