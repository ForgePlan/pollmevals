# Gold files for doc_01_cli_readme

This directory documents the expected executable gold pack.

Required files depend on task type.

For TypeScript coding tasks:

```text
gold/
  solution.ts or solution.tsx
  tests.spec.ts or tests.spec.tsx
  package.json
  tsconfig.json
  evaluator.sh
  calibration/
    perfect.ts
    good.ts
    mediocre.ts
    poor.ts
    broken.ts
```

For documentation tasks:

```text
gold/
  README.gold.md
  README.good.md
  README.mediocre.md
  README.poor.md
  README.broken.md
  evaluator.py
```

Activation rule: do not include the task in a public run until gold and evaluator files are implemented and pass quality gates.
