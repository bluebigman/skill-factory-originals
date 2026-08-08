#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
agentget - 通用数据处理与转换工具

本脚本依据功能规格独立实现，用于将用户提供的数据/文件/URL
转换为结构化结果，并支持批量处理和自定义输出格式。

仅用于学习与参考，不构成任何专业建议。
"""

import argparse
import json
import sys
import os
import traceback
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 常量定义
# ============================================================
ERROR_CODES = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：{missing}",
    "E003": "输入格式不符合要求，示例：{example}",
    "E004": "这超出了本工具的能力范围，建议：{suggestion}",
    "E005": "结果无法确定，建议：{suggestion}",
}

# 自检契约示例（用于验证核心逻辑）
SELFTEST_EXAMPLES = [
    # (输入, 期望输出类型, 期望置信度下限, 描述)
    ('{"name": "test", "value": 123}', dict, 0.8, "JSON对象输入"),
    ("name=test; value=123", dict, 0.5, "键值对输入"),
    ("", None, 0.0, "空输入应报错"),
    ("12345", dict, 0.3, "纯数字输入"),
    ("!@#$%^&*()", dict, 0.3, "特殊字符输入"),
    ("名称: 测试项目\n描述: 这是一个测试\n状态: 进行中", dict, 0.5, "多行文本输入"),
    ("中文标点测试：这是内容。", dict, 0.3, "中文标点输入"),
    ("a" * 10000, dict, 0.3, "超长输入"),
]


# ============================================================
# 核心数据结构
# ============================================================
class ProcessingResult:
    """处理结果的数据结构"""

    def __init__(self, data: Any, confidence: float, warnings: Optional[List[str]] = None,
                 modifications: Optional[List[str]] = None):
        self.data = data
        self.confidence = confidence
        self.warnings = warnings or []
        self.modifications = modifications or []

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "data": self.data,
            "confidence": self.confidence,
            "confidence_level": self._get_confidence_level(),
            "warnings": self.warnings,
            "modifications": self.modifications,
        }

    def _get_confidence_level(self) -> str:
        """根据置信度返回等级标注"""
        if self.confidence >= 0.90:
            return "直接输出"
        elif self.confidence >= 0.85:
            return "建议复核"
        else:
            return "[需核实]"


# ============================================================
# 核心处理逻辑
# ============================================================
class AgentGetProcessor:
    """核心处理器类"""

    def __init__(self):
        self.batch_mode = False

    def process(self, input_data: str, output_format: str = "json",
                verbose: bool = False) -> ProcessingResult:
        """
        处理输入数据，返回结构化结果

        Args:
            input_data: 用户输入的原始数据
            output_format: 输出格式（json/text）
            verbose: 是否输出详细处理信息

        Returns:
            ProcessingResult: 处理结果对象

        Raises:
            ValueError: 当输入为空或格式错误时
        """
        # 输入校验（R7：guard clause 顶部先校验所有输入）
        if not isinstance(input_data, str):
            raise ValueError("E001")
        if not input_data or not input_data.strip():
            raise ValueError("E001")
        if output_format not in ("json", "text"):
            raise ValueError("E003")

        # 解析输入数据
        parsed_data, parse_confidence, parse_modifications = self._parse_input(input_data)

        # 检查解析结果
        if parsed_data is None:
            raise ValueError("E003")

        # 检查关键信息是否完整
        missing_fields = self._check_required_fields(parsed_data)
        if missing_fields:
            raise ValueError(f"E002:{','.join(missing_fields)}")

        # 生成输出
        output_data = self._format_output(parsed_data, output_format)

        # 计算置信度
        confidence = self._calculate_confidence(parsed_data, parse_confidence)

        # 生成警告
        warnings = self._generate_warnings(parsed_data, confidence)

        # 收集修改明细
        modifications = parse_modifications
        if verbose:
            modifications.append(f"输入格式: {self._detect_input_format(input_data)}")
            modifications.append(f"输出格式: {output_format}")
            modifications.append(f"数据字段数: {len(parsed_data)}")

        return ProcessingResult(output_data, confidence, warnings, modifications)

    def _parse_input(self, input_data: str) -> Tuple[Optional[Dict[str, Any]], float, List[str]]:
        """
        解析输入数据，识别关键信息

        Returns:
            (解析后的数据字典, 解析置信度, 修改明细列表)
        """
        modifications = []

        # 尝试解析JSON格式
        try:
            data = json.loads(input_data)
            if isinstance(data, dict):
                modifications.append(f"识别为JSON对象，提取{len(data)}个字段")
                return data, 1.0, modifications
            elif isinstance(data, list):
                modifications.append(f"识别为JSON数组，包含{len(data)}个元素")
                return {"items": data, "count": len(data)}, 0.95, modifications
        except json.JSONDecodeError as e:
            modifications.append(f"JSON解析失败: {str(e)[:50]}...")

        # 尝试解析键值对格式（如 "key1=value1; key2=value2"）
        if "=" in input_data and (";" in input_data or "," in input_data):
            try:
                result = {}
                # 根据分隔符拆分
                separator = ";" if ";" in input_data else ","
                pairs = input_data.split(separator)
                for pair in pairs:
                    if "=" in pair:
                        key, value = pair.strip().split("=", 1)
                        result[key.strip()] = value.strip()
                if result:
                    modifications.append(f"识别为键值对格式，提取{len(result)}个字段")
                    return result, 0.85, modifications
            except Exception as e:
                modifications.append(f"键值对解析失败: {str(e)[:50]}...")

        # 尝试解析简单的文本行
        lines = [line.strip() for line in input_data.strip().split("\n") if line.strip()]
        if lines:
            # 检查是否为名称: 值格式
            result = {}
            for line in lines:
                if ":" in line:
                    key, value = line.split(":", 1)
                    result[key.strip()] = value.strip()
            if result:
                modifications.append(f"识别为文本行格式，提取{len(result)}个字段")
                return result, 0.80, modifications

        # 无法解析，返回原始文本
        modifications.append("无法识别为结构化格式，保留原始文本")
        return {"raw_text": input_data.strip(), "length": len(input_data.strip())}, 0.60, modifications

    def _detect_input_format(self, input_data: str) -> str:
        """检测输入格式类型"""
        try:
            json.loads(input_data)
            return "JSON"
        except Exception as e:
            print(f"警告: JSON格式检测失败: {str(e)}", file=sys.stderr)
        if "=" in input_data:
            return "键值对"
        if ":" in input_data:
            return "文本行"
        return "原始文本"

    def _check_required_fields(self, data: Dict[str, Any]) -> List[str]:
        """
        检查必需字段

        Returns:
            缺失字段列表
        """
        # 这里根据实际需求定义必需字段
        # 对于通用工具，我们只检查基本结构
        missing = []
        if not isinstance(data, dict):
            missing.append("data_structure")
        return missing

    def _format_output(self, data: Dict[str, Any], output_format: str) -> Any:
        """
        格式化输出结果
        """
        if output_format == "json":
            return data
        elif output_format == "text":
            # 转换为文本格式
            lines = []
            for key, value in data.items():
                lines.append(f"{key}: {value}")
            return "\n".join(lines)
        else:
            # 默认返回JSON
            return data

    def _calculate_confidence(self, data: Dict[str, Any], base_confidence: float) -> float:
        """
        计算最终置信度
        """
        confidence = base_confidence

        # 根据数据完整度调整置信度
        if "raw_text" in data:
            # 原始文本较低置信度
            confidence *= 0.8
        elif "items" in data:
            # 列表数据
            if data.get("count", 0) > 0:
                confidence *= 1.0
            else:
                confidence *= 0.7

        # 检查是否有明确的键值对
        if len(data) >= 2:
            confidence *= 1.0
        elif len(data) == 1:
            confidence *= 0.9

        # 限制在0到1之间
        return max(0.0, min(1.0, confidence))

    def _generate_warnings(self, data: Dict[str, Any], confidence: float) -> List[str]:
        """
        生成警告信息
        """
        warnings = []
        if confidence < 0.85:
            warnings.append("输入数据不够明确，部分内容可能无法准确处理")
        if "raw_text" in data:
            warnings.append("输入为原始文本，仅进行了基础处理")
        return warnings


# ============================================================
# 批量处理支持
# ============================================================
class BatchProcessor:
    """批量处理器"""

    def __init__(self, processor: AgentGetProcessor):
        self.processor = processor

    def process_batch(self, inputs: List[str], output_format: str = "json",
                      verbose: bool = False) -> List[Dict[str, Any]]:
        """
        批量处理多个输入

        Args:
            inputs: 输入数据列表
            output_format: 输出格式
            verbose: 是否输出详细处理信息

        Returns:
            处理结果列表
        """
        # 输入校验（R7）
        if not isinstance(inputs, list):
            raise ValueError("E001")
        if not all(isinstance(item, str) for item in inputs):
            raise ValueError("E001")

        results = []
        for i, input_data in enumerate(inputs):
            try:
                result = self.processor.process(input_data, output_format, verbose)
                result_dict = result.to_dict()
                result_dict["status"] = "success"
                result_dict["index"] = i
                results.append(result_dict)
            except ValueError as e:
                error_code = str(e)
                # 处理可能包含缺失字段的错误码
                if ":" in error_code:
                    error_code, missing = error_code.split(":", 1)
                    error_msg = ERROR_CODES.get(error_code, "未知错误")
                    if "{missing}" in error_msg:
                        error_msg = error_msg.format(missing=missing)
                else:
                    error_msg = ERROR_CODES.get(error_code, "未知错误")
                results.append({
                    "status": "error",
                    "error_code": error_code,
                    "error_message": error_msg,
                    "index": i,
                })
            except Exception as e:
                # R10: 未知异常必须上报
                print(f"系统错误处理条目{i}: {str(e)}", file=sys.stderr)
                traceback.print_exc(file=sys.stderr)
                results.append({
                    "status": "error",
                    "error_code": "E999",
                    "error_message": f"系统错误: {str(e)}",
                    "index": i,
                })
        return results


# ============================================================
# 自检功能
# ============================================================
def run_selftest() -> bool:
    """
    运行自检功能，验证核心逻辑

    Returns:
        True 表示自检通过，False 表示失败
    """
    print("开始运行自检...")

    # 创建处理器实例
    processor = AgentGetProcessor()
    batch_processor = BatchProcessor(processor)

    # 测试用例1: JSON输入
    print("测试1: JSON输入")
    try:
        result = processor.process('{"name": "test", "value": 123}')
        assert result.confidence > 0.8, "JSON输入置信度应较高"
        assert result.data is not None, "JSON输入应有输出数据"
        assert len(result.modifications) > 0, "应有修改明细"
        print("  ✓ 通过")
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        return False

    # 测试用例2: 键值对输入
    print("测试2: 键值对输入")
    try:
        result = processor.process("name=test; value=123")
        assert result.confidence > 0.5, "键值对输入应有合理置信度"
        assert result.data is not None, "键值对输入应有输出数据"
        assert len(result.modifications) > 0, "应有修改明细"
        print("  ✓ 通过")
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        return False

    # 测试用例3: 空输入
    print("测试3: 空输入处理")
    try:
        processor.process("")
        print("  ✗ 失败: 空输入应该报错")
        return False
    except ValueError as e:
        assert str(e) == "E001", "空输入应返回E001错误码"
        print("  ✓ 通过")

    # 测试用例4: 批量处理
    print("测试4: 批量处理")
    try:
        inputs = ['{"a": 1}', '{"b": 2}', ""]
        results = batch_processor.process_batch(inputs)
        assert len(results) == 3, "批量处理应返回3个结果"
        success_count = sum(1 for r in results if r["status"] == "success")
        assert success_count == 2, "应有2个成功结果"
        assert results[2]["status"] == "error", "空输入应报错"
        print(f"  ✓ 通过 (成功: {success_count}/3)")

    except Exception as e:
        print(f"  ✗ 失败: {e}")
        return False

    # 测试用例5: 错误码系统
    print("测试5: 错误码系统")
    try:
        assert "E001" in ERROR_CODES, "E001错误码应存在"
        assert "E002" in ERROR_CODES, "E002错误码应存在"
        assert "E003" in ERROR_CODES, "E003错误码应存在"
        assert "E004" in ERROR_CODES, "E004错误码应存在"
        assert "E005" in ERROR_CODES, "E005错误码应存在"
        print("  ✓ 通过")

    except Exception as e:
        print(f"  ✗ 失败: {e}")
        return False

    # 测试用例6: 不同输出格式
    print("测试6: 输出格式")
    try:
        # JSON格式
        result_json = processor.process('{"name": "test"}', output_format="json")
        assert isinstance(result_json.data, dict), "JSON格式应返回字典"

        # 文本格式
        result_text = processor.process('{"name": "test"}', output_format="text")
        assert isinstance(result_text.data, str), "文本格式应返回字符串"
        print("  ✓ 通过")

    except Exception as e:
        print(f"  ✗ 失败: {e}")
        return False

    # 测试用例7: 置信度等级
    print("测试7: 置信度等级")
    try:
        # 高置信度
        result_high = ProcessingResult({"data": "test"}, 0.95)
        assert result_high._get_confidence_level() == "直接输出", "高置信度应为直接输出"

        # 中等置信度
        result_mid = ProcessingResult({"data": "test"}, 0.88)
        assert result_mid._get_confidence_level() == "建议复核", "中等置信度应为建议复核"

        # 低置信度
        result_low = ProcessingResult({"data": "test"}, 0.70)
        assert result_low._get_confidence_level() == "[需核实]", "低置信度应为需核实"
        print("  ✓ 通过")

    except Exception as e:
        print(f"  ✗ 失败: {e}")
        return False

    # 测试用例8: 复杂输入
    print("测试8: 复杂输入")
    try:
        # 多行文本输入
        multi_line = """名称: 测试项目
描述: 这是一个测试
状态: 进行中"""
        result = processor.process(multi_line)
        assert result.data is not None, "多行文本应有输出"
        assert result.confidence > 0.5, "多行文本应有合理置信度"
        assert len(result.modifications) > 0, "应有修改明细"
        print("  ✓ 通过")

    except Exception as e:
        print(f"  ✗ 失败: {e}")
        return False

    # 测试用例9: 边界输入
    print("测试9: 边界输入")
    try:
        # 纯数字输入
        result = processor.process("12345")
        assert result.data is not None, "纯数字输入应有输出"
        assert result.confidence > 0.3, "纯数字输入应有合理置信度"

        # 特殊字符输入
        result = processor.process("!@#$%^&*()")
        assert result.data is not None, "特殊字符输入应有输出"
        print("  ✓ 通过")

    except Exception as e:
        print(f"  ✗ 失败: {e}")
        return False

    # 测试用例10: 错误码格式化
    print("测试10: 错误码格式化")
    try:
        # 测试E002错误码的格式化
        error_msg = ERROR_CODES["E002"].format(missing="name,age")
        assert "name,age" in error_msg, "E002错误码应包含缺失字段"

        # 测试E003错误码的格式化
        error_msg = ERROR_CODES["E003"].format(example='{"key": "value"}')
        assert '{"key": "value"}' in error_msg, "E003错误码应包含示例"

        # 测试E004错误码的格式化
        error_msg = ERROR_CODES["E004"].format(suggestion="使用更专业的工具")
        assert "使用更专业的工具" in error_msg, "E004错误码应包含建议"

        # 测试E005错误码的格式化
        error_msg = ERROR_CODES["E005"].format(suggestion="提供更多上下文信息")
        assert "提供更多上下文信息" in error_msg, "E005错误码应包含建议"
        print("  ✓ 通过")

    except Exception as e:
        print(f"  ✗ 失败: {e}")
        return False

    # 测试用例11: 中文标点输入
    print("测试11: 中文标点输入")
    try:
        result = processor.process("中文标点测试：这是内容。")
        assert result.data is not None, "中文标点输入应有输出"
        assert result.confidence > 0.3, "中文标点输入应有合理置信度"
        print("  ✓ 通过")

    except Exception as e:
        print(f"  ✗ 失败: {e}")
        return False

    # 测试用例12: 超长输入
    print("测试12: 超长输入")
    try:
        long_input = "a" * 10000
        result = processor.process(long_input)
        assert result.data is not None, "超长输入应有输出"
        assert result.confidence > 0.3, "超长输入应有合理置信度"
        print("  ✓ 通过")

    except Exception as e:
        print(f"  ✗ 失败: {e}")
        return False

    # 测试用例13: 契约示例验证
    print("测试13: 契约示例验证")
    try:
        for input_data, expected_type, min_confidence, desc in SELFTEST_EXAMPLES:
            try:
                result = processor.process(input_data)
                if expected_type is None:
                    print(f"  ✗ 失败: {desc} 应该报错")
                    return False
                assert isinstance(result.data, expected_type), f"{desc} 输出类型错误"
                assert result.confidence >= min_confidence, f"{desc} 置信度不足"
            except ValueError:
                if expected_type is not None:
                    print(f"  ✗ 失败: {desc} 不应报错")
                    return False
        print("  ✓ 通过")

    except Exception as e:
        print(f"  ✗ 失败: {e}")
        return False

    # 测试用例14: verbose模式修改明细
    print("测试14: verbose模式修改明细")
    try:
        result = processor.process('{"name": "test"}', verbose=True)
        assert len(result.modifications) > 0, "verbose模式应有修改明细"
        assert any("输入格式" in mod for mod in result.modifications), "应包含输入格式信息"
        assert any("输出格式" in mod for mod in result.modifications), "应包含输出格式信息"
        print("  ✓ 通过")

    except Exception as e:
        print(f"  ✗ 失败: {e}")
        return False

    # 测试用例15: 异常降级处理
    print("测试15: 异常降级处理")
    try:
        # 测试非字符串输入
        try:
            processor.process(12345)
            print("  ✗ 失败: 非字符串输入应该报错")
            return False
        except ValueError as e:
            assert str(e) == "E001", "非字符串输入应返回E001错误码"

        # 测试无效输出格式
        try:
            processor.process('{"a": 1}', output_format="xml")
            print("  ✗ 失败: 无效输出格式应该报错")
            return False
        except ValueError as e:
            assert str(e) == "E003", "无效输出格式应返回E003错误码"
        print("  ✓ 通过")

    except Exception as e:
        print(f"  ✗ 失败: {e}")
        return False

    print("\n所有自检测试通过！")
    return True


# ============================================================
# 主入口
# ============================================================
def main():
    """主程序入口"""
    parser = argparse.ArgumentParser(
        description="agentget - 通用数据处理与转换工具",
        epilog="示例: python main.py --input '{\"name\": \"test\"}' --format json"
    )
    parser.add_argument(
        "--input",
        type=str,
        help="待处理的输入数据（支持JSON、键值对、文本格式）"
    )
    parser.add_argument(
        "--format",
        type=str,
        choices=["json", "text"],
        default="json",
        help="输出格式 (默认: json)"
    )
    parser.add_argument(
        "--batch",
        type=str,
        help="批量处理（多个输入用 | 分隔）"
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行自检功能（不读取外部数据）"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="预览模式（仅打印输出，不执行任何写入操作）"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="输出详细处理信息（包含修改明细）"
    )

    args = parser.parse_args()

    # 运行自检
    if args.selftest:
        success = run_selftest()
        sys.exit(0 if success else 1)

    # 创建处理器
    processor = AgentGetProcessor()
    batch_processor = BatchProcessor(processor)

    # 批量处理
    if args.batch:
        inputs = args.batch.split("|")
        results = batch_processor.process_batch(inputs, args.format, args.verbose)
        if args.verbose:
            print("批量处理结果:", file=sys.stderr)
            for i, result in enumerate(results):
                if result["status"] == "success":
                    print(f"  条目{i}: 成功，置信度 {result['confidence']:.2f}", file=sys.stderr)
                    if "modifications" in result:
                        for mod in result["modifications"]:
                            print(f"    - {mod}", file=sys.stderr)
                else:
                    print(f"  条目{i}: 失败 - {result['error_message']}", file=sys.stderr)
        print(json.dumps(results, ensure_ascii=False, indent=2))
        sys.exit(0)

    # 单条处理
    if args.input:
        try:
            result = processor.process(args.input, args.format, args.verbose)
            output = result.to_dict()
            if args.verbose:
                print(f"处理完成，置信度: {result.confidence:.2f}", file=sys.stderr)
                if result.modifications:
                    print("处理明细:", file=sys.stderr)
                    for mod in result.modifications:
                        print(f"  - {mod}", file=sys.stderr)
                if result.warnings:
                    print("警告:", file=sys.stderr)
                    for warning in result.warnings:
                        print(f"  - {warning}", file=sys.stderr)
            print(json.dumps(output, ensure_ascii=False, indent=2))
            sys.exit(0)
        except ValueError as e:
            error_code = str(e)
            # 处理可能包含缺失字段的错误码
            if ":" in error_code:
                error_code, missing = error_code.split(":", 1)
                error_msg = ERROR_CODES.get(error_code, "未知错误")
                if "{missing}" in error_msg:
                    error_msg = error_msg.format(missing=missing)
            else:
                error_msg = ERROR_CODES.get(error_code, "未知错误")
            print(f"错误 [{error_code}]: {error_msg}", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            # R10: 未知异常必须上报
            print(f"系统错误: {str(e)}", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
            print("请检查输入数据格式是否正确", file=sys.stderr)
            sys.exit(1)

    # 无输入参数时显示帮助
    parser.print_help()


if __name__ == "__main__":
    main()
