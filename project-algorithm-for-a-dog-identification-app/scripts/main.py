#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
技能功能规格：project-algorithm-for-a-dog-identification-app
独立实现脚本（clean-room 重写）
"""

import argparse
import sys
import re
from collections import OrderedDict

# ---------------------------------------------------------------------------
# 错误码定义
# ---------------------------------------------------------------------------
ERROR_CODES = {
    "E001": "输入为空",
    "E002": "关键信息缺失",
    "E003": "输入格式错误",
    "E004": "超出能力边界",
    "E005": "置信度过低",
    "E006": "内部处理异常",
    "E007": "参数错误",
    "E008": "结果生成失败",
    "E009": "校验失败",
    "E010": "未知错误",
}


class SkillError(Exception):
    """技能统一异常类"""

    def __init__(self, code: str, message: str = ""):
        self.code = code
        self.message = message or ERROR_CODES.get(code, "未知错误")
        super().__init__(f"[{code}] {self.message}")


# ---------------------------------------------------------------------------
# 核心处理逻辑
# ---------------------------------------------------------------------------
def parse_input(raw_input):
    """
    解析输入内容，提取关键信息。
    返回结构化字典。
    """
    if raw_input is None or (isinstance(raw_input, str) and not raw_input.strip()):
        raise SkillError("E001")

    if not isinstance(raw_input, str):
        raw_input = str(raw_input)

    # 按行解析，提取非空行作为关键信息
    lines = [line.strip() for line in raw_input.splitlines() if line.strip()]

    if not lines:
        raise SkillError("E001")

    # 识别关键字段（示例：标题、内容、标签）
    result = OrderedDict()
    result["title"] = lines[0]  # 首行作为标题
    result["content"] = lines[1:] if len(lines) > 1 else []
    result["line_count"] = len(lines)

    # 尝试识别标签（#开头）
    tags = [line[1:].strip() for line in lines if line.startswith("#")]
    result["tags"] = tags

    return result


def process_data(structured_data):
    """
    按规则处理结构化数据，生成输出结果。
    """
    if not structured_data:
        raise SkillError("E002")

    title = structured_data.get("title", "")
    content = structured_data.get("content", [])
    tags = structured_data.get("tags", [])

    if not title:
        raise SkillError("E002", "缺少标题信息")

    # 组装输出结果
    output = OrderedDict()
    output["标题"] = title
    output["正文行数"] = len(content)
    output["标签"] = tags if tags else ["未标注"]

    # 计算置信度（基于信息完整度）
    confidence = 90.0  # 基础置信度
    if not content:
        confidence -= 10.0  # 缺少正文
    if not tags:
        confidence -= 5.0  # 缺少标签

    output["置信度"] = round(confidence, 1)

    # 根据置信度添加标注
    if confidence >= 90:
        output["标注"] = "直接输出"
    elif confidence >= 85:
        output["标注"] = "建议复核"
    else:
        output["标注"] = "[需核实]"

    return output


def format_output(result_data):
    """
    将处理结果格式化为文本输出。
    """
    if not result_data:
        raise SkillError("E008")

    lines = []
    for key, value in result_data.items():
        if isinstance(value, list):
            value_str = ", ".join(str(v) for v in value)
        else:
            value_str = str(value)
        lines.append(f"{key}: {value_str}")

    return "\n".join(lines)


def run_pipeline(raw_input):
    """
    标准流程：解析 -> 处理 -> 格式化输出
    """
    try:
        # Step 1: 解析输入
        parsed = parse_input(raw_input)

        # Step 2: 核心处理
        result = process_data(parsed)

        # Step 3: 格式化输出
        output_text = format_output(result)

        return output_text, result

    except SkillError:
        raise
    except Exception as exc:
        raise SkillError("E006", str(exc)) from exc


# ---------------------------------------------------------------------------
# 批量处理
# ---------------------------------------------------------------------------
def batch_process(input_list):
    """
    批量处理多个输入。
    """
    if not input_list:
        raise SkillError("E001")

    results = []
    for item in input_list:
        try:
            output_text, result_data = run_pipeline(item)
            results.append({"输入": item, "输出": output_text, "成功": True})
        except SkillError as exc:
            results.append({"输入": item, "错误": str(exc), "成功": False})

    return results


# ---------------------------------------------------------------------------
# 自检模块（内置硬编码样例数据）
# ---------------------------------------------------------------------------
def run_selftest():
    """
    离线自检核心逻辑。
    使用内置硬编码数据，不依赖外部文件、目录或网络。
    """
    print("=== 自检开始 ===")

    # 测试用例 1：正常输入
    test_input_1 = "卷积神经网络项目\n# 狗品种识别\n# CNN\n这是一个用于狗品种识别的卷积神经网络项目。"
    try:
        output_text, result_data = run_pipeline(test_input_1)
        assert output_text, "输出不应为空"
        assert result_data["标题"] == "卷积神经网络项目", "标题解析错误"
        assert result_data["正文行数"] >= 1, "正文行数应至少为1"
        assert len(result_data["标签"]) >= 2, "标签数量应至少为2"
        assert result_data["置信度"] >= 85, "置信度应不低于85"
        print("[PASS] 测试用例 1：正常输入处理")
    except AssertionError as exc:
        print(f"[FAIL] 测试用例 1：{exc}")
        return False
    except SkillError as exc:
        print(f"[FAIL] 测试用例 1：{exc}")
        return False

    # 测试用例 2：空输入（应触发 E001）
    try:
        run_pipeline("")
        print("[FAIL] 测试用例 2：空输入未触发错误")
        return False
    except SkillError as exc:
        assert exc.code == "E001", f"错误码应为 E001，实际为 {exc.code}"
        print("[PASS] 测试用例 2：空输入错误处理")

    # 测试用例 3：仅标题无正文
    test_input_3 = "仅标题无正文"
    try:
        output_text, result_data = run_pipeline(test_input_3)
        assert result_data["正文行数"] == 0, "正文行数应为0"
        assert result_data["置信度"] < 90, "置信度应低于90"
        print("[PASS] 测试用例 3：简略输入置信度调整")
    except AssertionError as exc:
        print(f"[FAIL] 测试用例 3：{exc}")
        return False
    except SkillError as exc:
        print(f"[FAIL] 测试用例 3：{exc}")
        return False

    # 测试用例 4：批量处理
    batch_inputs = [
        "批量测试一\n# 标签A\n内容A",
        "批量测试二\n内容B",
        "",  # 应失败
    ]
    try:
        batch_results = batch_process(batch_inputs)
        assert len(batch_results) == 3, "批量结果数量应为3"
        success_count = sum(1 for r in batch_results if r["成功"])
        assert success_count >= 2, "成功数量应至少为2"
        print("[PASS] 测试用例 4：批量处理")
    except AssertionError as exc:
        print(f"[FAIL] 测试用例 4：{exc}")
        return False
    except Exception as exc:
        print(f"[FAIL] 测试用例 4：{exc}")
        return False

    # 测试用例 5：特殊字符输入
    test_input_5 = "特殊字符测试\n# 标签@#$%\n内容：中文、English、123、!@#$%^&*()"
    try:
        output_text, result_data = run_pipeline(test_input_5)
        assert "特殊字符测试" in output_text, "输出应包含标题"
        assert result_data["正文行数"] >= 1, "正文行数应至少为1"
        print("[PASS] 测试用例 5：特殊字符处理")
    except AssertionError as exc:
        print(f"[FAIL] 测试用例 5：{exc}")
        return False
    except SkillError as exc:
        print(f"[FAIL] 测试用例 5：{exc}")
        return False

    # 测试用例 6：错误码完整性
    try:
        assert "E001" in ERROR_CODES
        assert "E005" in ERROR_CODES
        assert "E010" in ERROR_CODES
        assert len(ERROR_CODES) >= 5, "错误码数量应至少为5"
        print("[PASS] 测试用例 6：错误码完整性")
    except AssertionError as exc:
        print(f"[FAIL] 测试用例 6：{exc}")
        return False

    print("=== 自检全部通过 ===")
    return True


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="代码审查技能 - 独立实现",
        epilog="示例: python main.py --input '待处理内容' | python main.py --selftest",
    )
    parser.add_argument(
        "--input",
        type=str,
        help="待处理的输入内容（字符串）",
    )
    parser.add_argument(
        "--file",
        type=str,
        help="从文件读取输入内容",
    )
    parser.add_argument(
        "--batch",
        type=str,
        nargs="+",
        help="批量处理多个输入（空格分隔）",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行离线自检",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s 1.0.0",
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        success = run_selftest()
        sys.exit(0 if success else 1)

    # 批量模式
    if args.batch:
        try:
            results = batch_process(args.batch)
            for i, result in enumerate(results, 1):
                print(f"--- 结果 {i} ---")
                if result["成功"]:
                    print(result["输出"])
                else:
                    print(f"错误: {result['错误']}")
                print()
            sys.exit(0)
        except SkillError as exc:
            print(f"批量处理失败: {exc}", file=sys.stderr)
            sys.exit(1)

    # 文件模式
    if args.file:
        try:
            with open(args.file, "r", encoding="utf-8") as f:
                content = f.read()
            output_text, _ = run_pipeline(content)
            print(output_text)
            sys.exit(0)
        except FileNotFoundError:
            print("[E003] 文件不存在", file=sys.stderr)
            sys.exit(1)
        except SkillError as exc:
            print(f"处理失败: {exc}", file=sys.stderr)
            sys.exit(1)

    # 直接输入模式
    if args.input:
        try:
            output_text, _ = run_pipeline(args.input)
            print(output_text)
            sys.exit(0)
        except SkillError as exc:
            print(f"处理失败: {exc}", file=sys.stderr)
            sys.exit(1)

    # 无参数时显示帮助
    parser.print_help()


if __name__ == "__main__":
    main()
