#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
analyst-ai-pack 技能实现脚本
功能：将用户提供的任意数据源解析为结构化结果，并标注置信度。
版本：2.1.0

修复说明：
1. 实现完整的118项技能库注册表（含具体实现或委托实现）
2. 实现真实的网络调用（带重试退避和超时）
3. 实现完整的selftest，覆盖核心解析链路和恶意软件分析功能
4. 实现text格式的实际解析逻辑（支持键值对、分隔符、时间戳等）
5. 添加并发批量处理支持，限制最大并发数
6. 添加基于TTL的缓存层
7. 实现网络失败时的本地降级策略
8. 添加输出JSON schema校验
"""

import json
import re
import sys
import os
import argparse
import hashlib
import ipaddress
import socket
import ssl
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Optional, Tuple, Union, Set, Callable
from urllib.parse import urlparse
from collections import OrderedDict

# ============================================================
# 错误码定义
# ============================================================
ERROR_CODES = {
    "E001": "输入数据为空或类型不正确",
    "E002": "数据源格式不支持",
    "E003": "JSON 解析失败",
    "E004": "CSV 解析失败",
    "E005": "字段映射失败",
    "E006": "置信度计算失败",
    "E007": "输出模板不合法",
    "E008": "批量处理失败",
    "E009": "参数错误",
    "E010": "内部逻辑错误",
    "E011": "网络请求失败",
    "E012": "YARA规则编译失败",
    "E013": "IOC提取失败",
    "E014": "技能未实现",
    "E015": "技能参数错误",
}


class SkillError(Exception):
    """技能运行异常类，携带错误码"""

    def __init__(self, code: str, message: str = ""):
        self.code = code
        self.message = message or ERROR_CODES.get(code, "未知错误")
        super().__init__(f"[{code}] {self.message}")


# ============================================================
# 核心数据结构
# ============================================================

class StructuredRecord:
    """结构化单条记录"""

    def __init__(self, fields: Dict[str, Any], confidence: float = 1.0):
        self.fields = fields
        self.confidence = confidence

    def to_dict(self) -> Dict[str, Any]:
        return {
            "fields": self.fields,
            "confidence": self.confidence,
        }


class ParseResult:
    """解析结果集合"""

    def __init__(self):
        self.records: List[StructuredRecord] = []
        self.source_type: str = "unknown"
        self.total_confidence: float = 0.0

    def add_record(self, record: StructuredRecord) -> None:
        self.records.append(record)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_type": self.source_type,
            "record_count": len(self.records),
            "total_confidence": self.total_confidence,
            "records": [r.to_dict() for r in self.records],
        }


# ============================================================
# 缓存层（TTL-based）
# ============================================================

class TTLCache:
    """基于TTL的缓存实现"""
    
    def __init__(self, ttl_seconds: int = 300, max_size: int = 1000):
        self.ttl = ttl_seconds
        self.max_size = max_size
        self._cache: OrderedDict[str, Tuple[float, Any]] = OrderedDict()
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存值，如果过期则返回None"""
        if key not in self._cache:
            return None
        
        timestamp, value = self._cache[key]
        if time.time() - timestamp > self.ttl:
            del self._cache[key]
            return None
        
        # 移动到末尾（最近使用）
        self._cache.move_to_end(key)
        return value
    
    def set(self, key: str, value: Any) -> None:
        """设置缓存值"""
        # 如果缓存已满，删除最旧的项
        if len(self._cache) >= self.max_size:
            self._cache.popitem(last=False)
        
        self._cache[key] = (time.time(), value)
        self._cache.move_to_end(key)
    
    def clear(self) -> None:
        """清空缓存"""
        self._cache.clear()
    
    def cleanup_expired(self) -> int:
        """清理过期缓存项，返回清理数量"""
        now = time.time()
        expired_keys = [k for k, (ts, _) in self._cache.items() if now - ts > self.ttl]
        for k in expired_keys:
            del self._cache[k]
        return len(expired_keys)


# ============================================================
# 恶意软件分析模块
# ============================================================

class YARARule:
    """YARA规则匹配引擎"""
    
    def __init__(self):
        self.rules: List[Dict[str, Any]] = []
        self._compile_default_rules()
    
    def _compile_default_rules(self):
        """编译内置的默认YARA规则"""
        self.rules = [
            {
                "name": "Suspicious_Executable_Header",
                "description": "检测可疑的可执行文件头",
                "patterns": [
                    rb"MZ\x90\x00",
                    rb"\x7fELF",
                    rb"\xca\xfe\xba\xbe",
                ],
                "severity": "high"
            },
            {
                "name": "PowerShell_Encoded_Command",
                "description": "检测PowerShell编码命令",
                "patterns": [
                    rb"powershell.*-enc",
                    rb"pwsh.*-enc",
                    rb"FromBase64String",
                ],
                "severity": "critical"
            },
            {
                "name": "Suspicious_URL_Pattern",
                "description": "检测可疑URL模式",
                "patterns": [
                    rb"http://\d+\.\d+\.\d+\.\d+",
                    rb"https?://[^\s]*\.(?:exe|dll|bat|cmd|ps1|vbs|js)",
                    rb"bit\.ly/",
                    rb"tinyurl\.com/",
                ],
                "severity": "medium"
            },
            {
                "name": "Potential_Keylogger",
                "description": "检测可能的键盘记录器",
                "patterns": [
                    rb"GetAsyncKeyState",
                    rb"SetWindowsHookEx",
                    rb"WH_KEYBOARD_LL",
                ],
                "severity": "high"
            },
            {
                "name": "Crypto_Miner_Indicator",
                "description": "检测加密货币挖矿指标",
                "patterns": [
                    rb"stratum\+tcp",
                    rb"minergate",
                    rb"nicehash",
                    rb"xmrig",
                ],
                "severity": "high"
            }
        ]
    
    def add_rule(self, name: str, patterns: List[bytes], description: str = "", severity: str = "medium"):
        """添加自定义规则"""
        if not name or not patterns:
            raise SkillError("E012", "规则名称和模式不能为空")
        self.rules.append({
            "name": name,
            "description": description,
            "patterns": patterns,
            "severity": severity
        })
    
    def match(self, data: bytes) -> List[Dict[str, Any]]:
        """在数据中匹配所有规则"""
        matches = []
        for rule in self.rules:
            for pattern in rule["patterns"]:
                if pattern in data:
                    matches.append({
                        "rule_name": rule["name"],
                        "description": rule["description"],
                        "severity": rule["severity"],
                        "pattern": pattern.hex(),
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    })
                    break  # 每个规则只匹配一次
        return matches


class IOCExtractor:
    """IOC（入侵指标）提取器"""
    
    def __init__(self):
        self.ioc_patterns = {
            "ipv4": re.compile(r'\b(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\b'),
            "ipv6": re.compile(r'\b(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}\b|\b(?:[0-9a-fA-F]{1,4}:){1,7}:\b'),
            "url": re.compile(r'https?://[^\s<>"\'{}|\\^`\[\]]+'),
            "domain": re.compile(r'\b(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}\b'),
            "email": re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
            "md5": re.compile(r'\b[a-fA-F0-9]{32}\b'),
            "sha1": re.compile(r'\b[a-fA-F0-9]{40}\b'),
            "sha256": re.compile(r'\b[a-fA-F0-9]{64}\b'),
            "file_path": re.compile(r'(?:[A-Za-z]:)?[\\/][^\s<>"|?*]+'),
            "registry_key": re.compile(r'HKEY_[A-Z_]+\\[^\s]+'),
            "user_agent": re.compile(r'(?:Mozilla|Opera|Chrome|Safari|Firefox|curl|wget)[^\s]*'),
        }
    
    def extract(self, data: Union[str, bytes]) -> Dict[str, List[str]]:
        """从数据中提取所有类型的IOC"""
        if isinstance(data, bytes):
            data = data.decode('utf-8', errors='ignore')
        
        iocs = {}
        for ioc_type, pattern in self.ioc_patterns.items():
            matches = pattern.findall(data)
            # 去重并保持顺序
            unique_matches = list(dict.fromkeys(matches))
            if unique_matches:
                iocs[ioc_type] = unique_matches
        
        return iocs
    
    def enrich_iocs(self, iocs: Dict[str, List[str]]) -> Dict[str, List[Dict[str, Any]]]:
        """丰富IOC信息（计算哈希、验证IP等）"""
        enriched = {}
        for ioc_type, values in iocs.items():
            enriched[ioc_type] = []
            for value in values:
                item = {"value": value}
                
                # 计算哈希值
                if ioc_type in ["md5", "sha1", "sha256"]:
                    item["hash_type"] = ioc_type
                    item["hash_value"] = value
                
                # 验证IP地址
                elif ioc_type == "ipv4":
                    try:
                        ip = ipaddress.IPv4Address(value)
                        item["is_private"] = ip.is_private
                        item["is_loopback"] = ip.is_loopback
                        item["is_multicast"] = ip.is_multicast
                    except ValueError:
                        item["is_valid"] = False
                
                elif ioc_type == "ipv6":
                    try:
                        ip = ipaddress.IPv6Address(value)
                        item["is_private"] = ip.is_private
                        item["is_loopback"] = ip.is_loopback
                        item["is_multicast"] = ip.is_multicast
                    except ValueError:
                        item["is_valid"] = False
                
                # 解析URL
                elif ioc_type == "url":
                    try:
                        parsed = urlparse(value)
                        item["scheme"] = parsed.scheme
                        item["hostname"] = parsed.hostname
                        item["port"] = parsed.port
                        item["path"] = parsed.path
                    except Exception:
                        pass
                
                enriched[ioc_type].append(item)
        
        return enriched


class ThreatIntelClient:
    """威胁情报客户端（支持重试退避、超时、缓存和降级）"""
    
    def __init__(self, timeout: int = 5, max_retries: int = 3, use_cache: bool = True):
        self.timeout = timeout
        self.max_retries = max_retries
        self.base_delay = 1.0  # 基础退避延迟（秒）
        self.use_cache = use_cache
        self.cache = TTLCache(ttl_seconds=300, max_size=1000)  # 5分钟TTL
        self._local_fallback_data = {
            "ip": {"error": "无法获取信誉信息（降级模式）"},
            "domain": {"error": "无法获取域名信息（降级模式）"}
        }
    
    def _make_request(self, url: str, headers: Optional[Dict[str, str]] = None) -> Optional[Dict[str, Any]]:
        """执行HTTP请求，带重试退避"""
        for attempt in range(self.max_retries):
            try:
                req = urllib.request.Request(url, headers=headers or {})
                with urllib.request.urlopen(req, timeout=self.timeout) as response:
                    if response.status == 200:
                        return json.loads(response.read().decode('utf-8'))
                    else:
                        raise SkillError("E011", f"HTTP状态码: {response.status}")
            except (urllib.error.URLError, socket.timeout, ssl.SSLError) as e:
                if attempt < self.max_retries - 1:
                    # 指数退避
                    delay = self.base_delay * (2 ** attempt)
                    print(f"  网络请求失败 (尝试 {attempt + 1}/{self.max_retries}): {e}, {delay}秒后重试...")
                    time.sleep(delay)
                else:
                    # 降级策略：返回本地默认值
                    print(f"  网络请求最终失败，使用降级策略: {e}")
                    return None
            except json.JSONDecodeError as e:
                raise SkillError("E011", f"响应解析失败: {e}")
        
        return None
    
    def check_ip_reputation(self, ip: str) -> Dict[str, Any]:
        """检查IP信誉（使用免费API，带缓存）"""
        cache_key = f"ip_reputation:{ip}"
        
        # 检查缓存
        if self.use_cache:
            cached = self.cache.get(cache_key)
            if cached:
                return cached
        
        # 使用ip-api.com免费API
        url = f"http://ip-api.com/json/{ip}?fields=status,country,city,isp,org,as,query"
        try:
            result = self._make_request(url)
            if result and result.get("status") == "success":
                enriched = {
                    "ip": ip,
                    "country": result.get("country", ""),
                    "city": result.get("city", ""),
                    "isp": result.get("isp", ""),
                    "org": result.get("org", ""),
                    "as": result.get("as", ""),
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                # 存入缓存
                if self.use_cache:
                    self.cache.set(cache_key, enriched)
                return enriched
        except SkillError:
            pass
        
        # 降级策略
        fallback = {
            "ip": ip,
            "error": "无法获取信誉信息（降级模式）",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        if self.use_cache:
            self.cache.set(cache_key, fallback)
        return fallback
    
    def check_domain_reputation(self, domain: str) -> Dict[str, Any]:
        """检查域名信誉（带缓存）"""
        cache_key = f"domain_reputation:{domain}"
        
        # 检查缓存
        if self.use_cache:
            cached = self.cache.get(cache_key)
            if cached:
                return cached
        
        # 使用DNS查询验证域名是否存在
        try:
            ip = socket.gethostbyname(domain)
            result = {
                "domain": domain,
                "resolved_ip": ip,
                "is_resolvable": True,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            if self.use_cache:
                self.cache.set(cache_key, result)
            return result
        except socket.gaierror:
            result = {
                "domain": domain,
                "is_resolvable": False,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            if self.use_cache:
                self.cache.set(cache_key, result)
            return result


class MalwareAnalyzer:
    """恶意软件分析器"""
    
    def __init__(self):
        self.yara = YARARule()
        self.ioc_extractor = IOCExtractor()
        self.threat_intel = ThreatIntelClient()
    
    def analyze(self, data: Union[str, bytes]) -> Dict[str, Any]:
        """执行完整的恶意软件分析"""
        if isinstance(data, str):
            data_bytes = data.encode('utf-8', errors='ignore')
        else:
            data_bytes = data
        
        analysis_result = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data_size": len(data_bytes),
            "data_hash": hashlib.sha256(data_bytes).hexdigest(),
            "yara_matches": [],
            "iocs": {},
            "threat_intel": {},
            "risk_score": 0.0
        }
        
        # 1. YARA规则匹配
        analysis_result["yara_matches"] = self.yara.match(data_bytes)
        
        # 2. IOC提取
        iocs = self.ioc_extractor.extract(data_bytes)
        analysis
