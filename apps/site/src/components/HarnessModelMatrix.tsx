"use client";

import { useState } from "react";
import type { Board, Cell, Metric } from "@/lib/board";
import {
  buildMatrix,
  metricValue,
  metricRange,
  bestCell,
  frontierKeys,
} from "@/lib/board";
import { heat, heatText, norm } from "@/lib/color";
import { formatUsd, formatScore } from "@/lib/format";

const METRICS: { id: Metric; label: string; caption: string }[] = [
  {
    id: "mean_score",
    label: "Quality",
    caption:
      "Mean judged score (0–10). Watch a model column climb as scaffolding deepens downward.",
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

export function HarnessModelMatrix({ board }: { board: Board }) {
  const [metric, setMetric] = useState<Metric>("mean_score");
  const m = buildMatrix(board);
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

      <div className="matrix-scroll">
        <table
          className="matrix"
          aria-label="harness by model performance matrix"
        >
          <thead>
            <tr>
              <th className="corner" scope="col">
                <span className="ax-y">harness ↓ deeper</span>
                <span className="ax-x">model → pricier</span>
              </th>
              {m.cols.map((model) => (
                <th key={model.model_id} scope="col" className="model-col">
                  <span className="mname">{model.name}</span>
                  <span className={`tier ${model.tier}`}>{model.tier}</span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {m.rows.map((h) => (
              <tr key={h.stack_id}>
                <th scope="row" className="harness-row">
                  <span className="hname">{h.name}</span>
                  <span className={`hlevel ${h.family}`}>L{h.level}</span>
                </th>
                {m.cols.map((model) => {
                  const cell = m.cellAt(h, model);
                  return (
                    <MatrixCell
                      key={model.model_id}
                      cell={cell}
                      metric={metric}
                      range={range}
                      invert={invert}
                      isBest={
                        cell
                          ? `${cell.model_id}::${cell.stack_id}` === bestKey
                          : false
                      }
                      onFrontier={
                        cell
                          ? frontier.has(`${cell.model_id}::${cell.stack_id}`)
                          : false
                      }
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
    `score ${cell.mean_score ?? "—"} · ${formatUsd(
      cell.mean_cost_usd
    )}/task · ` +
    `pass^k ${
      cell.pass_hat_k === null ? "—" : Math.round(cell.pass_hat_k * 100) + "%"
    }`;
  return (
    <td
      className={`mcell ${isBest ? "best" : ""}`}
      style={{ background: bg, color: fg }}
      title={title}
    >
      <span className="mval">{label}</span>
      {onFrontier && <span className="pip" aria-hidden />}
    </td>
  );
}
