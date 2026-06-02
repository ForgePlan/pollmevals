import type { Board, Cell } from "@/lib/board";
import { frontierKeys } from "@/lib/board";
import { formatUsd, formatScore, formatLatency } from "@/lib/format";

/**
 * Detailed stack table — one row per (model × harness), ranked by overall
 * quality. A per-task sparkline shows where each stack is strong or weak;
 * cost, reliability (pass^k) and quality-per-$ complete the picture.
 */
const harnessName = (board: Board, stackId: string) =>
  board.harnesses.find((h) => h.stack_id === stackId)?.name ?? stackId;
const modelName = (board: Board, modelId: string) =>
  board.models.find((m) => m.model_id === modelId)?.name ?? modelId;

export function StackTable({ board }: { board: Board }) {
  const frontier = frontierKeys(board);
  const rows = [...board.cells].sort(
    (a, b) => (b.mean_score ?? -1) - (a.mean_score ?? -1)
  );

  return (
    <div className="table-wrap">
      <table className="lb">
        <thead>
          <tr>
            <th className="left">#</th>
            <th className="left">Stack (model + harness)</th>
            <th>Quality</th>
            <th className="hide-sm">By task</th>
            <th className="hide-sm">Reliability</th>
            <th>Cost / task</th>
            <th className="hide-sm">Latency</th>
            <th className="hide-sm">Quality / $</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((c, i) => {
            const onF = frontier.has(`${c.model_id}::${c.stack_id}`);
            return (
              <tr key={`${c.model_id}-${c.stack_id}`}>
                <td className="left rank">{i + 1}</td>
                <td className="left">
                  <div className="model">
                    <span className="name">
                      {modelName(board, c.model_id)}
                      {onF && (
                        <span
                          className="frontier-tag"
                          title="On the cost/quality Pareto frontier"
                        >
                          <span className="pip" />
                          frontier
                        </span>
                      )}
                    </span>
                    <span className="stack">
                      + {harnessName(board, c.stack_id)}
                    </span>
                  </div>
                </td>
                <td className="score-cell">
                  {c.mean_score === null ? (
                    <span className="muted">—</span>
                  ) : (
                    <span className="big tnum">
                      {formatScore(c.mean_score)}
                    </span>
                  )}
                </td>
                <td className="hide-sm">
                  <Spark board={board} cell={c} />
                </td>
                <td className="hide-sm tnum">
                  {c.pass_hat_k === null ? (
                    <span className="muted">—</span>
                  ) : (
                    `${Math.round(c.pass_hat_k * 100)}%`
                  )}
                </td>
                <td className="tnum">{formatUsd(c.mean_cost_usd)}</td>
                <td className="hide-sm tnum muted">
                  {formatLatency(c.mean_latency_ms)}
                </td>
                <td className="hide-sm tnum muted">
                  {c.quality_per_dollar === null
                    ? "—"
                    : Math.round(c.quality_per_dollar)}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

/** Tiny per-task bar sparkline (score/10 height), with task initials beneath. */
function Spark({ board, cell }: { board: Board; cell: Cell }) {
  return (
    <span className="spark" aria-hidden>
      {board.tasks.map((t) => {
        const s = cell.per_task[t]?.score ?? null;
        const h = s === null ? 0 : Math.max(2, (s / 10) * 22);
        return (
          <span key={t} className="spark-bar" title={`${t}: ${s ?? "—"}`}>
            <span style={{ height: `${h}px` }} />
          </span>
        );
      })}
    </span>
  );
}
