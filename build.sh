#!/bin/bash
# 构建sing-box网关镜像

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "========================================="
echo "  构建sing-box网关镜像"
echo "========================================="

# 构建主容器
echo ""
echo "1. 构建主容器镜像..."
cd primary
docker build -t singbox-gateway:v2.0 -t singbox-gateway:latest .
echo "   ✓ 主容器镜像构建完成"

# 构建备用容器
echo ""
echo "2. 构建备用容器镜像..."
cd ../backup
docker build -t simple-gateway:v1.0 -t simple-gateway:latest .
echo "   ✓ 备用容器镜像构建完成"

echo ""
echo "========================================="
echo "  ✅ 所有镜像构建完成"
echo "========================================="
echo ""
echo "镜像列表:"
docker images | grep -E "singbox-gateway|simple-gateway"
echo ""
echo "下一步:"
echo "  1. 准备sing-box配置文件（config.json）"
echo "  2. 运行 ./deploy.sh 部署容器"
echo ""
