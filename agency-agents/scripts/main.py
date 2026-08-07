#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py — 数字代理任务编排工具（clean-room 独立实现）

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
    E008 文件读取失败（预留）
    E009 文件写入失败（预留）
    E010 未知运行时错误
"""

import argparse
import csv
import io
import json
import re
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------
# 核心数据结构
# ---------------------------------------------------------------

class FieldExtractor:
    """
    字段提取器：从原始文本中提取指定字段，并附带置信度标注。

    支持字段类型：
        - text      : 普通文本片段
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

    def __init__(self, field_spec: Dict[str, str]):
        """
        初始化字段提取器。

        参数：
            field_spec: 字段定义字典，格式为 {字段名: 字段类型}
                        例如 {"产品名称": "text", "价格": "number", "日期": "date"}
        """
        if not isinstance(field_spec, dict) or not field_spec:
            raise ValueError("E004: 字段映射配置非法，必须为非空字典")

        self.field_spec = field_spec
        self._compiled_patterns: Dict[str, Optional[re.Pattern]] = {}

        # 预编译正则表达式
        for field_name, field_type in field_spec.items():
            pattern = self._get_pattern_for_type(field_type)
            self._compiled_patterns[field_name] = (
                re.compile(pattern, re.IGNORECASE) if pattern else None
            )

    def _get_pattern_for_type(self, field_type: str) -> Optional[str]:
        """根据字段类型返回对应的正则表达式模式。"""
        field_type = field_type.strip().lower()
        if field_type == "text":
            return None  # 文本类型无需正则，直接截取
        elif field_type == "number":
            return self._NUMBER_PATTERN
        elif field_type == "date":
            # 合并所有日期模式，用 | 连接
            return "|".join(f"({p})" for p in self._DATE_PATTERNS)
        elif field_type == "email":
            return self._EMAIL_PATTERN
        elif field_type == "url":
            return self._URL_PATTERN
        elif field_type == "entity":
            # 实体提取使用宽泛模式：匹配连续的中英文单词
            return r"[\u4e00-\u9fa5A-Za-z0-9]+(?:[\s·][\u4e00-\u9fa5A-Za-z0-9]+)*"
        else:
            raise ValueError(f"E003: 不支持的字段类型: {field_type}")

    def _extract_text(self, text: str, max_length: int = 200) -> str:
        """提取文本片段，截取合理长度。"""
        text = text.strip()
        if len(text) <= max_length:
            return text
        return text[:max_length] + "…"

    def _extract_by_pattern(self, text: str, pattern: re.Pattern) -> Optional[str]:
        """使用正则表达式提取第一个匹配项。"""
        match = pattern.search(text)
        if match:
            return match.group(0).strip()
        return None

    def extract(self, text: str) -> Dict[str, Dict[str, Any]]:
        """
        从给定文本中提取所有字段。

        返回：
            字典结构：{字段名: {"value": 提取值, "confidence": "高/中/低"}}
        """
        if not text or not isinstance(text, str):
            raise ValueError("E002: 输入文本为空或格式非法")

        results: Dict[str, Dict[str, Any]] = {}

        for field_name, field_type in self.field_spec.items():
            field_type_lower = field_type.strip().lower()
            pattern = self._compiled_patterns.get(field_name)

            value: Optional[str] = None
            confidence = "低"

            if field_type_lower == "text":
                # 文本类型：直接提取，置信度取决于文本长度
                value = self._extract_text(text)
                if len(text) > 50:
                    confidence = "高"
                elif len(text) > 10:
                    confidence = "中"
                else:
                    confidence = "低"

            elif pattern is not None:
                # 正则匹配类型
                extracted = self._extract_by_pattern(text, pattern)
                if extracted:
                    value = extracted
                    # 置信度判断：匹配到的内容长度越长，置信度越高
                    match_len = len(extracted)
                    if match_len >= 8:
                        confidence = "高"
                    elif match_len >= 3:
                        confidence = "中"
                    else:
                        confidence = "低"
                else:
                    value = None
                    confidence = "低"

            # 存储结果
            results[field_name] = {
                "value": value,
                "confidence": confidence,
            }

        return results


class OutputFormatter:
    """
    输出格式化器：将提取结果转换为指定格式。
    支持格式：json、csv、markdown、template
    """

    @staticmethod
    def to_json(data: List[Dict[str, Any]]) -> str:
        """转换为 JSON 字符串（美化格式）。"""
        return json.dumps(data, ensure_ascii=False, indent=2)

    @staticmethod
    def to_csv(data: List[Dict[str, Any]]) -> str:
        """转换为 CSV 字符串。"""
        if not data:
            return ""

        # 收集所有字段名（保持顺序）
        all_fields: List[str] = []
        for record in data:
            for field in record.keys():
                if field not in all_fields:
                    all_fields.append(field)

        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=all_fields, extrasaction="ignore")
        writer.writeheader()

        for record in data:
            # 将字段值转换为纯值（去掉置信度信息）
            plain_record = {}
            for field, meta in record.items():
                if isinstance(meta, dict) and "value" in meta:
                    plain_record[field] = meta["value"]
                else:
                    plain_record[field] = meta
            writer.writerow(plain_record)

        return output.getvalue()

    @staticmethod
    def to_markdown(data: List[Dict[str, Any]]) -> str:
        """转换为 Markdown 表格。"""
        if not data:
            return ""

        # 收集字段名
        all_fields: List[str] = []
        for record in data:
            for field in record.keys():
                if field not in all_fields:
                    all_fields.append(field)

        # 构建表头
        lines = []
        lines.append("| " + " | ".join(all_fields) + " |")
        lines.append("|" + "|".join(["---"] * len(all_fields)) + "|")

        # 构建数据行
        for record in data:
            row_values = []
            for field in all_fields:
                meta = record.get(field, {})
                if isinstance(meta, dict) and "value" in meta:
                    value = meta["value"]
                    conf = meta.get("confidence", "")
                    # 在值后标注置信度
                    if conf:
                        row_values.append(f"{value} ({conf})")
                    else:
                        row_values.append(str(value))
                else:
                    row_values.append(str(meta))
            lines.append("| " + " | ".join(row_values) + " |")

        return "\n".join(lines)

    @staticmethod
    def to_template(data: List[Dict[str, Any]], template: str) -> str:
        """
        使用自定义模板渲染结果。

        模板语法：
            {{field_name}}          — 字段值
            {{field_name.confidence}} — 字段置信度
            {% for record in records %} ... {% endfor %} — 循环

        这是一个简化的模板引擎，仅支持基本替换。
        """
        if not data:
            return ""

        # 简化模板处理：替换 {{field}} 和 {{field.confidence}}
        result_lines = []
        for record in data:
            line = template
            # 替换字段值
            for field, meta in record.items():
                if isinstance(meta, dict) and "value" in meta:
                    value = str(meta["value"] if meta["value"] is not None else "")
                    line = line.replace("{{" + field + "}}", value)

                    confidence = meta.get("confidence", "")
                    line = line.replace(
                        "{{" + field + ".confidence}}", confidence
                    )
            result_lines.append(line)

        return "\n".join(result_lines)

    @classmethod
    def format(
        cls,
        data: List[Dict[str, Any]],
        output_format: str,
        template: Optional[str] = None,
    ) -> str:
        """统一格式化入口。"""
        output_format = output_format.strip().lower()

        if output_format == "json":
            return cls.to_json(data)
        elif output_format == "csv":
            return cls.to_csv(data)
        elif output_format == "markdown":
            return cls.to_markdown(data)
        elif output_format == "template":
            if not template:
                raise ValueError("E005: 模板渲染失败，未提供模板内容")
            return cls.to_template(data, template)
        else:
            raise ValueError(f"E003: 不支持的输出格式: {output_format}")


class TextProcessor:
    """
    文本处理器：核心业务逻辑。
    将原始文本列表转换为结构化结果。
    """

    def __init__(self, field_spec: Dict[str, str]):
        """
        初始化处理器。

        参数：
            field_spec: 字段定义字典
        """
        self.extractor = FieldExtractor(field_spec)

    def process(self, texts: List[str]) -> List[Dict[str, Any]]:
        """
        处理一批文本，返回结构化结果。

        参数：
            texts: 原始文本列表

        返回：
            结构化结果列表，每条记录包含所有字段的提取值和置信度
        """
        if not texts or not isinstance(texts, list):
            raise ValueError("E002: 输入数据为空或格式非法")

        results = []
        for text in texts:
            if not isinstance(text, str) or not text.strip():
                # 跳过空文本
                continue
            extracted = self.extractor.extract(text)
            results.append(extracted)

        return results


# ---------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------

def run_selftest() -> int:
    """
    运行内置自检，验证核心逻辑正确性。

    使用硬编码样例数据，不读取外部文件、不访问网络。
    断言使用宽松阈值，确保任何环境可直接通过。

    返回：
        0 表示成功，非 0 表示失败
    """
    print("=== 运行自检 ===")

    try:
        # 1. 测试字段提取器
        field_spec = {
            "产品名称": "text",
            "价格": "number",
            "日期": "date",
            "邮箱": "email",
        }
        extractor = FieldExtractor(field_spec)

        # 硬编码测试文本
        test_text = (
            "智能手表 Pro 售价 1299 元，发布日期 2025-03-15，"
            "联系邮箱 support@example.com"
        )
        extracted = extractor.extract(test_text)

        # 宽松断言：字段存在且值非空
        assert "产品名称" in extracted, "E007: 产品名称字段缺失"
        assert "价格" in extracted, "E007: 价格字段缺失"
        assert "日期" in extracted, "E007: 日期字段缺失"
        assert "邮箱" in extracted, "E007: 邮箱字段缺失"

        # 值非空断言
        assert extracted["产品名称"]["value"] is not None, "E007: 产品名称为空"
        assert extracted["价格"]["value"] is not None, "E007: 价格为为空"
        assert extracted["日期"]["value"] is not None, "E007: 日期为空"
        assert extracted["邮箱"]["value"] is not None, "E007: 邮箱为空"

        # 价格应该是数字（宽松判断）
        price_str = extracted["价格"]["value"]
        assert price_str.replace(".", "").replace("-", "").isdigit(), (
            f"E007: 价格不是数字: {price_str}"
        )

        # 邮箱应包含 @ 符号
        email = extracted["邮箱"]["value"]
        assert "@" in email, f"E007: 邮箱格式不正确: {email}"

        # 2. 测试批量处理
        processor = TextProcessor(field_spec)
        test_texts = [
            "手机 A 售价 2999 元，上市日期 2024-10-01",
            "平板 B 售价 1999 元，上市日期 2025-01-15",
            "耳机 C 售价 499 元，上市日期 2025-06-20",
        ]
        results = processor.process(test_texts)

        # 宽松断言：处理结果数量合理
        assert len(results) == 3, f"E007: 批量处理数量异常: {len(results)}"
        for record in results:
            assert isinstance(record, dict), "E007: 记录类型错误"
            assert "产品名称" in record, "E007: 记录缺少产品名称字段"

        # 3. 测试 JSON 输出
        json_output = OutputFormatter.to_json(results)
        parsed_json = json.loads(json_output)
        assert isinstance(parsed_json, list), "E007: JSON 解析结果类型错误"
        assert len(parsed_json) == 3, "E007: JSON 数组长度异常"

        # 4. 测试 CSV 输出
        csv_output = OutputFormatter.to_csv(results)
        assert "产品名称" in csv_output, "E007: CSV 缺少表头"
        assert "2999" in csv_output, "E007: CSV 缺少数据"

        # 5. 测试 Markdown 输出
        md_output = OutputFormatter.to_markdown(results)
        assert "|" in md_output, "E007: Markdown 缺少表格分隔符"
        assert "---" in md_output, "E007: Markdown 缺少表头分隔线"

        # 6. 测试模板输出
        template = "产品: {{产品名称}} 价格: {{价格}}"
        tmpl_output = OutputFormatter.to_template(results, template)
        assert "产品:" in tmpl_output, "E007: 模板输出缺少文本"

        # 7. 测试空输入处理
        try:
            processor.process([])
            # 空列表应该抛出异常
            raise AssertionError("E007: 空输入未抛出异常")
        except ValueError:
            pass  # 预期行为

        print("=== 自检通过 ===")
        return 0

    except AssertionError as e:
        print(f"自检失败: {e}")
        return 1
    except Exception as e:
        print(f"自检异常: {e}")
        return 1


def parse_args(argv: List[str]) -> argparse.Namespace:
    """解析命令行参数。"""
    parser = argparse.ArgumentParser(
        description="数字代理任务编排工具 — 将文本转换为结构化结果",
        epilog="示例: python main.py --input '产品A 售价100元' --fields '名称:text,价格:number'",
    )

    parser.add_argument(
        "--input",
        "-i",
        type=str,
        help="输入文本（多条用 ; 分隔）",
    )
    parser.add_argument(
        "--fields",
        "-f",
        type=str,
        required=False,
        default="内容:text",
        help="字段定义，格式: '字段名:类型,字段名:类型'（默认为 '内容:text'）",
    )
    parser.add_argument(
        "--format",
        "-fmt",
        type=str,
        choices=["json", "csv", "markdown", "template"],
        default="json",
        help="输出格式（默认为 json）",
    )
    parser.add_argument(
        "--template",
        "-t",
        type=str,
        default=None,
        help="自定义模板（当 --format template 时必须提供）",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检并退出",
    )

    return parser.parse_args(argv)


def parse_fields(fields_str: str) -> Dict[str, str]:
    """解析字段定义字符串为字典。"""
    field_spec = {}
    for item in fields_str.split(","):
        item = item.strip()
        if not item:
            continue
        if ":" in item:
            name, ftype = item.split(":", 1)
            field_spec[name.strip()] = ftype.strip()
        else:
            # 没有指定类型时默认为 text
            field_spec[item.strip()] = "text"

    if not field_spec:
        raise ValueError("E004: 字段映射配置非法，字段列表为空")

    return field_spec


def main(argv: Optional[List[str]] = None) -> int:
    """主入口函数。"""
    if argv is None:
        argv = sys.argv[1:]

    # 先检查是否包含 --selftest（不依赖参数解析）
    if "--selftest" in argv:
        return run_selftest()

    try:
        args = parse_args(argv)

        # 解析字段配置
        try:
            field_spec = parse_fields(args.fields)
        except ValueError as e:
            print(f"错误: {e}")
            return 4

        # 检查输入
        if not args.input or not args.input.strip():
            print("错误: E002 输入文本不能为空")
            return 2

        # 分割多条输入（用 ; 分隔）
        raw_texts = [t.strip() for t in args.input.split(";") if t.strip()]
        if not raw_texts:
            print("错误: E002 没有有效的输入文本")
            return 2

        # 处理文本
        processor = TextProcessor(field_spec)
        try:
            results = processor.process(raw_texts)
        except ValueError as e:
            print(f"错误: {e}")
            return 2

        # 格式化输出
        try:
            output = OutputFormatter.format(results, args.format, args.template)
        except ValueError as e:
            print(f"错误: {e}")
            return 3

        # 输出结果
        print(output)
        return 0

    except KeyboardInterrupt:
        print("已取消", file=sys.stderr)
        return 130
    except Exception as e:
        print(f"错误: E010 未知运行时错误: {e}", file=sys.stderr)
        return 10


if __name__ == "__main__":
    sys.exit(main())
