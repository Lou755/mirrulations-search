# Postgres DB Setup

## To start postgresql and create, initialize, and populate the database, from the root directory, run:
```bash
./db/setup_postgres.sh
```

## To connect to DB:
```bash
python3 src/mirrsearch/db.py
# Postgres DB — Quick Reference

This file provides quick commands to start, stop, and initialize the `mirrulations` PostgreSQL database used by this project.

Prerequisites:
- Homebrew-installed PostgreSQL (or another PostgreSQL installation reachable from your shell)

Start PostgreSQL service
```bash
brew services start postgresql
```

Create / drop the `mirrulations` database
```bash
# Drop the database (if needed)
dropdb mirrulations

# Create the database
createdb mirrulations
```

Initialize schema (run the SQL schema file provided in the repository)
```bash
psql -d mirrulations -f db/schema-postgres.sql
```

Open a psql session connected to `mirrulations`:
```bash
psql mirrulations
```

Example `INSERT` for the `documents` table (adjust values as needed):
```sql
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
```
Common psql tips and example PSQL
- Enable expanded display (easier to read wide rows): `\x`
- Show all rows from the `documents` table:
```sql
SELECT * FROM documents;
```
Exit psql
```sql
\q
```

Stop PostgreSQL service 
```bash
brew services stop postgresql
```
