# 06 — Operational runbook

## Local smoke run

```bash
python -m pollmevals_eval_core.demo_run --tasks evals/tasks --output artifacts
```

Expected output:

- A run hash printed to stdout.
- A manifest at `artifacts/runs/<run_hash>/manifest.json`.
- One JSON artifact per eval.

## Start local infra

```bash
cp .env.example .env
docker compose -f infra/docker-compose.dev.yml up -d
```

## Start API

```bash
cd apps/api
pnpm install
pnpm dev
```

## Start site

```bash
cd apps/site
pnpm install
pnpm dev
```

## Publication checklist

Before publishing a result:

- Run is immutable and has hash.
- All task versions are pinned.
- All model provider pricing snapshots are stored.
- All raw outputs are stored.
- All evaluator logs are stored.
- Judge self-exclusion is confirmed.
- Calibration deviation is within threshold.
- Confidence intervals are computed.
- Methodology version is linked.
- Disclosure page is updated if a conflict exists.
