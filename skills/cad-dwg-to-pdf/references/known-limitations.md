# Known Limitations of ezdxf + PyMuPDF Pipeline

## Chinese characters render as boxes (□□□)

**Symptom**: Chinese text labels in the DWG appear as empty squares in the output PDF.

**Root cause**: ezdxf's drawing addons resolve text entities via the `ezdxf.fonts` module. When the DXF references a font name (e.g. `simsun.ttf`, `hztxt.shx`, `宋体`) that doesn't map to a system-installed TTF, the renderer falls back to a placeholder glyph.

**Workarounds** (ranked by effort):

1. **Install the missing font on the host system** — `sudo apt install fonts-noto-cjk` covers most cases.
2. **Embed the font path in ezdxf config** — point `ezdxf.fonts.font_directory` at a directory containing the TTF files referenced by the DWG.
3. **Pre-process the DXF** to replace missing-font text entities with their actual string content, then render with MatplotlibBackend where you control the font.
4. **Use a different backend** — `MatplotlibBackend` with `matplotlib.rcParams['font.sans-serif'] = ['Noto Sans CJK SC']` gives reliable Chinese rendering at the cost of slower speed.

For most packaging-machine drawings, **workaround 1 + restarting the Python process** is enough.

## First-run ODA AppImage failures

**Symptom**: `xdg-open: no method available` or `cannot open display: '0.0'` or hang with no output.

**Root cause**: ODAFileConverter needs either FUSE (for AppImage mount) or xvfb (for its own GUI bootstrap — even though the conversion is headless, the binary briefly initializes a display).

**Fix**:
```bash
sudo apt install -y libfuse2t64 xvfb
# Wrap python invocation:
xvfb-run -a python3 dwg2pdf.py file.dwg
```

## Large DWG files (>50K entities)

**Symptom**: Conversion takes >5 minutes, memory usage spikes, output PDF is huge (>100MB).

**Mitigations**:
- Lower DPI: replace `w, h = 1190, 842` with `w, h = 833, 590` (A3 @ 50dpi)
- Render only visible layers: `sp = doc.modelspace()` then filter by layer name before `Frontend.draw()`
- Convert to a simplified DXF first via `ezdxf.odafc.readfile(path, force_conversion=True, out_format=ezdxf.odafc.DXFFormat.R12)` — older DXF format is faster to parse

## Multi-page output

**When needed**: DWG has multiple layouts (paperspace tabs), or you want to split a long drawing into A3 pages.

**Pattern**:
```python
import pymupdf
from ezdxf.addons.drawing import Frontend, RenderContext
from ezdxf.addons.drawing.pymupdf import PyMuPdfBackend

doc = ezdxf.odafc.readfile(dwg_path)
page = pymupdf.open()
backend = PyMuPdfBackend()

# Each layout → one page
for layout_name in doc.layout_names():
    layout = doc.layouts.get(layout_name)
    page.new_page(width=1190, height=842)
    Frontend(RenderContext(doc), backend).draw(layout)
    backend.save(page, margin=(10,10,10,10), rect=pymupdf.Rect(0,0,1190,842))

# First page is blank (PyMuPdf quirk) — delete it
page.delete_page(0)
page.save("output.pdf")
```

Note the `delete_page(0)` quirk — `pymupdf.open()` creates one empty page by default, and `new_page` appends. Always delete the first blank page in this pattern.

## DPI / page size reference

| Page | w x h @ 72dpi (pt) | @ 96dpi (pt) | @ 50dpi (pt) |
|---|---|---|---|
| A4 portrait | 595, 842 | 794, 1123 | 413, 585 |
| A4 landscape | 842, 595 | 1123, 794 | 585, 413 |
| A3 portrait | 842, 1190 | 1123, 1587 | 585, 826 |
| **A3 landscape** | **1190, 842** | 1587, 1123 | 826, 585 |
| A2 portrait | 1190, 1684 | 1587, 2245 | 826, 1169 |
| A1 landscape | 2384, 1684 | 3179, 2245 | 1656, 1169 |

72dpi is fine for screen preview and quick review. Use 96+ dpi only if the PDF will be printed at near-original size.
