---
name: cad-drawing-bom
description: "Extract a BOM from packaging-machine CAD drawings. User provides PDF/image, VISION reads the drawing, DXF MTEXT cross-verifies. Delivers an inline markdown table with merged rows. Use when the user uploads a .pdf / .png / .dxf for a parts list / 零件清单 / BOM / 部件清单, especially for packaging machines, conveyors, and industrial equipment."
version: 2.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [cad, bom, dxf, packaging, vision, pdf, industrial]
    category: productivity
---

# CAD Drawing → BOM Extraction (VISION-first)

Extract a Bill of Materials from a 2D packaging-machine drawing. **Primary mode**: VISION reads the user's PDF/image. **Secondary mode**: DXF MTEXT cross-verifies when VISION is uncertain. Delivers an inline markdown table — no Excel, no DXF rendering.

## When to use this skill

Load when the user mentions any of:

- Uploads a `.pdf` / `.png` / `.dxf` + asks for BOM / 零件清单 / 部件清单 / part list
- `从图纸里抽 BOM` / `读图纸部件`
- A packaging-line or machine layout drawing where part names are written directly on the drawing (not a traditional parts list)

**Typical workflow**: the user sends a PDF or screenshot FIRST, then may also provide the DXF for cross-reference.

## When NOT to use this skill

- 3D models (`.step`, `.iges`, `.stp`) — different toolchain
- Drawings with no annotations and no labels (pure geometry) — VISION cannot identify unlabeled items. Ask the user to provide a parts list or annotations.
- A drawing that only has a single parts list / 明细栏 in a table — just extract that table directly, no VISION analysis needed.
- Scanned/photographed drawings of poor quality — low-resolution or heavily distorted images may cause VISION misreads. Ask for a cleaner export.

## Tool choice

**Primary tool**: `vision_analyze()` — the user provides a PDF or image. Convert PDF to PNG via PyMuPDF (fitz) first if needed, then analyze with vision.

**Secondary tool**: `ezdxf` (Python) for DXF/DWG MTEXT cross-reference — read MTEXT/TEXT/ATTRIB entities via nested-block recursion. Use `python3.12` explicitly on this host (ezdxf is in py3.12 site-packages, not python3/py3.11). `.dwg` files are auto-converted to DXF via ODAFC (see cad-bom-extraction skill for setup).

**No rendering**: Never use ezdxf's Frontend/MatplotlibBackend/PyMuPdfBackend to render DXF to image. The Frontend is the bottleneck (same processing time regardless of backend), and the user's CAD-exported PDF/PNG is always higher quality.

## DXF MTEXT extraction (reference)

When the user provides a DXF for cross-reference, extract MTEXT names via nested-block recursion:

```python
import ezdxf, re
doc = ezdxf.readfile(path)
seen = set()
def walk(entities):
    for ent in entities:
        if ent.dxftype() == 'MTEXT':
            t = ent.text.strip()
            if t and t not in seen:
                seen.add(t)
                # strip control codes: \\A1; \\W0.707; \\P \\C0;
                t2 = re.sub(r'\\\\[A-Za-z][^;]*;', '', t)
                t2 = t2.replace('\\\\P', ' / ').replace('\\\\A1;','').replace('\\\\C0;','')
                print(t2)  # collect for comparison
        elif ent.dxftype() == 'INSERT':
            try: walk(doc.blocks.get(ent.dxf.name))
            except: pass
walk(doc.modelspace())
```

For DXF with content entirely in nested blocks (e.g. SOONWIN → sub-blocks), the top-level modelspace may have 0 MTEXT entities. Always recurse.

**Performance note**: Complex drawings with >50 blocks may timeout (>10s). In that case, limit recursion or use a simpler text-extraction approach.

## BOM output format

Deliver as a markdown table — no Excel file. Conventions are stable as of 2026-06-18:

```
| # | 部件 | 规格 | 数量 | 说明 |
|---|---|---|---|---|
| 1 | Part name (English, from drawing) | spec | qty | Chinese position description |
```

**Rules**:

1. **Part names stay in original English** from the drawing — never translate to Chinese. Chinese only appears in the `说明` column for position/location context.
2. **Same-name same-spec items merge** into one row, quantities accumulate. Example: `Turnable unit (phi802)` appearing left+right → qty 2.
3. **Different spec = separate row** even if same name. Example: `Main conveyor 1-5` (1000mm) and `Main conveyor 6` (1500mm) are separate rows.
4. **Sort by material flow** through the layout (top→bottom, left→right, following the product path).
5. **Electrical cabinet auto-appends to BOM end** as an implied item — unless already explicitly drawn on the drawing (in which case it stays at its natural position, or at the end if preferred).
6. **Unlabeled but geometrically similar items**: When VISION sees a distinct shape (e.g. circular Turning unit) but only one instance is labeled, check the DXF for similar entities at other positions. Flag to user for confirmation.

## Workflow

### Step 1: Receive the user's input

The user typically sends both a PDF/image AND a DXF file. Always confirm: "Do you have a PDF or image for this drawing?" before falling back to DXF-only processing.

### Step 2: Convert PDF to image (if needed)

Use PyMuPDF (fitz) to render the first page at 3x zoom:

```python
import fitz
doc = fitz.open(pdf_path)
page = doc[0]
pix = page.get_pixmap(matrix=fitz.Matrix(3, 3))
pix.save(png_path)
```

### Step 3: VISION analysis

Call `vision_analyze()` on the image. Prompt must explicitly instruct:

**务必列出图纸上的每一个文字标注，包括小字、短字（如 baffle/挡板）。容易遗漏的情况：电机参数旁边的部件名、尺寸线附近的标注、电气柜旁的小字。先列出全部标注清单，再区分哪些是部件名、哪些是技术参数（0.6Mpa/3KW/220V等）。**

Structured prompt template:
```
这是一张[图纸类型]工程图纸。请仔细完成以下任务：

1. 列出图纸上的**每一个文字标注**（MTEXT文本），不论大小长短。先用表格列出全部标注原文，再标注每条是"部件名"还是"技术参数"。
2. 列出**每一个尺寸数字标注**（DIMENSION数字）。
3. 识别所有几何图形（矩形/圆/箭头/闪电符号等）。
4. 判断图纸布局和物料流向。
5. 识别有无对称件（左右/上下镜像布置）和同规格可合并项。
6. 识别图纸上未标注但明显存在的几何体（如电机座、滚筒、护栏等）。

注意：不要遗漏小尺寸文字（如 baffle、气缸附近短标注、电气柜旁小字）。每个部件名保留原始英文。
```

### Step 4: DXF MTEXT cross-verification (if DXF available)

Walk the DXF's nested blocks to extract exact MTEXT text at each position. Use the recursive entity walker from the existing `compute_bbox` / `_iter_all_geometry` pattern. Cross-check VISION's reads against the DXF ground truth.

Address discrepancies:
- If VISION misread a name or confirmed something DXF also has → correct it, include in main table.
- **If DXF found a label but VISION did NOT confirm it** (small text missed by VISION, or technical parameter like "0.6Mpa"/"3KW/220V") → **do NOT silently ignore**. Include it in the BOM as a `[?]` row (light orange, unverified), let the user decide whether it's a real component or should be removed/merged. Mark the source as "DXF-only — VISION未确认".

### Step 5: Compile BOM table

Group, merge, sort, append electrical cabinet. Deliver as markdown table.

### Step 6: Handle unlabeled items

If the drawing has distinct geometry (circular units, symmetric components) without labels, check the DXF for similar MTEXT-attached entities. If the DXF confirms an unlabeled match exists at a distinct position, flag it to the user for confirmation rather than silently including or excluding it.

## Pitfalls

- **VISION miscounts**: When VISION says `Card feeder` appears 3 times, cross-check with DXF MTEXT instance count. Visual crowding can cause VISION to overcount or undercount.
- **VISION misreads name**: `Transmit conveyor` instead of `Transition conveyor` — this happened in session 2026-06-18. Always verify against DXF MTEXT when available.
- **VISION hallucinates names**: If VISION reads a part name that is not confirmed by the DXF MTEXT, flag it as unverified.
- **DXF MTEXT traversal timeout**: Complex drawings with many nested blocks (>50) may time out on recursive traversal. Limit recursion depth or use a simpler MTEXT grep approach for large files.
- **DXF header extents ($EXTMIN/$EXTMAX) are unreliable** for bbox — they include ALL geometry including scattered LINEs and reference points. The old `compute_bbox` percentile trimming was designed to handle this, but it's irrelevant now since we don't render.
- **VISION misses a small label** (e.g. baffle near electrical cabinet): DXF found it but VISION didn't. Include as `[?]` row, flag for user confirmation. Do NOT silently drop it.
- **Forgetting to ask for PDF/image first**: The DXF is cross-reference only; the primary analysis comes from VISION on the user's PDF/screenshot. Always ask.
- **Electrical cabinet omission**: Always append to the BOM end as implied, even if not on the drawing. EXCEPTION: if the drawing explicitly shows and labels an Electrical cabinet, it's already in the table — don't duplicate.
- **Renumbering after corrections**: The user may correct item names or positions. Renumber # sequences after any insertion/deletion.

## Unlabeled geometry detection

When VISION spots a geometrically distinct item with no label (e.g. a circular unit that is clearly another Turning unit but unlabeled), check the DXF for similar entities at other positions. If the DXF confirms the existence of an identical geometric entity (same shape type, similar dimensions) at a different position, flag it to the user:

> "VISION noticed a second [shape type] at [position] that appears unlabeled. DXF confirms [same/larger/smaller] geometry exists there. Should this be listed as another [part name]?"

Do NOT silently include or exclude unlabeled items — always surface for human confirmation.

## Process when loaded

1. **Ask the user if they have a PDF or image** for the drawing. This is always step 1.
2. **If user provides PDF/image**: Convert to PNG (PyMuPDF), call `vision_analyze()` to extract all labels, dimensions, and geometry.
3. **If user also provides DXF**: Read MTEXT entities via nested-block recursion. Cross-check VISION reads against DXF ground truth. Correct any discrepancies.
4. **If user ONLY provides DXF** (no image): Fall back to DXF MTEXT-only extraction (names + dimensions from entities). Note: geometry without labels cannot be identified.
5. **Compile BOM table**: Group same-name same-spec items, accumulate qty, sort by material flow, append electrical cabinet. Use the markdown table format.
6. **Flag unlabeled geometry**: If VISION notices a geometrically distinct item with no label, check DXF for similar labeled entities. Ask the user to confirm.
7. **Deliver the BOM** as a markdown table in the reply.

## Related

- `packaging-machine-sales-cn` — loads this skill when the user wants a BOM for a packaging machine quote.
- `packaging-machine-naming` (domain knowledge) — the naming convention rules (HP/VP/BF/BS/FB) are stored in `~/.hermes/workspace/.learnings/domains/packaging-machines.md`.
- `ocr-and-documents` — alternate text extraction from PDFs; use for pure-text documents, not for engineering drawings with complex layout.
- BOM extraction workflow rules are also stored in persistent memory for quick reference across sessions.
