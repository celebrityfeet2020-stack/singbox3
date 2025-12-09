#!/bin/bash
set -e

echo "========================================="
echo "  简单网关容器启动中..."
echo "========================================="

# 启动DNS服务
echo "1. 启动DNS服务..."
dnsmasq \
  --no-daemon \
  --listen-address=0.0.0.0 \
  --server=114.114.114.114 \
  --server=223.5.5.5 \
  --cache-size=1000 \
  --log-queries \
  --log-facility=- &

# 等待网络接口就绪
sleep 2

# 配置NAT转发
echo "2. 配置NAT转发..."
iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE
iptables -A FORWARD -m state --state RELATED,ESTABLISHED -j ACCEPT
iptables -A FORWARD -j ACCEPT

echo "========================================="
echo "  ✅ 简单网关已启动"
echo "  DNS: 114.114.114.114, 223.5.5.5"
echo "  NAT: 已启用（直连外网）"
echo "========================================="

# 保持运行
tail -f /dev/null
