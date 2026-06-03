"use client";

import { useMemo, useState } from "react";
import type { Board, Cell } from "@/lib/board";
import { formatCost, formatScore } from "@/lib/format";

// Locale-independent thousands separator — `toLocaleString()` differs between
// the Node server render and the browser, which breaks hydration.
const grp = (n: number) =>
  Math.round(n)
    .toString()
    .replace(/\B(?=(\d{3})+(?!\d))/g, ",");

/**
 * The workhorse: every stack (model × harness) as a sortable, filterable row.
 * With many models the matrix and charts give the gestalt; this gives the exact
 * numbers — sort by any metric, filter by harness, to answer "rank them for X".
 */
type SortKey =
  | "model"
  | "harness"
  | "mean_score"
  | "mean_cost_usd"
  | "mean_latency_ms"
  | "pass_hat_k"
  | "quality_per_dollar";

interface Row {
  key: string;
  model: string;
  modelId: string;
  harness: string;
  stackId: string;
  tier: string;
  score: number | null;
  cost: number;
  latency: number;
  passk: number | null;
  qpd: number | null;
}

const COLS: { key: SortKey; label: string; num: boolean }[] = [
  { key: "model", label: "Model", num: false },
  { key: "harness", label: "Harness", num: false },
  { key: "mean_score", label: "Quality", num: true },
  { key: "mean_cost_usd", label: "Cost/task", num: true },
  { key: "mean_latency_ms", label: "Latency", num: true },
  { key: "pass_hat_k", label: "pass^k", num: true },
  { key: "quality_per_dollar", label: "Q/$", num: true },
];

export function StackMasterTable({ board }: { board: Board }) {
  const [sort, setSort] = useState<SortKey>("mean_score");
  const [dir, setDir] = useState<"asc" | "desc">("desc");
  const [harness, setHarness] = useState<string>("all");

  const nameOf = new Map(board.models.map((m) => [m.model_id, m]));
  const hOf = new Map(board.harnesses.map((h) => [h.stack_id, h]));

  const rows: Row[] = useMemo(
    () =>
      board.cells.map((c: Cell) => ({
        key: `${c.model_id}::${c.stack_id}`,
        model: nameOf.get(c.model_id)?.name ?? c.model_id,
        modelId: c.model_id,
        harness: hOf.get(c.stack_id)?.name ?? c.stack_id,
        stackId: c.stack_id,
        tier: nameOf.get(c.model_id)?.tier ?? "mid",
        score: c.mean_score,
        cost: c.mean_cost_usd,
        latency: c.mean_latency_ms,
        passk: c.pass_hat_k,
        qpd: c.quality_per_dollar,
      })),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [board]
  );

  const filtered =
    harness === "all" ? rows : rows.filter((r) => r.stackId === harness);

  const sorted = useMemo(() => {
    const val = (r: Row): number | string => {
      switch (sort) {
        case "model":
          return r.model.toLowerCase();
        case "harness":
          return r.harness.toLowerCase();
        case "mean_score":
          return r.score ?? -1;
        case "mean_cost_usd":
          return r.cost;
        case "mean_latency_ms":
          return r.latency;
        case "pass_hat_k":
          return r.passk ?? -1;
        case "quality_per_dollar":
          return r.qpd ?? -1;
      }
    };
    const s = [...filtered].sort((a, b) => {
      const va = val(a);
      const vb = val(b);
      const cmp =
        typeof va === "string"
          ? va.localeCompare(vb as string)
          : (va as number) - (vb as number);
      return dir === "asc" ? cmp : -cmp;
    });
    return s;
  }, [filtered, sort, dir]);

  const onSort = (k: SortKey) => {
    if (k === sort) setDir((d) => (d === "asc" ? "desc" : "asc"));
    else {
      setSort(k);
      setDir(k === "model" || k === "harness" ? "asc" : "desc");
    }
  };

  return (
    <div className="master-card">
      <div className="master-toolbar">
        <span className="master-count">{sorted.length} stacks</span>
        <div className="seg" role="tablist" aria-label="filter harness">
          <button
            className={`seg-btn ${harness === "all" ? "on" : ""}`}
            onClick={() => setHarness("all")}
          >
            All
          </button>
          {board.harnesses
            .slice()
            .sort((a, b) => a.level - b.level)
            .map((h) => (
              <button
                key={h.stack_id}
                className={`seg-btn ${harness === h.stack_id ? "on" : ""}`}
                onClick={() => setHarness(h.stack_id)}
              >
                {h.name}
              </button>
            ))}
        </div>
      </div>
      <div className="master-scroll">
        <table className="master">
          <thead>
            <tr>
              {COLS.map((col) => (
                <th
                  key={col.key}
                  className={`${col.num ? "num" : ""} ${
                    sort === col.key ? "sorted" : ""
                  }`}
                  onClick={() => onSort(col.key)}
                >
                  {col.label}
                  {sort === col.key && (
                    <span className="arrow">{dir === "asc" ? " ↑" : " ↓"}</span>
                  )}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {sorted.map((r) => (
              <tr key={r.key} className={r.score === null ? "unscored" : ""}>
                <td>
                  <span className="m-name">{r.model}</span>
                  <span className={`tier ${r.tier}`}>{r.tier}</span>
                </td>
                <td className="m-harness">{r.harness}</td>
                <td className="num strong">
                  {r.score === null ? "—" : formatScore(r.score)}
                </td>
                <td className="num">{formatCost(r.cost)}</td>
                <td className="num">
                  {r.latency ? (r.latency / 1000).toFixed(1) + "s" : "—"}
                </td>
                <td className="num">
                  {r.passk === null ? "—" : Math.round(r.passk * 100) + "%"}
                </td>
                <td className="num">{r.qpd === null ? "—" : grp(r.qpd)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
