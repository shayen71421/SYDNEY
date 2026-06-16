"use client";

import { useState } from "react";
import { ArrowLeftRight, AlertCircle, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { useCompareVariants } from "@/lib/hooks";
import { formatScore, significanceColor } from "@/lib/utils";
import type { CompareVariantData } from "@/types";

export function VariantCompare({ defaultQuery = "" }: { defaultQuery?: string }) {
  const [query2, setQuery2] = useState("");
  const [error, setError] = useState("");
  const compareMutation = useCompareVariants();

  const handleCompare = () => {
    if (!defaultQuery.trim() || !query2.trim()) {
      setError("Enter a variant to compare against");
      return;
    }
    setError("");
    compareMutation.mutate({ query1: defaultQuery.trim(), query2: query2.trim() });
  };

  const Row = ({ label, v1, v2, format }: {
    label: string;
    v1: string | number;
    v2: string | number;
    format?: (v: string | number) => string;
  }) => {
    const f1 = format ? format(v1) : String(v1);
    const f2 = format ? format(v2) : String(v2);
    return (
      <tr className="border-b border-slate-100 last:border-0 dark:border-slate-700">
        <td className="py-2.5 pr-4 text-sm text-slate-500">{label}</td>
        <td className="py-2.5 pr-4 text-right text-sm font-medium text-slate-800 dark:text-white">{f1}</td>
        <td className="py-2.5 text-right text-sm font-medium text-slate-800 dark:text-white">{f2}</td>
      </tr>
    );
  };

  const sigBadge = (sig: string | null) => {
    if (!sig) return "-";
    return (
      <span className={significanceColor(sig)}>
        {sig}
      </span>
    );
  };

  return (
    <div className="space-y-4">
      <div className="flex gap-3">
        <input
          type="text"
          value={defaultQuery}
          readOnly
          className="flex-1 rounded-lg border border-slate-300 bg-slate-50 px-3 py-2 text-sm text-slate-600 dark:border-slate-600 dark:bg-slate-700 dark:text-slate-400"
        />
        <input
          type="text"
          value={query2}
          onChange={(e) => setQuery2(e.target.value)}
          placeholder="e.g. TP53 R273H"
          className="flex-1 rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm placeholder:text-slate-400 focus:border-sydney-500 focus:outline-none dark:border-slate-600 dark:bg-slate-800 dark:text-white"
          onKeyDown={(e) => e.key === "Enter" && handleCompare()}
        />
        <Button onClick={handleCompare} loading={compareMutation.isPending}>
          <ArrowLeftRight className="mr-2 h-4 w-4" />
          Compare
        </Button>
      </div>

      {error && (
        <div className="flex items-center gap-2 rounded-md bg-red-50 p-2 text-xs text-red-700 dark:bg-red-900/20 dark:text-red-400">
          <AlertCircle className="h-3 w-3" />
          {error}
        </div>
      )}

      {compareMutation.isPending && (
        <div className="flex items-center justify-center py-4 text-sm text-slate-500">
          <Loader2 className="mr-2 h-4 w-4 animate-spin" />
          Analyzing variants...
        </div>
      )}

      {compareMutation.data && (
        <div className="overflow-x-auto rounded-lg border border-slate-200 dark:border-slate-700">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50 dark:border-slate-700 dark:bg-slate-800/50">
                <th className="py-2.5 pr-4 text-left text-xs font-medium text-slate-500 uppercase">Metric</th>
                <th className="py-2.5 pr-4 text-right text-xs font-medium text-slate-500 uppercase">
                  {compareMutation.data.variant1.label}
                </th>
                <th className="py-2.5 text-right text-xs font-medium text-slate-500 uppercase">
                  {compareMutation.data.variant2.label}
                </th>
              </tr>
            </thead>
            <tbody>
              <Row label="Gene" v1={compareMutation.data.variant1.gene} v2={compareMutation.data.variant2.gene} />
              <Row label="Papers" v1={compareMutation.data.variant1.papers} v2={compareMutation.data.variant2.papers} />
              <Row label="Confidence Score" v1={formatScore(compareMutation.data.variant1.confidence_score)} v2={formatScore(compareMutation.data.variant2.confidence_score)} />
              <Row label="Confidence Level" v1={compareMutation.data.variant1.confidence_level} v2={compareMutation.data.variant2.confidence_level} />
              <Row label="Evidence Volume" v1={compareMutation.data.variant1.evidence_volume} v2={compareMutation.data.variant2.evidence_volume} />
              <Row label="Evidence Quality" v1={formatScore(compareMutation.data.variant1.evidence_quality)} v2={formatScore(compareMutation.data.variant2.evidence_quality)} />
              <Row label="Study Agreement" v1={formatScore(compareMutation.data.variant1.study_agreement)} v2={formatScore(compareMutation.data.variant2.study_agreement)} />
              <tr className="border-b border-slate-100 last:border-0 dark:border-slate-700">
                <td className="py-2.5 pr-4 text-sm text-slate-500">Clinical Significance</td>
                <td className="py-2.5 pr-4 text-right text-sm font-medium">{sigBadge(compareMutation.data.variant1.clinical_significance)}</td>
                <td className="py-2.5 text-right text-sm font-medium">{sigBadge(compareMutation.data.variant2.clinical_significance)}</td>
              </tr>
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
