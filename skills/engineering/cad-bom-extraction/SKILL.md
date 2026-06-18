---
name: cad-bom-extraction
description: Extract structured BOM (Bill of Materials) from 2D CAD DXF/DWG engineering drawings. Accepts .dxf directly or .dwg via automatic ODAFC conversion. Use when the user provides a .dxf/.dwg file and wants a part list, when debugging DXF parsing where annotations/标注 are missing, or when the user mentions BOM / 部件清单 / 工程图 / 装配图 in a CAD context. Covers MTEXT/TEXT/ATTRIB/DIMENSION extraction, nested block recursion, text classification (part vs size vs annotation vs prefix), size-to-part spatial association, name normalization, and Excel output. Originally built for packaging-machine 总装图.
tags:
  - bom
  - cad
  - dxf
  - dwg
  - packaging
related_skills:
  - cad-drawing-bom
---

# CAD BOM Extraction from DXF/DWG

Extract a Bill of Materials from 2D CAD engineering drawings. The tool is `~/.hermes/workspace/cad-bom/tools/cad_bom_extract.py` (Python 3.12 + ezdxf + openpyxl). Run with:

```bash
python3.12 ~/.hermes/workspace/cad-bom/tools/cad_bom_extract.py <input.dxf|.dwg> [output.xlsx]
```

## Agent workflow — ALWAYS ask for PDF/image first

**This is the most important rule in this skill.** When the user sends a DWG or DXF:

1. **ASK first**: "你有对应的 PDF 或截图可以提供吗？用来做整体布局确认会准确很多。"
2. **Wait for user response** — do NOT run the extraction tool until the user replies.
3. **If user provides PDF**: convert to PNG, run VISION analysis, cross-check with DXF/DWG MTEXT, output corrected BOM. See "Vision-based extraction" below.
4. **If user says they don't have PDF**: only then run the DXF/DWG tool directly (DXF-only pipeline, no VISION cross-check).

**Why**: VISION reads layout and unlabeled geometry that DXF text extraction misses entirely. The DXF-only BOM is always a subset. Every session where you skip asking first will miss symmetric duplicates, unlabeled components, and layout context — and B will have to correct you.

**Pitfall**: Do NOT run `cad_bom_extract.py` as soon as the file arrives — the user may reply with a PDF within seconds. Wait for their answer.

## DWG → DXF auto-conversion (ODA File Converter)

The tool accepts `.dwg` files directly. On startup, it auto-detects `.dwg` extension and converts to DXF in a temp directory via `ezdxf.addons.odafc.readfile()`, then processes the result identically to a native DXF.

**Prerequisites** (one-time setup on this host):
- ODA File Converter AppImage at ~/Apps/ODAFileConverter_QT6_lnxX64_8.3dll_27.1.AppImage (82MB). Download from [ODA guest files](https://www.opendesign.com/guestfiles/oda_file_converter). Must be executable (chmod a+x).
- libfuse2: `sudo apt-get install -y libfuse2t64`
- Xvfb (for headless GUI): `sudo apt-get install -y xvfb`
- ezdxf.ini config at ~/.config/ezdxf/ezdxf.ini, `[odafc-addon]` section: `unix_exec_path = /path/to/AppImage`

**How it works**: The AppImage runs headless via Xvfb (ezdxf handles this internally with `_linux_dummy_display`). Input DWG is converted to temp DXF, then processing proceeds as normal.

**Troubleshooting**: If ODAFC fails with UnknownODAFCError:
1. Check libfuse.so.2 exists: `ldconfig -p | grep libfuse`
2. Check AppImage is executable
3. Check unix_exec_path in ezdxf.ini matches actual AppImage path
4. If Xvfb missing, AppImage opens GUI windows on server

Detailed setup: see `references/odafc-setup.md`.

## Drawing-style taxonomy (B 2026-06-17)

| Style | Indicator | Behavior |
|---|---|---|
| **Annotation-driven** | Has DIMENSION entities, MTEXT = part names | Standard path: MTEXT → classify as `part`, DIMENSION → spatial-associate to nearest MTEXT |
| **Text-driven** | Zero DIMENSION, MTEXT contains both part names AND bare numbers (e.g. `1000`, `1100`) | Digits are sizes, not parts. MTEXT classified as `size` goes into the size pool, not BOM |
| **Mixed** | Both styles on the same drawing | Both paths run; sizes merge into one pool |

**Diagnostic**: if `DIMENSION (有测量): 0` but `MTEXT (有文字): >10`, it's text-driven — the size pool is rebuilt from the text content.

## Text classification (classify_text)

Every MTEXT is classified into exactly one bucket before going anywhere:

| Class | Match rule | Action |
|---|---|---|
| `size` | `^\d+(?:[.,]\d+)?$` OR `^\d+\s*(MAX|MIN|mm|cm|m|Ø|⌀|D|±)$` | Extract number → add to size pool. **NOT** a BOM entry. |
| `annotation` | `^[A-Z][A-Z0-9_\-]*[A-Z0-9]$` AND no digit in text (FLOW, STRUCTURE, MAX as standalone) | Skip. **NOT** a BOM entry. |
| `prefix` | `^[A-Za-z][A-Za-z\-']{0,9}$` (single short word) | Look for nearby `part` to merge into (see prefix rules) |
| `part` | Default | Add to BOM. |

**Critical pitfall**: "含数字的全大写" (e.g. `SZ180`, `HP-FB-370`) is a **part** (model number), not annotation. The classification rule explicitly checks `not any(c.isdigit() for c in t)` before assigning annotation.

## Block recursion (the most common "0 entities found" cause)

DXF drawings commonly wrap content in nested INSERT blocks. A common AutoCAD convention:

```
SOONWIN (top-level block, the title-block frame)
  └─ 子块A
       ├─ MTEXT "HP-FB-370"
       └─ DIMENSION Ø802
  └─ 子块B
       └─ ...
```

If you only query `modelspace()`, you see 1 INSERT and 0 MTEXTs. You must walk the INSERT chain.

`cad_bom_extract._iter_all_entities(doc)` does this recursively. Key points:
- Maintain a `visited` set of block names to prevent cycles (A→B→A)
- Accumulate `offset = (offset[0] + ins.x * sx, offset[1] + ins.y * sy)` per recursion level so child entity positions reflect model-space coordinates
- Honor INSERT `xscale`/`yscale` in the offset accumulation
- Walk `paper space` layouts too (some users annotate in layout, not model space)

## MTEXT control-character cleaning (clean_mtext)

DXF MTEXT contains escape sequences that are NOT real text. Strip them all:

```python
s = re.sub(r'\\[A-Za-z][^;]*;', '', raw)   # \A1; \W0.707; \f Arial; ...
s = s.replace('\\P', ' ')                    # paragraph break → space
s = s.replace('\\~', ' ')                    # non-breaking space
s = re.sub(r'\{\s*([^}]+?)\s*\}', r'\1', s)  # {inline group} → group
return re.sub(r'\s+', ' ', s).strip()
```

Without `\\P` stripping, "Electrical\\Pcabinet" stays as two words.

## Prefix-merging (merge_prefix_to_part)

Detects 制图者 split a part name across two text entities ("Main" above + "conveyor 06" below). Rules:

- `max_dist = 1.5` (drawing units). Adjust to match the drawing's scale.
- **`|Δy| > 0.025` guard**: same-row close text is treated as "category + name" (e.g. `conveyor` + `Stack in-feed`), NOT a prefix.
- `Main` + `conveyor 06` (Δy ≈ 0.6) → merge into `Main conveyor 06`
- `Automatic` + `feeding conveyor` (Δy ≈ 0.04) → still merge (above the 0.025 floor)
- `conveyor` (Δy ≈ 0.02 from `Stack in-feed`) → NOT merged (below the floor)

## Name normalization (normalize_name)

Two-stage grouping: first by name, then by size within name.

**`NAME_PREFIX_RULES`** strips trailing digits and bracketed numbers:
```python
[r'\s+\d+\s*$',           # " 1", " 12" trailing
 r'[\(\[【\{]\s*\d+\s*[\)\]】\}]\s*$',  # "(1)", "【3】"
 r'\s+No\.?\s*\d+\s*$',  # "No.1"
 r'\s+#\s*\d+\s*$',      # "#1"
 r'#\d+\s*$']            # "abc#1"
```

`Transition conveyor 1/2/3/4` → all normalize to `Transition conveyor` → correctly grouped as one BOM row ×4.

**Special prefix strip**: before applying digit-stripping, peel off known prefixes:
```python
SPECIAL_PREFIXES = ['main', 'automatic', 'servo', 'auxiliary', 'sub']
```

Why: `Main conveyor 06` (post-merge) should normalize to `conveyor` (so it joins the `conveyor 01-06` group), but without prefix-stripping, the bare digit rule removes the `06` and we get `Main conveyor` — wrong.

## Size-to-part association (associate_sizes_to_texts)

For each MTEXT, find the nearest DIMENSION (or text-pool size) within `ASSOC_MAX_DIST = 2000` (drawing units). One DIMENSION can serve multiple MTEXTs — a single dimension line annotated once is shared by all parts of equal length.

**Known limitation**: assembly-total dimensions (e.g. `8535` on the left margin) get assigned to whichever part is geometrically closest, even when semantically the total applies to a different scope.

## BOM output rules (write_excel)

Three row types:

| Type | Color | Prefix | Source |
|---|---|---|---|
| Verified (text + size) | white | (none) | Standard classification |
| Guessed (geometry only) | light orange (`FCE4D6`) | `[?]` | `guess_unlabeled_geometry` |
| Implicit (packaging-line default) | light yellow (`FFF2CC`) | `[隐]` | `suggest_implicit_components` |

**B's hard rules** (2026-06-17/18, non-negotiable):

1. **Electrical cabinet row always last** in the main table, regardless of count, whether it came from MTEXT (annotated) or from `suggest_implicit_components`. Sort key: `is_cabinet → last`, otherwise `-count`.
2. **HP-FB-370, SZ180, etc. are real BOM entries** (the machine itself = 1 unit). No "（项目）" annotation, no special handling — they go into the table like any other part. Only filter `is_title()` keywords like "图号 / 装配说明 / 技术要求".
3. **Quantity = max(text instances, geometric instances) for symmetric parts**. `2 in 1 transition conveyor` text appears once but the drawing shows 2 → count=2. The "symmetric" detection uses X-coordinate distribution across the page midline; for text-only cases use the `SYMMETRIC_NAME_HINTS` regex below.
4. **`SYMMETRIC_NAME_HINTS` regex** = `\\b(2\\s*in\\s*1|2-1|twin|pair|dual|left|right|L/R|left\\s*&\\s*right|LH/RH)\\b` (case-insensitive). `double` is **deliberately excluded** — `Servo double pusher` is a single-part name, not a pair.
5. **同类型同规格部件合并**：B 2026-06-18 校准。相同名称模式且规格一致的部件合并为一行，数量累加，名称用编号范围表示（如 Main conveyor 2-3，均为 600×1000mm → ×2；非连续编号如 Sinking conveyor 1-2,4 → ×3）。不要分列多个相同规格行。
6. **Electrical cabinet 始终最后**：B 2026-06-18。Electrical cabinet 始终排主表最后一行的位置，不受物料流向顺序影响。即使图纸上有标注，仍然排最后（但不是隐含件，不需浅黄底色[隐]前缀）。
7. **Infeed conveyor 不列主表**：B 2026-06-18。Infeed conveyor 不放入主 BOM 表，改为放在主表下方的"忽略项"区段（灰色斜体），标记为"按要求忽略"。
8. **每项必须标注位置**：B 2026-06-18。每个 BOM 条目的"说明"栏必须有明确位置描述（如"主输送线最右侧""4支线各一，包装主机位置"），从 VISION 布局分析中提取，不允许笼统描述。
9. **Name from DXF MTEXT is authoritative** for exact spelling — VISION may misread characters. When DXF and VISION disagree on a name, trust DXF.

## Geometric guessing (guess_unlabeled_geometry)

Current rule: scan CIRCLE entities, bucket diameters to 5mm, find diameters 700-900mm appearing ≥2 times with no corresponding MTEXT — guess "Turnable unit". Output is light-orange + `[?]` prefix; user manually confirms.

The framework supports more rules — extend `GEOMETRY_GUESS_RULES` or branch on CIRCLE/LINE/RECT geometry with similar "shape + size + frequency" patterns.

## Vision-based extraction (B's confirmed workflow)

**Canonical pipeline** — run after user provides PDF:

1. Convert PDF → PNG with PyMuPDF (fitz) at 3x zoom:
   ```python
   import fitz
   doc = fitz.open(pdf_path)
   pix = doc[0].get_pixmap(matrix=fitz.Matrix(3, 3))
   pix.save(png_path)
   ```
2. Call `vision_analyze()` on the PNG with prompt asking for all MTEXT labels, DIMENSION numbers, geometry, and position relationships.
3. Cross-check VISION output against DXF/DWG MTEXT — correct name spellings (DXF is ground truth for exact text) and fix quantities (VISION is ground truth for symmetric duplicates).
4. Compile BOM: DXF names + VISION-verified quantities + DXF dimensions + position descriptions.
5. Always append `Electrical cabinet（总电箱）` at end as implicit item.
6. Send xlsx via Feishu (send_message with MEDIA: prefix).

**Key insights from practice**:
- **DXF counts unique text instances** — symmetric components (two packaging machines, two pushers) read as ×1. VISION sees the real layout count.
- VISION may misread characters (`连续数料` vs DXF's `连续拨料`). DXF text is the ground truth for spelling.
- VISION reads unlabeled geometry that DXF can never see.
- After presenting the BOM, ask B to confirm accuracy before finalizing.

**Vision prompt template**:
```
这是一张包装机工程图纸。请仔细列出所有部件名称（MTEXT文本标注）、所有尺寸数字标注、几何图形（矩形/圆/箭头等）。用中文列出完整BOM表，包括每个部件的名称、规格尺寸和位置关系。
```

## When the tool gets it wrong — diagnostic checklist

1. **0 entities found?** → Block recursion. Was the drawing wrapped in a SOONWIN or similar top-level block? Read `_iter_all_entities`.
2. **Pure numbers showing up as parts?** → Classification rule missing. Verify `classify_text` for that input.
3. **Two parts merged into one?** → Prefix-merge too aggressive. Check `|Δy|` between the two text entities.
4. **Conveyor 01/02/03 split into 3 groups?** → Name normalization rule. Check output of `normalize_name` for each.
5. **Sizes assigned to wrong parts?** → Spatial association threshold or layout quirks.
6. **CABINET not at the bottom?** → Sort key conflict. Check `sort_key` in `write_excel`.

## Running the tool — gotchas

- **Python version**: ezdxf/numpy are installed for Python 3.12 (`/usr/bin/python3.12`). The default `python3` is 3.11 and will fail with cryptic numpy ABI errors. Always use `python3.12`.
- **DWG input**: works exactly like DXF input — the tool auto-converts via ODAFC. First run may take a few seconds longer.
- **Output location**: if not specified, output is `<input>.bom.xlsx` next to the input.
- **Iterate, don't re-architect**: each user correction is usually a 1-3 line change in one function. The classification / merge / sort layers are independent.

## Files

- `tools/cad_bom_extract.py` — main extractor (DXF/DWG pinpoint mode)
- `scripts/dwg2pdf.py` — DWG → A3 PDF quick render via PyMuPdfBackend (for visual reference only, not used in BOM pipeline)
- `scripts/render_dxf_for_vision.py` — DXF → vision-readable PNG
- `references/drawing-style-examples.md` — concrete examples of each drawing style
- `references/correction-history.md` — chronological log of B's corrections
- `references/odafc-setup.md` — ODA File Converter setup steps, test commands, and failure troubleshooting
- `references/ezdxf-rendering-pitfalls.md` — rendering failure modes (historical reference, not for use)

## DWG quick-render (for visual reference, not BOM)

`scripts/dwg2pdf.py` converts a DWG to A3 PDF via the ezdxf + PyMuPdfBackend pipeline:
`dwg → ODAFC → DXF → Frontend.draw_layout → PyMuPdfBackend.get_pdf_bytes → .pdf`

Limitations:
- Chinese text may render as boxes (missing CJK font in ezdxf pipeline)
- Complex block-heavy drawings (>100 blocks) may take 30-60s
- The DIMASSOC warnings from ODAFC are normal and non-fatal
- This is NOT a substitute for the user's AutoCAD-exported PDF for VISION analysis
