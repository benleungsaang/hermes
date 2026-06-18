# Request Templates for Secondary Model Calls

Copy-paste templates the primary agent uses for the "申请" block.
Keep them short — the user is on a chat platform, not reading a
contract.

## Standard request block (default)

```
【申请 DeepSeek V4 Pro 协助】
任务：分析 1500 行的 BOM 提取 Python 脚本，找出内存泄漏路径
原因：我已扫一遍但有 3 个可疑点不确信，需要更严密的推理
预计：~3k input + 1k output，按官方价约 ¥0.5
调用后输出会标注【DeepSeek 协助】
同意请回 "1" 或 "yes"，拒绝请回 "0" 或 "no"
```

## Short request (when user is busy)

```
【申请 DeepSeek 协助】任务：[X]。原因：[Y]。预计 ¥[Z]。同意回 1/0。
```

## Re-request after rejection (only if conditions changed)

```
再次申请 DeepSeek 协助：刚才你说不需要，但我现在意识到这块
主要靠数学推导（不是经验判断），我这边准确率历史 60%。
预计 ¥[Z]。这次可以调吗？
```

## Result integration (always tag the secondary's contribution)

Inline form:
```
我先跑了 X（我自己），结果是 Y。但有个 [Z] 的子问题我不太
确定，调了 DeepSeek V4 Pro 协助：

【DeepSeek 协助】
[secondary's response, possibly summarized to 1-3 lines]
[/DeepSeek 协助]

综合下来答案是：[final synthesis, primary's voice]
```

Block form (for long secondary output):
```
DeepSeek V4 Pro 的完整分析如下：

---
[secondary's verbatim response, fenced or quoted]
---

我的判断是：[1-2 sentence synthesis]
```

## When NOT to use these templates

- The user has already turned on "always call without asking" for this model
- The model is the **primary** (not secondary)
- The task is a chat-platform content transformation (just do it inline)
