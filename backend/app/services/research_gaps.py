from sqlalchemy.orm import Session

from app.models.database import Variant, Evidence, Paper


class ResearchGapDetector:
    def __init__(self, db: Session):
        self.db = db

    def analyze_gaps(self, variant_id: int) -> dict:
        variant = self.db.query(Variant).filter(Variant.id == variant_id).first()
        if not variant:
            return {"gaps": [], "well_studied": False, "summary": "Variant not found."}

        evidence_list = self.db.query(Evidence).filter(Evidence.variant_id == variant_id).all()
        total = len(evidence_list)

        if total == 0:
            return {
                "gaps": [
                    "No published evidence found for this variant",
                    "Functional studies are needed",
                    "Clinical significance requires investigation"
                ],
                "well_studied": False,
                "summary": "This variant has no published evidence. All aspects require investigation."
            }

        high_quality = sum(1 for ev in evidence_list if (ev.evidence_score or 0) >= 0.7)
        clinical_trials = 0
        functional_studies = 0

        paper_types = {}
        years = []
        for ev in evidence_list:
            paper = self.db.query(Paper).filter(Paper.id == ev.paper_id).first()
            if paper:
                st = paper.study_type or "Unknown"
                paper_types[st] = paper_types.get(st, 0) + 1
                if paper.year:
                    years.append(paper.year)
                if st == "Clinical Trial":
                    clinical_trials += 1
                if st == "Functional Study":
                    functional_studies += 1

        gaps = []
        if clinical_trials == 0:
            gaps.append("No clinical trials found for this variant")
        if functional_studies == 0:
            gaps.append("Functional characterization studies are limited")
        if high_quality < 3:
            gaps.append(f"Only {high_quality} high-quality studies available (need 3+ for robust evidence)")
        if total < 5:
            gaps.append(f"Limited evidence volume ({total} papers)")

        if "Case Report" in paper_types and paper_types["Case Report"] > total * 0.5:
            gaps.append("Evidence is predominantly case reports; larger cohort studies needed")

        if years:
            recent = sum(1 for y in years if y >= 2020)
            if recent < 2:
                gaps.append("Recent studies (post-2020) are lacking")

        if not gaps:
            gaps.append("Relatively well-studied; further meta-analyses could strengthen evidence")

        return {
            "gaps": gaps,
            "well_studied": len(gaps) <= 1,
            "summary": self._generate_summary(total, high_quality, gaps),
            "paper_types": paper_types,
            "total_papers": total,
            "high_quality_studies": high_quality,
        }

    def _generate_summary(self, total: int, high_quality: int, gaps: list[str]) -> str:
        if total == 0:
            return "Insufficient evidence. Future research should prioritize basic characterization of this variant."
        if len(gaps) <= 1:
            return (f"Well-characterized variant with {total} papers, "
                    f"including {high_quality} high-quality studies. Further research could "
                    f"focus on meta-analyses and clinical trials.")
        return (f"Moderately studied variant with {total} papers. "
                f"Key gaps: {'; '.join(gaps[:3])}. "
                f"Priority areas: clinical trials and functional studies.")

    def compare_variants(self, gene_symbol: str) -> list[dict]:
        variants = self.db.query(Variant).join(Variant.gene).filter(
            Variant.gene.has(symbol=gene_symbol)
        ).all()

        results = []
        for v in variants:
            ev_count = self.db.query(Evidence).filter(Evidence.variant_id == v.id).count()
            results.append({
                "variant_id": v.id,
                "hgvs_c": v.hgvs_c,
                "protein_change": v.protein_change,
                "evidence_count": ev_count,
                "well_studied": ev_count >= 5,
            })

        results.sort(key=lambda x: x["evidence_count"], reverse=True)
        return results
