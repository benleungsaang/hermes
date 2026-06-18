#!/usr/bin/env python3
"""
两步渲染：先全幅低清 → PIL 扫内容区 → 精确定位 high-dpi 渲染
B 2026-06-18
"""
import sys, os
sys.path.insert(0, "/home/ubuntu/.local/lib/python3.12/site-packages")

import ezdxf
from ezdxf.addons.drawing import RenderContext, Frontend
from ezdxf.addons.drawing.pymupdf import PyMuPdfBackend
from ezdxf.addons.drawing.layout import Page, Units
from ezdxf.math import BoundingBox2d, Vec2
from PIL import Image
import numpy as np


def _dxf_extents(doc):
    """取 DXF header 的图形范围，兜底遍历"""
    try:
        emin = doc.header.get('$EXTMIN')
        emax = doc.header.get('$EXTMAX')
        if emin and emax:
            return (emin[0], emin[1], emax[0], emax[1])
    except:
        pass
    xs, ys = [], []
    for ent in doc.modelspace():
        try:
            if ent.dxftype() == 'LINE':
                s, e = ent.dxf.start, ent.dxf.end
                xs += [s.x, e.x]; ys += [s.y, e.y]
            elif ent.dxftype() in ('MTEXT', 'TEXT'):
                xs.append(ent.dxf.insert.x); ys.append(ent.dxf.insert.y)
        except: pass
    if xs: return (min(xs), min(ys), max(xs), max(ys))
    return None


def render_pass(doc, layout, dpi=72, render_box=None):
    """用 PyMuPdfBackend 渲染一次，返回 PIL Image"""
    ctx = RenderContext(doc)
    out = PyMuPdfBackend()
    Frontend(ctx, out).draw_layout(layout, finalize=True)

    if render_box:
        w = render_box.extmax.x - render_box.extmin.x
        h = render_box.extmax.y - render_box.extmin.y
        target_long = 2000
        if w >= h:
            pw, ph = target_long, int(target_long * h / w)
        else:
            pw, ph = int(target_long * w / h), target_long
        page = Page(pw, ph, Units.px)
    else:
        page = Page(420, 297, Units.mm)

    player = out.get_replay(page, render_box=render_box)
    pix = player.get_pixmap(dpi=dpi)
    mode = "RGBA" if pix.n == 4 else "RGB"
    return Image.frombytes(mode, (pix.width, pix.height), pix.samples)


def find_content_bbox(img, threshold=240):
    """找到非白像素的最小 bounding box，返回 (x1,y1,x2,y2) 像素坐标"""
    arr = np.array(img.convert("RGB"))
    mask = np.any(arr < threshold, axis=2)
    rows = np.any(mask, axis=1)
    cols = np.any(mask, axis=0)
    if not rows.any() or not cols.any():
        return None
    y1, y2 = int(np.where(rows)[0][[0, -1]][0]), int(np.where(rows)[0][[0, -1]][1])
    x1, x2 = int(np.where(cols)[0][[0, -1]][0]), int(np.where(cols)[0][[0, -1]][1])
    return (x1, y1, x2, y2)


def render_two_pass(input_path, output_path):
    doc = ezdxf.readfile(input_path)
    msp = doc.modelspace()

    extents = _dxf_extents(doc)
    if extents is None:
        print(f"  Cannot determine extents, abort."); return
    xmin, ymin, xmax, ymax = extents
    dx, dy = xmax - xmin, ymax - ymin
    print(f"  Extents: ({xmin:.0f},{ymin:.0f})-({xmax:.0f},{ymax:.0f})  ({dx:.0f}x{dy:.0f})")

    # PASS 1: 全幅低清
    print(f"  PASS 1: full render 72dpi...", end=" ", flush=True)
    img1 = render_pass(doc, msp, dpi=72)
    w1, h1 = img1.size
    print(f"{w1}x{h1}")

    # 扫内容区
    bbox_px = find_content_bbox(img1)
    if bbox_px is None:
        print(f"  No content found!"); return
    x1_px, y1_px, x2_px, y2_px = bbox_px
    cw, ch = x2_px - x1_px, y2_px - y1_px
    fill_w = cw / w1
    fill_h = ch / h1
    print(f"  Content: ({x1_px},{y1_px})-({x2_px},{y2_px})  fill={fill_w*100:.0f}%x{fill_h*100:.0f}%")

    # 如果内容已充满 >90%，直接第一张 high-dpi 重出即可
    if fill_w > 0.90 and fill_h > 0.90:
        print(f"  Content fills canvas. Re-render at 180dpi...", end=" ", flush=True)
        img2 = render_pass(doc, msp, dpi=180)
        img2.save(output_path)
        sz = os.path.getsize(output_path)
        print(f"{img2.size[0]}x{img2.size[1]}  ({sz//1024}KB)")
        return

    # 像素 → DXF 坐标映射
    # Page A3 横版 + 无 render_box = extents 映射到整页
    # 像素 (0,0) = DXF (xmin, ymax), 像素 (w,h) = DXF (xmax, ymin)
    dxf_x1 = xmin + x1_px / w1 * dx - dx * 0.05  # 加 5% padding
    dxf_y1 = ymin + (1 - y2_px / h1) * dy - dy * 0.05
    dxf_x2 = xmin + x2_px / w1 * dx + dx * 0.05
    dxf_y2 = ymin + (1 - y1_px / h1) * dy + dy * 0.05

    render_box = BoundingBox2d([Vec2(dxf_x1, dxf_y1), Vec2(dxf_x2, dxf_y2)])
    print(f"  Render box: ({dxf_x1:.0f},{dxf_y1:.0f})-({dxf_x2:.0f},{dxf_y2:.0f})")

    # PASS 2: 精确定位 high-dpi
    print(f"  PASS 2: zoomed render 180dpi...", end=" ", flush=True)
    img2 = render_pass(doc, msp, dpi=180, render_box=render_box)
    img2.save(output_path)
    sz = os.path.getsize(output_path)
    print(f"{img2.size[0]}x{img2.size[1]}  ({sz//1024}KB)")


if __name__ == "__main__":
    cache = "/home/ubuntu/.hermes/cache/documents"
    images = "/home/ubuntu/.hermes/image_cache"
    os.makedirs(images, exist_ok=True)

    for f in sorted(os.listdir(cache)):
        if not f.endswith('.dxf'): continue
        inp = os.path.join(cache, f)
        out = os.path.join(images, f"tp_{f.replace('.dxf','.png')}")
        print(f"\n{'='*50}\n{f}")
        render_two_pass(inp, out)
