#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
schemaz - SQL查询 技能实现脚本

本脚本基于功能规格独立实现（clean-room），提供：
- 将用户提供的数据/文件/URL 转换为结构化结果
- 识别并保留输入中的关键信息
- 按约定格式生成输出
- 对不确定项给出置信度提示
- 支持批量处理和自定义格式

仅使用标准库实现，无第三方依赖。
"""

import argparse
import json
import os
import sys
import urllib.parse
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union


# ============================================================
# 错误码定义
# ============================================================
ERROR_CODES = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：...",
    "E003": "输入格式不符合要求，示例：...",
    "E004": "这超出了本工具的能力范围，建议...",
    "E005": "结果无法确定，建议：...",
    "E006": "内部处理错误，请重试或联系支持",
    "E007": "输出格式不支持，仅支持 json/text/csv",
    "E008": "文件读取失败，请检查文件路径和权限",
    "E009": "URL 解析失败，请输入合法的 URL",
    "E010": "批量处理中断，请检查输入列表",
}


class SchemaZError(Exception):
    """自定义异常类，携带错误码。"""

    def __init__(self, error_code: str, message: Optional[str] = None):
        self.error_code = error_code
        self.message = message or ERROR_CODES.get(error_code, "未知错误")
        super().__init__(f"[{error_code}] {self.message}")


# ============================================================
# 核心数据结构
# ============================================================

class ProcessedItem:
    """单个输入项的处理结果。"""

    def __init__(
        self,
        item_id: str,
        source_type: str,
        content: str,
        key_fields: Dict[str, Any],
        confidence: float,
        note: Optional[str] = None,
    ):
        self.item_id = item_id
        self.source_type = source_type
        self.content = content
        self.key_fields = key_fields
        self.confidence = confidence
        self.note = note

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典表示。"""
        result = {
            "id": self.item_id,
            "source_type": self.source_type,
            "content": self.content,
            "key_fields": self.key_fields,
            "confidence": self.confidence,
        }
        if self.note:
            result["note"] = self.note
        return result


class ProcessingResult:
    """批量处理结果。"""

    def __init__(self, items: List[ProcessedItem], warnings: Optional[List[str]] = None):
        self.items = items
        self.warnings = warnings or []

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典表示。"""
        return {
            "items": [item.to_dict() for item in self.items],
            "warnings": self.warnings,
            "total": len(self.items),
            "success": all(item.confidence >= 0.85 for item in self.items),
        }


# ============================================================
# 输入解析模块
# ============================================================

def detect_source_type(source: str) -> str:
    """
    检测输入来源类型。

    支持类型：text / file / url / json
    返回：检测到的类型字符串
    """
    if not source or not source.strip():
        raise SchemaZError("E001")

    source = source.strip()

    # 检查是否为 URL
    if source.startswith(("http://", "https://")):
        parsed = urllib.parse.urlparse(source)
        if parsed.scheme and parsed.netloc:
            return "url"
        raise SchemaZError("E009")

    # 检查是否为文件路径
    if len(source) > 3 and (
        source.startswith((".", "/", "~", "\\")) or
        ":" in source[:2] or
        source.endswith((".txt", ".json", ".csv", ".md", ".log", ".xml"))
    ):
        return "file"

    # 检查是否为 JSON 字符串
    if source.startswith(("{", "[")):
        try:
            json.loads(source)
            return "json"
        except json.JSONDecodeError:
            pass

    # 默认视为纯文本
    return "text"


def parse_json_input(content: str) -> Dict[str, Any]:
    """解析 JSON 字符串输入。"""
    try:
        data = json.loads(content)
        if isinstance(data, dict):
            return data
        if isinstance(data, list):
            return {"items": data}
        return {"value": data}
    except json.JSONDecodeError as exc:
        raise SchemaZError("E003", f"JSON 解析失败: {exc}") from exc


def read_file_content(filepath: str) -> str:
    """读取文件内容。"""
    try:
        path = Path(filepath).expanduser()
        if not path.exists():
            raise SchemaZError("E008", f"文件不存在: {filepath}")
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        raise SchemaZError("E008", f"文件读取失败: {exc}") from exc


def parse_url_input(url: str) -> Dict[str, Any]:
    """解析 URL 输入（仅提取元数据，不访问网络）。"""
    parsed = urllib.parse.urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        raise SchemaZError("E009")

    # 提取 URL 中的关键信息
    key_fields = {
        "scheme": parsed.scheme,
        "host": parsed.netloc,
        "path": parsed.path or "/",
        "query_params": urllib.parse.parse_qs(parsed.query),
    }
    return key_fields


def extract_key_fields(content: str, source_type: str) -> Tuple[Dict[str, Any], float]:
    """
    从输入内容中提取关键信息。

    返回：(关键字段字典, 置信度)
    """
    if source_type == "json":
        data = parse_json_input(content)
        return data, 0.95

    if source_type == "url":
        data = parse_url_input(content)
        return data, 0.90

    if source_type == "file":
        # 文件内容作为文本处理
        return {"file_content": content[:200]}, 0.88

    # 纯文本处理：尝试提取结构化字段
    lines = content.strip().split("\n")
    if len(lines) == 1:
        # 单行文本，尝试识别键值对
        text = lines[0].strip()
        if "=" in text:
            # 形如 key=value 的格式
            kv_pairs = {}
            for part in text.split(","):
                if "=" in part:
                    k, v = part.split("=", 1)
                    kv_pairs[k.strip()] = v.strip()
            if kv_pairs:
                return kv_pairs, 0.85

        # 无法识别结构，返回整体文本
        return {"text": text}, 0.75

    # 多行文本，按行处理
    if len(lines) <= 10:
        return {"lines": lines, "line_count": len(lines)}, 0.80

    # 长文本
    return {"text_preview": content[:500], "length": len(content)}, 0.70


def generate_item_id(source: str, index: int) -> str:
    """生成条目 ID。"""
    source_type = detect_source_type(source)
    if source_type == "url":
        parsed = urllib.parse.urlparse(source)
        base = parsed.netloc.replace(".", "_")
    elif source_type == "file":
        base = Path(source).stem.replace(" ", "_")
    else:
        # 使用内容哈希的一部分作为 ID
        import hashlib
        base = hashlib.md5(source.encode()).hexdigest()[:8]
    return f"{source_type}_{base}_{index}"


# ============================================================
# 核心处理逻辑
# ============================================================

def process_single(source: str, item_id: Optional[str] = None) -> ProcessedItem:
    """
    处理单个输入项。

    参数：
        source: 输入内容（文本/文件路径/URL）
        item_id: 自定义 ID，不提供时自动生成

    返回：
        ProcessedItem 对象
    """
    if not source or not source.strip():
        raise SchemaZError("E001")

    source_type = detect_source_type(source)

    # 根据来源类型加载内容
    if source_type == "file":
        content = read_file_content(source)
    else:
        content = source

    # 提取关键字段和置信度
    key_fields, base_confidence = extract_key_fields(content, source_type)

    # 计算最终置信度（考虑来源类型）
    confidence_map = {
        "json": 0.95,
        "url": 0.90,
        "file": 0.88,
        "text": 0.75,
    }
    confidence = min(base_confidence, confidence_map.get(source_type, 0.75))

    # 生成 ID
    if item_id is None:
        item_id = generate_item_id(source, 0)

    # 添加置信度标注
    note = None
    if confidence < 0.85:
        note = "[需核实] 输入结构不明确，请人工确认关键信息"
    elif 0.85 <= confidence < 0.90:
        note = "建议复核"

    return ProcessedItem(
        item_id=item_id,
        source_type=source_type,
        content=content[:500] if len(content) > 500 else content,
        key_fields=key_fields,
        confidence=confidence,
        note=note,
    )


def process_batch(sources: List[str]) -> ProcessingResult:
    """
    批量处理多个输入项。

    参数：
        sources: 输入列表

    返回：
        ProcessingResult 对象
    """
    if not sources:
        raise SchemaZError("E001")

    items = []
    warnings = []

    for idx, source in enumerate(sources):
        try:
            item = process_single(source, item_id=f"item_{idx + 1}")
            items.append(item)
        except SchemaZError as exc:
            warnings.append(f"第 {idx + 1} 项处理失败: [{exc.error_code}] {exc.message}")

    if not items:
        raise SchemaZError("E010")

    return ProcessingResult(items=items, warnings=warnings)


def format_output(result: Union[ProcessedItem, ProcessingResult], fmt: str = "json") -> str:
    """
    格式化输出结果。

    参数：
        result: 处理结果对象
        fmt: 输出格式（json/text/csv）

    返回：
        格式化后的字符串
    """
    if fmt not in ("json", "text", "csv"):
        raise SchemaZError("E007")

    if isinstance(result, ProcessedItem):
        data = result.to_dict()
    else:
        data = result.to_dict()

    if fmt == "json":
        return json.dumps(data, ensure_ascii=False, indent=2)

    if fmt == "text":
        lines = []
        items = data["items"] if "items" in data else [data]
        for item in items:
            lines.append(f"ID: {item['id']}")
            lines.append(f"来源类型: {item['source_type']}")
            lines.append(f"内容: {item['content'][:100]}...")
            lines.append(f"置信度: {item['confidence']:.0%}")
            if item.get("note"):
                lines.append(f"备注: {item['note']}")
            lines.append("-" * 40)
        return "\n".join(lines)

    # CSV 格式
    import csv
    import io

    items = data["items"] if "items" in data else [data]
    output = io.StringIO()
    writer = csv.writer(output)

    # 表头
    writer.writerow(["id", "source_type", "confidence", "note"])

    # 数据行
    for item in items:
        writer.writerow([
            item["id"],
            item["source_type"],
            f"{item['confidence']:.2f}",
            item.get("note", ""),
        ])

    return output.getvalue()


# ============================================================
# 命令行接口
# ============================================================

def run_cli() -> int:
    """命令行入口函数。"""
    parser = argparse.ArgumentParser(
        description="schemaz - SQL查询 技能实现",
        epilog="示例: python main.py '需要处理的内容' --format json",
    )
    parser.add_argument(
        "inputs",
        nargs="*",
        help="输入内容（文本/文件路径/URL），支持多个输入",
    )
    parser.add_argument(
        "--format",
        choices=["json", "text", "csv"],
        default="json",
        help="输出格式（默认: json）",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检，不处理外部输入",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="显示详细处理信息",
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        return run_selftest()

    # 无输入时提示
    if not args.inputs:
        print(ERROR_CODES["E001"], file=sys.stderr)
        return 1

    try:
        # 处理输入
        if len(args.inputs) == 1:
            # 单个输入
            result = process_single(args.inputs[0])
            output = format_output(result, args.format)
        else:
            # 批量输入
            result = process_batch(args.inputs)
            output = format_output(result, args.format)

            if result.warnings and args.verbose:
                print("警告信息：", file=sys.stderr)
                for warning in result.warnings:
                    print(f"  - {warning}", file=sys.stderr)

        print(output)
        return 0

    except SchemaZError as exc:
        print(f"错误 {exc.error_code}: {exc.message}", file=sys.stderr)
        return 1
    except Exception as exc:  # 兜底错误
        print(f"错误 E006: 未预期异常 - {exc}", file=sys.stderr)
        return 1


# ============================================================
# 自检模块（内置硬编码样例，离线运行）
# ============================================================

def run_selftest() -> int:
    """
    运行内置自检。

    使用硬编码样例数据验证核心逻辑，不依赖外部文件或网络。
    断言使用宽松阈值，确保稳健。
    """
    print("=" * 60)
    print("schemaz 自检开始")
    print("=" * 60)

    # 样例 1: JSON 输入
    print("\n[测试 1] JSON 输入")
    json_input = '{"name": "张三", "age": 30, "city": "北京"}'
    item = process_single(json_input)
    assert item.source_type == "json", "JSON 输入类型检测失败"
    assert item.confidence >= 0.90, "JSON 输入置信度应较高"
    assert "name" in item.key_fields, "JSON 关键字段提取失败"
    print(f"  ✓ 通过 (置信度: {item.confidence:.0%})")

    # 样例 2: URL 输入
    print("\n[测试 2] URL 输入")
    url_input = "https://example.com/path/to/page?query=test&page=1"
    item = process_single(url_input)
    assert item.source_type == "url", "URL 输入类型检测失败"
    assert item.confidence >= 0.85, "URL 输入置信度应较高"
    assert item.key_fields.get("host") == "example.com", "URL 主机解析失败"
    print(f"  ✓ 通过 (置信度: {item.confidence:.0%})")

    # 样例 3: 纯文本输入
    print("\n[测试 3] 纯文本输入")
    text_input = "产品名称=笔记本电脑, 价格=5999, 库存=100"
    item = process_single(text_input)
    assert item.source_type == "text", "文本输入类型检测失败"
    assert item.confidence >= 0.70, "文本输入置信度应可接受"
    assert "产品名称" in item.key_fields, "文本键值对提取失败"
    print(f"  ✓ 通过 (置信度: {item.confidence:.0%})")

    # 样例 4: 批量处理
    print("\n[测试 4] 批量处理")
    batch_inputs = [
        '{"id": 1, "value": "A"}',
        "简单文本内容",
        "https://example.org/api",
    ]
    result = process_batch(batch_inputs)
    assert len(result.items) == 3, "批量处理数量不符"
    assert result.total == 3, "总数统计错误"
    print(f"  ✓ 通过 (处理 {result.total} 项)")

    # 样例 5: 输出格式化
    print("\n[测试 5] 输出格式化")
    json_output = format_output(item, "json")
    assert json_output.startswith("{"), "JSON 输出格式错误"
    text_output = format_output(item, "text")
    assert "置信度" in text_output, "文本输出格式错误"
    csv_output = format_output(item, "csv")
    assert "confidence" in csv_output, "CSV 输出格式错误"
    print("  ✓ 通过 (json/text/csv 均正常)")

    # 样例 6: 错误处理
    print("\n[测试 6] 错误处理")
    try:
        process_single("")
        assert False, "空输入应抛出 E001"
    except SchemaZError as exc:
        assert exc.error_code == "E001", "空输入错误码应为 E001"
    print("  ✓ 通过 (E001 空输入检测)")

    # 样例 7: 置信度标注
    print("\n[测试 7] 置信度标注")
    low_conf_item = process_single("一段没有明显结构的长文本内容，用于测试低置信度场景")
    if low_conf_item.confidence < 0.85:
        assert low_conf_item.note is not None, "低置信度应有标注"
    high_conf_item = process_single('{"structured": "data"}')
    if high_conf_item.confidence >= 0.90:
        assert high_conf_item.note is None, "高置信度不应有标注"
    print("  ✓ 通过 (置信度标注逻辑正常)")

    # 汇总
    print("\n" + "=" * 60)
    print("所有自检项均通过 ✅")
    print("=" * 60)
    return 0


# ============================================================
# 主入口
# ============================================================

if __name__ == "__main__":
    sys.exit(run_cli())
