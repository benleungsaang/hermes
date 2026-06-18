# DXF BOM Extraction — Line-by-Line Recipe

The canonical implementation is `~/.hermes/workspace/cad-bom/tools/cad_bom_extract.py`. This doc explains the *why* behind each block so future extensions don't have to reverse-engineer.

## 1. File open + sanity check

```python
import sys
sys.path.insert(0, "/home/ubuntu/.local/lib/python3.12/site-packages")
import ezdxf
doc = ezdxf.readfile(path)
print(doc.dxfversion)  # e.g. 'AC1027' = AutoCAD R2013
print(len(doc.layers), len(doc.blocks))
```

- `AC1015` = R2000, `AC1018` = R2004, `AC1021` = R2007, `AC1024` = R2010, `AC1027` = R2013, `AC1032` = R2018+
- The script's "if 0 entities and 0 blocks, tell the user" is a guard against a misnamed file or a non-DXF binary.

## 2. Recursive block walker (`_iter_all_entities`)

Three things this function must do:

1. **Skip already-visited blocks** — a block that references itself (or a cycle A → B → A) will infinite-loop without dedup. `visited: set[str]` covers this.
2. **Accumulate INSERT offset + scale at every level**. The child block's local coords (0,0) is its own origin; the parent's INSERT translates + scales. So child's global position = `parent.offset + ins.x * sx, parent.offset + ins.y * sy`.
3. **Recurse into paper space layouts too** (`doc.layouts`). CAD operators sometimes put text on a layout rather than modelspace.

```python
def walk(entities, block_name, depth=0, offset=(0.0, 0.0)):
    for ent in entities:
        if ent.dxftype() == 'INSERT':
            child_name = ent.dxf.name
            if child_name in visited: continue
            visited.add(child_name)
            ins = ent.dxf.insert
            sx = float(ent.dxf.get('xscale', 1.0))
            sy = float(ent.dxf.get('yscale', 1.0))
            child_offset = (offset[0] + ins.x * sx, offset[1] + ins.y * sy)
            yield from walk(doc.blocks.get(child_name), child_name, depth + 1, child_offset)
        else:
            yield ent, block_name, depth, offset
```

**Common bug**: forgetting to `visited.add(child_name)` → infinite recursion. Adding the check on a missing key is a defensive `try/except KeyError` because `doc.blocks.get(name)` returns `None` for unknown names.

## 3. MTEXT cleaning (`clean_mtext`)

DXF MTEXT raw string contains:

| Sequence | Meaning | Action |
|---|---|---|
| `\A1;` | font index 1 | drop the whole `\X...;` sequence |
| `\W0.707;` | width factor 0.707 | drop |
| `\P` | paragraph break (= newline) | replace with space |
| `\~` | non-breaking space | replace with space |
| `\{...}` | inline formatting (color, height) | unwrap, keep inner text |
| Multiple spaces | leftover after substitutions | collapse to one |

```python
def clean_mtext(raw):
    s = re.sub(r'\\[A-Za-z][^;]*;', '', raw)
    s = s.replace('\\P', ' ')
    s = s.replace('\\~', ' ')
    s = re.sub(r'\{\s*([^}]+?)\s*\}', r'\1', s)
    return re.sub(r'\s+', ' ', s).strip()
```

## 4. Title-block filter (`is_title`)

A title block contains metadata, not parts:

```python
TITLE_KEYWORDS = re.compile(
    r'^\s*图\s*\d+|'
    r'^\s*图\s*号|'
    r'^\s*技\s*术\s*要\s*求|'
    r'^\s*装\s*配\s*说\s*明|'
    r'^\s*说\s*明|'
    r'^\s*标\s*题\s*栏|'
    r'LAYOUT|ASSEMBLY\s*INSTRUCTION|TECHNICAL\s*REQUIREMENT',
    re.IGNORECASE
)
```

**Do NOT add `HP-FB` to this list** — model numbers are real BOM rows.

## 5. Size association

Brute-force nearest-DIMENSION. Tunable parameter: `ASSOC_MAX_DIST = 2000.0` (mm). 80% accuracy on real drawings; for the rest, manual review.

```python
def associate_sizes_to_texts(texts, dims, max_dist=ASSOC_MAX_DIST):
    for t in texts:
        candidates = sorted(
            ((dist(t['pos'], d['pos']), d['measure']) for d in dims
             if dist(t['pos'], d['pos']) <= max_dist),
            key=lambda x: x[0]
        )
        t['sizes'] = [c[1] for c in candidates]
        t['nearest_dist'] = candidates[0][0] if candidates else None
```

## 6. Name normalization (for clustering)

```python
NAME_PREFIX_RULES = [
    (r'\s+\d+\s*$', ''),                          # "1", " 2"
    (r'[\(\[\【\{]\s*\d+\s*[\)\]\】\}]\s*$', ''),  # "(1)", "（2）"
    (r'\s+No\.?\s*\d+\s*$', ''),                   # "No.1"
    (r'\s+#\s*\d+\s*$', ''),                       # "#1"
    (r'#\d+\s*$', ''),                             # "abc#1"
]
```

After normalization, `Transition conveyor 1` and `Transition conveyor (2)` both → `Transition conveyor`. Then group by name.

## 7. Clustering inside a name group

Two-pass:

1. Take the most-common size as "representative" (mode of the size list).
2. Each instance within ±3mm of the rep → main group. Anything beyond → "(尺寸异常)" sub-row.

## 8. Symmetric pair detection

Three signals (in trust order):

```python
def detect_symmetric_pairs(texts, dims):
    # Signal 1: same name appears ≥2 times with consistent size
    by_name = defaultdict(list)
    for t in texts:
        if not t.get('sizes'): continue
        by_name[normalize_name(t['text'])].append(t)
    for norm, instances in by_name.items():
        if len(instances) < 2: continue
        sizes = [t['sizes'][0] for t in instances]
        if max(sizes) - min(sizes) > SIZE_TOLERANCE_MM: continue
        # both left and right of the X-midline?
        all_x = [t['pos'][0] for t in texts]
        mid_x = sorted(all_x)[len(all_x) // 2]
        left = [t for t in instances if t['pos'][0] < mid_x - 100]
        right = [t for t in instances if t['pos'][0] > mid_x + 100]
        if left and right:
            yield norm
```

```python
SYMMETRIC_NAME_HINTS = re.compile(
    r'\b(2\s*in\s*1|2-1|twin|pair|dual|left|right|L/R|LH/RH)\b',
    re.IGNORECASE
)
def get_implied_count(name):
    # 2 in 1, twin, pair, dual, L/R, left, right → at least 2
    ...
```

Note: `double` is intentionally excluded. "Servo double pusher" is one part, not a pair. If you add new hints, test on real drawings first.

## 9. Geometry guess (`guess_unlabeled_geometry`)

```python
# Scan CIRCLE entities, find "orphan" diameters (no MTEXT for them).
# If Ø700-900 and ≥2 instances → guess "Turnable unit"
```

This is a v0.1 heuristic. Future versions may add:
- Rectangles with W:H ratio = 2:1 → guess "conveyor"
- Polylines with N vertices → guess "irregular bracket"

## 10. Excel output (`write_excel`)

Three row types, three fills:

```python
NORMAL  = no fill
GUESS   = PatternFill("solid", fgColor="FCE4D6")  # light orange
IMPLICIT = PatternFill("solid", fgColor="FFF2CC") # light yellow
```

**Sort order**: `(0=normal_or_guess, 1=cabinet)`, then `-count`, then `name`. The cabinet key is matched on substring `cabinet` in the canonical name (case-insensitive). This is the convention from B's 2026-06-17 instruction.

Columns (7 wide):

```
# | 部件名（归一化）| 代表名称 | 数量 | 尺寸 (mm) | 所有实例名 | 备注
```

Column widths: `[5, 32, 28, 8, 20, 50, 40]`.

## 11. The "header disclaimer" row 2

Always include this on the BOM header. B uses it to remind himself which color = which meaning when he opens an old file.

```
生成时间: ...  ·  浅黄色行 = packaging line 隐含件（电气柜等）  ·  浅橙色行 = 几何猜想部件（需人工确认：[?] 列）
```

## Common extension recipes

### Add a new symmetric hint

Edit `SYMMETRIC_NAME_HINTS` in `cad_bom_extract.py`. Test on a real drawing first — false positives are worse than misses.

### Add a new implicit component

Edit `suggest_implicit_components()`. The function returns a list of group-like dicts with `implicit: True`. They're sorted to the bottom automatically because the canonical_name contains `cabinet` (or `电箱`).

### Add a new geometry guess rule

Extend `guess_unlabeled_geometry()`. The function takes the doc + visited texts, and returns guess-rows with `guessed: True` and a `guess_reason` field that goes into the notes column.

### Change size association strategy

The brute-force nearest is in `associate_sizes_to_texts()`. To improve accuracy:
- Use a layer filter (e.g. only dimensions on layer `DIM` count)
- Use leader-line alignment (the dim's "defpoint" should be near the MTEXT's anchor)
- Use a scoring function (prefer dims in the same block, on the same layer)
