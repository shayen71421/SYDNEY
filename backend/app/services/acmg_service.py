from sqlalchemy.orm import Session
from app.models.database import Variant, Gene, Evidence, Paper


class ACMGService:
    def __init__(self, db: Session):
        self.db = db

    def classify(self, variant_id: int) -> dict:
        variant = self.db.query(Variant).filter(Variant.id == variant_id).first()
        if not variant:
            return {"criteria": [], "classification": "Not evaluated", "summary": "Variant not found"}

        gene = self.db.query(Gene).filter(Gene.id == variant.gene_id).first()
        evidence_list = self.db.query(Evidence).filter(Evidence.variant_id == variant_id).all()
        total_papers = len(evidence_list)
        variant_type = (variant.variant_type or "").lower()
        hgvs_c = variant.hgvs_c or ""
        protein_change = variant.protein_change or ""
        clin_sig = (variant.clinical_significance or "").lower()
        review_status = (variant.review_status or "").lower()

        criteria = []
        strengths = {"Very Strong": 4, "Strong": 3, "Moderate": 2, "Supporting": 1}

        pathogenic_score = 0
        benign_score = 0

        if self._is_null_variant(variant_type, hgvs_c, protein_change):
            criteria.append({
                "code": "PVS1",
                "strength": "Very Strong",
                "description": "Null variant (nonsense, frameshift, canonical splice) in a gene where LOF is a known mechanism of disease",
                "evidence": f"Variant type: {variant.variant_type or 'null variant'}",
                "classification": "Pathogenic",
            })
            pathogenic_score += strengths["Very Strong"]

        if "pathogenic" in clin_sig:
            if "expert panel" in review_status or "multiple submitters" in review_status:
                criteria.append({
                    "code": "PS1",
                    "strength": "Strong",
                    "description": "Same amino acid change as previously established pathogenic variant regardless of nucleotide change",
                    "evidence": f"ClinVar: {variant.clinical_significance}, Review: {variant.review_status}",
                    "classification": "Pathogenic",
                })
                pathogenic_score += strengths["Strong"]
            elif "conflicting" not in clin_sig:
                criteria.append({
                    "code": "PM2",
                    "strength": "Moderate",
                    "description": "Absent from population databases (or at extremely low frequency if recessive)",
                    "evidence": f"ClinVar classification: {variant.clinical_significance}",
                    "classification": "Pathogenic",
                })
                pathogenic_score += strengths["Moderate"]

        if variant_type in ("missense", "snv") and "pathogenic" in clin_sig and "conflicting" not in clin_sig:
            criteria.append({
                "code": "PP3",
                "strength": "Supporting",
                "description": "Multiple lines of computational evidence support a deleterious effect on the gene or gene product",
                "evidence": f"Missense variant classified as {variant.clinical_significance}",
                "classification": "Pathogenic",
            })
            pathogenic_score += strengths["Supporting"]

        if ("del" in variant_type or "ins" in variant_type) and "frameshift" not in variant_type:
            criteria.append({
                "code": "PM4",
                "strength": "Moderate",
                "description": "Protein length changes due to in-frame deletions/insertions in a non-repeat region",
                "evidence": f"Variant type: {variant.variant_type}",
                "classification": "Pathogenic",
            })
            pathogenic_score += strengths["Moderate"]

        if total_papers >= 5:
            criteria.append({
                "code": "PP4",
                "strength": "Supporting",
                "description": "Patient's phenotype or family history is highly specific for a disease with a single genetic etiology",
                "evidence": f"Supported by {total_papers} publications",
                "classification": "Pathogenic",
            })
            pathogenic_score += strengths["Supporting"]

        if total_papers >= 10:
            criteria.append({
                "code": "PS4",
                "strength": "Strong",
                "description": "Prevalence in affected individuals is significantly increased compared to controls",
                "evidence": f"Well-studied variant with {total_papers} supporting publications",
                "classification": "Pathogenic",
            })
            pathogenic_score += strengths["Strong"]

        if "benign" in clin_sig:
            criteria.append({
                "code": "BS1",
                "strength": "Strong",
                "description": "Allele frequency is greater than expected for disorder",
                "evidence": f"ClinVar: {variant.clinical_significance}",
                "classification": "Benign",
            })
            benign_score += strengths["Strong"]

        if "likely benign" in clin_sig:
            criteria.append({
                "code": "BP4",
                "strength": "Supporting",
                "description": "Multiple lines of computational evidence suggest no impact on gene or gene product",
                "evidence": f"ClinVar: {variant.clinical_significance}",
                "classification": "Benign",
            })
            benign_score += strengths["Supporting"]

        if total_papers == 0:
            criteria.append({
                "code": "PM2",
                "strength": "Moderate",
                "description": "Absent from population databases (no publications found)",
                "evidence": "No supporting publications identified",
                "classification": "Pathogenic",
            })
            pathogenic_score += strengths["Moderate"]

        point_mapping = [
            (10, "Pathogenic"),
            (6, "Likely pathogenic"),
            (4, "Uncertain significance"),
            (-2, "Likely benign"),
            (-6, "Benign"),
        ]

        net_score = pathogenic_score - benign_score
        if net_score <= 0 and benign_score > 0:
            if benign_score >= 6:
                classification = "Benign"
            elif benign_score >= 2:
                classification = "Likely benign"
            else:
                classification = "Uncertain significance"
        else:
            if pathogenic_score >= 10:
                classification = "Pathogenic"
            elif pathogenic_score >= 6:
                classification = "Likely pathogenic"
            else:
                classification = "Uncertain significance"

        pathogenic_criteria = [c for c in criteria if c["classification"] == "Pathogenic"]
        benign_criteria = [c for c in criteria if c["classification"] == "Benign"]

        summary_parts = []
        if pathogenic_criteria:
            codes = ", ".join(c["code"] for c in pathogenic_criteria)
            summary_parts.append(f"Pathogenic: {codes} (score {pathogenic_score})")
        if benign_criteria:
            codes = ", ".join(c["code"] for c in benign_criteria)
            summary_parts.append(f"Benign: {codes} (score {benign_score})")
        summary = "; ".join(summary_parts) if summary_parts else "No ACMG criteria met"

        return {
            "criteria": criteria,
            "classification": classification,
            "pathogenic_score": pathogenic_score,
            "benign_score": benign_score,
            "net_score": net_score,
            "summary": summary,
            "total_evidence_papers": total_papers,
        }

    def _is_null_variant(self, variant_type: str, hgvs_c: str, protein_change: str = "") -> bool:
        if variant_type in ("frameshift", "nonsense", "stop_gained", "splice_site"):
            return True
        null_keywords = ["del", "ins", "dup", "fs", "ter", "*"]
        variant_str = f"{hgvs_c} {protein_change}".lower()
        if any(kw in variant_str for kw in null_keywords):
            if variant_type == "missense":
                return False
            return True
        return False
