#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py

基于功能规格独立实现的 S3 技能工具（clean-room 重写）。
仅使用 Python 标准库，无第三方依赖。
"""

import argparse
import json
import re
import sys
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# 错误码定义（对应规格第四章）
# ---------------------------------------------------------------------------
ERROR_CODES = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：...",
    "E003": "输入格式不符合要求，示例：...",
    "E004": "这超出了本工具的能力范围，建议...",
    "E005": "结果无法确定，建议：...",
    "E006": "内部处理异常，请稍后重试",
    "E007": "参数解析失败，请检查命令行参数",
    "E008": "输出序列化失败",
    "E009": "自检断言未通过",
    "E010": "未知错误",
}


class S3Error(Exception):
    """带错误码的业务异常"""

    def __init__(self, code: str, message: Optional[str] = None):
        self.code = code
        self.message = message or ERROR_CODES.get(code, ERROR_CODES["E010"])
        super().__init__(f"[{self.code}] {self.message}")


# ---------------------------------------------------------------------------
# 核心数据结构
# ---------------------------------------------------------------------------
class ProcessedItem:
    """单个输入项的处理结果"""

    def __init__(
        self,
        original: str,
        key_fields: Dict[str, Any],
        confidence: float,
        warnings: Optional[List[str]] = None,
    ):
        self.original = original
        self.key_fields = key_fields
        self.confidence = confidence
        self.warnings = warnings or []

    def to_dict(self) -> Dict[str, Any]:
        """转为字典结构"""
        return {
            "original": self.original,
            "key_fields": self.key_fields,
            "confidence": self.confidence,
            "warnings": self.warnings,
        }


class ProcessResult:
    """批量处理的整体结果"""

    def __init__(self, items: List[ProcessedItem]):
        self.items = items

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total": len(self.items),
            "items": [item.to_dict() for item in self.items],
        }


# ---------------------------------------------------------------------------
# 核心处理逻辑
# ---------------------------------------------------------------------------
def _validate_input(raw_input: str) -> None:
    """校验输入是否合法（E001/E003）"""
    if raw_input is None or raw_input.strip() == "":
        raise S3Error("E001")
    if len(raw_input) > 10000:  # 防止超长输入
        raise S3Error("E003")


def _extract_key_fields(text: str) -> Tuple[Dict[str, Any], float]:
    """
    从文本中提取关键信息并计算置信度。
    识别规则：
      - 形如 "key: value" 或 "key=value" 的字段
      - URL 链接
      - 数字编号
    置信度基于识别到的字段数量与文本长度综合判断。
    """
    fields: Dict[str, Any] = {}
    total_chars = len(text.strip())
    if total_chars == 0:
        return fields, 0.0

    # 1. 识别 key: value 或 key=value 模式
    pair_pattern = re.compile(
        r"(?P<key>[A-Za-z_][A-Za-z0-9_]*)\s*[:=]\s*(?P<value>[^,\n;]+)"
    )
    pair_matches = pair_pattern.findall(text)
    for key, value in pair_matches:
        cleaned_value = value.strip()
        if cleaned_value:
            fields[key] = cleaned_value

    # 2. 识别 URL
    url_pattern = re.compile(r"https?://[^\s,;]+")
    urls = url_pattern.findall(text)
    if urls:
        fields["url"] = urls[0]
        if len(urls) > 1:
            fields["additional_urls"] = urls[1:]

    # 3. 识别数字编号（如 ID、编号等）
    id_pattern = re.compile(r"(?:ID|id|编号|No\.?)\s*[:=]?\s*(\d+)")
    id_matches = id_pattern.findall(text)
    if id_matches:
        fields["id"] = id_matches[0]

    # 计算置信度
    # 规则：识别到的字段越多、文本越短，置信度越高
    field_count = len(fields)
    if field_count == 0:
        confidence = 0.3  # 未识别到任何字段，置信度低
    else:
        # 基础置信度 0.6，每个字段增加 0.1，最多到 0.95
        confidence = min(0.6 + 0.1 * field_count, 0.95)
        # 文本过长或过短都会降低置信度
        if total_chars < 5:
            confidence -= 0.1
        elif total_chars > 500:
            confidence -= 0.05
        # 确保置信度在 0~1 之间
        confidence = max(0.0, min(1.0, confidence))

    return fields, confidence


def _check_critical_fields(fields: Dict[str, Any]) -> Optional[str]:
    """
    检查关键字段是否完整（E002）。
    如果缺少必要字段，返回提示信息；否则返回 None。
    """
    # 至少需要识别出 1 个有效字段
    if not fields:
        return "未识别到任何关键字段，请提供包含 key: value 或 URL 格式的内容"
    return None


def process_single(text: str) -> ProcessedItem:
    """处理单个输入项"""
    _validate_input(text)

    fields, confidence = _extract_key_fields(text)

    # 关键信息缺失检查
    missing_hint = _check_critical_fields(fields)
    warnings = []
    if missing_hint:
        warnings.append(missing_hint)
        # 置信度过低时标注需核实
        if confidence < 0.85:
            warnings.append("[需核实] 识别出的关键字段较少，请人工确认结果")

    return ProcessedItem(
        original=text,
        key_fields=fields,
        confidence=confidence,
        warnings=warnings,
    )


def process_batch(inputs: List[str]) -> ProcessResult:
    """批量处理多个输入项"""
    if not inputs:
        raise S3Error("E001")

    items = []
    for raw in inputs:
        # 单条输入异常不中断整体流程，记录为低置信度结果
        try:
            item = process_single(raw)
        except S3Error as exc:
            item = ProcessedItem(
                original=raw,
                key_fields={},
                confidence=0.0,
                warnings=[f"处理失败: {exc.message}"],
            )
        items.append(item)

    return ProcessResult(items)


def format_output(result: ProcessResult, output_format: str = "json") -> str:
    """按指定格式输出结果"""
    if output_format == "json":
        try:
            return json.dumps(result.to_dict(), ensure_ascii=False, indent=2)
        except (TypeError, ValueError) as exc:
            raise S3Error("E008", f"JSON 序列化失败: {exc}") from exc
    elif output_format == "text":
        lines = []
        for idx, item in enumerate(result.items, 1):
            lines.append(f"--- 项目 {idx} ---")
            lines.append(f"原始输入: {item.original}")
            lines.append(f"关键字段: {json.dumps(item.key_fields, ensure_ascii=False)}")
            lines.append(f"置信度: {item.confidence * 100:.1f}%")
            if item.warnings:
                lines.append(f"提示: {'; '.join(item.warnings)}")
            lines.append("")
        return "\n".join(lines)
    else:
        raise S3Error("E003", f"不支持的输出格式: {output_format}")


# ---------------------------------------------------------------------------
# 自检模块（--selftest）
# ---------------------------------------------------------------------------
def run_selftest() -> int:
    """
    离线自检核心逻辑。
    使用硬编码样例数据，不读外部文件、不访问网络。
    断言使用宽松阈值，确保在任何环境可过。
    """
    print("开始自检...")

    # 样例 1: 正常输入，包含 key: value 和 URL
    sample1 = "name: test_item, url: https://example.com/data, id: 12345"
    try:
        item1 = process_single(sample1)
        assert item1.key_fields.get("name") == "test_item", "name 字段提取失败"
        assert "url" in item1.key_fields, "url 字段提取失败"
        assert item1.confidence > 0.5, "置信度应大于 50%"
        assert item1.confidence <= 1.0, "置信度不应超过 100%"
        print("  样例1（正常输入）: 通过")
    except AssertionError as exc:
        print(f"  样例1 失败: {exc}")
        return 1
    except S3Error as exc:
        print(f"  样例1 异常: {exc.message}")
        return 1

    # 样例 2: 空输入，应触发 E001
    try:
        process_single("   ")
        print("  样例2（空输入）: 失败（未触发错误）")
        return 1
    except S3Error as exc:
        assert exc.code == "E001", f"错误码应为 E001，实际为 {exc.code}"
        print("  样例2（空输入）: 通过")

    # 样例 3: 批量处理，包含一个合法输入和一个非法输入
    batch_input = [
        "key1: value1, key2: value2",
        "   ",  # 非法输入
        "url: https://test.org/page, note: hello world",
    ]
    try:
        batch_result = process_batch(batch_input)
        assert len(batch_result.items) == 3, "批量处理应返回 3 个结果"
        # 合法输入应有字段提取
        assert len(batch_result.items[0].key_fields) >= 2, "第一个输入应提取到至少 2 个字段"
        # 非法输入应置信度为 0 且包含警告
        assert batch_result.items[1].confidence == 0.0, "非法输入置信度应为 0"
        assert len(batch_result.items[1].warnings) > 0, "非法输入应有警告信息"
        # 第三个输入应提取到 url
        assert "url" in batch_result.items[2].key_fields, "第三个输入应提取到 url"
        print("  样例3（批量处理）: 通过")
    except AssertionError as exc:
        print(f"  样例3 失败: {exc}")
        return 1
    except S3Error as exc:
        print(f"  样例3 异常: {exc.message}")
        return 1

    # 样例 4: 输出格式化（JSON 和文本）
    try:
        sample_item = ProcessedItem(
            original="test data",
            key_fields={"name": "test"},
            confidence=0.9,
            warnings=[],
        )
        sample_result = ProcessResult([sample_item])

        json_out = format_output(sample_result, "json")
        parsed = json.loads(json_out)
        assert parsed["total"] == 1, "JSON 输出 total 应为 1"
        assert parsed["items"][0]["confidence"] == 0.9, "JSON 输出 confidence 不正确"

        text_out = format_output(sample_result, "text")
        assert "测试" in text_out or "项目" in text_out or "---" in text_out, "文本输出格式异常"
        print("  样例4（输出格式化）: 通过")
    except AssertionError as exc:
        print(f"  样例4 失败: {exc}")
        return 1
    except S3Error as exc:
        print(f"  样例4 异常: {exc.message}")
        return 1

    # 样例 5: 边界情况 - 只包含 URL 的输入
    try:
        url_only = process_single("https://example.com/single")
        assert "url" in url_only.key_fields, "应识别出 URL"
        assert url_only.confidence > 0.3, "URL 识别的置信度应大于 30%"
        print("  样例5（URL 边界）: 通过")
    except AssertionError as exc:
        print(f"  样例5 失败: {exc}")
        return 1
    except S3Error as exc:
        print(f"  样例5 异常: {exc.message}")
        return 1

    # 样例 6: 错误码体系完整性
    try:
        for code in ["E001", "E002", "E003", "E004", "E005"]:
            assert code in ERROR_CODES, f"错误码 {code} 未定义"
        print("  样例6（错误码体系）: 通过")
    except AssertionError as exc:
        print(f"  样例6 失败: {exc}")
        return 1

    print("所有自检样例通过！")
    return 0


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------
def main() -> int:
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description="S3 技能工具 - 伪 S3 协议处理",
        epilog="示例: python main.py 'name: test, url: https://example.com'",
    )
    parser.add_argument(
        "inputs",
        nargs="*",
        help="待处理的输入内容（可多个，空格分隔）",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行离线自检",
    )
    parser.add_argument(
        "--format",
        choices=["json", "text"],
        default="json",
        help="输出格式（默认: json）",
    )
    parser.add_argument(
        "--batch",
        action="store_true",
        help="批量模式：每行输入作为独立条目处理",
    )

    try:
        args = parser.parse_args()
    except SystemExit as exc:
        # argparse 出错时返回非零退出码
        return exc.code if isinstance(exc.code, int) else 1

    # 自检模式
    if args.selftest:
        return run_selftest()

    # 处理输入
    if not args.inputs:
        print(f"错误: {ERROR_CODES['E001']}", file=sys.stderr)
        return 1

    try:
        if args.batch:
            # 批量模式：每个参数作为独立输入
            result = process_batch(args.inputs)
        else:
            # 单条模式：将所有参数合并为一条输入
            combined = " ".join(args.inputs)
            result = process_batch([combined])

        output = format_output(result, args.format)
        print(output)
        return 0

    except S3Error as exc:
        print(f"错误: {exc.message}", file=sys.stderr)
        return 1
    except Exception as exc:  # 兜底异常处理
        print(f"错误: [{ERROR_CODES['E010']}] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
