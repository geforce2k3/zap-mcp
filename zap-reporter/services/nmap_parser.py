import xml.etree.ElementTree as ET
import logging
from typing import List, Dict, Any

# 設定 Logger
logger = logging.getLogger(__name__)

class NmapParser:
    """
    負責解析 Nmap 輸出的 XML 檔案
    具備容錯機制，並支援解析 vulners script 產生的 CVE 資訊
    """

    @staticmethod
    def parse(xml_content: str) -> List[Dict[str, Any]]:
        """
        解析 Nmap XML 字串並返回結構化的主機列表
        如果 XML 破損或不完整，將返回空列表並記錄警告，不會導致程式崩潰。
        """
        if not xml_content:
            logger.warning("Nmap XML content is empty.")
            return []

        try:
            # 嘗試解析 XML
            root = ET.fromstring(xml_content)
            
            hosts_data = []
            for host in root.findall('host'):
                status = host.find('status')
                # 確保主機是 UP 的狀態
                if status is not None and status.get('state') == 'up':
                    host_info = NmapParser._extract_host_info(host)
                    hosts_data.append(host_info)
            
            if not hosts_data:
                logger.info("Nmap scan completed but no 'up' hosts found.")
                
            return hosts_data

        except ET.ParseError as e:
            logger.warning(f"Nmap XML is incomplete or malformed (Scan might have been interrupted). Error: {e}")
            logger.warning("Returning empty host list to ensure report generation continues.")
            return [] 
        except Exception as e:
            logger.error(f"Unexpected error during Nmap parsing: {e}")
            return []

    @staticmethod
    def _extract_host_info(host: ET.Element) -> Dict[str, Any]:
        """
        從單一 host 節點提取 IP, Hostname, Port 以及 CVE 資訊
        """
        try:
            # 1. 取得 IP 地址
            address = host.find("address[@addrtype='ipv4']")
            ip = address.get('addr') if address is not None else "Unknown"

            # 2. 取得 Hostname
            hostnames = host.find('hostnames')
            hostname = "Unknown"
            if hostnames is not None:
                hn = hostnames.find('hostname')
                if hn is not None:
                    hostname = hn.get('name')

            # 3. 取得 Port 與 CVE 資訊
            ports_data = []
            ports = host.find('ports')
            if ports is not None:
                for port in ports.findall('port'):
                    state = port.find('state')
                    if state is not None and state.get('state') == 'open':
                        service = port.find('service')
                        service_name = service.get('name') if service is not None else "unknown"
                        product = service.get('product') if service is not None else ""
                        version = service.get('version') if service is not None else ""
                        
                        # --- 新增：提取 CVE 資訊 ---
                        cves = NmapParser._extract_cves(port)
                        
                        ports_data.append({
                            "port": port.get('portid'),
                            "protocol": port.get('protocol'),
                            "service": service_name,
                            "product": f"{product} {version}".strip(),
                            "cves": cves  # 將 CVE 列表加入結果
                        })

            return {
                "ip": ip,
                "hostname": hostname,
                "ports": ports_data
            }
        except Exception as e:
            logger.error(f"Error extracting info for host: {e}")
            return {
                "ip": "Error",
                "hostname": "Error",
                "ports": []
            }

    @staticmethod
    def _extract_cves(port: ET.Element) -> List[Dict[str, Any]]:
        """
        從 Port 節點下的 script 標籤提取 CVE 資訊
        針對 Nmap '--script=vulners' 的輸出格式進行解析
        """
        cves = []
        try:
            # 尋找所有的 script 標籤
            for script in port.findall('script'):
                # 鎖定 id="vulners" 的 script
                if script.get('id') == 'vulners':
                    # vulners 的輸出通常包含在 table 中
                    for table in script.findall('table'):
                        # 內層 table 通常代表單一漏洞條目
                        for row in table.findall('table'):
                            cve_id = ""
                            cvss = "0.0"
                            is_exploit = "false"

                            # 解析 elem 元素 (key-value 結構)
                            for elem in row.findall('elem'):
                                key = elem.get('key')
                                if key == 'id':
                                    cve_id = elem.text
                                elif key == 'cvss':
                                    cvss = elem.text
                                elif key == 'is_exploit':
                                    is_exploit = elem.text
                            
                            # 只有拿到 CVE ID 才算有效資料
                            if cve_id:
                                cves.append({
                                    "id": cve_id,
                                    "cvss": float(cvss) if cvss else 0.0,
                                    "is_exploit": is_exploit == "true"
                                })
        except Exception as e:
            # 不讓 CVE 解析失敗影響主要 Port 資訊的讀取
            logger.warning(f"Failed to parse CVEs for port {port.get('portid')}: {e}")
        
        return cves