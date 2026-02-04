# Промпт для анализа графиков ЯМР (JSON-ответ)

В `analyze_graphics_llm.py` используется промпт, который просит модель вернуть **только валидный JSON-массив** без markdown. Каждый элемент массива описывает один график на странице.

## Формат ответа (пример)

```json
[
  {
    "graph_id": 1,
    "header_data": {
      "full_text": "Образец № 3 к Заключению № 11366; Индекс кристалличности = 0.73297; Протонная плотность = 0.25920",
      "structured_metrics": {
        "sample_reference": "Образец № 3 к Заключению № 11366",
        "crystallinity_index": 0.73297,
        "proton_density": 0.25920
      }
    },
    "graph_statistics": {
      "axes": {
        "y_axis": {
          "label": "Интенсивность, %",
          "visible_min": -40,
          "visible_max": 37,
          "step_interval": 9
        },
        "x_axis": {
          "label": "Время, мкс",
          "visible_min": 0,
          "visible_max": 405,
          "step_interval": 15
        }
      },
      "visible_tabs": ["NMR Signal", "Results Graph", "Code"]
    },
    "caption_data": {
      "illustration_number": "№155",
      "full_text": "Иллюстрация №155. Изображение одного из ЯМР участков...",
      "structured_details": {
        "object_type": "ЯМР участок исследуемых штрихов",
        "source_item": "оттиск круглой мастичной печати ПАО «Московский Индустриальный банк»",
        "investigation_object": "Объект №12",
        "condition": "при третьем проколе"
      }
    }
  },
  { "graph_id": 2, ... }
]
```

Результаты сохраняются в `data/graphics_llm_descriptions.json`: для каждой страницы поле `graphs` содержит распарсенный массив (если ответ удалось разобрать как JSON).
