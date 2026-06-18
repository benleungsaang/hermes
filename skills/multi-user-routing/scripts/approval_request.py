#!/usr/bin/env python3
"""
approval_request.py — elma 触发敏感操作时调用此脚本

用法:
  python3 approval_request.py "操作描述" "原因"

效果:
  - 发飞书给 bbbbb
  - 打印 elma 应回复的内容(不需要等待回复——实际审批通过 bbbbb 在飞书里手动回复触发)
"""
import sys
import os

# bbbbb 的飞书 chat_id
ADMIN_FEISHU_ID = "ou_319c04f041dfb251bd4a4eaa9f7ae43d"

def build_approval_message(operation: str, reason: str) -> str:
    return (
        "【权限审批】\n"
        f"来源: elma(微信)\n"
        f"操作: {operation}\n"
        f"她说: {reason}\n\n"
        "回复「同意」放行 / 「拒绝」阻断"
    )

def main():
    if len(sys.argv) < 3:
        print("用法: python3 approval_request.py <操作描述> <原因>")
        sys.exit(1)
    op = sys.argv[1]
    reason = sys.argv[2]
    msg = build_approval_message(op, reason)
    print("=== 待发飞书消息 ===")
    print(msg)
    print("==================")
    print(f"\n目标 chat_id: {ADMIN_FEISHU_ID}")
    print("\n注意:此脚本仅打印。实际发送需用 send_message 工具。")

if __name__ == "__main__":
    main()
