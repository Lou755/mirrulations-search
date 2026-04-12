"""
Tests for the Flask app endpoints - Header-based pagination (returns list)
"""
import json
import tempfile
import os
from datetime import date
from unittest.mock import patch, MagicMock
import pytest
from mock_db import MockDBLayer
from mirrsearch.app import create_app
from mirrsearch.db import get_postgres_connection, get_opensearch_connection
from mirrsearch.app import _make_oauth_handler

# pylint: disable=duplicate-code
class MockOAuthHandler:
    """Mock OAuth handler that always authenticates as a test user"""
    def get_authorization_url(self):
        return "http://mock-auth-url", None

    def validate_jwt_token(self, token):  # pylint: disable=unused-argument
        return "Test User|test@example.com"

    def exchange_code_for_user_info(self, code):  # pylint: disable=unused-argument
        return {"name": "Test User", "email": "test@example.com"}

    def create_jwt_token(self, user_id):  # pylint: disable=unused-argument
        return "mock-token"


class _ReadyDownloadMockDB(MockDBLayer):
    """Jobs can become ready; S3 URL is returned only when status is ready."""

    def get_download_s3_url(self, job_id, user_email):  # pylint: disable=unused-argument
        job = self._jobs.get(job_id)
        if job and job.get("status") == "ready":
            return "https://files.example.com/export.zip"
        return None


class _DocketsByIdMockDB(MockDBLayer):
    """Returns one docket row so GET /dockets exercises transform paths."""

    def get_dockets_by_ids(self, docket_ids):  # pylint: disable=unused-argument
        if not docket_ids:
            return []
        return [
            {
                "docket_id": "CMS-2025-0240",
                "modify_date": date(2024, 6, 1),
                "cfr_refs": [{"title": "42", "cfrParts": {"413": "https://example"}}],
            }
        ]


@pytest.fixture
def app(tmp_path):
    """Create and configure a test app instance"""
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("<html></html>")
    test_app = create_app(
        dist_dir=str(dist), db_layer=MockDBLayer(), oauth_handler=MockOAuthHandler()
    )
    test_app.config['TESTING'] = True
    return test_app


@pytest.fixture
def client(app):  # pylint: disable=redefined-outer-name
    """Create a test client for the app"""
    c = app.test_client()
    c.set_cookie("jwt_token", "mock-token")
    return c


def test_search_endpoint_exists(client):  # pylint: disable=redefined-outer-name
    """Test that the search endpoint exists and returns 200"""
    response = client.get('/search/')
    assert response.status_code == 200


def test_search_returns_list(client):  # pylint: disable=redefined-outer-name
    """Test that search endpoint returns a list (not dict)"""
    response = client.get('/search/')
    assert response.status_code == 200
    assert response.is_json
    data = response.get_json()
    assert isinstance(data, list)


def test_search_has_pagination_headers(client):  # pylint: disable=redefined-outer-name
    """Test that pagination metadata is in HTTP headers"""
    response = client.get('/search/')

    assert 'X-Page' in response.headers
    assert 'X-Page-Size' in response.headers
    assert 'X-Total-Results' in response.headers
    assert 'X-Total-Pages' in response.headers
    assert 'X-Has-Next' in response.headers
    assert 'X-Has-Prev' in response.headers


def test_search_with_query_parameter(client):  # pylint: disable=redefined-outer-name
    """Test search endpoint with query parameter"""
    response = client.get('/search/?str=ESRD')
    data = response.get_json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert any('ESRD' in item['title'] for item in data)


def test_search_with_different_query_parameters(client):  # pylint: disable=redefined-outer-name
    """Test search endpoint with various query parameters"""
    data1 = client.get('/search/?str=CMS-2025-024').get_json()
    assert isinstance(data1, list)
    assert len(data1) > 0
    assert all(item['docket_id'].startswith('CMS-2025-024') for item in data1)

    data2 = client.get('/search/?str=ESRD').get_json()
    assert isinstance(data2, list)
    assert len(data2) > 0
    assert any('ESRD' in item['title'] for item in data2)

    data3 = client.get('/search/?str=CMS').get_json()
    assert isinstance(data3, list)
    assert len(data3) > 0
    assert all(item['agency_id'] == 'CMS' for item in data3)


def test_search_without_filter_returns_all_matches(client):  # pylint: disable=redefined-outer-name
    """Search without filter returns all matching documents"""
    response = client.get('/search/?str=renal')
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)
    assert len(data) > 0


def test_search_with_valid_filter_returns_matching_docket_type(client):  # pylint: disable=redefined-outer-name
    """Filter param restricts results to the specified docket_type"""
    response = client.get('/search/?str=renal&docket_type=Proposed Rule')
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)
    assert len(data) > 0
    for doc in data:
        assert doc['document_type'] == 'Proposed Rule'


def test_search_with_filter_only_affects_docket_type(client):  # pylint: disable=redefined-outer-name
    """Filter only restricts docket_type; other fields are unaffected"""
    response = client.get('/search/?str=ESRD&docket_type=Proposed Rule')
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)
    assert len(data) > 0
    for item in data:
        assert 'ESRD' in item['title'] or 'esrd' in item['title'].lower()
        assert item['document_type'] == 'Proposed Rule'


def test_search_with_nonexistent_filter_returns_empty_list(client):  # pylint: disable=redefined-outer-name
    """A filter value matching no docket_type returns an empty list"""
    response = client.get('/search/?str=renal&docket_type=Final Rule')
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)
    assert len(data) == 0


def test_search_filter_without_query_string_uses_default(client):  # pylint: disable=redefined-outer-name
    """If str is missing, defaults to 'example_query' which matches nothing"""
    response = client.get('/search/?docket_type=Proposed Rule')
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)
    assert len(data) == 0


def test_search_filter_result_structure(client):  # pylint: disable=redefined-outer-name
    """Filtered results have all required fields"""
    response = client.get('/search/?str=CMS&docket_type=Proposed Rule')
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)
    assert len(data) > 0
    required_fields = ['docket_id', 'title', 'cfrPart', 'agency_id', 'document_type']
    for item in data:
        for field in required_fields:
            assert field in item, f"Result missing field: {field}"


def test_search_with_agency_filter(client):  # pylint: disable=redefined-outer-name
    """Agency param restricts results to the specified agency_id"""
    response = client.get('/search/?str=renal&agency=CMS')
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)
    assert len(data) > 0
    for doc in data:
        assert doc['agency_id'] == 'CMS'


def test_search_with_multiple_agency_filters(client):  # pylint: disable=redefined-outer-name
    """Multiple agency params return results matching any of them"""
    response = client.get('/search/?str=renal&agency=CMS&agency=EPA')
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)
    assert len(data) > 0
    for doc in data:
        assert doc['agency_id'] in ('CMS', 'EPA')


def test_search_with_nonexistent_agency_returns_empty_list(client):  # pylint: disable=redefined-outer-name
    """An agency value matching no agency_id returns an empty list"""
    response = client.get('/search/?str=renal&agency=FDA')
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)
    assert len(data) == 0


def test_search_with_multiple_cfr_part_filters(client):  # pylint: disable=redefined-outer-name
    """Multiple cfr_part params return results matching any of them"""
    response = client.get('/search/?str=renal&cfr_part=42 CFR Parts 413 and 512:413'
                          '&cfr_part=42 CFR Parts 413 and 512:512')
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)
    assert len(data) > 0


def test_search_with_agency_and_filter(client):  # pylint: disable=redefined-outer-name
    """Both agency and filter params can be combined"""
    response = client.get('/search/?str=renal&agency=CMS&docket_type=Proposed Rule')
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)
    assert len(data) > 0
    for doc in data:
        assert doc['agency_id'] == 'CMS'
        assert doc['document_type'] == 'Proposed Rule'


def test_search_returns_401_without_cookie(app):  # pylint: disable=redefined-outer-name
    """Search endpoint returns 401 when no JWT cookie is present"""
    anon = app.test_client()
    response = anon.get('/search/')
    assert response.status_code == 401


def test_login_route_redirects(app):  # pylint: disable=redefined-outer-name
    """Login route redirects to Google authorization URL"""
    anon = app.test_client()
    response = anon.get('/login')
    assert response.status_code == 302
    assert "mock-auth-url" in response.headers['Location']


def test_logout_route_clears_cookie(app):  # pylint: disable=redefined-outer-name
    """Logout route redirects to home and clears jwt_token cookie"""
    anon = app.test_client()
    anon.set_cookie("jwt_token", "mock-token")
    response = anon.get('/logout')
    assert response.status_code == 302
    assert any(
        'jwt_token' in h and 'expires' in h.lower()
        for h in response.headers.getlist('Set-Cookie')
    )


def test_auth_status_logged_in(client):  # pylint: disable=redefined-outer-name
    """Auth status returns logged_in true when valid cookie present"""
    response = client.get('/auth/status')
    assert response.status_code == 200
    data = response.get_json()
    assert data['logged_in'] is True
    assert data['name'] == 'Test User'
    assert data['email'] == 'test@example.com'


def test_auth_status_not_logged_in(app):  # pylint: disable=redefined-outer-name
    """Auth status returns logged_in false when no cookie"""
    anon = app.test_client()
    response = anon.get('/auth/status')
    assert response.status_code == 200
    data = response.get_json()
    assert data['logged_in'] is False


def test_invalid_cookie_treated_as_unauthenticated(tmp_path):
    """An invalid JWT cookie results in 401 on search"""
    from mirrsearch.oauth_handler import TokenInvalidError  # pylint: disable=import-outside-toplevel

    class RejectingOAuthHandler:  # pylint: disable=too-few-public-methods
        """OAuth handler that always rejects tokens"""
        def validate_jwt_token(self, token):  # pylint: disable=unused-argument
            raise TokenInvalidError("bad token")

    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("<html></html>")
    test_app = create_app(
        dist_dir=str(dist), db_layer=MockDBLayer(), oauth_handler=RejectingOAuthHandler()
    )
    test_app.config['TESTING'] = True
    anon = test_app.test_client()
    anon.set_cookie("jwt_token", "invalid-token")
    response = anon.get('/search/')
    assert response.status_code == 401


def test_home_route_with_oauth_code_redirects(app):  # pylint: disable=redefined-outer-name
    """Home route exchanges OAuth code and redirects"""
    anon = app.test_client()
    response = anon.get('/?code=valid-code')
    assert response.status_code == 302
    assert 'jwt_token' in response.headers.get('Set-Cookie', '')


def test_home_route_with_bad_oauth_code_redirects(tmp_path):
    """Home route redirects to / when OAuth code exchange fails"""
    class FailingOAuthHandler:
        """OAuth handler that always fails code exchange"""
        def exchange_code_for_user_info(self, code):  # pylint: disable=unused-argument
            from mirrsearch.oauth_handler import OAuthCodeError  # pylint: disable=import-outside-toplevel
            raise OAuthCodeError("bad code")

        def validate_jwt_token(self, token):  # pylint: disable=unused-argument
            from mirrsearch.oauth_handler import TokenInvalidError  # pylint: disable=import-outside-toplevel
            raise TokenInvalidError("invalid")

    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("<html></html>")
    test_app = create_app(
        dist_dir=str(dist), db_layer=MockDBLayer(), oauth_handler=FailingOAuthHandler()
    )
    test_app.config['TESTING'] = True
    anon = test_app.test_client()
    response = anon.get('/?code=bad-code')
    assert response.status_code == 302


def test_home_route_with_index_html():
    """Test home route serves index.html"""
    with tempfile.TemporaryDirectory() as tmpdir:
        index_path = os.path.join(tmpdir, 'index.html')
        with open(index_path, 'w', encoding='utf-8') as f:
            f.write('<html><body>Home</body></html>')

        test_app = create_app(dist_dir=tmpdir, db_layer=MockDBLayer())
        test_client = test_app.test_client()

        response = test_client.get('/')
        assert response.status_code == 200
        assert b'Home' in response.data


# --- Collections ---

def test_get_collections_returns_empty_list(client):  # pylint: disable=redefined-outer-name
    """GET /api/collections returns empty list when user has no collections"""
    response = client.get('/api/collections')
    assert response.status_code == 200
    assert response.get_json() == []


def test_get_collections_requires_auth(app):  # pylint: disable=redefined-outer-name
    """GET /api/collections returns 401 without cookie"""
    response = app.test_client().get('/api/collections')
    assert response.status_code == 401


def test_create_collection_returns_id(client):  # pylint: disable=redefined-outer-name
    """POST /api/collections creates a collection and returns its id"""
    response = client.post('/api/collections', json={"name": "My Collection"})
    assert response.status_code == 201
    data = response.get_json()
    assert "collection_id" in data
    assert isinstance(data["collection_id"], int)


def test_create_collection_requires_name(client):  # pylint: disable=redefined-outer-name
    """POST /api/collections returns 400 when name is missing"""
    response = client.post('/api/collections', json={})
    assert response.status_code == 400


def test_create_collection_requires_auth(app):  # pylint: disable=redefined-outer-name
    """POST /api/collections returns 401 without cookie"""
    response = app.test_client().post('/api/collections', json={"name": "Test"})
    assert response.status_code == 401


def test_delete_collection(client):  # pylint: disable=redefined-outer-name
    """DELETE /api/collections/<id> deletes an existing collection"""
    collection_id = client.post(
        '/api/collections', json={"name": "To Delete"}
    ).get_json()["collection_id"]
    response = client.delete(f'/api/collections/{collection_id}')
    assert response.status_code == 204


def test_delete_collection_not_found(client):  # pylint: disable=redefined-outer-name
    """DELETE /api/collections/<id> returns 404 for nonexistent collection"""
    response = client.delete('/api/collections/9999')
    assert response.status_code == 404


def test_delete_collection_requires_auth(app):  # pylint: disable=redefined-outer-name
    """DELETE /api/collections/<id> returns 401 without cookie"""
    response = app.test_client().delete('/api/collections/1')
    assert response.status_code == 401


def test_add_docket_to_collection(client):  # pylint: disable=redefined-outer-name
    """POST /api/collections/<id>/dockets adds a docket to a collection"""
    collection_id = client.post(
        '/api/collections', json={"name": "My List"}
    ).get_json()["collection_id"]
    response = client.post(
        f'/api/collections/{collection_id}/dockets', json={"docket_id": "CMS-2025-0240"}
    )
    assert response.status_code == 204


def test_add_docket_requires_docket_id(client):  # pylint: disable=redefined-outer-name
    """POST /api/collections/<id>/dockets returns 400 when docket_id is missing"""
    collection_id = client.post(
        '/api/collections', json={"name": "My List"}
    ).get_json()["collection_id"]
    response = client.post(f'/api/collections/{collection_id}/dockets', json={})
    assert response.status_code == 400


def test_add_docket_collection_not_found(client):  # pylint: disable=redefined-outer-name
    """POST /api/collections/<id>/dockets returns 404 for nonexistent collection"""
    response = client.post('/api/collections/9999/dockets', json={"docket_id": "CMS-2025-0240"})
    assert response.status_code == 404


def test_add_docket_requires_auth(app):  # pylint: disable=redefined-outer-name
    """POST /api/collections/<id>/dockets returns 401 without cookie"""
    response = app.test_client().post(
        '/api/collections/1/dockets', json={"docket_id": "CMS-2025-0240"}
    )
    assert response.status_code == 401


def test_remove_docket_from_collection(client):  # pylint: disable=redefined-outer-name
    """DELETE /api/collections/<id>/dockets/<docket_id> removes a docket"""
    collection_id = client.post(
        '/api/collections', json={"name": "My List"}
    ).get_json()["collection_id"]
    client.post(f'/api/collections/{collection_id}/dockets', json={"docket_id": "CMS-2025-0240"})
    response = client.delete(f'/api/collections/{collection_id}/dockets/CMS-2025-0240')
    assert response.status_code == 204


def test_remove_docket_collection_not_found(client):  # pylint: disable=redefined-outer-name
    """DELETE /api/collections/<id>/dockets/<docket_id> returns 404 for nonexistent collection"""
    response = client.delete('/api/collections/9999/dockets/CMS-2025-0240')
    assert response.status_code == 404


def test_remove_docket_requires_auth(app):  # pylint: disable=redefined-outer-name
    """DELETE /api/collections/<id>/dockets/<docket_id> returns 401 without cookie"""
    response = app.test_client().delete('/api/collections/1/dockets/CMS-2025-0240')
    assert response.status_code == 401


def test_get_collections_shows_added_dockets(client):  # pylint: disable=redefined-outer-name
    """GET /api/collections reflects dockets added to a collection"""
    collection_id = client.post(
        '/api/collections', json={"name": "My List"}
    ).get_json()["collection_id"]
    client.post(f'/api/collections/{collection_id}/dockets', json={"docket_id": "CMS-2025-0240"})
    data = client.get('/api/collections').get_json()
    match = next(c for c in data if c["collection_id"] == collection_id)
    assert "CMS-2025-0240" in match["docket_ids"]


# --- GET /api/collections/<id>/dockets (paginated) ---

def test_get_collection_dockets_returns_empty_for_empty_collection(client):  # pylint: disable=redefined-outer-name
    """GET /api/collections/<id>/dockets returns empty list for a collection with no dockets"""
    collection_id = client.post(
        '/api/collections', json={"name": "Empty"}
    ).get_json()["collection_id"]
    response = client.get(f'/api/collections/{collection_id}/dockets')
    assert response.status_code == 200
    assert response.get_json() == []


def test_get_collection_dockets_has_pagination_headers(client):  # pylint: disable=redefined-outer-name
    """GET /api/collections/<id>/dockets returns all required pagination headers"""
    collection_id = client.post(
        '/api/collections', json={"name": "Headers Check"}
    ).get_json()["collection_id"]
    response = client.get(f'/api/collections/{collection_id}/dockets')
    assert response.status_code == 200
    assert 'X-Page' in response.headers
    assert 'X-Page-Size' in response.headers
    assert 'X-Total-Results' in response.headers
    assert 'X-Total-Pages' in response.headers
    assert 'X-Has-Next' in response.headers
    assert 'X-Has-Prev' in response.headers


def test_get_collection_dockets_returns_404_for_nonexistent_collection(client):  # pylint: disable=redefined-outer-name
    """GET /api/collections/<id>/dockets returns 404 for a collection that does not exist"""
    response = client.get('/api/collections/9999/dockets')
    assert response.status_code == 404


def test_get_collection_dockets_requires_auth(app):  # pylint: disable=redefined-outer-name
    """GET /api/collections/<id>/dockets returns 401 without cookie"""
    response = app.test_client().get('/api/collections/1/dockets')
    assert response.status_code == 401


def test_get_collection_dockets_respects_page_size(client):  # pylint: disable=redefined-outer-name
    """GET /api/collections/<id>/dockets respects page_size query param"""
    collection_id = client.post(
        '/api/collections', json={"name": "Paged"}
    ).get_json()["collection_id"]
    response = client.get(f'/api/collections/{collection_id}/dockets?page=1&page_size=5')
    assert response.status_code == 200
    assert response.headers['X-Page'] == '1'
    assert response.headers['X-Page-Size'] == '5'


def test_get_collection_dockets_returns_json_list(client):  # pylint: disable=redefined-outer-name
    """GET /api/collections/<id>/dockets returns a JSON list"""
    collection_id = client.post(
        '/api/collections', json={"name": "List Check"}
    ).get_json()["collection_id"]
    response = client.get(f'/api/collections/{collection_id}/dockets')
    assert response.is_json
    assert isinstance(response.get_json(), list)


def test_get_collection_dockets_total_results_zero_for_empty(client):  # pylint: disable=redefined-outer-name
    """X-Total-Results is 0 for a collection with no dockets"""
    collection_id = client.post(
        '/api/collections', json={"name": "Zero"}
    ).get_json()["collection_id"]
    response = client.get(f'/api/collections/{collection_id}/dockets')
    assert response.headers['X-Total-Results'] == '0'
    assert response.headers['X-Has-Next'] == 'false'
    assert response.headers['X-Has-Prev'] == 'false'


# --- agencies ---

def test_agencies_returns_list(client):  # pylint: disable=redefined-outer-name
    """Test that agencies endpoint returns a JSON list"""
    response = client.get('/agencies')
    assert response.status_code == 200
    assert response.is_json
    data = response.get_json()
    assert isinstance(data, list)


@patch('mirrsearch.db.psycopg2.connect')
def test_get_postgres_connection(mock_connect):
    """Test postgres connection"""
    mock_conn = MagicMock()
    mock_connect.return_value = mock_conn

    with patch.dict(os.environ, {
        'DB_HOST': 'localhost',
        'DB_PORT': '5432',
        'DB_NAME': 'test',
        'DB_USER': 'test',
        'DB_PASSWORD': 'test'
    }):
        result = get_postgres_connection()
        assert result.conn == mock_conn
        mock_connect.assert_called_once()


@patch('mirrsearch.db.OpenSearch')
def test_get_opensearch_connection(mock_opensearch):
    """Test opensearch connection"""
    get_opensearch_connection()
    mock_opensearch.assert_called_once()


# --- Download ---

def test_request_download_returns_job_id(client):  # pylint: disable=redefined-outer-name
    """POST /download/request returns job_id and started status"""
    response = client.post('/download/request', json={
        "docket_ids": ["CMS-2025-0240"],
        "format": "raw",
        "include_binaries": False
    })
    assert response.status_code == 202
    data = response.get_json()
    assert "job_id" in data
    assert data["status"] == "started"


def test_request_download_requires_auth(app):  # pylint: disable=redefined-outer-name
    """POST /download/request returns 401 without cookie"""
    response = app.test_client().post('/download/request', json={
        "docket_ids": ["CMS-2025-0240"],
        "format": "raw",
        "include_binaries": False
    })
    assert response.status_code == 401


def test_request_download_requires_docket_ids(client):  # pylint: disable=redefined-outer-name
    """POST /download/request returns 400 when docket_ids is missing"""
    response = client.post('/download/request', json={
        "format": "raw",
        "include_binaries": False
    })
    assert response.status_code == 400


def test_request_download_enforces_10_docket_limit(client):  # pylint: disable=redefined-outer-name
    """POST /download/request returns 400 when more than 10 dockets provided"""
    response = client.post('/download/request', json={
        "docket_ids": [f"CMS-2025-000{i}" for i in range(11)],
        "format": "raw",
        "include_binaries": False
    })
    assert response.status_code == 400


def test_request_download_requires_valid_format(client):  # pylint: disable=redefined-outer-name
    """POST /download/request returns 400 for invalid format"""
    response = client.post('/download/request', json={
        "docket_ids": ["CMS-2025-0240"],
        "format": "json",
        "include_binaries": False
    })
    assert response.status_code == 400


def test_request_download_accepts_csv_format(client):  # pylint: disable=redefined-outer-name
    """POST /download/request accepts csv as a valid format"""
    response = client.post('/download/request', json={
        "docket_ids": ["CMS-2025-0240"],
        "format": "csv",
        "include_binaries": False
    })
    assert response.status_code == 202


def test_download_status_returns_job_info(client):  # pylint: disable=redefined-outer-name
    """GET /download/status/<job_id> returns job status"""
    job_id = client.post('/download/request', json={
        "docket_ids": ["CMS-2025-0240"],
        "format": "raw",
        "include_binaries": False
    }).get_json()["job_id"]
    response = client.get(f'/download/status/{job_id}')
    assert response.status_code == 200
    data = response.get_json()
    assert data["job_id"] == job_id
    assert "status" in data
    assert "format" in data
    assert "docket_ids" in data
    assert "created_at" in data


def test_download_status_not_found(client):  # pylint: disable=redefined-outer-name
    """GET /download/status/<job_id> returns 404 for nonexistent job"""
    response = client.get('/download/status/nonexistent-job-id')
    assert response.status_code == 404


def test_download_status_requires_auth(app):  # pylint: disable=redefined-outer-name
    """GET /download/status/<job_id> returns 401 without cookie"""
    response = app.test_client().get('/download/status/some-job-id')
    assert response.status_code == 401


def test_download_file_not_ready(client):  # pylint: disable=redefined-outer-name
    """GET /download/<job_id> returns 202 when job is still pending"""
    job_id = client.post('/download/request', json={
        "docket_ids": ["CMS-2025-0240"],
        "format": "raw",
        "include_binaries": False
    }).get_json()["job_id"]
    response = client.get(f'/download/{job_id}')
    assert response.status_code == 202


def test_download_file_not_found(client):  # pylint: disable=redefined-outer-name
    """GET /download/<job_id> returns 404 for nonexistent job"""
    response = client.get('/download/nonexistent-job-id')
    assert response.status_code == 404


def test_download_file_requires_auth(app):  # pylint: disable=redefined-outer-name
    """GET /download/<job_id> returns 401 without cookie"""
    response = app.test_client().get('/download/some-job-id')
    assert response.status_code == 401


def test_search_with_date_filters(client): # pylint: disable=redefined-outer-name
    """Test search with start_date and end_date filters"""
    response = client.get('/search/?str=renal&start_date=2024-01-01&end_date=2024-12-31')
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)


def test_search_with_invalid_page_size_defaults_to_10(client): # pylint: disable=redefined-outer-name
    """Test that invalid page_size defaults to 10"""
    response = client.get('/search/?page_size=200')  # > 100 should default to 10
    assert response.status_code == 200
    assert response.headers['X-Page-Size'] == '10'


def test_search_with_page_less_than_1_defaults_to_1(client): # pylint: disable=redefined-outer-name
    """Test that page < 1 defaults to 1"""
    response = client.get('/search/?page=0')
    assert response.status_code == 200
    assert response.headers['X-Page'] == '1'


def test_search_with_invalid_cfr_part_ignores_malformed(client): # pylint: disable=redefined-outer-name
    """Test that malformed cfr_part values are ignored"""
    response = client.get('/search/?str=renal&cfr_part=invalid&cfr_part=42:413')
    assert response.status_code == 200


def test_home_route_serves_index_html(tmp_path):
    """Test home route serves index.html when no OAuth code"""
    index_path = tmp_path / "dist" / "index.html"
    index_path.parent.mkdir()
    index_path.write_text("<html><body>Test</body></html>")

    test_app = create_app(dist_dir=str(tmp_path / "dist"), db_layer=MockDBLayer())
    test_client = test_app.test_client()

    response = test_client.get('/')
    assert response.status_code == 200
    assert b'Test' in response.data


def test_search_with_empty_query_uses_default(client): # pylint: disable=redefined-outer-name
    """Test search with empty query uses default 'example_query'"""
    response = client.get('/search/?str=')
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)


def test_oauth_handler_from_aws_secrets(monkeypatch):
    """Test OAuth handler creation from AWS Secrets Manager"""
    monkeypatch.setenv("USE_AWS_SECRETS", "true")
    monkeypatch.setenv("AWS_REGION", "us-east-1")

    mock_secret = {
        "base_url": "https://test.com",
        "google_client_id": "test-id",
        "google_client_secret": "test-secret",
        "jwt_secret": "test-jwt"
    }

    mock_boto3 = MagicMock()
    mock_client = MagicMock()
    mock_client.get_secret_value.return_value = {"SecretString": json.dumps(mock_secret)}
    mock_boto3.client.return_value = mock_client

    with patch.dict('sys.modules', {'boto3': mock_boto3}):
        with patch('mirrsearch.app._make_oauth_handler_from_aws') as mock_handler:
            mock_handler.return_value = MockOAuthHandler()
            handler = _make_oauth_handler()
            assert handler is not None


def test_internal_logic_error_handling(client): # pylint: disable=redefined-outer-name
    """Test error handling in InternalLogic"""
    with patch('mirrsearch.internal_logic.get_db') as mock_get_db:
        mock_get_db.side_effect = Exception("DB Error")
        response = client.get('/search/?str=test')
        assert response.status_code in [200, 500]

# --- Single docket download ---

def test_request_single_download_returns_job_id(client):  # pylint: disable=redefined-outer-name
    """POST /download/request/<docket_id> returns job_id and started status"""
    response = client.post('/download/request/CMS-2025-0240', json={
        "format": "raw",
        "include_binaries": False
    })
    assert response.status_code == 202
    data = response.get_json()
    assert "job_id" in data
    assert data["status"] == "started"


def test_request_single_download_requires_auth(app):  # pylint: disable=redefined-outer-name
    """POST /download/request/<docket_id> returns 401 without cookie"""
    response = app.test_client().post('/download/request/CMS-2025-0240', json={
        "format": "raw",
        "include_binaries": False
    })
    assert response.status_code == 401


def test_request_single_download_requires_valid_format(client):  # pylint: disable=redefined-outer-name
    """POST /download/request/<docket_id> returns 400 for invalid format"""
    response = client.post('/download/request/CMS-2025-0240', json={
        "format": "json",
        "include_binaries": False
    })
    assert response.status_code == 400


def test_request_single_download_accepts_csv_format(client):  # pylint: disable=redefined-outer-name
    """POST /download/request/<docket_id> accepts csv as a valid format"""
    response = client.post('/download/request/CMS-2025-0240', json={
        "format": "csv",
        "include_binaries": False
    })
    assert response.status_code == 202


def test_request_single_download_status_checkable(client):  # pylint: disable=redefined-outer-name
    """Job created via single docket endpoint is retrievable via status endpoint"""
    job_id = client.post('/download/request/CMS-2025-0240', json={
        "format": "raw",
        "include_binaries": False
    }).get_json()["job_id"]
    response = client.get(f'/download/status/{job_id}')
    assert response.status_code == 200
    data = response.get_json()
    assert data["job_id"] == job_id
    assert data["docket_ids"] == ["CMS-2025-0240"]


def test_search_cfr_part_skips_empty_title_or_part(client):  # pylint: disable=redefined-outer-name
    """Malformed cfr_part values with empty title or part are skipped (colon present)."""
    response = client.get(
        '/search/?str=renal&cfr_part=42:&cfr_part=:413&cfr_part=42:413'
    )
    assert response.status_code == 200


def test_download_ready_redirects(tmp_path):
    """GET /download/<job_id> redirects when job is ready and an S3 URL exists."""
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("<html></html>")
    db_layer = _ReadyDownloadMockDB()
    test_app = create_app(
        dist_dir=str(dist),
        db_layer=db_layer,
        oauth_handler=MockOAuthHandler(),
    )
    test_app.config["TESTING"] = True
    cli = test_app.test_client()
    cli.set_cookie("jwt_token", "mock-token")
    job_id = cli.post(
        "/download/request",
        json={
            "docket_ids": ["CMS-2025-0240"],
            "format": "raw",
            "include_binaries": False,
        },
    ).get_json()["job_id"]
    db_layer._jobs[job_id]["status"] = "ready"
    response = cli.get(f"/download/{job_id}")
    assert response.status_code == 302
    assert response.location == "https://files.example.com/export.zip"


def test_download_ready_without_s3_url_returns_404(tmp_path):
    """Ready job with no S3 URL yields 404."""
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("<html></html>")

    class _NoUrlReadyMock(_ReadyDownloadMockDB):
        def get_download_s3_url(self, job_id, user_email):  # pylint: disable=unused-argument
            return None

    db_layer = _NoUrlReadyMock()
    test_app = create_app(
        dist_dir=str(dist),
        db_layer=db_layer,
        oauth_handler=MockOAuthHandler(),
    )
    test_app.config["TESTING"] = True
    cli = test_app.test_client()
    cli.set_cookie("jwt_token", "mock-token")
    job_id = cli.post(
        "/download/request",
        json={
            "docket_ids": ["CMS-2025-0240"],
            "format": "raw",
            "include_binaries": False,
        },
    ).get_json()["job_id"]
    db_layer._jobs[job_id]["status"] = "ready"
    response = cli.get(f"/download/{job_id}")
    assert response.status_code == 404
    assert response.get_json()["error"] == "Download file not found"


def test_get_dockets_by_ids_endpoint(tmp_path):
    """GET /dockets serializes modify_date and cfr_refs for each requested id."""
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("<html></html>")
    test_app = create_app(
        dist_dir=str(dist),
        db_layer=_DocketsByIdMockDB(),
        oauth_handler=MockOAuthHandler(),
    )
    test_app.config["TESTING"] = True
    cli = test_app.test_client()
    cli.set_cookie("jwt_token", "mock-token")
    response = cli.get("/dockets?docket_id=CMS-2025-0240")
    assert response.status_code == 200
    data = response.get_json()
    assert len(data) == 1
    assert data[0]["docket_id"] == "CMS-2025-0240"
    assert data[0]["modify_date"] == "2024-06-01"
    assert "cfrPart" in data[0]
    assert data[0]["cfrPart"][0]["part"] == "413"


def test_get_dockets_by_ids_empty_returns_empty_list(tmp_path):
    """GET /dockets with no docket_id query params returns []."""
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("<html></html>")
    test_app = create_app(
        dist_dir=str(dist),
        db_layer=_DocketsByIdMockDB(),
        oauth_handler=MockOAuthHandler(),
    )
    test_app.config["TESTING"] = True
    cli = test_app.test_client()
    cli.set_cookie("jwt_token", "mock-token")
    response = cli.get("/dockets")
    assert response.status_code == 200
    assert response.get_json() == []


def test_get_dockets_by_ids_requires_auth(tmp_path):
    """GET /dockets returns 401 without JWT cookie."""
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("<html></html>")
    test_app = create_app(
        dist_dir=str(dist),
        db_layer=_DocketsByIdMockDB(),
        oauth_handler=MockOAuthHandler(),
    )
    test_app.config["TESTING"] = True
    response = test_app.test_client().get("/dockets?docket_id=CMS-2025-0240")
    assert response.status_code == 401


def test_collections_page_route_serves_index(tmp_path):
    """GET /collections serves the SPA index from dist."""
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("<html><body>collections</body></html>")
    test_app = create_app(dist_dir=str(dist), db_layer=MockDBLayer())
    test_app.config["TESTING"] = True
    response = test_app.test_client().get("/collections")
    assert response.status_code == 200
    assert b"collections" in response.data
