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


class TestNewGenes:
    """CHANGE 3: Verify all 6 new genes are accepted by parse_variant."""

    @pytest.mark.parametrize("input_str,gene,change", [
        ("EGFR c.2573T>G", "EGFR", "c.2573T>G"),
        ("KRAS c.35G>A", "KRAS", "c.35G>A"),
        ("ALK c.2920G>A", "ALK", "c.2920G>A"),
        ("BRAF c.1799T>A", "BRAF", "c.1799T>A"),
        ("MLH1 c.350C>T", "MLH1", "c.350C>T"),
        ("MSH2 c.942G>C", "MSH2", "c.942G>C"),
        ("egfr c.2573T>G", "EGFR", "c.2573T>G"),  # lowercase
    ])
    def test_new_genes_parse(self, db_session, input_str, gene, change):
        service = VariantAnalysisService(db_session)
        result = service.parse_variant(input_str)
        assert result is not None
        assert result["gene"] == gene
        assert result["change"] == change

    def test_new_genes_get_or_create(self, db_session):
        service = VariantAnalysisService(db_session)
        for symbol in ["EGFR", "KRAS", "ALK", "BRAF", "MLH1", "MSH2"]:
            gene = service.get_or_create_gene(symbol)
            assert gene.symbol == symbol

    def test_unsupported_gene_rejected(self, db_session):
        service = VariantAnalysisService(db_session)
        result = service.parse_variant("MYC c.1A>G")
        assert result is None


class TestBatchedStudyTypeClassification:
    """CHANGE 1: batched Groq with JSON fallback to keyword matching."""

    @patch("app.services.pubmed_service.PubMedService._batch_infer_study_types")
    def test_batch_fallback_to_keyword(self, mock_batch):
        mock_batch.side_effect = Exception("Groq unavailable")
        from app.services.pubmed_service import PubMedService
        svc = PubMedService()
        papers = [
            {"pmid": "1", "title": "A RCT of drug X",
             "abstract": "Randomized controlled trial with 500 patients showed significant improvement.",
             "keywords": ["clinical trial"]},
            {"pmid": "2", "title": "Case report of rare mutation",
             "abstract": "We report a single patient with a novel BRCA1 variant.",
             "keywords": ["case report"]},
        ]
        types = [svc._infer_study_type(p["abstract"], p["keywords"]) for p in papers]
        assert types[0] in svc.STUDY_TYPES
        assert types[1] in svc.STUDY_TYPES

    @patch("app.services.pubmed_service.PubMedService._batch_infer_study_types")
    def test_batch_returns_correct_count(self, mock_batch):
        mock_batch.side_effect = Exception("Groq unavailable")
        from app.services.pubmed_service import PubMedService
        svc = PubMedService()
        papers = [
            {"pmid": "1", "title": "Study A", "abstract": "Test abstract A", "keywords": []},
            {"pmid": "2", "title": "Study B", "abstract": "Test abstract B", "keywords": []},
        ]
        types = [svc._infer_study_type(p["abstract"], p["keywords"]) for p in papers]
        assert len(types) == 2


class TestConfidenceWeights:
    """CHANGE 2: Verify weights sum to 1.0 and calculation uses new formula."""

    def test_weights_sum_to_one(self, db_session):
        engine = ConfidenceEngine(db_session)
        # pylint: disable=protected-access
        weight_quality = 0.40
        weight_agreement = 0.30
        weight_volume = 0.20
        weight_review = 0.10
        total = weight_quality + weight_agreement + weight_volume + weight_review
        assert abs(total - 1.0) < 0.001

    def test_calculate_confidence_with_review(self, db_session):
        engine = ConfidenceEngine(db_session)
        result = engine._score_clinvar_review("reviewed by expert panel")
        assert result == 1.0
        result_multi = engine._score_clinvar_review("criteria provided, multiple submitters, no conflicts")
        assert result_multi == 0.9
        result_none = engine._score_clinvar_review("")
        assert result_none == 0.0


class TestGnomadService:
    """gnomAD population frequency integration tests."""

    def test_fetch_frequency_no_coordinates(self):
        from app.services.gnomad_service import GnomadService
        svc = GnomadService()
        result = svc.fetch_frequency("TP53", "R175H", None)
        assert result is None

    def test_fetch_frequency_with_coordinates_absent(self):
        from app.services.gnomad_service import GnomadService
        svc = GnomadService()
        result = svc.fetch_frequency("TP53", "R175H", {
            "genomic_coordinates": {"chr": "99", "pos": 1, "ref": "A", "alt": "T"}
        })
        assert result is None

    @patch("app.services.gnomad_service.httpx.post")
    def test_cache_write_and_read(self, mock_post):
        from app.services.gnomad_service import GnomadService
        svc = GnomadService()
        cache_key = "TEST_c.1A>T"
        cache_path = svc._cache_path(cache_key)
        if cache_path.exists():
            cache_path.unlink()

        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            "data": {
                "variant": {
                    "variant_id": "1-100-A-T",
                    "genome": {
                        "af": 0.000023, "ac": 5, "an": 217394,
                        "homozygotes": 0,
                        "populations": [
                            {"id": "afr", "af": 0.0001, "ac": 1, "an": 10000, "homozygotes": 0},
                        ],
                    },
                    "exome": None,
                }
            }
        }

        result = svc.fetch_frequency("TEST", "c.1A>T", {
            "genomic_coordinates": {"chr": "1", "pos": 100, "ref": "A", "alt": "T"}
        })
        assert result is not None
        assert result["allele_frequency"] == 0.000023
        assert result["homozygote_count"] == 0
        assert "afr" in result["population_frequencies"]

        cached = svc._load_cache(cache_key)
        assert cached is not None
        assert cached["allele_frequency"] == 0.000023

        if cache_path.exists():
            cache_path.unlink()
    """PM2 criterion with real gnomAD data."""

    def _build_variant(self, db_session, gnomad_af=None):
        from app.models.database import Gene, Variant
        gene = Gene(symbol="BRCA1", full_name="Test Gene")
        db_session.add(gene)
        db_session.commit()
        variant = Variant(
            gene_id=gene.id,
            hgvs_c="c.123A>G",
            protein_change="p.Lys41Arg",
            clinical_significance="Pathogenic",
            review_status="criteria provided, single submitter",
            variant_type="missense",
            gnomad_af=gnomad_af,
            gnomad_data={"allele_frequency": gnomad_af} if gnomad_af is not None else None,
        )
        db_session.add(variant)
        db_session.commit()
        return variant.id

    def test_pm2_triggers_when_af_below_threshold(self, db_session):
        variant_id = self._build_variant(db_session, gnomad_af=0.00001)
        from app.services.acmg_service import ACMGService
        acmg = ACMGService(db_session)
        result = acmg.classify(variant_id)
        codes = [c["code"] for c in result["criteria"]]
        assert "PM2" in codes
        pm2 = [c for c in result["criteria"] if c["code"] == "PM2"][0]
        assert "gnomAD" in pm2["evidence"]

    def test_pm2_triggers_when_absent_from_gnomad(self, db_session):
        variant_id = self._build_variant(db_session, gnomad_af=None)
        from app.services.acmg_service import ACMGService
        acmg = ACMGService(db_session)
        result = acmg.classify(variant_id)
        codes = [c["code"] for c in result["criteria"]]
        assert "PM2" in codes
        pm2 = [c for c in result["criteria"] if c["code"] == "PM2"][0]
        assert "absent" in pm2["evidence"].lower()

    def test_pm2_not_triggered_when_af_above_threshold(self, db_session):
        variant_id = self._build_variant(db_session, gnomad_af=0.005)
        from app.services.acmg_service import ACMGService
        acmg = ACMGService(db_session)
        result = acmg.classify(variant_id)
        codes = [c["code"] for c in result["criteria"]]
        assert "PM2" not in codes


class TestGnomadPipeline:
    """gnomAD integration in variant pipeline."""

    def test_gnomad_field_stored_after_pipeline(self, db_session):
        from app.services.variant_service import VariantAnalysisService
        from unittest.mock import patch, MagicMock

        mock_clinvar = MagicMock()
        mock_clinvar.fetch_variant_data.return_value = {
            "clinvar_id": "12345",
            "clinical_significance": "Pathogenic",
            "review_status": "criteria provided, single submitter",
            "genomic_coordinates": {"chr": "17", "pos": 41242954, "ref": "C", "alt": "T"},
        }
        mock_pubmed = MagicMock()
        mock_pubmed.search_papers.return_value = []
        mock_gnomad = MagicMock()
        mock_gnomad.fetch_frequency.return_value = {
            "allele_frequency": 0.000023,
            "allele_count": 5,
            "allele_number": 217394,
            "homozygote_count": 0,
            "population_frequencies": {},
        }

        from app.models.database import Variant, Gene

        service = VariantAnalysisService(db_session)
        service.clinvar = mock_clinvar
        service.pubmed = mock_pubmed
        service.gnomad = mock_gnomad

        result = service.analyze_variant("BRCA1 c.5266dupC")
        assert result is not None

        variant = result["variant"]
        db_session.refresh(variant)
        assert variant.gnomad_af == 0.000023
        assert variant.gnomad_data is not None
