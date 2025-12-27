import os
import subprocess
import json
import time
import platform
import sys
import traceback
import shutil
import re
import logging
import requests 
import xml.etree.ElementTree as ET
from urllib.parse import urlparse
from mcp.server.fastmcp import FastMCP

# 設定結構化日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    stream=sys.stderr
)
logger = logging.getLogger("ZAP-MCP")

# 全局異常捕獲
def exception_handler(exc_type, exc_value, exc_traceback):
    error_msg = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    logger.critical(f"Uncaught Exception: {error_msg}")
    sys.exit(1)

sys.excepthook = exception_handler

logger.info("Starting zap_mcp_server.py...")

# 初始化 MCP Server
mcp = FastMCP("ZAP Security All-in-One (Async Mode)")

# === 設定區 ===
SHARED_VOLUME_NAME = "zap_shared_data"
INTERNAL_DATA_DIR = "/app/data"
OUTPUT_DIR = "/output"
SCAN_CONTAINER_NAME = "zap-scanner-job"

# 安全驗證函式
def is_safe_url(url: str) -> bool:
    if not url: return False
    if any(char in url for char in [';', '|', '`', '$', '(', ')', '<', '>', '\\', '{', '}']):
        return False
    regex = re.compile(
        r'^(https?://)'  
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  
        r'localhost|' 
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})' 
        r'(?::\d+)?'  
        r'(?:/?|[/?][a-zA-Z0-9-._~:/?#\[\]@!$&\'()*+,;=%]*)$', 
        re.IGNORECASE
    )
    return re.match(regex, url) is not None

def parse_zap_progress(container_name):
    try:
        cmd = ["docker", "logs", "--tail", "20", container_name]
        result = subprocess.run(cmd, capture_output=True, text=True)
        logs = result.stdout + result.stderr
        
        if "Active Scan" in logs: return "正在進行主動攻擊掃描 (Active Scanning)..."
        elif "Spider" in logs: return "正在進行爬蟲探索 (Spidering)..."
        elif "Passive Scan" in logs: return "正在進行被動掃描 (Passive Scanning)..."
        else: return "初始化或處理中..."
    except: return "無法取得進度"

# ==========================================
# 工具 1: Nmap 偵察
# ==========================================
@mcp.tool()
def run_nmap_recon(target_host: str, ports: str = "top-1000") -> str:
    """【流程第一步】執行 Nmap 埠口掃描，自動識別 Web 服務。"""
    if any(char in target_host for char in [';', '|', '`', '$']):
        return "❌ 錯誤：目標主機包含非法字元。"

    logger.info(f"啟動 Nmap 偵察: Target={target_host}, Ports={ports}")
    nmap_xml_output = os.path.join(INTERNAL_DATA_DIR, "nmap_result.xml")
    
    nmap_cmd = ["nmap", "-sV", "--open", "-oX", nmap_xml_output, target_host]
    if ports != "top-1000":
        if ports == "p-": nmap_cmd.append("-p-")
        else: nmap_cmd.extend(["-p", ports])

    try:
        subprocess.run(nmap_cmd, check=True, capture_output=True, text=True)
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

                    protocol = "http"
                    if "https" in service_name or "ssl" in service_name: protocol = "https"
                    elif service_name not in ["http", "http-alt", "http-proxy", "soap"]: continue 

                    url = f"{protocol}://{target_host}:{port_id}"
                    if (protocol == "http" and port_id == "80") or (protocol == "https" and port_id == "443"):
                        url = f"{protocol}://{target_host}"
                    discovered_urls.append(url)

        if not discovered_urls:
            return f"🔍 Nmap 完成。開放端口: {', '.join(raw_services)}\n⚠️ 未發現明顯 Web 服務。"

        return f"✅ **偵察完成！發現 Web 服務**：\n{chr(10).join(['- ' + url for url in discovered_urls])}"

    except Exception as e:
        return f"❌ Nmap 執行失敗: {str(e)}"

# ==========================================
# 工具 2: 自動登入
# ==========================================
@mcp.tool()
def perform_login_and_get_cookie(
    login_url: str,
    username: str,
    password: str,
    username_field: str = "username",
    password_field: str = "password",
    submit_url: str = None
) -> str:
    """【輔助工具】執行自動登入並取得 Cookie。"""
    logger.info(f"執行自動登入: {login_url} User={username}")
    try:
        session = requests.Session()
        session.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) ZAP-MCP/1.0'})
        
        resp = session.get(login_url, timeout=10)
        if resp.status_code != 200: return f"無法存取頁面 (Status: {resp.status_code})"

        payload = {username_field: username, password_field: password}
        target = submit_url if submit_url else login_url
        
        post_resp = session.post(target, data=payload, timeout=10)
        if post_resp.status_code not in [200, 302, 303]: return f"登入異常 (Status: {post_resp.status_code})"

        cookies = session.cookies.get_dict()
        if not cookies: return "登入後未發現 Cookie。"
            
        cookie_str = "; ".join([f"{k}={v}" for k, v in cookies.items()])
        return f"**登入成功！** Cookie: `{cookie_str}`"
    except Exception as e:
        return f"登入錯誤: {str(e)}"

# ==========================================
# 工具 3: 啟動掃描 (修正 NameError)
# ==========================================
@mcp.tool()
def start_scan_job(
    target_url: str, 
    scan_type: str = "baseline", 
    aggressive: bool = False,
    auth_header: str = None,  
    auth_value: str = None    
) -> str:
    """【流程第二步】啟動 ZAP 弱點掃描任務。"""
    if not is_safe_url(target_url): return "錯誤：網址格式不合法。"

    logger.info(f"啟動掃描: URL={target_url}, Type={scan_type}, Auth={bool(auth_value)}")
    
    subprocess.run(["docker", "rm", "-f", SCAN_CONTAINER_NAME], capture_output=True)

    zap_configs = []
    mode_desc = []

    # [Auth]
    if auth_header and auth_value:
        zap_configs.extend([
            "-config", "replacer.full_list(0).description=MCP_Auth",
            "-config", "replacer.full_list(0).enabled=true",
            "-config", "replacer.full_list(0).matchtype=REQ_HEADER",
            "-config", f"replacer.full_list(0).matchstr={auth_header}",
            "-config", "replacer.full_list(0).regex=false",
            "-config", f"replacer.full_list(0).replacement={auth_value}"
        ])
        mode_desc.append("🔐 Authenticated")

    if aggressive:
        mode_desc.append("🕷️ Aggressive")

    script_name = "zap-full-scan.py" if scan_type == "full" else "zap-baseline.py"
    zap_cmd = [
        "docker", "run", "-d", "--name", SCAN_CONTAINER_NAME, "-u", "0",
        "--dns", "8.8.8.8",
        "-v", f"{SHARED_VOLUME_NAME}:/zap/wrk:rw", 
        "-t", "zaproxy/zap-stable",
        script_name, "-t", target_url, "-J", "ZAP-Report.json", "-I"
    ]
    
    if aggressive:
        zap_cmd.append("-j")
        zap_cmd.append("-a")
        if scan_type == "full":
            zap_configs.extend(["-config", "scanner.strength=HIGH", "-config", "scanner.threadPerHost=10"])
            mode_desc.append("High Strength")

    if zap_configs:
        zap_cmd.extend(["-z", " ".join(zap_configs)])

    # [Fix] 確保變數一定有值，且不會因為縮排問題被跳過
    aggressive_text = "標準模式 (Standard)" 
    if mode_desc:
        aggressive_text = " / ".join(mode_desc)

    try:
        result = subprocess.run(zap_cmd, check=False, capture_output=True, text=True)
        if result.returncode != 0: return f"啟動失敗: {result.stderr}"
        
        return f"""
🚀 **掃描任務已啟動！**
* **目標**: {target_url}
* **模式**: {aggressive_text}
* **驗證**: {'已啟用' if auth_header else '無'}

⚠️ **重要**: 掃描在背景執行，離開對話不會中斷。請稍後使用 `check_status` 查詢。
"""
    except Exception as e:
        return f"系統錯誤: {str(e)}"

# ==========================================
# 工具 4: 檢查狀態
# ==========================================
@mcp.tool()
def check_status_and_generate_report() -> str:
    """【流程第三步】檢查進度。若掃描中會提示等待；完成後自動產生 Word 報告。"""
    check_cmd = ["docker", "ps", "-q", "-f", f"name={SCAN_CONTAINER_NAME}"]
    is_running = subprocess.run(check_cmd, capture_output=True, text=True).stdout.strip()
    
    if is_running:
        progress = parse_zap_progress(SCAN_CONTAINER_NAME)
        return f"""
⏳ **掃描進行中** (Status: Running)
目前階段: {progress}

**SYSTEM NOTE:** 請 **等待 30 秒** 後再檢查狀態，不要立即重試。
"""
    
    logger.info("掃描結束，轉換報告中...")
    reporter_cmd = ["docker", "run", "--rm", "-v", f"{SHARED_VOLUME_NAME}:/app/data", "zap-reporter:latest"]

    try:
        subprocess.run(reporter_cmd, check=True, capture_output=True, text=True)
        
        # 讀取摘要
        read_json = ["docker", "run", "--rm", "-v", f"{SHARED_VOLUME_NAME}:/data", "alpine", "cat", "/data/ZAP-Report.json"]
        json_proc = subprocess.run(read_json, capture_output=True, text=True)
        
        if json_proc.returncode != 0: return "❌ 錯誤：找不到報告檔案，掃描可能失敗。"

        try:
            data = json.loads(json_proc.stdout)
            high = sum(1 for s in data.get('site',[]) for a in s.get('alerts',[]) if a.get('riskcode') == '3')
            med = sum(1 for s in data.get('site',[]) for a in s.get('alerts',[]) if a.get('riskcode') == '2')
            summary = f"🔴 高風險: {high} | 🟠 中風險: {med}"
        except: summary = "無法讀取統計"

        return f"✅ **掃描與報告生成完成！**\n{summary}\n請接著使用 `get_report_for_analysis` 進行分析。"
    except subprocess.CalledProcessError as e:
        return f"⚠️ 報告生成失敗: {e.stderr}"

# ==========================================
# 工具 5: 讀取精簡報告
# ==========================================
@mcp.tool()
def get_report_for_analysis() -> str:
    """【流程第四步】讀取關鍵弱點 (High/Medium) 供 AI 分析。(字數限制 2000)"""
    try:
        read_cmd = ["docker", "run", "--rm", "-v", f"{SHARED_VOLUME_NAME}:/data", "alpine", "cat", "/data/ZAP-Report.json"]
        proc = subprocess.run(read_cmd, capture_output=True, text=True)
        if proc.returncode != 0: return "無法讀取報告。"
            
        data = json.loads(proc.stdout)
        sites = data.get('site', [])
        
        report_context = ["# ZAP 關鍵風險摘要 (High/Medium Only)\n"]
        critical_count = 0
        
        for site in sites:
            target_host = site.get('@name', 'Unknown')
            alerts = site.get('alerts', [])
            # 只取 High/Medium
            critical_alerts = [a for a in alerts if a.get('riskcode') in ['2', '3']]
            
            if not critical_alerts: continue
                
            report_context.append(f"\n## 🎯 {target_host}")
            for i, alert in enumerate(critical_alerts, 1):
                name = alert.get('alert', 'Unknown')
                risk = alert.get('riskdesc', 'Info').split(' ')[0]
                
                desc = alert.get('desc', '').replace('<p>', '').replace('</p>', '\n')
                if len(desc) > 2000: desc = desc[:2000] + "...(truncated)"
                
                sol = alert.get('solution', '').replace('<p>', '').replace('</p>', '\n')
                if len(sol) > 2000: sol = sol[:2000] + "...(truncated)"
                
                report_context.append(f"- [{risk}] {name}")
                report_context.append(f"  - 📝 狀況: {desc}")
                report_context.append(f"  - 🛠️ 建議: {sol}")
                critical_count += 1

        final_report = "\n".join(report_context)
        
        try:
            with open(os.path.join(OUTPUT_DIR, "zap_analysis.md"), "w", encoding="utf-8") as f:
                f.write(final_report)
        except: pass

        if critical_count == 0:
            return "✅ 恭喜！未發現高/中風險弱點 (低風險已忽略)。"
            
        return final_report + "\n\n(已顯示 High/Medium 風險)"

    except Exception as e:
        return f"分析錯誤: {str(e)}"

# ==========================================
# 工具 6: 注入 AI 建議
# ==========================================
@mcp.tool()
def generate_report_with_ai_insights(executive_summary: str, solutions: str) -> str:
    """【流程第五步】將 AI 建議注入並生成最終 Word 報告。"""
    try:
        try:
            solutions_dict = json.loads(solutions)
        except json.JSONDecodeError:
            return "錯誤：solutions 參數必須是有效的 JSON 字串。"

        ai_data = {
            "executive_summary": executive_summary,
            "solutions": solutions_dict
        }

        local_ai_path = os.path.join(INTERNAL_DATA_DIR, "ai_insights.json")
        with open(local_ai_path, "w", encoding="utf-8") as f:
            json.dump(ai_data, f, ensure_ascii=False, indent=2)

        logger.info("啟動 Reporter 生成最終報告...")
        reporter_cmd = ["docker", "run", "--rm", "-v", f"{SHARED_VOLUME_NAME}:/app/data", "zap-reporter:latest"]
        
        proc = subprocess.run(reporter_cmd, check=True, capture_output=True, text=True)
        return f"✅ **AI 智慧報告已生成！**\n已注入 {len(solutions_dict)} 個建議。"

    except Exception as e:
        return f"生成報告錯誤: {str(e)}"

# ==========================================
# 工具 7: 匯出檔案
# ==========================================
@mcp.tool()
def retrieve_report() -> str:
    """【流程第六步】匯出所有報告檔案。"""
    try:
        if not os.path.exists(INTERNAL_DATA_DIR): return "資料目錄不存在。"
        
        files = [f for f in os.listdir(INTERNAL_DATA_DIR) if f.endswith('.docx') or f.endswith('.json') or f.endswith('.xml')]
        copied = []
        
        for f in files:
            shutil.copy2(os.path.join(INTERNAL_DATA_DIR, f), os.path.join(OUTPUT_DIR, f))
            copied.append(f)

        return f"✅ **匯出成功！**\n檔案: {', '.join(copied)}"
    except Exception as e:
        return f"匯出失敗: {str(e)}"

if __name__ == "__main__":
    mcp.run()