"""
掃描狀態檢查工具 (Async Fix)
"""
from core.config import SCAN_CONTAINER_NAME
from core.logging_config import logger
from docker_utils import DockerClient, parse_zap_progress

REPORTER_CONTAINER_NAME = "zap-reporter-job"

def check_status_and_generate_report() -> str:
    """
    【流程第三步】檢查進度與報告狀態。
    全異步設計，避免 MCP Timeout。
    """
    # 1. 檢查 ZAP 掃描器狀態
    if DockerClient.is_container_running(SCAN_CONTAINER_NAME):
        progress = parse_zap_progress(SCAN_CONTAINER_NAME)
        return f"""
**掃描進行中** (Status: Scanning)
目前階段: {progress}

請等待 30 秒後再檢查。
"""

    # 2. 檢查報告生成器狀態
    if DockerClient.is_container_running(REPORTER_CONTAINER_NAME):
        return """
⚙**報告生成中** (Status: Generating Report)
正在進行 AI 分析、翻譯與圖表繪製...

請等待 10 秒後再檢查。
"""

    # 3. 檢查最終報告是否已產生 (檢查是否有名為 Scan_Report_*.docx 的檔案)
    if DockerClient.check_file_exists("Scan_Report_*.docx"):
        # 讀取摘要數據
        data = DockerClient.read_json_from_volume("ZAP-Report.json")
        summary = "無法讀取統計"
        if data:
            try:
                sites = data.get('site', [])
                high = sum(1 for s in sites for a in s.get('alerts', []) if a.get('riskcode') == '3')
                med = sum(1 for s in sites for a in s.get('alerts', []) if a.get('riskcode') == '2')
                summary = f"🔴 高風險: {high} | 🟠 中風險: {med}"
            except: pass
            
        return f"""
**任務全部完成！**
{summary}

**報告已準備就緒**
請務必執行 `export_report` 指令將檔案下載到您的電腦。
"""

    # 4. 掃描結束但報告未產生 -> 啟動報告生成器 (背景執行)
    if DockerClient.check_file_exists("ZAP-Report.json"):
        success, msg = DockerClient.run_reporter_detached()
        if success:
            return "**掃描已完成，正在啟動報告生成器...**\n請在 10 秒後再次檢查狀態。"
        else:
            return f"啟動報告生成失敗: {msg}"

    return "錯誤：找不到 ZAP 報告檔案，掃描可能失敗或尚未開始。"