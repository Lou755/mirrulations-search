"""
Tests for the database layer (db.py)

Only tests DBLayer wiring, the postgres branch, and module-level
factory functions. Dummy-data behavior tests live in test_mock.py.
"""
# pylint: disable=redefined-outer-name,protected-access
import pytest
import mirrsearch.db as db_module
from mirrsearch.db import DBLayer, cfr_part_filter_patterns, get_db


# --- DBLayer instantiation ---

def test_db_layer_creation():
    """Test that DBLayer can be instantiated"""
    db = DBLayer()
    assert db is not None
    assert isinstance(db, DBLayer)


def test_db_layer_is_frozen():
    """Test that DBLayer is a frozen dataclass (immutable)"""
    db = DBLayer()
    with pytest.raises(Exception):  # FrozenInstanceError
        db.new_attribute = "test"


def test_db_layer_no_conn_returns_empty():
    """DBLayer with no connection returns empty list from search"""
    db = DBLayer()
    assert db.search("anything") == []


def test_get_agencies_no_conn_returns_empty():
    assert DBLayer().get_agencies() == []


def test_cfr_part_filter_patterns_skips_none_and_blank_parts():
    assert cfr_part_filter_patterns([None, {"part": "  "}, "413"]) == ["413"]


def test_merge_unique_comment_matches_unions_distinct_comment_ids():
    comments = {
        "aggregations": {
            "by_docket": {
                "buckets": [
                    {
                        "key": "D1",
                        "matching_comments": {
                            "by_comment": {"buckets": [{"key": "c1"}]}
                        },
                    }
                ]
            }
        }
    }
    extracted = {
        "aggregations": {
            "by_docket": {
                "buckets": [
                    {
                        "key": "D1",
                        "matching_extracted": {
                            "by_comment": {"buckets": [{"key": "c2"}]}
                        },
                    }
                ]
            }
        }
    }
    assert DBLayer._merge_unique_comment_matches(comments, extracted) == {"D1": 2}


def test_search_with_cfr_dict_applies_exact_docket_filter(monkeypatch):
    """Dict-style CFR filter keeps only dockets returned by exact title+part map."""
    rows = [
        ("DOC-001", "First", "CMS", "Rulemaking", "2024-01-01", "Title 42", "413", "http://a"),
        ("DOC-002", "Second", "EPA", "Rulemaking", "2024-01-01", "Title 40", "40", "http://b"),
    ]
    db = DBLayer(conn=_FakeConn(rows))
    monkeypatch.setattr(DBLayer, "_get_cfr_docket_ids", lambda self, _pairs: {"DOC-002"})

    results = db.search(
        "docket",
        cfr_part_param=[{"title": "42 CFR Parts 413 and 512", "part": "413"}],
    )

    assert [r["docket_id"] for r in results] == ["DOC-002"]


def test_search_with_plain_cfr_string_skips_exact_cfr_lookup(monkeypatch):
    """String-style CFR filters should not invoke exact title+part lookup."""
    db = DBLayer(conn=_FakeConn([]))

    def should_not_call(self, _pairs):
        raise AssertionError("_get_cfr_docket_ids should not run for plain string filters")

    monkeypatch.setattr(DBLayer, "_get_cfr_docket_ids", should_not_call)
    db.search("x", cfr_part_param=["413"])


def test_get_db_returns_dblayer():
    """Test the get_db factory function returns a DBLayer"""
    db = get_db()
    assert isinstance(db, DBLayer)


# --- Fake postgres helpers ---

class _FakeCursor:
    def __init__(self, rows):
        self._rows = rows
        self.executed = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, sql, params=None):
        self.executed.append((sql, params))

    def fetchall(self):
        return self._rows

    def close(self):
        return None


class _FakeConn:
    def __init__(self, rows):
        self.cursor_obj = _FakeCursor(rows)

    def cursor(self):
        return self.cursor_obj

    def commit(self):
        pass

    def close(self):
        return None


def test_get_agencies_with_conn():
    db = DBLayer(conn=_FakeConn([("CMS",), ("EPA",)]))
    assert db.get_agencies() == ["CMS", "EPA"]


# --- _search_dockets_postgres filter tests ---

def test_search_dockets_postgres_agency_filter():
    """Agency filter adds ILIKE clause and wraps value with wildcards"""
    db = DBLayer(conn=_FakeConn([]))
    db._search_dockets_postgres("", agency=["CMS"])
    sql, params = db.conn.cursor_obj.executed[0]
    assert "agency_id ILIKE %s" in sql
    assert params == ["%%", "%CMS%"]


def test_search_dockets_postgres_agency_multi_filter():
    """Multiple agencies produce OR'd ILIKE clauses"""
    db = DBLayer(conn=_FakeConn([]))
    db._search_dockets_postgres("", agency=["CMS", "EPA"])
    sql, params = db.conn.cursor_obj.executed[0]
    assert sql.count("agency_id ILIKE %s") == 2
    assert "%CMS%" in params
    assert "%EPA%" in params


def test_search_dockets_postgres_docket_type_filter():
    """Docket type filter adds exact match clause"""
    db = DBLayer(conn=_FakeConn([]))
    db._search_dockets_postgres("", docket_type_param="Rulemaking")
    sql, params = db.conn.cursor_obj.executed[0]
    assert "d.docket_type = %s" in sql
    assert params == ["%%", "Rulemaking"]


def test_search_dockets_postgres_agency_and_docket_type_filter():
    """Both filters add their clauses and params in order"""
    db = DBLayer(conn=_FakeConn([]))
    db._search_dockets_postgres("renal", docket_type_param="Rulemaking", agency=["CMS"])
    sql, params = db.conn.cursor_obj.executed[0]
    assert "d.docket_type = %s" in sql
    assert "agency_id ILIKE %s" in sql
    assert params == ["%renal%", "Rulemaking", "%CMS%"]


def test_search_dockets_postgres_no_filter_no_extra_clauses():
    """Without filters, SQL has no extra AND clauses beyond docket_title"""
    db = DBLayer(conn=_FakeConn([]))
    db._search_dockets_postgres("abc")
    sql, params = db.conn.cursor_obj.executed[0]
    assert "d.docket_type = %s" not in sql
    assert "agency_id ILIKE %s" not in sql
    assert params == ["%abc%"]


def test_search_dockets_postgres_cfr_filter_from_api_dict():
    """Dict CFR filter applies exact cfrPart = via EXISTS and exact FRD title+part EXISTS."""
    db = DBLayer(conn=_FakeConn([]))
    db._search_dockets_postgres(
        "renal",
        cfr_part_param=[{"title": "42 CFR Parts 413 and 512", "part": "413"}],
    )
    sql, params = db.conn.cursor_obj.executed[0]
    assert "cp3.cfrPart = %s" in sql
    assert "JOIN cfrparts cp3 ON cp3.frdocnum = d3.frdocnum" in sql
    assert "JOIN cfrparts cp2 ON cp2.frdocnum = d2.frdocnum" in sql
    assert "cp2.title = %s" in sql
    assert "cp2.cfrPart = %s" in sql
    assert params == ["%renal%", "413", "42 CFR Parts 413 and 512", "413"]


def test_search_dockets_postgres_cfr_empty_dict_skips_cfr_clause():
    """Dict with empty part does not add CFR SQL (avoids bogus %%dict%% params)."""
    db = DBLayer(conn=_FakeConn([]))
    db._search_dockets_postgres("x", cfr_part_param=[{"title": "t", "part": ""}])
    sql, _params = db.conn.cursor_obj.executed[0]
    assert "cp.cfrPart ILIKE" not in sql


def test_get_opensearch_connection_blank_port_no_crash(monkeypatch):
    """Empty OPENSEARCH_PORT in .env must not raise int('') (was HTTP 500)."""
    monkeypatch.setenv("OPENSEARCH_PORT", "")
    assert db_module.get_opensearch_connection() is not None


def test_opensearch_bucket_size_blank_env_defaults(monkeypatch):
    monkeypatch.setenv("OPENSEARCH_MATCH_DOCKET_BUCKET_SIZE", "")
    assert db_module._opensearch_match_docket_bucket_size() == 50000


def test_opensearch_bucket_size_invalid_env_defaults(monkeypatch):
    monkeypatch.setenv("OPENSEARCH_MATCH_DOCKET_BUCKET_SIZE", "not-a-number")
    assert db_module._opensearch_match_docket_bucket_size() == 50000


def test_opensearch_comment_id_size_blank_env_defaults(monkeypatch):
    monkeypatch.setenv("OPENSEARCH_COMMENT_ID_TERMS_SIZE", "")
    assert db_module._opensearch_comment_id_terms_size() == 65535


def test_get_opensearch_connection_invalid_port_env_defaults(monkeypatch):
    monkeypatch.setenv("OPENSEARCH_PORT", "not-a-port")
    assert db_module.get_opensearch_connection() is not None


def test_get_opensearch_connection_port_out_of_range_defaults(monkeypatch):
    monkeypatch.setenv("OPENSEARCH_PORT", "70000")
    assert db_module.get_opensearch_connection() is not None


def test_search_dockets_postgres_cfr_filter_plain_string():
    db = DBLayer(conn=_FakeConn([]))
    db._search_dockets_postgres("z", cfr_part_param=["413"])
    sql, params = db.conn.cursor_obj.executed[0]
    assert "cp3.cfrPart = %s" in sql
    assert "JOIN cfrparts cp3 ON cp3.frdocnum = d3.frdocnum" in sql
    assert params == ["%z%", "413"]


# --- _search_dockets_postgres tests ---

def test_search_dockets_postgres_empty_results():
    """No rows returns an empty list"""
    db = DBLayer(conn=_FakeConn([]))
    results = db._search_dockets_postgres("anything")
    assert results == []


def test_search_dockets_postgres_single_docket_single_cfr():
    """Single row returns one docket with one cfr_ref"""
    rows = [("DOC-001", "Test Docket", "CMS", "Rulemaking",
             "2024-01-01", "Title 42", "42", "http://link")]
    db = DBLayer(conn=_FakeConn(rows))

    results = db._search_dockets_postgres("test")

    assert len(results) == 1
    assert results[0]["docket_id"] == "DOC-001"
    assert results[0]["docket_title"] == "Test Docket"
    assert results[0]["agency_id"] == "CMS"
    assert results[0]["docket_type"] == "Rulemaking"
    assert results[0]["modify_date"] == "2024-01-01"
    assert len(results[0]["cfr_refs"]) == 1
    assert results[0]["cfr_refs"][0]["title"] == "Title 42"
    assert results[0]["cfr_refs"][0]["cfrParts"] == {"42": "http://link"}


def test_search_dockets_postgres_multiple_cfr_parts_same_title():
    """Multiple rows for same docket+title aggregate cfrParts without duplicates"""
    rows = [
        ("DOC-001", "Test Docket", "CMS", "Rulemaking",
         "2024-01-01", "Title 42", "42", "http://link"),
        ("DOC-001", "Test Docket", "CMS", "Rulemaking",
         "2024-01-01", "Title 42", "43", "http://link"),
    ]
    db = DBLayer(conn=_FakeConn(rows))

    results = db._search_dockets_postgres("test")

    assert len(results) == 1
    cfr_ref = results[0]["cfr_refs"][0]
    assert cfr_ref["title"] == "Title 42"
    assert "42" in cfr_ref["cfrParts"]
    assert "43" in cfr_ref["cfrParts"]
    assert len(cfr_ref["cfrParts"]) == 2


def test_search_dockets_postgres_multiple_titles_same_docket():
    """Multiple cfr titles for the same docket produce multiple cfr_refs"""
    rows = [
        ("DOC-001", "Test Docket", "CMS", "Rulemaking",
         "2024-01-01", "Title 42", "42", "http://link42"),
        ("DOC-001", "Test Docket", "CMS", "Rulemaking",
         "2024-01-01", "Title 45", "45", "http://link45"),
    ]
    db = DBLayer(conn=_FakeConn(rows))

    results = db._search_dockets_postgres("test")

    assert len(results) == 1
    titles = {ref["title"] for ref in results[0]["cfr_refs"]}
    assert titles == {"Title 42", "Title 45"}


def test_search_dockets_postgres_multiple_dockets():
    """Rows for different dockets produce separate docket entries"""
    rows = [
        ("DOC-001", "First Docket", "CMS", "Rulemaking",
         "2024-01-01", "Title 42", "42", "http://a"),
        ("DOC-002", "Second Docket", "EPA", "Rulemaking",
         "2024-02-01", "Title 40", "40", "http://b"),
    ]
    db = DBLayer(conn=_FakeConn(rows))

    results = db._search_dockets_postgres("docket")

    assert len(results) == 2
    ids = {r["docket_id"] for r in results}
    assert ids == {"DOC-001", "DOC-002"}


def test_search_dockets_postgres_none_cfr_fields_ignored():
    """Rows with None title or None cfrPart do not add entries to cfr_refs"""
    rows = [
        ("DOC-001", "Test Docket", "CMS", "Rulemaking", "2024-01-01", None, None, None),
    ]
    db = DBLayer(conn=_FakeConn(rows))

    results = db._search_dockets_postgres("test")

    assert len(results) == 1
    assert results[0]["cfr_refs"] == []


def test_search_dockets_postgres_duplicate_cfr_part_not_repeated():
    """Same cfrPart appearing in multiple rows is only stored once"""
    rows = [
        ("DOC-001", "Test Docket", "CMS", "Rulemaking",
         "2024-01-01", "Title 42", "42", "http://link"),
        ("DOC-001", "Test Docket", "CMS", "Rulemaking",
         "2024-01-01", "Title 42", "42", "http://link"),
    ]
    db = DBLayer(conn=_FakeConn(rows))

    results = db._search_dockets_postgres("test")

    assert results[0]["cfr_refs"][0]["cfrParts"] == {"42": "http://link"}


def test_search_dockets_postgres_query_param_formatting():
    """Query string is wrapped with %...% wildcards in params"""
    db = DBLayer(conn=_FakeConn([]))
    db._search_dockets_postgres("clean air")
    _, params = db.conn.cursor_obj.executed[0]
    assert params == ["%clean air%"]


def test_search_dockets_postgres_empty_query_uses_wildcard():
    """Empty query string results in a %% wildcard param"""
    db = DBLayer(conn=_FakeConn([]))
    db._search_dockets_postgres("")
    _, params = db.conn.cursor_obj.executed[0]
    assert params == ["%%"]


# --- get_dockets_by_ids tests ---

def test_get_dockets_by_ids_no_conn_returns_empty():
    assert DBLayer().get_dockets_by_ids(["DOC-001"]) == []


def test_get_dockets_by_ids_empty_ids_returns_empty():
    db = DBLayer(conn=_FakeConn([]))
    assert db.get_dockets_by_ids([]) == []


def test_get_dockets_by_ids_uses_any_and_reuses_row_shape():
    rows = [("DOC-002", "Other", "EPA", "Rulemaking",
             "2024-02-01", "Title 40", "40", "http://b")]
    db = DBLayer(conn=_FakeConn(rows))
    results = db.get_dockets_by_ids(["DOC-002"])
    sql, params = db.conn.cursor_obj.executed[0]
    assert "d.docket_id = ANY(%s)" in sql
    assert params == (["DOC-002"],)
    assert len(results) == 1
    assert results[0]["docket_id"] == "DOC-002"
    assert results[0]["docket_title"] == "Other"


# --- Factory function tests ---

def test_get_postgres_connection_uses_env_and_dotenv(monkeypatch):
    called = {"dotenv": False}

    def fake_load():
        called["dotenv"] = True

    captured = {}

    def fake_connect(**kwargs):
        captured.update(kwargs)
        return "conn"

    monkeypatch.setattr(db_module, "LOAD_DOTENV", fake_load)
    monkeypatch.setattr(db_module.psycopg2, "connect", fake_connect)
    monkeypatch.setenv("DB_HOST", "dbhost")
    monkeypatch.setenv("DB_PORT", "5433")
    monkeypatch.setenv("DB_NAME", "dbname")
    monkeypatch.setenv("DB_USER", "dbuser")
    monkeypatch.setenv("DB_PASSWORD", "dbpass")

    db = db_module.get_postgres_connection()

    assert isinstance(db, DBLayer)
    assert db.conn == "conn"
    assert called["dotenv"] is True
    assert captured == {
        "host": "dbhost",
        "port": "5433",
        "database": "dbname",
        "user": "dbuser",
        "password": "dbpass",
    }


def test_get_postgres_connection_uses_aws_secrets(monkeypatch):
    """USE_AWS_SECRETS=true uses boto3 to get credentials"""
    fake_creds = {
        "host": "aws-host",
        "port": "5432",
        "db": "aws-db",
        "username": "aws-user",
        "password": "aws-pass",
    }

    class FakeClient:  # pylint: disable=too-few-public-methods
        def get_secret_value(self, **_kwargs):  # pylint: disable=unused-argument
            return {"SecretString": __import__("json").dumps(fake_creds)}

        def describe_secret(self, **_kwargs):  # pylint: disable=unused-argument
            return {}

    fake_boto3 = type("boto3", (), {"client": staticmethod(lambda *a, **kw: FakeClient())})()
    captured = {}

    def fake_connect(**kwargs):
        captured.update(kwargs)
        return "aws-conn"

    monkeypatch.setattr(db_module, "boto3", fake_boto3)
    monkeypatch.setattr(db_module.psycopg2, "connect", fake_connect)
    monkeypatch.setenv("USE_AWS_SECRETS", "true")

    db = db_module.get_postgres_connection()

    assert isinstance(db, DBLayer)
    assert db.conn == "aws-conn"
    assert captured["host"] == "aws-host"
    assert captured["database"] == "aws-db"


def test_get_secrets_from_aws_raises_without_boto3(monkeypatch):
    """_get_secrets_from_aws raises ImportError when boto3 is None"""
    monkeypatch.setattr(db_module, "boto3", None)
    with pytest.raises(ImportError):
        db_module._get_secrets_from_aws()


def test_get_db_uses_postgres_when_env_set(monkeypatch):
    sentinel = DBLayer(conn="conn")
    monkeypatch.setattr(db_module, "get_postgres_connection", lambda: sentinel)

    db = get_db()

    assert db is sentinel


def test_get_opensearch_connection(monkeypatch):
    captured = {}

    def fake_opensearch(**kwargs):
        captured.update(kwargs)
        return "client"

    monkeypatch.setattr(db_module, "OpenSearch", fake_opensearch)

    client = db_module.get_opensearch_connection()

    assert client == "client"
    assert captured["hosts"] == [{"host": "localhost", "port": 9200}]
    assert captured["use_ssl"] is False
    assert captured["verify_certs"] is False
    assert "http_auth" not in captured


def test_get_opensearch_connection_https_and_basic_auth(monkeypatch):
    captured = {}

    def fake_opensearch(**kwargs):
        captured.update(kwargs)
        return "client"

    monkeypatch.setattr(db_module, "OpenSearch", fake_opensearch)
    monkeypatch.setenv("OPENSEARCH_USE_SSL", "true")
    monkeypatch.setenv("OPENSEARCH_USER", "admin")
    monkeypatch.setenv("OPENSEARCH_PASSWORD", "secret")

    client = db_module.get_opensearch_connection()

    assert client == "client"
    assert captured["use_ssl"] is True
    assert captured["verify_certs"] is False
    assert captured["http_auth"] == ("admin", "secret")
    assert captured["hosts"] == [
        {"host": "localhost", "port": 9200, "scheme": "https"},
    ]
    assert captured.get("ssl_assert_hostname") is False


def test_get_opensearch_connection_ssl_implicit_when_credentials_only(monkeypatch):
    """EC2-style .env: user+password but no OPENSEARCH_USE_SSL → HTTPS."""
    captured = {}

    def fake_opensearch(**kwargs):
        captured.update(kwargs)
        return "client"

    monkeypatch.setattr(db_module, "OpenSearch", fake_opensearch)
    monkeypatch.delenv("OPENSEARCH_USE_SSL", raising=False)
    monkeypatch.setenv("OPENSEARCH_USER", "admin")
    monkeypatch.setenv("OPENSEARCH_PASSWORD", "x")

    db_module.get_opensearch_connection()

    assert captured["use_ssl"] is True
    assert captured["hosts"][0].get("scheme") == "https"


def test_get_opensearch_connection_ssl_explicit_off_with_auth(monkeypatch):
    captured = {}

    def fake_opensearch(**kwargs):
        captured.update(kwargs)
        return "client"

    monkeypatch.setattr(db_module, "OpenSearch", fake_opensearch)
    monkeypatch.setenv("OPENSEARCH_USE_SSL", "false")
    monkeypatch.setenv("OPENSEARCH_USER", "admin")
    monkeypatch.setenv("OPENSEARCH_PASSWORD", "x")

    db_module.get_opensearch_connection()

    assert captured["use_ssl"] is False
    assert "scheme" not in captured["hosts"][0]


# --- OpenSearch text_match_terms tests ---

def _fake_os_comment_agg_bucket(docket_key: str, agg_name: str, *comment_ids: str):
    """Build a by_docket bucket with unique commentId terms (mirrors OpenSearch shape)."""
    uniq = sorted(set(comment_ids))
    return {
        "key": docket_key,
        agg_name: {
            "doc_count": len(uniq),
            "by_comment": {"buckets": [{"key": cid} for cid in uniq]},
        },
    }


class _FakeOpenSearch:  # pylint: disable=too-few-public-methods
    """Fake OpenSearch client that returns canned responses for multiple indices"""
    def __init__(self, doc_buckets, comment_buckets, extracted_buckets):
        self.doc_buckets = doc_buckets
        self.comment_buckets = comment_buckets
        self.extracted_buckets = extracted_buckets
        self.searches = []

    def search(self, index, body):
        self.searches.append((index, body))

        if index == "documents":
            return {
                "aggregations": {
                    "by_docket": {
                        "buckets": self.doc_buckets
                    }
                }
            }
        if index == "comments":
            return {
                "aggregations": {
                    "by_docket": {
                        "buckets": self.comment_buckets
                    }
                }
            }
        if index == "comments_extracted_text":
            return {
                "aggregations": {
                    "by_docket": {
                        "buckets": self.extracted_buckets
                    }
                }
            }
        return {"aggregations": {"by_docket": {"buckets": []}}}


def test_text_match_terms_searches_comments_and_extracted():
    """Test text_match_terms searches comments and extracted text"""
    doc_buckets = []
    comment_buckets = [
        _fake_os_comment_agg_bucket(
            "CMS-2025-0240", "matching_comments", "CMS-2025-0240-a", "CMS-2025-0240-b")
    ]
    extracted_buckets = [
        _fake_os_comment_agg_bucket(
            "CMS-2025-0240",
            "matching_extracted",
            "CMS-2025-0240-e1",
            "CMS-2025-0240-e2",
            "CMS-2025-0240-e3",
            "CMS-2025-0240-e4",
        )
    ]

    fake_client = _FakeOpenSearch(doc_buckets, comment_buckets, extracted_buckets)
    db = DBLayer()

    results = db.text_match_terms(["medicare"], opensearch_client=fake_client)

    # Should have searched all three indices
    assert len(fake_client.searches) == 3
    assert fake_client.searches[0][0] == "documents_text"
    assert fake_client.searches[1][0] == "comments"
    assert fake_client.searches[2][0] == "comments_extracted_text"

    assert len(results) == 1
    assert results[0]["docket_id"] == "CMS-2025-0240"
    assert results[0]["comment_match_count"] == 6
    assert results[0]["document_match_count"] == 0


def test_text_match_terms_combines_comment_sources():
    """Comment body and extracted text both count toward comNum."""
    doc_buckets = []
    comment_buckets = [
        _fake_os_comment_agg_bucket("DEA-2024-0059", "matching_comments", "DEA-2024-0059-c1")
    ]
    extracted_buckets = [
        _fake_os_comment_agg_bucket("DEA-2024-0059", "matching_extracted", "DEA-2024-0059-e1")
    ]

    fake_client = _FakeOpenSearch(doc_buckets, comment_buckets, extracted_buckets)
    db = DBLayer()

    results = db.text_match_terms(["cannabis"], opensearch_client=fake_client)

    assert len(results) == 1
    assert results[0]["docket_id"] == "DEA-2024-0059"
    assert results[0]["comment_match_count"] == 2
    assert results[0]["document_match_count"] == 0


def test_text_match_terms_same_comment_id_body_and_extracted_counts_once():
    """Same commentId in commentText and extractedText: counted once in comNum."""
    doc_buckets = []
    comment_buckets = [
        _fake_os_comment_agg_bucket("D1", "matching_comments", "SHARED-COMMENT-ID"),
    ]
    extracted_buckets = [
        _fake_os_comment_agg_bucket("D1", "matching_extracted", "SHARED-COMMENT-ID"),
    ]
    fake_client = _FakeOpenSearch(doc_buckets, comment_buckets, extracted_buckets)
    db = DBLayer()
    results = db.text_match_terms(["x"], opensearch_client=fake_client)
    assert len(results) == 1
    assert results[0]["docket_id"] == "D1"
    assert results[0]["comment_match_count"] == 1
    assert results[0]["document_match_count"] == 0


def test_text_match_terms_multiple_dockets_comments():
    """Test searching comments across multiple dockets"""
    doc_buckets = []
    comment_buckets = [
        _fake_os_comment_agg_bucket(
            "CMS-2025-0240", "matching_comments", "CMS-2025-0240-a", "CMS-2025-0240-b"),
        _fake_os_comment_agg_bucket("DEA-2024-0059", "matching_comments", "DEA-2024-0059-c1"),
    ]
    extracted_buckets = [
        _fake_os_comment_agg_bucket(
            "CMS-2025-0240",
            "matching_extracted",
            "CMS-2025-0240-e1",
            "CMS-2025-0240-e2",
            "CMS-2025-0240-e3",
            "CMS-2025-0240-e4",
        )
    ]

    fake_client = _FakeOpenSearch(doc_buckets, comment_buckets, extracted_buckets)
    db = DBLayer()

    results = db.text_match_terms(["test"], opensearch_client=fake_client)

    assert len(results) == 2

    cms = next(r for r in results if r["docket_id"] == "CMS-2025-0240")
    assert cms["comment_match_count"] == 6
    assert cms["document_match_count"] == 0

    dea = next(r for r in results if r["docket_id"] == "DEA-2024-0059")
    assert dea["comment_match_count"] == 1
    assert dea["document_match_count"] == 0


def test_text_match_terms_uses_filtered_aggregations():
    """Verify the OpenSearch queries use filtered aggregations"""
    fake_client = _FakeOpenSearch([], [], [])
    db = DBLayer()

    db.text_match_terms(["medicare", "medicaid"], opensearch_client=fake_client)

    # Check all three queries were made
    assert len(fake_client.searches) == 3

    # Check comments query structure
    comment_index, comment_body = fake_client.searches[1]
    assert comment_index == "comments"
    assert comment_body["size"] == 0
    assert "aggs" in comment_body
    assert "matching_comments" in comment_body["aggs"]["by_docket"]["aggs"]
    assert "filter" in comment_body["aggs"]["by_docket"]["aggs"]["matching_comments"]
    assert "by_comment" in comment_body["aggs"]["by_docket"]["aggs"]["matching_comments"]["aggs"]

    # Check extracted text query structure
    extracted_index, extracted_body = fake_client.searches[2]
    assert extracted_index == "comments_extracted_text"
    assert "matching_extracted" in extracted_body["aggs"]["by_docket"]["aggs"]
    assert "by_comment" in extracted_body["aggs"]["by_docket"]["aggs"]["matching_extracted"]["aggs"]


def test_text_match_terms_returns_correct_structure():
    """Verify each result has the required fields"""
    doc_buckets = []
    comment_buckets = [
        _fake_os_comment_agg_bucket(
            "TEST-001",
            "matching_comments",
            "T1",
            "T2",
            "T3",
            "T4",
            "T5",
        )
    ]
    extracted_buckets = []

    fake_client = _FakeOpenSearch(doc_buckets, comment_buckets, extracted_buckets)
    db = DBLayer()

    results = db.text_match_terms(["test"], opensearch_client=fake_client)

    assert len(results) == 1
    assert "docket_id" in results[0]
    assert "document_match_count" in results[0]
    assert "comment_match_count" in results[0]
    assert isinstance(results[0]["docket_id"], str)
    assert isinstance(results[0]["document_match_count"], int)
    assert isinstance(results[0]["comment_match_count"], int)


def test_text_match_terms_handles_empty_results():
    """When OpenSearch returns no buckets, return empty list"""
    fake_client = _FakeOpenSearch([], [], [])
    db = DBLayer()

    results = db.text_match_terms(["nonexistent"], opensearch_client=fake_client)

    assert not results


def test_text_match_terms_only_returns_comment_matches():
    """Only dockets with comment match_count > 0 are included"""
    doc_buckets = []
    comment_buckets = [
        _fake_os_comment_agg_bucket("HAS-MATCH", "matching_comments", "H1", "H2", "H3", "H4", "H5"),
        {
            "key": "NO-MATCH",
            "matching_comments": {"doc_count": 0, "by_comment": {"buckets": []}},
        },
    ]
    extracted_buckets = []

    fake_client = _FakeOpenSearch(doc_buckets, comment_buckets, extracted_buckets)
    db = DBLayer()

    results = db.text_match_terms(["test"], opensearch_client=fake_client)

    assert len(results) == 1
    assert results[0]["docket_id"] == "HAS-MATCH"


def test_text_match_terms_docket_only_in_comments():
    """When a docket only has matching comment text"""
    doc_buckets = []
    comment_buckets = [
        _fake_os_comment_agg_bucket(
            "COMMENT-ONLY",
            "matching_comments",
            *[f"C{i}" for i in range(10)],
        )
    ]
    extracted_buckets = []

    fake_client = _FakeOpenSearch(doc_buckets, comment_buckets, extracted_buckets)
    db = DBLayer()

    results = db.text_match_terms(["test"], opensearch_client=fake_client)

    assert len(results) == 1
    assert results[0]["docket_id"] == "COMMENT-ONLY"
    assert results[0]["comment_match_count"] == 10


def test_text_match_terms_malformed_response_returns_empty():
    class BadClient:  # pylint: disable=too-few-public-methods
        def search(self, index, body):  # pylint: disable=unused-argument
            return {}

    db = DBLayer()
    assert db.text_match_terms(["x"], opensearch_client=BadClient()) == []


def test_get_docket_ids_matching_filters():
    """Test lightweight filter query"""
    db = get_db()

    # This test assumes you have some dockets in your test database
    # Get some real docket IDs first
    all_dockets = db.search("")
    if not all_dockets:
        pytest.skip("No dockets in test database")

    docket_ids = [d["docket_id"] for d in all_dockets[:5]]

    # Test with no filters - should return all
    result = db.get_docket_ids_matching_filters(docket_ids)
    assert len(result) > 0

    # Test with agency filter
    if all_dockets[0].get("agency_id"):
        agency = [all_dockets[0]["agency_id"]]
        result = db.get_docket_ids_matching_filters(docket_ids, agency=agency)
        assert isinstance(result, list)
