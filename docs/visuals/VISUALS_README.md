# Visuals

Все визуализации которые мы делали в чате, переэкспортированы как standalone HTML/SVG файлы. Можно открыть напрямую в браузере или встроить в блог.

## Список

| Файл | Описание |
|---|---|
| `01-radar-example.html` | Пример радар-чарта моделей по 12 осям. Иллюстративные данные. |
| `02-ablation-bars.html` | Stacked bar chart "что даёт каждый слой обвязки". Главный график серии. |
| `03-roadmap-5-phases.svg` | Структура серии: 5 фаз исследования. |
| `04-competitive-landscape.html` | Quadrant chart конкурентов с пустой нишей POLLMEVALS. |
| `05-site-ia.svg` | Информационная архитектура сайта POLLMEVALS. |

## Использование

Все HTML файлы — самостоятельные, открываются в любом браузере, не требуют сервера. Chart.js подгружается с CDN.

Для **встраивания в блог:**
- WordPress / Ghost: используй `<iframe>` или extract SVG
- Static site (Astro, Next.js): import как components
- Telegram / Discord: сделай скриншот (или Lottie если хочется анимацию)

## Что улучшить для финальной версии в продакшен

Эти примеры — **draft из чата**. Для production версии:

1. **Заменить mock data на реальные результаты** из weekly run
2. **Добавить confidence intervals** (shaded zones на радаре)
3. **Интерактивные tooltips** с raw output ссылкой
4. **Dark/light mode auto-switch** (уже есть в HTML файлах)
5. **Mobile responsiveness** check
6. **Accessibility** — proper aria-labels, keyboard nav

## Source code

Все эти файлы — Chart.js + vanilla HTML / SVG. Никаких build-tools. Легко поддерживать.

Если переписывать на React — будут отдельные компоненты в `pollmevals/site` repo.
