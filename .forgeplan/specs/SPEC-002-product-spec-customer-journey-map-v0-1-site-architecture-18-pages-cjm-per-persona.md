---
depth: standard
id: SPEC-002
kind: spec
last_modified_at: 2026-05-24T23:21:46.549161+00:00
last_modified_by: claude-code/2.1.150
links:
- target: PRD-004
  relation: refines
- target: NOTE-005
  relation: refines
- target: PRD-001
  relation: informs
status: draft
title: Product spec + customer journey map v0.1 — site architecture, 18 pages, CJM per persona
---

# SPEC-002: Product spec + customer journey map v0.1 — site architecture, 18 pages, CJM per persona

## Summary

POLLMEVALS product spec в structured artifact form, lifted из `docs/old/dd.md` lines 1414-1738 (original product spec session by Eli) **plus** PM-grade Customer Journey Map (5 stages × 4 personas) **plus** page-level acceptance criteria for 18 site pages prioritized P0-P3. Includes API contracts for backend service (Hono + Postgres + R2), data flows, and full gap analysis estimating effort (~280-420h) to ship MVP. **Use case**: open этот SPEC когда нужно ответить "что мы строим как продукт, для кого, и какой effort до MVP".

## Purpose

POLLMEVALS product spec в structured artifact form. **Lifts content из `docs/old/dd.md` sections 1-12** + adds **PM-level Customer Journey Map** (5 stages × 4 personas) + page-level acceptance criteria.

**Use case**: when reading-up "что мы строим как продукт?" or "как пользователь дойдёт от первого касания до retention?" — этот SPEC отвечает. CJM section дает phasing для frontend build (PRD-004 implementation roadmap).

Source seed: `docs/old/dd.md` lines 1414-1738 (POLLMEVALS Product Specification v0.1 from Eli's original session с консультантом).

## Status

draft

## Personas (4 from dd.md)

### Persona A — Engineering Lead

- **Role**: выбирает stack для команды 3-50 человек
- **Pain**: тратит days/weeks figuring out which model+обвязка работает для production
- **Need**: cost-quality Pareto, region-aware latency, reproducibility, stability
- **Willing to pay**: Tier 1 API access ($50/мес для team dashboard)

### Persona B — Indie Hacker / Founder

- **Role**: builds на локальных моделях (M-chip) + cloud as needed
- **Pain**: не знает какие Ollama-models + skills дают приличный результат
- **Need**: filter by "local/Ollama-friendly" + Pareto на consumer hardware
- **Willing to pay**: $0 (Tier 0 free leaderboard)

### Persona C — Researcher / Industry Analyst

- **Role**: пишет reports, статьи, делает запросы для VC
- **Pain**: existing leaderboards (Arena, AA) субъективны или narrow
- **Need**: raw data export, methodology transparency, citation
- **Willing to pay**: Tier 1 API ($50/мес) или Tier 2 custom evals ($5-20k for org report)

### Persona D — Model Creator (Anthropic, OpenAI, OSS teams)

- **Role**: ML lead в LLM-vendor company
- **Pain**: existing leaderboards имеют bias / paid-only / hidden methodology
- **Need**: fair public evaluation + ability to add own model
- **Willing to pay**: Tier 3 sponsored eval (accelerated addition, always disclosed)

## Customer Journey Map — 5 stages × 4 personas

### Stage 1 — Awareness (узнал о существовании)

| Persona | Trigger | Channel | What hooks |
|---|---|---|---|
| A Lead | Blog post в HN/Reddit "scaffolding ablation" | HN frontpage, Twitter | "Наконец-то кто-то меряет стеки" |
| B Indie | Search "best local LLM coding" | Google, r/LocalLLaMA | Pareto на M-chip — practical |
| C Researcher | Citation в академической работе | arXiv reference list | Open data + reproducibility |
| D Vendor | Team monitoring competitor mentions | Twitter, Discord | "Sponsored eval" — controlled positioning |

### Stage 2 — Consideration (стоит ли тратить время)

| Persona | Critical question | Where they look |
|---|---|---|
| A Lead | "Серьёзные ли это ребята или ещё одна тяп-ляп лидербоарда?" | `/methodology` + `/judges` + `/calibration` — inter-judge α, bootstrap CI tables |
| B Indie | "Покрывает ли локальные модели?" | `/leaderboards` filter "local/Ollama only" |
| C Researcher | "Воспроизводимо?" | `/runs/[hash]` + raw outputs + version pins + license |
| D Vendor | "Можно ли добавить свою модель?" | `/propose-model` form + `/disclosures` page |

### Stage 3 — Onboarding (попробовал — захотел использовать)

```
A → Tier 1 API key signup → /datasets export Parquet → internal dashboard integration
B → /datasets bulk download (Tier 0 free) → pandas+plotly локальный анализ
C → /api OR /datasets с DOI/release tag → cite в paper
D → /propose-model форма OR sponsored Tier 3 → модель в weekly grid через 1-2 weeks
```

### Stage 4 — Active Use (еженедельно возвращается)

Weekly cycle для всех personas (Monday 03:00 UTC = run completed → 09:00 LT users check):

| Persona | Weekly action |
|---|---|
| A Lead | Open dashboard → check deltas → filter by region/budget → decide stack changes |
| B Indie | Read /blog post "what changed this week" → maybe `ollama pull <new-best>` |
| C Researcher | Download delta `/datasets/2026-W23.parquet` → feed в longitudinal study |
| D Vendor | Email alert "your model X drift z=2.3" → investigate causes → response в /discuss |

### Stage 5 — Retention + Advocacy

**Что вернёт A Lead**: ROI proof ("сэкономили $X/мес переключив stack по POLLMEVALS data")
**Что вернёт B Indie**: community feel — voting на /vote, comments на /blog, propose-task forms
**Что вернёт C Researcher**: citation count growth — POLLMEVALS becomes academic reference standard
**Что вернёт D Vendor**: fair treatment + transparent disclosure — vendor mentions POLLMEVALS в release notes

## Site architecture — 18 pages (from dd.md section 5)

### Pages priority (для MVP cut)

| Priority | Page | MVP target | Notes |
|---|---|---|---|
| **P0** | `/leaderboards` | ✅ MUST для MVP | 3 tabs: by Model, by Stack, by Task class |
| **P0** | `/models/[slug]` | ✅ MUST | Radar + history + latency by region + best stacks |
| **P0** | `/tasks/[slug]` | ✅ MUST | Description + gold + history (gold published after first weekly run для contamination guard) |
| **P0** | `/runs/[hash]` | ✅ MUST | Reproducibility proof: model versions + tool versions + raw outputs + cost |
| **P0** | `/methodology` | ✅ MUST | Frozen v0.1.0 + how-we-measure |
| **P1** | `/stacks/[slug]` | 🟡 v0.2 | Best models for stack + cost-quality vs bare |
| **P1** | `/compare` | 🟡 v0.2 | Side-by-side до 4 моделей/стеков + shareable URL |
| **P1** | `/judges` | 🟡 v0.2 | Judge list + calibration scores + inter-judge matrix |
| **P1** | `/calibration` | 🟡 v0.2 | Golden set + judge scores per task |
| **P1** | `/scoring` | 🟡 v0.2 | Formulas documentation per task category |
| **P2** | `/blog` | 🟡 v0.3 | Weekly updates + long-form posts |
| **P2** | `/changelog` | 🟡 v0.3 | Methodology + model + task changes + RSS |
| **P2** | `/status` | 🟡 v0.3 | Cron health + last/next run + worker uptime |
| **P3** | `/vote` | ❌ v1.0 | Community voting GitHub OAuth |
| **P3** | `/propose-model`, `/propose-task`, `/propose-stack` | ❌ v1.0 | Submission forms |
| **P3** | `/api` | ❌ v1.0 | Public OpenAPI docs + auth + rate limits |
| **P3** | `/datasets` | ❌ v1.0 | Bulk download Parquet/CSV |
| **P3** | `/pricing` | ❌ v1.0 | Tier 0/1/2 plans |

## Per-page acceptance criteria (P0 only)

### `/leaderboards`

- AC-1: Default sort by quality desc; URL `?sort=cost_per_correct` works
- AC-2: 3 tabs: by Model / by Stack / by Task class — switchable без full page reload
- AC-3: Filters: task category (multi), region (single), budget USD ceiling — URL-preserved
- AC-4: Top row shows last-week deltas (Δ% per top-5 entries)
- AC-5: Click row → detail page (`/models/[slug]` or `/stacks/[slug]` or `/tasks/[slug]`)
- AC-6: Load time < 1s on desktop с warm cache (R2 + Postgres + Redis 10-min TTL)

### `/models/[slug]`

- AC-1: Radar chart 8 categories (per scoring.md task taxonomy)
- AC-2: History line chart — last 12 weekly runs
- AC-3: Latency by region (4 regions table: TTFT + p95)
- AC-4: Top 3 stacks для этой модели — cost & quality
- AC-5: Raw outputs link на R2 (per-eval download)
- AC-6: Model card metadata: version_tag, context_window, max_output_tokens, is_open_weight

### `/tasks/[slug]`

- AC-1: Description + difficulty + category
- AC-2: Gold solution — **published только после первого weekly run** (contamination guard per NOTE-006)
- AC-3: Evaluator code link (GitHub)
- AC-4: History results по моделям (radar + table)
- AC-5: Submission form `/propose-task` link (если P3 launched)

### `/runs/[hash]`

- AC-1: Reproducibility headlines: total_cost_usd, total_input_tokens, total_output_tokens
- AC-2: Versions table: inspect_ai_version, litellm_version, vllm_version, methodology_version
- AC-3: Models pinned с version_tag
- AC-4: Raw outputs download (whole run archive)
- AC-5: Reproduce script: `make reproduce HASH=<this>` — copies command snippet
- AC-6: Status icon: `published` / `degraded` / `superseded`

### `/methodology`

- AC-1: Frozen methodology v0.1.0 published in full (scoring formulas, judge policy, sandbox spec)
- AC-2: Version selector — view methodology v0.1.0 / v0.2 / etc.
- AC-3: Each formula has worked example (small input → score breakdown)
- AC-4: Link к `/judges` (calibration scores) и `/scoring` (per-formula deep-dive)

## API Contracts

Hono backend service exposes REST API at `/api/v1/*`. All responses JSON. Auth via API key для Tier 1+ endpoints; public endpoints unauthenticated.

### `GET /api/v1/leaderboards`

Powers `/leaderboards` page.

**Query params**:
- `tab` — `models` (default) | `stacks` | `tasks`
- `sort` — `quality` (default) | `cost_per_correct` | `tps`
- `task_category` — multi: `backend,frontend,docs,...`
- `region` — single: `eu-central` (default) | `us-east` | `apac` | `sa`
- `budget_ceiling_usd` — float — exclude entries above

**Response**:
```typescript
{
  rows: Array<{
    model_id: string;        // or stack_id / task_id depending on tab
    quality_score: number;   // 0-10
    cost_per_correct_usd: number;
    tps_avg: number;
    delta_last_week_pct: number | null;
  }>;
  total: number;
  last_run_hash: string;     // for click-through /runs/[hash]
  cached_at: string;         // ISO-8601
}
```

### `GET /api/v1/models/[slug]`

Powers `/models/[slug]` page.

**Response**:
```typescript
{
  model: {
    slug: string;
    name: string;
    vendor: string;
    version_tag: string;
    is_open_weight: boolean;
    context_window: number;
    max_output_tokens: number;
  };
  radar: Array<{ axis: string; score: number; ci_lower: number; ci_upper: number; }>;
  history: Array<{ run_hash: string; week: string; overall_score: number; }>;
  latency_by_region: Array<{ region: string; ttft_ms_p50: number; ttft_ms_p95: number; total_latency_ms_p95: number; }>;
  best_stacks: Array<{ stack_slug: string; quality_uplift_pct: number; cost_usd: number; }>;
  raw_outputs_url: string;   // R2 archive download
}
```

### `GET /api/v1/runs/[hash]`

Powers `/runs/[hash]` page. **Direct reads from manifest.json** в R2 (no DB query for immutable runs).

**Response** (matches SPEC-001 Manifest schema verbatim):
```typescript
{
  schema_version: "pollmevals.run_manifest.v1.0.0";
  run_hash: string;
  run_type: "smoke" | "weekly" | "flagship_triggered";
  methodology_version: string;
  created_at: string; published_at: string;
  region: string;
  stack_pins: StackPin[];
  model_pins: ModelPin[];
  task_pins: TaskPin[];
  evals: EvalRow[];
  aggregates: RunAggregates;
  status: "published" | "degraded" | "superseded";
}
```

### `GET /api/v1/tasks/[slug]`

Powers `/tasks/[slug]` page.

**Response**:
```typescript
{
  task: { slug: string; version: string; category: string; difficulty: string; description_md: string; };
  gold_solution_url: string | null;  // null until first weekly run published (NOTE-006 contamination guard)
  evaluator_url: string;             // GitHub link
  history: Array<{ run_hash: string; week: string; model_scores: Array<{ model_slug: string; score: number; }>; }>;
}
```

### `GET /api/v1/methodology?version=v0.1.0`

Powers `/methodology` page. **Static SSG** — content served from `docs/02-methodology/`.

**Response**:
```typescript
{
  version: string;
  frozen_at: string;
  scoring_formulas: Record<string, string>;  // category -> formula markdown
  judge_policy: string;                       // markdown
  sandbox_spec: string;                       // markdown
  changelog: Array<{ version: string; changes: string[]; }>;
}
```

### Postgres tables (writes by orchestrator; reads by API)

Per `packages/db/migrations/0001_initial.sql` + new `0002_judges_calibration_votes.sql` (TBD per NOTE-005 Section H):

- `models`, `model_providers`, `stacks`, `tasks`, `runs`, `evals` — ✅ in 0001
- `judgments`, `calibration_runs`, `votes` — ❌ to add в 0002

### R2 paths (content-addressed, immutable)

```
r2://pollmevals/runs/sha256:<hash>/manifest.json    (mode 0o444 per ADR-002)
r2://pollmevals/evals/<eval_id>/raw_output-<sha>.txt
r2://pollmevals/evals/<eval_id>/normalized_output-<sha>.txt
r2://pollmevals/evals/<eval_id>/evaluator_json-<sha>.json
r2://pollmevals/evals/<eval_id>/judge_reasoning-<sha>.json
```

Manifest paths follow SPEC-001 ArtifactRef contract; URI prefix `r2://` vs current `file://` differs только в `R2 upload step` (Phase 4+ orchestrator scope; today writes locally per Track D fix).

## Data flow — где что хранится

```
┌─────────────────────────────────────────────────────────────┐
│ User browser  →  Next.js 15 SSG + Vercel edge functions     │
│                  (frontend, all P0-P1 pages)                │
└────────────────┬────────────────────────────────────────────┘
                 │ HTTP GET / API
                 ▼
        ┌────────────────────┐
        │ Backend API (Hono) │ ← stats, votes, datasets endpoints
        └─────┬──────────────┘
              │
       ┌──────▼─────┐   ┌──────────────┐   ┌──────────────────┐
       │ Postgres   │   │ Redis (10m)  │   │ Cloudflare R2    │
       │ - models   │   │ - leaderboard│   │ - raw outputs    │
       │ - evals    │   │   cache      │   │ - manifests      │
       │ - judges   │   │ - task queue │   │ - judge reasoning│
       │ - votes    │   └──────────────┘   └──────────────────┘
       └────────────┘
```

## Gap analysis — что нужно реализовать (полный список artifacts + code)

### Frontend stack (apps/site/)

| Что | Artifact / code | Effort | Status |
|---|---|---|---|
| Next.js 15 App Router skeleton | `apps/site/` дир + page.tsx per route | 4-8h initial | ❌ skeleton only |
| Component library (Tailwind + shadcn/ui) | `apps/site/components/` | 8-12h | ❌ |
| 5 P0 pages | `apps/site/app/(public)/<page>/page.tsx` | 30-50h | ❌ |
| Data fetch hooks (React Query → Hono API) | `apps/site/lib/queries.ts` | 4-8h | ❌ |
| Radar chart component (per-model, 8 axes) | `apps/site/components/radar.tsx` | 6-10h | ❌ |
| Cost-quality scatter (Pareto) | `apps/site/components/pareto.tsx` | 4-6h | ❌ |
| Reproduce snippet copy button | `apps/site/components/reproduce-snippet.tsx` | 2-4h | ❌ |

**Frontend MVP estimate: ~60-100h**.

### Backend API (apps/api/)

| Что | Artifact / code | Effort | Status |
|---|---|---|---|
| Hono service skeleton | `apps/api/` дир + routes | 4-6h | ❌ skeleton |
| 4 endpoints (leaderboards/models/runs/tasks) | `apps/api/routes/*.ts` | 18-28h | ❌ |
| Postgres schema migrations (judges + calibration + votes) | `packages/db/migrations/0002_*.sql` | 4-8h | ❌ Section H gap |
| Redis cache layer | `apps/api/lib/cache.ts` | 4-6h | ❌ |
| R2 upload integration | `apps/api/lib/r2.ts` + URL refs в Postgres | 6-10h | ❌ |

**Backend API MVP estimate: ~36-58h**.

### Operations (cron + drift + contamination)

| Что | Artifact | Effort | Status |
|---|---|---|---|
| Weekly cron via GitHub Actions | `.github/workflows/weekly-eval.yml` | 4-6h | ❌ |
| Drift detection logic (z-score > 2.0 alert) | PRD-007 impl per NOTE-006 policy | 8-12h | ❌ |
| Contamination check script | `infra/scripts/check_contamination.py` | 8-12h | ❌ |
| Held-out task vault (private repo) | `pollmevals/heldout-tasks` separate org | 4-6h | ❌ |
| Alert channels (RSS + Twitter + email) | Wire to /blog publish + RSS gen | 4-8h | ❌ |

**Operations MVP estimate: ~30-45h**.

### Content (без которого MVP пустой)

| Что | Artifact / code | Effort | Status |
|---|---|---|---|
| 17 missing task packs | PRD-006 Waves 1+2+3 | 120-150h | 🟡 PRD-006 draft есть |
| Methodology page rendered | Lift из `docs/02-methodology/` | 4-6h | ✅ docs exist |
| Blog seed posts (3-5) | `apps/site/content/blog/*.mdx` | 30-60h | ❌ marketing scope |
| Domain pollmevals.com | DNS purchase ($10/год) | 1h | ❌ **dd.md open Q#4** |
| OSS repo organization | github.com/pollmevals/* OR keep monorepo | 2-4h decision | 🟡 currently monorepo |

**Content MVP estimate: ~155-225h** (depends на task authoring approach).

### Missing forgeplan artifacts (от NOTE-005)

| Artifact | Closes gap | Status |
|---|---|---|
| **PRD-007** "Drift detection + alerting v0.2" | NOTE-005 Section F (drift) | ❌ — NOTE-006 has policy; impl PRD needed |
| **NOTE-008** "Legal + disclosure policy v0.1" | NOTE-005 Section J | ❌ |
| **RFC-003** "Artifact onboarding workflow v0.1" | NOTE-005 Section K | ❌ |
| **PRD-008** "Geo-aware latency v0.2 — 4-region workers" | NOTE-005 Section L | ❌ |
| **DB migration `0002_judges_calibration_votes`** | NOTE-005 Section H (3 missing tables) | ❌ |
| **EVID for SPEC-002 validation** | This SPEC validation | ❌ — when frontend ships + Postgres matches contract |

### Total effort estimate to MVP

```
Frontend       60-100h
Backend API    36-58h
Operations     30-45h
Content        155-225h  (dominated by 17 task authoring)
─────────────────────
Total          281-428h  →  3-4 months solo full-time (per dd.md MVP estimate)
```

Reduce content scope (e.g. 8 high-impact tasks instead of 17): ~140-280h → 2-3 months.

## Success criteria for SPEC-002 itself

- SC-1: All P0 pages have unambiguous AC (this doc — ✅)
- SC-2: Data flow diagram matches Postgres schema + R2 paths (✅ aligns SPEC-001)
- SC-3: CJM identifies exact pages each persona touches (✅)
- SC-4: Gap analysis lists effort estimates (h) per missing item (✅)
- SC-5: All missing artifact slots predicted (PRD-007, NOTE-008, RFC-003, PRD-008, DB migration) — ✅
- SC-6: API contracts defined для P0 endpoints (✅ — `/api/v1/{leaderboards,models,runs,tasks,methodology}`)

## Related Artifacts

- `docs/old/dd.md` sections 1-12 — original product spec seed (Eli + consultant 2026-05-23)
- `docs/01-vision/00-executive-vision.md` — frozen v0.1.0 vision statement
- NOTE-005 — coverage matrix (this SPEC closes Section G site pages partial)
- PRD-001 — smoke run base (informs)
- PRD-002 — judge methodology
- PRD-004 (draft) — public leaderboard MVP — **this SPEC refines body**
- PRD-006 (draft) — tasks catalog expansion (content для tasks pages)
- ADR-002 — reproducibility / immutability (drives `/runs/[hash]` AC)
- ADR-006 — 14-model adoption (drives `/models/[slug]` filter)
- NOTE-006 — anti-gaming policy (drives gold publication delay для `/tasks/[slug]`)
- SPEC-001 — manifest schema (data source для `/runs/[hash]`)

## Out of Scope

- Implementation code — этот SPEC только contract / acceptance criteria
- Detailed component design — frontend team's call given AC
- Multilingual UI — English only v0.1
- Real-time WebSocket updates — SSG + 10-min cache acceptable для weekly cadence

## Rollback Plan

- Если CJM proves wrong (after first user research): revise sections "Personas" + "CJM" + "Per-page AC" — SPEC bumps к v0.2
- Если frontend tech (Next.js) changes: rollback к Astro / vanilla SSG, AC unchanged
- Если P0 priority wrong: re-prioritize в SPEC v0.2 без changing AC contracts

