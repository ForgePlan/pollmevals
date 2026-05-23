# Scoring policy v0.1.0

## Coding tasks

```text
final_score_01 =
  0.40 * correctness +
  0.15 * test_coverage +
  0.10 * complexity_score +
  0.10 * lint_score +
  0.10 * type_safety_score +
  0.15 * judge_panel_pattern_score

final_score_10 = final_score_01 * 10
```

## Documentation tasks

Criteria:

- structural completeness
- factual accuracy
- clarity
- actionability
- consistency

For each criterion, take the median score across judges. Final score is the mean of criterion medians.

## Review tasks

```text
final_score_01 =
  0.40 * recall +
  0.30 * precision +
  0.20 * severity_match +
  0.10 * fix_quality
```

## Aggregate metrics

Aggregate by category:

- mean score
- standard deviation
- bootstrap 95% confidence interval
- number of evals
- cost per correct answer
- total tokens
- p50/p95 latency

## Negative result rule

If confidence intervals overlap materially and effect size is below threshold, the public conclusion must be `no meaningful difference`.
