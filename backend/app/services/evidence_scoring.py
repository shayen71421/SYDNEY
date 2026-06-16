from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.database import Variant, Evidence, Paper


class EvidenceScoringService:
    STUDY_QUALITY = {
        "Meta-Analysis": 0.95,
        "Clinical Trial": 0.90,
        "Systematic Review": 0.90,
        "Cohort Study": 0.75,
        "Case-Control Study": 0.65,
        "Genome-Wide Study": 0.80,
        "Functional Study": 0.70,
        "Review": 0.50,
        "Case Report": 0.35,
        "Research Article": 0.50,
    }

    def __init__(self, db: Session):
        self.db = db

    def score_evidence_for_variant(self, variant_id: int):
        evidence_list = self.db.query(Evidence).filter(Evidence.variant_id == variant_id).all()
        current_year = 2026

        for ev in evidence_list:
            paper = self.db.query(Paper).filter(Paper.id == ev.paper_id).first()
            if not paper:
                continue

            relevance = ev.relevance_score or self._calculate_relevance(paper, ev)

            study_quality = self.STUDY_QUALITY.get(paper.study_type, 0.50)

            if paper.year:
                years_old = current_year - paper.year
                recency = max(0, 1.0 - (years_old * 0.05))
            else:
                recency = 0.3

            ev.relevance_score = round(relevance, 4)
            ev.study_quality_score = round(study_quality, 4)
            ev.recency_score = round(recency, 4)

            evidence_score = (0.50 * relevance) + (0.30 * study_quality) + (0.20 * recency)
            ev.evidence_score = round(min(1.0, evidence_score), 4)

        self.db.commit()
        return evidence_list

    def _calculate_relevance(self, paper: Paper, evidence: Evidence) -> float:
        score = 0.5
        if paper.abstract and evidence.key_findings:
            keyword_overlap = 0
            keywords = set(paper.keywords or [])
            for kw in keywords:
                if kw.lower() in evidence.key_findings.lower():
                    keyword_overlap += 1
            if keywords:
                score += min(0.5, keyword_overlap / len(keywords) * 0.5)
        return min(1.0, score)

    def get_top_evidence(self, variant_id: int, limit: int = 10) -> list[dict]:
        evidence_list = self.db.query(Evidence).filter(
            Evidence.variant_id == variant_id
        ).order_by(Evidence.evidence_score.desc()).limit(limit).all()

        results = []
        for ev in evidence_list:
            paper = self.db.query(Paper).filter(Paper.id == ev.paper_id).first()
            results.append({
                "id": ev.id,
                "pmid": paper.pmid if paper else "",
                "title": paper.title if paper else "",
                "authors": paper.authors if paper else "",
                "journal": paper.journal if paper else "",
                "year": paper.year if paper else None,
                "abstract": paper.abstract if paper else "",
                "evidence_type": ev.evidence_type,
                "relevance_score": ev.relevance_score,
                "study_quality_score": ev.study_quality_score,
                "recency_score": ev.recency_score,
                "evidence_score": ev.evidence_score,
                "key_findings": ev.key_findings,
            })

        return results
