# sing-box网关备用容器
# 最小化功能：DNS + NAT转发（直连外网）

FROM alpine:latest

LABEL maintainer="gateway-admin"
LABEL description="sing-box网关备用容器 - 最小化功能，应急使用"
LABEL version="1.0.0"

# 安装必要软件
RUN apk add --no-cache \
    dnsmasq \
    iptables \
    iproute2 \
    bash \
    && rm -rf /var/cache/apk/*

# 复制启动脚本
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# 暴露DNS端口
EXPOSE 53/udp

# 健康检查
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD pgrep dnsmasq || exit 1

# 启动
ENTRYPOINT ["/entrypoint.sh"]
