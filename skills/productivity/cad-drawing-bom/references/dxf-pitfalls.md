# DXF Export Pitfalls — From Real Drawings

Pitfalls observed when extracting BOMs from real customer drawings (B's packaging machine workflow, 2026-06). This is a knowledge bank of "what can go wrong on the export side" — i.e. problems caused by the CAD operator, not by the parser.

## 1. Top-level block is the whole drawing (most common)

**Symptom**: `len(doc.modelspace().query('MTEXT')) == 0` and `len(doc.modelspace().query('DIMENSION')) == 0` and there's a single `INSERT` with block name `<CompanyName>` (e.g. `SOONWIN`).

**Cause**: The CAD operator drew everything inside a top-level block named after the company, and that block references sub-blocks for each assembly. The DXF export was done correctly — the file is fine; the parser is just not walking deep enough.

**Fix**: Recurse into `INSERT` blocks with offset accumulation. See `extraction-recipe.md` §2.

**Verification**: After walking, expect `len(mtexts) > 0`. If still 0, the file is probably a title-block-only template, not an assembly drawing.

## 2. PDF-to-DXF (raster tracing)

**Symptom**: Entities exist (lots of LINE / LWPOLYLINE / CIRCLE) but there are 0 MTEXT and 0 DIMENSION. Labels appear visually on the drawing (text in images) but not as CAD entities.

**Cause**: The drawing was originally a PDF, scanned or exported, then "converted to DXF" by a vectorizer that traced the geometry but couldn't recover the text. Common with old drawings, drawings from non-CAD sources (Illustrator, Corel), or when the customer runs PDF → DXF through an online converter.

**Fix**: There is no fix in pure CAD parsing. Either:
- Ask the customer for the original DWG (not the PDF-converted DXF)
- Use OCR (Tesseract) on the raster portions — out of scope for this skill
- Manually transcribe part names

**Detection**: Open the DXF in a text editor. If you see lots of LWPOLYLINE with many vertices and no MTEXT, suspect a traced PDF.

## 3. Wrong DXF export options in AutoCAD

**Symptom**: 0 entities, or entities without their text content.

**Cause**: The CAD operator's export options exclude certain entity types. The relevant AutoCAD dialog ("Save As DXF") has checkboxes for "Select objects" vs "All objects" and may include/exclude layers.

**Fix**: Re-export with "All objects" and **R2013 DXF** or later. Avoid pre-R14 DXF (text becomes geometry). Steps for AutoCAD 2018+:

1. File → Save As
2. Format: `AutoCAD 2013 DXF (*.dxf)` (or newer)
3. Tools → Options → DXF Options: ensure "Select objects" is OFF (use "All")
4. Export

**B's note** (2026-06-17): he uses AutoCAD, and the bad export was a one-time mistake. Most of his drawings are now exported correctly.

## 4. MTEXT control characters leaked through

**Symptom**: Part names show as `\{Transition conveyor 2\}` or `Transition conveyor\\P2` instead of `Transition conveyor 2`.

**Cause**: The `clean_mtext` function didn't run, or its regex doesn't cover the specific control character used.

**Fix**: The `clean_mtext` recipe in `extraction-recipe.md` §3 covers the common cases (`\A1;`, `\W0.707;`, `\P`, `\~`, `\{...\}`). If a new control character appears, add it to the function. Common others:
- `\H3.5;` — text height
- `\C1;` — color index
- `\U+00B0;` — Unicode codepoint (degree symbol)
- `\Lunderline\lp1;` — underline / strikethrough

## 5. Block INSERT with rotation

**Symptom**: Entities inside a rotated block appear at unexpected positions, breaking size association.

**Cause**: The block was inserted with a non-zero rotation angle. The child's local coords are pre-rotation; to get the actual model-space position you need to apply a 2D rotation matrix.

**Fix**: The current walker handles `xscale/yscale` but not rotation. For v0.1, this is acceptable because most packaging line drawings don't use rotation. If you hit it, add:

```python
import math
angle = math.radians(float(ent.dxf.get('rotation', 0.0)))
cos_a, sin_a = math.cos(angle), math.sin(angle)
rotated_offset = (
    offset[0] + ins.x * sx * cos_a - ins.y * sy * sin_a,
    offset[1] + ins.x * sx * sin_a + ins.y * sy * cos_a,
)
```

## 6. Duplicate block definitions

**Symptom**: Same part name appears with the same text but at different positions in different blocks, leading to false "symmetric" detection.

**Cause**: The CAD operator copy-pasted a sub-block and forgot to clean it up. Two physically-identical parts share the same block definition but are inserted at different positions.

**Fix**: This is actually correct behavior — the parts ARE symmetric, so the BOM should list them twice. The current detection picks them up via `detect_symmetric_pairs`.

## 7. Dimensions in paper space, not model space

**Symptom**: Some DIMENSIONs are detected but their `defpoint` is at (0,0) or far from any MTEXT.

**Cause**: The CAD operator placed dimensions on a layout (paper space) rather than model space, and the dim's position is in the layout's coord system, not the model's.

**Fix**: The walker already iterates layouts (`doc.layouts.names()`). The offset accumulation would need to be reset for each layout. v0.1 doesn't do this perfectly. For most real drawings, dimensions are in model space, so this rarely matters.

## 8. ATTRIB vs MTEXT (block attributes)

**Symptom**: Custom block attributes (e.g. `PART_NAME`, `DRAWING_NO` defined in a title block) are not picked up.

**Fix**: The walker already handles `ATTRIB` and `ATTDEF` types. Check `extract_entities()` for the ATTRIB/ATTDEF branch.

## 9. Unicode in part names

**Symptom**: Chinese characters appear as `?` or `\uXXXX` escape sequences in the output Excel.

**Cause**: The DXF was saved with a different encoding than expected, or the underlying `ezdxf` defaults to ASCII.

**Fix**: ezdxf handles Unicode correctly by default in modern versions. If you see escapes, the file itself is broken — re-export from AutoCAD with the system codepage set to UTF-8 or to the local Chinese codepage (GBK / GB18030).

## 10. Why "I just see a single big block" matters

When a CAD operator opens a DXF and sees "a single big block" that they must double-click to enter, that's **not** a sign of a broken file. It's the standard pattern for drawings built from nested blocks. Recurse, don't give up.

**B's verification step** (2026-06-17): "I open the DXF in AutoCAD, I see 'SOONWIN' as a single block, I double-click to enter, I see more blocks, I double-click again, I see the actual content. This is normal. Your script should do the same."
