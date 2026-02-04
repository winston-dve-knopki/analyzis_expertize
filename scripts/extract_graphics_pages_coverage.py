#!/usr/bin/env python3
"""
Извлекает каждую страницу graphics_with_coverage.pdf в отдельный PNG
(аналогично extract_graphics_pages.py для graphics_without_coverage.pdf).

Требуется: pip install pymupdf
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
GRAPHICS_PDF = PROJECT_ROOT / "graphics_with_coverage.pdf"
OUT_DIR = PROJECT_ROOT / "data" / "graphics_pages_coverage"

ZOOM = 2


def main():
    if not GRAPHICS_PDF.exists():
        print(f"Файл не найден: {GRAPHICS_PDF}", file=sys.stderr)
        return 1
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    try:
        import fitz  # PyMuPDF
    except ImportError:
        print("PyMuPDF не установлен. Выполните: pip install pymupdf", file=sys.stderr)
        return 1
    doc = fitz.open(GRAPHICS_PDF)
    for i in range(len(doc)):
        page = doc[i]
        mat = fitz.Matrix(ZOOM, ZOOM)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        out_path = OUT_DIR / f"page_{i+1:03d}.png"
        pix.save(str(out_path))
    doc.close()
    n = len(list(OUT_DIR.glob("*.png")))
    print(f"Сохранено {n} страниц в {OUT_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
