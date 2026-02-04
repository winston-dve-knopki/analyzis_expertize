#!/usr/bin/env python3
"""
Statistical analysis of D (давность в месяцах) from verified calculations.
Highlights suspicious uniformity: almost all D ≈ 57.42 or 56.25 despite varied inputs.
"""
import json
from pathlib import Path
from collections import Counter

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_JSON = PROJECT_ROOT / "data" / "calculations_verified.json"
OUT_REPORT = PROJECT_ROOT / "data" / "d_statistics_report.txt"
OUT_HIST_CSV = PROJECT_ROOT / "data" / "d_histogram.csv"


def main():
    with open(DATA_JSON, encoding="utf-8") as f:
        data = json.load(f)
    blocks = data["blocks"]
    D_values = [b["D"] for b in blocks]
    n = len(D_values)

    # Basic statistics
    mean_d = sum(D_values) / n
    variance = sum((x - mean_d) ** 2 for x in D_values) / n
    std_d = variance ** 0.5
    min_d, max_d = min(D_values), max(D_values)

    # Distribution by rounded value (to 2 decimals)
    rounded = [round(x, 2) for x in D_values]
    counts = Counter(rounded)
    sorted_counts = sorted(counts.items(), key=lambda x: -x[1])

    # Histogram bins (e.g. 56.0-56.5, 56.5-57.0, 57.0-57.5, 57.5-58.0)
    bins = [56.0, 56.25, 56.5, 56.75, 57.0, 57.25, 57.5, 57.75, 58.0]
    hist = {f"{bins[i]:.2f}-{bins[i+1]:.2f}": 0 for i in range(len(bins) - 1)}
    for d in D_values:
        for i in range(len(bins) - 1):
            if bins[i] <= d < bins[i + 1]:
                hist[f"{bins[i]:.2f}-{bins[i+1]:.2f}"] += 1
                break
        else:
            if d >= bins[-1]:
                key = f"{bins[-2]:.2f}-{bins[-1]:.2f}"
                if key not in hist:
                    hist[key] = 0
                hist[key] += 1

    # Unique D values and how many blocks each
    unique_d = sorted(set(rounded))
    n_unique = len(unique_d)

    lines = [
        "=== Статистика D (давность события создания, месяцы) ===",
        "",
        f"Число блоков (образцов): {n}",
        "",
        "--- Описательная статистика ---",
        f"  Среднее:     {mean_d:.4f}",
        f"  СКО:         {std_d:.4f}",
        f"  Мин:         {min_d:.2f}",
        f"  Макс:         {max_d:.2f}",
        "",
        "--- Распределение по заявленным D (округлено до 0.01) ---",
    ]
    for val, cnt in sorted_counts:
        pct = 100 * cnt / n
        lines.append(f"  D = {val:.2f}  —  {cnt} блоков  ({pct:.1f}%)")
    lines.extend([
        "",
        "--- Количество уникальных значений D ---",
        f"  Уникальных значений: {n_unique} из {n} блоков",
        "",
        "--- Гистограмма (интервалы по 0.25 мес) ---",
    ])
    for interval, cnt in sorted(hist.items(), key=lambda x: float(x[0].split("-")[0])):
        bar = "#" * min(cnt, 80) + (" ..." if cnt > 80 else "")
        lines.append(f"  {interval}: {cnt:3d}  {bar}")
    lines.extend([
        "",
        "--- Вывод о однородности D ---",
        "",
        "При независимых измерениях разных образцов (разные документы, реквизиты, "
        "покрытия) естественно ожидать разброс давности D в несколько месяцев или более. "
        "В данных заявленные значения D сосредоточены практически только в двух точках: "
        "около 57.42 мес и около 56.24–56.26 мес, при том что входные параметры (K1, K2, "
        "P1, P2, L1, L2, R1, R2) сильно различаются по блокам.",
        "",
        "Такой результат статистически маловероятен при честных измерениях и согласуется "
        "с гипотезой о подгонке результата под заданную давность (целевое D ≈ 57.4 или ≈ 56.25 мес).",
        "",
        "Риск: признаки возможной подгонки экспертного вывода под заранее заданный результат.",
        "",
    ])

    report = "\n".join(lines)
    with open(OUT_REPORT, "w", encoding="utf-8") as f:
        f.write(report)
    print(report)

    # Save histogram data for charts
    with open(OUT_HIST_CSV, "w", encoding="utf-8") as f:
        f.write("D_rounded,count\n")
        for val, cnt in sorted_counts:
            f.write(f"{val:.2f},{cnt}\n")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
