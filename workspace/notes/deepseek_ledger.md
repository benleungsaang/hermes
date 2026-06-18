# DeepSeek 费用账本

> 起点：2026-06-17，账户余额 **¥44.35 CNY**（B 手动核对起点）
> 单价源：https://api-docs.deepseek.com/zh-cn/quick_start/pricing（2026-06-17 抓取）

## 单价（CNY / 百万 tokens）

| 模型 | 输入（缓存命中） | 输入（未命中） | 输出 |
|---|---|---|---|
| deepseek-v4-pro | 0.025 | 3.0 | 6.0 |
| deepseek-v4-flash | 0.02 | 1.0 | 2.0 |

## 算费公式

- 单次费用 = (cached_input / 1e6 × input_cached) + (uncached_input / 1e6 × input_uncached) + (output / 1e6 × output)
- uncached_input = prompt_tokens − cached_tokens
- 余额递减 = 起点 − 累计消费

## 调用记录

| # | 时间 | 模型 | prompt | cached | output | 费用 (¥) | 累计 (¥) | 余额 (¥) | 任务 |
|---|---|---|---|---|---|---|---|---|---|
| 0 | 2026-06-17 | — | — | — | — | 0.00 | 0.00 | 44.35 | 起点 |
| 1 | 2026-06-17 17:50 | deepseek-v4-flash | 12 | 0 | 10 | 0.000032 | 44.349968 | 44.35 | 端到端链路验证：ping → pong |
| 2 | 2026-06-17 22:11 | deepseek-v4-flash | 555 | 0 | 1537 | 0.003629 | 44.346371 | 44.35 | 微信切消息问题修复方案（DeepSeek 协助 #2） |
| 3 | 2026-06-17 22:19 | deepseek-v4-flash | 1096 | 0 | 2500 | 0.006096 | 44.343904 | 44.34 | 微信切消息根因详细分析（DeepSeek 协助 #3） |
| 4 | 2026-06-17 22:20 | deepseek-v4-flash | 1096 | 0 | 2719 | 0.006534 | 44.333466 | 44.33 | 微信切消息根因详细分析（DeepSeek 协助 #3 重跑） |
| 5 | 2026-06-17 23:35 | deepseek-v4-flash | 1180 | 0 | 620 | ~0.003044 | 44.330422 | 44.33 | cad-bom 渲染脚本 v2（DeepSeek 协助 #5，写 render_dxf_v2.py + 自检 config 切换） |
