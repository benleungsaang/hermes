# Common Customer-Requirement Mistakes

Real examples parsed from BBBBB's training sessions. Each one caused a wrong model recommendation. Catch these patterns before recommending.

## Mistake 1 — "Single-piece spec + per-bag spec" → 多片装

> **Customer**: Round cookies ⌀35×7mm, 3.8g/cookie; pouches 30g 113×120mm and 100g 149×181mm

**Wrong read**: 整袋饼干是一个整体 → 枕式机 HFFS
**Right read**: 3.8g/片 + 30g/袋 → 每袋装 ~8 片 → 散装颗粒 + 预制袋 → 给袋机

**Signal keywords**:
- 单独给出 "per piece" 尺寸和重量
- 单独给出 "per bag" 尺寸和重量
- 两个数字明显不匹配 (1 个产品没有 30g 重)
- "pouches" 而非 "bags" (英语)

**Recovery**: route by 袋型 + 物料形态, not by per-piece shape.

## Mistake 2 — "pouches" + "固定尺寸" → 卷膜袋

> **Customer**: Pouches 100×150mm, daily output 5000 bags

**Wrong read**: pouch = 卷膜袋 → 立式机
**Right read**: pouch = 预制袋 (premade bag / stand-up pouch) → 给袋机

**Signal keywords**:
- "pouch" / "premade bag" / "stand-up bag" / "zipper bag" / "Doypack"
- "自立袋" / "拉链袋" / "异形袋" / "铝箔袋"
- "固定尺寸" with concrete W×H → 预制袋确定性

**Recovery**: pouch 在中文/英文行业里都是预制袋, never 卷膜袋.

## Mistake 3 — "饼干/薯片/狗粮" → 枕式机

> **Customer**: 想包装薯片, 8g/包

**Wrong read**: 薯片是定型单品 → 枕式机 HFFS
**Right read**: 8g 一包装多片 → 散装颗粒 → 立式机或给袋机 (按袋型)

**Recovery**: 个头小的"定型单品"也可以走散装路径. 关键是**多少片装一袋**, 不是产品本身形状.

## Mistake 4 — "需要抽真空" → 8 工位

> **Customer**: 给袋机包装, 需要抽真空

**Wrong read**: 必须 8 工位
**Right read**: 6 工位 + 集成真空模块可能够; 看真空度要求 + 工位空间

**Recovery**: ask engineering about vacuum specs before sizing the workstation count.

## Mistake 5 — "高产品" → 旋转切刀

> **Customer**: 包装高瓶子, 100mm 高, 想要高速

**Wrong read**: 高速 → 旋转式切刀
**Right read**: 高 100mm 超过旋转刀开口 → 必须用往复式 (B) 或上下切; 牺牲速度

**Recovery**: high product + high speed is a CONTRADICTION in HFFS. 先满足高度, 再谈速度.

## Mistake 6 — "大面包" → 给袋机装袋

> **Customer**: 想用给袋机包装大面包, 1 个/袋

**Wrong read**: 给袋机填充
**Right read**: 预制袋装不下大面包 → 套袋 (横式给袋, 先撑袋再把整块推入)

**Recovery**: 大件整块物料 → 不要"填充", 要"推入". 套袋是单独的工位类别.

## Mistake 7 — "易吸潮粉末" → 螺杆秤

> **Customer**: 易吸潮调味粉末, 预算有限

**Wrong read**: 粉末 → 螺杆秤
**Right read**: 易吸潮 → 密度变化 → ❌ 量杯 ❌ 螺杆秤 (都是体积计量) → 净重电子秤

**Recovery**: 螺杆秤也是体积计量. 密度敏感物料必须净重电子秤.

## Mistake 8 — "量杯预算低" → 默认安全

> **Customer**: 包装干燥绿豆, 预算极低

**Wrong read**: 量杯是预算优先的默认
**Right read**: 量杯仅在 4 个条件同时满足才安全 (干燥/形态稳定/无易碎/无受潮风险)

**Recovery**: 量杯禁忌清单 — 易碎 / 易吸潮 / 压缩比易变 / 高油脂粘连 (待验证)

## Mistake 9 — "坚果带壳 vs 去壳" → 硬度问题

> **Customer**: 包装核桃, 带壳 vs 去壳

**Wrong read**: 带壳更硬 → 影响下料
**Right read**: 主要是体积变化; 去壳变易碎 → 按易碎规则另议

**Recovery**: 物理特性的影响 (体积 > 硬度 > 摩擦). 易碎是单独的判断维度.

## Mistake 10 — "70-80% 装满" → 手工测试通过

> **Customer**: 手工测试装 80% 满没问题

**Wrong read**: 客户测试通过了 → 机器也能
**Right read**: 手工可以压实/抖动/扶正, 机器没有这个操作空间 → 预警 + 让客户重新评估袋型

**Recovery**: never trust hand-test for ≥70% fill rate.
