"use client";

import { useCallback, useRef, useEffect } from "react";
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

export function KnowledgeGraph({ data }: Props) {
  const svgRef = useRef<SVGSVGElement>(null);

  const layout = useCallback(() => {
    if (!data || !svgRef.current) return;

    const nodes = data.nodes;
    const edges = data.edges;
    const cx = 300;
    const cy = 200;
    const radius = 150;

    const positions: Record<string, { x: number; y: number }> = {};
    const angleStep = (2 * Math.PI) / nodes.length;

    nodes.forEach((node, i) => {
      const angle = angleStep * i - Math.PI / 2;
      positions[node.id] = {
        x: cx + radius * Math.cos(angle),
        y: cy + radius * Math.sin(angle),
      };
    });

    const variantNode = nodes.find((n) => n.type === "variant");
    if (variantNode) {
      positions[variantNode.id] = { x: cx, y: cy };
    }

    const geneNode = nodes.find((n) => n.type === "gene");
    if (geneNode) {
      positions[geneNode.id] = { x: cx, y: cy - 100 };
    }

    let paperIdx = 0;
    const diseaseNodes = nodes.filter((n) => n.type === "disease");
    const paperNodes = nodes.filter((n) => n.type === "paper");

    paperNodes.forEach((node) => {
      const angle = (2 * Math.PI * paperIdx) / Math.max(1, paperNodes.length) + Math.PI / 4;
      positions[node.id] = {
        x: cx + 120 * Math.cos(angle),
        y: cy + 80 * Math.sin(angle),
      };
      paperIdx++;
    });

    diseaseNodes.forEach((node, i) => {
      const angle = (2 * Math.PI * i) / Math.max(1, diseaseNodes.length) - Math.PI / 2;
      positions[node.id] = {
        x: cx + 160 * Math.cos(angle),
        y: cy + 100 * Math.sin(angle),
      };
    });

    return { nodes, edges, positions };
  }, [data]);

  const result = layout();

  if (!data || data.nodes.length === 0) {
    return (
      <p className="py-8 text-center text-sm text-slate-500">
        Knowledge graph data will appear here after evidence retrieval.
      </p>
    );
  }

  return (
    <div className="overflow-hidden rounded-lg border border-slate-200 dark:border-slate-700">
      <svg
        ref={svgRef}
        viewBox="0 0 600 400"
        className="h-80 w-full bg-slate-50 dark:bg-slate-800/50"
      >
        {result?.edges.map((edge, i) => {
          const source = result.positions[edge.source];
          const target = result.positions[edge.target];
          if (!source || !target) return null;
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
              />
              <text
                x={(source.x + target.x) / 2}
                y={(source.y + target.y) / 2 - 6}
                textAnchor="middle"
                fontSize={8}
                fill="#94a3b8"
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
          return (
            <g key={node.id}>
              <circle cx={pos.x} cy={pos.y} r={20} fill={color} opacity={0.9} />
              <text
                x={pos.x}
                y={pos.y + 4}
                textAnchor="middle"
                fontSize={8}
                fill="white"
                fontWeight="bold"
              >
                {node.label.slice(0, 12)}
              </text>
              <text
                x={pos.x}
                y={pos.y + 34}
                textAnchor="middle"
                fontSize={7}
                fill="#64748b"
              >
                {node.type}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}
