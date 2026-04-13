"""
OpenSearch connection, text_match_terms, filters, and auth-user DB tests.

Companion to test_db.py (keeps each module under pylint max module lines).
"""
# pylint: disable=redefined-outer-name,protected-access
import pytest

from db_test_fakes import _FakeConn

import mirrsearch.db as db_module
from mirrsearch.db import DBLayer, get_db


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

def test_get_docket_ids_matching_filters_no_conn_returns_empty():
    """No DB connection should return empty list immediately"""
    db = DBLayer()
    assert db.get_docket_ids_matching_filters(["D1", "D2"]) == []


def test_get_docket_ids_matching_filters_empty_ids_returns_empty():
    """Empty docket list should short-circuit"""
    db = DBLayer(conn=_FakeConn([]))
    assert db.get_docket_ids_matching_filters([]) == []


def test_get_docket_ids_matching_filters_basic_query():
    """Basic query with only docket_ids returns fetched rows"""

    db = DBLayer(conn=_FakeConn([]))

    # patch fetchall result
    db.conn.cursor_obj.fetchall = lambda: [("D1",), ("D2",)]

    result = db.get_docket_ids_matching_filters(["D1", "D2"])

    sql, params = db.conn.cursor_obj.executed[0]

    assert "SELECT docket_id FROM dockets" in sql
    assert "docket_id = ANY(%s)" in sql
    assert params == [["D1", "D2"]]
    assert result == ["D1", "D2"]


def test_get_docket_ids_matching_filters_agency_filter():
    """Agency filter adds OR ILIKE clauses and params"""

    db = DBLayer(conn=_FakeConn([]))
    db.conn.cursor_obj.fetchall = lambda: []

    db.get_docket_ids_matching_filters(["D1"], agency=["CMS", "EPA"])

    sql, params = db.conn.cursor_obj.executed[0]

    assert sql.count("agency_id ILIKE %s") == 2
    assert "AND (" in sql
    assert "%CMS%" in params
    assert "%EPA%" in params


def test_get_docket_ids_matching_filters_docket_type_filter():
    """Docket type adds exact match clause"""

    db = DBLayer(conn=_FakeConn([]))
    db.conn.cursor_obj.fetchall = lambda: [("D1",)]

    db.get_docket_ids_matching_filters(
        ["D1"], docket_type="Rulemaking"
    )

    sql, params = db.conn.cursor_obj.executed[0]

    assert "docket_type = %s" in sql
    assert "Rulemaking" in params


def test_get_docket_ids_matching_filters_date_filters():
    """Start and end date filters are included correctly"""

    db = DBLayer(conn=_FakeConn([]))
    db.conn.cursor_obj.fetchall = lambda: [("D1",)]

    db.get_docket_ids_matching_filters(
        ["D1"],
        start_date="2024-01-01",
        end_date="2024-12-31",
    )

    sql, params = db.conn.cursor_obj.executed[0]

    assert "modify_date >= %s::TIMESTAMP" in sql
    assert "modify_date <= %s::TIMESTAMP" in sql
    assert "2024-01-01" in params
    assert "2024-12-31" in params


def test_get_docket_ids_matching_filters_combined_filters():
    """All filters together produce full SQL and ordered params"""

    db = DBLayer(conn=_FakeConn([]))
    db.conn.cursor_obj.fetchall = lambda: [("D1",)]

    db.get_docket_ids_matching_filters(
        ["D1", "D2"],
        agency=["CMS"],
        docket_type="Rulemaking",
        start_date="2024-01-01",
    )

    sql, params = db.conn.cursor_obj.executed[0]

    assert "docket_id = ANY(%s)" in sql
    assert "agency_id ILIKE %s" in sql
    assert "docket_type = %s" in sql
    assert "modify_date >= %s::TIMESTAMP" in sql

    # ensure all values are passed
    assert ["D1", "D2"] in params
    assert "%CMS%" in params
    assert "Rulemaking" in params
    assert "2024-01-01" in params


# --- is_admin tests ---

def test_is_admin_no_conn_returns_false():
    assert DBLayer().is_admin("professor@email.com") is False

def test_is_admin_returns_true_when_found():
    db = DBLayer(conn=_FakeConn([(1,)]))
    assert db.is_admin("professor@email.com") is True

def test_is_admin_returns_false_when_not_found():
    db = DBLayer(conn=_FakeConn([]))
    assert db.is_admin("notadmin@email.com") is False


# --- is_authorized_user tests ---

def test_is_authorized_user_no_conn_returns_false():
    assert DBLayer().is_authorized_user("user@email.com") is False

def test_is_authorized_user_returns_true_when_found():
    db = DBLayer(conn=_FakeConn([(1,)]))
    assert db.is_authorized_user("user@email.com") is True

def test_is_authorized_user_returns_false_when_not_found():
    db = DBLayer(conn=_FakeConn([]))
    assert db.is_authorized_user("unknown@email.com") is False


# --- add_authorized_user tests ---

def test_add_authorized_user_no_conn_returns_false():
    assert DBLayer().add_authorized_user("user@email.com", "Test User") is False

def test_add_authorized_user_inserts_and_returns_true():
    db = DBLayer(conn=_FakeConn([]))
    result = db.add_authorized_user("user@email.com", "Test User")
    assert result is True
    sql, params = db.conn.cursor_obj.executed[0]
    assert "INSERT INTO authorized_users" in sql
    assert params == ("user@email.com", "Test User")


# --- remove_authorized_user tests ---

def test_remove_authorized_user_no_conn_returns_false():
    assert DBLayer().remove_authorized_user("user@email.com") is False

def test_remove_authorized_user_returns_true_when_deleted():
    db = DBLayer(conn=_FakeConn([]))
    db.conn.cursor_obj.rowcount = 1
    assert db.remove_authorized_user("user@email.com") is True

def test_remove_authorized_user_returns_false_when_not_found():
    db = DBLayer(conn=_FakeConn([]))
    db.conn.cursor_obj.rowcount = 0
    assert db.remove_authorized_user("nobody@email.com") is False


# --- get_authorized_users tests ---

def test_get_authorized_users_no_conn_returns_empty():
    assert DBLayer().get_authorized_users() == []

def test_get_authorized_users_returns_list():
    rows = [
        ("user1@email.com", "User One", "2026-01-01T00:00:00"),
        ("user2@email.com", "User Two", "2026-01-02T00:00:00"),
    ]
    db = DBLayer(conn=_FakeConn(rows))
    results = db.get_authorized_users()
    assert len(results) == 2
    assert results[0]["email"] == "user1@email.com"
    assert results[0]["name"] == "User One"
    assert results[0]["authorized_at"] == "2026-01-01T00:00:00"
    assert results[1]["email"] == "user2@email.com"

def test_get_authorized_users_empty_table_returns_empty():
    db = DBLayer(conn=_FakeConn([]))
    assert db.get_authorized_users() == []
