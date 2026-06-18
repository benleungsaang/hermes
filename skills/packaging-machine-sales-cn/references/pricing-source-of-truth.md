# Pricing — Source-of-Truth Pattern

> How B's packaging-machine pricing is stored and how to retrieve it
> without creating a duplicate / drifting copy.

## The rule (one-liner)

**The xlsx file at `~/.hermes/cache/documents/` is the canonical price
source. Read it with openpyxl on every query. Do NOT mirror the
price table into any `.md` file in `~/.hermes/workspace/`.**

**EXCEPTION — user override (added 2026-06-17):** When B explicitly
says "方案A：转成 md 走 qmd" / "不用保留权威源了" / similar, the
mirror-to-md pattern is **valid and preferred**. In that case:

- Convert xlsx → markdown once (openpyxl + write_file) into
  `~/.hermes/workspace/.learnings/domains/<topic>-price-table.md`
- Run `qmd update` to index it
- Quote/lookup goes through `qmd search` from then on
- The xlsx is no longer the source of truth — the .md is
- B has authority to switch the storage model at any time; do not
  push back, do not say "this risks drift" (B has decided, that's the
  decision)
- The earlier "B explicitly said storage is the agent's problem"
  quote still holds, but B also reserves the right to tell the
  agent WHICH storage. Both are B's call.

## Why

B explicitly stated on 2026-06-17: "你怎么记录是你的事情，我只要
我问我的时候，你能正确回复我价格即可." That is: storage is the
agent's problem, retrieval correctness is the user's success
criterion. So:

- **Default** (no explicit user direction): Mirror the xlsx to
  markdown → risks drift (B updates a price, the .md is now wrong,
  and a sales quote goes out with a 2-month-old number). Read xlsx
  every time → always correct, costs ~50ms. B has to edit ONE file
  (the xlsx) when prices change, not two.
- **Override** (user says to mirror): xlsx is treated as a one-time
  import; .md is the live source. qmd search does the lookup. B
  updates the .md by sending corrections ("VP-BF-180-06U 是
  ¥95,500 + 一体机"), not by re-uploading the xlsx.

## Stale-by-default anti-pattern to watch for

When the xlsx is mirrored to .md, B's correction pattern is
"tell the agent the new number, agent patches the .md". The
agent's job is to:

1. Patch the .md row (find by 画册型号, update cost/price/note)
2. Run `qmd update` so the index picks up the change
3. Confirm "VP-BF-180-06U ¥95,500 已更新"

Don't ask "do you want me to also update the original xlsx?"
unless B said to. The xlsx is read-only post-mirror.

## Where the price table lives

```
~/.hermes/cache/documents/doc_5791a0c51922_确认型号价格表.xlsx
```

Two sheets:
- `仅原始型号` — 55 machines, columns: 序号 / 画册型号 / 原始型号 /
  业务对外价（含税不含运）/ 成本价（含税不含运）/ 备注 / 单价（不含税）
- `含新型号` — 48 rows, columns: Model / OriginalModel (mapping
  table, no prices)

## How to read it

From `execute_code`:

```python
import sys
sys.path.insert(0, "/home/ubuntu/.local/lib/python3.12/site-packages")
from openpyxl import load_workbook
wb = load_workbook(
    "/home/ubuntu/.hermes/cache/documents/doc_5791a0c51922_确认型号价格表.xlsx",
    data_only=True,
)
ws = wb["仅原始型号"]  # the price-bearing sheet
# build a quick dict by 画册型号 (catalog code)
prices = {}
for row in ws.iter_rows(min_row=2, values_only=True):
    seq, catalog, orig, biz, cost, note, unit_no_tax = row[:7]
    if catalog:
        prices[catalog] = {
            "original_model": orig,
            "biz_price": biz,        # 业务对外价, 含税不含运 (0 = 询价)
            "cost_price": cost,      # 成本价, 含税不含运
            "unit_no_tax": unit_no_tax,  # 不含税单价 (some rows only)
            "note": note,
        }
```

## How B's "search by model" usually goes

User asks: "VP-BF-350B-08 多少钱" (or "VP-FB-320 成本多少").

Agent's job:
1. Build the dict (cache it for the turn — don't re-read xlsx on
   every lookup within the same session).
2. Return from the dict. If the catalog code is missing OR
   `biz_price == 0`, say "未报价 / 询价型号", not 0.
3. The 原始型号 column is the "factory internal code" — sometimes
   B asks for it ("拿 SZ-350 那个型号的成本给我"). Map back via
   `prices[catalog]["original_model"]`.

## Pricing fields B cares about, in priority order

When B says "多少钱" he usually means the **业务对外价** (what the
customer pays). When B says "成本" or "毛利" he means **成本价**.
The **不含税单价** is for accounting / invoice math (B2B 增值税
13% 抵扣链).

- 业务对外价（含税不含运） — for customer-facing quotes
- 成本价（含税不含运） — for 毛利 / 报价底线
- 不含税单价 — for 财务 / 发票 / 增值税核算
- 备注 — contains brand tag (珠冠 / 旋轴 / 瑞讯 / 运控 / 汇川) and
  promo info ("2025年10返1", "Elma 文字发送" etc.) — quote-relevant
  but not price; surface as supplementary

## Zero-price rows (询价型号)

13 rows have `biz_price == 0` (e.g. `VP-BF-210-08` / GDS210-08, the
non-`-B` variant). Per B's 2026-06-17 clarification, these are
simply "未有价格" — do NOT auto-flag as "停售" or "需另议". Just
say "暂无报价".

## FTB legacy typo handling (mandatory)

The 画册型号 column has many rows like `HP-FTB-...` and
`HP-FTB-BF-...`. Per the SKILL.md grammar table, **FTB is a legacy
typo for FB**. When B says "HP-FTB-370 多少钱":

- Read the price for `HP-FTB-370` from the xlsx (it IS there, no
  need to rewrite).
- In the reply to B, present the code as `HP-FB-370` (corrected)
  with the cost from the FTB row. Don't re-explain the typo every
  time — B knows, it's a waste of his reading time.

## The other 4 lessons B taught on 2026-06-17 about pricing context

1. **Use interval pricing for accessories, exact pricing for
   complete machines.** Small accessories get a ¥2-5万 range (room
   to negotiate, the user manually types the exact number per
   deal). Complete machines quote the exact cost / biz price
   straight from xlsx.
2. **Return both 成本价 and 不含税单价 in price queries** — B wants
   the cost basis AND the tax basis in one shot, not split across
   two replies.
3. **返点规则 ("10返1", "15返1") is in the 备注 column — surface
   it when B asks about margin, but don't volunteer it in basic
   price queries** (it's a sales-side tactic, not part of the
   public price).
4. **Don't write the price table into a `.md` file under
   `~/.hermes/workspace/`.** The xlsx IS the storage. If you
   wrote a copy once and B updates the xlsx, the .md is now
   wrong. B will notice and you'll be embarrassed.

## What to add to the skill body

None — the SKILL.md should stay product-knowledge-focused (model
grammar, selection logic, pitfalls). The "xlsx is the source of
truth" is an operational / storage rule, which lives here in
references. Future sessions load this file when answering the
first price query and have the recipe ready.
