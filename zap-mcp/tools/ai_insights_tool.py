"""
AI 建議注入工具
"""
import os
import json

from core.config import INTERNAL_DATA_DIR
from core.logging_config import logger
from docker_utils import DockerClient


def generate_report_with_ai_insights(executive_summary: str, solutions: str) -> str:
    """
    【流程第五步】將 AI 建議注入並生成最終 Word 報告。

    Args:
        executive_summary: AI 生成的執行摘要
        solutions: JSON 格式的解決方案 (弱點名稱 -> 建議)

    Returns:
        str: 生成結果訊息
    """
    try:
        # 驗證 solutions JSON 格式
        try:
            solutions_dict = json.loads(solutions)
        except json.JSONDecodeError:
            return "錯誤：solutions 參數必須是有效的 JSON 字串。"

        # 組合 AI 資料
        ai_data = {
            "executive_summary": executive_summary,
            "solutions": solutions_dict
        }

        # 儲存到共用 Volume
        local_ai_path = os.path.join(INTERNAL_DATA_DIR, "ai_insights.json")
        with open(local_ai_path, "w", encoding="utf-8") as f:
            json.dump(ai_data, f, ensure_ascii=False, indent=2)

        logger.info("啟動 Reporter 生成最終報告...")

        # 執行報告生成器
        success, message = DockerClient.run_reporter()
        if not success:
            return f"生成報告錯誤: {message}"

        solution_count = len(solutions_dict) if isinstance(solutions_dict, dict) else len(solutions_dict)
        return f"**AI 智慧報告已生成！**\n已注入 {solution_count} 個建議。"

    except Exception as e:
        logger.error(f"生成報告錯誤: {e}")
        return f"生成報告錯誤: {str(e)}"
