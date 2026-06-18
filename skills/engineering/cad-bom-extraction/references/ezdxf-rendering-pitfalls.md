# ezdxf 渲染瓶颈记录（2026-06-18 确认）

## 核心瓶颈

ezdxf Frontend 本身是瓶颈（实体遍历 + INSERT 块展开），不是后端。
- MatplotlibBackend: 每图 4-5s
- PyMuPdfBackend: 每图 5-34s（取决于 render_box 尺寸）
- 速度差异可忽略，不要花时间换后端

## 已尝试方案与结果

### 方案 1: 全幅 bbox + MatplotlibBackend（v2/v3）
- draw_1: 5s, 59KB, vision 可读 ✅
- draw_2: 超时（SOONWIN 块扩展）❌
- draw_4: 超时 ❌

### 方案 2: mtext-only bbox + MatplotlibBackend（v3 --mtext-only）
- draw_1: 112KB, vision 全读 ✅
- draw_2/draw_4: 被 50% padding 压太小 ❌

### 方案 3: dxfgrabber 计算 bbox + PyMuPdfBackend
- draw_1: 34s, 9.5MB（13230x38123 像素，太大）❌
- draw_2: bbox (0,0)-(0,0)（dxfgrabber 不展开 INSERT）❌
- draw_4: 5s, 3KB（bbox 太小）❌

### 方案 4: 两步像素分析（render_two_pass.py）
- PASS 1: 全幅 low-res
- PIL 扫非白像素区域
- PASS 2: 精裁 high-dpi
- 结果：三张图全部 100% fill（散点 LINE 布满全图），PASS 1 白做 ❌

### 方案 5: 实体遍历 bbox + PyMuPdfBackend（render_v7.py）
- 未执行。用户确认改用 PDF 方案。

## 结论

用户从 AutoCAD 直接出图的质量远好于 ezdxf 渲染。**不再尝试 ezdxf 渲染出图**。

## DXF 读取限制

### dxfgrabber（2026-06-18 测试）
- 读得快但浅
- 不展开 INSERT 嵌套块 → draw_2 bbox 变 (0,0) ❌
- 适合纯顶层 LINE/TEXT 的简单 DXF

### DXF header extents
- $EXTMIN/$EXTMAX 数据不可靠
- draw_1: 被散点 LINE 撑大到 full extents
- draw_2/draw_4: 不含 DIMENSION/块内部几何

### 实体遍历（compute_bbox + _iter_all_geometry）
- 递归正确但慢（遍历 + INSERT 展开 = Frontend 级别的处理量）
- draw_1 约 7s 完成 bbox 计算（仅遍历，不含渲染）
- 适合纯文本校验场景
