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
import requests # [New] 用於執行登入
from urllib.parse import urlparse
from mcp.server.fastmcp import FastMCP

# [Short-term Goal 1] 設定結構化日誌
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

# [Short-term Goal 2] 安全驗證函式
def is_safe_url(url: str) -> bool:
    """驗證 URL 安全性，防止 Shell Injection"""
    if not url: return False
    
    # 雙重檢查：禁止常見 Shell Injection 字元
    # 雖然 subprocess.run 列表形式能防護部分，但嚴格過濾是資安最佳實踐
    if any(char in url for char in [';', '|', '`', '$', '(', ')', '<', '>', '\\', '{', '}']):
        return False
        
    # 正則驗證：只允許標準 http/https 格式
    regex = re.compile(
        r'^(https?://)'  # 必須是 http:// 或 https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain name
        r'localhost|'  # localhost
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ip
        r'(?::\d+)?'  # port
        r'(?:/?|[/?][a-zA-Z0-9-._~:/?#\[\]@!$&\'()*+,;=%]*)$', # path
        re.IGNORECASE
    )
    return re.match(regex, url) is not None

def parse_zap_progress(container_name):
    """從 Docker Log 解析 ZAP 目前的掃描階段"""
    try:
        cmd = ["docker", "logs", "--tail", "20", container_name]
        result = subprocess.run(cmd, capture_output=True, text=True)
        logs = result.stdout + result.stderr
        
        if "Active Scan" in logs:
            return "正在進行主動攻擊掃描 (Active Scanning)..."
        elif "Spider" in logs or "spider" in logs:
            match = re.search(r'URLs found: (\d+)', logs)
            count = match.group(1) if match else "?"
            return f"正在進行爬蟲探索 (Spidering) - 已發現 {count} 個連結..."
        elif "Passive Scan" in logs:
             return "正在進行被動掃描 (Passive Scanning)..."
        else:
            return "初始化或處理中..."
    except Exception:
        return "無法取得進度細節"
# ==========================================
# [New] 新增工具：自動登入並取得 Cookie
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
    """
    【輔助工具】針對「使用者帳號密碼」登入的網站，執行登入並取得 Cookie 字串。
    
    參數:
    - login_url: 登入頁面網址 (例如 http://example.com/login)
    - username: 帳號
    - password: 密碼
    - username_field: 表單中帳號欄位的 name (預設 "username" 或 "email")
    - password_field: 表單中密碼欄位的 name (預設 "password")
    - submit_url: (選填) 如果表單提交到不同網址，請填寫。若未填則預設為 login_url。
    
    回傳:
    - 成功登入後的 Cookie 字串 (格式: "key=value; key2=value2")，可直接用於 start_scan_job。
    """
    logger.info(f"執行自動登入: {login_url} User={username}")
    
    try:
        session = requests.Session()
        # 1. 先 GET 一次頁面，取得 CSRF Token (若有) 或初始化 Cookie
        # 這裡做個簡單的 User-Agent 偽裝
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36 Edg/143.0.0.0'
        })
        
        response = session.get(login_url, timeout=10)
        if response.status_code != 200:
            return f"無法存取登入頁面 (Status: {response.status_code})"

        # 2. 準備登入資料
        payload = {
            username_field: username,
            password_field: password
        }
        
        # TODO: 若網站有 CSRF Token，這裡需要 BeautifulSoup 解析並放入 payload
        # 簡單版暫不處理複雜 CSRF，適用於一般測試站或 API
        
        target_url = submit_url if submit_url else login_url
        
        # 3. 送出 POST 登入
        post_response = session.post(target_url, data=payload, timeout=10)
        
        if post_response.status_code not in [200, 302, 303]:
             return f"登入請求回應異常 (Status: {post_response.status_code})，可能登入失敗。"

        # 4. 提取 Cookie
        cookies = session.cookies.get_dict()
        if not cookies:
            return "登入後未發現任何 Cookie，請確認帳號密碼或欄位名稱是否正確。"
            
        # 格式化為 Header 字串
        cookie_string = "; ".join([f"{k}={v}" for k, v in cookies.items()])
        
        return f"""
**登入成功！** (或已取得 Cookie)

**Cookie 字串**: 
`{cookie_string}`

您可以接著呼叫 `start_scan_job`，將此字串填入 `auth_value`，並設定 `auth_header='Cookie'`。
"""
    except Exception as e:
        return f"登入過程發生錯誤: {str(e)}"

# ==========================================
# [Enhanced] 掃描工具 (支援 Auth)
# ==========================================
@mcp.tool()
def start_scan_job(
    target_url: str, 
    scan_type: str = "baseline", 
    aggressive: bool = False,
    auth_header: str = None,  
    auth_value: str = None    
) -> str:
    """
    【第一步】啟動 ZAP 弱點掃描任務 (支援身分驗證)。
    
    參數:
    - target_url: 目標網址
    - scan_type: 'baseline' / 'full'
    - aggressive: True 開啟積極模式
    - auth_header: (選填) 驗證標頭名稱。若使用 Bearer Token 請填 'Authorization'；若使用 Cookie 請填 'Cookie'。
    - auth_value: (選填) 驗證內容。例如 'Bearer xyz...' 或 'session_id=abc...'。
    """
    if not is_safe_url(target_url):
        return "錯誤：網址格式不合法。"

    logger.info(f"接收掃描請求: URL={target_url}, Type={scan_type}, Auth={bool(auth_value)}")

    json_filename = "ZAP-Report.json"
    script_name = "zap-full-scan.py" if scan_type == "full" else "zap-baseline.py"
    
    subprocess.run(["docker", "rm", "-f", SCAN_CONTAINER_NAME], capture_output=True)

    zap_configs = []
    mode_desc = []

    # [Auth] 注入驗證標頭 (使用 ZAP Replacer)
    if auth_header and auth_value:
        zap_configs.extend([
            "-config", "replacer.full_list(0).description=MCP_Auth",
            "-config", "replacer.full_list(0).enabled=true",
            "-config", "replacer.full_list(0).matchtype=REQ_HEADER",
            "-config", f"replacer.full_list(0).matchstr={auth_header}",
            "-config", "replacer.full_list(0).regex=false",
            "-config", f"replacer.full_list(0).replacement={auth_value}" # ZAP 會將此值填入 Header
        ])
        mode_desc.append("🔐 Authenticated")

    if aggressive:
        mode_desc.append("🕷️ Aggressive")

    zap_cmd = [
        "docker", "run", "-d", "--name", SCAN_CONTAINER_NAME, "-u", "0",
        "--dns", "8.8.8.8",
        "-v", f"{SHARED_VOLUME_NAME}:/zap/wrk:rw", 
        "-t", "zaproxy/zap-stable",
        script_name, "-t", target_url, "-J", json_filename, "-I"
    ]
    
    if aggressive:
        zap_cmd.append("-j")
        zap_cmd.append("-a")
        if scan_type == "full":
            zap_configs.extend(["-config", "scanner.strength=HIGH", "-config", "scanner.threadPerHost=10"])
            mode_desc.append("High Strength")

    if zap_configs:
        zap_cmd.extend(["-z", " ".join(zap_configs)])

    aggressive_text = " / ".join(mode_desc) if mode_desc else "Standard"

    try:
        result = subprocess.run(zap_cmd, check=False, capture_output=True, text=True)
        if result.returncode != 0: return f"啟動失敗: {result.stderr}"
        
        return f"""
**掃描任務已啟動！**
* **目標**: {target_url}
* **模式**: {aggressive_text}
* **驗證**: {'已啟用 (' + auth_header + ')' if auth_header else '無'}
"""
    except Exception as e:
        return f"系統錯誤: {str(e)}"
@mcp.tool()
def check_status_and_generate_report() -> str:
    """
    【第二步】檢查掃描進度。若完成則產生報告，若未完成則回報詳細階段。
    """
    check_cmd = ["docker", "ps", "-q", "-f", f"name={SCAN_CONTAINER_NAME}"]
    is_running = subprocess.run(check_cmd, capture_output=True, text=True).stdout.strip()
    
    if is_running:
        progress_desc = parse_zap_progress(SCAN_CONTAINER_NAME)
        return f"⏳ **掃描進行中**\n狀態: {progress_desc}"
    
    logger.info("掃描容器已停止，開始執行報告轉換...")
    
    reporter_cmd = [
        "docker", "run", "--rm",
        "-v", f"{SHARED_VOLUME_NAME}:/app/data",
        "zap-reporter:latest"
    ]

    try:
        proc = subprocess.run(reporter_cmd, check=True, capture_output=True, text=True)
        logger.info(f"Reporter Output: {proc.stdout}")
        
        # 讀取 JSON 摘要
        read_json_cmd = [
            "docker", "run", "--rm",
            "-v", f"{SHARED_VOLUME_NAME}:/data",
            "alpine", "cat", "/data/ZAP-Report.json"
        ]
        json_proc = subprocess.run(read_json_cmd, capture_output=True, text=True)
        
        if json_proc.returncode != 0:
            logger.warning("找不到 ZAP-Report.json，掃描可能失敗")
            return "錯誤：找不到 ZAP-Report.json。這通常代表 ZAP 掃描異常終止。"

        try:
            data = json.loads(json_proc.stdout)
            high = sum(1 for s in data.get('site',[]) for a in s.get('alerts',[]) if a.get('riskcode') == '3')
            med = sum(1 for s in data.get('site',[]) for a in s.get('alerts',[]) if a.get('riskcode') == '2')
            summary_text = f"高風險: {high} | 中風險: {med}"
        except json.JSONDecodeError:
            return "錯誤：ZAP 輸出的 JSON 格式損毀，無法讀取。"

        return f"""
 **任務全部完成！**

{summary_text}

 **報告已生成**
請執行 `retrieve_report` 工具將檔案取出至桌面。
"""
            
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr if e.stderr else e.stdout
        logger.error(f"報告生成失敗: {error_msg}")
        return f" 報告生成失敗。\n程式回傳錯誤: {error_msg}"

@mcp.tool()
def get_report_for_analysis() -> str:
    """
    【第四步】讀取 ZAP 掃描報告 (僅擷取高/中風險)，以供 AI 分析。
    """
    try:
        read_cmd = [
            "docker", "run", "--rm",
            "-v", f"{SHARED_VOLUME_NAME}:/data",
            "alpine", "cat", "/data/ZAP-Report.json"
        ]
        
        proc = subprocess.run(read_cmd, capture_output=True, text=True)
        
        if proc.returncode != 0:
            return " 無法讀取報告檔案。請確認掃描是否已完成。"
            
        data = json.loads(proc.stdout)
        sites = data.get('site', [])
        
        # [Short-term Goal 3] AI 內容優化
        report_context = ["# ZAP 弱點掃描重點分析報告 (High/Medium Risk Only)\n"]
        report_context.append(f"- 掃描時間: {data.get('@generated', 'Unknown')}")
        
        critical_count = 0
        
        for site in sites:
            target_host = site.get('@name', 'Unknown')
            alerts = site.get('alerts', [])
            
            # 過濾邏輯：只看 High(3) 和 Medium(2)
            critical_alerts = [a for a in alerts if a.get('riskcode') in ['2', '3']]
            
            if not critical_alerts:
                continue
                
            report_context.append(f"\n## 🔍 {target_host} 關鍵弱點 ({len(critical_alerts)} 個)")
            
            for i, alert in enumerate(critical_alerts, 1):
                name = alert.get('alert', 'Unknown')
                risk = alert.get('riskdesc', 'Info')
                
                # 字串截斷處理
                desc = alert.get('desc', '').replace('<p>', '').replace('</p>', '\n')
                desc = (desc[:400] + '...') if len(desc) > 400 else desc
                
                solution = alert.get('solution', '').replace('<p>', '').replace('</p>', '\n')
                solution = (solution[:400] + '...') if len(solution) > 400 else solution
                
                reference = alert.get('reference', '').replace('<p>', '').replace('</p>', '\n')

                report_context.append(f"\n### {i}. {name}")
                report_context.append(f"**🔴 風險等級**: {risk}")
                report_context.append(f"**📝 簡述**: \n{desc}")
                report_context.append(f"**🛠️ 建議**: \n{solution}")
                
                if reference:
                    refs = [line for line in reference.split('\n') if line.strip()][:3] # 只取前3個參考資料
                    if refs:
                        report_context.append("**📚 參考**: " + ", ".join(refs))
                
                critical_count += 1

        final_report = "\n".join(report_context)

        # 寫入檔案
        try:
            output_path = os.path.join(OUTPUT_DIR, "zap_analysis.md")
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(final_report)
            save_msg = f"\n\n( 重點分析報告已同步儲存至: zap_analysis.md)"
        except Exception as e:
            logger.error(f"寫入 Markdown 失敗: {e}")
            save_msg = f"\n\n( 警告: 寫入檔案失敗)"

        if critical_count == 0:
            return " 恭喜！本次掃描未發現高/中風險弱點 (系統相對安全)。" + save_msg
            
        return final_report + save_msg

    except Exception as e:
        logger.exception("get_report_for_analysis 發生錯誤")
        return f" 系統錯誤: {str(e)}"

@mcp.tool()
def retrieve_report() -> str:
    """【第三步】將報告匯出到主機指定的資料夾。"""
    try:
        if not os.path.exists(INTERNAL_DATA_DIR):
            return f" 資料目錄不存在: {INTERNAL_DATA_DIR}"
            
        docx_files = [f for f in os.listdir(INTERNAL_DATA_DIR) if f.endswith('.docx')]
        
        if not docx_files:
            return " 找不到 .docx 報告。"

        copied_files = []
        for file in docx_files:
            src = os.path.join(INTERNAL_DATA_DIR, file)
            dst = os.path.join(OUTPUT_DIR, file)
            shutil.copy2(src, dst)
            copied_files.append(file)
            
        # 同步複製 JSON
        json_src = os.path.join(INTERNAL_DATA_DIR, 'ZAP-Report.json')
        if os.path.exists(json_src):
            shutil.copy2(json_src, os.path.join(OUTPUT_DIR, 'ZAP-Report.json'))
            copied_files.append('ZAP-Report.json')

        return f" **檔案匯出成功！**\n檔案列表: {', '.join(copied_files)}"
    except Exception as e:
        logger.exception("匯出報告失敗")
        return f" 匯出失敗: {str(e)}"

@mcp.tool()
def generate_report_with_ai_insights(executive_summary: str, solutions: str) -> str:
    """【最終步】將 AI 建議注入並生成最終 Word 報告。"""
    try:
        try:
            solutions_dict = json.loads(solutions)
        except json.JSONDecodeError:
            return " 錯誤：solutions 參數必須是有效的 JSON 字串。"

        ai_data = {
            "executive_summary": executive_summary,
            "solutions": solutions_dict
        }

        # 寫入 AI 數據
        local_ai_path = os.path.join(INTERNAL_DATA_DIR, "ai_insights.json")
        with open(local_ai_path, "w", encoding="utf-8") as f:
            json.dump(ai_data, f, ensure_ascii=False, indent=2)

        logger.info("AI 數據已儲存，啟動 Reporter 生成最終報告...")
        
        reporter_cmd = [
            "docker", "run", "--rm",
            "-v", f"{SHARED_VOLUME_NAME}:/app/data",
            "zap-reporter:latest"
        ]
        
        proc = subprocess.run(reporter_cmd, check=True, capture_output=True, text=True)
        logger.info(f"Reporter Log: {proc.stdout}")

        return f" **AI 智慧報告已生成！**\n已針對 {len(solutions_dict)} 個弱點注入建議。"

    except Exception as e:
        logger.exception("注入 AI 建議時發生錯誤")
        return f" 生成報告錯誤: {str(e)}"

if __name__ == "__main__":
    mcp.run()