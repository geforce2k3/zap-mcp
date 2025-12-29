"""
ZAP Reporter - 模組化主程式
"""
import os
from datetime import datetime

# [New] 引入 NMAP_REPORT_FILENAME
from config.settings import DATA_DIR, ZAP_REPORT_FILENAME, AI_INSIGHTS_FILENAME, NMAP_REPORT_FILENAME
from report_builder import generate_word_report
# [New] 引入 Nmap 解析器
from services.nmap_parser import NmapParser

def main():
    """主程式入口"""
    # 檔案路徑
    json_file = os.path.join(DATA_DIR, ZAP_REPORT_FILENAME)
    ai_file = os.path.join(DATA_DIR, AI_INSIGHTS_FILENAME)
    nmap_file = os.path.join(DATA_DIR, NMAP_REPORT_FILENAME) # [New]
    
    word_file = os.path.join(DATA_DIR, f'Scan_Report_{datetime.now().strftime("%y%m%d%H%M")}.docx')

    # 檢查 ZAP 報告 (這是必要的)
    if not os.path.exists(json_file):
        print(f"找不到 ZAP 報告檔案: {json_file}")
        return 1

    # [New] 解析 Nmap 報告 (如果是存在的)
    nmap_data = None
    if os.path.exists(nmap_file):
        print(f"發現 Nmap 報告，正在解析...")
        nmap_data = NmapParser().parse(nmap_file)

    # 生成報告 (傳入 nmap_data)
    success = generate_word_report(
        json_path=json_file,
        output_path=word_file,
        ai_insights_path=ai_file,
        nmap_data=nmap_data # [New]
    )

    return 0 if success else 1

if __name__ == "__main__":
    exit(main())