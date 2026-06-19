"use client";

import { X, ExternalLink } from "lucide-react";
import type { EvidenceProvenanceResponse } from "@/types";

interface Props {
  data: EvidenceProvenanceResponse;
  onClose: () => void;
}

export function EvidenceProvenanceModal({ data, onClose }: Props) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="max-h-[85vh] w-full max-w-3xl overflow-y-auto rounded-xl bg-white shadow-2xl dark:bg-slate-900">
        <div className="sticky top-0 flex items-center justify-between border-b border-slate-200 bg-white px-6 py-4 dark:border-slate-700 dark:bg-slate-900">
          <div>
            <h2 className="text-lg font-bold text-slate-900 dark:text-white">Evidence Provenance</h2>
            <p className="text-xs text-slate-500">
              {data.total_papers} papers &middot; Score: {(data.confidence_score * 100).toFixed(0)} &middot; {data.confidence_level}
            </p>
          </div>
          <button onClick={onClose} className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-600 dark:hover:bg-slate-800">
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="space-y-2 p-6">
          {data.papers.length === 0 && (
            <p className="py-8 text-center text-sm text-slate-500">No papers contributing to the score.</p>
          )}

          {data.papers.map((paper) => {
            const pct = paper.contribution_pct;
            const barColor = pct > 15 ? "bg-emerald-500" : pct > 8 ? "bg-sky-500" : pct > 3 ? "bg-amber-500" : "bg-slate-400";
            return (
              <div key={paper.id} className="rounded-lg border border-slate-100 p-4 transition-colors hover:bg-slate-50 dark:border-slate-700 dark:hover:bg-slate-800/50">
                <div className="mb-2 flex items-start justify-between gap-4">
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium text-slate-800 dark:text-white leading-snug line-clamp-2">
                      {paper.title}
                    </p>
                    <p className="mt-0.5 text-xs text-slate-500">
                      PMID: {paper.pmid}{paper.authors ? ` · ${paper.authors.split(",")[0]} et al.` : ""}{paper.year ? ` · ${paper.year}` : ""}
                    </p>
                  </div>
                  <a
                    href={`https://pubmed.ncbi.nlm.nih.gov/${paper.pmid}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex-shrink-0 text-slate-400 hover:text-slate-600"
                  >
                    <ExternalLink className="h-4 w-4" />
                  </a>
                </div>

                <div className="mb-1.5 flex items-center gap-2">
                  <div className="h-2 flex-1 overflow-hidden rounded-full bg-slate-100 dark:bg-slate-700">
                    <div className={`h-full rounded-full transition-all ${barColor}`} style={{ width: `${Math.min(pct, 100)}%` }} />
                  </div>
                  <span className="w-12 text-right text-xs font-bold text-slate-700 dark:text-slate-300">{pct.toFixed(1)}%</span>
                </div>

                <div className="flex flex-wrap gap-x-4 gap-y-1 text-[10px] text-slate-400">
                  <span>Score: {(paper.evidence_score * 100).toFixed(0)}</span>
                  <span>Relevance: {(paper.relevance_score * 100).toFixed(0)}%</span>
                  <span>Quality: {(paper.study_quality_score * 100).toFixed(0)}%</span>
                  <span>Recency: {(paper.recency_score * 100).toFixed(0)}%</span>
                  {paper.study_type && <span>Type: {paper.study_type}</span>}
                </div>

                <div className="mt-1.5 flex flex-wrap gap-x-4 gap-y-0.5 text-[10px] text-slate-400">
                  <span>Vol ×20%: {paper.volume_contrib.toFixed(3)}</span>
                  <span>Qual ×40%: {paper.quality_contrib.toFixed(3)}</span>
                  <span>Agree ×30%: {paper.agreement_contrib.toFixed(3)}</span>
                  <span>Review ×10%: {(paper as any).review_contrib?.toFixed(3) || "0.000"}</span>
                  <span className="font-medium text-slate-500">Contrib: {paper.total_contrib.toFixed(3)}</span>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
