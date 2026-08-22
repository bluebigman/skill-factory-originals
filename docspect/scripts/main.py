#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
docspect — 合同文本审阅与风险标注（独立实现）

本脚本依据功能规格独立编写，不参考任何既有实现。
仅使用 Python 标准库，无第三方依赖。

用法示例:
    python main.py --selftest              # 离线自检
    python main.py --file contract.txt     # 审查单个合同文件
    python main.py --compare a.txt b.txt   # 两份合同条款比对
    python main.py --file contract.txt --summary  # 输出摘要
    python main.py --file contract.txt --risks    # 输出风险点
"""

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone
import difflib

# ---------------------------------------------------------------------------
# 错误码定义
# E001: 参数错误
# E002: 文件不存在
# E003: 文件读取失败
# E004: 文本过短（少于500字）
# E005: 文本过长（超过50000字）
# E006: 文本为空
# E007: 内部解析异常
# E008: 比对文本长度不一致
# E009: 输出序列化失败
# E010: 未知错误
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# 数据结构定义
# ---------------------------------------------------------------------------

@dataclass
class ContractStructure:
    """合同结构树"""
    title: str = ""
    parties: List[str] = field(default_factory=list)
    recitals: List[str] = field(default_factory=list)
    definitions: List[str] = field(default_factory=list)
    body_clauses: List[Dict[str, str]] = field(default_factory=list)
    signature_block: List[str] = field(default_factory=list)


@dataclass
class ClauseClassification:
    """条款分类结果"""
    category: str = ""
    clause_text: str = ""
    confidence: float = 0.0


@dataclass
class RiskPoint:
    """风险点"""
    risk_type: str = ""
    clause_ref: str = ""
    description: str = ""
    severity: str = ""  # 高/中/低


@dataclass
class ContractSummary:
    """合同摘要"""
    core_transaction: str = ""
    total_amount: str = ""
    duration: str = ""
    key_obligations: List[str] = field(default_factory=list)


@dataclass
class ComparisonResult:
    """条款比对结果"""
    clause_index: int = 0
    clause_a: str = ""
    clause_b: str = ""
    difference: str = ""
    similarity: float = 0.0


# ---------------------------------------------------------------------------
# 核心分析引擎
# ---------------------------------------------------------------------------

class DocSpectEngine:
    """合同审阅引擎：负责结构解析、分类、风险识别、摘要生成、条款比对"""

    # 条款分类关键词表
    CATEGORY_KEYWORDS = {
        "付款": ["付款", "支付", "价款", "费用", "金额", "结算", "定金", "违约金", "赔偿"],
        "交付": ["交付", "交货", "提供", "送达", "移交", "验收", "签收"],
        "违约": ["违约", "责任", "赔偿", "解除", "终止", "补救"],
        "保密": ["保密", "机密", "披露", "泄露", "保护"],
        "知识产权": ["知识产权", "专利", "商标", "著作权", "版权", "技术秘密"],
        "管辖": ["管辖", "仲裁", "诉讼", "法律适用", "争议解决"],
        "其他": []
    }

    # 风险关键词
    RISK_PATTERNS = [
        (r"尽快|及时|合理时间|适当时候", "模糊时间表述", "中"),
        (r"相关费用|合理费用|必要费用", "费用表述不明确", "中"),
        (r"有权单方|可单方|自行决定", "单方权利失衡", "高"),
        (r"视情况|根据情况|酌情", "裁量权模糊", "中"),
        (r"本合同未尽事宜|其他事项", "未尽事宜条款缺失", "低"),
        (r"口头|电话|微信", "非书面形式约定", "低"),
        (r"不可抗力", "不可抗力条款", "低"),
        (r"续签|自动续期", "自动续期风险", "中"),
        (r"管辖法院|仲裁委员会", "争议解决条款", "低"),
        (r"盖章|签字|签署", "签署要件", "低"),
    ]

    # 金额异常检测模式
    AMOUNT_ANOMALY_PATTERNS = [
        (r"金额\s*[为是]\s*0", "金额为零", "高"),
        (r"金额\s*[为是]\s*负", "金额为负", "高"),
        (r"金额\s*[为是]\s*[一二三四五六七八九十百千万亿]+", "金额为中文数字", "中"),
        (r"金额\s*[为是]\s*[^\d¥￥元万元人民币美元欧元]+", "金额格式异常", "中"),
    ]

    # 期限缺失检测模式
    DURATION_MISSING_PATTERNS = [
        (r"付款.*?(?:未|没有|无).*?(?:期限|时间|日期)", "付款期限缺失", "高"),
        (r"交付.*?(?:未|没有|无).*?(?:期限|时间|日期)", "交付期限缺失", "高"),
        (r"履行.*?(?:未|没有|无).*?(?:期限|时间|日期)", "履行期限缺失", "高"),
    ]

    # 责任条款缺失检测模式
    LIABILITY_MISSING_PATTERNS = [
        (r"违约.*?(?:未|没有|无).*?(?:责任|赔偿|承担)", "违约责任缺失", "高"),
        (r"赔偿.*?(?:未|没有|无).*?(?:责任|条款|约定)", "赔偿责任缺失", "高"),
    ]

    def __init__(self) -> None:
        self._text = ""
        self._lines: List[str] = []

    # -----------------------------------------------------------------------
    # 对外主接口
    # -----------------------------------------------------------------------

    def analyze(self, text: str) -> Dict:
        """
        执行完整合同审阅流程。
        返回包含结构、分类、风险、摘要的结构化字典。
        """
        # 输入校验
        if not text or not text.strip():
            raise ValueError("E006: 文本为空")
        if len(text.strip()) < 500:
            raise ValueError("E004: 文本过短（少于500字）")
        if len(text.strip()) > 50000:
            raise ValueError("E005: 文本过长（超过50000字）")

        self._text = text.strip()
        self._lines = [ln.strip() for ln in self._text.splitlines() if ln.strip()]

        try:
            structure = self._parse_structure()
            classifications = self._classify_clauses(structure.body_clauses)
            risks = self._identify_risks(structure)
            summary = self._generate_summary(structure, classifications)

            return {
                "structure": asdict(structure),
                "classifications": [asdict(c) for c in classifications],
                "risks": [asdict(r) for r in risks],
                "summary": asdict(summary),
                "metadata": {
                    "analyzed_at": datetime.now(timezone.utc).isoformat(),
                    "text_length": len(self._text),
                    "clause_count": len(structure.body_clauses),
                }
            }
        except Exception as exc:
            raise RuntimeError(f"E007: 内部解析异常 - {str(exc)}") from exc

    def compare_contracts(self, text_a: str, text_b: str) -> List[Dict]:
        """
        比对两份合同的条款差异。
        返回差异对照表。
        """
        if not text_a or not text_b:
            raise ValueError("E006: 文本为空")

        # 提取条款
        clauses_a = self._extract_clauses(text_a)
        clauses_b = self._extract_clauses(text_b)

        # 对齐并比较
        max_len = max(len(clauses_a), len(clauses_b))
        results: List[ComparisonResult] = []

        for i in range(max_len):
            clause_a = clauses_a[i] if i < len(clauses_a) else ""
            clause_b = clauses_b[i] if i < len(clauses_b) else ""

            if not clause_a and not clause_b:
                continue

            similarity = self._compute_similarity(clause_a, clause_b)
            difference = self._describe_difference(clause_a, clause_b)

            results.append(ComparisonResult(
                clause_index=i + 1,
                clause_a=clause_a[:200],
                clause_b=clause_b[:200],
                difference=difference,
                similarity=similarity,
            ))

        return [asdict(r) for r in results]

    # -----------------------------------------------------------------------
    # 结构解析
    # -----------------------------------------------------------------------

    def _parse_structure(self) -> ContractStructure:
        """解析合同结构"""
        structure = ContractStructure()
        structure.title = self._detect_title()
        structure.parties = self._detect_parties()
        structure.recitals = self._detect_recitals()
        structure.definitions = self._detect_definitions()
        structure.body_clauses = self._extract_clauses(self._text)
        structure.signature_block = self._detect_signature_block()
        return structure

    def _detect_title(self) -> str:
        """检测合同标题"""
        for line in self._lines[:10]:
            if re.search(r"合同|协议|契约", line) and len(line) < 50:
                return line
        return "未命名合同"

    def _detect_parties(self) -> List[str]:
        """检测当事人"""
        parties = []
        patterns = [
            r"甲方[:：]?\s*(.+)",
            r"乙方[:：]?\s*(.+)",
            r"丙方[:：]?\s*(.+)",
            r"丁方[:：]?\s*(.+)",
        ]
        for line in self._lines:
            for pat in patterns:
                m = re.match(pat, line)
                if m:
                    parties.append(m.group(1).strip())
        return parties

    def _detect_recitals(self) -> List[str]:
        """检测鉴于条款"""
        recitals = []
        in_recital = False
        for line in self._lines:
            if re.search(r"鉴于|背景|前言", line):
                in_recital = True
                recitals.append(line)
                continue
            if in_recital:
                if re.match(r"第[一二三四五六七八九十百千0-9]+条", line):
                    break
                recitals.append(line)
        return recitals

    def _detect_definitions(self) -> List[str]:
        """检测定义条款"""
        definitions = []
        in_definition = False
        for line in self._lines:
            if re.search(r"定义|术语|解释", line):
                in_definition = True
                continue
            if in_definition:
                if re.match(r"第[一二三四五六七八九十百千0-9]+条", line):
                    break
                definitions.append(line)
        return definitions

    def _extract_clauses(self, text: str) -> List[str]:
        """提取正文条款"""
        clauses = []
        # 按条款编号分割
        pattern = r"(第[一二三四五六七八九十百千0-9]+条[^\n]*)"
        parts = re.split(pattern, text)
        for i in range(1, len(parts), 2):
            if i + 1 < len(parts):
                clause_header = parts[i].strip()
                clause_body = parts[i + 1].strip()
                if clause_body:
                    clauses.append(f"{clause_header}\n{clause_body[:500]}")
        return clauses

    def _detect_signature_block(self) -> List[str]:
        """检测签署页"""
        signature = []
        in_signature = False
        for line in self._lines:
            if re.search(r"签署|盖章|签字|法定代表人", line):
                in_signature = True
            if in_signature:
                signature.append(line)
                if len(signature) > 20:
                    break
        return signature

    # -----------------------------------------------------------------------
    # 条款分类
    # -----------------------------------------------------------------------

    def _classify_clauses(self, clauses: List[str]) -> List[ClauseClassification]:
        """对条款进行分类标注"""
        results = []
        for clause in clauses:
            category = "其他"
            best_score = 0.0
            for cat, keywords in self.CATEGORY_KEYWORDS.items():
                score = sum(1 for kw in keywords if kw in clause)
                if score > best_score:
                    best_score = score
                    category = cat
            confidence = min(best_score / 3.0, 1.0)
            results.append(ClauseClassification(
                category=category,
                clause_text=clause[:200],
                confidence=confidence,
            ))
        return results

    # -----------------------------------------------------------------------
    # 风险识别
    # -----------------------------------------------------------------------

    def _identify_risks(self, structure: ContractStructure) -> List[RiskPoint]:
        """识别风险点"""
        risks = []
        full_text = self._text

        # 基于关键词模式匹配
        for pattern, desc, severity in self.RISK_PATTERNS:
            matches = re.finditer(pattern, full_text)
            for m in matches:
                start = max(0, m.start() - 30)
                end = min(len(full_text), m.end() + 30)
                context = full_text[start:end].replace("\n", " ")
                risks.append(RiskPoint(
                    risk_type=desc,
                    clause_ref=f"位置 {m.start()}",
                    description=f"检测到: {context}...",
                    severity=severity,
                ))

        # 金额异常检测
        for pattern, desc, severity in self.AMOUNT_ANOMALY_PATTERNS:
            matches = re.finditer(pattern, full_text)
            for m in matches:
                start = max(0, m.start() - 30)
                end = min(len(full_text), m.end() + 30)
                context = full_text[start:end].replace("\n", " ")
                risks.append(RiskPoint(
                    risk_type=desc,
                    clause_ref=f"位置 {m.start()}",
                    description=f"检测到: {context}...",
                    severity=severity,
                ))

        # 期限缺失检测
        for pattern, desc, severity in self.DURATION_MISSING_PATTERNS:
            matches = re.finditer(pattern, full_text)
            for m in matches:
                start = max(0, m.start() - 30)
                end = min(len(full_text), m.end() + 30)
                context = full_text[start:end].replace("\n", " ")
                risks.append(RiskPoint(
                    risk_type=desc,
                    clause_ref=f"位置 {m.start()}",
                    description=f"检测到: {context}...",
                    severity=severity,
                ))

        # 责任条款缺失检测
        for pattern, desc, severity in self.LIABILITY_MISSING_PATTERNS:
            matches = re.finditer(pattern, full_text)
            for m in matches:
                start = max(0, m.start() - 30)
                end = min(len(full_text), m.end() + 30)
                context = full_text[start:end].replace("\n", " ")
                risks.append(RiskPoint(
                    risk_type=desc,
                    clause_ref=f"位置 {m.start()}",
                    description=f"检测到: {context}...",
                    severity=severity,
                ))

        # 检查缺失要素
        if not structure.parties:
            risks.append(RiskPoint(
                risk_type="缺少当事人信息",
                clause_ref="合同头部",
                description="未检测到甲方/乙方等当事人信息",
                severity="高",
            ))

        if not structure.signature_block:
            risks.append(RiskPoint(
                risk_type="缺少签署条款",
                clause_ref="合同尾部",
                description="未检测到签署/盖章条款",
                severity="高",
            ))

        # 去重
        unique_risks = []
        seen = set()
        for r in risks:
            key = (r.risk_type, r.clause_ref[:50])
            if key not in seen:
                seen.add(key)
                unique_risks.append(r)

        return unique_risks[:20]  # 最多返回20条

    # -----------------------------------------------------------------------
    # 摘要生成
    # -----------------------------------------------------------------------

    def _generate_summary(self, structure: ContractStructure,
                          classifications: List[ClauseClassification]) -> ContractSummary:
        """生成合同摘要"""
        summary = ContractSummary()

        # 核心交易结构
        transaction_parts = []
        if structure.parties:
            transaction_parts.append(f"当事人: {'、'.join(structure.parties[:4])}")
        if structure.recitals:
            transaction_parts.append(f"鉴于: {structure.recitals[0][:100]}")

        # 金额提取
        amount_pattern = r"[¥￥]?\s*(\d+(?:\.\d+)?)\s*(万元|元|人民币|美元|欧元)?"
        amounts = re.findall(amount_pattern, self._text)
        if amounts:
            total = sum(float(a[0]) for a in amounts[:10])
            unit = amounts[0][1] if amounts[0][1] else "元"
            summary.total_amount = f"约{total:.0f}{unit}（基于文本中出现的金额估算）"

        # 期限提取
        duration_pattern = r"(\d+)\s*(天|日|月|年|周)"
        durations = re.findall(duration_pattern, self._text)
        if durations:
            summary.duration = f"约{durations[0][0]}{durations[0][1]}"

        # 关键义务
        for cls in classifications:
            if cls.category in ("付款", "交付", "违约") and cls.confidence > 0.5:
                summary.key_obligations.append(cls.clause_text[:100])

        summary.core_transaction = "；".join(transaction_parts)
