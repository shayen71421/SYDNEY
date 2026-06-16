"use client";

import { Lightbulb, AlertCircle, CheckCircle2 } from "lucide-react";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import type { ResearchGaps } from "@/types";

interface Props {
  gaps: ResearchGaps | null;
}

export function GapsAnalysis({ gaps }: Props) {
  if (!gaps) {
    return (
      <Card>
        <CardContent className="py-8 text-center text-sm text-slate-500">
          Research gap analysis will be available after evidence retrieval.
        </CardContent>
      </Card>
    );
  }

  const ruleBased = gaps.rule_based;

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle>Research Gap Analysis</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="mb-4 flex items-center gap-2">
            {ruleBased.well_studied ? (
              <CheckCircle2 className="h-5 w-5 text-emerald-500" />
            ) : (
              <AlertCircle className="h-5 w-5 text-amber-500" />
            )}
            <span className="text-sm font-medium">
              {ruleBased.well_studied ? "Well-Studied Variant" : "Poorly Studied Variant"}
            </span>
            <Badge variant={ruleBased.well_studied ? "success" : "warning"}>
              {ruleBased.total_papers} papers
            </Badge>
          </div>

          <p className="mb-4 text-sm text-slate-600 dark:text-slate-400">
            {ruleBased.summary}
          </p>

          {ruleBased.gaps.length > 0 && (
            <div>
              <h4 className="mb-2 text-sm font-medium text-slate-700 dark:text-slate-300">
                Identified Gaps
              </h4>
              <ul className="space-y-2">
                {ruleBased.gaps.map((gap, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm text-slate-600 dark:text-slate-400">
                    <Lightbulb className="mt-0.5 h-4 w-4 flex-shrink-0 text-amber-500" />
                    {gap}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {Object.keys(ruleBased.paper_types).length > 0 && (
            <div className="mt-4">
              <h4 className="mb-2 text-sm font-medium text-slate-700 dark:text-slate-300">
                Study Type Distribution
              </h4>
              <div className="flex flex-wrap gap-2">
                {Object.entries(ruleBased.paper_types).map(([type, count]) => (
                  <Badge key={type} variant="outline">
                    {type}: {count}
                  </Badge>
                ))}
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {gaps.ai_analysis && (
        <Card>
          <CardHeader>
            <CardTitle>AI-Generated Research Directions</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="prose prose-sm max-w-none dark:prose-invert">
              {gaps.ai_analysis.split("\n").map((line, i) => {
                if (!line.trim()) return <br key={i} />;
                return (
                  <p key={i} className="text-sm text-slate-700 dark:text-slate-300">
                    {line}
                  </p>
                );
              })}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
