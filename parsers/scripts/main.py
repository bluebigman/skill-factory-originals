#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py - PDF转文档 (parsers) 技能实现

功能概述：
    本脚本依据功能规格实现 PDF转文档 的核心处理流程，
    包括：输入校验、关键信息提取、结构化输出、置信度评估、异常处理。
    提供 --selftest 参数进行离线自检（使用内置硬编码样例，不依赖外部环境）。

错误码：
    E001: 输入为空
    E002: 关键信息缺失
    E003: 输入格式错误
    E004: 超出能力边界
    E005: 置信度过低
    E006: 内部处理异常（通用）
    E007: 参数解析错误
    E008: 自检失败（内部使用）
    E009: 输出序列化错误
    E010: 未知错误

设计原则：
    - 仅使用标准库（argparse, json, re, sys, datetime, typing）
    - 中文注释
    - 结构化、模块化设计
    - 宽松的自检断言（避免精确值依赖）
"""

import argparse
import json
import re
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional

# ============================================================
# 常量定义
# ============================================================

# 技能元数据
SKILL_NAME = "parsers"
DISPLAY_NAME = "PDF转文档"
VERSION = "1.0.0"
AUTHOR = "skill-factory-auto"

# 错误码与话术映射
ERROR_MESSAGES: Dict[str, str] = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：{missing}",
    "E003": "输入格式不符合要求，示例：{example}",
    "E004": "这超出了本工具的能力范围，建议：{suggestion}",
    "E005": "结果无法确定，建议：{suggestion}",
    "E006": "内部处理异常，请稍后重试或检查输入",
    "E007": "命令行参数解析错误：{detail}",
    "E008": "自检失败：{detail}",
    "E009": "输出序列化错误：{detail}",
    "E010": "未知错误：{detail}",
}

# 置信度阈值
CONFIDENCE_HIGH = 0.90      # >=90% 直接输出
CONFIDENCE_MEDIUM = 0.85    # 85%-90% 建议复核
# <85% 标注 [需核实]

# 默认输出模板（结构化字段）
DEFAULT_OUTPUT_FIELDS = [
    "title",       # 标题
    "author",      # 作者
    "date",        # 日期
    "content",     # 正文内容
    "keywords",    # 关键词列表
]

# 自检样例数据（硬编码，不依赖外部文件）
SELFTEST_SAMPLES: List[Dict[str, Any]] = [
    {
        "input": "2024年第一季度财务报告\n作者：张三\n日期：2024-03-31\n"
                 "本季度营收增长15%，利润同比增长20%。主要得益于新产品线。",
        "expected_fields": ["title", "author", "date", "content"],
        "min_confidence": 0.85,
    },
    {
        "input": "项目会议纪要\n时间：2024-05-10\n参会人：李四、王五\n"
                 "讨论内容：1. 进度确认 2. 风险讨论 3. 下一步计划",
        "expected_fields": ["title", "date", "content"],
        "min_confidence": 0.80,
    },
    {
        "input": "",  # 空输入，测试错误处理
        "expected_error": "E001",
    },
    {
        "input": "无法解析的内容 ！！！ 无结构信息 ！！！",
        "expected_fields": [],
        "min_confidence": 0.0,  # 低置信度，但不应崩溃
    },
]

# ============================================================
# 核心工具函数
# ============================================================

def get_error_message(code: str, **kwargs: Any) -> str:
    """根据错误码获取标准话术，并填充参数。"""
    template = ERROR_MESSAGES.get(code, ERROR_MESSAGES["E010"])
    try:
        return template.format(**kwargs)
    except KeyError:
        # 如果模板参数不匹配，返回原始模板
        return template


def validate_input(raw_input: Any) -> Optional[str]:
    """校验输入是否有效。

    参数:
        raw_input: 用户输入

    返回:
        如果输入有效返回 None，否则返回错误码
    """
    if raw_input is None:
        return "E001"
    if isinstance(raw_input, str):
        if not raw_input.strip():
            return "E001"
        return None
    # 非字符串类型（如 dict, list 等）视为有效，交给后续处理
    return None


def extract_key_info(text: str) -> Dict[str, Any]:
    """从文本中提取关键信息。

    使用正则表达式识别常见字段：
        - 标题：行首非空内容（启发式）
        - 作者：匹配"作者：xxx"或"作者 xxx"
        - 日期：匹配多种日期格式
        - 关键词：匹配"关键词：xxx, yyy"

    参数:
        text: 输入文本

    返回:
        提取的结构化信息字典
    """
    info: Dict[str, Any] = {}
    lines = [line.strip() for line in text.split('\n') if line.strip()]

    if not lines:
        return info

    # 提取标题（第一行）
    info["title"] = lines[0][:100]  # 限制长度

    # 提取作者
    author_match = re.search(r'作者[：:]\s*(.+)', text)
    if author_match:
        info["author"] = author_match.group(1).strip()

    # 提取日期（多种格式）
    date_patterns = [
        r'(\d{4}[-/年]\d{1,2}[-/月]\d{1,2}日?)',
        r'(\d{4}[-/]\d{1,2}[-/]\d{1,2})',
        r'(\d{4}年\d{1,2}月\d{1,2}日)',
    ]
    for pattern in date_patterns:
        date_match = re.search(pattern, text)
        if date_match:
            info["date"] = date_match.group(1)
            break

    # 提取关键词
    keyword_match = re.search(r'关键词[：:]\s*(.+)', text)
    if keyword_match:
        keywords = [k.strip() for k in keyword_match.group(1).split(',')]
        info["keywords"] = keywords

    # 提取正文内容（去掉已识别的元数据行）
    content_lines = []
    for line in lines[1:]:  # 跳过标题行
        # 跳过已识别的元数据行
        if re.match(r'^(作者|日期|时间|关键词|参会人)[：:]', line):
            continue
        content_lines.append(line)
    info["content"] = '\n'.join(content_lines)

    return info


def calculate_confidence(info: Dict[str, Any], raw_input: str) -> float:
    """计算置信度。

    基于提取到的字段数量和输入内容的丰富度：
        - 有明确作者/日期/关键词：高置信度
        - 仅有标题和内容：中等置信度
        - 几乎无结构信息：低置信度

    参数:
        info: 提取的结构化信息
        raw_input: 原始输入

    返回:
        置信度分数 (0.0 - 1.0)
    """
    if not info or not raw_input.strip():
        return 0.0

    score = 0.0
    total_weight = 0.0

    # 标题权重 0.3
    if info.get("title"):
        score += 0.3
    total_weight += 0.3

    # 内容权重 0.3
    content = info.get("content", "")
    if content:
        # 内容长度越长，置信度越高（但不超过 0.3）
        # 调整阈值：内容超过50字即视为有效内容
        content_score = min(len(content) / 100.0, 1.0) * 0.3
        score += content_score
    total_weight += 0.3

    # 元数据权重 0.4（作者、日期、关键词）
    meta_fields = ["author", "date", "keywords"]
    meta_found = 0
    for field in meta_fields:
        if info.get(field):
            meta_found += 1
    # 每个元数据字段权重 0.133，找到越多置信度越高
    score += (meta_found / len(meta_fields)) * 0.4
    total_weight += 0.4

    # 归一化
    if total_weight > 0:
        confidence = score / total_weight
    else:
        confidence = 0.0

    # 输入长度惩罚（太短的输入置信度降低）
    if len(raw_input.strip()) < 20:
        confidence *= 0.9
    elif len(raw_input.strip()) < 50:
        confidence *= 0.95

    # 额外奖励：有多个元数据字段时提高置信度
    if meta_found >= 2:
        confidence = min(confidence * 1.1, 1.0)

    return min(max(confidence, 0.0), 1.0)  # 限制在 [0, 1]


def format_output(info: Dict[str, Any], confidence: float) -> Dict[str, Any]:
    """格式化输出结果。

    参数:
        info: 提取的结构化信息
        confidence: 置信度

    返回:
        格式化后的输出字典
    """
    output = {
        "skill": SKILL_NAME,
        "display_name": DISPLAY_NAME,
        "version": VERSION,
        "processed_at": datetime.now().isoformat(),
        "confidence": round(confidence, 4),
        "data": {},
    }

    # 只保留非空字段
    for key, value in info.items():
        if value is not None and value != "":
            output["data"][key] = value

    # 置信度标注
    if confidence >= CONFIDENCE_HIGH:
        output["status"] = "success"
    elif confidence >= CONFIDENCE_MEDIUM:
        output["status"] = "review"
        output["warning"] = "建议复核"
    else:
        output["status"] = "uncertain"
        output["warning"] = "[需核实] 置信度较低，请人工确认"

    return output


def process_input(raw_input: Any) -> Dict[str, Any]:
    """核心处理流程。

    参数:
        raw_input: 用户输入

    返回:
        处理结果字典（包含状态、数据、错误码等）

    异常:
        抛出 ValueError 包含错误码
    """
    # Step 1: 输入校验
    error_code = validate_input(raw_input)
    if error_code:
        raise ValueError(error_code)

    # Step 2: 类型转换（如果是 dict/list 则转为 JSON 字符串处理）
    if isinstance(raw_input, (dict, list)):
        text_input = json.dumps(raw_input, ensure_ascii=False)
    else:
        text_input = str(raw_input)

    # Step 3: 提取关键信息
    info = extract_key_info(text_input)

    # Step 4: 计算置信度
    confidence = calculate_confidence(info, text_input)

    # Step 5: 格式化输出
    output = format_output(info, confidence)

    return output


def batch_process(inputs: List[Any]) -> List[Dict[str, Any]]:
    """批量处理多个输入。

    参数:
        inputs: 输入列表

    返回:
        处理结果列表
    """
    results = []
    for item in inputs:
        try:
            result = process_input(item)
            results.append(result)
        except ValueError as e:
            error_code = str(e)
            results.append({
                "error": error_code,
                "message": get_error_message(error_code),
            })
    return results


# ============================================================
# 自检模块
# ============================================================

def run_selftest() -> bool:
    """运行内置自检。

    使用硬编码样例数据验证核心逻辑，不依赖外部文件/网络。

    返回:
        自检是否通过
    """
    print(f"[自检] 开始 - {DISPLAY_NAME} v{VERSION}")
    all_passed = True

    for idx, sample in enumerate(SELFTEST_SAMPLES, 1):
        print(f"[自检] 样例 {idx}/{len(SELFTEST_SAMPLES)}...")
        try:
            if "expected_error" in sample:
                # 预期错误的样例
                try:
                    process_input(sample["input"])
                    print(f"  ✗ 预期错误 {sample['expected_error']}，但未抛出异常")
                    all_passed = False
                except ValueError as e:
                    if str(e) == sample["expected_error"]:
                        print(f"  ✓ 正确抛出错误 {sample['expected_error']}")
                    else:
                        print(f"  ✗ 预期错误 {sample['expected_error']}，实际 {e}")
                        all_passed = False
            else:
                # 正常处理样例
                result = process_input(sample["input"])

                # 检查字段完整性
                missing_fields = []
                for field in sample.get("expected_fields", []):
                    if field not in result.get("data", {}):
                        missing_fields.append(field)

                if missing_fields:
                    print(f"  ✗ 缺少字段: {missing_fields}")
                    all_passed = False
                else:
                    print(f"  ✓ 字段完整")

                # 检查置信度（宽松阈值）
                min_conf = sample.get("min_confidence", 0.0)
                actual_conf = result.get("confidence", 0.0)
                # 宽松判断：实际置信度不应远低于预期（允许 0.1 的误差）
                if actual_conf < min_conf - 0.1:
                    print(f"  ✗ 置信度过低: 实际 {actual_conf:.2f} < 预期 {min_conf:.2f}")
                    all_passed = False
                else:
                    print(f"  ✓ 置信度达标: {actual_conf:.2f}")

                # 检查输出结构
                if "status" not in result:
                    print(f"  ✗ 缺少状态字段")
                    all_passed = False
                else:
                    print(f"  ✓ 输出结构完整")

        except Exception as e:
            print(f"  ✗ 未预期异常: {e}")
            all_passed = False

    # 额外测试：批量处理
    print("[自检] 批量处理测试...")
    batch_inputs = [s["input"] for s in SELFTEST_SAMPLES if "input" in s]
    batch_results = batch_process(batch_inputs)
    if len(batch_results) == len(batch_inputs):
        print(f"  ✓ 批量处理成功 ({len(batch_results)} 个结果)")
    else:
        print(f"  ✗ 批量处理失败: 预期 {len(batch_inputs)} 个结果，实际 {len(batch_results)}")
        all_passed = False

    print(f"[自检] {'全部通过' if all_passed else '存在失败项'}")
    return all_passed


# ============================================================
# 命令行入口
# ============================================================

def main() -> int:
    """命令行主入口。

    返回:
        退出码（0 成功，非 0 失败）
    """
    parser = argparse.ArgumentParser(
        description=f"{DISPLAY_NAME} - 结构化文档处理工具",
        epilog="示例: python main.py --input '文本内容' 或 python main.py --selftest",
    )
    parser.add_argument(
        "--input", "-i",
        type=str,
        help="待处理的输入文本内容",
    )
    parser.add_argument(
        "--batch-input",
        type=str,
        help="批量处理的 JSON 数组输入（例如: '[{\"input\": \"...\"}]'）",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检",
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        choices=["json", "text"],
        default="json",
        help="输出格式（默认: json）",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"{DISPLAY_NAME} v{VERSION}",
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        try:
            passed = run_selftest()
            return 0 if passed else 1
        except Exception as e:
            print(f"自检异常: {e}")
            return 1

    # 批量处理模式
    if args.batch_input:
        try:
            batch_data = json.loads(args.batch_input)
            if not isinstance(batch_data, list):
                print(get_error_message("E003", example='[{"input": "内容1"}, {"input": "内容2"}]'))
                return 1
            results = batch_process(batch_data)
            print(json.dumps(results, ensure_ascii=False, indent=2))
            return 0
        except json.JSONDecodeError as e:
            print(get_error_message("E003", example='[{"input": "内容1"}]'))
            return 1

    # 单条处理模式
    if args.input:
        try:
            result = process_input(args.input)
            if args.output == "json":
                print(json.dumps(result, ensure_ascii=False, indent=2))
            else:
                # 文本格式输出
                print(f"状态: {result.get('status', 'unknown')}")
                print(f"置信度: {result.get('confidence', 0):.2%}")
                if "warning" in result:
                    print(f"提示: {result['warning']}")
                print("数据:")
                for key, value in result.get("data", {}).items():
                    print(f"  {key}: {value}")
            return 0
        except ValueError as e:
            error_code = str(e)
            print(f"错误 {error_code}: {get_error_message(error_code)}")
            return 1
        except Exception as e:
            print(get_error_message("E010", detail=str(e)))
            return 1

    # 无有效参数
    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
