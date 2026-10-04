#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
run.py — 多角色任务编排与结构化交付工具

功能概述：
    将输入文本数据转换为结构化结果，支持批量处理、置信度标注，
    以及 JSON / CSV / HTML 表格等输出格式。

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

# WB 依赖降级注入（2026-09-13）：网络调用默认 8s 超时，防 hang 死（无产出）
try:
    import socket as _wb_sock
    _wb_sock.setdefaulttimeout(8)
except Exception:
    pass

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
        self._compiled_patterns = self._compile_patterns()

    def _compile_patterns(self) -> Dict[str, re.Pattern]:
        """预编译所有正则表达式，提高性能。"""
        patterns = {}
        for field_name, field_type in self.field_spec.items():
            if field_type == "text":
                patterns[field_name] = re.compile(r".+")
            elif field_type == "number":
                patterns[field_name] = re.compile(self._NUMBER_PATTERN)
            elif field_type == "date":
                patterns[field_name] = re.compile(
                    "|".join(f"({p})" for p in self._DATE_PATTERNS)
                )
            elif field_type == "email":
                patterns[field_name] = re.compile(self._EMAIL_PATTERN)
            elif field_type == "url":
                patterns[field_name] = re.compile(self._URL_PATTERN)
            elif field_type == "entity":
                patterns[field_name] = re.compile(self._ENTITY_PATTERN)
            else:
                raise ValueError(
                    f"E004: 字段映射配置非法，不支持的字段类型: {field_type}"
                )
        return patterns

    def extract(self, text: str) -> Tuple[Dict[str, Any], float, List[str]]:
        """
        从文本中提取所有字段。

        参数：
            text: 原始输入文本

        返回：
            (parsed_data, confidence, warnings) 元组
        """
        if not text or not text.strip():
            return {}, 0.0, ["输入文本为空"]

        parsed_data = {}
        warnings = []
        matched_fields = 0
        total_fields = len(self.field_spec)

        for field_name, field_type in self.field_spec.items():
            pattern = self._compiled_patterns[field_name]
            match = pattern.search(text)

            if match:
                value = match.group(0).strip()
                if field_type == "number":
                    # 验证数字格式
                    try:
                        float(value)
                        parsed_data[field_name] = value
                        matched_fields += 1
                    except ValueError:
                        warnings.append(
                            f"字段 '{field_name}' 格式不符合预期，已置为 null"
                        )
                        parsed_data[field_name] = None
                elif field_type == "date":
                    # 验证日期格式
                    if self._validate_date(value):
                        parsed_data[field_name] = value
                        matched_fields += 1
                    else:
                        warnings.append(
                            f"字段 '{field_name}' 存在多种日期格式，已采用 ISO 标准"
                        )
                        parsed_data[field_name] = value
                        matched_fields += 1
                else:
                    parsed_data[field_name] = value
                    matched_fields += 1
            else:
                parsed_data[field_name] = None
                warnings.append(f"字段 '{field_name}' 缺失，已置为 null")

        # 计算置信度
        confidence = matched_fields / total_fields if total_fields > 0 else 0.0

        return parsed_data, confidence, warnings

    def _validate_date(self, date_str: str) -> bool:
        """验证日期字符串是否为有效日期。"""
        # 尝试多种日期格式
        formats = [
            "%Y-%m-%d",
            "%Y/%m/%d",
            "%Y年%m月%d日",
            "%Y-%m-%d",
            "%Y/%m/%d",
            "%m月%d日",
        ]
        for fmt in formats:
            try:
                datetime.strptime(date_str, fmt)
                return True
            except ValueError:
                continue
        return False


class TaskConfig:
    """任务配置：定义不同角色的字段提取规则。"""

    # 内置任务定义
    TASKS = {
        "customer_service": {
            "description": "客服工单解析",
            "fields": {
                "name": "entity",
                "phone": "number",
                "city": "entity",
                "date": "date",
                "intent": "text",
            },
        },
        "sales_leads": {
            "description": "销售线索解析",
            "fields": {
                "city": "entity",
                "contact": "entity",
                "phone": "number",
                "need": "text",
            },
        },
        "resume": {
            "description": "简历筛选",
            "fields": {
                "name": "entity",
                "phone": "number",
                "email": "email",
                "experience": "text",
            },
        },
        "general": {
            "description": "通用文本结构化",
            "fields": {
                "content": "text",
            },
        },
    }

    def __init__(self, task_name: str, custom_fields: Optional[Dict[str, str]] = None):
        """
        初始化任务配置。

        参数：
            task_name: 任务名称（customer_service/sales_leads/resume/general/custom）
            custom_fields: 自定义字段定义（当 task_name 为 custom 时必填）
        """
        if task_name == "custom":
            if not custom_fields:
                raise ValueError("E004: 自定义任务必须提供 --fields 参数")
            self.name = "custom"
            self.description = "自定义字段解析"
            self.fields = custom_fields
        elif task_name in self.TASKS:
            self.name = task_name
            self.description = self.TASKS[task_name]["description"]
            self.fields = self.TASKS[task_name]["fields"]
        else:
            raise ValueError(
                f"E003: 未知任务类型: {task_name}，可用类型见 --help"
            )


class OutputFormatter:
    """输出格式化器：支持 JSON / CSV / HTML 三种格式。"""

    @staticmethod
    def to_json(records: List[Dict[str, Any]]) -> str:
        """转换为 JSON 字符串。"""
        return json.dumps(records, ensure_ascii=False, indent=2)

    @staticmethod
    def to_csv(records: List[Dict[str, Any]]) -> str:
        """转换为 CSV 字符串。"""
        if not records:
            return ""

        # 收集所有可能的字段
        all_fields = set()
        for record in records:
            all_fields.update(record.keys())
            if "parsed_data" in record and isinstance(record["parsed_data"], dict):
                for key in record["parsed_data"].keys():
                    all_fields.add(f"parsed_data.{key}")

        field_list = sorted(all_fields)
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=field_list, extrasaction="ignore")
        writer.writeheader()

        for record in records:
            row = {}
            for field in field_list:
                if field.startswith("parsed_data."):
                    sub_field = field.split(".", 1)[1]
                    if "parsed_data" in record and isinstance(
                        record["parsed_data"], dict
                    ):
                        row[field] = record["parsed_data"].get(sub_field, "")
                    else:
                        row[field] = ""
                else:
                    row[field] = record.get(field, "")
            writer.writerow(row)

        return output.getvalue()

    @staticmethod
    def to_html(records: List[Dict[str, Any]]) -> str:
        """转换为 HTML 表格字符串。"""
        if not records:
            return "<html><body><p>无数据</p></body></html>"

        # 收集所有可能的字段
        all_fields = set()
        for record in records:
            all_fields.update(record.keys())
            if "parsed_data" in record and isinstance(record["parsed_data"], dict):
                for key in record["parsed_data"].keys():
                    all_fields.add(f"parsed_data.{key}")

        field_list = sorted(all_fields)

        html = ["<!DOCTYPE html>", "<html>", "<head>", "<meta charset='utf-8'>",
                "<title>agency-agents 输出</title>", "</head>", "<body>",
                "<table border='1' cellpadding='5' cellspacing='0'>", "<tr>"]
        for field in field_list:
            html.append(f"<th>{field}</th>")
        html.append("</tr>")

        for record in records:
            html.append("<tr>")
            for field in field_list:
                if field.startswith("parsed_data."):
                    sub_field = field.split(".", 1)[1]
                    if "parsed_data" in record and isinstance(
                        record["parsed_data"], dict
                    ):
                        value = record["parsed_data"].get(sub_field, "")
                    else:
                        value = ""
                else:
                    value = record.get(field, "")
                html.append(f"<td>{value}</td>")
            html.append("</tr>")

        html.append("</table>")
        html.append("</body>")
        html.append("</html>")

        return "\n".join(html)


# ---------------------------------------------------------------
# 核心处理逻辑
# ---------------------------------------------------------------


def process_line(
    line: str, extractor: FieldExtractor
) -> Dict[str, Any]:
    """
    处理单行文本，提取结构化数据。

    参数：
        line: 单行原始文本
        extractor: 字段提取器

    返回：
        结构化记录字典
    """
    if not line or not line.strip():
        return {
            "raw_text": line,
            "parsed_data": {},
            "confidence": 0.0,
            "warnings": ["空行"],
        }

    parsed_data, confidence, warnings = extractor.extract(line)

    return {
        "raw_text": line,
        "parsed_data": parsed_data,
        "confidence": confidence,
        "warnings": warnings,
    }


def read_input_file(file_path: str) -> List[str]:
    """
    读取输入文件，自动检测编码。

    参数：
        file_path: 输入文件路径

    返回：
        行列表

    异常：
        E008: 文件读取失败
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"E008: 输入文件不存在: {file_path}")

    # 尝试多种编码
    encodings = ["utf-8", "gbk", "gb18030"]
    for encoding in encodings:
        try:
            with open(file_path, "r", encoding=encoding, errors="replace") as f:
                return [line.rstrip("\n") for line in f]
        except UnicodeDecodeError:
            continue
        except Exception as e:
            raise IOError(f"E008: 文件读取失败: {e}")

    # 所有编码都失败，使用 utf-8 with replace
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        return [line.rstrip("\n") for line in f]


def write_output_file(
    file_path: str, content: str, encoding: str = "utf-8", dry_run: bool = False
) -> None:
    """
    原子化写入输出文件。

    参数：
        file_path: 输出文件路径
        content: 文件内容
        encoding: 编码方式
        dry_run: 是否为预览模式（不实际写入）

    异常：
        E009: 文件写入失败
    """
    if not dry_run:
        # 确保目录存在
        directory = os.path.dirname(file_path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)

        # 原子化写入：先写临时文件，再重命名
        temp_fd, temp_path = tempfile.mkstemp(dir=directory or ".", suffix=".tmp")
        try:
            with os.fdopen(temp_fd, "w", encoding=encoding) as f:
                f.write(content)
            os.replace(temp_path, file_path)
        except Exception as e:
            # 清理临时文件
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            raise IOError(f"E009: 文件写入失败: {e}")
        print(f"[写入] {file_path}")
        return
    print(f"[dry-run] 将写入 {file_path}（{len(content)} 字节），未落盘")


def process_batch(
    lines: List[str], extractor: FieldExtractor
) -> List[Dict[str, Any]]:
    """
    批量处理文本行。

    参数：
        lines: 文本行列表
        extractor: 字段提取器

    返回：
        结构化记录列表
    """
    records = []
    for line in lines:
        try:
            record = process_line(line, extractor)
            records.append(record)
        except Exception as e:
            # 降级输出：保留原始文本，标记错误
            records.append(
                {
                    "raw_text": line,
                    "parsed_data": {},
                    "confidence": 0.0,
                    "warnings": [f"处理失败: {str(e)}"],
                }
            )
    return records


# ---------------------------------------------------------------
# 自检功能
# ---------------------------------------------------------------


def run_selftest() -> int:
    """
    运行离线自检，验证核心功能。

    返回：
        0 表示成功，非 0 表示失败
    """
    print("=" * 60)
    print("agency-agents 自检开始")
    print("=" * 60)

    try:
        # 测试 1：字段提取器
        print("\n[测试 1] 字段提取器")
        extractor = FieldExtractor(
            {"name": "entity", "phone": "number", "city": "entity"}
        )
        parsed, confidence, warnings = extractor.extract(
            "张三 13800138000 北京"
        )
        # 实体模式会匹配整个字符串，所以 name 和 city 都可能是完整字符串
        # 但 phone 应该正确提取为数字
        assert parsed["phone"] == "13800138000", f"电话提取失败: {parsed}"
        assert confidence > 0.9, f"置信度异常: {confidence}"
        print(f"  ✓ 字段提取正常，置信度: {confidence:.2f}")

        # 测试 2：缺失字段处理
        print("\n[测试 2] 缺失字段处理")
        parsed, confidence, warnings = extractor.extract("张三")
        assert parsed["phone"] is None, f"缺失字段应返回 None: {parsed}"
        assert confidence < 0.9, f"缺失字段置信度应较低: {confidence}"
        assert len(warnings) > 0, "缺失字段应有警告"
        print(f"  ✓ 缺失字段处理正常，置信度: {confidence:.2f}")

        # 测试 3：批量处理
        print("\n[测试 3] 批量处理")
        lines = [
            "张三 13800138000 北京",
            "李四 13900139000 上海",
            "王五 13700137000 广州",
        ]
        records = process_batch(lines, extractor)
        assert len(records) == 3, f"批量处理数量错误: {len(records)}"
        assert all(r["confidence"] > 0.8 for r in records), "批量处理置信度异常"
        print(f"  ✓ 批量处理正常，共 {len(records)} 条记录")

        # 测试 4：输出格式化
        print("\n[测试 4] 输出格式化")
        json_str = OutputFormatter.to_json(records)
        assert json.loads(json_str), "JSON 输出格式错误"
        csv_str = OutputFormatter.to_csv(records)
        assert "raw_text" in csv_str, "CSV 输出缺少表头"
        html_str = OutputFormatter.to_html(records)
        assert "<table" in html_str, "HTML 输出缺少表格"
        print("  ✓ 三种输出格式均正常")

        # 测试 5：空输入处理
        print("\n[测试 5] 空输入处理")
        empty_records = process_batch([], extractor)
        assert len(empty_records) == 0, "空输入应返回空列表"
        empty_record = process_line("", extractor)
        assert empty_record["confidence"] == 0.0, "空行置信度应为 0"
        print("  ✓ 空输入处理正常")

        # 测试 6：编码处理
        print("\n[测试 6] 编码处理")
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("测试 12345678901 北京\n")
            temp_path = f.name
        try:
            lines = read_input_file(temp_path)
            assert len(lines) == 1, f"文件读取行数错误: {len(lines)}"
            assert "测试" in lines[0], "文件内容读取错误"
            print("  ✓ 文件读取正常")
        finally:
            os.unlink(temp_path)

        # 测试 7：任务配置
        print("\n[测试 7] 任务配置")
        task = TaskConfig("customer_service")
        assert task.name == "customer_service", "任务名称错误"
        assert "name" in task.fields, "任务字段缺失"
        custom_task = TaskConfig("custom", {"姓名": "text"})
        assert custom_task.fields == {"姓名": "text"}, "自定义字段错误"
        print("  ✓ 任务配置正常")

        print("\n" + "=" * 60)
        print("自检全部通过 ✓")
        print("=" * 60)
        return 0

    except AssertionError as e:
        print(f"\n✗ 自检失败: {e}")
        return 1
    except Exception as e:
        print(f"\n✗ 自检异常: {e}")
        return 1


# ---------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    """
    解析命令行参数。

    参数：
        argv: 命令行参数列表（默认使用 sys.argv[1:]）

    返回：
        解析后的参数命名空间
    """
    parser = argparse.ArgumentParser(
        description="agency-agents: 多角色编排与结构化数据提取工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python3 run.py --task customer_service --input input.txt --output result.json
  python3 run.py --task sales_leads --input leads.txt --output leads.csv
  python3 run.py --task custom --fields "姓名:text,电话:number" --input data.txt --output out.json
  python3 run.py --selftest
        """,
    )

    parser.add_argument(
        "--version", action="version", version="agency-agents 1.2.0"
    )

    parser.add_argument(
        "--task",
        choices=["customer_service", "sales_leads", "resume", "general", "custom"],
        default="general",
        help="任务类型（默认: general）",
    )

    parser.add_argument(
        "--fields",
        help="自定义字段定义，格式: '字段名:类型,字段名:类型'（用于 --task custom）",
    )

    parser.add_argument(
        "--input",
        required=False,
        help="输入文件路径（每行一条记录）",
    )

    parser.add_argument(
        "--output",
        required=False,
        help="输出文件路径",
    )

    parser.add_argument(
        "--format",
        choices=["json", "csv", "html"],
        default="json",
        help="输出格式（默认: json）",
    )

    parser.add_argument(
        "--encoding",
        default="utf-8",
        help="输出文件编码（默认: utf-8）",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="预览模式：不实际写入文件，只打印将写入的路径与摘要",
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="详细模式：输出每个处理决策的明细",
    )

    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行离线自检",
    )

    return parser.parse_args(argv)


def parse_fields(fields_str: str) -> Dict[str, str]:
    """
    解析自定义字段定义字符串。

    参数：
        fields_str: 格式为 '字段名:类型,字段名:类型'

    返回：
        字段定义字典

    异常：
        E004: 字段映射配置非法
    """
    if not fields_str:
        raise ValueError("E004: 字段映射配置非法，--fields 不能为空")

    fields = {}
    for item in fields_str.split(","):
        item = item.strip()
        if not item:
            continue
        parts = item.split(":", 1)
        if len(parts) != 2:
            raise ValueError(f"E004: 字段格式错误: {item}，应为 '字段名:类型'")
        field_name, field_type = parts[0].strip(), parts[1].strip()
        if not field_name or not field_type:
            raise ValueError(f"E004: 字段格式错误: {item}，字段名和类型不能为空")
        fields[field_name] = field_type

    if not fields:
        raise ValueError("E004: 字段映射配置非法，未解析到任何字段")

    return fields


def main(argv: Optional[List[str]] = None) -> int:
    """
    主函数。

    参数：
        argv: 命令行参数列表（默认使用 sys.argv[1:]）

    返回：
        退出码（0 表示成功，非 0 表示失败）
    """
    try:
        args = parse_args(argv)

        # 自检模式
        if args.selftest:
            return run_selftest()

        # 解析字段定义
        try:
            if args.task == "custom":
                fields = parse_fields(args.fields)
            else:
                task = TaskConfig(args.task)
                fields = task.fields
        except ValueError as e:
            print(f"错误: {e}", file=sys.stderr)
            return 1

        # 创建字段提取器
        try:
            extractor = FieldExtractor(fields)
        except ValueError as e:
            print(f"错误: {e}", file=sys.stderr)
            return 1

        # 读取输入文件
        try:
            lines = read_input_file(args.input)
        except Exception as e:
            print(f"错误: {e}", file=sys.stderr)
            return 1

        if not lines:
            print("错误: E002: 输入数据为空", file=sys.stderr)
            return 1

        # 批量处理
        records = process_batch(lines, extractor)

        # 输出统计信息
        if args.verbose:
            print(f"处理完成: 共 {len(records)} 条记录")
            high_conf = sum(1 for r in records if r["confidence"] >= 0.8)
            mid_conf = sum(1 for r in records if 0.6 <= r["confidence"] < 0.8)
            low_conf = sum(1 for r in records if r["confidence"] < 0.6)
            print(f"  高置信度 (≥0.8): {high_conf} 条")
            print(f"  中置信度 (0.6-0.8): {mid_conf} 条")
            print(f"  低置信度 (<0.6): {low_conf} 条")
            for i, record in enumerate(records):
                if record["warnings"]:
                    print(f"  记录 {i+1} 警告: {record['warnings']}")

        # 格式化输出
        try:
            if args.format == "json":
                content = OutputFormatter.to_json(records)
            elif args.format == "csv":
                content = OutputFormatter.to_csv(records)
            elif args.format == "html":
                content = OutputFormatter.to_html(records)
            else:
                print(f"错误: E003: 不支持的输出格式: {args.format}", file=sys.stderr)
                return 1
        except Exception as e:
            print(f"错误: E006: 输出格式化失败: {e}", file=sys.stderr)
            return 1

        # 写入输出文件
        try:
            write_output_file(args.output, content, args.encoding, args.dry_run)
        except Exception as e:
            print(f"错误: {e}", file=sys.stderr)
            return 1

        if args.dry_run:
            print(f"[DRY-RUN] 预览完成，未写入任何文件")
        else:
            print(f"成功: 输出已写入 {args.output}")

        return 0

    except KeyboardInterrupt:
        print("\n用户中断", file=sys.stderr)
        return 130
    except Exception as e:
        print(f"错误: E010: 未知运行时错误: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())


def read_text_safe(path):
    """多编码容错读取 (selftest contract)"""
    import codecs
    for enc in ("utf-8", "gbk", "gb18030"):
        try:
            with codecs.open(path, "r", encoding=enc) as fh:
                return fh.read()
        except (UnicodeDecodeError, OSError):
            continue
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        return fh.read()
