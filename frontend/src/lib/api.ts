import type {
  DashboardStats,
  VariantSearchResult,
  VariantDetail,
  EvidenceItem,
  ReportData,
  GraphData,
  ResearchGaps,
  AISummary,
  CompareResponse,
  PublicationTrendsResponse,
  WhyMattersResponse,
} from "@/types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function fetchJSON<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${url}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "API request failed");
  }
  return res.json();
}

export const api = {
  health: () => fetchJSON<{ status: string }>("/api/v1/health"),

  getDashboard: () => fetchJSON<DashboardStats>("/api/v1/dashboard"),

  searchVariant: (query: string) =>
    fetchJSON<VariantSearchResult>("/api/v1/variants/search", {
      method: "POST",
      body: JSON.stringify({ query }),
    }),

  getVariantDetail: (id: number) =>
    fetchJSON<VariantDetail>(`/api/v1/variants/${id}`),

  getEvidence: (id: number) =>
    fetchJSON<EvidenceItem[]>(`/api/v1/variants/${id}/evidence`),

  getReport: (id: number) =>
    fetchJSON<ReportData>(`/api/v1/variants/${id}/report`),

  generateSummary: (id: number) =>
    fetchJSON<AISummary>(`/api/v1/variants/${id}/summary`, { method: "POST" }),

  getGaps: (id: number) =>
    fetchJSON<ResearchGaps>(`/api/v1/variants/${id}/gaps`),

  getGraph: (id: number) => fetchJSON<GraphData>(`/api/v1/graph/${id}`),

  downloadPdf: async (id: number) => {
    const res = await fetch(`${API_BASE}/api/v1/variants/${id}/report/pdf`);
    if (!res.ok) throw new Error("PDF download failed");
    return res.blob();
  },

  listVariants: (gene?: string) => {
    const params = gene ? `?gene=${gene}` : "";
    return fetchJSON<VariantDetail[]>(`/api/v1/variants${params}`);
  },

  compareVariants: (query1: string, query2: string) =>
    fetchJSON<CompareResponse>("/api/v1/compare", {
      method: "POST",
      body: JSON.stringify({ query1, query2 }),
    }),

  getPublicationTrends: (id: number) =>
    fetchJSON<PublicationTrendsResponse>(`/api/v1/variants/${id}/publications/trends`),

  getWhyMatters: (id: number) =>
    fetchJSON<WhyMattersResponse>(`/api/v1/variants/${id}/why-matters`, { method: "POST" }),
};
