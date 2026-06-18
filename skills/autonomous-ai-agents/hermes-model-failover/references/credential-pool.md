# Credential Pool for Same-Provider Multi-Key Rotation

`credential_pool.py` is Hermes's mechanism for rotating **multiple API keys for the *same* provider** within a single turn. It is **distinct** from the `fallback_providers` chain (which rotates across different providers).

## When to use which

| Scenario | Mechanism |
|---|---|
| One key for DeepSeek, want a backup key if first one hits 429 | credential pool (`hermes auth add deepseek`) |
| Primary is MiniMax, want DeepSeek as backup | fallback_providers chain |
| Three DeepSeek keys for cost spreading | credential pool, strategy = least_used |

## Status states

Defined in `agent/credential_pool.py`:

- `STATUS_OK` — healthy, will be selected
- `STATUS_EXHAUSTED` — 429/402/transient auth, on cooldown
- `STATUS_DEAD` — token invalidated/revoked, never recovers (e.g. upstream OAuth)

## Cooldown

- 401/403 transient failures: short cooldown (~minutes)
- 429/402/billing: 1 hour default
- Provider-supplied `reset_at` timestamp overrides the default

## How to set up

```bash
hermes auth add deepseek
# paste the second key when prompted
hermes auth add deepseek
# paste the third
hermes auth list deepseek  # see all keys + status
hermes auth remove deepseek 2  # remove the 2nd
```

The pool is stored in `~/.hermes/auth.json`. Each entry has `provider`, `key` (or OAuth token), `source` (manual/oauth/auto), `status`, `cooldown_until`.

## How selection works

`CredentialPool.get_credential()` returns the next OK key per the active strategy:

- `STRATEGY_ROUND_ROBIN` (default) — round-robin across OK keys
- `STRATEGY_LEAST_USED` — pick the key with lowest recent call count

If a key returns 429, it's marked `STATUS_EXHAUSTED` and the pool auto-rotates to the next OK key for the same call. If all keys are exhausted, the API call fails and the `fallback_providers` chain is then triggered (if configured).

## Pool exhaustion before fallback chain

Order of operations on a failed model call:

1. Pool selects a key
2. Call fails with 429/401 → key marked exhausted
3. Pool tries the next key
4. If **all** keys exhausted → `classify_api_error` returns `FailoverReason.quota_exceeded` (or `rate_limit`)
5. Main loop walks `model.fallback_providers` chain
6. If chain empty → user sees the error

So with both pool and fallback configured, you get:
- **Within-provider redundancy** (one provider, multiple keys)
- **Cross-provider redundancy** (one provider dies, another takes over)
