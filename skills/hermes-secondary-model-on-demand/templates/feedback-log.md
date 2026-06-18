# Feedback Log — DeepSeek V4 (secondary model)

> Append one row per call. Keep schema minimal — a one-row table beats
> a perfect schema the user never fills in.

## Schema

```
| date | task_summary | cost_yuan | quality_1_5 | user_notes |
```

- `date`: YYYY-MM-DD
- `task_summary`: ≤10 words, primary agent's voice
- `cost_yuan`: actual billed cost in RMB (fetch from provider dashboard, not estimated)
- `quality_1_5`: user rating; 5 = "perfect, would call again", 1 = "worse than primary alone"
- `user_notes`: anything the user wants to remember ("always rephrase X", "don't call for Y")

## Roll-up

After 10+ entries, compute:
- Median quality per task category
- Total spend per month
- Approval rate (% of asks that user said yes)

Adjust trigger threshold in `AGENTS.md` based on the data. If approval rate
<50%, the trigger is firing too often. If median quality ≤3, the model
isn't worth the cost for that task class — narrow the scope.

## Entries

| date | task_summary | cost_yuan | quality_1_5 | user_notes |
|------|--------------|-----------|-------------|------------|
