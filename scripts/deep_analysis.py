#!/usr/bin/env python3
"""
Deep analysis of calculations: ratio consistency, formula vs methodology, G2-G1 relationship.
Evidence that does not rely on "same D across one document".
"""
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_JSON = PROJECT_ROOT / "data" / "calculations_verified.json"
OUT_REPORT = PROJECT_ROOT / "data" / "deep_analysis_report.txt"


def main():
    with open(DATA_JSON, encoding="utf-8") as f:
        data = json.load(f)
    blocks = data["blocks"]
    n = len(blocks)

    # 1) Ratios K2/K1 and L2/L1 across blocks
    ratio_k = [b["K2"] / b["K1"] for b in blocks]
    ratio_l = [b["L2"] / b["L1"] for b in blocks]
    mean_rk = sum(ratio_k) / n
    mean_rl = sum(ratio_l) / n
    var_rk = sum((x - mean_rk) ** 2 for x in ratio_k) / n
    var_rl = sum((x - mean_rl) ** 2 for x in ratio_l) / n
    std_rk = var_rk ** 0.5
    std_rl = var_rl ** 0.5

    # 2) Methodology formula: calibration line has vertex at G=2 when D=0, slope = (G2-G1)/Δt.
    #    On the line, point (D, G2) gives: G2 = 2 + ((G2-G1)/Δt)*D  =>  D = (G2-2)*Δt/(G2-G1).
    #    With Δt=1: D_methodology = (G2-2)/G.  In calculations they use D_calc = G1/G.
    D_met = []
    D_calc = []
    for b in blocks:
        g = b["G2"] - b["G1"]
        if g <= 0:
            continue
        d_m = (b["G2"] - 2.0) / g
        d_c = b["G1"] / g
        D_met.append(d_m)
        D_calc.append(d_c)
    mean_d_met = sum(D_met) / len(D_met)
    mean_d_calc = sum(D_calc) / len(D_calc)

    # 3) If D is fixed at 57.42, then G = G1/57.42, so G2 = G1 + G1/57.42 = G1 * (1 + 1/57.42).
    target_d = 57.42
    expected_g2_over_g1 = 1 + 1 / target_d
    actual_ratio = [b["G2"] / b["G1"] for b in blocks if b["G1"] > 0]
    mean_g2g1 = sum(actual_ratio) / len(actual_ratio)
    var_g2g1 = sum((x - mean_g2g1) ** 2 for x in actual_ratio) / len(actual_ratio)
    std_g2g1 = var_g2g1 ** 0.5

    lines = [
        "=== Углублённый анализ (независимо от «один документ») ===",
        "",
        "1. ПОСТОЯНСТВО ОТНОШЕНИЙ K2/K1 и L2/L1",
        "   По методологии K и Pr зависят от вида покрытия и старения. Разные реквизиты ",
        "   (подпись, печать, тонер) и разные образцы должны давать разброс отношений.",
        "",
        f"   K2/K1:  среднее = {mean_rk:.6f},  СКО = {std_rk:.6f},  мин = {min(ratio_k):.6f},  макс = {max(ratio_k):.6f}",
        f"   L2/L1:  среднее = {mean_rl:.6f},  СКО = {std_rl:.6f},  мин = {min(ratio_l):.6f},  макс = {max(ratio_l):.6f}",
        "",
    ]
    if std_rk < 0.001 and std_rl < 0.001:
        lines.append("   Вывод: отношения K2/K1 и L2/L1 практически константны по всем блокам. При честных")
        lines.append("   измерениях от разных образцов ожидался бы заметный разброс. Возможное объяснение —")
        lines.append("   подбор входных величин под целевую формулу (или искусственно заданные константы).")
    else:
        lines.append("   Разброс отношений присутствует.")
    lines.extend([
        "",
        "2. СООТВЕТСТВИЕ ФОРМУЛЫ D МЕТОДОЛОГИИ",
        "   В методологии (п. 6.6): калибровочная прямая имеет вершину в точке G=2 при D=0 и наклон (G2-G1)/Δt.",
        "   Из этого следует: на прямой находят точку с ординатой G2 и считывают абсциссу D:",
        "   D = (G2 - 2) / (G2 - G1)  при Δt = 1 месяц.",
        "   В файле calculations используется формула:  D = G1 / (G2 - G1).",
        "   Это разные формулы.",
        "",
        f"   По методологии (D_met = (G2-2)/G):  среднее D = {mean_d_met:.2f} мес.",
        f"   По расчётам (D_calc = G1/G):         среднее D = {mean_d_calc:.2f} мес.",
        "",
    ])
    if abs(mean_d_met - mean_d_calc) > 5:
        lines.append("   Вывод: расчётная формула в calculations.pdf НЕ совпадает с методологией. Используемая")
        lines.append("   формула D = G1/G даёт систематически завышенную давность по сравнению с формулой")
        lines.append("   методологии D = (G2-2)/G. Либо применена неверная формула, либо иная интерпретация.")
    lines.extend([
        "",
        "3. СВЯЗЬ G2 И G1 ПРИ ФИКСИРОВАННОМ D",
        "   Если во всех блоках целевое D одно и то же (например 57.42), то G = G1/D, откуда",
        "   G2 = G1 + G1/D = G1 * (1 + 1/D). То есть отношение G2/G1 должно быть константой.",
        "",
        f"   Ожидаемое G2/G1 при D = {target_d}:  {expected_g2_over_g1:.6f}",
        f"   Фактическое среднее G2/G1 по блокам:  {mean_g2g1:.6f},  СКО = {std_g2g1:.6f}",
        "",
    ])
    if std_g2g1 < 0.001:
        lines.append("   Вывод: отношение G2/G1 практически не меняется по блокам, что согласуется с гипотезой")
        lines.append("   о подгонке входных данных под фиксированное целевое D.")
    lines.extend([
        "",
        "4. ИТОГ",
        "   — Постоянство K2/K1 и L2/L1 при разнотипных реквизитах даёт основание проверять, не подбирались",
        "     ли входные величины под заданный результат.",
        "   — Несоответствие формулы D в расчётах формуле методологии (вершина G=2 при D=0) указывает",
        "     на возможное нарушение методики или использование иного (не описанного в методике) правила.",
        "   — Стабильность G2/G1 согласуется с фиксированным целевым D по всем образцам.",
        "",
    ])

    report = "\n".join(lines)
    with open(OUT_REPORT, "w", encoding="utf-8") as f:
        f.write(report)
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
