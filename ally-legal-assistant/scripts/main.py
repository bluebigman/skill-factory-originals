#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py
合同审查助手 - Ally Legal Assistant 独立实现
基于功能规格 clean-room 重写，不依赖任何既有代码。
仅使用标准库，支持离线自检。
"""

import argparse
import json
import re
import sys
import time
import urllib.request
import urllib.error
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
import os
import hashlib
import pickle
from pathlib import Path


# ============================================================
# 错误码常量（规格 E001-E005，扩展至 E010）
# ============================================================
ERROR_CODES = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：输入来源、输出格式、期望完整度",
    "E003": "输入格式不符合要求，示例：请提供文本、JSON 或 URL",
    "E004": "这超出了本工具的能力范围，建议咨询专业人士或使用其他工具",
    "E005": "结果无法确定，建议：提供更多上下文或人工复核",
    "E006": "内部处理异常，请重试或检查输入",
    "E007": "置信度计算失败，请检查输入数据",
    "E008": "输出格式不支持，请选择：text / json",
    "E009": "批量处理时某个条目失败，已跳过该条目",
    "E010": "未知错误，请联系维护人员",
}


# ============================================================
# 数据结构定义
# ============================================================
@dataclass
class ContractItem:
    """合同关键信息条目"""
    field_name: str          # 字段名称
    value: str               # 提取的值
    confidence: float        # 置信度 0-100
    source: str = "input"    # 来源标记
    note: str = ""           # 备注（如"建议复核"）


@dataclass
class ParseResult:
    """解析结果"""
    items: List[ContractItem] = field(default_factory=list)
    raw_text: str = ""
    status: str = "ok"       # ok / warning / error
    error_code: str = ""
    message: str = ""


@dataclass
class OutputResult:
    """最终输出"""
    status: str = "ok"
    error_code: str = ""
    message: str = ""
    data: Dict[str, Any] = field(default_factory=dict)
    confidence_avg: float = 0.0


# ============================================================
# 条款比对与风险标注引擎
# ============================================================
class RiskRuleEngine:
    """
    风险规则引擎 - 基于条款内容进行风险标注
    实现合同条款比对与风险识别
    注意：本引擎为关键词和模式匹配工具，不构成法律意见。
    所有风险提示仅为辅助参考，最终判断需由专业法律人士完成。
    """
    
    def __init__(self, rules_config: Optional[Dict[str, Any]] = None) -> None:
        """初始化风险规则引擎
        Args:
            rules_config: 外部配置字典，包含 rules 列表和 thresholds
        """
        if rules_config and "rules" in rules_config and rules_config["rules"]:
            self.active_rules = rules_config["rules"]
            self.thresholds = rules_config.get("thresholds", {})
        else:
            # 默认规则（内置规则集，确保功能可用）
            self.active_rules = self._get_default_rules()
            self.thresholds = self._get_default_thresholds()

    def _get_default_rules(self) -> List[Dict[str, Any]]:
        """获取默认规则集"""
        return [
            {
                "id": "RISK-001",
                "name": "违约金过高",
                "keywords": ["违约金", "赔偿金"],
                "patterns": [
                    r"违约金[^。]*?(\d+(?:\.\d+)?)%",
                    r"违约金[^。]*?(\d+(?:\.\d+)?)\s*万元",
                    r"违约金[^。]*?(\d+(?:\.\d+)?)\s*元",
                ],
                "severity": "high",
                "description": "违约金比例或金额过高，可能超过法定上限",
                "suggestion": "建议核实违约金是否超过实际损失的30%"
            },
            {
                "id": "RISK-002",
                "name": "争议解决条款缺失",
                "keywords": ["争议解决", "仲裁", "诉讼"],
                "patterns": [],
                "severity": "medium",
                "description": "未发现争议解决条款，发生纠纷时可能面临不确定性",
                "suggestion": "建议补充争议解决条款，明确仲裁或诉讼管辖"
            },
            {
                "id": "RISK-003",
                "name": "保密条款缺失",
                "keywords": ["保密条款", "保密义务", "保密协议"],
                "patterns": [],
                "severity": "medium",
                "description": "未发现保密条款，商业机密可能缺乏保护",
                "suggestion": "建议补充保密条款，明确保密范围和期限"
            },
            {
                "id": "RISK-004",
                "name": "知识产权归属不明确",
                "keywords": ["知识产权", "版权", "专利"],
                "patterns": [],
                "severity": "high",
                "description": "未明确知识产权归属，可能引发后续纠纷",
                "suggestion": "建议明确知识产权归属和使用权限"
            },
            {
                "id": "RISK-005",
                "name": "付款条件苛刻",
                "keywords": ["付款", "支付"],
                "patterns": [
                    r"预付[^。]*?(\d+(?:\.\d+)?)%",
                    r"首付[^。]*?(\d+(?:\.\d+)?)%",
                ],
                "severity": "medium",
                "description": "预付款比例过高，可能增加资金风险",
                "suggestion": "建议协商降低预付款比例，增加分期付款"
            },
            {
                "id": "RISK-006",
                "name": "合同期限过长",
                "keywords": ["期限", "有效期"],
                "patterns": [
                    r"期限[^。]*?(\d+)\s*年",
                    r"有效期[^。]*?(\d+)\s*年",
                ],
                "severity": "low",
                "description": "合同期限较长，可能影响后续调整灵活性",
                "suggestion": "建议设置中期评估机制或提前终止条款"
            }
        ]

    def _get_default_thresholds(self) -> Dict[str, float]:
        """获取默认阈值"""
        return {
            "RISK-001": 30,  # 违约金超过30%视为高风险
            "RISK-005": 50,  # 预付款超过50%视为高风险
            "RISK-006": 5    # 合同期限超过5年视为高风险
        }

    def analyze_contract(self, text: str, extracted_items: List[ContractItem]) -> Dict[str, Any]:
        """
        分析合同文本，识别风险点
        Args:
            text: 合同全文
            extracted_items: 已提取的合同字段
        Returns:
            风险列表，每个风险包含规则ID、名称、严重程度、描述和建议
        """
        risks = []
        
        # 检查每个规则
        for rule in self.active_rules:
            risk = self._check_rule(rule, text, extracted_items)
            if risk:
                risks.append(risk)
        
        # 计算风险评分
        severity_scores = {"high": 3, "medium": 2, "low": 1}
        if risks:
            total_score = sum(severity_scores.get(r["severity"], 1) for r in risks)
            risk_level = "high" if total_score >= 6 else ("medium" if total_score >= 3 else "low")
        else:
            risk_level = "low"
            total_score = 0
        
        return {
            "risks": risks,
            "risk_level": risk_level,
            "risk_score": total_score
        }

    def _check_rule(self, rule: Dict[str, Any], text: str, items: List[ContractItem]) -> Optional[Dict[str, Any]]:
        """检查单个规则"""
        # 检查关键词是否出现
        text_lower = text.lower()
        keyword_found = any(kw.lower() in text_lower for kw in rule["keywords"])
        
        # 检查模式匹配
        pattern_matches = []
        for pattern in rule["patterns"]:
            matches = re.findall(pattern, text)
            if matches:
                pattern_matches.extend(matches)
        
        # 获取阈值
        threshold = self.thresholds.get(rule["id"], 0)
        
        # 判断是否触发风险
        if rule["id"] in ["RISK-001", "RISK-005", "RISK-006"]:
            if pattern_matches:
                for match in pattern_matches:
                    try:
                        value = float(match)
                        if value > threshold:
                            if rule["id"] == "RISK-001":
                                detail = f"违约金比例/金额为 {value}，超过阈值 {threshold}"
                            elif rule["id"] == "RISK-005":
                                detail = f"预付款比例为 {value}%，超过阈值 {threshold}%"
                            else:
                                detail = f"合同期限为 {value} 年，超过阈值 {threshold} 年"
                            return self._create_risk(rule, detail)
                    except ValueError:
                        continue
        else:  # 缺失类风险
            if not keyword_found:
                return self._create_risk(rule, f"未发现与'{rule['name']}'相关的条款")
        
        return None

    def _create_risk(self, rule: Dict[str, Any], detail: str) -> Dict[str, Any]:
        """创建风险记录"""
        return {
            "rule_id": rule["id"],
            "rule_name": rule["name"],
            "severity": rule["severity"],
            "description": rule["description"],
            "detail": detail,
            "suggestion": rule["suggestion"]
        }


# ============================================================
# 条款比对引擎
# ============================================================
class ClauseComparator:
    """
    条款比对引擎 - 计算合同条款之间的相似度
    用于版本对比或与标准模板对比
    """
    
    def __init__(self) -> None:
        """初始化比对引擎"""
        pass

    def compare_clauses(self, clause1: str, clause2: str) -> Dict[str, Any]:
        """
        比对两个条款的相似度
        Args:
            clause1: 条款1文本
            clause2: 条款2文本
        Returns:
            包含相似度分数和差异分析的字典
        """
        # 计算文本相似度
        similarity = self._calculate_similarity(clause1, clause2)
        
        # 找出差异部分
        differences = self._find_differences(clause1, clause2)
        
        return {
            "similarity": round(similarity * 100, 2),
            "differences": differences,
            "verdict": "一致" if similarity > 0.95 else ("基本一致" if similarity > 0.8 else "存在差异")
        }

    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """
        计算文本相似度（基于字符n-gram和Jaccard相似度）
        """
        if not text1 or not text2:
            return 0.0
        
        # 预处理：去除标点和空白
        def preprocess(text: str) -> str:
            text = re.sub(r'[^\w\s\u4e00-\u9fff]', '', text)
            return text.lower()
        
        t1 = preprocess(text1)
        t2 = preprocess(text2)
        
        if not t1 or not t2:
            return 0.0
        
        # 生成字符三元组
        def get_trigrams(text: str) -> set:
            if len(text) < 3:
                return {text}
            return {text[i:i+3] for i in range(len(text) - 2)}
        
        trigrams1 = get_trigrams(t1)
        trigrams2 = get_trigrams(t2)
        
        # Jaccard相似度
        intersection = len(trigrams1 & trigrams2)
        union = len(trigrams1 | trigrams2)
        
        if union == 0:
            return 0.0
        
        return intersection / union

    def _find_differences(self, text1: str, text2: str) -> List[Dict[str, str]]:
        """
        找出两个文本的差异部分
        """
        # 简单实现：按句子分割并比较
        sentences1 = re.split(r'[。；\n]', text1)
        sentences2 = re.split(r'[。；\n]', text2)
        
        differences = []
        
        # 找出只在text1中出现的句子
        for sent in sentences1:
            sent = sent.strip()
            if sent and sent not in sentences2:
                differences.append({
                    "type": "removed",
                    "content": sent
                })
        
        # 找出只在text2中出现的句子
        for sent in sentences2:
            sent = sent.strip()
            if sent and sent not in sentences1:
                differences.append({
                    "type": "added",
                    "content": sent
                })
        
        return differences


# ============================================================
# 网络请求工具类（带重试、退避、超时）
# ============================================================
class NetworkClient:
    """网络请求客户端，支持重试、退避、超时和降级"""
    
    def __init__(self, timeout: int = 10, max_retries: int = 3, base_delay: float = 1.0) -> None:
        """初始化网络客户端
        Args:
            timeout: 请求超时时间（秒）
            max_retries: 最大重试次数
            base_delay: 基础退避延迟（秒）
        """
        self.timeout = timeout
        self.max_retries = max_retries
        self.base_delay = base_delay

    def fetch_url(self, url: str) -> Tuple[bool, str]:
        """
        获取URL内容，带重试和退避
        Args:
            url: 目标URL
        Returns:
            (成功标志, 内容或错误信息)
        """
        if not url.startswith(('http://', 'https://')):
            return False, "E003: 无效的URL格式"
        
        for attempt in range(self.max_retries):
            try:
                req = urllib.request.Request(url, headers={'User-Agent': 'Ally-Legal-Assistant/1.0'})
                with urllib.request.urlopen(req, timeout=self.timeout) as response:
                    if response.status != 200:
                        return False, f"E006: HTTP状态码 {response.status}"
                    content = response.read().decode('utf-8', errors='replace')
                    return True, content
            except urllib.error.HTTPError as e:
                if attempt < self.max_retries - 1:
                    delay = self.base_delay * (2 ** attempt)  # 指数退避
                    time.sleep(delay)
                else:
                    return False, f"E006: HTTP错误 {e.code} - {e.reason}"
            except urllib.error.URLError as e:
                reason = str(e.reason) if hasattr(e, 'reason') else str(e)
                if attempt < self.max_retries - 1:
                    delay = self.base_delay * (2 ** attempt)  # 指数退避
                    time.sleep(delay)
                else:
                    return False, f"E006: 网络请求失败 - {reason}"
            except TimeoutError:
                if attempt < self.max_retries - 1:
                    delay = self.base_delay * (2 ** attempt)
                    time.sleep(delay)
                else:
                    return False, "E006: 请求超时"
            except Exception as e:
                return False, f"E006: 未知网络错误 - {str(e)}"
        
        return False, "E006: 重试次数耗尽"


# ============================================================
# 核心逻辑类
# ============================================================
class ContractAnalyzer:
    """
    合同分析器 - 核心逻辑
    根据规格实现：解析输入、识别关键信息、计算置信度、生成输出
    """

    # 常见合同关键字段（用于识别）
    KEY_FIELDS = [
        "合同编号", "合同名称", "甲方", "乙方", "签订日期",
        "生效日期", "终止日期", "金额", "币种", "付款方式",
        "违约责任", "争议解决", "保密条款", "知识产权",
    ]

    # 字段别名映射（用于更鲁棒的识别）
    FIELD_ALIASES = {
        "合同编号": ["编号", "合同号", "NO", "NO."],
        "合同名称": ["名称", "标题", "合同标题"],
        "甲方": ["委托方", "买方", "采购方", "客户"],
        "乙方": ["受托方", "卖方", "供应商", "服务方"],
        "签订日期": ["签署日期", "签订时间", "日期"],
        "生效日期": ["生效时间", "开始日期"],
        "终止日期": ["结束日期", "到期日", "失效日期"],
        "金额": ["总金额", "合同金额", "价款", "费用", "价格"],
        "币种": ["货币", "货币单位"],
        "付款方式": ["支付方式", "结算方式"],
        "违约责任": ["违约条款", "赔偿条款"],
        "争议解决": ["争议处理", "仲裁", "诉讼管辖"],
        "保密条款": ["保密义务", "保密协议"],
        "知识产权": ["IP", "版权", "专利"],
    }

    # 需要数值验证的字段
    NUMERIC_FIELDS = ["金额"]

    # 缓存目录
    CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".cache")

    def __init__(self) -> None:
        """初始化分析器"""
        self.risk_engine = RiskRuleEngine()
        self.comparator = Clause
