#!/usr/bin/env python3
"""
approval.py — 被动审批脚本（elma → bbbbb → 执行）

不需要轮询、不需要后台进程。三阶段调用:

  阶段 A - elma 提交申请(只创建文件,不等待)
    python3 approval.py submit "操作描述"
    写入 ~/.hermes/users/elma/approvals/<uuid>.json, status=pending
    输出待发飞书消息体(由 send_message 工具发送)
    立即退出

  阶段 B - bbbbb 填审批结果
    python3 approval.py decide <uuid> "同意" "备注"
    修改上述 json, status=approved/rejected
    立即退出

  阶段 C - 执行(谁调用都行:elma,bbbbb,或 cron)
    python3 approval.py execute <uuid>
    读取文件,根据 status 决定执行/拒绝
    立即退出

  辅助:
    python3 approval.py list          # 列出所有 pending/approved/rejected
    python3 approval.py show <uuid>   # 查看单个详情
"""
import sys
import os
import json
import uuid
import subprocess
from datetime import datetime
from pathlib import Path

# 引入同目录的意图分类器
sys.path.insert(0, str(Path(__file__).parent))
try:
    from intention_classifier import classify_with_keywords
except ImportError:
    def classify_with_keywords(op):
        return False, "未识别"

# 路径
APPROVAL_DIR = Path.home() / ".hermes" / "users" / "elma" / "approvals"
APPROVAL_DIR.mkdir(parents=True, exist_ok=True)

ADMIN_FEISHU_ID = "ou_319c04f041dfb251bd4a4eaa9f7ae43d"


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _gen_uuid() -> str:
    return uuid.uuid4().hex[:8]


def submit(operation: str) -> None:
    """阶段 A: elma 提交申请
    返回 elma 应看到的温和提醒话术(让 agent 在微信里回复 elma)
    """
    if len(sys.argv) < 3:
        print("用法: python3 approval.py submit <操作描述>")
        sys.exit(1)

    op = sys.argv[2]
    aid = _gen_uuid()

    # 先做意图判定,获取原因
    is_sensitive, reason = classify_with_keywords(op)
    if not is_sensitive:
        # 兜底:重新跑一次确保最新规则
        import subprocess as _sp
        r = _sp.run(
            ["python3", str(Path(__file__).parent / "intention_classifier.py"), op],
            capture_output=True, text=True
        )
        is_sensitive = r.returncode != 0
        reason = r.stdout.strip().split("\n")[-1].replace("原因: ", "") if r.stdout else "未识别原因"

    record = {
        "id": aid,
        "operation": op,
        "status": "pending",
        "submitted_at": _now(),
        "submitted_by": "elma",
        "channel": "weixin",
        "channel_chat_id": "o9cq804vpD1av7HMUGyTkztC5NAM@im.wechat",
        "admin_response": None,
        "admin_response_at": None,
        "executed_at": None,
        "execute_log": None,
        "notified_emma": False,
        "sensitive_reason": reason,  # 记录判定原因,供 elma 看
    }
    fp = APPROVAL_DIR / f"{aid}.json"
    fp.write_text(json.dumps(record, ensure_ascii=False, indent=2))

    # 飞书发给 bbbbb 的消息(管理员视角)
    feishu_msg = (
        f"【权限审批 #{aid}】\n"
        f"来源: elma(微信)\n"
        f"操作: {op}\n"
        f"原因: {reason}\n\n"
        f"回复编号 #{aid} + 同意/拒绝 (+ 备注)\n"
        f"例如: #{aid} 同意 测完恢复\n"
        f"或:   #{aid} 拒绝 不安全"
    )

    # 微信回复 elma 的话术(温和提醒 + 口语化 reason)
    # elma 看到的判定原因要简化,避免括号/英文触发微信切分
    reason_simple = reason.split("(")[0].strip()  # 去括号及之后
    reason_simple = reason_simple.replace("/", "或")  # 斜杠改中文

    elma_msg = (
        f"这个操作我帮您提交给 bbbbb 审一下。"
        f"原因:{reason_simple}。"
        f"审批结果出来后我会第一时间通知您。"
        f"您可以继续做别的事,不用等。"
    )

    print("=" * 70)
    print("[STAGE A] elma 提交审批")
    print("=" * 70)
    print(f"\napproval_id: {aid}")
    print(f"状态: pending")
    print(f"\n--- 飞书待发消息(给 bbbbb)---")
    print(feishu_msg)
    print("\n--- 微信待回 elma(温和提醒)---")
    print(elma_msg)
    print()
    print(f"\n接下来:")
    print(f"  1. agent 用 send_message 发飞书给 bbbbb (上面 feishu_msg)")
    print(f"  2. agent 用 send_message 发微信给 elma (上面 elma_msg)")
    print(f"  3. elma 不轮询,继续她自己的事")
    print(f"  4. bbbbb 回复后,agent 调 decide + 发微信通知 elma")


def decide(aid: str) -> None:
    """阶段 B: bbbbb 填审批结果 + 生成通知 elma 的微信消息"""
    if len(sys.argv) < 4:
        print("用法: python3 approval.py decide <aid> <同意|拒绝> [备注]")
        sys.exit(1)

    aid = sys.argv[2]
    decision = sys.argv[3]
    note = sys.argv[4] if len(sys.argv) > 4 else ""

    if decision not in ("同意", "拒绝", "approved", "rejected"):
        print(f"decision 必须是 同意/拒绝 或 approved/rejected, 得到: {decision}")
        sys.exit(1)

    fp = APPROVAL_DIR / f"{aid}.json"
    if not fp.exists():
        print(f"审批 #{aid} 不存在")
        sys.exit(1)

    record = json.loads(fp.read_text())
    if record["status"] != "pending":
        print(f"审批 #{aid} 已处理过 (status={record['status']})")
        sys.exit(1)

    new_status = "approved" if decision in ("同意", "approved") else "rejected"
    record["status"] = new_status
    record["admin_response"] = note
    record["admin_response_at"] = _now()
    fp.write_text(json.dumps(record, ensure_ascii=False, indent=2))

    # 生成 elma 通知消息(微信用,避免 \n\n 防客户端切分)
    if new_status == "approved":
        weixin_msg = (
            f"审批结果 #{aid}:已通过。"
            f"操作:{record['operation'][:30]}{'...' if len(record['operation']) > 30 else ''}。"
            f"{('备注:' + note + '。') if note else ''}"
            f"你下次发消息时自动执行。"
        )
    else:
        weixin_msg = (
            f"审批结果 #{aid}:已拒绝。"
            f"操作:{record['operation'][:30]}{'...' if len(record['operation']) > 30 else ''}。"
            f"{('原因:' + note + '。') if note else ''}"
            f"原操作未执行。"
        )

    print(f"审批 #{aid} 已更新: {new_status}")
    print(f"备注: {note or '(无)'}")

    # 关键:生成 elma 微信通知消息,让 bbbbb session 的 agent 调用 send_message 发送
    print()
    print("=== 待发 elma 微信消息(请 bbbbb 的 agent 用 send_message 发送)===")
    print(f"target: weixin:{record.get('channel_chat_id', 'o9cq804vpD1av7HMUGyTkztC5NAM@im.wechat')}")
    print(f"---微信消息内容---")
    print(weixin_msg)
    print("---end---")
    print()
    print("注:此消息必须在 bbbbb 的 session 里通过 send_message 发给 elma。")
    print("   approval.py 只负责状态文件,不直接发消息。")


def execute(aid: str) -> None:
    """阶段 C: 执行被批准的操作(此版本不实际执行 shell 命令,只返回状态)"""
    if len(sys.argv) < 3:
        print("用法: python3 approval.py execute <aid>")
        sys.exit(1)

    aid = sys.argv[2]
    fp = APPROVAL_DIR / f"{aid}.json"
    if not fp.exists():
        print(f"审批 #{aid} 不存在")
        sys.exit(1)

    record = json.loads(fp.read_text())

    if record["status"] == "pending":
        print(f"审批 #{aid} 仍在 pending。bbbbb 还没回复。")
        print(f"操作未执行。")
        sys.exit(2)

    if record["status"] == "rejected":
        record["executed_at"] = _now()
        record["execute_log"] = "rejected - no execution"
        fp.write_text(json.dumps(record, ensure_ascii=False, indent=2))
        print(f"审批 #{aid} 已被 bbbbb 拒绝。")
        print(f"备注: {record.get('admin_response', '(无)')}")
        print(f"操作未执行。")
        sys.exit(0)

    if record["status"] == "approved":
        print(f"审批 #{aid} 已批准。")
        print(f"操作: {record['operation']}")
        print(f"备注: {record.get('admin_response', '(无)')}")
        print(f"\n注意:此脚本不直接执行 shell 命令。")
        print(f"agent 现在可以根据此状态决定执行 hermes config / pip install / git push 等。")
        # 标记为已通知(但不实际执行,因为 hermes 命令由 agent 上下文决定)
        record["executed_at"] = _now()
        record["execute_log"] = "approved - ready for agent to execute"
        fp.write_text(json.dumps(record, ensure_ascii=False, indent=2))
        sys.exit(0)


def list_all() -> None:
    """辅助:列出所有审批"""
    items = sorted(APPROVAL_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not items:
        print("无审批记录")
        return

    print(f"{'ID':<10} {'STATUS':<10} {'OPERATION':<40} {'TIME':<20}")
    print("-" * 90)
    for fp in items[:20]:
        r = json.loads(fp.read_text())
        op_short = r["operation"][:38] + ".." if len(r["operation"]) > 40 else r["operation"]
        print(f"{r['id']:<10} {r['status']:<10} {op_short:<40} {r['submitted_at']:<20}")


def show(aid: str) -> None:
    fp = APPROVAL_DIR / f"{aid}.json"
    if not fp.exists():
        print(f"审批 #{aid} 不存在")
        sys.exit(1)
    print(json.dumps(json.loads(fp.read_text()), ensure_ascii=False, indent=2))


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)

    cmd = sys.argv[1]
    if cmd == "submit":
        submit(sys.argv[2] if len(sys.argv) > 2 else "")
    elif cmd == "decide":
        decide(sys.argv[2] if len(sys.argv) > 2 else "")
    elif cmd == "execute":
        execute(sys.argv[2] if len(sys.argv) > 2 else "")
    elif cmd == "list":
        list_all()
    elif cmd == "show":
        if len(sys.argv) < 3:
            print("用法: python3 approval.py show <aid>")
            sys.exit(1)
        show(sys.argv[2])
    else:
        print(f"未知命令: {cmd}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
