from opensearchpy import OpenSearch
from src.mirrsearch.db import get_db

INDEX_NAME = "docket-comments"
DOCKET_ID = "CMS-2025-0240"


def get_opensearch_client():
    return OpenSearch(
        hosts=[{"host": "localhost", "port": 9200}],
        http_compress=True,
        use_ssl=False,
        verify_certs=False,
    )


def create_index_if_not_exists(client):
    if not client.indices.exists(index=INDEX_NAME):
        client.indices.create(index=INDEX_NAME)


def ingest_one_docket(docket_id: str):
    db = get_db()
    client = get_opensearch_client()

    create_index_if_not_exists(client)

    # Search dummy DB for docket
    records = db.search(docket_id)

    for i, record in enumerate(records):
        doc_id = f"{docket_id}-{i}"

        client.index(
            index=INDEX_NAME,
            id=doc_id,
            body=record
        )

    print(f"Ingested {len(records)} records into OpenSearch.")


if __name__ == "__main__":
    ingest_one_docket(DOCKET_ID)
