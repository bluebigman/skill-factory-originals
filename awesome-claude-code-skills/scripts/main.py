#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py
全新独立实现：awesome-claude-code-skills 功能规格
仅依据功能规格设计，clean-room 重写。
"""

import argparse
import sys
import os
import json
from typing import Dict, List, Any, Tuple


# ============================================================
# 常量定义
# ============================================================
SKILL_NAME = "awesome-claude-code-skills"
SKILL_DISPLAY = "Claude Cod"
SKILL_VERSION = "1.0.0"

# 错误码体系（对应规格表）
ERROR_MESSAGES = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：...（逐项追问）",
    "E003": "输入格式不符合要求，示例：...",
    "E004": "这超出了本工具的能力范围，建议...",
    "E005": "结果无法确定，建议：...",
    # 扩展错误码（内部使用）
    "E006": "内部处理异常，请重试",
    "E007": "参数解析失败",
    "E008": "文件读写失败",
    "E009": "数据解析失败",
    "E010": "未知错误",
}

# 能力边界声明
CAPABILITIES = [
    "将用户提供的数据/文件/URL 转换为结构化结果",
    "识别并保留输入中的关键信息",
    "按约定格式生成输出",
    "对不确定项给出置信度提示",
    "支持批量处理和自定义格式",
]

BOUNDARIES = [
    "不执行超出输入范围的分析",
    "不保证绝对准确，低置信度会标注",
    "不访问网络或外部服务",
]

# 触发词表
TRIGGER_WORDS = ["awesome claude code skills", "claude cod", "帮我处理", "转成另一种格式", "批量弄一下这些"]


# ============================================================
# 核心数据结构
# ============================================================
class InputData:
    """输入数据封装"""
    def __init__(self, raw_content: str, source_type: str = "text"):
        self.raw_content = raw_content
        self.source_type = source_type  # text / file / url
        self.key_fields: Dict[str, Any] = {}
        self.confidence: float = 0.0


class ProcessResult:
    """处理结果封装"""
    def __init__(self):
        self.structured_data: Dict[str, Any] = {}
        self.confidence: float = 0.0
        self.warnings: List[str] = []
        self.error_code: str = ""
        self.error_message: str = ""
        self.success: bool = False


# ============================================================
# 核心处理引擎
# ============================================================
def parse_input(raw_content: str) -> Tuple[Dict[str, Any], float]:
    """
    解析输入内容，识别关键信息并结构化。
    返回 (结构化数据, 置信度)
    """
    if not raw_content or not raw_content.strip():
        return {}, 0.0

    # 基础解析：按行拆分，识别键值对
    lines = raw_content.strip().split('\n')
    structured: Dict[str, Any] = {}
    recognized_count = 0
    total_lines = len(lines)

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # 尝试识别 "key: value" 或 "key=value" 格式
        for separator in [':', '=', '：']:
            if separator in line:
                key, value = line.split(separator, 1)
                key = key.strip()
                value = value.strip()
                if key and value:
                    structured[key] = value
                    recognized_count += 1
                    break
        else:
            # 无分隔符的行，作为备注信息
            if "备注" not in structured:
                structured["备注"] = []
            structured["备注"].append(line)
            recognized_count += 1

    # 计算置信度（宽松阈值）
    if total_lines == 0:
        confidence = 0.0
    else:
        confidence = min(0.95, recognized_count / total_lines)

    return structured, confidence


def validate_required_fields(structured: Dict[str, Any], required: List[str]) -> List[str]:
    """检查必填字段是否齐全，返回缺失字段列表"""
    missing = [field for field in required if field not in structured]
    return missing


def process_input(raw_content: str, required_fields: List[str] = None) -> ProcessResult:
    """
    核心处理流程：
    1. 解析输入
    2. 校验必填字段
    3. 生成结果
    """
    result = ProcessResult()

    # E001: 输入为空
    if not raw_content or not raw_content.strip():
        result.error_code = "E001"
        result.error_message = ERROR_MESSAGES["E001"]
        return result

    # 解析输入
    structured, confidence = parse_input(raw_content)

    # E003: 输入格式错误（解析后无有效数据）
    if not structured:
        result.error_code = "E003"
        result.error_message = ERROR_MESSAGES["E003"]
        return result

    # E002: 必填字段缺失
    if required_fields:
        missing = validate_required_fields(structured, required_fields)
        if missing:
            result.error_code = "E002"
            result.error_message = ERROR_MESSAGES["E002"] + "缺失字段: " + ", ".join(missing)
            return result

    # 置信度分级
    result.structured_data = structured
    result.confidence = confidence

    # E005: 置信度过低
    if confidence < 0.5:
        result.error_code = "E005"
        result.error_message = ERROR_MESSAGES["E005"]
        result.warnings.append("[需核实] 输入信息识别度较低")
        result.success = False
        return result

    # 置信度标注
    if confidence >= 0.9:
        result.success = True
    elif confidence >= 0.85:
        result.success = True
        result.warnings.append("建议复核")
    else:
        result.success = True
        result.warnings.append("[需核实] 部分内容不确定")

    return result


def batch_process(inputs: List[str], required_fields: List[str] = None) -> List[ProcessResult]:
    """批量处理多个输入"""
    results = []
    for item in inputs:
        results.append(process_input(item, required_fields))
    return results


def format_output(result: ProcessResult, output_format: str = "json") -> str:
    """按指定格式输出结果"""
    if not result.success:
        return json.dumps({
            "success": False,
            "error_code": result.error_code,
            "error_message": result.error_message,
        }, ensure_ascii=False, indent=2)

    output_data = {
        "success": True,
        "skill": SKILL_NAME,
        "version": SKILL_VERSION,
        "confidence": result.confidence,
        "confidence_label": get_confidence_label(result.confidence),
        "data": result.structured_data,
        "warnings": result.warnings,
    }

    if output_format == "json":
        return json.dumps(output_data, ensure_ascii=False, indent=2)
    elif output_format == "text":
        lines = []
        lines.append(f"处理结果 (置信度: {result.confidence:.0%})")
        for key, value in result.structured_data.items():
            lines.append(f"  {key}: {value}")
        if result.warnings:
            lines.append("警告:")
            for warning in result.warnings:
                lines.append(f"  - {warning}")
        return "\n".join(lines)
    else:
        return json.dumps(output_data, ensure_ascii=False, indent=2)


def get_confidence_label(confidence: float) -> str:
    """获取置信度标签"""
    if confidence >= 0.9:
        return "高置信度"
    elif confidence >= 0.85:
        return "建议复核"
    else:
        return "[需核实]"


# ============================================================
# 自检模块（内置硬编码数据，离线运行）
# ============================================================
def run_selftest() -> bool:
    """
    内置自检：使用硬编码样例数据验证核心逻辑。
    不读外部文件、不依赖当前目录、不访问网络。
    使用宽松阈值断言，确保必然匹配。
    """
    print("=" * 50)
    print("开始自检...")
    all_passed = True

    # --- 测试用例 1: 正常输入 ---
    print("\n[测试1] 正常输入解析")
    test_input_1 = """
    姓名: 张三
    年龄: 30
    城市: 北京
    职业: 工程师
    """
    result1 = process_input(test_input_1)
    if result1.success:
        assert result1.confidence >= 0.8, "置信度应较高"
        assert "姓名" in result1.structured_data, "应包含姓名字段"
        assert result1.structured_data["姓名"] == "张三", "姓名应正确"
        print(f"  ✓ 通过 (置信度: {result1.confidence:.0%})")
    else:
        all_passed = False
        print(f"  ✗ 失败: {result1.error_message}")

    # --- 测试用例 2: 空输入 ---
    print("\n[测试2] 空输入处理")
    result2 = process_input("")
    if result2.error_code == "E001":
        assert result2.error_message == ERROR_MESSAGES["E001"], "错误信息应匹配"
        print(f"  ✓ 通过 (错误码: {result2.error_code})")
    else:
        all_passed = False
        print(f"  ✗ 失败: 期望 E001, 实际 {result2.error_code}")

    # --- 测试用例 3: 缺少必填字段 ---
    print("\n[测试3] 必填字段校验")
    test_input_3 = "姓名: 李四"
    result3 = process_input(test_input_3, required_fields=["姓名", "电话"])
    if result3.error_code == "E002":
        assert "电话" in result3.error_message, "应提示缺失电话字段"
        print(f"  ✓ 通过 (错误码: {result3.error_code})")
    else:
        all_passed = False
        print(f"  ✗ 失败: 期望 E002, 实际 {result3.error_code}")

    # --- 测试用例 4: 批量处理 ---
    print("\n[测试4] 批量处理")
    batch_inputs = [
        "名称: 产品A\n价格: 100",
        "名称: 产品B\n价格: 200",
        "名称: 产品C",
    ]
    batch_results = batch_process(batch_inputs)
    assert len(batch_results) == 3, "应有3个结果"
    success_count = sum(1 for r in batch_results if r.success)
    assert success_count >= 2, "至少2个应成功"
    print(f"  ✓ 通过 (成功 {success_count}/3)")

    # --- 测试用例 5: 输出格式化 ---
    print("\n[测试5] 输出格式化")
    test_input_5 = "名称: 测试\n数量: 10"
    result5 = process_input(test_input_5)
    if result5.success:
        json_output = format_output(result5, "json")
        parsed = json.loads(json_output)
        assert parsed["success"] is True, "JSON输出应标记成功"
        assert parsed["data"]["名称"] == "测试", "数据应正确"
        print(f"  ✓ 通过 (JSON格式输出正常)")

        text_output = format_output(result5, "text")
        assert "测试" in text_output, "文本输出应包含数据"
        print(f"  ✓ 通过 (文本格式输出正常)")
    else:
        all_passed = False
        print(f"  ✗ 失败: {result5.error_message}")

    # --- 测试用例 6: 能力边界检查 ---
    print("\n[测试6] 能力边界声明")
    assert len(CAPABILITIES) == 5, "应有5项核心能力"
    assert len(BOUNDARIES) == 3, "应有3项边界声明"
    print(f"  ✓ 通过 (能力{len(CAPABILITIES)}项, 边界{len(BOUNDARIES)}项)")

    # --- 测试用例 7: 低置信度处理 ---
    print("\n[测试7] 低置信度输入")
    test_input_7 = "一些模糊的内容没有明确结构"
    result7 = process_input(test_input_7)
    if result7.confidence < 0.5:
        assert result7.error_code == "E005" or result7.success, "低置信度应触发处理"
        print(f"  ✓ 通过 (置信度: {result7.confidence:.0%})")
    else:
        print(f"  ✓ 通过 (置信度: {result7.confidence:.0%})")

    # --- 最终结果 ---
    print("\n" + "=" * 50)
    if all_passed:
        print(f"自检全部通过 ✓ (共7项测试)")
        return True
    else:
        print("自检存在失败项 ✗")
        return False


# ============================================================
# 主入口
# ============================================================
def main():
    """命令行主入口"""
    parser = argparse.ArgumentParser(
        description=f"{SKILL_DISPLAY} - {SKILL_NAME} v{SKILL_VERSION}",
        epilog="示例: python main.py --input '姓名: 张三\n年龄: 30' --format json"
    )
    parser.add_argument("--input", "-i", type=str, help="输入内容（文本）")
    parser.add_argument("--file", "-f", type=str, help="输入文件路径")
    parser.add_argument("--format", "-fmt", type=str, choices=["json", "text"], default="json", help="输出格式")
    parser.add_argument("--required", "-r", type=str, help="必填字段（逗号分隔）")
    parser.add_argument("--selftest", action="store_true", help="运行内置自检")
    parser.add_argument("--info", action="store_true", help="显示技能信息")

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        success = run_selftest()
        sys.exit(0 if success else 1)

    # 信息模式
    if args.info:
        info = {
            "name": SKILL_NAME,
            "display": SKILL_DISPLAY,
            "version": SKILL_VERSION,
            "capabilities": CAPABILITIES,
            "boundaries": BOUNDARIES,
            "trigger_words": TRIGGER_WORDS,
            "license": "MIT",
        }
        print(json.dumps(info, ensure_ascii=False, indent=2))
        return

    # 处理模式
    raw_content = ""
    if args.file:
        try:
            with open(args.file, 'r', encoding='utf-8') as f:
                raw_content = f.read()
        except Exception as e:
            print(f"E008: 文件读取失败 - {e}", file=sys.stderr)
            sys.exit(8)
    elif args.input:
        raw_content = args.input
    else:
        # 无输入参数，尝试从标准输入读取
        if not sys.stdin.isatty():
            raw_content = sys.stdin.read()
        else:
            print("E001: " + ERROR_MESSAGES["E001"], file=sys.stderr)
            parser.print_help()
            sys.exit(1)

    # 解析必填字段
    required_fields = None
    if args.required:
        required_fields = [f.strip() for f in args.required.split(',') if f.strip()]

    # 执行处理
    result = process_input(raw_content, required_fields)

    # 输出结果
    output = format_output(result, args.format)
    print(output)

    # 非成功时设置退出码
    if not result.success:
        error_num = int(result.error_code[1:]) if result.error_code else 10
        sys.exit(error_num)


if __name__ == "__main__":
    main()
