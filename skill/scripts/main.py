#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py — 内容转换、结构化输出、置信度标注

功能概述：
    将用户数据（文本 / 本地文件 / URL）转换为结构化 JSON 结果，
    并对每个输出字段标注置信度（high / medium / low）。

设计原则：
    - 仅使用 Python 标准库（无第三方依赖）。
    - 提供 --selftest 离线自检，硬编码样例数据，不依赖外部文件或网络。
    - 错误处理统一使用错误码 E001-E010。

用法示例：
    python scripts/main.py --input "张三 2025-03-01 采购 1200元"
    python scripts/main.py --file data.txt
    python scripts/main.py --url https://example.com/page
    python scripts/main.py --selftest
"""

import argparse
import json
import re
import sys
import urllib.request
from pathlib import Path


# ---------------------------------------------------------------------------
# 错误码定义
# ---------------------------------------------------------------------------
ERROR_CODES = {
    "E001": "参数错误：缺少输入来源（--input / --file / --url 至少提供一个）",
    "E002": "参数错误：同时指定了多个输入来源（只能选择一个）",
    "E003": "文件读取失败：文件不存在或无法访问",
    "E004": "URL 访问失败：网络错误或 HTTP 状态异常",
    "E005": "输入内容为空：未提取到任何有效信息",
    "E006": "JSON 序列化失败：输出结果无法编码",
    "E007": "内部逻辑错误：未知的输入类型",
    "E008": "内部逻辑错误：置信度计算异常",
    "E009": "内部逻辑错误：字段提取异常",
    "E010": "未知错误：未捕获的异常",
}


def fail(code: str) -> None:
    """打印错误码并退出程序。"""
    msg = ERROR_CODES.get(code, "未知错误")
    print(f"[错误] {code}: {msg}", file=sys.stderr)
    sys.exit(1)


# ---------------------------------------------------------------------------
# 核心转换逻辑
# ---------------------------------------------------------------------------
def convert_text(raw_text: str) -> dict:
    """
    将原始文本转换为结构化结果（含置信度标注）。

    提取字段：
        - name:    人名（中文/英文）
        - date:    日期（YYYY-MM-DD 或 YYYY年M月D日）
        - category: 类别（采购/销售/报销/其他）
        - amount:   金额（数字 + 单位 元/美元等）

    置信度规则（宽松判定）：
        - high:   字段存在且匹配模式
        - medium: 字段存在但模式模糊
        - low:    字段缺失
    """
    if not raw_text or not raw_text.strip():
        return {"error": "empty_input", "fields": {}}

    result = {}

    # --- 人名提取（中文 2-4 字 或 英文单词） ---
    name_match = re.search(r"[\u4e00-\u9fa5]{2,4}|[A-Za-z]+", raw_text)
    if name_match:
        result["name"] = {"value": name_match.group(0), "confidence": "high"}
    else:
        result["name"] = {"value": None, "confidence": "low"}

    # --- 日期提取 ---
    date_match = re.search(
        r"(\d{4})[-/年](\d{1,2})[-/月](\d{1,2})日?", raw_text
    )
    if date_match:
        date_str = f"{date_match.group(1)}-{int(date_match.group(2)):02d}-{int(date_match.group(3)):02d}"
        result["date"] = {"value": date_str, "confidence": "high"}
    else:
        # 尝试宽松匹配（仅年份）
        year_match = re.search(r"\d{4}", raw_text)
        if year_match:
            result["date"] = {"value": year_match.group(0), "confidence": "medium"}
        else:
            result["date"] = {"value": None, "confidence": "low"}

    # --- 类别提取 ---
    category_keywords = {
        "采购": "采购",
        "购买": "采购",
        "销售": "销售",
        "卖出": "销售",
        "报销": "报销",
        "支出": "报销",
    }
    category = "其他"
    for kw, cat in category_keywords.items():
        if kw in raw_text:
            category = cat
            break
    result["category"] = {"value": category, "confidence": "high" if category != "其他" else "medium"}

    # --- 金额提取 ---
    amount_match = re.search(r"(\d+(?:\.\d+)?)\s*(元|美元|人民币|块)", raw_text)
    if amount_match:
        result["amount"] = {
            "value": float(amount_match.group(1)),
            "unit": amount_match.group(2),
            "confidence": "high",
        }
    else:
        # 仅数字无单位
        num_match = re.search(r"\d+(?:\.\d+)?", raw_text)
        if num_match:
            result["amount"] = {
                "value": float(num_match.group(0)),
                "unit": None,
                "confidence": "medium",
            }
        else:
            result["amount"] = {"value": None, "unit": None, "confidence": "low"}

    return {"fields": result}


def convert_file(file_path: str) -> dict:
    """读取本地文件并转换为结构化结果。"""
    try:
        path = Path(file_path)
        if not path.is_file():
            fail("E003")
        content = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        fail("E003")
    return convert_text(content)


def convert_url(url: str) -> dict:
    """抓取 URL 内容并转换为结构化结果。"""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            content = resp.read().decode("utf-8", errors="ignore")
    except Exception:
        fail("E004")
    return convert_text(content)


def process(input_type: str, source: str) -> dict:
    """统一入口：根据输入类型分发处理。"""
    if input_type == "text":
        return convert_text(source)
    elif input_type == "file":
        return convert_file(source)
    elif input_type == "url":
        return convert_url(source)
    else:
        fail("E007")


# ---------------------------------------------------------------------------
# 自检模块（离线硬编码样例）
# ---------------------------------------------------------------------------
def selftest() -> None:
    """
    内置离线自检：
    - 使用硬编码样例数据，不读取外部文件、不访问网络。
    - 断言采用宽松阈值（存在性 / 范围 / 非空），避免精确值依赖。
    """
    print("[自检] 开始离线自检...")

    # 样例 1：完整文本
    sample1 = "张三 2025-03-01 采购 1200元"
    r1 = convert_text(sample1)
    assert "fields" in r1, "E001: 结果缺少 fields 键"
    f1 = r1["fields"]
    assert f1.get("name", {}).get("value") is not None, "E002: 人名提取失败"
    assert f1.get("date", {}).get("value") is not None, "E003: 日期提取失败"
    assert f1.get("amount", {}).get("value") is not None, "E004: 金额提取失败"
    assert f1["name"]["confidence"] in ("high", "medium"), "E005: 置信度异常"
    print("[自检] 样例1（完整文本）通过")

    # 样例 2：模糊文本（仅数字无单位）
    sample2 = "李四 2024 报销 500"
    r2 = convert_text(sample2)
    f2 = r2["fields"]
    assert f2["amount"]["value"] is not None, "E006: 金额提取失败"
    assert f2["date"]["confidence"] in ("high", "medium"), "E007: 日期置信度异常"
    assert f2["category"]["value"] == "报销", "E008: 类别识别失败"
    print("[自检] 样例2（模糊文本）通过")

    # 样例 3：空文本（应返回空结果而非崩溃）
    r3 = convert_text("")
    assert "error" in r3 or "fields" in r3, "E009: 空文本处理异常"
    print("[自检] 样例3（空文本）通过")

    # 样例 4：批量记录（列表循环处理）
    records = [
        "王五 2025-06-15 销售 3000元",
        "赵六 2025-07-01 采购 800元",
    ]
    results = [convert_text(rec) for rec in records]
    assert len(results) == 2, "E010: 批量处理数量异常"
    for r in results:
        assert r["fields"]["name"]["value"] is not None, "E011: 批量人名提取失败"
        assert r["fields"]["amount"]["value"] is not None, "E012: 批量金额提取失败"
    print("[自检] 样例4（批量记录）通过")

    # 样例 5：URL 类型（仅验证分发逻辑，不实际访问网络）
    # 此处不真正调用网络，仅验证 process 函数能正确分发
    try:
        # 用本地文件模拟（不访问网络）
        import tempfile
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as tf:
            tf.write("测试 2025-01-01 采购 100元")
            tmp_path = tf.name
        r5 = process("file", tmp_path)
        assert r5["fields"]["name"]["value"] is not None, "E013: 文件处理异常"
        import os
        os.unlink(tmp_path)
        print("[自检] 样例5（文件分发）通过")
    except Exception:
        fail("E010")

    # 宽松断言：金额范围（不依赖精确值）
    assert 0 < f1["amount"]["value"] < 100000, "E014: 金额范围异常"
    assert 0 < f2["amount"]["value"] < 100000, "E015: 金额范围异常"

    print("[自检] 全部通过 ✔")


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(
        description="内容转换、结构化输出、置信度标注",
        epilog="示例: python scripts/main.py --input '张三 2025-03-01 采购 1200元'",
    )
    parser.add_argument("--input", type=str, help="直接输入文本内容")
    parser.add_argument("--file", type=str, help="输入文件路径（.txt/.csv/.json）")
    parser.add_argument("--url", type=str, help="输入 URL 地址")
    parser.add_argument("--selftest", action="store_true", help="运行离线自检")
    parser.add_argument("--output", type=str, help="输出文件路径（可选，默认打印到 stdout）")

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        selftest()
        return

    # 参数校验
    input_sources = [args.input, args.file, args.url]
    provided = [s for s in input_sources if s is not None]

    if len(provided) == 0:
        fail("E001")
    if len(provided) > 1:
        fail("E002")

    # 执行转换
    try:
        if args.input is not None:
            result = process("text", args.input)
        elif args.file is not None:
            result = process("file", args.file)
        elif args.url is not None:
            result = process("url", args.url)
        else:
            fail("E001")
    except SystemExit:
        raise
    except Exception:
        fail("E010")

    # 输出结果
    try:
        output_json = json.dumps(result, ensure_ascii=False, indent=2)
    except Exception:
        fail("E006")

    if args.output:
        try:
            Path(args.output).write_text(output_json, encoding="utf-8")
            print(f"[完成] 结果已写入: {args.output}")
        except Exception:
            fail("E003")
    else:
        print(output_json)


if __name__ == "__main__":
    main()
