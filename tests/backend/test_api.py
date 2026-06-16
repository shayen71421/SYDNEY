"""Tests for API routes."""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.db.migrations import run_migrations


@pytest.fixture(scope="session", autouse=True)
def setup_db():
    run_migrations()
    yield


client = TestClient(app)


class TestAPI:
    def test_health_check(self):
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["app"] == "Sydney"

    def test_dashboard(self):
        response = client.get("/api/v1/dashboard")
        assert response.status_code == 200
        data = response.json()
        assert "total_variants" in data
        assert "total_papers" in data
        assert "total_genes" in data

    def test_search_invalid_variant(self):
        response = client.post(
            "/api/v1/variants/search",
            json={"query": "invalid"}
        )
        assert response.status_code == 400

    def test_search_empty_query(self):
        response = client.post(
            "/api/v1/variants/search",
            json={"query": ""}
        )
        assert response.status_code == 422

    def test_variant_not_found(self):
        response = client.get("/api/v1/variants/99999")
        assert response.status_code == 404

    def test_list_variants(self):
        response = client.get("/api/v1/variants")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_list_variants_with_gene(self):
        response = client.get("/api/v1/variants?gene=BRCA1")
        assert response.status_code == 200

    def test_evidence_empty(self):
        response = client.get("/api/v1/variants/99999/evidence")
        assert response.status_code == 404

    def test_report_empty(self):
        response = client.get("/api/v1/variants/99999/report")
        assert response.status_code == 404

    def test_graph_empty(self):
        response = client.get("/api/v1/graph/99999")
        assert response.status_code == 404

    def test_gaps_empty(self):
        response = client.get("/api/v1/variants/99999/gaps")
        assert response.status_code == 404

    def test_openapi_docs(self):
        response = client.get("/docs")
        assert response.status_code in (200, 307)

    def test_openapi_schema(self):
        response = client.get("/openapi.json")
        assert response.status_code == 200
        assert "paths" in response.json()
