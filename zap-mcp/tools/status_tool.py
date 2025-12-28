"""
掃描狀態檢查工具
"""
from core.config import SCAN_CONTAINER_NAME
from core.logging_config import logger
from docker_utils import DockerClient, parse_zap_progress


def check_status_and_generate_report() -> str:
    """
    【流程第三步】檢查進度。若掃描中會提示等待；完成後自動產生 Word 報告。

    Returns:
        str: 狀態訊息或報告摘要
    """
    # 檢查掃描容器狀態
    if DockerClient.is_container_running(SCAN_CONTAINER_NAME):
        progress = parse_zap_progress(SCAN_CONTAINER_NAME)
        return f"""
**掃描進行中** (Status: Running)
目前階段: {progress}

**SYSTEM NOTE:** 請 **等待 30 秒** 後再檢查狀態，不要立即重試。
"""

    logger.info("掃描結束，轉換報告中...")

    # 執行報告生成器
    success, message = DockerClient.run_reporter()
    if not success:
        return f"報告生成失敗: {message}"

    # 讀取報告摘要
    data = DockerClient.read_json_from_volume("ZAP-Report.json")
    if data is None:
        return "錯誤：找不到報告檔案，掃描可能失敗。"

    # 統計風險數量
    try:
        sites = data.get('site', [])
        high = sum(1 for s in sites for a in s.get('alerts', []) if a.get('riskcode') == '3')
        med = sum(1 for s in sites for a in s.get('alerts', []) if a.get('riskcode') == '2')
        summary = f"高風險: {high} | 中風險: {med}"
    except Exception:
        summary = "無法讀取統計"

    return f"""**掃描與報告生成完成！**
{summary}
請接著使用 `get_report_for_analysis` 進行分析。"""
