"use client";

import { useState } from "react";
import type { Board, Cell } from "@/lib/board";

/**
 * Radar (spider) — a stack's QUALITY PROFILE across the rubric criteria
 * (correctness, security, error-handling, type-safety, clarity, test-alignment).
 * Each axis is a criterion (0–10); each stack is a polygon. Overlay a few to see
 * where they're strong vs weak — "everyone has these axes, but at different
 * levels", which is exactly what a radar reads well.
 *
 * Needs per_criterion on the cells (board emitter); until a run populates it the
 * chart shows a short note instead.
 */
const TIER_COLOR = {
  cheap: "#34d399",
  mid: "#8b83e6",
  frontier: "#f472b6",
} as const;
// Preferred axis order (be_01 rubric); any extra criteria are appended.
const CRIT_ORDER = [
  "correctness",
  "security_posture",
  "error_handling",
  "type_safety",
  "code_clarity",
  "test_alignment",
];
const CRIT_LABEL: Record<string, string> = {
  correctness: "Correctness",
  security_posture: "Security",
  error_handling: "Error handling",
  type_safety: "Type safety",
  code_clarity: "Clarity",
  test_alignment: "Tests",
};

export function RadarChart({ board }: { board: Board }) {
  const withCrit = board.cells.filter(
    (c) =>
      c.per_criterion &&
      Object.keys(c.per_criterion).length >= 3 &&
      c.mean_score !== null
  );

  // axes = union of criteria across cells, in preferred order
  const present = new Set<string>();
  withCrit.forEach((c) =>
    Object.keys(c.per_criterion ?? {}).forEach((k) => present.add(k))
  );
  const axes = [
    ...CRIT_ORDER.filter((k) => present.has(k)),
    ...[...present].filter((k) => !CRIT_ORDER.includes(k)),
  ];

  // default selection: top 3 scored stacks that have a profile
  const ranked = [...withCrit].sort(
    (a, b) => (b.mean_score ?? 0) - (a.mean_score ?? 0)
  );
  const candidates = ranked.slice(0, 8);
  const [sel, setSel] = useState<Set<string>>(
    () => new Set(ranked.slice(0, 3).map((c) => `${c.model_id}::${c.stack_id}`))
  );

  const nameOf = new Map(board.models.map((m) => [m.model_id, m]));
  const hOf = new Map(board.harnesses.map((h) => [h.stack_id, h.name]));
  const label = (c: Cell) =>
    `${nameOf.get(c.model_id)?.name ?? c.model_id} + ${
      hOf.get(c.stack_id) ?? c.stack_id
    }`;
  const color = (c: Cell) => TIER_COLOR[nameOf.get(c.model_id)?.tier ?? "mid"];

  if (axes.length < 3 || candidates.length === 0) {
    return (
      <div className="chart-card">
        <div className="chart-head">
          <span className="title">Stack profile (radar)</span>
        </div>
        <p className="radar-empty">
          Per-criterion scores aren&apos;t in this board yet — the next scored
          run populates the rubric breakdown (correctness, security, clarity, …)
          and this radar fills in.
        </p>
      </div>
    );
  }

  const W = 460;
  const cx = W / 2;
  const cy = 210;
  const R = 150;
  const N = axes.length;
  const angle = (i: number) => -Math.PI / 2 + (i / N) * 2 * Math.PI;
  const pt = (i: number, v: number) => {
    const r = (Math.max(0, Math.min(10, v)) / 10) * R;
    return [cx + r * Math.cos(angle(i)), cy + r * Math.sin(angle(i))] as const;
  };
  const polyFor = (c: Cell) =>
    axes.map((ax, i) => pt(i, c.per_criterion?.[ax] ?? 0).join(",")).join(" ");

  const toggle = (k: string) =>
    setSel((s) => {
      const n = new Set(s);
      if (n.has(k)) n.delete(k);
      else n.add(k);
      return n;
    });

  return (
    <div className="chart-card">
      <div className="chart-head">
        <span className="title">Stack profile — quality by criterion</span>
        <span className="hint">
          each axis a rubric criterion (0–10) · toggle stacks below
        </span>
      </div>
      <svg
        viewBox={`0 0 ${W} 320`}
        width="100%"
        role="img"
        aria-label="Radar of stack rubric profiles"
        style={{ display: "block" }}
      >
        {/* grid rings */}
        {[2, 4, 6, 8, 10].map((lvl) => (
          <polygon
            key={lvl}
            points={axes.map((_, i) => pt(i, lvl).join(",")).join(" ")}
            fill="none"
            stroke="#26262e"
            strokeWidth={lvl === 10 ? 1.2 : 0.8}
          />
        ))}
        {/* spokes + axis labels */}
        {axes.map((ax, i) => {
          const [ex, ey] = pt(i, 10);
          const [lx, ly] = pt(i, 11.6);
          return (
            <g key={ax}>
              <line x1={cx} y1={cy} x2={ex} y2={ey} stroke="#26262e" />
              <text
                x={lx}
                y={ly}
                textAnchor="middle"
                dominantBaseline="middle"
                fontSize={10.5}
                fill="#a8a8b3"
              >
                {CRIT_LABEL[ax] ?? ax}
              </text>
            </g>
          );
        })}
        {/* selected polygons */}
        {candidates
          .filter((c) => sel.has(`${c.model_id}::${c.stack_id}`))
          .map((c) => (
            <polygon
              key={`${c.model_id}::${c.stack_id}`}
              points={polyFor(c)}
              fill={color(c)}
              fillOpacity={0.1}
              stroke={color(c)}
              strokeWidth={2}
            />
          ))}
      </svg>
      <div className="radar-legend">
        {candidates.map((c) => {
          const k = `${c.model_id}::${c.stack_id}`;
          const on = sel.has(k);
          return (
            <button
              key={k}
              className={`radar-chip ${on ? "on" : ""}`}
              onClick={() => toggle(k)}
              style={on ? { borderColor: color(c) } : undefined}
            >
              <span
                className="dot"
                style={{
                  background: on ? color(c) : "transparent",
                  borderColor: color(c),
                }}
              />
              {label(c)}
            </button>
          );
        })}
      </div>
    </div>
  );
}
