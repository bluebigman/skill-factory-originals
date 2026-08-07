#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
prototype 技能功能规格的独立实现（clean-room 重写）。

仅依据功能规格文档实现，不参考任何既有代码。
提供：
  - 文本/文件/URL 内容的结构化解析
  - 批量处理
  - 自定义输出格式（JSON / Markdown / 表格）
  - 置信度标注
  - 离线自检（--selftest）
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import re
import sys
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# 错误码定义
# ---------------------------------------------------------------------------
ERR_OK = 0
ERR_INVALID_INPUT = "E001"      # 输入为空或格式不合法
ERR_FILE_NOT_FOUND = "E002"     # 文件不存在或无法读取
ERR_URL_ERROR = "E003"          # URL 访问失败
ERR_UNSUPPORTED_TYPE = "E004"   # 不支持的输入类型
ERR_PARSE_ERROR = "E005"        # 解析失败（字段提取失败）
ERR_OUTPUT_ERROR = "E006"       # 输出生成失败
ERR_BATCH_ERROR = "E007"        # 批量处理过程中出现错误
ERR_CONFIG_ERROR = "E008"       # 配置（自定义字段等）错误
ERR_INTERNAL = "E009"           # 内部未知错误
ERR_SELFTEST = "E010"           # 自检失败


# ---------------------------------------------------------------------------
# 数据结构
# ---------------------------------------------------------------------------
@dataclass
class ExtractedField:
    """单个提取字段的结果。"""
    name: str
    value: Any
    confidence: str  # high / medium / low


@dataclass
class ParseResult:
    """单条记录的解析结果。"""
    record_id: str
    fields: List[ExtractedField]
    source: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "record_id": self.record_id,
            "source": self.source,
            "created_at": self.created_at,
            "fields": [
                {"name": f.name, "value": f.value, "confidence": f.confidence}
                for f in self.fields
            ],
        }


# ---------------------------------------------------------------------------
# 核心解析逻辑（基于规格的能力边界）
# ---------------------------------------------------------------------------
class PrototypeParser:
    """
    核心解析器。

    支持：
      - 识别常见字段：email、日期、URL、金额、数字、枚举值
      - 置信度标注：
          high   —— 格式明确、正则强匹配
          medium —— 格式较模糊但可识别
          low    —— 仅能猜测或存在歧义
      - 不进行主观臆断，缺失字段不补全
    """

    # 基础正则模式
    EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
    URL_RE = re.compile(r"https?://[^\s]+")
    DATE_RE = re.compile(
        r"\b(\d{4}[-/]\d{1,2}[-/]\d{1,2}|\d{1,2}[-/]\d{1,2}[-/]\d{4})\b"
    )
    MONEY_RE = re.compile(r"[$¥€£]\s?\d+(?:\.\d{1,2})?")
    NUMBER_RE = re.compile(r"\b\d+(?:\.\d+)?\b")

    # 常见枚举值（用于识别）
    ENUM_MAP = {
        "gender": {"男", "女", "male", "female", "M", "F", "未知"},
        "status": {"active", "inactive", "pending", "closed", "启用", "停用", "待定"},
    }

    def parse_text(self, text: str, record_id: str = "rec_default") -> ParseResult:
        """
        解析一段纯文本，提取关键字段。
        """
        if not text or not text.strip():
            raise ValueError(ERR_INVALID_INPUT)

        fields: List[ExtractedField] = []

        # 1. 识别 Email（强匹配 → high）
        emails = self.EMAIL_RE.findall(text)
        if emails:
            fields.append(ExtractedField("email", emails[0], "high"))

        # 2. 识别 URL（强匹配 → high）
        urls = self.URL_RE.findall(text)
        if urls:
            fields.append(ExtractedField("url", urls[0], "high"))

        # 3. 识别日期（中等匹配 → medium）
        dates = self.DATE_RE.findall(text)
        if dates:
            # 只取第一个，避免过多噪声
            fields.append(ExtractedField("date", dates[0], "medium"))

        # 4. 识别金额（强匹配 → high）
        monies = self.MONEY_RE.findall(text)
        if monies:
            fields.append(ExtractedField("amount", monies[0], "high"))

        # 5. 识别数字（弱匹配 → low）
        numbers = self.NUMBER_RE.findall(text)
        if numbers:
            # 过滤掉已作为金额/日期的一部分的数字（简单去重）
            filtered = [n for n in numbers if n not in [d.replace("/", "-") for d in dates]]
            if filtered:
                fields.append(ExtractedField("number", filtered[0], "low"))

        # 6. 识别枚举值（中等匹配 → medium）
        for enum_name, enum_values in self.ENUM_MAP.items():
            for val in enum_values:
                if re.search(rf"\b{re.escape(val)}\b", text, re.IGNORECASE):
                    fields.append(ExtractedField(enum_name, val, "medium"))
                    break  # 每个枚举只取一个

        return ParseResult(
            record_id=record_id,
            fields=fields,
            source="text",
        )

    def parse_csv(self, content: str, record_id: str = "rec_csv") -> List[ParseResult]:
        """
        解析 CSV 内容，每行作为一条记录。
        """
        if not content or not content.strip():
            raise ValueError(ERR_INVALID_INPUT)

        results: List[ParseResult] = []
        try:
            reader = csv.DictReader(io.StringIO(content))
            for idx, row in enumerate(reader):
                # 将整行拼成文本后复用文本解析
                row_text = " ".join(str(v) for v in row.values() if v)
                fields: List[ExtractedField] = []
                for key, val in row.items():
                    if val and str(val).strip():
                        conf = "high" if key in ("email", "url", "amount") else "medium"
                        fields.append(ExtractedField(key, str(val), conf))
                results.append(
                    ParseResult(
                        record_id=f"{record_id}_{idx}",
                        fields=fields,
                        source="csv",
                    )
                )
        except Exception as exc:
            raise ValueError(f"{ERR_PARSE_ERROR}: {exc}") from exc

        return results

    def parse_json(self, content: str, record_id: str = "rec_json") -> List[ParseResult]:
        """
        解析 JSON 内容。支持：
          - 单个对象
          - 对象数组
        """
        if not content or not content.strip():
            raise ValueError(ERR_INVALID_INPUT)

        try:
            data = json.loads(content)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{ERR_PARSE_ERROR}: {exc}") from exc

        results: List[ParseResult] = []

        if isinstance(data, dict):
            # 单对象
            fields = [
                ExtractedField(k, str(v), "high" if k in ("email", "url") else "medium")
                for k, v in data.items()
                if v is not None
            ]
            results.append(ParseResult(record_id=record_id, fields=fields, source="json"))
        elif isinstance(data, list):
            # 数组
            for idx, item in enumerate(data):
                if isinstance(item, dict):
                    fields = [
                        ExtractedField(k, str(v), "high" if k in ("email", "url") else "medium")
                        for k, v in item.items()
                        if v is not None
                    ]
                    results.append(
                        ParseResult(record_id=f"{record_id}_{idx}", fields=fields, source="json")
                    )
                else:
                    # 非对象元素，转为文本解析
                    results.append(self.parse_text(str(item), f"{record_id}_{idx}"))
        else:
            raise ValueError(f"{ERR_UNSUPPORTED_TYPE}: JSON 根元素必须是对象或数组")

        return results


# ---------------------------------------------------------------------------
# 输出格式化
# ---------------------------------------------------------------------------
class OutputFormatter:
    """将 ParseResult 列表转换为不同格式。"""

    @staticmethod
    def to_json(results: List[ParseResult]) -> str:
        return json.dumps([r.to_dict() for r in results], ensure_ascii=False, indent=2)

    @staticmethod
    def to_markdown(results: List[ParseResult]) -> str:
        lines: List[str] = []
        for r in results:
            lines.append(f"## 记录: {r.record_id}")
            lines.append(f"- 来源: {r.source}")
            lines.append(f"- 时间: {r.created_at}")
            lines.append("")
            lines.append("| 字段 | 值 | 置信度 |")
            lines.append("|------|-----|--------|")
            for f in r.fields:
                lines.append(f"| {f.name} | {f.value} | {f.confidence} |")
            lines.append("")
        return "\n".join(lines)

    @staticmethod
    def to_table(results: List[ParseResult]) -> str:
        """以简单表格（制表符分隔）输出。"""
        lines: List[str] = []
        for r in results:
            lines.append(f"record_id: {r.record_id}")
            lines.append(f"source: {r.source}")
            lines.append("name\tvalue\tconfidence")
            for f in r.fields:
                lines.append(f"{f.name}\t{f.value}\t{f.confidence}")
            lines.append("")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# 批量处理
# ---------------------------------------------------------------------------
def batch_process(items: List[str], parser: PrototypeParser) -> List[ParseResult]:
    """
    批量处理多个文本条目。
    """
    results: List[ParseResult] = []
    for idx, item in enumerate(items):
        try:
            parsed = parser.parse_text(item, f"batch_{idx}")
            results.append(parsed)
        except ValueError as exc:
            # 单条失败不中断，但记录错误
            results.append(
                ParseResult(
                    record_id=f"batch_{idx}",
                    fields=[ExtractedField("error", str(exc), "low")],
                    source="batch_error",
                )
            )
    return results


# ---------------------------------------------------------------------------
# 输入加载
# ---------------------------------------------------------------------------
def load_input(source: str) -> str:
    """
    根据输入来源加载内容：
      - 文件路径（.txt/.csv/.json）
      - URL（http/https）
      - 直接文本
    """
    if not source or not source.strip():
        raise ValueError(ERR_INVALID_INPUT)

    # 检查是否为文件路径
    if source.startswith("file://"):
        path = source[7:]
        return _load_file(path)

    # 检查是否为 URL
    if source.startswith("http://") or source.startswith("https://"):
        return _load_url(source)

    # 检查是否为本地文件（存在且是文件）
    p = Path(source)
    if p.exists() and p.is_file():
        return _load_file(source)

    # 否则视为直接文本
    return source


def _load_file(path: str) -> str:
    try:
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"{ERR_FILE_NOT_FOUND}: 文件不存在: {path}")
        return p.read_text(encoding="utf-8", errors="replace")
    except FileNotFoundError as exc:
        raise ValueError(str(exc)) from exc
    except Exception as exc:
        raise ValueError(f"{ERR_FILE_NOT_FOUND}: {exc}") from exc


def _load_url(url: str) -> str:
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except Exception as exc:
        raise ValueError(f"{ERR_URL_ERROR}: {exc}") from exc


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------
def process_input(
    source: str,
    fmt: str = "json",
    batch: bool = False,
) -> str:
    """
    主处理函数。
    """
    parser = PrototypeParser()

    # 加载内容
    try:
        content = load_input(source)
    except ValueError as exc:
        return json.dumps({"error": str(exc)}, ensure_ascii=False)

    # 根据内容格式选择解析方式
    try:
        if batch:
            # 按行拆分进行批量处理
            lines = [ln for ln in content.splitlines() if ln.strip()]
            results = batch_process(lines, parser)
        elif content.lstrip().startswith("[") or content.lstrip().startswith("{"):
            results = parser.parse_json(content)
        elif "," in content.splitlines()[0] if content.splitlines() else False:
            results = parser.parse_csv(content)
        else:
            results = [parser.parse_text(content)]
    except ValueError as exc:
        return json.dumps({"error": str(exc)}, ensure_ascii=False)

    # 格式化输出
    try:
        formatter = OutputFormatter()
        if fmt == "json":
            return formatter.to_json(results)
        elif fmt == "markdown":
            return formatter.to_markdown(results)
        elif fmt == "table":
            return formatter.to_table(results)
        else:
            raise ValueError(f"{ERR_OUTPUT_ERROR}: 不支持的输出格式: {fmt}")
    except ValueError as exc:
        return json.dumps({"error": str(exc)}, ensure_ascii=False)


# ---------------------------------------------------------------------------
# 自检（--selftest）
# ---------------------------------------------------------------------------
def selftest() -> int:
    """
    离线自检核心逻辑。
    使用硬编码样例数据，不依赖外部文件/网络/当前目录。
    断言使用宽松阈值（大小/区间比较）。
    """
    print("[selftest] 开始自检...")

    parser = PrototypeParser()

    # 1. 文本解析测试
    sample_text = "联系人: 张三, 邮箱: zhangsan@example.com, 网站: https://example.com, 金额: $123.45, 日期: 2024-01-15, 状态: active"
    try:
        result = parser.parse_text(sample_text, "test_rec")
        fields = {f.name: f for f in result.fields}

        # 宽松断言：关键字段必须存在
        assert "email" in fields, "应识别 email"
        assert "url" in fields, "应识别 url"
        assert "amount" in fields, "应识别金额"
        assert "date" in fields, "应识别日期"
        assert "status" in fields, "应识别状态"

        # 值验证（宽松）
        assert "@" in fields["email"].value, "email 应包含 @"
        assert fields["email"].value.endswith(".com"), "email 应以 .com 结尾"
        assert "https://" in fields["url"].value, "url 应包含 https://"
        assert "$" in fields["amount"].value, "金额应包含 $ 符号"
        assert len(fields["date"].value) >= 8, "日期长度应至少 8 字符"
        print("  ✓ 文本解析测试通过")
    except AssertionError as exc:
        print(f"  ✗ 文本解析测试失败: {exc}")
        return 1
    except Exception as exc:
        print(f"  ✗ 文本解析异常: {exc}")
        return 1

    # 2. JSON 解析测试
    sample_json = '{"name": "测试", "email": "test@example.org", "age": 30}'
    try:
        results = parser.parse_json(sample_json, "json_rec")
        assert len(results) == 1, "JSON 单对象应产生一条记录"
        field_names = [f.name for f in results[0].fields]
        assert "email" in field_names, "JSON 应提取 email"
        assert "name" in field_names, "JSON 应提取 name"
        print("  ✓ JSON 解析测试通过")
    except AssertionError as exc:
        print(f"  ✗ JSON 解析测试失败: {exc}")
        return 1
    except Exception as exc:
        print(f"  ✗ JSON 解析异常: {exc}")
        return 1

    # 3. CSV 解析测试
    sample_csv = "name,email,amount\n李四,li@example.com,50.5\n王五,wang@example.com,100"
    try:
        results = parser.parse_csv(sample_csv, "csv_rec")
        assert len(results) == 2, "CSV 两行应产生两条记录"
        for r in results:
            assert len(r.fields) >= 1, "每条记录应至少有一个字段"
        print("  ✓ CSV 解析测试通过")
    except AssertionError as exc:
        print(f"  ✗ CSV 解析测试失败: {exc}")
        return 1
    except Exception as exc:
        print(f"  ✗ CSV 解析异常: {exc}")
        return 1

    # 4. 批量处理测试
    batch_items = [
        "第一行: 邮箱 a@b.com",
        "第二行: 网址 https://test.org",
        "第三行: 无特殊内容",
    ]
    try:
        batch_results = batch_process(batch_items, parser)
        assert len(batch_results) == 3, "批量处理应返回 3 条结果"
        email_found = any(
            any(f.name == "email" for f in r.fields) for r in batch_results
        )
        url_found = any(
            any(f.name == "url" for f in r.fields) for r in batch_results
        )
        assert email_found, "批量中应至少有一条含 email"
        assert url_found, "批量中应至少有一条含 url"
        print("  ✓ 批量处理测试通过")
    except AssertionError as exc:
        print(f"  ✗ 批量处理测试失败: {exc}")
        return 1
    except Exception as exc:
        print(f"  ✗ 批量处理异常: {exc}")
        return 1

    # 5. 输出格式化测试
    try:
        formatter = OutputFormatter()
        test_results = [ParseResult(record_id="t1", fields=[ExtractedField("k", "v", "high")], source="test")]
        json_out = formatter.to_json(test_results)
        md_out = formatter.to_markdown(test_results)
        table_out = formatter.to_table(test_results)

        assert "record_id" in json_out, "JSON 输出应包含 record_id"
        assert "|" in md_out, "Markdown 输出应包含表格分隔符"
        assert "\t" in table_out, "表格输出应包含制表符"
        print("  ✓ 输出格式化测试通过")
    except AssertionError as exc:
        print(f"  ✗ 输出格式化测试失败: {exc}")
        return 1
    except Exception as exc:
        print(f"  ✗ 输出格式化异常: {exc}")
        return 1

    # 6. 错误处理测试
    try:
        # 空输入
        try:
            parser.parse_text("")
            print("  ✗ 空输入应抛出异常")
            return 1
        except ValueError:
            pass

        # 非法 JSON
        try:
            parser.parse_json("{invalid json")
            print("  ✗ 非法 JSON 应抛出异常")
            return 1
        except ValueError:
            pass

        print("  ✓ 错误处理测试通过")
    except Exception as exc:
        print(f"  ✗ 错误处理异常: {exc}")
        return 1

    print("[selftest] 全部自检通过 ✓")
    return 0


# ---------------------------------------------------------------------------
# 入口
# ---------------------------------------------------------------------------
def main() -> int:
    parser = argparse.ArgumentParser(
        description="prototype: 原型转换、数据解析、结构化输出",
        epilog="示例: python main.py --input 'email: a@b.com' --format json",
    )
    parser.add_argument("--input", "-i", help="输入内容（文本/文件路径/URL）")
    parser.add_argument("--format", "-f", choices=["json", "markdown", "table"], default="json", help="输出格式")
    parser.add_argument("--batch", "-b", action="store_true", help="批量处理（按行拆分）")
    parser.add_argument("--selftest", action="store_true", help="运行离线自检")

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        return selftest()

    # 正常处理模式
    if not args.input:
        print("错误: 必须提供 --input 参数或使用 --selftest", file=sys.stderr)
        return 1

    try:
        output = process_input(args.input, args.format, args.batch)
        print(output)
        return 0
    except Exception as exc:
        print(f"错误: {ERR_INTERNAL}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
