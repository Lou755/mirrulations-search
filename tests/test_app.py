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


def test_search_endpoint_exists(client):
    """Test that the search endpoint exists and returns 200"""
    response = client.get('/search')
    assert response.status_code == 200


def test_search_returns_list(client):
    """Test that search endpoint returns a list"""
    response = client.get('/search')
    assert response.status_code == 200
    # Flask will auto-convert the list to JSON
    assert response.is_json
    data = response.get_json()
    assert isinstance(data, list)


def test_search_returns_test_data(client):
    """Test that search endpoint returns the expected dummy data"""
    response = client.get('/search')
    data = response.get_json()
    assert data == ["Test", "Dummy"]
    assert len(data) == 2
    assert "Test" in data
    assert "Dummy" in data
