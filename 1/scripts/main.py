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
dry_run = False  # v3.274 模块级 dry-run 标志

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
        """转换为字典"""
        return {
            "success": self.success,
            "data": self.data,
            "confidence": self.confidence,
            "error_code": self.error_code,
            "error_message": self.error_message,
            "warnings": self.warnings,
        }


@dataclass
class Clause:
    """条款结构"""
    id: str
    title: str
    content: str
    obligations: List[Dict[str, str]] = field(default_factory=list)
    risks: List[Dict[str, str]] = field(default_factory=list)


# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------
def get_utc_now() -> str:
    """获取 UTC 当前时间"""
    return datetime.now(timezone.utc).isoformat()


def read_file_with_fallback(file_path: str) -> str:
    """多编码读取文件，支持 utf-8/gbk/gb18030 三级 fallback"""
    for encoding in ["utf-8", "gbk", "gb18030"]:
        try:
            with open(file_path, "r", encoding=encoding) as f:
                return f.read()
        except UnicodeDecodeError:
            continue
        except FileNotFoundError:
            raise
        except Exception as e:
            raise
    # 最后尝试 replace 模式
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def atomic_write(file_path: str, content: str) -> None:
    """原子化写入文件"""
    dir_name = os.path.dirname(file_path) or "."
    fd, temp_path = tempfile.mkstemp(dir=dir_name, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(temp_path, file_path)
    except Exception:
        os.unlink(temp_path)
        raise


# ---------------------------------------------------------------------------
# 核心解析函数
# ---------------------------------------------------------------------------
def extract_parties(text: str) -> Dict[str, str]:
    """提取合同双方信息"""
    parties = {}
    patterns = {
        "甲方": r"甲方[：:]\s*([^\s，。；;]+)",
        "乙方": r"乙方[：:]\s*([^\s，。；;]+)",
        "丙方": r"丙方[：:]\s*([^\s，。；;]+)",
    }
    for role, pattern in patterns.items():
        match = re.search(pattern, text)
        if match:
            parties[role] = match.group(1).strip()
    return parties


def extract_amount(text: str) -> Optional[str]:
    """提取金额信息"""
    patterns = [
        r"金额[：:]\s*([^\s，。；;]+)",
        r"价款[：:]\s*([^\s，。；;]+)",
        r"人民币\s*([\d,，.]+)\s*元",
        r"([\d,，.]+)\s*万元",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1).strip()
    return None


def extract_date(text: str) -> Optional[str]:
    """提取日期信息"""
    patterns = [
        r"日期[：:]\s*([^\s，。；;]+)",
        r"(\d{4}年\d{1,2}月\d{1,2}日)",
        r"(\d{4}-\d{1,2}-\d{1,2})",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1).strip()
    return None


def split_clauses(text: str) -> List[Clause]:
    """按编号切分条款"""
    # 支持的模式：第一条、第1条、1.1、1.1.1
    pattern = r"(第[一二三四五六七八九十百千]+条|第\d+条|\d+\.\d+(?:\.\d+)?)"
    matches = list(re.finditer(pattern, text))
    clauses = []
    for i, match in enumerate(matches):
        clause_id = match.group(1)
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        content = text[start:end].strip()
        # 提取标题（第一行）
        lines = content.split("\n")
        title = lines[0].strip() if lines else ""
        # 去除标题行后的内容
        body = "\n".join(lines[1:]).strip() if len(lines) > 1 else ""
        if not body:
            body = content
        clauses.append(Clause(id=clause_id, title=title, content=body))
    return clauses


def extract_obligations(clause: Clause) -> List[Dict[str, str]]:
    """提取义务信息"""
    obligations = []
    # 义务主体模式
    subject_patterns = {
        "甲方": r"甲方(?:应|需|必须|应当)",
        "乙方": r"乙方(?:应|需|必须|应当)",
        "双方": r"双方(?:应|需|必须|应当)",
    }
    # 义务动词模式
    action_patterns = [
        r"(?:应|需|必须|应当)\s*([^，。；]+)",
        r"不得\s*([^，。；]+)",
    ]
    for subject, subj_pattern in subject_patterns.items():
        for subj_match in re.finditer(subj_pattern, clause.content):
            # 查找该主体后的义务内容
            after_subj = clause.content[subj_match.start():]
            for action_pattern in action_patterns:
                action_match = re.search(action_pattern, after_subj)
                if action_match:
                    action_text = action_match.group(1).strip()
                    # 提取期限
                    deadline = None
                    deadline_match = re.search(r"(?:于|在|自)?([^，。；]*?(?:日内|日前|之前|以内))", action_text)
                    if deadline_match:
                        deadline = deadline_match.group(1).strip()
                    obligations.append({
                        "subject": subject,
                        "action": action_text[:50],
                        "deadline": deadline or "未明确",
                    })
                    break
    return obligations


def extract_risks(clause: Clause) -> List[Dict[str, str]]:
    """提取风险信息"""
    risks = []
    risk_patterns = [
        ("模糊表述", ["合理", "适当", "尽快", "相关", "等"]),
        ("单方权利", ["有权单方", "可随时", "无需通知", "单方决定"]),
        ("责任限制", ["不承担责任", "免责", "上限为", "最高不超过"]),
        ("强制义务", ["必须", "不得", "禁止", "应当"]),
        ("时间压力", ["立即", "三日内", "七日内", "十五日内", "逾期"]),
    ]
    for risk_type, keywords in risk_patterns:
        for keyword in keywords:
            if keyword in clause.content:
                # 找到关键词所在句子
                sentences = re.split(r"[。；\n]", clause.content)
                for sentence in sentences:
                    if keyword in sentence:
                        risks.append({
                            "type": risk_type,
                            "keyword": keyword,
                            "description": sentence.strip()[:100],
                        })
                        break
                break  # 每个类型只标记一次
    return risks


def parse_text(text: str, mode: str = "full") -> ParseResult:
    """解析文本主函数"""
    try:
        if not text or not text.strip():
            return ParseResult(
                success=False,
                error_code="E001",
                error_message="输入文本为空",
                confidence=0.0,
            )
        if len(text) > MAX_TEXT_LENGTH:
            return ParseResult(
                success=False,
                error_code="E006",
                error_message=f"文本超出长度限制（{MAX_TEXT_LENGTH} 字符）",
                confidence=0.0,
            )

        result_data: Dict[str, Any] = {}
        warnings = []

        if mode in ("full", "fields"):
            # 提取关键字段
            parties = extract_parties(text)
            if parties:
                result_data["parties"] = parties
            amount = extract_amount(text)
            if amount:
                result_data["amount"] = amount
            date = extract_date(text)
            if date:
                result_data["date"] = date

        if mode in ("full", "clause"):
            # 条款切分
            clauses = split_clauses(text)
            if clauses:
                result_data["clauses"] = []
                for clause in clauses:
                    clause_dict = {
                        "id": clause.id,
                        "title": clause.title,
                        "content": clause.content[:200],
                    }
                    # 义务识别
                    obligations = extract_obligations(clause)
                    if obligations:
                        clause_dict["obligations"] = obligations
                    # 风险标注
                    risks = extract_risks(clause)
                    if risks:
                        clause_dict["risks"] = risks
                    result_data["clauses"].append(clause_dict)
                result_data["clause_count"] = len(clauses)
            else:
                warnings.append("未检测到条款编号，请检查文本格式")

        # 计算置信度
        confidence = 0.9
        if mode == "clause" and "clauses" not in result_data:
            confidence = 0.3
        elif mode == "fields" and not result_data:
            confidence = 0.2

        return ParseResult(
            success=True,
            data=result_data,
            confidence=confidence,
            warnings=warnings,
        )
    except Exception as e:
        return ParseResult(
            success=False,
            error_code="E010",
            error_message=f"未知错误: {str(e)}",
            confidence=0.0,
        )


def parse_file(file_path: str, file_format: str = "txt") -> ParseResult:
    """解析文件"""
    try:
        if not os.path.exists(file_path):
            return ParseResult(
                success=False,
                error_code="E002",
                error_message=f"文件不存在: {file_path}",
                confidence=0.0,
            )
        file_size = os.path.getsize(file_path)
        if file_size > MAX_FILE_SIZE:
            return ParseResult(
                success=False,
                error_code="E006",
                error_message=f"文件超出大小限制（5MB）",
                confidence=0.0,
            )

        content = read_file_with_fallback(file_path)

        if file_format == "json":
            try:
                data = json.loads(content)
                return ParseResult(
                    success=True,
                    data={"json_data": data},
                    confidence=0.95,
                )
            except json.JSONDecodeError as e:
                return ParseResult(
                    success=False,
                    error_code="E004",
                    error_message=f"JSON 解析失败: {str(e)}",
                    confidence=0.0,
                )
        elif file_format == "csv":
            try:
                reader = csv.DictReader(io.StringIO(content))
                rows = list(reader)
                return ParseResult(
                    success=True,
                    data={"csv_rows": rows, "fieldnames": reader.fieldnames},
                    confidence=0.95,
                )
            except Exception as e:
                return ParseResult(
                    success=False,
                    error_code="E005",
                    error_message=f"CSV 解析失败: {str(e)}",
                    confidence=0.0,
                )
        else:
            # txt / md 格式
            return parse_text(content, mode="full")
    except FileNotFoundError:
        return ParseResult(
            success=False,
            error_code="E002",
            error_message=f"文件不存在: {file_path}",
            confidence=0.0,
        )
    except Exception as e:
        return ParseResult(
            success=False,
            error_code="E010",
            error_message=f"未知错误: {str(e)}",
            confidence=0.0,
        )


def fetch_url(url: str) -> ParseResult:
    """抓取 URL 内容"""
    for attempt in range(URL_MAX_RETRIES):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=URL_TIMEOUT) as response:
                content = response.read().decode("utf-8", errors="replace")
                return ParseResult(
                    success=True,
                    data={"url": url, "content": content[:MAX_TEXT_LENGTH]},
                    confidence=0.9,
                )
        except Exception as e:
            if attempt < URL_MAX_RETRIES - 1:
                # 指数退避
                wait_time = 2 ** attempt
                time.sleep(wait_time)
            else:
                return ParseResult(
                    success=False,
                    error_code="E003",
                    error_message=f"URL 访问失败: {str(e)}",
                    confidence=0.0,
                )
    return ParseResult(
        success=False,
        error_code="E003",
        error_message="URL 访问失败",
        confidence=0.0,
    )


def batch_process(lines: str, delimiter: str = ",") -> ParseResult:
    """批量处理"""
    try:
        if not lines or not lines.strip():
            return ParseResult(
                success=False,
                error_code="E009",
                error_message="批量处理输入为空",
                confidence=0.0,
            )
        if not delimiter or len(delimiter) > 1:
            return ParseResult(
                success=False,
                error_code="E008",
                error_message="分隔符无效",
                confidence=0.0,
            )
        items = [item.strip() for item in lines.split(delimiter) if item.strip()]
        results = []
        for item in items:
            result = parse_text(item, mode="fields")
            results.append(result.to_dict())
        return ParseResult(
            success=True,
            data={"batch_results": results, "count": len(results)},
            confidence=0.85,
        )
    except Exception as e:
        return ParseResult(
            success=False,
            error_code="E010",
            error_message=f"未知错误: {str(e)}",
            confidence=0.0,
        )


def compare_texts(text1: str, text2: str) -> ParseResult:
    """对比两个文本的差异"""
    try:
        if not text1 or not text2:
            return ParseResult(
                success=False,
                error_code="E001",
                error_message="需要提供两个版本的文本",
                confidence=0.0,
            )
        clauses1 = split_clauses(text1)
        clauses2 = split_clauses(text2)
        diff = []
        for clause in clauses1:
            found = False
            for clause2 in clauses2:
                if clause.id == clause2.id:
                    found = True
                    if clause.content != clause2.content:
                        diff.append({
                            "clause_id": clause.id,
                            "type": "modified",
                            "old": clause.content[:100],
                            "new": clause2.content[:100],
                        })
                    break
            if not found:
                diff.append({
                    "clause_id": clause.id,
                    "type": "deleted",
                    "old": clause.content[:100],
                    "new": "",
                })
        for clause in clauses2:
            found = False
            for clause1 in clauses1:
                if clause.id == clause1.id:
                    found = True
                    break
            if not found:
                diff.append({
                    "clause_id": clause.id,
                    "type": "added",
                    "old": "",
                    "new": clause.content[:100],
                })
        return ParseResult(
            success=True,
            data={"diff": diff, "diff_count": len(diff)},
            confidence=0.9,
        )
    except Exception as e:
        return ParseResult(
            success=False,
            error_code="E010",
            error_message=f"未知错误: {str(e)}",
            confidence=0.0,
        )


# ---------------------------------------------------------------------------
# 输出格式化
# ---------------------------------------------------------------------------
def format_output(result: ParseResult, output_format: str = "json") -> str:
    """格式化输出"""
    if output_format == "json":
        return json.dumps(result.to_dict(), ensure_ascii=False, indent=2)
    else:
        # Markdown 格式
        lines = ["# 解析结果", ""]
        if result.success and result.data:
            for key, value in result.data.items():
                if isinstance(value, list):
                    lines.append(f"## {key}")
                    for item in value:
                        if isinstance(item, dict):
                            lines.append(f"- {json.dumps(item, ensure_ascii=False)}")
                        else:
                            lines.append(f"- {item}")
                elif isinstance(value, dict):
                    lines.append(f"## {key}")
                    for k, v in value.items():
                        lines.append(f"- {k}: {v}")
                else:
                    lines.append(f"## {key}")
                    lines.append(f"{value}")
        else:
            lines.append(f"错误: {result.error_message}")
        lines.append("")
        lines.append(f"置信度: {result.confidence}")
        if result.warnings:
            lines.append("")
            lines.append("## 警告")
            for warning in result.warnings:
                lines.append(f"- {warning}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# 自检函数
# ---------------------------------------------------------------------------
def run_selftest() -> int:
    """运行自检，返回退出码"""
    print("=" * 60)
    print("运行自检...")
    print("=" * 60)

    # 测试 1: 文本解析
    print("\n[测试 1] 文本解析")
    result = parse_text("甲方：张三；乙方：李四；金额：100元", mode="fields")
    assert result.success, f"文本解析失败: {result.error_message}"
    assert "parties" in result.data, "未提取到 parties"
    assert result.data["parties"].get("甲方") == "张三", f"甲方提取错误: {result.data['parties']}"
    assert result.data["parties"].get("乙方") == "李四", f"乙方提取错误: {result.data['parties']}"
    assert result.data.get("amount") == "100元", f"金额提取错误: {result.data.get('amount')}"
    print("  ✓ 文本解析测试通过")

    # 测试 2: 条款切分
    print("\n[测试 2] 条款切分")
    test_text = "第一条 定义 1.1 本合同所称'货物'指甲方提供的所有产品。第二条 付款 2.1 乙方应于收到货物后15日内支付货款。"
    result = parse_text(test_text, mode="clause")
    assert result.success, f"条款切分失败: {result.error_message}"
    assert "clauses" in result.data, "未提取到 clauses"
    assert len(result.data["clauses"]) >= 2, f"条款数量不足: {len(result.data['clauses'])}"
    print(f"  ✓ 条款切分测试通过（{len(result.data['clauses'])} 条）")

    # 测试 3: 义务识别
    print("\n[测试 3] 义务识别")
    found_obligation = False
    for clause in result.data["clauses"]:
        if "obligations" in clause:
            found_obligation = True
            break
    assert found_obligation, "未识别到义务"
    print("  ✓ 义务识别测试通过")

    # 测试 4: 风险标注
    print("\n[测试 4] 风险标注")
    # 使用包含明确风险关键词的文本，确保能识别到风险
    risk_test_text = "第一条 定义 1.1 本合同所称'货物'指甲方提供的所有产品。第二条 付款 2.1 乙方应于收到货物后15日内支付货款。第三条 免责 3.1 甲方不承担责任，且有权单方决定终止合同。"
    result = parse_text(risk_test_text, mode="clause")
    assert result.success, f"风险标注解析失败: {result.error_message}"
    found_risk = False
    for clause in result.data["clauses"]:
        if "risks" in clause:
            found_risk = True
            break
    assert found_risk, "未识别到风险"
    print("  ✓ 风险标注测试通过")

    # 测试 5: 文件解析
    print("\n[测试 5] 文件解析")
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
        f.write("甲方：测试公司\n乙方：测试个人\n金额：500元")
        temp_path = f.name
    try:
        result = parse_file(temp_path, "txt")
        assert result.success, f"文件解析失败: {result.error_message}"
        assert "parties" in result.data, "文件解析未提取到 parties"
        print("  ✓ 文件解析测试通过")
    finally:
        os.unlink(temp_path)

    # 测试 6: 批量处理
    print("\n[测试 6] 批量处理")
    result = batch_process("甲方：A；乙方：B,甲方：C；乙方：D", ",")
    assert result.success, f"批量处理失败: {result.error_message}"
    assert result.data["count"] == 2, f"批量处理数量错误: {result.data['count']}"
    print("  ✓ 批量处理测试通过")

    # 测试 7: 文本对比
    print("\n[测试 7] 文本对比")
    text1 = "第一条 定义 1.1 货物指甲方提供的产品。第二条 付款 2.1 乙方应于15日内付款。"
    text2 = "第一条 定义 1.1 货物指甲方提供的所有产品。第二条 付款 2.1 乙方应于30日内付款。"
    result = compare_texts(text1, text2)
    assert result.success, f"文本对比失败: {result.error_message}"
    assert result.data["diff_count"] >= 1, f"未检测到差异: {result.data['diff_count']}"
    print(f"  ✓ 文本对比测试通过（{result.data['diff_count']} 处差异）")

    # 测试 8: 空输入处理
    print("\n[测试 8] 空输入处理")
    result = parse_text("", mode="full")
    assert not result.success, "空输入应该失败"
    assert result.error_code == "E001", f"错误码错误: {result.error_code}"
    print("  ✓ 空输入处理测试通过")

    # 测试 9: 超长输入处理
    print("\n[测试 9] 超长输入处理")
    long_text = "a" * (MAX_TEXT_LENGTH + 100)
    result = parse_text(long_text, mode="full")
    assert not result.success, "超长输入应该失败"
    assert result.error_code == "E006", f"错误码错误: {result.error_code}"
    print("  ✓ 超长输入处理测试通过")

    # 测试 10: 编码处理
    print("\n[测试 10] 编码处理")
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="gbk") as f:
        f.write("甲方：测试公司\n乙方：测试个人")
        temp_path = f.name
    try:
        result = parse_file(temp_path, "txt")
        assert result.success, f"GBK 编码文件解析失败: {result.error_message}"
        print("  ✓ 编码处理测试通过")
    finally:
        os.unlink(temp_path)

    print("\n" + "=" * 60)
    print("所有自检测试通过！")
    print("=" * 60)
    return 0


# ---------------------------------------------------------------------------
# 主函数
# ---------------------------------------------------------------------------
def main():
    """CLI 入口"""
    parser = argparse.ArgumentParser(
        description="条款解析与合规审查工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""示例：
  python run.py parse --text "甲方：张三；乙方：李四；金额：100元"
  python run.py parse --text "第一条 定义..." --mode clause
  python run.py file --path ./data.csv --format csv
  python run.py url --url https://example.com
  python run.py batch --lines "a,b,c" --delimiter ","
  python run.py compare --text1 "旧版..." --text2 "新版..."
  python run.py --selftest
""",
    )

    # 全局参数
    parser.add_argument("--selftest", action="store_true", help="运行自检")
    parser.add_argument("--dry-run", action="store_true", help="预览模式，不实际写盘")
    parser.add_argument("--verbose", action="store_true", help="输出详细日志")
    parser.add_argument("--format", choices=["json", "markdown"], default="json", help="输出格式")
    parser.add_argument("--output", "-o", help="输出文件路径")

    # 子命令
    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # parse 命令
    parse_parser = subparsers.add_parser("parse", help="解析文本")
    parse_parser.add_argument("--text", required=False, help="待解析的文本")
    parse_parser.add_argument("--mode", choices=["full", "fields", "clause"], default="full", help="解析模式")

    # file 命令
    file_parser = subparsers.add_parser("file", help="解析文件")
    file_parser.add_argument("--path", required=False, help="文件路径")
    file_parser.add_argument("--format", choices=["txt", "md", "csv", "json"], default="txt", help="文件格式")

    # url 命令
    url_parser = subparsers.add_parser("url", help="抓取 URL")
    url_parser.add_argument("--url", required=False, help="URL 地址")

    # batch 命令
    batch_parser = subparsers.add_parser("batch", help="批量处理")
    batch_parser.add_argument("--lines", required=False, help="批量输入（用分隔符分隔）")
    batch_parser.add_argument("--delimiter", default=",", help="分隔符")

    # compare 命令
    compare_parser = subparsers.add_parser("compare", help="对比两个文本")
    compare_parser.add_argument("--text1", required=False, help="第一个文本")
    compare_parser.add_argument("--text2", required=False, help="第二个文本")

    args = parser.parse_args()

    global dry_run

    dry_run = getattr(args, "dry_run", False)  # v3.274 同步到全局

    # 自检模式
    if args.selftest:
        sys.exit(run_selftest())

    # 执行子命令
    result = None
    if args.command == "parse":
        result = parse_text(args.text, mode=args.mode)
    elif args.command == "file":
        result = parse_file(args.path, args.format)
    elif args.command == "url":
        result = fetch_url(args.url)
    elif args.command == "batch":
        result = batch_process(args.lines, args.delimiter)
    elif args.command == "compare":
        result = compare_texts(args.text1, args.text2)
    else:
        parser.print_help()
        sys.exit(1)

    # 输出结果
    output = format_output(result, args.format)

    if args.output:
        if not dry_run:
            try:
                atomic_write(args.output, output)
                print(f"结果已写入: {args.output}")
            except Exception as e:
                print(f"写入失败: {e}", file=sys.stderr)
                sys.exit(1)
        else:
            print(f"[DRY-RUN] 将写入: {args.output}")
            print(f"[DRY-RUN] 内容摘要: {output[:200]}...")
    else:
        print(output)

    # 非成功时返回非零退出码
    if not result.success:
        sys.exit(1)


if __name__ == "__main__":
    main()
