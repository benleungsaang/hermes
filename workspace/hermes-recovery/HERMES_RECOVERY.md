# Hermes 服务完整恢复清单

> 在新服务器上重新部署 Hermes Agent 的逐步骤指南。
> 由 agent 读取本文件后按序执行。

---

## Step 0 — 前置条件

- Ubuntu 22.04+ / Debian 12+
- Python 3.12+
- Git
- GitHub 仓库已 clone（含本恢复目录）

```bash
sudo apt-get update && sudo apt-get install -y git python3.12 python3.12-venv curl wget
```

---

## Step 1 — 恢复 Skills

```bash
# 将 GitHub 上的 skills/ 复制到 Hermes 目录
cp -r <repo>/skills/* ~/.hermes/skills/
```

确认：`ls ~/.hermes/skills/` 应看到 33 个技能目录。

---

## Step 2 — 恢复 Workspace（自定义工具 + 知识库）

```bash
cp -r <repo>/workspace/cad-bom/ ~/.hermes/workspace/cad-bom/
cp -r <repo>/workspace/notes/ ~/.hermes/workspace/notes/
cp -r <repo>/workspace/.learnings/ ~/.hermes/workspace/.learnings/
cp -r <repo>/workspace/hermes-recovery/ ~/.hermes/workspace/hermes-recovery/
```

确认：`ls ~/.hermes/workspace/` 应看到 cad-bom/ notes/ .learnings/ hermes-recovery/

---

## Step 3 — 恢复 config.yaml

```bash
# 复制脱敏后的 config.yaml，重新填入 API key
cp <repo>/config.yaml ~/.hermes/config.yaml
```

⚠️ 编辑 `~/.hermes/config.yaml` 填入实际的 API key：
- 主模型 provider 的 API key
- `auxiliary.vision.provider` 的 API key
- 其他第三方服务 key

---

## Step 4 — 配置 .env（API 密钥）

```bash
# 创建 .env 文件，填入以下密钥（顺序不重要，但必须全部设置）
cat > ~/.hermes/.env << 'ENVEOF'
# 主模型
DEEPSEEK_API_KEY=sk-xxxxxxxxxxxx

# 视觉模型
# MiniMax（当前 vision_analyze 用）
MINIMAX_API_KEY=xxxxxxxxxxxx

# 其他平台（按需）
# OPENAI_API_KEY=
# ANTHROPIC_API_KEY=
ENVEOF

chmod 600 ~/.hermes/.env
```

完整密钥列表见原服务器的 `~/.hermes/.env`，**不要上传 GitHub**。

---

## Step 5 — 安装 Python 依赖

```bash
# 创建虚拟环境（避免 PEP 668 报错）
python3.12 -m venv ~/.hermes/venv
source ~/.hermes/venv/bin/activate

# 核心依赖
pip install ezdxf openpyxl PyMuPDF

# Hermes Agent 自身依赖（按官方文档）
# cd ~/.hermes/hermes-agent && pip install -e .
```

---

## Step 6 — 安装系统依赖

```bash
# DWG → DXF 转换所需
sudo apt-get install -y libfuse2t64 xvfb

# 可选：PDF 处理、OCR 等
# sudo apt-get install -y poppler-utils tesseract-ocr
```

---

## Step 7 — 恢复 ODA File Converter（DWG 转换）

```bash
# 从 ODA 官网下载（需免费注册）
# https://www.opendesign.com/guestfiles/oda_file_converter
# 下载 ODAFileConverter_QT6_lnxX64_8.3dll_27.1.AppImage

mkdir -p ~/Apps
cp ODAFileConverter_QT6_lnxX64_8.3dll_27.1.AppImage ~/Apps/
chmod a+x ~/Apps/ODAFileConverter_QT6_lnxX64_8.3dll_27.1.AppImage

# 配置 ezdxf 指向 AppImage
mkdir -p ~/.config/ezdxf
cat >> ~/.config/ezdxf/ezdxf.ini << 'INIEOF'
[odafc-addon]
unix_exec_path = /home/<username>/Apps/ODAFileConverter_QT6_lnxX64_8.3dll_27.1.AppImage
INIEOF
```

验证：`python3.12 -c "from ezdxf.addons import odafc; print('ODAFC OK')"`

---

## Step 8 — 恢复内置记忆（memory entries）

手动重建：在首次对话中告知 agent 读取以下文件：

```
@read ~/.hermes/workspace/hermes-recovery/memory_export_20260618.md
然后说：将这些记忆导入到 memory store 和 user profile。
```

agent 会自动逐条写入。

---

## Step 9 — 验证完整功能

```bash
# 1. Skills 加载
hermes skills list | wc -l   # 应显示 33 个

# 2. DWG 转换测试
python3.12 ~/.hermes/workspace/cad-bom/tools/cad_bom_extract.py <test.dwg>

# 3. VISION 测试（需 MiniMax 或 Coze API key 正确）
# 发送图片给 agent，确认 vision_analyze 能正常返回分析

# 4. 主模型回复
# 发一条消息确认 DeepSeek 能正常回复
```

---

## 附录：文件清单

```
~/.hermes/
├── skills/              ← 33个技能，~12MB（GitHub 备份）
├── workspace/           ← ~300KB（GitHub 备份）
│   ├── cad-bom/tools/   ← BOM 提取工具
│   ├── notes/           ← reminders / deepseek 记账
│   ├── .learnings/      ← 纠正记录 / HOT 规则
│   └── hermes-recovery/ ← 本文件 + 记忆导出
├── config.yaml          ← 脱敏版可传 GitHub，key 需重填
├── .env                 ← ❌ 不上传，含全部 API key
└── hermes-agent/        ← Hermes 程序本体（从官方仓库 clone）
```

## 附录：需手动恢复项

| 项目 | 恢复方式 | 是否敏感 |
|---|---|---|
| .env（API keys） | 手动填入 | 🔴 敏感 |
| ODA AppImage | 官网重下 | ✅ 不敏感 |
| ezdxf 配置 | 本清单 Step 7 自动重建 | ✅ 不敏感 |
| 内置记忆 | 本清单 Step 8 从导出文件恢复 | ✅ 不敏感 |
| 对话历史（sessions） | 可选：复制 sessions.db | ⚠️ 含业务内容，用户自判 |
