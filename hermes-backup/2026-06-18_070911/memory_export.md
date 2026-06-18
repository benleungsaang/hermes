# Hermes Memory Export (2026-06-18)
# Safe to upload — no API keys, no passwords, no secrets.
# Restore with: hermes memory import (or manual re-add via conversation)

## Personal Notes (memory)
1. B 的技术交流风格（包装机选型场景下观察到的稳定偏好）：
   1a. 不接受笼统/绝对回答。选型回答必须带条件分支，列出"什么情况下例外"
   1b. 关注底层机制，不只是结论。触及原理而非只背规则
   1c. 对成本数字敏感且会校准
   1d. 培训时用反例驱动教学

2. Network: huggingface.co is BLOCKED from this host. hf-mirror.com works at 20+ MB/s.
   Set HF_ENDPOINT=https://hf-mirror.com before any model-pull.

3. DeepSeek 接入（2026-06-17）：key 走本地 .env。记账 notes/deepseek_ledger.md。
   主模型 = DeepSeek V4 Flash。MiniMax 仅用于 vision_analyze。
   每条任务结尾必报费用结算：tokens + 费用 + 累计 + 余额 + 任务。
   每次回复标注【DeepSeek Flash 协助】。

4. Reply format: 待办回复 = 序号列表 + 空行分隔。用户用人话问不反问编号。

5. BOM extraction (D-001): User sends PDF/image → VISION reads → DXF MTEXT cross-verify.
   DWG 自动转换通过 ODAFC。cad_bom_extract.py 支持 .dwg。
   依赖 libfuse2 + xvfb。No ezdxf rendering.
   Format: markdown table, English names, merge same-spec, sort by flow, cabinet last.

6. BOM 位置标注规则（2026-06-18）：每项必须有明确位置描述，不笼统。

## User Profile
1. 称呼：BBBBB
2. 个人记忆助手工作流：范围 = 个人生活/工作/技术学习笔记。源文件不保存。
3. 沟通偏好：默认极简，追问才展开。选型回答带条件分支+原理。培训反例驱动。
   轻量化优先。内部ID不暴露。渲染bug先问客户端。
4. 包装机命名规则 HP/VP/BF/BS/FB 等在工作区 .learnings/domains/packaging-machines.md
5. 主模型：DeepSeek Flash。MiniMax M3 仅用于 vision_analyze。
6. BOM 合并规则合集：
   - 同类型同规格合并，编号支持非连续（如 1-2,4）
   - Electrical cabinet 始终排主表最后
   - Infeed conveyor 不列主表，放"忽略项"区段
   - VISION 提示语需列出每个小字
   - DXF 有但 VISION 未确认的列 [?] 行
   - 技术参数（0.6Mpa/3KW/220V等）不当作部件名

## BOM Rules Detail
- 同类型同规格部件用编号范围合并：Main conveyor 2-3 (600x1000) → x2
- 非连续编号：Sinking conveyor 1-2,4 (1900mm) → x3
- Electrical cabinet 始终排主表最后（不受流向影响），标注件不需隐含底色
- Infeed conveyor 放入主表下方"忽略项"灰色斜体区段
- 每个 BOM 条目的说明栏必须有明确位置描述
