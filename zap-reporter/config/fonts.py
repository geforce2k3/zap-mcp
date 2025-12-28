"""
字型配置模組
"""
import os
import shutil
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm


def setup_fonts():
    """
    設定中文字型支援

    清除 Matplotlib 快取並設定中文字型優先順序
    """
    # 嘗試清除 Matplotlib 快取
    try:
        cache_dir = fm.get_cachedir()
        if os.path.exists(cache_dir):
            shutil.rmtree(cache_dir)
    except Exception:
        pass

    # 設定中文字型優先順序
    plt.rcParams['font.family'] = ['sans-serif']
    plt.rcParams['font.sans-serif'] = [
        'Noto Sans CJK TC',      # Docker 容器常用
        'Noto Sans CJK SC',      # 簡體中文備用
        'WenQuanYi Micro Hei',   # Linux
        'Microsoft JhengHei',     # Windows 繁體
        'SimHei',                 # Windows 簡體
        'sans-serif'
    ]
    plt.rcParams['axes.unicode_minus'] = False


# 模組載入時自動設定字型
setup_fonts()
