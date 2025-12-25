import json
import re
import os
import matplotlib.pyplot as plt
from datetime import datetime
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn

# ==========================================
# 1. 中英對照字典 (Mapping Dictionary)
# ==========================================

RISK_MAPPING = {
    "High": "高風險 (High)",
    "Medium": "中風險 (Medium)",
    "Low": "低風險 (Low)",
    "Informational": "資訊 (Info)",
    "False Positive": "誤報 (False Positive)"
}

TERM_MAPPING = {
    # --- OWASP ZAP 常見漏洞 ---
    "Cross Site Scripting (Reflected)": "反射型跨站腳本攻擊 (XSS)",
    "Cross Site Scripting (Persistent)": "儲存型跨站腳本攻擊 (XSS)",
    "Cross Site Scripting (DOM Based)": "DOM 型跨站腳本攻擊 (XSS)",
    "SQL Injection": "SQL 資料隱碼攻擊",
    "Path Traversal": "路徑遍歷漏洞",
    "Remote File Inclusion": "遠端檔案包含 (RFI)",
    "Server Side Include": "伺服器端包含注入 (SSI)",
    "Cross-Site Request Forgery": "跨站請求偽造 (CSRF)",
    "Directory Browsing": "目錄遍歷/目錄瀏覽",
    "Buffer Overflow": "緩衝區溢位",
    "Format String Error": "格式化字串錯誤",
    "Information Disclosure - Debug Error Messages": "資訊洩漏 - 偵錯錯誤訊息",
    "Information Disclosure - Sensitive Information in URL": "資訊洩漏 - URL 包含敏感資訊",
    "Information Disclosure - Suspicious Comments": "資訊洩漏 - 可疑的程式註解",
    "Weak Authentication Method": "身分驗證機制薄弱",
    "Absence of Anti-CSRF Tokens": "缺乏 Anti-CSRF Token",
    "Missing Anti-clickjacking Header": "遺失防點擊劫持標頭 (Clickjacking)",
    "X-Frame-Options Header Not Set": "未設定 X-Frame-Options 標頭",
    "X-Content-Type-Options Header Missing": "遺失 X-Content-Type-Options 標頭",
    "Strict-Transport-Security Header Not Set": "未設定 HSTS 安全傳輸標頭",
    "Cookie No HttpOnly Flag": "Cookie 遺失 HttpOnly 屬性",
    "Cookie Without Secure Flag": "Cookie 遺失 Secure 屬性",
    "Application Error Disclosure": "應用程式錯誤資訊揭露",
    "Private IP Disclosure": "內部 IP 位址洩漏",
    "Session ID in URL Rewrite": "Session ID 暴露於 URL",
    "Source Code Disclosure": "原始碼洩漏",

    # --- 雲端與其他術語 ---
    "AWS Identity and Access Management (IAM)": "AWS 身分與存取管理",
    "Amazon S3 (Simple Storage Service)": "Amazon S3 物件儲存服務",
    "CloudTrail": "AWS 操作紀錄稽核服務",
    "Cloud IAM": "Google Cloud 身分與存取管理",
}

# ==========================================
# 2. 輔助函式
# ==========================================

def clean_html(raw_html):
    if raw_html is None: return ""
    cleanr = re.compile('<.*?>')
    return re.sub(cleanr, '', raw_html).strip()

def translate_title(english_title):
    return TERM_MAPPING.get(english_title, english_title)

def set_table_header_style(cell):
    """設定表格標題的底色與粗體"""
    # 這裡使用簡單的粗體，底色需要操作 xml 較複雜，暫以文字格式為主
    paragraphs = cell.paragraphs
    for p in paragraphs:
        for run in p.runs:
            run.bold = True
            run.font.size = Pt(12)

# ==========================================
# 3. 報告生成主邏輯
# ==========================================

def generate_risk_chart(stats, output_img_path):
    """[Feature] 需求1: 繪製風險分佈圓餅圖"""
    labels = []
    sizes = []
    colors = []
    
    # 定義顏色與標籤
    mapping = {
        "High": ("高風險", "#ff0000"),
        "Medium": ("中風險", "#ffa500"),
        "Low": ("低風險", "#ffff00"),
        "Informational": ("資訊", "#0000ff")
    }
    
    for key, (label, color) in mapping.items():
        if stats[key] > 0:
            labels.append(f"{label} ({stats[key]})")
            sizes.append(stats[key])
            colors.append(color)
            
    if not sizes: return False

    plt.figure(figsize=(4, 3))
    plt.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', startangle=140)
    plt.axis('equal') # 確保是圓形
    plt.title("弱點風險分佈", fontname="Microsoft JhengHei") # 注意：Linux 環境可能需指定字體路徑，若無則會顯示方框，可改用英文 title
    plt.tight_layout()
    plt.savefig(output_img_path)
    plt.close()
    return True

def generate_word_report(json_path, output_path, company_name="Nextlink MSP"):
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"讀取 JSON 失敗: {e}")
        return

    doc = Document()
    style = doc.styles['Normal']
    style.font.name = 'Microsoft JhengHei'
    style.font.size = Pt(11)
    # 處理中文字型 (確保 Word 認得這是中文字型)
    style.element.rPr.rFonts.set(qn('w:eastAsia'), 'Microsoft JhengHei')

    # --- 1. 封面 ---
    doc.add_heading(f'{company_name} - 弱點掃描報告', 0)
    
    # Logo 處理
    base_dir = os.path.dirname(json_path)
    logo_path = os.path.join(base_dir, 'logo.png')
    if os.path.exists(logo_path):
        try:
            doc.add_picture(logo_path, width=Inches(2.0))
        except: pass
    
    doc.add_paragraph(f"掃描工具: OWASP ZAP")
    doc.add_paragraph(f"產生日期: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    scan_target = data.get('site', [{}])[0].get('@name', 'Unknown Target')
    doc.add_paragraph(f"掃描目標: {scan_target}")
    doc.add_page_break()

    # --- [新增功能] 2. 掃描摘要統計 ---
    doc.add_heading('1. 掃描結果摘要', level=1)

    
    # 計算統計數據
    sites = data.get('site', [])
    stats = {"High": 0, "Medium": 0, "Low": 0, "Informational": 0}
    
    for site in sites:
        for alert in site.get('alerts', []):
            risk_desc = alert.get('riskdesc', 'Info').split(' ')[0] # 抓取 High/Medium...
            if risk_desc in stats:
                stats[risk_desc] += 1
            else:
                stats["Informational"] += 1
    
    total_vulns = sum(stats.values())
    doc.add_paragraph(f"本次掃描共發現 {total_vulns} 個潛在弱點。風險分佈如下：")
    # [Feature] 插入圖表
    chart_path = os.path.join(os.path.dirname(json_path), "risk_chart.png")
    if generate_risk_chart(stats, chart_path):
        doc.add_picture(chart_path, width=Inches(4.0))
        # 移除暫存圖片
        if os.path.exists(chart_path): os.remove(chart_path)
    # 繪製統計表格
    table = doc.add_table(rows=5, cols=2)
    table.style = 'Table Grid'
    
    # 設定標題列
    hdr_cells = table.rows[0].cells
    hdr_cells[0].text = '風險等級'
    hdr_cells[1].text = '數量 (Count)'
    set_table_header_style(hdr_cells[0])
    set_table_header_style(hdr_cells[1])

    # 設定內容列 (帶顏色)
    def fill_row(row_idx, label, count, color_rgb=None):
        row_cells = table.rows[row_idx].cells
        run_label = row_cells[0].paragraphs[0].add_run(label)
        run_count = row_cells[1].paragraphs[0].add_run(str(count))
        
        run_label.bold = True
        run_count.bold = True
        if color_rgb:
            run_label.font.color.rgb = color_rgb
            run_count.font.color.rgb = color_rgb

    fill_row(1, "🔴 高風險 (High)", stats['High'], RGBColor(255, 0, 0))
    fill_row(2, "🟠 中風險 (Medium)", stats['Medium'], RGBColor(255, 165, 0)) # Orange
    fill_row(3, "🟡 低風險 (Low)", stats['Low'], RGBColor(200, 200, 0))   # Dark Yellow
    fill_row(4, "🔵 資訊 (Info)", stats['Informational'], RGBColor(0, 0, 255))

    doc.add_paragraph("") # 空行

    # 若有高風險，加入醒目提示
    if stats['High'] > 0:
        warning_p = doc.add_paragraph()
        run = warning_p.add_run(f"⚠️ 注意：系統存在 {stats['High']} 個高風險弱點，建議立即進行修復！")
        run.bold = True
        run.font.color.rgb = RGBColor(255, 0, 0)

    doc.add_page_break()

    # --- 3. 弱點詳情 ---
    doc.add_heading('2. 弱點詳情分析', level=1)

    for site in sites:
        alerts = site.get('alerts', [])
        if not alerts:
            doc.add_paragraph("未發現顯著弱點。")
            continue

        for alert in alerts:
            eng_name = alert.get('alert', 'Unknown Alert')
            risk_eng = alert.get('riskdesc', 'Info').split(' ')[0]
            desc = clean_html(alert.get('desc', ''))
            solution = clean_html(alert.get('solution', ''))
            
            tw_name = translate_title(eng_name)
            tw_risk = RISK_MAPPING.get(risk_eng, risk_eng)

            # 弱點標題
            doc.add_heading(tw_name, level=2)
            
            # 詳情表格
            det_table = doc.add_table(rows=4, cols=2)
            det_table.style = 'Table Grid'
            det_table.columns[0].width = Inches(1.5)
            det_table.columns[1].width = Inches(5.0)

            det_table.cell(0, 0).text = "弱點原名"
            det_table.cell(0, 1).text = eng_name

            det_table.cell(1, 0).text = "風險等級"
            run = det_table.cell(1, 1).paragraphs[0].add_run(tw_risk)
            run.bold = True
            if "High" in risk_eng: run.font.color.rgb = RGBColor(255, 0, 0)
            elif "Medium" in risk_eng: run.font.color.rgb = RGBColor(255, 165, 0)

            det_table.cell(2, 0).text = "弱點描述"
            det_table.cell(2, 1).text = desc

            det_table.cell(3, 0).text = "建議修復方式"
            det_table.cell(3, 1).text = solution

            doc.add_paragraph("")

    # 儲存
    try:
        doc.save(output_path)
        print(f"報告生成完畢！已儲存至: {output_path}")
    except Exception as e:
        print(f"儲存失敗: {e}")

if __name__ == "__main__":
    DATA_DIR = "/app/data"
    json_file = os.path.join(DATA_DIR, 'ZAP-Report.json')
    word_file = os.path.join(DATA_DIR, f'Scan_Report_{datetime.now().strftime("%Y%m%d")}.docx')
    
    if os.path.exists(json_file):
        generate_word_report(json_file, word_file, company_name="Nextlink MSP")
    else:
        print(f"找不到檔案: {json_file}")