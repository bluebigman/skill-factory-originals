#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
marketingskills - 营销技能工具（独立实现）

本脚本根据功能规格独立编写，提供以下能力：
1. 将用户提供的数据/文件/URL 转换为结构化结果
2. 识别并保留输入中的关键信息
3. 按约定格式生成输出
4. 对不确定项给出置信度提示
5. 支持批量处理和自定义格式

免责声明：本工具仅供学习与参考，不构成专业建议。
"""

import argparse
import json
import re
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 错误码定义
# ============================================================
ERROR_CODES = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：...",
    "E003": "输入格式不符合要求，示例：...",
    "E004": "这超出了本工具的能力范围，建议...",
    "E005": "结果无法确定，建议：...",
    "E006": "内部处理错误，请重试或检查输入",
    "E007": "批量处理中断，部分结果可能未生成",
    "E008": "输出格式不支持，请选择支持的格式",
    "E009": "置信度计算失败，请检查输入数据",
    "E010": "系统资源不足，请简化输入或稍后重试",
}


class MarketingSkillsError(Exception):
    """自定义异常类，携带错误码"""

    def __init__(self, error_code: str, message: str = ""):
        self.error_code = error_code
        self.message = message or ERROR_CODES.get(error_code, "未知错误")
        super().__init__(f"[{error_code}] {self.message}")


# ============================================================
# 核心数据模型
# ============================================================
class StructuredResult:
    """结构化输出结果"""

    def __init__(
        self,
        content: str,
        fields: Dict[str, Any],
        confidence: float,
        warnings: Optional[List[str]] = None,
    ):
        self.content = content
        self.fields = fields
        self.confidence = confidence
        self.warnings = warnings or []

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "content": self.content,
            "fields": self.fields,
            "confidence": self.confidence,
            "warnings": self.warnings,
            "timestamp": datetime.now().isoformat(),
        }

    def to_json(self) -> str:
        """转换为 JSON 字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


# ============================================================
# 核心处理逻辑
# ============================================================
class MarketingSkillsProcessor:
    """营销技能核心处理器"""

    # 能力边界常量
    MAX_INPUT_LENGTH = 100000  # 最大输入长度
    SUPPORTED_FORMATS = ["json", "table", "text"]  # 支持的输出格式

    def __init__(self):
        self.input_data = None
        self.output_format = "json"
        self.expected_completeness = "detailed"

    def process(self, input_data: Any, output_format: str = "json") -> StructuredResult:
        """
        主处理入口

        Args:
            input_data: 输入数据（字符串、字典、列表等）
            output_format: 输出格式（json/table/text）

        Returns:
            StructuredResult: 结构化处理结果

        Raises:
            MarketingSkillsError: 处理过程中出现的错误
        """
        # 验证输入
        self._validate_input(input_data)

        # 设置参数
        self.input_data = input_data
        self.output_format = output_format

        # 检查输出格式
        if output_format not in self.SUPPORTED_FORMATS:
            raise MarketingSkillsError("E008", f"不支持的输出格式: {output_format}，请选择 {self.SUPPORTED_FORMATS}")

        # 执行处理流程
        try:
            # Step 1: 解析输入
            parsed_data = self._parse_input(input_data)

            # Step 2: 提取关键信息
            fields, confidence = self._extract_key_info(parsed_data)

            # Step 3: 生成输出内容
            content = self._generate_output(fields, confidence)

            # 构建结果
            result = StructuredResult(
                content=content,
                fields=fields,
                confidence=confidence,
                warnings=self._generate_warnings(confidence),
            )

            return result

        except MarketingSkillsError:
            raise
        except Exception as e:
            raise MarketingSkillsError("E006", f"处理过程中发生错误: {str(e)}")

    def batch_process(
        self, inputs: List[Any], output_format: str = "json"
    ) -> List[StructuredResult]:
        """
        批量处理多个输入

        Args:
            inputs: 输入数据列表
            output_format: 输出格式

        Returns:
            List[StructuredResult]: 处理结果列表
        """
        if not inputs:
            raise MarketingSkillsError("E001")

        results = []
        try:
            for i, input_data in enumerate(inputs):
                try:
                    result = self.process(input_data, output_format)
                    results.append(result)
                except MarketingSkillsError as e:
                    # 单条失败不中断整体，记录错误
                    results.append(
                        StructuredResult(
                            content=f"处理失败: {e.error_code}",
                            fields={"error": e.error_code, "message": e.message},
                            confidence=0.0,
                            warnings=[e.message],
                        )
                    )
        except Exception:
            raise MarketingSkillsError("E007", "批量处理中断")

        return results

    # ============================================================
    # 内部方法
    # ============================================================
    def _validate_input(self, input_data: Any) -> None:
        """验证输入数据的合法性"""
        if input_data is None:
            raise MarketingSkillsError("E001")

        if isinstance(input_data, str):
            if not input_data.strip():
                raise MarketingSkillsError("E001")
            if len(input_data) > self.MAX_INPUT_LENGTH:
                raise MarketingSkillsError("E010", "输入内容过长")
        elif isinstance(input_data, (dict, list)):
            if len(input_data) == 0:
                raise MarketingSkillsError("E001")
        else:
            raise MarketingSkillsError("E003", f"不支持的输入类型: {type(input_data)}")

    def _parse_input(self, input_data: Any) -> Any:
        """
        解析输入数据

        支持：
        - 字符串（可能包含结构化文本）
        - 字典/列表（直接使用）
        - URL 字符串（提取域名和路径信息）
        """
        if isinstance(input_data, str):
            # 尝试解析 JSON
            try:
                return json.loads(input_data)
            except json.JSONDecodeError:
                pass

            # 检查是否为 URL
            if input_data.startswith(("http://", "https://")):
                return self._parse_url(input_data)

            # 普通文本，按行分割
            return {"text": input_data, "lines": input_data.split("\n")}

        return input_data

    def _parse_url(self, url: str) -> Dict[str, str]:
        """解析 URL 信息"""
        # 提取域名
        domain_match = re.search(r"https?://([^/]+)", url)
        domain = domain_match.group(1) if domain_match else ""

        # 提取路径
        path_match = re.search(r"https?://[^/]+(/[^?]*)", url)
        path = path_match.group(1) if path_match else "/"

        # 提取查询参数
        query_match = re.search(r"\?(.+)", url)
        query = query_match.group(1) if query_match else ""

        return {
            "url": url,
            "domain": domain,
            "path": path,
            "query": query,
            "type": "url",
        }

    def _extract_key_info(self, parsed_data: Any) -> Tuple[Dict[str, Any], float]:
        """
        提取关键信息并计算置信度

        Returns:
            Tuple[Dict, float]: (字段字典, 置信度)
        """
        fields = {}
        confidence = 0.0

        if isinstance(parsed_data, dict):
            # 字典类型输入
            if "type" in parsed_data and parsed_data["type"] == "url":
                # URL 输入
                fields = {
                    "source_type": "url",
                    "domain": parsed_data.get("domain", ""),
                    "path": parsed_data.get("path", ""),
                    "query_params": parsed_data.get("query", ""),
                }
                confidence = 0.95 if fields["domain"] else 0.7
            else:
                # 普通字典
                fields = parsed_data
                # 计算置信度：根据字段完整性
                required_fields = ["content", "title", "description"]
                present_fields = sum(1 for f in required_fields if f in parsed_data)
                confidence = 0.6 + (present_fields / len(required_fields)) * 0.35

        elif isinstance(parsed_data, list):
            # 列表类型输入
            fields = {
                "items_count": len(parsed_data),
                "items": parsed_data[:10],  # 最多保留10条
                "total_items": len(parsed_data),
            }
            confidence = 0.9 if len(parsed_data) > 0 else 0.5

        elif isinstance(parsed_data, str):
            # 纯文本输入
            lines = parsed_data.split("\n")
            fields = {
                "content": parsed_data,
                "line_count": len(lines),
                "char_count": len(parsed_data),
            }
            confidence = 0.8 if len(parsed_data) > 10 else 0.6

        # 确保置信度在 0-1 之间
        confidence = max(0.0, min(1.0, confidence))

        return fields, confidence

    def _generate_output(self, fields: Dict[str, Any], confidence: float) -> str:
        """根据格式生成输出内容"""
        if self.output_format == "json":
            return json.dumps(fields, ensure_ascii=False, indent=2)
        elif self.output_format == "table":
            return self._format_as_table(fields)
        else:  # text
            return self._format_as_text(fields, confidence)

    def _format_as_table(self, fields: Dict[str, Any]) -> str:
        """格式化为表格形式"""
        if not fields:
            return "(空)"

        lines = []
        lines.append("| 字段 | 值 |")
        lines.append("|------|-----|")
        for key, value in fields.items():
            # 截断过长的值
            str_value = str(value)
            if len(str_value) > 100:
                str_value = str_value[:97] + "..."
            lines.append(f"| {key} | {str_value} |")
        return "\n".join(lines)

    def _format_as_text(self, fields: Dict[str, Any], confidence: float) -> str:
        """格式化为纯文本形式"""
        if not fields:
            return "(空)"

        lines = []
        for key, value in fields.items():
            if isinstance(value, list):
                lines.append(f"{key}:")
                for item in value[:5]:
                    lines.append(f"  - {item}")
                if len(value) > 5:
                    lines.append(f"  ... 共 {len(value)} 项")
            else:
                lines.append(f"{key}: {value}")

        # 添加置信度标注
        if confidence >= 0.9:
            lines.append(f"\n[置信度: {confidence:.0%}]")
        elif confidence >= 0.85:
            lines.append(f"\n[置信度: {confidence:.0%}] 建议复核")
        else:
            lines.append(f"\n[置信度: {confidence:.0%}] [需核实]")

        return "\n".join(lines)

    def _generate_warnings(self, confidence: float) -> List[str]:
        """根据置信度生成警告信息"""
        warnings = []
        if confidence < 0.85:
            warnings.append("置信度低于85%，结果可能需要人工核实")
        if confidence < 0.7:
            warnings.append("置信度低于70%，建议重新检查输入数据")
        return warnings


# ============================================================
# 自检功能
# ============================================================
def run_selftest() -> bool:
    """
    运行自检程序

    使用内置硬编码样例数据，不依赖外部文件或网络。

    Returns:
        bool: 自检是否通过
    """
    print("=" * 60)
    print("marketingskills 自检程序")
    print("=" * 60)

    processor = MarketingSkillsProcessor()
    all_passed = True

    # 测试样例 1: 字典输入
    print("\n[测试 1] 字典输入")
    try:
        test_dict = {
            "title": "测试产品",
            "description": "这是一个测试用的产品描述",
            "price": 99.9,
            "category": "电子产品",
        }
        result = processor.process(test_dict, "json")
        assert result.fields["title"] == "测试产品"
        assert result.confidence >= 0.8  # 宽松阈值：置信度应较高
        assert result.confidence <= 1.0
        print(f"  ✓ 通过 (置信度: {result.confidence:.2%})")
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        all_passed = False

    # 测试样例 2: 文本输入
    print("\n[测试 2] 文本输入")
    try:
        test_text = "这是一段测试文本，用于验证文本处理功能是否正常工作。"
        result = processor.process(test_text, "text")
        assert result.fields["char_count"] > 0
        assert result.fields["line_count"] >= 1
        assert result.confidence > 0  # 置信度应大于0
        print(f"  ✓ 通过 (置信度: {result.confidence:.2%})")
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        all_passed = False

    # 测试样例 3: URL 输入
    print("\n[测试 3] URL 输入")
    try:
        test_url = "https://example.com/products?category=electronics"
        result = processor.process(test_url, "json")
        assert result.fields["domain"] == "example.com"
        assert result.fields["path"] == "/products"
        assert result.confidence >= 0.9  # URL 解析置信度应高
        print(f"  ✓ 通过 (置信度: {result.confidence:.2%})")
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        all_passed = False

    # 测试样例 4: 列表输入
    print("\n[测试 4] 列表输入")
    try:
        test_list = ["item1", "item2", "item3", "item4", "item5"]
        result = processor.process(test_list, "table")
        assert result.fields["items_count"] == 5
        assert result.fields["total_items"] == 5
        assert result.confidence > 0.5  # 宽松阈值
        print(f"  ✓ 通过 (置信度: {result.confidence:.2%})")
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        all_passed = False

    # 测试样例 5: 错误处理
    print("\n[测试 5] 错误处理")
    try:
        # 空输入应该抛出 E001
        try:
            processor.process(None, "json")
            print("  ✗ 失败: 空输入未抛出异常")
            all_passed = False
        except MarketingSkillsError as e:
            assert e.error_code == "E001"
            print(f"  ✓ 通过 (E001: {e.message})")

        # 不支持的输出格式应该抛出 E008
        try:
            processor.process("test", "xml")
            print("  ✗ 失败: 不支持的格式未抛出异常")
            all_passed = False
        except MarketingSkillsError as e:
            assert e.error_code == "E008"
            print(f"  ✓ 通过 (E008: {e.message})")
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        all_passed = False

    # 测试样例 6: 批量处理
    print("\n[测试 6] 批量处理")
    try:
        test_inputs = [
            {"name": "产品A", "price": 100},
            "这是第二段测试文本",
            ["a", "b", "c"],
        ]
        results = processor.batch_process(test_inputs, "json")
        assert len(results) == 3  # 应该处理3条
        for result in results:
            assert isinstance(result, StructuredResult)
            assert result.confidence >= 0  # 置信度合法
        print(f"  ✓ 通过 (处理 {len(results)} 条)")
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        all_passed = False

    # 测试样例 7: 置信度标注
    print("\n[测试 7] 置信度标注")
    try:
        # 测试高置信度
        high_conf_result = processor.process({"title": "测试"}, "text")
        assert high_conf_result.confidence >= 0.5

        # 测试警告生成
        low_conf_result = StructuredResult(
            content="test",
            fields={"data": "minimal"},
            confidence=0.5,
        )
        warnings = low_conf_result.warnings
        assert len(warnings) > 0  # 低置信度应该有警告

        print(f"  ✓ 通过 (高置信度: {high_conf_result.confidence:.2%})")
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        all_passed = False

    # 测试样例 8: 输出格式
    print("\n[测试 8] 输出格式")
    try:
        test_data = {"key1": "value1", "key2": "value2"}

        # JSON 格式
        json_result = processor.process(test_data, "json")
        parsed_json = json.loads(json_result.content)
        assert parsed_json["key1"] == "value1"

        # 表格格式
        table_result = processor.process(test_data, "table")
        assert "|" in table_result.content  # 表格包含分隔符

        # 文本格式
        text_result = processor.process(test_data, "text")
        assert "key1" in text_result.content

        print("  ✓ 通过 (JSON/Table/Text 格式)")
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        all_passed = False

    # 汇总结果
    print("\n" + "=" * 60)
    if all_passed:
        print("自检结果: 全部通过 ✓")
        print("所有核心功能正常，错误处理有效。")
    else:
        print("自检结果: 存在失败项 ✗")
        print("请检查代码逻辑或输入数据处理。")
    print("=" * 60)

    return all_passed


# ============================================================
# 命令行入口
# ============================================================
def main():
    """命令行主入口"""
    parser = argparse.ArgumentParser(
        description="marketingskills - 营销技能工具",
        epilog="示例: python main.py --input '{\"title\": \"测试\"}' --format json",
    )
    parser.add_argument(
        "--input",
        type=str,
        help="输入数据（JSON 字符串、文本或 URL）",
    )
    parser.add_argument(
        "--format",
        type=str,
        choices=["json", "table", "text"],
        default="json",
        help="输出格式 (默认: json)",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行自检程序（使用内置测试数据）",
    )
    parser.add_argument(
        "--batch",
        type=str,
        help="批量处理（JSON 数组格式）",
    )

    args = parser.parse_args()

    # 运行自检
    if args.selftest:
        success = run_selftest()
        sys.exit(0 if success else 1)

    # 创建处理器
    processor = MarketingSkillsProcessor()

    try:
        # 批量处理模式
        if args.batch:
            try:
                batch_data = json.loads(args.batch)
                if not isinstance(batch_data, list):
                    raise MarketingSkillsError("E003", "批量输入必须是 JSON 数组")
                results = processor.batch_process(batch_data, args.format)
                for i, result in enumerate(results):
                    print(f"--- 结果 {i+1} ---")
                    if args.format == "json":
                        print(result.to_json())
                    else:
                        print(result.content)
                    if result.warnings:
                        print("警告:", "; ".join(result.warnings))
                    print()
            except json.JSONDecodeError:
                raise MarketingSkillsError("E003", "批量输入必须是有效的 JSON 数组")

        # 单条处理模式
        elif args.input:
            # 尝试解析为 JSON
            try:
                input_data = json.loads(args.input)
            except json.JSONDecodeError:
                input_data = args.input

            result = processor.process(input_data, args.format)

            if args.format == "json":
                print(result.to_json())
            else:
                print(result.content)

            if result.warnings:
                print("\n警告:")
                for warning in result.warnings:
                    print(f"  - {warning}")

        # 无输入时显示帮助
        else:
            parser.print_help()
            print("\n" + "=" * 40)
            print("提示: 使用 --selftest 运行自检程序")
            print("示例:")
            print('  python main.py --input \'{"title": "测试"}\'')
            print('  python main.py --input "这是一段文本" --format text')
            print("  python main.py --input https://example.com --format json")
            print('  python main.py --batch \'["item1", "item2"]\'')

    except MarketingSkillsError as e:
        print(f"错误: [{e.error_code}] {e.message}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"未预期错误: {str(e)}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
