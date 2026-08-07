#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
脚本名称: scripts/main.py
功能描述: SEO文案 / AI Blog Article Generator 的独立实现脚本。

设计原则（Clean Room）:
- 仅依据功能规格文档进行独立实现，不参考任何既有代码。
- 标准库优先，不依赖第三方库。
- 提供 --selftest 参数进行离线自检，不访问网络、不读取外部文件。
"""

import argparse
import json
import sys
import re
from collections import OrderedDict


# ---------------------------------------------------------------------------
# 常量定义
# ---------------------------------------------------------------------------
# 错误码及对应话术（依据规格文档）
ERROR_MESSAGES = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：...",
    "E003": "输入格式不符合要求，示例：...",
    "E004": "这超出了本工具的能力范围，建议...",
    "E005": "结果无法确定，建议：...",
    "E006": "内部处理异常，请稍后重试。",
    "E007": "参数解析失败，请检查命令行参数。",
    "E008": "输出序列化失败，请检查输出格式。",
    "E009": "自检流程异常，请检查代码逻辑。",
    "E010": "未知错误，请联系开发者。",
}

# 触发词表（依据规格文档）
TRIGGER_WORDS = ["SEO文案", "ai blog article generator"]

# 置信度阈值（依据规格文档）
HIGH_CONFIDENCE_THRESHOLD = 90
MEDIUM_CONFIDENCE_THRESHOLD = 85


# ---------------------------------------------------------------------------
# 核心工具类
# ---------------------------------------------------------------------------
class ArticleGenerator:
    """
    SEO文案生成器核心逻辑类。
    负责解析输入、组织输出、计算置信度。
    """

    def __init__(self):
        """初始化生成器，设置默认模板。"""
        # 默认输出模板（仅作示例结构，实际内容由输入决定）
        self.output_template = OrderedDict([
            ("title", ""),
            ("summary", ""),
            ("keywords", []),
            ("content", ""),
            ("confidence", 0),
            ("needs_review", False),
            ("uncertain_points", []),
        ])

    def parse_input(self, raw_input):
        """
        解析输入内容，识别关键信息。

        参数:
            raw_input: 用户提供的原始输入（字符串）

        返回:
            dict: 解析后的结构化信息

        异常:
            ValueError: 当输入为空或格式错误时抛出
        """
        # 检查输入是否为空
        if not raw_input or not raw_input.strip():
            raise ValueError("E001")

        # 检查输入是否为字符串类型
        if not isinstance(raw_input, str):
            raise ValueError("E003")

        # 尝试解析 JSON 格式输入
        try:
            # 尝试解析为 JSON
            parsed_data = json.loads(raw_input, object_pairs_hook=OrderedDict)
            if isinstance(parsed_data, dict):
                # 提取关键字段
                result = self._extract_from_dict(parsed_data)
            else:
                # 非字典类型，按文本处理
                result = self._extract_from_text(raw_input)
        except json.JSONDecodeError:
            # 非 JSON 格式，按纯文本处理
            result = self._extract_from_text(raw_input)

        # 检查是否提取到关键信息
        if not result.get("key_fields"):
            raise ValueError("E002")

        return result

    def _extract_from_dict(self, data_dict):
        """
        从字典中提取关键信息。

        参数:
            data_dict: 解析后的字典数据

        返回:
            dict: 提取的结构化信息
        """
        result = {
            "key_fields": {},
            "raw_text": json.dumps(data_dict, ensure_ascii=False),
            "source_type": "structured_data",
        }

        # 常见字段名映射（中英文兼容）
        field_mappings = {
            "标题": "title",
            "title": "title",
            "摘要": "summary",
            "summary": "summary",
            "关键词": "keywords",
            "keywords": "keywords",
            "内容": "content",
            "content": "content",
        }

        # 遍历字典，提取已知字段
        for key, value in data_dict.items():
            normalized_key = field_mappings.get(key, key)
            if normalized_key in ["title", "summary", "content"]:
                result["key_fields"][normalized_key] = str(value)
            elif normalized_key == "keywords":
                if isinstance(value, list):
                    result["key_fields"]["keywords"] = [str(kw) for kw in value]
                else:
                    result["key_fields"]["keywords"] = [str(value)]

        # 如果没有任何已知字段，尝试提取所有字符串值
        if not result["key_fields"]:
            for key, value in data_dict.items():
                if isinstance(value, str) and value.strip():
                    result["key_fields"][key] = value

        return result

    def _extract_from_text(self, text):
        """
        从纯文本中提取关键信息。

        参数:
            text: 原始文本

        返回:
            dict: 提取的结构化信息
        """
        result = {
            "key_fields": {},
            "raw_text": text,
            "source_type": "plain_text",
        }

        # 按段落分割
        paragraphs = [p.strip() for p in text.split("\n") if p.strip()]

        if not paragraphs:
            return result

        # 第一段作为标题（如果长度合适）
        first_para = paragraphs[0]
        if len(first_para) <= 100:
            result["key_fields"]["title"] = first_para
            if len(paragraphs) > 1:
                result["key_fields"]["content"] = "\n".join(paragraphs[1:])
            else:
                result["key_fields"]["content"] = first_para
        else:
            result["key_fields"]["content"] = text

        # 提取可能的标题（# 开头）
        title_match = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
        if title_match:
            result["key_fields"]["title"] = title_match.group(1).strip()

        # 提取关键词（逗号分隔）
        keyword_match = re.search(r"关键词[:：]\s*(.+)", text)
        if keyword_match:
            keywords = [kw.strip() for kw in keyword_match.group(1).split("，")]
            result["key_fields"]["keywords"] = keywords

        return result

    def generate(self, parsed_input):
        """
        根据解析结果生成结构化输出。

        参数:
            parsed_input: parse_input 方法的返回值

        返回:
            dict: 符合输出模板的结果
        """
        output = OrderedDict(self.output_template)

        key_fields = parsed_input["key_fields"]

        # 填充标题
        output["title"] = key_fields.get("title", "未命名文章")

        # 填充摘要
        output["summary"] = key_fields.get("summary", "")

        # 填充关键词
        output["keywords"] = key_fields.get("keywords", [])

        # 填充内容
        content = key_fields.get("content", "")
        if not content and "summary" in key_fields:
            content = key_fields["summary"]
        output["content"] = content

        # 计算置信度
        confidence, uncertain_points = self._calculate_confidence(parsed_input)
        output["confidence"] = confidence

        # 根据置信度设置复核标记
        if confidence >= HIGH_CONFIDENCE_THRESHOLD:
            output["needs_review"] = False
        elif confidence >= MEDIUM_CONFIDENCE_THRESHOLD:
            output["needs_review"] = True
            uncertain_points.append("置信度在85%-90%之间，建议复核")
        else:
            output["needs_review"] = True
            uncertain_points.append("置信度低于85%，结果不确定")

        output["uncertain_points"] = uncertain_points

        return output

    def _calculate_confidence(self, parsed_input):
        """
        计算结果置信度。

        参数:
            parsed_input: 解析后的输入信息

        返回:
            tuple: (置信度数值, 不确定点列表)
        """
        key_fields = parsed_input["key_fields"]
        uncertain_points = []

        # 基础置信度
        confidence = 70

        # 根据字段完整度加分
        if "title" in key_fields:
            confidence += 10
        if "content" in key_fields:
            confidence += 10
        if "keywords" in key_fields:
            confidence += 5
        if "summary" in key_fields:
            confidence += 5

        # 根据内容长度调整
        content_length = len(key_fields.get("content", ""))
        if content_length > 500:
            confidence += 5
        elif content_length < 50:
            uncertain_points.append("内容较短，可能信息不完整")

        # 根据来源类型调整
        if parsed_input["source_type"] == "structured_data":
            confidence += 5
        else:
            uncertain_points.append("输入为纯文本，可能存在解析误差")

        # 检查是否有明确的关键词
        if not key_fields.get("keywords"):
            uncertain_points.append("未提取到明确的关键词")

        # 限制在合理范围内
        confidence = max(0, min(100, confidence))

        return confidence, uncertain_points

    def format_output(self, result, output_format="json"):
        """
        将结果格式化为指定格式。

        参数:
            result: generate 方法的返回值
            output_format: 输出格式（json 或 text）

        返回:
            str: 格式化后的输出字符串

        异常:
            ValueError: 当输出格式不支持时抛出
        """
        if output_format == "json":
            try:
                return json.dumps(result, ensure_ascii=False, indent=2)
            except (TypeError, ValueError):
                raise ValueError("E008")
        elif output_format == "text":
            lines = []
            lines.append(f"标题: {result['title']}")
            lines.append(f"摘要: {result['summary']}")
            lines.append(f"关键词: {', '.join(result['keywords'])}")
            lines.append(f"置信度: {result['confidence']}%")
            if result["needs_review"]:
                lines.append("复核建议: 建议复核")
            if result["uncertain_points"]:
                lines.append("不确定点:")
                for point in result["uncertain_points"]:
                    lines.append(f"  - {point}")
            lines.append("---")
            lines.append(result["content"])
            return "\n".join(lines)
        else:
            raise ValueError("E003")

    def process(self, raw_input, output_format="json"):
        """
        完整处理流程：解析 -> 生成 -> 格式化。

        参数:
            raw_input: 原始输入
            output_format: 输出格式

        返回:
            str: 最终输出结果
        """
        try:
            # 步骤1: 解析输入
            parsed = self.parse_input(raw_input)

            # 步骤2: 生成结果
            result = self.generate(parsed)

            # 步骤3: 格式化输出
            return self.format_output(result, output_format)

        except ValueError as e:
            error_code = str(e)
            error_msg = ERROR_MESSAGES.get(error_code, ERROR_MESSAGES["E010"])
            return json.dumps({
                "error": error_code,
                "message": error_msg,
            }, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# 自检模块
# ---------------------------------------------------------------------------
def run_selftest():
    """
    运行内置自检样例，验证核心逻辑。

    使用硬编码的测试数据，不依赖外部文件或网络。

    返回:
        bool: 自检是否通过
    """
    print("=" * 60)
    print("开始自检 (Self-Test)")
    print("=" * 60)

    generator = ArticleGenerator()
    test_cases = []

    # 测试用例1: JSON 结构化输入
    test_cases.append({
        "name": "JSON结构化输入",
        "input": json.dumps({
            "标题": "Python 异步编程入门",
            "摘要": "本文介绍 Python 异步编程的基础概念和最佳实践",
            "关键词": ["异步", "协程", "Python"],
            "内容": "异步编程是现代 Python 开发的重要技能。本文将深入探讨协程、事件循环等核心概念。"
        }, ensure_ascii=False),
        "expected_source": "structured_data",
    })

    # 测试用例2: Markdown 文本输入
    test_cases.append({
        "name": "Markdown文本输入",
        "input": "# 机器学习基础\n\n机器学习是人工智能的核心领域。\n\n关键词：监督学习，无监督学习",
        "expected_source": "plain_text",
    })

    # 测试用例3: 简单文本输入
    test_cases.append({
        "name": "简单文本输入",
        "input": "这是一篇关于数据科学的文章，讨论了数据清洗、特征工程和模型评估等重要话题。",
        "expected_source": "plain_text",
    })

    # 测试用例4: 空输入（应返回错误）
    test_cases.append({
        "name": "空输入错误处理",
        "input": "",
        "expect_error": True,
    })

    # 测试用例5: 带标题和内容的混合输入
    test_cases.append({
        "name": "混合输入",
        "input": "标题：Web开发最佳实践\n\n内容：本文总结 Web 开发中的最佳实践，包括前端优化、后端架构和数据库设计。",
        "expected_source": "plain_text",
    })

    all_passed = True

    for i, test_case in enumerate(test_cases, 1):
        print(f"\n测试用例 {i}: {test_case['name']}")
        print(f"  输入: {test_case['input'][:50]}...")

        try:
            # 解析输入
            parsed = generator.parse_input(test_case["input"])

            # 检查是否期待错误
            if test_case.get("expect_error", False):
                print("  [失败] 预期抛出错误，但成功解析了输入")
                all_passed = False
                continue

            # 验证来源类型
            if "expected_source" in test_case:
                if parsed["source_type"] != test_case["expected_source"]:
                    print(f"  [失败] 来源类型不匹配: 期望 {test_case['expected_source']}, 实际 {parsed['source_type']}")
                    all_passed = False
                    continue

            # 验证关键字段
            if not parsed["key_fields"]:
                print("  [失败] 未提取到任何关键字段")
                all_passed = False
                continue

            # 生成结果
            result = generator.generate(parsed)

            # 验证结果结构
            required_fields = ["title", "summary", "keywords", "content", "confidence"]
            for field in required_fields:
                if field not in result:
                    print(f"  [失败] 结果缺少字段: {field}")
                    all_passed = False
                    break

            # 验证置信度范围（宽松验证）
            if not (0 <= result["confidence"] <= 100):
                print(f"  [失败] 置信度超出范围: {result['confidence']}")
                all_passed = False

            # 验证内容非空（宽松验证）
            if not result["content"]:
                print("  [失败] 生成内容为空")
                all_passed = False

            # 验证关键词非空（宽松验证）
            if not result["keywords"]:
                print("  [警告] 未提取到关键词（不视为失败）")

            # 验证输出格式（宽松验证）
            output_json = generator.format_output(result, "json")
            if not output_json:
                print("  [失败] JSON 输出为空")
                all_passed = False
            else:
                # 验证 JSON 可解析
                parsed_output = json.loads(output_json)
                if not isinstance(parsed_output, dict):
                    print("  [失败] JSON 输出格式错误")
                    all_passed = False

            if all_passed:
                print(f"  [通过] 置信度: {result['confidence']}%, 内容长度: {len(result['content'])}")

        except ValueError as e:
            error_code = str(e)
            if test_case.get("expect_error", False):
                print(f"  [通过] 正确抛出错误: {error_code} - {ERROR_MESSAGES.get(error_code, '未知错误')}")
            else:
                print(f"  [失败] 意外抛出错误: {error_code} - {ERROR_MESSAGES.get(error_code, '未知错误')}")
                all_passed = False
        except Exception as e:
            print(f"  [失败] 未预期异常: {e}")
            all_passed = False

    # 测试错误处理
    print("\n测试错误处理:")
    error_cases = [
        ("", "E001"),
        (None, "E001"),
        ("   ", "E001"),
    ]

    for input_val, expected_error in error_cases:
        try:
            generator.parse_input(input_val)
            print(f"  [失败] 输入 '{input_val}' 未抛错")
            all_passed = False
        except ValueError as e:
            if str(e) == expected_error:
                print(f"  [通过] 正确抛出 {expected_error}")
            else:
                print(f"  [失败] 期望 {expected_error}, 实际 {e}")
                all_passed = False

    # 测试完整流程
    print("\n测试完整流程:")
    test_input = "标题：测试文章\n\n内容：这是一篇测试文章的内容，用于验证完整处理流程。"
    try:
        result = generator.process(test_input)
        parsed_result = json.loads(result)
        if "error" in parsed_result:
            print(f"  [失败] 完整流程处理失败: {parsed_result['error']}")
            all_passed = False
        else:
            print(f"  [通过] 完整流程成功，置信度: {parsed_result['confidence']}%")
    except Exception as e:
        print(f"  [失败] 完整流程异常: {e}")
        all_passed = False

    print("\n" + "=" * 60)
    if all_passed:
        print("自检结果: 全部通过 ✓")
    else:
        print("自检结果: 存在失败项 ✗")
    print("=" * 60)

    return all_passed


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------
def main():
    """
    命令行主入口函数。
    """
    parser = argparse.ArgumentParser(
        description="SEO文案生成器 - 基于功能规格的独立实现",
        epilog="示例: python main.py --input '标题：测试' --format json"
    )

    parser.add_argument(
        "--input", "-i",
        type=str,
        help="待处理的内容（数据/文本/JSON字符串）"
    )

    parser.add_argument(
        "--format", "-f",
        type=str,
        choices=["json", "text"],
        default="json",
        help="输出格式 (默认: json)"
    )

    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检，验证核心逻辑"
    )

    parser.add_argument(
        "--version",
        action="version",
        version="SEO文案生成器 v1.0.0 (Clean Room Implementation)"
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        success = run_selftest()
        sys.exit(0 if success else 1)

    # 正常处理模式
    if not args.input:
        # 尝试从标准输入读取
        if not sys.stdin.isatty():
            args.input = sys.stdin.read().strip()

    if not args.input:
        print(json.dumps({
            "error": "E001",
            "message": ERROR_MESSAGES["E001"]
        }, ensure_ascii=False, indent=2))
        sys.exit(1)

    # 创建生成器并处理输入
    generator = ArticleGenerator()
    output = generator.process(args.input, args.format)

    # 输出结果
    print(output)

    # 检查是否包含错误
    try:
        if args.format == "json":
            result = json.loads(output)
            if "error" in result:
                sys.exit(1)
    except json.JSONDecodeError:
        pass

    sys.exit(0)


if __name__ == "__main__":
    main()
