"""
報告匯出工具
"""
import os
import shutil

from core.config import INTERNAL_DATA_DIR, OUTPUT_DIR
from core.logging_config import logger


def retrieve_report() -> str:
    """
    【流程第六步】匯出所有報告檔案。

    Returns:
        str: 匯出結果訊息
    """
    try:
        if not os.path.exists(INTERNAL_DATA_DIR):
            return "資料目錄不存在。"

        # 確保輸出目錄存在
        os.makedirs(OUTPUT_DIR, exist_ok=True)

        # 找出所有報告檔案
        supported_extensions = ('.docx', '.json', '.xml', '.md')
        files = [
            f for f in os.listdir(INTERNAL_DATA_DIR)
            if f.endswith(supported_extensions)
        ]

        if not files:
            return "沒有找到可匯出的報告檔案。"

        copied = []
        for f in files:
            src = os.path.join(INTERNAL_DATA_DIR, f)
            dst = os.path.join(OUTPUT_DIR, f)
            shutil.copy2(src, dst)
            copied.append(f)
            logger.info(f"已匯出: {f}")

        return f"**匯出成功！**\n檔案: {', '.join(copied)}"

    except Exception as e:
        logger.error(f"匯出失敗: {e}")
        return f"匯出失敗: {str(e)}"
