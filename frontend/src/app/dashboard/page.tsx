"use client";

import Link from "next/link";
import {
  FlaskConical,
  FileText,
  Dna,
  Activity,
  TrendingUp,
  BarChart3,
} from "lucide-react";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/Card";
import { useDashboard, useVariants } from "@/lib/hooks";
import { formatScore } from "@/lib/utils";

export default function DashboardPage() {
  const { data: stats, isLoading } = useDashboard();
  const { data: variants } = useVariants();

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-sydney-500 border-t-transparent" />
      </div>
    );
  }

  const statCards = [
    {
      label: "Variants",
      value: stats?.total_variants ?? 0,
      icon: Dna,
      color: "text-violet-600 bg-violet-100 dark:bg-violet-900/30",
    },
    {
      label: "Papers",
      value: stats?.total_papers ?? 0,
      icon: FileText,
      color: "text-emerald-600 bg-emerald-100 dark:bg-emerald-900/30",
    },
    {
      label: "Genes",
      value: stats?.total_genes ?? 0,
      icon: FlaskConical,
      color: "text-blue-600 bg-blue-100 dark:bg-blue-900/30",
    },
    {
      label: "Diseases",
      value: stats?.total_diseases ?? 0,
      icon: Activity,
      color: "text-amber-600 bg-amber-100 dark:bg-amber-900/30",
    },
  ];

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-slate-900 dark:text-white">
          Dashboard
        </h1>
        <p className="mt-1 text-sm text-slate-500">
          Overview of the variant intelligence platform
        </p>
      </div>

      <div className="mb-8 grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {statCards.map((card) => (
          <Card key={card.label}>
            <CardContent>
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-slate-500">{card.label}</p>
                  <p className="text-3xl font-bold text-slate-900 dark:text-white">
                    {card.value}
                  </p>
                </div>
                <div className={`rounded-lg p-3 ${card.color}`}>
                  <card.icon className="h-6 w-6" />
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Recent Variants</CardTitle>
          </CardHeader>
          <CardContent>
            {variants && variants.length > 0 ? (
              <div className="space-y-2">
                {variants.slice(0, 10).map((v) => (
                  <Link
                    key={v.id}
                    href={`/variants/${v.id}`}
                    className="flex items-center justify-between rounded-md px-3 py-2 text-sm hover:bg-slate-50 dark:hover:bg-slate-700/50"
                  >
                    <div>
                      <span className="font-medium text-slate-900 dark:text-white">
                        {v.gene} {v.hgvs_c || v.protein_change || ""}
                      </span>
                    </div>
                    <span className="text-xs text-slate-500">
                      {v.clinical_significance || "Pending"}
                    </span>
                  </Link>
                ))}
              </div>
            ) : (
              <p className="py-4 text-center text-sm text-slate-500">
                No variants analyzed yet. Search for a variant to get started.
              </p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Quick Actions</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              <Link
                href="/"
                className="flex items-center gap-3 rounded-lg border border-slate-200 p-3 text-sm transition-colors hover:border-sydney-500 hover:bg-sydney-50 dark:border-slate-700 dark:hover:border-sydney-400 dark:hover:bg-sydney-900/20"
              >
                <TrendingUp className="h-5 w-5 text-sydney-600" />
                <div>
                  <p className="font-medium text-slate-900 dark:text-white">Search New Variant</p>
                  <p className="text-xs text-slate-500">Analyze BRCA1, BRCA2, TP53, CDH1, PALB2, CHEK2, ATM, or PTEN variants</p>
                </div>
              </Link>
              <div className="flex items-center gap-3 rounded-lg border border-slate-200 p-3 text-sm dark:border-slate-700">
                <BarChart3 className="h-5 w-5 text-sydney-600" />
                <div>
                  <p className="font-medium text-slate-900 dark:text-white">
                    Evidence-Based Scoring
                  </p>
                  <p className="text-xs text-slate-500">
                    Each paper scored on relevance, quality, and recency
                  </p>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
