#!/bin/bash

DB_NAME="mirrulations"

echo "Starting PostgreSQL..."
brew services start postgresql

#TODO: Change so database doesn't get dropped when prod ready.

echo "Dropping database if it exists..."
dropdb --if-exists $DB_NAME

echo "Creating database..."
createdb $DB_NAME

echo "Creating schema..."
psql -d $DB_NAME -f db/schema-postgres.sql

echo "Inserting seed data..."
psql $DB_NAME <<'EOF'

INSERT INTO documents (
    document_id,
    docket_id,
    document_api_link,
    agency_id,
    document_type,
    modify_date,
    posted_date,
    document_title,
    comment_start_date,
    comment_end_date
)
VALUES (
    'CMS-2025-0242-0001',
    'CMS-2025-0242',
    'https://api.regulations.gov/v4/documents/CMS-2025-0242-0001',
    'CMS',
    'Proposed Rule',
    '2025-02-12 11:20:00+00',
    '2025-02-10 10:15:00+00',
    'ESRD Treatment Choices Model Updates',
    '2025-03-01 00:00:00+00',
    '2025-05-01 00:00:00+00'
);

SELECT * FROM documents;

EOF

echo ""
echo "Database '$DB_NAME' is fully initialized."
echo "Connect with:"
echo "psql $DB_NAME"
