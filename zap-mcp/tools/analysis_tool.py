"""
報告分析工具
"""
import os

from core.config import OUTPUT_DIR
from core.logging_config import logger
from docker_utils import DockerClient


def get_report_for_analysis() -> str:
    """
    【流程第四步】讀取關鍵弱點 (High/Medium) 供 AI 分析。(字數限制 2000)

    Returns:
        str: Markdown 格式的弱點摘要
    """
    try:
        data = DockerClient.read_json_from_volume("ZAP-Report.json")
        if data is None:
            return "無法讀取報告。"

        sites = data.get('site', [])

        report_context = ["# ZAP 關鍵風險摘要 (High/Medium Only)\n"]
        critical_count = 0

        for site in sites:
            target_host = site.get('@name', 'Unknown')
            alerts = site.get('alerts', [])

            # 只取 High/Medium
            critical_alerts = [a for a in alerts if a.get('riskcode') in ['2', '3']]

            if not critical_alerts:
                continue

            report_context.append(f"\n## {target_host}")

            for alert in critical_alerts:
                name = alert.get('alert', 'Unknown')
                risk = alert.get('riskdesc', 'Info').split(' ')[0]

                # 清理 HTML 並限制長度
                desc = alert.get('desc', '').replace('<p>', '').replace('</p>', '\n')
                if len(desc) > 2000:
                    desc = desc[:2000] + "...(truncated)"

                sol = alert.get('solution', '').replace('<p>', '').replace('</p>', '\n')
                if len(sol) > 2000:
                    sol = sol[:2000] + "...(truncated)"

                report_context.append(f"- [{risk}] {name}")
                report_context.append(f"  - 狀況: {desc}")
                report_context.append(f"  - 建議: {sol}")
                critical_count += 1

        final_report = "\n".join(report_context)

        # 嘗試儲存到輸出目錄
        try:
            output_path = os.path.join(OUTPUT_DIR, "zap_analysis.md")
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(final_report)
        except Exception:
            pass

        if critical_count == 0:
            return "恭喜！未發現高/中風險弱點 (低風險已忽略)。"

        return final_report + "\n\n(已顯示 High/Medium 風險)"

    except Exception as e:
        logger.error(f"分析錯誤: {e}")
        return f"分析錯誤: {str(e)}"
