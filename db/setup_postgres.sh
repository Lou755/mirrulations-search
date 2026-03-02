#!/bin/bash

DB_NAME="mirrulations"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Starting PostgreSQL..."
brew services start postgresql

#TODO: Change so database doesn't get dropped when prod ready.

echo "Dropping database if it exists..."
dropdb --if-exists $DB_NAME

echo "Creating database..."
createdb $DB_NAME

echo "Creating schema..."
psql -d $DB_NAME -f "$SCRIPT_DIR/schema-postgres.sql"

echo "Inserting seed data..."
psql -d $DB_NAME -f "$SCRIPT_DIR/sample-data.sql"

echo ""
echo "Database '$DB_NAME' is fully initialized."
echo "Connect with:"
echo "psql $DB_NAME"
