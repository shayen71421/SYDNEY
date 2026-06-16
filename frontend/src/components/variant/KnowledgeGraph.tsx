"use client";

import { useCallback, useRef, useEffect, useState, useMemo } from "react";
import type { GraphData } from "@/types";

interface Props {
  data: GraphData | null;
}

const COLORS: Record<string, string> = {
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

const W = 1600;
const H = 1100;

interface LayoutResult {
  nodes: GraphData["nodes"];
  edges: GraphData["edges"];
  positions: Record<string, { x: number; y: number }>;
  maxLabelLen: number;
}

function resolveOverlaps(
  nodes: GraphData["nodes"],
  positions: Record<string, { x: number; y: number }>,
  cx: number,
  cy: number
) {
  const ITERS = 15;
  const paperIds = new Set(
    nodes.filter((n) => n.type === "paper").map((n) => n.id)
  );

  for (let iter = 0; iter < ITERS; iter++) {
    let moved = false;
    for (let i = 0; i < nodes.length; i++) {
      for (let j = i + 1; j < nodes.length; j++) {
        const a = positions[nodes[i].id];
        const b = positions[nodes[j].id];
        if (!a || !b) continue;

        const isPaperI = paperIds.has(nodes[i].id);
        const isPaperJ = paperIds.has(nodes[j].id);
        const rI = isPaperI ? 26 : 38;
        const rJ = isPaperJ ? 26 : 38;

        const minGap = 12;
        const minDist = rI + rJ + minGap;

        const dx = a.x - b.x;
        const dy = a.y - b.y;
        const dist = Math.sqrt(dx * dx + dy * dy);
        if (dist < minDist && dist > 0.01) {
          const overlap = minDist - dist;
          const nx = dx / dist;
          const ny = dy / dist;
          const push = overlap * 0.5;
          a.x += nx * push;
          a.y += ny * push;
          b.x -= nx * push;
          b.y -= ny * push;
          moved = true;
        }
      }
    }
    if (!moved) break;
  }

  for (const id of paperIds) {
    const p = positions[id];
    if (!p) continue;
    const angle = Math.atan2(p.y - cy, p.x - cx);
    const minRadius = 150;
    const r = Math.sqrt((p.x - cx) ** 2 + (p.y - cy) ** 2);
    if (r < minRadius) {
      p.x = cx + minRadius * Math.cos(angle);
      p.y = cy + minRadius * Math.sin(angle);
    }
  }
}

function computeLayout(data: GraphData): LayoutResult {
  const nodes = data.nodes;
  const edges = data.edges;
  const cx = W / 2;
  const cy = H / 2;
  const positions: Record<string, { x: number; y: number }> = {};

  const variantNode = nodes.find((n) => n.type === "variant");
  if (variantNode) positions[variantNode.id] = { x: cx, y: cy };

  const geneNode = nodes.find((n) => n.type === "gene");
  if (geneNode) positions[geneNode.id] = { x: cx, y: cy - 190 };

  const diseaseNodes = nodes.filter((n) => n.type === "disease");
  diseaseNodes.forEach((node, i) => {
    const angle = (2 * Math.PI * i) / Math.max(1, diseaseNodes.length) - Math.PI / 2;
    positions[node.id] = {
      x: cx + 250 * Math.cos(angle),
      y: cy + 180 * Math.sin(angle),
    };
  });

  const paperNodes = nodes.filter((n) => n.type === "paper");
  const total = paperNodes.length;
  if (total > 0) {
    const rings =
      total <= 6 ? [260] : total <= 12 ? [250, 370] : [240, 350, 460];
    const perRing = rings.map((_, ri) => {
      const count = Math.ceil(total / rings.length);
      const start = ri * count;
      const end = Math.min(start + count, total);
      return { radius: rings[ri], count: end - start, start };
    });

    perRing.forEach(({ radius, count, start }) => {
      for (let i = 0; i < count; i++) {
        const node = paperNodes[start + i];
        const angle = (2 * Math.PI * i) / count - Math.PI / 2;
        positions[node.id] = {
          x: cx + radius * Math.cos(angle),
          y: cy + radius * 0.7 * Math.sin(angle),
        };
      }
    });
  }

  resolveOverlaps(nodes, positions, cx, cy);

  let maxLabelLen = 0;
  for (const node of nodes) {
    if (node.label.length > maxLabelLen) maxLabelLen = node.label.length;
  }

  const otherNodes = nodes.filter(
    (n) =>
      n.type !== "variant" &&
      n.type !== "gene" &&
      n.type !== "disease" &&
      n.type !== "paper"
  );
  otherNodes.forEach((node, i) => {
    const angle = (2 * Math.PI * i) / Math.max(1, otherNodes.length);
    positions[node.id] = {
      x: cx + 520 * Math.cos(angle),
      y: cy + 400 * Math.sin(angle),
    };
  });

  return { nodes, edges, positions, maxLabelLen };
}

function edgePath(
  sx: number,
  sy: number,
  tx: number,
  ty: number,
  cx: number,
  cy: number
) {
  const mx = (sx + tx) / 2;
  const my = (sy + ty) / 2;
  const dx = mx - cx;
  const dy = my - cy;
  const d = Math.sqrt(dx * dx + dy * dy) || 1;
  const offset = 60;
  const cpx = mx + (dx / d) * offset;
  const cpy = my + (dy / d) * offset;
  return `M ${sx} ${sy} Q ${cpx} ${cpy} ${tx} ${ty}`;
}

export function KnowledgeGraph({ data }: Props) {
  const svgRef = useRef<SVGSVGElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [hoveredId, setHoveredId] = useState<string | null>(null);

  const [view, setView] = useState({ x: 0, y: 0, zoom: 1 });
  const panning = useRef({
    active: false,
    startX: 0,
    startY: 0,
    viewX: 0,
    viewY: 0,
  });

  const result = useMemo(() => (data ? computeLayout(data) : null), [data]);

  const handleMouseDown = useCallback(
    (e: React.MouseEvent) => {
      if (e.button !== 0) return;
      panning.current.active = true;
      panning.current.startX = e.clientX;
      panning.current.startY = e.clientY;
      panning.current.viewX = view.x;
      panning.current.viewY = view.y;
    },
    [view.x, view.y]
  );

  const handleMouseMove = useCallback((e: React.MouseEvent) => {
    if (!panning.current.active) return;
    const dx = e.clientX - panning.current.startX;
    const dy = e.clientY - panning.current.startY;
    setView((v) => ({
      ...v,
      x: panning.current.viewX + dx / v.zoom,
      y: panning.current.viewY + dy / v.zoom,
    }));
  }, []);

  const handleMouseUp = useCallback(() => {
    panning.current.active = false;
  }, []);

  const handleWheel = useCallback((e: React.WheelEvent) => {
    e.preventDefault();
    const factor = e.deltaY > 0 ? 0.9 : 1.1;
    setView((v) => {
      const newZoom = Math.min(5, Math.max(0.15, v.zoom * factor));
      const svg = svgRef.current;
      if (!svg) return v;
      const rect = svg.getBoundingClientRect();
      const mx = (e.clientX - rect.left) / rect.width;
      const my = (e.clientY - rect.top) / rect.height;
      return {
        zoom: newZoom,
        x: v.x + (W * mx) / v.zoom - (W * mx) / newZoom,
        y: v.y + (H * my) / v.zoom - (H * my) / newZoom,
      };
    });
  }, []);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const prevent = (e: WheelEvent) => e.preventDefault();
    el.addEventListener("wheel", prevent, { passive: false });
    return () => el.removeEventListener("wheel", prevent);
  }, []);

  if (!data || data.nodes.length === 0 || !result) {
    return (
      <p className="py-8 text-center text-sm text-slate-500">
        Knowledge graph data will appear here after evidence retrieval.
      </p>
    );
  }

  const connectedIds = useMemo(() => {
    if (!hoveredId) return new Set<string>();
    const ids = new Set<string>([hoveredId]);
    result.edges.forEach((e) => {
      if (e.source === hoveredId) ids.add(e.target);
      if (e.target === hoveredId) ids.add(e.source);
    });
    return ids;
  }, [hoveredId, result]);

  const isDimmed = (id: string) => hoveredId !== null && !connectedIds.has(id);

  const sx = W / 2;
  const sy = H / 2;

  const nodeR = (type: string) => (type === "paper" ? 26 : 38);
  const textBaseSize = 14;
  const subTextSize = 11;
  const edgeLabelSize = 13;

  return (
    <div
      ref={containerRef}
      className="relative overflow-hidden rounded-lg border border-slate-200 dark:border-slate-700"
      style={{ cursor: panning.current.active ? "grabbing" : "grab" }}
    >
      <svg
        ref={svgRef}
        viewBox={`0 0 ${W} ${H}`}
        className="h-[550px] w-full bg-slate-50 dark:bg-slate-800/50 select-none"
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
        onWheel={handleWheel}
      >
        <defs>
          <marker
            id="arrow"
            markerWidth="10"
            markerHeight="8"
            refX="10"
            refY="4"
            orient="auto"
          >
            <polygon points="0 0, 10 4, 0 8" fill="#94a3b8" />
          </marker>
          <filter id="shadow">
            <feDropShadow dx="0" dy="2" stdDeviation="3" floodOpacity="0.18" />
          </filter>
        </defs>

        <g transform={`translate(${view.x},${view.y}) scale(${view.zoom})`}>
          {result.edges.map((edge, i) => {
            const s = result.positions[edge.source];
            const t = result.positions[edge.target];
            if (!s || !t) return null;

            const mx = (s.x + t.x) / 2;
            const my = (s.y + t.y) / 2;
            const lw = Math.min(edge.label.length * 8, 200);

            const dimmed =
              hoveredId !== null &&
              !connectedIds.has(edge.source) &&
              !connectedIds.has(edge.target);

            return (
              <g key={`e-${i}`} opacity={dimmed ? 0.08 : 0.6}>
                <path
                  d={edgePath(s.x, s.y, t.x, t.y, sx, sy)}
                  fill="none"
                  stroke="#94a3b8"
                  strokeWidth={dimmed ? 0.5 : 2}
                  strokeDasharray="5 3"
                  markerEnd="url(#arrow)"
                />
                <rect
                  x={mx - lw / 2 - 5}
                  y={my - 11}
                  width={lw + 10}
                  height={20}
                  fill="white"
                  rx={4}
                  className="dark:fill-slate-700"
                  opacity={0.92}
                />
                <text
                  x={mx}
                  y={my + 4}
                  textAnchor="middle"
                  fontSize={edgeLabelSize}
                  fill="#64748b"
                  className="dark:fill-slate-300"
                  pointerEvents="none"
                >
                  {edge.label}
                </text>
              </g>
            );
          })}

          {result.nodes.map((node) => {
            const pos = result.positions[node.id];
            if (!pos) return null;
            const color = COLORS[node.type] || "#64748b";
            const r = nodeR(node.type);
            const dimmed = isDimmed(node.id);

            return (
              <g
                key={node.id}
                opacity={dimmed ? 0.1 : 1}
                style={{ transition: "opacity 0.15s" }}
                onMouseEnter={() => setHoveredId(node.id)}
                onMouseLeave={() => setHoveredId(null)}
                className="cursor-pointer"
              >
                {node.type === "paper" ? (
                  <>
                    <rect
                      x={pos.x - r - 4}
                      y={pos.y - r}
                      width={r * 2 + 8}
                      height={r * 2}
                      rx={8}
                      fill={color}
                      opacity={0.92}
                      filter="url(#shadow)"
                    />
                    <text
                      x={pos.x}
                      y={pos.y + 5}
                      textAnchor="middle"
                      fontSize={textBaseSize - 1}
                      fill="white"
                      fontWeight="bold"
                      pointerEvents="none"
                    >
                      {node.label.length > 10
                        ? node.label.slice(0, 10) + "\u2026"
                        : node.label}
                    </text>
                    <text
                      x={pos.x}
                      y={pos.y + r + 16}
                      textAnchor="middle"
                      fontSize={subTextSize}
                      fill="#64748b"
                      className="dark:fill-slate-400"
                      pointerEvents="none"
                    >
                      {TYPE_LABELS[node.type]}
                    </text>
                  </>
                ) : (
                  <>
                    <circle
                      cx={pos.x}
                      cy={pos.y}
                      r={hoveredId === node.id ? r + 6 : r}
                      fill={color}
                      opacity={0.92}
                      filter="url(#shadow)"
                      style={{ transition: "r 0.15s" }}
                    />
                    <text
                      x={pos.x}
                      y={pos.y + 6}
                      textAnchor="middle"
                      fontSize={textBaseSize}
                      fill="white"
                      fontWeight="bold"
                      pointerEvents="none"
                    >
                      {node.label.slice(0, 16)}
                    </text>
                    <text
                      x={pos.x}
                      y={pos.y + r + 18}
                      textAnchor="middle"
                      fontSize={subTextSize}
                      fill="#64748b"
                      className="dark:fill-slate-400"
                      pointerEvents="none"
                    >
                      {TYPE_LABELS[node.type]}
                    </text>
                  </>
                )}
              </g>
            );
          })}
        </g>
      </svg>

      <div className="pointer-events-none absolute right-3 top-3 space-y-2">
        {Object.entries(COLORS).map(([type, color]) => (
          <div key={type} className="flex items-center gap-2">
            <div
              className="h-3 w-3 rounded-full"
              style={{ backgroundColor: color }}
            />
            <span className="text-xs text-slate-500 dark:text-slate-400">
              {TYPE_LABELS[type] || type}
            </span>
          </div>
        ))}
      </div>

      <div className="pointer-events-none absolute bottom-3 left-3 text-xs text-slate-400 dark:text-slate-500">
        Scroll to zoom &middot; Drag to pan
      </div>
    </div>
  );
}
