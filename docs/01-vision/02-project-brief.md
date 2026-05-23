# 01 — Project Brief

## One-liner

**POLLMEVALS** — открытая evidence-based платформа для выбора production LLM-стека под конкретные engineering-задачи.

Она отвечает не на вопрос “какая модель умнее?”, а на вопрос:

> Какая комбинация model + agent CLI + tools + skills + memory + validator + region + budget лучше решает задачу класса X?

## Категория

POLLMEVALS находится на пересечении:

- LLM evaluation;
- agentic workflow evaluation;
- software engineering benchmarks;
- cost/latency analytics;
- reproducible research infrastructure;
- applied AI engineering decision support.

## Главный тезис

Обычные leaderboard’ы сравнивают голые модели. Практики же покупают не модель, а рабочий контур вокруг неё: агент, правила, память, инструменты, validator loop, запуск тестов, стоимость и latency.

POLLMEVALS делает этот контур измеримым.

## Главный insight

Дешёвая или локальная модель с правильной обвязкой может выигрывать у дорогой модели без обвязки на конкретном классе задач.

## Первые пользователи

| Persona | Что хочет |
|---|---|
| Engineering lead | выбрать стек для команды и защитить решение перед CTO/finance/security |
| Indie founder | понять, когда локальная модель + обвязка достаточно хороши |
| Researcher / analyst | получить raw data, reproducibility, confidence intervals |
| Model / agent vendor | честно сравнить себя с альтернативами |

## MVP definition

Первый реальный MVP — не сайт, а воспроизводимый eval-run:

- 3 задачи;
- 5 моделей;
- 3–5 seeds;
- автоматические метрики;
- artifact store;
- run manifest;
- публикация methodology post.

Judge panel и scaffolding ablation добавляются после того, как deterministic pipeline стабилен.
