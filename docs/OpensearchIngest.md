# How to Ingest Dummy Data into OpenSearch Database

This guide explains how to:
- Create and Activate a virtual environment
- Run OpenSearch locally
- Ingest dummy data
- Verify indexed data

Create/Activate Virtual Environment
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

1. Run OpenSearch Locally

Install OpenSearch via Homebrew (If not done already)
```bash
brew install opensearch
```

Start the OpenSearch Service
```bash
brew services start opensearch
```

Verify OpenSearch Is Running
```bash
curl -X GET "http://localhost:9200/"
```
If running correctly, you should see JSON output confirming the cluster is active.

2. Ingest Dummy Data

```bash
python ingest_docket.py
```
If successful, the script will print:
Ingested X records into OpenSearch.

3. Verify Indexed Data

```bash
curl -X GET "localhost:9200/docket-comments/_search?pretty"
```
If the ingest worked correctly, this command will return JSON containing the indexed documents.

Stop OpenSearch
```bash
brew services stop opensearch
```