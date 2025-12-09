#!/bin/bash
# 网关故障切换脚本
# 将备用容器切换到主IP，接管网关功能

set -e

PRIMARY_CONTAINER="singbox-gateway"
BACKUP_CONTAINER="simple-gateway"
GATEWAY_IP="192.168.9.201"
BACKUP_IP="192.168.9.202"
NETWORK="macvlan_net"

echo "========================================="
echo "  网关故障切换"
echo "========================================="

# 1. 停止主容器
echo "1. 停止主容器 ($PRIMARY_CONTAINER)..."
docker stop $PRIMARY_CONTAINER 2>/dev/null || echo "   主容器已停止或不存在"

# 2. 等待端口释放
echo "2. 等待端口释放..."
sleep 2

# 3. 断开备用容器的当前网络
echo "3. 断开备用容器的网络连接..."
docker network disconnect $NETWORK $BACKUP_CONTAINER 2>/dev/null || true

# 4. 重新连接备用容器到主IP
echo "4. 将备用容器切换到 $GATEWAY_IP..."
docker network connect $NETWORK $BACKUP_CONTAINER --ip $GATEWAY_IP

# 5. 验证
echo "5. 验证切换结果..."
sleep 2

if ping -c 2 $GATEWAY_IP > /dev/null 2>&1; then
    echo ""
    echo "========================================="
    echo "  ✅ 切换成功！"
    echo "========================================="
    echo "  网关IP: $GATEWAY_IP"
    echo "  当前容器: $BACKUP_CONTAINER (备用)"
    echo "  功能: 直连外网（不走VPN）"
    echo "========================================="
    echo ""
    echo "📋 客户端无需任何操作，网关已恢复"
    echo ""
else
    echo ""
    echo "========================================="
    echo "  ❌ 切换失败！"
    echo "========================================="
    echo "  请手动检查容器状态:"
    echo "    docker ps"
    echo "    docker logs $BACKUP_CONTAINER"
    echo ""
    exit 1
fi
