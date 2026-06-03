"use client";

import { useMemo, useState } from "react";
import type { Board, Cell } from "@/lib/board";
import { formatUsd, formatScore } from "@/lib/format";

/**
 * Ranked horizontal bars — the canonical leaderboard visual (Artificial Analysis,
 * llm-stats, Vellum all lead with this). One bar per stack, sorted best-first by
 * the chosen metric; bar length always reads "longer = better" (cost + speed are
 * inverted). The "All" tab packs four thin bars (quality / quality-per-$ / cost /
 * speed) into one row so every metric is visible at a glance.
 */
const TIER_COLOR = {
  cheap: "#34d399",
  mid: "#8b83e6",
  frontier: "#f472b6",
} as const;

type BaseMetric =
  | "mean_score"
  | "quality_per_dollar"
  | "mean_cost_usd"
  | "mean_latency_ms";
type MetricId = BaseMetric | "all";

interface MetricDef {
  id: BaseMetric;
  label: string;
  short: string;
  color: string;
  lowerBetter: boolean;
}
const BASE: MetricDef[] = [
  {
    id: "mean_score",
    label: "Quality",
    short: "Qual",
    color: "#34d399",
    lowerBetter: false,
  },
  {
    id: "quality_per_dollar",
    label: "Quality / $",
    short: "Q/$",
    color: "#8b83e6",
    lowerBetter: false,
  },
  {
    id: "mean_cost_usd",
    label: "Cost",
    short: "Cost",
    color: "#fbbf24",
    lowerBetter: true,
  },
  {
    id: "mean_latency_ms",
    label: "Speed",
    short: "Spd",
    color: "#38bdf8",
    lowerBetter: true,
  },
];

function rawVal(c: Cell, id: BaseMetric): number | null {
  if (id === "mean_cost_usd") return c.mean_cost_usd || null;
  if (id === "mean_latency_ms") return c.mean_latency_ms || null;
  return c[id];
}
function fmtVal(c: Cell, id: BaseMetric): string {
  const v = rawVal(c, id);
  if (v === null) return "—";
  if (id === "mean_cost_usd") return formatUsd(v);
  if (id === "mean_latency_ms") return `${(v / 1000).toFixed(1)}s`;
  if (id === "quality_per_dollar")
    return String(Math.round(v)).replace(/\B(?=(\d{3})+(?!\d))/g, " ");
  return formatScore(v);
}

export function RankedBars({ board }: { board: Board }) {
  const [metric, setMetric] = useState<MetricId>("mean_score");

  const nameOf = new Map(board.models.map((m) => [m.model_id, m]));
  const hOf = new Map(board.harnesses.map((h) => [h.stack_id, h.name]));

  // per-metric min/max across scored cells → "goodness" 0..1 (longer = better)
  const ranges = useMemo(() => {
    const r: Record<BaseMetric, { lo: number; hi: number }> = {} as never;
    for (const m of BASE) {
      const vals = board.cells
        .map((c) => rawVal(c, m.id))
        .filter((v): v is number => v !== null);
      r[m.id] = { lo: Math.min(...vals), hi: Math.max(...vals) };
    }
    return r;
  }, [board]);

  const good = (c: Cell, m: MetricDef): number | null => {
    const v = rawVal(c, m.id);
    if (v === null) return null;
    const { lo, hi } = ranges[m.id];
    const t = hi === lo ? 1 : (v - lo) / (hi - lo);
    return m.lowerBetter ? 1 - t : t;
  };

  const isAll = metric === "all";
  const sortMetric: MetricDef = (
    isAll ? BASE[0] : BASE.find((m) => m.id === metric)
  )!;
  const score = (c: Cell): number => {
    if (!isAll) return good(c, sortMetric) ?? -1;
    const gs = BASE.map((m) => good(c, m)).filter(
      (g): g is number => g !== null
    );
    return gs.length ? gs.reduce((a, b) => a + b, 0) / gs.length : -1;
  };

  const rows = board.cells
    .filter((c) => c.mean_score !== null)
    .map((c) => ({ c, s: score(c) }))
    .sort((a, b) => b.s - a.s);
  if (rows.length === 0) return null;

  const TABS: { id: MetricId; label: string }[] = [
    { id: "all", label: "All" },
    ...BASE.map((m) => ({ id: m.id as MetricId, label: m.label })),
  ];
  const activeLabel = isAll ? "all metrics" : sortMetric.label.toLowerCase();

  return (
    <div className="ranked-card">
      <div className="matrix-toolbar">
        <div className="seg" role="tablist" aria-label="ranking metric">
          {TABS.map((t) => (
            <button
              key={t.id}
              role="tab"
              aria-selected={metric === t.id}
              className={`seg-btn ${metric === t.id ? "on" : ""}`}
              onClick={() => setMetric(t.id)}
            >
              {t.label}
            </button>
          ))}
        </div>
        <p className="matrix-caption">
          {isAll ? (
            <>
              All four metrics per stack — sorted by overall (longer = better).{" "}
              {BASE.map((m) => (
                <span key={m.id} className="cap-key" style={{ color: m.color }}>
                  ▮ {m.short}{" "}
                </span>
              ))}
            </>
          ) : (
            <>
              Stacks ranked by {activeLabel} —{" "}
              {sortMetric.lowerBetter ? "lower" : "higher"} is better; longest
              bar wins.
            </>
          )}
        </p>
      </div>
      <ol className="ranked-list">
        {rows.map(({ c }, i) => {
          const tier = nameOf.get(c.model_id)?.tier ?? "mid";
          return (
            <li
              key={`${c.model_id}::${c.stack_id}`}
              className={`ranked-row ${isAll ? "all" : ""}`}
            >
              <span className="rk-pos">{i + 1}</span>
              <span className="rk-label">
                <span className="rk-model">
                  {nameOf.get(c.model_id)?.name ?? c.model_id}
                </span>
                <span className="rk-harness">
                  {hOf.get(c.stack_id) ?? c.stack_id}
                </span>
              </span>
              {isAll ? (
                <span className="all-bars">
                  {BASE.map((m) => {
                    const g = good(c, m);
                    return (
                      <span
                        className="all-bar"
                        key={m.id}
                        title={`${m.label}: ${fmtVal(c, m.id)}`}
                      >
                        <span className="ab-key" style={{ color: m.color }}>
                          {m.short}
                        </span>
                        <span className="ab-track">
                          <span
                            className="ab-fill"
                            style={{
                              width: `${Math.max(2, (g ?? 0) * 100)}%`,
                              background: m.color,
                            }}
                          />
                        </span>
                        <span className="ab-val">{fmtVal(c, m.id)}</span>
                      </span>
                    );
                  })}
                </span>
              ) : (
                <>
                  <span className="rk-track">
                    <span
                      className="rk-fill"
                      style={{
                        width: `${Math.max(
                          2,
                          (good(c, sortMetric) ?? 0) * 100
                        )}%`,
                        background: TIER_COLOR[tier],
                      }}
                    />
                  </span>
                  <span className="rk-val">{fmtVal(c, sortMetric.id)}</span>
                </>
              )}
            </li>
          );
        })}
      </ol>
    </div>
  );
}
