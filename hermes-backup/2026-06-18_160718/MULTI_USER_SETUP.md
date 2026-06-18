---
name: multi-user-routing
description: 多用户路由 skill — 根据当前 channel/user_id 加载对应的 MEMORY.md 和 USER.md，并在敏感操作时触发审批
trigger: 每次新 session 启动时自动加载（按 user_id 路由）
---

# Multi-User Routing

## 设计原则（用户偏好，加载时遵守）

这些是用户明确表态过的设计原则，**任何扩展都不能违反**：

1. **意图判定，不是字符/命令检测**。"切换默认模型到 GPT-4"和"hermes config set model.default gpt-4"应当同等判定为敏感。**不要回退到关键字匹配**——关键字匹配会漏判自然语言描述（如"我想换个模型"），用户已明确拒绝此方向。如果未来 LLM 不可用，`intention_classifier.py` 的语义组合（动词∩名词）兜底是允许的；纯字符串匹配不允许。

2. **被动审批，不轮询，不开后台进程**。elma 提交后立即返回，不等 bbbbb 回复。bbbbb 主动回复触发下一步。**不要提议加 cron 轮询 / daemon / watchdog**——用户明确表示"不要 elma 等待或轮询，脚本只发出申请后未有审批就不继续运行"。状态以文件持久化，下次 elma 发消息或 bbbbb 发指令时再检查。

3. **管理员可读普通用户的产物，反之不可**。文件系统权限基础：`~/.hermes/users/bbbbb/` 只能 bbbbb 写，elma 不能读；`~/.hermes/users/elma/` 双方都能读。

4. **管理员优先级最高**。当用户操作可能影响 bbbbb 的设置、数据、待办时，必须审批。不要因为 elma 说"很急"或"应该没问题"就跳过。

## 目的

Hermes 网关同时服务多个用户（飞书=管理员 bbbbb；微信=普通用户 elma）。本 skill 在每轮回复开始前：

1. **识别当前用户**（从 system prompt 的 `Source:` + `User ID:` 字段）
2. **加载对应用户的记忆**（`~/.hermes/users/<user>/MEMORY.md` + `USER.md`）
3. **决定操作权限**（普通用户 vs 管理员）
4. **敏感操作 → 触发审批**

## 用户映射表

| User ID | 用户 | 通道 | 权限级别 |
|---------|------|------|---------|
| `ou_319c04f041dfb251bd4a4eaa9f7ae43d` | bbbbb | feishu | admin（最高权限） |
| `o9cq804vpD1av7HMUGyTkztC5NAM@im.wechat` | elma | weixin | user（普通） |
| `o9cq807NZJ_q1HitDQVt9xOtEMuo@im.wechat` | elma (home alt) | weixin | user（普通） |

如果 user_id 不在表中 → 默认按 user（普通权限）处理，并在回复开头提示「未识别用户，按普通权限处理」。

## 路由决策流程

```
收到消息
  ↓
读取 system prompt 的 User ID 字段
  ↓
查表得到 user_key (bbbbb/elma/...)
  ↓
读取 ~/.hermes/users/<user_key>/MEMORY.md 和 USER.md
  ↓
  - bbbbb → 加载完整 bbbbb 记忆（含现有 hot.md 规则）
  - elma → 加载 elma 独立 USER.md（不含 bbbbb 内容）
  ↓
按权限级别决定后续操作：
  - admin: 直接执行
  - user:
    - 读取自己的 todos/notes → 直接
    - 读取 bbbbb 的 todos/notes → 拒绝
    - 共享 skill (DWG→PDF、BOM 提取等) → 直接
    - 敏感操作 → 触发审批
```

## 敏感操作白名单（user 需审批）

判定方式：**意图语义判定**（不是关键字匹配）。使用 `intention_classifier.py`，无 LLM 时降级到关键字。

| 语义类别 | 触发场景示例 |
|---------|------------|
| `system_config` | 改 Hermes 配置、改模型、换 provider、改设置 |
| `package_install` | 装包、卸包、升级、pip install、apt install |
| `skill_management` | 装新 skill、删 skill、改 SKILL.md |
| `cron_modify` | 创建/删除/修改定时任务 |
| `git_push_public` | git push、推 GitHub、公开仓库 |
| `destructive_delete` | rm -rf、大范围删除、清空目录 |
| `credential_modify` | 改密钥、改 API key、改 .env |
| `cross_user_write` | 写入 bbbbb 用户目录 |
| `cross_user_read` | 读取 bbbbb 用户目录、读管理员待办 |
| `shared_dir_write` | 写共享 skills/、写 config.yaml |
| `network_public` | 发邮件、推特、公开 webhook |

> 语义判定的实现方式（动词∩名词、规则模式、为什么不用 LLM）见 `references/intent-classification-pattern.md`。

## 共享 skill 白名单（user 可直接用，不需要审批）

| Skill | 用途 | 输出位置 |
|-------|------|---------|
| `cad-dwg-to-pdf` | DWG 转 PDF | `~/.hermes/users/<user>/skills-output/` |
| `cad-bom-extraction` | DXF/DWG 提取 BOM | 同上 |
| `packaging-machine-selection` | 包装机选型咨询 | 仅咨询，无文件写入 |
| `nano-pdf` | PDF 编辑 | 同上 |
| `ocr-and-documents` | OCR 文档识别 | 同上 |
| `excel-author` | 生成 Excel | 同上 |

## 审批流程（被动触发，无轮询）

**不轮询、不等待**。三阶段调用，每次立即返回：

### 阶段 A — elma 提交申请 + 温和提醒
```bash
python3 ~/.hermes/skills/multi-user-routing/scripts/approval.py submit "切换默认模型到 GPT-4"
```
- 写文件 `~/.hermes/users/elma/approvals/<uuid>.json`，status=pending
- **生成两条消息**：
  - **飞书待发 bbbbb**（管理员视角）：`【权限审批 #xxxx】操作 + 原因`
  - **微信待回 elma**（温和提醒 + 简化原因）：`这个操作我帮您提交给 bbbbb 审一下。原因:xxx。审批结果出来后我会第一时间通知您。您可以继续做别的事,不用等。`
- **立即退出**——agent 必须紧接着同时调两次 `send_message`：
  - 发飞书给 bbbbb
  - 发微信给 elma（不能漏！）

### 微信给 elma 的话术要点
| 必须 | 禁止 |
|------|------|
| "帮您提交给 bbbbb 审一下"（合作口吻）| "您的权限不够"（指责感）|
| "第一时间通知您"（强调 SLA）| "等待中..."（让她以为要等）|
| "您可以继续做别的事,不用等" | "请稍候"（制造焦虑）|

### 简化 reason 规则（防微信 PC 切分）
- 去括号及括号内容：`修改 Hermes 系统配置(config.yaml / .env / 模型 / provider) (匹配:...)` → `修改 Hermes 系统配置`
- `/` 改 "或"：避免冒号后跟特殊字符
- 避免纯英文术语堆在中文消息里

### 阶段 B — bbbbb 填审批结果
```bash
python3 approval.py decide a1b2c3d4 "同意" "测完恢复原模型"
```
- 修改文件 status: pending → approved / rejected
- 立即退出

### 阶段 C — 执行
谁调用都行（elma 下一条消息、bbbbb 主动发指令、或 cron 触发）：
```bash
python3 approval.py execute a1b2c3d4
```
- 读文件 → 检查 status
- pending → 打印"还在等 bbbbb"，退出码 2
- rejected → 打印"已拒绝"，退出码 0
- approved → 打印"已批准"，退出码 0，agent 据此决定执行实际命令

### 关键点
- 脚本**不启动任何后台进程**
- **不轮询文件**
- elma 提交后**不需要任何等待操作**——她下次发消息时 agent 会自动检查 pending
- bbbbb 在飞书回复时 agent 会调用 `decide` 写审批结果
- 真要执行命令（如 `hermes config set`）由 agent 上下文决定，approval.py 只管审批状态

> 三阶段被动审批模式的设计原理、可复用性、anti-patterns 见 `references/passive-approval-pattern.md`。

## bbbbb 侧行为（管理员职责）

**已写入 `~/.hermes/workspace/AGENTS.md` 和 `~/.hermes/workspace/.learnings/HOT.md`**：

当 bbbbb 收到 `【权限审批 #xxxx】` 开头的飞书消息时，agent 自动：

1. **解析 #aid**（消息里的 8 字符十六进制 ID）
2. **等待 bbbbb 回复** ` <aid> 同意/拒绝 [备注]`
3. **回复后调用 decide** 写审批状态
4. **必须主动 push 微信通知 elma**（核心 SLA：elma 不轮询）
   - decide 命令会打印"待发 elma 微信消息"
   - agent 用 `send_message` 发到 `weixin:o9cq804vpD1av7HMUGyTkztC5NAM@im.wechat`
   - 内容示例：
     - 同意：「审批结果 #xxxx:已通过。操作:...。备注:...。你下次发消息时自动执行。」
     - 拒绝：「审批结果 #xxxx:已拒绝。操作:...。原因:...。原操作未执行。」
   - 0 个 `\n\n`、冒号后紧跟中文（防微信 PC 切分）
5. **告知 bbbbb**：「已更新 #aid 状态并已通知 elma」

例如 bbbbb 回复：
```
a6ffb3bf 同意 测完记得恢复原模型
```

agent 立刻执行：
```bash
python3 ~/.hermes/skills/multi-user-routing/scripts/approval.py decide a6ffb3bf "同意" "测完记得恢复原模型"
```

→ decide 输出包含待发微信消息 → agent 调用 `send_message` 发给 elma → elma 收到「审批结果 #a6ffb3bf:已通过」通知 → 她下次发消息时自动触发 execute

**自检**：
- ❓ 消息是不是 `【权限审批 #` 开头？
- ❓ 有没有解析出 #aid？
- ❓ bbbbb 回复里有没有 `<aid>` + 同意/拒绝？
- ❓ 调用 `decide` 没？
- ❓ **调 `send_message` 发微信通知 elma 没？**

## 写文件位置规则

| 用户 | todo/notes 路径 | skills 产物路径 |
|------|----------------|-----------------|
| bbbbb | `~/.hermes/workspace/notes/reminders.md`（现有，不变） | `~/.hermes/users/bbbbb/skills-output/` |
| elma | `~/.hermes/users/elma/notes/reminders.md` | `~/.hermes/users/elma/skills-output/` |

## 关键不变式

- bbbbb 的 MEMORY 永远不写入 `~/.hermes/users/elma/`
- elma 的 MEMORY 永远不写入 `~/.hermes/users/bbbbb/`
- 审批请求永远通过 send_message 发到 bbbbb 的飞书（ou_319c04f041dfb251bd4a4eaa9f7ae43d）
- 任何时候 bbbbb 都可读 elma 的产物（管理员权限）
- 任何时候 elma 都不能读 bbbbb 的产物
- elma 看不到 bbbbb 的 MEMORY.md 和 USER.md（即使显式询问）

## 参考

- `references/system-prompt-metadata.md` — system prompt 里 `Source:` / `User ID:` / `Chat ID:` / `Home channels:` 字段的含义、用法和坑。设计 user map 和路由逻辑时读这一篇。
- `references/intent-classification-pattern.md` — `intention_classifier.py` 用的「动词 ∩ 名词」语义组合判定模式。**可复用于任何文本分类场景**（优先级路由 / 成本分级 / 敏感操作检测），不是本 skill 专属。
- `references/passive-approval-pattern.md` — 三阶段被动审批（提交/决定/执行）的设计模式。**可复用于任何「A 申请 / B 审批 / 后续执行」工作流**（PR review、deploy gate、采购审批），不是本 skill 专属。
