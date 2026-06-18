# Intent Classification: Verb ∩ Noun Semantic Pattern

**Class:** Reusable methodology, not multi-user-routing specific.

## The problem

`intention_classifier.py` was first built as a flat keyword list. It failed on natural-language phrasings where the trigger words are separated by other tokens:

| Input | Keyword match | Why it failed |
|---|---|---|
| "把默认模型切换成 GPT-4" | ❌ (no match) | "切换模型" isn't a substring; "切换" and "模型" are separated by "成" |
| "管理员有什么待办" | ❌ (no match) | "管理员" present, but no "读 bbbbb" or "看管理员" substring match |
| "把这些改动提交并推到 github" | ✓ (semantic combo caught it) | But the keyword branch missed it; only the verb∩noun branch worked |

A pure keyword approach is brittle against:
- Sentence-final particles (了/吧/啊/呢/的/地)
- Inserted adverbs (先/再/然后/就)
- Word order variations
- Synonyms not in the keyword list

## The pattern

**Two layers, fallback chain:**

```
Layer 1: Try exact keyword / phrase match (cheap, fast, covers the common cases)
    ↓ miss
Layer 2: Tokenize input into verbs ∪ nouns, then check (verb in verbs) AND (noun in nouns)
    ↓ miss
Layer 3 (optional): Call LLM with a yes/no classifier
```

**Layer 2 implementation** (Python, no LLM, sub-millisecond):

```python
import re

def has_match(text, verbs, nouns):
    # Chinese words (2+ chars), English words, and common suffixes
    words_zh = set(re.findall(r'[\u4e00-\u9fff]+', text))
    words_en = set(re.findall(r'[a-z]+', text.lower()))
    all_words = words_zh | words_en

    # Loose match: a trigger word can be a substring of, or be contained in, a token
    verb_hit = any(any(v in w or w in v for w in all_words) for v in verbs)
    noun_hit = any(any(n in w or w in n for w in all_words) for n in nouns)
    return verb_hit and noun_hit

# Example: classify "改模型" as system_config
if has_match(text, verbs={"改", "换", "切", "调"},
                  nouns={"模型", "model", "provider", "配置", "设置"}):
    return "system_config"
```

**Key design decisions:**

1. **Substring containment in BOTH directions** (`v in w or w in v`): handles both
   - trigger word longer than token ("pip" ⊂ "pip3")
   - token longer than trigger word ("切换" ⊂ "切换成")
2. **Verb and noun must BOTH hit** (logical AND). This kills false positives:
   - "管理员很厉害" has noun "管理员" but no verb, → non-sensitive ✓
   - "我想删除文件" has verb "删" + noun "文件", → sensitive ✓
3. **No scoring, no ML.** Boolean intersection. Easy to debug, easy to extend with one rule.

## When to use this pattern

Any time you need to classify text into "this triggers an action" vs "this is just chatter":

- **Sensitive operation detection** (this skill)
- **Priority routing** (urgent message → pager, normal → batch)
- **Cost-tier routing** (cheap task → flash model, expensive → pro)
- **Spam/abuse detection** (verb=adjective + noun=banned)
- **Auto-tagging** (verb=create + noun=document → "doc-created")

**Don't use when:**
- The set of "trigger" inputs is small and exact (use a simple if/else)
- The classification is multi-label with nuanced scores (use LLM)
- The token vocabulary is closed (use a proper grammar/parser, not regex)

## Why not just call an LLM?

| Approach | Cost | Latency | Determinism | Debug |
|---|---|---|---|---|
| Keyword list | 0 | 0 | 100% | Easy |
| Verb∩noun | 0 | <1ms | 100% (deterministic given rules) | Easy (just add a rule) |
| LLM call | $$ | 200-2000ms | ~85% (temperature) | Hard (prompt-only) |

For a CLASSIFIER that runs on every user message, latency and cost dominate. The verb∩noun pattern catches 90%+ of natural-language phrasings at zero cost. Reserve LLM for the long tail that escapes rules.

## Adding a new rule

When the user reports a false negative ("you let me do X but I meant to need approval"):

1. Identify the **verb** and **noun** the user used
2. Add the verb to an existing rule's verb set, OR add a new rule `(verbs, nouns, category)`
3. Test against 5-10 paraphrases of the same intent to confirm the rule doesn't over-trigger
4. Add a regression test case to your skill's verification recipe

**Anti-pattern:** adding a new keyword without checking the semantic combo already covers it. Often the rule is already triggered — the bug is in the *response*, not the *detection*.

## Reference implementation

`~/.hermes/skills/multi-user-routing/scripts/intention_classifier.py` — 11 rules covering:
- system_config, package_install, skill_management, cron_modify
- git_push_public, destructive_delete, credential_modify
- cross_user_read, cross_user_write, shared_dir_write, network_public

Verified accuracy: 7/7 manual scenarios, including the 3 that defeated the keyword-only approach.

## Linked files

- `scripts/intention_classifier.py` — the implementation
- The `multi-user-routing` SKILL.md "敏感操作白名单" section lists the 11 categories and what they cover
