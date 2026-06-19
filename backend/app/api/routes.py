from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional
from datetime import datetime
from pathlib import Path

from app.models.database import Variant, Gene, Evidence, Paper, Disease, Report as ReportModel
from app.models.schemas import (
    VariantSearchRequest, VariantSearchResponse, VariantDetailResponse,
    EvidenceResponse, ReportResponse, DashboardStats, GraphData,
    SearchHistoryResponse, ErrorResponse,
    CompareRequest, CompareResponse, CompareVariantData,
    PublicationTrend, PublicationTrendsResponse,
    EvidenceProvenanceResponse, EvidenceProvenanceItem,
    ACMGClassificationResponse, ACMGCriterion,
    ClassificationTimelineResponse, ClassificationEntry,
    GnomadResponse,
)
from app.services.variant_service import VariantAnalysisService
from app.services.evidence_scoring import EvidenceScoringService
from app.services.confidence_engine import ConfidenceEngine
from app.services.report_generator import PDFReportGenerator
from app.services.research_gaps import ResearchGapDetector
from app.services.ai_summary import AISummaryService
from app.services.acmg_service import ACMGService
from app.services.gnomad_service import GnomadService

router = APIRouter(prefix="/api/v1")


def get_db():
    from app.models.database import engine
    from sqlalchemy.orm import sessionmaker
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/health")
def health_check():
    return {"status": "ok", "app": "Sydney", "version": "0.1.0"}


@router.get("/dashboard", response_model=DashboardStats)
def get_dashboard(db: Session = Depends(get_db)):
    return DashboardStats(
        total_variants=db.query(Variant).count(),
        total_papers=db.query(Paper).count(),
        total_genes=db.query(Gene).count(),
        total_diseases=db.query(Disease).count(),
        recent_searches=["BRCA1 c.5266dupC", "TP53 R175H", "BRCA2 c.5946delT", "CDH1 c.1901C>T", "PALB2 c.1592delT"],
    )


@router.post("/variants/search", response_model=Optional[VariantSearchResponse])
def search_variant(req: VariantSearchRequest, db: Session = Depends(get_db)):
    service = VariantAnalysisService(db)
    result = service.analyze_variant(req.query)

    if not result:
        raise HTTPException(
            status_code=400,
            detail="Could not parse variant. Use format like: BRCA1 c.5266dupC, TP53 R175H, BRCA2 c.5946delT, CDH1 c.1901C>T, PALB2 c.1592delT"
        )

    variant = result["variant"]
    gene = result["gene"]

    return VariantSearchResponse(
        id=variant.id,
        hgvs_c=variant.hgvs_c,
        hgvs_p=variant.hgvs_p,
        protein_change=variant.protein_change,
        gene=gene.symbol,
        gene_full_name=gene.full_name,
        variant_type=variant.variant_type,
        clinical_significance=variant.clinical_significance,
        clinvar_id=variant.clinvar_id,
        review_status=variant.review_status,
        gnomad_af=variant.gnomad_af,
    )


@router.get("/variants/{variant_id}", response_model=Optional[VariantDetailResponse])
def get_variant_detail(variant_id: int, db: Session = Depends(get_db)):
    service = VariantAnalysisService(db)
    result = service.get_variant_detail(variant_id)

    if not result:
        raise HTTPException(status_code=404, detail="Variant not found")

    variant = result["variant"]
    gene = result["gene"]

    scoring = EvidenceScoringService(db)
    scoring.score_evidence_for_variant(variant_id)
    top_evidence = scoring.get_top_evidence(variant_id, 10)

    diseases = []
    if variant.clinvar_data and "diseases" in variant.clinvar_data:
        diseases = variant.clinvar_data["diseases"]

    return VariantDetailResponse(
        id=variant.id,
        hgvs_c=variant.hgvs_c,
        hgvs_p=variant.hgvs_p,
        protein_change=variant.protein_change,
        gene=gene.symbol,
        gene_full_name=gene.full_name,
        variant_type=variant.variant_type,
        clinical_significance=variant.clinical_significance,
        clinvar_id=variant.clinvar_id,
        review_status=variant.review_status,
        gnomad_af=variant.gnomad_af,
        description=variant.description,
        clinvar_data=variant.clinvar_data,
        gnomad_data=variant.gnomad_data,
        diseases=diseases,
        evidence=top_evidence,
    )


@router.get("/variants/{variant_id}/evidence", response_model=list[EvidenceResponse])
def get_variant_evidence(variant_id: int, db: Session = Depends(get_db)):
    variant = db.query(Variant).filter(Variant.id == variant_id).first()
    if not variant:
        raise HTTPException(status_code=404, detail="Variant not found")
    scoring = EvidenceScoringService(db)
    scoring.score_evidence_for_variant(variant_id)
    evidence = scoring.get_top_evidence(variant_id, 20)

    return [
        EvidenceResponse(
            id=e["id"],
            pmid=e["pmid"],
            title=e["title"],
            authors=e["authors"],
            journal=e["journal"],
            year=e["year"],
            abstract=e["abstract"],
            evidence_type=e["evidence_type"],
            relevance_score=e["relevance_score"],
            study_quality_score=e["study_quality_score"],
            recency_score=e["recency_score"],
            evidence_score=e["evidence_score"],
            key_findings=e["key_findings"],
        )
        for e in evidence
    ]


@router.get("/variants/{variant_id}/report", response_model=Optional[ReportResponse])
def get_variant_report(variant_id: int, db: Session = Depends(get_db)):
    variant = db.query(Variant).filter(Variant.id == variant_id).first()
    if not variant:
        raise HTTPException(status_code=404, detail="Variant not found")
    engine = ConfidenceEngine(db)
    report = engine.generate_report(variant_id)

    scoring = EvidenceScoringService(db)
    top_evidence = scoring.get_top_evidence(variant_id, 10)

    report_data = report.report_data or {}
    disease_assocs = report_data.get("disease_associations", [])
    if variant.clinvar_data and "diseases" in variant.clinvar_data:
        disease_assocs = [{"name": d} for d in variant.clinvar_data["diseases"]]

    return ReportResponse(
        id=report.id,
        variant_id=report.variant_id,
        confidence_level=report.confidence_level,
        confidence_score=report.confidence_score,
        evidence_volume=report.evidence_volume,
        evidence_quality=report.evidence_quality,
        study_agreement=report.study_agreement,
        clinvar_review_strength=report.clinvar_review_strength or 0.0,
        executive_summary=report.executive_summary,
        clinical_significance=report.clinical_significance or variant.clinical_significance,
        disease_associations=disease_assocs,
        mechanism_of_action=report.mechanism_of_action,
        evidence_overview=report.evidence_overview,
        confidence_assessment=report.confidence_assessment,
        research_gaps=[],
        ai_summary=report.ai_summary,
        created_at=report.created_at.isoformat() if report.created_at else None,
    )


@router.post("/variants/{variant_id}/summary")
def generate_ai_summary(variant_id: int, db: Session = Depends(get_db)):
    variant = db.query(Variant).filter(Variant.id == variant_id).first()
    if not variant:
        raise HTTPException(status_code=404, detail="Variant not found")

    gene = db.query(Gene).filter(Gene.id == variant.gene_id).first()
    scoring = EvidenceScoringService(db)
    top_evidence = scoring.get_top_evidence(variant_id, 10)

    engine = ConfidenceEngine(db)
    confidence = engine.calculate_confidence(variant_id)

    ai_service = AISummaryService()
    summary = ai_service.generate_summary(
        variant=variant.hgvs_c or variant.protein_change or "",
        gene=gene.symbol if gene else "",
        clinical_significance=variant.clinical_significance or "Unknown",
        evidence_list=top_evidence,
        confidence=confidence,
    )

    report = db.query(ReportModel).filter(ReportModel.variant_id == variant_id).first()
    if report:
        report.ai_summary = summary
        db.commit()

    return {"summary": summary}


@router.get("/variants/{variant_id}/gaps")
def get_research_gaps(variant_id: int, db: Session = Depends(get_db)):
    detector = ResearchGapDetector(db)
    gaps = detector.analyze_gaps(variant_id)

    variant = db.query(Variant).filter(Variant.id == variant_id).first()
    if not variant:
        raise HTTPException(status_code=404, detail="Variant not found")

    gene = db.query(Gene).filter(Gene.id == variant.gene_id).first() if variant else None

    ai_service = AISummaryService()
    ai_gaps = ai_service.generate_research_gaps(
        variant=variant.hgvs_c or variant.protein_change or "",
        gene=gene.symbol if gene else "",
        evidence_count=gaps["total_papers"],
        evidence_list=[],
    )

    return {
        "rule_based": gaps,
        "ai_analysis": ai_gaps,
    }


@router.get("/variants/{variant_id}/report/pdf")
def download_pdf_report(variant_id: int, db: Session = Depends(get_db)):
    variant = db.query(Variant).filter(Variant.id == variant_id).first()
    if not variant:
        raise HTTPException(status_code=404, detail="Variant not found")

    gene = db.query(Gene).filter(Gene.id == variant.gene_id).first()
    engine = ConfidenceEngine(db)
    report = engine.generate_report(variant_id)

    scoring = EvidenceScoringService(db)
    top_evidence = scoring.get_top_evidence(variant_id, 10)

    generator = PDFReportGenerator()
    pdf_bytes = generator.generate_report(variant, gene, report, top_evidence)

    from fastapi.responses import Response
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=sydney_report_{variant_id}.pdf"
        }
    )


@router.get("/graph/{variant_id}", response_model=GraphData)
def get_variant_graph(variant_id: int, db: Session = Depends(get_db)):
    variant = db.query(Variant).filter(Variant.id == variant_id).first()
    if not variant:
        raise HTTPException(status_code=404, detail="Variant not found")

    gene = db.query(Gene).filter(Gene.id == variant.gene_id).first()
    evidence_list = db.query(Evidence).filter(Evidence.variant_id == variant_id).all()

    nodes = [
        {"id": f"gene_{gene.id}", "label": gene.symbol, "type": "gene"},
        {"id": f"variant_{variant.id}", "label": variant.hgvs_c or variant.protein_change or "", "type": "variant"},
    ]
    edges = [
        {"source": f"gene_{gene.id}", "target": f"variant_{variant.id}", "label": "has variant"},
    ]

    diseases = set()
    for ev in evidence_list:
        paper = db.query(Paper).filter(Paper.id == ev.paper_id).first()
        if paper:
            nodes.append({
                "id": f"paper_{paper.id}",
                "label": paper.title[:50] + ("..." if len(paper.title or "") > 50 else ""),
                "type": "paper",
            })
            edges.append({
                "source": f"variant_{variant.id}",
                "target": f"paper_{paper.id}",
                "label": f"evidence ({ev.evidence_score:.2f})",
            })
            for d in (paper.diseases or []):
                diseases.add(d)

    for d in diseases:
        did = f"disease_{d.id}"
        if did not in [n["id"] for n in nodes]:
            nodes.append({"id": did, "label": d.name, "type": "disease"})
            edges.append({"source": did, "target": f"variant_{variant.id}", "label": "associated with"})

    unique_nodes = {}
    for n in nodes:
        unique_nodes[n["id"]] = n
    nodes = list(unique_nodes.values())

    return GraphData(nodes=nodes, edges=edges)


@router.post("/compare", response_model=CompareResponse)
def compare_variants(req: CompareRequest, db: Session = Depends(get_db)):
    service = VariantAnalysisService(db)

    def analyze(query: str) -> Optional[CompareVariantData]:
        result = service.analyze_variant(query)
        if not result:
            return None
        v = result["variant"]
        g = result["gene"]
        engine = ConfidenceEngine(db)
        conf = engine.calculate_confidence(v.id)
        evidence_count = db.query(Evidence).filter(Evidence.variant_id == v.id).count()
        return CompareVariantData(
            id=v.id,
            label=v.hgvs_c or v.protein_change or query,
            gene=g.symbol,
            clinical_significance=v.clinical_significance,
            papers=evidence_count,
            confidence_score=conf["score"],
            confidence_level=conf["level"],
            evidence_volume=conf["evidence_volume"],
            evidence_quality=conf["evidence_quality"],
            study_agreement=conf["study_agreement"],
            clinvar_review_strength=conf.get("clinvar_review_strength", 0.0),
            clinvar_id=v.clinvar_id,
            review_status=v.review_status,
        )

    v1 = analyze(req.query1)
    v2 = analyze(req.query2)

    if not v1:
        raise HTTPException(status_code=400, detail=f"Could not parse: {req.query1}")
    if not v2:
        raise HTTPException(status_code=400, detail=f"Could not parse: {req.query2}")

    return CompareResponse(variant1=v1, variant2=v2)


@router.get("/variants/{variant_id}/publications/trends", response_model=Optional[PublicationTrendsResponse])
def get_publication_trends(variant_id: int, db: Session = Depends(get_db)):
    variant = db.query(Variant).filter(Variant.id == variant_id).first()
    if not variant:
        raise HTTPException(status_code=404, detail="Variant not found")

    results = (
        db.query(Paper.year, func.count(Paper.id))
        .join(Evidence, Evidence.paper_id == Paper.id)
        .filter(Evidence.variant_id == variant_id)
        .group_by(Paper.year)
        .order_by(Paper.year)
        .all()
    )

    gene = db.query(Gene).filter(Gene.id == variant.gene_id).first()
    return PublicationTrendsResponse(
        variant_id=variant.id,
        label=f"{gene.symbol} {variant.hgvs_c or variant.protein_change or ''}" if gene else str(variant.id),
        trends=[PublicationTrend(year=row[0], count=row[1]) for row in results if row[0]],
    )


@router.post("/variants/{variant_id}/why-matters")
def get_why_matters(variant_id: int, db: Session = Depends(get_db)):
    variant = db.query(Variant).filter(Variant.id == variant_id).first()
    if not variant:
        raise HTTPException(status_code=404, detail="Variant not found")

    if variant.why_matters:
        return {"explanation": variant.why_matters}

    gene = db.query(Gene).filter(Gene.id == variant.gene_id).first()
    ai_service = AISummaryService()
    result = ai_service.generate_why_matters(
        variant=variant.hgvs_c or variant.protein_change or "",
        gene=gene.symbol if gene else "",
        gene_full=gene.full_name if gene else "",
        clinical_significance=variant.clinical_significance or "Unknown",
        description=variant.description or "",
        clinvar_data=variant.clinvar_data or {},
    )
    if result:
        variant.why_matters = result
        db.commit()
    return {"explanation": result}


@router.get("/variants/{variant_id}/evidence-provenance", response_model=EvidenceProvenanceResponse)
def get_evidence_provenance(variant_id: int, db: Session = Depends(get_db)):
    variant = db.query(Variant).filter(Variant.id == variant_id).first()
    if not variant:
        raise HTTPException(status_code=404, detail="Variant not found")

    scoring = EvidenceScoringService(db)
    scoring.score_evidence_for_variant(variant_id)
    top_evidence = scoring.get_top_evidence(variant_id, 50)

    engine = ConfidenceEngine(db)
    conf = engine.calculate_confidence(variant_id)

    items = []
    crs = conf.get("clinvar_review_strength", 0.0)
    for ev in top_evidence:
        volume_contrib = 0.20 * (1.0 if conf["evidence_volume"] >= 20 else
                                 0.8 if conf["evidence_volume"] >= 10 else
                                 0.6 if conf["evidence_volume"] >= 5 else
                                 0.4 if conf["evidence_volume"] >= 3 else 0.2)
        quality_contrib = 0.40 * (ev["study_quality_score"] or 0)
        agreement_contrib = 0.30 * (conf["study_agreement"])
        review_contrib = 0.10 * crs
        total_contrib = volume_contrib + quality_contrib + agreement_contrib + review_contrib
        contribution_pct = (total_contrib / conf["score"] * 100) if conf["score"] > 0 else 0

        items.append(EvidenceProvenanceItem(
            id=ev["id"],
            pmid=ev["pmid"],
            title=ev["title"],
            authors=ev.get("authors"),
            year=ev.get("year"),
            evidence_score=ev["evidence_score"],
            relevance_score=ev.get("relevance_score", 0),
            study_quality_score=ev.get("study_quality_score", 0),
            recency_score=ev.get("recency_score", 0),
            study_type=ev.get("study_type"),
            volume_contrib=round(volume_contrib, 4),
            quality_contrib=round(quality_contrib, 4),
            agreement_contrib=round(agreement_contrib, 4),
            review_contrib=round(review_contrib, 4),
            total_contrib=round(total_contrib, 4),
            contribution_pct=round(contribution_pct, 2),
        ))

    return EvidenceProvenanceResponse(
        variant_id=variant_id,
        total_papers=conf["evidence_volume"],
        confidence_score=conf["score"],
        confidence_level=conf["level"],
        papers=items,
    )


@router.get("/variants/{variant_id}/acmg", response_model=ACMGClassificationResponse)
def get_acmg_classification(variant_id: int, db: Session = Depends(get_db)):
    variant = db.query(Variant).filter(Variant.id == variant_id).first()
    if not variant:
        raise HTTPException(status_code=404, detail="Variant not found")

    acmg = ACMGService(db)
    return acmg.classify(variant_id)


@router.get("/variants/{variant_id}/gnomad", response_model=Optional[GnomadResponse])
def get_gnomad_data(variant_id: int, db: Session = Depends(get_db)):
    variant = db.query(Variant).filter(Variant.id == variant_id).first()
    if not variant:
        raise HTTPException(status_code=404, detail="Variant not found")

    if not variant.gnomad_data:
        return GnomadResponse(variant_id=variant_id)

    return GnomadResponse(
        variant_id=variant_id,
        allele_frequency=variant.gnomad_data.get("allele_frequency"),
        allele_count=variant.gnomad_data.get("allele_count"),
        allele_number=variant.gnomad_data.get("allele_number"),
        homozygote_count=variant.gnomad_data.get("homozygote_count"),
        population_frequencies=variant.gnomad_data.get("population_frequencies", {}),
        gnomad_variant_id=variant.gnomad_data.get("gnomad_variant_id"),
    )


@router.get("/variants/{variant_id}/classification-timeline", response_model=Optional[ClassificationTimelineResponse])
def get_classification_timeline(variant_id: int, db: Session = Depends(get_db)):
    variant = db.query(Variant).filter(Variant.id == variant_id).first()
    if not variant:
        raise HTTPException(status_code=404, detail="Variant not found")

    gene = db.query(Gene).filter(Gene.id == variant.gene_id).first()
    label = f"{gene.symbol} {variant.hgvs_c or variant.protein_change or ''}" if gene else str(variant.id)

    history = []
    if variant.clinvar_data and "classification_history" in variant.clinvar_data:
        for entry in variant.clinvar_data["classification_history"]:
            history.append(ClassificationEntry(
                classification=entry.get("classification", "Unknown"),
                review_status=entry.get("review_status", "No assertion"),
                date=entry.get("date", ""),
            ))

    return ClassificationTimelineResponse(
        variant_id=variant.id,
        label=label,
        current_classification=variant.clinical_significance or "Unknown",
        current_review_status=variant.review_status or "No assertion",
        history=history,
    )


@router.delete("/variants/{variant_id}")
def delete_variant(variant_id: int, db: Session = Depends(get_db)):
    variant = db.query(Variant).filter(Variant.id == variant_id).first()
    if not variant:
        raise HTTPException(status_code=404, detail="Variant not found")

    gene = db.query(Gene).filter(Gene.id == variant.gene_id).first()
    change = variant.hgvs_c or variant.protein_change or ""
    if gene and change:
        from app.services.clinvar_service import ClinVarService
        from app.services.gnomad_service import GnomadService
        from app.services.pubmed_service import PubMedService
        safe = change.replace("/", "_").replace(" ", "_").replace(".", "_")
        cache_dirs = [
            ClinVarService.CACHE_DIR,
            GnomadService.CACHE_DIR,
            PubMedService.CACHE_DIR,
        ]
        for cache_dir in cache_dirs:
            for p in Path(cache_dir).glob(f"{gene.symbol}_{safe}*"):
                p.unlink(missing_ok=True)

    db.query(Evidence).filter(Evidence.variant_id == variant_id).delete()
    db.query(ReportModel).filter(ReportModel.variant_id == variant_id).delete()
    db.delete(variant)
    db.commit()
    return {"deleted": variant_id}


@router.get("/variants")
def list_variants(
    gene: Optional[str] = None,
    limit: int = Query(default=20, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    query = db.query(Variant)
    if gene:
        query = query.join(Gene).filter(func.lower(Gene.symbol) == gene.lower())
    query = query.order_by(Variant.created_at.desc()).offset(offset).limit(limit)
    results = []
    for v in query.all():
        g = db.query(Gene).filter(Gene.id == v.gene_id).first()
        results.append({
            "id": v.id,
            "hgvs_c": v.hgvs_c,
            "hgvs_p": v.hgvs_p,
            "protein_change": v.protein_change,
            "gene": g.symbol if g else "",
            "clinical_significance": v.clinical_significance,
            "created_at": v.created_at.isoformat() if v.created_at else None,
        })
    return results
