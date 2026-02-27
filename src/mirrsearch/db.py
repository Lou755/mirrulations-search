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

    def search(
            self,
            query: str,
            document_type_param: str = None,
            agency:str = None,
            cfr_part_param: str = None) \
            -> List[Dict[str, Any]]:
        if self.conn is None:
            return []

        sql = """
            SELECT d.docket_id, d.document_title, c.cfrpart, d.agency_id, d.document_type
            FROM documents d
            LEFT JOIN cfrparts c ON d.document_id = c.document_id
            WHERE (d.docket_id ILIKE %s OR d.document_title ILIKE %s)
        """
        params = ([f"%{(query or '').strip().lower()}%"] * 2
                  if (query or "").strip()
                  else ["%%", "%%"])

        if document_type_param:
            sql += " AND d.document_type = %s"
            params.append(document_type_param)

        if cfr_part_param:
            sql += " AND c.cfrpart = %s"
            params.append(cfr_part_param)

        if agency:
            sql += " AND d.agency_id ILIKE %s"
            params.append(f"%{agency}%")

        with self.conn.cursor() as cur:
            cur.execute(sql, params)
            return [
                {
                    "docket_id": row[0],
                    "title": row[1],
                    "cfrPart": row[2],
                    "agency_id": row[3],
                    "document_type": row[4],
                }
                for row in cur.fetchall()
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
