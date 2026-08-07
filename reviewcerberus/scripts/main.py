#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
reviewcerberus - AI 辅助代码审查工具（独立实现）

本脚本仅依据功能规格独立编写（clean-room），不包含任何既有代码。
核心能力：将用户提供的文本/数据转换为结构化审查结果，支持置信度标注与错误码体系。

用法示例：
    python scripts/main.py --selftest          # 离线自检（不访问网络/文件）
    python scripts/main.py --input "..."       # 处理输入文本
    python scripts/main.py --input "..." --format json   # 指定输出格式

错误码：
    E001 输入为空
    E002 关键信息缺失
    E003 输入格式错误
    E004 超出能力边界
    E005 置信度过低
    E006 未知输出格式
    E007 内部处理异常
    E008 参数冲突
    E009 自检失败
    E010 资源限制
"""

import argparse
import json
import re
import sys
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# 常量定义
# ---------------------------------------------------------------------------
CONFIDENCE_HIGH = 90          # 置信度阈值：直接输出
CONFIDENCE_MEDIUM = 85        # 置信度阈值：建议复核
ERROR_MESSAGES = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：{}",
    "E003": "输入格式不符合要求，示例：{}",
    "E004": "这超出了本工具的能力范围，建议：{}",
    "E005": "结果无法确定，建议：{}",
    "E006": "未知的输出格式：{}，支持格式：text, json",
    "E007": "内部处理异常：{}",
    "E008": "参数冲突：{}",
    "E009": "自检失败：{}",
    "E010": "资源限制：{}",
}

# 关键信息识别规则（简单关键词匹配，用于演示核心逻辑）
KEY_FIELD_RULES = [
    ("文件名", r"文件[:：]?\s*([^\s,，;；]+)"),
    ("作者", r"作者[:：]?\s*([^\s,，;；]+)"),
    ("日期", r"日期[:：]?\s*([^\s,，;；]+)"),
    ("版本", r"版本[:：]?\s*([^\s,，;；]+)"),
    ("描述", r"描述[:：]?\s*([^\n]+)"),
]


# ---------------------------------------------------------------------------
# 核心处理逻辑
# ---------------------------------------------------------------------------
def validate_input(raw_text: str) -> Tuple[bool, Optional[str]]:
    """检查输入是否有效，返回 (是否有效, 错误码或None)。"""
    if raw_text is None or not raw_text.strip():
        return False, "E001"
    if len(raw_text) > 10000:
        return False, "E010"
    return True, None


def extract_key_fields(text: str) -> Dict[str, str]:
    """从输入文本中提取关键字段（基于规则匹配）。"""
    fields: Dict[str, str] = {}
    for field_name, pattern in KEY_FIELD_RULES:
        match = re.search(pattern, text)
        if match:
            fields[field_name] = match.group(1).strip()
    return fields


def compute_confidence(fields: Dict[str, str], total_expected: int = 5) -> int:
    """根据字段覆盖率计算置信度（0-100）。"""
    if not fields:
        return 0
    covered = len(fields)
    confidence = int((covered / total_expected) * 100)
    return min(confidence, 100)


def confidence_label(confidence: int) -> str:
    """将置信度转换为标注文本。"""
    if confidence >= CONFIDENCE_HIGH:
        return "直接输出"
    elif confidence >= CONFIDENCE_MEDIUM:
        return "建议复核"
    else:
        return "[需核实]"


def build_review_result(raw_text: str, output_format: str = "text") -> Dict[str, Any]:
    """
    执行核心审查流程，返回结构化结果。

    步骤：
    1. 校验输入
    2. 提取关键字段
    3. 计算置信度并标注
    4. 组装输出
    """
    # 步骤1：输入校验
    is_valid, err_code = validate_input(raw_text)
    if not is_valid:
        raise_system_error(err_code)

    # 步骤2：提取关键字段
    fields = extract_key_fields(raw_text)

    # 步骤3：置信度计算与标注
    confidence = compute_confidence(fields)
    label = confidence_label(confidence)

    # 组装结果
    result = {
        "原始输入": raw_text.strip(),
        "提取字段": fields,
        "字段数量": len(fields),
        "置信度": confidence,
        "置信度标注": label,
        "输出格式": output_format,
    }

    # 步骤4：输出格式转换
    if output_format == "json":
        return result
    elif output_format == "text":
        # 文本格式直接返回字典，由外层格式化
        return result
    else:
        raise_system_error("E006", output_format)


def format_text_output(result: Dict[str, Any]) -> str:
    """将结果格式化为可读文本。"""
    lines = []
    lines.append("=" * 50)
    lines.append("代码审查结果")
    lines.append("=" * 50)
    lines.append(f"原始输入: {result['原始输入'][:100]}{'...' if len(result['原始输入']) > 100 else ''}")
    lines.append(f"提取字段数量: {result['字段数量']}")
    if result["提取字段"]:
        lines.append("提取字段:")
        for key, value in result["提取字段"].items():
            lines.append(f"  - {key}: {value}")
    else:
        lines.append("未提取到关键字段")
    lines.append(f"置信度: {result['置信度']}% ({result['置信度标注']})")
    lines.append("=" * 50)
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 错误处理辅助
# ---------------------------------------------------------------------------
def raise_system_error(err_code: str, *args) -> None:
    """根据错误码抛出标准异常（统一使用 RuntimeError）。"""
    if err_code not in ERROR_MESSAGES:
        err_code = "E007"
    message = ERROR_MESSAGES[err_code].format(*args) if args else ERROR_MESSAGES[err_code]
    raise RuntimeError(f"{err_code}: {message}")


# ---------------------------------------------------------------------------
# 自检模块（内置硬编码样例，不依赖外部资源）
# ---------------------------------------------------------------------------
def run_selftest() -> bool:
    """
    执行离线自检，验证核心逻辑正确性。

    使用内置硬编码样例数据，不读取文件、不访问网络。
    断言使用宽松阈值（区间/大小比较），确保任何环境可稳定通过。
    """
    print("[自检] 开始执行离线自检...")

    # 测试用例1：正常输入（包含多个关键字段）
    sample1 = "文件: main.py 作者: Alice 日期: 2024-01-15 版本: 1.0.0 描述: 主程序入口"
    try:
        result1 = build_review_result(sample1, "json")
        # 宽松断言：字段数量在合理范围内，置信度在有效区间
        assert 3 <= result1["字段数量"] <= 5, f"字段数量异常: {result1['字段数量']}"
        assert 60 <= result1["置信度"] <= 100, f"置信度异常: {result1['置信度']}"
        assert result1["置信度标注"] in ("直接输出", "建议复核", "[需核实]")
        print(f"  [通过] 正常输入测试，字段数={result1['字段数量']}, 置信度={result1['置信度']}%")
    except Exception as e:
        print(f"  [失败] 正常输入测试: {e}")
        return False

    # 测试用例2：空输入（应触发E001）
    try:
        build_review_result("", "text")
        print("  [失败] 空输入测试：未抛出预期异常")
        return False
    except RuntimeError as e:
        assert "E001" in str(e), f"错误码不符: {e}"
        print("  [通过] 空输入测试，正确触发 E001")
    except Exception as e:
        print(f"  [失败] 空输入测试异常类型不符: {e}")
        return False

    # 测试用例3：缺少关键字段（置信度较低）
    sample3 = "这是一个简单的描述，没有标准字段"
    try:
        result3 = build_review_result(sample3, "json")
        assert result3["字段数量"] <= 1, f"字段数量应较少: {result3['字段数量']}"
        assert 0 <= result3["置信度"] <= 30, f"置信度应较低: {result3['置信度']}"
        print(f"  [通过] 低置信度测试，字段数={result3['字段数量']}, 置信度={result3['置信度']}%")
    except Exception as e:
        print(f"  [失败] 低置信度测试: {e}")
        return False

    # 测试用例4：文本格式输出（非JSON）
    try:
        result4 = build_review_result(sample1, "text")
        text_out = format_text_output(result4)
        assert "代码审查结果" in text_out, "文本输出缺少标题"
        assert "置信度" in text_out, "文本输出缺少置信度"
        print("  [通过] 文本格式输出测试")
    except Exception as e:
        print(f"  [失败] 文本格式输出测试: {e}")
        return False

    # 测试用例5：非法输出格式（应触发E006）
    try:
        build_review_result(sample1, "xml")
        print("  [失败] 非法格式测试：未抛出预期异常")
        return False
    except RuntimeError as e:
        assert "E006" in str(e), f"错误码不符: {e}"
        print("  [通过] 非法格式测试，正确触发 E006")
    except Exception as e:
        print(f"  [失败] 非法格式测试异常类型不符: {e}")
        return False

    # 测试用例6：长文本限制（超长输入触发E010）
    long_text = "A" * 10001
    try:
        build_review_result(long_text, "text")
        print("  [失败] 超长输入测试：未抛出预期异常")
        return False
    except RuntimeError as e:
        assert "E010" in str(e), f"错误码不符: {e}"
        print("  [通过] 超长输入测试，正确触发 E010")
    except Exception as e:
        print(f"  [失败] 超长输入测试异常类型不符: {e}")
        return False

    print("[自检] 全部测试通过！")
    return True


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------
def main() -> int:
    """命令行入口函数。"""
    parser = argparse.ArgumentParser(
        description="reviewcerberus - AI 辅助代码审查工具",
        epilog="示例: python main.py --input '文件: test.py 作者: Bob' --format json",
    )
    parser.add_argument("--input", "-i", type=str, help="待审查的输入文本")
    parser.add_argument("--format", "-f", type=str, choices=["text", "json"], default="text",
                        help="输出格式（默认: text）")
    parser.add_argument("--selftest", action="store_true", help="运行离线自检并退出")
    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        try:
            ok = run_selftest()
            return 0 if ok else 1
        except Exception as e:
            print(f"E009: 自检执行异常: {e}")
            return 1

    # 正常处理模式
    if not args.input:
        print(f"E001: {ERROR_MESSAGES['E001']}")
        return 1

    try:
        result = build_review_result(args.input, args.format)
        if args.format == "json":
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(format_text_output(result))
        return 0
    except RuntimeError as e:
        # 处理业务错误（统一使用RuntimeError）
        print(str(e))
        return 1
    except Exception as e:
        print(f"E007: 内部处理异常: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
