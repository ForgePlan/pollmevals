# @pollmevals/site

The POLLMEVALS public site — the open-evidence leaderboard, rendered from a
frozen `leaderboard.json` (produced by `apps/eval-core-py/scripts/build_leaderboard.py`).

Next.js 15 · App Router · static export (`output: 'export'`). No server runtime —
deployable to any static host (Cloudflare Pages / R2 / GitHub Pages).

```bash
pnpm install
pnpm --filter @pollmevals/site dev      # http://localhost:3000
pnpm --filter @pollmevals/site build     # → out/ (static)
pnpm --filter @pollmevals/site test      # lib unit tests (node --test)
```

## Honesty contract

`leaderboard.json` carries cost/latency always; quality fields (`mean_score`,
`pass^k`, …) are `null` until a run is scored. The UI renders that absence as
an em-dash with a note — never a fabricated zero. See `src/lib/leaderboard.ts`.
