"use client";

import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/Card";
import type { ClassificationTimelineResponse } from "@/types";

interface Props {
  data: ClassificationTimelineResponse | null;
}

const significanceColors: Record<string, string> = {
  "Pathogenic": "text-red-600 border-red-300 bg-red-50 dark:border-red-800 dark:bg-red-950/30",
  "Likely pathogenic": "text-orange-600 border-orange-300 bg-orange-50 dark:border-orange-800 dark:bg-orange-950/30",
  "Uncertain significance": "text-amber-600 border-amber-300 bg-amber-50 dark:border-amber-800 dark:bg-amber-950/30",
  "Likely benign": "text-emerald-600 border-emerald-300 bg-emerald-50 dark:border-emerald-800 dark:bg-emerald-950/30",
  "Benign": "text-emerald-600 border-emerald-300 bg-emerald-50 dark:border-emerald-800 dark:bg-emerald-950/30",
};

function getColorClass(sig: string): string {
  for (const [key, val] of Object.entries(significanceColors)) {
    if (sig.toLowerCase().includes(key.toLowerCase())) return val;
  }
  return "text-slate-600 border-slate-300 bg-slate-50 dark:border-slate-700 dark:bg-slate-800/50";
}

function formatDate(date: string): string {
  if (!date) return "Unknown date";
  const d = date.slice(0, 10);
  if (d.match(/^\d{4}-\d{2}-\d{2}$/)) {
    const parts = d.split("-");
    const months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
    return `${months[parseInt(parts[1]) - 1]} ${parts[2]}, ${parts[0]}`;
  }
  return date;
}

export function ClassificationTimeline({ data }: Props) {
  if (!data) {
    return (
      <Card>
        <CardContent className="py-8 text-center text-sm text-slate-500">
          Classification timeline will be available after variant analysis.
        </CardContent>
      </Card>
    );
  }

  const history = data.history || [];

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle>Clinical Significance Timeline</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="mb-4 text-sm text-slate-500">
            How the clinical significance of <strong>{data.label}</strong> has been recorded across ClinVar submissions.
          </p>

          {history.length === 0 && (
            <div className="rounded-lg border border-slate-200 p-6 text-center dark:border-slate-700">
              <p className="text-sm text-slate-500">
                No historical classification data is available for this variant.
                This typically means only one submission or version exists in ClinVar.
              </p>
            </div>
          )}

          {history.length > 0 && (
            <div className="relative">
              <div className="absolute left-4 top-0 h-full w-0.5 bg-slate-200 dark:bg-slate-700" />

              <div className="space-y-6">
                {history.map((entry, i) => {
                  const isLast = i === history.length - 1;
                  return (
                    <div key={i} className="relative flex items-start gap-4">
                      <div className={`z-10 flex h-8 w-8 items-center justify-center rounded-full border-2 text-xs font-bold ${
                        getColorClass(entry.classification)
                      }`}>
                        {i + 1}
                      </div>
                      <div className="flex-1 pb-2">
                        <div className="mb-1 flex items-center gap-2">
                          <span className={`text-sm font-semibold ${
                            entry.classification.toLowerCase().includes("pathogenic")
                              ? "text-red-600"
                              : entry.classification.toLowerCase().includes("benign")
                                ? "text-emerald-600"
                                : "text-amber-600"
                          }`}>
                            {entry.classification}
                          </span>
                          <span className="text-[10px] text-slate-400">
                            {formatDate(entry.date)}
                          </span>
                        </div>
                        <p className="text-xs text-slate-500">
                          Review: {entry.review_status}
                        </p>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          <div className="mt-6 border-t border-slate-100 pt-4 dark:border-slate-700">
            <h4 className="mb-2 text-sm font-semibold text-slate-700 dark:text-slate-300">Current Status</h4>
            <div className={`inline-flex items-center gap-2 rounded-lg border px-3 py-1.5 ${getColorClass(data.current_classification)}`}>
              <span className="text-sm font-semibold">{data.current_classification}</span>
              <span className="text-[10px] opacity-75">({data.current_review_status})</span>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}