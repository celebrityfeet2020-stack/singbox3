"""
sing-box网关管理后端API
提供流量统计、域名管理、系统状态查询等功能
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime, timedelta
import asyncio
import logging

from .database import Database
from .traffic_collector import TrafficCollector
from .domain_manager import DomainManager

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 创建FastAPI应用
app = FastAPI(
    title="sing-box网关管理API",
    description="提供流量统计、域名管理等功能",
    version="2.0.0"
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 初始化组件
db = Database()
traffic_collector = TrafficCollector(db)
domain_manager = DomainManager()

# ==================== 数据模型 ====================

class TrafficSnapshot(BaseModel):
    """流量快照"""
    timestamp: datetime
    direct_bytes: int = Field(ge=0, description="直连流量（字节）")
    us_bytes: int = Field(ge=0, description="美国线路流量（字节）")
    sg_bytes: int = Field(ge=0, description="新加坡线路流量（字节）")

class TrafficStats(BaseModel):
    """流量统计"""
    time: str = Field(description="时间（小时或日期）")
    direct_total: int = Field(ge=0, description="直连总流量（字节）")
    us_total: int = Field(ge=0, description="美国总流量（字节）")
    sg_total: int = Field(ge=0, description="新加坡总流量（字节）")

class DomainItem(BaseModel):
    """域名项"""
    domain: str = Field(description="域名")
    outbound: str = Field(default="wg-sg", description="出站标签")
    comment: Optional[str] = Field(default=None, description="备注")

class DomainAddRequest(BaseModel):
    """添加域名请求"""
    domain: str = Field(description="域名")
    comment: Optional[str] = Field(default=None, description="备注")

class SystemStatus(BaseModel):
    """系统状态"""
    status: str
    uptime: str
    container_ip: str
    sing_box_version: str
    services: dict

# ==================== 启动和关闭事件 ====================

@app.on_event("startup")
async def startup_event():
    """应用启动时执行"""
    logger.info("正在启动sing-box网关管理API...")
    
    # 初始化数据库
    await db.init_db()
    logger.info("数据库初始化完成")
    
    # 启动流量采集器
    asyncio.create_task(traffic_collector.start())
    logger.info("流量采集器已启动")
    
    logger.info("API服务启动完成")

@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时执行"""
    logger.info("正在关闭API服务...")
    await traffic_collector.stop()
    await db.close()
    logger.info("API服务已关闭")

# ==================== 健康检查 ====================

@app.get("/api/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    }

# ==================== 流量统计API ====================

@app.get("/api/traffic/realtime", response_model=TrafficSnapshot)
async def get_realtime_traffic():
    """获取实时流量"""
    try:
        snapshot = await db.get_latest_snapshot()
        if not snapshot:
            return TrafficSnapshot(
                timestamp=datetime.now(),
                direct_bytes=0,
                us_bytes=0,
                sg_bytes=0
            )
        return snapshot
    except Exception as e:
        logger.error(f"获取实时流量失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/traffic/hourly", response_model=List[TrafficStats])
async def get_hourly_traffic(hours: int = 24):
    """获取小时级流量统计
    
    Args:
        hours: 获取最近N小时的数据，默认24小时
    """
    try:
        if hours < 1 or hours > 168:  # 最多7天
            raise HTTPException(status_code=400, detail="hours参数必须在1-168之间")
        
        stats = await db.get_hourly_stats(hours)
        return [
            TrafficStats(
                time=s["hour"].strftime("%H:00") if isinstance(s["hour"], datetime) else s["hour"],
                direct_total=s["direct_total"],
                us_total=s["us_total"],
                sg_total=s["sg_total"]
            )
            for s in stats
        ]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取小时流量失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/traffic/daily", response_model=List[TrafficStats])
async def get_daily_traffic(days: int = 30):
    """获取日级流量统计
    
    Args:
        days: 获取最近N天的数据，默认30天
    """
    try:
        if days < 1 or days > 90:
            raise HTTPException(status_code=400, detail="days参数必须在1-90之间")
        
        stats = await db.get_daily_stats(days)
        return [
            TrafficStats(
                time=s["date"].strftime("%m/%d") if isinstance(s["date"], datetime) else s["date"],
                direct_total=s["direct_total"],
                us_total=s["us_total"],
                sg_total=s["sg_total"]
            )
            for s in stats
        ]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取日流量失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ==================== 域名管理API ====================

@app.get("/api/domains", response_model=List[DomainItem])
async def list_domains():
    """列出所有特殊域名"""
    try:
        domains = await domain_manager.list_domains()
        return domains
    except Exception as e:
        logger.error(f"列出域名失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/domains")
async def add_domain(request: DomainAddRequest):
    """添加特殊域名"""
    try:
        # 验证域名格式
        if not domain_manager.validate_domain(request.domain):
            raise HTTPException(status_code=400, detail="域名格式不正确")
        
        # 添加域名
        success = await domain_manager.add_domain(
            request.domain,
            comment=request.comment
        )
        
        if not success:
            raise HTTPException(status_code=409, detail="域名已存在")
        
        logger.info(f"添加域名成功: {request.domain}")
        return {
            "success": True,
            "message": "域名添加成功",
            "domain": request.domain
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"添加域名失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/domains/{domain}")
async def delete_domain(domain: str):
    """删除特殊域名"""
    try:
        success = await domain_manager.delete_domain(domain)
        
        if not success:
            raise HTTPException(status_code=404, detail="域名不存在")
        
        logger.info(f"删除域名成功: {domain}")
        return {
            "success": True,
            "message": "域名删除成功",
            "domain": domain
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除域名失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ==================== 系统状态API ====================

@app.get("/api/status", response_model=SystemStatus)
async def get_system_status():
    """获取系统状态"""
    try:
        import subprocess
        import socket
        
        # 获取容器IP
        hostname = socket.gethostname()
        container_ip = socket.gethostbyname(hostname)
        
        # 获取sing-box版本
        try:
            result = subprocess.run(
                ["sing-box", "version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            version_line = result.stdout.split('\n')[0]
            sing_box_version = version_line.split()[2] if len(version_line.split()) > 2 else "unknown"
        except:
            sing_box_version = "unknown"
        
        # 获取服务状态
        services = {
            "sing-box": "running",
            "fastapi": "running",
            "nginx": "running"
        }
        
        # 获取系统运行时间
        try:
            with open('/proc/uptime', 'r') as f:
                uptime_seconds = float(f.readline().split()[0])
                uptime = str(timedelta(seconds=int(uptime_seconds)))
        except:
            uptime = "unknown"
        
        return SystemStatus(
            status="running",
            uptime=uptime,
            container_ip=container_ip,
            sing_box_version=sing_box_version,
            services=services
        )
    except Exception as e:
        logger.error(f"获取系统状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ==================== 根路径 ====================

@app.get("/")
async def root():
    """根路径"""
    return {
        "name": "sing-box网关管理API",
        "version": "2.0.0",
        "docs": "/docs"
    }
