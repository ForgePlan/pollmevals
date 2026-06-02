import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";
import Link from "next/link";

/**
 * Homepage teaser for the task catalogue. The full catalogue lives at /tasks;
 * here we just show how many tasks there are, by source, with a link through.
 * Data: public/tasks.json (gen_tasks_json.py).
 */
interface TaskInfo {
  source: string;
  scored: boolean;
}

const SOURCE_ORDER = [
  "own-authored",
  "BigCodeBench",
  "LiveCodeBench",
  "SWE-rebench-V2",
];

function loadCounts(): { source: string; count: number; scored: boolean }[] {
  const path = join(process.cwd(), "public", "tasks.json");
  if (!existsSync(path)) return [];
  const raw = JSON.parse(readFileSync(path, "utf-8")) as { tasks?: TaskInfo[] };
  const tasks = raw.tasks ?? [];
  const by = new Map<
    string,
    { source: string; count: number; scored: boolean }
  >();
  for (const t of tasks) {
    const g = by.get(t.source) ?? {
      source: t.source,
      count: 0,
      scored: t.scored,
    };
    g.count += 1;
    by.set(t.source, g);
  }
  return [...by.values()].sort(
    (a, b) => SOURCE_ORDER.indexOf(a.source) - SOURCE_ORDER.indexOf(b.source)
  );
}

export function TaskTeaser() {
  const counts = loadCounts();
  if (counts.length === 0) return null;
  const total = counts.reduce((n, c) => n + c.count, 0);

  return (
    <div className="task-teaser">
      <ul className="teaser-sources">
        {counts.map((c) => (
          <li key={c.source}>
            <span className="ts-n">{c.count}</span>
            <span className="ts-src">{c.source}</span>
            <span
              className={`source-pill ${c.scored ? "scored" : "catalogue"}`}
            >
              {c.scored ? "scored" : "catalogue"}
            </span>
          </li>
        ))}
      </ul>
      <Link className="teaser-cta" href="/tasks">
        Browse all {total} tasks →
      </Link>
    </div>
  );
}
