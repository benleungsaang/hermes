#!/usr/bin/env python3.12
"""
Render a DXF to a vision-readable PNG.

B 2026-06-17: vision-based extraction is the new primary path. The render
quality is the bottleneck, not the parser. This script fixes the 3 known
failure modes:

  1. Auto-scaling to empty model space
  2. Block INSERT content in tiny offsets
  3. Chinese font missing (matplotlib default)

Strategy: find MTEXT bbox first (fast, deterministic, always has content).
Apply 20% padding for geometry context. If no MTEXT, fall back to ALL entity
positions.

Usage:
    python3.12 render_dxf_for_vision.py <input.dxf> <output.png> [--dpi 200]

Pitfalls:
  - Frontend is slow (15-20s per DXF). Plan timeouts accordingly.
  - DIMENSION and LINE entities can scatter bbox to 30x useful area.
    Always start with MTEXT bbox, not full entity scan.
"""
import sys
sys.path.insert(0, '/home/ubuntu/.local/lib/python3.12/site-packages')

import matplotlib
matplotlib.use('Agg')
matplotlib.rcParams['font.sans-serif'] = ['WenQuanYi Zen Hei', 'Noto Sans CJK SC', 'DejaVu Sans']
matplotlib.rcParams['axes.unicode_minus'] = False

import ezdxf
from ezdxf.addons.drawing import RenderContext, Frontend
from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
import matplotlib.pyplot as plt
from pathlib import Path
import re

_CTRL = re.compile(r'\\[A-Za-z][^;]*;')


def _mtext_positions(doc):
    """Recursively walk all blocks and collect MTEXT/TEXT positions.
    Returns list of (x, y) tuples, or empty list.
    DIMENSION/LINE entities are deliberately excluded to avoid bbox spread."""
    visited = set()
    pts = []

    def walk(entities, offset=(0.0, 0.0)):
        for ent in entities:
            t = ent.dxftype()
            if t == 'INSERT':
                name = ent.dxf.name
                if name in visited:
                    continue
                visited.add(name)
                try:
                    ins = ent.dxf.insert
                    sx = float(ent.dxf.get('xscale', 1.0))
                    sy = float(ent.dxf.get('yscale', 1.0))
                    child_off = (offset[0] + ins.x*sx, offset[1] + ins.y*sy)
                    yield from walk(doc.blocks.get(name), child_off)
                except (KeyError, AttributeError):
                    pass
            elif t in ('MTEXT', 'TEXT'):
                raw = _CTRL.sub('', ent.text).replace('\\P',' ').replace('\\~',' ')
                raw = re.sub(r'\s+', ' ', raw).strip()
                if raw and not (len(raw)==1 and raw in '?\\`/ '):
                    p = ent.dxf.insert
                    pts.append((p.x+offset[0], p.y+offset[1]))
    for _ in walk(doc.modelspace()):
        pass
    return pts


def _all_positions(doc):
    """Fallback: collect ALL entity positions. Used when MTEXT scan returns nothing."""
    visited = set()
    def walk(entities, offset=(0.0, 0.0)):
        for ent in entities:
            t = ent.dxftype()
            if t == 'INSERT':
                name = ent.dxf.name
                if name in visited:
                    continue
                visited.add(name)
                try:
                    ins = ent.dxf.insert
                    sx = float(ent.dxf.get('xscale', 1.0))
                    sy = float(ent.dxf.get('yscale', 1.0))
                    child_off = (offset[0] + ins.x*sx, offset[1] + ins.y*sy)
                    yield from walk(doc.blocks.get(name), child_off)
                except (KeyError, AttributeError):
                    pass
            else:
                for attr in ('insert', 'start', 'end', 'defpoint'):
                    if ent.dxf.hasattr(attr):
                        p = ent.dxf.get(attr)
                        if p is None:
                            continue
                        try:
                            yield (p.x+offset[0], p.y+offset[1])
                        except AttributeError:
                            try:
                                yield (p[0]+offset[0], p[1]+offset[1])
                            except (TypeError, IndexError):
                                pass
                        break
    return list(walk(doc.modelspace()))


def render_dxf(input_path, output_path, dpi=200):
    doc = ezdxf.readfile(input_path)

    # === Phase 1: compute bbox ===
    pts = _mtext_positions(doc)
    mode = 'mtext'

    if not pts or len(pts) < 3:
        pts = _all_positions(doc)
        mode = 'all-entities'
        if not pts:
            print(f'WARN: no positioned entities found in {input_path}', file=sys.stderr)
            return False

    xs = sorted(p[0] for p in pts)
    ys = sorted(p[1] for p in pts)
    x_min, x_max = xs[0], xs[-1]
    y_min, y_max = ys[0], ys[-1]
    width = x_max - x_min
    height = y_max - y_min

    pad_x = width * 0.20 or 1.0
    pad_y = height * 0.20 or 1.0

    # Adaptive figure size
    if width > height * 2:
        fig_w, fig_h = 22, 10
    elif height > width * 2:
        fig_w, fig_h = 10, 22
    else:
        fig_w, fig_h = 14, 10

    # === Phase 2: render ===
    fig, ax = plt.subplots(figsize=(fig_w, fig_h))
    ctx = RenderContext(doc)
    out_backend = MatplotlibBackend(ax)
    Frontend(ctx, out_backend).draw_layout(doc.modelspace(), finalize=True)

    ax.set_xlim(x_min - pad_x, x_max + pad_x)
    ax.set_ylim(y_min - pad_y, y_max + pad_y)
    ax.set_aspect('equal')
    ax.axis('off')
    plt.savefig(output_path, dpi=dpi, bbox_inches='tight', pad_inches=0)
    plt.close()

    kb = Path(output_path).stat().st_size // 1024
    print(f'Rendered: {output_path} ({kb} KB, mode={mode})')
    print(f'  Content bbox: [{x_min:.0f}, {x_max:.0f}] x [{y_min:.0f}, {y_max:.0f}]')
    print(f'  Content size: {width:.0f} x {height:.0f}')

    if mode == 'all-entities' and width > 50000:
        print(f'  WARN: all-entities bbox very wide ({width:.0f}). Vision may miss small text.',
              file=sys.stderr)
    return True


def main():
    if len(sys.argv) < 3:
        print('Usage: python3.12 render_dxf_for_vision.py <input.dxf> <output.png> [--dpi N]')
        sys.exit(1)

    input_path = sys.argv[1]
    output_path = sys.argv[2]
    dpi = 200

    for i, arg in enumerate(sys.argv[3:]):
        if arg == '--dpi' and i+1 < len(sys.argv[3:]):
            dpi = int(sys.argv[3:][i+1])

    if not Path(input_path).exists():
        print(f'File not found: {input_path}', file=sys.stderr)
        sys.exit(1)

    ok = render_dxf(input_path, output_path, dpi=dpi)
    sys.exit(0 if ok else 2)


if __name__ == '__main__':
    main()
