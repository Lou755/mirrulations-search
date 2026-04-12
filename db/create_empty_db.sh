#!/bin/bash
# Create an empty Postgres database with schema only (no sample data).
# Usage: [DB_NAME=mirrulations] ./db/create_empty_db.sh [-f|--force]
# For testing: DB_NAME=mirrulations_test ./db/create_empty_db.sh
# Options:
#   -f, --force    Overwrite database without prompting

set -e

FORCE=false
for arg in "$@"; do
    case "$arg" in
        -f|--force)
            FORCE=true
            ;;
        *)
            echo "Unknown option: $arg"
            exit 1
            ;;
    esac
done

DB_NAME="${DB_NAME:-mirrulations}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCHEMA_FILE="$SCRIPT_DIR/schema-postgres.sql"

# Ensure Postgres is running (Homebrew macOS)
PG_VERSION="${PG_VERSION:-$(brew list 2>/dev/null | grep -oE 'postgresql@[0-9]+' | sort -t@ -k2 -n | tail -1 | cut -d@ -f2)}"
if [ -n "$PG_VERSION" ]; then
    export PATH="/opt/homebrew/opt/postgresql@${PG_VERSION}/bin:$PATH"
fi
if ! pg_isready -q 2>/dev/null; then
    echo "Starting PostgreSQL..."
    brew services start postgresql@${PG_VERSION:-14} 2>/dev/null || brew services start postgresql 2>/dev/null || true
    sleep 2
fi
if ! pg_isready -q 2>/dev/null; then
    echo "Error: PostgreSQL is not running. Start it with: brew services start postgresql"
    exit 1
fi

# Check if database already exists → prompt before overwrite (unless -f/--force flag)
if psql postgres -tAc "SELECT 1 FROM pg_database WHERE datname='$DB_NAME'" 2>/dev/null | grep -q 1; then
    echo "Warning: Database '$DB_NAME' already exists."
    if [ "$FORCE" != "true" ]; then
        read -p "Overwrite it? (y/n): " confirm
        if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
            echo "Aborted. Database was not modified."
            exit 0
        fi
    fi
fi

if [ ! -f "$SCHEMA_FILE" ]; then
    echo "Error: Schema file not found at $SCHEMA_FILE"
    exit 1
fi

echo "Dropping database if it exists..."
dropdb --if-exists "$DB_NAME"

echo "Creating database..."
createdb "$DB_NAME"

echo "Loading schema..."
psql -q -d "$DB_NAME" -f "$SCHEMA_FILE"

# Verify: expect all 9 tables from schema-postgres.sql
TABLES=$(psql -d "$DB_NAME" -tAc "SELECT count(*) FROM information_schema.tables WHERE table_schema='public' AND table_name IN ('dockets','documentswithfrdoc','comments','links','cfrparts','federal_register_documents','users','collections','collection_dockets','admins','authorized_users');")
echo "Created $TABLES tables."
if [ "$TABLES" != "11" ]; then
    echo "Error: Expected 11 tables; found $TABLES."
    exit 1
fi

echo "Successfully created empty database '$DB_NAME' (schema only)."
echo "Connect with: psql $DB_NAME"
