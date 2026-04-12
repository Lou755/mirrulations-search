"""
Tests for MockDBLayer. Verifies that the mock's dummy data and search
behavior are correct. These are the tests that previously lived in
test_db.py but relied on DBLayer._items (which no longer exists).
"""
# pylint: disable=redefined-outer-name
import pytest
from mock_db import MockDBLayer


@pytest.fixture
def db():
    return MockDBLayer()


# --- get_all ---

def test_get_all_returns_list(db):
    assert isinstance(db.get_all(), list)


def test_get_all_returns_two_records(db):
    assert len(db.get_all()) == 2


def test_get_all_have_required_fields(db):
    required_fields = ["docket_id", "title", "cfrPart", "agency_id", "document_type"]
    for item in db.get_all():
        for field in required_fields:
            assert field in item, f"Item missing required field: {field}"


def test_get_all_field_types(db):
    for item in db.get_all():
        assert isinstance(item["docket_id"], str)
        assert isinstance(item["title"], str)
        assert isinstance(item["cfrPart"], str)
        assert isinstance(item["agency_id"], str)
        assert isinstance(item["document_type"], str)


def test_get_all_content(db):
    items = db.get_all()
    assert items[0]["docket_id"] == "CMS-2025-0240"
    assert items[0]["agency_id"] == "CMS"
    assert items[0]["document_type"] == "Proposed Rule"
    assert items[1]["docket_id"] == "CMS-2025-0240"
    assert items[1]["agency_id"] == "CMS"


# --- search ---

def test_search_returns_list(db):
    assert isinstance(db.search("CMS"), list)


def test_search_finds_by_docket_id(db):
    result = db.search("CMS-2025-0240")
    assert len(result) == 2
    assert all(item["docket_id"] == "CMS-2025-0240" for item in result)


def test_search_finds_by_title(db):
    result = db.search("ESRD")
    assert len(result) >= 1
    assert all("ESRD" in item["title"] or "esrd" in item["title"].lower() for item in result)


def test_search_is_case_insensitive(db):
    result_upper = db.search("CMS")
    result_lower = db.search("cms")
    result_mixed = db.search("Cms")
    assert len(result_upper) == len(result_lower) == len(result_mixed)
    assert result_upper == result_lower == result_mixed


def test_search_strips_whitespace(db):
    assert db.search("CMS") == db.search("  CMS  ")


def test_search_partial_match_title(db):
    result = db.search("Medicare")
    assert len(result) >= 1
    assert any("Medicare" in item["title"] for item in result)


def test_search_partial_match_docket(db):
    result = db.search("2025")
    assert len(result) == 2


def test_search_no_results(db):
    result = db.search("nonexistent_query_xyz123")
    assert result == []


def test_search_empty_string_returns_all(db):
    assert len(db.search("")) == 2


def test_search_specific_terms(db):
    assert len(db.search("Prospective Payment System")) >= 1
    assert len(db.search("Quality Incentive")) >= 1


def test_search_multiple_words(db):
    assert len(db.search("End-Stage Renal")) >= 1


def test_search_returns_correct_structure(db):
    for item in db.search("CMS"):
        assert isinstance(item, dict)
        for field in ["docket_id", "title", "cfrPart", "agency_id", "document_type"]:
            assert field in item


def test_search_does_not_modify_original_data(db):
    original = db.get_all()
    db.search("CMS")
    db.search("Medicare")
    db.search("xyz")
    assert db.get_all() == original


def test_search_special_characters(db):
    assert len(db.search("CMS-2025")) == 2


def test_search_numbers_only(db):
    assert len(db.search("2025")) == 2


def test_search_with_parentheses(db):
    assert len(db.search("(ESRD)")) >= 1


# --- filters ---

def test_search_filter_matching_document_type(db):
    result = db.search("renal", "Proposed Rule")
    assert len(result) > 0
    assert all(item["document_type"] == "Proposed Rule" for item in result)


def test_search_filter_nonexistent_document_type(db):
    assert db.search("renal", "Final Rule") == []


def test_search_filter_is_case_insensitive(db):
    lower = db.search("renal", "proposed rule")
    upper = db.search("renal", "PROPOSED RULE")
    mixed = db.search("renal", "Proposed Rule")
    assert lower == upper == mixed


def test_search_agency_filter(db):
    """Agency filter works in dummy branch"""
    result = db.search("", agency=["CMS"])
    assert len(result) == 2
    assert all(item["agency_id"] == "CMS" for item in result)


def test_search_agency_filter_multiple(db):
    """Multiple agency filters return results matching any"""
    result = db.search("", agency=["CMS", "EPA"])
    assert len(result) == 2
    for item in result:
        assert item["agency_id"] in ("CMS", "EPA")


def test_search_agency_filter_no_match(db):
    """Agency filter returns empty when no match"""
    result = db.search("", agency=["FDA"])
    assert result == []


def test_search_cfr_part_filter(db):
    """cfr_part_param filter works in dummy branch"""
    result = db.search("", cfr_part_param=[{"title": "42 CFR Parts 413 and 512", "part": "413"}])
    assert len(result) == 2


def test_search_cfr_part_filter_multiple(db):
    """Multiple cfr_part values return results matching any"""
    result = db.search("", cfr_part_param=[
        {"title": "42 CFR Parts 413 and 512", "part": "413"},
        {"title": "42 CFR Parts 413 and 512", "part": "512"},
    ])
    assert len(result) == 2


def test_search_cfr_part_filter_no_match(db):
    """cfr_part_param returns empty when no match"""
    result = db.search("", cfr_part_param=[{"title": "Title 99", "part": "999"}])
    assert result == []


# --- OpenSearch text_match_terms tests ---

def test_text_match_terms_returns_list(db):
    """Search term returns a list of results"""
    result = db.text_match_terms(["medicare"])
    assert isinstance(result, list)


def test_text_match_terms_structure(db):
    """Results contain correct structure"""
    result = db.text_match_terms(["medicare"])
    for item in result:
        assert set(item.keys()) == {
            "docket_id",
            "document_match_count",
            "comment_match_count"
        }
        assert isinstance(item["docket_id"], str)
        assert isinstance(item["document_match_count"], int)
        assert isinstance(item["comment_match_count"], int)


def test_text_match_terms_finds_drug(db):
    """Find dockets for 'drug'"""
    result = db.text_match_terms(["drug"])

    # Should find CMS-2025-0001 (1 doc)
    assert len(result) == 1

    # CMS-2025-0001: 1 doc with "Drug" in documentText, 0 comments
    cms_2025_0001 = next((r for r in result if r["docket_id"] == "CMS-2025-0001"), None)
    assert cms_2025_0001 is not None
    assert cms_2025_0001["document_match_count"] == 1
    assert cms_2025_0001["comment_match_count"] == 0


def test_text_match_terms_finds_medicare(db):
    """Find dockets for 'medicare'"""
    result = db.text_match_terms(["medicare"])

    # Should find 3 dockets: CMS-2025-0001, CMS-2025-0240, CMS-2019-0100
    assert len(result) == 3

    # CMS-2025-0001: 1 doc with "Medicare" in documentText, 0 comments
    cms_2025_0001 = next((r for r in result if r["docket_id"] == "CMS-2025-0001"), None)
    assert cms_2025_0001 is not None
    assert cms_2025_0001["document_match_count"] == 1
    assert cms_2025_0001["comment_match_count"] == 0

    # CMS-2025-0240: 4 extracted (distinct commentId) → doc; 2 comment bodies → com
    cms_2025 = next((r for r in result if r["docket_id"] == "CMS-2025-0240"), None)
    assert cms_2025 is not None
    assert cms_2025["document_match_count"] == 4
    assert cms_2025["comment_match_count"] == 2

    # CMS-2019-0100: 2 extracted with "medicare"; 4 comment bodies
    cms_2019 = next((r for r in result if r["docket_id"] == "CMS-2019-0100"), None)
    assert cms_2019 is not None
    assert cms_2019["document_match_count"] == 2
    assert cms_2019["comment_match_count"] == 4


def test_text_match_terms_finds_marijuana(db):
    """Find DEA docket for 'marijuana'"""
    result = db.text_match_terms(["marijuana"])

    assert len(result) == 1
    r = result[0]

    assert r["docket_id"] == "DEA-2024-0059"
    assert r["document_match_count"] == 0
    assert r["comment_match_count"] == 1  # 1 comment with "marijuana"


def test_text_match_terms_finds_cannabis(db):
    """Find DEA docket for 'cannabis'"""
    result = db.text_match_terms(["cannabis"])

    assert len(result) == 1
    r = result[0]

    assert r["docket_id"] == "DEA-2024-0059"
    assert r["document_match_count"] == 1  # extracted PDF text; one logical commentId
    assert r["comment_match_count"] == 0


def test_text_match_terms_no_results(db):
    """Returns empty list for nonexistent term"""
    result = db.text_match_terms(["nonexistent"])
    assert not result


def test_get_docket_ids_matching_filters(db):
    """Test mock filter method"""
    docket_ids = ["CMS-2025-0240", "DEA-2024-0059", "FAKE-ID"]
    
    # No filters - should return IDs that exist in mock data
    result = db.get_docket_ids_matching_filters(docket_ids)
    assert "CMS-2025-0240" in result
    
    # Agency filter - should filter correctly
    result = db.get_docket_ids_matching_filters(docket_ids, agency=["CMS"])
    assert "CMS-2025-0240" in result
    assert "DEA-2024-0059" not in result  # DEA != CMS
    
    # Non-matching agency
    result = db.get_docket_ids_matching_filters(docket_ids, agency=["FDA"])
    assert len(result) == 0
