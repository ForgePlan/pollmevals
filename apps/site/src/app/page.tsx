import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";
import type { Board } from "@/lib/board";
import { bestCell, cellMap } from "@/lib/board";
import { formatUsd, formatScore } from "@/lib/format";
import { HarnessModelMatrix } from "@/components/HarnessModelMatrix";
import { StackParetoChart } from "@/components/StackParetoChart";
import { ScaffoldingLift } from "@/components/ScaffoldingLift";
import { PerTaskWinners } from "@/components/PerTaskWinners";
import { StackTable } from "@/components/StackTable";
import { TaskTeaser } from "@/components/TaskTeaser";

function loadBoard(): Board {
  // Prefer the REAL run data (board.json, emitted by build_real_board.py) when
  // present; fall back to the illustrative preview otherwise (RFC-006 Phase 4c).
  const real = join(process.cwd(), "public", "board.json");
  const path = existsSync(real)
    ? real
    : join(process.cwd(), "public", "board.illustrative.json");
  return JSON.parse(readFileSync(path, "utf-8")) as Board;
}

export default function Home() {
  const board = loadBoard();
  const map = cellMap(board);
  const best = bestCell(board, "mean_score");

  // The headline thesis comparison: cheapest model + deepest scaffold vs the
  // most expensive model bare.
  const cheap = board.models[0];
  const dearest = board.models[board.models.length - 1];
  const deepest = [...board.harnesses].sort((a, b) => b.level - a.level)[0];
  const cheapScaffold =
    cheap && deepest
      ? map.get(`${cheap.model_id}::${deepest.stack_id}`)
      : undefined;
  const dearBare = dearest
    ? map.get(`${dearest.model_id}::raw-llm`)
    : undefined;

  return (
    <>
      <section className="hero">
        <p className="eyebrow">Open evidence layer · model × harness × task</p>
        <h1>
          A cheap model with the right scaffolding beats an expensive one{" "}
          <span className="em">without it.</span>
        </h1>
        <p className="lede">
          POLLMEVALS ranks whole <strong>stacks</strong> — a base model wrapped
          in an agent harness (tools, skills, memory, sub-agents, validator
          loops). The leaderboard&apos;s unit is the{" "}
          <strong>harness × model</strong> pairing, scored per task, on quality,
          cost, and reliability.
        </p>

        {board.illustrative && (
          <div className="honesty" role="note">
            <span className="icon">✱</span>
            <span>
              <strong>Illustrative preview.</strong> These numbers are a
              designed sample — not a real run — built to show how the
              leaderboard reads once the executor scores real harnesses
              end-to-end. Real runs replace this data wholesale; the shapes and
              methodology are real.
            </span>
          </div>
        )}

        {cheapScaffold && dearBare && (
          <div className="thesis-strip">
            <div className="ts-side">
              <span className="ts-cap">cheap model + deep harness</span>
              <span className="ts-combo">
                {cheap?.name} <span className="plus">+</span> {deepest?.name}
              </span>
              <span className="ts-stat">
                <b className="good">{formatScore(cheapScaffold.mean_score)}</b>{" "}
                quality · {formatUsd(cheapScaffold.mean_cost_usd)}/task
              </span>
            </div>
            <span className="ts-vs">beats</span>
            <div className="ts-side dim">
              <span className="ts-cap">expensive model, bare</span>
              <span className="ts-combo">
                {dearest?.name} <span className="plus">+</span> Raw LLM
              </span>
              <span className="ts-stat">
                <b>{formatScore(dearBare.mean_score)}</b> quality ·{" "}
                {formatUsd(dearBare.mean_cost_usd)}
                /task
              </span>
            </div>
          </div>
        )}
      </section>

      <section className="section" id="matrix">
        <h2>Which harness, with which model</h2>
        <p className="section-lede">
          Rows are harnesses from bare (L0) down to the deepest scaffold;
          columns are models from cheapest to priciest. Read a column
          top-to-bottom to watch scaffolding lift a single model
          {best && (
            <>
              {" "}
              — the best stack here is{" "}
              <strong>
                {board.models.find((m) => m.model_id === best.model_id)?.name} +{" "}
                {
                  board.harnesses.find((h) => h.stack_id === best.stack_id)
                    ?.name
                }
              </strong>
              .
            </>
          )}
        </p>
        <HarnessModelMatrix board={board} />
      </section>

      <section className="section" id="frontier">
        <h2>Cost vs quality</h2>
        <p className="section-lede">
          Every stack as a point. Scaffolded cheap models climb up-and-left of
          bare expensive ones; the emerald line is the Pareto frontier — stacks
          nothing else beats on both axes.
        </p>
        <StackParetoChart board={board} />
      </section>

      <section className="section" id="lift">
        <h2>What scaffolding buys each model</h2>
        <p className="section-lede">
          The ablation: quality as harness depth grows. Weaker models climb
          steepest — scaffolding compensates for a weaker base, which is the
          whole thesis.
        </p>
        <ScaffoldingLift board={board} />
      </section>

      <section className="section" id="catalogue">
        <h2>What we evaluate · the tasks</h2>
        <p className="section-lede">
          Every score traces back to a concrete task — a frozen prompt, a gold
          solution, hidden tests, and a weighted judge rubric. The full
          catalogue lives on its own page, grouped by source with licenses and
          dataset links.
        </p>
        <TaskTeaser />
      </section>

      <section className="section" id="tasks">
        <h2>Different tasks, different winners</h2>
        <p className="section-lede">
          The best stack is task-dependent: backend rewards validator loops,
          frontend rewards a strong base model, docs compress the field. Top-3
          per task:
        </p>
        <PerTaskWinners board={board} />
      </section>

      <section className="section" id="leaderboard">
        <h2>All stacks · {board.cells.length} combinations</h2>
        <StackTable board={board} />
      </section>

      <section className="section method" id="methodology">
        <div className="card">
          <h3>The unit is a stack</h3>
          <p>
            Not a model — a <strong>stack</strong>: base model + scaffolding
            ladder (L0–L8): system prompt, tools, skills, file &amp; vector
            memory, sub-agents, validator loops, framework. Same model,
            different harness = a different row.
          </p>
        </div>
        <div className="card">
          <h3>Quality, cost &amp; reliability</h3>
          <p>
            Quality is the judged score (≥3 models, never self-judging, median).
            Cost is the <em>total</em> incl. judges. Reliability is{" "}
            <code>pass^k</code> — solved on every seed, not just lucky once.
          </p>
        </div>
        <div className="card">
          <h3>Quality-per-$ is a lens, not a verdict</h3>
          <p>
            Pure quality ÷ cost over-rewards dirt-cheap stacks. The honest
            cost-vs-quality answer is the <strong>Pareto frontier</strong> — and
            which stack clears <em>your</em> quality bar most cheaply.
          </p>
        </div>
        <div className="card">
          <h3>Task-dependence is real</h3>
          <p>
            There is no single &ldquo;best stack&rdquo;. The winner shifts by
            task category, so the board reports per-task as well as overall —
            pick for the work you actually do.
          </p>
        </div>
      </section>
    </>
  );
}
