from pydantic import BaseModel, Field
from typing import Optional, Any
from datetime import datetime


class VariantSearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=200)


class VariantSearchResponse(BaseModel):
    id: int
    hgvs_c: Optional[str] = None
    hgvs_p: Optional[str] = None
    protein_change: Optional[str] = None
    gene: str
    gene_full_name: Optional[str] = None
    variant_type: Optional[str] = None
    clinical_significance: Optional[str] = None
    clinvar_id: Optional[str] = None
    review_status: Optional[str] = None
    diseases: list[str] = []


class VariantDetailResponse(VariantSearchResponse):
    description: Optional[str] = None
    clinvar_data: Optional[dict] = None
    evidence: list[dict] = []
    report: Optional[dict] = None


class EvidenceResponse(BaseModel):
    id: int
    pmid: str
    title: str
    authors: Optional[str] = None
    journal: Optional[str] = None
    year: Optional[int] = None
    abstract: Optional[str] = None
    evidence_type: str
    relevance_score: float
    study_quality_score: float
    recency_score: float
    evidence_score: float
    key_findings: Optional[str] = None


class ReportResponse(BaseModel):
    id: int
    variant_id: int
    confidence_level: str
    confidence_score: float
    evidence_volume: int
    evidence_quality: float
    study_agreement: float
    executive_summary: Optional[str] = None
    clinical_significance: Optional[str] = None
    disease_associations: list[dict] = []
    mechanism_of_action: Optional[str] = None
    evidence_overview: Optional[str] = None
    confidence_assessment: Optional[str] = None
    research_gaps: list[dict] = []
    ai_summary: Optional[str] = None
    created_at: Optional[str] = None


class DashboardStats(BaseModel):
    total_variants: int
    total_papers: int
    total_genes: int
    total_diseases: int
    recent_searches: list[str] = []


class GraphData(BaseModel):
    nodes: list[dict] = []
    edges: list[dict] = []


class SearchHistoryResponse(BaseModel):
    queries: list[str] = []


class CompareRequest(BaseModel):
    query1: str = Field(..., min_length=1, max_length=200)
    query2: str = Field(..., min_length=1, max_length=200)


class CompareVariantData(BaseModel):
    id: int
    label: str
    gene: str
    clinical_significance: Optional[str] = None
    papers: int = 0
    confidence_score: float = 0.0
    confidence_level: str = "Insufficient Evidence"
    evidence_volume: int = 0
    evidence_quality: float = 0.0
    study_agreement: float = 0.0
    clinvar_id: Optional[str] = None
    review_status: Optional[str] = None


class CompareResponse(BaseModel):
    variant1: CompareVariantData
    variant2: CompareVariantData


class PublicationTrend(BaseModel):
    year: int
    count: int


class PublicationTrendsResponse(BaseModel):
    variant_id: int
    label: str
    trends: list[PublicationTrend]


class ErrorResponse(BaseModel):
    detail: str
    code: Optional[str] = None
