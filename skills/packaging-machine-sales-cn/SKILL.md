---
name: packaging-machine-sales-cn
description: "Packaging machine sales support for the Chinese (Shunde / Foshan) packaging-equipment market — VFFS / HFFS / Premade Bag selection, model naming conventions (HP/VP/BF/BS/FB), customer-requirement parsing (especially the 'per-bag count vs per-piece spec' trap), and accessories / pricing catalog. Load when the user (a sales-side packaging-machine operator) asks about 选型 / 报价 / 配件 / 机型 / BOM for packaging equipment."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [packaging, machinery, vffs, hffs, premade-bag, sales, china, shunde, foshan]
    category: productivity
---

# Packaging Machine Sales (CN) — Selection & Quoting

Sales-side companion skill for B's packaging machine workflow (主营: 立式 / 给袋 / 枕式 + 套袋 / 装盒 / 码垛). Covers machine naming, selection logic, customer-requirement parsing, and the accessories catalog that turns a model number into a real quote.

## When to use this skill

Load when the user mentions any of:

- 包装机 / VFFS / HFFS / 给袋机 / 枕式机 / 立式机 / 套袋机 / 装盒机 / 码垛机
- 选型 / 报价 / 配件 / 计量秤 / 螺杆秤 / 量杯 / 组合秤 / 液体泵 / 提升机
- A model code pattern: HP-*, VP-*, BF, BS, FB, FTP (legacy typo for FB)
- A pouch/bag spec: 袋宽 / 袋长 / 工位 / 膜宽 / pouch / premade bag / stand-up bag
- BOM 输出 / 包装机零部件清单 → **load `cad-drawing-bom` for the extraction pipeline (DXF parsing, block recursion, Excel output conventions).** This skill is for the sales-side selection/quoting that frames the BOM; the actual extraction is the other skill.

If the user is selling something else entirely, this skill does NOT apply.

## The model-naming grammar

A model code is built left-to-right as `[结构]-[技术类型]-[结构分支?]-[主要参数]-[特性?]-[切刀?]`.

| Segment | Codes | Meaning |
|---|---|---|
| 结构 (structure) | `HP` / `VP` | Horizontal Package (枕式) / Vertical Package (立式) |
| 技术类型 (tech type) | `BF` / `BS` / `FB` | Bag Filling (给袋, 预制袋) / Bag Sleeving (套袋) / Film (to) Bag (膜袋, 卷膜制袋) |
| ⚠️ 旧拼写 | `FTB` / `FTP` | **legacy typo** — both should be read as `FB`. Real code: `HP-FTB-BF-400` → `HP-FB-BF-400`; `HP-FTP-BF-400` → `HP-FB-BF-400`. The original xlsx price table uses `FTB` (because someone typed Film-to-Bag phonetically as F-T-B instead of F-B); always correct on read, never propagate the typo into customer quotes. |
| 结构分支 (branch) | `BF` (3rd slot) / (empty) | Bottom Film Loader 下走膜 / Upper Film Loader 上走膜 (default, unmarked) |
| 主要参数 | numeric | Max 膜宽 / 袋宽 / 速度 / 载重 |
| 特性 (suffix) | `V` / `H` / `S` or `S(hr)` / `Oe` / `U` / `UD` / `ES` / `E` or `T` / `(B)` | Vacuum / High-Speed / Shrink / On-Edge / Unitized / Upgrade / Electronic Scale / cutter variant / Big wheel |
| 切刀 (cutter) | `B` / (empty) | Box Motion 往复式 / Rotary Motion 旋转式 (default) |

Examples:

- `HP-FB-370H` → 枕式 + 膜袋 + 上走膜 + 膜宽 370mm + 高速
- `HP-FB-BF-450S-B` → 枕式 + 膜袋 + 下走膜 + 膜宽 450mm + 热收缩 + 往复式切刀 (the longest form)
- `VP-BF-180-06` → 立式 + 给袋 + 袋宽 180mm + 6 工位
- `VP-FB-320U` → 立式 + 膜袋 + 膜宽 320mm + 一体机
- `HP-FTP-BF-400` → ⚠️ legacy typo. Real code is `HP-FB-BF-400`. Always correct this when seen.

## The 5-axis selection decision

When the customer gives a requirement, walk these in order:

```
1. 物料形态 (material form)
   - 散料 (粉末/液体/膏体/颗粒/散装小件) → VFFS or Premade Bag (按袋型)
   - 定型单品 (面包/饼干/五金/医疗器械/瓶装) → HFFS 枕式
   - 大件 (大面包等) + 预制袋装不下 → 套袋 (横式给袋, 先撑袋再推入)

2. 袋型 (pouch type) — this overrides 大类 by material
   - bag (卷膜袋) → VFFS 立式
   - pouch / premade bag / stand-up bag (预制袋) → Premade Bag 给袋机
   - 枕式袋 → HFFS 枕式
   ⚠️ 立式机 vs 给袋机物料兼容范围完全一致; 区别只在袋型.
   ⚠️ 一般 pouch + 高展示效果推荐给袋机 (更显高档).

3. 膜宽/袋宽核算 (width math)
   - VFFS / HFFS: 膜宽 = (成品袋宽 + 10~15mm 中封余量) × 2
   - 中封余量不应低于 10mm; 接近极限膜宽时与工程师/客户沟通
     是选更大机型还是缩小袋宽
   - Premade Bag: 按袋宽为主、袋长为辅

4. 枕式机额外 (HFFS only)
   - 走膜方式: 上走膜快, 下走膜平稳 (易滚动/易倒产品用下走膜)
   - 切刀: 旋转式最快但限矮, 往复式高开口首选, 上下切便宜但必停机
   - 高产品 + 高速是矛盾: 先看旋转刀的两个中心距能否容下产品
   - 易滚动产品送料: 推块输送带 (非纯皮带)

5. 给袋机工位 (Premade Bag only)
   - 6 工位: 标准 (拉链、开底袋等基础增值也能在 6 工位完成)
   - 8+ 工位: 真空/充气/双落料等复杂高配
   - 真空+充气: 不一定必须 8 工位; 6 工位 + 集成模块可行, 取决于
     真空/充气要求、大型设备配合、工位空间是否容纳新增设备

6. 计量选型 (metering — the high-stakes axis)
   - 粉末 → 螺杆秤 (性价比高) / 量杯 (仅常规干燥粉末)
   - 细小颗粒 / 体积密度稳定的物料 → 螺杆秤 (不只是粉末能用)
   - 易吸潮 / 压缩比易变物料 → ❌ 量杯 ❌ 螺杆秤 (都是体积计量,
     密度变化导致重量偏差) → 净重式电子秤 (称重反馈补偿)
   - 易碎颗粒 / 高精度需求 → 多头组合秤 (防碎定制版)
   - 液体/膏体 → 计量液体泵
   - 量杯 vs 防碎组合秤整机差价通常 ¥2~5万
   - 计量工具在立式机和给袋机上的参数基本一样, 不区分机型专用
```

## The single most common parsing mistake

> ⚠️ Customer writes: `Round cookies ⌀35×7mm, 3.8g/cookie; pouches 30g 113×120mm and 100g 149×181mm`.

**Read this as**: 1 piece is 3.8g, but the BAG is 30g or 100g. So each bag holds **multiple pieces** = **散装颗粒**, NOT a single solid product.

The default mistake is to treat the whole bag as "one product" and route to **枕式机 HFFS**. That's wrong. The customer is buying a machine to scoop loose cookies into a premade pouch → **Premade Bag 给袋机**.

Signal keywords that always force the 给袋机 path:

- "pouches" (English) — almost always premade pouches
- "premade bag" / "stand-up bag" / "zipper bag" / "异形袋" / "自立袋" — premade
- "固定尺寸" with concrete W×H → confirms premade, not film
- A per-piece spec (weight + dimensions) + a per-bag spec → multi-piece fill, loose

## The 70-80% fill warning

> Customer's hand test passing ≠ machine can fill the same way.

Hand can press, shake, reposition, settle. Machine can't. **When the bag looks 70-80% full by the customer's hand test, warn them** — the machine will jam, deform the product, or fail seal.

## Pricing architecture

A quote is **主机 + 必配件 + 可选配件 + 工位/工艺升级**:

- 主机: from the model catalog (e.g. `VP-BF-180-06` ¥49,800)
- 必配: 防碎组合秤 (易碎物料) / 提升机 (立式/给袋通用) / 卷膜或预制袋供给
- 可选: 打码机 / 视觉检测 / 输送机 / 料仓
- 工艺升级: 抽真空 / 充氮气 / 排空气 / 开底袋 / 开拉链 / 封拉链 / 双落料

Accessories catalog with prices is maintained at `~/.hermes/workspace/.learnings/domains/packaging-machine-accessories.md` — load it for actual quotes.

The **整机价格档** (whole-machine catalog with 业务对外价/成本价/不含税单价) lives at `~/.hermes/workspace/.learnings/domains/packaging-machine-price-table.md` (B's preferred storage as of 2026-06-17). The xlsx in cache is the one-time import source; for ongoing lookups, use `qmd search`. See `references/pricing-source-of-truth.md` for the full default-vs-override rule.

## Pitfalls

- **Don't default to 枕式机** when the customer gives both per-piece and per-bag specs. Multi-piece fill almost always means 给袋机 or 立式.
- **Don't auto-recommend 8 工位 for "vacuum + nitrogen"**. 6 工位 + integrated module is often enough; confirm with the engineering side.
- **Don't assume a body-size cookie needs HFFS**. Cookies are loose-fill; route by bag type, not by product shape.
- **Don't apply a 40-70% efficiency formula** for actual output. Theoretical speed matches the company models (e.g. VP-BF-180 ≤60 pouches/min); actual output is dominated by **填料速度**, which depends on bag opening (袋口越大物料更易进入, 理论速度越高).
- **Don't recommend 无托机 Oe**. Company doesn't use it; cost-prohibitive.
- **Don't claim "套袋 fits big bread via 给袋 filling"**. 套袋 is 横式给袋 — open the premade bag, PUSH the product in, not fill loose. Different mechanism.
- **不要把"立式机"和"给袋机"两个词混用**（B 在 2026-06-17 培训后明确过）：
  - **立式机** = VP-FB-*（立式制袋，无工位 / 膜袋成型）
  - **给袋机** = VP-BF-*（带工位，预制袋）
  - 旧章节标题"立式给袋机"是历史培训用词，**口语准确说法是"给袋机"**。配置 / 报价 / 选型时按这个区分。
  - 立式机和给袋机物料兼容范围完全一致（粉末/液体/颗粒都能用），区别**仅在袋型**（卷膜 vs 预制袋）
- **判定铁律（2026-06-17 B 再次强调）**：以 B 口语为准，**不根据型号号猜机型**。立式机和给袋机都有同号段（如都有 420 宽度规格），B 说"立式机"就是 VP-FB 无工位，B 说"给袋机"或带"工位/N 位"才是 VP-BF。B 明确说过"我没有说带什么工位，意味着这就是正确的立式机"。一旦判定错，立刻回退，不为"维护一致性"硬撑错误分类。（Bitten 2026-06-17：建文价表里写"420 立式机"，agent 根据型号前缀猜成给袋机，B 现场纠正。）
- **"U" 后缀**在 B 的型号体系里 = Unitized / 一体机化（如 `VP-BF-180-06U` = 主机 + Z 型提升机 + 色带打码 + 一体机化，¥95,500 整包价）。不要把 U 当 Upgrade 或 Unspecific 解释。
- **吸嘴袋 (spout pouch) requires top vs bottom fill decision** based on whether there's enough post-spout fill space.
- **带壳 vs 去壳 nuts**: the main impact is volume change, not hardness. If shelled → 易碎, apply the 易碎 rule separately.

## How the user (BBBBB) taught this

B is a sales/admin operator at a Shunde/Foshan packaging machine OEM, with a parallel self-taught flask+vue OA system for company-internal use. He works in Chinese with English terminology mixed. The training came from:

1. A `包装机机型适用范围及选型归纳总结.md` reference doc (early session input)
2. A Soonwin machine catalog JSON (57 machines, 22 missing prices)
3. Iterative corrections: `pouch != bag`, `fitting ≠ filling` for 套袋, `6 工位 handles zipper/bottom-open`, etc.

The training corpus lives at `~/.hermes/workspace/.learnings/domains/packaging-machines.md` and `packaging-machine-accessories.md`. Load both when answering real customer queries.

## Process when loaded

1. **Parse the requirement**. Identify: material form, target bag, per-piece spec, per-bag spec, target output.
2. **Route by bag type first**, then by material form, then by 6-axis selection.
3. **Pick a model** from the catalog (filter by 膜宽/袋宽/工位/特性).
4. **List the 必配件** by material (易碎 → 防碎秤, 液体 → 液体泵, etc.) and the 标配 (提升机 for VFFS/Premade Bag).
5. **Quote**: 主机 + 配件. Flag missing-price items as "待补".
6. **Sanity-check fill**. If 70-80% by hand-test, warn the customer.

## Related

- `chat-concise-defaults` — apply when B is on WeChat: short, only expand on request.
- `cad-drawing-bom` — load this when the user uploads a DXF/CAD drawing and wants a BOM. Covers nested-block entity walk, MTEXT cleaning, symmetric-pair detection, geometry guessing, and the Excel output conventions (electrical cabinet always last, model numbers as normal rows, three row types with three colors).
- See `references/decision-flow.md` — one-page flow chart of the 6-axis decision (for quick reuse).
- See `references/model-catalog-soonwin.md` — Soonwin's 57-machine catalog parsed by category (auto-classified by model code).
- See `references/common-customer-mistakes.md` — parsed-from-real-customer-requirements examples of mistakes to catch.
- See `references/pricing-source-of-truth.md` — the xlsx in `~/.hermes/cache/documents/` is the canonical price source; how to read it (openpyxl recipe), the FTB→FB typo correction rule, the "0 元 = 暂无报价" convention, and why the price table must NOT be mirrored into a `.md` file in workspace.
- See `references/channel-pricing.md` — multi-vendor quoting pattern (自家 vs 建文, two storage files, never mix), the channel-detection rule, and the建文 file's散件/整机 configuration quick-reference.
