import type { Board, Cell } from "@/lib/board";
import { frontierKeys } from "@/lib/board";
import { formatUsd } from "@/lib/format";

/**
 * Cost vs quality scatter — one point per STACK (model × harness). The thesis
 * made visual: scaffolded cheap models sit up-and-left of bare expensive ones.
 * Color encodes the model; the marker glyph encodes the harness family; the
 * Pareto frontier is connected in emerald. Hand-built SVG (no chart lib).
 */
const MODEL_COLORS: Record<string, string> = {
  "qwen-3-14b": "#f59e0b",
  "llama-3-3-70b": "#f472b6",
  "gemini-3-flash": "#38bdf8",
  "gpt-5-mini": "#34d399",
  "claude-sonnet-4-6": "#8b83e6",
};
const FALLBACK = "#a8a8b3";

export function StackParetoChart({ board }: { board: Board }) {
  const W = 760;
  const H = 380;
  const pad = { t: 20, r: 140, b: 48, l: 52 };
  const plotW = W - pad.l - pad.r;
  const plotH = H - pad.t - pad.b;

  const scored = board.cells.filter((c) => c.mean_score !== null);
  if (scored.length === 0) return null;
  const frontier = frontierKeys(board);

  const costs = scored.map((c) => c.mean_cost_usd);
  const xMax = Math.max(...costs) * 1.12 || 1;
  const xMin = 0;
  const yMin = Math.max(
    0,
    Math.min(...scored.map((c) => c.mean_score ?? 0)) - 1
  );
  const yMax = 10;

  const sx = (x: number) => pad.l + ((x - xMin) / (xMax - xMin)) * plotW;
  const sy = (y: number) =>
    pad.t + plotH - ((y - yMin) / (yMax - yMin)) * plotH;

  const xTicks = ticks(xMin, xMax, 4);
  const yTicks = ticks(yMin, yMax, 4);

  const frontierPts = scored
    .filter((c) => frontier.has(`${c.model_id}::${c.stack_id}`))
    .sort((a, b) => a.mean_cost_usd - b.mean_cost_usd);

  const color = (c: Cell) => MODEL_COLORS[c.model_id] ?? FALLBACK;

  return (
    <div className="chart-card">
      <div className="chart-head">
        <span className="title">Cost vs quality — every stack</span>
        <span className="hint">upper-left wins: cheaper + better</span>
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

        {/* frontier line */}
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

        {/* points */}
        {scored.map((c, i) => {
          const onF = frontier.has(`${c.model_id}::${c.stack_id}`);
          return (
            <circle
              key={i}
              cx={sx(c.mean_cost_usd)}
              cy={sy(c.mean_score ?? 0)}
              r={onF ? 6.5 : 4.5}
              fill={color(c)}
              fillOpacity={onF ? 1 : 0.7}
              stroke={onF ? "#0b0b0d" : "none"}
              strokeWidth={1.5}
            >
              <title>{`${c.model_id} × ${c.stack_id}: ${
                c.mean_score
              } @ ${formatUsd(c.mean_cost_usd)}`}</title>
            </circle>
          );
        })}

        {/* axis labels */}
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

        {/* model legend */}
        {board.models.map((model, i) => (
          <g
            key={model.model_id}
            transform={`translate(${pad.l + plotW + 18}, ${
              pad.t + 6 + i * 22
            })`}
          >
            <circle
              cx={5}
              cy={-4}
              r={5}
              fill={MODEL_COLORS[model.model_id] ?? FALLBACK}
            />
            <text x={16} y={0} fontSize={11.5} fill="#a8a8b3">
              {model.name}
            </text>
          </g>
        ))}
      </svg>
    </div>
  );
}

function ticks(min: number, max: number, n: number): number[] {
  if (max <= min) return [min];
  const step = (max - min) / n;
  return Array.from({ length: n + 1 }, (_, i) => min + step * i);
}
