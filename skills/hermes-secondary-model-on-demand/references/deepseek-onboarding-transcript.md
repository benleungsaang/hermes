# End-to-End Model 接入 — Reference Transcript (DeepSeek V4, 2026-06-17)

> Reference implementation of the "接入包" pattern. The shape, not the
> specific provider, is what carries over to GPT-4, Claude, Qwen-Coder, etc.

## The 5 files that get created

| # | File | Role | Owner writes |
|---|---|---|---|
| 1 | `~/.hermes/.env` | holds `DEEPSEEK_API_KEY=sk-...` | agent (silent) |
| 2 | `~/.hermes/workspace/tools/deepseek_cost.py` | single-source-of-truth cost + ledger script | agent (silent) |
| 3 | `~/.hermes/workspace/notes/deepseek_ledger.md` | append-only call log + running balance | agent (silent, with user-confirmed start balance) |
| 4 | `~/.hermes/workspace/notes/deepseek_config_snippet.md` | yaml snippet the user pastes into config.yaml (Hermes blocks agent writes) | agent (silent, user pastes) |
| 5 | `~/.hermes/workspace/MAINTENANCE.md` | human-readable接入 section | agent (silent) |

After all 5 land → connectivity check (silent, no tokens billed) → ask the user
to approve the first demo call.

## The cost script (canonical shape)

```python
# Key insight: ONE script does compute-cost + append-row + decrement-balance.
# Splitting these into 2-3 scripts causes balance drift.

LEDGER = Path.home() / ".hermes/workspace/notes/deepseek_ledger.md"
PRICING = {
    "deepseek-v4-pro":   {"input_cached": 0.025, "input_uncached": 3.0, "output": 6.0},
    "deepseek-v4-flash": {"input_cached": 0.020, "input_uncached": 1.0, "output": 2.0},
}

def calc_cost(model, prompt, completion, cached=0):
    p = PRICING[model]
    uncached = max(prompt - cached, 0)
    return round((cached/1e6)*p["input_cached"]
               + (uncached/1e6)*p["input_uncached"]
               + (completion/1e6)*p["output"], 6)

def parse_ledger_balance():
    """Read the LAST row's 余额 column (倒数第 2 列 in 10-col table)."""
    last = None
    for line in LEDGER.read_text().splitlines():
        if not line.startswith("|"): continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 9: continue
        try: last = float(cells[-2])
        except ValueError: continue
    return last  # raises if not found

def append_ledger(model, prompt, completion, cached, cost, balance_after, task):
    text = LEDGER.read_text()
    nums = [int(m.group(1)) for m in re.finditer(r"^\|\s*(\d+)\s*\|", text, re.M)]
    next_n = (max(nums) if nums else 0) + 1
    new_row = (f"| {next_n} | {datetime.now():%Y-%m-%d %H:%M} | {model} | "
               f"{prompt} | {cached} | {completion} | {cost:.6f} | "
               f"{(balance_after-cost+cost):.6f} | {balance_after:.2f} | {task} |")
    # *** Pitfall: find the LAST |---| separator, not the first. ***
    # A ledger file with two tables (单价表 + 调用记录表) will misroute
    # to the first table if you stop at the first separator. Walk from
    # the last separator forward to the first non-`|` line.
    lines = text.splitlines()
    sep_indices = [i for i, ln in enumerate(lines) if re.match(r"^\|---", ln)]
    if not sep_indices:
        lines.append(new_row)
    else:
        last_sep = sep_indices[-1]
        end = last_sep + 1
        while end < len(lines) and lines[end].startswith("|"):
            end += 1
        lines.insert(end, new_row)
    LEDGER.write_text("\n".join(lines) + "\n")
    return next_n
```

## The connectivity check (silent, no tokens billed)

```bash
# Source .env FIRST so $DEEPSEEK_API_KEY is in scope
set -a; source ~/.hermes/.env; set +a
curl -sS -m 10 -o /tmp/ds_models.json -w "HTTP:%{http_code}\n" \
     "https://api.deepseek.com/v1/models" \
     -H "Authorization: Bearer ***  expect: HTTP:200, body has deepseek-v4-pro + deepseek-v4-flash
```

If HTTP != 200, do not proceed. Report the error and ask the user to verify
the key (most common: paste-typo, region block, or revoked key).

## Worked example from 2026-06-17

User: "前面让你准备的 deepseek 的接入，前置工作处理好了吗" (B checking status)
User: "sk-*** (key)" (B pasted API key)
User: "当前账户余额为¥44.35 CNY" (B confirmed balance)

What I built:
- `~/.hermes/.env`: `DEEPSEEK_API_KEY=*** (chmod 600, never pasted in chat again)
- `tools/deepseek_cost.py`: 4884 bytes, single-source cost+ledger script
- `notes/deepseek_ledger.md`: 起点 ¥44.35, table schema copied from template
- `notes/deepseek_config_snippet.md`: 25-line yaml for config.yaml (agent blocked from writing)
- `MAINTENANCE.md`: full接入 section
- Connectivity check: HTTP 200, models listed correctly

What I did **wrong** (and the skill now encodes as pitfalls):
1. Echoed the key in plain text once in the response — fixed by redaction + user revoke request.
2. `append_ledger` first picked the first `|---|` separator → row landed in "单价表" instead of "调用记录表". Fixed by switching to "find the LAST separator".
3. `append_ledger` second try inserted the new row right after the table header → row # 1 appeared ABOVE the 起点 row # 0. Fixed by walking to the first non-`|` line.
4. Tried to `patch ~/.hermes/config.yaml` directly → Hermes safety net refused. Pivoted to writing a snippet the user pastes.

Each of these is now a "Pitfalls" entry in the parent SKILL.md, so the next
接入包 won't repeat them.

## Topup + drift recovery

If the user says "I topped up, balance is now ¥Y", append a "topup"
row to the ledger so the running balance recalculates correctly.
The cost script already exposes `PRICING`, `parse_ledger_balance`,
and `append_ledger` — invoke them directly:

```bash
# Don't manually edit the ledger. Append a "topup" row with NEGATIVE cost
# (= +topup amount) so the running balance recalculates correctly.
python3 -c "
import sys; sys.path.insert(0, '$HOME/.hermes/workspace/tools')
from deepseek_cost import PRICING, parse_ledger_balance, append_ledger
# A 1.00 ¥ topup is 'cost' of -1.00
TOPUP = 1.0000
prev = parse_ledger_balance()
append_ledger('TOPUP', 0, 0, 0, -TOPUP, prev + TOPUP, f'充值 +{TOPUP:.2f} ¥')
print('new balance:', prev + TOPUP)
"
```

Same pattern for "I want to reset the balance" — append a `RESET` row with
whatever delta moves the running total to the new value.

**Don't run a "balance-only" command** (e.g. `hermes deepseek balance`)
that returns the current balance without writing a row. The ledger
should always be the source of truth; any out-of-band read invites
drift. If the user asks "what's my balance now?", `grep` the last row
of the ledger or `cat` it — the answer is in the file, not in a script's
stdout.

**Don't try to write a `set_balance` function in the cost script.**
There's no clean use case (the user almost never resets mid-session,
and topup covers the 99% case). If a user *does* ask for a reset,
append a one-off `RESET` row with the delta; never let the script
"edit history".

## When this pattern doesn't apply

- **Local ollama/llama.cpp** — no per-call cost, no ledger, no approval gate.
  Drop into chat-concise-defaults only.
- **Vision / TTS / embedding** — different cost shape (per-image, per-audio-second,
  per-1k-chars). New skill if reused.
- **Models that bill in USD** — same pattern, swap `¥` for `$` and fetch current
  FX once at start of session, don't quote live rates in skill body.
