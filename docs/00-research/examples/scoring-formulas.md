# Scoring Formulas

Конкретные формулы scoring по типам задач. Все нормализуются в 0-1, потом × 10 для радара.

---

## Coding tasks (backend, frontend, fullstack, db, tests, refactor)

```python
def score_coding_task(eval_result, gold, judge_scores):
    # 1. Correctness — binary
    correctness = 1.0 if all(test.passed for test in eval_result.tests) else 0.0
    
    # 2. Test coverage (only if task требует tests)
    coverage = eval_result.coverage_percent / 100  # 0-1
    
    # 3. Cyclomatic complexity ratio
    cc_solution = eval_result.cyclomatic_complexity
    cc_gold = gold.cyclomatic_complexity
    # Closer to gold = better; penalize both too simple and too complex
    cc_score = max(0, 1 - abs(cc_solution - cc_gold) / cc_gold)
    
    # 4. Linter score
    max_acceptable_issues = eval_result.loc / 20  # 1 issue per 20 LOC
    lint_issues = eval_result.lint_errors + eval_result.lint_warnings / 3
    lint_score = max(0, 1 - lint_issues / max_acceptable_issues)
    
    # 5. Type safety
    type_score = max(0, 1 - eval_result.type_errors / eval_result.loc * 10)
    
    # 6. Pattern match via panel of judges (median)
    pattern_score = sorted(judge_scores)[len(judge_scores) // 2] / 10  # median, 0-1
    
    # Weighted sum
    weights = {
        'correctness': 0.40,
        'coverage': 0.15,
        'complexity': 0.10,
        'lint': 0.10,
        'type_safety': 0.10,
        'pattern_match': 0.15,
    }
    
    final_01 = (
        weights['correctness'] * correctness +
        weights['coverage'] * coverage +
        weights['complexity'] * cc_score +
        weights['lint'] * lint_score +
        weights['type_safety'] * type_score +
        weights['pattern_match'] * pattern_score
    )
    
    return final_01 * 10  # 0-10
```

---

## Documentation tasks (README, ADR, PRD, RFC)

Для документов automatic metrics плохо работают — используем panel of judges с rubric.

```python
def score_doc_task(eval_result, gold, judge_panel_scores):
    """
    judge_panel_scores: dict[judge_id][criterion] = score 0-10
    """
    
    criteria = [
        'structural_completeness',  # все нужные секции присутствуют
        'factual_accuracy',          # нет фактических ошибок относительно gold
        'clarity',                   # понятно ли junior-разработчику
        'actionability',             # можно ли по этому работать
        'consistency',               # не противоречит ли сам себе
    ]
    
    # Median score per criterion across judges
    per_criterion_scores = {}
    for criterion in criteria:
        scores_for_criterion = [
            judge_panel_scores[judge_id][criterion]
            for judge_id in judge_panel_scores
        ]
        per_criterion_scores[criterion] = sorted(scores_for_criterion)[len(scores_for_criterion) // 2]
    
    # Equal weighting between criteria
    final = sum(per_criterion_scores.values()) / len(criteria)
    
    return final  # already 0-10


# Rubric для judges (отправляется как system prompt):
DOC_JUDGE_RUBRIC = """
You are evaluating a technical document submission against a gold reference.
You will see the submission and the gold answer. Score each criterion 0-10.

CRITERIA:

1. structural_completeness (0-10)
   - Are all expected sections present?
   - 10 = perfect structure, 0 = missing major sections

2. factual_accuracy (0-10)
   - Are facts in submission consistent with gold answer?
   - 10 = no errors, 0 = many factual errors

3. clarity (0-10)
   - Would a junior developer understand this?
   - 10 = crystal clear, 0 = confusing

4. actionability (0-10)
   - Can someone act on this document?
   - 10 = immediately actionable, 0 = vague

5. consistency (0-10)
   - Does the document contradict itself?
   - 10 = fully consistent, 0 = many contradictions

DO NOT:
- Score based on length (long != better)
- Score based on formatting style
- Be influenced by who you think wrote it
- Add new criteria

Output ONLY JSON:
{
  "structural_completeness": <int>,
  "factual_accuracy": <int>,
  "clarity": <int>,
  "actionability": <int>,
  "consistency": <int>,
  "reasoning": "<brief 2-3 sentence reasoning>"
}
"""
```

---

## Code review tasks

```python
def score_review_task(eval_result, ground_truth_bugs):
    """
    eval_result.found_bugs: list of {location, severity, description}
    ground_truth_bugs: list of bugs with severity ('critical' | 'major' | 'minor')
    """
    
    found = set((b.location, b.severity) for b in eval_result.found_bugs)
    truth = set((b.location, b.severity) for b in ground_truth_bugs)
    
    # 1. Recall — какой % реальных багов нашёл
    if len(truth) == 0:
        recall = 1.0
    else:
        true_positives = found & truth
        recall = len(true_positives) / len(truth)
    
    # 2. Precision — из найденных, % реально багов
    if len(found) == 0:
        precision = 0.0
    else:
        true_positives = found & truth
        precision = len(true_positives) / len(found)
    
    # 3. Severity match — правильно ли оценил критичность
    matched_severity = 0
    for bug in eval_result.found_bugs:
        truth_bug = next((t for t in ground_truth_bugs if t.location == bug.location), None)
        if truth_bug and truth_bug.severity == bug.severity:
            matched_severity += 1
    severity_score = matched_severity / max(len(ground_truth_bugs), 1)
    
    # 4. Fix quality (LLM-judge)
    fix_quality = judge_evaluate_proposed_fixes(eval_result.proposed_fixes)
    
    weights = {
        'recall': 0.4,
        'precision': 0.3,
        'severity_match': 0.2,
        'fix_quality': 0.1,
    }
    
    final_01 = (
        weights['recall'] * recall +
        weights['precision'] * precision +
        weights['severity_match'] * severity_score +
        weights['fix_quality'] * fix_quality / 10
    )
    
    return final_01 * 10
```

---

## Composite metric calculation для радара

После того как у нас есть `final_score` (0-10) для каждой (model, task) комбинации, агрегируем для радара:

```python
def aggregate_for_radar(all_evals):
    """
    Группирует evals по (model, task_category) и считает summary.
    """
    radar_data = {}
    
    for model in all_models:
        radar_data[model] = {}
        for category in ['backend', 'frontend', 'fullstack', 'db', 'devops', 
                         'tests', 'docs', 'review', 'refactor']:
            
            evals_for_cat = [
                e for e in all_evals 
                if e.model == model and e.task.category == category
            ]
            
            scores = [e.final_score for e in evals_for_cat]
            
            radar_data[model][category] = {
                'mean': sum(scores) / len(scores),
                'std': statistics.stdev(scores) if len(scores) > 1 else 0,
                'n_evals': len(scores),
                # Bootstrap 95% CI
                'ci_lower': bootstrap_ci_lower(scores, confidence=0.95),
                'ci_upper': bootstrap_ci_upper(scores, confidence=0.95),
            }
    
    return radar_data
```

---

## Cost-quality для Pareto scatter (Фаза 5)

```python
def compute_pareto_point(model, stack, task_category, all_evals):
    """
    Для финального scatter — точка на (cost_per_correct, quality).
    """
    evals = [
        e for e in all_evals
        if e.model == model and e.stack == stack 
        and e.task.category == task_category
    ]
    
    # Quality: mean final score
    quality = sum(e.final_score for e in evals) / len(evals)
    
    # Cost per correct answer
    total_cost = sum(e.cost_usd for e in evals)
    n_correct = sum(1 for e in evals if e.is_correct)
    cost_per_correct = total_cost / max(n_correct, 1)
    
    return {
        'x': cost_per_correct,   # $ per correct answer (lower = better)
        'y': quality,             # 0-10 (higher = better)
        'label': f"{model.name} + {stack.name}",
        'n_evals': len(evals),
        'ci_x_lower': bootstrap_ci_lower([e.cost_usd for e in evals if e.is_correct]),
        'ci_x_upper': bootstrap_ci_upper([e.cost_usd for e in evals if e.is_correct]),
        'ci_y_lower': bootstrap_ci_lower([e.final_score for e in evals]),
        'ci_y_upper': bootstrap_ci_upper([e.final_score for e in evals]),
    }
```

Pareto frontier визуально — выделить точки которые не доминируются никакой другой (где нет другой точки с одновременно меньшим x И большим y).

---

## Anchors для калибровки (Вариант Б из методологии)

Чтобы оси радара были стабильны между постами, используем **фиксированные якоря**:

```python
ANCHORS = {
    # ось: (значение_для_0, значение_для_10)
    'backend':      (0.20, 0.95),  # accuracy на be_* задачах
    'frontend':     (0.15, 0.90),
    'fullstack':    (0.10, 0.85),
    'db':           (0.25, 0.95),
    'devops':       (0.20, 0.90),
    'tests':        (0.30, 0.95),
    'docs':         (0.30, 0.95),
    'review':       (0.20, 0.85),
    'refactor':     (0.10, 0.80),
}

def normalize_to_radar(accuracy, category):
    lo, hi = ANCHORS[category]
    return max(0, min(10, 10 * (accuracy - lo) / (hi - lo)))
```

Если **state-of-the-art** улучшается значительно — обновляем anchors с announcement в `/changelog`.
