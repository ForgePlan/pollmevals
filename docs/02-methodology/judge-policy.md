# Judge policy v0.1.0

## Rules

1. A model does not judge itself.
2. Judges are from different model families where possible.
3. Submissions are normalized before judging.
4. The judge sees task, rubric, gold reference when allowed, and anonymous submission.
5. The judge does not see model identity, provider, stack name or cost.
6. Scores are JSON-only.
7. Median is used to aggregate judges.
8. Calibration is run before production judging.

## Bias mitigations

| Bias | Mitigation |
|---|---|
| Self-enhancement | self-judging disabled |
| Position bias | randomized ordering |
| Length bias | rubric says long is not better |
| Style bias | markdown and greetings normalized |
| Anchor bias | independent calls |
| Calibration drift | known-score calibration samples |

## Minimum publishable judge quality

- Krippendorff alpha target: >= 0.70.
- Calibration mean absolute deviation target: <= 1.5 points on 0-10 scale.
- Identification probe target: <= 30% model-origin accuracy.
