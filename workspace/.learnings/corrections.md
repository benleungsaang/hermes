# 用户纠正记录

- [2026-06-17] 把"我的工程进度"（qmd 装好、skills 更新、bug 修复等）当成了"用户的工作待办"列出来 → 严格区分 🔴【B-工作】= 用户自己做的事，🔵【B×H-讨论】= 需要和我讨论的工程事项。工程维护进度不进 reminders，进 MAINTENANCE.md（如果需要的话）。已写入 AGENTS.md "Reminders 分类规则" 章节，今后 session 启动自动遵守。
- [2026-06-17] 编号 "W-XXX / D-XXX" 是 Hermes 内部索引，B 不会用编号查询 → B 永远用人话查（"上次提过的泰国客户"），Hermes 自动定位；不要反过来要求 B 报编号。已写入 AGENTS.md "Reminders 分类规则 → 编号约定"。
- [2026-06-17] 微信 PC 端消息被切（反复出现）→ 根因不是单一：1) 我滥用空行分段 + 段末冒号（最常见） 2) 微信 PC 客户端自动按段落视觉分段 3) weixin.py 的 _should_split_short_chat_block_for_weixin（潜在，已用配置防御但未重启 gateway）。详细分析在 `.learnings/lessons/wechat-pc-message-splitting.md`，写作规范在 AGENTS.md "微信 PC 端写作规范" 章节。
- [2026-06-17] 差点用 write_file 覆盖 AGENTS.md（覆盖了所有 Reminders 分类、记忆助手工作流、微信写作规范章节）→ write_file 是全量覆盖不是追加，新增章节必须用 patch 或先 read 再 write 完整版。今后修改 AGENTS.md / reminders.md 等已有内容，**默认用 patch**，不用 write_file。已修复并验证 AGENTS.md 恢复 163 行 + 19 个二级标题。
