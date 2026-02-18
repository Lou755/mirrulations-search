# Postgres DB Setup

## To start postgresql, create and initialize the database, as well as populate the database:
```bash
./setup_postgres.sh
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
psql -d mirrulations -f postgres.sql
```

Open a psql session connected to `mirrulations`:
```bash
psql mirrulations
```

Example `INSERT` for the `document` table (adjust values as needed):
```sql
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
```
Common psql tips and example PSQL
- Enable expanded display (easier to read wide rows): `\x`
- Show all rows from the `document` table:
```sql
SELECT * FROM document;
```
Exit psql
```sql
\q
```

Stop PostgreSQL service 
```bash
brew services stop postgresql
```