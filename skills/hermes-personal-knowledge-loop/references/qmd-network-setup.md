# qmd Network Setup — Blocked HF Main, Mirror Works

Last reproduced: 2026-06-17 on BBBBB's host during initial qmd setup.

## Symptom

`qmd embed` (or `qmd pull`) appears to start, shows the spinner at "Gathering information" for minutes, then exits with:

```
fetch failed
If qmd still behaves unexpectedly, run 'qmd doctor' for diagnostics.
```

`qmd doctor` confirms the failure mode:

```
⚠ model cache: missing 3/3: embedding: hf:ggml-org/.../embeddinggemma-300M-Q8_0.gguf; ...
⚠ embedding freshness: 7 active documents need embeddings. Next: `qmd embed`
```

`~/.cache/qmd/models/` stays empty (or contains stale `*.ipull` files from aborted attempts).

## Root Cause

qmd's underlying engine (node-llama-cpp) builds HF download URLs from the model spec:

```js
const url = `https://huggingface.co/${ref.repo}/resolve/main/${ref.file}`;
```

If the host can't reach `huggingface.co` (typical for hosts behind GFW, corporate firewalls, or restrictive NAT), every fetch times out.

## Diagnostic recipe (30 seconds)

```bash
# 1. Confirm the main domain is dead
timeout 15 curl -sSI -o /dev/null -w "hf.co: %{http_code} (%{time_total}s)\n" \
  https://huggingface.co/ggml-org/embeddinggemma-300M-GGUF/resolve/main/embeddinggemma-300M-Q8_0.gguf
# expect: 000 (timeout) or curl: (28) Failed to connect

# 2. Confirm a mirror is alive
timeout 15 curl -sSI -o /dev/null -w "hf-mirror: %{http_code} (%{time_total}s)\n" \
  https://hf-mirror.com/ggml-org/embeddinggemma-300M-GGUF/resolve/main/embeddinggemma-300M-Q8_0.gguf
# expect: 302 (redirect to CDN) in <1s

# 3. Check no qmd download is in progress (a hung TCP connection to hf.co is a tell)
ss -tnp | grep -E "huggingface|443" | head -5
```

If step 1 returns `000` and step 2 returns `302`, the network is definitely blocking HF main.

## Fix

node-llama-cpp honors the standard `HF_ENDPOINT` env var. Set it for the current process AND persist:

```bash
# Immediate
export HF_ENDPOINT=https://hf-mirror.com

# Persistent (so future sessions don't re-hit this)
grep -q HF_ENDPOINT ~/.bashrc || echo 'export HF_ENDPOINT=https://hf-mirror.com' >> ~/.bashrc

# Clean any stale partial downloads
rm -f ~/.cache/qmd/models/*.ipull

# Retry
HF_ENDPOINT=https://hf-mirror.com qmd pull
# or
qmd pull  # if you exported + sourced ~/.bashrc
```

Expected output (with hf-mirror):

```
⏵ hf_ggml-o...8_0.gguf  10.43% (35.42MB/333.59MB)  3.54MB/s | 1m23s left
⏵ hf_ggml-o...8_0.gguf  21.79% (72.71MB/333.59MB)  7.27MB/s | 60s left
...
```

Speeds of 15–25 MB/s on hf-mirror are normal. Total ~2GB downloads in 2–4 minutes.

## Models downloaded (do NOT need manual setup if HF_ENDPOINT works)

| Model | Size | Purpose |
|---|---|---|
| `embeddinggemma-300M-Q8_0.gguf` | 334 MB | Vector embeddings |
| `qwen3-reranker-0.6b-q8_0.gguf` | 640 MB | Result reranking |
| `qmd-query-expansion-1.7B-q4_k_m.gguf` | 1.2 GB | Query expansion |

Files land in `~/.cache/qmd/models/`. After all three are present, `qmd embed` finishes in seconds (no further downloads).

## Other env vars that may help

If `HF_ENDPOINT` doesn't take effect for a specific tool, try:

| Variable | Used by |
|---|---|
| `HF_ENDPOINT` | node-llama-cpp, huggingface_hub (HF standard) |
| `HUGGINGFACE_HUB_BASE_URL` | huggingface_hub (alt name) |
| `HUGGINGFACE_HUB_CACHE` | Cache directory override |
| `HF_HOME` | Same as above |
| `TRANSFORMERS_OFFLINE=1` | Force offline mode (use only after models exist locally) |

## Mirrors known to work in CN (Jun 2026)

- `https://hf-mirror.com` — official community mirror, fastest in our test (15-25 MB/s)

## Why the timeout is silent (qmd doesn't surface it loudly)

The node-llama-cpp fetch layer prints a friendly `Something is intercepting the download from huggingface.co...` message — but qmd's spinner UI swallows it under the "Gathering information" state. Always check `qmd doctor` AND the actual model directory, not just the spinner output.

## Lesson

This is a network-environment fact, not a qmd bug. Apply the same `HF_ENDPOINT` preflight to ANY future HF model puller on this host: llama.cpp CLI, sentence-transformers (via huggingface_hub), Ollama (some regions), etc. Capture in memory under the host's network profile so the next session doesn't re-discover it from scratch.
