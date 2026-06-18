#!/usr/bin/env python3
"""
DXF 渲染脚本 v3 — 自动检测最优裁剪 + 中文字体
B 2026-06-17 DeepSeek Flash 主导 / MiniMax 辅助
================================================
核心变化 v2→v3:
- auto_detect_bbox() 自动决策：full bbox vs mtext bbox
  决策规则：
    (1) 如果 full_bbox 面积 / mtext_bbox 面积 > 20 → 用 mtext_bbox
        （draw_1 情形：MTEXT 压缩在极小区域，LINE 散布在全图）
    (2) 如果 full_bbox 有效 → 用 full_bbox（draw_4 情形：紧凑图）
    (3) 如果 full_bbox 和 mtext_bbox 都有效且面积接近 → 用 full_bbox
    (4) 兜底：无剔除 full_bbox
- 不再需要 --mtext-only / --all-geometry 手动开关
- 内置 "dryrun" 模式：只打印检测结果不渲染
"""
import sys
import os
import math
import argparse
import re as _re

sys.path.insert(0, "/home/ubuntu/.local/lib/python3.12/site-packages")

import matplotlib
matplotlib.use("Agg")
matplotlib.rcParams["font.sans-serif"] = [
    "WenQuanYi Zen Hei",
    "Noto Sans CJK SC",
    "DejaVu Sans",
]
matplotlib.rcParams["axes.unicode_minus"] = False

import ezdxf
from ezdxf.addons.drawing import RenderContext, Frontend
from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
import matplotlib.pyplot as plt


# ============================================================
# 遍历（含嵌套块展开）
# ============================================================
def _iter_all(doc, layout_name="Model"):
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


# ============================================================
# MTEXT 清洗（判断有效文本）
# ============================================================
_RE_CONTROL_ONLY = _re.compile(r'^\\?[A-Za-z]?$')


def _is_valid_mtext(text):
    s = _re.sub(r'\\[A-Za-z][^;]*;', '', text)
    s = s.replace('\\P', ' ').replace('\\~', ' ')
    s = _re.sub(r'\s+', ' ', s).strip()
    return None if (not s or _RE_CONTROL_ONLY.match(s)) else s


# ============================================================
# bbox 计算
# ============================================================
def _collect_pts(doc, layout_name, entity_type="all"):
    """遍历 entity 返回点列表 [(x, y), ...]"""
    pts = []
    for ent, _depth, (ox, oy) in _iter_all(doc, layout_name):
        t = ent.dxftype()
        # 文字类型
        if entity_type == "mtext" and t not in ("MTEXT", "TEXT"):
            continue
        if entity_type == "mtext":
            clean = _is_valid_mtext(ent.text)
            if not clean:
                continue
            p = ent.dxf.insert
            pts.append((p.x + ox, p.y + oy))
            continue

        try:
            if t == "LINE":
                s, e = ent.dxf.start, ent.dxf.end
                pts.extend([(s.x + ox, s.y + oy), (e.x + ox, e.y + oy)])
            elif t == "CIRCLE":
                c = ent.dxf.center
                r = float(ent.dxf.radius)
                pts.extend([(c.x + ox - r, c.y + oy - r), (c.x + ox + r, c.y + oy + r)])
            elif t == "ARC":
                c = ent.dxf.center
                r = float(ent.dxf.radius)
                pts.extend([(c.x + ox - r, c.y + oy - r), (c.x + ox + r, c.y + oy + r)])
            elif t in ("MTEXT", "TEXT"):
                p = ent.dxf.insert
                pts.append((p.x + ox, p.y + oy))
            elif t == "LWPOLYLINE":
                for pt in ent.get_points():
                    pts.append((pt[0] + ox, pt[1] + oy))
            elif t == "SPLINE":
                for pt in ent.control_points:
                    pts.append((pt[0] + ox, pt[1] + oy))
            elif t == "DIMENSION":
                p = ent.dxf.get("insert") or ent.dxf.get("defpoint")
                if p is not None:
                    pts.append((p.x + ox, p.y + oy))
            elif t == "LEADER":
                for vtx in ent.vertices:
                    pts.append((vtx[0] + ox, vtx[1] + oy))
        except Exception:
            pass
    return pts


def bbox_from_pts(pts, trim_outliers=True):
    """从点列表算 bbox。返回 (xmin,ymin,xmax,ymax) 或 None"""
    if not pts:
        return None
    xs = sorted(p[0] for p in pts)
    ys = sorted(p[1] for p in pts)
    n = len(xs)

    if trim_outliers and n >= 20:
        lo = int(n * 0.03)      # 跳过最小 3%
        hi = int(n * 0.97) - 1  # 跳过最大 3%
        return (xs[lo], ys[lo], xs[hi], ys[hi])

    return (xs[0], ys[0], xs[-1], ys[-1])


def auto_detect_bbox(doc, layout_name="Model"):
    """
    自动检测最优 bbox。
    返回 (xmin,ymin,xmax,ymax, mode)，mode 为 "full" / "mtext"
    """
    # --- 1. 算三种 bbox ---
    all_pts = _collect_pts(doc, layout_name, "all")
    full_bbox = bbox_from_pts(all_pts, trim_outliers=True)
    raw_bbox = bbox_from_pts(all_pts, trim_outliers=False)

    mtext_pts = _collect_pts(doc, layout_name, "mtext")
    mtext_bbox = bbox_from_pts(mtext_pts, trim_outliers=False)

    full_area = None
    mtext_area = None
    if full_bbox:
        full_area = (full_bbox[2] - full_bbox[0]) * (full_bbox[3] - full_bbox[1])
    if mtext_bbox:
        mtext_area = (mtext_bbox[2] - mtext_bbox[0]) * (mtext_bbox[3] - mtext_bbox[1])

    print(f"   full bbox: {bbox_str(full_bbox)}  area={fmt_area(full_area)}")
    print(f"   mtext bbox: {bbox_str(mtext_bbox)}  area={fmt_area(mtext_area)}")
    print(f"   raw  bbox: {bbox_str(raw_bbox)}")

    # --- 2. 决策树 ---
    # 两者都有且 full >> mtext → 用 mtext
    if full_bbox and mtext_bbox and full_area and mtext_area:
        ratio = full_area / mtext_area
        print(f"   full/mtext ratio: {ratio:.1f}")
        if ratio > 10:
            print(f"   → 选择 mtext bbox（full 太大，文字集中在 mtext 区）")
            return (*mtext_bbox, "mtext")
        # 两者接近 → 用 full（包含几何和文字）
        return (*full_bbox, "full")

    # 只有 full → 用 full
    if full_bbox:
        print(f"   → 选择 full bbox")
        return (*full_bbox, "full")

    # 只有 mtext → 用 mtext
    if mtext_bbox:
        print(f"   → 选择 mtext bbox（full 为空）")
        return (*mtext_bbox, "mtext")

    # 都没有 → 用 raw 兜底
    if raw_bbox:
        print(f"   → 选择 raw bbox（兜底）")

    # 【第 2 级】如果 ratio > 10 但 mtext_bbox 也很大（draw_2 SOONWIN 块场景）
    # 用 1% 百分位再试一次 full bbox
    if full_area and mtext_area and full_area / mtext_area > 10 and len(mtext_pts) >= 5:
    tighter_full_bbox = bbox_from_pts(all_pts, trim_outliers=True, trim_pct=1.0)
    if tighter_full_bbox:
        tf_area = (tighter_full_bbox[2] - tighter_full_bbox[0]) * (tighter_full_bbox[3] - tighter_full_bbox[1])
        print(f"   tighter full bbox: {bbox_str(tighter_full_bbox)}  area={fmt_area(tf_area)}")
        if tf_area and mtext_area:
            t_ratio = tf_area / mtext_area
            print(f"   tighter/mtext ratio: {t_ratio:.1f}")
            if t_ratio < 10:
                print(f"   → 选择 tighter full bbox")
                return (*tighter_full_bbox, "full+tighter")
            # 如果 tighter 后 ratio 仍大但 mtext 小，且 tighter 包含几何 → 选 tighter
            print(f"   → 选择 tighter full bbox（still large but has geometry context）")
            return (*tighter_full_bbox, "full+tighter")

    return (*mtext_bbox, "mtext")

    if raw_bbox:
    print(f"   → 选择 raw bbox（兜底）")




def bbox_str(b):
    if not b:
        return "None"
    return f"x=[{b[0]:.0f},{b[2]:.0f}] y=[{b[1]:.0f},{b[3]:.0f}] ({b[2]-b[0]:.0f}x{b[3]-b[1]:.0f})"


def fmt_area(a):
    if a is None:
        return "None"
    a_abs = abs(a)
    if a_abs > 1e8:
        return f"{a_abs / 1e6:.1f}M"
    if a_abs > 1e4:
        return f"{a_abs / 1e4:.1f}万"
    return f"{a_abs:.0f}"


# ============================================================
# 渲染
# ============================================================
def render_dxf(input_path, output_path, layout_name="Model", padding=0.08, dpi=200):
    """
    1. 自动检测 bbox
    2. ezdxf Frontend 渲染
    3. 裁剪 + 保存
    """
    if not os.path.exists(input_path):
        print(f"❌ 找不到: {input_path}")
        return None

    doc = ezdxf.readfile(input_path)

    result = auto_detect_bbox(doc, layout_name)
    if result is None:
        print(f"⚠️  {input_path}: 没有可渲染的内容")
        return None

    x_min, y_min, x_max, y_max, mode = result
    w, h = x_max - x_min, y_max - y_min
    print(f"📐 最终裁剪 [{mode}]: x=[{x_min:.0f}, {x_max:.0f}], y=[{y_min:.0f}, {y_max:.0f}] ({w:.0f} × {h:.0f})")

    # 自适应画布比例
    aspect = w / h if h > 0 else 1.0
    if aspect > 2.5:
        figsize = (22, 10)
    elif aspect > 1.8:
        figsize = (20, 12)
    elif aspect < 0.5:
        figsize = (10, 20)
    else:
        figsize = (16, 12)

    fig, ax = plt.subplots(figsize=figsize)

    ctx = RenderContext(doc)
    out = MatplotlibBackend(ax)
    target = doc.modelspace() if layout_name == "Model" else doc.layouts.get(layout_name)
    Frontend(ctx, out).draw_layout(target, finalize=True)

    pad_x = w * padding
    pad_y = h * padding
    ax.set_xlim(x_min - pad_x, x_max + pad_x)
    ax.set_ylim(y_min - pad_y, y_max + pad_y)
    ax.set_aspect("equal")
    ax.set_title(f"{os.path.basename(input_path)} · layout={layout_name} · mode={mode}", fontsize=8)

    plt.tight_layout()
    plt.savefig(output_path, dpi=dpi, bbox_inches="tight")
    plt.close()
    kb = os.path.getsize(output_path) // 1024
    print(f"✅ saved {output_path} ({kb} KB | {w:.0f}×{h:.0f} @ {dpi}dpi)")
    return output_path, w, h, mode


def auto_process(dxf_path, output_dir=None, dpi=200):
    """自动处理一个 DXF：渲染 + 打印结果"""
    output_dir = output_dir or "/tmp"
    os.makedirs(output_dir, exist_ok=True)
    basename = os.path.splitext(os.path.basename(dxf_path))[0]
    out_path = os.path.join(output_dir, f"{basename}_render.png")
    return render_dxf(dxf_path, out_path, dpi=dpi)


# ============================================================
# CLI
# ============================================================
def main():
    parser = argparse.ArgumentParser(description="DXF → PNG 渲染 v3（自动检测最优裁剪）")
    parser.add_argument("input", help="输入 DXF 路径（或目录 = 批量处理）")
    parser.add_argument("output", default=None, nargs="?", help="输出 PNG 路径（默认 /tmp/<dxfname>_render.png）")
    parser.add_argument("--layout", default="Model", help="布局名")
    parser.add_argument("--padding", type=float, default=0.08, help="裁剪 padding 比例")
    parser.add_argument("--dpi", type=int, default=200, help="图片分辨率")
    parser.add_argument("--dryrun", action="store_true", help="只检测 bbox 不渲染")
    args = parser.parse_args()

    import pathlib

    # 批量处理目录
    in_path = pathlib.Path(args.input)
    if in_path.is_dir():
        dxf_files = sorted(in_path.glob("*.dxf"))
        print(f"📁 批量处理 {len(dxf_files)} 个 DXF 文件...")
        for f in dxf_files:
            print(f"\n--- {f.name} ---")
            if args.dryrun:
                _dryrun(str(f), args.layout)
            else:
                out = args.output or None
                if out:
                    out = str(pathlib.Path(out) / f"{f.stem}_render.png")
                render_dxf(str(f), out or None, args.layout, args.padding, args.dpi)
        return

    # 单个文件
    out_path = args.output
    if not out_path:
        out_path = f"/tmp/{in_path.stem}_render.png"

    if args.dryrun:
        _dryrun(args.input, args.layout)
    else:
        render_dxf(args.input, out_path, args.layout, args.padding, args.dpi)


def _dryrun(dxf_path, layout):
    import ezdxf
    doc = ezdxf.readfile(dxf_path)
    result = auto_detect_bbox(doc, layout)
    if result:
        print(f"   mode={result[4]}")
    else:
        print(f"   ❌ 无内容")


if __name__ == "__main__":
    main()
