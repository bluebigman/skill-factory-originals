#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
redesigned-pancake 数据整理工具
===============================
将用户提供的文本、文件或 URL 内容转化为带置信度标记的结构化结果。

仅依据功能规格独立实现（clean-room）。
"""

import argparse
import json
import re
import sys
import urllib.request
from pathlib import Path

# 错误码定义
ERR_OK = "E000"
ERR_INPUT_EMPTY = "E001"
ERR_FILE_NOT_FOUND = "E002"
ERR_FILE_READ = "E003"
ERR_URL_FETCH = "E004"
ERR_UNSUPPORTED_FORMAT = "E005"
ERR_JSON_PARSE = "E006"
ERR_OUTPUT_WRITE = "E007"
ERR_INVALID_TEMPLATE = "E008"
ERR_INTERNAL = "E009"
ERR_UNKNOWN = "E010"


# ==================== 核心逻辑 ====================

def parse_input(raw_text: str) -> list:
    """
    将原始文本拆分为多条记录。
    规则：
      - 按空行或分隔符（--- 或 ===）区分多条记录
      - 每条记录保留原始内容
    """
    if not raw_text or not raw_text.strip():
        return []

    # 使用空行或分隔符拆分
    parts = re.split(r"\n\s*\n|(?:\n\s*[-=]{3,}\s*\n)", raw_text.strip())
    records = [p.strip() for p in parts if p.strip()]
    return records


def extract_entities(text: str) -> dict:
    """
    从单条文本中提取关键信息：
      - 日期（YYYY-MM-DD 或 YYYY年MM月DD日）
      - 数字（整数、小数、百分比）
      - 邮箱
      - 网址
      - 结论性语句（包含"结论/结果/确定"等关键词的句子）
    """
    result = {
        "dates": [],
        "numbers": [],
        "emails": [],
        "urls": [],
        "conclusions": [],
    }

    # 日期
    date_patterns = [
        r"\d{4}-\d{1,2}-\d{1,2}",
        r"\d{4}年\d{1,2}月\d{1,2}日",
    ]
    for pat in date_patterns:
        result["dates"].extend(re.findall(pat, text))

    # 数字（含小数和百分比）
    num_pattern = r"\d+\.?\d*(?:%|％)?"
    result["numbers"] = re.findall(num_pattern, text)

    # 邮箱
    email_pattern = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
    result["emails"] = re.findall(email_pattern, text)

    # 网址
    url_pattern = r"https?://[^\s<>\"']+"
    result["urls"] = re.findall(url_pattern, text)

    # 结论性语句（按句号/分号/换行切分后筛选）
    sentences = re.split(r"[。；;\n]", text)
    conclusion_keywords = ["结论", "结果", "确定", "确认", "表明", "显示"]
    for sent in sentences:
        sent = sent.strip()
        if any(kw in sent for kw in conclusion_keywords) and len(sent) >= 5:
            result["conclusions"].append(sent)

    # 去重并保持顺序
    for key in result:
        seen = set()
        unique = []
        for item in result[key]:
            if item not in seen:
                seen.add(item)
                unique.append(item)
        result[key] = unique

    return result


def make_confidence(value, has_source: bool = True) -> str:
    """
    根据信息完整度返回置信度：
      - 高：值非空且来源明确
      - 中：值非空但来源不明确
      - 低：值为空或需要核实
    """
    if value is None or value == "" or value == []:
        return "低"
    return "高" if has_source else "中"


def build_record(record_text: str, source: str = "文本") -> dict:
    """
    将单条文本转换为结构化记录（含置信度标注）。
    """
    entities = extract_entities(record_text)

    # 原始文本作为基础字段
    record = {
        "原文": record_text,
        "日期": entities["dates"],
        "数字": entities["numbers"],
        "邮箱": entities["emails"],
        "网址": entities["urls"],
        "结论": entities["conclusions"],
        "来源": source,
    }

    # 添加置信度标注
    confidence = {}
    for field in ["日期", "数字", "邮箱", "网址", "结论"]:
        confidence[field] = make_confidence(record[field], source != "文本")

    record["置信度"] = confidence

    # 低置信度字段附加占位符
    for field, level in confidence.items():
        if level == "低":
            record[field] = f"{record[field]} [需核实:{field}]"

    return record


def process_text(raw_text: str, source: str = "文本") -> dict:
    """
    处理纯文本输入，返回结构化结果。
    """
    records = parse_input(raw_text)
    if not records:
        return {
            "错误码": ERR_INPUT_EMPTY,
            "错误信息": "输入内容为空",
            "记录数": 0,
            "记录": [],
        }

    structured = [build_record(rec, source) for rec in records]
    return {
        "错误码": ERR_OK,
        "记录数": len(structured),
        "记录": structured,
    }


def process_file(file_path: str) -> dict:
    """
    处理文件输入（.txt/.csv/.json/.md）。
    """
    path = Path(file_path)
    if not path.exists():
        return {"错误码": ERR_FILE_NOT_FOUND, "错误信息": f"文件不存在: {file_path}"}

    suffix = path.suffix.lower()
    if suffix not in [".txt", ".csv", ".md", ".json"]:
        return {"错误码": ERR_UNSUPPORTED_FORMAT, "错误信息": f"不支持的文件格式: {suffix}"}

    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except Exception as exc:
        return {"错误码": ERR_FILE_READ, "错误信息": f"读取文件失败: {exc}"}

    if suffix == ".json":
        # JSON 文件尝试解析
        try:
            data = json.loads(content)
            if isinstance(data, list):
                # 列表格式：每条记录一个对象
                records = []
                for item in data:
                    if isinstance(item, dict):
                        records.append(json.dumps(item, ensure_ascii=False))
                    else:
                        records.append(str(item))
                return {
                    "错误码": ERR_OK,
                    "记录数": len(records),
                    "记录": [build_record(r, f"文件:{path.name}") for r in records],
                }
            else:
                # 单个对象
                return {
                    "错误码": ERR_OK,
                    "记录数": 1,
                    "记录": [build_record(json.dumps(data, ensure_ascii=False), f"文件:{path.name}")],
                }
        except json.JSONDecodeError as exc:
            return {"错误码": ERR_JSON_PARSE, "错误信息": f"JSON 解析失败: {exc}"}
    else:
        # 纯文本类文件
        return process_text(content, f"文件:{path.name}")


def process_url(url: str) -> dict:
    """
    处理 URL 输入（仅公开可访问）。
    """
    try:
        # 设置超时和 User-Agent
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            content = resp.read().decode("utf-8", errors="replace")
    except Exception as exc:
        return {"错误码": ERR_URL_FETCH, "错误信息": f"获取 URL 失败: {exc}"}

    # 简单去除 HTML 标签
    text = re.sub(r"<[^>]+>", " ", content)
    text = re.sub(r"\s+", " ", text).strip()

    return process_text(text, f"URL:{url}")


def format_output(result: dict, output_format: str = "json") -> str:
    """
    将结果格式化为 JSON 或 Markdown。
    """
    if result.get("错误码") != ERR_OK:
        return json.dumps(result, ensure_ascii=False, indent=2)

    if output_format == "markdown":
        lines = []
        lines.append(f"# 结构化输出（共 {result['记录数']} 条记录）\n")
        for i, rec in enumerate(result["记录"], 1):
            lines.append(f"## 记录 {i}")
            lines.append(f"- **原文**: {rec['原文'][:100]}{'...' if len(rec['原文']) > 100 else ''}")
            lines.append(f"- **来源**: {rec['来源']}")
            for field in ["日期", "数字", "邮箱", "网址", "结论"]:
                conf = rec["置信度"].get(field, "中")
                lines.append(f"- **{field}**: {rec[field]}  (置信度: {conf})")
            lines.append("")
        return "\n".join(lines)
    else:
        return json.dumps(result, ensure_ascii=False, indent=2)


# ==================== 自检功能 ====================

def run_selftest() -> bool:
    """
    内置硬编码样例数据，离线自检核心逻辑。
    使用宽松断言，不依赖精确值。
    """
    print("[自检] 开始运行核心逻辑自检...")

    # 测试样例1：基本文本解析
    sample1 = "2024-01-15 会议记录\n参会人数 12 人，预算 5000 元。\n结论：项目进展顺利。\n联系邮箱 test@example.com"
    result1 = process_text(sample1)
    assert result1["错误码"] == ERR_OK, "样例1 应成功处理"
    assert result1["记录数"] >= 1, "样例1 应至少产生 1 条记录"
    rec1 = result1["记录"][0]
    assert len(rec1["日期"]) >= 1, "样例1 应提取到日期"
    assert len(rec1["数字"]) >= 2, "样例1 应提取到多个数字"
    assert len(rec1["邮箱"]) >= 1, "样例1 应提取到邮箱"
    assert len(rec1["结论"]) >= 1, "样例1 应提取到结论性语句"
    print("  ✓ 样例1（文本解析）通过")

    # 测试样例2：多记录拆分
    sample2 = "记录A：销售额 100 万\n\n记录B：成本 30 万\n---\n记录C：利润 70 万"
    result2 = process_text(sample2)
    assert result2["记录数"] >= 3, "样例2 应拆分为 3 条记录"
    print("  ✓ 样例2（多记录拆分）通过")

    # 测试样例3：空输入
    result3 = process_text("   ")
    assert result3["错误码"] == ERR_INPUT_EMPTY, "样例3 应返回空输入错误码"
    print("  ✓ 样例3（空输入处理）通过")

    # 测试样例4：置信度标记
    sample4 = "无来源数据 2025-01-01"
    result4 = process_text(sample4)
    assert result4["错误码"] == ERR_OK, "样例4 应成功处理"
    rec4 = result4["记录"][0]
    # 文本来源置信度应为中或高（非低）
    assert rec4["置信度"]["日期"] in ["中", "高"], "样例4 日期置信度不应为低"
    print("  ✓ 样例4（置信度标注）通过")

    # 测试样例5：URL 处理（不实际访问，仅验证函数存在和错误处理）
    # 使用无效 URL 测试错误处理路径
    result5 = process_url("http://invalid.local.host/nonexistent")
    assert result5["错误码"] == ERR_URL_FETCH, "样例5 应返回 URL 获取错误"
    print("  ✓ 样例5（URL 错误处理）通过")

    # 测试样例6：JSON 输出格式
    sample6 = "测试 JSON 输出"
    result6 = process_text(sample6)
    output6 = format_output(result6, "json")
    parsed = json.loads(output6)
    assert parsed["错误码"] == ERR_OK, "样例6 JSON 输出应可解析"
    print("  ✓ 样例6（JSON 输出）通过")

    # 测试样例7：Markdown 输出格式
    output7 = format_output(result6, "markdown")
    assert "结构化输出" in output7, "样例7 Markdown 应包含标题"
    assert "记录 1" in output7, "样例7 Markdown 应包含记录编号"
    print("  ✓ 样例7（Markdown 输出）通过")

    print("[自检] 全部测试通过！")
    return True


# ==================== 主入口 ====================

def main():
    parser = argparse.ArgumentParser(
        description="redesigned-pancake 数据整理工具：将任意数据转为带置信度标记的结构化结果"
    )
    parser.add_argument("input", nargs="?", help="输入内容：文本、文件路径或 URL")
    parser.add_argument("--file", "-f", help="从文件读取输入")
    parser.add_argument("--url", "-u", help="从 URL 获取输入")
    parser.add_argument("--format", "-F", choices=["json", "markdown"], default="json",
                        help="输出格式（默认: json）")
    parser.add_argument("--output", "-o", help="输出到文件（默认输出到 stdout）")
    parser.add_argument("--selftest", action="store_true", help="运行内置自检")

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        try:
            run_selftest()
            sys.exit(0)
        except AssertionError as exc:
            print(f"[自检] 失败: {exc}")
            sys.exit(1)

    # 确定输入来源
    result = None
    if args.url:
        result = process_url(args.url)
    elif args.file:
        result = process_file(args.file)
    elif args.input:
        # 判断是文件路径还是纯文本
        if Path(args.input).exists():
            result = process_file(args.input)
        elif args.input.startswith(("http://", "https://")):
            result = process_url(args.input)
        else:
            result = process_text(args.input)
    else:
        # 无输入参数，尝试从 stdin 读取
        try:
            stdin_text = sys.stdin.read().strip()
            if stdin_text:
                result = process_text(stdin_text)
            else:
                result = {"错误码": ERR_INPUT_EMPTY, "错误信息": "未提供任何输入"}
        except KeyboardInterrupt:
            result = {"错误码": ERR_INPUT_EMPTY, "错误信息": "用户取消输入"}

    if result is None:
        result = {"错误码": ERR_INTERNAL, "错误信息": "未知处理错误"}

    # 格式化输出
    output_text = format_output(result, args.format)

    # 输出到文件或 stdout
    if args.output:
        try:
            Path(args.output).write_text(output_text, encoding="utf-8")
            print(f"结果已写入: {args.output}")
        except Exception as exc:
            print(f"错误码 {ERR_OUTPUT_WRITE}: 写入输出文件失败 - {exc}", file=sys.stderr)
            sys.exit(1)
    else:
        print(output_text)

    # 非 OK 错误码时返回非零退出码
    if result.get("错误码") != ERR_OK:
        sys.exit(1)


if __name__ == "__main__":
    main()
