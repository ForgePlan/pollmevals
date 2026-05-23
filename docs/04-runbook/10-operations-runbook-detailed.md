# 14 — Operations Runbook

## Daily operations during MVP

- verify API health;
- verify LiteLLM proxy health;
- verify Postgres backups;
- verify R2 artifact writes;
- check failed evals;
- check spend against budget;
- check provider rate limits;
- inspect run queue length.

## Weekly run checklist

1. Freeze task snapshot.
2. Freeze model snapshot.
3. Freeze stack snapshot.
4. Capture pricing snapshot.
5. Create run manifest draft.
6. Execute smoke sanity check.
7. Start full run.
8. Monitor failures.
9. Aggregate automatic metrics.
10. Run judge phase if enabled.
11. Compute bootstrap CI and agreement metrics.
12. Publish run page.
13. Publish postmortem if failures are material.
14. Invalidate leaderboard cache.
15. Export public dataset snapshot.

## Incident classes

| Class | Example | Action |
|---|---|---|
| Provider outage | OpenRouter/Cerebras unavailable | mark evals failed or retry per policy |
| Evaluator bug | test suite wrong | supersede run, do not edit old scores |
| Cost spike | model loop or retry storm | stop run, cap spend, investigate |
| Judge drift | calibration deviation high | exclude judge or mark run experimental |
| Contamination | task appears online | retire task, create replacement |
| Security incident | sandbox escape suspicion | disable evaluator class, rotate secrets |

## Public transparency

If a public run has material errors, publish:

- what happened;
- affected run hash;
- affected tasks/models;
- whether results are withdrawn;
- replacement run hash if any;
- prevention change.
