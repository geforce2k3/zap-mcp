"""
Word 文檔樣式設定
"""
from docx.shared import Pt, RGBColor


def set_table_header_style(cell):
    """
    設定表格標頭樣式

    Args:
        cell: Word 表格單元格
    """
    paragraphs = cell.paragraphs
    for p in paragraphs:
        for run in p.runs:
            run.bold = True
            run.font.size = Pt(12)


def get_risk_color(risk_level: str) -> RGBColor:
    """
    根據風險等級取得對應顏色

    Args:
        risk_level: 風險等級 (High/Medium/Low/Informational)

    Returns:
        RGBColor: 對應的顏色
    """
    color_map = {
        "High": RGBColor(255, 0, 0),      # 紅色
        "Medium": RGBColor(255, 165, 0),   # 橙色
        "Low": RGBColor(200, 200, 0),      # 黃色
        "Informational": RGBColor(0, 0, 255)  # 藍色
    }
    return color_map.get(risk_level, RGBColor(0, 0, 0))
