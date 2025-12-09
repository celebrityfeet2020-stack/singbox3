"""
数据库操作模块
使用SQLite存储流量统计数据
"""

import aiosqlite
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)

class Database:
    """数据库管理类"""
    
    def __init__(self, db_path: str = "/var/lib/sing-box/traffic.db"):
        self.db_path = db_path
        self.conn: Optional[aiosqlite.Connection] = None
    
    async def init_db(self):
        """初始化数据库"""
        self.conn = await aiosqlite.connect(self.db_path)
        self.conn.row_factory = aiosqlite.Row
        
        # 创建表
        await self.conn.executescript("""
            -- 实时快照表（每分钟一条，保留24小时）
            CREATE TABLE IF NOT EXISTS traffic_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                direct_bytes INTEGER DEFAULT 0,
                us_bytes INTEGER DEFAULT 0,
                sg_bytes INTEGER DEFAULT 0
            );
            
            -- 小时统计表（每小时一条，保留7天）
            CREATE TABLE IF NOT EXISTS hourly_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                hour DATETIME NOT NULL UNIQUE,
                direct_total INTEGER DEFAULT 0,
                us_total INTEGER DEFAULT 0,
                sg_total INTEGER DEFAULT 0
            );
            
            -- 日统计表（每天一条，保留90天）
            CREATE TABLE IF NOT EXISTS daily_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date DATE NOT NULL UNIQUE,
                direct_total INTEGER DEFAULT 0,
                us_total INTEGER DEFAULT 0,
                sg_total INTEGER DEFAULT 0
            );
            
            -- 创建索引
            CREATE INDEX IF NOT EXISTS idx_snapshots_timestamp ON traffic_snapshots(timestamp);
            CREATE INDEX IF NOT EXISTS idx_hourly_hour ON hourly_stats(hour);
            CREATE INDEX IF NOT EXISTS idx_daily_date ON daily_stats(date);
        """)
        
        await self.conn.commit()
        logger.info("数据库表创建完成")
    
    async def close(self):
        """关闭数据库连接"""
        if self.conn:
            await self.conn.close()
    
    # ==================== 快照操作 ====================
    
    async def save_snapshot(self, direct_bytes: int, us_bytes: int, sg_bytes: int):
        """保存流量快照"""
        await self.conn.execute("""
            INSERT INTO traffic_snapshots (timestamp, direct_bytes, us_bytes, sg_bytes)
            VALUES (?, ?, ?, ?)
        """, (datetime.now(), direct_bytes, us_bytes, sg_bytes))
        await self.conn.commit()
    
    async def get_latest_snapshot(self) -> Optional[Dict]:
        """获取最新的流量快照"""
        cursor = await self.conn.execute("""
            SELECT timestamp, direct_bytes, us_bytes, sg_bytes
            FROM traffic_snapshots
            ORDER BY timestamp DESC
            LIMIT 1
        """)
        row = await cursor.fetchone()
        if row:
            return dict(row)
        return None
    
    async def cleanup_old_snapshots(self, hours: int = 24):
        """清理旧的快照数据"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        await self.conn.execute("""
            DELETE FROM traffic_snapshots
            WHERE timestamp < ?
        """, (cutoff_time,))
        await self.conn.commit()
        logger.info(f"清理了{hours}小时前的快照数据")
    
    # ==================== 小时统计操作 ====================
    
    async def update_hourly_stats(self):
        """更新小时统计（聚合最近一小时的快照数据）"""
        current_hour = datetime.now().replace(minute=0, second=0, microsecond=0)
        
        # 聚合最近一小时的数据
        cursor = await self.conn.execute("""
            SELECT 
                COALESCE(SUM(direct_bytes), 0) as direct_total,
                COALESCE(SUM(us_bytes), 0) as us_total,
                COALESCE(SUM(sg_bytes), 0) as sg_total
            FROM traffic_snapshots
            WHERE timestamp >= ? AND timestamp < ?
        """, (current_hour, current_hour + timedelta(hours=1)))
        
        row = await cursor.fetchone()
        if row:
            # 插入或更新小时统计
            await self.conn.execute("""
                INSERT INTO hourly_stats (hour, direct_total, us_total, sg_total)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(hour) DO UPDATE SET
                    direct_total = excluded.direct_total,
                    us_total = excluded.us_total,
                    sg_total = excluded.sg_total
            """, (current_hour, row["direct_total"], row["us_total"], row["sg_total"]))
            await self.conn.commit()
            logger.info(f"更新小时统计: {current_hour}")
    
    async def get_hourly_stats(self, hours: int = 24) -> List[Dict]:
        """获取最近N小时的统计数据"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        cursor = await self.conn.execute("""
            SELECT hour, direct_total, us_total, sg_total
            FROM hourly_stats
            WHERE hour >= ?
            ORDER BY hour ASC
        """, (cutoff_time,))
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
    
    async def cleanup_old_hourly_stats(self, days: int = 7):
        """清理旧的小时统计"""
        cutoff_time = datetime.now() - timedelta(days=days)
        await self.conn.execute("""
            DELETE FROM hourly_stats
            WHERE hour < ?
        """, (cutoff_time,))
        await self.conn.commit()
        logger.info(f"清理了{days}天前的小时统计")
    
    # ==================== 日统计操作 ====================
    
    async def update_daily_stats(self):
        """更新日统计（聚合当天的小时统计）"""
        today = datetime.now().date()
        
        # 聚合当天的小时统计
        cursor = await self.conn.execute("""
            SELECT 
                COALESCE(SUM(direct_total), 0) as direct_total,
                COALESCE(SUM(us_total), 0) as us_total,
                COALESCE(SUM(sg_total), 0) as sg_total
            FROM hourly_stats
            WHERE DATE(hour) = ?
        """, (today,))
        
        row = await cursor.fetchone()
        if row:
            # 插入或更新日统计
            await self.conn.execute("""
                INSERT INTO daily_stats (date, direct_total, us_total, sg_total)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(date) DO UPDATE SET
                    direct_total = excluded.direct_total,
                    us_total = excluded.us_total,
                    sg_total = excluded.sg_total
            """, (today, row["direct_total"], row["us_total"], row["sg_total"]))
            await self.conn.commit()
            logger.info(f"更新日统计: {today}")
    
    async def get_daily_stats(self, days: int = 30) -> List[Dict]:
        """获取最近N天的统计数据"""
        cutoff_date = datetime.now().date() - timedelta(days=days)
        cursor = await self.conn.execute("""
            SELECT date, direct_total, us_total, sg_total
            FROM daily_stats
            WHERE date >= ?
            ORDER BY date ASC
        """, (cutoff_date,))
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
    
    async def cleanup_old_daily_stats(self, days: int = 90):
        """清理旧的日统计"""
        cutoff_date = datetime.now().date() - timedelta(days=days)
        await self.conn.execute("""
            DELETE FROM daily_stats
            WHERE date < ?
        """, (cutoff_date,))
        await self.conn.commit()
        logger.info(f"清理了{days}天前的日统计")
