---
name: cad-dwg-to-pdf
description: 将 DWG 文件通过 ODA File Converter + ezdxf + PyMuPDF 转换为 PDF 渲染图。覆盖系统依赖、ODA AppImage 安装、ezdxf 渲染参数（幅面/DPI/margin）、已知限制（中文方块、首次运行 FUSE 问题、命令行 xvfb 包装）、批处理与多页输出模式。Load when user says "把 DWG 转成 PDF"、"渲染 DWG"、"导出 PDF 预览"、"CAD 预览图"、"DXF 渲染"。
---

# CAD DWG → PDF 转换

把 DWG 专有格式转成 ezdxf 能处理的 DXF 临时文件，再用 ezdxf 的 `PyMuPdfBackend` 渲染成 PDF。

## 工作流（一次完整调用）

1. `ezdxf.odafc.readfile(dwg_path)` — 内部调 ODA AppImage 把 DWG 转临时 DXF
2. `RenderContext(doc)` + `Frontend(ctx, PyMuPdfBackend()).draw(modelspace())` — ezdxf 渲染
3. `backend.save(page, margin=..., rect=pymupdf.Rect(0,0,w,h))` — 输出到 pymupdf Page
4. `page.save(pdf_path)` — 落盘

## 最小可跑脚本

```python
import sys, ezdxf, pymupdf
from ezdxf.addons.drawing import Frontend, RenderContext
from ezdxf.addons.drawing.pymupdf import PyMuPdfBackend

def dwg_to_pdf(dwg_path: str) -> str:
    pdf_path = dwg_path.rsplit(".", 1)[0] + ".pdf"
    doc = ezdxf.odafc.readfile(dwg_path)
    sp = doc.modelspace()
    Frontend(RenderContext(doc), PyMuPdfBackend()).draw(sp)

    page = pymupdf.open()
    w, h = 1190, 842  # A3 横向 @ 72dpi ≈ 420x297mm
    page[0] = page.new_page(width=w, height=h) if page.page_count else None  # see references/multipage.md
    # First-page pattern (single page):
    backend = PyMuPdfBackend()
    Frontend(RenderContext(doc), backend).draw(sp)
    backend.save(page, margin=(10, 10, 10, 10), rect=pymupdf.Rect(0, 0, w, h))
    page.save(pdf_path)
    page.close()
    return pdf_path
```

完整且已验证可用的脚本见 `scripts/dwg2pdf.py`（本 skill 自带）。

## 前置条件速查

| 依赖 | 安装命令 | 说明 |
|---|---|---|
| libfuse2t64 | `sudo apt install -y libfuse2t64` | ODA AppImage 运行时（Ubuntu 24.04 包名） |
| xvfb | `sudo apt install -y xvfb` | ODA 命令行需要虚拟显示 |
| ezdxf | `pip install ezdxf` | 读写 DXF + 渲染 |
| PyMuPDF | `pip install PyMuPDF pymupdf` | 后端渲染引擎 |
| ODA AppImage | 见 `references/oda-installation.md` | ~82MB，下载后 `chmod a+x` |

## 关键参数

| 参数 | 默认 | 含义 |
|---|---|---|
| `w, h` | 1190, 842 | A3 横向 @ 72dpi (420×297mm) |
| `margin` | (10,10,10,10) | 上下左右留白（pt） |
| `rect` | pymupdf.Rect(0,0,w,h) | PDF 页面矩形 |
| `api_mode` | chat_completions/anthropic_messages | 与 ezdxf 无关，是 model.fallback_providers 配置项 |

## 已知限制（详尽版见 `references/known-limitations.md`）

- **中文文字方块**：ezdxf 渲染中文若 DXF 未带 TTF 字体映射会显示为方块。需要预先在 DXF 中嵌入字体或换 MatplotlibBackend + 指定中文字体。
- **首次 ODA 运行**可能需要 xvfb 包装：`xvfb-run -a python3 dwg2pdf.py file.dwg`。
- **大图纸**（>50K 实体）72dpi 仍可能慢，必要时降到 50dpi。
- **ODA AppImage 路径**必须在 `~/.hermes/config.yaml` 的 `ezdxf.odafc.unix_exec_path` 中配好，否则 ezdxf 找不到转换器。

## 何时不该用

- 要做高质量中文图纸渲染 → 改用 MatplotlibBackend + 中文字体，或导出 SVG 后用 Inkscape 转 PDF
- 要做 3D 模型预览 → ezdxf 不支持，用 ODA Viewer 或 FreeCAD
- 要做工程量计算（长度、面积） → 走 `cad-bom-extraction` skill，那里有 DXF 实体遍历工具
