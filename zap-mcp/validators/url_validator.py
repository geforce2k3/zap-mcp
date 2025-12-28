"""
URL 和主機安全驗證模組
"""
import re

# 危險字元清單
DANGEROUS_CHARS = [';', '|', '`', '$', '(', ')', '<', '>', '\\', '{', '}']


def is_safe_url(url: str) -> bool:
    """
    驗證 URL 是否安全，防止命令注入攻擊

    Args:
        url: 待驗證的 URL 字串

    Returns:
        bool: URL 是否安全
    """
    if not url:
        return False

    # 檢查危險字元
    if any(char in url for char in DANGEROUS_CHARS):
        return False

    # URL 格式正則表達式
    regex = re.compile(
        r'^(https?://)'  # http:// 或 https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # 域名
        r'localhost|'  # localhost
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # IP 位址
        r'(?::\d+)?'  # 可選埠號
        r'(?:/?|[/?][a-zA-Z0-9-._~:/?#\[\]@!$&\'()*+,;=%]*)$',  # 路徑
        re.IGNORECASE
    )
    return re.match(regex, url) is not None


def is_safe_host(host: str) -> bool:
    """
    驗證主機名稱是否安全

    Args:
        host: 待驗證的主機名稱

    Returns:
        bool: 主機名稱是否安全
    """
    if not host:
        return False

    # 檢查命令注入字元
    if any(char in host for char in DANGEROUS_CHARS):
        return False

    return True
