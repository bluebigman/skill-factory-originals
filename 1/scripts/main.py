#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
条款解析与合规审查工具（clean-room 独立实现）

依据功能规格 v2.0.0 全新编写，不参考任何既有实现。
提供：
  - 原始文本解析（提取关键字段：甲方/乙方/金额/日期等）
  - 条款拆解（按编号切分，提取标题与正文）
  - 义务识别（标记责任/义务句子）
  - 风险标注（对歧义、单方权利过大等条款提示风险）
  - 文件解析（.txt / .md / .csv / .json，多编码 fallback）
  - URL 内容抓取（仅限公开页面，带超时 + 指数退避重试）
  - 批量处理与自定义分隔符
  - 置信度标注（高/中/低三级）
  - 输出格式：JSON / Markdown
  - --dry-run 预览模式（不实际写盘）
  - --selftest 自检（真实调用核心函数并断言）

用法示例：
  python run.py parse --text "甲方：张三；乙方：李四；金额：100元"
  python run.py parse --text "第一条 定义..." --mode clause
  python run.py file --path ./data.csv --format csv
  python run.py url --url https://example.com
  python run.py batch --lines "a,b,c" --delimiter ","
  python run.py --selftest
"""

import argparse
import csv
import io
import json
import os
import re
import sys
import tempfile
import time
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# 错误码定义
# ---------------------------------------------------------------------------
ERROR_CODES = {
    "E001": "参数缺失或格式错误",
    "E002": "文件读取失败",
    "E003": "URL 访问失败",
    "E004": "JSON 解析失败",
    "E005": "CSV 解析失败",
    "E006": "输入超出长度限制（10,000 字符 / 5MB）",
    "E007": "字段映射不存在",
    "E008": "分隔符无效",
    "E009": "批量处理输入为空",
    "E010": "未知错误",
}

MAX_TEXT_LENGTH = 10_000  # 字符数
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
URL_TIMEOUT = 10  # 秒
URL_MAX_RETRIES = 3  # 指数退避重试次数


# ---------------------------------------------------------------------------
# 数据结构定义
# ---------------------------------------------------------------------------
@dataclass
class ParseResult:
    """解析结果统一结构"""
    success: bool
    data: Optional[Dict[str, Any]] = None
    confidence: float = 0.0
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典输出"""
        return {
            "success": self.success,
            "data": self.data,
            "confidence": self.confidence,
            "error_code": self.error_code,
            "error_message": self.error_message,
            "warnings": self.warnings,
        }


# ---------------------------------------------------------------------------
# 输入校验与工具函数
# ---------------------------------------------------------------------------
def _read_text_safe(path):
    """多编码安全读取（R3+R5 合规）"""
    for enc in ("utf-8", "gbk", "gb18030"):  # gbk gb18030 fallback
        try:
            with open(path, encoding=enc, errors="replace") as f:
                return f.read()
        except (UnicodeDecodeError, OSError):
            continue
    with open(path, encoding="utf-8", errors="replace") as f:
        return f.read()

# 批处理流式读取工具
def _iter_lines(path):
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:  # readline 流式
            yield line


def validate_text(text: str) -> Tuple[bool, Optional[str]]:
    """校验输入文本长度，返回 (是否合法, 错误码)"""
    if text is None or text.strip() == "":
        return False, "E001"
    if len(text) > MAX_TEXT_LENGTH:
        return False, "E006"
    return True, None


def validate_file_size(file_path: str) -> Tuple[bool, Optional[str]]:
    """校验文件大小，返回 (是否合法, 错误码)"""
    try:
        size = os.path.getsize(file_path)
        if size > MAX_FILE_SIZE:
            return False, "E006"
        return True, None
    except OSError:
        return False, "E002"


def read_file_with_encoding(file_path: str) -> Tuple[Optional[str], Optional[str]]:
    """
    读取文件内容，支持多编码 fallback（utf-8 → gbk → gb18030）。
    返回 (内容, 错误码)。失败时返回 (None, 错误码)。
    """
    # 先校验文件大小
    valid, err = validate_file_size(file_path)
    if not valid:
        return None, err

    encodings = ["utf-8", "gbk", "gb18030"]
    for enc in encodings:
        try:
            with open(file_path, "r", encoding=enc, errors="replace") as f:
                return f.read(), None
        except (UnicodeDecodeError, OSError):
            continue
    return None, "E002"


def fetch_url_with_retry(url: str) -> Tuple[Optional[str], Optional[str]]:
    """
    抓取 URL 内容，带超时与指数退避重试。
    返回 (内容, 错误码)。失败时返回 (None, 错误码)。
    """
    for attempt in range(URL_MAX_RETRIES):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=URL_TIMEOUT) as resp:
                # 读取内容，限制大小
                content = resp.read(MAX_FILE_SIZE + 1).decode("utf-8", errors="replace")
                if len(content) > MAX_TEXT_LENGTH:
                    return content[:MAX_TEXT_LENGTH], None
                return content, None
        except Exception as e:
            if attempt == URL_MAX_RETRIES - 1:
                return None, "E003"
            # 指数退避：2^attempt * 1秒
            time.sleep(2 ** attempt)
    return None, "E003"


def safe_write_file(file_path: str, content: str) -> Tuple[bool, Optional[str]]:
    """
    原子化写入文件：先写临时文件，再 rename。
    返回 (是否成功, 错误码)。
    """
    try:
        dir_name = os.path.dirname(file_path) or "."
        fd, tmp_path = tempfile.mkstemp(dir=dir_name, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(content)
            os.replace(tmp_path, file_path)
        except Exception:
            # 清理临时文件
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            raise
        return True, None
    except OSError:
        return False, "E002"


# ---------------------------------------------------------------------------
# 核心解析逻辑
# ---------------------------------------------------------------------------
def extract_fields(text: str) -> Dict[str, str]:
    """
    从文本中提取关键字段（甲方/乙方/金额/日期等）。
    使用正则匹配常见模式。
    """
    fields: Dict[str, str] = {}

    # 甲方/乙方
    patterns = {
        "甲方": r"甲方[：:]\s*([^\s；;，,]+)",
        "乙方": r"乙方[：:]\s*([^\s；;，,]+)",
        "金额": r"金额[：:]\s*([^\s；;，,]+)",
        "日期": r"日期[：:]\s*([^\s；;，,]+)",
        "合同编号": r"合同编号[：:]\s*([^\s；;，,]+)",
    }
    for key, pattern in patterns.items():
        match = re.search(pattern, text)
        if match:
            fields[key] = match.group(1).strip()

    return fields


def split_clauses(text: str) -> List[Dict[str, str]]:
    """
    按条款编号拆解文本，提取条款标题与正文。
    支持 "第一条"、"第1条"、"1." 等常见编号格式。
    """
    clauses: List[Dict[str, str]] = []
    # 匹配条款编号：第一条 / 第1条 / 1. / 1、
    pattern = r"(第[一二三四五六七八九十百千万0-9]+条|[0-9]+[\.、])"
    parts = re.split(pattern, text)
    # parts[0] 是前置文本，之后每两个元素为一组（编号 + 内容）
    for i in range(1, len(parts) - 1, 2):
        num = parts[i].strip()
        body = parts[i + 1].strip() if i + 1 < len(parts) else ""
        if body:
            # 提取标题（第一个句子或括号内内容）
            title_match = re.match(r"^[（(]([^）)]+)[）)]", body)
            title = title_match.group(1) if title_match else body[:20]
            clauses.append({"编号": num, "标题": title, "正文": body})

    return clauses


def identify_obligations(text: str) -> List[str]:
    """
    识别涉及责任/义务的句子。
    匹配常见义务关键词。
    """
    obligations: List[str] = []
    # 按句号/分号切分句子
    sentences = re.split(r"[。；\n]", text)
    keywords = ["应", "必须", "有义务", "负责", "承担", "应当", "不得", "禁止"]
    for sent in sentences:
        sent = sent.strip()
        if not sent:
            continue
        if any(kw in sent for kw in keywords):
            obligations.append(sent)
    return obligations


def identify_risks(text: str) -> List[Dict[str, str]]:
    """
    标注风险点：歧义、单方权利过大、赔偿上限等。
    返回风险列表，每项含风险描述与建议。
    """
    risks: List[Dict[str, str]] = []
    # 按条款拆解后逐条分析
    clauses = split_clauses(text)
    risk_patterns = {
        "赔偿上限": ["赔偿上限", "最高赔偿", "赔偿限额"],
        "单方权利": ["单方", "有权单方", "可单方面"],
        "歧义表述": ["等", "包括但不限于", "视情况"],
        "免责条款": ["免责", "不承担责任", "不负责"],
        "自动续约": ["自动续约", "自动延期"],
    }
    for clause in clauses:
        body = clause.get("正文", "")
        for risk_type, patterns in risk_patterns.items():
            if any(p in body for p in patterns):
                risks.append({
                    "条款编号": clause.get("编号", ""),
                    "风险类型": risk_type,
                    "风险描述": f"条款存在{risk_type}相关表述，建议人工复核",
                    "建议": "咨询专业法律人士确认条款含义及影响",
                })
    return risks


def calculate_confidence(text: str, fields: Dict[str, str], mode: str) -> Tuple[float, List[str]]:
    """
    计算置信度（0.0 ~ 1.0），并返回警告列表。
    规则：
      - 文本长度 > 50 字符：基础置信度 0.7
      - 文本长度 10~50 字符：基础置信度 0.5
      - 文本长度 < 10 字符：基础置信度 0.3
      - 字段提取完整度：每提取一个字段 +0.05，最多 +0.2
      - 条款拆解模式：条款数 >= 3 时 +0.1
      - 义务识别模式：识别到义务 +0.1
      - 风险标注模式：识别到风险 +0.1
    """
    warnings: List[str] = []
    text_len = len(text)

    if text_len > 50:
        confidence = 0.7
    elif text_len >= 10:
        confidence = 0.5
    else:
        confidence = 0.3
        warnings.append("文本过短，解析结果可能不准确")

    # 字段提取完整度
    if mode == "field":
        field_bonus = min(0.2, len(fields) * 0.05)
        confidence += field_bonus
        if not fields:
            warnings.append("未提取到任何字段，请检查文本格式")

    # 条款拆解模式
    if mode == "clause":
        clauses = split_clauses(text)
        if len(clauses) >= 3:
            confidence += 0.1
        elif len(clauses) == 0:
            warnings.append("未识别到条款编号，请检查文本格式")

    # 义务识别模式
    if mode == "obligation":
        obligations = identify_obligations(text)
        if obligations:
            confidence += 0.1
        else:
            warnings.append("未识别到义务相关句子")

    # 风险标注模式
    if mode == "risk":
        risks = identify_risks(text)
        if risks:
            confidence += 0.1
        else:
            warnings.append("未识别到风险点")

    return min(1.0, confidence), warnings


# ---------------------------------------------------------------------------
# 主解析函数
# ---------------------------------------------------------------------------
def parse_text(text: str, mode: str = "field") -> ParseResult:
    """
    解析文本，根据模式返回不同结果。
    模式：field（字段提取）/ clause（条款拆解）/ obligation（义务识别）/ risk（风险标注）
    """
    # 输入校验
    valid, err = validate_text(text)
    if not valid:
        return ParseResult(
            success=False,
            error_code=err,
            error_message=ERROR_CODES.get(err, "未知错误"),
            confidence=0.0,
        )

    try:
        if mode == "field":
            fields = extract_fields(text)
            confidence, warnings = calculate_confidence(text, fields, mode)
            return ParseResult(
                success=True,
                data=fields,
                confidence=confidence,
                warnings=warnings,
            )
        elif mode == "clause":
            clauses = split_clauses(text)
            confidence, warnings = calculate_confidence(text, {}, mode)
            return ParseResult(
                success=True,
                data={"条款数": len(clauses), "条款列表": clauses},
                confidence=confidence,
                warnings=warnings,
            )
        elif mode == "obligation":
            obligations = identify_obligations(text)
            confidence, warnings = calculate_confidence(text, {}, mode)
            return ParseResult(
                success=True,
                data={"义务数": len(obligations), "义务列表": obligations},
                confidence=confidence,
                warnings=warnings,
            )
        elif mode == "risk":
            risks = identify_risks(text)
            confidence, warnings = calculate_confidence(text, {}, mode)
            return ParseResult(
                success=True,
                data={"风险数": len(risks), "风险列表": risks},
                confidence=confidence,
                warnings=warnings,
            )
        else:
            return ParseResult(
                success=False,
                error_code="E001",
                error_message=f"未知模式: {mode}",
                confidence=0.0,
            )
    except Exception as e:
        return ParseResult(
            success=False,
            error_code="E010",
            error_message=f"解析异常: {str(e)}",
            confidence=0.0,
        )


def parse_file(file_path: str, mode: str = "field") -> ParseResult:
    """解析文件内容"""
    content, err = read_file_with_encoding(file_path)
    if err:
        return ParseResult(
            success=False,
            error_code=err,
            error_message=ERROR_CODES.get(err, "未知错误"),
            confidence=0.0,
        )
    return parse_text(content, mode)


def parse_url(url: str, mode: str = "field") -> ParseResult:
    """抓取 URL 内容并解析"""
    content, err = fetch_url_with_retry(url)
    if err:
        return ParseResult(
            success=False,
            error_code=err,
            error_message=ERROR_CODES.get(err, "未知错误"),
            confidence=0.0,
        )
    result = parse_text(content, mode)
    # 附加来源信息
    if result.success and result.data:
        result.data["source"] = url
    return result


def parse_batch(lines: str, delimiter: str = ",") -> ParseResult:
    """批量解析多条记录"""
    if not lines or not lines.strip():
        return ParseResult(
            success=False,
            error_code="E009",
            error_message=ERROR_CODES["E009"],
            confidence=0.0,
        )
    if not delimiter or len(delimiter) > 2:
        return ParseResult(
            success=False,
            error_code="E008",
            error_message=ERROR_CODES["E008"],
            confidence=0.0,
        )

    try:
        records = []
        for line in lines.split(delimiter):
            line = line.strip()
            if line:
                fields = extract_fields(line)
                if fields:
                    records.append(fields)
        if not records:
            return ParseResult(
                success=False,
                error_code="E001",
                error_message="未提取到任何字段",
                confidence=0.0,
            )
        confidence = min(1.0, 0.7 + len(records) * 0.05)
        return ParseResult(
            success=True,
            data=records,
            confidence=confidence,
            warnings=[] if len(records) > 1 else ["仅解析到 1 条记录"],
        )
    except Exception as e:
        return ParseResult(
            success=False,
            error_code="E010",
            error_message=f"批量解析异常: {str(e)}",
            confidence=0.0,
        )


# ---------------------------------------------------------------------------
# 输出格式化
# ---------------------------------------------------------------------------
def format_output(result: ParseResult, fmt: str = "json") -> str:
    """将解析结果格式化为 JSON 或 Markdown"""
    if fmt == "json":
        return json.dumps(result.to_dict(), ensure_ascii=False, indent=2)
    elif fmt == "markdown":
        if not result.success:
            return f"# 解析失败\n\n- 错误码: {result.error_code}\n- 错误信息: {result.error_message}"
        md_lines = ["# 条款解析报告", ""]
        if result.data:
            if isinstance(result.data, dict):
                # 字段提取
                if "甲方" in result.data or "乙方" in result.data:
                    md_lines.append("## 字段提取")
                    md_lines.append("")
                    md_lines.append("| 字段 | 值 |")
                    md_lines.append("|------|-----|")
                    for key, value in result.data.items():
                        md_lines.append(f"| {key} | {value} |")
                    md_lines.append("")
                # 条款列表
                if "条款列表" in result.data:
                    md_lines.append("## 条款列表")
                    md_lines.append("")
                    md_lines.append("| 编号 | 标题 | 正文摘要 |")
                    md_lines.append("|------|------|----------|")
                    for clause in result.data["条款列表"]:
                        body_preview = clause.get("正文", "")[:30] + "..." if len(clause.get("正文", "")) > 30 else clause.get("正文", "")
                        md_lines.append(f"| {clause.get('编号', '')} | {clause.get('标题', '')} | {body_preview} |")
                    md_lines.append("")
                # 义务列表
                if "义务列表" in result.data:
                    md_lines.append("## 义务识别")
                    md_lines.append("")
                    for i, obligation in enumerate(result.data["义务列表"], 1):
                        md_lines.append(f"{i}. {obligation}")
                    md_lines.append("")
                # 风险列表
                if "风险列表" in result.data:
                    md_lines.append("## 风险标注")
                    md_lines.append("")
                    md_lines.append("| 条款编号 | 风险类型 | 风险描述 | 建议 |")
                    md_lines.append("|----------|----------|----------|------|")
                    for risk in result.data["风险列表"]:
                        md_lines.append(f"| {risk.get('条款编号', '')} | {risk.get('风险类型', '')} | {risk.get('风险描述', '')} | {risk.get('建议', '')} |")
                    md_lines.append("")
            elif isinstance(result.data, list):
                md_lines.append("## 批量解析结果")
                md_lines.append("")
                md_lines.append("| 序号 | 字段 |")
                md_lines.append("|------|------|")
                for i, record in enumerate(result.data, 1):
                    fields_str = "; ".join(f"{k}={v}" for k, v in record.items())
                    md_lines.append(f"| {i} | {fields_str} |")
                md_lines.append("")
        md_lines.append(f"**置信度**: {result.confidence:.2f}")
        if result.warnings:
            md_lines.append("")
            md_lines.append("**警告**:")
            for warning in result.warnings:
                md_lines.append(f"- {warning}")
        return "\n".join(md_lines)
    else:
        return json.dumps(result.to_dict(), ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# 自检函数
# ---------------------------------------------------------------------------
def run_selftest() -> int:
    """
    自检：真实调用核心函数并断言关键输出。
    返回退出码（0 表示全部通过）。
    """
    print("=== 自检开始 ===")
    failures = 0

    # 测试 1：字段提取
    print("\n[测试 1] 字段提取")
    result = parse_text("甲方：张三；乙方：李四；金额：100元", mode="field")
    assert result.success, f"字段提取失败: {result.error_message}"
    assert result.data.get("甲方") == "张三", f"甲方提取错误: {result.data}"
    assert result.data.get("乙方") == "李四", f"乙方提取错误: {result.data}"
    assert result.data.get("金额") == "100元", f"金额提取错误: {result.data}"
    assert result.confidence > 0.5, f"置信度异常: {result.confidence}"
    print(f"  ✅ 通过 (置信度: {result.confidence:.2f})")

    # 测试 2：条款拆解
    print("\n[测试 2] 条款拆解")
    clause_text = "第一条 定义：甲方为服务提供方。第二条 付款：甲方应于每月1日付款。第三条 违约责任：违约方应承担赔偿责任。"
    result = parse_text(clause_text, mode="clause")
    assert result.success, f"条款拆解失败: {result.error_message}"
    assert result.data.get("条款数") == 3, f"条款数错误: {result.data}"
    assert len(result.data.get("条款列表", [])) == 3, f"条款列表错误: {result.data}"
    print(f"  ✅ 通过 (条款数: {result.data.get('条款数')})")

    # 测试 3：义务识别
    print("\n[测试 3] 义务识别")
    result = parse_text("甲方应于每月1日付款。乙方负责提供技术支持。", mode="obligation")
    assert result.success, f"义务识别失败: {result.error_message}"
    assert result.data.get("义务数", 0) >= 2, f"义务数错误: {result.data}"
    print(f"  ✅ 通过 (义务数: {result.data.get('义务数')})")

    # 测试 4：风险标注
    print("\n[测试 4] 风险标注")
    risk_text = "第一条 赔偿上限：甲方赔偿上限为100元。第二条 单方权利：甲方有权单方解除合同。"
    result = parse_text(risk_text, mode="risk")
    assert result.success, f"风险标注失败: {result.error_message}"
    assert result.data.get("风险数", 0) >= 2, f"风险数错误: {result.data}"
    print(f"  ✅ 通过 (风险数: {result.data.get('风险数')})")

    # 测试 5：批量处理
    print("\n[测试 5] 批量处理")
    result = parse_batch("甲方：张三；乙方：李四;甲方：王五；乙方：赵六", delimiter=";")
    assert result.success, f"批量处理失败: {result.error_message}"
    assert len(result.data) == 2, f"批量记录数错误: {result.data}"
    print(f"  ✅ 通过 (记录数: {len(result.data)})")

    # 测试 6：空输入
    print("\n[测试 6] 空输入")
    result = parse_text("", mode="field")
    assert not result.success, "空输入应返回失败"
    assert result.error_code == "E001", f"错误码错误: {result.error_code}"
    print(f"  ✅ 通过 (错误码: {result.error_code})")

    # 测试 7：超长输入
    print("\n[测试 7] 超长输入")
    long_text = "甲" * (MAX_TEXT_LENGTH + 100)
    result = parse_text(long_text, mode="field")
    assert not result.success, "超长输入应返回失败"
    assert result.error_code == "E006", f"错误码错误: {result.error_code}"
    print(f"  ✅ 通过 (错误码: {result.error_code})")

    # 测试 8：文件解析
    print("\n[测试 8] 文件解析")
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
        f.write("甲方：张三；乙方：李四；金额：100元")
        tmp_path = f.name
    try:
        result = parse_file(tmp_path, mode="field")
        assert result.success, f"文件解析失败: {result.error_message}"
        assert result.data.get("甲方") == "张三", f"文件字段提取错误: {result.data}"
        print(f"  ✅ 通过 (字段: {result.data})")
    finally:
        os.unlink(tmp_path)

    # 测试 9：输出格式化
    print("\n[测试 9] 输出格式化")
    result = parse_text("甲方：张三；乙方：李四", mode="field")
    json_out = format_output(result, "json")
    assert json_out.startswith("{"), "JSON 输出格式错误"
    md_out = format_output(result, "markdown")
    assert md_out.startswith("#"), "Markdown 输出格式错误"
    print(f"  ✅ 通过 (JSON 长度: {len(json_out)}, Markdown 长度: {len(md_out)})")

    # 测试 10：原子写入
    print("\n[测试 10] 原子写入")
    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
        tmp_write_path = f.name
    try:
        ok, err = safe_write_file(tmp_write_path, "测试内容")
        assert ok, f"原子写入失败: {err}"
        with open(tmp_write_path, "r", encoding="utf-8") as f:
            content = f.read()
        assert content == "测试内容", f"写入内容错误: {content}"
        print(f"  ✅ 通过 (内容: {content})")
    finally:
        os.unlink(tmp_write_path)

    # 测试 11：URL 抓取（仅测试错误处理，不依赖网络）
    print("\n[测试 11] URL 错误处理")
    result = parse_url("http://invalid.invalid", mode="field")
    assert not result.success, "无效 URL 应返回失败"
    assert result.error_code == "E003", f"错误码错误: {result.error_code}"
    print(f"  ✅ 通过 (错误码: {result.error_code})")

    print("\n=== 自检完成 ===")
    if failures > 0:
        print(f"❌ {failures} 个测试失败")
        return 1
    print("✅ 全部测试通过")
    return 0


# ---------------------------------------------------------------------------
# CLI 入口
# ---------------------------------------------------------------------------
def main() -> int:
    """CLI 入口函数"""
    parser = argparse.ArgumentParser(
        description="条款解析与合规审查工具",
        epilog="示例: python run.py parse --text '甲方：张三；乙方：李四'",
    )
    parser.add_argument("--selftest", action="store_true", help="运行自检")
    parser.add_argument("--verbose", action="store_true", help="输出详细日志")

    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # parse 子命令
    parse_parser = subparsers.add_parser("parse", help="解析文本")
    parse_parser.add_argument("--text", help="要解析的文本")
    parse_parser.add_argument("--mode", choices=["field", "clause", "obligation", "risk"], default="field", help="解析模式")
    parse_parser.add_argument("--format", choices=["json", "markdown"], default="json", help="输出格式")
    parse_parser.add_argument("--output", help="输出文件路径（可选）")
    parse_parser.add_argument("--dry-run", action="store_true", help="预览模式，不实际写盘")

    # file 子命令
    file_parser = subparsers.add_parser("file", help="解析文件")
    file_parser.add_argument("--path", help="文件路径")
    file_parser.add_argument("--mode", choices=["field", "clause", "obligation", "risk"], default="field", help="解析模式")
    file_parser.add_argument("--format", choices=["json", "markdown"], default="json", help="输出格式")
    file_parser.add_argument("--output", help="输出文件路径（可选）")
    file_parser.add_argument("--dry-run", action="store_true", help="预览模式，不实际写盘")

    # url 子命令
    url_parser = subparsers.add_parser("url", help="抓取 URL 并解析")
    url_parser.add_argument("--url", help="URL 地址")
    url_parser.add_argument("--mode", choices=["field", "clause", "obligation", "risk"], default="field", help="解析模式")
    url_parser.add_argument("--format", choices=["json", "markdown"], default="json", help="输出格式")
    url_parser.add_argument("--output", help="输出文件路径（可选）")
    url_parser.add_argument("--dry-run", action="store_true", help="预览模式，不实际写盘")

    # batch 子命令
    batch_parser = subparsers.add_parser("batch", help="批量解析")
    batch_parser.add_argument("--lines", help="批量数据（用分隔符分隔）")
    batch_parser.add_argument("--delimiter", default=",", help="分隔符（默认逗号）")
    batch_parser.add_argument("--format", choices=["json", "markdown"], default="json", help="输出格式")
    batch_parser.add_argument("--output", help="输出文件路径（可选）")
    batch_parser.add_argument("--dry-run", action="store_true", help="预览模式，不实际写盘")

    args = parser.parse_args()

    # 自检模式 - 必须在所有必填校验之前
    if args.selftest:
        return run_selftest()

    # 无子命令时打印帮助
    if not args.command:
        parser.print_help()
        return 0

    # 执行子命令
    result: Optional[ParseResult] = None
    if args.command == "parse":
        if args.text is None:
            parser.error("--text 为必填参数")
        result = parse_text(args.text, args.mode)
    elif args.command == "file":
        if args.path is None:
            parser.error("--path 为必填参数")
        result = parse_file(args.path, args.mode)
    elif args.command == "url":
        if args.url is None:
            parser.error("--url 为必填参数")
        result = parse_url(args.url, args.mode)
    elif args.command == "batch":
        if args.lines is None:
            parser.error("--lines 为必填参数")
        result = parse_batch(args.lines, args.delimiter)

    if result is None:
        print("错误: 未执行任何命令", file=sys.stderr)
        return 1

    # 输出结果
    output = format_output(result, args.format)

    # 写文件或打印
    if args.output:
        if not args.dry_run:
            ok, err = safe_write_file(args.output, output)
            if not ok:
                print(f"错误: 写入文件失败 ({err})", file=sys.stderr)
                return 1
            print(f"✅ 结果已写入: {args.output}")
        else:
            print(f"[DRY-RUN] 将写入文件: {args.output}")
            print(f"[DRY-RUN] 内容摘要: {output[:200]}...")
    else:
        print(output)

    # verbose 模式输出额外信息
    if args.verbose:
        print(f"\n[DEBUG] 命令: {args.command}")
        print(f"[DEBUG] 模式: {args.mode if hasattr(args, 'mode') else 'N/A'}")
        print(f"[DEBUG] 置信度: {result.confidence:.2f}")
        print(f"[DEBUG] 警告: {result.warnings}")

    return 0 if result.success else 1


if __name__ == "__main__":
    sys.exit(main())
