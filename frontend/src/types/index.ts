export interface VariantSearchResult {
  id: number;
  hgvs_c: string | null;
  hgvs_p: string | null;
  protein_change: string | null;
  gene: string;
  gene_full_name: string | null;
  variant_type: string | null;
  clinical_significance: string | null;
  clinvar_id: string | null;
  review_status: string | null;
  diseases: string[];
}

export interface VariantDetail extends VariantSearchResult {
  description: string | null;
  clinvar_data: Record<string, unknown> | null;
  evidence: EvidenceItem[];
  report: ReportData | null;
}

export interface EvidenceItem {
  id: number;
  pmid: string;
  title: string;
  authors: string | null;
  journal: string | null;
  year: number | null;
  abstract: string | null;
  evidence_type: string;
  relevance_score: number;
  study_quality_score: number;
  recency_score: number;
  evidence_score: number;
  key_findings: string | null;
}

export interface ReportData {
  id: number;
  variant_id: number;
  confidence_level: string;
  confidence_score: number;
  evidence_volume: number;
  evidence_quality: number;
  study_agreement: number;
  executive_summary: string | null;
  clinical_significance: string | null;
  disease_associations: Record<string, unknown>[];
  mechanism_of_action: string | null;
  evidence_overview: string | null;
  confidence_assessment: string | null;
  research_gaps: Record<string, unknown>[];
  ai_summary: string | null;
  created_at: string | null;
}

export interface DashboardStats {
  total_variants: number;
  total_papers: number;
  total_genes: number;
  total_diseases: number;
  recent_searches: string[];
}

export interface GraphNode {
  id: string;
  label: string;
  type: string;
}

export interface GraphEdge {
  source: string;
  target: string;
  label: string;
}

export interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface ResearchGaps {
  rule_based: {
    gaps: string[];
    well_studied: boolean;
    summary: string;
    paper_types: Record<string, number>;
    total_papers: number;
    high_quality_studies: number;
  };
  ai_analysis: string | null;
}

export interface AISummary {
  summary: string;
}
