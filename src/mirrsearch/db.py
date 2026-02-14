from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import psycopg2
from opensearchpy import OpenSearch 


@dataclass(frozen=True)
class DBLayer:
    """
    DB layer for connecting to PostgreSQL and returning data.
    """
    conn: Any

    def _items(self) -> List[Dict[str, Any]]:
        return [
            {
                "docket_id": "CMS-2025-0240",
                "title": "CY 2026 Changes to the End-Stage Renal Disease (ESRD) Prospective Payment System and Quality Incentive Program. CMS1830-P Display",
                "cfrPart": "42 CFR Parts 413 and 512",
                "agency_id": "CMS",
                "document_type": "Proposed Rule",
            },
            {
                "docket_id": "CMS-2025-0240",
                "title": "Medicare Program: End-Stage Renal Disease Prospective Payment System, Payment for Renal Dialysis Services Furnished to Individuals with Acute Kidney Injury, End-Stage Renal Disease Quality Incentive Program, and End-Stage Renal Disease Treatment Choices Model",
                "cfrPart": "42 CFR Parts 413 and 512",
                "agency_id": "CMS",
                "document_type": "Proposed Rule",
            }
        ]

    def search(self, query: str) -> List[Dict[str, Any]]:
        # Query that matches title or docket_id in the dummy data and returns them
        q = query.lower().strip()
        return [
            item for item in self._items()
            if q in item["title"].lower() or q in item["docket_id"].lower()
        ]

def get_postgres_connection() -> DBLayer:
    conn = psycopg2.connect(
        host="localhost",
        dbname="your_db",
        user="your_user",
        password="your_password"
    )
    return DBLayer(conn)

def get_db() -> DBLayer:
    """
    Return the default DB layer for the app.
    Currently uses the in-memory dummy data for local/test usage.
    """
    return DBLayer(conn=None)

def get_opensearch_connection() -> OpenSearch:
     client = OpenSearch(
         hosts=[{"host": "localhost", "port": 9200}],
         use_ssl=False,
         verify_certs=False,
     )
     return client
