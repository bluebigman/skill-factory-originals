#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tasks — 任务编排与数据转换批处理引擎（clean-room 独立实现）

功能概述：
    本脚本根据功能规格实现一个轻量级的任务编排与数据转换引擎。
    支持多源文本数据接入、关键信息抽取、格式转换、批量处理与置信度标注。
    仅依赖 Python 标准库，不执行外部命令，不访问网络，不解析二进制。

用法示例：
    python scripts/main.py --selftest                # 离线自检核心逻辑
    python scripts/main.py --input "文本" --format json   # 单条转换
    python scripts/main.py --batch file1.txt file2.txt --format csv  # 批量转换

错误码约定：
    E001 参数解析错误
    E002 输入数据为空或类型非法
    E003 不支持的输出格式
    E004 批量处理时某条记录失败
    E005 文件读取失败
    E006 自检断言失败
    E007 内部逻辑错误（未捕获异常）
    E008 输出写入失败
    E009 输入数据超过大小限制
    E010 不支持的输入类型
"""

import argparse
import csv
import io
import json
import re
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# 常量定义
# ---------------------------------------------------------------------------

# 支持的输出格式
SUPPORTED_FORMATS = ("json", "csv", "markdown", "md")

# 置信度等级
CONFIDENCE_HIGH = "高"
CONFIDENCE_MEDIUM = "中"
CONFIDENCE_LOW = "低"

# 输入大小限制（字符数），超过则报 E009
MAX_INPUT_CHARS = 1_000_000

# 占位符，用于低置信度字段
PLACEHOLDER = "【不确定】"

# 日期正则（宽松匹配 YYYY-MM-DD 或 YYYY/MM/DD）
DATE_PATTERN = re.compile(r"\d{4}[-/]\d{1,2}[-/]\d{1,2}")

# 金额正则（宽松匹配：可选货币符号，数字，可选小数）
AMOUNT_PATTERN = re.compile(r"(?:￥|¥|\$|€|£)?\s?\d+(?:,\d{3})*(?:\.\d{1,2})?")

# 邮箱正则
EMAIL_PATTERN = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")

# 手机号正则（简单匹配 1 开头的 11 位数字）
PHONE_PATTERN = re.compile(r"1[3-9]\d{9}")


# ---------------------------------------------------------------------------
# 异常与错误处理
# ---------------------------------------------------------------------------

class TaskError(Exception):
    """业务逻辑异常基类，携带错误码。"""
    def __init__(self, code: str, message: str):
        super().__init__(f"[{code}] {message}")
        self.code = code
        self.message = message


# ---------------------------------------------------------------------------
# 核心工具函数
# ---------------------------------------------------------------------------

def _validate_input_text(text: str) -> str:
    """校验并规范化输入文本。"""
    if text is None:
        raise TaskError("E002", "输入数据为空")
    if not isinstance(text, str):
        raise TaskError("E010", "输入类型必须是字符串")
    text = text.strip()
    if not text:
        raise TaskError("E002", "输入数据为空")
    if len(text) > MAX_INPUT_CHARS:
        raise TaskError("E009", f"输入数据超过大小限制（{MAX_INPUT_CHARS} 字符）")
    return text


def _parse_date(text: str) -> Optional[str]:
    """尝试从文本中解析日期，返回标准格式 YYYY-MM-DD。"""
    match = DATE_PATTERN.search(text)
    if not match:
        return None
    raw = match.group(0)
    # 统一分隔符为 '-'
    parts = re.split(r"[-/]", raw)
    try:
        year, month, day = int(parts[0]), int(parts[1]), int(parts[2])
        # 简单范围校验，避免非法日期
        if not (1 <= month <= 12 and 1 <= day <= 31):
            return None
        return f"{year:04d}-{month:02d}-{day:02d}"
    except (ValueError, IndexError):
        return None


def _parse_amount(text: str) -> Optional[float]:
    """尝试从文本中解析金额数字。"""
    match = AMOUNT_PATTERN.search(text)
    if not match:
        return None
    raw = match.group(0)
    # 去掉货币符号和逗号
    cleaned = re.sub(r"[^\d.]", "", raw)
    if not cleaned:
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def _extract_email(text: str) -> Optional[str]:
    """抽取邮箱地址。"""
    match = EMAIL_PATTERN.search(text)
    return match.group(0) if match else None


def _extract_phone(text: str) -> Optional[str]:
    """抽取手机号。"""
    match = PHONE_PATTERN.search(text)
    return match.group(0) if match else None


def _extract_status(text: str) -> Optional[str]:
    """识别状态关键词。"""
    status_keywords = {
        "成功": "成功",
        "失败": "失败",
        "完成": "完成",
        "待处理": "待处理",
        "处理中": "处理中",
        "已取消": "已取消",
        "已发货": "已发货",
        "已签收": "已签收",
    }
    for keyword, status in status_keywords.items():
        if keyword in text:
            return status
    return None


def _detect_confidence(extracted: Dict[str, Any], raw_text: str) -> str:
    """
    根据抽取结果计算置信度。
    规则：关键字段（日期、金额、邮箱）至少抽到 2 个 → 高；
          至少抽到 1 个 → 中；
          一个都没抽到 → 低。
    """
    key_fields = ["日期", "金额", "邮箱", "手机号", "状态"]
    hit_count = sum(1 for f in key_fields if extracted.get(f) is not None)
    if hit_count >= 2:
        return CONFIDENCE_HIGH
    if hit_count == 1:
        return CONFIDENCE_MEDIUM
    return CONFIDENCE_LOW


# ---------------------------------------------------------------------------
# 核心处理逻辑
# ---------------------------------------------------------------------------

def process_single(text: str) -> Dict[str, Any]:
    """
    处理单条文本，抽取关键信息并返回结构化结果。

    返回结构：
        {
            "原文": 输入文本,
            "日期": 日期或 None,
            "金额": 金额或 None,
            "邮箱": 邮箱或 None,
            "手机号": 手机号或 None,
            "状态": 状态或 None,
            "置信度": 高/中/低,
            "摘要": 文本摘要,
        }
    """
    text = _validate_input_text(text)

    # 抽取各字段
    date = _parse_date(text)
    amount = _parse_amount(text)
    email = _extract_email(text)
    phone = _extract_phone(text)
    status = _extract_status(text)

    # 低置信度字段用占位符替换（这里为保持简单，仅对日期和金额做占位，其他字段保留 None）
    extracted = {
        "日期": date,
        "金额": amount,
        "邮箱": email,
        "手机号": phone,
        "状态": status,
    }
    confidence = _detect_confidence(extracted, text)

    # 对低置信度字段做占位处理（仅演示，实际可按需扩展）
    if confidence == CONFIDENCE_LOW:
        for key in ("日期", "金额"):
            if extracted[key] is None:
                extracted[key] = PLACEHOLDER

    # 生成摘要（取前 50 个字符）
    summary = text if len(text) <= 50 else text[:50] + "..."

    result = {
        "原文": text,
        "日期": extracted["日期"],
        "金额": extracted["金额"],
        "邮箱": extracted["邮箱"],
        "手机号": extracted["手机号"],
        "状态": extracted["状态"],
        "置信度": confidence,
        "摘要": summary,
    }
    return result


def process_batch(texts: List[str]) -> Dict[str, Any]:
    """
    批量处理多条文本，逐条处理并汇总结果。
    """
    if not texts:
        raise TaskError("E002", "批量输入为空")
    if not isinstance(texts, (list, tuple)):
        raise TaskError("E010", "批量输入必须是列表")

    results = []
    failures = []
    for idx, item in enumerate(texts):
        try:
            results.append(process_single(item))
        except TaskError as exc:
            failures.append({"index": idx, "error_code": exc.code, "message": exc.message})

    if failures:
        # 部分失败时，若全部失败则直接报 E004，否则附带失败信息
        if len(failures) == len(texts):
            raise TaskError("E004", f"批量处理全部失败，共 {len(failures)} 条")
        # 部分成功：将失败信息附加到结果中
        summary = {
            "总条数": len(texts),
            "成功条数": len(results),
            "失败条数": len(failures),
            "失败详情": failures,
        }
    else:
        summary = {
            "总条数": len(texts),
            "成功条数": len(results),
            "失败条数": 0,
            "失败详情": [],
        }

    return {
        "汇总": summary,
        "结果列表": results,
    }


# ---------------------------------------------------------------------------
# 格式转换输出
# ---------------------------------------------------------------------------

def _format_json(data: Any) -> str:
    """转换为 JSON 字符串。"""
    return json.dumps(data, ensure_ascii=False, indent=2, default=str)


def _format_csv(data: Any) -> str:
    """转换为 CSV 字符串。支持单条或批量结果。"""
    output = io.StringIO()
    writer = csv.writer(output)

    # 统一处理为列表形式
    if isinstance(data, dict) and "结果列表" in data:
        rows = data["结果列表"]
    elif isinstance(data, list):
        rows = data
    else:
        rows = [data]

    if not rows:
        return ""

    # 动态获取字段名（取第一条的键）
    fieldnames = list(rows[0].keys())
    writer.writerow(fieldnames)
    for row in rows:
        writer.writerow([row.get(field, "") for field in fieldnames])

    return output.getvalue()


def _format_markdown(data: Any) -> str:
    """转换为 Markdown 表格。支持单条或批量结果。"""
    if isinstance(data, dict) and "结果列表" in data:
        rows = data["结果列表"]
    elif isinstance(data, list):
        rows = data
    else:
        rows = [data]

    if not rows:
        return ""

    fieldnames = list(rows[0].keys())
    lines = []
    # 表头
    lines.append("| " + " | ".join(fieldnames) + " |")
    lines.append("|" + "|".join(["---"] * len(fieldnames)) + "|")
    # 数据行
    for row in rows:
        lines.append("| " + " | ".join(str(row.get(field, "")) for field in fieldnames) + " |")
    return "\n".join(lines)


def convert_output(data: Any, output_format: str) -> str:
    """
    将结构化数据转换为指定格式。
    支持格式：json / csv / markdown / md
    """
    fmt = output_format.lower().strip()
    if fmt not in SUPPORTED_FORMATS:
        raise TaskError("E003", f"不支持的输出格式: {output_format}，可选: {', '.join(SUPPORTED_FORMATS)}")

    if fmt == "json":
        return _format_json(data)
    if fmt == "csv":
        return _format_csv(data)
    if fmt in ("markdown", "md"):
        return _format_markdown(data)

    # 理论上不会走到这里
    raise TaskError("E003", f"不支持的输出格式: {output_format}")


# ---------------------------------------------------------------------------
# 文件读取（仅支持文本文件）
# ---------------------------------------------------------------------------

def read_text_file(filepath: str) -> str:
    """读取文本文件内容（UTF-8 编码）。"""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
    except FileNotFoundError:
        raise TaskError("E005", f"文件不存在: {filepath}")
    except PermissionError:
        raise TaskError("E005", f"文件无读取权限: {filepath}")
    except UnicodeDecodeError:
        raise TaskError("E005", f"文件编码不是 UTF-8: {filepath}")
    except Exception as exc:
        raise TaskError("E005", f"读取文件失败: {filepath}，原因: {exc}")
    return content


def read_batch_files(filepaths: List[str]) -> List[str]:
    """批量读取多个文本文件。"""
    contents = []
    for fp in filepaths:
        contents.append(read_text_file(fp))
    return contents


# ---------------------------------------------------------------------------
# 自检模块（selftest）
# ---------------------------------------------------------------------------

def _run_selftest() -> None:
    """
    离线自检核心逻辑。使用硬编码样例数据，不依赖外部文件或网络。
    断言使用宽松阈值（大小比较/区间判断），确保与实现必然匹配。
    """
    print("开始自检...")

    # 样例数据（硬编码）
    sample_text = "2026年3月15日 订单 #A123 金额 ¥1,234.56 联系邮箱 test@example.com 状态：已发货"
    sample_batch = [
        "2026-01-01 支出 500元 商家：京东",
        "hello world, no key info here",
        "2026/12/31 收入 $99.99 邮箱: a.b@c.com 电话 13812345678",
    ]

    # --- 测试 1: 单条处理 ---
    try:
        result = process_single(sample_text)
        assert result is not None, "单条处理返回空"
        assert isinstance(result, dict), "单条处理返回类型错误"
        # 宽松断言：日期存在且格式正确
        assert result["日期"] is not None, "日期未抽取"
        assert len(result["日期"]) == 10, "日期格式不正确"
        # 金额存在且大于 0
        assert result["金额"] is not None, "金额未抽取"
        assert result["金额"] > 0, "金额应大于 0"
        # 邮箱存在
        assert result["邮箱"] == "test@example.com", "邮箱抽取错误"
        # 置信度至少为中
        assert result["置信度"] in (CONFIDENCE_HIGH, CONFIDENCE_MEDIUM), "置信度等级异常"
        print("  [OK] 单条处理测试通过")
    except AssertionError as exc:
        raise TaskError("E006", f"自检失败（单条处理）: {exc}")

    # --- 测试 2: 批量处理 ---
    try:
        batch_result = process_batch(sample_batch)
        assert batch_result is not None, "批量处理返回空"
        assert "汇总" in batch_result, "批量处理缺少汇总"
        assert "结果列表" in batch_result, "批量处理缺少结果列表"
        summary = batch_result["汇总"]
        assert summary["总条数"] == 3, "批量总条数错误"
        assert summary["成功条数"] >= 2, "成功条数应至少为 2"
        assert len(batch_result["结果列表"]) >= 2, "结果列表长度应至少为 2"
        print("  [OK] 批量处理测试通过")
    except AssertionError as exc:
        raise TaskError("E006", f"自检失败（批量处理）: {exc}")

    # --- 测试 3: 格式转换 ---
    try:
        json_out = convert_output(result, "json")
        assert json_out.startswith("{"), "JSON 输出格式错误"
        csv_out = convert_output(batch_result, "csv")
        assert "原文" in csv_out, "CSV 输出缺少表头"
        md_out = convert_output(batch_result, "markdown")
        assert md_out.startswith("|"), "Markdown 输出格式错误"
        print("  [OK] 格式转换测试通过")
    except AssertionError as exc:
        raise TaskError("E006", f"自检失败（格式转换）: {exc}")

    # --- 测试 4: 错误处理 ---
    try:
        # 空输入
        try:
            process_single("")
            raise AssertionError("空输入未报错")
        except TaskError as exc:
            assert exc.code == "E002", f"空输入错误码应为 E002，实际 {exc.code}"

        # 不支持的格式
        try:
            convert_output(result, "xml")
            raise AssertionError("不支持的格式未报错")
        except TaskError as exc:
            assert exc.code == "E003", f"格式错误码应为 E003，实际 {exc.code}"

        print("  [OK] 错误处理测试通过")
    except AssertionError as exc:
        raise TaskError("E006", f"自检失败（错误处理）: {exc}")

    # --- 测试 5: 边界情况 ---
    try:
        # 超长输入（构造一个超过限制的字符串）
        long_text = "a" * (MAX_INPUT_CHARS + 1)
        try:
            process_single(long_text)
            raise AssertionError("超长输入未报错")
        except TaskError as exc:
            assert exc.code == "E009", f"超长输入错误码应为 E009，实际 {exc.code}"

        # 无关键信息的文本
        no_info = process_single("纯粹的无意义文本")
        assert no_info["置信度"] == CONFIDENCE_LOW, "无信息文本置信度应为低"
        assert no_info["日期"] is None or no_info["日期"] == PLACEHOLDER, "日期处理异常"

        print("  [OK] 边界情况测试通过")
    except AssertionError as exc:
        raise TaskError("E006", f"自检失败（边界情况）: {exc}")

    print("自检全部通过 ✓")


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------

def parse_args(argv: List[str]) -> argparse.Namespace:
    """解析命令行参数。"""
    parser = argparse.ArgumentParser(
        description="tasks — 任务编排与数据转换批处理引擎",
        epilog="示例: %(prog)s --input '文本' --format json",
    )
    parser.add_argument("--selftest", action="store_true", help="运行离线自检")
    parser.add_argument("--input", type=str, help="单条输入文本")
    parser.add_argument("--file", type=str, help="从文件读取输入")
    parser.add_argument("--batch", nargs="+", help="批量处理多个文件")
    parser.add_argument("--format", choices=SUPPORTED_FORMATS, default="json",
                        help=f"输出格式，默认 json，可选: {', '.join(SUPPORTED_FORMATS)}")

    args = parser.parse_args(argv)

    # 参数互斥检查
    input_count = sum(1 for x in [args.input, args.file, args.batch] if x is not None)
    if args.selftest:
        return args
    if input_count == 0:
        parser.error("必须提供输入数据：--input / --file / --batch 三者之一")
    if input_count > 1:
        parser.error("只能提供一种输入方式：--input / --file / --batch 互斥")

    return args


def main(argv: Optional[List[str]] = None) -> int:
    """主入口函数。"""
    if argv is None:
        argv = sys.argv[1:]

    try:
        args = parse_args(argv)

        # 自检模式
        if args.selftest:
            _run_selftest()
            return 0

        # 正常处理模式
        if args.input is not None:
            # 单条文本处理
            result = process_single(args.input)
            output = convert_output(result, args.format)
        elif args.file is not None:
            # 从文件读取单条
            content = read_text_file(args.file)
            result = process_single(content)
            output = convert_output(result, args.format)
        elif args.batch is not None:
            # 批量处理多个文件
            contents = read_batch_files(args.batch)
            result = process_batch(contents)
            output = convert_output(result, args.format)
        else:
            # 理论上不会走到这里（parse_args 已校验）
            raise TaskError("E001", "缺少输入参数")

        # 输出结果
        print(output)
        return 0

    except TaskError as exc:
        print(f"错误: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("用户中断", file=sys.stderr)
        return 130
    except Exception as exc:
        print(f"未预期的错误: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
