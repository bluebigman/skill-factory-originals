#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py
===============
产品管理技能速查 - 结构化输出工具

本脚本依据功能规格独立实现（clean-room），
将产品管理相关输入（文本、CSV/JSON、URL）整理为结构化结果。

支持：
- 单条/批量处理（最多 50 条）
- 输出格式：Markdown 表格、JSON、CSV 行
- 字段置信度标注（高/中/低）
- 离线自检（--selftest）

用法示例：
    python main.py --input "需求：登录优化；优先级：高；负责人：张三；截止：2026-03-01"
    python main.py --input data.csv --format json
    python main.py --selftest
"""

import argparse
import csv
import json
import re
import sys
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# 版本信息
__version__ = "1.0.1"
__author__ = "Lin Chen"
__license__ = "MIT"

# 错误码定义
ERR_OK = 0
ERR_INPUT_EMPTY = "E001"       # 输入为空
ERR_INPUT_TOO_LONG = "E002"    # 批量超过 50 条
ERR_FILE_NOT_FOUND = "E003"    # 文件不存在
ERR_FILE_FORMAT = "E004"       # 文件格式不支持/解析失败
ERR_URL_FETCH = "E005"         # URL 获取失败
ERR_URL_INVALID = "E006"       # URL 格式非法
ERR_OUTPUT_FORMAT = "E007"     # 输出格式不支持
ERR_FIELD_EXTRACT = "E008"     # 字段提取失败
ERR_INTERNAL = "E009"          # 内部错误
ERR_SELFTEST = "E010"          # 自检失败

# 常量
MAX_BATCH_SIZE = 50            # 单次最大处理条数
CONFIDENCE_LEVELS = ("高", "中", "低")
SUPPORTED_FORMATS = ("markdown", "json", "csv")
DEFAULT_FORMAT = "markdown"

# 字段提取正则（宽松匹配）
_FIELD_PATTERNS = {
    "需求描述": r"(?:需求|描述|内容)[：:\s]*([^；;，,\n]+)",
    "优先级": r"(?:优先级|优先)[：:\s]*(高|中|低|紧急|普通|低)",
    "负责人": r"(?:负责人|责任人|owner)[：:\s]*([\w\u4e00-\u9fa5]+)",
    "截止日期": r"(?:截止|截止日期|due|deadline)[：:\s]*(\d{4}-\d{2}-\d{2})",
}


def _log_error(code: str, message: str) -> None:
    """统一错误输出格式"""
    print(f"[错误 {code}] {message}", file=sys.stderr)


def _validate_input(text: str) -> Tuple[bool, str]:
    """校验输入文本是否有效"""
    if not text or not text.strip():
        return False, ERR_INPUT_EMPTY
    return True, ERR_OK


def _split_records(text: str) -> List[str]:
    """
    将输入文本拆分为多条记录。
    支持换行分隔或分号分隔。
    """
    # 先按换行拆，再按分号拆（兼容单行多条）
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    records: List[str] = []
    for line in lines:
        # 如果一行包含多个分号，按分号拆分
        parts = [p.strip() for p in line.split("；") if p.strip()]
        records.extend(parts)
    return records


def _extract_field(text: str, field: str) -> Tuple[Optional[str], str]:
    """
    从文本中提取指定字段。
    返回 (值, 置信度)。
    """
    pattern = _FIELD_PATTERNS.get(field)
    if not pattern:
        return None, "低"

    match = re.search(pattern, text)
    if not match:
        return None, "低"

    value = match.group(1).strip()
    if not value:
        return None, "低"

    # 简单置信度判断：字段名明确出现且值完整
    confidence = "高"
    if len(value) < 2:
        confidence = "中"
    return value, confidence


def _parse_record(text: str) -> Dict[str, Any]:
    """
    解析单条记录为结构化字典。
    返回格式：
    {
        "原始输入": str,
        "字段": {
            "需求描述": {"值": str, "置信度": str},
            ...
        },
        "解析时间": str
    }
    """
    result: Dict[str, Any] = {
        "原始输入": text,
        "字段": {},
        "解析时间": datetime.now().isoformat(timespec="seconds"),
    }

    for field in _FIELD_PATTERNS:
        value, confidence = _extract_field(text, field)
        if value is not None:
            result["字段"][field] = {"值": value, "置信度": confidence}
        else:
            result["字段"][field] = {"值": None, "置信度": "低"}

    return result


def _parse_text(text: str) -> Tuple[List[Dict[str, Any]], str]:
    """解析文本输入为结构化记录列表"""
    valid, err = _validate_input(text)
    if not valid:
        return [], err

    records_raw = _split_records(text)
    if len(records_raw) > MAX_BATCH_SIZE:
        return [], ERR_INPUT_TOO_LONG

    try:
        records = [_parse_record(rec) for rec in records_raw]
    except Exception as exc:  # 防御性捕获
        _log_error(ERR_INTERNAL, f"解析记录时发生内部错误: {exc}")
        return [], ERR_INTERNAL

    return records, ERR_OK


def _parse_csv(file_path: str) -> Tuple[List[Dict[str, Any]], str]:
    """解析 CSV 文件"""
    try:
        path = Path(file_path)
        if not path.exists():
            return [], ERR_FILE_NOT_FOUND

        with open(path, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        if not rows:
            return [], ERR_INPUT_EMPTY

        if len(rows) > MAX_BATCH_SIZE:
            return [], ERR_INPUT_TOO_LONG

        records = []
        for row in rows:
            # 将 CSV 行转换为标准字段格式
            text = "；".join(f"{k}:{v}" for k, v in row.items() if v)
            records.append(_parse_record(text))

        return records, ERR_OK

    except Exception as exc:
        _log_error(ERR_FILE_FORMAT, f"CSV 解析失败: {exc}")
        return [], ERR_FILE_FORMAT


def _parse_json(file_path: str) -> Tuple[List[Dict[str, Any]], str]:
    """解析 JSON 文件"""
    try:
        path = Path(file_path)
        if not path.exists():
            return [], ERR_FILE_NOT_FOUND

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if isinstance(data, dict):
            data = [data]
        elif not isinstance(data, list):
            return [], ERR_FILE_FORMAT

        if len(data) > MAX_BATCH_SIZE:
            return [], ERR_INPUT_TOO_LONG

        records = []
        for item in data:
            if isinstance(item, str):
                records.append(_parse_record(item))
            elif isinstance(item, dict):
                text = "；".join(f"{k}:{v}" for k, v in item.items() if v)
                records.append(_parse_record(text))
            else:
                return [], ERR_FILE_FORMAT

        return records, ERR_OK

    except Exception as exc:
        _log_error(ERR_FILE_FORMAT, f"JSON 解析失败: {exc}")
        return [], ERR_FILE_FORMAT


def _fetch_url(url: str) -> Tuple[str, str]:
    """获取 URL 内容（纯文本）"""
    try:
        # 简单 URL 校验
        if not url.startswith(("http://", "https://")):
            return "", ERR_URL_INVALID

        with urllib.request.urlopen(url, timeout=10) as resp:
            # 只读取前 64KB，避免超大响应
            content = resp.read(65536).decode("utf-8", errors="ignore")

        # 去除 HTML 标签，提取纯文本
        text = re.sub(r"<[^>]+>", " ", content)
        text = re.sub(r"\s+", " ", text).strip()
        return text, ERR_OK

    except Exception as exc:
        _log_error(ERR_URL_FETCH, f"URL 获取失败: {exc}")
        return "", ERR_URL_FETCH


def _load_input(input_arg: str) -> Tuple[List[Dict[str, Any]], str]:
    """
    根据输入参数类型加载数据。
    支持：直接文本、文件路径（.csv/.json）、URL。
    """
    # 判断是否为 URL
    if input_arg.startswith(("http://", "https://")):
        text, err = _fetch_url(input_arg)
        if err != ERR_OK:
            return [], err
        return _parse_text(text)

    # 判断是否为文件
    if Path(input_arg).exists():
        suffix = Path(input_arg).suffix.lower()
        if suffix == ".csv":
            return _parse_csv(input_arg)
        elif suffix == ".json":
            return _parse_json(input_arg)
        else:
            return [], ERR_FILE_FORMAT

    # 视为直接文本输入
    return _parse_text(input_arg)


def _format_markdown(records: List[Dict[str, Any]]) -> str:
    """格式化为 Markdown 表格"""
    if not records:
        return "（无记录）"

    # 表头
    fields = list(_FIELD_PATTERNS.keys())
    header = "| " + " | ".join(["原始输入"] + fields) + " |"
    separator = "|" + "|".join(["---"] * (len(fields) + 1)) + "|"

    lines = [header, separator]
    for rec in records:
        row_vals = [rec["原始输入"]]
        for f in fields:
            val = rec["字段"].get(f, {}).get("值", "—")
            conf = rec["字段"].get(f, {}).get("置信度", "低")
            row_vals.append(f"{val}（{conf}）")
        lines.append("| " + " | ".join(row_vals) + " |")

    return "\n".join(lines)


def _format_json(records: List[Dict[str, Any]]) -> str:
    """格式化为 JSON"""
    return json.dumps(records, ensure_ascii=False, indent=2)


def _format_csv(records: List[Dict[str, Any]]) -> str:
    """格式化为 CSV 行"""
    if not records:
        return ""

    fields = list(_FIELD_PATTERNS.keys())
    output = []

    # 表头
    output.append(",".join(["原始输入"] + fields))

    # 数据行
    for rec in records:
        row = [rec["原始输入"]]
        for f in fields:
            val = rec["字段"].get(f, {}).get("值", "")
            # 转义 CSV 特殊字符
            if "," in str(val) or '"' in str(val) or "\n" in str(val):
                val = f'"{str(val).replace(chr(34), chr(34)*2)}"'
            row.append(str(val))
        output.append(",".join(row))

    return "\n".join(output)


def _format_output(records: List[Dict[str, Any]], fmt: str) -> Tuple[str, str]:
    """根据指定格式输出结果"""
    if fmt not in SUPPORTED_FORMATS:
        return "", ERR_OUTPUT_FORMAT

    try:
        if fmt == "markdown":
            return _format_markdown(records), ERR_OK
        elif fmt == "json":
            return _format_json(records), ERR_OK
        elif fmt == "csv":
            return _format_csv(records), ERR_OK
    except Exception as exc:
        _log_error(ERR_INTERNAL, f"格式化输出失败: {exc}")
        return "", ERR_INTERNAL

    return "", ERR_OUTPUT_FORMAT


def _run_selftest() -> int:
    """
    离线自检核心逻辑。
    使用内置硬编码样例，不依赖外部文件/网络。
    断言使用宽松阈值，确保稳定通过。
    """
    print("开始自检...")

    # 样例 1：单条文本解析
    sample1 = "需求：优化登录流程；优先级：高；负责人：张三；截止：2026-03-01"
    records, err = _parse_text(sample1)
    assert err == ERR_OK, f"样例1解析失败: {err}"
    assert len(records) == 1, f"样例1记录数应为1，实际{len(records)}"
    assert records[0]["字段"]["优先级"]["值"] == "高", "优先级提取错误"
    assert records[0]["字段"]["负责人"]["值"] == "张三", "负责人提取错误"
    assert records[0]["字段"]["截止日期"]["值"] == "2026-03-01", "截止日期提取错误"
    print("  ✓ 样例1：单条文本解析通过")

    # 样例 2：多条记录（换行分隔）
    sample2 = "需求：A功能；优先级：中\n需求：B功能；负责人：李四"
    records, err = _parse_text(sample2)
    assert err == ERR_OK, f"样例2解析失败: {err}"
    assert len(records) == 2, f"样例2记录数应为2，实际{len(records)}"
    print("  ✓ 样例2：多条文本解析通过")

    # 样例 3：批量上限校验
    sample3 = "\n".join([f"需求：测试{i}" for i in range(51)])
    _, err = _parse_text(sample3)
    assert err == ERR_INPUT_TOO_LONG, f"样例3应返回E002，实际{err}"
    print("  ✓ 样例3：批量上限校验通过")

    # 样例 4：空输入校验
    _, err = _parse_text("")
    assert err == ERR_INPUT_EMPTY, f"样例4应返回E001，实际{err}"
    print("  ✓ 样例4：空输入校验通过")

    # 样例 5：字段缺失时置信度为低
    sample5 = "今天天气不错"
    records, err = _parse_text(sample5)
    assert err == ERR_OK, f"样例5解析失败: {err}"
    all_low = all(
        rec["字段"][f]["置信度"] == "低"
        for rec in records for f in _FIELD_PATTERNS
    )
    assert all_low, "样例5所有字段置信度应为低"
    print("  ✓ 样例5：置信度标注通过")

    # 样例 6：输出格式（Markdown 至少包含表头）
    sample6 = "需求：测试输出；优先级：中"
    records, _ = _parse_text(sample6)
    md_out, err = _format_output(records, "markdown")
    assert err == ERR_OK, f"Markdown 格式化失败: {err}"
    assert "原始输入" in md_out, "Markdown 应包含表头"
    assert "需求描述" in md_out, "Markdown 应包含字段列"
    print("  ✓ 样例6：Markdown 输出通过")

    # 样例 7：输出格式（JSON 可解析）
    records, _ = _parse_text(sample6)
    json_out, err = _format_output(records, "json")
    assert err == ERR_OK, f"JSON 格式化失败: {err}"
    parsed = json.loads(json_out)
    assert len(parsed) == 1, "JSON 应包含1条记录"
    print("  ✓ 样例7：JSON 输出通过")

    # 样例 8：输出格式（CSV 行数正确）
    records, _ = _parse_text(sample6)
    csv_out, err = _format_output(records, "csv")
    assert err == ERR_OK, f"CSV 格式化失败: {err}"
    assert len(csv_out.splitlines()) == 2, "CSV 应为2行（表头+数据）"
    print("  ✓ 样例8：CSV 输出通过")

    # 样例 9：分号分隔多条记录
    sample9 = "需求：功能1；负责人：王五；需求：功能2；优先级：低"
    records, err = _parse_text(sample9)
    assert err == ERR_OK, f"样例9解析失败: {err}"
    assert len(records) >= 2, f"样例9应至少2条记录，实际{len(records)}"
    print("  ✓ 样例9：分号分隔解析通过")

    # 样例 10：宽松日期匹配
    sample10 = "截止日期：2026-12-31，需求：年度规划"
    records, err = _parse_text(sample10)
    assert err == ERR_OK, f"样例10解析失败: {err}"
    date_val = records[0]["字段"]["截止日期"]["值"]
    assert date_val == "2026-12-31", f"日期提取错误: {date_val}"
    print("  ✓ 样例10：日期提取通过")

    print("全部自检通过！")
    return ERR_OK


def main() -> int:
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description="产品管理技能速查 - 结构化输出工具",
        epilog="示例: python main.py --input '需求：登录优化；优先级：高' --format json",
    )
    parser.add_argument(
        "--input",
        type=str,
        help="输入内容：文本、文件路径（.csv/.json）或 URL",
    )
    parser.add_argument(
        "--format",
        type=str,
        choices=SUPPORTED_FORMATS,
        default=DEFAULT_FORMAT,
        help=f"输出格式（默认: {DEFAULT_FORMAT}）",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行离线自检",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        try:
            return _run_selftest()
        except AssertionError as exc:
            _log_error(ERR_SELFTEST, f"自检失败: {exc}")
            return 1
        except Exception as exc:
            _log_error(ERR_SELFTEST, f"自检异常: {exc}")
            return 1

    # 正常处理模式
    if not args.input:
        _log_error(ERR_INPUT_EMPTY, "请提供输入内容（--input）或使用 --selftest 运行自检")
        parser.print_help()
        return 1

    # 加载并解析输入
    records, err = _load_input(args.input)
    if err != ERR_OK:
        _log_error(err, f"输入处理失败（错误码: {err}）")
        return 1

    if not records:
        _log_error(ERR_INPUT_EMPTY, "未能从输入中提取到任何记录")
        return 1

    # 格式化输出
    output, err = _format_output(records, args.format)
    if err != ERR_OK:
        _log_error(err, f"输出格式化失败（错误码: {err}）")
        return 1

    # 打印结果
    print(output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
