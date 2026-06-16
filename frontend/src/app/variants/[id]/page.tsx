"use client";

import { use, useState } from "react";
import Link from "next/link";
import {
  ArrowLeft,
  Download,
  Brain,
  Network,
  AlertTriangle,
  CheckCircle,
  XCircle,
  HelpCircle,
  BarChart3,
  ArrowLeftRight,
  Sparkles,
} from "lucide-react";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Tabs } from "@/components/ui/Tabs";
import { EvidenceChart } from "@/components/variant/EvidenceChart";
import { EvidenceTable } from "@/components/variant/EvidenceTable";
import { KnowledgeGraph } from "@/components/variant/KnowledgeGraph";
import { GapsAnalysis } from "@/components/variant/GapsAnalysis";
import { ConfidenceBreakdown } from "@/components/variant/ConfidenceBreakdown";
import { PublicationTrends } from "@/components/variant/PublicationTrends";
import { VariantCompare } from "@/components/variant/VariantCompare";
import { WhyMatters } from "@/components/variant/WhyMatters";
import { useVariantDetail, useReport, useAISummary, useEvidence, useGraph, useGaps, usePublicationTrends } from "@/lib/hooks";
import { formatScore, significanceColor, confidenceColor, confidenceBg } from "@/lib/utils";
import { api } from "@/lib/api";

export default function VariantPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const variantId = parseInt(id);
  const [showAISummary, setShowAISummary] = useState(false);

  const { data: detail, isLoading: detailLoading } = useVariantDetail(variantId);
  const { data: report } = useReport(variantId);
  const { data: evidence } = useEvidence(variantId);
  const { data: graph } = useGraph(variantId);
  const { data: gaps } = useGaps(variantId);
  const { data: trends } = usePublicationTrends(variantId);
  const summaryMutation = useAISummary();

  if (detailLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-sydney-500 border-t-transparent" />
      </div>
    );
  }

  if (!detail) {
    return (
      <div className="py-20 text-center text-slate-500">
        Variant not found.
      </div>
    );
  }

  async function handleDownloadPdf() {
    try {
      const blob = await api.downloadPdf(variantId);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `sydney_report_${variantId}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      alert("Failed to download PDF");
    }
  }

  function handleGenerateSummary() {
    setShowAISummary(true);
    if (!summaryMutation.data) {
      summaryMutation.mutate(variantId);
    }
  }

  const sigIcon = (sig: string | null) => {
    if (!sig) return <HelpCircle className="h-4 w-4" />;
    const s = sig.toLowerCase();
    if (s.includes("pathogenic")) return <XCircle className="h-4 w-4" />;
    if (s.includes("benign")) return <CheckCircle className="h-4 w-4" />;
    return <AlertTriangle className="h-4 w-4" />;
  };

  const totalScore = report
    ? Math.round(
        report.evidence_volume * 30 +
          report.evidence_quality * 100 * 40 +
          report.study_agreement * 100 * 30
      )
    : 0;

  const tabs = [
    {
      id: "overview",
      label: "Overview",
      content: (
        <div className="grid gap-4 md:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle>Variant Information</CardTitle>
            </CardHeader>
            <CardContent>
              <dl className="space-y-3 text-sm">
                <div className="flex justify-between">
                  <dt className="text-slate-500">Gene</dt>
                  <dd className="font-medium">{detail.gene}</dd>
                </div>
                {detail.hgvs_c && (
                  <div className="flex justify-between">
                    <dt className="text-slate-500">HGVS c.</dt>
                    <dd className="font-mono text-xs">{detail.hgvs_c}</dd>
                  </div>
                )}
                {detail.hgvs_p && (
                  <div className="flex justify-between">
                    <dt className="text-slate-500">HGVS p.</dt>
                    <dd className="font-mono text-xs">{detail.hgvs_p}</dd>
                  </div>
                )}
                {detail.protein_change && (
                  <div className="flex justify-between">
                    <dt className="text-slate-500">Protein Change</dt>
                    <dd className="font-mono text-xs">{detail.protein_change}</dd>
                  </div>
                )}
                <div className="flex justify-between">
                  <dt className="text-slate-500">Variant Type</dt>
                  <dd>{detail.variant_type || "SNV"}</dd>
                </div>
                {detail.clinvar_id && (
                  <div className="flex justify-between">
                    <dt className="text-slate-500">ClinVar ID</dt>
                    <dd className="font-mono text-xs">{detail.clinvar_id}</dd>
                  </div>
                )}
              </dl>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Clinical Significance</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="mb-4 flex items-center gap-2">
                <span className={significanceColor(detail.clinical_significance)}>
                  {sigIcon(detail.clinical_significance)}
                </span>
                <span className={`text-lg font-semibold ${significanceColor(detail.clinical_significance)}`}>
                  {detail.clinical_significance || "Not determined"}
                </span>
              </div>
              {detail.review_status && (
                <p className="text-sm text-slate-500">
                  Review Status: {detail.review_status}
                </p>
              )}
              {detail.diseases && detail.diseases.length > 0 && (
                <div className="mt-3">
                  <p className="mb-2 text-sm font-medium text-slate-500">Associated Diseases</p>
                  <div className="flex flex-wrap gap-2">
                    {detail.diseases.map((d, i) => (
                      <Badge key={i} variant="outline">{d}</Badge>
                    ))}
                  </div>
                </div>
              )}
              <div className="mt-4 border-t border-slate-100 pt-4 dark:border-slate-700">
                <div className="mb-2 flex items-center gap-1.5">
                  <Sparkles className="h-3.5 w-3.5 text-slate-400" />
                  <span className="text-xs font-medium text-slate-500">Why This Variant Matters</span>
                </div>
                <WhyMatters variantId={variantId} />
              </div>
            </CardContent>
          </Card>

          {report && (
            <Card className="md:col-span-2">
              <CardHeader>
                <CardTitle>Confidence Assessment</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid gap-4 md:grid-cols-4">
                  <div className={`rounded-lg border p-3 text-center ${confidenceBg(report.confidence_level)}`}>
                    <p className={`text-2xl font-bold ${confidenceColor(report.confidence_level)}`}>
                      {report.confidence_level}
                    </p>
                    <p className="mt-1 text-xs text-slate-500">Confidence</p>
                  </div>
                  <div className="rounded-lg border border-slate-200 p-3 text-center dark:border-slate-700">
                    <p className="text-2xl font-bold text-slate-900 dark:text-white">
                      {formatScore(report.confidence_score)}
                    </p>
                    <p className="mt-1 text-xs text-slate-500">Score</p>
                  </div>
                  <div className="rounded-lg border border-slate-200 p-3 text-center dark:border-slate-700">
                    <p className="text-2xl font-bold text-slate-900 dark:text-white">
                      {report.evidence_volume}
                    </p>
                    <p className="mt-1 text-xs text-slate-500">Papers</p>
                  </div>
                  <div className="rounded-lg border border-slate-200 p-3 text-center dark:border-slate-700">
                    <p className="text-2xl font-bold text-slate-900 dark:text-white">
                      {totalScore}
                    </p>
                    <p className="mt-1 text-xs text-slate-500">Weighted Total</p>
                  </div>
                </div>
                {report.evidence_overview && (
                  <p className="mt-3 text-sm text-slate-600 dark:text-slate-400">
                    {report.evidence_overview}
                  </p>
                )}
                <div className="mt-6 border-t border-slate-100 pt-4 dark:border-slate-700">
                  <h4 className="mb-3 text-sm font-semibold text-slate-700 dark:text-slate-300">
                    Confidence Breakdown
                  </h4>
                  <ConfidenceBreakdown report={report} />
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      ),
    },
    {
      id: "evidence",
      label: "Evidence",
      content: (
        <div className="space-y-4">
          {evidence && evidence.length > 0 ? (
            <>
              <Card>
                <CardHeader>
                  <CardTitle>Evidence Score Distribution</CardTitle>
                </CardHeader>
                <CardContent>
                  <EvidenceChart evidence={evidence} />
                </CardContent>
              </Card>
              <EvidenceTable evidence={evidence} />
            </>
          ) : (
            <Card>
              <CardContent className="py-8 text-center text-slate-500">
                No evidence retrieved yet. The variant was analyzed but no PubMed results were found.
              </CardContent>
            </Card>
          )}
          <div className="flex justify-end">
            <Button variant="outline" onClick={handleDownloadPdf}>
              <Download className="mr-2 h-4 w-4" />
              Download PDF Report
            </Button>
          </div>
        </div>
      ),
    },
    {
      id: "ai-summary",
      label: "AI Summary",
      content: (
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>AI Research Summary</CardTitle>
              {!showAISummary && (
                <Button size="sm" onClick={handleGenerateSummary}>
                  <Brain className="mr-2 h-4 w-4" />
                  Generate Summary
                </Button>
              )}
            </div>
          </CardHeader>
          <CardContent>
            {!showAISummary ? (
              <p className="text-sm text-slate-500">
                Generate an AI-powered research summary with executive summary, clinical significance,
                disease associations, and confidence assessment.
              </p>
            ) : summaryMutation.isPending ? (
              <div className="flex items-center justify-center py-8">
                <div className="h-6 w-6 animate-spin rounded-full border-2 border-sydney-500 border-t-transparent" />
                <span className="ml-3 text-sm text-slate-500">Generating summary...</span>
              </div>
            ) : summaryMutation.isError ? (
              <p className="text-sm text-red-500">Failed to generate summary.</p>
            ) : (
              <div className="prose prose-sm max-w-none dark:prose-invert">
                {summaryMutation.data?.summary?.split("\n").map((line, i) => {
                  if (line.startsWith("**") && line.endsWith("**")) {
                    return (
                      <h3 key={i} className="mt-4 mb-2 text-base font-semibold text-slate-800 dark:text-slate-200">
                        {line.replace(/\*\*/g, "")}
                      </h3>
                    );
                  }
                  if (line.startsWith("#")) {
                    return (
                      <h2 key={i} className="mt-4 mb-2 text-lg font-bold text-slate-900 dark:text-white">
                        {line.replace(/^#+\s*/, "")}
                      </h2>
                    );
                  }
                  if (line.trim().startsWith("-") || line.trim().startsWith("*")) {
                    return (
                      <li key={i} className="ml-4 text-slate-700 dark:text-slate-300">
                        {line.replace(/^[\s*\-]+/, "")}
                      </li>
                    );
                  }
                  if (!line.trim()) return <br key={i} />;
                  return (
                    <p key={i} className="text-slate-700 dark:text-slate-300">
                      {line}
                    </p>
                  );
                })}
              </div>
            )}
          </CardContent>
        </Card>
      ),
    },
    {
      id: "trends",
      label: "Publication Trends",
      content: (
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <BarChart3 className="h-5 w-5 text-slate-400" />
              <CardTitle>Research Activity Trend</CardTitle>
            </div>
          </CardHeader>
          <CardContent>
            {trends && trends.trends.length > 0 ? (
              <>
                <PublicationTrends trends={trends.trends} />
                <div className="mt-4 grid grid-cols-2 gap-3 text-sm md:grid-cols-4">
                  <div className="rounded-lg border border-slate-200 p-3 text-center dark:border-slate-700">
                    <p className="text-xl font-bold text-slate-900 dark:text-white">
                      {trends.trends.length}
                    </p>
                    <p className="text-xs text-slate-500">Years of Data</p>
                  </div>
                  <div className="rounded-lg border border-slate-200 p-3 text-center dark:border-slate-700">
                    <p className="text-xl font-bold text-slate-900 dark:text-white">
                      {trends.trends.reduce((s, t) => s + t.count, 0)}
                    </p>
                    <p className="text-xs text-slate-500">Total Papers</p>
                  </div>
                  <div className="rounded-lg border border-slate-200 p-3 text-center dark:border-slate-700">
                    <p className="text-xl font-bold text-slate-900 dark:text-white">
                      {trends.trends[trends.trends.length - 1]?.year || "-"}
                    </p>
                    <p className="text-xs text-slate-500">Most Recent Year</p>
                  </div>
                  <div className="rounded-lg border border-slate-200 p-3 text-center dark:border-slate-700">
                    <p className="text-xl font-bold text-slate-900 dark:text-white">
                      {trends.trends[trends.trends.length - 1]?.count || 0}
                    </p>
                    <p className="text-xs text-slate-500">Papers (Latest Year)</p>
                  </div>
                </div>
              </>
            ) : (
              <p className="py-6 text-center text-sm text-slate-500">
                No publication trend data available. Search a variant with PubMed results to see trends.
              </p>
            )}
          </CardContent>
        </Card>
      ),
    },
    {
      id: "graph",
      label: "Knowledge Graph",
      content: (
        <Card>
          <CardHeader>
            <CardTitle>Knowledge Relationships</CardTitle>
          </CardHeader>
          <CardContent>
            <KnowledgeGraph data={graph || null} />
          </CardContent>
        </Card>
      ),
    },
    {
      id: "gaps",
      label: "Research Gaps",
      content: <GapsAnalysis gaps={gaps || null} />,
    },
    {
      id: "compare",
      label: "Compare",
      content: (
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <ArrowLeftRight className="h-5 w-5 text-slate-400" />
              <CardTitle>Variant Comparison</CardTitle>
            </div>
          </CardHeader>
          <CardContent>
            <VariantCompare defaultQuery={`${detail.gene} ${detail.hgvs_c || detail.protein_change || ""}`} />
          </CardContent>
        </Card>
      ),
    },
  ];

  return (
    <div>
      <Link
        href="/"
        className="mb-4 flex items-center gap-1 text-sm text-slate-500 hover:text-slate-700"
      >
        <ArrowLeft className="h-4 w-4" />
        Back to search
      </Link>

      <div className="mb-6">
        <h1 className="text-2xl font-bold text-slate-900 dark:text-white">
          {detail.gene} {detail.hgvs_c || detail.protein_change || ""}
        </h1>
        <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
          {detail.gene_full_name}
        </p>
      </div>

      <Tabs tabs={tabs} />
    </div>
  );
}
