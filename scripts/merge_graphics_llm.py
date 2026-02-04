#!/usr/bin/env python3
"""
Сливает данные по графикам из graphics_llm (без покрытия) и graphics_llm_coverage (с покрытием)
в единый JSON: для каждого (page, graph_id) — K1/Pr1 из без покрытия, K2/Pr2 и log_panel_data/status_bar_data из с покрытием.

Пример запуска (первые 3 страницы):
  python scripts/merge_graphics_llm.py --pages 1,2,3
"""
import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DIR_WITHOUT = PROJECT_ROOT / "data" / "graphics_llm"
DIR_COVERAGE = PROJECT_ROOT / "data" / "graphics_llm_coverage"
OUT_JSON = PROJECT_ROOT / "data" / "graphics_merged.json"


def load_page(path: Path) -> Optional[dict]:
    if not path.exists():
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def get_graphs(data: Optional[dict]) -> List[dict]:
    if not data or "graphs" not in data:
        return []
    return data.get("graphs") or []


def merge_graph(without_graph: dict, coverage_graph: Optional[dict], page_context: Optional[dict]) -> dict:
    """Один элемент merged: без покрытия (K1, Pr1) + с покрытием (K2, Pr2, log_panel, status_bar)."""
    out = {
        "without_coverage": {
            "structured_metrics": {
                "crystallinity_index": None,
                "proton_density": None,
                "sample_reference": "",
            },
            "graph_statistics": without_graph.get("graph_statistics"),
            "caption_data": without_graph.get("caption_data"),
        },
        "with_coverage": None,
    }

    h = without_graph.get("header_data", {}).get("structured_metrics", {})
    out["without_coverage"]["structured_metrics"]["crystallinity_index"] = h.get("crystallinity_index")
    out["without_coverage"]["structured_metrics"]["proton_density"] = h.get("proton_density")
    out["without_coverage"]["structured_metrics"]["sample_reference"] = h.get("sample_reference") or ""

    if coverage_graph:
        out["with_coverage"] = {
            "structured_metrics": {
                "crystallinity_index": coverage_graph.get("header_data", {}).get("structured_metrics", {}).get("crystallinity_index"),
                "proton_density": coverage_graph.get("header_data", {}).get("structured_metrics", {}).get("proton_density"),
                "sample_reference": coverage_graph.get("header_data", {}).get("structured_metrics", {}).get("sample_reference") or "",
            },
            "log_panel_data": coverage_graph.get("log_panel_data"),
            "status_bar_data": coverage_graph.get("status_bar_data"),
            "caption_data": coverage_graph.get("caption_data"),
        }

    if page_context is not None:
        out["page_context"] = page_context

    return out


def main():
    parser = argparse.ArgumentParser(description="Слияние graphics_llm и graphics_llm_coverage в единый JSON")
    parser.add_argument("--pages", type=str, default=', '.join([str(i) for i in range(1, 65)]), help="Номера страниц через запятую (по умолчанию 1,2,3)")
    parser.add_argument("--out", type=str, default=None, help="Выходной JSON (по умолчанию data/graphics_merged.json)")
    args = parser.parse_args()

    page_numbers = [int(x.strip()) for x in args.pages.split(",")]
    out_path = Path(args.out) if args.out else OUT_JSON

    merged = {
        "source": {
            "without_coverage": str(DIR_WITHOUT),
            "with_coverage": str(DIR_COVERAGE),
        },
        "pages": [],
        "graphs": [],
    }

    for page in page_numbers:
        without_data = load_page(DIR_WITHOUT / f"page_{page:03d}.json")
        coverage_data = load_page(DIR_COVERAGE / f"page_{page:03d}.json")

        graphs_without = get_graphs(without_data)
        graphs_coverage = get_graphs(coverage_data)

        page_context = None
        if graphs_coverage and graphs_coverage[0].get("page_context"):
            page_context = graphs_coverage[0]["page_context"]

        page_entry = {"page": page, "graph_ids": []}

        for i, gw in enumerate(graphs_without):
            gid = gw.get("graph_id", i + 1)
            page_entry["graph_ids"].append(gid)
            gc = next((g for g in graphs_coverage if g.get("graph_id") == gid), None)
            merged_graph = {
                "page": page,
                "graph_id": gid,
                **merge_graph(gw, gc, page_context if i == 0 else None),
            }
            merged["graphs"].append(merged_graph)

        merged["pages"].append(page_entry)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)

    print(f"Сохранено: {out_path}")
    print(f"Страниц: {len(merged['pages'])}, всего графиков: {len(merged['graphs'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
