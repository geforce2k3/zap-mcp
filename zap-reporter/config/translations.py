"""
翻譯對照表
"""

# 風險等級對照表
RISK_MAPPING = {
    "High": "高風險 (High)",
    "Medium": "中風險 (Medium)",
    "Low": "低風險 (Low)",
    "Informational": "資訊 (Info)",
    "False Positive": "誤報 (False Positive)"
}

# 弱點名稱對照表 (英文 -> 繁體中文)
TERM_MAPPING = {
    # XSS 相關
    "Cross Site Scripting (Reflected)": "反射型跨站腳本攻擊 (XSS)",
    "Cross Site Scripting (Persistent)": "儲存型跨站腳本攻擊 (XSS)",
    "Cross Site Scripting (DOM Based)": "DOM 型跨站腳本攻擊 (XSS)",

    # 注入攻擊
    "SQL Injection": "SQL 資料隱碼攻擊",
    "Path Traversal": "路徑遍歷漏洞",
    "Remote File Inclusion": "遠端檔案包含 (RFI)",
    "Server Side Include": "伺服器端包含注入 (SSI)",
    "Buffer Overflow": "緩衝區溢位",
    "Format String Error": "格式化字串錯誤",

    # CSRF
    "Cross-Site Request Forgery": "跨站請求偽造 (CSRF)",
    "Absence of Anti-CSRF Tokens": "缺乏 Anti-CSRF Token",

    # 目錄相關
    "Directory Browsing": "目錄遍歷/目錄瀏覽",

    # 資訊洩漏
    "Information Disclosure - Debug Error Messages": "資訊洩漏 - 偵錯錯誤訊息",
    "Information Disclosure - Sensitive Information in URL": "資訊洩漏 - URL 包含敏感資訊",
    "Information Disclosure - Suspicious Comments": "資訊洩漏 - 可疑的程式註解",
    "Application Error Disclosure": "應用程式錯誤資訊揭露",
    "Private IP Disclosure": "內部 IP 位址洩漏",
    "Source Code Disclosure": "原始碼洩漏",

    # 認證相關
    "Weak Authentication Method": "身分驗證機制薄弱",
    "Session ID in URL Rewrite": "Session ID 暴露於 URL",

    # HTTP 標頭
    "Missing Anti-clickjacking Header": "遺失防點擊劫持標頭 (Clickjacking)",
    "X-Frame-Options Header Not Set": "未設定 X-Frame-Options 標頭",
    "X-Content-Type-Options Header Missing": "遺失 X-Content-Type-Options 標頭",
    "Strict-Transport-Security Header Not Set": "未設定 HSTS 安全傳輸標頭",

    # Cookie 相關
    "Cookie No HttpOnly Flag": "Cookie 遺失 HttpOnly 屬性",
    "Cookie Without Secure Flag": "Cookie 遺失 Secure 屬性",

    # 雲端服務
    "AWS Identity and Access Management (IAM)": "AWS 身分與存取管理",
    "Amazon S3 (Simple Storage Service)": "Amazon S3 物件儲存服務",
    "CloudTrail": "AWS 操作紀錄稽核服務",
    "Cloud IAM": "Google Cloud 身分與存取管理",
}


def translate_title(english_title: str) -> str:
    """
    翻譯弱點名稱

    Args:
        english_title: 英文弱點名稱

    Returns:
        str: 對應的中文名稱，若無對應則回傳原文
    """
    return TERM_MAPPING.get(english_title, english_title)
