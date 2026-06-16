"use client";

import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import type { ACMGClassificationResponse, ACMGCriterion } from "@/types";

interface Props {
  acmg: ACMGClassificationResponse | null;
}

const strengthColors: Record<string, string> = {
  "Very Strong": "bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300",
  "Strong": "bg-orange-100 text-orange-700 dark:bg-orange-900 dark:text-orange-300",
  "Moderate": "bg-amber-100 text-amber-700 dark:bg-amber-900 dark:text-amber-300",
  "Supporting": "bg-sky-100 text-sky-700 dark:bg-sky-900 dark:text-sky-300",
};

const classColors: Record<string, string> = {
  "Pathogenic": "text-red-600",
  "Likely pathogenic": "text-orange-600",
  "Uncertain significance": "text-amber-600",
  "Likely benign": "text-emerald-600",
  "Benign": "text-emerald-600",
};

const strengthValues: Record<string, number> = {
  "Very Strong": 4,
  "Strong": 3,
  "Moderate": 2,
  "Supporting": 1,
};

export function ACMGClassification({ acmg }: Props) {
  if (!acmg) {
    return (
      <Card>
        <CardContent className="py-8 text-center text-sm text-slate-500">
          ACMG classification will be available after variant analysis.
        </CardContent>
      </Card>
    );
  }

  const pathoCodes = acmg.criteria.filter(c => c.classification === "Pathogenic").map(c => c.code).join(", ");
  const benignCodes = acmg.criteria.filter(c => c.classification === "Benign").map(c => c.code).join(", ");

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>ACMG/AMP Classification</CardTitle>
            <Badge variant={acmg.classification === "Pathogenic" || acmg.classification === "Likely pathogenic" ? "danger" : acmg.classification === "Uncertain significance" ? "warning" : "success"}>
              {acmg.classification}
            </Badge>
          </div>
        </CardHeader>
        <CardContent>
          <div className="mb-4 grid grid-cols-3 gap-3">
            <div className="rounded-lg border border-slate-200 p-3 text-center dark:border-slate-700">
              <p className="text-xl font-bold text-red-600">{acmg.pathogenic_score}</p>
              <p className="text-xs text-slate-500">Pathogenic Score</p>
            </div>
            <div className="rounded-lg border border-slate-200 p-3 text-center dark:border-slate-700">
              <p className="text-xl font-bold text-emerald-600">{acmg.benign_score}</p>
              <p className="text-xs text-slate-500">Benign Score</p>
            </div>
            <div className="rounded-lg border border-slate-200 p-3 text-center dark:border-slate-700">
              <p className={`text-xl font-bold ${acmg.net_score >= 0 ? "text-red-600" : "text-emerald-600"}`}>
                {acmg.net_score >= 0 ? "+" : ""}{acmg.net_score}
              </p>
              <p className="text-xs text-slate-500">Net Score</p>
            </div>
          </div>

          {acmg.summary && (
            <p className="mb-4 text-sm text-slate-600 dark:text-slate-400">{acmg.summary}</p>
          )}

          {acmg.criteria.length > 0 && (
            <div className="space-y-2">
              <h4 className="text-sm font-medium text-slate-700 dark:text-slate-300">Met Criteria</h4>
              <div className="space-y-2">
                {acmg.criteria.map((c, i) => (
                  <CriterionCard key={i} criterion={c} />
                ))}
              </div>
            </div>
          )}

          {acmg.criteria.length === 0 && (
            <p className="py-4 text-center text-sm text-slate-500">No ACMG criteria were triggered for this variant.</p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function CriterionCard({ criterion }: { criterion: ACMGCriterion }) {
  return (
    <div className="flex items-start gap-3 rounded-lg border border-slate-100 p-3 dark:border-slate-700">
      <div className="flex-shrink-0">
        <Badge className={strengthColors[criterion.strength] || ""}>
          {criterion.code}
        </Badge>
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span className={`text-xs font-semibold ${classColors[criterion.classification] || "text-slate-600"}`}>
            {criterion.strength}
          </span>
          <span className="text-xs text-slate-400">
            ({strengthValues[criterion.strength] || 0} pt{criterion.classification === "Pathogenic" ? " pathogenicity" : " benign"})
          </span>
        </div>
        <p className="text-xs text-slate-600 dark:text-slate-400 mt-0.5">{criterion.description}</p>
        <p className="text-[10px] text-slate-400 mt-0.5 italic">{criterion.evidence}</p>
      </div>
    </div>
  );
}
