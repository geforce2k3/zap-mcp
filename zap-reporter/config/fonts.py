"""
字型配置模組
"""
import os
import shutil
import logging
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

logger = logging.getLogger(__name__)

def setup_fonts():
    """
    設定 Matplotlib 全域字型設定 (簡化版)
    """
    try:
        # 為了避免語法錯誤，我們將設定寫得緊湊一點
        # 設定 sans-serif 優先使用的字型列表
        plt.rcParams['font.sans-serif'] = ['Noto Sans CJK TC', 'sans-serif']

        # 設定字型家族
        plt.rcParams['font.family'] = ['sans-serif']

        # 解決負號顯示問題
        plt.rcParams['axes.unicode_minus'] = False
        
        logger.info("Fonts configuration loaded.")

    except Exception as e:
        logger.error(f"Error setting up fonts: {e}")
# 模組載入時自動設定字型
setup_fonts()
