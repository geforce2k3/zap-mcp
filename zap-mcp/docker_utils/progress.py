"""
ZAP 掃描進度解析模組
"""
from .client import DockerClient
from core.config import SCAN_CONTAINER_NAME


def parse_zap_progress(container_name: str = SCAN_CONTAINER_NAME) -> str:
    """
    解析 ZAP 掃描進度

    Args:
        container_name: 容器名稱

    Returns:
        str: 當前掃描階段描述
    """
    try:
        logs = DockerClient.get_container_logs(container_name, tail=20)

        if "Active Scan" in logs:
            return "正在進行主動攻擊掃描 (Active Scanning)..."
        elif "Spider" in logs:
            return "正在進行爬蟲探索 (Spidering)..."
        elif "Passive Scan" in logs:
            return "正在進行被動掃描 (Passive Scanning)..."
        else:
            return "初始化或處理中..."
    except Exception:
        return "無法取得進度"
