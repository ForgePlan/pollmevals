# 02 — Product Vision

## Vision statement

POLLMEVALS becomes the evidence layer for choosing LLM stacks in production.

It measures complete working configurations rather than isolated models:

```text
model + agent CLI + system prompt + tools + skills + memory + validator + region + cost
```

## Product promise

Для пользователя продукт должен отвечать так:

> Для backend/security задач в TypeScript при бюджете до $X/task и регионе EU-Central лучший Pareto stack сейчас: Claude Sonnet + Claude Code + skills + test validator. Локальный Qwen stack дешевле в N раз, но имеет меньший recall на code review задачах.

## What the product must prove

1. Scaffolding даёт измеримый lift на сложных задачах.
2. Этот lift зависит от категории задачи.
3. Cost-per-correct-answer важнее, чем цена за миллион токенов.
4. Region-aware latency меняет UX и выбор provider’а.
5. LLM judge без calibration и self-exclusion недостаточно надёжен.
6. Reproducibility и artifact-level audit делают leaderboard credible.

## What POLLMEVALS is not

- Не Chatbot Arena: не human preference для general chat.
- Не Artificial Analysis: не только speed/cost/intelligence для голых моделей.
- Не SWE-bench clone: использует engineering tasks, но оценивает весь stack.
- Не pure academic benchmark: cadence быстрее, цель — practical decision support.
- Не enterprise consulting platform на старте: сначала open research credibility.

## Positioning language

### Short

Stack-level evals for people who actually ship with LLMs.

### Russian

POLLMEVALS показывает, какой LLM-стек реально работает в production-задачах: с учётом обвязки, стоимости, latency, стабильности и воспроизводимости.

### Website hero

**Stop choosing models. Start choosing stacks.**

Compare LLM stacks by task quality, cost-per-correct-answer, latency by region, reproducibility, and scaffold lift.
