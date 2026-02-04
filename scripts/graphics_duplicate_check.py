#!/usr/bin/env python3
"""
Compute perceptual hashes of each graphics page. Find duplicate or near-duplicate pages.
If different samples have identical or near-identical graphs, that suggests reuse
of the same curve — K2/K1 and L2/L1 would be from the same underlying data.
"""
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PAGES_DIR = PROJECT_ROOT / "data" / "graphics_pages"
OUT_JSON = PROJECT_ROOT / "data" / "graphics_hashes.json"
OUT_REPORT = PROJECT_ROOT / "data" / "graphics_duplicates_report.txt"

NEAR_DUP_THRESHOLD = 3
EXACT_THRESHOLD = 0


def main():
    try:
        from PIL import Image
        import imagehash
    except ImportError as e:
        print("Install: pip install Pillow imagehash", file=__import__("sys").stderr)
        return 1

    PAGES_DIR.mkdir(parents=True, exist_ok=True)
    paths = sorted(PAGES_DIR.glob("page_*.png"))
    if not paths:
        print(f"No page_*.png in {PAGES_DIR}. Run extract_graphics_pages.py first.", file=__import__("sys").stderr)
        return 1

    hashes = []
    for p in paths:
        img = Image.open(p)
        ph = imagehash.phash(img)
        page_num = int(p.stem.split("_")[1])
        hashes.append({"page": page_num, "path": str(p.name), "phash": str(ph)})
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump({"hashes": hashes}, f, indent=2)

    by_phash = {}
    for h in hashes:
        k = h["phash"]
        by_phash.setdefault(k, []).append(h["page"])
    exact_dups = {k: pages for k, pages in by_phash.items() if len(pages) > 1}

    near_dups = []
    for i, a in enumerate(hashes):
        ha = imagehash.hex_to_hash(a["phash"])
        for j, b in enumerate(hashes):
            if j <= i:
                continue
            hb = imagehash.hex_to_hash(b["phash"])
            d = ha - hb
            if EXACT_THRESHOLD < d <= NEAR_DUP_THRESHOLD:
                near_dups.append((a["page"], b["page"], int(d)))

    lines = [
        "=== Проверка графиков ЯМР на дубликаты ===",
        "",
        "Графики — сырые данные (спад ССИ). Если у разных образцов графики совпадают,",
        "это может означать повторное использование одних и тех же данных (подгонка).",
        "",
        f"Всего страниц: {len(hashes)}",
        "",
        "--- Точные дубликаты (одинаковый перцептивный хэш) ---",
    ]
    if exact_dups:
        for phash_val, pages in sorted(exact_dups.items(), key=lambda x: -len(x[1])):
            lines.append(f"  Страницы {pages} — идентичны.")
        lines.append("")
        lines.append("  Вывод: разные образцы представлены одинаковыми графиками.")
    else:
        lines.append("  Не обнаружено.")
    lines.extend([
        "",
        "--- Близкие по хэшу страницы (расстояние <= 3) ---",
    ])
    if near_dups:
        for p1, p2, dist in sorted(near_dups, key=lambda x: (x[0], x[1]))[:30]:
            lines.append(f"  Страницы {p1} и {p2}, расстояние = {dist}")
        if len(near_dups) > 30:
            lines.append(f"  ... и ещё {len(near_dups) - 30} пар.")
    else:
        lines.append("  Нет.")
    lines.append("")
    lines.append("Справка: стр. 1 = ил. 1–2 (Объект 1, первый прокол), стр. 40 = ил. 79–80 (третий прокол).")
    lines.append("")

    report = "\n".join(lines)
    with open(OUT_REPORT, "w", encoding="utf-8") as f:
        f.write(report)
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
