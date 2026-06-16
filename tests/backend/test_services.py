"""Tests for backend services."""

import pytest
from unittest.mock import patch, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.database import Base, Variant, Gene, Paper, Evidence
from app.services.variant_service import VariantAnalysisService
from app.services.evidence_scoring import EvidenceScoringService
from app.services.confidence_engine import ConfidenceEngine
from app.services.research_gaps import ResearchGapDetector


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


class TestVariantAnalysisService:
    def test_parse_brca1_hgvs(self, db_session):
        service = VariantAnalysisService(db_session)
        result = service.parse_variant("BRCA1 c.5266dupC")
        assert result is not None
        assert result["gene"] == "BRCA1"
        assert result["change"] == "c.5266dupC"

    def test_parse_tp53_protein(self, db_session):
        service = VariantAnalysisService(db_session)
        result = service.parse_variant("TP53 R175H")
        assert result is not None
        assert result["gene"] == "TP53"
        assert result["change"] == "R175H"

    def test_parse_invalid(self, db_session):
        service = VariantAnalysisService(db_session)
        result = service.parse_variant("invalid query here")
        assert result is None

    def test_parse_lowercase(self, db_session):
        service = VariantAnalysisService(db_session)
        result = service.parse_variant("brca2 c.5946delT")
        assert result is not None
        assert result["gene"] == "BRCA2"

    def test_parse_p53_alias(self, db_session):
        service = VariantAnalysisService(db_session)
        result = service.parse_variant("P53 R273H")
        assert result is not None
        assert result["gene"] == "TP53"

    def test_get_or_create_gene_new(self, db_session):
        service = VariantAnalysisService(db_session)
        gene = service.get_or_create_gene("BRCA1")
        assert gene.symbol == "BRCA1"
        assert gene.full_name == "Breast Cancer Gene 1"

    def test_get_or_create_gene_existing(self, db_session):
        service = VariantAnalysisService(db_session)
        gene1 = service.get_or_create_gene("BRCA1")
        gene2 = service.get_or_create_gene("BRCA1")
        assert gene1.id == gene2.id


class TestEvidenceScoringService:
    def test_score_evidence_empty(self, db_session):
        scoring = EvidenceScoringService(db_session)
        result = scoring.score_evidence_for_variant(999)
        assert result == []

    def test_calculate_relevance(self, db_session):
        paper = Paper(pmid="12345", title="Test", abstract="BRCA1 mutation study",
                       keywords=["BRCA1", "mutation"])
        db_session.add(paper)
        db_session.commit()

        evidence = Evidence(
            variant_id=1, paper_id=paper.id,
            evidence_type="literature", key_findings="BRCA1 mutation in breast cancer"
        )
        db_session.add(evidence)
        db_session.commit()

        scoring = EvidenceScoringService(db_session)
        score = scoring._calculate_relevance(paper, evidence)
        assert 0.5 <= score <= 1.0

    def test_study_quality_mapping(self, db_session):
        scoring = EvidenceScoringService(db_session)
        assert scoring.STUDY_QUALITY["Meta-Analysis"] == 0.95
        assert scoring.STUDY_QUALITY["Case Report"] == 0.35
        assert scoring.STUDY_QUALITY.get("Unknown", 0.50) == 0.50


class TestConfidenceEngine:
    def test_no_evidence(self, db_session):
        engine = ConfidenceEngine(db_session)
        result = engine.calculate_confidence(999)
        assert result["level"] == "Insufficient Evidence"
        assert result["score"] == 0.0

    def test_score_volume_thresholds(self, db_session):
        engine = ConfidenceEngine(db_session)
        assert engine._score_volume(0) == 0.0
        assert engine._score_volume(1) == 0.2
        assert engine._score_volume(20) == 1.0


class TestResearchGapDetector:
    def test_no_variant(self, db_session):
        detector = ResearchGapDetector(db_session)
        result = detector.analyze_gaps(999)
        assert result["well_studied"] is False
        assert "Variant not found" in result["summary"]

    def test_no_evidence_gaps(self, db_session):
        gene = Gene(symbol="BRCA1", full_name="Test")
        db_session.add(gene)
        db_session.commit()

        variant = Variant(gene_id=gene.id, hgvs_c="c.123A>G")
        db_session.add(variant)
        db_session.commit()

        detector = ResearchGapDetector(db_session)
        result = detector.analyze_gaps(variant.id)
        assert len(result["gaps"]) > 0
        assert result["well_studied"] is False
