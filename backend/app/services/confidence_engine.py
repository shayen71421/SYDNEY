import math
from sqlalchemy.orm import Session

from app.models.database import Variant, Evidence, Paper, Report
from app.services.evidence_scoring import EvidenceScoringService


class ConfidenceEngine:
    def __init__(self, db: Session):
        self.db = db
        self.scoring = EvidenceScoringService(db)

    def calculate_confidence(self, variant_id: int) -> dict:
        evidence_list = self.db.query(Evidence).filter(Evidence.variant_id == variant_id).all()
        variant = self.db.query(Variant).filter(Variant.id == variant_id).first()
        total_papers = len(evidence_list)

        if total_papers == 0:
            return {
                "level": "Insufficient Evidence",
                "score": 0.0,
                "evidence_volume": 0,
                "evidence_quality": 0.0,
                "study_agreement": 0.0,
                "clinvar_review_strength": 0.0,
                "reasoning": "No supporting evidence found for this variant."
            }

        scores = [ev.evidence_score for ev in evidence_list if ev.evidence_score]
        qualities = [ev.study_quality_score for ev in evidence_list if ev.study_quality_score]

        evidence_volume_score = self._score_volume(total_papers)
        evidence_quality_score = sum(qualities) / len(qualities) if qualities else 0.0

        study_agreement = self._calculate_agreement(evidence_list)
        clinvar_review_strength = self._score_clinvar_review(variant.review_status if variant else "")

        confidence_score = (
            0.25 * evidence_volume_score +
            0.35 * evidence_quality_score +
            0.25 * study_agreement +
            0.15 * clinvar_review_strength
        )

        if confidence_score >= 0.7:
            level = "High"
        elif confidence_score >= 0.4:
            level = "Moderate"
        else:
            level = "Low"

        reasoning_parts = []
        reasoning_parts.append(f"Based on {total_papers} supporting papers")
        reasoning_parts.append(f"evidence volume score: {evidence_volume_score:.2f}")
        reasoning_parts.append(f"average study quality: {evidence_quality_score:.2f}")
        reasoning_parts.append(f"study agreement: {study_agreement:.2f}")
        reasoning_parts.append(f"ClinVar review strength: {clinvar_review_strength:.2f}")

        return {
            "level": level,
            "score": round(confidence_score, 4),
            "evidence_volume": total_papers,
            "evidence_quality": round(evidence_quality_score, 4),
            "study_agreement": round(study_agreement, 4),
            "clinvar_review_strength": round(clinvar_review_strength, 4),
            "reasoning": "; ".join(reasoning_parts)
        }

    def _score_volume(self, count: int) -> float:
        if count >= 20:
            return 1.0
        if count >= 10:
            return 0.8
        if count >= 5:
            return 0.6
        if count >= 3:
            return 0.4
        if count >= 1:
            return 0.2
        return 0.0

    def _score_clinvar_review(self, review_status: str) -> float:
        status = review_status.lower().strip() if review_status else ""
        mapping = {
            "reviewed by expert panel": 1.0,
            "criteria provided, multiple submitters, no conflicts": 0.9,
            "criteria provided, single submitter": 0.7,
            "criteria provided, conflicting interpretations": 0.5,
            "no assertion criteria provided": 0.3,
            "no assertion": 0.0,
            "no assertion provided": 0.0,
        }
        return mapping.get(status, 0.0)

    def _calculate_agreement(self, evidence_list: list) -> float:
        if not evidence_list:
            return 0.0

        sig_map = {}
        for ev in evidence_list:
            variant = self.db.query(Variant).filter(Variant.id == ev.variant_id).first()
            sig = (variant.clinical_significance or "Unknown") if variant else "Unknown"
            sig_map[ev.id] = sig

        if not sig_map:
            return 0.0

        sig_counts = {}
        for sig in sig_map.values():
            sig_counts[sig] = sig_counts.get(sig, 0) + 1

        max_sig_count = max(sig_counts.values())
        agreement = max_sig_count / len(sig_map)

        return agreement

    def generate_report(self, variant_id: int) -> Report:
        variant = self.db.query(Variant).filter(Variant.id == variant_id).first()
        if not variant:
            raise ValueError("Variant not found")

        self.scoring.score_evidence_for_variant(variant_id)
        confidence = self.calculate_confidence(variant_id)

        top_evidence = self.scoring.get_top_evidence(variant_id, 10)

        existing = self.db.query(Report).filter(Report.variant_id == variant_id).first()
        if existing:
            return existing

        report = Report(
            variant_id=variant_id,
            confidence_level=confidence["level"],
            confidence_score=confidence["score"],
            evidence_volume=confidence["evidence_volume"],
            evidence_quality=confidence["evidence_quality"],
            study_agreement=confidence["study_agreement"],
            clinvar_review_strength=confidence.get("clinvar_review_strength", 0.0),
            evidence_overview=f"Found {confidence['evidence_volume']} supporting papers. "
                              f"Average evidence score: {confidence['evidence_quality']:.2f}. "
                              f"Confidence level: {confidence['level']}.",
        )
        self.db.add(report)
        self.db.commit()
        self.db.refresh(report)

        return report
