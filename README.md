# sing-box网关Docker镜像

> 基于sing-box的透明网关系统，支持双WireGuard隧道智能分流、Web管理、流量统计

## 📦 镜像说明

### 主容器（singbox-gateway:v2.0）

**完整功能网关**，包含：

- ✅ sing-box透明网关（最新版1.12.12+）
- ✅ 双WireGuard隧道（美国/新加坡）
- ✅ 智能分流（rule-set热更新）
- ✅ Web管理界面
- ✅ 流量统计（三线路分别统计）
- ✅ 特殊域名管理（热重载）
- ✅ FastAPI后端
- ✅ SSH访问

**镜像大小**: ~500MB  
**内存占用**: ~200MB  
**启动时间**: ~10秒

### 备用容器（simple-gateway:v1.0）

**最小化应急网关**，包含：

- ✅ DNS服务（dnsmasq）
- ✅ NAT转发（直连外网）
- ✅ 极简设计

**镜像大小**: ~50MB  
**内存占用**: ~10MB  
**启动时间**: ~2秒

---

## 🚀 快速开始

### 1. 准备配置文件

创建`config/config.json`（sing-box配置）：

```bash
mkdir -p config
cp primary/config/sing-box/config.json.template config/config.json
```

**重要**：修改`config.json`中的WireGuard密钥：

```json
{
  "outbounds": [
    {
      "type": "wireguard",
      "tag": "wg-us",
      "private_key": "替换为实际的私钥",
      "peer_public_key": "替换为VPS8的公钥"
    },
    {
      "type": "wireguard",
      "tag": "wg-sg",
      "private_key": "替换为实际的私钥",
      "peer_public_key": "替换为VPS9的公钥"
    }
  ]
}
```

### 2. 构建镜像

```bash
./build.sh
```

### 3. 部署容器

```bash
./deploy.sh
```

### 4. 访问管理界面

浏览器打开：`http://192.168.9.201`

---

## 📊 功能说明

### Web管理界面

访问 `http://192.168.9.201` 可以：

1. **查看流量统计**
   - 实时流量（直连/美国/新加坡）
   - 24小时流量趋势图
   - 30天流量趋势图

2. **管理特殊域名**
   - 添加域名（走新加坡线路）
   - 删除域名
   - 实时生效（无需重启）

### API接口

FastAPI文档：`http://192.168.9.201:9091/docs`

**主要端点**：

```
GET  /api/traffic/realtime      # 实时流量
GET  /api/traffic/hourly?hours=24  # 小时统计
GET  /api/traffic/daily?days=30    # 日统计
GET  /api/domains                # 域名列表
POST /api/domains                # 添加域名
DELETE /api/domains/{domain}     # 删除域名
```

### Clash API

访问：`http://192.168.9.201:9090`

---

## 🔧 容器管理

### 查看日志

```bash
# 主容器
docker logs -f singbox-gateway

# 备用容器
docker logs -f simple-gateway
```

### 进入容器

```bash
# SSH方式
ssh root@192.168.9.201  # 密码: gateway2024

# Docker方式
docker exec -it singbox-gateway bash
```

### 重启容器

```bash
docker restart singbox-gateway
```

### 查看容器状态

```bash
docker ps | grep gateway
```

---

## 🔄 故障切换

### 切换到备用网关

当主容器故障时，执行：

```bash
./failover.sh
```

**效果**：
- 停止主容器
- 备用容器接管192.168.9.201
- 客户端无感知切换
- **注意**：备用网关只提供直连（不走VPN）

### 恢复主容器

修复主容器后，执行：

```bash
./restore.sh
```

**效果**：
- 启动主容器（192.168.9.201）
- 备用容器回到192.168.9.202
- VPN功能恢复

---

## 📁 目录结构

```
gateway-docker/
├── primary/                    # 主容器
│   ├── Dockerfile
│   ├── app/
│   │   ├── server/            # FastAPI后端
│   │   │   ├── main.py
│   │   │   ├── database.py
│   │   │   ├── traffic_collector.py
│   │   │   └── domain_manager.py
│   │   └── scripts/
│   │       └── entrypoint.sh
│   ├── frontend/              # Web前端
│   │   └── index.html
│   ├── config/                # 配置文件
│   │   ├── sing-box/
│   │   ├── supervisor/
│   │   └── nginx/
│   └── requirements.txt
│
├── backup/                    # 备用容器
│   ├── Dockerfile
│   └── entrypoint.sh
│
├── config/                    # 运行时配置
│   └── config.json           # sing-box配置（需手动创建）
│
├── build.sh                  # 构建脚本
├── deploy.sh                 # 部署脚本
├── failover.sh               # 故障切换脚本
├── restore.sh                # 恢复脚本
└── README.md                 # 本文档
```

---

## ⚙️ 高级配置

### 修改容器IP

编辑`deploy.sh`：

```bash
PRIMARY_IP="192.168.9.201"  # 修改主容器IP
BACKUP_IP="192.168.9.202"   # 修改备用容器IP
```

### 修改SSH密码

编辑`primary/Dockerfile`：

```dockerfile
RUN echo 'root:你的密码' | chpasswd
```

### 自定义流量统计间隔

编辑`primary/app/server/traffic_collector.py`：

```python
COLLECT_INTERVAL = 60  # 修改为你想要的秒数
```

### 修改数据保留策略

编辑`primary/app/server/database.py`：

```python
SNAPSHOT_RETENTION_HOURS = 24   # 快照保留时间
HOURLY_RETENTION_DAYS = 7       # 小时统计保留天数
DAILY_RETENTION_DAYS = 90       # 日统计保留天数
```

---

## 🐛 故障排查

### 容器无法启动

```bash
# 查看日志
docker logs singbox-gateway

# 检查配置文件
cat config/config.json | jq .

# 检查网络
docker network ls | grep macvlan
```

### 无法访问Web界面

```bash
# 检查nginx状态
docker exec singbox-gateway supervisorctl status nginx

# 检查端口
docker exec singbox-gateway netstat -tlnp | grep 80

# 测试连通性
curl http://192.168.9.201/health
```

### 流量统计不准确

```bash
# 检查iptables规则
docker exec singbox-gateway iptables -L TRAFFIC_US -v -n

# 检查数据库
docker exec singbox-gateway sqlite3 /var/lib/traffic.db "SELECT * FROM traffic_snapshots ORDER BY timestamp DESC LIMIT 10;"

# 重启流量采集
docker exec singbox-gateway supervisorctl restart fastapi
```

### WireGuard连接失败

```bash
# 检查sing-box日志
docker exec singbox-gateway tail -f /var/log/supervisor/sing-box.log

# 检查配置
docker exec singbox-gateway sing-box check -c /etc/sing-box/config.json

# 测试连通性
docker exec singbox-gateway ping -c 3 49.235.186.64  # VPS8
docker exec singbox-gateway ping -c 3 212.64.83.18   # VPS9
```

---

## 📝 更新日志

### v2.0.0 (2024-12-09)

- ✅ 基于sing-box最新版本（1.12.12+）
- ✅ 支持rule-set热更新
- ✅ 新增Web管理界面
- ✅ 新增流量统计功能
- ✅ 新增特殊域名管理
- ✅ 优化容器启动流程
- ✅ 新增备用网关

---

## 📄 许可证

MIT License

---

## 🙏 致谢

- [sing-box](https://github.com/SagerNet/sing-box) - 核心网关
- [FastAPI](https://fastapi.tiangolo.com/) - 后端框架
- [Chart.js](https://www.chartjs.org/) - 图表库

---

## 📮 联系方式

如有问题，请联系管理员。
