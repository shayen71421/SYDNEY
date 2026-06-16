"use client";

import { useState } from "react";
import { ChevronDown, ChevronUp, ExternalLink } from "lucide-react";
import type { EvidenceItem } from "@/types";
import { formatScore } from "@/lib/utils";

interface Props {
  evidence: EvidenceItem[];
}

export function EvidenceTable({ evidence }: Props) {
  const [expanded, setExpanded] = useState<number | null>(null);

  const sorted = [...evidence].sort((a, b) => b.evidence_score - a.evidence_score);

  return (
    <div className="overflow-hidden rounded-lg border border-slate-200 dark:border-slate-700">
      <table className="w-full text-sm">
        <thead>
          <tr className="bg-slate-50 dark:bg-slate-800">
            <th className="px-3 py-2 text-left font-medium text-slate-500">Score</th>
            <th className="px-3 py-2 text-left font-medium text-slate-500">Title</th>
            <th className="hidden px-3 py-2 text-left font-medium text-slate-500 md:table-cell">
              Year
            </th>
            <th className="hidden px-3 py-2 text-left font-medium text-slate-500 md:table-cell">
              Type
            </th>
            <th className="px-3 py-2 text-right font-medium text-slate-500">PMID</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-200 dark:divide-slate-700">
          {sorted.map((ev) => (
            <>
              <tr
                key={ev.id}
                className="cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-800/50"
                onClick={() => setExpanded(expanded === ev.id ? null : ev.id)}
              >
                <td className="px-3 py-2.5">
                  <div className="flex items-center gap-2">
                    <div
                      className="h-2 w-16 rounded-full bg-slate-200 dark:bg-slate-700"
                    >
                      <div
                        className={`h-full rounded-full ${
                          ev.evidence_score >= 0.7
                            ? "bg-emerald-500"
                            : ev.evidence_score >= 0.4
                            ? "bg-amber-500"
                            : "bg-red-500"
                        }`}
                        style={{ width: `${formatScore(ev.evidence_score)}%` }}
                      />
                    </div>
                    <span className="w-8 text-right text-xs font-medium">
                      {formatScore(ev.evidence_score)}
                    </span>
                  </div>
                </td>
                <td className="max-w-xs truncate px-3 py-2.5 font-medium text-slate-900 dark:text-white">
                  {ev.title}
                </td>
                <td className="hidden px-3 py-2.5 text-slate-500 md:table-cell">
                  {ev.year || "-"}
                </td>
                <td className="hidden px-3 py-2.5 md:table-cell">
                  <span className="rounded bg-slate-100 px-2 py-0.5 text-xs text-slate-600 dark:bg-slate-700 dark:text-slate-400">
                    {ev.evidence_type}
                  </span>
                </td>
                <td className="px-3 py-2.5 text-right">
                  <a
                    href={`https://pubmed.ncbi.nlm.nih.gov/${ev.pmid}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="font-mono text-xs text-sydney-600 hover:underline"
                    onClick={(e) => e.stopPropagation()}
                  >
                    {ev.pmid}
                    <ExternalLink className="ml-1 inline h-3 w-3" />
                  </a>
                </td>
              </tr>
              {expanded === ev.id && (
                <tr key={`detail-${ev.id}`}>
                  <td colSpan={5} className="bg-slate-50 px-4 py-3 dark:bg-slate-800/50">
                    <div className="grid gap-2 text-sm md:grid-cols-3">
                      <div>
                        <span className="text-xs text-slate-500">Relevance</span>
                        <div className="score-bar mt-1">
                          <div
                            className="score-fill bg-sydney-500"
                            style={{ width: `${formatScore(ev.relevance_score)}%` }}
                          />
                        </div>
                        <span className="text-xs text-slate-400">{formatScore(ev.relevance_score)}%</span>
                      </div>
                      <div>
                        <span className="text-xs text-slate-500">Study Quality</span>
                        <div className="score-bar mt-1">
                          <div
                            className="score-fill bg-emerald-500"
                            style={{ width: `${formatScore(ev.study_quality_score)}%` }}
                          />
                        </div>
                        <span className="text-xs text-slate-400">{formatScore(ev.study_quality_score)}%</span>
                      </div>
                      <div>
                        <span className="text-xs text-slate-500">Recency</span>
                        <div className="score-bar mt-1">
                          <div
                            className="score-fill bg-amber-500"
                            style={{ width: `${formatScore(ev.recency_score)}%` }}
                          />
                        </div>
                        <span className="text-xs text-slate-400">{formatScore(ev.recency_score)}%</span>
                      </div>
                    </div>
                    {ev.abstract && (
                      <p className="mt-2 text-xs leading-relaxed text-slate-600 dark:text-slate-400">
                        {ev.abstract.slice(0, 300)}...
                      </p>
                    )}
                  </td>
                </tr>
              )}
            </>
          ))}
        </tbody>
      </table>
    </div>
  );
}
