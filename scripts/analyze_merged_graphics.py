#!/usr/bin/env python3
"""
Анализ data/graphics_merged.json: расчёт G1, G2 и давности D по обеим формулам.
K и Pr берутся только из основных полей (structured_metrics) в обоих JSON,
не из log_panel_data.structured_log_metrics.

Для страниц 1, 2, 3, 20, 21, 22 (вручную поправленный лог): проверка соответствия
лог-метрик заголовку и расчёт подразумеваемой массы m = A_short / Pr.
"""
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MERGED_JSON = PROJECT_ROOT / "data" / "graphics_merged.json"
CALC_JSON = PROJECT_ROOT / "data" / "calculations_verified.json"
OUT_REPORT = PROJECT_ROOT / "data" / "merged_graphics_analysis_report.txt"

# Страницы с вручную исправленным логом — для них проверяем расчёт K, Pr и implied mass
PAGES_WITH_FIXED_LOG = {1, 2, 3, 20, 21, 22}


def block_index_from_page_graph(page: int, graph_id: int) -> int:
    return (page - 1) * 2 + graph_id


# Допуск для сопоставления блока по K1, K2 (значения из PDF и merged могут немного отличаться)
K_MATCH_TOLERANCE = 0.001


def find_block_by_k1_k2(blocks: list, K1: float, K2: float):
    """Найти блок по ближайшим K1, K2 среди всех блоков (fallback для страниц 40+)."""
    best_block = None
    best_dist = float("inf")
    for b in blocks:
        d = abs(b["K1"] - K1) + abs(b["K2"] - K2)
        if d < best_dist:
            best_dist = d
            best_block = b
    if best_block is not None and best_dist <= K_MATCH_TOLERANCE:
        return best_block
    return None


def find_block_by_l1_l2(blocks: list, L1: float, L2: float, tolerance: float = 0.02):
    """Найти блок по L1, L2 (в merged для страниц 40+ в полях K могут быть значения L из PDF)."""
    best_block = None
    best_dist = float("inf")
    for b in blocks:
        d = abs(b["L1"] - L1) + abs(b["L2"] - L2)
        if d < best_dist:
            best_dist = d
            best_block = b
    if best_block is not None and best_dist <= tolerance:
        return best_block
    return None


def main():
    with open(MERGED_JSON, encoding="utf-8") as f:
        merged = json.load(f)
    with open(CALC_JSON, encoding="utf-8") as f:
        calc = json.load(f)
    blocks_by_idx = {b["block_index"]: b for b in calc["blocks"]}

    blocks_list = calc["blocks"]
    num_blocks = len(blocks_list)
    calc_pages = (num_blocks + 1) // 2  # 78 блоков → страницы 1–39

    lines = [
        "=== Анализ graphics_merged.json: G1, G2, давность D (только основные поля K, Pr) ===",
        "",
        f"calculations_verified.json: {num_blocks} блоков (страницы 1–{calc_pages} по 2 графика). Для страницы {calc_pages + 1}+ блок по индексу отсутствует; при совпадении по K1,K2 или по L1,L2 используется найденный блок (прим. «по K1,K2» / «по L1,L2»).",
        "",
        "Источники K и Pr: только header_data.structured_metrics (без покрытия и с покрытием).",
        "Лог-метрики (log_panel_data) для расчёта K/Pr не используются.",
        "",
        "--- 1. Формулы ---",
        "",
        "G1 = K2/K1 + Pr2/Pr1  (методология, формула 1; в calculations это G1).",
        "G2 = L2/L1 + R2/R1    (в calculations; в merged нет L, R → G2 берём из блока calculations).",
        "G = G2 − G1.",
        "D_методология = (G2 − 2) / G.   D_calculations = G1 / G.",
        "",
        "--- 2. Результаты по всем графикам (G1 из merged, G1/G2/D из блока) ---",
        "",
    ]

    rows = []
    log_check_rows = []  # для страниц 1,2,3,20,21,22

    for g in merged.get("graphs", []):
        if g.get("with_coverage") is None:
            continue
        page = g["page"]
        graph_id = g["graph_id"]
        w = g.get("without_coverage", {}).get("structured_metrics", {})
        c = g.get("with_coverage", {}).get("structured_metrics", {})
        log_metrics = (g.get("with_coverage") or {}).get("log_panel_data", {}).get("structured_log_metrics") or {}

        K1 = w.get("crystallinity_index")
        Pr1 = w.get("proton_density")
        K2 = c.get("crystallinity_index")
        Pr2 = c.get("proton_density")

        if K1 is None or Pr1 is None or K2 is None or Pr2 is None or Pr1 == 0:
            rows.append((page, graph_id, K1, K2, Pr1, Pr2, None, None, None, None, None, None, "нет K/Pr"))
            continue

        G1_merged = K2 / K1 + Pr2 / Pr1
        bidx = block_index_from_page_graph(page, graph_id)
        block = blocks_by_idx.get(bidx)
        matched_by_k = False
        matched_by_l = False
        if not block and (K1 is not None and K2 is not None):
            block = find_block_by_k1_k2(blocks_list, K1, K2)
            matched_by_k = bool(block)
        if not block and (K1 is not None and K2 is not None):
            block = find_block_by_l1_l2(blocks_list, K1, K2)
            matched_by_l = bool(block)
        G2_pdf = G1_pdf = D_met = D_calc = D_pdf = None
        if block:
            G1_pdf = block["G1"]
            G2_pdf = block["G2"]
            G_pdf = block["G"]
            D_pdf = block["D"]
            G = G_pdf
            D_met = (G2_pdf - 2.0) / G if G > 0 else None
            D_calc = G1_pdf / G if G > 0 else None

        note = ""
        if not block:
            note = "нет блока"
        elif matched_by_k:
            note = "по K1,K2"
        elif matched_by_l:
            note = "по L1,L2"

        rows.append((page, graph_id, K1, K2, Pr1, Pr2, G1_merged, G1_pdf, G2_pdf, D_met, D_calc, D_pdf, note))

        if page in PAGES_WITH_FIXED_LOG and log_metrics:
            a_short = log_metrics.get("amplitude_short_component_au")
            k_log = log_metrics.get("calculated_crystallinity_index")
            pr_log = log_metrics.get("calculated_proton_density")
            header_match = ""
            if k_log is not None and K2 is not None:
                dk = abs(k_log - K2)
                header_match += f" K_лог≈K2" if dk < 0.01 else f" K_лог={k_log}"
            if pr_log is not None and Pr2 is not None:
                dp = abs(pr_log - Pr2)
                header_match += " Pr_лог≈Pr2" if dp < 0.01 else f" Pr_лог={pr_log}"
            implied_m = (a_short / Pr2) if (a_short is not None and Pr2 and Pr2 > 0) else None
            log_check_rows.append((page, graph_id, K2, Pr2, k_log, pr_log, a_short, implied_m, header_match.strip()))

    lines.append("  page  gid   K1       K2       Pr1      Pr2      G1_merged  G1_PDF   G2_PDF   D_met   D_calc  D_PDF   прим.")
    lines.append("  " + "-" * 115)
    for r in rows:
        page, gid, K1, K2, Pr1, Pr2, G1_m, G1_p, G2_p, D_met, D_calc, D_pdf, note = r
        k1s = f"{K1:.5f}" if K1 is not None else "—"
        k2s = f"{K2:.5f}" if K2 is not None else "—"
        p1s = f"{Pr1:.5f}" if Pr1 is not None else "—"
        p2s = f"{Pr2:.5f}" if Pr2 is not None else "—"
        g1ms = f"{G1_m:.4f}" if G1_m is not None else "—"
        g1ps = f"{G1_p:.4f}" if G1_p is not None else "—"
        g2ps = f"{G2_p:.4f}" if G2_p is not None else "—"
        dm = f"{D_met:.1f}" if D_met is not None else "—"
        dc = f"{D_calc:.1f}" if D_calc is not None else "—"
        dp = f"{D_pdf:.1f}" if D_pdf is not None else "—"
        lines.append(f"  {page:4}  {gid:3}  {k1s:>8}  {k2s:>8}  {p1s:>8}  {p2s:>8}  {g1ms:>10}  {g1ps:>8}  {g2ps:>8}  {dm:>6}  {dc:>6}  {dp:>6}  {note}")

    lines.extend([
        "",
        "--- 3. Проверка по страницам с исправленным логом (1, 2, 3, 20, 21, 22) ---",
        "",
        "Для этих страниц в логе вручную поправлены метрики. Проверяем:",
        "  • Совпадение calculated_crystallinity_index и calculated_proton_density в логе с K2 и Pr2 из заголовка.",
        "  • Подразумеваемая масса по методологии: Pr = A_short/m  =>  m = A_short/Pr2 (Pr2 из заголовка).",
        "  (Точная формула K из T2 и амплитуд в методике не выписана — см. RELAX 8SB45.)",
        "",
    ])
    if log_check_rows:
        lines.append("  page  gid   K2(header)  Pr2(header)  K_лог     Pr_лог    A_short    m_implied   примечание")
        lines.append("  " + "-" * 95)
        for r in log_check_rows:
            page, gid, K2, Pr2, k_log, pr_log, a_short, implied_m, header_match = r
            k2s = f"{K2:.5f}" if K2 is not None else "—"
            p2s = f"{Pr2:.5f}" if Pr2 is not None else "—"
            kls = f"{k_log:.5f}" if k_log is not None else "—"
            pls = f"{pr_log:.5f}" if pr_log is not None else "—"
            as_ = f"{a_short:.5f}" if a_short is not None else "—"
            im_ = f"{implied_m:.4f}" if implied_m is not None else "—"
            lines.append(f"  {page:4}  {gid:3}  {k2s:>11}  {p2s:>11}  {kls:>8}  {pls:>8}  {as_:>10}  {im_:>10}  {header_match}")
    else:
        lines.append("  (нет данных с логом для указанных страниц в текущем merged.)")
    lines.append("")

    lines.extend([
        "--- 4. Масса и протонная плотность по методологии ---",
        "",
        "Методика (п. 6.4): из фрагментов штрихов берут «приблизительно равные навески»; «массу каждой",
        "навески фиксирует прибор» для учёта при расчётах. То есть каждый образец (открытый участок и",
        "участок с покрытием) — своя навеска со своей массой. Разные эксперименты = разные проколы/участки,",
        "масса от эксперимента к эксперименту может отличаться (размер навески не задан жёстко).",
        "",
        "Pr = A_k / m (амплитуда короткой компоненты / масса). Поэтому:",
        "  • Разброс Pr между образцами (разные графики, разные объекты) — ожидаем.",
        "  • Различие Pr1 и Pr2 для одной пары (без/с покрытием) — норма: это две разные навески.",
        "  • Сильное изменение «протонной плотности на одном и том же образце»: если имеется в виду",
        "    один и тот же штрих, но два измерения (открытый и под покрытием) — это две навески, различие",
        "    допустимо. Если один и тот же образец измерен повторно в тех же условиях, методика предполагает",
        "    воспроизводимость (п. 6.4 — три повторности, данные используют при воспроизводимости).",
        "  • Кратное отличие «веса» (массы) от эксперимента к эксперименту по методологии возможно:",
        "    навески «приблизительно равные», масса фиксируется прибором и может варьироваться.",
        "",
    ])

    report = "\n".join(lines)
    with open(OUT_REPORT, "w", encoding="utf-8") as f:
        f.write(report)
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
