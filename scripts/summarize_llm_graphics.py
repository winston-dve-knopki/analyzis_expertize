#!/usr/bin/env python3
"""
Сводка по данным LLM-анализа графиков (data/graphics_llm/page_XXX.json) и валидация
вычислений давности D (месяцы) по методологии.

Методология (из parse_calculations / deep_analysis):
  G1 = K2/K1 + P2/P1
  G2 = L2/L1 + R2/R1
  G  = G2 - G1
  D (расчёт в PDF)   = G1 / G
  D (по методологии) = (G2 - 2) / G   при Δt = 1 месяц

Из JSON по каждому графику есть: crystallinity_index (K), proton_density (P),
y_metrics_max: red, blue, green. Сопоставляем блоки расчётов с парами графиков по (K1, K2),
проверяем G1 по данным с графиков и при наличии всех полей — D.
"""
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent
GRAPHICS_LLM_DIR = PROJECT_ROOT / "data" / "graphics_llm"
CALC_JSON = PROJECT_ROOT / "data" / "calculations_verified.json"
OUT_REPORT = PROJECT_ROOT / "data" / "graphics_llm_summary.txt"

PAGE_FILE_PATTERN = re.compile(r"^page_(\d+)\.json$")
TOL_K = 0.002  # допуск при сопоставлении K
TOL_G1 = 0.02  # относительный допуск для G1
TOL_D = 0.5    # абсолютный допуск для D (мес.)


def _safe_float(x: Any) -> Optional[float]:
    if x is None:
        return None
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def load_page_results() -> Dict[int, dict]:
    """Загрузить все page_XXX.json из data/graphics_llm."""
    data = {}
    if not GRAPHICS_LLM_DIR.exists():
        return data
    for p in GRAPHICS_LLM_DIR.iterdir():
        if not p.is_file():
            continue
        m = PAGE_FILE_PATTERN.match(p.name)
        if not m:
            continue
        page_num = int(m.group(1))
        try:
            with open(p, encoding="utf-8") as f:
                data[page_num] = json.load(f)
        except (json.JSONDecodeError, OSError):
            data[page_num] = {"error": f"Не удалось прочитать {p.name}"}
    return data


def extract_graphs_from_pages(pages_data: Dict[int, dict]) -> List[dict]:
    """Собрать плоский список графиков: каждый элемент — page, graph_id, K, P, red, blue, green."""
    graphs = []
    for page in sorted(pages_data.keys()):
        v = pages_data[page]
        if "error" in v or "graphs" not in v:
            continue
        for g in v["graphs"]:
            h = g.get("header_data", {}).get("structured_metrics", {})
            s = g.get("graph_statistics", {})
            ym = s.get("y_metrics_max") or {}
            graphs.append({
                "page": page,
                "graph_id": g.get("graph_id"),
                "K": _safe_float(h.get("crystallinity_index")),
                "P": _safe_float(h.get("proton_density")),
                "red": _safe_float(ym.get("red")),
                "blue": _safe_float(ym.get("blue")),
                "green": _safe_float(ym.get("green")),
            })
    return graphs


def get_graphs_by_page(graphs: List[dict]) -> Dict[int, List[dict]]:
    """Сгруппировать графики по номеру страницы (page)."""
    by_page: Dict[int, List[dict]] = {}
    for g in graphs:
        p = g.get("page")
        if p is not None:
            by_page.setdefault(p, []).append(g)
    for p in by_page:
        by_page[p].sort(key=lambda x: (x.get("graph_id") or 0))
    return by_page


def find_graph_pair_for_block(
    block: dict, graphs: List[dict], by_page: Dict[int, List[dict]]
) -> Optional[Tuple[dict, dict]]:
    """
    Найти пару графиков для блока.
    1) Если block_index совпадает с номером страницы и на странице ровно 2 графика — берём их.
    2) Иначе ищем по (K1, K2) среди всех графиков.
    """
    bidx = block.get("block_index")
    k1 = block.get("K1")
    k2 = block.get("K2")

    # Страница = блок: на странице N два графика → образец 1 и образец 2 для блока N
    if bidx is not None and by_page.get(bidx) and len(by_page[bidx]) >= 2:
        two = by_page[bidx][:2]
        return (two[0], two[1])

    if k1 is None or k2 is None:
        return None
    best = None
    best_err = float("inf")
    for i, g1 in enumerate(graphs):
        for g2 in graphs[i + 1 :]:
            if g1["K"] is None or g2["K"] is None:
                continue
            err1 = (g1["K"] - k1) ** 2 + (g2["K"] - k2) ** 2
            err2 = (g2["K"] - k1) ** 2 + (g1["K"] - k2) ** 2
            err = min(err1, err2)
            if err < best_err:
                best_err = err
                if err1 <= err2:
                    best = (g1, g2)
                else:
                    best = (g2, g1)
    if best is None or best_err > TOL_K ** 2 * 2:
        return None
    return best


def compute_G1_from_graphs(g1: dict, g2: dict) -> Optional[float]:
    """G1 = K2/K1 + P2/P1. Первый график = образец 1 (K1, P1), второй = образец 2 (K2, P2)."""
    k1, p1 = g1.get("K"), g1.get("P")
    k2, p2 = g2.get("K"), g2.get("P")
    if k1 is None or k2 is None or p1 is None or p2 is None or k1 <= 0 or p1 <= 0:
        return None
    return k2 / k1 + p2 / p1


def compute_G2_from_graphs_assumed(g1: dict, g2: dict) -> Optional[float]:
    """
    G2 = L2/L1 + R2/R1. В JSON нет явных L, R.
    Предположение: L = proton_density (P), R = blue max (интенсивность синей кривой).
    Если blue нет — пробуем red. Результат помечается как предположительный.
    """
    p1, p2 = g1.get("P"), g2.get("P")
    r1 = g1.get("blue") if g1.get("blue") is not None else g1.get("red")
    r2 = g2.get("blue") if g2.get("blue") is not None else g2.get("red")
    if p1 is None or p2 is None or p1 <= 0:
        return None
    if r1 is None or r2 is None or r1 <= 0:
        return None
    return p2 / p1 + r2 / r1


def main() -> int:
    pages_data = load_page_results()
    if not pages_data:
        print("Нет файлов data/graphics_llm/page_XXX.json. Сначала: python scripts/analyze_graphics_llm.py")
        return 1

    graphs = extract_graphs_from_pages(pages_data)
    if not graphs:
        print("Нет распарсенных графиков в JSON.")
        return 1

    by_page = get_graphs_by_page(graphs)

    lines = [
        "=== Сводка по анализу графиков ЯМР (LLM) и валидация расчёта давности D ===",
        "",
        f"Страниц с данными: {len(pages_data)}, всего графиков: {len(graphs)}",
        "",
    ]

    # Загружаем верифицированные расчёты
    if not CALC_JSON.exists():
        lines.append("Файл data/calculations_verified.json не найден. Запустите scripts/parse_calculations.py")
        lines.append("")
        report = "\n".join(lines)
        with open(OUT_REPORT, "w", encoding="utf-8") as f:
            f.write(report)
        print(report)
        return 0

    with open(CALC_JSON, encoding="utf-8") as f:
        calc = json.load(f)
    blocks = calc.get("blocks", [])

    # Сопоставление блоков с графиками и проверка G1, D
    lines.append("--- Методология ---")
    lines.append("  G1 = K2/K1 + P2/P1,  G2 = L2/L1 + R2/R1,  G = G2 - G1")
    lines.append("  D (расчёт в PDF)   = G1 / G")
    lines.append("  D (по методологии) = (G2 - 2) / G  [мес.]")
    lines.append("  Из графиков берём: K, P = crystallinity_index, proton_density; для G2 используем предположение L=P, R=blue (см. ниже).")
    lines.append("")

    matched = 0
    g1_ok = 0
    d_ok_calc = 0
    d_ok_met = 0
    details = []

    for b in blocks:
        bidx = b.get("block_index")
        g1_pdf = b.get("G1")
        g2_pdf = b.get("G2")
        g_pdf = b.get("G")
        d_pdf = b.get("D")
        pair = find_graph_pair_for_block(b, graphs, by_page)
        if pair is None:
            details.append((bidx, None, None, None, None, None, "нет пары графиков по K1,K2"))
            continue
        g1_gr, g2_gr = pair
        matched += 1

        G1_from_graphs = compute_G1_from_graphs(g1_gr, g2_gr)
        G2_from_graphs = compute_G2_from_graphs_assumed(g1_gr, g2_gr)
        ok_g1 = False
        D_from_graphs_calc = None
        D_from_graphs_met = None
        msg = ""

        if G1_from_graphs is not None and g1_pdf is not None and g1_pdf > 0:
            rel = abs(G1_from_graphs - g1_pdf) / g1_pdf
            ok_g1 = rel <= TOL_G1
            if ok_g1:
                g1_ok += 1
            msg = f"G1_граф={G1_from_graphs:.4f} vs G1_PDF={g1_pdf:.4f}  {'OK' if ok_g1 else 'расхождение'}"

        if G2_from_graphs is not None and G1_from_graphs is not None:
            G_from_graphs = G2_from_graphs - G1_from_graphs
            if G_from_graphs > 1e-9:
                D_from_graphs_calc = G1_from_graphs / G_from_graphs
                D_from_graphs_met = (G2_from_graphs - 2.0) / G_from_graphs
                if d_pdf is not None:
                    if abs(D_from_graphs_calc - d_pdf) <= TOL_D:
                        d_ok_calc += 1
                    if abs(D_from_graphs_met - d_pdf) <= TOL_D:
                        d_ok_met += 1
                msg += f"  D_граф(calc)={D_from_graphs_calc:.2f}  D_граф(met)={D_from_graphs_met:.2f}  D_PDF={d_pdf}"
        else:
            msg += "  (G2 по графикам не вычислить: нет L,R или blue/red)"

        details.append((bidx, G1_from_graphs, D_from_graphs_calc, D_from_graphs_met, d_pdf, ok_g1, msg))

    lines.append("--- Сопоставление блоков с графиками и проверка G1, D ---")
    lines.append(f"  Блоков в расчётах: {len(blocks)}, подходящих пар графиков по (K1,K2): {matched}")
    lines.append(f"  Из них G1 (графы vs PDF) совпадает: {g1_ok}")
    lines.append(f"  D по формуле расчёта (G1/G) совпадает с PDF: {d_ok_calc} (при допуске ±{TOL_D} мес.)")
    lines.append(f"  D по формуле методологии ((G2-2)/G) совпадает с PDF: {d_ok_met}")
    lines.append("")
    lines.append("  Примечание: G2 и D по графикам считаются с предположением L=proton_density, R=blue_max;")
    lines.append("  если это не соответствует методике, расхождения не означают ошибку в расчётах.")
    lines.append("")

    # Детали по первым 20 блокам и блокам с расхождениями
    lines.append("--- Примеры (блок, G1_граф, D_граф(calc), D_граф(met), D_PDF, статус) ---")
    for bidx, G1g, Dcg, Dmg, Dpdf, ok_g1, msg in details[:20]:
        if msg:
            lines.append(f"  Блок {bidx}: {msg}")
    if len(details) > 20:
        lines.append(f"  ... и ещё {len(details) - 20} блоков.")
    lines.append("")

    # Уникальность описаний (как раньше)
    contents = []
    for p in sorted(pages_data.keys()):
        v = pages_data[p]
        if "error" in v:
            contents.append((p, f"[ошибка: {v['error']}]"))
        else:
            contents.append((p, (v.get("content") or "").strip()))
    by_len = {}
    for p, t in contents:
        key = (len(t), t[:200] if len(t) >= 200 else t)
        by_len.setdefault(key, []).append(p)
    lines.append("--- Уникальность текстовых описаний по страницам ---")
    if len(by_len) == len(contents):
        lines.append("  Все описания различаются.")
    else:
        groups = [pg for pg in by_len.values() if len(pg) > 1]
        for g in sorted(groups, key=lambda x: -len(x))[:10]:
            lines.append(f"  Одинаковое описание: страницы {g}")
    lines.append("")
    lines.append("Полные данные: data/graphics_llm/page_XXX.json")
    lines.append("")

    report = "\n".join(lines)
    with open(OUT_REPORT, "w", encoding="utf-8") as f:
        f.write(report)
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
