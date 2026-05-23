# 12 — Scoring Contract

## Global scoring principle

Every final score is normalized to 0–10.

Each task category defines its own scoring components, but all component values must be machine-readable and stored in `automatic_metrics_json` or `rubric_scores_json`.

## Coding task formula

```text
final_score_01 =
  0.40 * correctness +
  0.15 * coverage +
  0.10 * complexity_score +
  0.10 * lint_score +
  0.10 * type_safety_score +
  0.15 * pattern_match_score

final_score_10 = final_score_01 * 10
```

## Documentation task formula

Criteria:

- structural completeness;
- factual accuracy;
- clarity;
- actionability;
- consistency.

Final documentation score is the median judge score per criterion, averaged across criteria.

## Code review task formula

```text
final_score_01 =
  0.40 * recall +
  0.30 * precision +
  0.20 * severity_match +
  0.10 * fix_quality
```

## Aggregation

For leaderboards:

- aggregate per model;
- aggregate per stack;
- aggregate per task category;
- show mean, std, n, 95% bootstrap CI;
- never hide variance;
- show cost and latency next to quality.

## Negative result rule

If difference between two stacks is smaller than variance or confidence intervals overlap materially, conclusion must be:

> No statistically meaningful difference.

Do not market tiny deltas as wins.

## Pareto rule

A stack is Pareto-dominated if another stack has both:

- higher or equal quality;
- lower or equal cost;
- with at least one strict improvement.

Pareto charts must show uncertainty intervals.
