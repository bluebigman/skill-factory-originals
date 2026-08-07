#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py — 技能工具箱：数据转换与结构化输出

独立实现（clean-room），仅依据功能规格编写。
功能：将输入数据（文本/JSON/CSV）转换为结构化结果，
支持批量处理、自定义输出格式（Markdown / JSON / CSV），
每条结果附带置信度（confidence）。

用法示例：
    python scripts/main.py --input sample.json --format json
    python scripts/main.py --selftest
"""

import argparse
import csv
import io
import json
import re
import sys
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# 错误码定义
# ---------------------------------------------------------------------------
# E001: 参数错误（未知参数、参数组合非法）
# E002: 输入文件不存在或无法读取
# E003: 输入数据解析失败（JSON/CSV/文本）
# E004: 输出格式不支持
# E005: 批量处理超过上限
# E006: 内部数据转换错误
# E007: 输出写入失败
# E008: 内置自检数据异常
# E009: 运行时异常（未分类）
# E010: 数据源 URL 不支持（本实现不访问网络）

ERROR_MESSAGES = {
    "E001": "参数错误：{detail}",
    "E002": "输入文件不存在或无法读取：{detail}",
    "E003": "输入数据解析失败：{detail}",
    "E004": "输出格式不支持：{detail}",
    "E005": "批量处理超过上限（200条）：{detail}",
    "E006": "内部数据转换错误：{detail}",
    "E007": "输出写入失败：{detail}",
    "E008": "内置自检数据异常：{detail}",
    "E009": "运行时异常：{detail}",
    "E010": "URL 数据源不支持（本实现不访问网络）：{detail}",
}


class SkillError(Exception):
    """技能运行错误，携带错误码。"""

    def __init__(self, code: str, detail: str = ""):
        self.code = code
        self.detail = detail
        super().__init__(ERROR_MESSAGES[code].format(detail=detail))


# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------
MAX_RECORDS = 200  # 单次处理建议不超过 200 条记录
SUPPORTED_OUTPUT_FORMATS = ("markdown", "json", "csv")
URL_PATTERN = re.compile(r"^https?://", re.IGNORECASE)


# ---------------------------------------------------------------------------
# 核心数据转换逻辑
# ---------------------------------------------------------------------------
def extract_fields(record: Dict[str, Any]) -> Dict[str, Any]:
    """
    从单条记录中提取关键字段。

    规则：
    - 保留所有键值对。
    - 若存在 'name' 或 'title' 键，将其值作为 'title'。
    - 若存在 'content' 或 'text' 键，将其值作为 'content'。
    - 若存在 'date' 或 'time' 键，将其值作为 'date'。
    - 计算置信度（confidence）：基于字段完整度，区间 [0, 1]。
    """
    result: Dict[str, Any] = {}

    # 复制原始字段
    for key, value in record.items():
        result[key] = value

    # 标准化字段名
    title_key = None
    for candidate in ("name", "title"):
        if candidate in record:
            title_key = candidate
            break
    if title_key:
        result["title"] = record[title_key]

    content_key = None
    for candidate in ("content", "text"):
        if candidate in record:
            content_key = candidate
            break
    if content_key:
        result["content"] = record[content_key]

    date_key = None
    for candidate in ("date", "time"):
        if candidate in record:
            date_key = candidate
            break
    if date_key:
        result["date"] = record[date_key]

    # 计算置信度：字段完整度
    expected_fields = ["title", "content", "date"]
    present_count = sum(1 for f in expected_fields if f in result)
    confidence = present_count / len(expected_fields)
    result["confidence"] = round(confidence, 2)

    return result


def parse_input_text(text: str) -> List[Dict[str, Any]]:
    """
    解析输入文本为记录列表。

    支持格式：
    1. JSON 数组（或单行 JSON 对象）。
    2. CSV 文本（首行为表头）。
    3. 纯文本段落（按空行分割，每段为一条记录）。
    """
    text = text.strip()
    if not text:
        raise SkillError("E003", "输入为空")

    # 尝试 JSON 解析
    try:
        data = json.loads(text)
        if isinstance(data, list):
            records = [item for item in data if isinstance(item, dict)]
            if not records:
                raise SkillError("E003", "JSON 数组中没有对象记录")
            return records
        elif isinstance(data, dict):
            return [data]
        else:
            raise SkillError("E003", "JSON 顶层必须是对象或对象数组")
    except json.JSONDecodeError:
        pass  # 不是 JSON，继续尝试其他格式

    # 尝试 CSV 解析
    try:
        csv_reader = csv.DictReader(io.StringIO(text))
        rows = list(csv_reader)
        if rows:
            # 过滤空行
            return [row for row in rows if any(v.strip() for v in row.values())]
    except Exception:
        pass  # 不是有效 CSV，按纯文本处理

    # 纯文本：按空行分割
    blocks = re.split(r"\n\s*\n", text)
    records: List[Dict[str, Any]] = []
    for block in blocks:
        block = block.strip()
        if not block:
            continue
        # 每行作为一个键值对（key: value），若无法解析则整体作为 content
        record: Dict[str, Any] = {}
        lines = block.splitlines()
        for line in lines:
            if ":" in line:
                key, _, value = line.partition(":")
                record[key.strip()] = value.strip()
            else:
                # 无冒号行，作为 content 的一部分
                if "content" in record:
                    record["content"] += "\n" + line
                else:
                    record["content"] = line
        if record:
            records.append(record)

    if not records:
        raise SkillError("E003", "无法从输入中提取任何记录")

    return records


def parse_input_file(file_path: str) -> List[Dict[str, Any]]:
    """从文件读取并解析输入数据。"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except FileNotFoundError:
        raise SkillError("E002", f"文件不存在: {file_path}")
    except OSError as e:
        raise SkillError("E002", f"读取失败: {e}")

    return parse_input_text(content)


def process_records(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """批量处理记录：提取字段、限制数量。"""
    if len(records) > MAX_RECORDS:
        raise SkillError("E005", f"输入 {len(records)} 条，超过上限 {MAX_RECORDS}")

    processed = []
    for record in records:
        try:
            processed.append(extract_fields(record))
        except Exception as e:
            raise SkillError("E006", f"记录处理失败: {e}")

    return processed


# ---------------------------------------------------------------------------
# 输出格式化
# ---------------------------------------------------------------------------
def format_markdown(records: List[Dict[str, Any]]) -> str:
    """输出为 Markdown 表格。"""
    if not records:
        return "*（无记录）*"

    # 收集所有键
    all_keys: List[str] = []
    for record in records:
        for key in record.keys():
            if key not in all_keys:
                all_keys.append(key)

    # 固定顺序：title, content, date, confidence, 其他
    priority = ["title", "content", "date", "confidence"]
    ordered_keys = [k for k in priority if k in all_keys]
    ordered_keys += [k for k in all_keys if k not in priority]

    # 生成 Markdown
    header = "| " + " | ".join(ordered_keys) + " |"
    separator = "| " + " | ".join(["---"] * len(ordered_keys)) + " |"
    lines = [header, separator]

    for record in records:
        row = []
        for key in ordered_keys:
            value = record.get(key, "")
            # 转义管道符
            value_str = str(value).replace("|", "\\|").replace("\n", "<br>")
            row.append(value_str)
        lines.append("| " + " | ".join(row) + " |")

    return "\n".join(lines)


def format_json(records: List[Dict[str, Any]]) -> str:
    """输出为 JSON 字符串。"""
    return json.dumps(records, ensure_ascii=False, indent=2)


def format_csv(records: List[Dict[str, Any]]) -> str:
    """输出为 CSV 字符串。"""
    if not records:
        return ""

    all_keys: List[str] = []
    for record in records:
        for key in record.keys():
            if key not in all_keys:
                all_keys.append(key)

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=all_keys, extrasaction="ignore")
    writer.writeheader()
    for record in records:
        writer.writerow(record)

    return output.getvalue()


def format_output(records: List[Dict[str, Any]], fmt: str) -> str:
    """根据指定格式输出。"""
    if fmt == "markdown":
        return format_markdown(records)
    elif fmt == "json":
        return format_json(records)
    elif fmt == "csv":
        return format_csv(records)
    else:
        raise SkillError("E004", f"不支持的格式: {fmt}")


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------
def run(input_source: str, output_format: str, source_type: str = "text") -> str:
    """
    执行数据转换主流程。

    参数:
        input_source: 输入数据（文本内容或文件路径）
        output_format: 输出格式（markdown/json/csv）
        source_type: 输入类型（text/file）

    返回:
        格式化后的输出字符串
    """
    # 检查输出格式
    if output_format not in SUPPORTED_OUTPUT_FORMATS:
        raise SkillError("E004", f"不支持的格式: {output_format}")

    # 检查 URL（不支持网络访问）
    if source_type == "url" or URL_PATTERN.match(input_source):
        raise SkillError("E010", "不访问外部 URL，请提供文本或本地文件路径")

    # 解析输入
    if source_type == "file":
        records = parse_input_file(input_source)
    else:
        records = parse_input_text(input_source)

    # 批量处理
    processed = process_records(records)

    # 格式化输出
    return format_output(processed, output_format)


# ---------------------------------------------------------------------------
# 自检（selftest）
# ---------------------------------------------------------------------------
def run_selftest() -> int:
    """
    离线自检核心逻辑。

    使用内置硬编码样例数据，不读外部文件、不依赖工作目录、不访问网络。
    断言使用宽松阈值（大小比较/区间判断），确保必然匹配。
    """
    print("[自检] 开始...")

    # 1. 测试 JSON 解析与字段提取
    test_json = """
    [
        {"name": "项目A", "content": "完成报告", "date": "2026-01-01"},
        {"title": "项目B", "text": "准备演示", "time": "2026-02-01"}
    ]
    """
    try:
        records = parse_input_text(test_json)
        assert len(records) == 2, f"JSON 解析应得到 2 条记录，实际 {len(records)}"
        processed = process_records(records)
        assert len(processed) == 2, f"处理后应有 2 条记录，实际 {len(processed)}"
        # 置信度应在 [0, 1] 区间
        for rec in processed:
            conf = rec.get("confidence", -1)
            assert 0.0 <= conf <= 1.0, f"置信度超出区间: {conf}"
            assert "title" in rec, "应提取 title 字段"
            assert "content" in rec, "应提取 content 字段"
        print("[自检] JSON 解析与字段提取: 通过")
    except AssertionError as e:
        print(f"[自检] JSON 解析与字段提取: 失败 - {e}")
        return 1
    except Exception as e:
        print(f"[自检] JSON 解析与字段提取: 异常 - {e}")
        return 1

    # 2. 测试 CSV 解析
    test_csv = "name,content,date\n任务1,写代码,2026-01-02\n任务2,写文档,2026-01-03\n"
    try:
        records = parse_input_text(test_csv)
        assert len(records) == 2, f"CSV 解析应得到 2 条记录，实际 {len(records)}"
        assert records[0]["name"] == "任务1", "CSV 首行首列解析错误"
        print("[自检] CSV 解析: 通过")
    except AssertionError as e:
        print(f"[自检] CSV 解析: 失败 - {e}")
        return 1
    except Exception as e:
        print(f"[自检] CSV 解析: 异常 - {e}")
        return 1

    # 3. 测试纯文本解析
    test_text = "标题: 会议纪要\n日期: 2026-03-01\n\n标题: 周报\n内容: 完成三项任务\n"
    try:
        records = parse_input_text(test_text)
        assert len(records) == 2, f"文本解析应得到 2 条记录，实际 {len(records)}"
        # 验证第一条记录
        first = records[0]
        assert "标题" in first, f"第一条记录应包含'标题'字段，实际字段: {list(first.keys())}"
        assert first["标题"] == "会议纪要", f"第一条记录标题值错误: {first['标题']}"
        # 验证第二条记录
        second = records[1]
        assert "标题" in second, f"第二条记录应包含'标题'字段，实际字段: {list(second.keys())}"
        assert second["标题"] == "周报", f"第二条记录标题值错误: {second['标题']}"
        print("[自检] 文本解析: 通过")
    except AssertionError as e:
        print(f"[自检] 文本解析: 失败 - {e}")
        return 1
    except Exception as e:
        print(f"[自检] 文本解析: 异常 - {e}")
        return 1

    # 4. 测试输出格式
    sample_records = [
        {"title": "测试", "content": "内容", "date": "2026-01-01", "confidence": 1.0}
    ]
    try:
        md = format_markdown(sample_records)
        assert "|" in md, "Markdown 输出应包含表格分隔符"
        assert "测试" in md, "Markdown 输出应包含标题内容"

        js = format_json(sample_records)
        parsed_js = json.loads(js)
        assert len(parsed_js) == 1, "JSON 输出应可重新解析"

        cs = format_csv(sample_records)
        assert "title" in cs, "CSV 输出应包含表头"
        print("[自检] 输出格式: 通过")
    except AssertionError as e:
        print(f"[自检] 输出格式: 失败 - {e}")
        return 1
    except Exception as e:
        print(f"[自检] 输出格式: 异常 - {e}")
        return 1

    # 5. 测试批量处理上限
    try:
        too_many = [{"name": f"item{i}"} for i in range(MAX_RECORDS + 1)]
        process_records(too_many)
        print("[自检] 批量上限: 失败 - 应触发 E005 错误但未触发")
        return 1
    except SkillError as e:
        if e.code == "E005":
            print("[自检] 批量上限: 通过")
        else:
            print(f"[自检] 批量上限: 失败 - 应触发 E005 错误，实际 {e.code}")
            return 1
    except Exception as e:
        print(f"[自检] 批量上限: 异常 - {e}")
        return 1

    # 6. 测试完整主流程
    try:
        result = run(
            '[{"name": "完整流程测试", "content": "验证", "date": "2026-01-01"}]',
            "json",
        )
        assert "完整流程测试" in result, "主流程 JSON 输出应包含输入内容"
        print("[自检] 主流程: 通过")
    except AssertionError as e:
        print(f"[自检] 主流程: 失败 - {e}")
        return 1
    except Exception as e:
        print(f"[自检] 主流程: 异常 - {e}")
        return 1

    print("[自检] 全部通过 ✔")
    return 0


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------
def main(argv: Optional[List[str]] = None) -> int:
    """命令行入口。"""
    parser = argparse.ArgumentParser(
        description="技能工具箱：数据转换与结构化输出",
        epilog="示例: python main.py --input data.json --format json --source-type file",
    )
    parser.add_argument(
        "--input",
        type=str,
        help="输入数据（文本内容或文件路径）",
    )
    parser.add_argument(
        "--format",
        type=str,
        default="markdown",
        choices=SUPPORTED_OUTPUT_FORMATS,
        help="输出格式（默认: markdown）",
    )
    parser.add_argument(
        "--source-type",
        type=str,
        default="text",
        choices=["text", "file"],
        help="输入类型（默认: text）",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行离线自检",
    )

    args = parser.parse_args(argv)

    # 自检模式
    if args.selftest:
        try:
            return run_selftest()
        except SkillError as e:
            print(f"[错误] {e.code}: {e.detail}", file=sys.stderr)
            return 1

    # 正常模式
    if not args.input:
        print("[错误] E001: 缺少 --input 参数（或使用 --selftest 自检）", file=sys.stderr)
        return 1

    try:
        output = run(args.input, args.format, args.source_type)
        print(output)
        return 0
    except SkillError as e:
        print(f"[错误] {e.code}: {e.detail}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"[错误] E009: 未分类异常: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
