"""
Tests for the Flask app endpoints
"""
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
    response = client.get('/search/')
    assert response.status_code == 200


def test_search_returns_list(client):
    """Test that search endpoint returns a list"""
    response = client.get('/search/')
    assert response.status_code == 200
    # Flask will auto-convert the list to JSON
    assert response.is_json
    data = response.get_json()
    assert isinstance(data, list)


def test_search_returns_dummy_data(client):
    """Test that search endpoint returns the expected dummy data"""
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
    response = client.get('/search/?str=Medicare')
    data = response.get_json()
    # Should return a list
    assert isinstance(data, list)
    assert len(data) > 0
    # Verify it returns Medicare-related results
    assert any('Medicare' in item['title'] for item in data)


def test_search_with_different_query_parameters(client):
    """Test search endpoint with various query strings"""
    # Test with docket ID
    response1 = client.get('/search/?str=CMS-2025-0240')
    data1 = response1.get_json()
    assert isinstance(data1, list)
    assert len(data1) > 0
    assert all(item['docket_id'] == 'CMS-2025-0240' for item in data1)
    
    # Test with partial title match
    response2 = client.get('/search/?str=kidney')
    data2 = response2.get_json()
    assert isinstance(data2, list)
    assert len(data2) > 0
    assert any('Kidney' in item['title'] for item in data2)
    
    # Test with agency ID match
    response3 = client.get('/search/?str=CMS')
    data3 = response3.get_json()
    assert isinstance(data3, list)
    assert len(data3) > 0
    assert all(item['agency_id'] == 'CMS' for item in data3)