"use client";

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";
import type { EvidenceItem } from "@/types";

interface Props {
  evidence: EvidenceItem[];
}

export function EvidenceChart({ evidence }: Props) {
  const data = evidence
    .sort((a, b) => b.evidence_score - a.evidence_score)
    .slice(0, 10)
    .map((e) => ({
      name: `PMID:${e.pmid}`,
      score: Math.round(e.evidence_score * 100),
      relevance: Math.round(e.relevance_score * 100),
      quality: Math.round(e.study_quality_score * 100),
      recency: Math.round(e.recency_score * 100),
    }));

  if (data.length === 0) {
    return <p className="py-4 text-center text-sm text-slate-500">No data available</p>;
  }

  return (
    <div className="h-64">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
          <XAxis
            dataKey="name"
            tick={{ fontSize: 10 }}
            angle={-30}
            textAnchor="end"
          />
          <YAxis domain={[0, 100]} tick={{ fontSize: 11 }} />
          <Tooltip
            contentStyle={{
              background: "#fff",
              border: "1px solid #e2e8f0",
              borderRadius: "6px",
              fontSize: "12px",
            }}
          />
          <Bar dataKey="score" name="Evidence Score" radius={[4, 4, 0, 0]}>
            {data.map((_, i) => (
              <Cell
                key={i}
                fill={data[i].score >= 70 ? "#059669" : data[i].score >= 40 ? "#d97706" : "#dc2626"}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
