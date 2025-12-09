# sing-box网关主容器
# 基于官方sing-box镜像，添加完整管理功能

FROM ghcr.io/sagernet/sing-box:latest

LABEL maintainer="gateway-admin"
LABEL description="sing-box网关主容器 - 包含Web管理、流量统计、域名管理"
LABEL version="2.0.0"

# 安装系统依赖
RUN apk add --no-cache \
    # 基础工具
    bash \
    curl \
    wget \
    jq \
    # 网络工具
    iptables \
    iproute2 \
    net-tools \
    # SSH
    openssh-server \
    openssh-client \
    sshpass \
    # Web服务器
    nginx \
    # Python和依赖
    python3 \
    py3-pip \
    # 进程管理
    supervisor \
    # 数据库
    sqlite \
    # Python编译依赖
    gcc \
    musl-dev \
    python3-dev \
    libffi-dev \
    openssl-dev \
    cargo \
    && rm -rf /var/cache/apk/*

# 安装Python包
RUN pip3 install --no-cache-dir \
    fastapi==0.104.1 \
    uvicorn[standard]==0.24.0 \
    pydantic==2.5.0 \
    aiosqlite==0.19.0 \
    httpx==0.25.2 \
    python-multipart==0.0.6

# 创建必要目录
RUN mkdir -p \
    /app/server \
    /app/frontend \
    /app/scripts \
    /etc/sing-box \
    /var/lib/sing-box \
    /var/log/supervisor \
    /var/www/html \
    /run/sshd

# 复制应用代码
COPY app/server/ /app/server/
COPY app/scripts/ /app/scripts/
COPY frontend/ /app/frontend/

# 复制配置文件
COPY config/supervisor/supervisord.conf /etc/supervisor/conf.d/supervisord.conf
COPY config/nginx/default.conf /etc/nginx/http.d/default.conf

# 设置权限
RUN chmod +x /app/scripts/*.sh && \
    chmod 755 /var/www/html && \
    chmod 700 /run/sshd

# 配置SSH
RUN sed -i 's/#PermitRootLogin.*/PermitRootLogin yes/' /etc/ssh/sshd_config && \
    sed -i 's/#PasswordAuthentication.*/PasswordAuthentication yes/' /etc/ssh/sshd_config && \
    echo 'root:gateway2024' | chpasswd

# 暴露端口
EXPOSE 53/udp
EXPOSE 80/tcp
EXPOSE 22/tcp
EXPOSE 9090/tcp
EXPOSE 9091/tcp

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost/health || exit 1

# 工作目录
WORKDIR /app

# 启动脚本
ENTRYPOINT ["/app/scripts/entrypoint.sh"]
