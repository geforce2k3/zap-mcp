"""
圖表生成模組
"""
import os
from typing import Dict

import matplotlib.pyplot as plt

# 確保字型已設定
from config.fonts import setup_fonts
setup_fonts()


def generate_risk_chart(stats: Dict[str, int], output_path: str) -> bool:
    """
    生成風險分佈圓餅圖

    Args:
        stats: 風險統計字典 {"High": n, "Medium": n, ...}
        output_path: 輸出圖片路徑

    Returns:
        bool: 是否成功生成
    """
    labels = []
    sizes = []
    colors = []

    # 風險等級對照
    mapping = {
        "High": ("高風險", "#ff0000"),
        "Medium": ("中風險", "#ffa500"),
        "Low": ("低風險", "#ffff00"),
        "Informational": ("資訊", "#0000ff")
    }

    for key, (label, color) in mapping.items():
        count = stats.get(key, 0)
        if count > 0:
            labels.append(f"{label} ({count})")
            sizes.append(count)
            colors.append(color)

    if not sizes:
        return False

    try:
        plt.figure(figsize=(4, 3))
        plt.pie(
            sizes,
            labels=labels,
            colors=colors,
            autopct='%1.1f%%',
            startangle=140
        )
        plt.axis('equal')
        plt.title("弱點風險分佈")
        plt.tight_layout()
        plt.savefig(output_path, dpi=150)
        plt.close()
        return True
    except Exception as e:
        print(f"繪圖失敗: {e}")
        plt.close()
        return False
