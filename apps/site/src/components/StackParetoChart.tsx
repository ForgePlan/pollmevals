"use client";

import { useState } from "react";
import type { Board, Cell } from "@/lib/board";
import { cellMap, frontierKeys } from "@/lib/board";
import { formatUsd, formatScore } from "@/lib/format";

/**
 * Cost vs quality scatter — one point per STACK (model × harness). The thesis
 * made visual: scaffolded cheap models sit up-and-left of bare expensive ones.
 *
 * With many models a per-model legend doesn't fit, so points are colored by the
 * model's PRICE TIER (cheap / mid / frontier) — few colors, clean legend — and
 * hovering a point reveals the exact stack + its full metrics in an in-SVG card.
 */
const TIER_COLOR = {
  cheap: "#34d399",
  mid: "#8b83e6",
  frontier: "#f472b6",
} as const;

export function StackParetoChart({ board }: { board: Board }) {
  const [hover, setHover] = useState<string | null>(null);
  const W = 760;
  const H = 380;
  const pad = { t: 20, r: 28, b: 48, l: 52 };
  const plotW = W - pad.l - pad.r;
  const plotH = H - pad.t - pad.b;

  const scored = board.cells.filter((c) => c.mean_score !== null);
  if (scored.length === 0) return null;
  const frontier = frontierKeys(board);
  const map = cellMap(board);
  const tierOf = new Map(board.models.map((m) => [m.model_id, m.tier]));
  const nameOf = new Map(board.models.map((m) => [m.model_id, m.name]));
  const hOf = new Map(board.harnesses.map((h) => [h.stack_id, h.name]));

  const costs = scored.map((c) => c.mean_cost_usd);
  const xMax = Math.max(...costs) * 1.12 || 1;
  const yMin = Math.max(
    0,
    Math.min(...scored.map((c) => c.mean_score ?? 0)) - 1
  );
  const yMax = 10;

  const sx = (x: number) => pad.l + (x / xMax) * plotW;
  const sy = (y: number) =>
    pad.t + plotH - ((y - yMin) / (yMax - yMin)) * plotH;

  const xTicks = ticks(0, xMax, 4);
  const yTicks = ticks(yMin, yMax, 4);
  const frontierPts = scored
    .filter((c) => frontier.has(`${c.model_id}::${c.stack_id}`))
    .sort((a, b) => a.mean_cost_usd - b.mean_cost_usd);

  const color = (c: Cell) => TIER_COLOR[tierOf.get(c.model_id) ?? "mid"];
  const hovered = hover ? map.get(hover) : undefined;

  return (
    <div className="chart-card">
      <div className="chart-head">
        <span className="title">Cost vs quality — every stack</span>
        <span className="hint">
          upper-left wins: cheaper + better · hover a point
        </span>
      </div>
      <svg
        viewBox={`0 0 ${W} ${H}`}
        width="100%"
        role="img"
        aria-label="Cost versus quality scatter for every model and harness stack"
        style={{ display: "block" }}
      >
        {yTicks.map((t) => (
          <g key={`y${t}`}>
            <line
              x1={pad.l}
              x2={pad.l + plotW}
              y1={sy(t)}
              y2={sy(t)}
              stroke="#26262e"
            />
            <text
              x={pad.l - 9}
              y={sy(t) + 4}
              textAnchor="end"
              fontSize={11}
              fill="#6e6e7a"
              fontFamily="var(--font-mono)"
            >
              {t.toFixed(0)}
            </text>
          </g>
        ))}
        {xTicks.map((t) => (
          <g key={`x${t}`}>
            <line
              x1={sx(t)}
              x2={sx(t)}
              y1={pad.t}
              y2={pad.t + plotH}
              stroke="#1c1c24"
            />
            <text
              x={sx(t)}
              y={pad.t + plotH + 18}
              textAnchor="middle"
              fontSize={11}
              fill="#6e6e7a"
              fontFamily="var(--font-mono)"
            >
              {formatUsd(t)}
            </text>
          </g>
        ))}

        {frontierPts.length >= 2 && (
          <path
            d={frontierPts
              .map(
                (c, i) =>
                  `${i === 0 ? "M" : "L"}${sx(c.mean_cost_usd).toFixed(1)} ${sy(
                    c.mean_score ?? 0
                  ).toFixed(1)}`
              )
              .join(" ")}
            fill="none"
            stroke="#10b981"
            strokeWidth={1.5}
            strokeOpacity={0.4}
            strokeDasharray="4 4"
          />
        )}

        {scored.map((c) => {
          const k = `${c.model_id}::${c.stack_id}`;
          const onF = frontier.has(k);
          const isH = hover === k;
          return (
            <circle
              key={k}
              cx={sx(c.mean_cost_usd)}
              cy={sy(c.mean_score ?? 0)}
              r={isH ? 8 : onF ? 6.5 : 4.5}
              fill={color(c)}
              fillOpacity={hover && !isH ? 0.35 : onF ? 1 : 0.78}
              stroke={isH ? "#fff" : onF ? "#0b0b0d" : "none"}
              strokeWidth={1.5}
              style={{ cursor: "pointer" }}
              onMouseEnter={() => setHover(k)}
              onMouseLeave={() => setHover((h) => (h === k ? null : h))}
            />
          );
        })}

        <text
          x={pad.l + plotW / 2}
          y={H - 6}
          textAnchor="middle"
          fontSize={12}
          fill="#a8a8b3"
        >
          Cost per task (USD) — lower is better
        </text>
        <text
          x={15}
          y={pad.t + plotH / 2}
          textAnchor="middle"
          fontSize={12}
          fill="#a8a8b3"
          transform={`rotate(-90 15 ${pad.t + plotH / 2})`}
        >
          Quality (0–10)
        </text>

        {/* tier legend (compact, few colors) */}
        {(["cheap", "mid", "frontier"] as const).map((tier, i) => (
          <g
            key={tier}
            transform={`translate(${pad.l + 8 + i * 92}, ${pad.t + 6})`}
          >
            <circle cx={5} cy={-4} r={5} fill={TIER_COLOR[tier]} />
            <text x={15} y={0} fontSize={11} fill="#a8a8b3">
              {tier.charAt(0).toUpperCase() + tier.slice(1)}
            </text>
          </g>
        ))}

        {hovered && (
          <Tooltip
            cell={hovered}
            sx={sx}
            sy={sy}
            W={W}
            nameOf={nameOf}
            hOf={hOf}
          />
        )}
      </svg>
    </div>
  );
}

function Tooltip({
  cell,
  sx,
  sy,
  W,
  nameOf,
  hOf,
}: {
  cell: Cell;
  sx: (x: number) => number;
  sy: (y: number) => number;
  W: number;
  nameOf: Map<string, string>;
  hOf: Map<string, string>;
}) {
  const px = sx(cell.mean_cost_usd);
  const py = sy(cell.mean_score ?? 0);
  const bw = 188;
  const bh = 86;
  // flip left if near the right edge
  const left = px + bw + 14 > W ? px - bw - 12 : px + 12;
  const top = Math.max(6, py - bh - 8);
  const lines = [
    `quality ${formatScore(cell.mean_score)} · pass^k ${
      cell.pass_hat_k === null ? "—" : Math.round(cell.pass_hat_k * 100) + "%"
    }`,
    `${formatUsd(cell.mean_cost_usd)}/task · ${
      cell.mean_latency_ms
        ? (cell.mean_latency_ms / 1000).toFixed(1) + "s"
        : "—"
    }`,
    `q/$ ${
      cell.quality_per_dollar === null
        ? "—"
        : Math.round(cell.quality_per_dollar)
    }`,
  ];
  return (
    <g pointerEvents="none">
      <rect
        x={left}
        y={top}
        width={bw}
        height={bh}
        rx={8}
        fill="#16161c"
        stroke="#34343f"
      />
      <text
        x={left + 12}
        y={top + 20}
        fontSize={12.5}
        fontWeight={700}
        fill="#f4f4f6"
      >
        {nameOf.get(cell.model_id) ?? cell.model_id}
      </text>
      <text x={left + 12} y={top + 36} fontSize={11} fill="#8b83e6">
        {hOf.get(cell.stack_id) ?? cell.stack_id}
      </text>
      {lines.map((l, i) => (
        <text
          key={i}
          x={left + 12}
          y={top + 52 + i * 14}
          fontSize={11}
          fill="#a8a8b3"
          fontFamily="var(--font-mono)"
        >
          {l}
        </text>
      ))}
    </g>
  );
}

function ticks(min: number, max: number, n: number): number[] {
  if (max <= min) return [min];
  const step = (max - min) / n;
  return Array.from({ length: n + 1 }, (_, i) => min + step * i);
}
