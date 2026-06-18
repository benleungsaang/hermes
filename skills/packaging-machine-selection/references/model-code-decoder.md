# Packaging machine — model code decoder

> Compact reference. The user's live workspace files
> (`~/.hermes/workspace/.learnings/domains/packaging-machines.md`)
> are the canonical source. Update THIS file only when the
> company conventions change, not per-product.

## Model code structure

```
[STRUCTURE]-[TECH]-[BRANCH?]-[NUMBER]-[FEATURES?]-[CUTTER?]
```

| Segment    | Code | Meaning                                                |
|------------|------|--------------------------------------------------------|
| Structure  | HP   | Horizontal Package (枕式 HFFS)                          |
|            | VP   | Vertical Package (立式 VFFS)                            |
| Tech       | BF   | Bag Filling — premade bag, fill-then-seal              |
|            | BS   | Bag Sleeving — slip outer bag over product             |
|            | FB   | Film-to-Bag — roll film formed into bag in-line        |
| Branch     | BF   | Bottom Film Loader (下走膜) — only on HFFS             |
|            | (UF) | Upper Film Loader (上走膜) — default, unmarked          |
| Number     | nn   | Max film/bag width in mm (main sizing parameter)       |
| Features   | V    | Vacuum                                                 |
|            | H    | High-speed                                             |
|            | S    | Shrink-wrap                                            |
|            | Oe   | On-Edge (托槽 / 料斗扶稳) — user's company does NOT use  |
|            | U    | Unitized (host + weigher integrated)                   |
|            | UD   | Updated model                                          |
|            | ES   | Electronic scale series                                |
|            | E,T  | Cutter variants                                        |
|            | (B)  | Big (e.g. big wheel / big sealing ring)                |
| Cutter     | B    | Box-motion (往复式, taller opening, no-stop)            |
|            | (R)  | Rotary (旋转式, fastest, default unmarked)             |

## Family mapping cheat-sheet

| User says …                              | → Machine family                  |
|------------------------------------------|------------------------------------|
| Pillow bag, regular solid product        | HFFS (HP-FB-* / HP-FB-BF-*)        |
| Premade pouch / stand-up / zipper        | Premade Bag (VP-BF-* / HP-BS-*)    |
| Bulk powder / liquid / granule           | VFFS (VP-FB-*) OR Premade Bag — depends on bag, NOT product |
| Premade bag, big item (won't fit in pouch)| Sleeving (push product into bag, not fill) |
| Big bread, etc.                          | Sleeving (HP-BS / VP-BS)           |

## Measuring tool by product (universal — same tool on VFFS and Premade Bag)

| Product                                | Tool                          |
|----------------------------------------|--------------------------------|
| Powder / density-stable fine particles | Screw feeder (螺杆秤)           |
| Hygroscopic / variable-density         | Net-weight electronic scale    |
| Dry stable non-fragile granules        | Volumetric cup (量杯, cheap)    |
| Fragile solids (cookies, nuts)         | Anti-break multihead weigher   |
| Liquids / pastes                       | Liquid pump                    |

## Station count (Premade Bag only)

- 6 stations = standard. Includes zipper, open-bottom, basic value-adds.
- 8+ stations = vacuum / N₂ / double-feed / complex multi-step.

## Cutter type (HFFS only)

| Need                          | Pick         |
|-------------------------------|--------------|
| Speed + short product         | Rotary (R, default) |
| Tall product                  | Box-motion (B) |
| Budget-tight + slow production| Up-down (上下切) |

## Quick math

- Film width = (pouch width + 10~15mm) × 2
- Never go below 10mm seal margin. If near machine max, talk to engineering.
- Predicted machine fill = 70-80% of manual-pack fill. If you estimate
  ≥ 80%, warn the customer to test manually first.
