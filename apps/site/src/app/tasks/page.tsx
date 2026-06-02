import type { Metadata } from "next";
import Link from "next/link";
import { TaskCatalogue } from "@/components/TaskCatalogue";

export const metadata: Metadata = {
  title: "Tasks · POLLMEVALS",
  description:
    "The task catalogue behind the leaderboard — every task grouped by source, with its license, dataset link, and full spec. Own-authored tasks are scored; imported benchmark tasks are catalogue-only.",
};

export default function TasksPage() {
  return (
    <>
      <section className="hero compact">
        <p className="eyebrow">What we evaluate · the task catalogue</p>
        <h1>
          Every score traces back to a{" "}
          <span className="em">concrete task.</span>
        </h1>
        <p className="lede">
          A task is a frozen prompt, a gold solution, hidden tests, and a
          weighted judge rubric. This is the full catalogue, grouped by where
          each task comes from — with the source license, a link to the dataset,
          and a link to each task&apos;s full spec in the repo.
        </p>
        <div className="honesty" role="note">
          <span className="icon">✱</span>
          <span>
            <strong>Own-authored tasks are the scored ground truth.</strong>{" "}
            Imported benchmark tasks are <strong>catalogue-only</strong> for now
            — they need new runners and must pass the ADR-007 G4 contamination
            gate before any scored run. See{" "}
            <a
              href="https://github.com/ForgePlan/pollmevals/blob/main/evals/task-packs/IMPORTED-CATALOGUE.md"
              target="_blank"
              rel="noreferrer"
            >
              IMPORTED-CATALOGUE.md
            </a>
            .
          </span>
        </div>
        <p className="back-link">
          <Link href="/">← Back to the leaderboard</Link>
        </p>
      </section>

      <TaskCatalogue />
    </>
  );
}
