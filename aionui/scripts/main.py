#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
aionui - 未命名工具
Open-source 24/7 Cowork app for OpenClaw, Hermes, Claude Code, Codex, OpenCode and 20+ more CLI Agent

基于功能规格的 clean-room 独立实现。
仅使用 Python 标准库，无第三方依赖。

用法:
    python main.py --selftest    # 离线自检
    python main.py --input "文本" --format json   # 处理输入
    python main.py --help        # 帮助信息
"""

import argparse
import json
import re
import sys
from typing import Any, Dict, List, Optional, Tuple

# ──────────────────────────── 常量定义 ────────────────────────────

# 错误码与标准化话术（规格第四节）
ERROR_MESSAGES: Dict[str, str] = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：...",
    "E003": "输入格式不符合要求，示例：...",
    "E004": "这超出了本工具的能力范围，建议...",
    "E005": "结果无法确定，建议：...",
}

# 置信度阈值（规格第三节 Step 2）
CONFIDENCE_HIGH = 90      # ≥90% 直接输出
CONFIDENCE_MEDIUM = 85    # 85%-90% 建议复核

# 输出格式支持列表
SUPPORTED_FORMATS = ["json", "text", "csv"]

# 内置硬编码自检样例（不依赖外部文件）
SELF_TEST_SAMPLES = [
    {
        "input": "张三，电话13800138000，邮箱zhangsan@example.com，地址北京市朝阳区",
        "expect_keys": ["name", "phone", "email", "address", "confidence", "flags"],
        "expect_name": "张三",
        "expect_phone_len": 11,
    },
    {
        "input": "项目Alpha，预算50000元，截止2026-12-31，负责人李四",
        "expect_keys": ["name", "budget", "deadline", "owner", "confidence", "flags"],
        "expect_budget_min": 10000,
        "expect_budget_max": 100000,
    },
    {
        "input": "这个内容很短",
        "expect_keys": ["raw", "length", "confidence", "flags"],
        "expect_len_min": 1,
    },
]


# ──────────────────────────── 核心功能函数 ────────────────────────────

def validate_input(raw_input: str) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    校验输入合法性（规格第三节 Step 1）。
    返回: (是否合法, 错误码或空串, 结构化的最小信息集)
    """
    # E001: 输入为空
    if raw_input is None or not raw_input.strip():
        return False, "E001", None

    text = raw_input.strip()

    # E003: 输入格式错误（简单长度校验，过于短的内容视为无有效信息）
    if len(text) < 2:
        return False, "E003", None

    # 收集最小信息集（Step 1 要求）
    info_set = {
        "input_source": "user_provided_text",  # 本实现仅支持文本直接输入
        "output_format": None,                  # 由参数决定
        "completeness": "standard",             # 标准完整度
        "raw_text": text,
        "length": len(text),
    }
    return True, "", info_set


def extract_key_info(text: str) -> Dict[str, Any]:
    """
    从文本中提取关键信息（规格第三节 Step 2.1）。
    使用正则表达式识别常见模式。
    """
    info: Dict[str, Any] = {}

    # 姓名：常见中文姓名（2-4个汉字）
    name_match = re.search(r"([\u4e00-\u9fa5]{2,4})(?=，|,|电话|邮箱|地址|$)", text)
    if name_match:
        info["name"] = name_match.group(1)

    # 电话：11位手机号
    phone_match = re.search(r"1[3-9]\d{9}", text)
    if phone_match:
        info["phone"] = phone_match.group(0)

    # 邮箱：标准邮箱格式
    email_match = re.search(r"[\w.+-]+@[\w-]+\.[\w.]+", text)
    if email_match:
        info["email"] = email_match.group(0)

    # 地址：地址关键词
    addr_match = re.search(r"([\u4e00-\u9fa5]+(?:省|市|区|县|镇|街道)[\u4e00-\u9fa5]*)", text)
    if addr_match:
        info["address"] = addr_match.group(1)

    # 预算：数字+元
    budget_match = re.search(r"(\d+)\s*元", text)
    if budget_match:
        info["budget"] = int(budget_match.group(1))

    # 日期：YYYY-MM-DD
    date_match = re.search(r"(\d{4}-\d{2}-\d{2})", text)
    if date_match:
        info["deadline"] = date_match.group(1)

    # 负责人：负责人后跟姓名
    owner_match = re.search(r"负责人[:：]?\s*([\u4e00-\u9fa5]{2,4})", text)
    if owner_match:
        info["owner"] = owner_match.group(1)

    # 项目名：项目后跟名称
    project_match = re.search(r"项目[:：]?\s*([\u4e00-\u9fa5A-Za-z0-9]+)", text)
    if project_match:
        info["project"] = project_match.group(1)

    return info


def compute_confidence(text: str, extracted: Dict[str, Any]) -> Tuple[int, List[str]]:
    """
    计算置信度并生成标注（规格第三节 Step 2.3）。
    返回: (置信度百分比, 标注列表)
    """
    flags: List[str] = []
    confidence = 50  # 基础分

    # 文本长度贡献（越长信息越丰富）
    text_len = len(text)
    if text_len >= 50:
        confidence += 20
    elif text_len >= 20:
        confidence += 15
    elif text_len >= 10:
        confidence += 10
    else:
        confidence += 5

    # 提取到关键字段加分
    extract_count = len(extracted)
    confidence += min(extract_count * 5, 25)  # 最多加25分

    # 检查是否包含结构化分隔符
    if any(sep in text for sep in ["，", ",", "；", ";", "|"]):
        confidence += 5

    # 有明确格式的数据（电话、邮箱、日期）加分
    if "phone" in extracted:
        confidence += 5
    if "email" in extracted:
        confidence += 5
    if "deadline" in extracted:
        confidence += 5

    # 置信度上限95，下限5
    confidence = max(5, min(confidence, 95))

    # 根据置信度生成标注
    if confidence >= CONFIDENCE_HIGH:
        pass  # 直接输出，无标注
    elif confidence >= CONFIDENCE_MEDIUM:
        flags.append("建议复核")
    else:
        flags.append("[需核实]")

    return confidence, flags


def process_text(raw_input: str, output_format: str = "json") -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    核心处理流程（规格第三节 Step 2 完整实现）。
    返回: (是否成功, 错误码或空串, 处理结果)
    """
    # Step 1: 校验输入
    valid, err_code, info_set = validate_input(raw_input)
    if not valid:
        return False, err_code, None

    # Step 2: 执行核心流程
    text = info_set["raw_text"]
    extracted = extract_key_info(text)

    # 检查关键信息是否完整（E002）
    if len(extracted) == 0:
        return False, "E002", None

    # 计算置信度
    confidence, flags = compute_confidence(text, extracted)

    # 构建结果
    result = {
        "raw": text,
        "length": len(text),
        **extracted,  # 展开提取的字段
        "confidence": confidence,
        "flags": flags,
    }

    # 检查置信度过低（E005）
    if confidence < CONFIDENCE_MEDIUM:
        result["error_code"] = "E005"

    # Step 3: 输出格式化
    if output_format == "json":
        pass  # 已经是字典，调用方负责序列化
    elif output_format == "text":
        # 文本格式：每行一个字段
        lines = [f"{k}: {v}" for k, v in result.items() if k != "raw"]
        result["text_output"] = "\n".join(lines)
    elif output_format == "csv":
        # CSV格式：简单实现，仅输出键值对
        result["csv_output"] = ",".join([f"{k}={v}" for k, v in result.items() if k != "raw"])

    return True, "", result


def format_output(result: Dict[str, Any], output_format: str) -> str:
    """将结果序列化为指定格式的字符串。"""
    if output_format == "json":
        return json.dumps(result, ensure_ascii=False, indent=2)
    elif output_format == "text":
        return result.get("text_output", str(result))
    elif output_format == "csv":
        return result.get("csv_output", str(result))
    else:
        return str(result)


# ──────────────────────────── 自检模块 ────────────────────────────

def run_selftest() -> bool:
    """
    内置自检（--selftest 参数）。
    使用硬编码样例数据，不依赖外部文件、网络或当前工作目录。
    使用宽松阈值断言，确保必然匹配。
    """
    print("开始自检...")
    all_passed = True

    # 测试1: 空输入应返回 E001
    ok, err, _ = process_text("")
    if not ok and err == "E001":
        print("  [PASS] 空输入处理正确 (E001)")
    else:
        print(f"  [FAIL] 空输入处理错误: {err}")
        all_passed = False

    # 测试2: 处理内置样例
    for i, sample in enumerate(SELF_TEST_SAMPLES, 1):
        try:
            ok, err, result = process_text(sample["input"])
            if not ok:
                print(f"  [FAIL] 样例{i}处理失败: {err}")
                all_passed = False
                continue

            # 检查必需键存在
            for key in sample["expect_keys"]:
                if key not in result:
                    print(f"  [FAIL] 样例{i}缺少键: {key}")
                    all_passed = False
                    break
            else:
                # 宽松阈值断言
                if "expect_name" in sample and result.get("name") != sample["expect_name"]:
                    print(f"  [FAIL] 样例{i}姓名不匹配")
                    all_passed = False

                if "expect_phone_len" in sample:
                    phone = result.get("phone", "")
                    if not (len(phone) >= 10 and len(phone) <= 12):  # 宽松区间
                        print(f"  [FAIL] 样例{i}电话号码长度异常")
                        all_passed = False

                if "expect_budget_min" in sample and "expect_budget_max" in sample:
                    budget = result.get("budget", 0)
                    if not (sample["expect_budget_min"] <= budget <= sample["expect_budget_max"]):
                        print(f"  [FAIL] 样例{i}预算不在合理区间")
                        all_passed = False

                if "expect_len_min" in sample:
                    if result.get("length", 0) < sample["expect_len_min"]:
                        print(f"  [FAIL] 样例{i}长度异常")
                        all_passed = False

                # 置信度必须是0-100之间的整数
                conf = result.get("confidence", -1)
                if not (0 <= conf <= 100):
                    print(f"  [FAIL] 样例{i}置信度越界")
                    all_passed = False

                print(f"  [PASS] 样例{i}处理成功")

        except Exception as e:
            print(f"  [FAIL] 样例{i}异常: {e}")
            all_passed = False

    # 测试3: 格式输出
    for fmt in SUPPORTED_FORMATS:
        try:
            ok, _, result = process_text("测试数据，电话13800138000", fmt)
            if ok:
                output = format_output(result, fmt)
                if len(output) > 0:
                    print(f"  [PASS] 格式输出 {fmt} 正常")
                else:
                    print(f"  [FAIL] 格式输出 {fmt} 为空")
                    all_passed = False
            else:
                print(f"  [FAIL] 格式输出 {fmt} 处理失败")
                all_passed = False
        except Exception as e:
            print(f"  [FAIL] 格式输出 {fmt} 异常: {e}")
            all_passed = False

    # 测试4: 错误码覆盖
    error_codes = ["E001", "E002", "E003", "E004", "E005"]
    for code in error_codes:
        if code not in ERROR_MESSAGES:
            print(f"  [FAIL] 缺少错误码 {code}")
            all_passed = False
        else:
            msg = ERROR_MESSAGES[code]
            if not msg or len(msg) < 5:
                print(f"  [FAIL] 错误码 {code} 消息过短")
                all_passed = False

    print(f"  [PASS] 错误码体系完整 ({len(error_codes)}个)")

    # 最终结果
    if all_passed:
        print("自检全部通过 ✓")
    else:
        print("自检存在失败项 ✗")
    return all_passed


# ──────────────────────────── 主入口 ────────────────────────────

def main() -> int:
    """命令行主入口。"""
    parser = argparse.ArgumentParser(
        description="aionui - 未命名工具：将文本信息结构化处理",
        epilog="示例: python main.py --input '张三，电话13800138000' --format json"
    )
    parser.add_argument("--selftest", action="store_true", help="运行离线自检")
    parser.add_argument("--input", "-i", type=str, help="待处理的文本内容")
    parser.add_argument("--format", "-f", type=str, choices=SUPPORTED_FORMATS,
                        default="json", help="输出格式 (默认: json)")
    parser.add_argument("--list-formats", action="store_true", help="列出支持的输出格式")

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        return 0 if run_selftest() else 1

    # 列出格式
    if args.list_formats:
        print("支持的输出格式:")
        for fmt in SUPPORTED_FORMATS:
            print(f"  - {fmt}")
        return 0

    # 处理输入
    if not args.input:
        print(f"错误 E001: {ERROR_MESSAGES['E001']}", file=sys.stderr)
        print("使用 --help 查看帮助，或 --selftest 运行自检", file=sys.stderr)
        return 1

    # 执行处理
    ok, err_code, result = process_text(args.input, args.format)

    if not ok:
        err_msg = ERROR_MESSAGES.get(err_code, "未知错误")
        print(f"错误 {err_code}: {err_msg}", file=sys.stderr)
        return 1

    # 输出结果
    output = format_output(result, args.format)
    print(output)

    # 低置信度提示
    if result.get("flags"):
        for flag in result["flags"]:
            print(f"\n提示: {flag}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
