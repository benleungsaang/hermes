# Attachment: extract → summarize → discard source

A workflow for handling media attachments (image / voice / video / PDF) when the user wants the *information* preserved, not the *file*. Pairs naturally with terse chat replies.

## The user's stated workflow (from onboarding)

> "我会以文字，语音，图片，视频等方式发送给你并告诉你帮我记住，你帮我归纳整理，发送给你的文件可以以文字方式归纳不保存源文件。"

Translation: user will send text / voice / image / video / files. Agent's job is to **summarize to text** and **not keep the source**.

## Why this is a class of work

This pattern recurs across:

- Personal memory assistants (this user)
- "Send me a screenshot, I'll extract the data" tasks
- Voice memo → meeting notes workflows
- Receipt / business card / whiteboard photo → structured text
- Any case where the user wants recall, not retention

## Extract → Summarize → Discard recipe

For any non-text attachment:

1. **Extract**: use the right tool for the format.
   - Image: `vision_analyze(image_url=..., question="...")` — pose a specific extraction question
   - Voice: `text_to_speech` is the wrong tool; for transcription use `terminal` with `whisper`/`faster-whisper`/`insanely-fast-whisper`, or a plugin if installed
   - Video: extract audio first (`ffmpeg -i input.mp4 -vn -ac 1 audio.wav`), then transcribe
   - PDF: `ocr-and-documents` skill (marker-pdf / pymupdf)
   - Generic file: `read_file` (text/markdown/JSON), `terminal` with `cat`/`file` for binary inspection
2. **Summarize**: turn the extracted content into structured text. Use the user's preferred categories if known (this user: 生活 / 工作 / 技术笔记).
3. **Discard**: do NOT save the source file to `~/.hermes/` or anywhere persistent. The source lives only in the chat session. If the user's workflow requires long-term retention of the *summary*, route it to the user's chosen store (for this user: not into agent memory; into a separate retrieval store the user has not yet designed).

## What to ask the user

Before summarizing, confirm if unclear:

- "存哪里?" — which store (built-in memory? local file? external?)
- "保留多久?" — retention horizon
- "要不要按 [已知分类] 归类?"

This user's answers (record verbatim in memory):
- 不保存源文件
- 具体事项不写入内置记忆
- 用户主动问时才检索
- 范围：生活 / 工作 / 技术笔记

## Pitfalls

- **Do not auto-delete the chat platform's local cache** — you don't have access to it, and the user may want the source on their phone.
- **Do not write summaries into built-in memory** unless the user explicitly opts in. Built-in memory is per-agent and doesn't scale; users often want their own store.
- **Do extract, even when the format looks like noise** — voice memos with "uh" and pauses, blurry photos, partial screenshots. Ask for a re-send only if extraction genuinely fails, not on first attempt.
- **Cite the source format in the summary** so the user can verify ("你 12:03 发的那张白板照片里写了…") — but don't store the file path or media reference beyond the current session.

## vision_analyze needs an explicit auxiliary provider config

Even when your main model is multimodal (e.g. MiniMax-M3 via `custom:<provider_id>` / `api_mode: anthropic_messages`), the `vision_analyze` tool is a separate auxiliary task and fails with `No LLM provider configured for task=vision provider=auto. Run: hermes setup` until you set `auxiliary.vision.*` explicitly.

Fix in three `hermes config set` calls (do NOT edit `~/.hermes/config.yaml` directly — Hermes' safety guard blocks agent writes to that file; always go through the CLI):

```
hermes config set auxiliary.vision.provider custom:<provider_id>
hermes config set auxiliary.vision.model     <model-name>
hermes config set auxiliary.vision.api_mode   anthropic_messages   # match your main model
```

Use the same `provider`, `model`, and `api_mode` as your main model so vision requests route to the same endpoint. Verify with `hermes config show | grep -A4 auxiliary`.

## Transport-noise filter for chat platforms

WeChat, Telegram, Discord and similar surfaces sometimes append or interleave platform-side status text into the user turn:

- `⏳ Working — N min — iteration M/60, <task>` — autonomous-agent progress leak from another concurrent agent
- Auto-quoted re-render of the previous `clarify` prompt with the original choices (looks like the user pasted your own question back)
- Read receipts, typing indicators, "user is typing…"

**Rule**: treat only the user-authored portion as input. If a message contains status text AND a normal reply, parse the reply; if it contains ONLY status text, ask the user to repeat. Don't try to answer an auto-quoted prompt — it isn't a new question. When replying terse to a noise-laden message, address only the real content.

## Pairing with `chat-concise-defaults`

When the summary is done, reply terse:

> "记下了：周三跟客户 A 确认订单，Q3 前交付。"

Not:

> "I've reviewed the image you sent and extracted the following information: 您发送的图片显示…"

The user wants the takeaway, not the process.

## When the user delegates a technical decision, DON'T bounce it back

This shows up often in setup / design conversations. The user says "你来定" / "你自己考虑" / "检索方式是你去考虑的问题" / "你觉得呢" — and the agent's instinct is to ask a multiple-choice question to confirm. **Wrong move.** The user is asking in natural language precisely because they want a result, not options to evaluate.

Rule:

- If the user explicitly hands you the decision ("你来定", "你自己考虑", "是你去考虑的问题", "随你") → **pick a reasonable default, build it, report one line of what you picked and why**. Do NOT convert it into a `clarify` question.
- If the user answers with "Other" / "随你" / "你看着办" to your earlier question → that's also a delegation; same rule applies.
- True ambiguities that warrant a question: requirements the user *must* own (e.g. "what's your budget", "which platform do you deploy to"). Implementation choices inside a stated goal are NOT user-owned.

The "ask when ambiguous" instinct is right for *requirements* (what outcome they want). It's wrong for *implementation* (how to get there). Pick for the user, then deliver.

## "问才回答" — push nothing proactively

Many users who want terse replies also want zero unsolicited notifications. Specifically for cron / scheduled jobs / proactive summaries:

- Don't deliver a daily/weekly summary unless the user asked for one.
- Don't enable `notify_on_complete` on background tasks unless the user requested push-style updates.
- Default `deliver` for `cronjob` to `local` (save only, no chat output) unless the user said otherwise.
- If the user later asks "what did you do today", that's the trigger to surface stored output — not a scheduled summary.

This pairs with terse chat: both are about respecting the user's attention budget.
