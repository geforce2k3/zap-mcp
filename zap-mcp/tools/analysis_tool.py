"""
報告分析工具 (整合 Nmap + ZAP)
"""
import os
import json
import xml.etree.ElementTree as ET
from typing import Optional

from core.config import OUTPUT_DIR
from core.logging_config import logger
from docker_utils import DockerClient


def _parse_nmap_xml(xml_content: str) -> str:
    """
    解析 Nmap XML 內容並轉換為 Markdown 摘要
    """
    if not xml_content:
        return "Nmap 掃描結果: 無資料或無法讀取。\n"

    try:
        root = ET.fromstring(xml_content)
        summary = ["## 🔍 基礎設施偵察 (Nmap Result)"]
        
        hosts_found = False
        
        for host in root.findall('host'):
            hosts_found = True
            # 取得 IP 或 Hostname
            address = host.find('address').get('addr')
            hostnames = host.find('hostnames')
            hostname_str = ""
            if hostnames:
                for hn in hostnames.findall('hostname'):
                    hostname_str = f" ({hn.get('name')})"
                    break
            
            summary.append(f"\n### 目標主機: {address}{hostname_str}")
            
            # 取得 OS 資訊 (如果有)
            os_elem = host.find('os')
            if os_elem and os_elem.find('osmatch'):
                os_name = os_elem.find('osmatch').get('name')
                summary.append(f"- **作業系統**: {os_name}")

            # 取得開放端口與服務
            ports_elem = host.find('ports')
            if ports_elem:
                open_ports = []
                for port in ports_elem.findall('port'):
                    state = port.find('state').get('state')
                    if state == 'open':
                        portid = port.get('portid')
                        protocol = port.get('protocol')
                        
                        service = port.find('service')
                        svc_name = service.get('name') if service is not None else "unknown"
                        svc_product = service.get('product') if service is not None else ""
                        svc_version = service.get('version') if service is not None else ""
                        
                        svc_info = f"{svc_product} {svc_version}".strip()
                        if not svc_info: 
                            svc_info = "Unknown Version"

                        open_ports.append(f"- **Port {portid}/{protocol}**: {svc_name.upper()} - {svc_info}")
                
                if open_ports:
                    summary.append("**開放端口與服務:**")
                    summary.extend(open_ports)
                else:
                    summary.append("- 未發現開放端口")

        if not hosts_found:
            return "Nmap 掃描結果: 未發現存活主機。\n"

        return "\n".join(summary) + "\n\n---\n"

    except Exception as e:
        logger.error(f"Nmap XML 解析失敗: {e}")
        return f"⚠️ Nmap 報告解析失敗: {str(e)}\n"


def _parse_zap_json(json_data: dict) -> str:
    """
    解析 ZAP JSON 內容並轉換為 Markdown 摘要
    """
    if not json_data:
        return "ZAP 掃描結果: 無法讀取報告。\n"

    summary = ["## 🛡️ 應用程式弱點 (ZAP Scan Result)"]
    sites = json_data.get('site', [])
    critical_count = 0

    for site in sites:
        target_host = site.get('@name', 'Unknown')
        alerts = site.get('alerts', [])

        # 只取 High(3) 和 Medium(2)
        critical_alerts = [a for a in alerts if a.get('riskcode') in ['2', '3']]

        if not critical_alerts:
            continue

        summary.append(f"\n### 應用程式目標: {target_host}")

        for alert in critical_alerts:
            name = alert.get('alert', 'Unknown')
            risk = alert.get('riskdesc', 'Info').split(' ')[0] # 取出 High/Medium

            # 清理 HTML 並限制長度 (避免 Token 爆炸)
            desc = alert.get('desc', '').replace('<p>', '').replace('</p>', '\n')
            if len(desc) > 800: # 稍微放寬限制，讓 LLM 讀多一點
                desc = desc[:800] + "...(truncated)"

            solution = alert.get('solution', '').replace('<p>', '').replace('</p>', '\n')
            if len(solution) > 800:
                solution = solution[:800] + "...(truncated)"

            summary.append(f"#### [{risk}] {name}")
            summary.append(f"- **弱點描述**: {desc}")
            summary.append(f"- **修復建議**: {solution}")
            critical_count += 1

    if critical_count == 0:
        summary.append("\n✅ 恭喜！未發現高/中風險弱點 (低風險已忽略)。")

    return "\n".join(summary)


def get_report_for_analysis() -> str:
    """
    【流程第四步】整合 Nmap 與 ZAP 報告，提供給 AI 進行深度分析。

    Returns:
        str: 整合後的 Markdown 報告
    """
    try:
        # 1. 讀取並解析 Nmap 報告
        # 注意：我們使用 read_file_from_volume (讀取純文字/XML)，不是 read_json
        nmap_content = DockerClient.read_file_from_volume("nmap_result.xml")
        nmap_md = _parse_nmap_xml(nmap_content)

        # 2. 讀取並解析 ZAP 報告
        zap_data = DockerClient.read_json_from_volume("ZAP-Report.json")
        zap_md = _parse_zap_json(zap_data)

        # 3. 組合最終報告
        final_report = f"""# 綜合資安評估報告數據 (Integrated Security Assessment Data)

請根據以下提供的 Nmap (基礎設施層) 與 ZAP (應用層) 掃描數據，進行深度的關聯分析。

{nmap_md}
{zap_md}

(此報告由 ZAP-MCP 自動生成，僅包含關鍵資訊以節省 Token)
"""

        # 備份 Markdown 到輸出目錄 (方便 Debug)
        try:
            output_path = os.path.join(OUTPUT_DIR, "integrated_analysis.md")
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(final_report)
        except Exception:
            pass

        return final_report

    except Exception as e:
        logger.error(f"整合分析錯誤: {e}")
        return f"整合分析錯誤: {str(e)}"