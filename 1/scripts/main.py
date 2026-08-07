#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据解析与结构化转换工具（clean-room 独立实现）

依据功能规格 v1.0.1 全新编写，不参考任何既有实现。
提供：
  - 原始文本解析（提取关键字段）
  - 常见文本文件内容识别（.txt / .md / .csv / .json）
  - URL 内容抓取（仅限公开页面，不做登录认证）
  - 结构化输出生成（按字段映射输出）
  - 批量处理与自定义分隔符
  - 置信度标注

用法示例：
  python main.py parse --text "甲方：张三；乙方：李四；金额：100元"
  python main.py file --path ./data.csv --format csv
  python main.py url --url https://example.com
  python main.py batch --lines "a,b,c" --delimiter ","
  python main.py --selftest
"""

import argparse
import csv
import io
import json
import re
import sys
import urllib.request
from dataclasses import dataclass, field
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
# 核心功能类
# ---------------------------------------------------------------------------
class DataParser:
    """数据解析与结构化转换主类"""

    # 常见字段模式（用于从非结构化文本提取）
    FIELD_PATTERNS = {
        "甲方": r"(?:甲方|甲方名称)[：:\s]*([^\s；;，,]+)",
        "乙方": r"(?:乙方|乙方名称)[：:\s]*([^\s；;，,]+)",
        "金额": r"(?:金额|总金额|价格)[：:\s]*([0-9,，.]+(?:元|万元|亿)?)",
        "日期": r"(?:日期|时间)[：:\s]*(\d{4}[-/年]\d{1,2}[-/月]\d{1,2}日?)",
        "编号": r"(?:编号|合同号|单号)[：:\s]*([A-Za-z0-9\-_]+)",
        "电话": r"(?:电话|联系电话|手机)[：:\s]*(1[3-9]\d{9})",
        "邮箱": r"([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})",
        "地址": r"(?:地址|地点)[：:\s]*([^\s；;，,]+(?:省|市|区|县|路|街|号)[^\s；;，,]*)",
    }

    def __init__(self):
        """初始化解析器"""
        self._field_patterns = dict(self.FIELD_PATTERNS)
        self._custom_fields: Dict[str, str] = {}

    def parse_text(self, text: str, fields: Optional[List[str]] = None) -> ParseResult:
        """
        从原始文本中提取关键字段

        参数:
            text: 原始文本
            fields: 需要提取的字段列表（默认使用内置模式）

        返回:
            ParseResult 对象
        """
        # 输入检查
        if not text or not text.strip():
            return ParseResult(False, error_code="E001", error_message=ERROR_CODES["E001"])

        if len(text) > MAX_TEXT_LENGTH:
            return ParseResult(False, error_code="E006", error_message=ERROR_CODES["E006"])

        # 合并自定义字段模式
        patterns = dict(self._field_patterns)
        patterns.update(self._custom_fields)

        # 确定要提取的字段
        target_fields = fields if fields else list(patterns.keys())

        result_data: Dict[str, Any] = {}
        found_count = 0

        for field_name in target_fields:
            if field_name not in patterns:
                continue

            match = re.search(patterns[field_name], text)
            if match:
                result_data[field_name] = match.group(1).strip()
                found_count += 1

        # 计算置信度（基于找到字段的比例和文本长度）
        if target_fields:
            base_conf = found_count / len(target_fields)
        else:
            base_conf = 0.0

        # 文本长度因子（过短文本置信度降低）
        length_factor = min(1.0, len(text.strip()) / 100)

        confidence = round(base_conf * 0.7 + length_factor * 0.3, 2)

        return ParseResult(
            success=True,
            data=result_data,
            confidence=confidence,
            warnings=[] if found_count > 0 else ["未提取到任何字段"],
        )

    def parse_file(self, file_path: str, file_format: Optional[str] = None) -> ParseResult:
        """
        读取并解析常见文本文件

        参数:
            file_path: 文件路径
            file_format: 文件格式（txt/md/csv/json），默认根据扩展名判断

        返回:
            ParseResult 对象
        """
        # 参数检查
        if not file_path:
            return ParseResult(False, error_code="E001", error_message=ERROR_CODES["E001"])

        # 确定格式
        if not file_format:
            ext = file_path.rsplit(".", 1)[-1].lower() if "." in file_path else ""
            file_format = ext

        # 读取文件
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
        except UnicodeDecodeError:
            try:
                with open(file_path, "r", encoding="gbk") as f:
                    content = f.read()
            except Exception:
                return ParseResult(False, error_code="E002", error_message=ERROR_CODES["E002"])
        except Exception:
            return ParseResult(False, error_code="E002", error_message=ERROR_CODES["E002"])

        # 大小检查
        if len(content.encode("utf-8")) > MAX_FILE_SIZE:
            return ParseResult(False, error_code="E006", error_message=ERROR_CODES["E006"])

        # 按格式解析
        if file_format in ("txt", "md", "markdown"):
            return self._parse_markdown(content)
        elif file_format == "csv":
            return self._parse_csv(content)
        elif file_format == "json":
            return self._parse_json(content)
        else:
            # 未知格式按纯文本处理
            return self.parse_text(content)

    def parse_url(self, url: str, timeout: int = 10) -> ParseResult:
        """
        抓取公开网页并提取关键信息

        参数:
            url: 网页地址
            timeout: 超时时间（秒）

        返回:
            ParseResult 对象
        """
        if not url or not url.startswith(("http://", "https://")):
            return ParseResult(False, error_code="E001", error_message=ERROR_CODES["E001"])

        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                content = resp.read().decode("utf-8", errors="ignore")
        except Exception:
            return ParseResult(False, error_code="E003", error_message=ERROR_CODES["E003"])

        # 简单提取<title>和正文文本
        title_match = re.search(r"<title[^>]*>([^<]+)</title>", content, re.IGNORECASE)
        title = title_match.group(1).strip() if title_match else ""

        # 去除 HTML 标签
        text_content = re.sub(r"<script[^>]*>.*?</script>", "", content, flags=re.DOTALL | re.IGNORECASE)
        text_content = re.sub(r"<style[^>]*>.*?</style>", "", text_content, flags=re.DOTALL | re.IGNORECASE)
        text_content = re.sub(r"<[^>]+>", " ", text_content)
        text_content = re.sub(r"\s+", " ", text_content).strip()

        # 截断超长文本
        if len(text_content) > MAX_TEXT_LENGTH:
            text_content = text_content[:MAX_TEXT_LENGTH]
            warning = "内容超出长度限制，已截断"
        else:
            warning = ""

        result_data = {"title": title, "text_length": len(text_content)}

        # 尝试提取关键字段
        field_result = self.parse_text(text_content)
        if field_result.data:
            result_data.update(field_result.data)
            confidence = field_result.confidence
        else:
            confidence = 0.5 if title else 0.1

        warnings = [warning] if warning else []
        if not title:
            warnings.append("未提取到网页标题")

        return ParseResult(
            success=True,
            data=result_data,
            confidence=round(confidence, 2),
            warnings=warnings,
        )

    def batch_process(
        self,
        lines: List[str],
        delimiter: str = ",",
        field_mapping: Optional[Dict[str, int]] = None,
    ) -> ParseResult:
        """
        批量处理多条记录

        参数:
            lines: 原始记录列表
            delimiter: 分隔符
            field_mapping: 字段映射（字段名 -> 列索引）

        返回:
            ParseResult 对象
        """
        if not lines:
            return ParseResult(False, error_code="E009", error_message=ERROR_CODES["E009"])

        if not delimiter or len(delimiter) > 2:
            return ParseResult(False, error_code="E008", error_message=ERROR_CODES["E008"])

        records: List[Dict[str, str]] = []
        total_items = 0
        success_items = 0

        for line in lines:
            line = line.strip()
            if not line:
                continue

            parts = line.split(delimiter)
            total_items += 1

            if field_mapping:
                # 使用字段映射
                record = {}
                for field_name, index in field_mapping.items():
                    if index < len(parts):
                        record[field_name] = parts[index].strip()
                if record:
                    records.append(record)
                    success_items += 1
            else:
                # 自动生成字段名
                record = {f"field_{i}": part.strip() for i, part in enumerate(parts) if part.strip()}
                if record:
                    records.append(record)
                    success_items += 1

        confidence = round(success_items / total_items, 2) if total_items > 0 else 0.0

        return ParseResult(
            success=True,
            data={"records": records, "count": len(records)},
            confidence=confidence,
            warnings=[] if success_items == total_items else ["部分记录解析失败"],
        )

    def add_custom_field(self, field_name: str, pattern: str) -> None:
        """添加自定义字段提取模式"""
        if field_name and pattern:
            self._custom_fields[field_name] = pattern

    # ------------------------------------------------------------------
    # 内部辅助方法
    # ------------------------------------------------------------------
    def _parse_markdown(self, content: str) -> ParseResult:
        """解析 Markdown/纯文本内容"""
        # 提取标题
        title_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
        title = title_match.group(1).strip() if title_match else ""

        # 提取表格
        tables = []
        table_pattern = r"^\|(.+)\|$"
        lines = content.split("\n")
        current_table = []

        for line in lines:
            if re.match(table_pattern, line):
                cells = [c.strip() for c in line.strip("|").split("|")]
                if cells and not all(re.match(r"^[-:]+$", c) for c in cells):
                    current_table.append(cells)
            else:
                if current_table:
                    tables.append(current_table)
                    current_table = []

        if current_table:
            tables.append(current_table)

        result_data = {"title": title, "tables": tables, "line_count": len(lines)}

        # 使用文本解析提取关键字段
        field_result = self.parse_text(content)
        if field_result.data:
            result_data.update(field_result.data)
            confidence = max(field_result.confidence, 0.5 if tables else 0.3)
        else:
            confidence = 0.5 if title or tables else 0.2

        warnings = []
        if not title and not tables:
            warnings.append("未提取到标题或表格")

        return ParseResult(
            success=True,
            data=result_data,
            confidence=round(confidence, 2),
            warnings=warnings,
        )

    def _parse_csv(self, content: str) -> ParseResult:
        """解析 CSV 内容"""
        try:
            reader = csv.reader(io.StringIO(content))
            rows = list(reader)
        except Exception:
            return ParseResult(False, error_code="E005", error_message=ERROR_CODES["E005"])

        if not rows:
            return ParseResult(False, error_code="E005", error_message=ERROR_CODES["E005"])

        # 第一行作为表头
        header = rows[0]
        data_rows = []

        for row in rows[1:]:
            if len(row) == len(header):
                record = dict(zip(header, row))
                data_rows.append(record)
            elif len(row) > 0:
                # 列数不匹配，用索引作为字段名
                record = {f"column_{i}": val for i, val in enumerate(row)}
                data_rows.append(record)

        confidence = round(len(data_rows) / max(1, len(rows) - 1), 2)

        return ParseResult(
            success=True,
            data={"header": header, "rows": data_rows, "count": len(data_rows)},
            confidence=confidence,
            warnings=[] if len(data_rows) == len(rows) - 1 else ["部分行解析失败"],
        )

    def _parse_json(self, content: str) -> ParseResult:
        """解析 JSON 内容"""
        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            return ParseResult(False, error_code="E004", error_message=ERROR_CODES["E004"])

        # 判断 JSON 结构
        if isinstance(data, dict):
            result_data = data
            confidence = 1.0
        elif isinstance(data, list):
            result_data = {"items": data, "count": len(data)}
            confidence = 0.9
        else:
            result_data = {"value": data}
            confidence = 0.8

        return ParseResult(
            success=True,
            data=result_data,
            confidence=confidence,
            warnings=[],
        )


# ---------------------------------------------------------------------------
# 自检模块
# ---------------------------------------------------------------------------
def run_selftest() -> bool:
    """
    内置硬编码样例数据的离线自检

    使用宽松阈值，不依赖精确值，确保任何环境都能通过。
    """
    print("=" * 60)
    print("自检开始：数据解析与结构化转换工具")
    print("=" * 60)

    parser = DataParser()
    all_passed = True

    # 测试1：文本解析
    print("\n[1/5] 文本解析测试...")
    test_text = "合同编号：HT-2026-001；甲方：北京某某科技有限公司；乙方：上海某软件公司；金额：150000元；日期：2026年3月15日"
    result = parser.parse_text(test_text)
    assert result.success, "文本解析应成功"
    assert result.data is not None, "解析结果不应为空"
    assert result.confidence > 0.3, f"置信度应大于0.3，实际: {result.confidence}"
    assert "甲方" in result.data, "应提取到甲方字段"
    assert "乙方" in result.data, "应提取到乙方字段"
    assert "金额" in result.data, "应提取到金额字段"
    print(f"  通过 - 提取字段数: {len(result.data)}, 置信度: {result.confidence}")

    # 测试2：CSV 解析
    print("\n[2/5] CSV 解析测试...")
    csv_content = "name,age,city\n张三,28,北京\n李四,35,上海\n王五,42,广州"
    result = parser._parse_csv(csv_content)
    assert result.success, "CSV解析应成功"
    assert result.data is not None, "CSV解析结果不应为空"
    assert result.data["count"] == 3, f"CSV应有3行数据，实际: {result.data['count']}"
    assert result.confidence > 0.8, f"CSV置信度应较高，实际: {result.confidence}"
    print(f"  通过 - 行数: {result.data['count']}, 置信度: {result.confidence}")

    # 测试3：JSON 解析
    print("\n[3/5] JSON 解析测试...")
    json_content = '{"name": "测试项目", "version": "1.0", "items": [1, 2, 3]}'
    result = parser._parse_json(json_content)
    assert result.success, "JSON解析应成功"
    assert result.data is not None, "JSON解析结果不应为空"
    assert "name" in result.data, "应提取到name字段"
    assert result.confidence > 0.7, f"JSON置信度应较高，实际: {result.confidence}"
    print(f"  通过 - 字段数: {len(result.data)}, 置信度: {result.confidence}")

    # 测试4：批量处理
    print("\n[4/5] 批量处理测试...")
    lines = ["苹果,红色,水果", "香蕉,黄色,水果", "白菜,绿色,蔬菜"]
    result = parser.batch_process(lines, delimiter=",")
    assert result.success, "批量处理应成功"
    assert result.data is not None, "批量处理结果不应为空"
    assert result.data["count"] == 3, f"批量处理应有3条记录，实际: {result.data['count']}"
    assert result.confidence > 0.8, f"批量处理置信度应较高，实际: {result.confidence}"
    print(f"  通过 - 记录数: {result.data['count']}, 置信度: {result.confidence}")

    # 测试5：错误处理
    print("\n[5/5] 错误处理测试...")
    result = parser.parse_text("")
    assert not result.success, "空文本应失败"
    assert result.error_code == "E001", f"空文本应返回E001，实际: {result.error_code}"

    result = parser.parse_text("x" * (MAX_TEXT_LENGTH + 1))
    assert not result.success, "超长文本应失败"
    assert result.error_code == "E006", f"超长文本应返回E006，实际: {result.error_code}"

    result = parser._parse_json("{invalid json")
    assert not result.success, "无效JSON应失败"
    assert result.error_code == "E004", f"无效JSON应返回E004，实际: {result.error_code}"
    print("  通过 - 错误码检查")

    print("\n" + "=" * 60)
    print("全部自检通过！")
    print("=" * 60)
    return all_passed


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------
def main() -> int:
    """命令行主入口"""
    parser = argparse.ArgumentParser(
        description="数据解析与结构化转换工具 v1.0.1",
        epilog="示例：python main.py parse --text '甲方：张三；金额：100元'",
    )

    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # parse 子命令：文本解析
    parse_parser = subparsers.add_parser("parse", help="解析原始文本")
    parse_parser.add_argument("--text", type=str, required=True, help="原始文本")
    parse_parser.add_argument("--fields", type=str, nargs="*", help="要提取的字段列表")

    # file 子命令：文件解析
    file_parser = subparsers.add_parser("file", help="解析文件")
    file_parser.add_argument("--path", type=str, required=True, help="文件路径")
    file_parser.add_argument("--format", type=str, choices=["txt", "md", "csv", "json"], help="文件格式")

    # url 子命令：URL 解析
    url_parser = subparsers.add_parser("url", help="解析URL")
    url_parser.add_argument("--url", type=str, required=True, help="网页地址")
    url_parser.add_argument("--timeout", type=int, default=10, help="超时秒数")

    # batch 子命令：批量处理
    batch_parser = subparsers.add_parser("batch", help="批量处理")
    batch_parser.add_argument("--lines", type=str, nargs="+", required=True, help="记录列表")
    batch_parser.add_argument("--delimiter", type=str, default=",", help="分隔符")

    # selftest 参数
    parser.add_argument("--selftest", action="store_true", help="运行内置自检")

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        passed = run_selftest()
        return 0 if passed else 1

    # 无命令时显示帮助
    if not args.command:
        parser.print_help()
        return 0

    # 创建解析器实例
    data_parser = DataParser()

    # 执行对应命令
    if args.command == "parse":
        result = data_parser.parse_text(args.text, args.fields)
    elif args.command == "file":
        result = data_parser.parse_file(args.path, args.format)
    elif args.command == "url":
        result = data_parser.parse_url(args.url, args.timeout)
    elif args.command == "batch":
        result = data_parser.batch_process(args.lines, args.delimiter)
    else:
        print(f"未知命令: {args.command}")
        return 1

    # 输出结果
    output = json.dumps(result.to_dict(), ensure_ascii=False, indent=2)
    print(output)

    return 0 if result.success else 1


if __name__ == "__main__":
    sys.exit(main())
