# DeepSeek V4 — Provider Quirks & Gotchas

> Reference: the **provider itself**, not the接入流程 (that's
> `deepseek-onboarding-transcript.md`). If a future session needs to
> call DeepSeek and something is weird, look here first.

Source: https://api-docs.deepseek.com/zh-cn/ (2026-06-17 snapshot)

## 1. "Auto-disable" on leaked keys (CRITICAL)

**Symptom:** New key returns HTTP 401 on first use, even though it
shows up in the console as active (or as a row with `最后使用: -`).

**Root cause:** DeepSeek's console has a visible warning that says
"我们可能会自动禁用我们发现已公开泄露的 API key". The detection
triggers on plaintext key appearing in chat / commit messages /
public logs — not on `.env` files. Once disabled, the key can no
longer be revived; you must Revoke and create a new one.

**Operational rule:** **Never paste the key into any chat platform,
even once.** The leak window is the moment of paste, not the moment
of `.env` write. The right way to give the agent a key:
1. User creates the key in console
2. User pastes into a terminal-only file (`nano ~/.hermes/.env`)
3. User tells the agent "key is in .env, please verify"
4. Agent does the connectivity check

If a key has already been pasted in chat → tell the user to Revoke +
reissue **before** debugging anything else. Don't waste time
"checking if it's really disabled".

## 2. deepseek-v4-flash: thinking mode is on by default

**Symptom:** You ask for "Reply with the single word: pong" and get
back `content: ""` with `reasoning_content: "We are asked to reply
with the single word:..."` and `finish_reason: "length"` because
all 10 max_tokens were spent on thinking.

**Why:** Docs say "支持非思考与思考模式（默认）" — default IS
thinking. This is different from most chat-completions APIs where
thinking requires explicit opt-in.

**To disable thinking:**

```json
{
  "model": "deepseek-v4-flash",
  "messages": [...],
  "thinking": {"type": "disabled"}
}
```

(Pro may have a different switch shape — check the docs at the time
of use. As of 2026-06-17 the docs page is at
https://api-docs.deepseek.com/zh-cn/guides/thinking_mode)

**Cost impact:** `reasoning_tokens` count toward `completion_tokens`
in the bill. So a "free thinking warmup" is not actually free.
Always include the "disable thinking" param when you want a fast
classification / extract / yes-no answer.

## 3. usage field shape (the bits that vary from spec)

The actual `usage` object returned by DeepSeek in 2026-06-17:

```json
{
  "usage": {
    "prompt_tokens": 12,
    "completion_tokens": 10,
    "total_tokens": 22,
    "prompt_tokens_details": {"cached_tokens": 0},
    "completion_tokens_details": {"reasoning_tokens": 10},
    "prompt_cache_hit_tokens": 0,
    "prompt_cache_miss_tokens": 12
  }
}
```

Notes for the cost script:
- `cached_tokens` lives at `usage.prompt_tokens_details.cached_tokens`
  (snake case, nested), NOT at the OpenAI-standard top-level
  `prompt_tokens_details.cached_tokens` (it is nested, but in some
  versions the path is `usage.cached_tokens` directly).
- `reasoning_tokens` is at `usage.completion_tokens_details.reasoning_tokens`.
  This **is** part of `completion_tokens` (don't double-count).
- For cost computation: `uncached = prompt - cached`,
  `cost = (cached/1M)*cached_rate + (uncached/1M)*uncached_rate + (completion/1M)*output_rate`.
  The cost script in `tools/deepseek_cost.py` already handles this.

## 4. Two API protocols at the same host

DeepSeek exposes both OpenAI-format and Anthropic-format on the
**same** host. Different path prefix, different request shape:

| Protocol | URL | Auth header | Body shape |
|---|---|---|---|
| OpenAI | `https://api.deepseek.com/v1/chat/completions` | `Authorization: Bearer *** | `{"model":..., "messages":[...]}` |
| Anthropic | `https://api.deepseek.com/anthropic` | `x-api-key: sk-...` + `anthropic-version: 2023-06-01` | `{"model":..., "max_tokens":..., "messages":[...]}` |

**Hermes config for the anthropic format:**
```yaml
providers:
  deepseek:
    base_url: https://api.deepseek.com/anthropic
    api_mode: anthropic_messages
```

**For direct curl / Python (when not going through Hermes),** use
the OpenAI format — it's the most documented and the cheapest to
debug (the `curl` recipes in the deepseek docs are all OpenAI-format).

## 5. Model IDs and aliases

Stable IDs as of 2026-06-17:
- `deepseek-v4-pro` — top tier, ¥3/M input, ¥6/M output
- `deepseek-v4-flash` — cheap tier, ¥1/M input, ¥2/M output

**Important:** `deepseek-chat` and `deepseek-reasoner` are deprecated
aliases, hard-deleted on 2026-07-24 23:59 (Beijing time). They map
to `deepseek-v4-flash` non-thinking / thinking modes respectively.
If a script anywhere references these old names, fix them before
the deprecation date.

## 6. Pricing — where the source of truth lives

The price table in `notes/deepseek_ledger.md` and `config.yaml` is a
**copy** of the official page. Source of truth:
https://api-docs.deepseek.com/zh-cn/quick_start/pricing

When the agent quotes a price, the rule is:
- For cost estimates in chat → round generously (¥0.0001 vs ¥0.00009
  both fit in "less than 1 分钱"). Don't make the user wait for 6
  decimal places.
- For ledger entries → use the full 6 decimal places the cost tool
  produces. The 余额 column is rounded to 2 decimals; the 累计 column
  keeps 6 so running balance is exact over many calls.

## 7. Concurrency limits (don't surprise the user)

| Model | Concurrent limit |
|---|---|
| deepseek-v4-pro | 500 |
| deepseek-v4-flash | 2500 |

If the agent is running a parallel batch (e.g. delegate_task with
3 children each calling deepseek), check the limit before queuing
too many. Detail: https://api-docs.deepseek.com/zh-cn/quick_start/rate_limit

## When the agent hits something not in this file

The DeepSeek docs are in Chinese only on the official site, but the
curl / JSON examples are language-agnostic. The most useful pages:
- `/quick_start/pricing` — prices (the only source of truth)
- `/guides/thinking_mode` — how to switch modes (changes often)
- `/guides/tool_calls` — function calling shape (OpenAI-compatible)
- `/quick_start/rate_limit` — concurrency + backoff
