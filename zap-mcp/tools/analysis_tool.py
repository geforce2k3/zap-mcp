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


import xml.etree.ElementTree as ET

def parse_nmap_with_cve(xml_content: str) -> str:
    if not xml_content:
        return "無資料"

    try:
        root = ET.fromstring(xml_content)
        summary = ["## Nmap 深度掃描報告 (含 CVE 漏洞分析)"]
        
        for host in root.findall('host'):
            # --- 1. 基礎主機資訊 ---
            address = host.find('address').get('addr')
            
            # OS 偵測 (包含先前的修正邏輯)
            os_name = "Unknown"
            os_elem = host.find('os')
            if os_elem and os_elem.find('osmatch'):
                os_name = os_elem.find('osmatch').get('name')
            
            # Service Fingerprinting (輔助 OS 判斷)
            detected_hints = []
            ports_elem = host.find('ports')
            
            # 先掃描一次服務來確認 OS (若 Nmap 未偵測到)
            if ports_elem and os_name == "Unknown":
                for port in ports_elem.findall('port'):
                    service = port.find('service')
                    if service is not None:
                        extra = service.get('extrainfo', '') + " " + service.get('product', '')
                        keywords = ['Ubuntu', 'Debian', 'CentOS', 'Windows', 'FreeBSD']
                        for kw in keywords:
                            if kw.lower() in extra.lower():
                                detected_hints.append(kw)
                if detected_hints:
                    os_name = f"Inferred: {', '.join(set(detected_hints))}"

            summary.append(f"\n### 目標: {address} (OS: {os_name})")
            
            # --- 2. 端口與 CVE 解析 ---
            if ports_elem:
                for port in ports_elem.findall('port'):
                    state = port.find('state').get('state')
                    if state != 'open':
                        continue

                    portid = port.get('portid')
                    proto = port.get('protocol')
                    
                    # 服務資訊
                    svc_elem = port.find('service')
                    svc_name = svc_elem.get('name') if svc_elem is not None else "unknown"
                    svc_ver = f"{svc_elem.get('product', '')} {svc_elem.get('version', '')}".strip()
                    
                    port_header = f"- **Port {portid}/{proto}**: {svc_name} ({svc_ver})"
                    summary.append(port_header)

                    # --- [關鍵新增] 解析 vulners script ---
                    # 尋找該端口下的 script 標籤
                    found_cves = []
                    for script in port.findall('script'):
                        if script.get('id') == 'vulners':
                            # vulners 的結構通常是巢狀 table
                            # 第一層 table 對應 CPE
                            for cpe_table in script.findall('table'):
                                # 第二層 table 對應具體漏洞
                                for vuln_table in cpe_table.findall('table'):
                                    vuln_id = ""
                                    cvss = "0.0"
                                    is_exploit = "false"
                                    
                                    for elem in vuln_table.findall('elem'):
                                        key = elem.get('key')
                                        if key == 'id':
                                            vuln_id = elem.text
                                        elif key == 'cvss':
                                            cvss = elem.text
                                        elif key == 'is_exploit':
                                            is_exploit = elem.text
                                    
                                    # 篩選條件：只顯示高風險 (CVSS >= 7.0) 或有 Exploit 的漏洞
                                    try:
                                        if float(cvss) >= 7.0 or is_exploit == 'true':
                                            found_cves.append({'id': vuln_id, 'cvss': cvss, 'exploit': is_exploit})
                                    except ValueError:
                                        pass # 忽略無法轉換分數的項目

                    # 將 CVE 排序 (分數高到低) 並加入報告
                    if found_cves:
                        # 依照 CVSS 分數排序
                        found_cves.sort(key=lambda x: float(x['cvss']), reverse=True)
                        
                        summary.append("  > **高風險漏洞偵測:**")
                        # 限制顯示數量以免洗版 (例如只顯示前 5 個最嚴重的)
                        for cve in found_cves[:5]: 
                            exploit_mark = "EXPLOIT" if cve['exploit'] == 'true' else ""
                            summary.append(f"  * [{cve['cvss']}] **{cve['id']}** {exploit_mark}")
                        
                        if len(found_cves) > 5:
                            summary.append(f"  * ... 以及其他 {len(found_cves)-5} 個漏洞")
                    else:
                        summary.append("  > 未偵測到已知的高風險 CVE。")

        return "\n".join(summary)

    except Exception as e:
        return f"解析錯誤: {e}"

def _parse_zap_json(json_data: dict) -> str:
    """
    解析 ZAP JSON 內容並轉換為 Markdown 摘要
    """
    if not json_data:
        return "ZAP 掃描結果: 無法讀取報告。\n"

    summary = ["## 應用程式弱點 (ZAP Scan Result)"]
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
            if len(desc) > 1000: # 稍微放寬限制，讓 LLM 讀多一點
                desc = desc[:1000] + "...(truncated)"

            solution = alert.get('solution', '').replace('<p>', '').replace('</p>', '\n')
            if len(solution) > 1000:
                solution = solution[:1000] + "...(truncated)"

            summary.append(f"#### [{risk}] {name}")
            summary.append(f"- **弱點描述**: {desc}")
            summary.append(f"- **修復建議**: {solution}")
            critical_count += 1

    if critical_count == 0:
        summary.append("\n 恭喜！未發現高/中風險弱點 (低風險已忽略)。")

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
        nmap_md = parse_nmap_with_cve(nmap_content)

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