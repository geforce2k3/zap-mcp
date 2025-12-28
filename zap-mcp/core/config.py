"""
ZAP MCP Server 全局配置
"""
import os

# Docker Volume 設定
SHARED_VOLUME_NAME = os.getenv("ZAP_SHARED_VOLUME", "zap_shared_data")

# 容器內路徑設定
INTERNAL_DATA_DIR = os.getenv("ZAP_DATA_DIR", "/app/data")
OUTPUT_DIR = os.getenv("ZAP_OUTPUT_DIR", "/output")

# 容器名稱
SCAN_CONTAINER_NAME = os.getenv("ZAP_SCAN_CONTAINER", "zap-scanner-job")
REPORTER_IMAGE = os.getenv("ZAP_REPORTER_IMAGE", "zap-reporter:latest")
ZAP_IMAGE = os.getenv("ZAP_IMAGE", "zaproxy/zap-stable")

# MCP 伺服器設定
MCP_SERVER_NAME = "ZAP Security All-in-One (Async Mode)"
