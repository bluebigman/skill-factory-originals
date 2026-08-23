#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py
金融论文 学术写作 风格校准 (jf-writing-skill)

基于功能规格的 clean-room 独立实现。
仅依赖 Python 标准库。

用法示例:
    python scripts/main.py --selftest          # 离线自检
    python scripts/main.py --check <file.txt>  # 检查文本文件
    python scripts/main.py --convert <file.txt> # 风格转换
    python scripts/main.py --format <file.txt>  # 格式校准
"""

import argparse
import re
import sys
from datetime import datetime, timezone
from typing import Dict, List, Tuple

# ============================================================
# 错误码定义
# ============================================================
ERROR_CODES = {
    "E001": "参数错误：无法识别的命令行参数",
    "E002": "文件错误：输入文件不存在或无法读取",
    "E003": "文件错误：输出文件无法写入",
    "E004": "格式错误：输入文本为空或格式不正确",
    "E005": "内部错误：风格转换核心逻辑异常",
    "E006": "内部错误：结构检查核心逻辑异常",
    "E007": "内部错误：术语一致性检查异常",
    "E008": "内部错误：引用格式核对异常",
    "E009": "内部错误：自检失败，核心逻辑未通过验证",
    "E010": "运行时错误：未知异常",
    "E011": "内部错误：格式校准逻辑异常",
}


def _fail(code: str, message: str = None) -> None:
    """统一错误输出并退出"""
    msg = ERROR_CODES.get(code, "未知错误")
    if message:
        msg = f"{msg} — {message}"
    print(f"[错误 {code}] {msg}", file=sys.stderr)
    sys.exit(1)


# ============================================================
# 核心数据结构：风格词库（内置，不依赖外部文件）
# ============================================================
# 口语化 → 学术化 转换映射（金融领域）
# 注意：这是基于金融写作常见规则的映射，非期刊风格库
STYLE_CONVERSIONS: Dict[str, str] = {
    "涨了不少": "呈现显著上行趋势",
    "跌了": "出现回落",
    "赚了": "获得正收益",
    "亏了": "产生负收益",
    "好多": "大量",
    "一点点": "边际性",
    "差不多": "近似",
    "很厉害": "显著",
    "不太行": "表现欠佳",
    "看看": "考察",
    "搞": "实施",
    "弄": "执行",
    "东西": "要素",
    "想法": "观点",
    "公司": "企业",
    "老板": "管理层",
    "股票涨": "股票价格上行",
    "借钱": "债务融资",
    "还钱": "债务偿付",
    "风险大": "风险水平较高",
    "风险小": "风险水平较低",
    "赚钱": "获取收益",
    "花钱": "发生支出",
    "买": "购入",
    "卖": "售出",
    "觉得": "认为",
    "大概": "约略",
    "真的": "确实",
    "非常": "极为",
    "特别": "尤为",
}

# 冗余引导句（学术写作中应删改）
REDUNDANT_PHRASES: List[str] = [
    "It is important to note that",
    "It should be noted that",
    "It is worth mentioning that",
    "As we all know",
    "In my opinion",
    "Obviously",
    "As everyone knows",
]

# 章节结构要求（金融论文标准章节）
REQUIRED_SECTIONS: List[str] = [
    "abstract",
    "introduction",
    "literature review",
    "hypothesis",
    "data",
    "empirical result",
    "conclusion",
]

# 章节中文别名映射
SECTION_ALIASES: Dict[str, List[str]] = {
    "abstract": ["abstract", "摘要"],
    "introduction": ["introduction", "引言", "导言"],
    "literature review": ["literature review", "文献综述", "文献回顾"],
    "hypothesis": ["hypothesis", "假设", "假说"],
    "data": ["data", "数据", "数据描述"],
    "empirical result": ["empirical result", "实证结果", "回归结果", "结果"],
    "conclusion": ["conclusion", "结论", "结语"],
}

# 常见金融术语（用于一致性检查）
FINANCE_TERMS: Dict[str, List[str]] = {
    "corporate governance": ["公司治理", "corporate governance", "企业治理"],
    "asset pricing": ["资产定价", "asset pricing"],
    "capital structure": ["资本结构", "capital structure"],
    "market efficiency": ["市场效率", "market efficiency"],
    "risk management": ["风险管理", "risk management"],
    "portfolio": ["投资组合", "portfolio", "资产组合"],
    "derivatives": ["衍生品", "derivatives", "衍生工具"],
    "liquidity": ["流动性", "liquidity"],
    "volatility": ["波动率", "volatility", "波动性"],
    "return": ["收益", "return", "回报"],
}

# 格式校准规则（引用格式、标点、数字格式等）
FORMAT_RULES = {
    "citation_pattern": r"\(([A-Z][a-z]+(?:\s+et\s+al\.)?,\s*\d{4})\)",
    "citation_replacement": r"(\1)",
    "double_quotes": r'"([^"]*)"',
    "double_quotes_replacement": r"「\1」",
    "number_pattern": r"(\d+),(\d{3})",
    "number_replacement": r"\1\2",
    "decimal_pattern": r"(\d+)\.(\d+)",
    "decimal_replacement": r"\1.\2",
    "percent_pattern": r"(\d+)\s*%",
    "percent_replacement": r"\1%",
    "date_pattern": r"(\d{4})-(\d{2})-(\d{2})",
    "date_replacement": r"\1年\2月\3日",
    "time_pattern": r"(\d{1,2}):(\d{2})",
    "time_replacement": r"\1:\2",
}


# ============================================================
# 核心功能模块
# ============================================================
class StyleCalibrator:
    """风格校准核心类"""

    def __init__(self):
        self.conversions = STYLE_CONVERSIONS
        self.redundant = REDUNDANT_PHRASES
        self.format_rules = FORMAT_RULES

    def convert_style(self, text: str) -> str:
        """C1: 文本风格转换（口语化 → 学术化）"""
        if not text or not text.strip():
            raise ValueError("输入文本为空")

        result = text
        # 1. 替换口语化词汇
        for informal, formal in self.conversions.items():
            result = re.sub(informal, formal, result, flags=re.IGNORECASE)

        # 2. 删除冗余引导句
        for phrase in self.redundant:
            pattern = re.compile(re.escape(phrase), re.IGNORECASE)
            result = pattern.sub("", result)

        # 3. 清理多余空格
        result = re.sub(r"\s+", " ", result).strip()
        return result

    def check_structure(self, text: str) -> List[str]:
        """C2: 结构合规检查，返回缺失章节列表"""
        if not text or not text.strip():
            raise ValueError("输入文本为空")

        text_lower = text.lower()
        missing = []

        for section in REQUIRED_SECTIONS:
            found = False
            for alias in SECTION_ALIASES[section]:
                if alias in text_lower:
                    found = True
                    break
            if not found:
                missing.append(section)

        return missing

    def check_terminology(self, text: str) -> List[str]:
        """C3: 术语一致性检查，返回混用术语建议"""
        if not text or not text.strip():
            raise ValueError("输入文本为空")

        text_lower = text.lower()
        issues = []

        for term, variants in FINANCE_TERMS.items():
            # 检查是否出现多个变体（混用）
            found_variants = [v for v in variants if v.lower() in text_lower]
            if len(found_variants) > 1:
                # 建议统一为第一个变体（通常是标准译名）
                suggestion = f"术语 '{term}' 混用: {', '.join(found_variants)} → 建议统一为 '{variants[0]}'"
                issues.append(suggestion)

        return issues

    def simplify_sentences(self, text: str) -> List[str]:
        """C4: 句式精炼建议，返回改写建议列表"""
        if not text or not text.strip():
            raise ValueError("输入文本为空")

        suggestions = []
        sentences = re.split(r"[.!?。！？]", text)

        for i, sent in enumerate(sentences):
            sent = sent.strip()
            if not sent:
                continue

            # 检查过长句子（>80字符）
            if len(sent) > 80:
                suggestions.append(
                    f"第{i+1}句过长({len(sent)}字符)，建议拆分或精简: '{sent[:50]}...'"
                )

            # 检查被动语态滥用
            passive_patterns = [
                (r"\bwas\s+\w+ed\b", "被动语态"),
                (r"\bwere\s+\w+ed\b", "被动语态"),
                (r"\bis\s+\w+ed\b", "被动语态"),
                (r"\bare\s+\w+ed\b", "被动语态"),
            ]
            for pattern, label in passive_patterns:
                if re.search(pattern, sent, re.IGNORECASE):
                    suggestions.append(f"第{i+1}句存在{label}，建议改为主动语态")
                    break

            # 检查模糊指代
            vague_words = ["it", "this", "that", "these", "those"]
            for word in vague_words:
                if re.search(rf"\b{word}\b", sent, re.IGNORECASE):
                    suggestions.append(f"第{i+1}句存在模糊指代 '{word}'，建议明确指代对象")
                    break

        return suggestions

    def check_citations(self, text: str) -> List[str]:
        """C5: 引用格式核对，返回缺失引用问题"""
        if not text or not text.strip():
            raise ValueError("输入文本为空")

        issues = []
        # 提取文中引用 (Author, Year) 模式
        citations = re.findall(r"\(([A-Z][a-z]+(?:\s+et\s+al\.)?,\s*\d{4})\)", text)
        # 提取参考文献列表
        ref_section = text.split("references", 1)[-1] if "references" in text.lower() else ""

        for cite in citations:
            author = cite.split(",")[0].strip()
            year = cite.split(",")[1].strip()
            # 检查参考文献列表中是否有对应条目
            if author and year:
                pattern = re.compile(
                    rf"{re.escape(author)}[^\n]*{year}", re.IGNORECASE
                )
                if not pattern.search(ref_section):
                    issues.append(f"引用 ({author}, {year}) 在参考文献列表中缺失")

        return issues

    def format_text(self, text: str) -> str:
        """C6: 格式校准（引用格式、标点、数字格式等）"""
        if not text or not text.strip():
            raise ValueError("输入文本为空")

        result = text

        # 1. 引用格式统一
        result = re.sub(
            self.format_rules["citation_pattern"],
            self.format_rules["citation_replacement"],
            result,
        )

        # 2. 双引号统一为中文引号
        result = re.sub(
            self.format_rules["double_quotes"],
            self.format_rules["double_quotes_replacement"],
            result,
        )

        # 3. 数字格式（千位分隔符）
        result = re.sub(
            self.format_rules["number_pattern"],
            self.format_rules["number_replacement"],
            result,
        )

        # 4. 小数格式
        result = re.sub(
            self.format_rules["decimal_pattern"],
            self.format_rules["decimal_replacement"],
            result,
        )

        # 5. 百分比格式
        result = re.sub(
            self.format_rules["percent_pattern"],
            self.format_rules["percent_replacement"],
            result,
        )

        # 6. 日期格式
        result = re.sub(
            self.format_rules["date_pattern"],
            self.format_rules["date_replacement"],
            result,
        )

        # 7. 时间格式
        result = re.sub(
            self.format_rules["time_pattern"],
            self.format_rules["time_replacement"],
            result,
        )

        # 8. 清理多余空格
        result = re.sub(r"\s+", " ", result).strip()
        return result

    def academic_score(self, text: str) -> float:
        """C7: 学术性评分（0-100），用于自检和转换质量评估"""
        if not text or not text.strip():
            return 0.0

        score = 50.0  # 基础分

        # 1. 口语化词汇检测（扣分）
        informal_count = 0
        for informal in self.conversions.keys():
            informal_count += len(re.findall(informal, text, re.IGNORECASE))
        score -= informal_count * 5

        # 2. 冗余引导句检测（扣分）
        redundant_count = 0
        for phrase in self.redundant:
            redundant_count += len(re.findall(re.escape(phrase), text, re.IGNORECASE))
        score -= redundant_count * 3

        # 3. 学术术语使用（加分）
        academic_terms = 0
        for variants in FINANCE_TERMS.values():
            for variant in variants:
                academic_terms += len(re.findall(variant, text, re.IGNORECASE))
        score += min(academic_terms * 2, 30)

        # 4. 引用格式规范（加分）
        citation_count = len(re.findall(r"\([A-Z][a-z]+(?:\s+et\s+al\.)?,\s*\d{4}\)", text))
        score += min(citation_count * 2, 10)

        # 5. 句子长度合理性（加分/扣分）
        sentences = re.split(r"[.!?。！？]", text)
        long_sentences = sum(1 for s in sentences if len(s.strip()) > 80)
        score -= long_sentences * 2

        # 6. 被动语态使用（扣分）
        passive_count = 0
        for pattern in [r"\bwas\s+\w+ed\b", r"\bwere\s+\w+ed\b", r"\bis\s+\w+ed\b", r"\bare\s+\w+ed\b"]:
            passive_count += len(re.findall(pattern, text, re.IGNORECASE))
        score -= passive_count * 1.5

        # 限制在 0-100 范围
        return max(0.0, min(100.0, score))


# ============================================================
# 文件处理函数
# ============================================================
def read_file(filepath: str) -> str:
    """读取文件内容"""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        _fail("E002", f"文件不存在: {filepath}")
    except Exception as e:
        _fail("E002", str(e))


def write_file(filepath: str, content: str) -> None:
    """写入文件内容"""
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
    except Exception:
        _fail("E003", f"无法写入: {filepath}")


def convert_file(filepath: str, output: str = None) -> None:
    """转换文件风格"""
    text = read_file(filepath)
    calibrator = StyleCalibrator()
    try:
        result = calibrator.convert_style(text)
        score = calibrator.academic_score(result)
        print(f"学术性评分: {score:.1f}/100")
    except ValueError as e:
        _fail("E004", str(e))
    except Exception:
        _fail("E005")

    if output:
        write_file(output, result)
    else:
        print(result)


def check_file(filepath: str, output: str = None) -> None:
    """检查文件结构"""
    text = read_file(filepath)
    calibrator = StyleCalibrator()
    try:
        missing = calibrator.check_structure(text)
        terminology = calibrator.check_terminology(text)
        suggestions = calibrator.simplify_sentences(text)
        citations = calibrator.check_citations(text)
        score = calibrator.academic_score(text)

        result = []
        result.append("=== 结构检查 ===")
        if missing:
            result.append(f"缺失章节: {', '.join(missing)}")
        else:
            result.append("所有必需章节均已覆盖 ✓")

        result.append("\n=== 术语一致性 ===")
        if terminology:
            result.extend(terminology)
        else:
            result.append("未发现术语混用 ✓")

        result.append("\n=== 句式建议 ===")
        if suggestions:
            result.extend(suggestions)
        else:
            result.append("未发现需要精简的句式 ✓")

        result.append("\n=== 引用检查 ===")
        if citations:
            result.extend(citations)
        else:
            result.append("引用格式基本一致 ✓")

        result.append(f"\n=== 学术性评分: {score:.1f}/100 ===")

        result = "\n".join(result)

    except ValueError as e:
        _fail("E004", str(e))
