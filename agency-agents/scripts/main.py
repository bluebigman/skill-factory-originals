#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
run.py — 多角色任务编排与结构化交付工具

功能概述：
    将输入文本数据转换为结构化结果，支持批量处理、置信度标注，
    以及 JSON / CSV / Markdown 表格 / 自定义模板等输出格式。

设计原则：
    1. 仅依据功能规格独立实现，不参考任何既有代码。
    2. 标准库优先，无第三方依赖。
    3. 提供 --selftest 离线自检，使用内置硬编码样例，不访问外部资源。

错误码约定：
    E001 参数解析失败
    E002 输入数据为空或格式非法
    E003 输出格式不支持
    E004 字段映射配置非法
    E005 模板渲染失败
    E006 内部数据转换异常
    E007 自检断言失败
    E008 文件读取失败
    E009 文件写入失败
    E010 未知运行时错误
"""

import argparse
import csv
import io
import json
import os
import re
import sys
import tempfile
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
dry_run = False  # v3.274 模块级 dry-run 标志


# ---------------------------------------------------------------
# 核心数据结构
# ---------------------------------------------------------------

class FieldExtractor:
    """
    字段提取器：从原始文本中提取指定字段，并附带置信度标注。

    支持字段类型：
        - text      : 普通文本片段（按行截取，每行最多200字符）
        - number    : 数字（整数/小数）
        - date      : 日期（支持常见格式）
        - email     : 电子邮件地址
        - url       : 网页链接
        - entity    : 实体（专有名词，如产品名、人名）
    """

    # 常见日期格式模式（宽松匹配）
    _DATE_PATTERNS = [
        r"\d{4}[-/年]\d{1,2}[-/月]\d{1,2}日?",
        r"\d{4}[-/]\d{1,2}[-/]\d{1,2}",
        r"\d{1,2}[-/]\d{1,2}[-/]\d{2,4}",
        r"\d{1,2}月\d{1,2}日",
    ]

    # 电子邮件模式
    _EMAIL_PATTERN = r"[\w.+-]+@[\w-]+\.[\w.-]+"

    # URL 模式
    _URL_PATTERN = r"https?://[^\s<>\"']+|www\.[^\s<>\"']+"

    # 数字模式（整数、小数、负数）
    _NUMBER_PATTERN = r"-?\d+(?:\.\d+)?"

    # 实体模式（中文/英文/数字组合）
    _ENTITY_PATTERN = r"[\u4e00-\u9fa5A-Za-z0-9]+(?:[\s·][\u4e00-\u9fa5A-Za-z0-9]+)*"

    def __init__(self, field_spec: Dict[str, str]):
        """
        初始化字段提取器。

        参数：
            field_spec: 字段定义字典，格式为 {字段名: 字段类型}
                        例如 {"产品名称": "text", "价格": "number", "日期": "date"}
        """
        if not isinstance(field_spec, dict) or not field_spec:
            raise ValueError("E004: 字段映射配置非法，字段定义不能为空")

        self.field_spec = field_spec
        self._validate_field_spec()

    def _validate_field_spec(self) -> None:
        """校验字段定义合法性。"""
        valid_types = {"text", "number", "date", "email", "url", "entity"}
        for field_name, field_type in self.field_spec.items():
            if not field_name or not isinstance(field_name, str):
                raise ValueError("E004: 字段名必须为非空字符串")
            if field_type not in valid_types:
                raise ValueError(
                    f"E004: 字段 '{field_name}' 的类型 '{field_type}' 不支持，"
                    f"可选类型: {', '.join(sorted(valid_types))}"
                )

    def extract(self, text: str) -> Dict[str, Any]:
        """
        从文本中提取所有配置的字段。

        参数：
            text: 输入文本

        返回：
            提取结果字典，格式为 {字段名: 提取值}
            未找到的字段标记为 "[需核实:字段名]"
        """
        if not text or not isinstance(text, str):
            return {field: f"[需核实:{field}]" for field in self.field_spec}

        result = {}
        for field_name, field_type in self.field_spec.items():
            try:
                value = self._extract_field(text, field_type)
                result[field_name] = value if value is not None else f"[需核实:{field_name}]"
            except Exception as e:
                # 降级输出：提取失败时标记需核实
                result[field_name] = f"[需核实:{field_name}]"
                print(f"警告: 字段 '{field_name}' 提取失败: {e}", file=sys.stderr)

        return result

    def _extract_field(self, text: str, field_type: str) -> Optional[Any]:
        """根据字段类型提取对应值。"""
        if field_type == "text":
            return self._extract_text(text)
        elif field_type == "number":
            return self._extract_number(text)
        elif field_type == "date":
            return self._extract_date(text)
        elif field_type == "email":
            return self._extract_email(text)
        elif field_type == "url":
            return self._extract_url(text)
        elif field_type == "entity":
            return self._extract_entity(text)
        return None

    def _extract_text(self, text: str) -> Optional[str]:
        """提取文本：取第一行，最多200字符。"""
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        if not lines:
            return None
        return lines[0][:200]

    def _extract_number(self, text: str) -> Optional[float]:
        """提取数字：匹配第一个数字。"""
        match = re.search(self._NUMBER_PATTERN, text)
        if match:
            try:
                return float(match.group())
            except ValueError:
                return None
        return None

    def _extract_date(self, text: str) -> Optional[str]:
        """提取日期：匹配常见日期格式。"""
        for pattern in self._DATE_PATTERNS:
            match = re.search(pattern, text)
            if match:
                return match.group()
        return None

    def _extract_email(self, text: str) -> Optional[str]:
        """提取邮箱：匹配第一个邮箱地址。"""
        match = re.search(self._EMAIL_PATTERN, text)
        return match.group() if match else None

    def _extract_url(self, text: str) -> Optional[str]:
        """提取URL：匹配第一个链接。"""
        match = re.search(self._URL_PATTERN, text)
        return match.group() if match else None

    def _extract_entity(self, text: str) -> Optional[str]:
        """提取实体：匹配第一个专有名词。"""
        match = re.search(self._ENTITY_PATTERN, text)
        return match.group() if match else None


# ---------------------------------------------------------------
# 输出格式化
# ---------------------------------------------------------------

class OutputFormatter:
    """输出格式化器：将提取结果转换为指定格式。"""

    @staticmethod
    def format_json(data: Any) -> str:
        """格式化为 JSON 字符串。"""
        return json.dumps(data, ensure_ascii=False, indent=2)

    @staticmethod
    def format_csv(data: List[Dict[str, Any]]) -> str:
        """格式化为 CSV 字符串（带 UTF-8 BOM）。"""
        if not data:
            return "\ufeff"  # 仅返回 BOM

        # 收集所有字段名
        fieldnames = []
        for item in data:
            for key in item.keys():
                if key not in fieldnames:
                    fieldnames.append(key)

        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        for item in data:
            writer.writerow(item)

        return "\ufeff" + output.getvalue()

    @staticmethod
    def format_markdown(data: List[Dict[str, Any]]) -> str:
        """格式化为 Markdown 表格。"""
        if not data:
            return "*空结果*"

        # 收集所有字段名
        fieldnames = []
        for item in data:
            for key in item.keys():
                if key not in fieldnames:
                    fieldnames.append(key)

        # 生成表头
        lines = ["| " + " | ".join(fieldnames) + " |"]
        lines.append("| " + " | ".join(["---"] * len(fieldnames)) + " |")

        # 生成数据行
        for item in data:
            row = []
            for field in fieldnames:
                value = item.get(field, "")
                # 转义 Markdown 特殊字符
                value = str(value).replace("|", "\\|")
                row.append(value)
            lines.append("| " + " | ".join(row) + " |")

        return "\n".join(lines)

    @staticmethod
    def format_text(data: Any) -> str:
        """格式化为纯文本。"""
        if isinstance(data, list):
            return "\n".join(str(item) for item in data)
        return str(data)

    @staticmethod
    def format_template(data: Any, template: str) -> str:
        """按自定义模板渲染。"""
        try:
            if isinstance(data, dict):
                return template.format(**data)
            elif isinstance(data, list):
                return "\n".join(template.format(**item) for item in data)
            return template
        except KeyError as e:
            raise ValueError(f"E005: 模板渲染失败，缺少字段: {e}")
        except Exception as e:
            raise ValueError(f"E005: 模板渲染失败: {e}")


# ---------------------------------------------------------------
# 文件读写工具
# ---------------------------------------------------------------

def read_text_file(file_path: str) -> str:
    """
    读取文本文件，支持多编码。

    编码检测顺序：UTF-8 → GBK → GB18030 → 使用 errors="replace"
    """
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"E008: 文件不存在: {file_path}")

    encodings = ["utf-8", "gbk", "gb18030"]
    for encoding in encodings:
        try:
            with open(file_path, "r", encoding=encoding) as f:
                return f.read()
        except UnicodeDecodeError:
            continue

    # 最后尝试：使用 replace 错误处理
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def write_text_file_atomic(file_path: str, content: str) -> None:
    """
    原子化写入文本文件。

    先写入临时文件，再原子替换目标文件，避免写入中断导致文件损坏。
    """
    directory = os.path.dirname(os.path.abspath(file_path))
    if not os.path.isdir(directory):
        raise FileNotFoundError(f"E009: 目录不存在: {directory}")

    # 创建临时文件
    fd, temp_path = tempfile.mkstemp(dir=directory, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        # 原子替换
        os.replace(temp_path, file_path)
    except Exception as e:
        # 清理临时文件
        if os.path.exists(temp_path):
            os.unlink(temp_path)
        raise IOError(f"E009: 文件写入失败: {e}")


# ---------------------------------------------------------------
# 批量处理
# ---------------------------------------------------------------

def process_batch(text: str, extractor: FieldExtractor) -> List[Dict[str, Any]]:
    """
    批量处理：按行分割输入文本，逐行提取字段。

    参数：
        text: 输入文本（每行一条记录）
        extractor: 字段提取器

    返回：
        提取结果列表，每项包含 index 和 result
    """
    results = []
    lines = text.split('\n')

    for idx, line in enumerate(lines, 1):
        line = line.strip()
        if not line:
            continue

        try:
            extracted = extractor.extract(line)
            results.append({
                "index": idx,
                "result": extracted
            })
        except Exception as e:
            # 降级输出：单行处理失败时记录错误
            results.append({
                "index": idx,
                "result": {"error": f"处理失败: {e}"}
            })
            print(f"警告: 第 {idx} 行处理失败: {e}", file=sys.stderr)

    return results


# ---------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------

def parse_fields(fields_str: str) -> Dict[str, str]:
    """
    解析字段定义字符串。

    格式: "字段名1:类型1 字段名2:类型2"
    示例: "名称:text 价格:number 日期:date"
    """
    if not fields_str or not isinstance(fields_str, str):
        raise ValueError("E004: 字段定义不能为空")

    field_spec = {}
    parts = fields_str.strip().split()

    for part in parts:
        if ":" not in part:
            raise ValueError(f"E004: 字段定义格式错误: '{part}'，应为 '字段名:类型'")

        field_name, field_type = part.rsplit(":", 1)
        field_name = field_name.strip()
        field_type = field_type.strip()

        if not field_name:
            raise ValueError("E004: 字段名不能为空")
        if not field_type:
            raise ValueError(f"E004: 字段 '{field_name}' 的类型不能为空")

        field_spec[field_name] = field_type

    if not field_spec:
        raise ValueError("E004: 字段定义不能为空")

    return field_spec


def process_single(text: str, extractor: FieldExtractor) -> Dict[str, Any]:
    """处理单条文本。"""
    extracted = extractor.extract(text)
    return {
        "status": "ok",
        "data": extracted,
        "meta": {
            "fields_extracted": sum(1 for v in extracted.values() if not str(v).startswith("[需核实")),
            "fields_total": len(extracted),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    }


def format_output(data: Any, output_format: str, template: Optional[str] = None) -> str:
    """根据指定格式格式化输出。"""
    formatter = OutputFormatter()

    if template:
        return formatter.format_template(data, template)

    if output_format == "json":
        return formatter.format_json(data)
    elif output_format == "csv":
        if isinstance(data, dict) and "data" in data:
            return formatter.format_csv([data["data"]])
        elif isinstance(data, list):
            return formatter.format_csv([item["result"] for item in data])
        return formatter.format_csv([data])
    elif output_format == "markdown":
        if isinstance(data, dict) and "data" in data:
            return formatter.format_markdown([data["data"]])
        elif isinstance(data, list):
            return formatter.format_markdown([item["result"] for item in data])
        return formatter.format_markdown([data])
    elif output_format == "text":
        return formatter.format_text(data)
    else:
        raise ValueError(f"E003: 不支持的输出格式: {output_format}")


# ---------------------------------------------------------------
# 自检模式
# ---------------------------------------------------------------

def run_selftest() -> int:
    """
    运行自检，验证核心功能。

    返回：
        0 表示全部通过，非 0 表示有失败
    """
    print("=== 自检开始 ===")
    failures = 0

    # 测试 1：字段提取 - 数字
    print("\n[测试 1] 数字提取")
    try:
        extractor = FieldExtractor({"价格": "number"})
        result = extractor.extract("产品A 价格99元")
        assert result["价格"] == 99.0, f"期望 99.0，实际 {result['价格']}"
        print("  通过: 数字提取正确")
    except AssertionError as e:
        print(f"  失败: {e}")
        failures += 1
    except Exception as e:
        print(f"  失败: 异常 {e}")
        failures += 1

    # 测试 2：字段提取 - 日期
    print("\n[测试 2] 日期提取")
    try:
        extractor = FieldExtractor({"日期": "date"})
        result = extractor.extract("会议日期 2024-01-15 举行")
        assert result["日期"] == "2024-01-15", f"期望 2024-01-15，实际 {result['日期']}"
        print("  通过: 日期提取正确")
    except AssertionError as e:
        print(f"  失败: {e}")
        failures += 1
    except Exception as e:
        print(f"  失败: 异常 {e}")
        failures += 1

    # 测试 3：字段提取 - 邮箱
    print("\n[测试 3] 邮箱提取")
    try:
        extractor = FieldExtractor({"邮箱": "email"})
        result = extractor.extract("联系邮箱 test@example.com 获取更多信息")
        assert result["邮箱"] == "test@example.com", f"期望 test@example.com，实际 {result['邮箱']}"
        print("  通过: 邮箱提取正确")
    except AssertionError as e:
        print(f"  失败: {e}")
        failures += 1
    except Exception as e:
        print(f"  失败: 异常 {e}")
        failures += 1

    # 测试 4：字段提取 - 缺失字段
    print("\n[测试 4] 缺失字段标记")
    try:
        extractor = FieldExtractor({"名称": "text", "价格": "number"})
        result = extractor.extract("只有名称没有价格")
        assert result["名称"] == "只有名称没有价格", f"期望 '只有名称没有价格'，实际 {result['名称']}"
        assert result["价格"] == "[需核实:价格]", f"期望 '[需核实:价格]'，实际 {result['价格']}"
        print("  通过: 缺失字段正确标记")
    except AssertionError as e:
        print(f"  失败: {e}")
        failures += 1
    except Exception as e:
        print(f"  失败: 异常 {e}")
        failures += 1

    # 测试 5：批量处理
    print("\n[测试 5] 批量处理")
    try:
        extractor = FieldExtractor({"名称": "text", "价格": "number"})
        text = "产品A 99元\n产品B 199元\n产品C 299元"
        results = process_batch(text, extractor)
        assert len(results) == 3, f"期望 3 条结果，实际 {len(results)}"
        # 修正：text 类型提取的是整行内容，所以期望值是整行
        assert results[0]["result"]["名称"] == "产品A 99元", f"期望 '产品A 99元'，实际 {results[0]['result']['名称']}"
        assert results[1]["result"]["价格"] == 199.0, f"期望 199.0，实际 {results[1]['result']['价格']}"
        print("  通过: 批量处理正确")
    except AssertionError as e:
        print(f"  失败: {e}")
        failures += 1
    except Exception as e:
        print(f"  失败: 异常 {e}")
        failures += 1

    # 测试 6：CSV 格式化
    print("\n[测试 6] CSV 格式化")
    try:
        formatter = OutputFormatter()
        data = [{"名称": "产品A", "价格": 99.0}]
        csv_output = formatter.format_csv(data)
        assert csv_output.startswith("\ufeff"), "CSV 应包含 UTF-8 BOM"
        assert "产品A" in csv_output, "CSV 应包含数据"
        print("  通过: CSV 格式化正确")
    except AssertionError as e:
        print(f"  失败: {e}")
        failures += 1
    except Exception as e:
        print(f"  失败: 异常 {e}")
        failures += 1

    # 测试 7：Markdown 格式化
    print("\n[测试 7] Markdown 格式化")
    try:
        formatter = OutputFormatter()
        data = [{"名称": "产品A", "价格": 99.0}]
        md_output = formatter.format_markdown(data)
        assert "| 名称 | 价格 |" in md_output, "Markdown 应包含表头"
        assert "| 产品A | 99.0 |" in md_output, "Markdown 应包含数据行"
        print("  通过: Markdown 格式化正确")
    except AssertionError as e:
        print(f"  失败: {e}")
        failures += 1
    except Exception as e:
        print(f"  失败: 异常 {e}")
        failures += 1

    # 测试 8：模板渲染
    print("\n[测试 8] 模板渲染")
    try:
        formatter = OutputFormatter()
        data = {"名称": "产品A", "价格": 99.0}
        # 修正：使用正确的模板语法（{} 而不是 {{}}）
        output = formatter.format_template(data, "{名称} 售价 {价格} 元")
        assert output == "产品A 售价 99.0 元", f"期望 '产品A 售价 99.0 元'，实际 '{output}'"
        print("  通过: 模板渲染正确")
    except AssertionError as e:
        print(f"  失败: {e}")
        failures += 1
    except Exception as e:
        print(f"  失败: 异常 {e}")
        failures += 1

    # 测试 9：空输入处理
    print("\n[测试 9] 空输入处理")
    try:
        extractor = FieldExtractor({"名称": "text"})
        result = extractor.extract("")
        assert result["名称"] == "[需核实:名称]", f"期望 '[需核实:名称]'，实际 {result['名称']}"
        print("  通过: 空输入正确标记")
    except AssertionError as e:
        print(f"  失败: {e}")
        failures += 1
    except Exception as e:
        print(f"  失败: 异常 {e}")
        failures += 1

    # 测试 10：非法字段类型
    print("\n[测试 10] 非法字段类型")
    try:
        FieldExtractor({"字段": "invalid_type"})
        print("  失败: 应抛出 ValueError")
        failures += 1
    except ValueError:
        print("  通过: 正确拒绝非法字段类型")
    except Exception as e:
        print(f"  失败: 异常 {e}")
        failures += 1

    # 测试 11：中文标点
    print("\n[测试 11] 中文标点处理")
    try:
        extractor = FieldExtractor({"名称": "text", "价格": "number"})
        result = extractor.extract("产品：苹果，价格：１２８元")
        assert result["名称"] == "产品：苹果，价格：１２８元", f"期望 '产品：苹果，价格：１２８元'，实际 {result['名称']}"
        print("  通过: 中文标点处理正确")
    except AssertionError as e:
        print(f"  失败: {e}")
        failures += 1
    except Exception as e:
        print(f"  失败: 异常 {e}")
        failures += 1

    # 测试 12：超长输入
    print("\n[测试 12] 超长输入")
    try:
        extractor = FieldExtractor({"名称": "text"})
        long_text = "A" * 5000
        result = extractor.extract(long_text)
        assert len(result["名称"]) <= 200, f"文本应截断到 200 字符，实际 {len(result['名称'])}"
        print("  通过: 超长输入正确截断")
    except AssertionError as e:
        print(f"  失败: {e}")
        failures += 1
    except Exception as e:
        print(f"  失败: 异常 {e}")
        failures += 1

    # 汇总
    print(f"\n=== 自检完成: {12 - failures}/12 通过 ===")
    return 0 if failures == 0 else 1


# ---------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------

def main() -> int:
    """主入口函数。"""
    parser = argparse.ArgumentParser(
        description="多角色任务编排与结构化交付工具",
        epilog="示例: python run.py --input '产品A 价格99元' --fields '名称:text 价格:number'"
    )

    parser.add_argument("--input", type=str, help="输入文本或文件路径")
    parser.add_argument("--fields", type=str, help="字段定义，格式: '字段名:类型 字段名:类型'")
    parser.add_argument("--format", type=str, default="json",
                        choices=["json", "csv", "markdown", "text"],
                        help="输出格式 (默认: json)")
    parser.add_argument("--batch", action="store_true", help="批量模式，逐行处理输入")
    parser.add_argument("--template", type=str, help="自定义输出模板")
    parser.add_argument("--dry-run", action="store_true", help="预览模式，不写文件")
    parser.add_argument("--verbose", action="store_true", help="详细日志输出")
    parser.add_argument("--selftest", action="store_true", help="运行自检")
    parser.add_argument("--version", action="store_true", help="显示版本号")

    args = parser.parse_args()

    global dry_run

    dry_run = getattr(args, "dry_run", False)  # v3.274 同步到全局

    # 版本号
    if args.version:
        print("agency-agents version 1.1.0")
        return 0

    # 自检模式（必须在必填校验之前）
    if args.selftest:
        return run_selftest()

    # 参数校验（手工校验，不使用 required=False）
    if not args.input:
        print("错误: 缺少必要参数 --input", file=sys.stderr)
        print("用法: python run.py --input <文本或文件路径> --fields <字段定义>", file=sys.stderr)
        return 1

    if not args.fields:
        print("错误: 缺少必要参数 --fields", file=sys.stderr)
        print("用法: python run.py --input <文本或文件路径> --fields <字段定义>", file=sys.stderr)
        return 1

    try:
        # 解析字段定义
        field_spec = parse_fields(args.fields)
        if args.verbose:
            print(f"字段定义: {field_spec}", file=sys.stderr)

        # 创建提取器
        extractor = FieldExtractor(field_spec)

        # 读取输入
        if os.path.isfile(args.input):
            text = read_text_file(args.input)
            if args.verbose:
                print(f"从文件读取: {args.input} ({len(text)} 字符)", file=sys.stderr)
        else:
            text = args.input
            if args.verbose:
                print(f"从参数读取: {len(text)} 字符", file=sys.stderr)

        if not text or not text.strip():
            print("错误: 输入内容为空", file=sys.stderr)
            return 1

        # 处理数据
        if args.batch:
            if args.verbose:
                print("批量模式: 逐行处理", file=sys.stderr)
            results = process_batch(text, extractor)
            output_data = results
        else:
            if args.verbose:
                print("单条模式: 整体处理", file=sys.stderr)
            output_data = process_single(text, extractor)

        # 格式化输出
        output_str = format_output(output_data, args.format, args.template)

        # 输出结果
        if not dry_run:
            print(output_str)
        else:
            print("[dry-run] 将输出以下内容:")
            print(output_str)

        return 0

    except ValueError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1
    except FileNotFoundError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1
    except IOError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"错误: 未知异常 {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
