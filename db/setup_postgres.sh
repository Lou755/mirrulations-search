#!/bin/bash

DB_NAME="mirrulations"

echo "Starting PostgreSQL..."
brew services start postgresql

echo "Dropping database if it exists..."
dropdb --if-exists $DB_NAME

echo "Creating database..."
createdb $DB_NAME

echo "Creating schema and inserting seed data..."

psql $DB_NAME <<'EOF'

-- Enable expanded display
\x

-- =========================
-- Create document table
-- =========================
CREATE TABLE document (
    docket_id TEXT PRIMARY KEY,
    title TEXT,
    cfr_part TEXT,
    agency_id TEXT,
    document_type TEXT,
    authors TEXT,
    comment_start_date DATE,
    comment_end_date DATE,
    posted_date TIMESTAMP,
    modified_date TIMESTAMP
);

-- =========================
-- Insert sample row
-- =========================
INSERT INTO document (
    docket_id,
    title,
    cfr_part,
    agency_id,
    document_type,
    authors,
    comment_start_date,
    comment_end_date,
    posted_date,
    modified_date
)
VALUES (
    'CMS-2025-0242',
    'ESRD Treatment Choices Model Updates',
    '42 CFR Parts 413 and 512',
    'CMS',
    'Proposed Rule',
    'CMS Innovation Center',
    '2025-03-01',
    '2025-05-01',
    '2025-02-10 10:15:00',
    '2025-02-12 11:20:00'
);

-- Show inserted data
SELECT * FROM document;

EOF

echo ""
echo "Database '$DB_NAME' is fully initialized."
echo "Connect with:"
echo "psql $DB_NAME"
