"""
ZAP MCP Server 日誌配置
"""
import sys
import logging
import traceback

# 設定結構化日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    stream=sys.stderr
)

logger = logging.getLogger("ZAP-MCP")


def setup_exception_handler():
    """設定全局異常捕獲處理器"""
    def exception_handler(exc_type, exc_value, exc_traceback):
        error_msg = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
        logger.critical(f"Uncaught Exception: {error_msg}")
        sys.exit(1)

    sys.excepthook = exception_handler
