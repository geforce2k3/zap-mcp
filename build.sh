#!/bin/bash
set -e

echo "========================================"
echo "  ZAP MCP - 建置腳本 (模組化版本)"
echo "========================================"

# 顏色定義
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}[1/3]${NC} 正在建立共用 Volume..."
docker volume create zap_shared_data
echo -e "${GREEN}✓${NC} Volume 建立完成"

echo ""
echo -e "${YELLOW}[2/3]${NC} 正在建置 Reporter Image..."
docker build -f zap-reporter/Dockerfile.reporter -t zap-reporter:latest ./zap-reporter
echo -e "${GREEN}✓${NC} Reporter Image 建置完成"

echo ""
echo -e "${YELLOW}[3/3]${NC} 正在建置 MCP Server Image..."
docker build -f zap-mcp/Dockerfile.mcp -t zap-mcp-server:latest ./zap-mcp
echo -e "${GREEN}✓${NC} MCP Server Image 建置完成"

echo ""
echo "========================================"
echo -e "${GREEN}建置完成！${NC}"
echo "========================================"
echo ""
echo "可用映像檔:"
echo "  - zap-reporter:latest"
echo "  - zap-mcp-server:latest"
echo ""
echo "共用 Volume:"
echo "  - zap_shared_data"
