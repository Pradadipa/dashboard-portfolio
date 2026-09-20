#!/usr/bin/env bash
# Copy table data (no sequences, no generated columns) from a source database
# into the compose `db` container. Use when pg_dump fails on sequence privileges.
#
#   docker compose up -d db
#   docker compose exec -T db psql -U dashboard -d dashboard_demo -v ON_ERROR_STOP=1 < db/schema.sql
#   SRC_URL="postgresql://user:pass@localhost:5433/shopify" bash db/copy_real_data.sh
#
# The target tables/columns come from the target database, so schema.sql must be loaded first.
set -euo pipefail

: "${SRC_URL:?set SRC_URL to the source database URL (plain postgresql://, no +asyncpg)}"
DST_CMD="${DST_CMD:-docker compose exec -T db psql -U dashboard -d dashboard_demo}"

list=$($DST_CMD -qAt -F $'\t' -c "
  SELECT c.table_schema || '.' || c.table_name,
         string_agg(quote_ident(c.column_name), ',' ORDER BY c.ordinal_position)
  FROM information_schema.columns c
  JOIN information_schema.tables t USING (table_schema, table_name)
  WHERE t.table_type = 'BASE TABLE'
    AND c.is_generated = 'NEVER'
    AND c.table_schema IN ('shopify', 'ga4', 'ads', 'judgeme', 'auth')
  GROUP BY 1 ORDER BY 1" | tr -d '\r')

{
    # replica role = skip FK checks, so table order does not matter
    echo "SET session_replication_role = replica;"
    while IFS=$'\t' read -r tbl cols; do
        echo "copying $tbl" >&2
        echo "COPY $tbl ($cols) FROM stdin;"
        psql "$SRC_URL" -qAt -c "\\copy (SELECT $cols FROM $tbl) TO STDOUT" | tr -d '\r'
        echo '\.'
    done <<< "$list"
} | $DST_CMD -q -v ON_ERROR_STOP=1

echo "done" >&2
