"""
域名管理模块
管理特殊域名列表（走新加坡线路）
"""

import json
import re
from typing import List, Dict, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class DomainManager:
    """域名管理器"""
    
    SPECIAL_DOMAINS_FILE = "/etc/sing-box/special_domains.json"
    
    def __init__(self):
        self.domains_file = Path(self.SPECIAL_DOMAINS_FILE)
        self._ensure_file_exists()
    
    def _ensure_file_exists(self):
        """确保域名文件存在"""
        if not self.domains_file.exists():
            # 创建默认文件
            default_data = {
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
            self.domains_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.domains_file, 'w', encoding='utf-8') as f:
                json.dump(default_data, f, indent=2, ensure_ascii=False)
            logger.info("创建默认特殊域名文件")
    
    async def list_domains(self) -> List[Dict]:
        """列出所有特殊域名"""
        try:
            with open(self.domains_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            domains = []
            if "rules" in data and len(data["rules"]) > 0:
                domain_list = data["rules"][0].get("domain_suffix", [])
                for domain in domain_list:
                    domains.append({
                        "domain": domain,
                        "outbound": "wg-sg",
                        "comment": None
                    })
            
            return domains
            
        except Exception as e:
            logger.error(f"读取域名列表失败: {e}")
            raise
    
    async def add_domain(self, domain: str, comment: Optional[str] = None) -> bool:
        """添加域名
        
        Args:
            domain: 域名
            comment: 备注（暂不使用）
        
        Returns:
            True表示添加成功，False表示域名已存在
        """
        try:
            with open(self.domains_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 获取域名列表
            if "rules" not in data or len(data["rules"]) == 0:
                data["rules"] = [{"domain_suffix": []}]
            
            domain_list = data["rules"][0].get("domain_suffix", [])
            
            # 检查是否已存在
            if domain in domain_list:
                return False
            
            # 添加域名
            domain_list.append(domain)
            data["rules"][0]["domain_suffix"] = domain_list
            
            # 保存文件
            with open(self.domains_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"添加域名: {domain}")
            
            # sing-box 1.10.0+ 会自动检测文件变化并重载
            # 无需手动触发
            
            return True
            
        except Exception as e:
            logger.error(f"添加域名失败: {e}")
            raise
    
    async def delete_domain(self, domain: str) -> bool:
        """删除域名
        
        Args:
            domain: 域名
        
        Returns:
            True表示删除成功，False表示域名不存在
        """
        try:
            with open(self.domains_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 获取域名列表
            if "rules" not in data or len(data["rules"]) == 0:
                return False
            
            domain_list = data["rules"][0].get("domain_suffix", [])
            
            # 检查是否存在
            if domain not in domain_list:
                return False
            
            # 删除域名
            domain_list.remove(domain)
            data["rules"][0]["domain_suffix"] = domain_list
            
            # 保存文件
            with open(self.domains_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"删除域名: {domain}")
            
            # sing-box 1.10.0+ 会自动检测文件变化并重载
            
            return True
            
        except Exception as e:
            logger.error(f"删除域名失败: {e}")
            raise
    
    @staticmethod
    def validate_domain(domain: str) -> bool:
        """验证域名格式
        
        Args:
            domain: 域名
        
        Returns:
            True表示格式正确
        """
        # 简单的域名格式验证
        pattern = r'^([a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$'
        return bool(re.match(pattern, domain))
