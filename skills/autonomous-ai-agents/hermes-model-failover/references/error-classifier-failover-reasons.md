# FailoverReason Reference

Source: `agent/error_classifier.py`

## How classification works

`classify_api_error(error, *, provider, model, approx_tokens)` returns a `FailoverReason` enum. The classifier looks at:

1. The exception's HTTP status code (if any)
2. The exception message body
3. Provider-specific patterns (OpenAI, Anthropic, Google, custom transports each have a slightly different error format)

## The full enum

| Value | Typical HTTP | What it means | Triggers failover? |
|---|---|---|---|
| `quota_exceeded` | 402 | Billing/quota exhausted | ✅ |
| `rate_limit` | 429 | Too many requests | ✅ |
| `auth` | 401, 403 | Invalid/expired/missing key | ✅ |
| `server_error` | 5xx | Upstream provider outage | ✅ |
| `content_policy_block` | 400 (safety) | Provider safety filter rejected prompt/response | ✅ |
| `network` | n/a | Connection timeout, DNS failure, TLS error | ✅ |
| `context_too_long` | 400 | Request exceeded model's context window | ❌ |
| `invalid_request` | 400 | Malformed request — bug, not transient | ❌ |
| `cancelled` | n/a | User cancelled the request | ❌ |
| `unknown` | any | Classifier couldn't determine | ✅ (safe default) |

## Reading the error message for clues

Common patterns the classifier matches:

- `"insufficient_quota"` / `"balance"` / `"billing"` → `quota_exceeded`
- `"rate_limit"` / `"too many requests"` / `"tokens per minute"` → `rate_limit`
- `"invalid api key"` / `"unauthorized"` / `"authentication"` → `auth`
- `"internal server error"` / `"service unavailable"` / `"bad gateway"` → `server_error`
- `"content_policy_violation"` / `"safety"` / `"harmful"` → `content_policy_block`
- `"connection"` / `"timeout"` / `"ssl"` / `"dns"` → `network`

## When `unknown` is returned

The classifier falls back to `unknown` when it can't match any pattern. `unknown` is treated as failover-worthy (safe default — better to retry on a backup than to surface a confusing error to the user). If you want to suppress failover for a specific unknown error class, that's a code change in `error_classifier.py` — not a config tweak.

## Mid-conversation context handoff

When the chain fires, `conversation_loop.py` re-sends the full conversation prefix to the fallback provider. The fallback provider may have a different system prompt interpretation, different tool schema, or different format requirements. Known quirk (line 935-939 of `conversation_loop.py`):

> A mid-conversation fallback can switch to a require-side provider (DeepSeek / Kimi / MiMo) that rejects assistant turns lacking reasoning_content. Re-apply the echo-back pad for the *current* provider here (idempotent no-op unless the active provider needs it) so the fallback request goes through.

In practice this means: if your primary is an OpenAI-format provider and you fall back to a "reasoning_content" provider, the assistant turns need to be re-padded with their reasoning trace. Hermes does this automatically but it's a known fragile spot — a fresh session is more reliable than a long-running one that hit a failover.
