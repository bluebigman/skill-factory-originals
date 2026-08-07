#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ck-env 技能功能实现脚本
版本: 1.0.1
功能: 环境适配、数据转换、跨平台执行辅助
"""

import argparse
import csv
import io
import json
import os
import re
import sys
import tempfile
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union


# ---------------------------------------------------------------------------
# 错误码定义
# ---------------------------------------------------------------------------
ERROR_CODES = {
    "E001": "输入为空或格式不合法",
    "E002": "文件不存在或无法读取",
    "E003": "URL 无法访问或非 HTTP/HTTPS 协议",
    "E004": "数据转换失败",
    "E005": "输入超过大小限制",
    "E006": "JSON 解析失败",
    "E007": "CSV 解析失败",
    "E008": "字段提取失败",
    "E009": "平台识别失败",
    "E010": "内部逻辑错误",
}


# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------
MAX_TEXT_LENGTH = 50000  # 单次输入文本上限
MAX_FILE_SIZE = 5 * 1024 * 1024  # 单文件大小上限 5MB
SUPPORTED_URL_SCHEMES = ("http", "https")


# ---------------------------------------------------------------------------
# 核心功能类
# ---------------------------------------------------------------------------
class DataConverter:
    """数据转换核心类"""

    @staticmethod
    def detect_platform(path: str) -> Dict[str, str]:
        """
        识别输入路径的平台风格。
        返回包含平台类型和规范化路径的字典。
        """
        if not path or not isinstance(path, str):
            raise ValueError("E001: 路径不能为空")

        # Windows 风格: 包含盘符或反斜杠
        if re.match(r"^[A-Za-z]:[\\/]", path) or "\\" in path:
            platform = "windows"
            normalized = path.replace("\\", "/")
        # Unix 风格: 以 / 开头
        elif path.startswith("/"):
            platform = "unix"
            normalized = path
        # 相对路径
        else:
            platform = "relative"
            normalized = path

        return {"platform": platform, "normalized_path": normalized}

    @staticmethod
    def parse_json(text: str) -> Dict[str, Any]:
        """解析 JSON 字符串"""
        if not text or not text.strip():
            raise ValueError("E001: JSON 输入为空")
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            raise ValueError(f"E006: JSON 解析失败 - {e}")

    @staticmethod
    def parse_csv(text: str) -> List[Dict[str, str]]:
        """解析 CSV 字符串为字典列表"""
        if not text or not text.strip():
            raise ValueError("E001: CSV 输入为空")
        try:
            reader = csv.DictReader(io.StringIO(text))
            return [dict(row) for row in reader]
        except Exception as e:
            raise ValueError(f"E007: CSV 解析失败 - {e}")

    @staticmethod
    def extract_fields(data: Dict[str, Any], fields: List[str]) -> Dict[str, Any]:
        """从数据字典中提取指定字段"""
        result = {}
        for field in fields:
            if field in data:
                result[field] = data[field]
            else:
                result[field] = None
        return result

    @staticmethod
    def to_markdown_table(data: List[Dict[str, Any]]) -> str:
        """将字典列表转换为 Markdown 表格"""
        if not data:
            return ""

        # 获取所有字段名
        headers = list(data[0].keys())
        # 确保所有行都有相同的字段
        for row in data[1:]:
            for key in row.keys():
                if key not in headers:
                    headers.append(key)

        # 生成表头
        lines = []
        lines.append("| " + " | ".join(headers) + " |")
        lines.append("| " + " | ".join(["---"] * len(headers)) + " |")

        # 生成数据行
        for row in data:
            values = []
            for header in headers:
                value = row.get(header, "")
                values.append(str(value).replace("|", "\\|"))
            lines.append("| " + " | ".join(values) + " |")

        return "\n".join(lines)


class FileProcessor:
    """文件处理类"""

    @staticmethod
    def read_file(file_path: str) -> str:
        """读取文件内容，检查大小限制"""
        try:
            path = Path(file_path)
            if not path.exists():
                raise ValueError("E002: 文件不存在")

            file_size = path.stat().st_size
            if file_size > MAX_FILE_SIZE:
                raise ValueError(f"E005: 文件大小超过 {MAX_FILE_SIZE} 字节限制")

            return path.read_text(encoding="utf-8", errors="replace")
        except ValueError:
            raise
        except Exception as e:
            raise ValueError(f"E002: 文件读取失败 - {e}")

    @staticmethod
    def write_file(file_path: str, content: str) -> bool:
        """写入文件内容"""
        try:
            path = Path(file_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            return True
        except Exception as e:
            raise ValueError(f"E010: 文件写入失败 - {e}")


class URLFetcher:
    """URL 获取类"""

    @staticmethod
    def fetch_url(url: str, timeout: int = 10) -> str:
        """从 URL 获取内容"""
        if not url:
            raise ValueError("E001: URL 为空")

        # 检查协议
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme not in SUPPORTED_URL_SCHEMES:
            raise ValueError(f"E003: 不支持的协议 '{parsed.scheme}'")

        try:
            with urllib.request.urlopen(url, timeout=timeout) as response:
                content = response.read().decode("utf-8", errors="replace")
                if len(content) > MAX_TEXT_LENGTH:
                    raise ValueError(f"E005: 内容超过 {MAX_TEXT_LENGTH} 字符限制")
                return content
        except ValueError:
            raise
        except Exception as e:
            raise ValueError(f"E003: URL 访问失败 - {e}")


class EnvironmentAdapter:
    """环境适配主类"""

    def __init__(self):
        self.converter = DataConverter()
        self.file_processor = FileProcessor()
        self.url_fetcher = URLFetcher()

    def process_text(self, text: str, output_format: str = "json") -> Dict[str, Any]:
        """处理纯文本数据"""
        if not text or not text.strip():
            raise ValueError("E001: 输入文本为空")

        if len(text) > MAX_TEXT_LENGTH:
            raise ValueError(f"E005: 文本长度超过 {MAX_TEXT_LENGTH} 字符")

        # 尝试解析为 JSON
        try:
            data = self.converter.parse_json(text)
            return {"format": "json", "data": data}
        except ValueError:
            pass

        # 尝试解析为 CSV
        try:
            data = self.converter.parse_csv(text)
            return {"format": "csv", "data": data}
        except ValueError:
            pass

        # 纯文本处理
        return {"format": "text", "data": text}

    def process_file(self, file_path: str, output_format: str = "json") -> Dict[str, Any]:
        """处理文件"""
        content = self.file_processor.read_file(file_path)
        return self.process_text(content, output_format)

    def process_url(self, url: str, output_format: str = "json") -> Dict[str, Any]:
        """处理 URL"""
        content = self.url_fetcher.fetch_url(url)
        return self.process_text(content, output_format)

    def convert(self, data: Any, target_format: str) -> Any:
        """数据格式转换"""
        try:
            if target_format == "json":
                if isinstance(data, str):
                    return json.loads(data)
                return json.dumps(data, ensure_ascii=False, indent=2)

            elif target_format == "markdown":
                if isinstance(data, list) and data and isinstance(data[0], dict):
                    return self.converter.to_markdown_table(data)
                return str(data)

            elif target_format == "csv":
                if isinstance(data, list) and data and isinstance(data[0], dict):
                    output = io.StringIO()
                    writer = csv.DictWriter(output, fieldnames=list(data[0].keys()))
                    writer.writeheader()
                    writer.writerows(data)
                    return output.getvalue()
                return str(data)

            else:
                raise ValueError(f"E004: 不支持的转换格式 '{target_format}'")

        except ValueError:
            raise
        except Exception as e:
            raise ValueError(f"E004: 数据转换失败 - {e}")

    def extract(self, data: Any, fields: List[str]) -> Dict[str, Any]:
        """提取关键字段"""
        try:
            if isinstance(data, str):
                data = json.loads(data)
            if isinstance(data, dict):
                return self.converter.extract_fields(data, fields)
            elif isinstance(data, list):
                return [self.converter.extract_fields(item, fields) for item in data]
            else:
                raise ValueError("E008: 无法从当前数据类型提取字段")
        except ValueError:
            raise
        except Exception as e:
            raise ValueError(f"E008: 字段提取失败 - {e}")


# ---------------------------------------------------------------------------
# 自检功能
# ---------------------------------------------------------------------------
def run_selftest() -> bool:
    """
    内置自检功能，使用硬编码样例数据。
    不依赖外部文件、网络或当前工作目录。
    """
    print("开始自检...")
    tests_passed = 0
    tests_failed = 0

    # 测试 1: 平台识别
    try:
        adapter = EnvironmentAdapter()
        result = adapter.converter.detect_platform("C:\\Users\\test\\file.txt")
        assert result["platform"] == "windows", "Windows 路径识别失败"
        assert "C:/Users/test/file.txt" in result["normalized_path"], "路径规范化失败"
        tests_passed += 1
        print("  [PASS] 平台识别测试")
    except Exception as e:
        tests_failed += 1
        print(f"  [FAIL] 平台识别测试: {e}")

    # 测试 2: JSON 解析
    try:
        adapter = EnvironmentAdapter()
        json_text = '{"name": "test", "value": 123}'
        result = adapter.process_text(json_text)
        assert result["format"] == "json", "JSON 格式识别失败"
        assert result["data"]["name"] == "test", "JSON 字段提取失败"
        tests_passed += 1
        print("  [PASS] JSON 解析测试")
    except Exception as e:
        tests_failed += 1
        print(f"  [FAIL] JSON 解析测试: {e}")

    # 测试 3: CSV 解析
    try:
        adapter = EnvironmentAdapter()
        csv_text = "name,age\nAlice,30\nBob,25"
        result = adapter.process_text(csv_text)
        assert result["format"] == "csv", "CSV 格式识别失败"
        assert len(result["data"]) == 2, "CSV 行数不正确"
        assert result["data"][0]["name"] == "Alice", "CSV 字段提取失败"
        tests_passed += 1
        print("  [PASS] CSV 解析测试")
    except Exception as e:
        tests_failed += 1
        print(f"  [FAIL] CSV 解析测试: {e}")

    # 测试 4: 字段提取
    try:
        adapter = EnvironmentAdapter()
        data = {"name": "test", "value": 123, "extra": "ignored"}
        result = adapter.extract(data, ["name", "value"])
        assert result["name"] == "test", "字段 name 提取失败"
        assert result["value"] == 123, "字段 value 提取失败"
        tests_passed += 1
        print("  [PASS] 字段提取测试")
    except Exception as e:
        tests_failed += 1
        print(f"  [FAIL] 字段提取测试: {e}")

    # 测试 5: 数据转换
    try:
        adapter = EnvironmentAdapter()
        data = [{"name": "Alice", "age": 30}, {"name": "Bob", "age": 25}]
        markdown = adapter.convert(data, "markdown")
        assert "| name" in markdown, "Markdown 表头缺失"
        assert "Alice" in markdown, "Markdown 数据缺失"
        tests_passed += 1
        print("  [PASS] 数据转换测试")
    except Exception as e:
        tests_failed += 1
        print(f"  [FAIL] 数据转换测试: {e}")

    # 测试 6: 错误处理
    try:
        adapter = EnvironmentAdapter()
        try:
            adapter.process_text("")
            assert False, "空输入应该抛出异常"
        except ValueError as e:
            assert "E001" in str(e), "错误码 E001 未正确抛出"
        tests_passed += 1
        print("  [PASS] 错误处理测试")
    except Exception as e:
        tests_failed += 1
        print(f"  [FAIL] 错误处理测试: {e}")

    # 测试 7: 完整流程
    try:
        adapter = EnvironmentAdapter()
        sample_data = [
            {"id": 1, "name": "Alice", "score": 95.5},
            {"id": 2, "name": "Bob", "score": 87.0},
        ]
        # 转换为 JSON
        json_result = adapter.convert(sample_data, "json")
        # 解析回字典
        parsed = json.loads(json_result)
        assert len(parsed) == 2, "JSON 转换后数据量不匹配"
        tests_passed += 1
        print("  [PASS] 完整流程测试")
    except Exception as e:
        tests_failed += 1
        print(f"  [FAIL] 完整流程测试: {e}")

    # 测试 8: 平台适配
    try:
        adapter = EnvironmentAdapter()
        # 模拟不同平台路径
        unix_path = "/home/user/data.txt"
        win_path = "D:\\data\\file.csv"
        rel_path = "data/output.json"

        unix_result = adapter.converter.detect_platform(unix_path)
        win_result = adapter.converter.detect_platform(win_path)
        rel_result = adapter.converter.detect_platform(rel_path)

        assert unix_result["platform"] == "unix", "Unix 路径识别失败"
        assert win_result["platform"] == "windows", "Windows 路径识别失败"
        assert rel_result["platform"] == "relative", "相对路径识别失败"
        tests_passed += 1
        print("  [PASS] 平台适配测试")
    except Exception as e:
        tests_failed += 1
        print(f"  [FAIL] 平台适配测试: {e}")

    # 汇总结果
    print(f"\n自检完成: {tests_passed} 通过, {tests_failed} 失败")
    return tests_failed == 0


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------
def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="ck-env: 环境适配、数据转换、跨平台执行工具",
        epilog="示例: python main.py --input data.json --format json"
    )

    # 输入选项
    parser.add_argument("--input", "-i", help="输入文本、文件路径或 URL")
    parser.add_argument("--file", "-f", help="输入文件路径")
    parser.add_argument("--url", "-u", help="输入 URL")

    # 处理选项
    parser.add_argument("--format", "-fmt", choices=["json", "markdown", "csv", "text"],
                        default="json", help="输出格式 (默认: json)")
    parser.add_argument("--extract", "-e", nargs="+", help="提取指定字段")
    parser.add_argument("--detect-platform", action="store_true",
                        help="检测输入路径的平台类型")

    # 输出选项
    parser.add_argument("--output", "-o", help="输出文件路径")

    # 其他
    parser.add_argument("--selftest", action="store_true", help="运行内置自检")
    parser.add_argument("--version", action="version", version="ck-env 1.0.1")

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        success = run_selftest()
        sys.exit(0 if success else 1)

    # 初始化适配器
    adapter = EnvironmentAdapter()

    try:
        # 平台检测模式
        if args.detect_platform:
            if not args.input:
                print("错误: --detect-platform 需要 --input 参数")
                sys.exit(1)
            result = adapter.converter.detect_platform(args.input)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return

        # 获取输入数据
        if args.file:
            result = adapter.process_file(args.file, args.format)
        elif args.url:
            result = adapter.process_url(args.url, args.format)
        elif args.input:
            result = adapter.process_text(args.input, args.format)
        else:
            # 从标准输入读取
            text = sys.stdin.read()
            if not text.strip():
                print("错误: 请输入数据 (文本、文件路径或 URL)", file=sys.stderr)
                sys.exit(1)
            result = adapter.process_text(text, args.format)

        # 字段提取
        if args.extract:
            result["data"] = adapter.extract(result["data"], args.extract)

        # 格式转换
        if args.format != "json" and "data" in result:
            result["data"] = adapter.convert(result["data"], args.format)

        # 输出结果
        output = json.dumps(result, ensure_ascii=False, indent=2)

        if args.output:
            adapter.file_processor.write_file(args.output, output)
            print(f"结果已写入: {args.output}")
        else:
            print(output)

    except ValueError as e:
        print(f"错误: {e}", file=sys.stderr)
        # 提取错误码
        error_code = str(e).split(":")[0].strip()
        if error_code in ERROR_CODES:
            print(f"错误码说明: {ERROR_CODES[error_code]}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"错误: E010 - 内部错误: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
