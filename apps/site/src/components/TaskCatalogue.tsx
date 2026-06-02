import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";

/**
 * Task catalogue (the dedicated /tasks page). The leaderboard shows scores; this
 * shows every task BEHIND those scores — grouped by where it came from, with the
 * source's license, a link to the dataset, and a per-task link to the full spec.
 *
 * Honesty: own-authored tasks are the scored ground truth; imported benchmark
 * tasks are catalogue-only (not yet scored — they need new runners + the ADR-007
 * G4 contamination gate). The `scored` flag drives that badge per source.
 * Data: public/tasks.json (gen_tasks_json.py).
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
  source: string;
  source_url: string | null;
  license: string;
  sourcing: string;
  scored: boolean;
}

// One-line "what is this source" blurb per source name. Keeps the catalogue
// self-explanatory without a docs round-trip.
const SOURCE_BLURB: Record<string, string> = {
  "own-authored":
    "Written by the maintainer under the RFC-003 protocol — the scored ground truth for v0.1.",
  BigCodeBench:
    "Function-level Python coding tasks from the BigCodeBench benchmark.",
  LiveCodeBench:
    "Competitive-programming problems (AtCoder, 2025) — released after the model training cutoff, so contamination-resistant.",
  "SWE-rebench-V2":
    "Real GitHub bug-fix tasks pinned to a commit, from Nebius SWE-rebench-V2.",
};

// Stable display order: own-authored first (it's what's scored), then imports.
const SOURCE_ORDER = [
  "own-authored",
  "BigCodeBench",
  "LiveCodeBench",
  "SWE-rebench-V2",
];

function loadTasks(): TaskInfo[] {
  const path = join(process.cwd(), "public", "tasks.json");
  if (!existsSync(path)) return [];
  const raw = JSON.parse(readFileSync(path, "utf-8")) as { tasks?: TaskInfo[] };
  return raw.tasks ?? [];
}

interface SourceGroup {
  source: string;
  source_url: string | null;
  license: string;
  scored: boolean;
  tasks: TaskInfo[];
}

function groupBySource(tasks: TaskInfo[]): SourceGroup[] {
  const by = new Map<string, SourceGroup>();
  for (const t of tasks) {
    let g = by.get(t.source);
    if (!g) {
      g = {
        source: t.source,
        source_url: t.source_url,
        license: t.license,
        scored: t.scored,
        tasks: [],
      };
      by.set(t.source, g);
    }
    g.tasks.push(t);
  }
  return [...by.values()].sort(
    (a, b) => SOURCE_ORDER.indexOf(a.source) - SOURCE_ORDER.indexOf(b.source)
  );
}

function TaskCard({ t }: { t: TaskInfo }) {
  return (
    <div className="task-card">
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
                <span className="crit-w"> {Math.round(c.weight * 100)}%</span>
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
  );
}

export function TaskCatalogue() {
  const groups = groupBySource(loadTasks());
  if (groups.length === 0) return null;

  return (
    <div className="catalogue">
      {groups.map((g) => (
        <section className="source-group" key={g.source}>
          <div className="source-head">
            <div className="source-title">
              <h2>{g.source}</h2>
              <span
                className={`source-pill ${g.scored ? "scored" : "catalogue"}`}
              >
                {g.scored ? "scored" : "catalogue-only"}
              </span>
              <span className="source-count">{g.tasks.length} tasks</span>
            </div>
            <p className="source-blurb">{SOURCE_BLURB[g.source] ?? ""}</p>
            <div className="source-meta">
              <span className="source-lic">license · {g.license}</span>
              {g.source_url && (
                <a href={g.source_url} target="_blank" rel="noreferrer">
                  dataset ↗
                </a>
              )}
            </div>
          </div>
          <div className="task-grid">
            {g.tasks.map((t) => (
              <TaskCard t={t} key={t.task_id} />
            ))}
          </div>
        </section>
      ))}
    </div>
  );
}
