#!/bin/bash
set -e

echo "========================================="
echo "  sing-box网关容器启动中..."
echo "========================================="

# 1. 设置iptables流量统计规则
echo "1. 设置iptables流量统计规则..."
iptables -N TRAFFIC_US 2>/dev/null || iptables -F TRAFFIC_US
iptables -N TRAFFIC_SG 2>/dev/null || iptables -F TRAFFIC_SG
iptables -N TRAFFIC_TOTAL 2>/dev/null || iptables -F TRAFFIC_TOTAL

# 删除旧规则（如果存在）
iptables -D OUTPUT -d 49.235.186.64 -p udp --dport 51823 -j TRAFFIC_US 2>/dev/null || true
iptables -D OUTPUT -d 212.64.83.18 -p udp --dport 51822 -j TRAFFIC_SG 2>/dev/null || true
iptables -D OUTPUT -j TRAFFIC_TOTAL 2>/dev/null || true

# 添加新规则
iptables -A OUTPUT -d 49.235.186.64 -p udp --dport 51823 -j TRAFFIC_US
iptables -A OUTPUT -d 212.64.83.18 -p udp --dport 51822 -j TRAFFIC_SG
iptables -A OUTPUT -j TRAFFIC_TOTAL

echo "   ✓ iptables规则设置完成"

# 2. 确保目录存在
echo "2. 创建必要目录..."
mkdir -p /var/lib/sing-box
mkdir -p /var/log/supervisor
mkdir -p /var/www/html
mkdir -p /run/sshd

# 3. 复制前端文件
echo "3. 部署前端文件..."
cp /app/frontend/index.html /var/www/html/

# 4. 检查sing-box配置
echo "4. 检查sing-box配置..."
if [ ! -f "/etc/sing-box/config.json" ]; then
    echo "   ⚠️  警告: /etc/sing-box/config.json 不存在"
    echo "   请确保已挂载配置文件"
fi

# 5. 确保特殊域名文件存在
if [ ! -f "/etc/sing-box/special_domains.json" ]; then
    echo "   创建默认特殊域名文件..."
    cat > /etc/sing-box/special_domains.json <<'EOF'
{
  "version": 1,
  "rules": [
    {
      "domain_suffix": [
        "manus.im",
        "genspark.ai",
        "binance.com",
        "bybit.com",
        "okx.com"
      ]
    }
  ]
}
EOF
fi

# 6. 启动supervisor
echo "5. 启动服务..."
echo "========================================="
echo "  ✅ 容器启动完成"
echo "  - sing-box: 透明网关"
echo "  - FastAPI: http://0.0.0.0:9091"
echo "  - nginx: http://0.0.0.0:80"
echo "  - SSH: 端口22"
echo "========================================="

exec /usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf
