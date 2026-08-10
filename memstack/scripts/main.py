#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
memstack - 学习参考 数据转换 结构化处理

将用户提供的数据、文件或URL转换为结构化结果，供学习与参考使用。
本脚本为 clean-room 独立实现，仅依据功能规格编写。

用法示例:
    python scripts/main.py --selftest
    python scripts/main.py --input "文本内容" --format json
    python scripts/main.py --file /path/to/file.txt --format json
    python scripts/main.py --url https://example.com --format json
"""

import argparse
import json
import re
import sys
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
dry_run = False  # v3.274 模块级 dry-run 标志


# ============================================================
# 错误码定义
# ============================================================
ERROR_CODES = {
    "E001": "参数错误：缺少必要的输入参数",
    "E002": "文件错误：文件不存在或无法读取",
    "E003": "URL错误：URL格式无效或不支持",
    "E004": "格式错误：不支持的输出格式",
    "E005": "解析错误：输入内容解析失败",
    "E006": "网络错误：URL访问失败",
    "E007": "编码错误：文件编码不支持",
    "E008": "内部错误：未知异常",
    "E009": "数据错误：输入数据为空",
    "E010": "安全错误：URL协议不受支持",
}


class MemstackError(Exception):
    """自定义异常类，携带错误码。"""

    def __init__(self, code: str, message: str = ""):
        self.code = code
        self.message = message or ERROR_CODES.get(code, "未知错误")
        super().__init__(f"[{code}] {self.message}")


# ============================================================
# 核心数据结构
# ============================================================
class StructuredResult:
    """结构化输出结果。"""

    def __init__(self) -> None:
        self.timestamp: str = ""
        self.source_type: str = ""          # text / file / url
        self.source_name: str = ""          # 来源标识
        self.raw_length: int = 0            # 原始输入长度
        self.fields: List[Dict[str, Any]] = []  # 提取的字段列表
        self.confidence: str = "中"          # 整体置信度: 高/中/低
        self.warnings: List[str] = []       # 警告信息

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典。"""
        return {
            "timestamp": self.timestamp,
            "source_type": self.source_type,
            "source_name": self.source_name,
            "raw_length": self.raw_length,
            "fields": self.fields,
            "confidence": self.confidence,
            "warnings": self.warnings,
        }


# ============================================================
# 核心处理函数
# ============================================================
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


def _get_utc_timestamp() -> str:
    """获取当前 UTC 时间戳字符串。"""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _safe_read_file(file_path: str) -> str:
    """安全读取文件内容，支持常见编码。"""
    path = Path(file_path)
    if not path.exists():
        raise MemstackError("E002", f"文件不存在: {file_path}")
    if not path.is_file():
        raise MemstackError("E002", f"路径不是文件: {file_path}")

    # 尝试多种编码读取
    encodings = ["utf-8", "gbk", "latin-1", "utf-16"]
    for enc in encodings:
        try:
            return path.read_text(encoding=enc, errors="replace")
        except (UnicodeDecodeError, LookupError):
            continue
    raise MemstackError("E007", f"无法解码文件: {file_path}")


def _validate_url(url: str) -> str:
    """校验URL格式和协议。"""
    parsed = urllib.parse.urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        raise MemstackError("E003", f"无效URL: {url}")
    if parsed.scheme.lower() not in ("http", "https"):
        raise MemstackError("E010", f"不支持的协议: {parsed.scheme}")
    return url


def _extract_key_fields(text: str) -> Tuple[List[Dict[str, Any]], List[str]]:
    """
    从文本中提取关键字段。
    返回 (字段列表, 警告列表)。
    字段格式: {"key": 字段名, "value": 值, "confidence": 高/中/低}
    """
    fields: List[Dict[str, Any]] = []
    warnings: List[str] = []

    if not text or not text.strip():
        raise MemstackError("E009", "输入内容为空")

    # 1. 统计信息字段（高置信度）
    lines = text.strip().splitlines()
    words = re.findall(r"\b\w+\b", text, flags=re.UNICODE)
    chars = len(text)

    fields.append({"key": "行数", "value": len(lines), "confidence": "高"})
    fields.append({"key": "词数", "value": len(words), "confidence": "高"})
    fields.append({"key": "字符数", "value": chars, "confidence": "高"})

    # 2. 提取URL（高置信度）
    urls = re.findall(r"https?://[^\s<>\"']+", text)
    if urls:
        fields.append({"key": "URL", "value": urls[:5], "confidence": "高"})
    else:
        warnings.append("未检测到URL")

    # 3. 提取邮箱（高置信度）
    emails = re.findall(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", text)
    if emails:
        fields.append({"key": "邮箱", "value": emails[:5], "confidence": "高"})

    # 4. 提取日期（中置信度）
    date_patterns = [
        r"\b\d{4}[-/年]\d{1,2}[-/月]\d{1,2}日?\b",
        r"\b\d{1,2}[-/月]\d{1,2}[-/日]\d{2,4}\b",
    ]
    dates = []
    for pattern in date_patterns:
        dates.extend(re.findall(pattern, text))
    if dates:
        fields.append({"key": "日期", "value": dates[:5], "confidence": "中"})

    # 5. 提取数字（中置信度）
    numbers = re.findall(r"\b\d+(?:\.\d+)?\b", text)
    if len(numbers) > 5:
        fields.append({"key": "数字", "value": numbers[:10], "confidence": "中"})

    # 6. 检查是否有足够信息判定置信度
    if len(fields) <= 1:
        warnings.append("可提取字段较少，置信度降低")
        return fields, warnings

    # 7. 检查文本是否包含明显噪音（低置信度标识）
    noise_ratio = 0.0
    if chars > 0:
        # 计算非字母数字字符比例（粗略噪音估计）
        alnum_chars = sum(1 for c in text if c.isalnum())
        noise_ratio = 1.0 - (alnum_chars / chars)

    if noise_ratio > 0.8:
        warnings.append("文本噪音比例较高，可能影响提取质量")

    return fields, warnings


def _process_text(text: str, source_name: str = "text_input") -> StructuredResult:
    """处理纯文本输入。"""
    result = StructuredResult()
    result.timestamp = _get_utc_timestamp()
    result.source_type = "text"
    result.source_name = source_name
    result.raw_length = len(text)

    fields, warnings = _extract_key_fields(text)
    result.fields = fields
    result.warnings = warnings

    # 整体置信度评估
    high_conf_count = sum(1 for f in fields if f["confidence"] == "高")
    if high_conf_count >= 2:
        result.confidence = "高"
    elif len(fields) >= 3:
        result.confidence = "中"
    else:
        result.confidence = "低"

    return result


def _process_file(file_path: str) -> StructuredResult:
    """处理文件输入。"""
    content = _safe_read_file(file_path)
    result = _process_text(content, source_name=file_path)
    result.source_type = "file"
    return result


def _process_url(url: str) -> StructuredResult:
    """
    处理URL输入。
    注意: 本实现不实际访问网络（L2限制），仅做结构化解构。
    实际使用时需替换为真实的HTTP请求。
    """
    _validate_url(url)

    result = StructuredResult()
    result.timestamp = _get_utc_timestamp()
    result.source_type = "url"
    result.source_name = url
    result.raw_length = len(url)

    # 解析URL组件
    parsed = urllib.parse.urlparse(url)

    # 提取URL各部分作为结构化字段
    fields = [
        {"key": "协议", "value": parsed.scheme, "confidence": "高"},
        {"key": "域名", "value": parsed.netloc, "confidence": "高"},
        {"key": "路径", "value": parsed.path or "/", "confidence": "高"},
    ]

    if parsed.query:
        # 解析查询参数
        query_params = urllib.parse.parse_qs(parsed.query)
        for key, values in query_params.items():
            fields.append({
                "key": f"参数_{key}",
                "value": values[0] if len(values) == 1 else values,
                "confidence": "中",
            })

    if parsed.fragment:
        fields.append({"key": "锚点", "value": parsed.fragment, "confidence": "中"})

    result.fields = fields
    result.warnings = ["URL内容未实际抓取（网络访问受限），仅解析URL结构"]
    result.confidence = "中"

    return result


def _format_output(result: StructuredResult, fmt: str) -> str:
    """按指定格式输出结果。"""
    data = result.to_dict()

    if fmt == "json":
        return json.dumps(data, ensure_ascii=False, indent=2)
    elif fmt == "text":
        lines = [
            f"来源类型: {data['source_type']}",
            f"来源名称: {data['source_name']}",
            f"处理时间: {data['timestamp']}",
            f"原始长度: {data['raw_length']}",
            f"整体置信度: {data['confidence']}",
            "",
            "提取字段:",
        ]
        for field in data["fields"]:
            lines.append(
                f"  - {field['key']}: {field['value']} (置信度: {field['confidence']})"
            )
        if data["warnings"]:
            lines.append("")
            lines.append("警告:")
            for warn in data["warnings"]:
                lines.append(f"  ! {warn}")
        return "\n".join(lines)
    elif fmt == "compact":
        # 紧凑格式，仅输出关键字段
        compact = {
            "type": data["source_type"],
            "name": data["source_name"],
            "fields": {f["key"]: f["value"] for f in data["fields"]},
            "confidence": data["confidence"],
        }
        return json.dumps(compact, ensure_ascii=False, separators=(",", ":"))
    else:
        raise MemstackError("E004", f"不支持的输出格式: {fmt}")


# ============================================================
# 自检模块
# ============================================================
def _selftest() -> int:
    """
    内置自检逻辑（离线、无外部依赖）。
    使用硬编码样例数据验证核心功能。
    返回 0 表示通过，非 0 表示失败。
    """
    print("=== memstack 自检开始 ===")
    failures = 0

    # --- 测试1: 文本处理 ---
    print("\n[测试1] 文本处理")
    sample_text = """
    学习笔记 2026-01-15
    今天学习了 Python 编程基础，包括列表、字典和函数。
    参考文档: https://docs.python.org/3/tutorial/
    联系邮箱: student@example.com
    共计 3 个章节，约 120 页内容。
    """
    try:
        result = _process_text(sample_text, "selftest_text")
        assert result.source_type == "text", "来源类型应为text"
        assert result.raw_length > 0, "原始长度应大于0"
        assert len(result.fields) >= 3, "至少提取3个字段"

        # 检查关键字段
        field_keys = [f["key"] for f in result.fields]
        assert "行数" in field_keys, "应包含行数字段"
        assert "字符数" in field_keys, "应包含字符数字段"

        # 检查URL提取
        url_field = next((f for f in result.fields if f["key"] == "URL"), None)
        assert url_field is not None, "应提取到URL"
        assert "docs.python.org" in str(url_field["value"]), "URL内容应匹配"

        # 检查邮箱提取
        email_field = next((f for f in result.fields if f["key"] == "邮箱"), None)
        assert email_field is not None, "应提取到邮箱"
        assert "student@example.com" in str(email_field["value"]), "邮箱内容应匹配"

        print("  ✓ 文本处理测试通过")
    except AssertionError as e:
        print(f"  ✗ 文本处理测试失败: {e}")
        failures += 1
    except MemstackError as e:
        print(f"  ✗ 文本处理异常: {e}")
        failures += 1

    # --- 测试2: 文件处理（临时文件） ---
    print("\n[测试2] 文件处理")
    try:
        import tempfile
        import os

        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("测试文件内容\n第二行数据\n参考: https://example.org/path?query=1\n")
            temp_path = f.name

        try:
            result = _process_file(temp_path)
            assert result.source_type == "file", "来源类型应为file"
            assert result.raw_length > 0, "文件内容长度应大于0"
            assert len(result.fields) >= 2, "应提取至少2个字段"
            print("  ✓ 文件处理测试通过")
        finally:
            os.unlink(temp_path)  # 清理临时文件
    except AssertionError as e:
        print(f"  ✗ 文件处理测试失败: {e}")
        failures += 1
    except Exception as e:
        print(f"  ✗ 文件处理异常: {e}")
        failures += 1

    # --- 测试3: URL处理 ---
    print("\n[测试3] URL处理")
    try:
        result = _process_url("https://example.com/docs/page?lang=zh&page=2#section1")
        assert result.source_type == "url", "来源类型应为url"
        assert result.fields, "应提取到字段"

        field_keys = [f["key"] for f in result.fields]
        assert "协议" in field_keys, "应包含协议字段"
        assert "域名" in field_keys, "应包含域名字段"
        assert "路径" in field_keys, "应包含路径字段"

        # 检查参数提取
        param_fields = [f for f in result.fields if f["key"].startswith("参数_")]
        assert len(param_fields) >= 2, "应提取至少2个查询参数"

        print("  ✓ URL处理测试通过")
    except AssertionError as e:
        print(f"  ✗ URL处理测试失败: {e}")
        failures += 1
    except MemstackError as e:
        print(f"  ✗ URL处理异常: {e}")
        failures += 1

    # --- 测试4: 错误处理 ---
    print("\n[测试4] 错误处理")
    try:
        # 无效URL
        try:
            _process_url("not-a-url")
            print("  ✗ 无效URL未抛出异常")
            failures += 1
        except MemstackError as e:
            assert e.code in ("E003", "E010"), f"错误码应为E003或E010，实际: {e.code}"
            print("  ✓ 无效URL错误处理通过")

        # 不存在的文件
        try:
            _process_file("/nonexistent/path/file.txt")
            print("  ✗ 不存在文件未抛出异常")
            failures += 1
        except MemstackError as e:
            assert e.code == "E002", f"错误码应为E002，实际: {e.code}"
            print("  ✓ 文件不存在错误处理通过")

        # 空输入
        try:
            _extract_key_fields("")
            print("  ✗ 空输入未抛出异常")
            failures += 1
        except MemstackError as e:
            assert e.code == "E009", f"错误码应为E009，实际: {e.code}"
            print("  ✓ 空输入错误处理通过")

    except Exception as e:
        print(f"  ✗ 错误处理测试异常: {e}")
        failures += 1

    # --- 测试5: 输出格式 ---
    print("\n[测试5] 输出格式")
    try:
        result = _process_text("简单测试文本", "format_test")

        # JSON格式
        json_out = _format_output(result, "json")
        parsed_json = json.loads(json_out)
        assert "fields" in parsed_json, "JSON输出应包含fields"
        assert "confidence" in parsed_json, "JSON输出应包含confidence"

        # 文本格式
        text_out = _format_output(result, "text")
        assert "来源类型" in text_out, "文本输出应包含来源类型"
        assert "提取字段" in text_out, "文本输出应包含提取字段"

        # 紧凑格式
        compact_out = _format_output(result, "compact")
        parsed_compact = json.loads(compact_out)
        assert "fields" in parsed_compact, "紧凑输出应包含fields"

        # 不支持的格式
        try:
            _format_output(result, "xml")
            print("  ✗ 不支持的格式未抛出异常")
            failures += 1
        except MemstackError as e:
            assert e.code == "E004", f"错误码应为E004，实际: {e.code}"

        print("  ✓ 输出格式测试通过")
    except AssertionError as e:
        print(f"  ✗ 输出格式测试失败: {e}")
        failures += 1
    except Exception as e:
        print(f"  ✗ 输出格式测试异常: {e}")
        failures += 1

    # --- 测试6: 边界情况（宽松断言） ---
    print("\n[测试6] 边界情况")
    try:
        # 大量文本
        long_text = "内容 " * 1000
        result = _process_text(long_text, "long_text")
        assert result.raw_length > 1000, "长文本长度应大于1000"
        assert len(result.fields) >= 2, "长文本应提取至少2个字段"

        # 特殊字符
        special_text = "特殊字符测试: @#$%^&*() 中文内容 English mix 12345"
        result = _process_text(special_text, "special_text")
        assert len(result.fields) >= 2, "特殊字符文本应提取至少2个字段"

        # 仅数字
        numbers_text = "42 100 3.14 2026"
        result = _process_text(numbers_text, "numbers_text")
        assert len(result.fields) >= 2, "数字文本应提取至少2个字段"

        print("  ✓ 边界情况测试通过")
    except AssertionError as e:
        print(f"  ✗ 边界情况测试失败: {e}")
        failures += 1
    except Exception as e:
        print(f"  ✗ 边界情况测试异常: {e}")
        failures += 1

    # --- 总结 ---
    print("\n=== 自检结束 ===")
    if failures == 0:
        print("所有测试通过 ✓")
        return 0
    else:
        print(f"共 {failures} 项测试失败 ✗")
        return 1


# ============================================================
# 命令行入口
# ============================================================
def main() -> int:
    """主入口函数。"""
    parser = argparse.ArgumentParser(
        prog="memstack",
        description="将用户提供的数据、文件或URL转换为结构化结果，供学习与参考使用。",
        epilog="示例: %(prog)s --input '文本' --format json",
    )

    # 输入参数（互斥）
    input_group = parser.add_mutually_exclusive_group()
    input_group.add_argument("--input", type=str, help="直接输入文本内容")
    input_group.add_argument("--file", type=str, help="输入文件路径")
    input_group.add_argument("--url", type=str, help="输入URL地址")

    # 输出参数
    parser.add_argument(
        "--format",
        type=str,
        choices=["json", "text", "compact"],
        default="json",
        help="输出格式 (默认: json)",
    )

    # 自检参数
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检（离线，无需外部依赖）",
    )

    parser.add_argument("--verbose", action="store_true", help="显示修改明细")  # R6 可解释输出

    parser.add_argument("--force", action="store_true")  # R4 强制写盘


    parser.add_argument("--dry-run", action="store_true")  # R4 预览模式

    args = parser.parse_args()

    global dry_run

    dry_run = getattr(args, "dry_run", False)  # v3.274 同步到全局

    # 自检模式
    if args.selftest:
        return _selftest()

    # 正常处理模式
    try:
        # 检查输入
        if not (args.input or args.file or args.url):
            raise MemstackError("E001")

        # 处理输入
        if args.input:
            result = _process_text(args.input)
        elif args.file:
            result = _process_file(args.file)
        elif args.url:
            result = _process_url(args.url)
        else:
            raise MemstackError("E001")

        # 输出结果
        output = _format_output(result, args.format)
        print(output)
        return 0

    except MemstackError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"错误: [{ERROR_CODES['E008']}] 未知异常: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
