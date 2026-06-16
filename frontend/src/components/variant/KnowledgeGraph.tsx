"use client";

import { useCallback, useRef, useEffect, useState } from "react";
import type { GraphData } from "@/types";

interface Props {
  data: GraphData | null;
}

const TYPE_COLORS: Record<string, string> = {
  gene: "#3b82f6",
  variant: "#8b5cf6",
  paper: "#059669",
  disease: "#d97706",
};

const TYPE_LABELS: Record<string, string> = {
  gene: "Gene",
  variant: "Variant",
  paper: "Study",
  disease: "Disease",
};

export function KnowledgeGraph({ data }: Props) {
  const svgRef = useRef<SVGSVGElement>(null);
  const [tooltip, setTooltip] = useState<{ x: number; y: number; text: string } | null>(null);

  const layout = useCallback(() => {
    if (!data) return null;

    const nodes = data.nodes;
    const edges = data.edges;
    const W = 900;
    const H = 700;
    const cx = W / 2;
    const cy = H / 2;

    const positions: Record<string, { x: number; y: number }> = {};

    const variantNode = nodes.find((n) => n.type === "variant");
    if (variantNode) {
      positions[variantNode.id] = { x: cx, y: cy };
    }

    const geneNode = nodes.find((n) => n.type === "gene");
    if (geneNode) {
      positions[geneNode.id] = { x: cx, y: cy - 120 };
    }

    const diseaseNodes = nodes.filter((n) => n.type === "disease");
    diseaseNodes.forEach((node, i) => {
      const angle = (2 * Math.PI * i) / Math.max(1, diseaseNodes.length) - Math.PI / 2;
      positions[node.id] = {
        x: cx + 160 * Math.cos(angle),
        y: cy + 120 * Math.sin(angle),
      };
    });

    const paperNodes = nodes.filter((n) => n.type === "paper");
    const paperRadius = Math.min(340, 180 + paperNodes.length * 6);
    paperNodes.forEach((node, i) => {
      const angle = (2 * Math.PI * i) / Math.max(1, paperNodes.length) - Math.PI / 2;
      positions[node.id] = {
        x: cx + paperRadius * Math.cos(angle),
        y: cy + (paperRadius * 0.75) * Math.sin(angle),
      };
    });

    const otherNodes = nodes.filter(
      (n) => n.type !== "variant" && n.type !== "gene" && n.type !== "disease" && n.type !== "paper"
    );
    otherNodes.forEach((node, i) => {
      const angle = (2 * Math.PI * i) / Math.max(1, otherNodes.length);
      positions[node.id] = {
        x: cx + 400 * Math.cos(angle),
        y: cy + 300 * Math.sin(angle),
      };
    });

    return { nodes, edges, positions, W, H };
  }, [data]);

  const result = layout();

  if (!data || data.nodes.length === 0) {
    return (
      <p className="py-8 text-center text-sm text-slate-500">
        Knowledge graph data will appear here after evidence retrieval.
      </p>
    );
  }

  const labelWidth = (text: string) => Math.min(text.length * 7, 180);

  return (
    <div className="relative overflow-hidden rounded-lg border border-slate-200 dark:border-slate-700">
      <svg
        ref={svgRef}
        viewBox={`0 0 ${result?.W || 900} ${result?.H || 700}`}
        className="h-[500px] w-full bg-slate-50 dark:bg-slate-800/50"
      >
        <defs>
          <marker id="arrowhead" markerWidth="8" markerHeight="6" refX="8" refY="3" orient="auto">
            <polygon points="0 0, 8 3, 0 6" fill="#94a3b8" />
          </marker>
        </defs>

        {result?.edges.map((edge, i) => {
          const source = result.positions[edge.source];
          const target = result.positions[edge.target];
          if (!source || !target) return null;

          const mx = (source.x + target.x) / 2;
          const my = (source.y + target.y) / 2;
          const labelLen = labelWidth(edge.label);

          return (
            <g key={`edge-${i}`}>
              <line
                x1={source.x}
                y1={source.y}
                x2={target.x}
                y2={target.y}
                stroke="#94a3b8"
                strokeWidth={1.5}
                strokeDasharray="4 2"
                markerEnd="url(#arrowhead)"
              />
              <rect
                x={mx - labelLen / 2 - 4}
                y={my - 10}
                width={labelLen + 8}
                height={16}
                fill="white"
                rx={3}
                className="dark:fill-slate-700"
                opacity={0.85}
              />
              <text
                x={mx}
                y={my + 3}
                textAnchor="middle"
                fontSize={9}
                fill="#64748b"
                className="dark:fill-slate-300"
              >
                {edge.label}
              </text>
            </g>
          );
        })}

        {result?.nodes.map((node) => {
          const pos = result.positions[node.id];
          if (!pos) return null;
          const color = TYPE_COLORS[node.type] || "#64748b";
          const r = node.type === "paper" ? 22 : 28;
          const lw = labelWidth(node.label);
          const truncated = node.label.length > 25;

          return (
            <g
              key={node.id}
              onMouseEnter={(e) => {
                const rect = svgRef.current?.getBoundingClientRect();
                if (rect) {
                  setTooltip({
                    x: e.clientX - rect.left,
                    y: e.clientY - rect.top - 10,
                    text: `${node.label} (${TYPE_LABELS[node.type] || node.type})`,
                  });
                }
              }}
              onMouseLeave={() => setTooltip(null)}
              className="cursor-default"
            >
              {node.type === "paper" ? (
                <>
                  <rect
                    x={pos.x - lw / 2 - 6}
                    y={pos.y - r}
                    width={lw + 12}
                    height={r * 2}
                    rx={6}
                    fill={color}
                    opacity={0.9}
                  />
                  <text
                    x={pos.x}
                    y={pos.y + 1}
                    textAnchor="middle"
                    fontSize={8}
                    fill="white"
                    fontWeight="bold"
                  >
                    {truncated ? node.label.slice(0, 22) + "…" : node.label}
                  </text>
                  <text
                    x={pos.x}
                    y={pos.y + r + 12}
                    textAnchor="middle"
                    fontSize={7}
                    fill="#64748b"
                    className="dark:fill-slate-400"
                  >
                    {TYPE_LABELS[node.type]}
                  </text>
                </>
              ) : (
                <>
                  <circle cx={pos.x} cy={pos.y} r={r} fill={color} opacity={0.9} />
                  <text
                    x={pos.x}
                    y={pos.y + 4}
                    textAnchor="middle"
                    fontSize={10}
                    fill="white"
                    fontWeight="bold"
                  >
                    {node.label.slice(0, 14)}
                  </text>
                  <text
                    x={pos.x}
                    y={pos.y + r + 14}
                    textAnchor="middle"
                    fontSize={8}
                    fill="#64748b"
                    className="dark:fill-slate-400"
                  >
                    {TYPE_LABELS[node.type]}
                  </text>
                </>
              )}
            </g>
          );
        })}
      </svg>

      {tooltip && (
        <div
          className="pointer-events-none absolute z-10 rounded bg-slate-800 px-2 py-1 text-xs text-white shadow-lg dark:bg-slate-200 dark:text-slate-800"
          style={{ left: tooltip.x, top: tooltip.y }}
        >
          {tooltip.text}
        </div>
      )}
    </div>
  );
}
