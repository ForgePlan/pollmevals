"use client";

import { useEffect } from "react";
import type { Board, Cell } from "@/lib/board";
import { formatCost, formatScore } from "@/lib/format";

/**
 * Right-side drawer: everything about one stack (model × harness) in one place —
 * all metrics + the full per-criterion rubric profile. Opened by clicking a row
 * in the ranked list (or any cell). Click the backdrop or press Esc to close.
 */
const TIER_COLOR = {
  cheap: "#34d399",
  mid: "#8b83e6",
  frontier: "#f472b6",
} as const;
const CRIT_LABEL: Record<string, string> = {
  correctness: "Correctness",
  security_posture: "Security",
  error_handling: "Error handling",
  type_safety: "Type safety",
  code_clarity: "Clarity",
  test_alignment: "Tests",
};
const CRIT_ORDER = Object.keys(CRIT_LABEL);

const grp = (n: number) =>
  String(Math.round(n)).replace(/\B(?=(\d{3})+(?!\d))/g, " ");

export function StackDrawer({
  cell,
  board,
  onClose,
}: {
  cell: Cell | null;
  board: Board;
  onClose: () => void;
}) {
  useEffect(() => {
    if (!cell) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [cell, onClose]);

  if (!cell) return null;
  const model = board.models.find((m) => m.model_id === cell.model_id);
  const harness = board.harnesses.find((h) => h.stack_id === cell.stack_id);
  const tier = model?.tier ?? "mid";
  const pc = cell.per_criterion ?? {};
  const crits = [
    ...CRIT_ORDER.filter((k) => k in pc),
    ...Object.keys(pc).filter((k) => !CRIT_ORDER.includes(k)),
  ];

  const metrics: { label: string; value: string }[] = [
    { label: "Quality", value: formatScore(cell.mean_score) },
    {
      label: "Quality / $",
      value:
        cell.quality_per_dollar === null ? "—" : grp(cell.quality_per_dollar),
    },
    { label: "Cost / task", value: formatCost(cell.mean_cost_usd) },
    {
      label: "Speed",
      value: cell.mean_latency_ms
        ? `${(cell.mean_latency_ms / 1000).toFixed(1)}s`
        : "—",
    },
    {
      label: "Reliability (pass^k)",
      value:
        cell.pass_hat_k === null
          ? "—"
          : `${Math.round(cell.pass_hat_k * 100)}%`,
    },
  ];

  return (
    <div
      className="drawer-root"
      role="dialog"
      aria-modal="true"
      aria-label="stack details"
    >
      <div className="drawer-backdrop" onClick={onClose} />
      <aside className="drawer-panel">
        <div className="drawer-head">
          <div className="drawer-title">
            <span className="dw-model">{model?.name ?? cell.model_id}</span>
            <span className={`tier ${tier}`}>{tier}</span>
          </div>
          <button className="drawer-close" onClick={onClose} aria-label="close">
            ✕
          </button>
        </div>
        <div className="drawer-harness">
          <span className="dw-plus">+</span> {harness?.name ?? cell.stack_id}
          {harness && <span className="dw-level">L{harness.level}</span>}
          {cell.on_frontier && (
            <span className="dw-frontier">on Pareto frontier</span>
          )}
        </div>

        <div className="drawer-metrics">
          {metrics.map((m) => (
            <div className="dw-metric" key={m.label}>
              <span className="dw-mlabel">{m.label}</span>
              <span className="dw-mval">{m.value}</span>
            </div>
          ))}
        </div>

        {crits.length > 0 ? (
          <div className="drawer-section">
            <h4>Rubric profile</h4>
            <div className="dw-crits">
              {crits.map((k) => {
                const v = pc[k] ?? 0;
                return (
                  <div className="dw-crit" key={k}>
                    <span className="dw-cname">{CRIT_LABEL[k] ?? k}</span>
                    <span className="dw-ctrack">
                      <span
                        className="dw-cfill"
                        style={{
                          width: `${(v / 10) * 100}%`,
                          background: TIER_COLOR[tier],
                        }}
                      />
                    </span>
                    <span className="dw-cval">{v.toFixed(1)}</span>
                  </div>
                );
              })}
            </div>
          </div>
        ) : (
          <p className="drawer-note">
            No per-criterion breakdown for this stack yet.
          </p>
        )}
      </aside>
    </div>
  );
}
