from dataclasses import dataclass
from typing import List, Dict, Any
import os
import psycopg2
from opensearchpy import OpenSearch

try:
    from dotenv import load_dotenv
except ImportError:
    LOAD_DOTENV = None
else:
    LOAD_DOTENV = load_dotenv


@dataclass(frozen=True)
class DBLayer:
    """
    DB layer for connecting to PostgreSQL and returning data.
    """
    conn: Any = None

    def _items(self) -> List[Dict[str, Any]]:
        return [
            {
                "docket_id": "CMS-2025-0240",
                "title": (
                    "CY 2026 Changes to the End-Stage Renal Disease (ESRD) "
                    "Prospective Payment System and Quality Incentive Program. "
                    "CMS1830-P Display"
                ),
                "cfrPart": "42 CFR Parts 413 and 512",
                "agency_id": "CMS",
                "document_type": "Proposed Rule",
            },
            {
                "docket_id": "CMS-2025-0240",
                "title": (
                    "Medicare Program: End-Stage Renal Disease Prospective "
                    "Payment System, Payment for Renal Dialysis Services "
                    "Furnished to Individuals with Acute Kidney Injury, "
                    "End-Stage Renal Disease Quality Incentive Program, and "
                    "End-Stage Renal Disease Treatment Choices Model"
                ),
                "cfrPart": "42 CFR Parts 413 and 512",
                "agency_id": "CMS",
                "document_type": "Proposed Rule",
            }
        ]

    def search(self, query: str, filter_param: str = None) -> List[Dict[str, Any]]:
        q = (query or "").strip()

        if self.conn is None:
            q = q.lower()
            results = [
                item for item in self._items()
                if q in item["title"].lower() or q in item["docket_id"].lower()
            ]
            if filter_param:
                results = [
                    item for item in results
                     if item["document_type"].lower() == filter_param.lower()
                ]
            return results
        else:
            sql = """
                SELECT docket_id, title, cfr_part, agency_id, document_type
                FROM document
                WHERE (docket_id ILIKE %s OR title ILIKE %s)
            """
            params = [f"%{q}%", f"%{q}%"] if q else ["%%", "%%"]

            if filter_param:
                sql += " AND document_type = %s"
                params.append(filter_param)

            with self.conn.cursor() as cur:
                cur.execute(sql, params)
                rows = cur.fetchall()

            return [
                {
                    "docket_id": row[0],
                    "title": row[1],
                    "cfrPart": row[2],
                    "agency_id": row[3],
                    "document_type": row[4],
                }
                for row in rows
            ]

def get_postgres_connection() -> DBLayer:
    if LOAD_DOTENV is not None:
        LOAD_DOTENV()
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
        database=os.getenv("DB_NAME", "your_db"),
        user=os.getenv("DB_USER", "your_user"),
        password=os.getenv("DB_PASSWORD", "your_password")
    )
    return DBLayer(conn)


def get_db() -> DBLayer:
    """
    Return the default DB layer for the app.
    Currently uses the in-memory dummy data for local/test usage.
    """
    if LOAD_DOTENV is not None:
        LOAD_DOTENV()
    use_postgres = os.getenv("USE_POSTGRES", "").lower() in {"1", "true", "yes", "on"}
    if use_postgres:
        return get_postgres_connection()
    return DBLayer()


def get_opensearch_connection() -> OpenSearch:
    client = OpenSearch(
        hosts=[{"host": "localhost", "port": 9200}],
        use_ssl=False,
        verify_certs=False,
    )
    return client
