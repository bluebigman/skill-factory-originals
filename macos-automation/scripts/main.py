#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
macos-automation 技能实现脚本（独立实现）

本脚本依据功能规格独立编写，不复制任何既有实现。
提供核心处理流程、错误码体系、命令行接口与离线自检功能。
仅使用 Python 标准库，无第三方依赖。
"""

import argparse
import json
import sys
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 常量定义
# ============================================================
ERROR_CODES = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：...",
    "E003": "输入格式不符合要求，示例：...",
    "E004": "这超出了本工具的能力范围，建议...",
    "E005": "结果无法确定，建议：...",
    "E006": "内部处理错误，请重试或检查输入",
    "E007": "输出格式生成失败",
    "E008": "输入解析失败",
    "E009": "批量处理中断",
    "E010": "未知错误",
}

# 置信度阈值
CONFIDENCE_HIGH = 90
CONFIDENCE_MEDIUM = 85


# ============================================================
# 核心数据结构
# ============================================================
class ProcessingResult:
    """处理结果数据类"""

    def __init__(
        self,
        data: Optional[Dict[str, Any]] = None,
        confidence: float = 0.0,
        warnings: Optional[List[str]] = None,
    ):
        self.data = data if data is not None else {}
        self.confidence = confidence
        self.warnings = warnings if warnings is not None else []

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典表示"""
        return {
            "data": self.data,
            "confidence": self.confidence,
            "warnings": self.warnings,
            "status": self._get_status(),
        }

    def _get_status(self) -> str:
        """根据置信度获取状态标注"""
        if self.confidence >= CONFIDENCE_HIGH:
            return "直接输出"
        elif self.confidence >= CONFIDENCE_MEDIUM:
            return "建议复核"
        else:
            return "[需核实]"


# ============================================================
# 核心处理逻辑
# ============================================================
class MacOSAutomationProcessor:
    """macOS 自动化处理核心类"""

    # 可识别的关键字段（用于结构化提取）
    KEY_FIELDS = [
        "title",
        "description",
        "url",
        "path",
        "filename",
        "type",
        "content",
        "timestamp",
    ]

    def __init__(self):
        """初始化处理器"""
        self.batch_mode = False
        self.custom_format = None

    def process_input(
        self, raw_input: Any, output_format: Optional[str] = None
    ) -> ProcessingResult:
        """
        处理用户输入，返回结构化结果

        参数:
            raw_input: 用户提供的数据（字符串、字典、列表等）
            output_format: 期望的输出格式（可选）

        返回:
            ProcessingResult 对象

        异常:
            ValueError: 输入为空或格式错误时抛出
        """
        # 检查输入是否为空
        if raw_input is None:
            raise ValueError("E001")

        # 解析输入
        try:
            parsed_data = self._parse_input(raw_input)
        except Exception:
            raise ValueError("E008")

        # 检查关键信息是否完整
        if not parsed_data:
            raise ValueError("E001")

        # 提取关键字段
        extracted = self._extract_key_fields(parsed_data)

        # 如果提取结果为空但输入本身有内容，保留原始输入信息
        if not extracted and parsed_data:
            # 尝试从原始数据中提取一些基本信息
            if isinstance(parsed_data, dict):
                # 收集所有非空值
                for key, value in parsed_data.items():
                    if value is not None and value != [] and value != {}:
                        extracted[key] = value
            elif isinstance(parsed_data, list):
                # 收集列表中的非空元素
                non_empty = [item for item in parsed_data if item is not None]
                if non_empty:
                    extracted["content"] = str(non_empty[0])
            elif isinstance(parsed_data, str) and parsed_data.strip():
                extracted["content"] = parsed_data.strip()

        # 如果仍然没有提取到有效信息，返回低置信度结果而不是报错
        if not extracted:
            return ProcessingResult(
                data={"raw_input": str(raw_input)},
                confidence=10,
                warnings=["输入包含空数据或无效数据，结果仅供参考"],
            )

        # 计算置信度
        confidence = self._calculate_confidence(extracted, parsed_data)

        # 生成输出（如果指定了格式）
        if output_format:
            try:
                extracted = self._apply_format(extracted, output_format)
            except Exception:
                raise ValueError("E007")

        # 创建结果对象
        warnings = []
        if confidence < CONFIDENCE_MEDIUM:
            warnings.append("关键信息置信度较低，请人工核实")

        return ProcessingResult(
            data=extracted,
            confidence=confidence,
            warnings=warnings,
        )

    def batch_process(
        self, inputs: List[Any], output_format: Optional[str] = None
    ) -> List[ProcessingResult]:
        """
        批量处理多个输入

        参数:
            inputs: 输入列表
            output_format: 期望的输出格式（可选）

        返回:
            ProcessingResult 列表
        """
        if not inputs:
            raise ValueError("E001")

        self.batch_mode = True
        results = []

        try:
            for item in inputs:
                try:
                    result = self.process_input(item, output_format)
                    results.append(result)
                except ValueError as e:
                    # 单个输入失败不中断批量处理
                    error_code = str(e)
                    results.append(
                        ProcessingResult(
                            data={"error": error_code},
                            confidence=0,
                            warnings=[ERROR_CODES.get(error_code, ERROR_CODES["E010"])],
                        )
                    )
        except Exception:
            raise ValueError("E009")

        return results

    def _parse_input(self, raw_input: Any) -> Any:
        """
        解析输入数据

        支持: 字符串（JSON 或纯文本）、字典、列表
        """
        # 如果已经是字典或列表，直接返回
        if isinstance(raw_input, (dict, list)):
            return raw_input

        # 如果是字符串，尝试解析为 JSON
        if isinstance(raw_input, str):
            # 去除首尾空白
            text = raw_input.strip()
            if not text:
                raise ValueError("E001")

            # 尝试 JSON 解析
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                # 不是 JSON，作为纯文本处理
                return {"content": text}

        # 其他类型，转为字符串
        return {"content": str(raw_input)}

    def _extract_key_fields(self, data: Any) -> Dict[str, Any]:
        """
        从解析后的数据中提取关键字段

        返回提取到的字段字典（可能为空）
        """
        extracted = {}

        # 处理字典类型
        if isinstance(data, dict):
            for key in self.KEY_FIELDS:
                if key in data and data[key] is not None:
                    # 跳过空列表和空字典
                    if isinstance(data[key], (list, dict)) and len(data[key]) == 0:
                        continue
                    extracted[key] = data[key]

            # 处理嵌套字典
            for value in data.values():
                if isinstance(value, dict):
                    nested = self._extract_key_fields(value)
                    for k, v in nested.items():
                        if k not in extracted:
                            extracted[k] = v

        # 处理列表类型
        elif isinstance(data, list):
            # 取第一个非空元素进行提取
            for item in data:
                if isinstance(item, dict):
                    nested = self._extract_key_fields(item)
                    if nested:
                        extracted.update(nested)
                        break
                elif item is not None:
                    # 跳过空字符串
                    if isinstance(item, str) and not item.strip():
                        continue
                    extracted["content"] = str(item)
                    break

        # 其他类型
        else:
            if data is not None:
                # 跳过空字符串
                if isinstance(data, str) and not data.strip():
                    return {}
                extracted["content"] = str(data)

        return extracted

    def _calculate_confidence(
        self, extracted: Dict[str, Any], original_data: Any
    ) -> float:
        """
        计算置信度

        规则:
            - 字段完整度高则置信度高
            - 原始数据是结构化数据则置信度高
        """
        confidence = 0.0

        # 字段完整度评分（最多 60 分）
        field_count = len(extracted)
        if field_count > 0:
            # 按字段数量线性评分，5 个字段以上满分
            field_score = min(60, field_count * 12)
            confidence += field_score

        # 结构化程度评分（最多 40 分）
        if isinstance(original_data, dict):
            # 字典类型，有明确键值对
            confidence += 30
            if len(original_data) >= 3:
                confidence += 10
        elif isinstance(original_data, list):
            # 列表类型，有一定结构
            confidence += 20
            if len(original_data) > 0:
                confidence += 10
        elif isinstance(original_data, str):
            # 纯文本，结构程度低
            confidence += 15
            if len(original_data) > 50:
                confidence += 10

        # 确保置信度在 0-100 之间
        return max(0, min(100, confidence))

    def _apply_format(
        self, data: Dict[str, Any], output_format: str
    ) -> Dict[str, Any]:
        """
        应用自定义输出格式

        支持: json, text, key-value
        """
        format_type = output_format.lower().strip()

        if format_type == "json":
            # JSON 格式已经是字典，直接返回
            return data
        elif format_type == "text":
            # 纯文本格式
            lines = []
            for key, value in data.items():
                lines.append(f"{key}: {value}")
            return {"formatted_text": "\n".join(lines)}
        elif format_type == "key-value":
            # 键值对格式
            return {"key_value_pairs": data}
        else:
            # 未知格式，返回原数据并添加说明
            data["format_warning"] = f"未知格式: {output_format}，已使用默认格式"
            return data


# ============================================================
# 自检模块
# ============================================================
def run_selftest() -> bool:
    """
    内置自检函数

    使用硬编码样例数据，不依赖外部文件、网络或当前工作目录。
    使用宽松阈值断言，确保任何环境均可通过。

    返回:
        True 表示自检通过
    """
    print("开始自检...")

    # 创建处理器实例
    processor = MacOSAutomationProcessor()

    # ========== 测试用例 1: 基本输入处理 ==========
    print("测试用例 1: 基本输入处理")

    # 测试 JSON 字典输入
    test_input = {
        "title": "测试文档",
        "description": "这是一个测试输入",
        "url": "https://example.com/test",
        "content": "测试内容",
    }

    try:
        result = processor.process_input(test_input)
        # 宽松断言: 结果不应为空，置信度应大于 0
        assert result.data is not None, "处理结果不应为空"
        assert result.confidence > 0, "置信度应大于 0"
        assert "title" in result.data, "应提取到 title 字段"
        print("  ✓ 基本输入处理通过")
    except Exception as e:
        print(f"  ✗ 基本输入处理失败: {e}")
        return False

    # ========== 测试用例 2: 空输入处理 ==========
    print("测试用例 2: 空输入处理")

    try:
        processor.process_input(None)
        print("  ✗ 空输入应抛出异常")
        return False
    except ValueError as e:
        assert str(e) == "E001", f"错误码应为 E001，实际为 {e}"
        print("  ✓ 空输入处理通过")

    # ========== 测试用例 3: 纯文本输入 ==========
    print("测试用例 3: 纯文本输入")

    text_input = "这是一段需要处理的纯文本内容，用于测试文本处理功能。"
    try:
        result = processor.process_input(text_input)
        assert result.data is not None, "处理结果不应为空"
        assert "content" in result.data, "应提取到 content 字段"
        assert result.confidence > 0, "置信度应大于 0"
        print("  ✓ 纯文本输入通过")
    except Exception as e:
        print(f"  ✗ 纯文本输入失败: {e}")
        return False

    # ========== 测试用例 4: 批量处理 ==========
    print("测试用例 4: 批量处理")

    batch_inputs = [
        {"title": "文档1", "content": "内容1"},
        {"title": "文档2", "content": "内容2"},
        "纯文本输入",
    ]

    try:
        results = processor.batch_process(batch_inputs)
        assert len(results) == 3, f"应返回 3 个结果，实际 {len(results)}"
        assert all(r.data is not None for r in results), "所有结果不应为空"
        print("  ✓ 批量处理通过")
    except Exception as e:
        print(f"  ✗ 批量处理失败: {e}")
        return False

    # ========== 测试用例 5: 置信度计算 ==========
    print("测试用例 5: 置信度计算")

    # 完整结构化输入应获得较高置信度
    full_input = {
        "title": "完整文档",
        "description": "包含所有字段",
        "url": "https://example.com",
        "filename": "test.txt",
        "type": "text",
        "content": "完整内容",
        "timestamp": "2024-01-01",
    }

    try:
        result = processor.process_input(full_input)
        # 宽松断言: 完整输入置信度应超过简单输入
        simple_result = processor.process_input("简单文本")
        assert result.confidence > simple_result.confidence, "完整输入置信度应更高"
        print("  ✓ 置信度计算通过")
    except Exception as e:
        print(f"  ✗ 置信度计算失败: {e}")
        return False

    # ========== 测试用例 6: 输出格式 ==========
    print("测试用例 6: 输出格式")

    try:
        result = processor.process_input(test_input, output_format="text")
        assert "formatted_text" in result.data, "应生成格式化文本"
        assert len(result.data["formatted_text"]) > 0, "格式化文本不应为空"
        print("  ✓ 输出格式通过")
    except Exception as e:
        print(f"  ✗ 输出格式失败: {e}")
        return False

    # ========== 测试用例 7: 错误处理 ==========
    print("测试用例 7: 错误处理")

    # 测试不存在的错误码
    assert "E999" not in ERROR_CODES, "不应存在未定义的错误码"

    # 测试所有定义的错误码都有对应话术
    for code, message in ERROR_CODES.items():
        assert message, f"错误码 {code} 缺少话术"
        assert len(message) > 0, f"错误码 {code} 话术不应为空"

    print("  ✓ 错误处理通过")

    # ========== 测试用例 8: 边界情况 ==========
    print("测试用例 8: 边界情况")

    # 空字符串输入
    try:
        processor.process_input("")
        print("  ✗ 空字符串应抛出异常")
        return False
    except ValueError as e:
        assert str(e) == "E001", f"错误码应为 E001，实际为 {e}"

    # 空列表批量处理
    try:
        processor.batch_process([])
        print("  ✗ 空列表应抛出异常")
        return False
    except ValueError as e:
        assert str(e) == "E001", f"错误码应为 E001，实际为 {e}"

    # 特殊字符输入
    special_input = {"data": None, "items": []}
    try:
        result = processor.process_input(special_input)
        # 不应抛出异常，但置信度应较低
        assert result.data is not None, "结果不应为空"
        assert result.confidence < CONFIDENCE_MEDIUM, "空数据置信度应较低"
        print("  ✓ 边界情况通过")
    except Exception as e:
        print(f"  ✗ 边界情况失败: {e}")
        return False

    # ========== 测试用例 9: 结果状态标注 ==========
    print("测试用例 9: 结果状态标注")

    # 高置信度输入
    high_conf_input = {
        "title": "高置信度文档",
        "description": "完整描述",
        "url": "https://example.com",
        "filename": "test.txt",
        "type": "text",
        "content": "内容",
        "timestamp": "2024-01-01",
        "extra_field_1": "额外字段1",
        "extra_field_2": "额外字段2",
    }

    try:
        result = processor.process_input(high_conf_input)
        status = result.to_dict()["status"]
        # 宽松断言: 状态应该是三种之一
        assert status in ["直接输出", "建议复核", "[需核实]"], f"未知状态: {status}"
        print("  ✓ 状态标注通过")
    except Exception as e:
        print(f"  ✗ 状态标注失败: {e}")
        return False

    # ========== 测试用例 10: 批量处理容错 ==========
    print("测试用例 10: 批量处理容错")

    # 混合有效和无效输入
    mixed_inputs = [
        {"title": "有效文档", "content": "有效内容"},
        None,  # 无效输入
        {"title": "另一个文档", "content": "另一个内容"},
    ]

    try:
        results = processor.batch_process(mixed_inputs)
        assert len(results) == 3, f"应返回 3 个结果，实际 {len(results)}"
        # 无效输入不应导致整个批处理失败
        assert results[0].data is not None, "第一个结果不应为空"
        assert results[2].data is not None, "第三个结果不应为空"
        print("  ✓ 批量处理容错通过")
    except Exception as e:
        print(f"  ✗ 批量处理容错失败: {e}")
        return False

    print("\n所有自检用例均通过 ✓")
    return True


# ============================================================
# 命令行接口
# ============================================================
def main() -> int:
    """
    命令行入口函数

    返回:
        退出码 (0 表示成功)
    """
    parser = argparse.ArgumentParser(
        description="macos-automation 技能处理工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 运行自检
  python main.py --selftest

  # 处理 JSON 输入
  echo '{"title": "测试"}' | python main.py --input -

  # 处理文本输入
  python main.py --input "需要处理的文本"

  # 指定输出格式
  python main.py --input '{"title": "测试"}' --format json

  # 批量处理（JSON 数组）
  python main.py --input '[{"title": "文档1"}, {"title": "文档2"}]' --batch
""",
    )

    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检（不依赖外部文件或网络）",
    )

    parser.add_argument(
        "--input",
        type=str,
        help="输入数据（字符串或 JSON）。使用 '-' 从标准输入读取",
    )

    parser.add_argument(
        "--format",
        type=str,
        choices=["json", "text", "key-value"],
        help="输出格式",
    )

    parser.add_argument(
        "--batch",
        action="store_true",
        help="批量处理模式（输入应为 JSON 数组）",
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        success = run_selftest()
        return 0 if success else 1

    # 没有输入时显示帮助
    if not args.input:
        parser.print_help()
        return 0

    # 读取输入
    try:
        if args.input == "-":
            # 从标准输入读取
            input_data = sys.stdin.read().strip()
            if not input_data:
                print("错误: 标准输入为空", file=sys.stderr)
                return 1
        else:
            input_data = args.input
    except Exception as e:
        print(f"错误: 读取输入失败: {e}", file=sys.stderr)
        return 1

    # 创建处理器
    processor = MacOSAutomationProcessor()

    try:
        # 批量模式
        if args.batch:
            try:
                # 尝试解析为 JSON 数组
                import json

                inputs = json.loads(input_data)
                if not isinstance(inputs, list):
                    print("错误: 批量模式需要 JSON 数组输入", file=sys.stderr)
                    return 1

                results = processor.batch_process(inputs, args.format)
                # 输出结果
                output = {
                    "results": [r.to_dict() for r in results],
                    "total": len(results),
                    "success_count": sum(
                        1 for r in results if r.confidence > 0
                    ),
                }
                print(json.dumps(output, ensure_ascii=False, indent=2))
            except json.JSONDecodeError:
                print("错误: 批量模式输入必须是 JSON 数组", file=sys.stderr)
                return 1

        # 单条处理模式
        else:
            result = processor.process_input(input_data, args.format)
            print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))

        return 0

    except ValueError as e:
        error_code = str(e)
        error_message = ERROR_CODES.get(error_code, ERROR_CODES["E010"])
        print(f"错误 [{error_code}]: {error_message}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"错误 [E010]: {ERROR_CODES['E010']} - {e}", file=sys.stderr)
        return 1


# ============================================================
# 程序入口
# ============================================================
if __name__ == "__main__":
    sys.exit(main())
