#!/usr/bin/env python3
"""Build manifest of graphics pages (page, file, illustration numbers, punch) for vision analysis."""
from pathlib import Path
import csv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PAGES_DIR = PROJECT_ROOT / "data" / "graphics_pages"
OUT_CSV = PROJECT_ROOT / "data" / "graphics_manifest.csv"
PAGES_TOTAL = 78


def main():
    PAGES_DIR.mkdir(parents=True, exist_ok=True)
    rows = []
    for page in range(1, PAGES_TOTAL + 1):
        ill_1 = (page - 1) * 2 + 1
        ill_2 = (page - 1) * 2 + 2
        punch = "первый прокол" if page <= 39 else "третий прокол"
        fname = f"page_{page:03d}.png"
        path = PAGES_DIR / fname
        rows.append({
            "page": page,
            "file": fname,
            "illustration_1": ill_1,
            "illustration_2": ill_2,
            "punch": punch,
            "path": str(path),
        })
    with open(OUT_CSV, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["page", "file", "illustration_1", "illustration_2", "punch", "path"])
        w.writeheader()
        w.writerows(rows)
    print(f"Written {OUT_CSV} with {len(rows)} rows.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
