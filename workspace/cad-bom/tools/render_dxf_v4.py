#!/usr/bin/env python3
"""
DXF 渲染 v4.1 — 两步法（pragmatic）
第一步：全幅渲染到文件 + PIL 像素密度分析
第二步：缩放渲染到精准裁剪

B 2026-06-17 思路：不要算 DXF bbox，用"读像素"替代
"""
import sys, os, math, subprocess
sys.path.insert(0, "/home/ubuntu/.local/lib/python3.12/site-packages")

import matplotlib
matplotlib.use("Agg")
matplotlib.rcParams["font.sans-serif"] = ["WenQuanYi Zen Hei", "DejaVu Sans"]
matplotlib.rcParams["axes.unicode_minus"] = False

from ezdxf.addons.drawing import RenderContext, Frontend
from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
import matplotlib.pyplot as plt
import ezdxf
from PIL import Image
import numpy as np


def render_to_file(doc, layout, output_path, dpi=72, figsize=(16, 10)):
    """渲染 DXF 到文件（最低开销）"""
    fig, ax = plt.subplots(figsize=figsize)
    ctx = RenderContext(doc)
    out = MatplotlibBackend(ax)
    Frontend(ctx, out).draw_layout(layout, finalize=True)
    ax.set_aspect("equal")
    ax.axis("off")
    fig.subplots_adjust(left=0, right=1, bottom=0, top=1)
    plt.savefig(output_path, dpi=dpi, bbox_inches="tight", pad_inches=0)
    plt.close(fig)


def find_content_bbox_from_file(image_path, grids=20, tolerance=30):
    """从 PNG 文件读像素，找密度高的内容区"""
    img = Image.open(image_path).convert("RGB")
    arr = np.array(img, dtype=np.uint8)
    h, w, _ = arr.shape

    # 子采样加速
    step = max(1, min(w, h) // 300)
    thin = arr[::step, ::step]
    th, tw, _ = thin.shape

    bg = np.array([85, 85, 85], dtype=np.uint8)
    diff = np.abs(thin.astype(np.int16) - bg.astype(np.int16))
    mask = np.any(diff > tolerance, axis=2)

    # 密度网格
    cell_h = th / grids
    cell_w = tw / grids
    density = np.zeros((grids, grids), dtype=np.float32)

    for gy in range(grids):
        ys = int(gy * cell_h)
        ye = int((gy + 1) * cell_h)
        for gx in range(grids):
            xs = int(gx * cell_w)
            xe = int((gx + 1) * cell_w)
            cell = mask[ys:ye, xs:xe]
            if cell.size > 0:
                density[gy, gx] = cell.sum() / cell.size

    # 找高密度区：> 2x 均值 或 > 2%
    m = density[density > 0].mean() if (density > 0).any() else 0
    high = density > max(m * 2, 0.02)

    if not high.any():
        # 散点情况（draw_1）→ fallback 到非空像素范围
        rows = np.any(mask, axis=1)
        cols = np.any(mask, axis=0)
        xi = np.where(cols)[0]
        yi = np.where(rows)[0]
        if len(xi) < 3 or len(yi) < 3:
            return None
        # 变成像素坐标
        return (int(xi[0])*step, int(yi[0])*step,
                int(xi[-1])*step, int(yi[-1])*step)

    gy, gx = np.where(high)
    # 前后补 1 个格子
    gx1, gx2 = max(0, gx.min() - 1), min(grids - 1, gx.max() + 1)
    gy1, gy2 = max(0, gy.min() - 1), min(grids - 1, gy.max() + 1)

    def grid_to_px(gi, total_cells, total_px):
        return int(gi / total_cells * total_px * step)

    return (grid_to_px(gx1, grids, tw) * step // step * step,
            grid_to_px(gy1, grids, th) * step // step * step,
            grid_to_px(gx2 + 1, grids, tw) * step,
            grid_to_px(gy2 + 1, grids, th) * step)


def render_dxf_v41(input_path, output_path, layout_name="Model", dpi=200):
    doc = ezdxf.readfile(input_path)
    layout = doc.modelspace() if layout_name == "Model" else doc.layouts.get(layout_name)

    # Step 1: 全幅渲染（72dpi 碎片）
    tmp = "/tmp/_dxf_step1.png"
    print(f"🅰️ step 1: 全幅渲染（72dpi）...", end=" ", flush=True)
    render_to_file(doc, layout, tmp, dpi=72)
    kb1 = os.path.getsize(tmp) // 1024
    print(f"{kb1}KB")

    # Step 2: 像素密度分析
    print(f"🅱️ step 2: 像素分析...", end=" ", flush=True)
    cbox = find_content_bbox_from_file(tmp)
    if cbox is None:
        print("找不到内容，输出 step1")
        os.rename(tmp, output_path)
        return output_path, None, "fallback-no-content"
    x1, y1, x2, y2 = cbox
    cw, ch = x2 - x1, y2 - y1
    img = Image.open(tmp)
    iw, ih = img.size
    fill = (cw * ch) / (iw * ih) * 100
    print(f"内容区 ({x1},{y1})-({x2},{y2}) = {cw}×{ch} px, 填充率 {fill:.0f}%")
    os.remove(tmp)

    # Step 3: 缩放渲染
    print(f"🅲 step 3: 缩放渲染（{dpi}dpi）...", end=" ", flush=True)
    fig, ax = plt.subplots(figsize=(16, 10))
    ctx = RenderContext(doc)
    out = MatplotlibBackend(ax)
    Frontend(ctx, out).draw_layout(layout, finalize=True)
    ax.set_aspect("equal")
    ax.axis("off")
    fig.subplots_adjust(left=0, right=0, bottom=0, top=1)

    # 用像素比例反推数据坐标缩放
    cur_xl, cur_xr = ax.get_xlim()
    cur_yb, cur_yt = ax.get_ylim()
    cur_w = cur_xr - cur_xl
    cur_h = cur_yt - cur_yb

    # scale factor = 让内容填充 70% 画布
    target_fill = 0.7
    scale = math.sqrt(target_fill / max(fill / 100, 0.01))
    scale = max(0.5, min(scale, 10))  # clamp

    cx = (cur_xl + cur_xr) / 2
    cy = (cur_yb + cur_yt) / 2
    new_w = cur_w / scale
    new_h = cur_h / scale

    ax.set_xlim(cx - new_w / 2, cx + new_w / 2)
    ax.set_ylim(cy - new_h / 2, cy + new_h / 2)

    plt.savefig(output_path, dpi=dpi, bbox_inches="tight", pad_inches=0)
    plt.close(fig)
    kb = os.path.getsize(output_path) // 1024
    print(f"{kb}KB ✅")
    return output_path, {"fill_pct": fill, "scale": scale}, "two-pass"


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python3 render_dxf_v4.py <input.dxf> [output.png]")
        sys.exit(1)
    inp = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else inp.replace(".dxf", "_v4.png")
    render_dxf_v41(inp, out)
