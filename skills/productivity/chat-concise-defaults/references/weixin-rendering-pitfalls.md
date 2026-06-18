# WeChat (微信) Content Rendering — Investigation Notes

> Session-derived. Verified by reading
> `~/.hermes/hermes-agent/gateway/platforms/weixin.py` (v0.16.0).
> Not a full mirror of the source — only the parts that explain user-observed
> behaviour and how to debug the next report.

## What users actually see vs what we send

Hermes sends Markdown to the user's WeChat via the iLink gateway
(`ilinkai.weixin.qq.com`). The WeChat client renders Markdown, but:

- **Length cap**: `_SPLIT_THRESHOLD = 1800` chars. Content > ~1800 chars is
  auto-chunked at the iLink boundary (`~2048` hard limit). The Hermes code
  packs chunks via `_pack_markdown_blocks_for_weixin` so blocks stay
  intact across the split.
- **Whitespace normalisation**: `_normalize_markdown_blocks` collapses
  consecutive blank lines. Does NOT drop content.
- **Per-line "chatty" detection**: `_looks_like_chatty_line_for_weixin`
  marks lines starting with `>`, `-`, `*`, `【`, `#`, `|`, `**...**`, or
  `\d+\.` as "non-chatty". This only affects whether the reply splits into
  multiple chat bubbles — these lines are NOT dropped from the message.

So **no rule on the Hermes side silently deletes table rows, list items,
or headings**. If the user reports "content not rendered," it is one of:

1. **The chunk boundary landed mid-block in a way the WeChat client
   rendered as separate messages and only some reached the device** —
   i.e. network / iLink delivery flake.
2. **The WeChat client itself rejected a Markdown construct** — e.g. a
   stray unmatched fence, mixed table syntax (`|` vs `||`), or a URL
   inside a code span. These render fine in some clients and silently
   blank in others.
3. **The reply was actually sent complete but the user's client only
   rendered the first / last chunk** — usually a stale-message-cache
   issue, fixed by pull-to-refresh.
4. **A tool call earlier in the turn produced a large payload** and the
   truncated display bled into what looked like a "missing" reply.

## How to debug a "missing content" report

Do NOT guess. Read the actual code path first:

1. Check length: `len(reply_text) > 1800` → chunking happened, ask which
   chunk the user didn't see.
2. Check for mixed Markdown: scan for `|` outside code spans, unmatched
   ```` ``` ````, URL inside backticks. These are the highest-risk
   constructs.
3. Ask the user: which client (mobile / desktop / web), which OS, and
   whether pulling to refresh recovers the content. Mobile WeChat is
   the most aggressive Markdown renderer.
4. If reproducing locally, run the same reply through a different
   gateway (Telegram / Discord) and compare.

## Anti-pattern: inventing a rule to explain a bug

A past session saw "content not rendered" several times and immediately
wrote "禁止使用 Markdown 表格" into HOT.md. The user correctly pushed
back — tables aren't the cause. Burning a permanent rule that wasn't
verified is worse than admitting "I don't know, help me reproduce."

The rule of thumb:

- One observation → don't write a rule.
- Two observations → look for a common cause in the source.
- Three observations → you can write a rule, but phrase it as
  "investigate first, fall back to X if no other cause found," not
  "always avoid X."

## See also

- `references/attachment-extract-summarize-discard.md` — the
  extract→summarize→discard pattern for media. Same philosophy: don't
  keep raw files when the user wants short text.
