#!/usr/bin/env python3
"""
DXF 渲染脚本 v2 —— 自动裁剪到内容 + 中文字体支持
B 2026-06-17 联合 MiniMax-M3 + DeepSeek Flash 协作
=================================================
解决问题：
- draw_1/draw_2 用 ezdxf.addons.drawing 默认渲染时，model space 范围巨大
  （左下空白 + 右上小内容），导致内容被压成像素点，vision 看不到
- draw_2 几何全在嵌套 SOONWIN 块里，INSERT 后 x 偏移 166700，渲染画布巨大
- matplotlib 默认 sans-serif 不支持中文，MTEXT 中文显示成方块

策略：
1. 递归遍历所有 entity（含嵌套块的 INSERT）算出真实 bounding box
2. 用 ezdxf Frontend 渲染（它会自动展开 INSERT 的块内容）
3. 强制裁剪到 bbox + 10% padding
4. matplotlib font 设置为 WenQuanYi Zen Hei（中文）+ DejaVu Sans（英文回退）

用法：
  python3.12 render_dxf_v2.py <input.dxf> <output.png> [--layout Model]
"""
import sys
import os
import math
import argparse

# 强制走用户级 site-packages（ezdxf/numpy 装在 py3.12）
sys.path.insert(0, "/home/ubuntu/.local/lib/python3.12/site-packages")

# matplotlib 必须在 import pyplot 前设字体
import matplotlib
matplotlib.use("Agg")
matplotlib.rcParams["font.sans-serif"] = [
    "WenQuanYi Zen Hei",   # 中文字体（Ubuntu 预装）
    "Noto Sans CJK SC",     # 备选中文字体
    "DejaVu Sans",          # 英文回退
]
matplotlib.rcParams["axes.unicode_minus"] = False  # 负号正常显示

import ezdxf
from ezdxf.addons.drawing import RenderContext, Frontend
from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
import matplotlib.pyplot as plt


def _iter_all_geometry(doc, layout_name="Model"):
    """
    递归遍历 model space / paper space 里的所有 entity，
    含 INSERT 的嵌套块展开。返回 entity 生成器。
    """
    if layout_name == "Model":
        layout = doc.modelspace()
    else:
        layout = doc.layouts.get(layout_name)

    visited = set()  # 防止块循环引用

    def walk(entities, depth=0, offset=(0.0, 0.0)):
        for ent in entities:
            t = ent.dxftype()
            if t == "INSERT":
                child_name = ent.dxf.name
                if child_name in visited:
                    continue
                visited.add(child_name)
                try:
                    child_block = doc.blocks.get(child_name)
                    ins = ent.dxf.insert
                    sx = float(ent.dxf.get("xscale", 1.0))
                    sy = float(ent.dxf.get("yscale", 1.0))
                    child_offset = (
                        offset[0] + ins.x * sx,
                        offset[1] + ins.y * sy,
                    )
                    yield from walk(child_block, depth + 1, child_offset)
                except (KeyError, AttributeError):
                    pass
            else:
                yield ent, depth, offset

    yield from walk(layout)


def compute_bbox(doc, layout_name="Model", trim_outliers=True):
    """
    遍历所有 entity 算真实 bounding box（含嵌套块的 INSERT 展开）。
    返回 (x_min, y_min, x_max, y_max)。如果没有内容，返回 None。

    trim_outliers: True 时用百分位剔除离群 entity（图框/标注外引线），
    只保留包含 80% 几何的核心区域。
    """
    xs, ys = [], []
    for ent, _depth, (ox, oy) in _iter_all_geometry(doc, layout_name):
        t = ent.dxftype()
        try:
            if t == "LINE":
                s, e = ent.dxf.start, ent.dxf.end
                xs.extend([s.x + ox, e.x + ox])
                ys.extend([s.y + oy, e.y + oy])
            elif t == "CIRCLE":
                c = ent.dxf.center
                r = float(ent.dxf.radius)
                xs.extend([c.x + ox - r, c.x + ox + r])
                ys.extend([c.y + oy - r, c.y + oy + r])
            elif t == "ARC":
                c = ent.dxf.center
                r = float(ent.dxf.radius)
                xs.extend([c.x + ox - r, c.x + ox + r])
                ys.extend([c.y + oy - r, c.y + oy + r])
            elif t in ("MTEXT", "TEXT"):
                p = ent.dxf.insert
                xs.append(p.x + ox)
                ys.append(p.y + oy)
            elif t == "LWPOLYLINE":
                for pt in ent.get_points():
                    xs.append(pt[0] + ox)
                    ys.append(pt[1] + oy)
            elif t == "SPLINE":
                try:
                    for pt in ent.control_points:
                        xs.append(pt[0] + ox)
                        ys.append(pt[1] + oy)
                except Exception:
                    pass
            elif t == "DIMENSION":
                try:
                    p = ent.dxf.get("insert") or ent.dxf.get("defpoint")
                    if p is not None:
                        xs.append(p.x + ox)
                        ys.append(p.y + oy)
                except Exception:
                    pass
            elif t == "LEADER":
                try:
                    for vtx in ent.vertices:
                        xs.append(vtx[0] + ox)
                        ys.append(vtx[1] + oy)
                except Exception:
                    pass
            elif t == "ATTRIB":
                try:
                    p = ent.dxf.get("insert", (0, 0, 0))
                    xs.append(p[0] + ox)
                    ys.append(p[1] + oy)
                except Exception:
                    pass
        except Exception:
            pass

    if not xs:
        return None

    if trim_outliers:
        # 用 10%/90% 百分位剔除离群 entity（图框、外引线）
        sorted_xs = sorted(xs)
        sorted_ys = sorted(ys)
        n = len(sorted_xs)
        if n >= 10:  # 数量够才剔除
            lo = max(1, int(n * 0.05))   # 跳过最小 5%
            hi = min(n - 1, int(n * 0.95))  # 跳过最大 5%
            return (sorted_xs[lo], sorted_ys[lo], sorted_xs[hi], sorted_ys[hi])

    return (min(xs), min(ys), max(xs), max(ys))


def render_dxf(input_path, output_path, layout_name="Model", padding=0.1, dpi=180, mtext_only=False):
    """
    渲染 DXF 为 PNG：
    1. 算真实 bbox
    2. ezdxf Frontend 渲染（自动展开 INSERT）
    3. 裁剪到 bbox + padding
    4. 保存 PNG

    Args:
        padding: 相对 bbox 大小的 padding 比例（0.1 = 10%）
        dpi: 输出图片分辨率
        mtext_only: True 时只算 MTEXT/TEXT 的 bbox（不包含 LINE/CIRCLE 等几何），
                    适用于 MTEXT 散布在大几何里、需要突出文字标签的场景
    """
    doc = ezdxf.readfile(input_path)

    if mtext_only:
        # 只算 MTEXT/TEXT 的 bbox
        import re as _re
        RE_CONTROL_ONLY = _re.compile(r'^\\?[A-Za-z]?$')

        def _clean(s):
            s = _re.sub(r'\\[A-Za-z][^;]*;', '', s)
            s = s.replace('\\P', ' ').replace('\\~', ' ')
            return _re.sub(r'\s+', ' ', s).strip()

        xs, ys = [], []
        for ent, _depth, (ox, oy) in _iter_all_geometry(doc, layout_name):
            if ent.dxftype() not in ('MTEXT', 'TEXT'):
                continue
            clean = _clean(ent.text)
            if not clean or RE_CONTROL_ONLY.match(clean):
                continue
            p = ent.dxf.insert
            xs.append(p.x + ox)
            ys.append(p.y + oy)
        if not xs:
            print(f"⚠️  {input_path}: 没有 MTEXT 内容")
            return None
        bbox = (min(xs), min(ys), max(xs), max(ys))
    else:
        bbox = compute_bbox(doc, layout_name)
        if bbox is None:
            print(f"⚠️  {input_path}: 没有可渲染的几何内容")
            return None

    x_min, y_min, x_max, y_max = bbox
    w = x_max - x_min
    h = y_max - y_min
    print(f"📐 {input_path} bbox: x=[{x_min:.0f}, {x_max:.0f}], y=[{y_min:.0f}, {y_max:.0f}]  ({w:.0f} × {h:.0f})")

    fig, ax = plt.subplots(figsize=(18, 14))

    ctx = RenderContext(doc)
    out = MatplotlibBackend(ax)
    if layout_name == "Model":
        target = doc.modelspace()
    else:
        target = doc.layouts.get(layout_name)
    Frontend(ctx, out).draw_layout(target, finalize=True)

    pad_x = w * padding
    pad_y = h * padding
    ax.set_xlim(x_min - pad_x, x_max + pad_x)
    ax.set_ylim(y_min - pad_y, y_max + pad_y)
    ax.set_aspect("equal")
    ax.set_title(f"{os.path.basename(input_path)}  ·  layout={layout_name}  ·  mode={'mtext' if mtext_only else 'all'}", fontsize=10)

    plt.tight_layout()
    plt.savefig(output_path, dpi=dpi, bbox_inches="tight")
    plt.close()
    print(f"✅  saved {output_path}  ({os.path.getsize(output_path) // 1024} KB)")
    return output_path


def main():
    parser = argparse.ArgumentParser(description="DXF → PNG 渲染（自动裁剪 + 中文字体）")
    parser.add_argument("input", help="输入 DXF 路径")
    parser.add_argument("output", help="输出 PNG 路径")
    parser.add_argument("--layout", default="Model", help="布局名（默认 Model）")
    parser.add_argument("--padding", type=float, default=0.1, help="裁剪 padding 比例（默认 0.1 = 10%）")
    parser.add_argument("--dpi", type=int, default=180, help="图片分辨率（默认 180）")
    parser.add_argument("--mtext-only", action="store_true", help="只渲染 MTEXT 区域（不包含几何）")
    args = parser.parse_args()

    render_dxf(args.input, args.output, args.layout, args.padding, args.dpi, args.mtext_only)


if __name__ == "__main__":
    main()
