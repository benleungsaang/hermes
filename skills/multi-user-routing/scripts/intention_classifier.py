#!/usr/bin/env python3
"""
intention_classifier.py — 意图判定(替代关键字匹配)

不是检测字符,而是基于操作描述判定是否敏感。
无 LLM 时降级到关键字表;有 LLM 时调用 DeepSeek/MiniMax 做语义判定。

用法:
  python3 intention_classifier.py "切换默认模型到 GPT-4"
  输出: SENSITIVE | NON_SENSITIVE + 理由
"""
import sys
import os
import re

# 敏感操作类别(语义层,不是命令匹配)
SENSITIVE_CATEGORIES = {
    "system_config": "修改 Hermes 系统配置(config.yaml / .env / 模型 / provider)",
    "package_install": "安装/卸载/升级系统包(pip / apt / npm / cargo)",
    "skill_management": "装/删/修改 skill 文件(SKILL.md / scripts/)",
    "cron_modify": "创建/删除/修改定时任务(cron job)",
    "git_push_public": "推送到 GitHub / 公开仓库 / 共享存储",
    "destructive_delete": "删除文件/目录(rm -rf / 大范围删除)",
    "credential_modify": "改密钥 / API key / 令牌 / .env",
    "cross_user_write": "写入 bbbbb 用户目录(跨用户数据)",
    "cross_user_read": "读取 bbbbb 用户目录(隐私)",
    "shared_dir_write": "写入共享目录(skills/ / .learnings/ / config/)",
    "network_public": "公开网络操作(发送邮件 / 推特 / 公开 webhook)",
}

# 兜底关键字(无 LLM 时使用)
# 每条: (触发词列表, 类别)
# 触发词按"出现任一即匹配"
FALLBACK_SENSITIVE_RULES = [
    # system_config — 改 Hermes 配置/模型/provider
    (["改配置", "改设置", "改模型", "换模型", "切换模型", "换 provider",
      "切换 provider", "改 provider", "改 api key", "换 api key",
      "改 .env", "改 config", "hermes config"], "system_config"),

    # package_install — 装/卸/升级包
    (["装包", "装一下", "装一个", "卸载", "升级", "降级",
      "pip install", "pip uninstall", "apt install", "apt remove",
      "npm install", "cargo install"], "package_install"),

    # skill_management — 装/删/改 skill
    (["装 skill", "装一个 skill", "删 skill", "改 skill",
      "改 SKILL.md", "写 SKILL.md"], "skill_management"),

    # cron_modify
    (["改 cron", "改 crontab", "创建定时", "删除定时", "改定时"], "cron_modify"),

    # git_push_public
    (["git push", "推 git", "推送 github", "推 gitlab",
      "gh repo", "gh pr", "提交代码"], "git_push_public"),

    # destructive_delete
    (["rm -rf", "rm -f /", "删文件", "删目录", "清空目录",
      "删除全部", "都删了", "清空"], "destructive_delete"),

    # credential_modify
    (["改密钥", "改密码", "改 token", "改 api", "改 key"], "credential_modify"),

    # cross_user_read/write — 跨用户
    # "管理员"在 elma 上下文里专指 bbbbb,只有配合"操作动词"才视为敏感操作
    # (单独的"管理员"二字可能是普通提及,不应误判)
    (["读 bbbbb", "看 bbbbb", "看 boss", "看老板",
      "管理员的待办", "管理员的笔记", "管理员的记忆",
      "管理员待办", "管理员笔记", "管理员记忆"], "cross_user_read"),
    (["看管理员", "管理员有什么", "管理员做啥",
      "管理员今天", "管理员最近"], "cross_user_read"),
    (["写 bbbbb", "写管理员", "改 bbbbb"], "cross_user_write"),

    # shared_dir_write
    (["写 skills", "改 skills", "写 .learnings", "改 .learnings"], "shared_dir_write"),

    # network_public
    (["发邮件", "发推", "发 twitter", "公开 webhook"], "network_public"),
]


def classify_with_keywords(operation: str) -> tuple[bool, str]:
    """无 LLM 兜底:基于规则匹配
    规则:每条规则有一个触发词列表,任一词出现即触发;同时支持"词 A + 词 B"语义组合
    """
    op_lower = operation.lower()

    # 规则 1: 单一词匹配
    for trigger_words, category in FALLBACK_SENSITIVE_RULES:
        for kw in trigger_words:
            if kw.lower() in op_lower:
                reason = SENSITIVE_CATEGORIES.get(category, "命中敏感规则")
                return True, f"{reason} (匹配: \"{kw}\")"

    # 规则 2: 语义组合(如"模型"+"换/改/切/调")
    semantic_combos = [
        # (动词词集, 名词词集, 类别)
        ({"换", "切", "改", "调", "换到", "切到", "改成", "调成"},
         {"模型", "model", "provider", "配置", "设置"},
         "system_config"),
        ({"装", "安装", "卸", "卸载", "升级"},
         {"包", "package", "skill", "插件", "plugin"},
         "package_install"),
        ({"读", "看", "查", "显示", "列出"},
         {"bbbbb", "管理员", "boss", "老板", "管理员的"},
         "cross_user_read"),
        ({"写", "改", "覆盖"},
         {"bbbbb", "管理员", "boss", "老板", "管理员的"},
         "cross_user_write"),
        ({"删", "rm", "清空"},
         {"文件", "目录", "folder", "directory", "file"},
         "destructive_delete"),
        ({"推", "push"},
         {"git", "github", "gitlab", "代码"},
         "git_push_public"),
    ]
    import re as _re
    # 提取操作里的"词"集合(2 字符以上的汉字或英文)
    words_zh = set(_re.findall(r'[\u4e00-\u9fff]+', operation))
    words_en = set(_re.findall(r'[a-z]+', op_lower))
    all_words = words_zh | words_en

    for verbs, nouns, category in semantic_combos:
        verb_match = any(any(v in w or w in v for w in all_words) for v in verbs)
        noun_match = any(any(n in w or w in n for w in all_words) for n in nouns)
        if verb_match and noun_match:
            reason = SENSITIVE_CATEGORIES.get(category, "语义组合触发")
            return True, f"{reason} (语义: 动词∩名词)"

    return False, "未命中敏感关键字/语义组合"


def classify_with_llm(operation: str) -> tuple[bool, str]:
    """有 LLM 时:语义判定(调用 DeepSeek/MiniMax)
    当前未启用,留作扩展点"""
    return classify_with_keywords(operation)


def main():
    if len(sys.argv) < 2:
        print("用法: python3 intention_classifier.py <操作描述>")
        sys.exit(1)

    operation = " ".join(sys.argv[1:])
    is_sensitive, reason = classify_with_llm(operation)

    label = "SENSITIVE" if is_sensitive else "NON_SENSITIVE"
    print(f"[{label}] {operation}")
    print(f"原因: {reason}")

    sys.exit(0 if not is_sensitive else 1)


if __name__ == "__main__":
    main()
