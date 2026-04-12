# pylint: disable=too-few-public-methods,unused-argument
"""Tests for OpenSearch merge path in InternalLogic.search()."""
from datetime import date
from typing import List

from mirrsearch.internal_logic import InternalLogic


class _FakeDbMerge:
    def __init__(self, sql_rows, os_hits, by_id_rows):
        self._sql_rows = sql_rows
        self._os_hits = os_hits
        self._by_id_rows = by_id_rows
        self.get_dockets_by_ids_calls = []

    def search(self, query, *args, **kwargs):  # pylint: disable=unused-argument
        return list(self._sql_rows)

    def text_match_terms(self, terms, opensearch_client=None):
        return list(self._os_hits)

    def get_dockets_by_ids(self, docket_ids):
        self.get_dockets_by_ids_calls.append(list(docket_ids))
        return list(self._by_id_rows)

    def get_docket_ids_matching_filters( # pylint: disable=too-many-arguments,too-many-positional-arguments,too-many-branches,too-many-statements,too-many-locals
        self,
        docket_ids: List[str],
        agency: List[str] = None,
        docket_type: str = None,
        start_date: str = None,
        end_date: str = None
        ) -> List[str]:
        """
        Fake version: filters by_id_rows based on criteria.
        Returns IDs that would pass filters.
        """
        # Normalize keys to strings for consistency
        by_id = {str(r["docket_id"]): r for r in self._by_id_rows}
        filtered = []
        for did in docket_ids:
            did = str(did)
            row = by_id.get(did)
            if row is None:
                continue

            # Agency filter (substring match, consistent with expectations)
            if agency:
                row_agency = (row.get("agency_id") or "").lower()
                if not any((a or "").strip().lower() in row_agency for a in agency):
                    continue

            # Docket type filter
            if docket_type:
                if row.get("docket_type") != docket_type:
                    continue

            filtered.append(did)

        return filtered

    def get_docket_document_comment_totals(self, docket_ids, opensearch_client=None):  # pylint: disable=unused-argument
        # Provide deterministic denominators for assertions.
        dids = [str(d) for d in docket_ids]
        totals = {
            "A": {"document_total_count": 10, "comment_total_count": 2},
            "B": {"document_total_count": 4, "comment_total_count": 5},
            "C": {"document_total_count": 7, "comment_total_count": 3},
        }
        return {d: totals[d] for d in dids if d in totals}


def test_search_json_sanitizes_modify_date():
    """Postgres-style date objects become ISO strings for JSON responses."""
    sql_rows = [
        {
            "docket_id": "A",
            "docket_title": "t",
            "cfr_refs": [],
            "modify_date": date(2024, 6, 15),
        },
    ]
    db = _FakeDbMerge(sql_rows, os_hits=[], by_id_rows=[])
    logic = InternalLogic("x", db_layer=db)
    out = logic.search("q", page=1, page_size=10)
    assert out["results"][0]["modify_date"] == "2024-06-15"


def test_merge_opensearch_empty_uses_sql_only_with_match_source():
    db = _FakeDbMerge(
        sql_rows=[{"docket_id": "A", "docket_title": "t", "cfr_refs": []}],
        os_hits=[],
        by_id_rows=[],
    )
    logic = InternalLogic("x", db_layer=db)
    out = logic.search("q", page=1, page_size=10)
    assert len(out["results"]) == 1
    assert out["results"][0]["match_source"] == "title"
    assert out["results"][0]["documentNumerator"] == 0
    assert out["results"][0]["commentNumerator"] == 0
    assert out["results"][0]["documentDenominator"] == 10
    assert out["results"][0]["commentDenominator"] == 2
    assert not db.get_dockets_by_ids_calls



def test_merge_appends_full_text_with_counts_and_order():  # pylint: disable=too-many-statements
    sql_rows = [{"docket_id": "A", "docket_title": "ta", "cfr_refs": []}]
    os_hits = [
        {"docket_id": "A", "document_match_count": 9, "comment_match_count": 1},
        {"docket_id": "B", "document_match_count": 2, "comment_match_count": 3},
        {"docket_id": "C", "document_match_count": 1, "comment_match_count": 0},
    ]
    by_id_rows = [
        {"docket_id": "C", "docket_title": "tc", "cfr_refs": []},
        {"docket_id": "B", "docket_title": "tb", "cfr_refs": []},
    ]
    db = _FakeDbMerge(sql_rows, os_hits, by_id_rows)
    logic = InternalLogic("x", db_layer=db)
    out = logic.search("q", page=1, page_size=10)
    merged = out["results"]
    assert [r["docket_id"] for r in merged] == ["A", "B", "C"]
    assert merged[0]["match_source"] == "title"
    assert merged[0]["documentNumerator"] == 9
    assert merged[0]["commentNumerator"] == 1
    assert merged[0]["documentDenominator"] == 10
    assert merged[0]["commentDenominator"] == 2
    assert merged[1]["match_source"] == "full_text"
    assert merged[1]["documentNumerator"] == 2
    assert merged[1]["commentNumerator"] == 3
    assert merged[1]["documentDenominator"] == 4
    assert merged[1]["commentDenominator"] == 5
    assert merged[2]["match_source"] == "full_text"
    assert merged[2]["documentNumerator"] == 1
    assert merged[2]["documentDenominator"] == 7
    assert db.get_dockets_by_ids_calls == [["B", "C"]]


def test_merge_skips_os_docket_missing_in_postgres():
    sql_rows = [{"docket_id": "A", "docket_title": "ta", "cfr_refs": []}]
    os_hits = [{"docket_id": "B", "document_match_count": 1, "comment_match_count": 0}]
    db = _FakeDbMerge(sql_rows, os_hits, by_id_rows=[])
    logic = InternalLogic("x", db_layer=db)
    out = logic.search("q", page=1, page_size=10)
    assert len(out["results"]) == 1
    assert out["results"][0]["docket_id"] == "A"
    assert out["results"][0]["documentNumerator"] == 0
    assert out["results"][0]["commentNumerator"] == 0
    assert out["results"][0]["documentDenominator"] == 10
    assert out["results"][0]["commentDenominator"] == 2


def test_row_docket_key_accepts_id_for_mocks():
    db = _FakeDbMerge(
        sql_rows=[{"id": 1, "title": "x", "cfr_refs": []}],
        os_hits=[],
        by_id_rows=[],
    )
    logic = InternalLogic("x", db_layer=db)
    out = logic.search("q", page=1, page_size=2)
    assert out["results"][0]["match_source"] == "title"
    assert out["results"][0]["documentNumerator"] == 0
    assert out["results"][0]["commentNumerator"] == 0
    assert out["results"][0]["documentDenominator"] == 0
    assert out["results"][0]["commentDenominator"] == 0


def test_merge_full_text_dropped_when_agency_filter_no_match():
    """OpenSearch-only dockets must satisfy the same agency filter as title search."""
    sql_rows = [{"docket_id": "A", "docket_title": "ta", "cfr_refs": [], "agency_id": "CMS"}]
    os_hits = [
        {"docket_id": "A", "document_match_count": 1, "comment_match_count": 0},
        {"docket_id": "B", "document_match_count": 5, "comment_match_count": 1},
    ]
    by_id_rows = [
        {"docket_id": "B", "docket_title": "tb", "cfr_refs": [], "agency_id": "EPA"},
    ]
    db = _FakeDbMerge(sql_rows, os_hits, by_id_rows)
    logic = InternalLogic("x", db_layer=db)
    out = logic.search("q", agency=["CMS"], page=1, page_size=10)
    assert len(out["results"]) == 1
    assert out["results"][0]["docket_id"] == "A"


def test_merge_full_text_kept_when_agency_filter_matches():
    sql_rows = [{"docket_id": "A", "docket_title": "ta", "cfr_refs": [], "agency_id": "CMS"}]
    os_hits = [
        {"docket_id": "B", "document_match_count": 2, "comment_match_count": 0},
    ]
    by_id_rows = [
        {"docket_id": "B", "docket_title": "tb", "cfr_refs": [], "agency_id": "CMS-FOO"},
    ]
    db = _FakeDbMerge(sql_rows, os_hits, by_id_rows)
    logic = InternalLogic("x", db_layer=db)
    out = logic.search("q", agency=["CMS"], page=1, page_size=10)
    # B ranks above A (higher match counts vs totals from _FakeDbMerge).
    assert [r["docket_id"] for r in out["results"]] == ["B", "A"]


def test_merge_full_text_dropped_when_docket_type_filter_no_match():
    sql_rows = [
        {"docket_id": "A", "docket_title": "ta", "cfr_refs": [], "agency_id": "X",
         "docket_type": "Rulemaking"},
    ]
    os_hits = [{"docket_id": "B", "document_match_count": 1, "comment_match_count": 0}]
    by_id_rows = [
        {"docket_id": "B", "docket_title": "tb", "cfr_refs": [], "agency_id": "X",
         "docket_type": "Notice"},
    ]
    db = _FakeDbMerge(sql_rows, os_hits, by_id_rows)
    logic = InternalLogic("x", db_layer=db)
    out = logic.search("q", docket_type_param="Rulemaking", page=1, page_size=10)
    assert len(out["results"]) == 1
    assert out["results"][0]["docket_id"] == "A"


def test_merge_full_text_dropped_when_cfr_part_filter_no_match():
    sql_rows = [
        {"docket_id": "A", "docket_title": "ta", "cfr_refs": [
            {"title": "Title 42", "cfrParts": {"413": "http://a"}},
        ], "agency_id": "CMS"},
    ]
    os_hits = [{"docket_id": "B", "document_match_count": 1, "comment_match_count": 0}]
    by_id_rows = [
        {"docket_id": "B", "docket_title": "tb", "cfr_refs": [
            {"title": "Title 40", "cfrParts": {"99": "http://b"}},
        ], "agency_id": "CMS"},
    ]
    db = _FakeDbMerge(sql_rows, os_hits, by_id_rows)
    logic = InternalLogic("x", db_layer=db)
    out = logic.search(
        "q",
        cfr_part_param=[{"title": "42 CFR", "part": "413"}],
        page=1,
        page_size=10,
    )
    assert len(out["results"]) == 1
    assert out["results"][0]["docket_id"] == "A"


def test_merge_os_hits_all_title_matches_falls_back_to_title_only():
    """OpenSearch returns hits but none are new vs title search → no get_dockets_by_ids."""
    sql_rows = [{"docket_id": "A", "docket_title": "ta", "cfr_refs": []}]
    os_hits = [{"docket_id": "A", "document_match_count": 9, "comment_match_count": 1}]
    db = _FakeDbMerge(sql_rows, os_hits, by_id_rows=[])
    logic = InternalLogic("x", db_layer=db)
    out = logic.search("q", page=1, page_size=10)
    assert len(out["results"]) == 1
    assert out["results"][0]["match_source"] == "title"
    assert out["results"][0]["documentNumerator"] == 9
    assert out["results"][0]["commentNumerator"] == 1
    assert out["results"][0]["documentDenominator"] == 10
    assert out["results"][0]["commentDenominator"] == 2
    assert not db.get_dockets_by_ids_calls


def test_merge_duplicate_os_hits_for_same_docket_only_fetch_once():
    """Second OpenSearch row with the same docket_id is skipped in _get_new_docket_ids."""
    sql_rows = [{"docket_id": "A", "docket_title": "ta", "cfr_refs": []}]
    os_hits = [
        {"docket_id": "B", "document_match_count": 1, "comment_match_count": 0},
        {"docket_id": "B", "document_match_count": 1, "comment_match_count": 0},
    ]
    by_id_rows = [{"docket_id": "B", "docket_title": "tb", "cfr_refs": []}]
    db = _FakeDbMerge(sql_rows, os_hits, by_id_rows)
    logic = InternalLogic("x", db_layer=db)
    out = logic.search("q", page=1, page_size=10)
    assert db.get_dockets_by_ids_calls == [["B"]]
    b_rows = [r for r in out["results"] if r["docket_id"] == "B"]
    assert len(b_rows) == 1
    assert b_rows[0]["documentNumerator"] == 1


def test_merge_full_text_kept_when_cfr_pattern_filter_matches():
    """Non-dict CFR filter (substring patterns) uses _cfr_part_patterns_match_row."""
    sql_rows = [{"docket_id": "A", "docket_title": "ta", "cfr_refs": [], "agency_id": "CMS"}]
    os_hits = [{"docket_id": "B", "document_match_count": 1, "comment_match_count": 0}]
    by_id_rows = [
        {
            "docket_id": "B",
            "docket_title": "tb",
            "cfr_refs": [{"title": "42", "cfrParts": {"413": "http://x"}}],
            "agency_id": "CMS",
        },
    ]
    db = _FakeDbMerge(sql_rows, os_hits, by_id_rows)
    logic = InternalLogic("x", db_layer=db)
    out = logic.search("q", cfr_part_param=["413"], page=1, page_size=10)
    assert [r["docket_id"] for r in out["results"]] == ["B", "A"]


class _FakeDbCollectionDockets:
    """Minimal db_layer for InternalLogic.get_collection_dockets."""

    def get_collections(self, user_email):  # pylint: disable=unused-argument
        return [{"collection_id": 7, "docket_ids": ["DOCKET-1"]}]

    def get_dockets_by_ids(self, docket_ids):
        return [
            {
                "docket_id": "DOCKET-1",
                "docket_title": "T",
                "cfr_refs": [{"title": "40", "cfrParts": {"99": "u"}}],
                "modify_date": date(2024, 3, 1),
            }
        ]

    def get_docket_document_comment_totals(self, docket_ids, opensearch_client=None):  # pylint: disable=unused-argument
        return {
            "DOCKET-1": {"document_total_count": 5, "comment_total_count": 3}
        }

def test_get_collection_dockets_non_empty_sanitizes_and_paginates():
    """Branch with docket_ids loads rows, sanitizes modify_date, returns slice + pagination."""
    logic = InternalLogic("x", db_layer=_FakeDbCollectionDockets())
    out = logic.get_collection_dockets(7, "user@example.com", page=1, page_size=10)
    assert out["pagination"]["total_results"] == 1
    assert out["pagination"]["total_pages"] == 1
    assert out["results"][0]["modify_date"] == "2024-03-01"
    assert "cfrPart" in out["results"][0]
    assert out["results"][0]["documentDenominator"] == 5
    assert out["results"][0]["commentDenominator"] == 3
