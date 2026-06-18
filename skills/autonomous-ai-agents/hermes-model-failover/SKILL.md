---
name: hermes-model-failover
description: Configure Hermes to automatically fall back from a primary LLM to a secondary provider when the primary fails (quota exhausted, 401/429/5xx, content policy block, network error). Covers the native model.fallback_providers chain in config.yaml, how Hermes' error_classifier.FailoverReason drives the handoff, the credential_pool cooldown model, and known gotchas when editing config.yaml via the CLI vs by hand. Load when the user asks for "fallback / 兜底 / 备用模型 / 切换模型 / failover / primary model died / provider dead" or when adding redundancy to a model setup.
---

# Hermes Model Failover

Hermes has a **native failover mechanism** — no wrapper code, no cron, no plugin. Configure it once in `~/.hermes/config.yaml` and the main agent loop will automatically try the next provider in the chain when the primary returns a retriable-but-not-prompt-cached error.

## When the chain triggers

`agent/conversation_loop.py` calls `classify_api_error(error, provider, model, …)` from `agent/error_classifier.py` on every model-call exception. The classifier returns a `FailoverReason` enum value. The main loop iterates through `model.fallback_providers` in order and retries the same turn on the next entry when the reason is in the failover-trigger set:

| FailoverReason | Trigger |
|---|---|
| `quota_exceeded` | Provider billing/quota hit (402, balance errors) |
| `rate_limit` | 429 from provider |
| `auth` | 401, 403, invalid/expired key |
| `server_error` | 5xx, upstream provider outage |
| `content_policy_block` | Provider refused the request (e.g. safety filter) |
| `network` | Connection timeout, DNS failure, TLS error |

Reasons that do **not** trigger failover (they retry the same provider or surface to the user):
- `context_too_long` — only the original provider can help
- `invalid_request` — bug, retrying on a different provider won't fix it
- `cancelled` — user-initiated

## Configuration

Add `model.fallback_providers` as a list of dicts. Each entry must have `provider`, `model`. `base_url` and `api_key` are required if the provider is a custom endpoint or differs from the default for that provider name. `api_mode` (anthropic_messages | chat_completions) should match what the provider expects.

```yaml
model:
  default: MiniMax-M3
  provider: custom:minimax_domestic
  base_url: https://api.minimaxi.com/anthropic
  api_key: ${MINIMAX_DOMESTIC_API_KEY}
  api_mode: anthropic_messages
  fallback_providers:
    - provider: deepseek
      model: deepseek-v4-flash
      base_url: https://api.deepseek.com/v1
      api_key: ${DEEPSEEK_API_KEY}
      api_mode: chat_completions
    - provider: openrouter
      model: anthropic/claude-3-5-sonnet
      # api_key inherited from OPENROUTER_API_KEY env if not set
```

Notes:
- `${VAR}` env-var substitution in `api_key` is **supported and recommended** — keeps secrets in `.env` not in `config.yaml`.
- Multiple fallback entries are tried in order. As soon as one succeeds, the response goes back to the user as if it came from the primary.
- A single-provider setup with **multiple keys** can use the credential pool (`auth.json` / `hermes auth add <provider>`) for same-provider key rotation — see `references/credential-pool.md`.

## Known gotchas when editing `config.yaml`

Hermes has a **two-layer defense** against the agent silently rewriting its own model config:

1. **The `patch` tool refuses to write to `~/.hermes/config.yaml`.** You'll see `Refusing to write to Hermes config file`. This is intentional and good — the agent should not be able to swap its own model mid-conversation.
2. **`hermes config set` is a thin YAML setter** that handles scalar values cleanly but **silently mangles list-of-dict values** into a string. Example failure mode:
   ```
   $ hermes config set model.fallback_providers '[{"provider":"deepseek",...}]'
   ✓ Set model.fallback_providers = [{"provider":...}] in /home/ubuntu/.hermes/config.yaml
   # but the file actually contains:
   fallback_providers: '[{"provider":...}]'  # ← quoted string, not a YAML list
   ```
   Hermes's `get_fallback_chain()` reads it back as a list because the string parses as JSON, but config drift is real. **For nested list/dict values, edit `config.yaml` by hand.** The security guard only blocks agent-initiated `patch` calls — manual edits are fine.

3. **Environment-variable expansion** in `api_key: ${VAR}` happens at config load time. The variable must be in `~/.hermes/.env` (or the shell environment when Hermes starts). Missing vars cause `KeyError` on startup, not a graceful failure.

4. **`api_mode` matters.** Anthropic-protocol providers (MiniMax, Anthropic, Bedrock) need `api_mode: anthropic_messages`. OpenAI-protocol providers (OpenAI, DeepSeek, OpenRouter) need `api_mode: chat_completions`. Wrong mode = HTTP 400 on the first call.

5. **`provider` and `base_url` must agree.** The `provider` field is what routing logic keys on; `base_url` is where the HTTP call actually goes. If you set `provider: custom:minimax_domestic` but leave `base_url: https://api.deepseek.com/v1` from a previous DeepSeek setup, every "primary" call silently hits DeepSeek — which will 401 if a MiniMax key is used, or return wrong-model responses if a DeepSeek key is left in place. **Symptom: the primary looks "dead" and failover fires — but the user sees DeepSeek responses when they asked for MiniMax.** Always verify `provider` + `base_url` + `api_key` + `api_mode` form a consistent tuple before assuming failover is wired right. Quick check:

   ```bash
   curl -s -X POST <base_url>/v1/messages \
     -H "x-api-key: $API_KEY" \
     -H "anthropic-version: 2023-06-01" \
     -d '{"model":"<model>","max_tokens":10,"messages":[{"role":"user","content":"ping"}]}' \
     | head -c 300
   ```

   The response should come back from the same vendor as `provider` claims.

6. **Mid-conversation failover does NOT re-check the config.** Once a primary+base_url mismatch is in place, every turn re-hits the wrong vendor until the user fixes `config.yaml`. The agent cannot do this for them (see gotcha #1). If the user reports "the model keeps dying", check for this BEFORE adding fallback entries — you'll just be papering over a config bug.

## Mid-conversation behavior

When the primary fails mid-conversation and the chain falls over, the assistant message comes from the fallback provider. Two consequences:

- **Prompt cache invalidation.** The next user turn re-sends the full prefix to the new provider, losing any cache the previous provider had. Cost goes up briefly.
- **Role alternation.** If the fallback provider requires `reasoning_content` echo-back (DeepSeek, Kimi, MiMo) and the primary's prior assistant turn did not emit it, the fallback call may 400. `conversation_loop.py` line 935-939 handles this by re-applying the echo-back pad to the *active* provider's prior messages — usually fine, but a known gotcha.

## Quick verification recipe

After editing `config.yaml`, confirm Hermes parses the chain without errors:

```bash
python3 -c "
from hermes_cli.fallback_config import get_fallback_chain
import yaml
with open('$HOME/.hermes/config.yaml') as f:
    cfg = yaml.safe_load(f)
chain = get_fallback_chain(cfg)
print(f'Fallback chain length: {len(chain)}')
for i, e in enumerate(chain):
    print(f'  [{i}] {e[\"provider\"]}/{e[\"model\"]} (api_mode={e.get(\"api_mode\",\"default\")})')
"
```

Should print the primary's `model.fallback_providers` list. If `len == 0`, the YAML was malformed (usually the string-quoting bug above).

## When NOT to use

- **For non-failover model routing** (e.g. "use Claude for code, DeepSeek for chat"), use `delegate_task` with an explicit `model`/`provider` override per call. The fallback chain is for *emergency* handoff, not routing.
- **For vision/image tasks**, the fallback chain only covers chat-completions / anthropic_messages transports. Vision providers (Coze, Doubao, GPT-4V) live under `auxiliary.vision.*` config and have their own provider chain.
- **For a temporary model switch** (one-off, not a permanent backup), use `/model <name> --provider <provider>` in-session instead of editing config.

## Related skills

- `hermes-secondary-model-on-demand` — covers *user-initiated* secondary model calls (approval flow, cost tracking) — different from automatic failover.
- `hermes-backup` — config backup utility, useful for backing up `config.yaml` before failover edits.

## See also

- `references/credential-pool.md` — same-provider multi-key rotation (orthogonal to fallback_providers)
- `references/error-classifier-failover-reasons.md` — full FailoverReason enum + classifier behavior
