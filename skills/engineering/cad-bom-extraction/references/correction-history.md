# Correction history (B 2026-06-17)

Chronological log of B's corrections during the v0.1 → v0.3 development of `cad_bom_extract.py`.
Each entry: what was wrong → what changed in code → the rule it produced.

## 1. 0 entities found in draw_2.dxf
**Symptom**: DXF was reported as 22 layers + 182 blocks but `MTEXT: 0, DIMENSION: 0`. Image inspection showed clear annotations (HP-FB-370, ∅802, etc.).

**Root cause**: Drawing wrapped everything inside a top-level INSERT block `SOONWIN` (a title-block frame). `modelspace()` only saw that one INSERT. The actual content was in nested child blocks.

**Fix**: `_iter_all_entities(doc)` walker that recurses into INSERT → block_record, with `visited` set for cycle protection and accumulated `offset = (offset.x + ins.x * scale, offset.y + ins.y * scale)` so child positions are in model-space coordinates.

**Rule**: If a DXF reports 0 text/dimension entities but has >0 blocks, the content is almost certainly nested inside INSERTs. Block recursion is the first thing to add.

## 2. Position math wrong even after block recursion
**Symptom**: child entity `pos` came back in block-local coordinates, not model-space, breaking the spatial size-association.

**Fix**: pass an `offset` tuple through the recursion; each INSERT adds `ins.x * xscale, ins.y * yscale` to the offset.

**Rule**: Block recursion needs to thread position offset, not just enumerate entities.

## 3. `Electrical\Pcabinet` stayed as one weird string
**Symptom**: `clean_mtext` stripped `\A1;` and `\W0.707;` but not `\P` (paragraph break). Output had `Electrical\Pcabinet` as if it were one part name.

**Fix**: `s = s.replace('\\P', ' ')` and `\\~` → ' ' in `clean_mtext`. Also collapse multiple whitespace via `re.sub(r'\s+', ' ', s)` at the end.

**Rule**: DXF MTEXT control characters: `\A<align>;`, `\W<width>;`, `\f<font>;`, `\H<height>;`, `\P` (paragraph), `\~` (NBSP), `{group}`. Strip all of them.

## 4. draw_4 — every digit became a "part"
**Symptom**: BOM listed `1000`, `1100`, `1800`, `2200`, `1435` as parts. They were dimensions, not part names.

**Root cause**: This drawing was text-driven (0 DIMENSION entities); the dimension values were written as bare MTEXT numbers.

**Fix**: introduced `classify_text()` returning one of `size | annotation | part | prefix`. `size` extracts the numeric value into a separate `sizes` pool; `associate_sizes_to_texts` now feeds from both DIMENSION entities AND the text-pool.

**Rule**: Drawing style detection is a prerequisite for classification. `if DIMENSION_count == 0 and MTEXT_count > 5: text-driven mode`.

## 5. `FLOW`, `STRUCTURE`, `MAX` listed as parts
**Symptom**: All-caps single-word MTEXTs treated as parts.

**Fix**: `RE_ALL_CAPS` → `annotation` class. But the rule must NOT fire on `SZ180` (model number with digits) — added `and not any(c.isdigit() for c in t)` guard.

**Rule**: Annotation = "ALL CAPS, no digits". Anything with digits in all-caps form is a part.

## 6. `conveyor` got merged into `Stack in-feed` as "conveyor Stack in-feed"
**Symptom**: `conveyor` (standalone MTEXT at one location) got prefixed into `Stack in-feed` because they were 0.02 drawing-units apart.

**Root cause**: 制图者 used "category + name" layout: `conveyor` (the kind) and `Stack in-feed` (the specific part) are placed on the same row. Prefix-merge should not fire for same-row close text.

**Fix**: added `if abs(pt['pos'][1] - best['pos'][1]) < 0.025: continue` in `merge_prefix_to_part`.

**Rule**: Prefix-merge requires `|Δy| > 0.025` (drawing units). Below that, treat as "category + name", not prefix.

## 7. `Servo double pusher` × 2 (wrong — it's 1)
**Symptom**: `double` in `SYMMETRIC_NAME_HINTS` triggered count=2 for `Servo double pusher`, which is a single unit.

**Fix**: removed `double` from the symmetric-hint regex. Kept `2 in 1`, `twin`, `pair`, `dual`. `left`/`right`/`L/R` still count as a pair (because they're half of a labeled pair).

**Rule**: `double` is ambiguous. Only the explicit pair-naming patterns trigger ≥2.

## 8. `HP-FB-370L` was labeled "（项目）" in the BOM
**Symptom**: B's earlier rule (2026-06-16) marked HP-FB-XXX as a "project" entry, with a suffix. B clarified: it's a real BOM entry like any other part, count=1, no annotation.

**Fix**: removed the "（项目）" annotation in `write_excel`. HP-FB-XXX is now a regular row.

**Rule**: Model numbers (HP-FB-370L, SZ180, VP-BF-180) are real BOM rows. No special suffix. Only filter `is_title()` keywords: 图号, 装配说明, 技术要求, LAYOUT, ASSEMBLY INSTRUCTION, TECHNICAL REQUIREMENT.

## 9. `Electrical cabinet` should be last regardless of count
**Symptom**: With count=2, cabinet was second by `-count` sort. B wanted it always at the bottom.

**Fix**: `sort_key` returns `(is_cabinet, -count, name)` — cabinet gets `is_cabinet=1` and sorts last.

**Rule**: Packaging-line convention: cabinet is "infrastructure", listed after actual mechanical components.

## 10. `Main conveyor 06` lost the `06` after normalization
**Symptom**: prefix-merge produced `Main conveyor 06` correctly, but `normalize_name` then stripped the trailing `06` (because of `\s+\d+\s*$` rule), leaving `Main conveyor`. Then it wouldn't group with `conveyor 01-05`.

**Fix**: Added a prefix-strip step at the start of `normalize_name`:
```python
SPECIAL_PREFIXES = ['main', 'automatic', 'servo', 'auxiliary', 'sub']
if lower.startswith(sp + ' '): out = out[len(sp)+1:].strip(); break
```
After peeling `Main`, normalize sees `conveyor 06` → strips to `conveyor`, which joins the conveyor group. The `rep_name` field still shows the full `Main conveyor 06` (longest member name wins via Counter).

**Rule**: Prefix-merge + digit-strip is order-sensitive. Strip known prefixes BEFORE applying digit-stripping rules, so the digit-strip operates on the real part name.

## 11. `SZ180` disappeared (filtered as annotation)
**Symptom**: All-caps-with-digits got classified as annotation due to `RE_ALL_CAPS` matching.

**Fix**: `RE_ALL_CAPS` rule now requires `not any(c.isdigit() for c in t)`. `SZ180`, `HP-FB-370`, etc. fall through to `part`.

**Rule**: ALL CAPS with embedded digits is a model number, not a label. Annotation = strictly letters-only all-caps.

## 12. `2 in 1 transition conveyor` count=1, should be 2
**Symptom**: Text only mentions this once, but the drawing shows 2 instances.

**Fix**: `SYMMETRIC_NAME_HINTS` regex catches "2 in 1" → forces `implied_count = 2`. Then `group_components` does `count = max(matched, implied)`.

**Rule**: Part name with embedded count hint (`2 in 1`, `twin`, `pair`, `dual`, `L/R`) → use the hint as a lower bound on count.

## 13. Five rounds of "parse more from DXF" beat by one vision call (B's reversal)
**Symptom**: After v0.1 → v0.3, the extractor was 90% accurate on text-driven drawings (draw_4) and ~60% on annotation-driven drawings (draw_1, draw_2). Each round of fixes added rules for one more corner case. B pointed out: vision reading a rendered PNG of draw_4 saw 90%+ of parts in one shot — including Storage unit, conveyor 07/08, Servo machine, which the DXF text extraction has no way to know about (no MTEXT points to them).

**Root cause**: The pipeline was DXF-text-only. Vision was being treated as a "verification step" instead of the primary path. The renderer had 3 unaddressed failure modes (auto-scaling to empty model space, INSERT offsets in tiny regions, missing Chinese font fallback) that made vision calls return near-empty results — which the agent then interpreted as "vision can't see it" rather than "the render is broken".

**Fix**: Reversed the pipeline. Vision is now stage 1 (render PNG → vision_analyze → part list with positions). DXF is stage 2 (pinpoint lookup at each vision-reported position, not a full re-scan). Output includes confidence tags from a 2x2 cross-check matrix (vision-found × DXF-found).

**Rule**: When a multi-round text-parsing effort plateaus, ask "what other modality could read this directly?" For engineering drawings, that modality is vision on a properly-rendered PNG. The renderer is the bottleneck, not the parser.

**Renderer fixes** (scripts/render_dxf_for_vision.py):
1. Pre-compute content bounding box by recursively walking blocks (with INSERT offset accumulation), then `ax.set_xlim`/`ax.set_ylim` with 10% padding. Do NOT rely on ezdxf's auto data-limits.
2. Force Chinese font: `matplotlib.rcParams['font.sans-serif'] = ['WenQuanYi Zen Hei', 'Noto Sans CJK SC', 'DejaVu Sans']`.
3. Adjust figure aspect ratio based on content bbox (30x14 for wide drawings, 14x30 for tall, 24x16 default).

**Verification step after every render**: list text bounding boxes; if any text box is <1% of the image area, the render is too sparse — re-crop tighter.
