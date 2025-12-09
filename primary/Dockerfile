# sing-box网关主容器 - 多阶段构建版本
# 阶段1: Python环境准备
# 阶段2: 最终镜像组装

# ============================================================
# 阶段1: Python环境构建
# ============================================================
FROM python:3.11-alpine AS python-builder

LABEL stage="python-builder"

# 安装Python编译依赖
RUN apk add --no-cache \
    gcc \
    musl-dev \
    libffi-dev \
    openssl-dev \
    cargo \
    rust

# 安装Python包到独立目录
RUN pip3 install --no-cache-dir --prefix=/python-install \
    fastapi \
    "uvicorn[standard]" \
    pydantic \
    aiosqlite \
    httpx \
    python-multipart

# ============================================================
# 阶段2: 最终镜像
# ============================================================
FROM ghcr.io/sagernet/sing-box:latest

LABEL maintainer="gateway-admin"
LABEL description="sing-box网关主容器 - 包含Web管理、流量统计、域名管理"
LABEL version="3.0.0"
LABEL architecture="amd64"

# 从python-builder复制Python环境
COPY --from=python-builder /python-install /usr/local

# 安装系统依赖（不包含Python编译工具）
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
    # Python运行时
    python3 \
    # 进程管理
    supervisor \
    # 数据库
    sqlite \
    && rm -rf /var/cache/apk/*

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
