#!/bin/bash
# BioFabric ERP — Database Initialization
# Выполняет все SQL-файлы в правильном порядке

set -e

PGUSER="${POSTGRES_USER:-biofabric}"
PGDATABASE="${POSTGRES_DB:-biofabric}"

run_sql() {
    echo "Running: $1"
    psql -U "$PGUSER" -d "$PGDATABASE" -f "$1"
}

cd /docker-entrypoint-initdb.d/migrations

# Core
run_sql v1_core_schema.sql
run_sql v1_core_schema_delta.sql
run_sql v1_core_departments.sql

# OOK + CPVBP + OVBK
run_sql v2_v3_v4-2.sql

# Legal
run_sql v5_legal.sql
run_sql v6_legal_delta.sql

# HSE
run_sql v6_hse.sql

# HR
run_sql v7_hr.sql

# Marketing
run_sql v8_marketing.sql

# Procurement
run_sql v9_procurement.sql

# Quarantine
run_sql v10_quarantine_animals.sql

# R&D
run_sql v11_rnd.sql

# PEO
run_sql v12_peo.sql

# OKS
run_sql v13_oks.sql

echo "==================================="
echo "Database initialization complete!"
echo "==================================="
