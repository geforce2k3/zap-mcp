import os
import subprocess
import json
import time
import platform
import sys
import traceback
import shutil  # [Fix] 需求2: 補上遺失的模組
import re      # [Feature] 需求5: 用於解析 Log 進度
from mcp.server.fastmcp import FastMCP

# [新增] 全局異常捕獲，將錯誤印到 Log
def exception_handler(exc_type, exc_value, exc_traceback):
    error_msg = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    print(f"[Fatal Error] {error_msg}", file=sys.stderr)
    sys.exit(1)

sys.excepthook = exception_handler

print("DEBUG: Starting zap_mcp_server.py...", file=sys.stderr)

# 初始化 MCP Server
mcp = FastMCP("ZAP Security All-in-One (Async Mode)")

# === 設定區 ===
# Docker Volume 名稱 (請確保您已執行 docker volume create zap_shared_data)
SHARED_VOLUME_NAME = "zap_shared_data"
# 容器內部資料路徑
INTERNAL_DATA_DIR = "/app/data"
# 這是輸出路徑，對應到主機的桌面或下載資料夾
OUTPUT_DIR = "/output"
# 掃描任務容器名稱 (固定名稱以便追蹤)
SCAN_CONTAINER_NAME = "zap-scanner-job"

def analyze_json_summary(json_path):
    """讀取 ZAP JSON 檔案並產生統計摘要字串"""
    try:
        if not os.path.exists(json_path):
            return "⚠️ 尚未找到 JSON 報告檔案。"

        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        sites = data.get('site', [])
        stats = {"High": 0, "Medium": 0, "Low": 0, "Informational": 0}
        total_alerts = 0
        
        for site in sites:
            alerts = site.get('alerts', [])
            total_alerts += len(alerts)
            for alert in alerts:
                risk_code = alert.get('riskcode', '0')
                if risk_code == '3': stats["High"] += 1
                elif risk_code == '2': stats["Medium"] += 1
                elif risk_code == '1': stats["Low"] += 1
                else: stats["Informational"] += 1

        return f"""
### 📊 掃描結果摘要
* **總弱點數**: {total_alerts}
* 🔴 **高風險**: {stats['High']}
* 🟠 **中風險**: {stats['Medium']}
* 🟡 **低風險**: {stats['Low']}
"""
    except Exception as e:
        return f"⚠️ 無法分析 JSON 摘要: {str(e)}"

def parse_zap_progress(container_name):
    """從 Docker Log 解析 ZAP 目前的掃描階段"""
    try:
        # 抓取最後 20 行 Log
        cmd = ["docker", "logs", "--tail", "20", container_name]
        result = subprocess.run(cmd, capture_output=True, text=True)
        logs = result.stdout + result.stderr
        
        if "Active Scan" in logs:
            return "🔥 正在進行主動攻擊掃描 (Active Scanning)..."
        elif "Spider" in logs or "spider" in logs:
            # 嘗試抓取 URL 數量
            match = re.search(r'URLs found: (\d+)', logs)
            count = match.group(1) if match else "?"
            return f"🕷️ 正在進行爬蟲探索 (Spidering) - 已發現 {count} 個連結..."
        elif "Passive Scan" in logs:
             return "👀 正在進行被動掃描 (Passive Scanning)..."
        else:
            return "⏳ 初始化或處理中..."
    except Exception:
        return "無法取得進度細節"

@mcp.tool()
def start_scan_job(target_url: str, scan_type: str = "baseline", aggressive: bool = False) -> str:
    """
    【第一步】啟動 ZAP 弱點掃描任務 (背景執行)。
    
    參數說明:
    - target_url: 目標網址
    - scan_type: 'baseline' (快速) 或 'full' (完整攻擊)
    - aggressive: True 開啟積極模式 (含 AJAX 爬蟲、Alpha 規則與高強度攻擊)，掃描時間會大幅增加。
    """
    json_filename = "ZAP-Report.json"
    script_name = "zap-full-scan.py" if scan_type == "full" else "zap-baseline.py"
    
    # 1. 清理舊的容器
    subprocess.run(["docker", "rm", "-f", SCAN_CONTAINER_NAME], capture_output=True)

    # 2. 準備基礎 Docker 指令
    zap_cmd = [
        "docker", "run", 
        "-d",                              # 背景執行
        "--name", SCAN_CONTAINER_NAME,     # 指定容器名稱
        "-u", "0",                         # 使用 Root 權限
        "--dns", "8.8.8.8",                # 強制使用 Google DNS
        "-v", f"{SHARED_VOLUME_NAME}:/zap/wrk:rw", 
        "-t", "zaproxy/zap-stable",
        script_name, 
        "-t", target_url,
        "-J", json_filename,
        "-I"                               # 忽略警告直接執行
    ]

    # 3. [新增] 處理積極模式參數
    mode_desc = []
    if aggressive:
        # -j: 啟用 AJAX Spider (針對 JS 動態網頁)
        zap_cmd.append("-j")
        mode_desc.append("🕷️ AJAX Spider (深入 JS)")

        # -a: 啟用 Alpha 實驗性規則 (發現更多潛在漏洞)
        zap_cmd.append("-a")
        mode_desc.append("🧪 Alpha Rules (實驗性規則)")

        # 針對 Full Scan 提高攻擊強度
        if scan_type == "full":
            # -z: 傳遞參數給 ZAP 核心
            # scanner.strength=HIGH: 對每個弱點進行更多種 payload 測試
            # scanner.threadPerHost=20: 提高執行緒數加速 (視伺服器承受力而定)
            zap_cmd.extend(["-z", "-config scanner.strength=HIGH -config scanner.threadPerHost=10"])
            mode_desc.append("🔥 High Strength (高強度攻擊)")
    
    # 組合說明文字
    aggressive_text = " / ".join(mode_desc) if aggressive else "標準模式 (Standard)"
    scan_mode_text = "完整攻擊掃描 (Full)" if scan_type == "full" else "基礎被動掃描 (Baseline)"

    try:
        # 執行 Docker run
        result = subprocess.run(zap_cmd, check=False, capture_output=True, text=True)
        
        if result.returncode != 0 and result.stderr:
             return f"❌ 啟動失敗: {result.stderr}"

        return f"""
🚀 **掃描任務已成功啟動！**

* **目標**: {target_url}
* **模式**: {scan_mode_text}
* **策略**: {aggressive_text}
* **狀態**: 正在背景執行中...

⚠️ **重要提醒**：
1. **積極模式 (Aggressive)** 會顯著增加掃描時間（Full Scan 可能需數小時）。
2. AJAX Spider 會消耗更多記憶體與運算資源。
3. 高強度攻擊可能會對目標伺服器造成負擔，請確保您有授權。
"""
    except Exception as e:
        return f"❌ 呼叫 Docker 發生例外: {str(e)}"

@mcp.tool()
def check_status_and_generate_report() -> str:
    """
    【第二步】檢查掃描進度。若完成則產生報告，若未完成則回報詳細階段。
    """
    # 1. 檢查容器狀態
    check_cmd = ["docker", "ps", "-q", "-f", f"name={SCAN_CONTAINER_NAME}"]
    is_running = subprocess.run(check_cmd, capture_output=True, text=True).stdout.strip()
    
    if is_running:
        # [Feature] 需求5: 回傳更聰明的即時進度
        progress_desc = parse_zap_progress(SCAN_CONTAINER_NAME)
        return f"""
⏳ **掃描進行中**
狀態: {progress_desc}

您可以稍後再回來確認。
"""
    
    # 2. 容器已停止，開始生成報告
    # [Refactor] 需求4: 優化錯誤處理流程
    print("DEBUG: 掃描容器已停止，開始執行報告轉換...", file=sys.stderr)
    
    reporter_cmd = [
        "docker", "run", "--rm",
        "-v", f"{SHARED_VOLUME_NAME}:/app/data",
        "zap-reporter:latest"
    ]

    try:
        # 執行報告轉換
        proc = subprocess.run(reporter_cmd, check=True, capture_output=True, text=True)
        print(f"DEBUG: Reporter Output: {proc.stdout}", file=sys.stderr)
        
        # 3. 讀取 JSON 摘要
        read_json_cmd = [
            "docker", "run", "--rm",
            "-v", f"{SHARED_VOLUME_NAME}:/data",
            "alpine", "cat", "/data/ZAP-Report.json"
        ]
        json_proc = subprocess.run(read_json_cmd, capture_output=True, text=True)
        
        if json_proc.returncode != 0:
            return "❌ 錯誤：找不到 ZAP-Report.json。這通常代表 ZAP 掃描異常終止 (例如目標網站無法連線)。"

        # 解析 JSON
        try:
            data = json.loads(json_proc.stdout)
            high = sum(1 for s in data.get('site',[]) for a in s.get('alerts',[]) if a.get('riskcode') == '3')
            med = sum(1 for s in data.get('site',[]) for a in s.get('alerts',[]) if a.get('riskcode') == '2')
            summary_text = f"🔴 高風險: {high} | 🟠 中風險: {med}"
        except json.JSONDecodeError:
            return "❌ 錯誤：ZAP 輸出的 JSON 格式損毀，無法讀取。"

        return f"""
✅ **任務全部完成！**

{summary_text}

📄 **報告已生成**
請執行 `retrieve_report` 工具將檔案取出至桌面。
"""
            
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr if e.stderr else e.stdout
        return f"⚠️ 報告生成失敗。\n程式回傳錯誤: {error_msg}"

@mcp.tool()
def get_report_for_analysis() -> str:
    """
    【第四步】讀取 ZAP 掃描報告的詳細技術內容，以供 AI 進行資安分析。
    
    當使用者要求「分析報告」、「提供修復建議」或「解釋弱點」時，請務必呼叫此工具。
    它會回傳弱點名稱、描述、風險等級、解決方案與參考文獻連結。
    """
    try:
        # 1. 從 Docker Volume 讀取原始 JSON 報告
        # 我們使用一個臨時容器來 cat 檔案內容
        read_cmd = [
            "docker", "run", "--rm",
            "-v", f"{SHARED_VOLUME_NAME}:/data",
            "alpine", "cat", "/data/ZAP-Report.json"
        ]
        
        proc = subprocess.run(read_cmd, capture_output=True, text=True)
        
        if proc.returncode != 0:
            return "⚠️ 無法讀取報告檔案。請確認是否已執行 'check_status_and_generate_report' 且掃描已完成。"
            
        # 2. 解析 JSON 並轉換為 AI 易讀的 Markdown 格式
        data = json.loads(proc.stdout)
        sites = data.get('site', [])
        
        if not sites:
            return "報告是空的，未發現任何站點資訊。"

        report_context = ["# ZAP 弱點掃描技術分析報告\n"]
        
        # 統計資訊
        report_context.append("## 📊 執行摘要")
        generated_time = data.get('@generated', 'Unknown Date')
        report_context.append(f"- 掃描時間: {generated_time}")
        
        total_alerts = 0
        
        for site in sites:
            target_host = site.get('@name', 'Unknown Host')
            target_port = site.get('@port', '80')
            report_context.append(f"- 目標主機: {target_host}:{target_port}")
            
            alerts = site.get('alerts', [])
            total_alerts += len(alerts)
            
            if not alerts:
                report_context.append("\n(此站點未發現明顯弱點)")
                continue

            report_context.append(f"\n## 🔍 {target_host} 弱點詳情")
            
            for i, alert in enumerate(alerts, 1):
                # 擷取關鍵欄位
                name = alert.get('alert', 'Unknown Vulnerability')
                risk = alert.get('riskdesc', 'Info')
                desc = alert.get('desc', 'No description provided.').replace('<p>', '').replace('</p>', '\n')
                solution = alert.get('solution', 'No solution provided.').replace('<p>', '').replace('</p>', '\n')
                reference = alert.get('reference', '').replace('<p>', '').replace('</p>', '\n')
                
                # 組合為結構化文字
                report_context.append(f"\n### {i}. {name}")
                report_context.append(f"**🔴 風險等級**: {risk}")
                report_context.append(f"**📝 弱點描述**: \n{desc[:500]}...") # 截斷過長的描述避免 Token 爆炸
                report_context.append(f"**🛠️ 建議修復方式**: \n{solution[:500]}...")
                
                # 處理參考資料
                if reference:
                    refs = [line for line in reference.split('\n') if line.strip()]
                    if refs:
                        report_context.append("**📚 技術參考資料**:")
                        for ref in refs:
                            report_context.append(f"- {ref.strip()}")

        if total_alerts == 0:
            return "✅ 恭喜！本次掃描未發現任何風險。"
            
        return "\n".join(report_context)

    except json.JSONDecodeError:
        return "❌ 錯誤：報告 JSON 格式損毀，無法解析。"
    except Exception as e:
        return f"❌ 讀取分析資料時發生系統錯誤: {str(e)}"


@mcp.tool()
def retrieve_report() -> str:
    """
    【第三步】將報告匯出到主機指定的資料夾 (例如桌面)。
    """
    try:
        # Debug: 列出目錄內容
        print(f"DEBUG: INTERNAL_DATA_DIR={INTERNAL_DATA_DIR}", file=sys.stderr)
        print(f"DEBUG: OUTPUT_DIR={OUTPUT_DIR}", file=sys.stderr)
        
        if not os.path.exists(INTERNAL_DATA_DIR):
            return f"❌ 資料目錄不存在: {INTERNAL_DATA_DIR}"
        if not os.path.exists(OUTPUT_DIR):
            return f"❌ 輸出目錄不存在: {OUTPUT_DIR}"
            
        all_files = os.listdir(INTERNAL_DATA_DIR)
        print(f"DEBUG: Files in data dir: {all_files}", file=sys.stderr)
        
        # 1. 檢查內部掛載點是否有報告
        docx_files = [f for f in all_files if f.endswith('.docx')]
        
        if not docx_files:
            return f"⚠️ 在資料夾中找不到 .docx 報告。\n目前檔案: {all_files}\n請確認是否已執行「檢查掃描狀態」。"

        # 2. 直接複製檔案 (因為 MCP 容器已經掛載了 Volume)
        copied_files = []
        for file in docx_files:
            src = os.path.join(INTERNAL_DATA_DIR, file)
            dst = os.path.join(OUTPUT_DIR, file)
            print(f"DEBUG: Copying {src} -> {dst}", file=sys.stderr)
            shutil.copy2(src, dst)
            copied_files.append(file)
            
        # 同步複製 JSON 以備不時之需
        json_src = os.path.join(INTERNAL_DATA_DIR, 'ZAP-Report.json')
        if os.path.exists(json_src):
            json_dst = os.path.join(OUTPUT_DIR, 'ZAP-Report.json')
            shutil.copy2(json_src, json_dst)
            copied_files.append('ZAP-Report.json')

        return f"""
✅ **檔案匯出成功！**

已將以下檔案儲存至您的輸出資料夾：
{', '.join(copied_files)}

路徑: /Users/kevin/Documents/zap-output/
"""
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        print(f"DEBUG: Error - {error_detail}", file=sys.stderr)
        return f"❌ 匯出檔案失敗: {str(e)}\n詳細: {error_detail}"

@mcp.tool()
def generate_report_with_ai_insights(executive_summary: str, solutions: str) -> str:
    """
    【最終步】將 AI 分析後的建議注入並生成最終 Word 報告。
    
    當您（AI）完成弱點分析後，請呼叫此工具來生成報告。
    
    參數說明:
    - executive_summary: 您針對整體掃描結果撰寫的「資安顧問總結」段落 (純文字)。
    - solutions: 一個 JSON 格式的字串。Key 必須是弱點的英文原名 (如 'Cross Site Scripting (Reflected)')，Value 是您提供的詳細修復建議與程式碼範例。
                 格式範例: '{"Cross Site Scripting (Reflected)": "建議使用 html.escape() 處理...", "SQL Injection": "請使用參數化查詢..."}'
    """
    try:
        # 1. 驗證並儲存 AI 的建議數據
        try:
            solutions_dict = json.loads(solutions)
        except json.JSONDecodeError:
            return "❌ 錯誤：solutions 參數必須是有效的 JSON 字串。"

        ai_data = {
            "executive_summary": executive_summary,
            "solutions": solutions_dict
        }

        # 寫入到共享 Volume，讓 Reporter 讀取
        # 我們利用一個臨時容器寫入檔案 (因為 shared volume 在 host 上的路徑對 mcp 容器來說可能不同，直接用 volume 寫入最保險)
        # 但這裡為了簡便，我們假設 MCP 容器已經掛載了 /app/data -> zap_shared_data (我們在 Dockerfile.mcp 裡有做)
        # 所以直接寫入 /app/data 即可
        
        local_ai_path = os.path.join(INTERNAL_DATA_DIR, "ai_insights.json")
        with open(local_ai_path, "w", encoding="utf-8") as f:
            json.dump(ai_data, f, ensure_ascii=False, indent=2)

        # 2. 呼叫 Reporter 容器生成 Word
        print("DEBUG: AI 數據已儲存，啟動 Reporter...", file=sys.stderr)
        
        reporter_cmd = [
            "docker", "run", "--rm",
            "-v", f"{SHARED_VOLUME_NAME}:/app/data",
            "zap-reporter:latest"
        ]
        
        proc = subprocess.run(reporter_cmd, check=True, capture_output=True, text=True)
        print(f"DEBUG: Reporter Log: {proc.stdout}", file=sys.stderr)

        return f"""
✅ **AI 智慧報告已生成！**

您的專業分析已成功注入到 Word 報告中。
* 已包含「AI 資安顧問總結」
* 已針對 {len(solutions_dict)} 個弱點替換了詳細修復建議

請執行 `retrieve_report` 將最終報告取出。
"""

    except Exception as e:
        return f"❌ 生成報告時發生錯誤: {str(e)}"


# 程式進入點 - 只保留一個
if __name__ == "__main__":
    mcp.run()