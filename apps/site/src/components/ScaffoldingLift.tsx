import type { Board } from "@/lib/board";
import { scaffoldingLift } from "@/lib/board";
import { formatScore } from "@/lib/format";

/**
 * Scaffolding-lift ablation: one line per model, quality climbing as harness
 * depth increases (L0 → L8). Only models that actually have ≥2 harness levels
 * draw a line (those are the ones that "lift"); models with a single bare (L0)
 * point are shown as faint baseline dots for context. A small palette keeps the
 * lifting lines distinguishable + the legend compact even with many models.
 */
const PALETTE = [
  "#34d399",
  "#8b83e6",
  "#f472b6",
  "#38bdf8",
  "#fbbf24",
  "#fb7185",
  "#a3e635",
  "#22d3ee",
];

export function ScaffoldingLift({ board }: { board: Board }) {
  const series = scaffoldingLift(board).filter((s) =>
    s.points.some((p) => p.cell.mean_score !== null)
  );
  if (series.length === 0) return null;

  const scoredPts = (s: (typeof series)[number]) =>
    s.points.filter((p) => p.cell.mean_score !== null);
  const lifting = series.filter((s) => scoredPts(s).length >= 2);
  const baselineOnly = series.filter((s) => scoredPts(s).length === 1);

  const harnessOrder = [...board.harnesses].sort((a, b) => a.level - b.level);
  const W = 760;
  const H = 360;
  const pad = { t: 18, r: lifting.length ? 168 : 28, b: 56, l: 48 };
  const plotW = W - pad.l - pad.r;
  const plotH = H - pad.t - pad.b;
  const yMin = 0;
  const yMax = 10;

  const xAt = (i: number) =>
    pad.l +
    (harnessOrder.length === 1
      ? plotW / 2
      : (i / (harnessOrder.length - 1)) * plotW);
  const sy = (y: number) =>
    pad.t + plotH - ((y - yMin) / (yMax - yMin)) * plotH;
  const idxOf = (stackId: string) =>
    harnessOrder.findIndex((h) => h.stack_id === stackId);
  const colorOf = (i: number) => PALETTE[i % PALETTE.length];

  return (
    <div className="chart-card">
      <div className="chart-head">
        <span className="title">Scaffolding lift</span>
        <span className="hint">what each layer of harness buys a model</span>
      </div>
      <svg
        viewBox={`0 0 ${W} ${H}`}
        width="100%"
        role="img"
        aria-label="Quality lift per model as harness scaffolding deepens"
        style={{ display: "block" }}
      >
        {[0, 2, 4, 6, 8, 10].map((t) => (
          <g key={t}>
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
              {t}
            </text>
          </g>
        ))}
        {harnessOrder.map((h, i) => (
          <text
            key={h.stack_id}
            x={xAt(i)}
            y={pad.t + plotH + 20}
            textAnchor="middle"
            fontSize={11}
            fill="#a8a8b3"
          >
            <tspan
              x={xAt(i)}
              dy={0}
              fontFamily="var(--font-mono)"
              fill="#6e6e7a"
            >
              L{h.level}
            </tspan>
            <tspan x={xAt(i)} dy={15}>
              {h.name.length > 12 ? h.name.slice(0, 11) + "…" : h.name}
            </tspan>
          </text>
        ))}

        {/* baseline-only models: faint context dots at their single level */}
        {baselineOnly.map((s) => {
          const p = scoredPts(s)[0];
          if (!p) return null;
          return (
            <circle
              key={s.model.model_id}
              cx={xAt(idxOf(p.harness.stack_id))}
              cy={sy(p.cell.mean_score ?? 0)}
              r={3}
              fill="#3a3a44"
            >
              <title>{`${s.model.name}: ${formatScore(
                p.cell.mean_score
              )} (bare only)`}</title>
            </circle>
          );
        })}

        {/* lifting models: a line each */}
        {lifting.map((s, li) => {
          const pts = scoredPts(s).map((p) => ({
            x: xAt(idxOf(p.harness.stack_id)),
            y: sy(p.cell.mean_score ?? 0),
            s: p.cell.mean_score,
          }));
          const color = colorOf(li);
          const d = pts
            .map(
              (p, i) =>
                `${i === 0 ? "M" : "L"}${p.x.toFixed(1)} ${p.y.toFixed(1)}`
            )
            .join(" ");
          return (
            <g key={s.model.model_id}>
              <path
                d={d}
                fill="none"
                stroke={color}
                strokeWidth={2.2}
                strokeOpacity={0.95}
              />
              {pts.map((p, i) => (
                <circle key={i} cx={p.x} cy={p.y} r={4} fill={color}>
                  <title>{`${s.model.name}: ${formatScore(p.s)}`}</title>
                </circle>
              ))}
            </g>
          );
        })}

        <text
          x={pad.l + plotW / 2}
          y={H - 6}
          textAnchor="middle"
          fontSize={12}
          fill="#a8a8b3"
        >
          Harness depth (scaffolding layers) →
        </text>

        {/* legend: only the lifting models (compact) */}
        {lifting.map((s, li) => (
          <g
            key={s.model.model_id}
            transform={`translate(${pad.l + plotW + 18}, ${
              pad.t + 6 + li * 22
            })`}
          >
            <line
              x1={0}
              x2={14}
              y1={-4}
              y2={-4}
              stroke={colorOf(li)}
              strokeWidth={2.5}
            />
            <text x={20} y={0} fontSize={11.5} fill="#a8a8b3">
              {s.model.name}
            </text>
          </g>
        ))}
        {baselineOnly.length > 0 && (
          <g
            transform={`translate(${pad.l + plotW + 18}, ${
              pad.t + 6 + lifting.length * 22 + 6
            })`}
          >
            <circle cx={7} cy={-4} r={3} fill="#3a3a44" />
            <text x={20} y={0} fontSize={11} fill="#6e6e7a">
              {baselineOnly.length} bare-only
            </text>
          </g>
        )}
      </svg>
    </div>
  );
}
