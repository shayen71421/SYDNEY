import re
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.database import Variant, Gene, Evidence, Paper
from app.services.clinvar_service import ClinVarService
from app.services.pubmed_service import PubMedService


class VariantAnalysisService:
    GENE_ALIASES = {
        "brca1": "BRCA1", "brca1": "BRCA1",
        "brca2": "BRCA2", "brca2": "BRCA2",
        "tp53": "TP53", "tp53": "TP53", "p53": "TP53",
        "cdh1": "CDH1", "cdh1": "CDH1",
        "palb2": "PALB2", "palb2": "PALB2",
        "chek2": "CHEK2", "chek2": "CHEK2",
        "atm": "ATM", "atm": "ATM",
        "pten": "PTEN", "pten": "PTEN",
    }

    def __init__(self, db: Session):
        self.db = db
        self.clinvar = ClinVarService()
        self.pubmed = PubMedService()

    def parse_variant(self, query: str) -> Optional[dict]:
        query = query.strip()
        if not query:
            return None

        gene_alt = "BRCA1|BRCA2|TP53|P53|CDH1|PALB2|CHEK2|ATM|PTEN"
        patterns = [
            (rf"^({gene_alt})\s+(c\.\d+[A-Za-z_>delinsup*]{{1,30}})$", None),
            (rf"^({gene_alt})\s+(p\.[A-Za-z]{{1,3}}\d+[A-Za-z*]{{1,5}})$", None),
            (rf"^({gene_alt})\s+([A-Z][a-z]{{2}}\d+[A-Za-z*]{{1,5}})$", None),
            (rf"^({gene_alt})\s+([A-Z]\d+[A-Z*]{{1,3}})$", None),
            (rf"^({gene_alt})\s+(\d+del[A-Z]+)$", None),
            (rf"^({gene_alt})\s+(\d+ins[A-Z]+)$", None),
        ]

        for pattern, _ in patterns:
            m = re.match(pattern, query, re.IGNORECASE)
            if m:
                gene = m.group(1).upper()
                change = m.group(2)
                if gene == "P53":
                    gene = "TP53"
                return {"gene": gene, "change": change, "original": query}

        return None

    def get_or_create_gene(self, symbol: str) -> Gene:
        gene = self.db.query(Gene).filter(func.lower(Gene.symbol) == symbol.lower()).first()
        if not gene:
            gene_data = {
                "BRCA1": ("BRCA1", "Breast Cancer Gene 1", "17", "Tumor suppressor gene involved in DNA repair"),
                "BRCA2": ("BRCA2", "Breast Cancer Gene 2", "13", "Tumor suppressor gene involved in DNA repair"),
                "TP53": ("TP53", "Tumor Protein P53", "17", "Tumor suppressor gene regulating cell cycle"),
                "CDH1": ("CDH1", "Cadherin 1", "16", "Cell adhesion protein; germline mutations cause hereditary diffuse gastric cancer"),
                "PALB2": ("PALB2", "Partner And Localizer of BRCA2", "16", "Fanconi anemia group N protein; BRCA2-interacting partner for DNA repair"),
                "CHEK2": ("CHEK2", "Checkpoint Kinase 2", "22", "Cell cycle checkpoint kinase involved in DNA damage response"),
                "ATM": ("ATM", "ATM Serine/Threonine Kinase", "11", "DNA damage response kinase; master regulator of double-strand break repair"),
                "PTEN": ("PTEN", "Phosphatase and Tensin Homolog", "10", "Tumor suppressor phosphatase; negative regulator of PI3K/AKT pathway"),
            }
            info = gene_data.get(symbol.upper(), (symbol.upper(), symbol.upper(), "", ""))
            gene = Gene(symbol=info[0], full_name=info[1], chromosome=info[2], description=info[3])
            self.db.add(gene)
            self.db.commit()
            self.db.refresh(gene)
        return gene

    def analyze_variant(self, query: str) -> Optional[dict]:
        parsed = self.parse_variant(query)
        if not parsed:
            return None

        gene = self.get_or_create_gene(parsed["gene"])

        variant = self.db.query(Variant).filter(
            Variant.gene_id == gene.id,
            (Variant.hgvs_c == parsed["change"]) | (Variant.protein_change == parsed["change"])
        ).first()

        if not variant:
            variant = Variant(
                gene_id=gene.id,
                hgvs_c=parsed["change"] if parsed["change"].startswith("c.") else None,
                protein_change=parsed["change"] if not parsed["change"].startswith("c.") else None,
                variant_type="snv",
            )
            self.db.add(variant)
            self.db.commit()
            self.db.refresh(variant)

        clinvar_data = self.clinvar.fetch_variant_data(parsed["gene"], parsed["change"])
        if clinvar_data:
            variant.clinical_significance = clinvar_data.get("clinical_significance")
            variant.clinvar_id = clinvar_data.get("clinvar_id")
            variant.review_status = clinvar_data.get("review_status")
            variant.clinvar_data = clinvar_data
            variant.description = clinvar_data.get("description")
            self.db.commit()

        papers = self.pubmed.search_papers(parsed["gene"], parsed["change"])
        for paper_data in papers:
            existing = self.db.query(Paper).filter(Paper.pmid == paper_data["pmid"]).first()
            if not existing:
                paper = Paper(**paper_data)
                self.db.add(paper)
                self.db.commit()
                self.db.refresh(paper)
                existing = paper

            evidence_exists = self.db.query(Evidence).filter(
                Evidence.variant_id == variant.id,
                Evidence.paper_id == existing.id
            ).first()
            if not evidence_exists:
                evidence = Evidence(
                    variant_id=variant.id,
                    paper_id=existing.id,
                    evidence_type="literature",
                    source="PubMed",
                    key_findings=paper_data.get("abstract", "")[:500] if paper_data.get("abstract") else "",
                )
                self.db.add(evidence)
                self.db.commit()

        return {"variant": variant, "gene": gene}

    def get_variant_detail(self, variant_id: int) -> Optional[dict]:
        variant = self.db.query(Variant).filter(Variant.id == variant_id).first()
        if not variant:
            return None
        gene = self.db.query(Gene).filter(Gene.id == variant.gene_id).first()
        evidence_list = self.db.query(Evidence).filter(Evidence.variant_id == variant_id).all()
        papers_list = []
        for ev in evidence_list:
            paper = self.db.query(Paper).filter(Paper.id == ev.paper_id).first()
            if paper:
                papers_list.append({
                    "evidence_id": ev.id,
                    "pmid": paper.pmid,
                    "title": paper.title,
                    "authors": paper.authors,
                    "journal": paper.journal,
                    "year": paper.year,
                    "abstract": paper.abstract,
                    "evidence_type": ev.evidence_type,
                    "relevance_score": ev.relevance_score,
                    "study_quality_score": ev.study_quality_score,
                    "recency_score": ev.recency_score,
                    "evidence_score": ev.evidence_score,
                    "key_findings": ev.key_findings,
                })

        return {
            "variant": variant,
            "gene": gene,
            "evidence": papers_list,
        }
