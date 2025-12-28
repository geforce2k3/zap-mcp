"""
Nmap 偵察工具
"""
import os
import subprocess
import xml.etree.ElementTree as ET

from core.config import INTERNAL_DATA_DIR
from core.logging_config import logger
from validators import is_safe_host


def run_nmap_recon(target_host: str, ports: str = "top-1000") -> str:
    """
    【流程第一步】執行 Nmap 埠口掃描，自動識別 Web 服務。

    Args:
        target_host: 目標主機 (IP 或域名)
        ports: 掃描埠號範圍 (預設: top-1000, 可用 "p-" 掃全部)

    Returns:
        str: 掃描結果摘要
    """
    if not is_safe_host(target_host):
        return "錯誤：目標主機包含非法字元。"

    logger.info(f"啟動 Nmap 偵察: Target={target_host}, Ports={ports}")
    nmap_xml_output = os.path.join(INTERNAL_DATA_DIR, "nmap_result.xml")

    # 組建 Nmap 命令
    nmap_cmd = ["nmap", "-sV", "--open", "-oX", nmap_xml_output, target_host]
    if ports != "top-1000":
        if ports == "p-":
            nmap_cmd.append("-p-")
        else:
            nmap_cmd.extend(["-p", ports])

    try:
        subprocess.run(nmap_cmd, check=True, capture_output=True, text=True)

        # 解析 XML 結果
        tree = ET.parse(nmap_xml_output)
        root = tree.getroot()

        discovered_urls = []
        raw_services = []

        for host in root.findall('host'):
            ports_elem = host.find('ports')
            if ports_elem:
                for port in ports_elem.findall('port'):
                    port_id = port.get('portid')
                    service = port.find('service')
                    service_name = service.get('name') if service is not None else "unknown"
                    raw_services.append(f"Port {port_id}: {service_name}")

                    # 判斷協議
                    protocol = "http"
                    if "https" in service_name or "ssl" in service_name:
                        protocol = "https"
                    elif service_name not in ["http", "http-alt", "http-proxy", "soap"]:
                        continue

                    # 組建 URL
                    url = f"{protocol}://{target_host}:{port_id}"
                    if (protocol == "http" and port_id == "80") or \
                       (protocol == "https" and port_id == "443"):
                        url = f"{protocol}://{target_host}"
                    discovered_urls.append(url)

        if not discovered_urls:
            return f"Nmap 完成。開放端口: {', '.join(raw_services)}\n未發現明顯 Web 服務。"

        url_list = '\n'.join(['- ' + url for url in discovered_urls])
        return f"**偵察完成！發現 Web 服務**：\n{url_list}"

    except Exception as e:
        logger.error(f"Nmap 執行失敗: {e}")
        return f"Nmap 執行失敗: {str(e)}"
