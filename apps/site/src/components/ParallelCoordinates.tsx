"use client";

import { useState } from "react";
import type { Board, Cell } from "@/lib/board";
import { formatUsd, formatScore } from "@/lib/format";

/**
 * Parallel coordinates — each stack is a polyline across normalized axes
 * (quality, cost, latency, reliability, quality-per-$). Every axis is oriented
 * "up = better" (cost + latency are inverted), so a line that stays high is a
 * stack that's good on everything. The shape of the bundle IS the distribution:
 * where lines spread = where stacks differ; where they converge = consensus.
 */
const TIER_COLOR = {
  cheap: "#34d399",
  mid: "#8b83e6",
  frontier: "#f472b6",
} as const;

interface Axis {
  key: string;
  label: string;
  value: (c: Cell) => number | null;
  invert: boolean; // lower raw value = better → flip so "up = better"
}

const AXES: Axis[] = [
  { key: "q", label: "Quality", value: (c) => c.mean_score, invert: false },
  { key: "cost", label: "Cost", value: (c) => c.mean_cost_usd, invert: true },
  {
    key: "lat",
    label: "Latency",
    value: (c) => c.mean_latency_ms || null,
    invert: true,
  },
  { key: "passk", label: "pass^k", value: (c) => c.pass_hat_k, invert: false },
  {
    key: "qpd",
    label: "Quality/$",
    value: (c) => c.quality_per_dollar,
    invert: false,
  },
];

export function ParallelCoordinates({ board }: { board: Board }) {
  const [hover, setHover] = useState<string | null>(null);
  const W = 760;
  const H = 360;
  const pad = { t: 30, r: 28, b: 40, l: 28 };
  const plotW = W - pad.l - pad.r;
  const plotH = H - pad.t - pad.b;

  const scored = board.cells.filter((c) => c.mean_score !== null);
  if (scored.length === 0) return null;

  const nameOf = new Map(board.models.map((m) => [m.model_id, m]));
  const hOf = new Map(board.harnesses.map((h) => [h.stack_id, h.name]));

  // per-axis min/max across scored cells
  const ranges = AXES.map((ax) => {
    const vals = scored.map(ax.value).filter((v): v is number => v !== null);
    return { min: Math.min(...vals), max: Math.max(...vals) };
  });

  const axisX = (i: number) =>
    pad.l + (AXES.length === 1 ? 0 : (i / (AXES.length - 1)) * plotW);
  const norm = (v: number, i: number) => {
    const r = ranges[i] ?? { min: 0, max: 1 };
    const t = r.max === r.min ? 0.5 : (v - r.min) / (r.max - r.min);
    return AXES[i]?.invert ? 1 - t : t;
  };
  const axisY = (t: number) => pad.t + plotH - t * plotH;

  const pathFor = (c: Cell): string =>
    AXES.map((ax, i) => {
      const v = ax.value(c);
      const y = v === null ? pad.t + plotH : axisY(norm(v, i));
      return `${i === 0 ? "M" : "L"}${axisX(i).toFixed(1)} ${y.toFixed(1)}`;
    }).join(" ");

  const color = (c: Cell) => TIER_COLOR[nameOf.get(c.model_id)?.tier ?? "mid"];
  const hovered = hover
    ? scored.find((c) => `${c.model_id}::${c.stack_id}` === hover)
    : undefined;

  return (
    <div className="chart-card">
      <div className="chart-head">
        <span className="title">Every stack across all axes</span>
        <span className="hint">
          all axes oriented up = better · hover a line
        </span>
      </div>
      <svg
        viewBox={`0 0 ${W} ${H}`}
        width="100%"
        role="img"
        aria-label="Parallel coordinates of all stacks"
        style={{ display: "block" }}
      >
        {/* axes */}
        {AXES.map((ax, i) => (
          <g key={ax.key}>
            <line
              x1={axisX(i)}
              x2={axisX(i)}
              y1={pad.t}
              y2={pad.t + plotH}
              stroke="#34343f"
            />
            <text
              x={axisX(i)}
              y={pad.t - 12}
              textAnchor="middle"
              fontSize={11.5}
              fill="#a8a8b3"
              fontWeight={600}
            >
              {ax.label}
            </text>
            <text
              x={axisX(i)}
              y={pad.t + plotH + 16}
              textAnchor="middle"
              fontSize={9.5}
              fill="#6e6e7a"
              fontFamily="var(--font-mono)"
            >
              {fmtAxis(ax, ranges[i] ?? { min: 0, max: 1 })}
            </text>
          </g>
        ))}

        {/* lines */}
        {scored.map((c) => {
          const k = `${c.model_id}::${c.stack_id}`;
          const isH = hover === k;
          return (
            <path
              key={k}
              d={pathFor(c)}
              fill="none"
              stroke={color(c)}
              strokeWidth={isH ? 2.4 : 1.3}
              strokeOpacity={hover ? (isH ? 1 : 0.12) : 0.55}
              style={{ cursor: "pointer" }}
              onMouseEnter={() => setHover(k)}
              onMouseLeave={() => setHover((h) => (h === k ? null : h))}
            />
          );
        })}

        {hovered && (
          <g pointerEvents="none">
            <text
              x={pad.l}
              y={H - 8}
              fontSize={12}
              fill="#f4f4f6"
              fontWeight={700}
            >
              {nameOf.get(hovered.model_id)?.name ?? hovered.model_id}
              <tspan fill="#8b83e6" fontWeight={500}>
                {"  + " + (hOf.get(hovered.stack_id) ?? hovered.stack_id)}
              </tspan>
              <tspan fill="#a8a8b3" fontWeight={400} fontSize={11}>
                {`   ${formatScore(hovered.mean_score)} · ${formatUsd(
                  hovered.mean_cost_usd
                )}/task`}
              </tspan>
            </text>
          </g>
        )}
      </svg>
    </div>
  );
}

function fmtAxis(ax: Axis, r: { min: number; max: number }): string {
  const fmt = (v: number) =>
    ax.key === "cost"
      ? formatUsd(v)
      : ax.key === "lat"
      ? Math.round(v / 1000) + "s"
      : ax.key === "qpd"
      ? Math.round(v).toString()
      : v.toFixed(1);
  return `${fmt(r.min)}–${fmt(r.max)}`;
}
