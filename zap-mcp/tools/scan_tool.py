"""
ZAP 掃描啟動工具
"""
from typing import Optional, List

from core.config import SCAN_CONTAINER_NAME
from core.logging_config import logger
from validators import is_safe_url
from docker_utils import DockerClient


def _build_auth_config(auth_header: str, auth_value: str) -> List[str]:
    """建立認證配置"""
    return [
        "-config", "replacer.full_list(0).description=MCP_Auth",
        "-config", "replacer.full_list(0).enabled=true",
        "-config", "replacer.full_list(0).matchtype=REQ_HEADER",
        "-config", f"replacer.full_list(0).matchstr={auth_header}",
        "-config", "replacer.full_list(0).regex=false",
        "-config", f"replacer.full_list(0).replacement={auth_value}"
    ]


def _build_aggressive_config(scan_type: str) -> List[str]:
    """建立積極掃描配置"""
    configs = []
    configs.extend([
        "-config", "scanner.threadPerHost=20", # 增加執行緒 (加速但高負載)
        "-config", "spider.thread=10"
    ])
    if scan_type == "full":
        configs.extend([
            "-config", "scanner.strength=HIGH",
            "-config", "scanner.threadPerHost=10",
            "-config", "scanner.alertThreshold=LOW",
            "-config", "rules.sqli.level=HIGH",  # 測試 SQL Injection
            "-config", "rules.xss.level=HIGH",   # 測試 XSS
            "-config", "rules.pathtraversal.level=HIGH" # 測試路徑遍歷
        ])
    return configs


def start_scan_job(
    target_url: str,
    scan_type: str = "baseline",
    aggressive: bool = False,
    auth_header: Optional[str] = None,
    auth_value: Optional[str] = None
) -> str:
    """
    【流程第二步】啟動 ZAP 弱點掃描任務。

    Args:
        target_url: 目標 URL
        scan_type: 掃描類型 (baseline: 被動掃描 / full: 完整掃描)
        aggressive: 是否使用積極模式
        auth_header: 認證標頭名稱 (如 Authorization)
        auth_value: 認證標頭值 (如 Bearer token)

    Returns:
        str: 啟動結果訊息
    """
    if not is_safe_url(target_url):
        return "錯誤：網址格式不合法。"

    logger.info(f"啟動掃描: URL={target_url}, Type={scan_type}, Auth={bool(auth_value)}")

    # 清理舊容器
    DockerClient.remove_container(SCAN_CONTAINER_NAME)

    # 組建配置
    zap_configs = []
    mode_desc = []

    # 認證配置
    if auth_header and auth_value:
        zap_configs.extend(_build_auth_config(auth_header, auth_value))
        mode_desc.append("Authenticated")

    # 積極模式
    if aggressive:
        mode_desc.append("Aggressive")
        zap_configs.extend(_build_aggressive_config(scan_type))

    # 執行掃描
    success, message = DockerClient.run_zap_scan(
        target_url=target_url,
        scan_type=scan_type,
        aggressive=aggressive,
        zap_configs=zap_configs if zap_configs else None
    )

    if not success:
        return message

    # 組建模式描述
    mode_text = " / ".join(mode_desc) if mode_desc else "Standard"

    return f"""
**掃描任務已啟動！**
* **目標**: {target_url}
* **模式**: {mode_text}
* **驗證**: {'已啟用' if auth_header else '無'}

**重要**: 掃描在背景執行，離開對話不會中斷。請稍後使用 `check_status` 查詢。
"""
