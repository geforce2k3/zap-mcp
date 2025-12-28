"""
AI 建議注入工具 (Async Fix)
"""
import os
import json

from core.config import INTERNAL_DATA_DIR
from core.logging_config import logger
from docker_utils import DockerClient


def generate_report_with_ai_insights(executive_summary: str, solutions: str) -> str:
    """
    【流程第五步】將 AI 建議注入並啟動報告生成 (背景執行)。

    Args:
        executive_summary: AI 生成的執行摘要
        solutions: JSON 格式的解決方案 (弱點名稱 -> 建議)

    Returns:
        str: 啟動結果訊息
    """
    try:
        # 1. 驗證與解析 JSON
        try:
            solutions_dict = json.loads(solutions)
        except json.JSONDecodeError:
            return "錯誤：solutions 參數必須是有效的 JSON 字串。"

        # 2. 儲存 AI 資料到 Volume
        ai_data = {
            "executive_summary": executive_summary,
            "solutions": solutions_dict
        }

        local_ai_path = os.path.join(INTERNAL_DATA_DIR, "ai_insights.json")
        with open(local_ai_path, "w", encoding="utf-8") as f:
            json.dump(ai_data, f, ensure_ascii=False, indent=2)

        logger.info("AI 數據已儲存，背景啟動 Reporter...")

        # 3. [Fix] 改用 run_reporter_detached (背景執行)，避免 MCP 超時
        success, message = DockerClient.run_reporter_detached()
        
        if not success:
            return f"啟動報告生成失敗: {message}"

        solution_count = len(solutions_dict) if isinstance(solutions_dict, dict) else len(solutions_dict)
        
        return f"""
**AI 智慧報告生成任務已啟動！**
已注入 {solution_count} 個建議。

**SYSTEM NOTE:** 報告生成正在背景進行中。
請 **等待約 10-20 秒**，然後使用 `check_status` 確認是否完成。
(完成後即可執行 `retrieve_report` 下載)
"""

    except Exception as e:
        logger.error(f"工具執行錯誤: {e}")
        return f"工具執行錯誤: {str(e)}"