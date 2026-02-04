# Анализ графиков ЯМР для проверки K2/K1 и L2/L1

Графики в `graphics_without_coverage.pdf` — сырые данные (спад ССИ). По ним считаются K1, K2, Pr1, Pr2. Проверка по графикам: подогнаны ли отношения.

## Шаги

### 1. Извлечь страницы в PNG
```bash
pip install pymupdf   # или в venv: .venv/bin/pip install pymupdf
python scripts/extract_graphics_pages.py   # или .venv/bin/python scripts/...
```
Появится `data/graphics_pages/` с page_001.png … page_078.png.

### 2. Проверка на дубликаты
```bash
python scripts/graphics_duplicate_check.py
```
Результат: `data/graphics_duplicates_report.txt`.

### 3. Анализ графиков через LLM (vision) — основной способ проверки
Хэш страниц из п. 2 из‑за схожести «тонкие линии на тёмном фоне» даёт ложное срабатывание; реальные отличия кривых и индексов по нему не оценить. Используйте LLM.

```bash
export ELIZA_TOKEN="ваш_токен"   # как в api_example.py
python scripts/analyze_graphics_llm.py        # все 78 страниц (или --pages 1,5,10 или --sample 10)
python scripts/summarize_llm_graphics.py       # сводка по ответам
```

Результаты: `data/graphics_llm_descriptions.json`, `data/graphics_llm_summary.txt`. Логика вызова API — в `scripts/api_example.py`; при необходимости подставьте другой endpoint/модель в `analyze_graphics_llm.py`.
