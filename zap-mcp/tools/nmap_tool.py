"""
Nmap 偵察工具 (Async / Non-blocking 版)
解決 MCP Timeout 問題，支援背景執行與狀態檢查
"""
import os
import subprocess
import xml.etree.ElementTree as ET
from typing import Optional

from core.config import INTERNAL_DATA_DIR
from core.logging_config import logger
from validators import is_safe_host

# 定義輸出檔案路徑
NMAP_XML_OUTPUT = os.path.join(INTERNAL_DATA_DIR, "nmap_result.xml")
NMAP_LOG_FILE = os.path.join(INTERNAL_DATA_DIR, "nmap_run.log")


def is_nmap_running() -> bool:
    """
    檢查 Nmap 是否正在背景執行
    
    Returns:
        bool: True 表示正在執行
    """
    try:
        # 使用 pgrep 檢查是否有 nmap 程序正在執行
        result = subprocess.run(["pgrep", "-x", "nmap"], capture_output=True)
        return result.returncode == 0
    except Exception:
        return False


def _parse_nmap_results() -> str:
    """
    解析 Nmap XML 輸出檔案並回傳摘要
    
    Returns:
        str: 發現的 Web 服務列表
    """
    try:
        if not os.path.exists(NMAP_XML_OUTPUT):
            return "尚未產生掃描結果 (檔案不存在)。"

        # 解析 XML
        tree = ET.parse(NMAP_XML_OUTPUT)
        root = tree.getroot()
        
        discovered_urls = []
        raw_services = []

        for host in root.findall('host'):
            # 嘗試取得 Hostname 或 IP
            hostnames = host.find('hostnames')
            hostname = None
            if hostnames:
                for hn in hostnames.findall('hostname'):
                    hostname = hn.get('name')
                    break
            
            # 若無 hostname 則使用 IP
            if not hostname:
                address = host.find('address')
                if address is not None:
                    hostname = address.get('addr')

            if not hostname:
                continue

            ports_elem = host.find('ports')
            if ports_elem:
                for port in ports_elem.findall('port'):
                    port_id = port.get('portid')
                    service = port.find('service')
                    service_name = service.get('name') if service is not None else "unknown"
                    
                    # 記錄原始服務以便除錯
                    raw_services.append(f"Port {port_id}: {service_name}")

                    # 判斷是否為 Web 服務 (HTTP/HTTPS)
                    protocol = "http"
                    if "https" in service_name or "ssl" in service_name:
                        protocol = "https"
                    elif service_name not in ["http", "http-alt", "http-proxy", "soap", "glrpc", "unknown"]:
                        # 跳過明顯非 Web 的服務 (如 ssh, ftp, smtp)
                        continue

                    # 針對 443 強制 https, 80 強制 http
                    if port_id == "443":
                        protocol = "https"
                    elif port_id == "80":
                        protocol = "http"

                    # 組合 URL
                    url = f"{protocol}://{hostname}:{port_id}"
                    
                    # 對於標準端口，移除端口號讓 URL 更乾淨
                    if (protocol == "http" and port_id == "80") or \
                       (protocol == "https" and port_id == "443"):
                        url = f"{protocol}://{hostname}"
                        
                    discovered_urls.append(url)

        if not discovered_urls:
            return f"Nmap 掃描完成。\n開放端口: {', '.join(raw_services)}\n  未發現明顯的 HTTP/HTTPS 服務。"

        url_list = '\n'.join(['- ' + url for url in discovered_urls])
        return f"**偵察完成！發現 Web 服務**：\n{url_list}"

    except Exception as e:
        logger.error(f"解析 Nmap XML 失敗: {e}")
        return f"解析結果失敗: {str(e)}"


def run_nmap_recon(target_host: str, ports: str = "top-1000", force_rescan: bool = False) -> str:
    """
    【流程第一步】啟動 Nmap 背景掃描。
    
    此函式為非阻塞式 (Non-blocking)，會立即回傳狀態，避免 MCP Client 超時。

    Args:
        target_host: 目標主機 (IP 或域名)
        ports: 掃描埠號範圍
        force_rescan: 若已有結果，是否強制重新掃描

    Returns:
        str: 啟動訊息或掃描結果
    """
    if not is_safe_host(target_host):
        return "錯誤：目標主機包含非法字元。"

    # 1. 檢查是否正在執行 (避免重複啟動)
    if is_nmap_running():
        return f"""
**Nmap 掃描正在背景進行中...**
目標: {target_host}

請 **等待約 30-60 秒**，然後使用 `check_status` 查看結果。
(請勿重複執行此指令)
"""

    # 2. 檢查是否已有結果 (且使用者未要求強制重掃)
    # 這能節省大量的時間
    if not force_rescan and os.path.exists(NMAP_XML_OUTPUT):
        # 簡單檢查檔案大小，確保不是空檔
        if os.path.getsize(NMAP_XML_OUTPUT) > 100:
            logger.info("發現現有的 Nmap 結果，直接回傳。")
            return f"**發現已存在的掃描結果** (若需重掃請指定 force_rescan=True)：\n\n{_parse_nmap_results()}"

    # 3. 啟動背景掃描
    logger.info(f"啟動 Nmap 背景偵察: Target={target_host}, Ports={ports}")
    
    # 建立 Nmap 指令
    # -T4: 加速掃描
    # -oN: 輸出文字 Log (方便除錯)
    # -oX: 輸出 XML (給程式解析)
    nmap_cmd = [
        "nmap", "-sV", "-sC", "--script=vulners", "-O", "--open", "-T4",
        "-oX", NMAP_XML_OUTPUT,
        "-oN", NMAP_LOG_FILE,
        target_host
    ]
    
    # 處理端口參數
    if ports != "top-1000":
        if ports == "p-":
            nmap_cmd.insert(1, "-p-") # 全端口掃描
        else:
            nmap_cmd.insert(1, ports)
            nmap_cmd.insert(1, "-p")

    try:
        # [關鍵修改] 使用 Popen 取代 run，實現非阻塞執行
        # stdout/stderr 導向到檔案，避免 Buffer 塞滿導致卡住
        with open(NMAP_LOG_FILE, "w") as log_f:
            subprocess.Popen(
                nmap_cmd,
                stdout=log_f,
                stderr=subprocess.STDOUT,
                # start_new_session=True # 如果是在 Linux 環境可考慮加入，但在 Docker 內通常不需要
            )
            
        return f"""
**Nmap 偵察已在背景啟動！**
目標: {target_host}
掃描範圍: {ports}

**請注意**：
由於 Nmap 掃描需要時間 (視端口數量而定，約 1~5 分鐘)，
MCP 不會在此等待結果。

請 **等待約 30 秒** 後，使用 `check_status` 工具來確認掃描是否完成並查看結果。
"""

    except Exception as e:
        logger.error(f"Nmap 啟動失敗: {e}")
        return f"Nmap 啟動失敗: {str(e)}"