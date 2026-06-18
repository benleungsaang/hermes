# Memory Export — 2026-06-18 (备份版 v2)

> Generated: 2026-06-19 (Asia/Shanghai)
> 备份脚本: hermes-backup skill

---

## MEMORY.md (2081 chars)

```markdown
B 的技术交流风格（包装机选型场景下观察到的稳定偏好）：
1. **不接受笼统/绝对回答**。当我说"❌ 不能用量杯""立式机不适合定型单品""默认推枕式"时，他会立刻反例修正。期望：选型回答必须带条件分支，列出"什么情况下例外"。
2. **关注底层机制，不只是结论**。他纠正"螺杆秤"时解释了 WHY（螺杆秤也是体积计量，密度变化同样偏差）。期望：技术回答触及原理而非只背规则。
3. **对成本数字敏感且会校准**。他确认了我说的 ¥2-5万 组合秤价差区间。后续报价/成本讨论时，他给的校准数字是稳定参考。
4. **培训时用反例驱动教学**。他不直接说正确答案，而是先用我的错误回答当靶子，再展开"实际是这样 + 还有这些变体"。这是他的培训方式，按这个节奏配合效果好。
§
Network: huggingface.co is BLOCKED from this host (HTTPS connection times out). The mirror hf-mirror.com works at 20+ MB/s. node-llama-cpp (used by qmd and any llama.cpp-based tool) honors `HF_ENDPOINT=https://hf-mirror.com` — set this env var BEFORE running any model-pull. Other HF env vars that may also help: `HUGGINGFACE_HUB_BASE_URL`, `HUGGINGFACE_HUB_CACHE`. Already added to ~/.bashrc.
§
DeepSeek 接入（2026-06-17, v0.3 切换 2026-06-18）：key 走本地 .env 绝不能贴对话。记账 `notes/deepseek_ledger.md`,基线 ¥44.35,v4-flash input ¥1/M+cached ¥0.02/M+output ¥2/M。**v0.3 现状**：MiniMax-M3=主（custom:minimax_domestic, anthropic_messages, api.minimaxi.com），DeepSeek V4 Flash 走 `model.fallback_providers` 兜底。**关键 bug**：provider=minimax 但 base_url 留 DeepSeek 的→实际打 DeepSeek 用 MiniMax key 必 401→看似"额度耗尽"。修复必 4 者一致。验证命令在 hermes-model-failover skill。DeepSeek 只在 vision_analyze 内部用。
§
Reply format (2026-06-17, reinforced by skill rules in `chat-concise-defaults` + `hermes-personal-knowledge-loop`):
- 待办/待处理项目 reply = "1. XXX" 序号列表 + 空行分隔，不用 W-001/D-001
- "待办" 默认只回 🔴 W-工作，"待处理项目" 只回 🔵 D-讨论，"提醒事项" 两类都带标签
- 任何 "W-XXX/D-XXX" 是 agent 内部账本，用户永远用人话问，不反问"哪个编号"
§
BOM extraction (D-001): User sends PDF/image → VISION reads BOM → DXF MTEXT cross-verify. DWG 自动转换通过 ODAFC（~Apps/ODAFileConverter_QT6_lnxX64_8.3dll_27.1.AppImage）配置在 ezdxf.ini [odafc-addon] unix_exec_path。cad_bom_extract.py 支持 .dwg 输入自动转 DXF 再读。依赖 libfuse2 + xvfb。No ezdxf rendering. Format: `| # | 部件 | 规格 | 数量 | 说明 |`, part names original English. Same-name same-spec merge; different spec separate. Sort by material flow. Electrical cabinet auto-appends to end.
§
BOM 位置标注规则（2026-06-18）：每项 BOM 的说明栏必须有明确位置描述（如"主输送线最右侧""4支线各一，包装主机位置"），来源为 VISION 布局分析中的各区段位置信息。不允许笼统描述（如"主输送段""挡板"）。是整理遗漏问题，不是 VISION 未提供。
```

---

## USER.md (1201 chars)

```markdown
称呼：BBBBB（单字母 B 易与其他内容混淆，2026-06-16 改用 BBBBB）
§
「个人事项记忆助手」工作流（2026-06-16 设定）：
- 范围：个人生活 / 工作（客户/订单/会议） / 技术学习笔记
- 输入：文字/语音/图片/视频 都可能
- 我：接收后归纳整理成文字
- 源文件：不保存（音/视频/图片解析完即丢弃）
- 存储：具体事项不写入内置记忆；B 主动问时才检索；介质（Markdown/SQLite/文件库）待后续讨论
- 实现：用户逐一从头讨论，先记偏好与边界，方案细节后续再定
§
沟通偏好（2026-06-17 扩充）：
- 默认极简；追问才展开
- 选型/技术回答**带条件分支 + 原理**，不笼统/绝对
- **培训用反例驱动**：先说错哪、再展开正确+变体
- 轻量化优先：ship minimum, ask if more needed
- 内部 ID（W-NNN/D-NNN）不暴露
- 渲染 bug 先问客户端（WeChat/Telegram/Web/CLI）再下结论
§
- 包装机命名规则 HP/VP/BF/BS/FB 等已整理在
    ~/.hermes/workspace/.learnings/domains/packaging-machines.md
- 价格来源：用户指名（如"建文"）→ 落盘带源；未指名 → 默认"自家"。绝不编造渠道（2026-06-17）
- 立式机 vs 给袋机判定以 B 口语为准，不根据型号号（420/180）猜（2026-06-17，已写入 packaging-machine-selection skill）
§
默认主模型：DeepSeek Flash（2026-06-17 起）。MiniMax M3 仅用于 vision_analyze（多模态图识别）。所有对话和工具任务用 DeepSeek Flash，不再需要"申请"DeepSeek 协助流程。每次多步任务完成后必须显示费用结算（prompt tokens / completion tokens / 费用 / 余额 / 任务描述）。
§
喜欢轻量实用方案，会果断叫停不产出的复杂尝试。我应主动简化方案而非等他纠正。他发 PDF/图片时先 VISION 读，不够清晰才用 DXF 辅助，不要自作主张跑渲染。
§
BOM 规则合集（2026-06-18 累计）：同类型同规格合并，编号支持非连续（如 1-2,4）。Electrical cabinet 始终排主表最后。Infeed conveyor 不列主表，放"忽略项"区段。VISION 提示语需明确要求列出每个小字。DXF 有但 VISION 未确认的标注列[?]行由用户确认。技术参数（0.6Mpa/3KW/220V等）不当作部件名。
§
称呼：Elma（通过此微信联系时使用）
```

---

## 本次新增内容（v1 → v2 变化）

### 1. 模型配置变化
- **v1**: 默认模型 DeepSeek-v4-flash
- **v2**: 默认模型 MiniMax-M3 + fallback DeepSeek-v4-flash
- 原因: 用户切换主模型并要求 quota 耗尽自动切 DeepSeek 兜底

### 2. 新增 skill
- `~/.hermes/skills/multi-user-routing/` — 多用户路由 + 审批流
- `~/.hermes/skills/cad-dwg-to-pdf/` — DWG 转 PDF（ODA + ezdxf + pymupdf）
- `~/.hermes/skills/hermes-backup/` — 自动备份到 GitHub

### 3. 新增用户隔离目录
- `~/.hermes/users/bbbbb/` — 管理员（暂未迁移）
- `~/.hermes/users/elma/` — 普通用户（独立 MEMORY/USER/reminders/approvals/skills-output）

### 4. bbbbb 行为规则变更
- `~/.hermes/workspace/AGENTS.md` 新增「管理员职责：审批 elma」
- `~/.hermes/workspace/.learnings/HOT.md` 新增「elma 审批职责」章节
- 多用户权限矩阵：shared skills + 隔离 memory + 审批流

### 5. 备份机制
- repo: https://github.com/benleungsaang/hermes
- 滚动保留 10 版
- token 存 ~/.hermes/.env (HERMES_BACKUP_TOKEN)
