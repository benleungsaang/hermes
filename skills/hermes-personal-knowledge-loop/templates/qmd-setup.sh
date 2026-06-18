#!/usr/bin/env bash
# qmd-setup.sh — install qmd + index the user's Hermes workspace
# Run once per Hermes host. Idempotent.
#
# IMPORTANT: qmd (via node-llama-cpp) downloads its 3 GGUF models from
# huggingface.co on first embed. If that domain is blocked on this network
# (the case on BBBBB's host), qmd embed silently fails with "fetch failed".
# The fix is HF_ENDPOINT=https://hf-mirror.com — node-llama-cpp honors this
# env var natively, no qmd config changes needed.
# See ~/.hermes/skills/hermes-personal-knowledge-loop/SKILL.md for the
# troubleshooting section.

set -e

# ---- Mirror setup (do this BEFORE first embed) ----
if ! grep -q "HF_ENDPOINT" "$HOME/.bashrc" 2>/dev/null; then
  echo "==> Persisting HF_ENDPOINT=https://hf-mirror.com to ~/.bashrc"
  echo "" >> "$HOME/.bashrc"
  echo "# qmd / llama.cpp: use HF mirror (huggingface.co is blocked on this host)" >> "$HOME/.bashrc"
  echo "export HF_ENDPOINT=https://hf-mirror.com" >> "$HOME/.bashrc"
fi
export HF_ENDPOINT="${HF_ENDPOINT:-https://hf-mirror.com}"

# Optional sanity check — confirm the mirror is reachable. Non-fatal: if it
# times out the embed step will fail loudly enough on its own.
if ! timeout 15 curl -sSI -o /dev/null -w "%{http_code}" \
    "$HF_ENDPOINT/ggml-org/embeddinggemma-300M-GGUF/resolve/main/embeddinggemma-300M-Q8_0.gguf" \
    2>/dev/null | grep -qE "^(200|302)$"; then
  echo "WARN: $HF_ENDPOINT unreachable — qmd embed will likely fail."
  echo "      If a different mirror works for you, set HF_ENDPOINT before running."
fi

echo "==> Checking qmd install"
if ! command -v qmd >/dev/null 2>&1; then
  echo "==> Installing qmd via npm"
  # Try user-level first to avoid EACCES on system node_modules.
  # Fall back to global only if user explicitly wants system-wide install.
  NPM_PREFIX="${NPM_PREFIX:-$HOME/.local}"
  if ! npm install -g @tobilu/qmd --prefix "$NPM_PREFIX" 2>/dev/null; then
    echo "==> User-level install failed; trying global (may need sudo)"
    npm install -g @tobilu/qmd
  fi
  # Make sure the install dir is on PATH for this session.
  case ":$PATH:" in
    *":$NPM_PREFIX/bin:"*) ;;
    *) export PATH="$NPM_PREFIX/bin:$PATH" ;;
  esac
else
  echo "==> qmd already installed: $(qmd --version)"
fi

WORKSPACE="${HOME}/.hermes/workspace"

if [ ! -d "$WORKSPACE" ]; then
  echo "==> Creating $WORKSPACE"
  mkdir -p "$WORKSPACE"/{notes,.learnings/domains,.learnings/projects,.learnings/archive}
fi

# qmd's default file glob excludes dotfile directories (.learnings/).
# Explicitly index both the user-facing notes/ tree and the dotfile-prefixed
# .learnings/ tree. Without this, .learnings/domains/*.md will be invisible.
echo "==> Indexing workspace notes"
qmd collection add "$WORKSPACE/notes"
qmd collection add "$WORKSPACE/.learnings/domains"

# Clean up any half-finished downloads from a previous failed attempt
# (HF_ENDPOINT wasn't set, or mirror unreachable, etc.).
if [ -d "$HOME/.cache/qmd/models" ]; then
  find "$HOME/.cache/qmd/models" -name '*.ipull' -delete 2>/dev/null || true
fi

# qmd collection add only registers paths — it does NOT generate embeddings.
# Embedding requires the three local GGUF models (~2GB total, downloaded
# on first run). Tell the user to expect a long wait on first embed.
echo "==> Triggering initial embed (downloads ~2GB of GGUF models; may take 10+ min)"
echo "    HF_ENDPOINT=$HF_ENDPOINT"
echo "    Run interactively to see progress:"
echo "      qmd embed"
echo "    Or run in the background:"
echo "      qmd embed &"

echo "==> Done. Try:  qmd search \"<your query>\""
