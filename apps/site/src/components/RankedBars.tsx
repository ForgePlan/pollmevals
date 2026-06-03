"use client";

import { useState } from "react";
import type { Board, Cell } from "@/lib/board";
import { formatUsd, formatScore } from "@/lib/format";

/**
 * Ranked horizontal bars — the canonical leaderboard visual (Artificial Analysis,
 * llm-stats, Vellum all lead with this). One bar per stack, sorted best-first by
 * the chosen metric; bar length always reads "longer = better" (cost is inverted
 * so the cheapest bar is longest). Far more legible than a parallel-coordinate
 * tangle when there are many stacks.
 */
const TIER_COLOR = {
  cheap: "#34d399",
  mid: "#8b83e6",
  frontier: "#f472b6",
} as const;

type MetricId =
  | "mean_score"
  | "quality_per_dollar"
  | "mean_cost_usd"
  | "mean_latency_ms";
const METRICS: { id: MetricId; label: string; lowerBetter: boolean }[] = [
  { id: "mean_score", label: "Quality", lowerBetter: false },
  { id: "quality_per_dollar", label: "Quality / $", lowerBetter: false },
  { id: "mean_cost_usd", label: "Cost", lowerBetter: true },
  { id: "mean_latency_ms", label: "Speed", lowerBetter: true },
];

export function RankedBars({ board }: { board: Board }) {
  const [metric, setMetric] = useState<MetricId>("mean_score");
  const active = METRICS.find((m) => m.id === metric)!;

  const nameOf = new Map(board.models.map((m) => [m.model_id, m]));
  const hOf = new Map(board.harnesses.map((h) => [h.stack_id, h.name]));

  const val = (c: Cell): number | null => {
    if (metric === "mean_cost_usd") return c.mean_cost_usd || null;
    if (metric === "mean_latency_ms") return c.mean_latency_ms || null;
    return c[metric];
  };
  const fmt = (c: Cell): string => {
    const v = val(c);
    if (v === null) return "—";
    if (metric === "mean_cost_usd") return formatUsd(v);
    if (metric === "mean_latency_ms") return `${(v / 1000).toFixed(1)}s`;
    if (metric === "quality_per_dollar")
      return String(Math.round(v)).replace(/\B(?=(\d{3})+(?!\d))/g, " ");
    return formatScore(v);
  };

  const rows = board.cells
    .map((c) => ({ c, v: val(c) }))
    .filter((r): r is { c: Cell; v: number } => r.v !== null);
  const vals = rows.map((r) => r.v);
  const lo = Math.min(...vals);
  const hi = Math.max(...vals);
  // "goodness" 0..1 — longer bar = better, regardless of metric direction
  const good = (v: number) => {
    if (hi === lo) return 1;
    const t = (v - lo) / (hi - lo);
    return active.lowerBetter ? 1 - t : t;
  };
  const sorted = [...rows].sort((a, b) => good(b.v) - good(a.v));

  if (sorted.length === 0) return null;

  return (
    <div className="ranked-card">
      <div className="matrix-toolbar">
        <div className="seg" role="tablist" aria-label="ranking metric">
          {METRICS.map((m) => (
            <button
              key={m.id}
              role="tab"
              aria-selected={metric === m.id}
              className={`seg-btn ${metric === m.id ? "on" : ""}`}
              onClick={() => setMetric(m.id)}
            >
              {m.label}
            </button>
          ))}
        </div>
        <p className="matrix-caption">
          Stacks ranked by {active.label.toLowerCase()} —{" "}
          {active.lowerBetter ? "lower" : "higher"} is better; longest bar wins.
        </p>
      </div>
      <ol className="ranked-list">
        {sorted.map(({ c, v }, i) => {
          const tier = nameOf.get(c.model_id)?.tier ?? "mid";
          return (
            <li key={`${c.model_id}::${c.stack_id}`} className="ranked-row">
              <span className="rk-pos">{i + 1}</span>
              <span className="rk-label">
                <span className="rk-model">
                  {nameOf.get(c.model_id)?.name ?? c.model_id}
                </span>
                <span className="rk-harness">
                  {hOf.get(c.stack_id) ?? c.stack_id}
                </span>
              </span>
              <span className="rk-track">
                <span
                  className="rk-fill"
                  style={{
                    width: `${Math.max(2, good(v) * 100)}%`,
                    background: TIER_COLOR[tier],
                  }}
                />
              </span>
              <span className="rk-val">{fmt(c)}</span>
            </li>
          );
        })}
      </ol>
    </div>
  );
}
