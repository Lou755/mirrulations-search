"""
Tests for the database layer (db.py)
"""
import pytest
from mirrsearch.db import DBLayer, get_db


@pytest.fixture
def db():
    """Create a DBLayer instance for testing"""
    return DBLayer()


# Tests for DBLayer initialization and basic functionality
def test_db_layer_creation():
    """Test that DBLayer can be instantiated"""
    db = DBLayer()
    assert db is not None
    assert isinstance(db, DBLayer)


def test_db_layer_is_frozen():
    """Test that DBLayer is a frozen dataclass (immutable)"""
    db = DBLayer()
    # Frozen dataclasses should raise an error when trying to modify
    with pytest.raises(Exception):  # FrozenInstanceError
        db.new_attribute = "test"


def test_get_db_function():
    """Test the get_db factory function"""
    db = get_db()
    assert isinstance(db, DBLayer)


# Tests for _items() method
def test_items_returns_list():
    """Test that _items returns a list"""
    db = DBLayer()
    items = db._items()
    assert isinstance(items, list)


def test_items_returns_two_records():
    """Test that _items returns exactly 2 records"""
    db = DBLayer()
    items = db._items()
    assert len(items) == 2


def test_items_have_required_fields():
    """Test that each item has all required fields"""
    db = DBLayer()
    items = db._items()
    
    required_fields = ["docket_id", "title", "cfrPart", "agency_id", "document_type"]
    
    for item in items:
        for field in required_fields:
            assert field in item, f"Item missing required field: {field}"


def test_items_field_types():
    """Test that fields in items have correct types"""
    db = DBLayer()
    items = db._items()
    
    for item in items:
        assert isinstance(item["docket_id"], str)
        assert isinstance(item["title"], str)
        assert isinstance(item["cfrPart"], str)
        assert isinstance(item["agency_id"], str)
        assert isinstance(item["document_type"], str)


def test_items_content():
    """Test specific content of the items"""
    db = DBLayer()
    items = db._items()
    
    # Check first item
    assert items[0]["docket_id"] == "CMS-2025-0240"
    assert items[0]["agency_id"] == "CMS"
    assert items[0]["document_type"] == "Proposed Rule"
    
    # Check second item
    assert items[1]["docket_id"] == "CMS-2025-0240"
    assert items[1]["agency_id"] == "CMS"


# Tests for search() method
def test_search_returns_list(db):
    """Test that search returns a list"""
    result = db.search("CMS")
    assert isinstance(result, list)


def test_search_finds_by_docket_id(db):
    """Test search can find items by docket_id"""
    result = db.search("CMS-2025-0240")
    assert len(result) == 2  # Both items have this docket_id
    assert all(item["docket_id"] == "CMS-2025-0240" for item in result)


def test_search_finds_by_title(db):
    """Test search can find items by title keywords"""
    result = db.search("ESRD")
    assert len(result) >= 1
    assert all("ESRD" in item["title"] or "esrd" in item["title"].lower() for item in result)


def test_search_is_case_insensitive(db):
    """Test that search is case-insensitive"""
    result_upper = db.search("CMS")
    result_lower = db.search("cms")
    result_mixed = db.search("Cms")
    
    assert len(result_upper) == len(result_lower) == len(result_mixed)
    assert result_upper == result_lower == result_mixed


def test_search_strips_whitespace(db):
    """Test that search strips leading/trailing whitespace"""
    result_normal = db.search("CMS")
    result_spaces = db.search("  CMS  ")
    
    assert result_normal == result_spaces


def test_search_partial_match_title(db):
    """Test search with partial title match"""
    result = db.search("Medicare")
    assert len(result) >= 1
    assert any("Medicare" in item["title"] for item in result)


def test_search_partial_match_docket(db):
    """Test search with partial docket_id match"""
    result = db.search("2025")
    assert len(result) == 2  # Both items have 2025 in docket_id


def test_search_no_results(db):
    """Test search returns empty list when no matches"""
    result = db.search("nonexistent_query_xyz123")
    assert result == []
    assert len(result) == 0


def test_search_empty_string(db):
    """Test search with empty string returns all items"""
    result = db.search("")
    # Empty string matches everything (it's in every string)
    assert len(result) == 2


def test_search_specific_terms(db):
    """Test search with specific medical terms"""
    # Search for "Prospective Payment System"
    result = db.search("Prospective Payment System")
    assert len(result) >= 1
    
    # Search for "Quality Incentive"
    result = db.search("Quality Incentive")
    assert len(result) >= 1


def test_search_multiple_words(db):
    """Test search with multiple words (treated as single query)"""
    result = db.search("End-Stage Renal")
    assert len(result) >= 1


def test_search_returns_correct_structure(db):
    """Test that search results have correct structure"""
    result = db.search("CMS")
    
    for item in result:
        assert isinstance(item, dict)
        assert "docket_id" in item
        assert "title" in item
        assert "cfrPart" in item
        assert "agency_id" in item
        assert "document_type" in item


def test_search_does_not_modify_original_data(db):
    """Test that search doesn't modify the original data"""
    original_items = db._items()
    original_count = len(original_items)
    
    # Perform multiple searches
    db.search("CMS")
    db.search("Medicare")
    db.search("xyz")
    
    # Check data is unchanged
    assert len(db._items()) == original_count
    assert db._items() == original_items


# Edge case tests
def test_search_special_characters(db):
    """Test search with special characters"""
    result = db.search("CMS-2025")
    assert len(result) == 2


def test_search_numbers_only(db):
    """Test search with only numbers"""
    result = db.search("2025")
    assert len(result) == 2


def test_search_with_parentheses(db):
    """Test search with parentheses in query"""
    result = db.search("(ESRD)")
    assert len(result) >= 1