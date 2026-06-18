# Passive Approval Pattern

**Class:** Reusable methodology. Not multi-user-routing specific.

## The pattern

When a workflow needs **user A to request, user B to approve, then someone to execute** — without polling, daemons, or background processes:

```
Phase A — User A submits
  - Write state to a file (status=pending)
  - Send notification to user B (push, not poll)
  - IMMEDIATELY return to user A
  - User A does NOT wait, polls, or blocks

Phase B — User B approves (or later)
  - User B replies with decision (whatever format)
  - B's agent updates the file (status=approved/rejected)
  - B's agent pushes notification to user A (so A knows without polling)
  - IMMEDIATELY return to user B

Phase C — Execution (triggered by anyone, any time later)
  - Someone calls `execute` on the file
  - Read status → decide what to do
  - If pending: "still waiting on B"
  - If rejected: "B said no, operation skipped"
  - If approved: proceed with the real action
```

## Why this pattern

User said explicitly: "**不要 elma 等待或轮询，脚本只发出申请后未有审批就不继续运行**"

Translation: no polling, no daemons, no cron watchdog. State on disk, push notifications, lazy evaluation.

**Properties:**
- Zero background processes (no cron job to manage)
- Zero polling (no "check status every 30s" loop)
- File-system as the source of truth (no in-memory state to lose on crash)
- Three phases decoupled (each can be invoked independently, any time)
- B can approve hours later, no one has to be waiting
- A can check status any time, but doesn't have to

## When to use

Any approval-style workflow:
- **Permission requests** (user A wants to do X, admin B approves) — this skill
- **Async code review** (A submits PR, B reviews, CI runs)
- **Purchase orders** (A requests $X, B approves, then procurement runs)
- **Deploy gates** (A wants to deploy, B approves, deploy script runs)
- **Cross-team handoffs** (A does step 1, B does step 2, A continues when notified)

**Don't use when:**
- The approval must be synchronous (use a direct API call)
- There's no one to "push to" (no notification channel)
- The operation is cheap and reversible (just do it, no approval)

## Implementation rules

1. **One file per request.** UUID-named, lives in `~/.hermes/users/<requester>/approvals/<uuid>.json`. File = state, don't reinvent with a DB.
2. **Status field is small.** `pending` / `approved` / `rejected` / `cancelled`. Don't put complex state machines in here.
3. **Each phase is a separate CLI command.** `submit`, `decide`, `execute`. Each exits immediately. No long-running process.
4. **The submit and decide commands print "to-be-sent" messages** — the calling agent is responsible for actually sending them via `send_message`. The script doesn't know your platform; it just produces the payload.
5. **Notifications are the agent's job, not the script's.** Otherwise the script needs to know your chat platform, auth tokens, and rate limits.
6. **The execute command does NOT actually run the dangerous thing.** It only reports status. The calling agent, having received "approved", is responsible for executing the actual command in context — with whatever additional safety checks it wants to apply.

## Anti-patterns to avoid

❌ **Polling the file in a loop:** "let me check every 30s..."
→ Wastes CPU, hides race conditions, and the user said no.

❌ **Daemon process watching the directory:** `inotifywait` + a background script
→ Survives crashes, but adds operational burden. Only worth it if you have 100+ concurrent approvals.

❌ **Embedding the actual operation inside approve:** `decide` runs `hermes config set ...`
→ Couples the approval to the operation. If the operation is destructive, you want the operator (agent) to do it after, not the approver (different context, different safety).

❌ **HTTP webhook from the requester to the approver:** "POST /approve"
→ Adds a service. The chat platform already has the notification channel.

❌ **State in agent memory only:** "I'll remember the approval in our conversation"
→ Lost on session end, lost on context compression, lost when the session resets.

## Reference implementation

- `~/.hermes/skills/multi-user-routing/scripts/approval.py` — 3 phases + `list` / `show` helpers
- The `multi-user-routing` SKILL.md "审批流程" section has the full state machine
- Test scenarios in the session log: 7/7 success rate on the verb∩noun classifier

## Customizing for other workflows

To adapt for a different approval pair (e.g. customer service → sales approval → warehouse):

1. Change the notification target: `weixin:...` → whatever the approver uses
2. Change the reply format: `#aid 同意` → whatever the approver naturally writes
3. Change the file location: `~/.hermes/users/<requester>/approvals/` → your domain
4. Keep the 3-phase shape. The state machine is the same regardless of who approves what.
