#!/usr/bin/env python3
"""
DWG → DXF(ODA) → PDF(ezdxf+PyMuPDF) 转换
用法: python3 dwg2pdf.py <file.dwg>
输出: 同目录同名 .pdf
"""
import os, sys, tempfile, ezdxf
from ezdxf.addons.drawing import Frontend, RenderContext
from ezdxf.addons.drawing.pymupdf import PyMuPdfBackend
import pymupdf

def dwg_to_pdf(dwg_path: str) -> str:
    pdf_path = dwg_path.rsplit(".", 1)[0] + ".pdf"
    doc = ezdxf.odafc.readfile(dwg_path)
    sp = doc.modelspace()
    ctx = RenderContext(doc)
    backend = PyMuPdfBackend()
    Frontend(ctx, backend).draw(sp)

    page = pymupdf.open()
    w, h = 1190, 842  # A3 横向 @72dpi
    backend.save(page, margin=(10, 10, 10, 10), rect=pymupdf.Rect(0, 0, w, h))
    page.save(pdf_path)
    page.close()
    entity_count = len(list(sp.query()))
    print(f"✓ {dwg_path} → {pdf_path}  (entities: {entity_count})")
    return pdf_path

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python3 dwg2pdf.py <file.dwg>", file=sys.stderr)
        sys.exit(1)
    dwg_to_pdf(sys.argv[1])
