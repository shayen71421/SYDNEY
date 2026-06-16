"use client";

import { ReportData } from "@/types";

interface Props {
  report: ReportData;
}

export function ConfidenceBreakdown({ report }: Props) {
  const volumeContrib = Math.round(report.evidence_volume * 30);
  const qualityContrib = Math.round(report.evidence_quality * 100 * 40);
  const agreementContrib = Math.round(report.study_agreement * 100 * 30);
  const total = volumeContrib + qualityContrib + agreementContrib;

  const bar = (val: number, max: number, color: string) => {
    const pct = max > 0 ? (val / max) * 100 : 0;
    return (
      <div className="h-2 w-full overflow-hidden rounded-full bg-slate-100 dark:bg-slate-700">
        <div
          className="h-full rounded-full transition-all"
          style={{ width: `${pct}%`, backgroundColor: color }}
        />
      </div>
    );
  };

  return (
    <div className="space-y-4">
      <div className="space-y-3">
        <div>
          <div className="mb-1 flex items-center justify-between text-sm">
            <span className="text-slate-600 dark:text-slate-400">Evidence Volume</span>
            <span className="font-medium text-slate-800 dark:text-white">{volumeContrib}</span>
          </div>
          {bar(volumeContrib, 30, "#3b82f6")}
          <p className="mt-0.5 text-[10px] text-slate-400">
            {report.evidence_volume} papers &times; 30% weight
          </p>
        </div>
        <div>
          <div className="mb-1 flex items-center justify-between text-sm">
            <span className="text-slate-600 dark:text-slate-400">Evidence Quality</span>
            <span className="font-medium text-slate-800 dark:text-white">{qualityContrib}</span>
          </div>
          {bar(qualityContrib, 40, "#8b5cf6")}
          <p className="mt-0.5 text-[10px] text-slate-400">
            {(report.evidence_quality * 100).toFixed(0)}% avg quality &times; 40% weight
          </p>
        </div>
        <div>
          <div className="mb-1 flex items-center justify-between text-sm">
            <span className="text-slate-600 dark:text-slate-400">Study Agreement</span>
            <span className="font-medium text-slate-800 dark:text-white">{agreementContrib}</span>
          </div>
          {bar(agreementContrib, 30, "#059669")}
          <p className="mt-0.5 text-[10px] text-slate-400">
            {(report.study_agreement * 100).toFixed(0)}% consensus &times; 30% weight
          </p>
        </div>
      </div>
      <div className="flex items-center justify-between border-t border-slate-100 pt-3 dark:border-slate-700">
        <span className="text-sm font-semibold text-slate-700 dark:text-slate-300">
          Total Confidence Score
        </span>
        <span className="text-lg font-bold text-slate-900 dark:text-white">
          {total}
        </span>
      </div>
    </div>
  );
}
