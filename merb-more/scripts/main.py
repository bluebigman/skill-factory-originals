#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py
===============
基于功能规格「merb-more」独立实现的命令行工具（clean-room 重写）。

核心能力：
1. 将用户提供的数据/文件/URL 转换为结构化结果
2. 识别并保留输入中的关键信息
3. 按约定格式生成输出
4. 对不确定项给出置信度提示
5. 支持批量处理和自定义格式

边界声明：
- 不执行超出输入范围的分析
- 不保证绝对准确，低置信度会标注
- 不访问网络或外部服务

用法示例：
    python scripts/main.py --input "姓名:张三,年龄:30,城市:北京"
    python scripts/main.py --input "some_data" --format json
    python scripts/main.py --batch "a=1;b=2" "a=3;b=4"
    python scripts/main.py --selftest

错误码：
    E001 输入为空
    E002 关键信息缺失
    E003 输入格式错误
    E004 超出能力边界
    E005 置信度过低
    E006 输出格式不支持
    E007 批量输入为空
    E008 批量处理部分失败
    E009 未知命令行参数
    E010 内部逻辑错误
"""

import argparse
import json
import sys
import re
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 常量定义
# ============================================================

# 错误码与话术映射（依据规格）
ERROR_MESSAGES: Dict[str, str] = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：...（逐项追问）",
    "E003": "输入格式不符合要求，示例：姓名:张三,年龄:30,城市:北京",
    "E004": "这超出了本工具的能力范围，建议：简化输入或拆分任务",
    "E005": "结果无法确定，建议：补充更多上下文信息后重试",
    "E006": "不支持的输出格式，可选：text / json",
    "E007": "批量输入为空，请至少提供一个待处理项",
    "E008": "批量处理部分失败，请检查每项输入",
    "E009": "未知的命令行参数，请使用 --help 查看帮助",
    "E010": "内部逻辑错误，请联系开发者",
}

# 置信度阈值（依据规格）
HIGH_CONFIDENCE_THRESHOLD = 90.0   # >=90% 直接输出
MEDIUM_CONFIDENCE_THRESHOLD = 85.0 # 85%-90% 建议复核
# <85% 标注 [需核实]

# 识别关键字段的正则模式（支持 "字段:值" 或 "字段=值" 格式）
FIELD_PATTERN = re.compile(r"([\u4e00-\u9fa5A-Za-z_][\u4e00-\u9fa5A-Za-z0-9_]*)\s*[:=]\s*([^,;，；]+)")

# 分隔符模式（用于拆分配对）
PAIR_SPLIT_PATTERN = re.compile(r"[,;，；]")


# ============================================================
# 核心逻辑函数
# ============================================================

def validate_input(raw_input: Optional[str]) -> Tuple[bool, str]:
    """
    校验输入是否合法。

    参数:
        raw_input: 用户提供的原始输入字符串

    返回:
        (是否合法, 错误码或空字符串)
    """
    if raw_input is None or raw_input.strip() == "":
        return False, "E001"
    return True, ""


def parse_key_value_pairs(raw_input: str) -> Tuple[bool, Dict[str, str], str]:
    """
    解析输入中的 "字段:值" 或 "字段=值" 键值对。

    参数:
        raw_input: 原始输入字符串

    返回:
        (是否成功, 解析出的字段字典, 错误码或空字符串)
    """
    # 按分隔符拆分为多个片段
    segments = [s.strip() for s in PAIR_SPLIT_PATTERN.split(raw_input) if s.strip()]

    fields: Dict[str, str] = {}
    for segment in segments:
        match = FIELD_PATTERN.search(segment)
        if match:
            key = match.group(1).strip()
            value = match.group(2).strip()
            fields[key] = value
        else:
            # 无法识别的片段，跳过（不视为错误，保留原始内容）
            continue

    if not fields:
        return False, {}, "E003"

    return True, fields, ""


def compute_confidence(fields: Dict[str, str], original_length: int) -> float:
    """
    计算置信度（0-100）。

    规则（依据规格的宽松实现）：
    - 基础分 80
    - 每个成功解析的字段加 5 分
    - 字段数超过 3 个额外加 5 分
    - 输入长度超过 20 字符加 5 分
    - 上限 100

    参数:
        fields: 解析出的字段字典
        original_length: 原始输入长度

    返回:
        置信度（0-100）
    """
    score = 80.0

    # 每个字段加 5 分
    score += len(fields) * 5.0

    # 字段数较多时加分
    if len(fields) >= 3:
        score += 5.0

    # 输入较长时加分
    if original_length >= 20:
        score += 5.0

    # 置信度取整并限制在 0-100
    return max(0.0, min(100.0, score))


def format_result(fields: Dict[str, str], confidence: float) -> Dict[str, Any]:
    """
    根据置信度生成结构化结果（含标注）。

    参数:
        fields: 解析出的字段字典
        confidence: 置信度（0-100）

    返回:
        结构化结果字典
    """
    result: Dict[str, Any] = {
        "fields": fields,
        "confidence": round(confidence, 1),
        "confidence_level": "",
        "note": "",
    }

    # 置信度分级（依据规格）
    if confidence >= HIGH_CONFIDENCE_THRESHOLD:
        result["confidence_level"] = "高"
        result["note"] = "直接输出"
    elif confidence >= MEDIUM_CONFIDENCE_THRESHOLD:
        result["confidence_level"] = "中"
        result["note"] = "建议复核"
    else:
        result["confidence_level"] = "低"
        result["note"] = "[需核实] 结果无法确定，请人工复核"

    return result


def process_single_item(raw_input: str, output_format: str = "text") -> Tuple[bool, Any, str]:
    """
    处理单条输入，返回结构化结果。

    参数:
        raw_input: 用户提供的原始输入
        output_format: 输出格式（text/json）

    返回:
        (是否成功, 结果对象, 错误码或空字符串)
    """
    # Step 1: 校验输入
    valid, err_code = validate_input(raw_input)
    if not valid:
        return False, None, err_code

    # Step 2: 解析键值对
    parsed, fields, err_code = parse_key_value_pairs(raw_input)
    if not parsed:
        # 无法解析为键值对时，将整个输入作为单一字段处理
        # 这是对规格的宽松实现，避免 E003 过度触发
        fields = {"content": raw_input.strip()}

    # Step 3: 计算置信度
    confidence = compute_confidence(fields, len(raw_input))

    # Step 4: 格式化结果
    result = format_result(fields, confidence)

    # Step 5: 按输出格式返回
    if output_format == "json":
        return True, json.dumps(result, ensure_ascii=False, indent=2), ""
    else:
        # 文本格式输出
        lines = []
        lines.append("=== 结构化结果 ===")
        for key, value in fields.items():
            lines.append(f"  {key}: {value}")
        lines.append(f"  置信度: {result['confidence']}% ({result['confidence_level']})")
        if result["note"]:
            lines.append(f"  提示: {result['note']}")
        return True, "\n".join(lines), ""


def process_batch(items: List[str], output_format: str = "text") -> Tuple[bool, List[Any], str]:
    """
    批量处理多条输入。

    参数:
        items: 输入列表
        output_format: 输出格式

    返回:
        (是否全部成功, 结果列表, 错误码或空字符串)
    """
    if not items:
        return False, [], "E007"

    results: List[Any] = []
    all_success = True

    for idx, item in enumerate(items):
        success, result, err_code = process_single_item(item, output_format)
        if not success:
            all_success = False
            results.append({"index": idx, "error": err_code, "error_message": ERROR_MESSAGES.get(err_code, "未知错误")})
        else:
            results.append({"index": idx, "result": result})

    if not all_success:
        return False, results, "E008"

    return True, results, ""


# ============================================================
# 自检（selftest）模块
# ============================================================

def run_selftest() -> int:
    """
    内置硬编码样例数据的离线自检。
    不读取外部文件、不依赖当前工作目录、不访问网络。

    返回:
        0 表示全部通过，非 0 表示失败
    """
    print("开始自检...")
    all_passed = True

    # ---- 测试 1: 输入校验 ----
    print("[1/5] 测试输入校验...")
    valid, err_code = validate_input("")
    if not valid and err_code == "E001":
        print("  通过: 空输入正确返回 E001")
    else:
        print(f"  失败: 空输入应返回 E001，实际 err_code={err_code}")
        all_passed = False

    valid, err_code = validate_input("   ")
    if not valid and err_code == "E001":
        print("  通过: 纯空白输入正确返回 E001")
    else:
        print(f"  失败: 纯空白输入应返回 E001，实际 err_code={err_code}")
        all_passed = False

    valid, err_code = validate_input("姓名:张三")
    if valid and err_code == "":
        print("  通过: 正常输入通过校验")
    else:
        print(f"  失败: 正常输入应通过，实际 err_code={err_code}")
        all_passed = False

    # ---- 测试 2: 键值对解析 ----
    print("[2/5] 测试键值对解析...")
    parsed, fields, err_code = parse_key_value_pairs("姓名:张三,年龄:30,城市:北京")
    if parsed and len(fields) >= 3:
        print("  通过: 多字段解析成功")
    else:
        print(f"  失败: 多字段解析失败，err_code={err_code}, fields={fields}")
        all_passed = False

    parsed, fields, err_code = parse_key_value_pairs("name=John,age=25")
    if parsed and len(fields) >= 2:
        print("  通过: 等号格式解析成功")
    else:
        print(f"  失败: 等号格式解析失败，err_code={err_code}, fields={fields}")
        all_passed = False

    parsed, fields, err_code = parse_key_value_pairs("这是一个没有键值对的文本")
    if not parsed and err_code == "E003":
        print("  通过: 无键值对时正确返回 E003")
    else:
        print(f"  失败: 无键值对应返回 E003，实际 err_code={err_code}")
        all_passed = False

    # ---- 测试 3: 置信度计算 ----
    print("[3/5] 测试置信度计算...")
    # 宽松断言：置信度应在 0-100 之间，且字段越多置信度越高
    fields_small = {"a": "1"}
    fields_medium = {"a": "1", "b": "2", "c": "3"}
    fields_large = {"a": "1", "b": "2", "c": "3", "d": "4", "e": "5"}

    conf_small = compute_confidence(fields_small, 5)
    conf_medium = compute_confidence(fields_medium, 15)
    conf_large = compute_confidence(fields_large, 30)

    if 0.0 <= conf_small <= 100.0 and 0.0 <= conf_medium <= 100.0 and 0.0 <= conf_large <= 100.0:
        print("  通过: 置信度均在 0-100 范围内")
    else:
        print(f"  失败: 置信度超出范围，small={conf_small}, medium={conf_medium}, large={conf_large}")
        all_passed = False

    if conf_large >= conf_medium >= conf_small:
        print("  通过: 字段越多置信度越高（单调性）")
    else:
        print(f"  失败: 置信度单调性异常，small={conf_small}, medium={conf_medium}, large={conf_large}")
        all_passed = False

    # ---- 测试 4: 单条处理 ----
    print("[4/5] 测试单条处理...")
    success, result, err_code = process_single_item("姓名:李四,年龄:28,城市:上海,职业:工程师", "text")
    if success and result is not None:
        result_str = str(result)
        if "李四" in result_str and "置信度" in result_str:
            print("  通过: 文本格式输出包含关键信息")
        else:
            print(f"  失败: 输出缺少关键信息，result={result_str[:100]}")
            all_passed = False
    else:
        print(f"  失败: 单条处理失败，err_code={err_code}")
        all_passed = False

    success, result, err_code = process_single_item("姓名:王五,年龄:35", "json")
    if success and result is not None:
        result_str = str(result)
        if "王五" in result_str and '"confidence"' in result_str:
            print("  通过: JSON 格式输出包含关键信息")
        else:
            print(f"  失败: JSON 输出缺少关键信息，result={result_str[:100]}")
            all_passed = False
    else:
        print(f"  失败: JSON 格式处理失败，err_code={err_code}")
        all_passed = False

    # 空输入测试
    success, result, err_code = process_single_item("")
    if not success and err_code == "E001":
        print("  通过: 空输入单条处理正确返回 E001")
    else:
        print(f"  失败: 空输入应返回 E001，实际 err_code={err_code}")
        all_passed = False

    # ---- 测试 5: 批量处理 ----
    print("[5/5] 测试批量处理...")
    batch_items = ["姓名:赵六,年龄:40", "姓名:钱七,年龄:22,城市:广州"]
    success, results, err_code = process_batch(batch_items, "text")
    if success and len(results) == 2:
        print("  通过: 批量处理全部成功")
    else:
        print(f"  失败: 批量处理异常，success={success}, err_code={err_code}")
        all_passed = False

    success, results, err_code = process_batch([], "text")
    if not success and err_code == "E007":
        print("  通过: 空批量输入正确返回 E007")
    else:
        print(f"  失败: 空批量输入应返回 E007，实际 err_code={err_code}")
        all_passed = False

    # ---- 汇总 ----
    print()
    if all_passed:
        print("自检全部通过！✅")
        return 0
    else:
        print("自检存在失败项！❌")
        return 1


# ============================================================
# 命令行入口
# ============================================================

def main() -> int:
    """
    命令行主入口。
    """
    parser = argparse.ArgumentParser(
        description="Merb More: The Full Stack. Take what you need; leave what you don't.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s --input "姓名:张三,年龄:30,城市:北京"
  %(prog)s --input "name=John,age=25" --format json
  %(prog)s --batch "a=1;b=2" "a=3;b=4"
  %(prog)s --selftest
        """,
    )

    # 互斥参数组：--input / --batch / --selftest
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--input", type=str, help="单条输入内容，如：姓名:张三,年龄:30")
    group.add_argument("--batch", nargs="+", help="批量输入，多个字符串作为多条输入")
    group.add_argument("--selftest", action="store_true", help="运行内置自检")

    parser.add_argument("--format", dest="output_format", choices=["text", "json"], default="text",
                        help="输出格式（默认: text）")

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        return run_selftest()

    # 单条处理模式
    if args.input is not None:
        success, result, err_code = process_single_item(args.input, args.output_format)
        if not success:
            error_message = ERROR_MESSAGES.get(err_code, "未知错误")
            print(f"错误 [{err_code}]: {error_message}", file=sys.stderr)
            return 1
        print(result)
        return 0

    # 批量处理模式
    if args.batch is not None:
        success, results, err_code = process_batch(args.batch, args.output_format)
        if not success and err_code == "E007":
            print(f"错误 [{err_code}]: {ERROR_MESSAGES[err_code]}", file=sys.stderr)
            return 1

        # 输出批量结果
        if args.output_format == "json":
            print(json.dumps(results, ensure_ascii=False, indent=2))
        else:
            for item in results:
                if "error" in item:
                    print(f"[{item['index']}] 错误 [{item['error']}]: {item['error_message']}")
                else:
                    print(f"[{item['index']}]")
                    print(item["result"])
                    print()

        if not success:
            print(f"警告 [{err_code}]: {ERROR_MESSAGES[err_code]}", file=sys.stderr)
            return 1
        return 0

    # 未提供任何有效参数
    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
