#!/usr/bin/env python3
"""DWG → PDF conversion via ezdxf + PyMuPdfBackend (for quick visual reference, not BOM extraction).

Usage:
    python3 dwg2pdf.py <input.dwg> [output.pdf]

Requires: ODAFC configured (DW→DXF), ezdxf, PyMuPdfBackend.
Output: single-page A3 PDF (~900KB typical for packaging-line DWGs).
"""
import sys
sys.path.insert(0, "/home/ubuntu/.local/lib/python3.12/site-packages")

from ezdxf.addons import odafc
from ezdxf.addons.drawing import Frontend, RenderContext
from ezdxf.addons.drawing.pymupdf import PyMuPdfBackend, layout

dwg_path = sys.argv[1]
pdf_path = sys.argv[2] if len(sys.argv) > 2 else dwg_path.rsplit(".", 1)[0] + ".pdf"

print(f"Reading DWG: {dwg_path}")
doc = odafc.readfile(dwg_path)
msp = doc.modelspace()
print(f"  Version: {doc.dxfversion}, blocks: {len(doc.blocks)}")

# Count nested entities
visited, total = set(), 0
def count_ents(entities):
    global total
    for e in entities:
        total += 1
        if e.dxftype() == 'INSERT':
            try:
                blk = doc.blocks.get(e.dxf.name)
                if blk.name not in visited:
                    visited.add(blk.name)
                    count_ents(blk)
            except:
                pass
count_ents(msp)
print(f"  Total entities (incl. nested blocks): {total}")

print("Rendering with PyMuPdfBackend...")
backend = PyMuPdfBackend()
ctx = RenderContext(doc)
frontend = Frontend(ctx, backend)
frontend.draw_layout(msp)
backend.finalize()

page = layout.Page(420.0, 297.0, layout.Units.mm, layout.Margins(10, 10, 10, 10))
pdf_bytes = backend.get_pdf_bytes(page)

with open(pdf_path, "wb") as f:
    f.write(pdf_bytes)
print(f"Saved: {pdf_path} ({len(pdf_bytes)} bytes)")
