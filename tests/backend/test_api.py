"""Tests for API routes with full pipeline verification."""

import pytest
from unittest.mock import patch, MagicMock
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


class TestPipelineIntegration:
    """Full pipeline integration tests with mocked external services."""

    @patch("app.services.clinvar_service.ClinVarService.fetch_variant_data")
    @patch("app.services.pubmed_service.PubMedService.search_papers")
    def test_full_search_pipeline(self, mock_pubmed, mock_clinvar):
        mock_clinvar.return_value = {
            "clinical_significance": "Pathogenic",
            "clinvar_id": "VCV000012374",
            "review_status": "criteria provided, multiple submitters, no conflicts",
            "description": "This pathogenic variant is associated with breast cancer.",
            "diseases": ["Breast Cancer", "Ovarian Cancer"],
        }
        mock_pubmed.return_value = [
            {
                "pmid": "12345678",
                "title": "BRCA1 variant study",
                "authors": "Author A et al.",
                "journal": "Nature Genetics",
                "year": 2022,
                "abstract": "This study examines the BRCA1 c.5266dupC variant.",
                "doi": "10.1000/xyz",
                "study_type": "Cohort Study",
                "keywords": ["BRCA1", "mutation", "breast cancer"],
            },
            {
                "pmid": "23456789",
                "title": "Functional analysis of BRCA1 variants",
                "authors": "Author B et al.",
                "journal": "Cell Reports",
                "year": 2023,
                "abstract": "Functional characterization of pathogenic BRCA1 variants.",
                "doi": "10.1000/abc",
                "study_type": "Functional Study",
                "keywords": ["BRCA1", "functional", "DNA repair"],
            },
        ]

        response = client.post(
            "/api/v1/variants/search",
            json={"query": "BRCA1 c.5266dupC"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["gene"] == "BRCA1"
        assert data["clinical_significance"] == "Pathogenic"
        assert data["clinvar_id"] == "VCV000012374"
        assert "c.5266dupC" in data["hgvs_c"]
        mock_clinvar.assert_called_once()
        mock_pubmed.assert_called_once()

    @patch("app.services.clinvar_service.ClinVarService.fetch_variant_data")
    @patch("app.services.pubmed_service.PubMedService.search_papers")
    def test_tp53_search_pipeline(self, mock_pubmed, mock_clinvar):
        mock_clinvar.return_value = {
            "clinical_significance": "Pathogenic",
            "clinvar_id": "VCV000012345",
            "review_status": "reviewed by expert panel",
            "description": "Hotspot mutation in TP53.",
            "diseases": ["Li-Fraumeni Syndrome", "Breast Cancer"],
        }
        mock_pubmed.return_value = [
            {
                "pmid": "34567890",
                "title": "TP53 R175H functional impact",
                "authors": "Author C et al.",
                "journal": "Cancer Research",
                "year": 2021,
                "abstract": "Analysis of TP53 R175H hotspot mutation.",
                "doi": "10.1000/def",
                "study_type": "Functional Study",
                "keywords": ["TP53", "R175H", "p53"],
            }
        ]

        response = client.post(
            "/api/v1/variants/search",
            json={"query": "TP53 R175H"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["gene"] == "TP53"
        assert data["clinical_significance"] == "Pathogenic"

    @patch("app.services.clinvar_service.ClinVarService.fetch_variant_data")
    @patch("app.services.pubmed_service.PubMedService.search_papers")
    def test_compare_endpoint(self, mock_pubmed, mock_clinvar):
        def clinvar_side_effect(gene, change):
            return {
                "clinical_significance": "Pathogenic",
                "clinvar_id": "VCV000012374",
                "review_status": "multiple submitters",
                "description": f"{gene} {change} variant",
                "diseases": ["Breast Cancer"],
            }

        def pubmed_side_effect(gene, change):
            return [
                {
                    "pmid": "12345678",
                    "title": f"Study of {gene} {change}",
                    "authors": "Author A",
                    "journal": "Journal",
                    "year": 2022,
                    "abstract": f"Study of {gene} {change} variant.",
                    "doi": "10.1000/xyz",
                    "study_type": "Cohort Study",
                    "keywords": [gene],
                }
            ]

        mock_clinvar.side_effect = clinvar_side_effect
        mock_pubmed.side_effect = pubmed_side_effect

        response = client.post(
            "/api/v1/compare",
            json={"query1": "TP53 R175H", "query2": "TP53 R273H"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "variant1" in data
        assert "variant2" in data
        assert data["variant1"]["gene"] == "TP53"
        assert data["variant2"]["gene"] == "TP53"

    def test_publication_trends_not_found(self):
        response = client.get("/api/v1/variants/99999/publications/trends")
        assert response.status_code == 404

    def test_why_matters_not_found(self):
        response = client.post("/api/v1/variants/99999/why-matters")
        assert response.status_code == 404

    @patch("app.services.clinvar_service.ClinVarService.fetch_variant_data")
    @patch("app.services.pubmed_service.PubMedService.search_papers")
    def test_full_pipeline_data_integrity(self, mock_pubmed, mock_clinvar):
        mock_clinvar.return_value = {
            "clinical_significance": "Pathogenic",
            "clinvar_id": "VCV000012374",
            "review_status": "multiple submitters",
            "description": "Pathogenic BRCA1 variant.",
            "diseases": ["Breast Cancer"],
        }
        mock_pubmed.return_value = [
            {
                "pmid": str(10000000 + i),
                "title": f"BRCA1 study {i}",
                "authors": "Author",
                "journal": "Journal",
                "year": 2020 + (i % 5),
                "abstract": f"Abstract for study {i}.",
                "doi": f"10.1000/study{i}",
                "study_type": t,
                "keywords": ["BRCA1"],
            }
            for i, t in enumerate([
                "Meta-Analysis", "Clinical Trial", "Cohort Study",
                "Case-Control Study", "Functional Study", "Review",
                "Case Report", "Systematic Review",
            ])
        ]

        response = client.post(
            "/api/v1/variants/search",
            json={"query": "BRCA1 c.5266dupC"}
        )
        assert response.status_code == 200

        variant_id = response.json()["id"]

        evidence_resp = client.get(f"/api/v1/variants/{variant_id}/evidence")
        assert evidence_resp.status_code == 200
        evidence = evidence_resp.json()
        assert len(evidence) > 0
        for ev in evidence:
            assert "evidence_score" in ev
            assert "relevance_score" in ev
            assert "study_quality_score" in ev
            assert "recency_score" in ev

        report_resp = client.get(f"/api/v1/variants/{variant_id}/report")
        assert report_resp.status_code == 200
        report = report_resp.json()
        assert "confidence_level" in report
        assert "confidence_score" in report
        assert "evidence_volume" in report
        assert "evidence_quality" in report
        assert "study_agreement" in report
