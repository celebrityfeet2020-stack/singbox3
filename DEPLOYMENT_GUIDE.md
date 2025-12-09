# sing-box网关部署指南

## 📋 部署前准备

### 1. 系统要求

- Docker 20.10+
- Docker Compose 2.0+（可选）
- 操作系统：Ubuntu 20.04+ / Debian 11+
- 内存：至少4GB
- 磁盘：至少10GB可用空间

### 2. 网络要求

- macvlan网络已创建
- 可用IP：192.168.9.201（主容器）、192.168.9.202（备用容器）
- 能够访问VPS8（49.235.186.64）和VPS9（212.64.83.18）

### 3. 准备WireGuard密钥

从现有容器获取密钥：

```bash
# 在D5上执行
docker exec singbox-gateway cat /etc/sing-box/config.json | jq '.outbounds[] | select(.type=="wireguard")'
```

记录以下信息：
- D5容器的私钥（private_key）
- VPS8的公钥（peer_public_key）
- VPS9的公钥（peer_public_key）

---

## 🚀 部署步骤

### 步骤1：解压文件

```bash
cd /home/double5090
tar -xzf singbox-gateway-docker-v2.0.tar.gz
cd gateway-docker
```

### 步骤2：准备配置文件

```bash
# 复制模板
cp primary/config/sing-box/config.json.template config/config.json

# 编辑配置文件
nano config/config.json
```

**必须修改的地方**：

1. WireGuard密钥（两处）：

```json
{
  "outbounds": [
    {
      "type": "wireguard",
      "tag": "wg-us",
      "server": "49.235.186.64",
      "server_port": 51823,
      "local_address": ["10.99.98.3/24"],
      "private_key": "替换为D5的私钥",
      "peer_public_key": "替换为VPS8的公钥",
      "mtu": 1420
    },
    {
      "type": "wireguard",
      "tag": "wg-sg",
      "server": "212.64.83.18",
      "server_port": 51822,
      "local_address": ["10.99.99.3/24"],
      "private_key": "替换为D5的私钥",
      "peer_public_key": "替换为VPS9的公钥",
      "mtu": 1420
    }
  ]
}
```

### 步骤3：构建镜像

```bash
./build.sh
```

**预计时间**：5-10分钟（取决于网络速度）

**输出示例**：
```
========================================
  构建sing-box网关镜像
========================================

1. 构建主容器镜像...
   ✓ 主容器镜像构建完成

2. 构建备用容器镜像...
   ✓ 备用容器镜像构建完成

========================================
  ✅ 所有镜像构建完成
========================================
```

### 步骤4：部署容器

```bash
./deploy.sh
```

**预计时间**：30秒

**输出示例**：
```
========================================
  部署sing-box网关容器
========================================

1. 检查配置文件...
   ✓ 配置文件存在

2. 检查macvlan网络...
   ✓ macvlan网络存在

3. 清理旧容器...
   ✓ 旧容器已清理

4. 部署主容器...
   ✓ 主容器已启动
   容器名: singbox-gateway
   IP地址: 192.168.9.201

5. 部署备用容器...
   ✓ 备用容器已启动
   容器名: simple-gateway
   IP地址: 192.168.9.202

========================================
  ✅ 部署完成
========================================
```

### 步骤5：验证部署

#### 5.1 检查容器状态

```bash
docker ps | grep gateway
```

应该看到两个容器都在运行。

#### 5.2 检查网络连通性

```bash
ping -c 3 192.168.9.201
ping -c 3 192.168.9.202
```

#### 5.3 访问Web界面

浏览器打开：`http://192.168.9.201`

应该看到网关管理界面。

#### 5.4 检查WireGuard连接

```bash
docker exec singbox-gateway sing-box version
docker logs singbox-gateway | grep -i wireguard
```

应该看到WireGuard连接成功的日志。

---

## 🔧 配置macvlan-shim（如果需要）

如果D5宿主机无法访问容器，需要配置macvlan-shim：

```bash
# 在D5宿主机上执行
sudo ip link add macvlan-shim link enp7s0 type macvlan mode bridge
sudo ip addr add 192.168.9.254/32 dev macvlan-shim
sudo ip link set macvlan-shim up
sudo ip route add 192.168.9.201/32 dev macvlan-shim
sudo ip route add 192.168.9.202/32 dev macvlan-shim
```

**持久化**（添加到`/etc/rc.local`）：

```bash
sudo nano /etc/rc.local
```

添加：
```bash
#!/bin/bash
ip link add macvlan-shim link enp7s0 type macvlan mode bridge
ip addr add 192.168.9.254/32 dev macvlan-shim
ip link set macvlan-shim up
ip route add 192.168.9.201/32 dev macvlan-shim
ip route add 192.168.9.202/32 dev macvlan-shim
exit 0
```

设置权限：
```bash
sudo chmod +x /etc/rc.local
```

---

## 📊 功能测试

### 测试1：流量统计

1. 访问 `http://192.168.9.201`
2. 应该看到三条线路的流量统计
3. 等待1-2分钟，刷新页面，数据应该更新

### 测试2：特殊域名管理

1. 在Web界面添加域名：`test.example.com`
2. 检查配置文件：
   ```bash
   docker exec singbox-gateway cat /etc/sing-box/special_domains.json
   ```
3. 应该看到新添加的域名
4. 删除域名，再次检查，域名应该消失

### 测试3：API接口

```bash
# 获取实时流量
curl http://192.168.9.201:9091/api/traffic/realtime

# 获取域名列表
curl http://192.168.9.201:9091/api/domains
```

### 测试4：故障切换

```bash
# 切换到备用网关
./failover.sh

# 检查网关IP
ping -c 3 192.168.9.201

# 恢复主网关
./restore.sh

# 再次检查
ping -c 3 192.168.9.201
```

---

## 🔄 从旧容器迁移

### 方案1：停机迁移（推荐）

1. 停止旧容器：
   ```bash
   docker stop singbox-gateway
   ```

2. 备份旧容器数据：
   ```bash
   docker cp singbox-gateway:/etc/sing-box/config.json ./old_config.json
   ```

3. 部署新容器（使用旧配置）

4. 验证新容器正常后，删除旧容器：
   ```bash
   docker rm singbox-gateway
   ```

### 方案2：无缝切换

1. 先在192.168.9.202测试新容器：
   ```bash
   # 修改deploy.sh中的IP
   PRIMARY_IP="192.168.9.202"
   
   # 部署
   ./deploy.sh
   ```

2. 测试新容器功能

3. 确认无问题后，切换IP：
   ```bash
   # 停止旧容器
   docker stop singbox-gateway-old
   
   # 断开新容器网络
   docker network disconnect macvlan_net singbox-gateway
   
   # 重新连接到.201
   docker network connect macvlan_net singbox-gateway --ip 192.168.9.201
   ```

---

## 🐛 常见问题

### Q1: 构建镜像时提示"无法拉取基础镜像"

**原因**：网络问题或Docker Hub访问受限

**解决**：
```bash
# 配置Docker镜像加速
sudo nano /etc/docker/daemon.json
```

添加：
```json
{
  "registry-mirrors": [
    "https://mirror.ccs.tencentyun.com"
  ]
}
```

重启Docker：
```bash
sudo systemctl restart docker
```

### Q2: 容器启动失败，提示"权限不足"

**原因**：缺少必要的capabilities

**解决**：确保deploy.sh中包含：
```bash
--cap-add NET_ADMIN \
--cap-add NET_RAW \
```

### Q3: Web界面无法访问

**检查步骤**：
```bash
# 1. 检查nginx状态
docker exec singbox-gateway supervisorctl status nginx

# 2. 检查端口监听
docker exec singbox-gateway netstat -tlnp | grep 80

# 3. 检查防火墙
sudo iptables -L | grep 80

# 4. 测试健康检查
curl http://192.168.9.201/health
```

### Q4: 流量统计显示为0

**检查步骤**：
```bash
# 1. 检查iptables规则
docker exec singbox-gateway iptables -L TRAFFIC_US -v -n

# 2. 检查数据库
docker exec singbox-gateway ls -lh /var/lib/traffic.db

# 3. 检查FastAPI日志
docker logs singbox-gateway | grep fastapi

# 4. 手动触发采集
docker exec singbox-gateway supervisorctl restart fastapi
```

### Q5: WireGuard连接失败

**检查步骤**：
```bash
# 1. 检查配置文件
docker exec singbox-gateway sing-box check -c /etc/sing-box/config.json

# 2. 检查网络连通性
docker exec singbox-gateway ping -c 3 49.235.186.64

# 3. 检查sing-box日志
docker logs singbox-gateway | grep -i error

# 4. 验证密钥
docker exec singbox-gateway cat /etc/sing-box/config.json | jq '.outbounds[] | select(.type=="wireguard")'
```

---

## 📞 技术支持

如遇到无法解决的问题，请提供以下信息：

1. 系统信息：
   ```bash
   uname -a
   docker version
   ```

2. 容器日志：
   ```bash
   docker logs singbox-gateway > gateway.log
   ```

3. 网络配置：
   ```bash
   docker network inspect macvlan_net > network.json
   ```

4. 错误截图或描述

---

## 🎉 部署完成

恭喜！sing-box网关已成功部署。

**下一步**：
- 配置客户端设备使用192.168.9.201作为网关
- 监控流量统计
- 根据需要添加特殊域名

**享受高速、稳定的网络体验！** 🚀
