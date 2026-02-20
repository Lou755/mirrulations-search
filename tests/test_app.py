"""
Tests for the Flask app endpoints
"""
# pylint: disable=redefined-outer-name
import os
import pytest
from mirrsearch.app import create_app


@pytest.fixture
def app():
    """Create and configure a test app instance"""
    app = create_app()
    app.config['TESTING'] = True
    return app


@pytest.fixture
def client(app):
    """Create a test client for the app"""
    return app.test_client()


def test_home_endpoint(client):
    """Test the home endpoint returns the index.html template"""
    response = client.get('/')
    assert response.status_code == 200


def test_search_endpoint_exists(client):
    """Test that the search endpoint exists and returns 200"""
    if os.getenv("USE_POSTGRES", "").lower() in {"1", "true", "yes", "on"}:
        pytest.skip("Unit tests expect dummy data")
    response = client.get('/search/')
    assert response.status_code == 200


def test_search_returns_list(client):
    """Test that search endpoint returns a list"""
    if os.getenv("USE_POSTGRES", "").lower() in {"1", "true", "yes", "on"}:
        pytest.skip("Unit tests expect dummy data")
    response = client.get('/search/')
    assert response.status_code == 200
    # Flask will auto-convert the list to JSON
    assert response.is_json
    data = response.get_json()
    assert isinstance(data, list)


def test_search_returns_dummy_data(client):
    """Test that search endpoint returns expected data (dummy or Postgres)"""
    if os.getenv("USE_POSTGRES", "").lower() in {"1", "true", "yes", "on"}:
        pytest.skip("Unit tests expect dummy data")
    response = client.get('/search/?str=ESRD')
    data = response.get_json()
    # Should return a list
    assert isinstance(data, list)
    assert len(data) > 0
    # Verify the data contains expected fields
    assert 'docket_id' in data[0]
    assert 'title' in data[0]
    assert 'ESRD' in data[0]['title'] or 'End-Stage Renal Disease' in data[0]['title']


def test_search_with_query_parameter(client):
    """Test that search endpoint accepts and returns query parameter"""
    if os.getenv("USE_POSTGRES", "").lower() in {"1", "true", "yes", "on"}:
        pytest.skip("Unit tests expect dummy data")
    response = client.get('/search/?str=ESRD')
    data = response.get_json()
    # Should return a list
    assert isinstance(data, list)
    assert len(data) > 0
    # Verify it returns ESRD-related results (dummy or Postgres)
    assert any('ESRD' in item['title'] for item in data)


def test_search_with_different_query_parameters(client):
    """Test search endpoint with various query strings"""
    if os.getenv("USE_POSTGRES", "").lower() in {"1", "true", "yes", "on"}:
        pytest.skip("Unit tests expect dummy data")
    # Test with docket ID
    response1 = client.get('/search/?str=CMS-2025-024')
    data1 = response1.get_json()
    assert isinstance(data1, list)
    assert len(data1) > 0
    assert all(item['docket_id'].startswith('CMS-2025-024') for item in data1)

    # Test with partial title match
    response2 = client.get('/search/?str=ESRD')
    data2 = response2.get_json()
    assert isinstance(data2, list)
    assert len(data2) > 0
    assert any('ESRD' in item['title'] for item in data2)

    # Test with agency ID match
    response3 = client.get('/search/?str=CMS')
    data3 = response3.get_json()
    assert isinstance(data3, list)
    assert len(data3) > 0
    assert all(item['agency_id'] == 'CMS' for item in data3)


@pytest.mark.integration
def test_search_with_postgres_seed_data(client):
    """Integration test: requires Postgres with seed data."""
    if os.getenv("USE_POSTGRES", "").lower() not in {"1", "true", "yes", "on"}:
        pytest.skip("Integration test requires USE_POSTGRES=true")
    response = client.get('/search/?str=CMS-2025-0242')
    data = response.get_json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert all(item['docket_id'] == 'CMS-2025-0242' for item in data)

def test_search_without_filter_returns_all_matches(client):
    """Test that omitting the filter param returns all matching results regardless of document_type"""
    if os.getenv("USE_POSTGRES", "").lower() in {"1", "true", "yes", "on"}:
        pytest.skip("Unit tests expect dummy data")
    response = client.get('/search/?str=renal')
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)
    assert len(data) > 0
    # All dummy records are "Proposed Rule", but the point is no filter was applied
    document_types = {item['document_type'] for item in data}
    assert len(document_types) >= 1


def test_search_with_valid_filter_returns_matching_document_type(client):
    """Test that the filter param restricts results to the specified document_type"""
    if os.getenv("USE_POSTGRES", "").lower() in {"1", "true", "yes", "on"}:
        pytest.skip("Unit tests expect dummy data")
    response = client.get('/search/?str=renal&filter=Proposed Rule')
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert all(item['document_type'] == 'Proposed Rule' for item in data)


def test_search_with_filter_only_affects_document_type(client):
    """Test that filtered results still match the search query"""
    if os.getenv("USE_POSTGRES", "").lower() in {"1", "true", "yes", "on"}:
        pytest.skip("Unit tests expect dummy data")
    response = client.get('/search/?str=ESRD&filter=Proposed Rule')
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)
    assert len(data) > 0
    # Every result must satisfy both the query and the filter
    for item in data:
        assert 'ESRD' in item['title'] or 'esrd' in item['title'].lower()
        assert item['document_type'] == 'Proposed Rule'


def test_search_with_nonexistent_filter_returns_empty_list(client):
    """Test that a filter value matching no document_type returns an empty list"""
    if os.getenv("USE_POSTGRES", "").lower() in {"1", "true", "yes", "on"}:
        pytest.skip("Unit tests expect dummy data")
    response = client.get('/search/?str=renal&filter=Final Rule')
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)
    assert len(data) == 0


def test_search_filter_is_case_insensitive(client):
    """Test that the filter comparison is case-insensitive"""
    if os.getenv("USE_POSTGRES", "").lower() in {"1", "true", "yes", "on"}:
        pytest.skip("Unit tests expect dummy data")
    response_lower = client.get('/search/?str=renal&filter=proposed rule')
    response_upper = client.get('/search/?str=renal&filter=PROPOSED RULE')
    response_mixed = client.get('/search/?str=renal&filter=Proposed Rule')

    data_lower = response_lower.get_json()
    data_upper = response_upper.get_json()
    data_mixed = response_mixed.get_json()

    assert len(data_lower) == len(data_upper) == len(data_mixed)
    assert data_lower == data_upper == data_mixed


def test_search_filter_without_query_string_uses_default(client):
    """Test that filter works even when no str param is provided (falls back to default query)"""
    if os.getenv("USE_POSTGRES", "").lower() in {"1", "true", "yes", "on"}:
        pytest.skip("Unit tests expect dummy data")
    # No str param — app defaults to "example_query", which matches nothing in dummy data
    response = client.get('/search/?filter=Proposed Rule')
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)
    # "example_query" won't match any dummy records, so the result should be empty
    assert len(data) == 0


def test_search_filter_result_structure(client):
    """Test that filtered results still contain all required fields"""
    if os.getenv("USE_POSTGRES", "").lower() in {"1", "true", "yes", "on"}:
        pytest.skip("Unit tests expect dummy data")
    response = client.get('/search/?str=CMS&filter=Proposed Rule')
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)
    assert len(data) > 0

    required_fields = ['docket_id', 'title', 'cfrPart', 'agency_id', 'document_type']
    for item in data:
        for field in required_fields:
            assert field in item, f"Filtered result missing field: {field}"