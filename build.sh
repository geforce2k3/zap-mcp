#!/bin/bash
echo "正在建立共用 Volume..."
docker volume create zap_shared_data

echo "正在建置 Reporter Image..."
docker build -f zap-reporter/Dockerfile.reporter -t zap-reporter ./zap-reporter

echo "正在建置 MCP Server Image..."
docker build -f zap-mcp/Dockerfile.mcp -t zap-mcp-server ./zap-mcp

echo "建置完成！"
