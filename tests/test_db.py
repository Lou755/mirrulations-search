"""
Tests for the database layer (db.py)

Only tests DBLayer wiring, the postgres branch, and module-level
factory functions. Dummy-data behavior tests live in test_mock.py.
"""
# pylint: disable=redefined-outer-name,protected-access
import pytest

from db_test_fakes import _FakeConn

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
