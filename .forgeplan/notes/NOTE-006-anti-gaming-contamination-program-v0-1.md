---
depth: standard
id: NOTE-006
kind: note
last_modified_at: 2026-05-24T23:10:51.673631+00:00
last_modified_by: claude-code/2.1.150
links:
- target: NOTE-005
  relation: refines
- target: PRD-003
  relation: informs
- target: PRD-002
  relation: informs
status: draft
title: Anti-gaming + contamination program v0.1
---

# NOTE-006: Anti-gaming + contamination program v0.1

> **Note**: this artifact was predicted NOTE-007 in NOTE-005 Section I but was assigned NOTE-006 at creation time (sequential numbering). NOTE-005 Section I should be updated to point at NOTE-006 on next revision.

## Context

POLLMEVALS publishes results публично — это creates incentives для:

1. **Vendors optimize модели на public tasks** — training data contamination is a known failure mode (LiveBench documents it explicitly; HELM 2.x addresses it via held-out portions).
2. **Vendor pressure** — when a flagship model scores low, vendors push back on methodology; without anti-gaming infra, pressure становится political rather than statistical.
3. **Closed-API drift** — vendor changes model "за кулисами" даже под same version tag (Claude / GPT / Gemini all do this; documented в `docs/old/dd.md` line 1698).

Без anti-gaming program — leaderboard теряет credibility за 6-12 months после launch. Это closes NOTE-005 Section I gap (3 items: model drift detection, contamination detection, anti-gaming held-out set).

Source spec: `docs/old/dd.md` lines 1698-1710 (Eli's original требование).

---

## Three pillars

### Pillar 1 — Contamination detection

Periodic check that public tasks НЕ leaked into training data.

- Each task имеет **content hash** (sha256 of `task.yaml` + prompt template + evaluator script, computed at task-pack publish time)
- **Monthly cadence**: search GitHub Code Search + Stack Overflow + arxiv abstracts + общие public datasets (RedPajama, The Stack v2, Common Crawl WET samples) для task fragments
- **Similarity threshold**: if any hit found с >70% n-gram overlap (3-grams, normalised whitespace) → task flagged contaminated
- **Outcome**: contaminated task **retired** (NOT modified — per dd.md "Task versioning") + replaced + EVID-NNN with finding
- **Implementation candidate** (out of scope for this NOTE): `infra/scripts/check_contamination.py` (run weekly через cron); fed to future PRD-007 "Drift detection + alerting"

### Pillar 2 — Held-out anti-gaming set

20% задач (4 из 20 в v0.1) — **never published**, never в OSS репо.

- **Rotation**: replaced ежемесячно (replaced after 1 month, archived in private store)
- **Use**: validation only — публичная версия leaderboard показывает full grid, но held-out scores summarized as **ratio** `held_out_score / public_score` per model+stack
- **Flag rule**: if model's public-task score >> held-out score (ratio < 0.85) → flag suspicious (likely contamination/overfitting) + public note in `/changelog`
- **Storage**: encrypted в private repo `pollmevals/heldout-tasks` (separate org from public `pollmevals/core`)
- **Authoring standard**: same gold + evaluator + calibration rigor as public tasks (extra cost ~2-4h per task per month; documented as open question below)

### Pillar 3 — Model drift detection

Closed-API модели change silently. Detection:

- **Baseline**: rolling previous **12 weekly runs** per (model, task_category) pair
- **Statistic**: z-score `(current_week_score - rolling_mean) / rolling_std`
- **Trigger**: if `|z| > 2.0` per task category → flag model + public note в `/blog` + EVID-NNN with measurement
- **Implementation**: extension of weekly run pipeline (Step 10 of dd.md eval pipeline — currently marked ❌ in NOTE-005 Section F); lands inside PRD-003 weekly cadence build
- **Channel**: public RSS feed (`/changelog.xml`) + Twitter post + dedicated `/drift-alerts/<model>/<week>` page

---

## Policy decisions

- **D1 — Disclosure timing**: contamination findings published immediately в `/changelog` + Twitter / Telegram / RSS (transparency > convenience). No embargo, no vendor preview. Rationale: credibility of evidence layer depends on independence from vendor pressure.
- **D2 — Retirement vs revision**: contaminated tasks **retired** (NOT modified) — preserves citation integrity per dd.md "Task versioning" rule. Replacement task gets new `slug`, NOT bumped `version` on old slug. Old eval data stays valid for its task version forever; citing papers don't get rug-pulled.
- **D3 — Held-out access**: only **maintainer (Eli)** + **1 backup** имеют access; quarterly rotation of backup; if leak detected (held-out task appears in public corpus), full held-out set rotated immediately + post-mortem EVID published.

---

## Success criteria

| ID | Criterion | Target | Measurement |
|---|---|---|---|
| SC-1 | Tasks have public content hash | 100% of tasks в `evals/task-packs/` carry `content_hash: sha256:…` в `task.yaml` frontmatter | grep + validation script in CI |
| SC-2 | Contamination check frequency | ≥1× per month (manual в v0.1; automated в v0.2+) | published EVID per month with `evidence_type: audit` |
| SC-3 | Held-out rotation | ≤30 days (max) between rotations | rotation log в private repo; quarterly summary public |
| SC-4 | Drift detection coverage | All closed-API models (Claude/GPT/Gemini/Grok) flagged when `|z| > 2.0` per task category | weekly run journal includes z-score vector; EVID-drift-<week> created on flag |
| SC-5 | Public finding integrity | 100% of contamination/drift/anti-gaming flags backed by EVID artifact linked to this NOTE | spot-audit during quarterly methodology review |

---

## Implementation timeline

- **v0.1 MVP** (this NOTE establishes policy; impl is TBD): manual contamination check (1× before public launch — gating PRD-001 → public publish transition)
- **v0.2**: automated weekly contamination check (Pillar 1) + drift detection wiring (Pillar 3) — lands as part of PRD-003 weekly cadence build
- **v0.3**: held-out set v1 (4 tasks) + monthly rotation cron — separate PRD (TBD)
- **v1.0**: encrypted private repo для held-out + 2 maintainers + audit log + quarterly external methodology review

---

## Open questions

- **OQ-1**: Who runs contamination check before v0.2 automation? Estimated **2-4h/month manual labour**; Eli solo for v0.1, but bus-factor 1 is fragile. Backup process TBD.
- **OQ-2**: Held-out task authoring cost — same gold/evaluator standard as public, but never published. Extra cost ~2-4h per task per month (4 tasks × 4h = 16h/month). Resource decision TBD; may need дискуссию about authoring budget или task licensing from external sources.
- **OQ-3**: Drift detection alert channel — RSS feed (`/changelog.xml`)? Twitter? Telegram? Dedicated blog post? Per Eli's preference; v0.2 default = RSS + Twitter, expand later.
- **OQ-4**: 12-week rolling baseline (Pillar 3) requires **12 published weekly runs before drift detection can run** — what's the cold-start protocol? Suggested: skip drift detection for weeks 1-12, publish disclaimer, switch on at week 13.
- **OQ-5**: Contamination similarity threshold (70% n-gram overlap) — calibrated to what corpus? May produce false positives on idiomatic boilerplate (e.g. JWT auth examples are inherently similar). Calibration set + threshold tuning is itself a sub-project.

---

## Cross-references

- **Source spec**: `docs/old/dd.md` lines 1698-1710 (Eli's anti-gaming requirements)
- **Closes gap**: NOTE-005 Section I (3 items: model drift, contamination detection, anti-gaming held-out)
- **Informs PRD-003** (weekly cadence) — drift detection runs inside Step 10 of dd.md eval pipeline
- **Informs PRD-002** (judges) — calibration уже addresses **judge** drift; this NOTE addresses **MODEL** drift; the two are complementary (judge drift = scoring instability; model drift = candidate instability)
- **Future PRD candidate**: PRD-007 "Drift detection + alerting" — automates Pillar 3
- **Future RFC candidate**: RFC for contamination check pipeline (Pillar 1 impl)
- **Future EVID slots**:
  - `EVID-NNN` "Contamination scan results week <X>"
  - `EVID-NNN` "Drift detection alert: model <Y> week <Z>"
  - `EVID-NNN` "Held-out vs public score ratio analysis <quarter>"

---

## How to keep this NOTE current

- Update success criteria thresholds after first 2-3 contamination scans calibrate the 70% similarity bar
- Update Pillar 3 baseline window (12 weeks) if statistical evidence shows different window size is more robust
- Resolve open questions (OQ-1..OQ-5) as decisions land; supersede this NOTE with NOTE-NNN if scope expands materially

This NOTE is **policy-level only**. Concrete implementation = future PRD-007 (drift detection + alerting) + future RFC (contamination check pipeline). Do NOT implement from this NOTE directly — it's the spec source for downstream artifacts.




