# Prompt for fe_01_multistep_form

The canonical prompt is defined in `task.yaml` under `prompt_template`.

When creating the executable benchmark pack, render the prompt from:

1. `description`;
2. task-specific constraints;
3. installed dependency list;
4. output-only instruction;
5. evaluator expectations.

The final model prompt must avoid exposing gold solution, hidden tests, judge rubric internals or calibration labels.
