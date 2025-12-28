"""
自動登入工具
"""
import requests

from core.logging_config import logger


def perform_login_and_get_cookie(
    login_url: str,
    username: str,
    password: str,
    username_field: str = "username",
    password_field: str = "password",
    submit_url: str = None
) -> str:
    """
    【輔助工具】執行自動登入並取得 Cookie。

    Args:
        login_url: 登入頁面 URL
        username: 使用者名稱
        password: 密碼
        username_field: 使用者名稱欄位名稱 (預設: username)
        password_field: 密碼欄位名稱 (預設: password)
        submit_url: 表單提交 URL (若與登入頁不同)

    Returns:
        str: Cookie 字串或錯誤訊息
    """
    logger.info(f"執行自動登入: {login_url} User={username}")

    try:
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) ZAP-MCP/1.0'
        })

        # 先存取登入頁面
        resp = session.get(login_url, timeout=10)
        if resp.status_code != 200:
            return f"無法存取頁面 (Status: {resp.status_code})"

        # 提交登入表單
        payload = {username_field: username, password_field: password}
        target = submit_url if submit_url else login_url

        post_resp = session.post(target, data=payload, timeout=10)
        if post_resp.status_code not in [200, 302, 303]:
            return f"登入異常 (Status: {post_resp.status_code})"

        # 取得 Cookie
        cookies = session.cookies.get_dict()
        if not cookies:
            return "登入後未發現 Cookie。"

        cookie_str = "; ".join([f"{k}={v}" for k, v in cookies.items()])
        return f"**登入成功！** Cookie: `{cookie_str}`"

    except requests.exceptions.Timeout:
        return "登入逾時，請確認網站可存取。"
    except requests.exceptions.RequestException as e:
        logger.error(f"登入錯誤: {e}")
        return f"登入錯誤: {str(e)}"
