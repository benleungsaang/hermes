# Hermes System Prompt Metadata for Routing

When the agent needs to know which channel / user / chat it is currently serving, look at the **system prompt**. The gateway injects a block like this at the top of every turn:

```
Source: feishu
Chat ID: oc_df5852f0458839f3481053eae9896370
Chat Type: dm
User ID: ou_319c04f041dfb251bd4a4eaa9f7ae43d
User ID Alt: (sometimes present, e.g. WhatsApp LID-flip case)
Thread ID: (only for threaded conversations)

Home channels:
  feishu:ou_319c04f041dfb251bd4a4eaa9f7ae43d
  weixin:o9cq804vpD1av7HMUGyTkztC5NAM@im.wechat
```

## Fields

- `Source` — the platform adapter name (`feishu`, `weixin`, `telegram`, `discord`, `slack`, `wechat`, `whatsapp`, `signal`, `matrix`, etc.). Same vocabulary as `Platform` enum in `gateway/platforms/base.py`.
- `Chat ID` — platform-specific chat identifier. For Feishu DMs it's `oc_…` (open chat id), for WeChat DMs it's the `o9cq…` openid.
- `User ID` — the *sender's* identifier on that platform. For Feishu DMs it's `ou_…` (user open id), for WeChat DMs it's the `o9cq…@im.wechat` openid. This is the right key for **per-user isolation** (DMs are always isolated per user — see `group_sessions_per_user: true` in config.yaml).
- `User ID Alt` — alternate identifier for the same user. Some platforms (notably WhatsApp) flip between two ID schemes; `get_user_id()` falls back to `user_id_alt` when `user_id` is missing. **Do not treat absence of `user_id_alt` as a missing user** — it's a platform-specific field, not always present.
- `Thread ID` — only set in threaded group conversations (Telegram forum topics, Discord threads, Slack threads). Empty in plain DMs.
- `Home channels` — the user's configured "home" channels across all platforms. Multi-channel users have multiple entries here. A message from a `Source:` that is NOT in `Home channels` means the user is being reached on a non-default channel (e.g. a group chat, a notification channel, or a channel where pairing isn't yet approved).

## How to use this

- **"Who is talking to me right now?"** → read `User ID` and look it up in the user map for this skill.
- **"Am I in a DM or a group?"** → read `Chat Type`. If `dm`, treat the sender as the only participant. If `group` / `channel`, multiple participants may share a session unless `group_sessions_per_user` is on.
- **"Where should I send the response?"** → the same `Chat ID` + `Source` you read. The `send_message` tool accepts `platform:chat_id[:thread_id]` as target.
- **"Should I cross-reference with another channel?"** → check `Home channels` to see all the user's reachable identities. Use this when you need to send a notification to a different channel than the one being talked to (e.g. user is on WeChat DM, you want to email them — there's no email in Home channels, so don't).

## Session-key construction (Hermes internals)

Hermes builds a session key from these fields so that the same physical user on the same physical chat always lands in the same conversation, but two different users (or two different chats) never collide. The single source of truth is `gateway/session.py::build_session_key`. Mental model:

- DMs → `agent:main:<platform>:dm:<chat_id>` (or `:dm:<user_id>:<thread_id>` if no chat_id)
- Group/channel, default → `agent:main:<platform>:<chat_type>:<chat_id>:<user_id>` (per-user isolation)
- Threaded, default → shared across thread participants unless `thread_sessions_per_user: true`

## Pitfalls

- **Don't trust `User ID` for a cross-channel lookup without canonicalization.** WeChat and some others can have two ID forms (openid vs unionid) for the same person. The `user_id_alt` field exists for this. If you build a user map keyed on `User ID`, also include `User ID Alt` in the lookup table, OR canonicalize before keying.
- **`Source: cli` is a different beast.** CLI invocations have no `User ID` / `Chat ID`; they're the developer talking to their own agent. Don't try to apply per-user routing there — the user map will miss and you'll fall through to the "unknown user → default to user role" branch, which is wrong for a developer running `hermes chat` locally.
- **`Source: cron` is also different.** Cron jobs are scheduled tasks, not user messages. `User ID` may be empty or synthetic. The right key for "which user is this task acting for" is whatever you put in the job's `context_from` / cron configuration, not the system-prompt fields.
- **The system prompt can lie about the user if pairing/approval hasn't happened.** Some adapters put a placeholder `User ID` for unapproved users; check whether the value is in your user map before trusting the `User ID`-driven branch.
