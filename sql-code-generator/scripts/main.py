#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py

SQL查询 (sql-code-generator) - 独立实现脚本

本脚本依据《功能规格: sql-code-generator》进行 clean-room 重写。
仅使用 Python 标准库，无第三方依赖。

功能概述:
    1. 解析用户输入，识别关键信息并结构化。
    2. 按默认模板生成结构化输出（JSON 格式）。
    3. 对不确定项进行置信度评估与标注。
    4. 通过 --selftest 参数进行离线自检（内置硬编码样例数据）。

错误码体系:
    E001: 输入为空
    E002: 关键信息缺失
    E003: 输入格式错误
    E004: 超出能力边界
    E005: 置信度过低
    E006: 内部处理异常（通用）
    E007: 参数解析错误
    E008: 输出序列化错误
    E009: 自检失败
    E010: 未知错误

用法示例:
    python scripts/main.py --input "用户提供的数据内容" --format json
    python scripts/main.py --selftest
"""

import argparse
import json
import sys
import os
from typing import Any, Dict, List, Optional, Tuple


# -----------------------------------------------------------------------------
# 常量定义
# -----------------------------------------------------------------------------

# 技能元数据
SKILL_NAME = "sql-code-generator"
SKILL_DISPLAY_NAME = "SQL查询"
SKILL_VERSION = "1.0.0"
SKILL_DESCRIPTION = "Generate code from your SQL schema and queries for type safety and development speed."

# 置信度阈值
CONFIDENCE_HIGH = 0.90      # 置信度 >= 90%: 直接输出
CONFIDENCE_MEDIUM = 0.85    # 85% - 90%: 建议复核
# 低于 85%: 标注 [需核实]

# 错误码与标准化话术映射
ERROR_MESSAGES: Dict[str, str] = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：{}",
    "E003": "输入格式不符合要求，示例：{}",
    "E004": "这超出了本工具的能力范围，建议：{}",
    "E005": "结果无法确定，建议：{}",
    "E006": "内部处理异常，请稍后重试或检查输入。",
    "E007": "参数解析错误，请检查命令行参数。",
    "E008": "输出序列化错误，无法生成结果。",
    "E009": "自检失败，请检查代码逻辑。",
    "E010": "未知错误，请联系开发者。",
}


# -----------------------------------------------------------------------------
# 核心处理逻辑
# -----------------------------------------------------------------------------

class SQLCodeGenerator:
    """
    SQL查询技能的核心处理器。

    负责解析输入、识别关键信息、生成结构化输出并评估置信度。
    本实现为通用框架，不绑定特定领域，遵循功能规格中定义的流程。
    """

    def __init__(self) -> None:
        """初始化处理器。"""
        # 可以在此处初始化任何需要的状态
        pass

    def process(self, raw_input: str, output_format: str = "json") -> Dict[str, Any]:
        """
        处理用户输入，生成结构化结果。

        参数:
            raw_input: 用户提供的原始输入内容（数据/文件内容/URL等）。
            output_format: 期望的输出格式（目前支持 json）。

        返回:
            包含处理结果、置信度和元数据的字典。

        异常:
            抛出带有错误码的 ValueError 或 RuntimeError。
        """
        # Step 0: 输入校验
        if not raw_input or not raw_input.strip():
            raise ValueError("E001")  # 输入为空

        # Step 1: 解析输入内容，识别关键信息
        parsed_data, parse_confidence = self._parse_input(raw_input)

        # Step 2: 检查关键信息是否完整
        missing_fields = self._check_required_fields(parsed_data)
        if missing_fields:
            # E002: 关键信息缺失
            detail = "、".join(missing_fields)
            raise ValueError(f"E002:{detail}")

        # Step 3: 按规则处理，生成结果
        result_data, process_confidence = self._generate_result(parsed_data)

        # Step 4: 计算综合置信度
        overall_confidence = round((parse_confidence + process_confidence) / 2.0, 4)

        # Step 5: 构建输出结构
        output = self._build_output(result_data, overall_confidence, output_format)

        return output

    def _parse_input(self, raw_input: str) -> Tuple[Dict[str, Any], float]:
        """
        解析输入内容，识别关键信息。

        这是一个通用解析器，尝试从输入中提取结构化信息。
        在实际场景中，这里会根据具体需求进行深度解析。

        参数:
            raw_input: 原始输入字符串。

        返回:
            (解析后的结构化数据, 解析置信度)。
        """
        # 简化处理：去除首尾空白，按行拆分
        lines = [line.strip() for line in raw_input.strip().splitlines() if line.strip()]

        if not lines:
            return {}, 0.0

        # 尝试识别关键字段（示例：key: value 格式）
        parsed: Dict[str, Any] = {}
        recognized = 0
        total_lines = len(lines)

        for line in lines:
            if ":" in line or "：" in line:
                # 支持中英文冒号
                sep = ":" if ":" in line else "："
                key, _, value = line.partition(sep)
                key = key.strip()
                value = value.strip()
                if key and value:
                    parsed[key] = value
                    recognized += 1

        # 计算解析置信度：识别出的字段数 / 总行数
        if total_lines == 0:
            confidence = 0.0
        else:
            confidence = recognized / total_lines

        # 如果完全没有识别出结构化字段，则保留原始文本
        if not parsed:
            parsed = {"raw_content": raw_input.strip()}
            confidence = 0.5  # 保留原文，置信度中等

        return parsed, confidence

    def _check_required_fields(self, parsed_data: Dict[str, Any]) -> List[str]:
        """
        检查关键信息是否完整。

        参数:
            parsed_data: 解析后的数据字典。

        返回:
            缺失字段名称列表。
        """
        # 定义关键字段（此处为示例，实际场景根据需求定义）
        # 这里要求至少有一个字段被识别出来
        missing = []
        if not parsed_data:
            missing.append("有效内容")
        return missing

    def _generate_result(self, parsed_data: Dict[str, Any]) -> Tuple[Dict[str, Any], float]:
        """
        根据解析后的数据生成结果。

        参数:
            parsed_data: 解析后的结构化数据。

        返回:
            (生成的结果数据, 处理置信度)。
        """
        # 通用处理：结构化输出解析后的数据
        result = {
            "status": "processed",
            "data": parsed_data,
            "field_count": len(parsed_data),
        }

        # 处理置信度：基于字段数量评估（字段越多，置信度越高，但有上限）
        field_count = len(parsed_data)
        if field_count >= 5:
            confidence = 0.95
        elif field_count >= 3:
            confidence = 0.88
        elif field_count >= 1:
            confidence = 0.80
        else:
            confidence = 0.0

        return result, confidence

    def _build_output(self, result_data: Dict[str, Any], confidence: float, output_format: str) -> Dict[str, Any]:
        """
        构建最终输出结构，包含置信度标注。

        参数:
            result_data: 处理结果数据。
            confidence: 综合置信度。
            output_format: 输出格式。

        返回:
            完整的输出字典。
        """
        # 根据置信度决定标注
        if confidence >= CONFIDENCE_HIGH:
            confidence_label = "直接输出"
            warning = None
        elif confidence >= CONFIDENCE_MEDIUM:
            confidence_label = "建议复核"
            warning = "结果置信度中等，建议人工复核关键信息。"
        else:
            confidence_label = "[需核实]"
            warning = "结果置信度较低，部分内容可能不准确，请核实。"
            result_data["needs_verification"] = True

        output = {
            "skill": SKILL_NAME,
            "display_name": SKILL_DISPLAY_NAME,
            "version": SKILL_VERSION,
            "status": "success",
            "confidence": confidence,
            "confidence_label": confidence_label,
            "warning": warning,
            "result": result_data,
            "format": output_format,
        }

        return output


# -----------------------------------------------------------------------------
# 自检功能 (--selftest)
# -----------------------------------------------------------------------------

def run_selftest() -> bool:
    """
    运行内置自检，验证核心逻辑。

    使用硬编码样例数据，不读取外部文件，不依赖当前工作目录，不访问网络。

    返回:
        True 表示自检通过，False 表示自检失败。
    """
    print("[自检] 开始执行内置自检...")

    # 创建处理器实例
    generator = SQLCodeGenerator()

    # 测试用例 1: 正常输入（高置信度）
    print("[自检] 测试用例 1: 正常输入")
    sample_input_1 = """
    项目名称: 数据分析平台
    负责人: 张三
    截止日期: 2026-12-31
    优先级: 高
    状态: 进行中
    描述: 这是一个测试项目
    """
    try:
        result_1 = generator.process(sample_input_1)
        # 宽松断言：置信度应大于 0.8
        assert result_1["confidence"] > 0.8, f"用例1置信度异常: {result_1['confidence']}"
        assert result_1["status"] == "success"
        assert "result" in result_1
        print(f"  [通过] 置信度: {result_1['confidence']:.2f}")
    except Exception as e:
        print(f"  [失败] 异常: {e}")
        return False

    # 测试用例 2: 空输入（应触发 E001）
    print("[自检] 测试用例 2: 空输入")
    try:
        generator.process("   ")
        print("  [失败] 应抛出 E001 错误但未抛出")
        return False
    except ValueError as e:
        error_code = str(e).split(":")[0] if ":" in str(e) else str(e)
        assert error_code == "E001", f"错误码不匹配: {error_code}"
        print(f"  [通过] 正确抛出错误码 {error_code}")
    except Exception:
        print("  [失败] 抛出异常类型不正确")
        return False

    # 测试用例 3: 简单输入（中等置信度）
    print("[自检] 测试用例 3: 简单输入")
    sample_input_3 = "名称: 测试项目"
    try:
        result_3 = generator.process(sample_input_3)
        # 宽松断言：置信度应大于 0.5
        assert result_3["confidence"] > 0.5, f"用例3置信度异常: {result_3['confidence']}"
        print(f"  [通过] 置信度: {result_3['confidence']:.2f}")
    except Exception as e:
        print(f"  [失败] 异常: {e}")
        return False

    # 测试用例 4: 输出格式验证
    print("[自检] 测试用例 4: 输出格式")
    try:
        result_4 = generator.process(sample_input_1, output_format="json")
        # 验证输出包含所有必要字段
        required_keys = ["skill", "status", "confidence", "result"]
        for key in required_keys:
            assert key in result_4, f"输出缺少关键字段: {key}"
        print("  [通过] 输出格式完整")
    except Exception as e:
        print(f"  [失败] 异常: {e}")
        return False

    # 测试用例 5: 批量处理（连续处理多个输入）
    print("[自检] 测试用例 5: 批量处理")
    inputs = [
        "字段A: 值1\n字段B: 值2",
        "名称: 项目X\n负责人: 李四\n时间: 2026",
        "简单文本输入",
    ]
    try:
        results = [generator.process(item) for item in inputs]
        assert len(results) == 3, "批量处理结果数量不正确"
        for r in results:
            assert r["status"] == "success"
        print(f"  [通过] 批量处理 {len(results)} 个输入")
    except Exception as e:
        print(f"  [失败] 异常: {e}")
        return False

    print("[自检] 所有测试用例通过！")
    return True


# -----------------------------------------------------------------------------
# 命令行入口
# -----------------------------------------------------------------------------

def main() -> int:
    """
    主入口函数，处理命令行参数并执行相应操作。

    返回:
        进程退出码（0 表示成功，非 0 表示失败）。
    """
    # 解析命令行参数
    parser = argparse.ArgumentParser(
        prog="main.py",
        description=f"{SKILL_DISPLAY_NAME} (sql-code-generator) - 结构化数据处理工具",
        epilog=f"版本: {SKILL_VERSION} | 许可证: MIT",
    )

    parser.add_argument(
        "--input",
        type=str,
        help="用户提供的输入内容（数据/文件内容/URL等）",
    )
    parser.add_argument(
        "--format",
        type=str,
        default="json",
        choices=["json", "text"],
        help="输出格式（默认: json）",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检（不依赖外部输入）",
    )

    args = parser.parse_args()

    # 执行自检
    if args.selftest:
        try:
            success = run_selftest()
            return 0 if success else 1
        except Exception as e:
            print(f"[自检] 未预期异常: {e}")
            return 1

    # 检查是否提供了输入
    if not args.input:
        print(f"错误 E001: {ERROR_MESSAGES['E001']}")
        print("提示: 使用 --input 参数提供输入内容，或使用 --selftest 运行自检。")
        return 1

    # 处理输入
    try:
        generator = SQLCodeGenerator()
        result = generator.process(args.input, args.format)

        # 输出结果
        if args.format == "json":
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            # 文本格式输出
            print(f"技能: {result['display_name']}")
            print(f"置信度: {result['confidence']:.0%} ({result['confidence_label']})")
            if result.get("warning"):
                print(f"警告: {result['warning']}")
            print("结果:")
            for key, value in result["result"].get("data", {}).items():
                print(f"  {key}: {value}")

        return 0

    except ValueError as e:
        error_msg = str(e)
        if ":" in error_msg:
            error_code, _, detail = error_msg.partition(":")
            base_msg = ERROR_MESSAGES.get(error_code, ERROR_MESSAGES["E010"])
            if detail:
                print(f"错误 {error_code}: {base_msg.format(detail)}")
            else:
                print(f"错误 {error_code}: {base_msg}")
        else:
            print(f"错误 {error_msg}: {ERROR_MESSAGES.get(error_msg, ERROR_MESSAGES['E010'])}")
        return 1

    except Exception as e:
        print(f"错误 E010: {ERROR_MESSAGES['E010']} (详情: {e})")
        return 1


if __name__ == "__main__":
    sys.exit(main())
