# Cost Ledger — <MODEL_NAME> (secondary model)

> Copy this file to `~/.hermes/workspace/notes/<model>_ledger.md` and fill in the
> values. Every call appends one row to the bottom table. The 余额 column is
> ALWAYS the result of the cost tool reading the previous row — never typed by
> the agent — so the running balance cannot drift.

## Start

- **Start date:** YYYY-MM-DD
- **Start balance:** ¥X.XX CNY (user-confirmed, B manual)
- **Pricing source:** https://api-docs.<provider>.com/pricing (date fetched)

## Unit prices (CNY / 1M tokens)

| Model | Input (cached) | Input (uncached) | Output |
|---|---|---|---|
| <model-pro> | X | X | X |
| <model-flash> | X | X | X |

## Cost formula

```
cost = (cached_input / 1e6) × input_cached
     + (uncached_input / 1e6) × input_uncached
     + (output / 1e6) × output
where  uncached_input = prompt_tokens − cached_tokens
```

## Call log

| # | Time | Model | prompt | cached | output | Cost (¥) | Running (¥) | Balance (¥) | Task |
|---|---|---|---|---|---|---|---|---|---|
| 0 | YYYY-MM-DD | — | — | — | — | 0.00 | 0.00 | START_BALANCE | 起点 |
