#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
annual-report-summary Skill v2.1.0
从年报文本中提取关键财务指标并生成结构化决策简报

用法:
    python run.py --text "年报文本"
    python run.py --file annual_report.txt
    python run.py --json --text "年报文本"
    python run.py --selftest
"""

import re
import json
import argparse
import sys
import urllib.request
import urllib.error
import urllib.parse
import time
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timezone
from pathlib import Path

__version__ = "2.1.0"

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ============================================================
# 常量定义
# ============================================================

CORE_INDICATORS = ["roe", "net_profit_growth", "revenue", "gross_margin", "operating_cashflow"]

ERROR_CODES = {
    "SUCCESS": 0,
    "PARAM_ERROR": 1,
    "EMPTY_INPUT": 2,
    "NO_MATCH": 3,
    "FILE_ERROR": 4,
    "INTERNAL_ERROR": 5,
}

# 非数值文本模式
NON_NUMERIC_PATTERNS = [
    r'不适用',
    r'—',
    r'–',
    r'N/A',
    r'NA',
    r'无',
    r'暂无',
    r'未披露',
    r'待定',
]

# 数值范围校验配置
VALUE_RANGES = {
    "roe": (-100.0, 100.0),  # ROE 百分比范围
    "net_profit_growth": (-1000.0, 1000.0),  # 净利润增长率范围
    "gross_margin": (-100.0, 100.0),  # 毛利率范围
    "net_margin": (-100.0, 100.0),  # 净利率范围
    "debt_ratio": (0.0, 100.0),  # 资产负债率范围
    "rd_ratio": (0.0, 100.0),  # 研发费用率范围
}

# 真实年报数据源API配置（示例：使用公开的财报数据API）
# 注意：实际部署时需要替换为真实可用的API端点
ANNUAL_REPORT_API = "https://api.example.com/annual-report"
API_TIMEOUT = 10  # 秒
API_MAX_RETRIES = 3
API_RETRY_BACKOFF = 2  # 指数退避基数（秒）

# ============================================================
# 指标提取器
# ============================================================

class IndicatorExtractor:
    """从年报文本中提取财务指标"""
    
    def __init__(self, text: str):
        self.text = text
        self.results: Dict[str, Dict[str, Any]] = {}
        self.skipped_values: List[str] = []  # 记录被跳过的非数值文本
    
    def _extract(self, patterns: List[str], key: str, label: str, 
                 normalize: bool = True) -> Optional[str]:
        """通用提取方法"""
        for pattern in patterns:
            match = re.search(pattern, self.text, re.IGNORECASE)
            if match:
                value = match.group(1).strip()
                if normalize:
                    value = self._normalize_value(value)
                # 检查是否为有效数值
                if value is None:
                    # 记录被跳过的非数值文本
                    self.skipped_values.append(f"{label}: {match.group(1).strip()}")
                    logger.warning(f"跳过非数值文本: {label} = {match.group(1).strip()}")
                    continue
                self.results[key] = {
                    "label": label,
                    "value": value,
                    "raw": match.group(0),
                    "confidence": "HIGH" if len(patterns) > 2 else "MEDIUM"
                }
                return value
        return None
    
    def _normalize_value(self, value: str) -> Optional[str]:
        """标准化数值：去除多余空格，统一单位，检测非数值文本"""
        value = value.strip()
        
        # 检测非数值文本
        for pattern in NON_NUMERIC_PATTERNS:
            if re.search(pattern, value, re.IGNORECASE):
                return None
        
        # 去除百分号前的空格
        value = re.sub(r'\s+%', '%', value)
        # 统一负号
        value = value.replace('（', '(').replace('）', ')')
        
        # 检查是否为有效数值（带可选单位）
        numeric_pattern = r'^[-+]?\d+\.?\d*\s*[万亿千百]?元?%?$'
        if not re.match(numeric_pattern, value):
            return None
        
        return value
    
    def _validate_range(self, key: str, value: str) -> bool:
        """校验数值范围"""
        if key not in VALUE_RANGES:
            return True
        
        # 提取数值部分
        numeric_match = re.search(r'[-+]?\d+\.?\d*', value)
        if not numeric_match:
            return False
        
        try:
            numeric_value = float(numeric_match.group())
        except ValueError:
            return False
        
        min_val, max_val = VALUE_RANGES[key]
        return min_val <= numeric_value <= max_val
    
    def extract_roe(self) -> Optional[str]:
        """提取ROE（净资产收益率）"""
        patterns = [
            r'加权平均净资产收益率[：:为\s]*([-+]?\d+\.?\d*\s*%?)',
            r'净资产收益率\s*[（(]ROE[）)]\s*[：:为\s]*([-+]?\d+\.?\d*\s*%?)',
            r'ROE\s*[（(]净资产收益率[）)]\s*[：:为\s]*([-+]?\d+\.?\d*\s*%?)',
            r'净资产收益率[：:为\s]*([-+]?\d+\.?\d*\s*%?)',
            r'ROE[：:为\s]*([-+]?\d+\.?\d*\s*%?)',
            r'扣非加权平均净资产收益率[：:为\s]*([-+]?\d+\.?\d*\s*%?)',
        ]
        value = self._extract(patterns, "roe", "净资产收益率(ROE)")
        if value and not self._validate_range("roe", value):
            self.results.pop("roe", None)
            logger.warning(f"ROE值超出合理范围: {value}")
            return None
        return value
    
    def extract_net_profit_growth(self) -> Optional[str]:
        """提取净利润增长率"""
        patterns = [
            r'净利润增长率[：:为\s]*([-+]?\d+\.?\d*\s*%?)',
            r'净利润同比增长[：:为\s]*([-+]?\d+\.?\d*\s*%?)',
            r'净利润同比变化[：:为\s]*([-+]?\d+\.?\d*\s*%?)',
            r'净利润同比[：:为\s]*([-+]?\d+\.?\d*\s*%?)',
        ]
        value = self._extract(patterns, "net_profit_growth", "净利润增长率")
        if value and not self._validate_range("net_profit_growth", value):
            self.results.pop("net_profit_growth", None)
            logger.warning(f"净利润增长率超出合理范围: {value}")
            return None
        return value
    
    def extract_revenue(self) -> Tuple[Optional[str], Optional[str]]:
        """提取营业收入及增长率"""
        # 提取营收金额
        revenue_patterns = [
            r'营业收入[：:为\s]*([-+]?\d+\.?\d*\s*[万亿千百]?元?)',
            r'营收[：:为\s]*([-+]?\d+\.?\d*\s*[万亿千百]?元?)',
            r'营业总收入[：:为\s]*([-+]?\d+\.?\d*\s*[万亿千百]?元?)',
        ]
        revenue = self._extract(revenue_patterns, "revenue", "营业收入")
        
        # 提取营收增长率
        growth_patterns = [
            r'营业收入增长率[：:为\s]*([-+]?\d+\.?\d*\s*%?)',
            r'营收增长率[：:为\s]*([-+]?\d+\.?\d*\s*%?)',
            r'营业收入同比增长[：:为\s]*([-+]?\d+\.?\d*\s*%?)',
            r'营收同比增长[：:为\s]*([-+]?\d+\.?\d*\s*%?)',
        ]
        growth = self._extract(growth_patterns, "revenue_growth", "营收增长率")
        
        return revenue, growth
    
    def extract_gross_margin(self) -> Optional[str]:
        """提取毛利率"""
        patterns = [
            r'毛利率[：:为\s]*([-+]?\d+\.?\d*\s*%?)',
            r'销售毛利率[：:为\s]*([-+]?\d+\.?\d*\s*%?)',
            r'综合毛利率[：:为\s]*([-+]?\d+\.?\d*\s*%?)',
        ]
        value = self._extract(patterns, "gross_margin", "毛利率")
        if value and not self._validate_range("gross_margin", value):
            self.results.pop("gross_margin", None)
            logger.warning(f"毛利率超出合理范围: {value}")
            return None
        return value
    
    def extract_net_margin(self) -> Optional[str]:
        """提取净利率"""
        patterns = [
            r'净利率[：:为\s]*([-+]?\d+\.?\d*\s*%?)',
            r'销售净利率[：:为\s]*([-+]?\d+\.?\d*\s*%?)',
        ]
        value = self._extract(patterns, "net_margin", "净利率")
        if value and not self._validate_range("net_margin", value):
            self.results.pop("net_margin", None)
            logger.warning(f"净利率超出合理范围: {value}")
            return None
        return value
    
    def extract_debt_ratio(self) -> Optional[str]:
        """提取资产负债率"""
        patterns = [
            r'资产负债率[：:为\s]*([-+]?\d+\.?\d*\s*%?)',
            r'负债率[：:为\s]*([-+]?\d+\.?\d*\s*%?)',
        ]
        value = self._extract(patterns, "debt_ratio", "资产负债率")
        if value and not self._validate_range("debt_ratio", value):
            self.results.pop("debt_ratio", None)
            logger.warning(f"资产负债率超出合理范围: {value}")
            return None
        return value
    
    def extract_operating_cashflow(self) -> Optional[str]:
        """提取经营现金流净额"""
        patterns = [
            r'经营活动产生的现金流量净额[：:为\s]*([-+]?\d+\.?\d*\s*[万亿千百]?元?)',
            r'经营现金流净额[：:为\s]*([-+]?\d+\.?\d*\s*[万亿千百]?元?)',
            r'经营性现金流[：:为\s]*([-+]?\d+\.?\d*\s*[万亿千百]?元?)',
        ]
        return self._extract(patterns, "operating_cashflow", "经营现金流净额")
    
    def extract_eps(self) -> Optional[str]:
        """提取每股收益"""
        patterns = [
            r'基本每股收益[：:为\s]*([-+]?\d+\.?\d*\s*元?)',
            r'每股收益[：:为\s]*([-+]?\d+\.?\d*\s*元?)',
            r'EPS[：:为\s]*([-+]?\d+\.?\d*\s*元?)',
        ]
        return self._extract(patterns, "eps", "每股收益(EPS)")
    
    def extract_rd_ratio(self) -> Optional[str]:
        """提取研发费用率"""
        patterns = [
            r'研发费用率[：:为\s]*([-+]?\d+\.?\d*\s*%?)',
            r'研发投入占比[：:为\s]*([-+]?\d+\.?\d*\s*%?)',
            r'研发费用占营业收入比例[：:为\s]*([-+]?\d+\.?\d*\s*%?)',
        ]
        value = self._extract(patterns, "rd_ratio", "研发费用率")
        if value and not self._validate_range("rd_ratio", value):
            self.results.pop("rd_ratio", None)
            logger.warning(f"研发费用率超出合理范围: {value}")
            return None
        return value
    
    def extract_goodwill(self) -> Optional[str]:
        """提取商誉"""
        patterns = [
            r'商誉[：:为\s]*([-+]?\d+\.?\d*\s*[万亿千百]?元?)',
            r'商誉账面价值[：:为\s]*([-+]?\d+\.?\d*\s*[万亿千百]?元?)',
        ]
        return self._extract(patterns, "goodwill", "商誉")
    
    def extract_audit_opinion(self) -> Optional[str]:
        """提取审计意见类型"""
        patterns = [
            r'审计意见[：:为\s]*([^。；\n]+)',
            r'审计报告意见类型[：:为\s]*([^。；\n]+)',
        ]
        for pattern in patterns:
            match = re.search(pattern, self.text)
            if match:
                opinion = match.group(1).strip()
                # 判断意见类型
                if "标准" in opinion or "无保留" in opinion:
                    opinion_type = "标准无保留意见"
                elif "保留" in opinion:
                    opinion_type = "保留意见"
                elif "否定" in opinion:
                    opinion_type = "否定意见"
                elif "无法表示" in opinion:
                    opinion_type = "无法表示意见"
                else:
                    opinion_type = opinion
                
                self.results["audit_opinion"] = {
                    "label": "审计意见",
                    "value": opinion_type,
                    "raw": match.group(0),
                    "confidence": "HIGH"
                }
                return opinion_type
        return None
    
    def extract_all(self) -> Dict[str, Dict[str, Any]]:
        """执行所有提取"""
        self.extract_roe()
        self.extract_net_profit_growth()
        self.extract_revenue()
        self.extract_gross_margin()
        self.extract_net_margin()
        self.extract_debt_ratio()
        self.extract_operating_cashflow()
        self.extract_eps()
        self.extract_rd_ratio()
        self.extract_goodwill()
        self.extract_audit_opinion()
        return self.results


# ============================================================
# 真实数据源接入（API客户端）
# ============================================================

class AnnualReportAPIClient:
    """接入真实年报数据源的API客户端"""
    
    def __init__(self, api_url: str = ANNUAL_REPORT_API, timeout: int = API_TIMEOUT):
        self.api_url = api_url
        self.timeout = timeout
    
    def fetch_annual_report(self, company_code: str, year: int) -> Dict[str, Any]:
        """
        从API获取真实年报数据
        
        Args:
            company_code: 公司代码（如股票代码）
            year: 年报年份
        
        Returns:
            包含财务指标的年报数据字典
        
        Raises:
            RuntimeError: 当API请求失败时
        """
        if not company_code or not year:
            raise ValueError("company_code和year不能为空")
        
        # 构建请求参数
        params = {
            "company_code": company_code,
            "year": year,
            "format": "json"
        }
        url = f"{self.api_url}?{urllib.parse.urlencode(params)}"
        
        # 带重试退避的请求
        last_error = None
        for attempt in range(API_MAX_RETRIES):
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "annual-report-summary/2.1.0"})
                with urllib.request.urlopen(req, timeout=self.timeout) as response:
                    if response.status != 200:
                        raise RuntimeError(f"API返回状态码: {response.status}")
                    data = json.loads(response.read().decode("utf-8"))
                    return self._validate_response(data)
            except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as e:
                last_error = e
                if attempt < API_MAX_RETRIES - 1:
                    # 指数退避
                    wait_time = API_RETRY_BACKOFF * (2 ** attempt)
                    logger.warning(f"API请求失败（第{attempt+1}次），{wait_time}秒后重试: {e}")
                    time.sleep(wait_time)
                continue
        
        raise RuntimeError(f"API请求失败（已重试{API_MAX_RETRIES}次）: {last_error}")
    
    def _validate_response(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """验证API响应数据格式"""
        required_fields = ["indicators", "company_name", "year"]
        for field in required_fields:
            if field not in data:
                raise ValueError(f"API响应缺少字段: {field}")
        
        # 验证指标数据
        indicators = data["indicators"]
        if not isinstance(indicators, dict):
            raise ValueError("indicators字段必须是字典")
        
        return data


#
