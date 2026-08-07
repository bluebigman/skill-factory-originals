#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py
全新独立实现：awesome-growth-hacking-skills 技能核心逻辑
仅依据功能规格编写，不参考任何既有代码。
"""

import argparse
import json
import re
import sys
from typing import Any, Dict, List, Optional, Tuple


# ------------------------------------------------------------
# 错误码与话术映射（依据规格第四节）
# ------------------------------------------------------------
ERROR_MESSAGES: Dict[str, str] = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：输入来源、输出格式、期望完整度",
    "E003": "输入格式不符合要求，示例：{'source': '...', 'format': '...', 'completeness': '...'}",
    "E004": "这超出了本工具的能力范围，建议简化需求或咨询专业人士",
    "E005": "结果无法确定，建议：补充更多信息或人工复核",
    "E006": "内部处理异常，请重试或检查输入",
    "E007": "JSON 解析失败，请检查输入是否为合法 JSON",
    "E008": "置信度计算异常，请检查输入数据",
    "E009": "输出渲染失败，请检查字段配置",
    "E010": "未知错误，请联系管理员",
}


class GrowthHackingError(Exception):
    """业务异常，携带错误码"""

    def __init__(self, code: str, message: Optional[str] = None):
        self.code = code
        self.message = message or ERROR_MESSAGES.get(code, ERROR_MESSAGES["E010"])
        super().__init__(self.message)


# ------------------------------------------------------------
# 核心数据结构
# ------------------------------------------------------------
class InputData:
    """标准化输入对象"""

    def __init__(self, source: Any, output_format: str, completeness: str):
        self.source = source
        self.output_format = output_format
        self.completeness = completeness

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source,
            "output_format": self.output_format,
            "completeness": self.completeness,
        }


class ProcessedResult:
    """处理结果对象"""

    def __init__(self, fields: Dict[str, Any], confidence: float, warnings: List[str]):
        self.fields = fields
        self.confidence = confidence
        self.warnings = warnings

    def to_dict(self) -> Dict[str, Any]:
        return {
            "fields": self.fields,
            "confidence": self.confidence,
            "warnings": self.warnings,
        }


# ------------------------------------------------------------
# 核心处理逻辑（依据规格第三节）
# ------------------------------------------------------------
def validate_input(raw_input: Any) -> InputData:
    """Step 1: 收集最小信息集，校验输入完整性

    参数:
        raw_input: 原始输入，支持 dict 或 JSON 字符串

    返回:
        标准化 InputData 对象

    异常:
        E001: 输入为空
        E002: 关键信息缺失
        E003: 输入格式错误
        E007: JSON 解析失败
    """
    # 空值检查
    if raw_input is None or (isinstance(raw_input, str) and not raw_input.strip()):
        raise GrowthHackingError("E001")

    # 解析 JSON 字符串
    if isinstance(raw_input, str):
        try:
            raw_input = json.loads(raw_input)
        except json.JSONDecodeError:
            raise GrowthHackingError("E007")

    # 类型检查
    if not isinstance(raw_input, dict):
        raise GrowthHackingError("E003")

    # 关键字段检查
    required_keys = ["source", "output_format", "completeness"]
    missing = [k for k in required_keys if k not in raw_input]
    if missing:
        raise GrowthHackingError("E002")

    source = raw_input["source"]
    output_format = raw_input["output_format"]
    completeness = raw_input["completeness"]

    # 字段非空检查
    if not source or not output_format or not completeness:
        raise GrowthHackingError("E002")

    # 格式合法检查
    if not isinstance(output_format, str) or not output_format.strip():
        raise GrowthHackingError("E003")
    if not isinstance(completeness, str) or completeness not in ("快速骨架", "详细成品"):
        raise GrowthHackingError("E003")

    return InputData(source=source, output_format=output_format, completeness=completeness)


def extract_key_fields(source: Any) -> Tuple[Dict[str, Any], float]:
    """Step 2.1: 从输入源中提取关键字段

    参数:
        source: 输入源，可以是任意类型

    返回:
        (字段字典, 置信度)
    """
    fields: Dict[str, Any] = {}
    confidence = 0.0
    warnings: List[str] = []

    # 处理字符串输入
    if isinstance(source, str):
        text = source.strip()
        if not text:
            warnings.append("输入源为空字符串")
            confidence = 0.0
            return fields, confidence

        # 尝试识别 URL
        url_pattern = r'^https?://[^\s]+$'
        if re.match(url_pattern, text):
            fields["type"] = "URL"
            fields["content"] = text
            confidence = 0.95
        else:
            # 尝试识别 JSON
            try:
                parsed = json.loads(text)
                fields["type"] = "JSON"
                fields["content"] = parsed
                confidence = 0.9
            except json.JSONDecodeError:
                # 普通文本
                fields["type"] = "text"
                fields["content"] = text
                confidence = 0.7
                warnings.append("文本内容无法完全结构化，建议人工复核")

    # 处理字典输入
    elif isinstance(source, dict):
        if "content" in source:
            fields["type"] = "dict"
            fields["content"] = source["content"]
            confidence = 0.85
        else:
            fields["type"] = "dict"
            fields["content"] = source
            confidence = 0.75
            warnings.append("字典结构不标准，部分字段可能遗漏")

    # 处理列表输入
    elif isinstance(source, list):
        if len(source) > 0:
            fields["type"] = "list"
            fields["content"] = source
            fields["count"] = len(source)
            confidence = 0.8
        else:
            warnings.append("列表为空")
            confidence = 0.0

    # 其他类型
    else:
        fields["type"] = type(source).__name__
        fields["content"] = str(source)
        confidence = 0.5
        warnings.append("输入类型不常见，结构化程度较低")

    # 置信度修正：有警告时降低置信度
    if warnings:
        confidence = max(0.0, confidence - 0.1 * len(warnings))

    return fields, confidence


def format_output(fields: Dict[str, Any], output_format: str, completeness: str) -> Dict[str, Any]:
    """Step 2.2: 按指定格式组织输出

    参数:
        fields: 提取的字段字典
        output_format: 输出格式（如 json/yaml/text）
        completeness: 完整度（快速骨架/详细成品）

    返回:
        格式化后的输出字典
    """
    # 默认模板组织
    output = {
        "metadata": {
            "tool": "awesome-growth-hacking-skills",
            "version": "1.0.0",
            "output_format": output_format,
            "completeness": completeness,
        },
        "data": fields,
    }

    # 快速骨架：只保留核心字段
    if completeness == "快速骨架":
        output["data"] = {
            k: v for k, v in fields.items() if k in ("type", "content")
        }
        output["metadata"]["skeleton"] = True

    # 详细成品：保留全部字段
    else:
        output["metadata"]["skeleton"] = False

    return output


def calculate_confidence(fields: Dict[str, Any], base_confidence: float) -> float:
    """Step 2.3: 计算最终置信度

    参数:
        fields: 字段字典
        base_confidence: 基础置信度

    返回:
        0-1 之间的置信度
    """
    if not fields:
        return 0.0

    # 字段完整度修正
    expected_keys = {"type", "content"}
    present_keys = set(fields.keys())
    completeness_ratio = len(present_keys & expected_keys) / len(expected_keys)

    # 综合置信度
    final_confidence = base_confidence * (0.7 + 0.3 * completeness_ratio)

    # 限制在 [0, 1] 区间
    return max(0.0, min(1.0, final_confidence))


def add_confidence_marker(result: Dict[str, Any], confidence: float) -> Dict[str, Any]:
    """Step 2.4: 根据置信度添加标注

    参数:
        result: 处理结果字典
        confidence: 置信度值

    返回:
        带标注的结果字典
    """
    if confidence >= 0.9:
        result["confidence_label"] = "直接输出"
    elif confidence >= 0.85:
        result["confidence_label"] = "建议复核"
    else:
        result["confidence_label"] = "[需核实]"
        result["uncertainty_note"] = "置信度低于85%，请人工复核关键结果"

    result["confidence"] = round(confidence, 2)
    return result


def process_input(raw_input: Any) -> Dict[str, Any]:
    """Step 2: 执行核心处理流程（主入口）

    参数:
        raw_input: 原始输入

    返回:
        处理完成的结果字典
    """
    try:
        # 1. 校验输入
        input_data = validate_input(raw_input)

        # 2. 提取关键字段
        fields, base_confidence = extract_key_fields(input_data.source)

        # 3. 格式化输出
        result = format_output(fields, input_data.output_format, input_data.completeness)

        # 4. 计算置信度
        confidence = calculate_confidence(fields, base_confidence)

        # 5. 添加置信度标注
        result = add_confidence_marker(result, confidence)

        return result

    except GrowthHackingError:
        raise
    except Exception as e:
        raise GrowthHackingError("E006") from e


# ------------------------------------------------------------
# 输出与校验（依据规格第三节 Step 3）
# ------------------------------------------------------------
def render_output(result: Dict[str, Any], output_format: str) -> str:
    """Step 3: 将结果渲染为指定格式

    参数:
        result: 处理结果字典
        output_format: 输出格式

    返回:
        渲染后的字符串
    """
    try:
        if output_format.lower() == "json":
            return json.dumps(result, ensure_ascii=False, indent=2)
        elif output_format.lower() == "text":
            # 简单文本渲染
            lines = []
            for key, value in result.items():
                if isinstance(value, dict):
                    lines.append(f"{key}:")
                    for sub_key, sub_value in value.items():
                        lines.append(f"  {sub_key}: {sub_value}")
                else:
                    lines.append(f"{key}: {value}")
            return "\n".join(lines)
        else:
            # 默认 JSON
            return json.dumps(result, ensure_ascii=False, indent=2)
    except Exception as e:
        raise GrowthHackingError("E009") from e


def self_check(result: Dict[str, Any]) -> List[str]:
    """Step 3.2: 自查结果质量

    参数:
        result: 处理结果字典

    返回:
        问题列表，空列表表示无问题
    """
    issues = []

    # 字段完整性检查
    required_keys = ["data", "confidence", "confidence_label"]
    for key in required_keys:
        if key not in result:
            issues.append(f"缺少必需字段: {key}")

    # 置信度范围检查
    if "confidence" in result:
        conf = result["confidence"]
        if not (0.0 <= conf <= 1.0):
            issues.append(f"置信度超出范围: {conf}")

    # 标注一致性检查
    if "confidence" in result and "confidence_label" in result:
        conf = result["confidence"]
        label = result["confidence_label"]
        if conf >= 0.9 and label != "直接输出":
            issues.append("置信度≥90%但标注不是'直接输出'")
        elif 0.85 <= conf < 0.9 and label != "建议复核":
            issues.append("置信度85%-90%但标注不是'建议复核'")
        elif conf < 0.85 and label != "[需核实]":
            issues.append("置信度<85%但标注不是'[需核实]'")

    return issues


# ------------------------------------------------------------
# 主流程（命令行入口）
# ------------------------------------------------------------
def run_pipeline(raw_input: Any, output_format: str = "json") -> Dict[str, Any]:
    """完整处理流程：输入 -> 处理 -> 校验 -> 输出

    参数:
        raw_input: 原始输入
        output_format: 输出格式

    返回:
        最终输出字典
    """
    # 处理
    result = process_input(raw_input)

    # 自查
    issues = self_check(result)
    if issues:
        result["self_check_issues"] = issues

    # 渲染
    rendered = render_output(result, output_format)
    result["_rendered"] = rendered

    return result


# ------------------------------------------------------------
# 自检模块（依据规格要求）
# ------------------------------------------------------------
def run_selftest() -> bool:
    """内置硬编码样例数据离线自检核心逻辑

    返回:
        True 表示全部通过，否则抛出异常
    """
    print("开始自检...")

    # 样例 1: 标准 JSON 输入
    sample1 = {
        "source": {"content": {"title": "测试", "body": "内容"}},
        "output_format": "json",
        "completeness": "详细成品"
    }
    result1 = process_input(sample1)
    assert result1["data"]["type"] == "dict", "样例1类型识别失败"
    assert 0.0 <= result1["confidence"] <= 1.0, "样例1置信度范围异常"
    print("✓ 样例1（标准JSON输入）通过")

    # 样例 2: URL 输入
    sample2 = {
        "source": "https://example.com/page",
        "output_format": "text",
        "completeness": "快速骨架"
    }
    result2 = process_input(sample2)
    assert result2["data"]["type"] == "URL", "样例2类型识别失败"
    assert result2["data"]["content"].startswith("http"), "样例2内容异常"
    print("✓ 样例2（URL输入）通过")

    # 样例 3: 列表输入
    sample3 = {
        "source": ["item1", "item2", "item3"],
        "output_format": "json",
        "completeness": "详细成品"
    }
    result3 = process_input(sample3)
    assert result3["data"]["type"] == "list", "样例3类型识别失败"
    assert result3["data"]["count"] >= 2, "样例3列表长度异常"
    print("✓ 样例3（列表输入）通过")

    # 样例 4: 空输入应报错
    try:
        process_input(None)
        assert False, "样例4未抛出异常"
    except GrowthHackingError as e:
        assert e.code == "E001", f"样例4错误码异常: {e.code}"
    print("✓ 样例4（空输入错误处理）通过")

    # 样例 5: 缺失字段应报错
    try:
        process_input({"source": "测试"})
        assert False, "样例5未抛出异常"
    except GrowthHackingError as e:
        assert e.code == "E002", f"样例5错误码异常: {e.code}"
    print("✓ 样例5（缺失字段错误处理）通过")

    # 样例 6: 完整流程与渲染
    sample6 = {
        "source": "这是一段普通文本",
        "output_format": "text",
        "completeness": "快速骨架"
    }
    pipeline_result = run_pipeline(sample6, "text")
    assert "_rendered" in pipeline_result, "样例6渲染失败"
    assert len(pipeline_result["_rendered"]) > 0, "样例6渲染结果为空"
    print("✓ 样例6（完整流程）通过")

    # 样例 7: 置信度标注逻辑
    sample7 = {
        "source": {"content": "数据"},
        "output_format": "json",
        "completeness": "详细成品"
    }
    result7 = process_input(sample7)
    conf = result7["confidence"]
    label = result7["confidence_label"]
    if conf >= 0.9:
        assert label == "直接输出", "样例7高置信度标注错误"
    elif conf >= 0.85:
        assert label == "建议复核", "样例7中置信度标注错误"
    else:
        assert label == "[需核实]", "样例7低置信度标注错误"
    print("✓ 样例7（置信度标注）通过")

    # 样例 8: 自查功能
    sample8 = {
        "source": "测试数据",
        "output_format": "json",
        "completeness": "详细成品"
    }
    result8 = process_input(sample8)
    issues = self_check(result8)
    assert isinstance(issues, list), "样例8自查返回类型错误"
    print("✓ 样例8（自查功能）通过")

    print("全部自检通过！")
    return True


# ------------------------------------------------------------
# 命令行入口
# ------------------------------------------------------------
def main() -> int:
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description="awesome-growth-hacking-skills 技能工具",
        epilog="示例: python main.py --input '{\"source\": \"数据\", \"output_format\": \"json\", \"completeness\": \"详细成品\"}'"
    )
    parser.add_argument(
        "--input",
        type=str,
        help="输入内容（JSON字符串），需包含 source/output_format/completeness 字段"
    )
    parser.add_argument(
        "--format",
        type=str,
        default="json",
        choices=["json", "text"],
        help="输出格式（默认: json）"
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检（不读外部文件、不依赖工作目录、不访问网络）"
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        try:
            run_selftest()
            return 0
        except AssertionError as e:
            print(f"自检失败: {e}", file=sys.stderr)
            return 1
        except Exception as e:
            print(f"自检异常: {e}", file=sys.stderr)
            return 1

    # 正常处理模式
    if not args.input:
        print(f"错误 [E001]: {ERROR_MESSAGES['E001']}", file=sys.stderr)
        return 1

    try:
        result = run_pipeline(args.input, args.format)
        print(result["_rendered"])
        return 0
    except GrowthHackingError as e:
        print(f"错误 [{e.code}]: {e.message}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"错误 [E010]: {ERROR_MESSAGES['E010']} - {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
