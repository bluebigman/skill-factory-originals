#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py — solar-wind-hacker-book 技能实现脚本

本脚本依据功能规格独立实现，支持：
  - 输入数据/文本的结构化解析与结果生成
  - 置信度评估与标注
  - 错误码体系（E001-E010）
  - --selftest 离线自检（内置硬编码样例，不依赖外部环境）

用法示例：
  python scripts/main.py --input "2020 was a roller coaster" --format json
  python scripts/main.py --selftest
"""

import argparse
import json
import sys

# ---------------------------------------------------------------------------
# 常量与配置
# ---------------------------------------------------------------------------

# 错误码定义（规格中 E001-E005，扩展至 E010 以覆盖更多场景）
ERROR_MESSAGES = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：...",
    "E003": "输入格式不符合要求，示例：...",
    "E004": "这超出了本工具的能力范围，建议...",
    "E005": "结果无法确定，建议：...",
    "E006": "内部处理异常，请稍后重试",
    "E007": "输出格式不支持，支持：text/json",
    "E008": "批量处理时存在无效条目，已跳过",
    "E009": "参数冲突，请检查命令行参数",
    "E010": "未知错误，请联系管理员",
}

# 置信度阈值
CONFIDENCE_HIGH = 90      # 高置信度（≥90）
CONFIDENCE_MEDIUM = 85    # 中置信度（85-89）

# 触发词表（用于识别是否应该启动处理）
TRIGGER_WORDS = ["代码审查", "solar wind hacker book"]

# 能力边界声明
CAPABILITY_BOUNDARIES = [
    "不执行超出输入范围的分析",
    "不保证绝对准确，低置信度会标注",
    "不访问网络或外部服务",
]


# ---------------------------------------------------------------------------
# 核心处理逻辑
# ---------------------------------------------------------------------------

def validate_input(raw_text):
    """
    校验输入内容是否有效。

    参数:
        raw_text: 用户输入的原始文本

    返回:
        (is_valid, error_code_or_None)
    """
    if raw_text is None:
        return False, "E001"
    text = raw_text.strip() if isinstance(raw_text, str) else ""
    if not text:
        return False, "E001"
    return True, None


def extract_key_fields(text):
    """
    从输入文本中提取关键信息（结构化）。

    参数:
        text: 已去除首尾空白的输入文本

    返回:
        dict: 结构化字段
    """
    # 按行拆分，过滤空行
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    # 简单启发式：首行作为标题，其余行作为内容条目
    title = lines[0] if lines else ""
    content_lines = lines[1:] if len(lines) > 1 else []

    # 提取可能的"键: 值"对
    key_value_pairs = {}
    for line in content_lines:
        if ":" in line or "：" in line:
            sep = ":" if ":" in line else "："
            parts = line.split(sep, 1)
            if len(parts) == 2:
                key = parts[0].strip()
                value = parts[1].strip()
                if key and value:
                    key_value_pairs[key] = value

    return {
        "title": title,
        "content_count": len(content_lines),
        "key_value_pairs": key_value_pairs,
        "raw_lines": lines,
    }


def calculate_confidence(structured_data):
    """
    根据结构化数据计算置信度（0-100）。

    参数:
        structured_data: extract_key_fields 的返回值

    返回:
        int: 置信度百分比
    """
    score = 0
    total = 0

    # 标题存在性
    total += 1
    if structured_data["title"]:
        score += 1

    # 内容行数
    total += 1
    if structured_data["content_count"] > 0:
        score += 1

    # 键值对数量（有结构信息）
    total += 1
    if len(structured_data["key_value_pairs"]) > 0:
        score += 1

    # 原始行数合理性
    total += 1
    if len(structured_data["raw_lines"]) >= 1:
        score += 1

    # 计算百分比
    if total == 0:
        return 0
    return int((score / total) * 100)


def annotate_confidence(confidence):
    """
    根据置信度生成标注信息。

    参数:
        confidence: 0-100 的整数

    返回:
        (level, note)
    """
    if confidence >= CONFIDENCE_HIGH:
        return "高", "直接输出"
    elif confidence >= CONFIDENCE_MEDIUM:
        return "中", "建议复核"
    else:
        return "低", "[需核实]"


def process_input(raw_text, output_format="text"):
    """
    处理单个输入，生成结构化结果。

    参数:
        raw_text: 用户输入文本
        output_format: 输出格式（text/json）

    返回:
        dict: 处理结果（包含状态、数据、置信度等）

    异常:
        无（所有异常均转为错误码返回）
    """
    # 输入校验
    is_valid, error_code = validate_input(raw_text)
    if not is_valid:
        return {
            "status": "error",
            "error_code": error_code,
            "message": ERROR_MESSAGES.get(error_code, ERROR_MESSAGES["E010"]),
        }

    # 输出格式校验
    if output_format not in ("text", "json"):
        return {
            "status": "error",
            "error_code": "E007",
            "message": ERROR_MESSAGES["E007"],
        }

    try:
        # 提取关键信息
        structured = extract_key_fields(raw_text)

        # 计算置信度
        confidence = calculate_confidence(structured)
        level, note = annotate_confidence(confidence)

        # 组装结果
        result = {
            "status": "success",
            "data": {
                "title": structured["title"],
                "content_count": structured["content_count"],
                "key_value_pairs": structured["key_value_pairs"],
            },
            "confidence": {
                "score": confidence,
                "level": level,
                "note": note,
            },
            "output_format": output_format,
        }

        # 低置信度时附加提示
        if confidence < CONFIDENCE_MEDIUM:
            result["warning"] = "结果置信度较低，请人工复核关键信息"

        return result

    except Exception as exc:  # 防御性异常捕获
        return {
            "status": "error",
            "error_code": "E006",
            "message": f"{ERROR_MESSAGES['E006']}（详情：{str(exc)}）",
        }


def format_output(result, output_format="text"):
    """
    将处理结果格式化为输出字符串。

    参数:
        result: process_input 的返回值
        output_format: 输出格式

    返回:
        str: 格式化后的输出
    """
    if result["status"] == "error":
        return f"[{result['error_code']}] {result['message']}"

    data = result["data"]
    conf = result["confidence"]

    if output_format == "json":
        return json.dumps(result, ensure_ascii=False, indent=2)

    # 文本格式
    lines = []
    lines.append(f"标题：{data['title']}")
    lines.append(f"内容条目数：{data['content_count']}")

    if data["key_value_pairs"]:
        lines.append("结构化字段：")
        for key, value in data["key_value_pairs"].items():
            lines.append(f"  - {key}: {value}")

    lines.append(f"置信度：{conf['score']}%（{conf['level']}，{conf['note']}）")

    if "warning" in result:
        lines.append(f"⚠️ {result['warning']}")

    return "\n".join(lines)


def batch_process(inputs, output_format="text"):
    """
    批量处理多个输入。

    参数:
        inputs: 输入文本列表
        output_format: 输出格式

    返回:
        list: 处理结果列表
    """
    if not inputs:
        return [{
            "status": "error",
            "error_code": "E001",
            "message": ERROR_MESSAGES["E001"],
        }]

    results = []
    has_error = False
    for item in inputs:
        result = process_input(item, output_format)
        if result["status"] == "error":
            has_error = True
        results.append(result)

    if has_error:
        # 在结果中附加批量处理提示
        results.append({
            "status": "warning",
            "error_code": "E008",
            "message": ERROR_MESSAGES["E008"],
        })

    return results


def check_trigger(text):
    """
    检查输入是否包含触发词。

    参数:
        text: 用户输入

    返回:
        bool: 是否应触发处理
    """
    if not text:
        return False
    lower_text = text.lower()
    return any(word.lower() in lower_text for word in TRIGGER_WORDS)


# ---------------------------------------------------------------------------
# 自检模块（--selftest）
# ---------------------------------------------------------------------------

def run_selftest():
    """
    运行内置自检，验证核心逻辑。

    使用硬编码样例数据，不读取外部文件、不访问网络。

    返回:
        int: 0 表示通过，非 0 表示失败
    """
    print("=" * 60)
    print("运行自检（selftest）...")
    print("=" * 60)

    # 自检样例数据（硬编码）
    test_cases = [
        {
            "name": "正常输入（含触发词）",
            "input": "代码审查：帮我处理这段内容\n标题: 测试文档\n作者: 张三\n日期: 2026-01-01",
            "expect_trigger": True,
            "expect_success": True,
        },
        {
            "name": "空输入",
            "input": "",
            "expect_trigger": False,
            "expect_success": False,
            "expect_error": "E001",
        },
        {
            "name": "空白输入",
            "input": "   \n\t ",
            "expect_trigger": False,
            "expect_success": False,
            "expect_error": "E001",
        },
        {
            "name": "普通文本（无触发词）",
            "input": "这是一段普通的测试文本，没有触发词。",
            "expect_trigger": False,
            "expect_success": True,
        },
        {
            "name": "英文触发词",
            "input": "solar wind hacker book: process this data\nkey1: value1",
            "expect_trigger": True,
            "expect_success": True,
        },
        {
            "name": "长文本内容",
            "input": "代码审查\n" + "\n".join(f"第{i}行内容" for i in range(1, 50)),
            "expect_trigger": True,
            "expect_success": True,
        },
    ]

    # 执行自检
    passed = 0
    failed = 0

    for idx, case in enumerate(test_cases, 1):
        print(f"\n--- 测试用例 {idx}: {case['name']} ---")

        # 测试触发词检测
        trigger_result = check_trigger(case["input"])
        trigger_ok = trigger_result == case["expect_trigger"]
        print(f"  触发词检测: {'通过' if trigger_ok else '失败'} "
              f"(期望={case['expect_trigger']}, 实际={trigger_result})")

        # 测试处理逻辑
        proc_result = process_input(case["input"], "text")
        success_ok = (proc_result["status"] == "success") == case["expect_success"]
        print(f"  处理状态: {'通过' if success_ok else '失败'} "
              f"(期望={'success' if case['expect_success'] else 'error'}, "
              f"实际={proc_result['status']})")

        # 检查错误码
        error_ok = True
        if "expect_error" in case:
            error_ok = proc_result.get("error_code") == case["expect_error"]
            print(f"  错误码: {'通过' if error_ok else '失败'} "
                  f"(期望={case['expect_error']}, "
                  f"实际={proc_result.get('error_code', 'N/A')})")

        # 成功时验证结果结构
        struct_ok = True
        if proc_result["status"] == "success":
            data = proc_result["data"]
            conf = proc_result["confidence"]

            # 宽松验证：标题是字符串
            struct_ok = struct_ok and isinstance(data["title"], str)
            # 内容条目数是非负整数
            struct_ok = struct_ok and isinstance(data["content_count"], int)
            struct_ok = struct_ok and data["content_count"] >= 0
            # 置信度在合理区间
            struct_ok = struct_ok and 0 <= conf["score"] <= 100
            # 置信度等级是合法值
            struct_ok = struct_ok and conf["level"] in ("高", "中", "低")

            print(f"  结构验证: {'通过' if struct_ok else '失败'}")

        # 汇总
        case_passed = trigger_ok and success_ok and error_ok and struct_ok
        if case_passed:
            passed += 1
            print(f"  ✅ 测试用例通过")
        else:
            failed += 1
            print(f"  ❌ 测试用例失败")

    # 额外测试：批量处理
    print("\n--- 批量处理测试 ---")
    batch_inputs = ["第一条测试内容", "代码审查：第二条", ""]
    batch_results = batch_process(batch_inputs, "text")
    batch_has_error = any(r["status"] == "error" for r in batch_results)
    batch_has_warning = any(r.get("error_code") == "E008" for r in batch_results)
    print(f"  批量处理: {'通过' if batch_has_error and batch_has_warning else '失败'}")
    if batch_has_error and batch_has_warning:
        passed += 1
    else:
        failed += 1

    # 额外测试：JSON 输出
    print("\n--- JSON 输出测试 ---")
    json_result = process_input("代码审查：测试JSON输出", "json")
    json_ok = json_result["status"] == "success"
    try:
        json_str = format_output(json_result, "json")
        json.loads(json_str)  # 验证可解析
        json_ok = json_ok and True
    except Exception:
        json_ok = False
    print(f"  JSON 输出: {'通过' if json_ok else '失败'}")
    if json_ok:
        passed += 1
    else:
        failed += 1

    # 汇总结果
    print("\n" + "=" * 60)
    print(f"自检完成：{passed} 通过，{failed} 失败")
    print("=" * 60)

    return 0 if failed == 0 else 1


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------

def parse_args(argv=None):
    """
    解析命令行参数。

    参数:
        argv: 参数列表（默认使用 sys.argv[1:]）

    返回:
        argparse.Namespace
    """
    parser = argparse.ArgumentParser(
        description="solar-wind-hacker-book 技能实现（代码审查）",
        epilog="示例: %(prog)s --input '代码审查：处理这段内容' --format json",
    )

    parser.add_argument(
        "--input", "-i",
        type=str,
        help="待处理的输入内容（文本）",
    )

    parser.add_argument(
        "--format", "-f",
        choices=["text", "json"],
        default="text",
        help="输出格式（默认: text）",
    )

    parser.add_argument(
        "--batch",
        type=str,
        help="批量处理：提供文件路径（每行一条输入），或使用 ';' 分隔多条输入",
    )

    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行离线自检（使用内置硬编码样例数据）",
    )

    parser.add_argument(
        "--check-trigger",
        type=str,
        help="检查文本是否包含触发词，输出 true/false",
    )

    return parser.parse_args(argv)


def main(argv=None):
    """
    主入口函数。

    参数:
        argv: 参数列表（默认使用 sys.argv[1:]）

    返回:
        int: 退出码（0 成功，非 0 失败）
    """
    args = parse_args(argv)

    # 自检模式
    if args.selftest:
        return run_selftest()

    # 触发词检查模式
    if args.check_trigger is not None:
        result = check_trigger(args.check_trigger)
        print("true" if result else "false")
        return 0

    # 批量模式
    if args.batch:
        # 支持 ';' 分隔或文件路径
        batch_input = args.batch.strip()
        if batch_input.endswith(".txt") or batch_input.endswith(".log"):
            # 尝试读取文件（可能失败，返回错误）
            try:
                with open(batch_input, "r", encoding="utf-8") as f:
                    lines = [line.strip() for line in f if line.strip()]
            except Exception as exc:
                print(f"[E006] 读取文件失败：{str(exc)}")
                return 1
        else:
            # 按 ';' 分隔
            lines = [item.strip() for item in batch_input.split(";") if item.strip()]

        if not lines:
            print(f"[E001] {ERROR_MESSAGES['E001']}")
            return 1

        results = batch_process(lines, args.format)
        for result in results:
            print(format_output(result, args.format))
            print("-" * 40)
        return 0

    # 单条处理模式
    if args.input is not None:
        result = process_input(args.input, args.format)
        print(format_output(result, args.format))
        return 0 if result["status"] == "success" else 1

    # 无参数时显示帮助
    print("未提供输入。使用 --help 查看帮助，或使用 --selftest 运行自检。")
    print("示例：")
    print("  python scripts/main.py --input '代码审查：测试内容'")
    print("  python scripts/main.py --selftest")
    return 0


if __name__ == "__main__":
    sys.exit(main())
