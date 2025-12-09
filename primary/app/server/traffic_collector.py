"""
流量采集模块
使用iptables统计三条线路的流量
"""

import asyncio
import subprocess
import re
from datetime import datetime
from typing import Dict, Tuple
import logging

logger = logging.getLogger(__name__)

class TrafficCollector:
    """流量采集器"""
    
    # VPS地址和端口
    VPS8_ADDR = "49.235.186.64"  # 美国线路
    VPS8_PORT = "51823"
    VPS9_ADDR = "212.64.83.18"   # 新加坡线路
    VPS9_PORT = "51822"
    
    def __init__(self, database):
        self.db = database
        self.running = False
        self.task = None
        
        # 上一次的计数器值（用于计算增量）
        self.last_counters = {
            "total": 0,
            "us": 0,
            "sg": 0
        }
    
    async def start(self):
        """启动采集器"""
        if self.running:
            logger.warning("流量采集器已在运行")
            return
        
        self.running = True
        self.task = asyncio.create_task(self._collect_loop())
        logger.info("流量采集器已启动")
    
    async def stop(self):
        """停止采集器"""
        self.running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        logger.info("流量采集器已停止")
    
    async def _collect_loop(self):
        """采集循环"""
        # 等待系统启动完成
        await asyncio.sleep(10)
        
        while self.running:
            try:
                # 采集流量数据
                await self._collect_traffic()
                
                # 每分钟采集一次
                await asyncio.sleep(60)
                
                # 每小时更新一次小时统计
                if datetime.now().minute == 0:
                    await self.db.update_hourly_stats()
                    await self.db.cleanup_old_snapshots(hours=24)
                
                # 每天凌晨更新日统计
                if datetime.now().hour == 0 and datetime.now().minute == 0:
                    await self.db.update_daily_stats()
                    await self.db.cleanup_old_hourly_stats(days=7)
                    await self.db.cleanup_old_daily_stats(days=90)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"流量采集失败: {e}")
                await asyncio.sleep(60)
    
    async def _collect_traffic(self):
        """采集流量数据"""
        try:
            # 读取iptables计数器
            total_bytes, us_bytes, sg_bytes = await self._read_iptables_counters()
            
            # 计算增量（本分钟的流量）
            direct_bytes = max(0, total_bytes - us_bytes - sg_bytes)
            us_increment = max(0, us_bytes - self.last_counters["us"])
            sg_increment = max(0, sg_bytes - self.last_counters["sg"])
            direct_increment = max(0, direct_bytes - self.last_counters.get("direct", 0))
            
            # 保存快照
            await self.db.save_snapshot(
                direct_bytes=direct_increment,
                us_bytes=us_increment,
                sg_bytes=sg_increment
            )
            
            # 更新上一次的计数器
            self.last_counters = {
                "total": total_bytes,
                "us": us_bytes,
                "sg": sg_bytes,
                "direct": direct_bytes
            }
            
            logger.debug(f"流量采集: 直连={direct_increment}, 美国={us_increment}, 新加坡={sg_increment}")
            
        except Exception as e:
            logger.error(f"采集流量数据失败: {e}")
            raise
    
    async def _read_iptables_counters(self) -> Tuple[int, int, int]:
        """读取iptables计数器
        
        Returns:
            (总流量, 美国流量, 新加坡流量) 单位：字节
        """
        try:
            # 读取iptables统计
            result = subprocess.run(
                ["iptables", "-L", "OUTPUT", "-v", "-n", "-x"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode != 0:
                raise Exception(f"iptables命令失败: {result.stderr}")
            
            output = result.stdout
            
            # 解析输出
            total_bytes = self._parse_chain_bytes(output, "TRAFFIC_TOTAL")
            us_bytes = self._parse_chain_bytes(output, "TRAFFIC_US")
            sg_bytes = self._parse_chain_bytes(output, "TRAFFIC_SG")
            
            return total_bytes, us_bytes, sg_bytes
            
        except subprocess.TimeoutExpired:
            logger.error("iptables命令超时")
            raise
        except Exception as e:
            logger.error(f"读取iptables计数器失败: {e}")
            raise
    
    def _parse_chain_bytes(self, output: str, chain_name: str) -> int:
        """解析iptables输出中指定链的字节数
        
        Args:
            output: iptables -L -v -n -x 的输出
            chain_name: 链名称（如TRAFFIC_US）
        
        Returns:
            字节数
        """
        try:
            # 查找目标链的行
            # 格式: pkts bytes target prot opt in out source destination
            # 例如: 1234 567890 TRAFFIC_US all -- * * 0.0.0.0/0 49.235.186.64
            
            pattern = rf'\s+(\d+)\s+(\d+)\s+{chain_name}\s+'
            match = re.search(pattern, output)
            
            if match:
                bytes_count = int(match.group(2))
                return bytes_count
            else:
                logger.warning(f"未找到链 {chain_name} 的统计信息")
                return 0
                
        except Exception as e:
            logger.error(f"解析链 {chain_name} 失败: {e}")
            return 0
    
    @classmethod
    async def setup_iptables_rules(cls):
        """设置iptables规则（容器启动时调用）"""
        try:
            logger.info("正在设置iptables流量统计规则...")
            
            # 创建自定义链
            subprocess.run(["iptables", "-N", "TRAFFIC_US"], stderr=subprocess.DEVNULL)
            subprocess.run(["iptables", "-N", "TRAFFIC_SG"], stderr=subprocess.DEVNULL)
            subprocess.run(["iptables", "-N", "TRAFFIC_TOTAL"], stderr=subprocess.DEVNULL)
            
            # 清空链
            subprocess.run(["iptables", "-F", "TRAFFIC_US"])
            subprocess.run(["iptables", "-F", "TRAFFIC_SG"])
            subprocess.run(["iptables", "-F", "TRAFFIC_TOTAL"])
            
            # 添加规则（统计发往VPS的WireGuard流量）
            subprocess.run([
                "iptables", "-A", "OUTPUT",
                "-d", cls.VPS8_ADDR,
                "-p", "udp", "--dport", cls.VPS8_PORT,
                "-j", "TRAFFIC_US"
            ])
            
            subprocess.run([
                "iptables", "-A", "OUTPUT",
                "-d", cls.VPS9_ADDR,
                "-p", "udp", "--dport", cls.VPS9_PORT,
                "-j", "TRAFFIC_SG"
            ])
            
            # 统计所有出站流量
            subprocess.run([
                "iptables", "-A", "OUTPUT",
                "-j", "TRAFFIC_TOTAL"
            ])
            
            logger.info("iptables流量统计规则设置完成")
            
        except Exception as e:
            logger.error(f"设置iptables规则失败: {e}")
            raise
