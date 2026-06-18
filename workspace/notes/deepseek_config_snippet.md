# config.yaml 接入片段 — 需 B 手动粘贴

> 因为 `~/.hermes/config.yaml` 是 Hermes 安全敏感配置，agent 不能直接 patch。
> 请在 `providers:` 段下（紧跟 `minimax_domestic:` 之后）粘贴以下片段：

```yaml
  deepseek:
    base_url: https://api.deepseek.com/anthropic
    protocol: ''
    api_key: ${DEEPSEEK_API_KEY}
    api_mode: anthropic_messages
    available_models_json: '[{"id":"deepseek-v4-pro","name":"DeepSeek V4 Pro","context_window":1000000,"max_output_tokens":384000},{"id":"deepseek-v4-flash","name":"DeepSeek V4 Flash","context_window":1000000,"max_output_tokens":384000}]'
    cost_per_million:
      deepseek-v4-pro:
        input_cached: 0.025
        input_uncached: 3.0
        output: 6.0
        currency: CNY
      deepseek-v4-flash:
        input_cached: 0.02
        input_uncached: 1.0
        output: 2.0
        currency: CNY
    pricing_source: https://api-docs.deepseek.com/zh-cn/quick_start/pricing
    pricing_updated: 2026-06-17
```

## 粘贴位置

`~/.hermes/config.yaml` 第 163 行 `providers:` 段下，缩进对齐 `minimax_domestic:`。

## 粘贴后

`hermes gateway restart`（或重启 hermes-agent）让新 provider 生效。

## 已就绪（不依赖 config.yaml）

- `DEEPSEEK_API_KEY` 已写入 `~/.hermes/.env`
- `tools/deepseek_cost.py` 已就绪（CLI 调用，**不依赖** config.yaml 段）
- `notes/deepseek_ledger.md` 已初始化（起点 ¥44.35）
- 连通性测试可直接用 key 跑（也不依赖 config.yaml）

**config.yaml 段是给"未来从 Hermes 内部切换模型"用的优化配置，不是算费/连通性的前置条件**。当前所有 DeepSeek 协助流程已经能跑。
