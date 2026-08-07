#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
self-learning-skills 工具实现脚本
==================================
一个自改进技能工具，用于：
- 将用户提供的数据/文件/URL 转换为结构化结果
- 识别并保留输入中的关键信息
- 按约定格式生成输出
- 对不确定项给出置信度提示
- 支持批量处理和自定义格式

仅依据功能规格独立实现（clean-room）。
"""

import argparse
import json
import os
import re
import sys
import urllib.parse
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# 错误码定义
# ---------------------------------------------------------------------------
ERROR_CODES = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：",
    "E003": "输入格式不符合要求，示例：",
    "E004": "这超出了本工具的能力范围，建议：",
    "E005": "结果无法确定，建议：",
    "E006": "文件读取失败，请检查文件路径和权限",
    "E007": "URL 解析失败，请输入合法的 URL",
    "E008": "批量处理输入格式错误，应为列表",
    "E009": "输出格式不受支持，支持格式：json/text",
    "E010": "内部处理逻辑错误，请联系开发者",
}


# ---------------------------------------------------------------------------
# 数据模型
# ---------------------------------------------------------------------------
@dataclass
class ProcessedItem:
    """单个输入的处理结果"""
    raw_input: str
    extracted_fields: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0
    warnings: List[str] = field(default_factory=list)
    needs_review: bool = False


@dataclass
class ProcessingResult:
    """批量处理的结果集合"""
    items: List[ProcessedItem] = field(default_factory=list)
    overall_confidence: float = 0.0
    warnings: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# 核心处理引擎
# ---------------------------------------------------------------------------
class SkillEngine:
    """核心处理引擎，负责解析、识别、结构化"""

    # 常见关键字段的正则模式（用于识别输入中的关键信息）
    FIELD_PATTERNS = {
        "email": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
        "phone": r"(\+?\d{1,3}[-.]?)?\(?\d{2,4}\)?[-.]?\d{3,4}[-.]?\d{3,4}",
        "url": r"https?://[^\s]+",
        "date": r"\d{4}[-/]\d{1,2}[-/]\d{1,2}",
        "ip": r"\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b",
    }

    def __init__(self, custom_fields: Optional[Dict[str, str]] = None):
        """
        初始化引擎
        
        Args:
            custom_fields: 自定义字段的正则模式字典，格式: {"字段名": "正则表达式"}
        """
        self.field_patterns = self.FIELD_PATTERNS.copy()
        if custom_fields:
            self.field_patterns.update(custom_fields)

    # ------------------------------------------------------------------
    # 输入解析
    # ------------------------------------------------------------------
    def parse_input(self, raw_input: str) -> Tuple[Dict[str, Any], float, List[str]]:
        """
        解析输入内容，识别关键信息
        
        Returns:
            (提取的字段字典, 置信度, 警告列表)
        """
        warnings: List[str] = []
        extracted: Dict[str, Any] = {}

        if not raw_input or not raw_input.strip():
            raise ValueError("E001")

        # 尝试解析 JSON 格式输入
        try:
            data = json.loads(raw_input)
            if isinstance(data, dict):
                extracted = {k: v for k, v in data.items() if v is not None}
            elif isinstance(data, list):
                extracted = {"items": data}
            else:
                extracted = {"value": data}
            confidence = 0.95
            return extracted, confidence, warnings
        except (json.JSONDecodeError, ValueError):
            pass

        # 尝试解析 URL 格式输入
        if self._looks_like_url(raw_input):
            try:
                parsed = urllib.parse.urlparse(raw_input)
                if parsed.scheme and parsed.netloc:
                    extracted = {
                        "url": raw_input,
                        "scheme": parsed.scheme,
                        "domain": parsed.netloc,
                        "path": parsed.path or "/",
                    }
                    confidence = 0.92
                    return extracted, confidence, warnings
            except Exception:
                raise ValueError("E007")

        # 尝试解析文件路径输入
        if self._looks_like_file_path(raw_input):
            if os.path.isfile(raw_input):
                try:
                    with open(raw_input, "r", encoding="utf-8") as f:
                        content = f.read()
                    extracted = {
                        "file_path": raw_input,
                        "file_name": os.path.basename(raw_input),
                        "file_size": os.path.getsize(raw_input),
                        "content_preview": content[:200],
                    }
                    confidence = 0.90
                    return extracted, confidence, warnings
                except (IOError, OSError):
                    raise ValueError("E006")
            else:
                warnings.append("文件路径存在但无法读取，已按文本处理")

        # 普通文本：识别关键字段
        extracted = self._extract_fields_from_text(raw_input)
        confidence = self._calculate_confidence(extracted, raw_input)

        if confidence < 0.85:
            warnings.append("输入内容较模糊，识别结果置信度较低")

        return extracted, confidence, warnings

    def _looks_like_url(self, text: str) -> bool:
        """判断是否为 URL 格式"""
        return bool(re.match(r"^https?://", text.strip()))

    def _looks_like_file_path(self, text: str) -> bool:
        """判断是否为文件路径格式"""
        return bool(re.match(r"^[\w/\\:.~-]+\.\w+$", text.strip())) and (
            os.path.sep in text or "/" in text
        )

    def _extract_fields_from_text(self, text: str) -> Dict[str, Any]:
        """从普通文本中提取关键字段"""
        extracted: Dict[str, Any] = {}
        text_lower = text.lower()

        # 按预定义模式提取
        for field_name, pattern in self.field_patterns.items():
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                unique_matches = list(set(matches))
                extracted[field_name] = (
                    unique_matches[0] if len(unique_matches) == 1 else unique_matches
                )

        # 检测意图关键词
        intent_keywords = {
            "convert": ["convert", "转换", "转成", "变成"],
            "summarize": ["summar", "总结", "摘要", "概括"],
            "extract": ["extract", "提取", "抽取", "解析"],
            "batch": ["batch", "批量", "多个", "一堆"],
        }

        detected_intents = []
        for intent, keywords in intent_keywords.items():
            if any(kw in text_lower for kw in keywords):
                detected_intents.append(intent)

        if detected_intents:
            extracted["intent"] = detected_intents

        # 检测语言
        if re.search(r"[\u4e00-\u9fff]", text):
            extracted["language"] = "zh"
        else:
            extracted["language"] = "en"

        return extracted

    def _calculate_confidence(self, extracted: Dict[str, Any], raw_input: str) -> float:
        """
        计算置信度：
        - 提取到关键字段数量越多，置信度越高
        - 有明确意图关键词，置信度提升
        - 输入长度过短，置信度降低
        """
        confidence = 0.5  # 基础置信度

        # 字段数量加分
        field_count = len(extracted)
        confidence += min(field_count * 0.1, 0.3)

        # 意图明确加分
        if "intent" in extracted:
            confidence += 0.1

        # 输入长度影响
        input_len = len(raw_input.strip())
        if input_len > 100:
            confidence += 0.1
        elif input_len < 20:
            confidence -= 0.1

        # 限制在 0.3 ~ 0.98 之间
        return max(0.3, min(0.98, confidence))

    # ------------------------------------------------------------------
    # 输出生成
    # ------------------------------------------------------------------
    def generate_output(
        self,
        item: ProcessedItem,
        output_format: str = "json",
        template: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        生成输出结果
        
        Args:
            item: 处理结果项
            output_format: 输出格式 (json/text)
            template: 自定义模板，用于指定输出字段结构
            
        Returns:
            格式化后的输出字符串
        """
        # 构建输出数据
        output_data = {
            "input": item.raw_input,
            "extracted": item.extracted_fields,
            "confidence": round(item.confidence, 2),
            "needs_review": item.needs_review,
            "warnings": item.warnings,
        }

        # 应用自定义模板（如果有）
        if template:
            filtered_data = {}
            for field in template:
                if field in item.extracted_fields:
                    filtered_data[field] = item.extracted_fields[field]
                elif field in output_data:
                    filtered_data[field] = output_data[field]
            output_data["extracted"] = filtered_data

        # 添加置信度标注
        if item.confidence >= 0.90:
            output_data["status"] = "直接输出"
        elif item.confidence >= 0.85:
            output_data["status"] = "建议复核"
        else:
            output_data["status"] = "[需核实]"

        # 按格式输出
        if output_format == "json":
            return json.dumps(output_data, ensure_ascii=False, indent=2)
        elif output_format == "text":
            return self._format_as_text(output_data)
        else:
            raise ValueError("E009")

    def _format_as_text(self, data: Dict[str, Any]) -> str:
        """格式化为纯文本输出"""
        lines = []
        lines.append(f"输入: {data['input']}")
        lines.append(f"状态: {data['status']}")
        lines.append(f"置信度: {data['confidence'] * 100:.1f}%")
        lines.append("识别字段:")
        for key, value in data["extracted"].items():
            lines.append(f"  {key}: {value}")
        if data["warnings"]:
            lines.append("警告:")
            for warning in data["warnings"]:
                lines.append(f"  - {warning}")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # 主流程
    # ------------------------------------------------------------------
    def process(
        self,
        inputs: List[str],
        output_format: str = "json",
        template: Optional[Dict[str, Any]] = None,
    ) -> ProcessingResult:
        """
        处理输入列表
        
        Args:
            inputs: 输入内容列表
            output_format: 输出格式
            template: 自定义模板
            
        Returns:
            ProcessingResult 对象
        """
        if not inputs:
            raise ValueError("E001")

        result = ProcessingResult()

        for raw_input in inputs:
            try:
                extracted, confidence, warnings = self.parse_input(raw_input)

                item = ProcessedItem(
                    raw_input=raw_input,
                    extracted_fields=extracted,
                    confidence=confidence,
                    warnings=warnings,
                    needs_review=confidence < 0.85,
                )
                result.items.append(item)

            except ValueError as e:
                # 将错误信息作为警告附加
                error_code = str(e)
                error_msg = ERROR_CODES.get(error_code, str(e))
                item = ProcessedItem(
                    raw_input=raw_input,
                    extracted_fields={"error": error_code},
                    confidence=0.0,
                    warnings=[error_msg],
                    needs_review=True,
                )
                result.items.append(item)

        # 计算整体置信度
        if result.items:
            confidences = [item.confidence for item in result.items if item.confidence > 0]
            result.overall_confidence = (
                sum(confidences) / len(confidences) if confidences else 0.0
            )

        # 汇总警告
        for item in result.items:
            result.warnings.extend(item.warnings)

        return result


# ---------------------------------------------------------------------------
# 自检模块
# ---------------------------------------------------------------------------
def run_selftest() -> bool:
    """
    内置样例数据自检核心逻辑，不依赖外部文件/网络
    
    Returns:
        True 表示自检通过，False 表示失败
    """
    print("=" * 50)
    print("开始自检 (Self-Test)...")
    print("=" * 50)

    engine = SkillEngine()
    test_cases = []

    # 测试用例 1: 包含邮箱和 URL 的文本
    test_cases.append(
        (
            "请帮我提取这个邮箱 test@example.com 和网站 https://github.com 的信息",
            {"email", "url", "intent", "language"},
            0.85,
        )
    )

    # 测试用例 2: JSON 格式输入
    test_cases.append(
        (
            '{"name": "张三", "age": 30, "city": "北京"}',
            {"name", "age", "city"},
            0.9,
        )
    )

    # 测试用例 3: 空输入（应触发 E001）
    test_cases.append(("", set(), 0.0))

    # 测试用例 4: 批量处理
    test_cases.append(
        (
            "批量处理: 第一个 test1@example.com 第二个 test2@example.com",
            {"email", "intent", "language"},
            0.85,
        )
    )

    passed = 0
    failed = 0

    for i, (input_text, expected_fields, min_confidence) in enumerate(test_cases, 1):
        print(f"\n测试用例 {i}: {input_text[:50]}...")
        try:
            extracted, confidence, warnings = engine.parse_input(input_text)

            # 检查字段
            if expected_fields:
                actual_fields = set(extracted.keys())
                missing = expected_fields - actual_fields
                if missing:
                    print(f"  [失败] 缺少字段: {missing}")
                    failed += 1
                    continue

                # 检查置信度
                if confidence < min_confidence:
                    print(f"  [失败] 置信度过低: {confidence:.2f} < {min_confidence}")
                    failed += 1
                    continue
            else:
                # 预期错误情况
                if extracted:
                    print(f"  [失败] 预期错误但成功解析: {extracted}")
                    failed += 1
                    continue

            print(f"  提取字段: {list(extracted.keys())}")
            print(f"  置信度: {confidence:.2f}")
            print(f"  警告: {warnings if warnings else '无'}")
            print("  [通过]")
            passed += 1

        except ValueError as e:
            if str(e) == "E001" and not input_text:
                print(f"  错误码: {e} - 符合预期")
                print("  [通过]")
                passed += 1
            else:
                print(f"  [失败] 意外错误: {e}")
                failed += 1

    # 测试输出生成
    print("\n测试输出生成...")
    test_item = ProcessedItem(
        raw_input="测试输入 test@example.com",
        extracted_fields={"email": "test@example.com", "language": "en"},
        confidence=0.92,
        warnings=[],
        needs_review=False,
    )

    try:
        json_output = engine.generate_output(test_item, "json")
        if '"email"' in json_output and '"confidence"' in json_output:
            print("  JSON 输出格式: [通过]")
            passed += 1
        else:
            print("  JSON 输出格式: [失败]")
            failed += 1
    except Exception as e:
        print(f"  JSON 输出格式: [失败] {e}")
        failed += 1

    try:
        text_output = engine.generate_output(test_item, "text")
        if "输入:" in text_output and "置信度:" in text_output:
            print("  文本输出格式: [通过]")
            passed += 1
        else:
            print("  文本输出格式: [失败]")
            failed += 1
    except Exception as e:
        print(f"  文本输出格式: [失败] {e}")
        failed += 1

    # 测试批量处理
    print("\n测试批量处理...")
    try:
        result = engine.process(
            ["test1@example.com", "test2@example.com", "普通文本没有特殊字段"]
        )
        if len(result.items) == 3:
            print(f"  批量处理 {len(result.items)} 项: [通过]")
            passed += 1
        else:
            print(f"  批量处理项数不符: [失败]")
            failed += 1
    except Exception as e:
        print(f"  批量处理: [失败] {e}")
        failed += 1

    # 测试错误处理
    print("\n测试错误处理...")
    try:
        engine.process([])
        print("  空输入处理: [失败] 未抛出异常")
        failed += 1
    except ValueError as e:
        if str(e) == "E001":
            print("  空输入处理: [通过]")
            passed += 1
        else:
            print(f"  空输入处理: [失败] 错误码不正确: {e}")
            failed += 1

    # 总结
    print("\n" + "=" * 50)
    print(f"自检完成: {passed} 通过, {failed} 失败")
    print("=" * 50)

    return failed == 0


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------
def main() -> int:
    """命令行主入口"""
    parser = argparse.ArgumentParser(
        description="self-learning-skills 工具 - 数据转换与结构化处理",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s --input "提取 test@example.com 的邮箱信息"
  %(prog)s --input "test1@example.com" "test2@example.com" --batch
  %(prog)s --input '{"name": "张三", "age": 30}'
  %(prog)s --selftest
        """,
    )

    parser.add_argument(
        "--input", "-i",
        action="append",
        help="输入内容（可多次指定，或配合 --batch 使用）",
    )
    parser.add_argument(
        "--batch",
        action="store_true",
        help="批量处理模式（将多个 --input 作为独立项处理）",
    )
    parser.add_argument(
        "--output-format",
        "-o",
        choices=["json", "text"],
        default="json",
        help="输出格式 (默认: json)",
    )
    parser.add_argument(
        "--template",
        "-t",
        help="自定义输出模板（JSON 格式，指定要输出的字段列表，如: '[\"email\", \"name\"]'）",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检，验证核心逻辑",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="显示详细警告信息",
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        success = run_selftest()
        return 0 if success else 1

    # 检查输入
    if not args.input:
        print(f"错误 E001: {ERROR_CODES['E001']}", file=sys.stderr)
        return 1

    # 解析模板
    template = None
    if args.template:
        try:
            template = json.loads(args.template)
            if not isinstance(template, list):
                print("错误 E009: 模板格式应为 JSON 数组", file=sys.stderr)
                return 1
        except json.JSONDecodeError:
            print("错误 E009: 模板格式不是合法 JSON", file=sys.stderr)
            return 1

    # 初始化引擎
    engine = SkillEngine()

    try:
        # 处理输入
        if args.batch:
            result = engine.process(args.input, args.output_format, template)
        else:
            # 非批量模式：将所有输入合并为一个
            combined_input = "\n".join(args.input)
            result = engine.process([combined_input], args.output_format, template)

        # 输出结果
        for item in result.items:
            output = engine.generate_output(item, args.output_format, template)
            print(output)

            # 显示警告（verbose 模式）
            if args.verbose and item.warnings:
                print("\n警告:")
                for warning in item.warnings:
                    print(f"  - {warning}")

        # 整体置信度
        print(f"\n整体置信度: {result.overall_confidence * 100:.1f}%")

        return 0

    except ValueError as e:
        error_code = str(e)
        error_msg = ERROR_CODES.get(error_code, str(e))
        print(f"错误 {error_code}: {error_msg}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"错误 E010: 内部错误 - {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
