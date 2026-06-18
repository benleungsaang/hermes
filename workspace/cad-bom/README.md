# CAD → BOM 工具链

## 目标
读取包装机/机械 CAD 图纸（DWG/DXF）→ 解析出零部件清单 → 输出 Excel BOM 表

## 当前方案（v0.1，2026-06-17 验证通过）

**方案 B：标注驱动**
- 输入：DXF 文件（R2013 及以下，ezdxf 原生支持；R2018+ 需要先转 DXF）
- 抽取：MTEXT（部件名） + DIMENSION（尺寸）
- 关联：空间最近原则
- 聚类：名称归一化（去末尾数字）+ 尺寸容差聚类（默认 ±3mm）
- 输出：Excel BOM 表（部件名、数量、尺寸、实例名）

## 验证结果（draw_1.dxf，HP-FB-370L 整机图）
- 抽取：7 个 MTEXT（含 HP-FB-370L 整机型号，识别为项目本身保留）
- 输出：5 行 BOM（含 packaging line 隐含件）
  - Transition conveyor × 4（801.9-802.9mm）
  - Feeding conveyor × 1（600mm）
  - HP-FB-370L（项目）× 1（1201mm）
  - Turnable unit × 1（600mm）
  - Electrical cabinet（总电箱）× 1（自动追加，浅黄色行，不需要时手动删除）

## 工具
- `tools/cad_bom_extract.py` —— 主程序

## 用法

```bash
# 用 system python 3.12（ezdxf/numpy/openpyxl 已装在 /home/ubuntu/.local/lib/python3.12/site-packages）
/usr/bin/python3.12 ~/.hermes/workspace/cad-bom/tools/cad_bom_extract.py <input.dxf> [output.xlsx]
```

## 已知限制
- **R2018+ DWG 必须先转 DXF**（用 AutoCAD/中望/浩辰的"另存为 DXF"功能）
- **无传统明细栏的图**才适用本工具（你确认这是典型样本）
- **未标注件**不强行聚类，输出到「未关联尺寸」sheet 提醒人工确认
- **尺寸聚类容差**默认 ±3mm，图纸比例尺大时可能需要调整

## 配置参数（在 cad_bom_extract.py 顶部）
- `SIZE_TOLERANCE_MM = 3.0` —— 尺寸聚类容差
- `ASSOC_MAX_DIST = 2000.0` —— MTEXT-DIMENSION 最大关联距离（图纸单位）
- `TITLE_KEYWORDS` —— 标题/整机型号关键字（用于过滤）

## 待办（v0.2+）
- 几何相似度聚类（识别"未标注"的重复件，方案 A）
- 块属性（ATTRIB）解析支持
- 多图纸批量处理
- PDF 视觉识别对比（如果你以后会收到 PDF 终版图）
