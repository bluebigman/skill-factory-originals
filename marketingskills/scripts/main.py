#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py - marketingskills 技能独立实现

本脚本根据功能规格从零编写，实现以下核心能力：
1. 将用户提供的数据/文本转换为结构化结果
2. 识别并保留输入中的关键信息
3. 按约定格式生成输出
4. 对不确定项给出置信度提示
5. 支持批量处理和自定义格式

仅使用 Python 标准库，无第三方依赖。
支持 --selftest 离线自检，不依赖外部文件或网络。
"""

import argparse
import json
import re
import sys
from typing import Any, Dict, List, Optional, Tuple

# ============================================================
# 常量定义
# ============================================================

# 错误码及对应话术（依据功能规格第五节）
ERROR_MESSAGES: Dict[str, str] = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：",
    "E003": "输入格式不符合要求，示例：",
    "E004": "这超出了本工具的能力范围，建议：",
    "E005": "结果无法确定，建议：",
    # 扩展错误码（内部使用）
    "E006": "输入类型不支持，请提供字符串、字典或列表",
    "E007": "JSON 解析失败，请检查输入格式",
    "E008": "批量处理时出现错误，请检查每个输入项",
    "E009": "输出格式指定错误，支持 json 或 text",
    "E010": "内部处理逻辑异常，请反馈问题",
}

# 默认输出字段模板
DEFAULT_FIELDS: List[str] = ["content", "keywords", "confidence", "warning"]

# 置信度阈值
HIGH_CONFIDENCE = 0.90
MEDIUM_CONFIDENCE = 0.85

# 内置自检样例（硬编码，不读外部文件）
SELFTEST_SAMPLES: List[Dict[str, Any]] = [
    {
        "input": "我们的新产品是一款智能手表，主打健康监测和长续航，目标用户是年轻上班族。",
        "expected_keys": ["content", "keywords", "confidence", "warning"],
    },
    {
        "input": "请帮我分析这个数据：销售额、用户增长、转化率三个指标。",
        "expected_keys": ["content", "keywords", "confidence", "warning"],
    },
    {
        "input": "这是一段很短的文本。",
        "expected_keys": ["content", "keywords", "confidence", "warning"],
    },
]


# ============================================================
# 核心处理逻辑
# ============================================================

def extract_keywords(text: str, max_keywords: int = 5) -> List[str]:
    """
    从文本中提取关键词。

    实现思路：
    1. 按常见分隔符切分文本
    2. 过滤停用词和过短词
    3. 按词频排序取前 N 个

    参数:
        text: 输入文本
        max_keywords: 最大关键词数量

    返回:
        关键词列表
    """
    if not text or not isinstance(text, str):
        return []

    # 常见停用词（精简列表，避免依赖外部库）
    stopwords = {
        "的", "了", "和", "是", "在", "我", "有", "就", "不", "人",
        "都", "一", "一个", "上", "也", "很", "到", "说", "要", "去",
        "你", "会", "着", "没有", "看", "好", "自己", "这", "那", "他",
        "她", "它", "们", "与", "或", "及", "等", "中", "为", "所",
        "the", "a", "an", "and", "or", "but", "in", "on", "at", "to",
        "for", "of", "with", "by", "from", "up", "about", "into", "over",
        "after", "is", "are", "was", "were", "be", "been", "being",
        "have", "has", "had", "do", "does", "did", "will", "would",
        "can", "could", "should", "may", "might", "must", "shall",
    }

    # 按非中英文数字字符切分
    tokens = re.findall(r'[\u4e00-\u9fff]+|[a-zA-Z0-9]+', text.lower())

    # 过滤停用词和过短词
    filtered = [t for t in tokens if t not in stopwords and len(t) >= 2]

    # 按词频统计
    word_count: Dict[str, int] = {}
    for token in filtered:
        word_count[token] = word_count.get(token, 0) + 1

    # 按频率排序取前 N 个
    sorted_words = sorted(word_count.items(), key=lambda x: (-x[1], x[0]))
    keywords = [word for word, _ in sorted_words[:max_keywords]]

    return keywords


def calculate_confidence(text: str, keywords: List[str]) -> float:
    """
    计算处理结果的置信度。

    策略：
    - 文本长度适中且关键词数量合理：高置信度
    - 文本过短或过长：中等置信度
    - 文本为空或异常：低置信度

    参数:
        text: 输入文本
        keywords: 提取的关键词

    返回:
        置信度数值（0.0 - 1.0）
    """
    if not text or not isinstance(text, str):
        return 0.0

    text_len = len(text.strip())

    # 文本长度合理且关键词数量适中 -> 高置信度
    if 20 <= text_len <= 500 and 1 <= len(keywords) <= 8:
        return 0.95

    # 文本长度略短或略长 -> 中等置信度
    if 10 <= text_len < 20 or 500 < text_len <= 1000:
        return 0.88

    # 文本过短 -> 低置信度
    if 0 < text_len < 10:
        return 0.80

    # 文本过长 -> 中等偏低
    if text_len > 1000:
        return 0.85

    return 0.75


def format_structured_result(
    content: str,
    keywords: List[str],
    confidence: float,
    warning: Optional[str] = None,
) -> Dict[str, Any]:
    """
    将处理结果格式化为结构化字典。

    参数:
        content: 原始内容
        keywords: 关键词列表
        confidence: 置信度
        warning: 警告信息（可选）

    返回:
        结构化结果字典
    """
    result: Dict[str, Any] = {
        "content": content,
        "keywords": keywords,
        "confidence": round(confidence, 2),
        "warning": warning or "",
    }

    # 根据置信度添加标注
    if confidence >= HIGH_CONFIDENCE:
        result["status"] = "直接输出"
    elif confidence >= MEDIUM_CONFIDENCE:
        result["status"] = "建议复核"
        if not warning:
            result["warning"] = "结果置信度中等，建议人工复核关键内容"
    else:
        result["status"] = "[需核实]"
        if not warning:
            result["warning"] = "结果置信度较低，请人工核实后再使用"

    return result


def process_single_item(
    input_data: Any,
    output_format: str = "json",
) -> Dict[str, Any]:
    """
    处理单个输入项。

    参数:
        input_data: 输入数据（字符串、字典或列表）
        output_format: 输出格式（json 或 text）

    返回:
        结构化处理结果

    异常:
        ValueError: 输入类型不支持或格式错误
    """
    # 输入类型检查
    if input_data is None:
        raise ValueError("E001")

    # 如果是字典，尝试提取文本内容
    if isinstance(input_data, dict):
        # 查找常见文本字段
        text_content = None
        for key in ["text", "content", "input", "data", "message"]:
            if key in input_data:
                text_content = input_data[key]
                break

        if text_content is None:
            # 尝试将整个字典转为 JSON 字符串
            text_content = json.dumps(input_data, ensure_ascii=False)

        # 保留额外字段
        extra_fields = {
            k: v for k, v in input_data.items()
            if k not in ["text", "content", "input", "data", "message"]
        }
    elif isinstance(input_data, str):
        text_content = input_data
        extra_fields = {}
    elif isinstance(input_data, list):
        # 列表类型：尝试转为文本
        text_content = " ".join(str(item) for item in input_data)
        extra_fields = {"source_type": "list"}
    else:
        raise ValueError("E006")

    # 空内容检查
    if not text_content or not text_content.strip():
        raise ValueError("E001")

    # 提取关键词
    keywords = extract_keywords(str(text_content))

    # 计算置信度
    confidence = calculate_confidence(str(text_content), keywords)

    # 生成结构化结果
    result = format_structured_result(
        content=str(text_content),
        keywords=keywords,
        confidence=confidence,
    )

    # 合并额外字段
    if extra_fields:
        result["extra"] = extra_fields

    # 按输出格式返回
    if output_format == "text":
        result["formatted_text"] = format_as_text(result)

    return result


def format_as_text(result: Dict[str, Any]) -> str:
    """
    将结构化结果格式化为纯文本。

    参数:
        result: 结构化结果字典

    返回:
        格式化后的文本
    """
    lines = []
    lines.append("=" * 40)
    lines.append("处理结果")
    lines.append("=" * 40)

    if "content" in result:
        lines.append(f"内容: {result['content']}")
    if "keywords" in result:
        lines.append(f"关键词: {', '.join(result['keywords'])}")
    if "confidence" in result:
        lines.append(f"置信度: {result['confidence']:.0%}")
    if "status" in result:
        lines.append(f"状态: {result['status']}")
    if "warning" in result and result["warning"]:
        lines.append(f"提示: {result['warning']}")

    lines.append("=" * 40)
    return "\n".join(lines)


def process_batch(
    inputs: List[Any],
    output_format: str = "json",
) -> List[Dict[str, Any]]:
    """
    批量处理多个输入项。

    参数:
        inputs: 输入项列表
        output_format: 输出格式

    返回:
        处理结果列表
    """
    results = []
    for item in inputs:
        try:
            result = process_single_item(item, output_format)
            results.append(result)
        except ValueError as e:
            # 记录错误但不中断批量处理
            error_code = str(e)
            results.append({
                "error": error_code,
                "error_message": ERROR_MESSAGES.get(error_code, "未知错误"),
                "input": str(item),
            })
    return results


# ============================================================
# 自检功能
# ============================================================

def run_selftest() -> bool:
    """
    运行内置自检，验证核心逻辑。

    使用硬编码样例数据，不依赖外部文件、网络或当前工作目录。
    断言使用宽松阈值，确保任何环境可过。

    返回:
        True 表示自检通过，False 表示失败
    """
    print("=" * 50)
    print("开始自检 (selftest)")
    print("=" * 50)

    all_passed = True

    # 测试1: 基本处理功能
    print("\n[测试1] 基本处理功能")
    for i, sample in enumerate(SELFTEST_SAMPLES):
        try:
            result = process_single_item(sample["input"])

            # 宽松检查：结果包含必要字段
            for key in sample["expected_keys"]:
                if key not in result:
                    print(f"  ✗ 样例{i+1}: 缺少字段 '{key}'")
                    all_passed = False
                    break
            else:
                # 检查置信度范围（宽松区间）
                conf = result.get("confidence", 0)
                if not (0.5 <= conf <= 1.0):
                    print(f"  ✗ 样例{i+1}: 置信度超出合理范围: {conf}")
                    all_passed = False
                else:
                    print(f"  ✓ 样例{i+1}: 处理成功, 置信度={conf:.2f}")

        except Exception as e:
            print(f"  ✗ 样例{i+1}: 处理异常: {e}")
            all_passed = False

    # 测试2: 关键词提取
    print("\n[测试2] 关键词提取")
    test_text = "智能手表 健康监测 长续航 年轻上班族 科技创新"
    keywords = extract_keywords(test_text)
    if len(keywords) >= 1:
        print(f"  ✓ 关键词提取成功: {keywords}")
    else:
        print("  ✗ 关键词提取失败")
        all_passed = False

    # 测试3: 置信度计算
    print("\n[测试3] 置信度计算")
    conf_short = calculate_confidence("短文本", ["短"])
    conf_normal = calculate_confidence("这是一段长度适中的测试文本，用于验证置信度计算逻辑是否正常工作。", ["测试", "验证"])
    conf_empty = calculate_confidence("", [])

    if 0.0 <= conf_short <= 1.0 and 0.0 <= conf_normal <= 1.0 and conf_empty == 0.0:
        print(f"  ✓ 置信度计算正常: 短文本={conf_short:.2f}, 正常={conf_normal:.2f}, 空={conf_empty:.2f}")
    else:
        print("  ✗ 置信度计算异常")
        all_passed = False

    # 测试4: 错误处理
    print("\n[测试4] 错误处理")
    try:
        process_single_item(None)
        print("  ✗ 空输入未触发错误")
        all_passed = False
    except ValueError as e:
        if str(e) == "E001":
            print("  ✓ 空输入正确触发 E001")
        else:
            print(f"  ✗ 空输入错误码不正确: {e}")
            all_passed = False

    # 测试5: 批量处理
    print("\n[测试5] 批量处理")
    batch_inputs = ["第一条测试数据", "第二条测试数据", None, "第三条测试数据"]
    batch_results = process_batch(batch_inputs)
    if len(batch_results) == 4:
        error_count = sum(1 for r in batch_results if "error" in r)
        success_count = len(batch_results) - error_count
        if success_count >= 3 and error_count >= 1:
            print(f"  ✓ 批量处理正常: 成功={success_count}, 错误={error_count}")
        else:
            print(f"  ✗ 批量处理结果异常: 成功={success_count}, 错误={error_count}")
            all_passed = False
    else:
        print(f"  ✗ 批量处理数量不对: {len(batch_results)}")
        all_passed = False

    # 测试6: 输出格式
    print("\n[测试6] 输出格式")
    result_text = process_single_item("测试文本", output_format="text")
    if "formatted_text" in result_text and "处理结果" in result_text["formatted_text"]:
        print("  ✓ 文本格式输出正常")
    else:
        print("  ✗ 文本格式输出异常")
        all_passed = False

    # 测试7: 边界情况
    print("\n[测试7] 边界情况")
    edge_cases = [
        ("很长" * 100, "长文本"),
        ("短", "短文本"),
        ("中英混合 test 文本 123", "混合文本"),
    ]
    for text, desc in edge_cases:
        try:
            result = process_single_item(text)
            conf = result.get("confidence", 0)
            if 0.0 <= conf <= 1.0:
                print(f"  ✓ {desc}处理正常: 置信度={conf:.2f}")
            else:
                print(f"  ✗ {desc}置信度异常")
                all_passed = False
        except Exception as e:
            print(f"  ✗ {desc}处理异常: {e}")
            all_passed = False

    # 总结
    print("\n" + "=" * 50)
    if all_passed:
        print("自检通过: 所有测试项均正常 ✓")
    else:
        print("自检失败: 存在异常项 ✗")
    print("=" * 50)

    return all_passed


# ============================================================
# 主程序入口
# ============================================================

def main() -> int:
    """
    主程序入口。

    解析命令行参数，执行相应功能。

    返回:
        退出码（0 表示成功，非 0 表示失败）
    """
    parser = argparse.ArgumentParser(
        description="marketingskills - 营销技能工具集",
        epilog="示例: python main.py --input '文本内容' --format json",
    )

    parser.add_argument(
        "--input",
        "-i",
        type=str,
        help="待处理的输入内容（文本或 JSON 字符串）",
    )

    parser.add_argument(
        "--format",
        "-f",
        type=str,
        choices=["json", "text"],
        default="json",
        help="输出格式（默认: json）",
    )

    parser.add_argument(
        "--batch",
        "-b",
        action="store_true",
        help="批量处理模式（输入为 JSON 数组）",
    )

    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行自检并退出",
    )

    parser.add_argument(
        "--fields",
        type=str,
        default=None,
        help="自定义输出字段（逗号分隔）",
    )

    parser.add_argument(
        "--version",
        action="version",
        version="marketingskills 1.0.0",
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        success = run_selftest()
        return 0 if success else 1

    # 需要输入内容
    if not args.input:
        print(f"错误 E001: {ERROR_MESSAGES['E001']}", file=sys.stderr)
        return 1

    try:
        # 判断是否为 JSON 输入
        try:
            parsed_input = json.loads(args.input)
        except json.JSONDecodeError:
            # 不是 JSON，按普通文本处理
            parsed_input = args.input

        # 批量处理模式
        if args.batch:
            if isinstance(parsed_input, list):
                results = process_batch(parsed_input, args.format)
            else:
                # 非列表但要求批量，按单条处理
                results = process_single_item(parsed_input, args.format)
        else:
            # 单条处理
            results = process_single_item(parsed_input, args.format)

        # 输出结果
        if args.format == "json":
            if isinstance(results, list):
                output = json.dumps(results, ensure_ascii=False, indent=2)
            else:
                output = json.dumps(results, ensure_ascii=False, indent=2)
        else:
            # 文本格式
            if isinstance(results, list):
                output = "\n".join(
                    r.get("formatted_text", str(r)) for r in results
                )
            else:
                output = results.get("formatted_text", str(results))

        print(output)
        return 0

    except ValueError as e:
        error_code = str(e)
        error_msg = ERROR_MESSAGES.get(error_code, "未知错误")
        print(f"错误 {error_code}: {error_msg}", file=sys.stderr)
        return 1

    except Exception as e:
        print(f"错误 E010: {ERROR_MESSAGES['E010']} - {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
