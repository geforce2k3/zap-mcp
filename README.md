# ZAP MCP Server - OWASP ZAP 弱點掃描自動化工具

透過 MCP (Model Context Protocol) 整合 OWASP ZAP 弱點掃描工具，讓 AI 助理 (如 Claude Desktop、Kiro) 能夠直接執行網站安全掃描並產生正體中文報告。

## 功能特色

- 🔍 **自動化弱點掃描** - 支援 Baseline (快速) 與 Full (完整攻擊) 兩種掃描模式
- 🕷️ **Aggressive 模式** - 啟用 AJAX Spider、Alpha 規則與高強度攻擊
- 📊 **正體中文報告** - 自動產生 Word 格式報告，含風險統計圖表
- 🐳 **Docker 容器化** - 完全容器化部署，無需安裝額外依賴

## 系統需求

- Docker Desktop (macOS / Windows / Linux)
- Claude Desktop 或 Kiro IDE (支援 MCP 的 AI 客戶端)

## 專案結構

```
zap-auto/
├── build.sh                    # 一鍵建置腳本
├── README.md
├── zap-mcp/
│   ├── Dockerfile.mcp          # MCP Server 映像檔
│   └── zap_mcp_server.py       # MCP Server 主程式
└── zap-reporter/
    ├── Dockerfile.reporter     # 報告產生器映像檔
    ├── requirements.txt        # Python 依賴
    └── zap_report_gen.py       # Word 報告產生器
```

## 安裝步驟

### 1. 建置 Docker 映像檔

```bash
# 給予執行權限
chmod +x build.sh

# 執行建置腳本
./build.sh
```

這會自動：
- 建立共用 Docker Volume (`zap_shared_data`)
- 建置 `zap-reporter` 映像檔
- 建置 `zap-mcp-server` 映像檔

### 2. 建立報告輸出資料夾

```bash
mkdir -p ~/Documents/zap-output
```

### 3. 設定 MCP 客戶端

#### Claude Desktop

編輯 `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) 或對應路徑：

```json
{
  "mcpServers": {
    "zap-mcp": {
      "command": "docker",
      "args": [
        "run",
        "-i",
        "--rm",
        "-v", "/var/run/docker.sock:/var/run/docker.sock",
        "-v", "zap_shared_data:/app/data",
        "-v", "/Users/YOUR_USERNAME/Documents/zap-output:/output",
        "zap-mcp-server"
      ]
    }
  }
}
```

> ⚠️ 請將 `YOUR_USERNAME` 替換為你的使用者名稱

#### Kiro IDE

編輯 `~/.kiro/settings/mcp.json`：

```json
{
  "mcpServers": {
    "zap-mcp": {
      "command": "docker",
      "args": [
        "run",
        "-i",
        "--rm",
        "-v", "/var/run/docker.sock:/var/run/docker.sock",
        "-v", "zap_shared_data:/app/data",
        "-v", "/Users/YOUR_USERNAME/Documents/zap-output:/output",
        "zap-mcp-server"
      ]
    }
  }
}
```

### 4. 重啟 AI 客戶端

設定完成後，重新啟動 Claude Desktop 或 Kiro IDE 以載入 MCP Server。

## 使用方式

### 可用工具 (MCP Tools)

| 工具名稱 | 說明 |
|---------|------|
| `scan_job` | 【第一步】啟動 ZAP 弱點掃描任務 |
| `get_analysis` | 【第二步】檢查掃描進度，完成後產生報告 |
| `ai_insights` | 【第三步】將報告匯出到本機資料夾 |

### 操作流程

#### 步驟一：啟動掃描

對 AI 助理說：

```
請對 http://example.com 執行弱點掃描
```

或指定進階選項：

```
請對 http://example.com 執行 Full 掃描，並開啟 Aggressive 模式
```

**參數說明：**

| 參數 | 說明 | 預設值 |
|-----|------|-------|
| `target_url` | 目標網址 | (必填) |
| `scan_type` | `baseline` (快速) 或 `full` (完整攻擊) | `baseline` |
| `aggressive` | 是否啟用積極模式 | `false` |

**掃描模式比較：**

| 模式 | 說明 | 預估時間 |
|-----|------|---------|
| Baseline | 被動掃描，不會對目標發送攻擊請求 | 1-5 分鐘 |
| Full | 主動攻擊掃描，測試各種漏洞 | 10-60 分鐘 |
| Full + Aggressive | 含 AJAX Spider、Alpha 規則、高強度攻擊 | 30 分鐘 - 數小時 |

#### 步驟二：檢查進度

```
檢查掃描狀態
```

系統會回報目前進度：
- 🕷️ 正在進行爬蟲探索 (Spidering)
- 👀 正在進行被動掃描 (Passive Scanning)
- 🔥 正在進行主動攻擊掃描 (Active Scanning)

掃描完成後會自動產生報告並顯示摘要：

```
✅ 任務全部完成！
🔴 高風險: 2 | 🟠 中風險: 15
```

#### 步驟三：匯出報告

```
請匯出報告
```

報告會儲存至：
- **Word 報告**: `~/Documents/zap-output/Scan_Report_YYYYMMDD.docx`
- **JSON 原始資料**: `~/Documents/zap-output/ZAP-Report.json`

## 報告內容

產生的 Word 報告包含：

1. **封面** - 公司名稱、掃描工具、日期、目標網址
2. **掃描結果摘要** - 風險分佈圓餅圖、統計表格
3. **弱點詳情分析** - 每個弱點的：
   - 弱點名稱 (中英對照)
   - 風險等級 (以顏色標示)
   - 弱點描述
   - 建議修復方式

## 進階設定

### 自訂公司名稱

編輯 `zap-reporter/zap_report_gen.py`，修改 `company_name` 參數：

```python
generate_word_report(json_file, word_file, company_name="您的公司名稱")
```

### 新增 Logo

將 `logo.png` 放入 Docker Volume：

```bash
docker run --rm -v zap_shared_data:/data -v $(pwd):/src alpine cp /src/logo.png /data/
```

## 疑難排解

### MCP Server 無法連線

1. 確認 Docker Desktop 正在運行
2. 檢查 MCP 設定檔路徑是否正確
3. 重新建置映像檔：`./build.sh`
4. 重啟 AI 客戶端

### 掃描失敗

1. 確認目標網址可以正常存取
2. 檢查 Docker 容器 log：
   ```bash
   docker logs zap-scanner-job
   ```

### 報告無法匯出

1. 確認輸出資料夾存在：
   ```bash
   mkdir -p ~/Documents/zap-output
   ```
2. 檢查 Volume 內容：
   ```bash
   docker run --rm -v zap_shared_data:/data alpine ls -la /data
   ```

## 技術架構

```
┌─────────────────┐     MCP Protocol     ┌──────────────────┐
│  Claude/Kiro    │ ◄──────────────────► │  zap-mcp-server  │
│  (AI Client)    │                      │  (Docker)        │
└─────────────────┘                      └────────┬─────────┘
                                                  │
                                                  │ Docker API
                                                  ▼
                    ┌─────────────────────────────────────────┐
                    │              Docker Engine              │
                    │  ┌─────────────┐  ┌─────────────────┐  │
                    │  │ zaproxy/    │  │  zap-reporter   │  │
                    │  │ zap-stable  │  │  (Word 報告)    │  │
                    │  └──────┬──────┘  └────────┬────────┘  │
                    │         │                  │           │
                    │         ▼                  ▼           │
                    │  ┌─────────────────────────────────┐   │
                    │  │     zap_shared_data (Volume)    │   │
                    │  │  - ZAP-Report.json              │   │
                    │  │  - Scan_Report_YYYYMMDD.docx    │   │
                    │  └─────────────────────────────────┘   │
                    └─────────────────────────────────────────┘
```

## Prompt Example
```

你是一位資深的自動化滲透測試專家。你的任務是依照以下 SOP 對目標進行檢測:

【階段一:偵察 (Recon)】
1. 請對 http://nl-bwapp.turn2cloud.net 使用 `nmap_recon` 工具，並且強制重新掃描 force_rescan=True。
2. 分析回傳結果(xml)，找出所有的入口點，以及目標作業系統版本(web service 透露)，CVE清單。

【階段二:掃描策略 (Strategy)】
1. 請根據 nmap 掃描出的 port，透過上面提供的 FQDN 組合出各種連線方式，並寫入報告內。
2. 如果有登入的頁面,請調用 `login_and_get_cookie` 取得憑證。`帳號` bee `密碼` bug
3. 登入後的 URL - http://nl-bwapp.turn2cloud.net/portal.php
4. 若有 Cookie,準備在下一步呼叫時使用 `auth_header='Cookie'`。
5. 使用激進模式掃描: `scan_type='full', aggressive=True`。
6. 將組合後的連線方式與第三點提供的 URI，暫存起來,提供給階段三使用

【階段三:執行掃描 (Execution)】
1. 針對 階段二的 第 6 點的連線方式 呼叫 `scan_job`。
2. 透過 `check_status` 監控進度。

【階段四:分析與報告 (Reporting)】
1. 掃描完成後,務必呼叫 `get_analysis` 取得 Markdown 數據。
2. 請運用你的資安知識,針對讀取到的弱點進行深度分析(不要只複述數據)。
   - 分析漏洞的潛在影響 (Business Impact)。
   - 提供具體的程式碼修復範例 (Code Fix)。
3. 將你的分析總結 (Executive Summary) 與詳細修復建議 (Solutions JSON),傳入 `ai_insights` 工具。
4. 最後,執行 `export_report` 下載圖文並茂的 Docx 報告。


* 重要規則:在生成 solutions JSON 時,Key (鍵) 必須嚴格使用掃描報告中的「英文弱點原名 (English Alert Name)」,絕對不要翻譯成中文,也不要自行簡化。Value (值) 的內容則請使用繁體中文撰寫。

範例指令:

「請分析報告並產生 solutions JSON。請注意:JSON 的 Key 必須是 "Absence of Anti-CSRF Tokens" 這樣的英文原名,不要寫成 "CSRF 缺失"。內容請用中文。」

```


## 授權聲明

本專案使用 MIT License。

OWASP ZAP 為開源專案，請參考 [OWASP ZAP 官方網站](https://www.zaproxy.org/)。

## 貢獻

歡迎提交 Issue 或 Pull Request！
