"""
ZAP 報告建構器
將 ZAP JSON 報告轉換為格式化的 Word 文檔
"""
import os
import json
from typing import Optional

from docx import Document
from docx.shared import Pt
from docx.oxml.ns import qn

from config.settings import DATA_DIR, DEFAULT_COMPANY_NAME
from services.translator import save_translation_cache
from document.sections import add_cover_page, add_summary_section, add_details_section


def _load_json(file_path: str) -> Optional[dict]:
    """載入 JSON 檔案"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"讀取 JSON 失敗: {file_path} - {e}")
        return None


def _init_document() -> Document:
    """初始化 Word 文檔並設定預設樣式"""
    doc = Document()

    # 設定預設字型
    style = doc.styles['Normal']
    style.font.name = 'Microsoft JhengHei'
    style.font.size = Pt(11)
    style.element.rPr.rFonts.set(qn('w:eastAsia'), 'Microsoft JhengHei')

    return doc


def generate_word_report(
    json_path: str,
    output_path: str,
    ai_insights_path: Optional[str] = None,
    company_name: str = DEFAULT_COMPANY_NAME
) -> bool:
    """
    生成 Word 格式的弱點掃描報告

    Args:
        json_path: ZAP JSON 報告路徑
        output_path: Word 輸出路徑
        ai_insights_path: AI 分析 JSON 路徑 (可選)
        company_name: 公司名稱

    Returns:
        bool: 是否成功生成
    """
    # 載入 ZAP 報告
    data = _load_json(json_path)
    if data is None:
        return False

    # 載入 AI 分析 (可選)
    ai_data = None
    if ai_insights_path and os.path.exists(ai_insights_path):
        ai_data = _load_json(ai_insights_path)
        if ai_data:
            print("成功載入 AI 分析數據！")

    # 初始化文檔
    doc = _init_document()
    base_dir = os.path.dirname(json_path)

    # 生成各區塊
    add_cover_page(doc, data, base_dir, company_name)
    add_summary_section(doc, data, base_dir, ai_data)
    add_details_section(doc, data, ai_data)

    # 儲存文檔
    try:
        doc.save(output_path)
        print(f"報告生成完畢！已儲存至: {output_path}")

        # 儲存翻譯快取
        save_translation_cache()

        return True
    except Exception as e:
        print(f"儲存失敗: {e}")
        return False
