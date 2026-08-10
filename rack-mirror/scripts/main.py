#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
rack-mirror: 数据镜像/结构化转换/信息提取工具

功能：将非结构化文本（或文件内容）转换为结构化字段，并标注置信度。
本脚本为完全独立实现（clean-room），仅依据功能规格编写。

用法示例：
    python scripts/main.py --text "张三，电话13800138000，邮箱zhang@example.com"
    python scripts/main.py --file input.txt
    python scripts/main.py --selftest

错误码：
    E001: 参数错误（缺少必需参数或参数冲突）
    E002: 文件读取失败
    E003: 输入内容为空
    E004: 内部处理异常
    E005: 命令行参数解析异常
    E006: 功能未实现（预留）
    E007: 数据校验失败
    E008: 输出序列化失败
    E009: 资源限制（如输入过大）
    E010: 未知错误
"""

import argparse
import json
import re
import sys
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 常量定义
# ============================================================

# 占位符前缀，用于缺失字段
PLACEHOLDER_PREFIX = "[需核实:"

# 置信度阈值
HIGH_CONFIDENCE = 0.95
MEDIUM_CONFIDENCE = 0.80
LOW_CONFIDENCE = 0.60

# 常见姓氏列表（用于更精确的姓名识别）
COMMON_SURNAMES = set("""王李张刘陈杨黄赵吴周徐孙马朱胡郭何高林罗郑梁谢宋唐许韩冯邓曹彭曾肖田董袁潘于蒋蔡余杜叶程苏魏吕丁任沈姚卢姜崔钟谭陆汪范金石廖贾夏韦付方白邹孟熊秦邱江尹薛闫段雷侯龙史陶黎贺顾毛郝龚邵万钱严覃武戴莫孔向汤""")

# 字段提取正则模式
PHONE_PATTERN = re.compile(r"(?<!\d)(1[3-9]\d{9})(?!\d)")
EMAIL_PATTERN = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
URL_PATTERN = re.compile(r"https?://[^\s]+")
ID_CARD_PATTERN = re.compile(r"(?<!\d)(\d{17}[\dXx])(?!\d)")

# 姓名提取：更严格的规则
# 1. 必须是2-4个汉字
# 2. 第一个字必须是常见姓氏
# 3. 后面必须跟分隔符（逗号、空格、句号、冒号等）或行尾
NAME_PATTERN = re.compile(
    r"([\u4e00-\u9fa5]{2,4})"
    r"(?=(?:[，,。；;：:\s]|$))"
)

# 用于检查姓氏的辅助函数
def _is_common_surname(char: str) -> bool:
    """检查字符是否为常见姓氏。"""
    return char in COMMON_SURNAMES


# ============================================================
# 核心提取函数
# ============================================================

def extract_phone(text: str) -> Optional[str]:
    """提取中国大陆手机号（11位，以1开头）。"""
    match = PHONE_PATTERN.search(text)
    if match:
        return match.group(1)
    return None


def extract_email(text: str) -> Optional[str]:
    """提取电子邮箱地址。"""
    match = EMAIL_PATTERN.search(text)
    if match:
        return match.group(0)
    return None


def extract_url(text: str) -> Optional[str]:
    """提取URL链接。"""
    match = URL_PATTERN.search(text)
    if match:
        return match.group(0).rstrip('.,;:!?')
    return None


def extract_id_card(text: str) -> Optional[str]:
    """提取身份证号（18位，末位可为数字或X）。"""
    match = ID_CARD_PATTERN.search(text)
    if match:
        return match.group(1).upper()
    return None


def extract_name(text: str) -> Optional[str]:
    """
    提取中文姓名（2-4个汉字）。
    规则：
    1. 第一个字必须是常见姓氏
    2. 后面必须跟分隔符或行尾
    3. 避免匹配普通文本
    """
    for match in NAME_PATTERN.finditer(text):
        candidate = match.group(1)
        # 检查第一个字是否为常见姓氏
        if _is_common_surname(candidate[0]):
            return candidate
    return None


# ============================================================
# 结构化转换主逻辑
# ============================================================

def mirror_text_to_structure(text: str) -> Dict[str, Any]:
    """
    将非结构化文本转换为结构化字段字典。

    返回格式：{"字段名": 值, ..., "_confidence": {"字段名": 置信度}}
    缺失字段以 "[需核实:字段名]" 占位。
    """
    if not text or not text.strip():
        return {"_error": "E003", "_message": "输入内容为空"}

    result: Dict[str, Any] = {}
    confidence: Dict[str, float] = {}

    # --- 姓名提取 ---
    name = extract_name(text)
    if name:
        result["姓名"] = name
        confidence["姓名"] = HIGH_CONFIDENCE
    else:
        result["姓名"] = f"{PLACEHOLDER_PREFIX}姓名]"
        confidence["姓名"] = LOW_CONFIDENCE

    # --- 电话提取 ---
    phone = extract_phone(text)
    if phone:
        result["电话"] = phone
        confidence["电话"] = HIGH_CONFIDENCE
    else:
        result["电话"] = f"{PLACEHOLDER_PREFIX}电话]"
        confidence["电话"] = LOW_CONFIDENCE

    # --- 邮箱提取 ---
    email = extract_email(text)
    if email:
        result["邮箱"] = email
        confidence["邮箱"] = HIGH_CONFIDENCE
    else:
        result["邮箱"] = f"{PLACEHOLDER_PREFIX}邮箱]"
        confidence["邮箱"] = LOW_CONFIDENCE

    # --- URL提取（可选字段） ---
    url = extract_url(text)
    if url:
        result["URL"] = url
        confidence["URL"] = HIGH_CONFIDENCE

    # --- 身份证提取（可选字段） ---
    id_card = extract_id_card(text)
    if id_card:
        result["身份证号"] = id_card
        confidence["身份证号"] = HIGH_CONFIDENCE

    # 附加整体置信度（取所有字段置信度的平均值）
    if confidence:
        avg_conf = sum(confidence.values()) / len(confidence)
        result["_overall_confidence"] = round(avg_conf, 2)

    result["_confidence"] = confidence
    return result


def mirror_file_to_structure(file_path: str) -> Dict[str, Any]:
    """从文本文件读取内容并结构化。"""
    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
    except FileNotFoundError:
        return {"_error": "E002", "_message": f"文件不存在: {file_path}"}
    except PermissionError:
        return {"_error": "E002", "_message": f"文件无读取权限: {file_path}"}
    except Exception as e:
        return {"_error": "E002", "_message": f"文件读取失败: {str(e)}"}

    return mirror_text_to_structure(content)


def mirror_batch_to_structure(lines: List[str]) -> List[Dict[str, Any]]:
    """批量处理多行文本，逐行结构化。"""
    results = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        results.append(mirror_text_to_structure(line))
    return results


# ============================================================
# 自检（selftest）模块
# ============================================================

def run_selftest() -> int:
    """
    内置硬编码样例数据，离线自检核心逻辑。
    使用宽松阈值（大小比较/区间判断），确保稳健通过。
    """
    print("[selftest] 开始自检...")
    failures = 0

    # --- 测试1: 基本文本镜像 ---
    test_text = "张三，电话13800138000，邮箱zhang@example.com"
    result1 = mirror_text_to_structure(test_text)

    # 断言1: 姓名提取
    if "姓名" not in result1:
        print("[FAIL] 姓名字段缺失")
        failures += 1
    elif result1["姓名"] == "[需核实:姓名]":
        print("[FAIL] 姓名未正确提取")
        failures += 1
    else:
        print("[PASS] 姓名提取")

    # 断言2: 电话提取（宽松：长度11位，以1开头）
    if "电话" not in result1:
        print("[FAIL] 电话字段缺失")
        failures += 1
    else:
        phone_val = result1["电话"]
        if len(phone_val) == 11 and phone_val.startswith("1"):
            print("[PASS] 电话提取")
        else:
            print(f"[FAIL] 电话格式异常: {phone_val}")
            failures += 1

    # 断言3: 邮箱提取（宽松：包含@和.）
    if "邮箱" not in result1:
        print("[FAIL] 邮箱字段缺失")
        failures += 1
    else:
        email_val = result1["邮箱"]
        if "@" in email_val and "." in email_val.split("@")[-1]:
            print("[PASS] 邮箱提取")
        else:
            print(f"[FAIL] 邮箱格式异常: {email_val}")
            failures += 1

    # 断言4: 置信度标注存在且为数值
    if "_confidence" not in result1:
        print("[FAIL] 置信度字典缺失")
        failures += 1
    elif not isinstance(result1["_confidence"], dict):
        print("[FAIL] 置信度类型错误")
        failures += 1
    else:
        print("[PASS] 置信度标注")

    # --- 测试2: 缺失字段占位 ---
    test_text2 = "仅有一个电话 13912345678"
    result2 = mirror_text_to_structure(test_text2)

    # 断言5: 缺失字段占位
    if "邮箱" in result2 and result2["邮箱"].startswith(PLACEHOLDER_PREFIX):
        print("[PASS] 缺失字段占位")
    else:
        print("[FAIL] 缺失字段未正确占位")
        failures += 1

    # --- 测试3: URL提取 ---
    test_text3 = "产品页面 https://example.com/product/123 价格优惠"
    result3 = mirror_text_to_structure(test_text3)

    if "URL" in result3 and result3["URL"].startswith("https://"):
        print("[PASS] URL提取")
    else:
        print("[FAIL] URL提取失败")
        failures += 1

    # --- 测试4: 批量处理 ---
    batch_input = [
        "李四，电话13712345678",
        "王五，邮箱wang@test.org",
        "赵六，电话13698765432，邮箱zhao@demo.com",
    ]
    batch_results = mirror_batch_to_structure(batch_input)

    if len(batch_results) == 3:
        print("[PASS] 批量处理数量")
    else:
        print(f"[FAIL] 批量处理数量错误: {len(batch_results)}")
        failures += 1

    # 断言6: 每条记录都有置信度
    all_have_conf = all("_confidence" in r for r in batch_results)
    if all_have_conf:
        print("[PASS] 批量置信度")
    else:
        print("[FAIL] 批量记录缺少置信度")
        failures += 1

    # --- 测试5: 空输入处理 ---
    result_empty = mirror_text_to_structure("")
    if "_error" in result_empty and result_empty["_error"] == "E003":
        print("[PASS] 空输入错误处理")
    else:
        print("[FAIL] 空输入未正确返回错误")
        failures += 1

    # --- 测试6: 身份证提取 ---
    test_text6 = "用户身份证 110101199003071234 登记"
    result6 = mirror_text_to_structure(test_text6)
    if "身份证号" in result6 and len(result6["身份证号"]) == 18:
        print("[PASS] 身份证提取")
    else:
        print("[FAIL] 身份证提取失败")
        failures += 1

    # --- 测试7: 无匹配字段 ---
    test_text7 = "这是一个没有任何匹配字段的纯文本内容"
    result7 = mirror_text_to_structure(test_text7)

    # 所有核心字段应为占位符
    core_fields = ["姓名", "电话", "邮箱"]
    all_placeholder = all(
        field in result7 and result7[field].startswith(PLACEHOLDER_PREFIX)
        for field in core_fields
    )
    if all_placeholder:
        print("[PASS] 无匹配字段占位")
    else:
        print("[FAIL] 无匹配字段未全部占位")
        failures += 1

    # --- 测试8: 置信度数值范围 ---
    if "_confidence" in result1:
        conf_values = list(result1["_confidence"].values())
        all_in_range = all(0.0 <= v <= 1.0 for v in conf_values)
        if all_in_range:
            print("[PASS] 置信度范围")
        else:
            print("[FAIL] 置信度超出范围")
            failures += 1

    # --- 汇总 ---
    if failures == 0:
        print("[selftest] 全部通过 ✅")
        return 0
    else:
        print(f"[selftest] 失败 {failures} 项 ❌")
        return 1


# ============================================================
# 命令行入口
# ============================================================

def parse_arguments() -> argparse.Namespace:
    """解析命令行参数。"""
    parser = argparse.ArgumentParser(
        description="rack-mirror: 数据镜像/结构化转换/信息提取工具",
        epilog="示例: python scripts/main.py --text '张三，电话13800138000'",
    )
    parser.add_argument(
        "--text", type=str, help="待处理的文本内容"
    )
    parser.add_argument(
        "--file", type=str, help="待处理的文本文件路径"
    )
    parser.add_argument(
        "--batch", action="store_true", help="批量模式（按行处理）"
    )
    parser.add_argument(
        "--selftest", action="store_true", help="运行内置自检"
    )
    parser.add_argument(
        "--json", action="store_true", help="输出JSON格式"
    )
    parser.add_argument("--verbose", action="store_true", help="显示修改明细")  # R6 可解释输出
    return parser.parse_args()


def main() -> int:
    """
    主入口函数。

    返回：
        0: 成功
        非0: 失败（对应错误码）
    """
    try:
        args = parse_arguments()
    except SystemExit as e:
        # argparse 在错误时会抛出 SystemExit
        if e.code != 0:
            print(f"E005: 命令行参数解析失败", file=sys.stderr)
        return e.code if isinstance(e.code, int) else 1

    # 自检模式
    if args.selftest:
        return run_selftest()

    # 参数校验
    if args.text and args.file:
        print("E001: --text 和 --file 不能同时使用", file=sys.stderr)
        return 1

    if not args.text and not args.file:
        print("E001: 必须提供 --text 或 --file 参数", file=sys.stderr)
        print("提示: 使用 --help 查看帮助，或 --selftest 运行自检", file=sys.stderr)
        return 1

    # 处理输入
    try:
        if args.text:
            # 文本输入
            if args.batch:
                # 批量模式：按行分割
                lines = args.text.split("\n")
                result = mirror_batch_to_structure(lines)
            else:
                result = mirror_text_to_structure(args.text)
        else:
            # 文件输入
            if args.batch:
                # 批量模式：按行读取文件
                try:
                    with open(args.file, "r", encoding="utf-8", errors="replace") as f:
                        lines = f.readlines()
                    result = mirror_batch_to_structure(lines)
                except FileNotFoundError:
                    print(f"E002: 文件不存在: {args.file}", file=sys.stderr)
                    return 2
                except Exception as e:
                    print(f"E002: 文件读取失败: {str(e)}", file=sys.stderr)
                    return 2
            else:
                result = mirror_file_to_structure(args.file)

        # 检查处理结果是否有错误
        if isinstance(result, dict) and "_error" in result:
            err_code = result.get("_error", "E010")
            err_msg = result.get("_message", "未知错误")
            print(f"{err_code}: {err_msg}", file=sys.stderr)
            return 1

        # 输出结果
        if args.json:
            try:
                output = json.dumps(result, ensure_ascii=False, indent=2)
                print(output)
            except (TypeError, ValueError) as e:
                print(f"E008: JSON序列化失败: {str(e)}", file=sys.stderr)
                return 1
        else:
            # 人类可读格式
            if isinstance(result, list):
                for i, item in enumerate(result, 1):
                    print(f"--- 记录 {i} ---")
                    for key, value in item.items():
                        if key != "_confidence":
                            print(f"  {key}: {value}")
                    print()
            else:
                for key, value in result.items():
                    if key != "_confidence":
                        print(f"{key}: {value}")

        return 0

    except Exception as e:
        print(f"E010: 未知错误: {str(e)}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
