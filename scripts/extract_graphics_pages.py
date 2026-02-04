#!/usr/bin/env python3
"""
Extract each page of graphics_without_coverage.pdf as PNG for duplicate detection
and for vision/LLM analysis (to verify K2/K1, L2/L1 from raw curves).

Requires: pip install pymupdf
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
GRAPHICS_PDF = PROJECT_ROOT / "graphics_without_coverage.pdf"
OUT_DIR = PROJECT_ROOT / "data" / "graphics_pages"

ZOOM = 2


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    try:
        import fitz  # PyMuPDF
    except ImportError:
        print("PyMuPDF not installed. Run: pip install pymupdf", file=sys.stderr)
        return 1
    doc = fitz.open(GRAPHICS_PDF)
    for i in range(len(doc)):
        page = doc[i]
        mat = fitz.Matrix(ZOOM, ZOOM)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        out_path = OUT_DIR / f"page_{i+1:03d}.png"
        pix.save(str(out_path))
    doc.close()
    print(f"Saved {len(list(OUT_DIR.glob('*.png')))} pages to {OUT_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
