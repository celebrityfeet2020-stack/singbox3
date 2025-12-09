#!/bin/bash
# 网关恢复脚本
# 恢复主容器到主IP，备用容器回到备用IP

set -e

PRIMARY_CONTAINER="singbox-gateway"
BACKUP_CONTAINER="simple-gateway"
PRIMARY_IP="192.168.9.201"
BACKUP_IP="192.168.9.202"
NETWORK="macvlan_net"
CONFIG_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/config"

echo "========================================="
echo "  恢复主容器"
echo "========================================="

# 1. 断开备用容器的网络
echo "1. 断开备用容器的网络连接..."
docker network disconnect $NETWORK $BACKUP_CONTAINER 2>/dev/null || true

# 2. 等待端口释放
echo "2. 等待端口释放..."
sleep 2

# 3. 启动主容器
echo "3. 启动主容器..."
docker start $PRIMARY_CONTAINER 2>/dev/null || {
    echo "   主容器不存在，重新创建..."
    docker run -d \
      --name $PRIMARY_CONTAINER \
      --network $NETWORK \
      --ip $PRIMARY_IP \
      --cap-add NET_ADMIN \
      --cap-add NET_RAW \
      --sysctl net.ipv4.ip_forward=1 \
      --sysctl net.ipv4.conf.all.src_valid_mark=1 \
      --device /dev/net/tun \
      --restart unless-stopped \
      -v "${CONFIG_DIR}/config.json:/etc/sing-box/config.json:ro" \
      -v singbox-data:/var/lib/sing-box \
      singbox-gateway:latest
}

# 4. 等待主容器启动
echo "4. 等待主容器启动..."
sleep 10

# 5. 恢复备用容器到备用IP
echo "5. 恢复备用容器到备用IP..."
docker network connect $NETWORK $BACKUP_CONTAINER --ip $BACKUP_IP

# 6. 验证
echo "6. 验证恢复结果..."
sleep 2

PRIMARY_OK=false
BACKUP_OK=false

if ping -c 2 $PRIMARY_IP > /dev/null 2>&1; then
    PRIMARY_OK=true
    echo "   ✓ 主容器网络正常 ($PRIMARY_IP)"
else
    echo "   ❌ 主容器网络异常"
fi

if ping -c 2 $BACKUP_IP > /dev/null 2>&1; then
    BACKUP_OK=true
    echo "   ✓ 备用容器网络正常 ($BACKUP_IP)"
else
    echo "   ❌ 备用容器网络异常"
fi

if [ "$PRIMARY_OK" = true ] && [ "$BACKUP_OK" = true ]; then
    echo ""
    echo "========================================="
    echo "  ✅ 恢复成功！"
    echo "========================================="
    echo "  主容器: $PRIMARY_IP (sing-box网关)"
    echo "  备用容器: $BACKUP_IP (简单网关)"
    echo "========================================="
    echo ""
    echo "📋 网关已恢复正常，VPN功能已启用"
    echo ""
else
    echo ""
    echo "========================================="
    echo "  ⚠️  恢复部分成功"
    echo "========================================="
    echo "  请手动检查容器状态:"
    echo "    docker ps"
    echo "    docker logs $PRIMARY_CONTAINER"
    echo "    docker logs $BACKUP_CONTAINER"
    echo ""
fi
