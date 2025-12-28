"""
ZAP Reporter - 模組化主程式
將 ZAP JSON 報告轉換為格式化的 Word 文檔
"""
import os
from datetime import datetime

from config.settings import DATA_DIR, ZAP_REPORT_FILENAME, AI_INSIGHTS_FILENAME
from report_builder import generate_word_report


def main():
    """主程式入口"""
    # 檔案路徑
    json_file = os.path.join(DATA_DIR, ZAP_REPORT_FILENAME)
    ai_file = os.path.join(DATA_DIR, AI_INSIGHTS_FILENAME)
    word_file = os.path.join(DATA_DIR, f'Scan_Report_{datetime.now().strftime("%y%m%d%H%M")}.docx')

    # 檢查報告檔案
    if not os.path.exists(json_file):
        print(f"找不到檔案: {json_file}")
        return 1

    # 生成報告
    success = generate_word_report(
        json_path=json_file,
        output_path=word_file,
        ai_insights_path=ai_file
    )

    return 0 if success else 1


if __name__ == "__main__":
    exit(main())
