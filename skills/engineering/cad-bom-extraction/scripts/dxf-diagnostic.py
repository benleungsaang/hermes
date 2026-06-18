#!/usr/bin/env python3.12
"""
Diagnostic dump for a DXF file — shows every MTEXT/TEXT/ATTRIB with its
classify_text bucket and the spatial size pool.

Run before debugging "wrong BOM". Tells you in 5 seconds whether the issue
is block recursion, classification, or size association.

Usage:
    python3.12 dxf-diagnostic.py <input.dxf>
"""

import sys
import math
from pathlib import Path

# ezdxf lives in py3.12 site-packages on this host
sys.path.insert(0, '/home/ubuntu/.local/lib/python3.12/site-packages')
sys.path.insert(0, str(Path.home() / '.hermes/workspace/cad-bom/tools'))

import ezdxf
import cad_bom_extract


def main():
    if len(sys.argv) < 2:
        print("Usage: python3.12 dxf-diagnostic.py <input.dxf>")
        sys.exit(1)

    src = Path(sys.argv[1])
    if not src.exists():
        print(f"❌ 找不到: {src}")
        sys.exit(1)

    doc = ezdxf.readfile(str(src))
    print(f"📂 {src.name}")
    print(f"   DXF version: {doc.dxfversion}")
    print(f"   图层: {len(doc.layers)}, 块: {len(doc.blocks)}")
    print()

    texts, dims = cad_bom_extract.extract_entities(doc)

    # Style detection
    if len(dims) == 0 and len(texts) > 5:
        print("⚠️  TEXT-DRIVEN DRAWING (0 DIMENSION, many MTEXT)")
        print("   Bare digits in MTEXT are sizes, not parts.")
        print()

    # Counts by class
    by_class = {'part': 0, 'prefix': 0, 'annotation': 0, 'size': 0}
    for t in texts:
        cls = t.get('_class', '?')
        by_class[cls] = by_class.get(cls, 0) + 1
    print(f"   Text pool: part={by_class['part']}, prefix={by_class['prefix']}, "
          f"annotation={by_class['annotation']}, size={by_class.get('size', 0)}")
    print(f"   Size pool (DIMENSION + text-extracted): {len(dims)}")
    print()

    # All MTEXT/ATTRIB with classification, sorted by position
    print("=== All extracted text (sorted by position) ===")
    all_text = []
    for ent, bn, depth, off in cad_bom_extract._iter_all_entities(doc):
        t = ent.dxftype()
        if t in ('MTEXT', 'TEXT', 'ATTRIB', 'ATTDEF'):
            try:
                raw = ent.text if hasattr(ent, 'text') else ent.dxf.get('text', '')
            except Exception:
                raw = ''
            clean = cad_bom_extract.clean_mtext(raw) if raw else ''
            if not clean:
                continue
            cls = cad_bom_extract.classify_text(clean)
            if t in ('MTEXT', 'TEXT'):
                p = ent.dxf.insert
            else:
                p = ent.dxf.get('insert', (0, 0, 0))
            all_text.append((p[0] + off[0], p[1] + off[1], cls, clean, t))

    all_text.sort(key=lambda r: (round(r[1], 1), r[0]))
    for x, y, cls, text, etype in all_text:
        marker = {'part': '✓', 'size': '#', 'annotation': '∅', 'prefix': '+'}.get(cls, '?')
        print(f"  {marker} ({x:7.2f}, {y:7.2f}) [{etype:6s}/{cls:10s}] \"{text}\"")

    # Size pool dump
    print()
    print(f"=== Size pool ({len(dims)} entries) ===")
    sorted_dims = sorted(dims, key=lambda d: (round(d['pos'][1], 1), d['pos'][0]))
    for d in sorted_dims[:30]:
        print(f"    ({d['pos'][0]:7.2f}, {d['pos'][1]:7.2f})  {d['measure']:8.2f}")
    if len(dims) > 30:
        print(f"    ... and {len(dims) - 30} more")


if __name__ == '__main__':
    main()
