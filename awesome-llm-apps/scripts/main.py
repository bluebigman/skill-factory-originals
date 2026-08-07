#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
awesome-llm-apps 技能工具

基于功能规格独立实现的命令行工具，提供：
- 输入内容结构化处理
- 关键信息提取与置信度评估
- 批量处理与格式转换
- 内置离线自检（--selftest）

错误码：
    E001: 输入为空
    E002: 关键信息缺失
    E003: 输入格式错误
    E004: 超出能力边界
    E005: 置信度过低
    E006: 未知命令参数
    E007: 内部处理错误
    E008: 输出格式不支持
    E009: 批量处理中断
    E010: 自检失败

许可证：MIT License
Copyright (c) 2026 原创作者（自持版权）
"""

import argparse
import json
import re
import sys
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# 数据模型
# ---------------------------------------------------------------------------

@dataclass
class ProcessedItem:
    """单条输入的处理结果"""
    original: str                    # 原始输入
    key_fields: Dict[str, Any] = field(default_factory=dict)  # 提取的关键字段
    confidence: float = 0.0          # 置信度 0~1
    needs_review: bool = False       # 是否需要人工复核
    uncertain_points: List[str] = field(default_factory=list)  # 不确定点说明
    status: str = "ok"               # ok / error


@dataclass
class BatchResult:
    """批量处理结果"""
    items: List[ProcessedItem] = field(default_factory=list)
    success_count: int = 0
    error_count: int = 0
    error_codes: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# 核心处理逻辑
# ---------------------------------------------------------------------------

class ContentProcessor:
    """
    内容处理器：负责将输入内容转换为结构化结果。
    完全离线工作，不访问网络。
    """

    # 常见关键字段的识别模式（宽松匹配）
    _FIELD_PATTERNS = {
        "email": r"[\w.+-]+@[\w-]+\.[\w.]+",
        "phone": r"(\+?\d{1,3}[-\s]?)?\d{3}[-\s]?\d{3,4}[-\s]?\d{4}",
        "url": r"https?://[^\s]+",
        "date": r"\d{4}[-/]\d{1,2}[-/]\d{1,2}",
        "price": r"[\$¥€£]\s?\d+(\.\d{1,2})?",
    }

    # 可识别的输出格式
    _SUPPORTED_FORMATS = ("json", "text", "dict")

    def __init__(self, min_confidence: float = 0.85):
        """
        初始化处理器

        Args:
            min_confidence: 最低可接受置信度，低于此值需要复核
        """
        self.min_confidence = min_confidence

    def process(self, content: str, output_format: str = "json") -> ProcessedItem:
        """
        处理单条输入

        Args:
            content: 用户输入的内容
            output_format: 输出格式（json/text/dict）

        Returns:
            ProcessedItem: 处理结果

        Raises:
            ValueError: 输入为空或格式不支持
        """
        # 输入校验
        if not content or not content.strip():
            raise ValueError("E001: 输入为空")

        if output_format not in self._SUPPORTED_FORMATS:
            raise ValueError(f"E008: 不支持的输出格式: {output_format}")

        # 提取关键字段
        key_fields = self._extract_key_fields(content)

        # 计算置信度
        confidence, uncertain = self._evaluate_confidence(content, key_fields)

        # 构建结果
        item = ProcessedItem(
            original=content,
            key_fields=key_fields,
            confidence=confidence,
            needs_review=confidence < self.min_confidence,
            uncertain_points=uncertain,
        )

        # 格式转换
        if output_format == "json":
            return self._to_json(item)
        elif output_format == "text":
            return self._to_text(item)
        else:
            return item

    def process_batch(self, contents: List[str], output_format: str = "json") -> BatchResult:
        """
        批量处理多个输入

        Args:
            contents: 输入内容列表
            output_format: 输出格式

        Returns:
            BatchResult: 批量处理结果
        """
        result = BatchResult()

        for idx, content in enumerate(contents):
            try:
                item = self.process(content, output_format)
                result.items.append(item)
                result.success_count += 1
            except ValueError as e:
                # 解析错误码
                code = str(e).split(":")[0] if ":" in str(e) else "E007"
                result.error_codes.append(code)
                result.error_count += 1
                # 记录错误项
                result.items.append(ProcessedItem(
                    original=content,
                    status="error",
                    uncertain_points=[str(e)]
                ))

        return result

    def _extract_key_fields(self, content: str) -> Dict[str, Any]:
        """提取内容中的关键字段（宽松匹配）"""
        fields: Dict[str, Any] = {}

        for field_name, pattern in self._FIELD_PATTERNS.items():
            matches = re.findall(pattern, content, re.IGNORECASE)
            if matches:
                # 取第一个匹配作为值，多个匹配则存列表
                if len(matches) == 1:
                    fields[field_name] = matches[0]
                else:
                    fields[field_name] = list(matches)

        # 尝试识别结构化数据（JSON）
        if content.strip().startswith(("{", "[")):
            try:
                parsed = json.loads(content)
                if isinstance(parsed, dict):
                    fields["structured_data"] = parsed
                elif isinstance(parsed, list):
                    fields["structured_list"] = parsed
            except json.JSONDecodeError:
                # 不是合法 JSON，忽略
                pass

        return fields

    def _evaluate_confidence(self, content: str, key_fields: Dict[str, Any]) -> Tuple[float, List[str]]:
        """
        评估处理结果的置信度

        规则：
        - 基础置信度 0.5
        - 每提取到一个关键字段 +0.1
        - 内容长度 > 20 字符 +0.1
        - 内容包含结构化数据 +0.1
        - 内容包含不确定词汇则 -0.1

        Returns:
            (置信度, 不确定点列表)
        """
        confidence = 0.5
        uncertain_points = []

        # 关键字段奖励
        field_count = len(key_fields)
        confidence += min(field_count * 0.1, 0.3)  # 最多加 0.3

        # 内容长度奖励
        if len(content.strip()) > 20:
            confidence += 0.1

        # 结构化数据奖励
        if "structured_data" in key_fields or "structured_list" in key_fields:
            confidence += 0.1

        # 不确定词汇惩罚
        uncertain_words = ["可能", "大概", "也许", "不确定", "maybe", "perhaps", "unknown"]
        for word in uncertain_words:
            if word.lower() in content.lower():
                confidence -= 0.1
                uncertain_points.append(f"包含不确定词汇: {word}")

        # 限制在 0~1 范围
        confidence = max(0.0, min(1.0, confidence))

        # 如果置信度过低，添加说明
        if confidence < self.min_confidence:
            uncertain_points.append("整体置信度偏低，建议人工复核")

        return confidence, uncertain_points

    def _to_json(self, item: ProcessedItem) -> ProcessedItem:
        """转换为 JSON 兼容结构"""
        # 为 JSON 序列化做准备
        item.key_fields = self._make_serializable(item.key_fields)
        return item

    def _to_text(self, item: ProcessedItem) -> ProcessedItem:
        """转换为文本友好结构"""
        # 文本格式的字段简化
        simplified = {}
        for k, v in item.key_fields.items():
            if isinstance(v, (dict, list)):
                simplified[k] = json.dumps(v, ensure_ascii=False)[:100]
            else:
                simplified[k] = str(v)
        item.key_fields = simplified
        return item

    @staticmethod
    def _make_serializable(obj: Any) -> Any:
        """确保对象可 JSON 序列化"""
        if isinstance(obj, dict):
            return {k: ContentProcessor._make_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [ContentProcessor._make_serializable(v) for v in obj]
        elif isinstance(obj, (str, int, float, bool, type(None))):
            return obj
        else:
            return str(obj)


# ---------------------------------------------------------------------------
# 输出格式化
# ---------------------------------------------------------------------------

def format_output(result: Any, output_format: str = "json") -> str:
    """
    将处理结果格式化为字符串输出

    Args:
        result: 处理结果（ProcessedItem 或 BatchResult）
        output_format: 输出格式

    Returns:
        格式化的字符串
    """
    if output_format == "json":
        return json.dumps(asdict(result), ensure_ascii=False, indent=2, default=str)
    else:
        # 文本格式
        lines = []
        if isinstance(result, ProcessedItem):
            lines.append(f"原始输入: {result.original}")
            lines.append(f"置信度: {result.confidence:.1%}")
            lines.append(f"需要复核: {'是' if result.needs_review else '否'}")
            if result.key_fields:
                lines.append("关键字段:")
                for k, v in result.key_fields.items():
                    lines.append(f"  {k}: {v}")
            if result.uncertain_points:
                lines.append("不确定点:")
                for p in result.uncertain_points:
                    lines.append(f"  - {p}")
        elif isinstance(result, BatchResult):
            lines.append(f"批量处理完成: 成功 {result.success_count}, 失败 {result.error_count}")
            if result.error_codes:
                lines.append(f"错误码: {', '.join(result.error_codes)}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# 自测模块
# ---------------------------------------------------------------------------

def run_selftest() -> int:
    """
    内置自检：使用硬编码样例数据验证核心逻辑。
    不读取外部文件，不依赖工作目录，不访问网络。

    Returns:
        0 表示成功，非 0 表示失败
    """
    print("开始自检 (--selftest)...")

    processor = ContentProcessor()

    # 测试用例 1: 正常输入，包含多种关键字段
    test1 = "联系人: test@example.com, 电话: 138-1234-5678, 网址: https://example.com"
    try:
        result1 = processor.process(test1, "json")
        # 宽松断言：置信度应大于 0.5（基础值）
        assert result1.confidence > 0.5, f"测试1失败: 置信度应 > 0.5, 实际 {result1.confidence}"
        # 应提取到至少 2 个关键字段
        assert len(result1.key_fields) >= 2, f"测试1失败: 应提取至少2个字段, 实际 {len(result1.key_fields)}"
        print(f"  ✓ 测试1通过: 置信度 {result1.confidence:.1%}, 字段数 {len(result1.key_fields)}")
    except Exception as e:
        print(f"  ✗ 测试1失败: {e}")
        return 1

    # 测试用例 2: 空输入，应触发 E001
    try:
        processor.process("", "json")
        print("  ✗ 测试2失败: 空输入应抛出异常")
        return 1
    except ValueError as e:
        assert "E001" in str(e), f"测试2失败: 错误码应为 E001, 实际 {e}"
        print("  ✓ 测试2通过: 正确拒绝空输入")

    # 测试用例 3: 批量处理，包含正常和异常输入
    batch_inputs = [
        "项目预算: $5000, 截止日期: 2026-12-31",
        "",  # 空输入，应失败
        "联系邮箱: user@domain.org",
    ]
    batch_result = processor.process_batch(batch_inputs, "json")
    # 宽松断言：应至少有 1 个成功
    assert batch_result.success_count >= 1, f"测试3失败: 应至少1个成功, 实际 {batch_result.success_count}"
    # 应至少有 1 个失败（空输入）
    assert batch_result.error_count >= 1, f"测试3失败: 应至少1个失败, 实际 {batch_result.error_count}"
    print(f"  ✓ 测试3通过: 成功 {batch_result.success_count}, 失败 {batch_result.error_count}")

    # 测试用例 4: JSON 输入解析
    test4 = '{"name": "测试项目", "budget": 10000, "owner": "张三"}'
    try:
        result4 = processor.process(test4, "dict")
        # 应能识别结构化数据
        assert "structured_data" in result4.key_fields, "测试4失败: 应识别结构化数据"
        # 置信度应较高
        assert result4.confidence >= 0.7, f"测试4失败: 置信度应 >= 0.7, 实际 {result4.confidence}"
        print(f"  ✓ 测试4通过: 结构化数据识别成功, 置信度 {result4.confidence:.1%}")
    except Exception as e:
        print(f"  ✗ 测试4失败: {e}")
        return 1

    # 测试用例 5: 边界处理 - 极短输入
    test5 = "你好"
    try:
        result5 = processor.process(test5, "json")
        # 短输入置信度应较低（不高于 0.6）
        assert result5.confidence <= 0.6, f"测试5失败: 短输入置信度应 <= 0.6, 实际 {result5.confidence}"
        print(f"  ✓ 测试5通过: 短输入处理正常, 置信度 {result5.confidence:.1%}")
    except Exception as e:
        print(f"  ✗ 测试5失败: {e}")
        return 1

    # 测试用例 6: 格式输出验证
    try:
        test6 = processor.process("联系电话: 010-12345678", "json")
        json_str = format_output(test6, "json")
        # 验证能解析为 JSON
        parsed = json.loads(json_str)
        assert "original" in parsed, "测试6失败: JSON 应包含 original 字段"
        assert "confidence" in parsed, "测试6失败: JSON 应包含 confidence 字段"
        print("  ✓ 测试6通过: JSON 输出格式正确")
    except Exception as e:
        print(f"  ✗ 测试6失败: {e}")
        return 1

    # 测试用例 7: 不确定词汇识别
    test7 = "这个可能是个邮箱: test@test.com"
    try:
        result7 = processor.process(test7, "json")
        # 应识别出不确定点
        assert len(result7.uncertain_points) >= 1, "测试7失败: 应识别出不确定词汇"
        # 置信度应低于无不确定词汇的情况
        assert result7.confidence < 0.9, f"测试7失败: 置信度应 < 0.9, 实际 {result7.confidence}"
        print(f"  ✓ 测试7通过: 不确定词汇识别成功, 置信度 {result7.confidence:.1%}")
    except Exception as e:
        print(f"  ✗ 测试7失败: {e}")
        return 1

    # 测试用例 8: 错误码体系验证
    try:
        processor.process("", "json")
        print("  ✗ 测试8失败: 应抛出 E001")
        return 1
    except ValueError as e:
        assert "E001" in str(e), f"测试8失败: 错误码应为 E001"
        print("  ✓ 测试8通过: E001 错误码正确")

    try:
        processor.process("测试内容", "xml")  # 不支持的格式
        print("  ✗ 测试8失败: 应抛出 E008")
        return 1
    except ValueError as e:
        assert "E008" in str(e), f"测试8失败: 错误码应为 E008, 实际 {e}"
        print("  ✓ 测试8通过: E008 错误码正确")

    print("\n所有自检通过！")
    return 0


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------

def main() -> int:
    """
    命令行主入口

    Returns:
        退出码（0 成功，非 0 失败）
    """
    parser = argparse.ArgumentParser(
        description="awesome-llm-apps 技能工具 - 将输入内容转换为结构化结果",
        epilog="示例: python main.py '联系人: test@example.com' --format json"
    )
    parser.add_argument(
        "input",
        nargs="?",
        help="待处理的内容（不提供则进入交互模式）"
    )
    parser.add_argument(
        "--format",
        choices=["json", "text"],
        default="json",
        help="输出格式 (默认: json)"
    )
    parser.add_argument(
        "--batch",
        nargs="*",
        help="批量处理多个输入（空格分隔）"
    )
    parser.add_argument(
        "--min-confidence",
        type=float,
        default=0.85,
        help="最低置信度阈值 (默认: 0.85)"
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检并退出"
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        return run_selftest()

    # 初始化处理器
    processor = ContentProcessor(min_confidence=args.min_confidence)

    # 批量模式
    if args.batch:
        if not args.batch:
            print("错误: --batch 模式需要至少一个输入参数", file=sys.stderr)
            return 1
        result = processor.process_batch(args.batch, args.format)
        print(format_output(result, args.format))
        return 0 if result.error_count == 0 else 1

    # 单条输入模式
    if args.input:
        try:
            result = processor.process(args.input, args.format)
            print(format_output(result, args.format))
            return 0
        except ValueError as e:
            print(f"错误: {e}", file=sys.stderr)
            return 1

    # 交互模式
    print("请输入要处理的内容（输入 'exit' 退出，'batch' 进入批量模式）:")
    try:
        while True:
            line = input("> ").strip()
            if line.lower() == "exit":
                break
            if line.lower() == "batch":
                print("批量模式：每行一个输入，空行结束")
                batch_lines = []
                while True:
                    batch_line = input(">> ").strip()
                    if not batch_line:
                        break
                    batch_lines.append(batch_line)
                if batch_lines:
                    result = processor.process_batch(batch_lines, args.format)
                    print(format_output(result, args.format))
                continue
            if not line:
                print("错误: E001 输入为空", file=sys.stderr)
                continue
            try:
                result = processor.process(line, args.format)
                print(format_output(result, args.format))
            except ValueError as e:
                print(f"错误: {e}", file=sys.stderr)
    except (KeyboardInterrupt, EOFError):
        print("\n退出")

    return 0


if __name__ == "__main__":
    sys.exit(main())
