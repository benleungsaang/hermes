#!/usr/bin/env python3
"""
渲染 v7 —— 递归实体遍历 bbox + PyMuPdfBackend 渲染
整合 v2 的精准 bbox 计算（含嵌套 INSERT 展开 + 百分位剔除离群）
和 PyMuPdfBackend 的快速出图
"""
import sys, os, math
sys.path.insert(0, "/home/ubuntu/.local/lib/python3.12/site-packages")

import ezdxf
from ezdxf.addons.drawing import RenderContext, Frontend
from ezdxf.addons.drawing.pymupdf import PyMuPdfBackend
from ezdxf.addons.drawing.layout import Page, Units
from ezdxf.math import BoundingBox2d, Vec2
from PIL import Image


def _iter_all_geometry(doc, layout_name="Model"):
    """递归遍历所有 entity（含嵌套块 INSERT），返回 (ent, depth, offset) 生成器"""
    if layout_name == "Model":
        layout = doc.modelspace()
    else:
        layout = doc.layouts.get(layout_name)
    visited = set()
    def walk(entities, depth=0, offset=(0.0, 0.0)):
        for ent in entities:
            t = ent.dxftype()
            if t == "INSERT":
                child_name = ent.dxf.name
                if child_name in visited: continue
                visited.add(child_name)
                try:
                    child_block = doc.blocks.get(child_name)
                    ins = ent.dxf.insert
                    sx = float(ent.dxf.get("xscale", 1.0))
                    sy = float(ent.dxf.get("yscale", 1.0))
                    child_offset = (offset[0] + ins.x * sx, offset[1] + ins.y * sy)
                    yield from walk(child_block, depth + 1, child_offset)
                except (KeyError, AttributeError): pass
            else:
                yield ent, depth, offset
    yield from walk(layout)


def compute_bbox(doc, layout_name="Model", trim_outliers=True):
    """遍历所有 entity 算真实 bbox，返回 (x_min, y_min, x_max, y_max)"""
    xs, ys = [], []
    for ent, _depth, (ox, oy) in _iter_all_geometry(doc, layout_name):
        t = ent.dxftype()
        try:
            if t == "LINE":
                s, e = ent.dxf.start, ent.dxf.end
                xs.extend([s.x + ox, e.x + ox]); ys.extend([s.y + oy, e.y + oy])
            elif t == "CIRCLE":
                c = ent.dxf.center; r = float(ent.dxf.radius)
                xs.extend([c.x + ox - r, c.x + ox + r]); ys.extend([c.y + oy - r, c.y + oy + r])
            elif t == "ARC":
                c = ent.dxf.center; r = float(ent.dxf.radius)
                xs.extend([c.x + ox - r, c.x + ox + r]); ys.extend([c.y + oy - r, c.y + oy + r])
            elif t in ("MTEXT", "TEXT"):
                p = ent.dxf.insert; xs.append(p.x + ox); ys.append(p.y + oy)
            elif t == "LWPOLYLINE":
                for pt in ent.get_points(): xs.append(pt[0] + ox); ys.append(pt[1] + oy)
            elif t == "SPLINE":
                try:
                    for pt in ent.control_points: xs.append(pt[0] + ox); ys.append(pt[1] + oy)
                except: pass
            elif t == "DIMENSION":
                try:
                    p = ent.dxf.get("insert") or ent.dxf.get("defpoint")
                    if p: xs.append(p.x + ox); ys.append(p.y + oy)
                except: pass
            elif t == "LEADER":
                try:
                    for vtx in ent.vertices: xs.append(vtx[0] + ox); ys.append(vtx[1] + oy)
                except: pass
            elif t == "ATTRIB":
                try:
                    p = ent.dxf.get("insert", (0, 0, 0)); xs.append(p[0] + ox); ys.append(p[1] + oy)
                except: pass
        except: pass

    if not xs: return None

    if trim_outliers and len(xs) >= 10:
        sx, sy = sorted(xs), sorted(ys)
        n = len(sx)
        lo, hi = max(1, int(n * 0.05)), min(n - 1, int(n * 0.95))
        return (sx[lo], sy[lo], sx[hi], sy[hi])

    return (min(xs), min(ys), max(xs), max(ys))


def compute_mtext_bbox(doc, layout_name="Model"):
    """只算 MTEXT/TEXT 的 bbox（不含几何），用于文字散布在大几何里的场景"""
    import re
    RE_CTRL = re.compile(r'^\\?[A-Za-z]?$')
    def clean(s):
        s = re.sub(r'\\[A-Za-z][^;]*;', '', s)
        s = s.replace('\\P', ' ').replace('\\~', ' ')
        return re.sub(r'\s+', ' ', s).strip()

    xs, ys = [], []
    for ent, _depth, (ox, oy) in _iter_all_geometry(doc, layout_name):
        if ent.dxftype() not in ('MTEXT', 'TEXT'): continue
        text = clean(ent.text)
        if not text or RE_CTRL.match(text): continue
        p = ent.dxf.insert; xs.append(p.x + ox); ys.append(p.y + oy)

    if not xs: return None
    pad = 0.1
    x1, y1, x2, y2 = min(xs), min(ys), max(xs), max(ys)
    return (x1 - (x2-x1)*pad, y1 - (y2-y1)*pad, x2 + (x2-x1)*pad, y2 + (y2-y1)*pad)


def render_to_file(input_path, output_path, layout_name="Model", dpi=180, padding=0.1, mtext_only=False):
    """主渲染函数：ezdxf bbox → PyMuPdfBackend 出图"""
    doc = ezdxf.readfile(input_path)
    msp = doc.modelspace() if layout_name == "Model" else doc.layouts.get(layout_name)

    if mtext_only:
        bbox = compute_mtext_bbox(doc, layout_name)
        mode = "mtext"
    else:
        bbox = compute_bbox(doc, layout_name)
        mode = "all"

    if bbox is None:
        print(f"  No content!"); return

    x_min, y_min, x_max, y_max = bbox
    w = x_max - x_min; h = y_max - y_min
    print(f"  bbox: ({x_min:.0f},{y_min:.0f})-({x_max:.0f},{y_max:.0f})  ({w:.0f}x{h:.0f})  mode={mode}")

    render_box = BoundingBox2d([
        Vec2(x_min - w*padding, y_min - h*padding),
        Vec2(x_max + w*padding, y_max + h*padding)
    ])

    ctx = RenderContext(doc)
    out = PyMuPdfBackend()
    Frontend(ctx, out).draw_layout(msp, finalize=True)

    # page size from render_box + target DPI
    rw = render_box.extmax.x - render_box.extmin.x
    rh = render_box.extmax.y - render_box.extmin.y
    # 大约 160 像素/毫米 = 实际大小
    px_w = int(rw * dpi / 25.4)
    px_h = int(rh * dpi / 25.4)
    # 限制最大长边 4000px
    if max(px_w, px_h) > 4000:
        scale = 4000 / max(px_w, px_h)
        px_w, px_h = int(px_w * scale), int(px_h * scale)
    px_w = max(px_w, 200); px_h = max(px_h, 200)

    page = Page(px_w, px_h, Units.px)
    player = out.get_replay(page, render_box=render_box)
    pix = player.get_pixmap(dpi=dpi)
    mode_pil = "RGBA" if pix.n == 4 else "RGB"
    img = Image.frombytes(mode_pil, (pix.width, pix.height), pix.samples)
    img.save(output_path)
    sz = os.path.getsize(output_path)
    print(f"  saved: ({sz//1024}KB, {pix.width}x{pix.height})")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="DXF → PNG (实体遍历 bbox + PyMuPdfBackend)")
    parser.add_argument("input", help="输入 DXF")
    parser.add_argument("output", help="输出 PNG")
    parser.add_argument("--layout", default="Model")
    parser.add_argument("--dpi", type=int, default=180)
    parser.add_argument("--padding", type=float, default=0.1)
    parser.add_argument("--mtext-only", action="store_true")
    args = parser.parse_args()
    render_to_file(args.input, args.output, args.layout, args.dpi, args.padding, args.mtext_only)


if __name__ == "__main__":
    cache = "/home/ubuntu/.hermes/cache/documents"
    images = "/home/ubuntu/.hermes/image_cache"
    os.makedirs(images, exist_ok=True)

    for f in sorted(os.listdir(cache)):
        if not f.endswith('.dxf'): continue
        inp = os.path.join(cache, f)
        out = os.path.join(images, f"v7_{f.replace('.dxf','.png')}")
        # 先试 full mode
        print(f"\n{'='*50}\n{f}  (mode=all)")
        render_to_file(inp, out)
PYEOF
