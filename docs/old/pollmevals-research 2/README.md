# POLLMEVALS — research archive

Архив всего что мы обсудили за серию итераций: от первоначальной задачи "локально гонять бенчмарки" до полного продуктового видения **POLLMEVALS** — платформы scaffolding evaluation с panel of LLM judges.

## Что внутри

| Файл | О чём |
|---|---|
| `00-MASTER.md` | Один длинный документ — всё в одном файле, для linear read |
| `01-problem-vision.md` | Какую задачу решаем, целевые юзеры, UVP |
| `02-methodology.md` | Scaffolding L0–L8, panel of judges, biases, statistical rigor |
| `03-experiment-design.md` | 5 фаз исследования, пул из 14 моделей, 20 задач, scoring |
| `04-infrastructure.md` | Inspect AI + LiteLLM + Cerebras + Runpod + OpenRouter |
| `05-product-spec.md` | POLLMEVALS PRD: проблема, фишки, юзеры |
| `06-site-architecture.md` | IA сайта, страницы, data model, eval pipeline |
| `07-onboarding-flows.md` | Как добавляем модель, стек, задачу |
| `08-must-consider.md` | Reproducibility, security, legal, anti-gaming, disclosures |
| `09-business-model.md` | Persona, монетизация, tiers |
| `10-competitive-landscape.md` | Конкуренты: Arena, AA, BenchLM, SEAL — твоя ниша |
| `11-roadmap.md` | MVP → v0.2 → v0.3 → v1.0 → v2.0 |
| `12-next-steps.md` | Что делать прямо сейчас, open questions |
| `examples/litellm-config.yaml` | Стартовый LiteLLM конфиг с моделями |
| `examples/inspect-task.yaml` | Пример yaml-спеки задачи для Inspect AI |
| `examples/scoring-formulas.md` | Конкретные формулы scoring по типам задач |
| `visuals/` | HTML/SVG версии визуалов которые делали в чате |

## Как читать

**Линейно от и до:** открой `00-MASTER.md` — там всё в одном.

**Тематически:** начни с `01-problem-vision.md` → `05-product-spec.md` → `12-next-steps.md`. Это product perspective.

**Технически:** `02-methodology.md` → `03-experiment-design.md` → `04-infrastructure.md` → `06-site-architecture.md`. Это implementation.

## Версии

Это **v0.1**, draft. После твоего ревью пойдём в v0.2 — конкретные YAML-спеки 3 первых задач + работающий pipeline.

---

Сгенерировано по итогам серии итераций. Все идеи и решения зафиксированы в decision log внутри `12-next-steps.md`.
