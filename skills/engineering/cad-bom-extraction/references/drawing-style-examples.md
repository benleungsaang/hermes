# Drawing-style examples (B 2026-06-17)

Concrete examples observed across draw_1 / draw_2 / draw_4. Use these as reference dumps when diagnosing "what kind of drawing is this?".

## draw_1 (annotation-driven, simple)

```
DXF version: AC1027
图层: 60, 块: 814
MTEXT (有文字): 7
DIMENSION (有测量): 9
```

Distinct part names: `Transition conveyor 1/2/3/4`, `Feeding conveyor`, `HP-FB-370L`, `Turnable unit`. All have corresponding DIMENSION entities. `Electrical cabinet` not drawn → tool appends it as implicit (light yellow).

**Lesson**: 60 layers + 814 blocks but only 7 MTEXT / 9 DIMENSION. The block count looks alarming; don't conclude "complex drawing" from it. Look at entity-type counts.

## draw_2 (annotation-driven, nested blocks)

```
DXF version: AC1027
图层: 22, 块: 182
MTEXT (有文字): 0    ← BEFORE fix
DIMENSION (有测量): 0  ← BEFORE fix
```

After block recursion:

```
MTEXT (有文字): 8
DIMENSION (有测量): 13
```

Part names extracted: `Electrical cabinet ×2`, `∅802 ×2`, `2 in 1 transition conveyor`, `Feeding conveyor`, `HP-FB-370`, `Servo double pusher`.

**Lesson**: When MTEXT and DIMENSION are both 0 despite nonzero block count, the content is INSIDE blocks. The recursive walker finds it.

## draw_4 (text-driven, mixed)

```
DXF version: AC1027
图层: 4, 块: 3
MTEXT (有文字): 42
DIMENSION (有测量): 0
```

42 MTEXT — but only ~10 are real parts. The other ~30 are:
- bare digits: `1000`, `1100`, `1800`, `2200`, `1435`, `1500`, `3500`, `7844`, `8535` → these are sizes
- digit+suffix: `1250 MAX` → size
- all-caps: `FLOW ×5`, `STRUCTURE ×2`, `MAX` (standalone) → annotations
- short words: `Main`, `Automatic`, `conveyor` (alone) → prefixes (need to merge)
- all-caps-with-digits: `SZ180` → part (model number)

**Lesson**: A `DIMENSION: 0` result with high `MTEXT: N` is the text-driven signature. Don't try to do dimension-based association — fall back to spatial-association with text-pool sizes.

## Diagnostic dump (use this when starting a new draw)

Run this and read the output before running `cad_bom_extract.py`:

```python
import sys
sys.path.insert(0, '/home/ubuntu/.local/lib/python3.12/site-packages')
sys.path.insert(0, '/home/ubuntu/.hermes/workspace/cad-bom/tools')
import ezdxf
import cad_bom_extract
doc = ezdxf.readfile('<file>.dxf')
texts, dims = cad_bom_extract.extract_entities(doc)
for t in sorted(texts, key=lambda t: (round(t['pos'][1], 1), t['pos'][0])):
    print(f'  {t["pos"]} [{t["_class"]:10s}] "{t["text"]}"')
```

Look for:
- `0` in any bucket → block recursion or wrong classification
- All positions clustered near origin → units issue (multiplier needed)
- All text classified as `size` → pattern in `classify_text` doesn't match this drafter's style (extend `RE_PURE_NUMBER` / `RE_NUMBER_WITH_SUFFIX`)

## Output format reference

`cad_bom_extract.py` writes `<input>.bom.xlsx` with these sheets:

| Sheet | Contents |
|---|---|
| `BOM` | Main table. Columns: #, 部件名(归一化), 代表名称, 数量, 尺寸(mm), 所有实例名, 备注. Cabinet always last. Implicit rows light yellow, guessed rows light orange. |
| `未关联尺寸` | MTEXT within ASSOC_MAX_DIST of no DIMENSION. Useful for catching parts where the spatial association failed. |

The main table's `#` column is the row number, NOT an internal id. Use the part name to look up; the count column distinguishes identical parts at different positions.
