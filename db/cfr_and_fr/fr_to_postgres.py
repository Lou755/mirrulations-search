#!/usr/bin/env python3
"""
Fetch CFR references from the Federal Register API and insert into a PostgreSQL database.

Usage:
    python3 fr_to_postgres.py                        # interactive menu
    python3 fr_to_postgres.py --fr-doc 2025-13271 --docket-id FDA-2027-0001  # single CLI entry

Input modes (chosen from the interactive menu):
    1. Manual      — type in FR doc numbers and docket IDs one at a time
    2. Text file   — Large text document
    3. JSON file   — JSON from regulations.gov

Required .env file (same directory as this script):
    DB_HOST=localhost
    DB_PORT=5432
    DB_USER=your_user
    DB_PASSWORD=your_password

The database 'frtocfr' will be created automatically if it does not exist.
"""

import argparse
import json
import os
import re
import sys

# ── Dependency check ──────────────────────────────────────────────────────────
missing_packages = []
try:
    import requests
except ImportError:
    missing_packages.append("requests")
try:
    import psycopg2
    from psycopg2 import sql
    from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
except ImportError:
    missing_packages.append("psycopg2-binary")
try:
    from dotenv import load_dotenv
except ImportError:
    missing_packages.append("python-dotenv")

if missing_packages:
    print("ERROR: The following required packages are not installed:")
    for pkg in missing_packages:
        print(f"  pip install {pkg}")
    print(f"\nInstall them all at once with:\n  pip install {' '.join(missing_packages)}")
    sys.exit(1)
# ─────────────────────────────────────────────────────────────────────────────

APP_DB_NAME = "frtocfr"
TABLE_NAME  = "cfr_references"
FR_API_URL  = "https://www.federalregister.gov/api/v1/documents/{doc_number}.json"


# ── .env / DB helpers ─────────────────────────────────────────────────────────

def load_db_config() -> dict:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    env_path   = os.path.join(script_dir, ".env")

    if not os.path.exists(env_path):
        print(f"ERROR: No .env file found at: {env_path}")
        print(
            "Create a .env file with:\n"
            "  DB_HOST=localhost\n"
            "  DB_PORT=5432\n"
            "  DB_USER=...\n"
            "  DB_PASSWORD=..."
        )
        sys.exit(1)

    load_dotenv(env_path)
    required = ["DB_HOST", "DB_PORT", "DB_USER", "DB_PASSWORD"]
    missing  = [k for k in required if not os.getenv(k)]
    if missing:
        print(f"ERROR: Missing from .env: {', '.join(missing)}")
        sys.exit(1)

    return {
        "host":     os.getenv("DB_HOST"),
        "port":     int(os.getenv("DB_PORT")),
        "user":     os.getenv("DB_USER"),
        "password": os.getenv("DB_PASSWORD"),
    }


def ensure_database_exists(base_config: dict):
    print(f"Checking whether database '{APP_DB_NAME}' exists ...")
    try:
        conn = psycopg2.connect(**base_config, dbname="postgres")
    except psycopg2.OperationalError as e:
        print(f"ERROR: Could not connect to PostgreSQL: {e}")
        sys.exit(1)

    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (APP_DB_NAME,))
            exists = cur.fetchone()
        if exists:
            print(f"Database '{APP_DB_NAME}' already exists — skipping creation.")
        else:
            with conn.cursor() as cur:
                cur.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(APP_DB_NAME)))
            print(f"Database '{APP_DB_NAME}' created successfully.")
    finally:
        conn.close()


def database_exists(base_config: dict) -> bool:
    try:
        conn = psycopg2.connect(**base_config, dbname="postgres")
    except psycopg2.OperationalError as e:
        print(f"ERROR: Could not connect to PostgreSQL: {e}")
        return False

    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (APP_DB_NAME,))
            return cur.fetchone() is not None
    finally:
        conn.close()


def view_database(base_config: dict):
    if not database_exists(base_config):
        print(f"\nDatabase '{APP_DB_NAME}' does not exist yet.")
        return

    try:
        conn = psycopg2.connect(**base_config, dbname=APP_DB_NAME)
    except psycopg2.OperationalError as e:
        print(f"ERROR: Could not connect to database '{APP_DB_NAME}': {e}")
        return

    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT EXISTS (
                    SELECT 1
                    FROM information_schema.tables
                    WHERE table_schema = 'public' AND table_name = %s
                )
                """,
                (TABLE_NAME,),
            )
            table_ready = cur.fetchone()[0]

            if not table_ready:
                print(f"\nTable '{TABLE_NAME}' does not exist in '{APP_DB_NAME}'.")
                return

            cur.execute(
                sql.SQL(
                    """
                    SELECT id, docket_id, cfr_title, cfr_section
                    FROM {table}
                    ORDER BY id
                    """
                ).format(table=sql.Identifier(TABLE_NAME))
            )
            rows = cur.fetchall()

        print(f"\n{TABLE_NAME} rows: {len(rows)}")
        if not rows:
            print("  (no rows)")
            return

        print("  id | docket_id | cfr_title | cfr_section")
        print("  " + "-" * 50)
        for row in rows:
            row_id, docket_id, cfr_title, cfr_section = row
            print(f"  {row_id} | {docket_id} | {cfr_title} | {cfr_section}")
    finally:
        conn.close()


def ensure_table_exists(conn):
    create_sql = sql.SQL("""
        CREATE TABLE IF NOT EXISTS {table} (
            id          SERIAL PRIMARY KEY,
            docket_id   TEXT        NOT NULL,
            cfr_title   INTEGER     NOT NULL,
            cfr_section INTEGER     NOT NULL
        );
    """).format(table=sql.Identifier(TABLE_NAME))
    with conn.cursor() as cur:
        cur.execute(create_sql)
    conn.commit()


# ── Federal Register API ──────────────────────────────────────────────────────

def fetch_cfr_references(fr_doc_number: str) -> list[dict]:
    url     = FR_API_URL.format(doc_number=fr_doc_number)
    params  = {"fields[]": "cfr_references"}
    headers = {"accept": "*/*"}

    print(f"  Fetching CFR references for FR doc: {fr_doc_number} ...")
    try:
        response = requests.get(url, params=params, headers=headers, timeout=30)
    except requests.ConnectionError:
        print("  ERROR: Could not reach the Federal Register API.")
        return []

    if response.status_code == 404:
        print(f"  ERROR: FR doc '{fr_doc_number}' not found.")
        return []

    response.raise_for_status()
    cfr_refs = response.json().get("cfr_references", [])
    if not cfr_refs:
        print("  WARNING: No CFR references found for this document.")
    return cfr_refs


# ── DB insert ─────────────────────────────────────────────────────────────────

def insert_references(conn, docket_id: str, cfr_refs: list[dict]) -> int:
    insert_sql = sql.SQL("""
        INSERT INTO {table} (docket_id, cfr_title, cfr_section)
        VALUES (%s, %s, %s)
    """).format(table=sql.Identifier(TABLE_NAME))

    rows = []
    for ref in cfr_refs:
        title = ref.get("title")
        part  = ref.get("part")
        if title is None or part is None:
            print(f"  Skipping incomplete reference: {ref}")
            continue
        rows.append((docket_id, int(title), int(part)))

    if not rows:
        print("  No valid rows to insert.")
        return 0

    with conn.cursor() as cur:
        cur.executemany(insert_sql, rows)
    conn.commit()
    return len(rows)


def process_entry(conn, fr_doc: str, docket_id: str) -> int:
    cfr_refs = fetch_cfr_references(fr_doc)
    if not cfr_refs:
        return 0
    print(f"  Found {len(cfr_refs)} CFR reference(s): {cfr_refs}")
    inserted = insert_references(conn, docket_id, cfr_refs)
    print(f"  Inserted {inserted} row(s) for docket {docket_id}.")
    return inserted


# ── Input mode 1: Manual ──────────────────────────────────────────────────────

def collect_manual_entries() -> list[tuple[str, str]]:
    print("\n--- Manual Entry ---")
    while True:
        try:
            count = int(input("How many entries do you want to add? ").strip())
            if count >= 1:
                break
            print("  Please enter a number greater than 0.")
        except ValueError:
            print("  Invalid input — please enter a whole number.")

    entries = []
    for i in range(1, count + 1):
        print(f"\n  Entry {i} of {count}")
        fr_doc    = input("    Federal Register document number (e.g. 2025-13271): ").strip()
        docket_id = input("    Regulations.gov docket ID       (e.g. FDA-2027-0001): ").strip()
        if not fr_doc or not docket_id:
            print("    Both fields are required — skipping this entry.")
            continue
        entries.append((fr_doc, docket_id))
    return entries


# ── Input mode 2: Text file ───────────────────────────────────────────────────

def parse_text_file(path: str) -> list[tuple[str, str]]:
    """
    Large text document.

    Each document block looks like:
        data/AMS/AMS-2005-0001/text-.../documents/....json | frDocNum=05-17055
          FR: Docket No. FV05-984-1 IFR | 7 CFR 984

    Docket ID  = path split by '/' at index 2  (e.g. AMS-2005-0001)
    FR doc num = value after 'frDocNum='
    """
    if not os.path.exists(path):
        print(f"  ERROR: File not found: {path}")
        return []

    entries: list[tuple[str, str]] = []

    with open(path, "r", encoding="utf-8") as fh:
        lines = fh.readlines()

    current_fr_doc    = None
    current_docket_id = None

    for line in lines:
        line = line.rstrip("\n")

        # Document line: contains 'frDocNum='
        if "frDocNum=" in line:
            # Extract docket ID from path (index 2 when split on '/')
            path_part = line.split("|")[0].strip()
            parts     = path_part.split("/")
            if len(parts) >= 3:
                current_docket_id = parts[2].strip()
            else:
                current_docket_id = None

            # Extract FR doc number
            match = re.search(r"frDocNum=([^\s|]+)", line)
            current_fr_doc = match.group(1).strip() if match else None

            if current_docket_id and current_fr_doc:
                # Only add the pair once per document block (the FR lines below
                # are informational — we use the API instead)
                if (current_fr_doc, current_docket_id) not in entries:
                    entries.append((current_fr_doc, current_docket_id))

    print(f"  Parsed {len(entries)} unique (FR doc, docket) pair(s) from text file.")
    return entries


# ── Input mode 3: JSON file ───────────────────────────────────────────────────

def parse_json_file(path: str) -> list[tuple[str, str]]:
    """
    Parse a JSON array of regulations.gov document objects.

    Each element has the shape:
        { "document": { "attributes": { "docketId": "...", "frDocNum": "..." } } }

    Skips entries where frDocNum is missing, null, or looks like a bare
    Federal Register volume number (purely numeric, typically 1-3 digits).
    """
    if not os.path.exists(path):
        print(f"  ERROR: File not found: {path}")
        return []

    with open(path, "r", encoding="utf-8") as fh:
        try:
            data = json.load(fh)
        except json.JSONDecodeError as e:
            print(f"  ERROR: Could not parse JSON file: {e}")
            return []

    if not isinstance(data, list):
        print("  ERROR: Expected a JSON array at the top level.")
        return []

    entries: list[tuple[str, str]] = []
    skipped = 0

    for item in data:
        try:
            attrs     = item["document"]["attributes"]
            docket_id = attrs.get("docketId")
            fr_doc    = attrs.get("frDocNum")

            # Skip if either field is missing or null
            if not docket_id or not fr_doc:
                skipped += 1
                continue

            fr_doc    = str(fr_doc).strip()
            docket_id = str(docket_id).strip()

            # Skip bare volume numbers (e.g. "41", "75", "141") — these are
            # Federal Register volume numbers, not document numbers
            if re.fullmatch(r"\d{1,3}", fr_doc):
                skipped += 1
                continue

            pair = (fr_doc, docket_id)
            if pair not in entries:
                entries.append(pair)

        except (KeyError, TypeError):
            skipped += 1
            continue

    print(f"  Parsed {len(entries)} unique (FR doc, docket) pair(s) from JSON file.")
    if skipped:
        print(f"  Skipped {skipped} record(s) with missing/invalid frDocNum or docketId.")
    return entries


# ── Interactive menu ──────────────────────────────────────────────────────────

def interactive_menu(base_config: dict) -> list[tuple[str, str]]:
    print("=" * 55)
    print("  Federal Register → CFR → PostgreSQL importer")
    print("=" * 55)
    while True:
        print()
        print("  How would you like to proceed?")
        print("  1) Manual  — enter FR doc numbers and docket IDs by hand")
        print("  2) Text file — parse a large text document (.txt)")
        print("  3) JSON file — parse a regulations.gov documents JSON array")
        print("  4) View database — show current rows in cfr_references")
        print("  0) Exit")
        print()

        choice = input("  Enter 0, 1, 2, 3, or 4: ").strip()
        if choice == "1":
            return collect_manual_entries()
        if choice == "2":
            path = input("\n  Path to text file: ").strip()
            return parse_text_file(path)
        if choice == "3":
            path = input("\n  Path to JSON file: ").strip()
            return parse_json_file(path)
        if choice == "4":
            view_database(base_config)
            continue
        if choice == "0":
            return []

        print("  Please enter 0, 1, 2, 3, or 4.")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Fetch CFR references from the Federal Register and store in PostgreSQL.",
    )
    parser.add_argument("--fr-doc",    help="Federal Register document number, e.g. 2025-13271")
    parser.add_argument("--docket-id", help="Regulations.gov docket ID, e.g. FDA-2027-0001")
    args = parser.parse_args()

    # DB config is required for import mode and menu option 4
    base_config = load_db_config()

    # Single-entry shortcut via CLI flags
    if args.fr_doc and args.docket_id:
        entries = [(args.fr_doc, args.docket_id)]
    else:
        entries = interactive_menu(base_config)

    if not entries:
        print("\nNo valid entries to process. Exiting.")
        sys.exit(0)

    print(f"\n{len(entries)} entr{'y' if len(entries) == 1 else 'ies'} to process.")

    # DB setup
    ensure_database_exists(base_config)

    print(f"Connecting to '{APP_DB_NAME}' at {base_config['host']}:{base_config['port']} ...")
    conn = psycopg2.connect(**base_config, dbname=APP_DB_NAME)
    ensure_table_exists(conn)
    print(f"Table '{TABLE_NAME}' is ready.\n")

    # Process each entry
    total_rows = 0
    for idx, (fr_doc, docket_id) in enumerate(entries, start=1):
        print(f"[{idx}/{len(entries)}] FR doc: {fr_doc}  |  Docket: {docket_id}")
        total_rows += process_entry(conn, fr_doc, docket_id)
        print()

    conn.close()
    print(f"Done. {total_rows} total row(s) inserted across "
          f"{len(entries)} entr{'y' if len(entries) == 1 else 'ies'}.")


if __name__ == "__main__":
    main()
