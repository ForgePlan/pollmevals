import type { Board } from "@/lib/board";
import { scaffoldingLift } from "@/lib/board";

/**
 * Scaffolding-lift ablation: one line per model, quality climbing as harness
 * depth increases (L0 → L8). The thesis per model — weak models climb steepest,
 * and a cheap model's line can cross above an expensive model's bare baseline.
 */
const MODEL_COLORS: Record<string, string> = {
  "qwen-3-14b": "#f59e0b",
  "llama-3-3-70b": "#f472b6",
  "gemini-3-flash": "#38bdf8",
  "gpt-5-mini": "#34d399",
  "claude-sonnet-4-6": "#8b83e6",
};

export function ScaffoldingLift({ board }: { board: Board }) {
  const series = scaffoldingLift(board).filter((s) =>
    s.points.some((p) => p.cell.mean_score !== null)
  );
  if (series.length === 0) return null;

  // x positions: ordered harness levels shared across models.
  const harnessOrder = [...board.harnesses].sort((a, b) => a.level - b.level);
  const W = 760;
  const H = 360;
  const pad = { t: 18, r: 150, b: 56, l: 48 };
  const plotW = W - pad.l - pad.r;
  const plotH = H - pad.t - pad.b;
  const yMin = 3;
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
        {[4, 6, 8, 10].map((t) => (
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

        {series.map((s) => {
          const pts = s.points
            .filter((p) => p.cell.mean_score !== null)
            .map((p) => ({
              x: xAt(idxOf(p.harness.stack_id)),
              y: sy(p.cell.mean_score ?? 0),
            }));
          const color = MODEL_COLORS[s.model.model_id] ?? "#a8a8b3";
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
                strokeWidth={2}
                strokeOpacity={0.9}
              />
              {pts.map((p, i) => (
                <circle key={i} cx={p.x} cy={p.y} r={3.5} fill={color} />
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

        {board.models.map((model, i) => (
          <g
            key={model.model_id}
            transform={`translate(${pad.l + plotW + 18}, ${
              pad.t + 6 + i * 22
            })`}
          >
            <line
              x1={0}
              x2={14}
              y1={-4}
              y2={-4}
              stroke={MODEL_COLORS[model.model_id] ?? "#a8a8b3"}
              strokeWidth={2.5}
            />
            <text x={20} y={0} fontSize={11.5} fill="#a8a8b3">
              {model.name}
            </text>
          </g>
        ))}
      </svg>
    </div>
  );
}
