#!/bin/bash
# 部署sing-box网关容器

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 配置参数
PRIMARY_CONTAINER="singbox-gateway"
BACKUP_CONTAINER="simple-gateway"
PRIMARY_IP="192.168.9.201"
BACKUP_IP="192.168.9.202"
NETWORK="macvlan_net"
CONFIG_DIR="${SCRIPT_DIR}/config"

echo "========================================="
echo "  部署sing-box网关容器"
echo "========================================="

# 检查配置文件
echo ""
echo "1. 检查配置文件..."
if [ ! -f "${CONFIG_DIR}/config.json" ]; then
    echo "   ❌ 错误: 未找到 ${CONFIG_DIR}/config.json"
    echo "   请先准备sing-box配置文件"
    exit 1
fi
echo "   ✓ 配置文件存在"

# 检查macvlan网络
echo ""
echo "2. 检查macvlan网络..."
if ! docker network ls | grep -q "$NETWORK"; then
    echo "   ❌ 错误: macvlan网络 $NETWORK 不存在"
    echo "   请先创建macvlan网络"
    exit 1
fi
echo "   ✓ macvlan网络存在"

# 停止并删除旧容器
echo ""
echo "3. 清理旧容器..."
docker stop $PRIMARY_CONTAINER 2>/dev/null || true
docker rm $PRIMARY_CONTAINER 2>/dev/null || true
docker stop $BACKUP_CONTAINER 2>/dev/null || true
docker rm $BACKUP_CONTAINER 2>/dev/null || true
echo "   ✓ 旧容器已清理"

# 部署主容器
echo ""
echo "4. 部署主容器..."
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

echo "   ✓ 主容器已启动"
echo "   容器名: $PRIMARY_CONTAINER"
echo "   IP地址: $PRIMARY_IP"

# 部署备用容器
echo ""
echo "5. 部署备用容器..."
docker run -d \
  --name $BACKUP_CONTAINER \
  --network $NETWORK \
  --ip $BACKUP_IP \
  --cap-add NET_ADMIN \
  --sysctl net.ipv4.ip_forward=1 \
  --restart unless-stopped \
  simple-gateway:latest

echo "   ✓ 备用容器已启动"
echo "   容器名: $BACKUP_CONTAINER"
echo "   IP地址: $BACKUP_IP"

# 等待容器启动
echo ""
echo "6. 等待容器启动..."
sleep 5

# 检查容器状态
echo ""
echo "7. 检查容器状态..."
if docker ps | grep -q $PRIMARY_CONTAINER; then
    echo "   ✓ 主容器运行正常"
else
    echo "   ❌ 主容器启动失败"
    docker logs $PRIMARY_CONTAINER
    exit 1
fi

if docker ps | grep -q $BACKUP_CONTAINER; then
    echo "   ✓ 备用容器运行正常"
else
    echo "   ❌ 备用容器启动失败"
    docker logs $BACKUP_CONTAINER
    exit 1
fi

# 测试网络连通性
echo ""
echo "8. 测试网络连通性..."
if ping -c 2 $PRIMARY_IP > /dev/null 2>&1; then
    echo "   ✓ 主容器网络正常 ($PRIMARY_IP)"
else
    echo "   ⚠️  警告: 无法ping通主容器"
fi

if ping -c 2 $BACKUP_IP > /dev/null 2>&1; then
    echo "   ✓ 备用容器网络正常 ($BACKUP_IP)"
else
    echo "   ⚠️  警告: 无法ping通备用容器"
fi

echo ""
echo "========================================="
echo "  ✅ 部署完成"
echo "========================================="
echo ""
echo "访问信息:"
echo "  - Web管理界面: http://$PRIMARY_IP"
echo "  - API接口: http://$PRIMARY_IP:9091/docs"
echo "  - Clash API: http://$PRIMARY_IP:9090"
echo "  - SSH: ssh root@$PRIMARY_IP (密码: gateway2024)"
echo ""
echo "容器管理:"
echo "  - 查看日志: docker logs -f $PRIMARY_CONTAINER"
echo "  - 进入容器: docker exec -it $PRIMARY_CONTAINER bash"
echo "  - 重启容器: docker restart $PRIMARY_CONTAINER"
echo ""
echo "故障切换:"
echo "  - 切换到备用: ./failover.sh"
echo "  - 恢复主容器: ./restore.sh"
echo ""
