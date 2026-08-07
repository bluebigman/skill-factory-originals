#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py — 未命名工具（swiftui-design-skill）独立实现

本脚本依据功能规格 clean-room 重写，仅使用标准库。
提供命令行交互与 --selftest 离线自检。
"""

import argparse
import json
import sys
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# 错误码定义（E001-E010）
# ---------------------------------------------------------------------------
ERROR_CODES = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：...（逐项追问）",
    "E003": "输入格式不符合要求，示例：...",
    "E004": "这超出了本工具的能力范围，建议：...",
    "E005": "结果无法确定，建议：...",
    "E006": "内部处理错误，请重试",
    "E007": "输出序列化失败",
    "E008": "参数解析错误",
    "E009": "自检失败，核心逻辑异常",
    "E010": "未知错误",
}


class ToolError(Exception):
    """带错误码的异常类"""

    def __init__(self, code: str, message: Optional[str] = None):
        self.code = code
        self.message = message or ERROR_CODES.get(code, ERROR_CODES["E010"])
        super().__init__(f"[{code}] {self.message}")


# ---------------------------------------------------------------------------
# 核心数据结构
# ---------------------------------------------------------------------------
@dataclass
class ProcessedItem:
    """单条处理结果"""

    input_text: str
    output_text: str
    confidence: float  # 0.0 ~ 1.0
    needs_review: bool = False
    uncertain_points: List[str] = field(default_factory=list)


@dataclass
class ProcessResult:
    """批量处理结果"""

    items: List[ProcessedItem] = field(default_factory=list)
    summary: Dict[str, Any] = field(default_factory=dict)

    def add_item(self, item: ProcessedItem) -> None:
        self.items.append(item)

    def finalize(self) -> None:
        """汇总统计信息"""
        total = len(self.items)
        if total == 0:
            self.summary = {"total": 0, "high_conf": 0, "medium_conf": 0, "low_conf": 0}
            return
        high = sum(1 for it in self.items if it.confidence >= 0.90)
        medium = sum(1 for it in self.items if 0.85 <= it.confidence < 0.90)
        low = sum(1 for it in self.items if it.confidence < 0.85)
        self.summary = {
            "total": total,
            "high_conf": high,
            "medium_conf": medium,
            "low_conf": low,
        }


# ---------------------------------------------------------------------------
# 核心处理逻辑
# ---------------------------------------------------------------------------
class CoreProcessor:
    """核心处理器：解析输入、生成结构化输出、计算置信度"""

    # 可识别的关键字段（按优先级）
    KEY_FIELDS = ["name", "type", "value", "date", "amount"]

    def process(self, raw_input: str) -> ProcessResult:
        """
        处理用户输入的文本。

        :param raw_input: 用户提供的原始文本
        :return: 处理结果
        """
        if raw_input is None or not raw_input.strip():
            raise ToolError("E001")

        lines = [ln.strip() for ln in raw_input.splitlines() if ln.strip()]
        result = ProcessResult()

        for line in lines:
            item = self._process_line(line)
            result.add_item(item)

        result.finalize()
        return result

    def _process_line(self, line: str) -> ProcessedItem:
        """处理单行输入"""
        # 尝试解析 JSON
        parsed = self._try_parse_json(line)
        if parsed is not None:
            return self._handle_structured(parsed)

        # 尝试解析 key=value 格式
        kv = self._try_parse_kv(line)
        if kv:
            return self._handle_kv(kv)

        # 默认按自由文本处理
        return self._handle_free_text(line)

    # -- 各解析分支 ------------------------------------------------------
    def _try_parse_json(self, text: str) -> Optional[Dict[str, Any]]:
        """尝试将文本解析为 JSON 对象"""
        try:
            obj = json.loads(text)
            if isinstance(obj, dict):
                return obj
        except (json.JSONDecodeError, ValueError):
            pass
        return None

    def _try_parse_kv(self, text: str) -> Dict[str, str]:
        """尝试解析 key=value 对（逗号或分号分隔）"""
        result: Dict[str, str] = {}
        for sep in [",", ";"]:
            if sep in text:
                parts = [p.strip() for p in text.split(sep) if p.strip()]
                for part in parts:
                    if "=" in part:
                        k, v = part.split("=", 1)
                        result[k.strip().lower()] = v.strip()
                if result:
                    return result
        return result

    # -- 各处理分支 ------------------------------------------------------
    def _handle_structured(self, data: Dict[str, Any]) -> ProcessedItem:
        """处理结构化数据（JSON）"""
        # 提取关键字段
        extracted: Dict[str, Any] = {}
        missing = []
        for field_name in self.KEY_FIELDS:
            if field_name in data and data[field_name] is not None:
                extracted[field_name] = data[field_name]
            else:
                missing.append(field_name)

        # 计算置信度
        known = len(extracted)
        total_fields = len(self.KEY_FIELDS)
        confidence = known / total_fields if total_fields > 0 else 0.0

        # 生成输出
        output_lines = ["已识别关键信息："]
        for k, v in extracted.items():
            output_lines.append(f"  - {k}: {v}")

        uncertain = []
        if missing:
            output_lines.append(f"缺失字段: {', '.join(missing)}")
            uncertain.append(f"缺少字段: {', '.join(missing)}")

        needs_review = confidence < 0.85
        if 0.85 <= confidence < 0.90:
            output_lines.append("⚠️ 建议复核")
        elif confidence < 0.85:
            output_lines.append("🔍 [需核实] 部分信息不确定")

        return ProcessedItem(
            input_text=json.dumps(data, ensure_ascii=False),
            output_text="\n".join(output_lines),
            confidence=confidence,
            needs_review=needs_review,
            uncertain_points=uncertain,
        )

    def _handle_kv(self, kv: Dict[str, str]) -> ProcessedItem:
        """处理 key=value 格式"""
        # 规范化：只保留关键字段
        extracted = {k: v for k, v in kv.items() if k in self.KEY_FIELDS}
        
        # 如果有非关键字段，也记录一下
        non_key_fields = {k: v for k, v in kv.items() if k not in self.KEY_FIELDS}
        
        # 计算置信度：基于实际提供的字段数量
        # 如果提供了关键字段，置信度较高；否则较低
        if extracted:
            # 根据关键字段的覆盖比例计算基础置信度
            coverage = len(extracted) / len(self.KEY_FIELDS)
            # 基础置信度：0.6 + 0.4 * coverage，确保至少有0.6
            confidence = min(0.6 + 0.4 * coverage, 0.95)
        else:
            # 只有非关键字段，置信度较低
            confidence = 0.3

        # 生成输出
        output_lines = ["已识别关键信息："]
        if extracted:
            for k, v in extracted.items():
                output_lines.append(f"  - {k}: {v}")
        else:
            output_lines.append("  （未识别到标准关键字段）")

        uncertain = []
        if non_key_fields:
            output_lines.append(f"其他字段: {', '.join(f'{k}={v}' for k, v in non_key_fields.items())}")
            uncertain.append("包含非标准字段")

        # 缺失的关键字段
        missing_fields = [f for f in self.KEY_FIELDS if f not in extracted]
        if missing_fields:
            output_lines.append(f"缺失字段: {', '.join(missing_fields)}")
            uncertain.append(f"缺少字段: {', '.join(missing_fields)}")

        needs_review = confidence < 0.85
        if 0.85 <= confidence < 0.90:
            output_lines.append("⚠️ 建议复核")
        elif confidence < 0.85:
            output_lines.append("🔍 [需核实] 部分信息不确定")

        return ProcessedItem(
            input_text=", ".join(f"{k}={v}" for k, v in kv.items()),
            output_text="\n".join(output_lines),
            confidence=confidence,
            needs_review=needs_review,
            uncertain_points=uncertain,
        )

    def _handle_free_text(self, text: str) -> ProcessedItem:
        """处理自由文本（低置信度）"""
        # 简单启发式：检测是否包含关键字段名
        found = [f for f in self.KEY_FIELDS if f in text.lower()]
        confidence = min(0.5 + 0.1 * len(found), 0.8)  # 最高 0.8

        output = f"已接收文本（长度 {len(text)} 字符）"
        if found:
            output += f"，识别到字段关键词: {', '.join(found)}"
        output += "\n🔍 [需核实] 自由文本无法完全结构化"

        return ProcessedItem(
            input_text=text,
            output_text=output,
            confidence=confidence,
            needs_review=True,
            uncertain_points=["自由文本，无法保证结构化解析"],
        )


# ---------------------------------------------------------------------------
# 输出格式化
# ---------------------------------------------------------------------------
def format_output(result: ProcessResult, fmt: str = "text") -> str:
    """将处理结果格式化为指定格式"""
    if fmt == "json":
        try:
            return json.dumps(
                {
                    "summary": result.summary,
                    "items": [
                        {
                            "input": it.input_text,
                            "output": it.output_text,
                            "confidence": it.confidence,
                            "needs_review": it.needs_review,
                            "uncertain_points": it.uncertain_points,
                        }
                        for it in result.items
                    ],
                },
                ensure_ascii=False,
                indent=2,
            )
        except (TypeError, ValueError) as e:
            raise ToolError("E007", f"JSON 序列化失败: {e}") from e

    # 默认 text 格式
    lines = ["=== 处理结果 ==="]
    for i, item in enumerate(result.items, 1):
        lines.append(f"--- 条目 {i} ---")
        lines.append(item.output_text)
        conf = item.confidence * 100
        lines.append(f"置信度: {conf:.1f}%")
        if item.needs_review:
            lines.append("状态: 建议人工复核")
        if item.uncertain_points:
            lines.append("不确定点: " + "; ".join(item.uncertain_points))
    lines.append("--- 汇总 ---")
    lines.append(f"总数: {result.summary.get('total', 0)}")
    lines.append(f"高置信度: {result.summary.get('high_conf', 0)}")
    lines.append(f"中置信度: {result.summary.get('medium_conf', 0)}")
    lines.append(f"低置信度: {result.summary.get('low_conf', 0)}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    """构建命令行参数解析器"""
    parser = argparse.ArgumentParser(
        description="未命名工具 — SwiftUI 设计技能辅助处理",
        epilog="示例: python main.py --input '{\"name\":\"test\"}' --format json",
    )
    parser.add_argument(
        "--input",
        type=str,
        help="待处理的输入文本，支持 JSON、key=value 或自由文本",
    )
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="输出格式（默认 text）",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检（不读外部文件、不访问网络）",
    )
    return parser


def run_selftest() -> int:
    """内置自检：使用硬编码样例验证核心逻辑"""
    print("开始自检...")
    processor = CoreProcessor()

    # 测试用例 1: JSON 输入
    try:
        json_input = '{"name": "demo", "type": "sample", "value": 42}'
        result1 = processor.process(json_input)
        assert result1.summary["total"] > 0, "JSON 处理应产生条目"
        assert result1.items[0].confidence > 0.5, "JSON 置信度应较高"
        print("  ✓ JSON 输入处理正常")
    except AssertionError as e:
        print(f"  ✗ JSON 测试失败: {e}")
        raise ToolError("E009", f"JSON 自检失败: {e}") from e

    # 测试用例 2: key=value 输入
    try:
        kv_input = "name=test, type=demo"
        result2 = processor.process(kv_input)
        assert result2.summary["total"] > 0, "KV 处理应产生条目"
        assert result2.items[0].confidence > 0.5, "KV 置信度应较高"
        print("  ✓ KV 输入处理正常")
    except AssertionError as e:
        print(f"  ✗ KV 测试失败: {e}")
        raise ToolError("E009", f"KV 自检失败: {e}") from e

    # 测试用例 3: 自由文本
    try:
        free_input = "这是一段普通文本，包含 name 字段"
        result3 = processor.process(free_input)
        assert result3.summary["total"] > 0, "自由文本应产生条目"
        assert result3.items[0].confidence < 0.9, "自由文本置信度应较低"
        assert result3.items[0].needs_review, "自由文本应标记需复核"
        print("  ✓ 自由文本处理正常")
    except AssertionError as e:
        print(f"  ✗ 自由文本测试失败: {e}")
        raise ToolError("E009", f"自由文本自检失败: {e}") from e

    # 测试用例 4: 空输入
    try:
        processor.process("")
        print("  ✗ 空输入应抛出 E001")
        raise ToolError("E009", "空输入未正确抛出 E001")
    except ToolError as e:
        assert e.code == "E001", f"应抛出 E001，实际 {e.code}"
        print("  ✓ 空输入正确处理")

    # 测试用例 5: 批量多行
    try:
        batch_input = '{"name":"a"}\nname=b, type=c\n自由文本'
        result5 = processor.process(batch_input)
        assert result5.summary["total"] >= 3, "多行输入应产生多个条目"
        print("  ✓ 批量处理正常")
    except AssertionError as e:
        print(f"  ✗ 批量测试失败: {e}")
        raise ToolError("E009", f"批量自检失败: {e}") from e

    print("全部自检通过 ✅")
    return 0


def main() -> int:
    """主入口"""
    parser = build_parser()
    try:
        args = parser.parse_args()
    except SystemExit as e:
        # argparse 内部错误
        raise ToolError("E008", "参数解析失败") from e

    # 自检模式
    if args.selftest:
        try:
            return run_selftest()
        except ToolError as e:
            print(f"自检失败: {e}", file=sys.stderr)
            return 1

    # 正常处理模式
    if not args.input:
        raise ToolError("E001")

    try:
        processor = CoreProcessor()
        result = processor.process(args.input)
        output = format_output(result, args.format)
        print(output)
        return 0
    except ToolError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1
    except Exception as e:  # 兜底
        print(f"错误: [{ERROR_CODES['E010']}] 未预期异常: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
