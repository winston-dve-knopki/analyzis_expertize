#!/usr/bin/env python3
"""
Анализ графиков ЯМР через LLM (vision): по каждой странице получаем описание кривых,
осей и чисел. Так можно проверить, действительно ли графики различаются между образцами
(и согласуются ли с разными K2/K1, L2/L1), в отличие от хэша страниц, который даёт
ложное срабатывание из‑за схожести «тонкие линии на тёмном фоне».
Вызов API — по логике из api_example.py (Yandex Eliza / OpenAI-совместимый).
"""
import argparse
import base64
import json
import os
import time
from pathlib import Path
from typing import Any, List, Optional
import warnings
warnings.filterwarnings("ignore")
import requests

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PAGES_DIR = PROJECT_ROOT / "data" / "graphics_pages"
OUT_DIR = PROJECT_ROOT / "data" / "graphics_llm"
API_URL = "https://api.eliza.yandex.net/openai/v1/chat/completions"
os.environ["ELIZA_TOKEN"] = 'y1__xCO5uSRpdT-ARiuKyCNuNgCfT9dyn8T_pEyXKpRdI4xPCSSwIg'
# По умолчанию gpt-4o — лучше читает числа с осей графиков; gpt-4o-mini часто даёт null для visible_min/max
MODEL = "gpt-4o"

PROMPT = """На изображении — страница с одним или двумя графиками ЯМР (спад свободной индукции, ССИ). В интерфейсе могут быть: заголовок с образцом, индексом кристалличности и протонной плотностью; сами графики с осями (время в мкс, интенсивность в % и т.п.); подпись к иллюстрации (номер, объект, тип реквизита, прокол).

Извлеки все данные, которые видишь на странице, и верни **строго один JSON-массив** без обёртки в markdown и без пояснений до/после. Каждый элемент массива — один график на странице (graph_id: 1, 2, …).

Формат каждого элемента:

{
  "graph_id": <номер графика на странице, 1 или 2>,
  "header_data": {
    "full_text": "<полный текст заголовка над графиком, если есть>",
    "structured_metrics": {
      "sample_reference": "<ссылка на образец, например «Образец № 3 к Заключению № 11366»>",
      "crystallinity_index": <число — индекс кристалличности K, если виден>,
      "proton_density": <число — протонная плотность Pr, если видна>
    }
  },
  "graph_statistics": {
    "axes": {
      "y_axis": {
        "label": "<подпись оси Y, например «Интенсивность, %»>",
        "visible_min": <число — значение на оси Y в начале шкалы>,
        "visible_max": <число — значение в конце шкалы Y>,
        "step_interval": <число — шаг между делениями, если виден; иначе null>
      },
      "x_axis": {
        "label": "<подпись оси X, например «Время, мкс»>",
        "visible_min": <число — значение на оси X в начале шкалы>,
        "visible_max": <число — значение в конце шкалы X>,
        "step_interval": <число — шаг между делениями, если виден; иначе null>
      }
    },
    "y_metrics_max": {
      "red": <число — максимальное значение по оси Y у красной кривой; null если кривой нет или не читаемо>,
      "blue": <число — максимальное значение по оси Y у синей кривой; null если нет>,
      "green": <число — максимальное значение по оси Y у зелёной кривой; null если нет>
    },
    "visible_tabs": ["<название вкладки, если видна>", ...]
  },
  "caption_data": {
    "illustration_number": "<номер иллюстрации, например «№155»>",
    "full_text": "<полный текст подписи к иллюстрации>",
    "structured_details": {
      "object_type": "<тип, например «ЯМР участок исследуемых штрихов»>",
      "source_item": "<источник, например «оттиск круглой мастичной печати ПАО …»>",
      "investigation_object": "<объект, например «Объект №12»>",
      "condition": "<условие, например «при третьем проколе»>"
    }
  }
}

Правила:
- Обязательно прочитай числа с делений осей каждого графика: visible_min и visible_max — это числа, подписанные у начала и конца оси; step_interval — шаг сетки, если подписи делений видны. null только если шкала действительно не читаема.
- На графике три метрики (кривые): красная, синяя, зелёная. В y_metrics_max укажи максимальное значение по оси Y для каждой кривой (пик или верхняя граница по шкале Y); null, если кривой нет или значение не определить.
- Если какого-то блока или поля на изображении нет — используй пустую строку "" или null для чисел.
- crystallinity_index и proton_density — только числа (float).
- visible_tabs — массив строк с названиями вкладок интерфейса, если они видны; иначе [].
- Ответ должен быть только валидным JSON-массивом, начинаться с [ и заканчиваться ]."""


def call_vision_api(image_path: Path, token: str, model: str = MODEL) -> dict:
    """Отправить изображение и промпт в API, вернуть ответ API (dict)."""
    with open(image_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("ascii")
    image_url = f"data:image/png;base64,{b64}"

    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": PROMPT},
                    {
                        "type": "image_url",
                        "image_url": {"url": image_url},
                    },
                ],
            }
        ],
    }
    headers = {
        "authorization": f"OAuth {token}",
        "content-type": "application/json",
    }
    r = requests.post(API_URL, json=payload, headers=headers, timeout=120, verify=False)
    r.raise_for_status()
    return r.json()


def parse_response_json(text: str) -> Optional[List[Any]]:
    """Из ответа модели извлечь JSON-массив (убрать обёртку ```json ... ``` при наличии)."""
    raw = text.strip()
    for prefix in ("```json\n", "```json\r\n", "```\n"):
        if raw.startswith(prefix):
            raw = raw[len(prefix):]
            break
    for suffix in ("\n```", "\r\n```"):
        if raw.endswith(suffix):
            raw = raw[: -len(suffix)]
            break
    raw = raw.strip()
    if not raw.startswith("["):
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def main():
    parser = argparse.ArgumentParser(description="Анализ графиков ЯМР через LLM (vision)")
    parser.add_argument("--pages", type=str, default=None, help="Номера страниц через запятую, например 1,2,5,10. По умолчанию — все 1..78")
    parser.add_argument("--sample", type=int, default=None, help="Взять каждую N-ю страницу (например 10)")
    parser.add_argument("--delay", type=float, default=1.0, help="Пауза между запросами (сек)")
    parser.add_argument("--force", action="store_true", help="Перезаписать уже сохранённые страницы")
    parser.add_argument("--model", type=str, default=os.getenv("ELIZA_MODEL", MODEL), help="Модель vision (по умолчанию: gpt-4o для лучшего чтения осей)")
    args = parser.parse_args()
    model = args.model or MODEL

    token = os.getenv("ELIZA_TOKEN")
    if not token:
        print("Укажите ELIZA_TOKEN в окружении (как в api_example.py).", file=__import__("sys").stderr)
        return 1

    if not PAGES_DIR.exists():
        print(f"Сначала выполните: python scripts/extract_graphics_pages.py", file=__import__("sys").stderr)
        return 1

    # Список страниц для обработки
    if args.pages:
        page_numbers = [int(x.strip()) for x in args.pages.split(",")]
    elif args.sample:
        page_numbers = list(range(1, 79))[:: args.sample]
    else:
        page_numbers = list(range(1, 79))

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    for page in page_numbers:
        out_file = OUT_DIR / f"page_{page:03d}.json"
        if out_file.exists() and not args.force:
            print(f"Пропуск страницы {page} (уже есть {out_file.name}).")
            continue
        path = PAGES_DIR / f"page_{page:03d}.png"
        if not path.exists():
            print(f"Файл не найден: {path}")
            continue
        print(f"Страница {page}...", end=" ", flush=True)
        try:
            data = call_vision_api(path, token, model)
            completion = data.get("response", data)
            text = completion["choices"][0]["message"]["content"]
            graphs = parse_response_json(text)
            payload = {
                "page": page,
                "content": text,
                "graphs": graphs,
                "model": completion.get("model", model),
                "usage": completion.get("usage") or data.get("usage"),
            }
            with open(out_file, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
            print("OK" if graphs is not None else "OK (JSON не распарсен)")
        except Exception as e:
            print(f"Ошибка: {e}")
            payload = {"page": page, "error": str(e)}
            with open(out_file, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
        time.sleep(args.delay)

    print(f"Результаты по страницам: {OUT_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
