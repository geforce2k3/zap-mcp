"""
ZAP Reporter 全局設定
"""
import os

# 資料目錄
DATA_DIR = os.getenv("ZAP_DATA_DIR", "/app/data")

# 翻譯快取檔案路徑
CACHE_FILE = os.path.join(DATA_DIR, "translation_cache.json")

# 報告預設公司名稱
DEFAULT_COMPANY_NAME = os.getenv("REPORT_COMPANY_NAME", "Nextlink MSP")

# 報告輸入輸出檔案
ZAP_REPORT_FILENAME = "ZAP-Report.json"
AI_INSIGHTS_FILENAME = "ai_insights.json"

# 文字長度限制
MAX_TEXT_LENGTH = 4500  # 翻譯 API 限制
