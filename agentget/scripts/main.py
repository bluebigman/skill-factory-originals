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


# ============================================================
# 核心数据结构
# ============================================================
class ProcessingResult:
    """处理结果的数据结构"""

    def __init__(self, data: Any, confidence: float, warnings: Optional[List[str]] = None):
        self.data = data
        self.confidence = confidence
        self.warnings = warnings or []

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "data": self.data,
            "confidence": self.confidence,
            "confidence_level": self._get_confidence_level(),
            "warnings": self.warnings,
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

    def process(self, input_data: str, output_format: str = "json") -> ProcessingResult:
        """
        处理输入数据，返回结构化结果

        Args:
            input_data: 用户输入的原始数据
            output_format: 输出格式（json/text）

        Returns:
            ProcessingResult: 处理结果对象

        Raises:
            ValueError: 当输入为空或格式错误时
        """
        # 检查输入是否为空
        if not input_data or not input_data.strip():
            raise ValueError("E001")

        # 解析输入数据
        parsed_data, parse_confidence = self._parse_input(input_data)

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

        return ProcessingResult(output_data, confidence, warnings)

    def _parse_input(self, input_data: str) -> Tuple[Optional[Dict[str, Any]], float]:
        """
        解析输入数据，识别关键信息

        Returns:
            (解析后的数据字典, 解析置信度)
        """
        # 尝试解析JSON格式
        try:
            data = json.loads(input_data)
            if isinstance(data, dict):
                return data, 1.0
            elif isinstance(data, list):
                return {"items": data, "count": len(data)}, 0.95
        except json.JSONDecodeError:
            pass

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
                    return result, 0.85
            except Exception:
                pass

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
                return result, 0.80

        # 无法解析，返回原始文本
        return {"raw_text": input_data.strip(), "length": len(input_data.strip())}, 0.60

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

    def process_batch(self, inputs: List[str], output_format: str = "json") -> List[Dict[str, Any]]:
        """
        批量处理多个输入

        Args:
            inputs: 输入数据列表
            output_format: 输出格式

        Returns:
            处理结果列表
        """
        results = []
        for input_data in inputs:
            try:
                result = self.processor.process(input_data, output_format)
                result_dict = result.to_dict()
                result_dict["status"] = "success"
                results.append(result_dict)
            except ValueError as e:
                error_code = str(e)
                error_msg = ERROR_CODES.get(error_code, "未知错误")
                results.append({
                    "status": "error",
                    "error_code": error_code,
                    "error_message": error_msg,
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
        results = batch_processor.process_batch(inputs, args.format)
        print(json.dumps(results, ensure_ascii=False, indent=2))
        sys.exit(0)

    # 单条处理
    if args.input:
        try:
            result = processor.process(args.input, args.format)
            output = result.to_dict()
            print(json.dumps(output, ensure_ascii=False, indent=2))
            sys.exit(0)
        except ValueError as e:
            error_code = str(e)
            error_msg = ERROR_CODES.get(error_code, "未知错误")
            print(f"错误 [{error_code}]: {error_msg}", file=sys.stderr)
            sys.exit(1)

    # 无输入参数时显示帮助
    parser.print_help()


if __name__ == "__main__":
    main()
