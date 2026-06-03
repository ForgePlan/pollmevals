"use client";

import { useState } from "react";
import type { Board, Cell, Metric } from "@/lib/board";
import {
  cellMap,
  metricValue,
  metricRange,
  bestCell,
  frontierKeys,
} from "@/lib/board";
import { heat, heatText, norm } from "@/lib/color";
import { formatUsd, formatCost, formatScore } from "@/lib/format";

const METRICS: { id: Metric; label: string; caption: string }[] = [
  {
    id: "mean_score",
    label: "Quality",
    caption:
      "Mean judged score (0–10). Read a model row left-to-right to watch scaffolding lift it.",
  },
  {
    id: "mean_cost_usd",
    label: "Cost",
    caption:
      "Mean cost per task (incl. judges). Deeper scaffolding costs more — the trade-off the Pareto chart resolves.",
  },
  {
    id: "quality_per_dollar",
    label: "Quality / $",
    caption:
      "Quality ÷ cost. Rewards cheap stacks heavily — read it alongside the Pareto frontier, not alone.",
  },
];

const tierRank = { cheap: 0, mid: 1, frontier: 2 } as const;

export function HarnessModelMatrix({ board }: { board: Board }) {
  const [metric, setMetric] = useState<Metric>("mean_score");
  // Transposed: models are ROWS (many → vertical scroll), harnesses are COLUMNS
  // (few → always fit). Read a model's row left→right (bare → scaffolded) to see
  // the scaffolding lift. Models cheap→expensive top-down; harnesses L0→deepest.
  const models = [...board.models].sort(
    (a, b) => tierRank[a.tier] - tierRank[b.tier]
  );
  const harnesses = [...board.harnesses].sort((a, b) => a.level - b.level);
  const map = cellMap(board);
  const range = metricRange(board, metric);
  const invert = metric === "mean_cost_usd";
  const best = bestCell(board, metric);
  const bestKey = best ? `${best.model_id}::${best.stack_id}` : "";
  const frontier = frontierKeys(board);
  const active = METRICS.find((x) => x.id === metric)!;

  const fmt = (v: number | null) => {
    if (v === null) return "—";
    if (metric === "mean_cost_usd") return formatUsd(v);
    if (metric === "quality_per_dollar") return Math.round(v).toString();
    return formatScore(v);
  };

  return (
    <div className="matrix-card">
      <div className="matrix-toolbar">
        <div className="seg" role="tablist" aria-label="matrix metric">
          {METRICS.map((x) => (
            <button
              key={x.id}
              role="tab"
              aria-selected={metric === x.id}
              className={`seg-btn ${metric === x.id ? "on" : ""}`}
              onClick={() => setMetric(x.id)}
            >
              {x.label}
            </button>
          ))}
        </div>
        <p className="matrix-caption">{active.caption}</p>
      </div>

      <div className="matrix-scroll tall">
        <table
          className="matrix transposed"
          aria-label="model by harness performance matrix"
        >
          <thead>
            <tr>
              <th className="corner" scope="col">
                <span className="ax-y">model ↓ pricier</span>
                <span className="ax-x">harness → deeper</span>
              </th>
              {harnesses.map((h) => (
                <th key={h.stack_id} scope="col" className="harness-col">
                  <span className="hname">{h.name}</span>
                  <span className={`hlevel ${h.family}`}>L{h.level}</span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {models.map((model) => (
              <tr key={model.model_id}>
                <th scope="row" className="model-row">
                  <span className="mname">{model.name}</span>
                  <span className={`tier ${model.tier}`}>{model.tier}</span>
                </th>
                {harnesses.map((h) => {
                  const cell = map.get(`${model.model_id}::${h.stack_id}`);
                  const k = cell ? `${cell.model_id}::${cell.stack_id}` : "";
                  return (
                    <MatrixCell
                      key={h.stack_id}
                      cell={cell}
                      metric={metric}
                      range={range}
                      invert={invert}
                      isBest={k === bestKey}
                      onFrontier={cell ? frontier.has(k) : false}
                      label={cell ? fmt(metricValue(cell, metric)) : "·"}
                    />
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="matrix-legend">
        <span className="lg-scale" aria-hidden>
          <span className="lg-grad" />
          <span className="lg-ends">
            <span>{invert ? "cheap" : "low"}</span>
            <span>{invert ? "pricey" : "high"}</span>
          </span>
        </span>
        <span className="lg-mark">
          <span className="ring" /> best stack
        </span>
        <span className="lg-mark">
          <span className="pip" /> on Pareto frontier
        </span>
      </div>
    </div>
  );
}

function MatrixCell({
  cell,
  metric,
  range,
  invert,
  isBest,
  onFrontier,
  label,
}: {
  cell: Cell | undefined;
  metric: Metric;
  range: { min: number; max: number };
  invert: boolean;
  isBest: boolean;
  onFrontier: boolean;
  label: string;
}) {
  if (!cell) {
    return (
      <td className="mcell empty" aria-label="no data">
        ·
      </td>
    );
  }
  const v = metricValue(cell, metric);
  const t = v === null ? 0 : norm(v, range.min, range.max, invert);
  const bg = v === null ? "transparent" : heat(t);
  const fg = v === null ? "#6e6e7a" : heatText(t);
  const title =
    `${cell.model_id} × ${cell.stack_id}\n` +
    `score ${cell.mean_score ?? "—"} · ${formatCost(
      cell.mean_cost_usd
    )}/task · ` +
    `${
      cell.mean_latency_ms
        ? Math.round(cell.mean_latency_ms / 100) / 10 + "s"
        : "—"
    } · ` +
    `pass^k ${
      cell.pass_hat_k === null ? "—" : Math.round(cell.pass_hat_k * 100) + "%"
    }`;
  return (
    <td
      className={`mcell ${isBest ? "best" : ""} ${v === null ? "empty" : ""}`}
      style={{ background: bg, color: fg }}
      title={title}
    >
      <span className="mval">{label}</span>
      {onFrontier && <span className="pip" aria-hidden />}
    </td>
  );
}
