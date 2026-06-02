import type { Board, Cell } from "@/lib/board";
import { formatUsd, formatScore } from "@/lib/format";

/**
 * Per-task winners — because the best stack is NOT the same for every task.
 * For each task we show a small podium (top-3 stacks by that task's score), so
 * the task-dependence of "which harness × model" is explicit.
 */
const TASK_LABELS: Record<string, { label: string; kind: string }> = {
  be_01_jwt_auth: { label: "JWT auth middleware", kind: "backend" },
  fe_01_multistep_form: { label: "Multi-step form", kind: "frontend" },
  doc_01_cli_readme: { label: "CLI README", kind: "docs" },
};

const harnessName = (board: Board, stackId: string) =>
  board.harnesses.find((h) => h.stack_id === stackId)?.name ?? stackId;
const modelName = (board: Board, modelId: string) =>
  board.models.find((m) => m.model_id === modelId)?.name ?? modelId;

export function PerTaskWinners({ board }: { board: Board }) {
  const podiums = board.tasks.map((task) => {
    const ranked = board.cells
      .map((c) => ({
        cell: c,
        score: c.per_task[task]?.score ?? null,
        cost: c.per_task[task]?.cost_usd ?? c.mean_cost_usd,
      }))
      .filter(
        (x): x is { cell: Cell; score: number; cost: number } =>
          x.score !== null
      )
      .sort((a, b) => b.score - a.score)
      .slice(0, 3);
    return { task, ranked };
  });

  if (podiums.every((p) => p.ranked.length === 0)) return null;

  return (
    <div className="task-grid">
      {podiums.map(({ task, ranked }) => {
        const meta = TASK_LABELS[task] ?? { label: task, kind: "" };
        return (
          <div className="task-card" key={task}>
            <div className="task-head">
              <span className="task-label">{meta.label}</span>
              {meta.kind && (
                <span className={`task-kind ${meta.kind}`}>{meta.kind}</span>
              )}
            </div>
            <ol className="podium">
              {ranked.map((r, i) => (
                <li key={i} className={i === 0 ? "win" : ""}>
                  <span className="pos">{i + 1}</span>
                  <span className="combo">
                    <span className="cm">
                      {modelName(board, r.cell.model_id)}
                    </span>
                    <span className="ch">
                      + {harnessName(board, r.cell.stack_id)}
                    </span>
                  </span>
                  <span className="psc tnum">{formatScore(r.score)}</span>
                  <span className="pcost tnum muted">{formatUsd(r.cost)}</span>
                </li>
              ))}
            </ol>
          </div>
        );
      })}
    </div>
  );
}
