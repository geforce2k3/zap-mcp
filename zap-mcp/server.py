"""
ZAP MCP Server - 模組化主程式
OWASP ZAP 安全掃描 MCP 伺服器
"""
from mcp.server.fastmcp import FastMCP

# 初始化核心模組
from core import logger, setup_exception_handler
from core.config import MCP_SERVER_NAME

# 載入工具函數
from tools import (
    run_nmap_recon,
    perform_login_and_get_cookie,
    start_scan_job,
    check_status_and_generate_report,
    get_report_for_analysis,
    generate_report_with_ai_insights,
    retrieve_report
)

# 設定全局異常處理
setup_exception_handler()

logger.info("Starting ZAP MCP Server (Modular)...")

# 初始化 MCP Server
mcp = FastMCP(MCP_SERVER_NAME)


# ==========================================
# 註冊 MCP 工具
# ==========================================

@mcp.tool()
def nmap_recon(target_host: str, ports: str = "top-1000") -> str:
    """【流程第一步】執行 Nmap 埠口掃描，自動識別 Web 服務。"""
    return run_nmap_recon(target_host, ports)


@mcp.tool()
def login_and_get_cookie(
    login_url: str,
    username: str,
    password: str,
    username_field: str = "username",
    password_field: str = "password",
    submit_url: str = None
) -> str:
    """【輔助工具】執行自動登入並取得 Cookie。"""
    return perform_login_and_get_cookie(
        login_url, username, password,
        username_field, password_field, submit_url
    )


@mcp.tool()
def scan_job(
    target_url: str,
    scan_type: str = "baseline",
    aggressive: bool = False,
    auth_header: str = None,
    auth_value: str = None
) -> str:
    """【流程第二步】啟動 ZAP 弱點掃描任務。"""
    return start_scan_job(target_url, scan_type, aggressive, auth_header, auth_value)


@mcp.tool()
def check_status() -> str:
    """【流程第三步】檢查進度。若掃描中會提示等待；完成後自動產生 Word 報告。"""
    return check_status_and_generate_report()


@mcp.tool()
def get_analysis() -> str:
    """【流程第四步】讀取關鍵弱點 (High/Medium) 供 AI 分析。"""
    return get_report_for_analysis()


@mcp.tool()
def ai_insights(executive_summary: str, solutions: str) -> str:
    """【流程第五步】將 AI 建議注入並生成最終 Word 報告。"""
    return generate_report_with_ai_insights(executive_summary, solutions)


@mcp.tool()
def export_report() -> str:
    """【流程第六步】匯出所有報告檔案。"""
    return retrieve_report()

async def shutdown(signal, loop):
    logger.info(f"收到信號 {signal.name}，正在關閉伺服器...")
    loop.stop()

# ==========================================
# 主程式入口
# ==========================================

if __name__ == "__main__":
    try:
        mcp.run()
    except KeyboardInterrupt:
        logger.info("使用者強制停止")
    except Exception as e:
        logger.error(f"伺服器異常退出: {e}")