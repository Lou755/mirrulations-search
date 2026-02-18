#from opensearchpy import OpenSearch 
from dataclasses import dataclass
from typing import List, Dict, Any
import psycopg2
from psycopg2.extras import RealDictCursor

@dataclass(frozen=True)
class DBLayer:
    """
    DB layer for connecting to PostgreSQL and returning data.
    """
    conn: Any

    def search(self, query: str) -> List[Dict[str, Any]]:
        """
        Search documents by query string in title or docket_id.
        """
        q = f"%{query.lower()}%"
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT 
                    docket_id,
                    title,
                    cfr_part as "cfrPart",
                    agency_id,
                    document_type,
                    authors,
                    comment_start_date,
                    comment_end_date,
                    posted_date,
                    modified_date
                FROM document
                WHERE LOWER(title) LIKE %s OR LOWER(docket_id) LIKE %s
            """, (q, q))
            return [dict(row) for row in cur.fetchall()]

    def get_all(self) -> List[Dict[str, Any]]:
        """
        Get all documents from the database.
        """
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT 
                    docket_id,
                    title,
                    cfr_part as "cfrPart",
                    agency_id,
                    document_type,
                    authors,
                    comment_start_date,
                    comment_end_date,
                    posted_date,
                    modified_date
                FROM document
            """)
            return [dict(row) for row in cur.fetchall()]


def get_postgres_connection() -> DBLayer:
    """
    Connect to the PostgreSQL database in dev environment.
    """
    conn = psycopg2.connect(
        host="localhost",
        dbname="mirrulations"
    )
    return DBLayer(conn=conn)



def get_db() -> DBLayer:
    """
    Return the DB layer connected to PostgreSQL.
    """
    return get_postgres_connection()

if __name__ == "__main__":
    try:
        db = get_db()
        print("Database connected successfully!")
        print("\nDocuments in database:")
        
        docs = db.get_all()
        for doc in docs:
            print(f"\n  Docket ID: {doc['docket_id']}")
            print(f"  Title: {doc['title']}")
            print(f"  Agency: {doc['agency_id']}")
            print(f"  Type: {doc['document_type']}")
            
    except Exception as e:
        print(f"Connection failed: {e}")

#def get_opensearch_connection() -> OpenSearch:
    #client = OpenSearch(
     #    hosts=[{"host": "localhost", "port": 9200}],
      #   use_ssl=False,
       #  verify_certs=False,
   #  )
    # return client
