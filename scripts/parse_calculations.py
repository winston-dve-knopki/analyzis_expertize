#!/usr/bin/env python3
"""
Parse calculations.pdf and verify all G1, G2, G, D formulas.
Output: data/calculations_verified.json and verification report.
"""
import re
import json
from pathlib import Path
from decimal import Decimal, getcontext

getcontext().prec = 20

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CALC_PDF = PROJECT_ROOT / "calculations.pdf"
OUT_DIR = PROJECT_ROOT / "data"
OUT_JSON = OUT_DIR / "calculations_verified.json"
OUT_REPORT = OUT_DIR / "verification_report.txt"

# Tolerance for comparing floats (relative and absolute)
TOL_ABS = 0.002
TOL_REL = 0.001


def extract_text_from_pdf():
    try:
        import pdfplumber
    except ImportError:
        raise SystemExit("Install: pip install pdfplumber")
    text_parts = []
    with pdfplumber.open(CALC_PDF) as pdf:
        for page in pdf.pages:
            t = page.extract_text()
            if t:
                text_parts.append(t)
    return "\n".join(text_parts)


def parse_float(s):
    s = s.replace(",", ".")
    return float(s)


def parse_block(chunk):
    """Extract K1, K2, L1, L2, P1, P2, R1, R2, G1, G2, G, D from a block of text."""
    # K1: 0.80296, K2: 0.79092
    m = re.search(r"K1:\s*([\d.,]+)\s*,\s*K2:\s*([\d.,]+)", chunk)
    if not m:
        return None
    k1, k2 = parse_float(m.group(1)), parse_float(m.group(2))
    m = re.search(r"L1:\s*([\d.,]+)\s*,\s*L2:\s*([\d.,]+)", chunk)
    if not m:
        return None
    l1, l2 = parse_float(m.group(1)), parse_float(m.group(2))
    m = re.search(r"P1:\s*([\d.,]+)\s*,\s*P2:\s*([\d.,]+)", chunk)
    if not m:
        return None
    p1, p2 = parse_float(m.group(1)), parse_float(m.group(2))
    m = re.search(r"R1:\s*([\d.,]+)\s*,\s*R2:\s*([\d.,]+)", chunk)
    if not m:
        return None
    r1, r2 = parse_float(m.group(1)), parse_float(m.group(2))
    m = re.search(r"G1:\s*([\d.,]+)\s*,\s*G2:\s*([\d.,]+)\s*,\s*G:\s*([\d.,]+)\s*,\s*D:\s*([\d.,]+)", chunk)
    if not m:
        return None
    g1, g2, g, d = (
        parse_float(m.group(1)),
        parse_float(m.group(2)),
        parse_float(m.group(3)),
        parse_float(m.group(4)),
    )
    return {
        "K1": k1, "K2": k2, "L1": l1, "L2": l2,
        "P1": p1, "P2": p2, "R1": r1, "R2": r2,
        "G1": g1, "G2": g2, "G": g, "D": d,
    }


def verify_block(b):
    """Recompute G1, G2, G, D and compare with stated values."""
    g1_check = b["K2"] / b["K1"] + b["P2"] / b["P1"]
    g2_check = b["L2"] / b["L1"] + b["R2"] / b["R1"]
    g_check = g2_check - g1_check
    if abs(g_check) < 1e-12:
        d_check = float("nan")
    else:
        d_check = b["G1"] / g_check
    ok_g1 = abs(g1_check - b["G1"]) <= TOL_ABS or abs((g1_check - b["G1"]) / b["G1"]) <= TOL_REL
    ok_g2 = abs(g2_check - b["G2"]) <= TOL_ABS or abs((g2_check - b["G2"]) / b["G2"]) <= TOL_REL
    ok_g = abs(g_check - b["G"]) <= TOL_ABS or (b["G"] and abs((g_check - b["G"]) / b["G"]) <= TOL_REL)
    ok_d = abs(d_check - b["D"]) <= TOL_ABS or abs((d_check - b["D"]) / b["D"]) <= TOL_REL
    return {
        "G1_check": g1_check, "G2_check": g2_check, "G_check": g_check, "D_check": d_check,
        "ok_G1": ok_g1, "ok_G2": ok_g2, "ok_G": ok_g, "ok_D": ok_d,
        "match": ok_g1 and ok_g2 and ok_g and ok_d,
    }


def main():
    OUT_DIR.mkdir(exist_ok=True)
    text = extract_text_from_pdf()
    chunks = re.split(r"----------------------------------------", text)
    blocks = []
    errors = []
    for i, chunk in enumerate(chunks):
        b = parse_block(chunk)
        if b is None:
            continue
        v = verify_block(b)
        blocks.append({
            "block_index": len(blocks) + 1,
            **b,
            **v,
        })
        if not v["match"]:
            errors.append({
                "block": len(blocks),
                "stated": {"G1": b["G1"], "G2": b["G2"], "G": b["G"], "D": b["D"]},
                "computed": {
                    "G1": v["G1_check"], "G2": v["G2_check"],
                    "G": v["G_check"], "D": v["D_check"],
                },
            })

    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump({"blocks": blocks, "errors": errors, "total_blocks": len(blocks)}, f, indent=2, ensure_ascii=False)

    # Report
    lines = [
        "=== Verification report: calculations.pdf ===",
        "",
        f"Total blocks parsed: {len(blocks)}",
        f"Blocks with full match (G1, G2, G, D): {sum(1 for bl in blocks if bl.get('match'))}",
        f"Blocks with at least one mismatch: {len(errors)}",
        "",
    ]
    if errors:
        lines.append("--- Mismatches (block index, stated vs computed) ---")
        for e in errors[:30]:
            lines.append(f"  Block {e['block']}: G1 {e['stated']['G1']} vs {e['computed']['G1']:.6f}, "
                        f"G2 {e['stated']['G2']} vs {e['computed']['G2']:.6f}, "
                        f"G {e['stated']['G']} vs {e['computed']['G']:.6f}, "
                        f"D {e['stated']['D']} vs {e['computed']['D']:.6f}")
        if len(errors) > 30:
            lines.append(f"  ... and {len(errors) - 30} more.")
    lines.append("")
    lines.append("Methodology check: G = K2/K1 + P2/P1 (first), G2 = L2/L1 + R2/R1 (second), G = G2-G1, D = G1/G (Δt=1 month).")
    report = "\n".join(lines)
    with open(OUT_REPORT, "w", encoding="utf-8") as f:
        f.write(report)
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
