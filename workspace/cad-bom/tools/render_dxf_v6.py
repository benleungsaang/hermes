#!/usr/bin/env python3
"""
DXF 渲染 v6 —— 最终版
策略：只找 MTEXT/TEXT 的 bbox（不要 DIMENSION），
然后全幅渲染到该 bbox ±100% padding，确保几何 + 文字都可见。

draw_1 验证通过验收的选项：v3 --mtext-only
draw_2 验证通过验收的选项：v2 full trimmed bbox
draw_4 验证通过验收的选项：v2 default

三者取的策略平衡：mtext-bbox + 100% padding = 包含附近几何 + 不扩到没意义的大。
"""
import sys, os, re as _re
sys.path.insert(0, "/home/ubuntu/.local/lib/python3.12/site-packages")

import matplotlib
matplotlib.use("Agg")
matplotlib.rcParams["font.sans-serif"] = ["WenQuanYi Zen Hei", "DejaVu Sans"]
matplotlib.rcParams["axes.unicode_minus"] = False

import matplotlib.pyplot as plt
from ezdxf.addons.drawing import RenderContext, Frontend
from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
import ezdxf


_RE_CTRL = _re.compile(r'\\[A-Za-z][^;]*;')

def mtext_bbox(doc, layout="Model"):
    """只找 MTEXT/TEXT，递归进嵌套块。返回 (x1,y1,x2,y2) 或 None"""
    target = doc.modelspace() if layout == "Model" else doc.layouts.get(layout)
    visited = set()
    pts = []

    def walk(entities, offset=(0.0, 0.0)):
        for ent in entities:
            if ent.dxftype() == "INSERT":
                name = ent.dxf.name
                if name in visited: continue
                visited.add(name)
                try:
                    blk = doc.blocks.get(name)
                    ins = ent.dxf.insert
                    sx = float(ent.dxf.get("xscale", 1.0))
                    sy = float(ent.dxf.get("yscale", 1.0))
                    yield from walk(blk, (offset[0] + ins.x * sx, offset[1] + ins.y * sy))
                except: pass
            elif ent.dxftype() in ("MTEXT", "TEXT"):
                raw = _RE_CTRL.sub('', ent.text).replace('\\P', ' ').replace('\\~', ' ')
                raw = _re.sub(r'\s+', ' ', raw).strip()
                if raw and not (len(raw) == 1 and raw in r'?\`/ '):
                    p = ent.dxf.insert
                    pts.append((p.x + offset[0], p.y + offset[1]))

    for _ in walk(target):
        pass
    if not pts:
        return None
    xs = sorted(p[0] for p in pts)
    ys = sorted(p[1] for p in pts)
    return (xs[0], ys[0], xs[-1], ys[-1])


def render(input_path, output_path, padding=1.0, dpi=200):
    doc = ezdxf.readfile(input_path)
    layout = doc.modelspace()

    bbox = mtext_bbox(doc)
    if bbox:
        x1, y1, x2, y2 = bbox
        w, h = x2 - x1, y2 - y1
        px, py = w * padding, h * padding
        xl, xr = x1 - px, x2 + px
        yb, yt = y1 - py, y2 + py
        print(f"bbox ({w:.0f}×{h:.0f}) +{padding*100:.0f}% → ({xr-xl:.0f}×{yt-yb:.0f})")
    else:
        print("无 MTEXT，全幅渲染")
        xl, xr, yb, yt = None, None, None, None

    fig, ax = plt.subplots(figsize=(14, 10))
    ctx = RenderContext(doc)
    out = MatplotlibBackend(ax)
    Frontend(ctx, out).draw_layout(layout, finalize=True)
    if bbox:
        ax.set_xlim(xl, xr)
        ax.set_ylim(yb, yt)
    ax.set_aspect("equal")
    ax.axis("off")

    plt.savefig(output_path, dpi=dpi, bbox_inches="tight", pad_inches=0)
    plt.close(fig)
    kb = os.path.getsize(output_path) // 1024
    print(f"✅ {output_path} ({kb} KB)")
    return output_path


if __name__ == "__main__":
    for arg in sys.argv[1:]:
        if arg.endswith(".dxf"):
            out = arg.replace(".dxf", "_v6.png")
            render(arg, out)
