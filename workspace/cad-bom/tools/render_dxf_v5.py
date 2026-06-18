#!/usr/bin/env python3
"""
DXF 渲染 v5 — 最简方案
核心策略：MTEXT bbox + 50% padding（确保几何也能看到）
MTEXT 一定是能算出来的（不管在不在嵌套块里），而且 MTEXT 的 bbox 一定包含"真正有内容"的区域。
50% padding 给图框附近几何留足空间，兼顾 vision 识别几何和文字。
"""
import sys, os, math, re as _re
sys.path.insert(0, "/home/ubuntu/.local/lib/python3.12/site-packages")

import matplotlib
matplotlib.use("Agg")
matplotlib.rcParams["font.sans-serif"] = ["WenQuanYi Zen Hei", "DejaVu Sans"]
matplotlib.rcParams["axes.unicode_minus"] = False

import matplotlib.pyplot as plt
from ezdxf.addons.drawing import RenderContext, Frontend
from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
import ezdxf


# ============================================================
# MTEXT bbox — 最快、最稳、最可靠
# ============================================================
_RE_CTRL = _re.compile(r'\\[A-Za-z][^;]*;')
_RE_WS = _re.compile(r'\s+')
def _clean(s):
    """清洗后判断是否有效文字"""
    s = _RE_CTRL.sub('', s)
    s = s.replace('\\P', ' ').replace('\\~', ' ')
    s = _RE_WS.sub(' ', s).strip()
    if not s or (len(s) == 1 and s in ('?', '\\', '/')):
        return None
    return s

def find_mtext_bbox(doc, layout_name="Model"):
    """递归遍历所有 entity（含嵌套块 INSERT），找有效 MTEXT/TEXT 的 bbox"""
    layout = doc.modelspace() if layout_name == "Model" else doc.layouts.get(layout_name)
    visited = set()
    pts = []

    def walk(entities, offset=(0.0, 0.0)):
        for ent in entities:
            if ent.dxftype() == "INSERT":
                name = ent.dxf.name
                if name in visited: continue
                visited.add(name)
                try:
                    b = doc.blocks.get(name)
                    ins = ent.dxf.insert
                    sx, sy = float(ent.dxf.get("xscale", 1.0)), float(ent.dxf.get("yscale", 1.0))
                    yield from walk(b, (offset[0] + ins.x * sx, offset[1] + ins.y * sy))
                except: pass
            else:
                if ent.dxftype() in ("MTEXT", "TEXT"):
                    clean = _clean(ent.text)
                    if clean:
                        p = ent.dxf.insert
                        pts.append((p.x + offset[0], p.y + offset[1]))

    for _ in walk(layout):
        pass
    # 也扫 DIMENSION（有时尺寸数字在 DIMENSION 实体里）
    for ent, depth, offset in _walk_full(doc, layout_name, "DIMENSION only"):
        if ent.dxftype() == "DIMENSION":
            try:
                p = ent.dxf.get("insert") or ent.dxf.get("defpoint")
                if p:
                    pts.append((p.x + offset[0], p.y + offset[1]))
            except: pass

    if not pts:
        return None

    xs = sorted(p[0] for p in pts)
    ys = sorted(p[1] for p in pts)
    return (xs[0], ys[0], xs[-1], ys[-1])


def _walk_full(doc, layout_name="Model", kind="all"):
    """递归遍历全部 entity（含 DIMENSION 的位置点）"""
    layout = doc.modelspace() if layout_name == "Model" else doc.layouts.get(layout_name)
    visited = set()

    def walk(entities, depth=0, offset=(0.0, 0.0)):
        for ent in entities:
            t = ent.dxftype()
            if t == "INSERT":
                name = ent.dxf.name
                if name in visited: continue
                visited.add(name)
                try:
                    b = doc.blocks.get(name)
                    ins = ent.dxf.insert
                    sx, sy = float(ent.dxf.get("xscale", 1.0)), float(ent.dxf.get("yscale", 1.0))
                    yield from walk(b, depth + 1, (offset[0] + ins.x * sx, offset[1] + ins.y * sy))
                except: pass
            else:
                yield ent, depth, offset

    return walk(layout)


def render_dxf_v5(input_path, output_path, layout_name="Model", dpi=200, padding=0.5):
    doc = ezdxf.readfile(input_path)
    layout = doc.modelspace() if layout_name == "Model" else doc.layouts.get(layout_name)

    # Fast path: 从 MTEXT bbox 起
    mbox = find_mtext_bbox(doc, layout_name)
    if mbox is None:
        print(f"⚠️ 找不到 MTEXT，全幅渲染")
        fig, ax = plt.subplots(figsize=(14, 10))
        ctx = RenderContext(doc); out = MatplotlibBackend(ax)
        Frontend(ctx, out).draw_layout(layout, finalize=True)
        plt.savefig(output_path, dpi=dpi, bbox_inches="tight")
        plt.close()
        return output_path, None, "fallback"

    x_min, y_min, x_max, y_max = mbox
    mw, mh = x_max - x_min, y_max - y_min

    # padding = 50% of text bbox (确保几何能看到)
    px = mw * padding
    py = mh * padding
    x_min -= px
    x_max += px
    y_min -= py
    y_max += py

    print(f"📐 MTEXT bbox ({mw:.0f}×{mh:.0f}) → render bbox +{padding*100:.0f}% padding")

    fig, ax = plt.subplots(figsize=(14, 10))
    ctx = RenderContext(doc)
    out = MatplotlibBackend(ax)
    Frontend(ctx, out).draw_layout(layout, finalize=True)
    ax.set_xlim(x_min, x_max)
    ax.set_ylim(y_min, y_max)
    ax.set_aspect("equal")
    ax.axis("off")

    plt.savefig(output_path, dpi=dpi, bbox_inches="tight", pad_inches=0)
    plt.close(fig)
    kb = os.path.getsize(output_path) // 1024
    print(f"✅ saved {output_path} ({kb} KB)")
    return output_path, mbox, "mtext-bbox"


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python3 render_dxf_v5.py <input.dxf> [output.png]")
        sys.exit(1)
    inp = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else inp.replace(".dxf", "_v5.png")
    render_dxf_v5(inp, out, dpi=200)
