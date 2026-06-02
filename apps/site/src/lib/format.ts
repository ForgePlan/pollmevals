/** Number / value formatting for the leaderboard. Deterministic, locale-stable. */

/** USD with adaptive precision: sub-cent → 4dp, else 2-4dp. Always "$" prefixed. */
export function formatUsd(value: string | number): string {
  const n = typeof value === "string" ? Number(value) : value;
  if (n === 0) return "$0";
  if (n < 0.01) return `$${n.toFixed(4)}`;
  if (n < 1) return `$${n.toFixed(3)}`;
  return `$${n.toFixed(2)}`;
}

/** Latency ms → human: "3.3s" or "847ms". */
export function formatLatency(ms: number): string {
  if (ms >= 1000) return `${(ms / 1000).toFixed(1)}s`;
  return `${Math.round(ms)}ms`;
}

/** Token counts with thin-space thousands grouping: 12 345. */
export function formatTokens(n: number): string {
  return n.toLocaleString("en-US").replace(/,/g, " ");
}

/** A 0-1 fraction as a whole-percent: 0.358 → "36%". */
export function formatPct(value: number | null): string {
  if (value === null) return "—";
  return `${Math.round(value * 100)}%`;
}

/** A 0-10 score to 1dp, or em-dash when absent. */
export function formatScore(value: number | null): string {
  if (value === null) return "—";
  return value.toFixed(1);
}

/** Truncate a content hash for display: "sha256:6050f794…7e7af". */
export function shortHash(hash: string): string {
  const body = hash.replace(/^sha256:/, "");
  if (body.length <= 13) return hash;
  return `${body.slice(0, 8)}…${body.slice(-5)}`;
}
