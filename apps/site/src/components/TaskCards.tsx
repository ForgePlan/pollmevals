import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";

/**
 * Task catalogue — WHAT the leaderboard evaluates. The board shows scores; this
 * shows the tasks behind them (category, difficulty, what's asked, what's
 * judged, and a link to the full spec in the repo) so a viewer can see and
 * verify the work being scored. Data: public/tasks.json (gen_tasks_json.py).
 */
interface TaskCriterion {
  name: string;
  weight: number | null;
}
interface TaskInfo {
  id: string;
  task_id: string;
  slug: string;
  category: string;
  difficulty: string;
  language: string;
  summary: string;
  criteria: TaskCriterion[];
  repo_url: string;
}

function loadTasks(): TaskInfo[] {
  const path = join(process.cwd(), "public", "tasks.json");
  if (!existsSync(path)) return [];
  const raw = JSON.parse(readFileSync(path, "utf-8")) as { tasks?: TaskInfo[] };
  return raw.tasks ?? [];
}

export function TaskCards() {
  const tasks = loadTasks();
  if (tasks.length === 0) return null;

  return (
    <div className="task-grid">
      {tasks.map((t) => (
        <div className="task-card" key={t.task_id}>
          <div className="task-head">
            <span className="task-label">{t.id}</span>
            <span className={`task-kind ${t.category}`}>{t.category}</span>
          </div>
          <div className="task-meta">
            {t.difficulty} · {t.language}
          </div>
          <p className="task-summary">{t.summary}</p>
          {t.criteria.length > 0 && (
            <div className="task-criteria">
              {t.criteria.map((c) => (
                <span className="crit-chip" key={c.name}>
                  {c.name}
                  {c.weight != null ? (
                    <span className="crit-w">
                      {" "}
                      {Math.round(c.weight * 100)}%
                    </span>
                  ) : null}
                </span>
              ))}
            </div>
          )}
          <a
            className="task-spec"
            href={t.repo_url}
            target="_blank"
            rel="noreferrer"
          >
            View full spec ↗
          </a>
        </div>
      ))}
    </div>
  );
}
