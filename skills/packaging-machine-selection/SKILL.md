---
name: packaging-machine-selection
description: "Act as a packaging-machine consultant when a sales engineer user (or a simulated customer role-play) describes a product and packaging requirement. Decide the machine family (VFFS / HFFS / Premade Bag / Sleeving / Cartoning / Palletizing), the specific model line, and the measuring / feeding / sealing accessories. Use when the user describes 'a product that needs packaging' and asks for 'which machine, what model, how much'. The user's domain-specific knowledge base lives at ~/.hermes/workspace/.learnings/domains/packaging-machines.md — read it FIRST, treat it as the source of truth for the user's company conventions."
version: 0.1.0
author: Hermes Agent (from session with user BBBBB)
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [packaging, machinery, sales, quoting, vffs, hffs, premade-bag]
    category: domain-knowledge
---

# Packaging machine selection — consultative role

Help a packaging-machine sales engineer pick the right machine family, model,
and accessory stack for a customer's product + packaging requirement. The
canonical knowledge base for this user's company lives at
`~/.hermes/workspace/.learnings/domains/packaging-machines.md` and the
supporting accessory catalog at
`~/.hermes/workspace/.learnings/domains/packaging-machine-accessories.md`.

**Always read those two files first** — they encode the user's actual
company conventions, naming rules, and corrections. Generic packaging
knowledge is not enough; this user has a specific catalog and
specific traps.

## When to load this skill

- User describes a product (material, dimensions, weight per piece, quantity
  per pack) and asks which packaging machine / which model / how much
- User is role-playing a customer scenario and asking "what would you
  recommend for X"
- User asks to look up a model code, decode a model code, or compare models
- User provides a new customer requirement that needs to be turned into a
  model + price quote
- User attaches a CAD drawing or BOM that needs to be turned into a machine
  configuration

## Core flow

```
1. Read the knowledge base
   - domains/packaging-machines.md  (machine catalog, naming, decision tree)
   - domains/packaging-machine-accessories.md (measuring / bag-handling / gas / lifter)
   - /home/ubuntu/.hermes/cache/documents/  (the company's machine JSON, if relevant)

2. Decode the request
   - What is the product? (material, form factor, fragility, density)
   - Single-piece spec + bulk spec → number of pieces per pack
   - "Pouches" + fixed dimensions → premade bag (NOT film bag)
   - Vacuum / nitrogen flush / zipper / stand-up needed? (drives station count)
   - Target throughput? (drives cut type, speed class)

3. Pick the family — the bag type is the key signal
   - bag (film, roll-fed) → VFFS (立式 VP-* / VP-FB-*)
   - pouch / premade bag / stand-up pouch → Premade Bag (给袋机 VP-BF-* / HP-BS-*)
   - pillow bag with regular solid product → HFFS (枕式 HP-FB-*)
   - big item where pouch can't fit → Sleeving (套袋 HP-BS / VP-BS, push-in not fill)
   - secondary carton → Cartoning; pallet → Palletizing

4. Pick the model line
   - VFFS / HFFS: film width = (pouch width + 10~15mm) × 2; never go below 10mm seal margin; consult engineering if near the machine's max film width
   - Premade Bag: bag width is the primary spec; bag length secondary; stations depend on extras (6 = standard incl. zipper / open-bottom; 8+ for vacuum/N₂/double-feed)
   - HFFS extras: cut type (rotary = fastest but can't pack tall products, box-motion = best for tall, up-down = cheap but must stop), film loader (top = fast for stable shapes, bottom = stable for rolling products)

5. Pick the accessories
   - Measuring: screw feeder (powders + density-stable fine particles), volumetric cup (only cheap + dry + non-fragile + non-hygroscopic), net-weight electronic scale (hygroscopic / variable-density), multihead weigher (fragile / high-precision solids), liquid pump (fluids/pastes) — SAME measuring tool works on VFFS and Premade Bag; do not distinguish by machine
   - Lifter / Z-elevator / C-elevator: required auto-feeder for both VFFS and Premade Bag
   - Fragile product (cookies, nuts): anti-break multihead weigher mandatory
   - Vacuum / N₂ flush / air-evacuation: usually 8+ stations unless space allows integration on 6

6. Quote
   - Pull model price from the catalog JSON
   - Sum accessories (lifter + measuring + extras)
   - Flag missing prices as TBD; do NOT guess
   - Flag the manual-vs-machine packing density gap (machine ≈ 70-80% of manual pack)

## Critical pitfalls (from this user's corrections)

1. **"Single-piece spec given + bag spec given" means MULTIPLE PIECES PER
   BAG = bulk / granular, NOT a single rigid product.** Always re-read the
   request and confirm "pieces per bag" before recommending HFFS. Past
   session mistakenly suggested HP-FB pillow wrapper for cookies that came
   8-26 per bag.

2. **"Pouches" almost always means premade bags in this industry**, not
   generic bags. The user has a SOUL rule: bag = film (VFFS), pouch =
   premade (Premade Bag). Follow that.

3. **Both VFFS and Premade Bag handle the same bulk products** (powders,
   liquids, granules, pieces). The choice between them is driven by BAG
   TYPE, not by product. Past .md said "bulk → VFFS" — that's wrong by
   this user's practice.

4. **6-station Premade Bag is NOT "no-extras"** — it covers zipper, open-
   bottom, basic value-adds. Only go to 8+ stations for vacuum / N₂ /
   double-feed / complex multi-step. Don't upsell stations the customer
   doesn't need.

5. **Manual pack ≠ machine pack**. Manual packing has more "operating
   room" — pressing, shaking, repositioning. If the predicted fill
   reaches 70-80% of bag volume, warn the customer to test manually
   first.

6. **High-product + high-speed is an inherent conflict on HFFS** with
   rotary cutter. The machine design fix is "taller bag length, accept
   tighter product spacing" — but most of the time the answer is
   downgrade to box-motion cutter (slower, taller opening). The user's
   company has no special "tall + fast" SKU.

7. **Density-stable material + screw feeder works**, not just powders.
   "Powders only" was an overcorrection; the right rule is "materials
   whose volume-density is stable."

8. **Hygroscopic / density-variable materials break BOTH volumetric cup
   AND screw feeder** — both are volumetric. Solution: net-weight
   electronic scale with feedback compensation. Don't recommend screw
   feeder for "absorbent powders, slightly cheaper."

9. **Anti-break multihead weighers cost more** but the price delta is
   small enough that the user will default to them for fragile products
   rather than start with the standard and lose product to breakage.

10. **"立式机" vs "给袋机" — iron rule, decided by spoken word, NOT
    model number** (user correction 2026-06-17). When the user says
    "立式机" or writes "X 立式机" with no mention of "工位 / N 位 / 给袋
    机", treat it as **VP-FB (立式制袋, no station)**. When the user
    says "给袋机" or "X-NN 工位" (e.g. "180-06 = 6 工位"), treat it as
    **VP-BF**. **Never** infer machine type from the model-number
    segment alone — both VP-FB and VP-BF share width codes like 180,
    210, 260, 420. Earlier in the same session, the agent did exactly
    this and was corrected: "文本里我明确说的是 420 立式机, 并且没有
    说带什么工位, 意味着这就是正确的立式机, 不应该理解成给袋机".

11. **Suffix `U` = unitized / 一体机** (user correction 2026-06-17).
    Model code like `VP-BF-180-06U` means the base machine PLUS
    integrated Z-type elevator + ribbon coder, sold as one bundled
    package. Recording convention: write the suffix and what it
    includes in the **备注** column (e.g. "U = 一体机, 含 Z 型提升机 +
    色带打码"), and store the bundled price as the unit price. Do not
    decompose the U-package into line items unless the user asks for a
    bill-of-materials breakdown.

12. **Price-source attribution** (user clarification 2026-06-17).
    When the user names a source channel for a price (e.g. "建文" —
    a separate channel distinct from the company's own price list),
    record the source in the **filename or front-matter**, e.g.
    `packaging-machine-parts-prices-jianwen.md`. When the user just
    gives a price with no source attribution, default to the company's
    own (自家) price list. Never invent or assume a channel.

## Workflow state

This skill is consulted in a **long-running mock-sales loop**. Between
sessions, the user adds:
- New product / customer requirements → record under
  `~/.hermes/workspace/notes/customers.md` or equivalent
- New model prices → record in
  `~/.hermes/workspace/.learnings/domains/packaging-machines.md`
- New accessory prices → record in
  `~/.hermes/workspace/.learnings/domains/packaging-machine-accessories.md`
- Corrections / pushback → record in
  `~/.hermes/workspace/.learnings/corrections.md`

Read all of those at session start. They are the user's evolving
knowledge base, more current than this skill.

## Related

- `chat-concise-defaults` — replies should be terse unless the user asks
  for detail; this skill's content is dense so the agent's *rendering* of
  recommendations should still be terse by default.
- `humanizer` — when generating customer-facing sales copy.
- See `references/model-code-decoder.md` — compact model-code lookup
  table (HP/VP/BF/BS/FB + branch + features + cutter) and the
  measuring-tool / station-count cheat-sheets.

## How the user taught this

The user explicitly walked through ~12 question/answer pairs covering
all four machine families, then ran a full mock-selection exercise for
"round cookies in pouches" with extensive pushback when the agent got
the family / model wrong. The pitfalls above are direct extracts from
those corrections.
