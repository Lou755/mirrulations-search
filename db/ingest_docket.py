#!/usr/bin/env python3
"""
Load docket metadata, regulatory documents, and public comments from mirrulations S3 JSON into
PostgreSQL (tables ``dockets``, ``documentsWithFRdoc``, and ``comments``).

By default, S3 download includes ``docket/``, ``documents/``, ``comments/``, and derived data (when
present). Use ``--skip-comments-download`` to fetch only docket + documents. Use
``--skip-comments-ingest`` to load docket + documents into Postgres but not ``comments``.

Maps regulations.gov v4 fields via ``fed_reg_gov_data/load_documents.py`` for documents and the
same comment column mapping as the former ``ingest_comments.py`` workflow.

Directory layout after S3 download:
    <output-folder>/<DOCKET-ID>/raw-data/docket/*.json
    <output-folder>/<DOCKET-ID>/raw-data/documents/*.json
    <output-folder>/<DOCKET-ID>/raw-data/comments/*.json

Examples:
    python db/ingest_docket.py
    python db/ingest_docket.py --download-s3 CMS-2025-0240
    python db/ingest_docket.py --docket-dir ./CMS-2025-0240
    python db/ingest_docket.py --download-s3 FAA-2025-0618 --download-only
"""
from __future__ import annotations

import argparse
import glob
import json
import logging
import os
import queue
import sys
import threading
import time
import warnings
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    import boto3
    from botocore import UNSIGNED
    from botocore.config import Config
except ImportError:
    boto3 = None
    UNSIGNED = None
    Config = None
import psycopg2
import psycopg2.errors
from psycopg2.extras import execute_values

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

from fed_reg_gov_data.load_documents import COLUMNS as DOC_COLS, map_document

warnings.filterwarnings(
    "ignore",
    message=".*Boto3 will no longer support Python 3.9.*",
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)

BATCH_SIZE = 500

# ---------------------------------------------------------------------------
# S3 download (mirrulations public bucket, unsigned)
# ---------------------------------------------------------------------------

S3_BUCKET = "mirrulations"
RAW_DATA_PREFIX = "raw-data"
DERIVED_DATA_PREFIX = "derived-data"
_s3_client = None


def _s3():
    global _s3_client  # pylint: disable=global-statement
    if _s3_client is None:
        _s3_client = boto3.client("s3", config=Config(signature_version=UNSIGNED))
    return _s3_client


def _normalize_docket_id(docket_id: str) -> str:
    s = docket_id.strip()
    if not s:
        return s
    if "-" not in s:
        return s.upper()
    head, tail = s.split("-", 1)
    return f"{head.split('_')[0].upper()}-{tail}"


def _s3_agency(docket: str) -> str:
    return _normalize_docket_id(docket).split("-")[0]


def _s3_key_exists(prefix: str) -> bool:
    resp = _s3().list_objects_v2(Bucket=S3_BUCKET, Prefix=prefix, MaxKeys=1)
    return "Contents" in resp and len(resp["Contents"]) > 0


def _s3_download_file(s3_key: str, local_path: str) -> None:
    os.makedirs(os.path.dirname(local_path), exist_ok=True)
    _s3().download_file(S3_BUCKET, s3_key, local_path)


def _s3_get_file_list(prefix: str, label: Optional[str] = None) -> Tuple[List[Dict[str, Any]], int]:
    files: List[Dict[str, Any]] = []
    paginator = _s3().get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=S3_BUCKET, Prefix=prefix):
        for obj in page.get("Contents", []):
            files.append({"Key": obj["Key"], "Size": obj["Size"]})
        if label:
            print(f"{label}: {len(files)}", end="\r", flush=True)
    if label:
        print(f"{label}: {len(files)}")
    total_size = sum(f["Size"] for f in files)
    return files, total_size


def _s3_rel_path(s3_key: str, base_prefix: str) -> str:
    return os.path.relpath(s3_key, base_prefix)


def _eta_line(done: int, total: int, elapsed: float) -> str:
    rate = done / elapsed if elapsed > 0 else 0
    remain = total - done
    eta = (remain / rate) if rate > 0 else float("inf")
    if eta == float("inf"):
        return "  N/A "
    return f"{int(eta // 60):2d}m{int(eta % 60):02d}s"


def _s3_print_stats(stats: dict, totals: dict, start_times: dict) -> None:
    text_done = (
        stats["docket"] + stats["documents"] + stats["comments"] + stats.get("derived", 0)
    )
    elapsed = time.time() - start_times["text"]
    text_eta = _eta_line(text_done, totals["text"], elapsed)
    output = f"Text: {text_done:6}/{totals['text']:6} ETA:{text_eta:7}"
    if "binary" in stats:
        bin_done = stats["binary"]
        if start_times["binary"] is None and bin_done > 0:
            start_times["binary"] = time.time()
        elapsed_bin = (time.time() - start_times["binary"]) if start_times["binary"] else 0
        bin_eta = _eta_line(bin_done, totals["binary"], elapsed_bin)
        output += f" | Bin: {bin_done:6}/{totals['binary']:6} ETA:{bin_eta:7}"
    print(f"\r{output.ljust(80)}", end="", flush=True)


def _s3_download_worker(
    q: queue.Queue,
    stats: dict,
    totals: dict,
    start_times: dict,
    base_prefix: dict,
    output_folder: str,
) -> None:
    while True:
        item = q.get()
        if item is None:
            break
        s3_key, file_type, _size = item
        rel_path = _s3_rel_path(s3_key, base_prefix[file_type])
        if file_type in ("docket", "documents", "comments", "binary"):
            local_path = os.path.join(output_folder, "raw-data", rel_path)
        elif file_type == "derived":
            local_path = os.path.join(output_folder, "derived-data", rel_path)
        else:
            local_path = os.path.join(output_folder, rel_path)
        try:
            _s3_download_file(s3_key, local_path)
            if file_type in stats:
                stats[file_type] += 1
        except Exception as e:  # pylint: disable=broad-except
            print(f"\nError downloading {s3_key}: {e}", file=sys.stderr)
            sys.exit(1)
        stats["remaining"][file_type] -= 1
        _s3_print_stats(stats, totals, start_times)
        q.task_done()


def download_docket_from_s3(
    docket_id: str,
    output_folder: str = ".",
    include_binary: bool = False,
    no_comments: bool = False,
) -> Path:
    """
    Download mirrulations S3 data into ``{output_folder}/{docket_id}/``.
    ``no_comments=True``: skip ``comments/`` and derived data.
    """
    docket_id = _normalize_docket_id(docket_id)
    agency = _s3_agency(docket_id)
    raw_agency = f"{RAW_DATA_PREFIX}/{agency}/{docket_id}/"
    text_base = f"{raw_agency}text-{docket_id}/"
    raw_binary_prefix = f"{RAW_DATA_PREFIX}/{agency}/{docket_id}/binary-{docket_id}/"
    derived_prefix = f"{DERIVED_DATA_PREFIX}/{agency}/{docket_id}/"

    if not _s3_key_exists(raw_agency):
        log.error("No data at s3://%s/%s — check docket id / casing.", S3_BUCKET, raw_agency)
        log.error("Expected: raw-data/<AGENCY>/<DOCKET-ID>/ (e.g. FAA-2025-0618).")
        sys.exit(1)
    if not _s3_key_exists(text_base):
        log.error(
            "No text bundle at s3://%s/%s (need text-%s/ under the docket folder).",
            S3_BUCKET,
            text_base,
            docket_id,
        )
        sys.exit(1)

    docket_root = Path(output_folder).resolve() / docket_id
    docket_root_str = str(docket_root)

    print("Preparing download lists...")
    file_lists: Dict[str, List] = {}
    total_sizes: Dict[str, int] = {}

    file_lists["docket"], total_sizes["docket"] = _s3_get_file_list(f"{text_base}docket/", "docket")
    print(f"Docket total size:   {total_sizes['docket']/1e6:.2f} MB")

    file_lists["documents"], total_sizes["documents"] = _s3_get_file_list(
        f"{text_base}documents/", "documents"
    )
    print(f"Document total size: {total_sizes['documents']/1e6:.2f} MB")

    if no_comments:
        file_lists["comments"], total_sizes["comments"] = [], 0
        print("Comments: skipped (--skip-comments-download)")
    else:
        file_lists["comments"], total_sizes["comments"] = _s3_get_file_list(
            f"{text_base}comments/", "comments"
        )
        print(f"Comment total size:  {total_sizes['comments']/1e6:.2f} MB")

    if no_comments:
        print("Derived data: skipped (no comments download)")
    elif _s3_key_exists(derived_prefix):
        file_lists["derived"], total_sizes["derived"] = _s3_get_file_list(derived_prefix, "derived")
        print(f"Derived total size:  {total_sizes['derived']/1e6:.2f} MB")
    else:
        print("Derived data not found - skipping")

    if include_binary and _s3_key_exists(raw_binary_prefix):
        file_lists["binary"], total_sizes["binary"] = _s3_get_file_list(raw_binary_prefix, "binary")
        print(f"Binary total size:   {total_sizes['binary']/1e6:.2f} MB")

    totals: Dict[str, int] = {
        "text": len(file_lists["docket"]) + len(file_lists["documents"]) + len(file_lists["comments"])
    }
    if "derived" in file_lists:
        totals["text"] += len(file_lists["derived"])

    stats = {
        "docket": 0,
        "documents": 0,
        "comments": 0,
        "remaining": {k: len(v) for k, v in file_lists.items()},
    }
    if "derived" in file_lists:
        stats["derived"] = 0
    start_times: Dict[str, Any] = {"text": time.time(), "binary": None}
    if "binary" in file_lists:
        totals["binary"] = len(file_lists["binary"])
        stats["binary"] = 0

    base_prefix = {
        "docket": text_base,
        "documents": text_base,
        "comments": text_base,
        "binary": f"{RAW_DATA_PREFIX}/{agency}/{docket_id}/",
        "derived": derived_prefix,
    }

    q: queue.Queue = queue.Queue()
    for file_type, files in file_lists.items():
        for f in files:
            q.put((f["Key"], file_type, f["Size"]))

    n_threads = min(8, max(1, q.qsize() or 1))
    threads = [
        threading.Thread(
            target=_s3_download_worker,
            args=(q, stats, totals, start_times, base_prefix, docket_root_str),
        )
        for _ in range(n_threads)
    ]
    for t in threads:
        t.start()
    q.join()
    for _ in threads:
        q.put(None)
    for t in threads:
        t.join()
    print("\nS3 download finished.")
    print(f"Files for {docket_id} → {docket_root}")
    return docket_root


# ---------------------------------------------------------------------------
# SQL + mapping
# ---------------------------------------------------------------------------

DOCKET_COLS = [
    "docket_id",
    "docket_api_link",
    "agency_id",
    "docket_category",
    "docket_type",
    "effective_date",
    "flex_field1",
    "flex_field2",
    "modify_date",
    "organization",
    "petition_nbr",
    "program",
    "rin",
    "short_title",
    "flex_subtype1",
    "flex_subtype2",
    "docket_title",
    "docket_abstract",
]

COMMENT_COLS = [
    "comment_id", "api_link", "document_id", "duplicate_comment_count",
    "address1", "address2", "agency_id", "city", "comment_category", "comment",
    "country", "docket_id", "document_type", "email", "fax",
    "flex_field1", "flex_field2", "first_name",
    "submitter_gov_agency", "submitter_gov_agency_type",
    "last_name", "modification_date", "submitter_org", "phone",
    "posted_date", "postmark_date", "reason_withdrawn", "received_date",
    "restriction_reason", "restriction_reason_type",
    "state_province_region", "comment_subtype", "comment_title",
    "is_withdrawn", "postal_code",
]


def _upsert_sql(table: str, columns: list[str], pk: str) -> str:
    cols = ", ".join(columns)
    updates = ", ".join(f"{c} = EXCLUDED.{c}" for c in columns if c != pk)
    return (
        f"INSERT INTO {table} ({cols})\nVALUES %s\nON CONFLICT ({pk}) DO UPDATE SET\n{updates}"
    )


DOCKET_UPSERT_SQL = _upsert_sql("dockets", DOCKET_COLS, "docket_id")
DOCUMENT_UPSERT_SQL = _upsert_sql("documentsWithFRdoc", DOC_COLS, "document_id")
COMMENT_UPSERT_SQL = _upsert_sql("comments", COMMENT_COLS, "comment_id")

# Added in newer ``schema-postgres.sql``; older DBs lack these but ``DOC_COLS`` always supplies them.
_DOCUMENT_TABLE_OPTIONAL_COLUMNS: tuple[tuple[str, str], ...] = (
    ("attachments_self_link", "VARCHAR(2000)"),
    ("attachments_related_link", "VARCHAR(2000)"),
    ("file_formats", "JSONB"),
    ("display_properties", "JSONB"),
)


def extract_self_link(data: dict) -> str | None:
    links = data.get("links")
    if isinstance(links, dict):
        return links.get("self")
    if isinstance(links, list) and links:
        first = links[0]
        if isinstance(first, dict):
            return first.get("self")
    return None


def map_docket(payload: dict) -> dict[str, Any] | None:
    try:
        data = payload["data"]
        attr = data["attributes"]
    except (KeyError, TypeError):
        return None

    did = data.get("id")
    if not did:
        return None

    modify = attr.get("modifyDate")
    dtype = attr.get("docketType")
    agency = attr.get("agencyId")
    if not modify or not dtype or not agency:
        return None

    self_link = extract_self_link(data)
    api_link = self_link or f"https://api.regulations.gov/v4/dockets/{did}"

    return {
        "docket_id": did,
        "docket_api_link": api_link,
        "agency_id": agency,
        "docket_category": attr.get("category"),
        "docket_type": dtype,
        "effective_date": attr.get("effectiveDate"),
        "flex_field1": attr.get("field1"),
        "flex_field2": attr.get("field2"),
        "modify_date": modify,
        "organization": attr.get("organization"),
        "petition_nbr": attr.get("petitionNbr"),
        "program": attr.get("program"),
        "rin": attr.get("rin"),
        "short_title": attr.get("shortTitle"),
        "flex_subtype1": attr.get("subType"),
        "flex_subtype2": attr.get("subType2"),
        "docket_title": attr.get("title"),
        "docket_abstract": attr.get("dkAbstract"),
    }


def map_document_safe(raw: dict) -> dict[str, Any] | None:
    doc = map_document(raw)
    if not doc:
        return None
    dt = doc.get("document_type")
    if isinstance(dt, str) and len(dt) > 30:
        doc["document_type"] = dt[:30]
    return doc


def extract_comment(data: dict) -> dict[str, Any]:
    attrs = data.get("attributes", {})
    links = data.get("links", {})
    return {
        "comment_id": data.get("id"),
        "api_link": links.get("self"),
        "document_id": attrs.get("commentOnDocumentId"),
        "duplicate_comment_count": attrs.get("duplicateComments", 0) or 0,
        "address1": attrs.get("address1"),
        "address2": attrs.get("address2"),
        "agency_id": attrs.get("agencyId"),
        "city": attrs.get("city"),
        "comment_category": attrs.get("category"),
        "comment": attrs.get("comment"),
        "country": attrs.get("country"),
        "docket_id": attrs.get("docketId"),
        "document_type": attrs.get("documentType"),
        "email": attrs.get("email"),
        "fax": attrs.get("fax"),
        "flex_field1": attrs.get("field1"),
        "flex_field2": attrs.get("field2"),
        "first_name": attrs.get("firstName"),
        "submitter_gov_agency": attrs.get("govAgency"),
        "submitter_gov_agency_type": attrs.get("govAgencyType"),
        "last_name": attrs.get("lastName"),
        "modification_date": attrs.get("modifyDate"),
        "submitter_org": attrs.get("organization"),
        "phone": attrs.get("phone"),
        "posted_date": attrs.get("postedDate"),
        "postmark_date": attrs.get("postmarkDate"),
        "reason_withdrawn": attrs.get("reasonWithdrawn"),
        "received_date": attrs.get("receiveDate"),
        "restriction_reason": attrs.get("restrictReason"),
        "restriction_reason_type": attrs.get("restrictReasonType"),
        "state_province_region": attrs.get("stateProvinceRegion"),
        "comment_subtype": attrs.get("subtype"),
        "comment_title": attrs.get("title"),
        "is_withdrawn": attrs.get("withdrawn", False) or False,
        "postal_code": attrs.get("zip"),
    }


def _row_tuple(record: dict, columns: list[str]) -> tuple:
    return tuple(record[c] for c in columns)


_REQUIRED_PUBLIC_TABLES = frozenset({"dockets", "documentswithfrdoc", "comments"})


def _require_ingest_schema(conn, args: argparse.Namespace) -> None:
    """Fail fast if ``schema-postgres.sql`` was not applied (common cause of UndefinedTable)."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT lower(table_name) FROM information_schema.tables
            WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
            """
        )
        have = {r[0] for r in cur.fetchall()}
    missing = sorted(_REQUIRED_PUBLIC_TABLES - have)
    if missing:
        log.error(
            "Database %r is missing required table(s): %s.\n"
            "From the project root, load the schema (creates documentsWithFRdoc, etc.):\n"
            "  psql -h %s -p %s -U %s -d %s -f db/schema-postgres.sql",
            args.dbname,
            ", ".join(missing),
            args.host,
            args.port,
            args.user,
            args.dbname,
        )
        sys.exit(1)


def _ensure_documentswithfrdoc_columns(conn) -> None:
    """Add document columns from current ``schema-postgres.sql`` if the table predates them."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT column_name FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = 'documentswithfrdoc'
            """
        )
        have = {r[0].lower() for r in cur.fetchall()}

    modified = False
    with conn.cursor() as cur:
        for col, typ in _DOCUMENT_TABLE_OPTIONAL_COLUMNS:
            if col.lower() in have:
                continue
            log.info("Adding missing column documentsWithFRdoc.%s (%s).", col, typ)
            cur.execute(f"ALTER TABLE documentsWithFRdoc ADD COLUMN {col} {typ}")
            modified = True
    if modified:
        conn.commit()


def _ensure_comments_document_fk(conn) -> None:
    """
    Legacy DBs may have ``comments.document_id`` referencing ``documents`` while ingest writes to
    ``documentsWithFRdoc``. Drop the wrong FK and attach to ``documentsWithFRdoc`` (matches
    ``schema-postgres.sql``). Idempotent.
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT c.conname, pg_get_constraintdef(c.oid, true)
            FROM pg_constraint c
            JOIN pg_class t ON t.oid = c.conrelid
            JOIN pg_namespace n ON n.oid = t.relnamespace
            WHERE n.nspname = 'public' AND t.relname = 'comments' AND c.contype = 'f'
            """
        )
        rows = cur.fetchall()

    has_fr = False
    drop_names: list[str] = []
    for conname, defn in rows:
        compact = defn.lower().replace(" ", "")
        if "foreignkey(document_id)" not in compact:
            continue
        if "documentswithfrdoc" in defn.lower():
            has_fr = True
            continue
        drop_names.append(conname)

    if not drop_names and has_fr:
        return

    with conn.cursor() as cur:
        for conname in drop_names:
            log.info(
                "Updating comments FK: dropping %s (referenced legacy table ``documents``).",
                conname,
            )
            cur.execute(f'ALTER TABLE comments DROP CONSTRAINT "{conname}"')
        if not has_fr:
            try:
                cur.execute(
                    """
                    ALTER TABLE comments
                    ADD CONSTRAINT comments_document_id_fkey
                    FOREIGN KEY (document_id) REFERENCES documentsWithFRdoc (document_id)
                    """
                )
                log.info(
                    "Added FK comments.document_id → documentsWithFRdoc.document_id."
                )
            except psycopg2.errors.DuplicateObject:
                pass
    conn.commit()


def _fk_id_sets(conn) -> tuple[set[str], set[str]]:
    with conn.cursor() as cur:
        cur.execute("SELECT document_id FROM documentsWithFRdoc;")
        docs = {r[0] for r in cur.fetchall()}
        cur.execute("SELECT docket_id FROM dockets;")
        dockets = {r[0] for r in cur.fetchall()}
    return docs, dockets


def _batch_write(
    conn: Any,
    sql: str,
    batch: list[tuple],
    dry_run: bool,
    label: str,
    log_each: bool = True,
) -> int:
    if not batch:
        return 0
    if dry_run:
        log.info("[DRY RUN] Would upsert %d %s row(s).", len(batch), label)
        return len(batch)
    with conn.cursor() as cur:
        execute_values(cur, sql, batch)
    conn.commit()
    if log_each:
        log.info("Upserted %d %s row(s).", len(batch), label)
    return len(batch)


def load_raw_json(path: Path) -> dict | None:
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (json.JSONDecodeError, OSError) as exc:
        log.warning("Skipping %s — %s", path, exc)
        return None


def _paths(docket_dir: Path, sub: str) -> list[Path]:
    pattern = str(docket_dir / "raw-data" / sub / "*.json")
    return sorted(Path(p) for p in glob.glob(pattern))


def ingest_docket_and_documents(
    docket_dir: Path,
    conn,
    dry_run: bool = False,
    verbose: bool = False,
) -> tuple[bool, int, int, str | None]:
    docket_paths = _paths(docket_dir, "docket")
    doc_paths = _paths(docket_dir, "documents")

    docket_row: dict[str, Any] | None = None
    for path in docket_paths:
        raw = load_raw_json(path)
        if not raw:
            continue
        row = map_docket(raw)
        if row:
            docket_row = row
            break

    if not docket_row:
        log.error(
            "No valid docket JSON under %s/raw-data/docket/ (need regulations.gov v4 export).",
            docket_dir,
        )
        return False, 0, len(doc_paths), None

    if dry_run:
        log.info("[DRY RUN] Would upsert docket %s", docket_row["docket_id"])
    else:
        tup = tuple(docket_row[c] for c in DOCKET_COLS)
        with conn.cursor() as cur:
            execute_values(cur, DOCKET_UPSERT_SQL, [tup])
        conn.commit()
        if verbose:
            log.info("Upserted docket %s", docket_row["docket_id"])

    batch: list[tuple] = []
    skipped = 0
    upserted = 0

    for path in doc_paths:
        raw = load_raw_json(path)
        if raw is None:
            skipped += 1
            continue
        doc = map_document_safe(raw)
        if not doc:
            log.warning("Skipping %s — could not map document.", path.name)
            skipped += 1
            continue
        batch.append(_row_tuple(doc, DOC_COLS))
        if len(batch) >= BATCH_SIZE:
            upserted += _batch_write(conn, DOCUMENT_UPSERT_SQL, batch, dry_run, "document", log_each=False)
            batch.clear()

    upserted += _batch_write(conn, DOCUMENT_UPSERT_SQL, batch, dry_run, "document", log_each=False)

    if verbose and upserted:
        log.info("Upserted %d document(s).", upserted)

    return True, upserted, skipped, docket_row["docket_id"]


def _fetch_db_summary(conn, docket_id: str) -> tuple[str | None, int, int, list[str]]:
    """Return (docket_title, doc_count, comment_count, up_to_5_document_titles)."""
    with conn.cursor() as cur:
        cur.execute("SELECT docket_title FROM dockets WHERE docket_id = %s", (docket_id,))
        row = cur.fetchone()
        title = row[0] if row else None
        cur.execute(
            "SELECT COUNT(*) FROM documentsWithFRdoc WHERE docket_id = %s",
            (docket_id,),
        )
        n_docs = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM comments WHERE docket_id = %s", (docket_id,))
        n_comments = cur.fetchone()[0]
        cur.execute(
            """
            SELECT document_title FROM documentsWithFRdoc
            WHERE docket_id = %s AND document_title IS NOT NULL AND TRIM(document_title) <> ''
            ORDER BY document_id
            LIMIT 5
            """,
            (docket_id,),
        )
        titles: list[str] = []
        for (t,) in cur.fetchall():
            if not t:
                continue
            s = str(t).strip()
            if len(s) > 90:
                s = s[:87] + "..."
            titles.append(s)
    return title, n_docs, n_comments, titles


def _ingest_summary(
    docket_dir: Path,
    docket_id: str | None,
    conn: Any,
    *,
    dry_run: bool,
    skip_comments_ingest: bool,
    verbose: bool = False,
) -> None:
    if not docket_id:
        return
    if dry_run:
        title = None
        for path in _paths(docket_dir, "docket"):
            raw = load_raw_json(path)
            if raw:
                row = map_docket(raw)
                if row:
                    title = row.get("docket_title")
                    break
        n_df = len(_paths(docket_dir, "documents"))
        n_cf = len(_paths(docket_dir, "comments"))
        log.info("Docket: %s", docket_id)
        log.info("Title: %s", title or "—")
        log.info(
            "Local JSON files: %d document(s), %d comment(s) (dry run — nothing written to DB)",
            n_df,
            n_cf,
        )
        if skip_comments_ingest:
            log.info("Comments ingest skipped (--skip-comments-ingest).")
        return

    assert conn is not None
    if verbose:
        title, n_docs, n_comments, doc_titles = _fetch_db_summary(conn, docket_id)
        log.info("Docket: %s", docket_id)
        log.info("Title: %s", title or "—")
        log.info("In database: %d document(s), %d comment(s) for this docket_id", n_docs, n_comments)
        if doc_titles:
            log.info("Sample document titles:")
            for i, t in enumerate(doc_titles, 1):
                log.info("  %d. %s", i, t)
        if skip_comments_ingest:
            log.info("Comments were not ingested (--skip-comments-ingest).")


_COMMENT_REQUIRED = (
    "comment_id",
    "api_link",
    "agency_id",
    "document_type",
    "posted_date",
)


def ingest_comments(
    docket_dir: Path,
    conn,
    dry_run: bool = False,
    verbose: bool = False,
) -> tuple[int, int]:
    files = _paths(docket_dir, "comments")
    if not files:
        log.info(
            "No comment JSON under %s/raw-data/comments/ — skipping comments ingest.",
            docket_dir,
        )
        return 0, 0
    if verbose:
        log.info("Found %d comment JSON file(s).", len(files))
    valid_doc_ids: set[str] = set()
    valid_docket_ids: set[str] = set()
    if not dry_run and conn is not None:
        valid_doc_ids, valid_docket_ids = _fk_id_sets(conn)
        if verbose:
            log.info(
                "FK check: %d document_id(s), %d docket_id(s) in DB.",
                len(valid_doc_ids),
                len(valid_docket_ids),
            )

    batch: list[tuple] = []
    skipped = 0
    nulled_doc = 0
    nulled_docket = 0
    upserted = 0

    for path in files:
        payload = load_raw_json(path)
        if not isinstance(payload, dict):
            skipped += 1
            continue
        data = payload.get("data")
        if data is None:
            skipped += 1
            continue

        record = extract_comment(data)
        missing = [c for c in _COMMENT_REQUIRED if not record.get(c)]
        if missing:
            log.warning("Skipping %s — missing required fields: %s", path.name, missing)
            skipped += 1
            continue

        doc_id = record.get("document_id")
        if doc_id and not dry_run and doc_id not in valid_doc_ids:
            log.warning(
                "%s: document_id %r not in documentsWithFRdoc — setting NULL.",
                path.name,
                doc_id,
            )
            record["document_id"] = None
            nulled_doc += 1

        dk = record.get("docket_id")
        if dk and not dry_run and dk not in valid_docket_ids:
            log.warning("%s: docket_id %r not in dockets — setting NULL.", path.name, dk)
            record["docket_id"] = None
            nulled_docket += 1

        batch.append(_row_tuple(record, COMMENT_COLS))
        if len(batch) >= BATCH_SIZE:
            upserted += _batch_write(conn, COMMENT_UPSERT_SQL, batch, dry_run, "comment", log_each=False)
            batch.clear()

    upserted += _batch_write(conn, COMMENT_UPSERT_SQL, batch, dry_run, "comment", log_each=False)

    if nulled_doc:
        log.info(
            "%d comment(s) had document_id set to NULL (missing documentsWithFRdoc row).",
            nulled_doc,
        )
    if nulled_docket:
        log.info("%d comment(s) had docket_id set to NULL (missing dockets row).", nulled_docket)

    return len(files) - skipped, skipped


def _has_local_docket_or_docs(docket_dir: Path) -> bool:
    return bool(_paths(docket_dir, "docket")) or bool(_paths(docket_dir, "documents"))


def _ddir_from_docket_id(did: str, args: argparse.Namespace) -> Path:
    """``OUTPUT_FOLDER/DOCKET-ID/``; download from S3 if missing local docket/document JSON."""
    ddir = Path(args.output_folder).resolve() / did
    if args.download_only or not _has_local_docket_or_docs(ddir):
        if args.download_only:
            log.info("Downloading from S3 (--download-only)…")
        else:
            log.info("No docket/document JSON under %s — downloading from S3…", ddir)
        download_docket_from_s3(
            did,
            output_folder=args.output_folder,
            include_binary=args.include_binary,
            no_comments=args.s3_no_comments,
        )
    return ddir


def _resolve_docket_directory(args: argparse.Namespace) -> Path:
    """Return path to ``.../DOCKET-ID/`` after optional S3 download."""
    if args.download_s3:
        did = _normalize_docket_id(args.download_s3)
        if did != args.download_s3.strip():
            log.info("Normalized docket id for S3: %s", did)
        download_docket_from_s3(
            did,
            output_folder=args.output_folder,
            include_binary=args.include_binary,
            no_comments=args.s3_no_comments,
        )
        return Path(args.output_folder).resolve() / did

    if args.docket_dir:
        return Path(args.docket_dir).expanduser().resolve()

    if not sys.stdin.isatty():
        log.error(
            "This mode requires an interactive terminal to enter a docket ID. "
            "Use --download-s3 DOCKET_ID or --docket-dir PATH for scripts/CI (see --help)."
        )
        sys.exit(1)

    print("Docket ingest — enter a regulations.gov docket ID.", file=sys.stderr)
    raw = input("Docket ID: ").strip()
    if not raw:
        log.error("Docket ID cannot be empty.")
        sys.exit(1)
    did = _normalize_docket_id(raw)
    if did != raw:
        log.info("Normalized docket ID: %s", did)
    return _ddir_from_docket_id(did, args)


def parse_args():
    p = argparse.ArgumentParser(
        description="Download docket bundle from S3 (optional) and ingest dockets, documents, "
        "and comments into Postgres.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Without --download-s3 or --docket-dir, you are always prompted for a docket ID "
            "(interactive terminal only). Data is stored under OUTPUT_FOLDER/<DOCKET-ID>/ "
            "(default: dockets/<DOCKET-ID>/)."
        ),
    )
    p.set_defaults(s3_no_comments=False)
    p.add_argument(
        "--skip-comments-download",
        action="store_true",
        dest="s3_no_comments",
        help="Do not download comments/ or derived/ from S3 (smaller, faster download).",
    )
    p.add_argument(
        "--skip-comments-ingest",
        action="store_true",
        help="Upsert dockets and documents only; skip loading the comments table.",
    )
    p.add_argument(
        "--download-s3",
        metavar="DOCKET_ID",
        help="Download docket bundle from mirrulations S3 into --output-folder/DOCKET_ID/",
    )
    p.add_argument(
        "--output-folder",
        default="dockets",
        help="Parent directory for S3 download (default: dockets/)",
    )
    p.add_argument(
        "--include-binary",
        action="store_true",
        help="With --download-s3: also download binary-* objects",
    )
    p.add_argument(
        "--download-only",
        action="store_true",
        help="Only S3 download, no database writes",
    )
    p.add_argument(
        "--docket-dir",
        help="Path to folder containing raw-data/docket/ and raw-data/documents/",
    )
    p.add_argument("--host", default=os.getenv("DB_HOST", "localhost"))
    p.add_argument("--port", type=int, default=int(os.getenv("DB_PORT", "5432")))
    p.add_argument("--dbname", default=os.getenv("DB_NAME", os.getenv("PGDATABASE", "mirrulations")))
    p.add_argument(
        "--user",
        default=os.getenv("DB_USER", os.getenv("PGUSER", os.getenv("USER", "postgres"))),
    )
    p.add_argument(
        "--password",
        default=os.getenv("DB_PASSWORD", os.getenv("PGPASSWORD", "")),
    )
    p.add_argument("--dry-run", action="store_true", help="Parse JSON only; no database writes")
    p.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )
    return p.parse_args()


def main():
    if load_dotenv:
        load_dotenv(Path(__file__).resolve().parent.parent / ".env")

    args = parse_args()
    docket_dir = _resolve_docket_directory(args)

    if args.download_only:
        if args.docket_dir:
            log.error("--download-only downloads from S3; omit --docket-dir.")
            sys.exit(1)
        log.info("Download complete (--download-only).")
        return

    if args.dry_run:
        log.info("DRY RUN — no database writes.")
        ok, n_doc, sk, docket_id = ingest_docket_and_documents(docket_dir, conn=None, dry_run=True, verbose=args.verbose)
        pc, cs = (0, 0)
        if ok and not args.skip_comments_ingest:
            pc, cs = ingest_comments(docket_dir, conn=None, dry_run=True, verbose=args.verbose)
        if ok:
            log.info("Documents: %d upserted, %d skipped", n_doc, sk)
            if not args.skip_comments_ingest:
                log.info("Comments: %d processed, %d skipped", pc, cs)
            _ingest_summary(
                docket_dir,
                docket_id,
                None,
                dry_run=True,
                skip_comments_ingest=args.skip_comments_ingest,
                verbose=args.verbose,
            )
        else:
            sys.exit(1)
        return

    log.info("Connecting to PostgreSQL at %s:%d/%s …", args.host, args.port, args.dbname)
    try:
        conn = psycopg2.connect(
            host=args.host,
            port=args.port,
            dbname=args.dbname,
            user=args.user,
            password=args.password or None,
        )
    except psycopg2.OperationalError as exc:
        log.error("Could not connect to database: %s", exc)
        sys.exit(1)
    _require_ingest_schema(conn, args)
    _ensure_documentswithfrdoc_columns(conn)
    _ensure_comments_document_fk(conn)
    try:
        ok, n_doc, sk, docket_id = ingest_docket_and_documents(docket_dir, conn, dry_run=False, verbose=args.verbose)
        pc, cs = (0, 0)
        if ok and not args.skip_comments_ingest:
            pc, cs = ingest_comments(docket_dir, conn, dry_run=False, verbose=args.verbose)
        if ok:
            log.info("Documents: %d upserted, %d skipped", n_doc, sk)
            if not args.skip_comments_ingest:
                log.info("Comments: %d processed, %d skipped", pc, cs)
            _ingest_summary(
                docket_dir,
                docket_id,
                conn,
                dry_run=False,
                skip_comments_ingest=args.skip_comments_ingest,
                verbose=args.verbose,
            )
        else:
            sys.exit(1)
    finally:
        conn.close()

if __name__ == "__main__":
    main()
