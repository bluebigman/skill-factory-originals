#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
agent-toolkit 技能编排与数据转换工具
基于功能规格独立实现（clean-room），仅依赖标准库。
"""

import argparse
import csv
import io
import json
import re
import sys
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

# 错误码定义（对应规格 E1001-E1005，内部使用 E001-E010 便于区分）
ERROR_CODES = {
    "E001": "输入为空或不可解析",
    "E002": "超出大小限制（10MB 或 1000 条记录）",
    "E003": "字段映射冲突",
    "E004": "输出格式不支持",
    "E005": "批量处理中断",
    "E006": "文件读取失败",
    "E007": "URL 解析失败",
    "E008": "JSON 解析失败",
    "E009": "参数错误",
    "E010": "内部逻辑错误",
}

# 内置默认字段集
DEFAULT_FIELDS = ["title", "date", "category", "summary", "url"]

# 大小限制
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
MAX_RECORDS = 1000


class ToolkitError(Exception):
    """技能工具自定义异常，携带错误码"""

    def __init__(self, code: str, message: str = ""):
        self.code = code
        self.message = message or ERROR_CODES.get(code, "未知错误")
        super().__init__(f"[{code}] {self.message}")


def _now_iso() -> str:
    """返回当前 UTC 时间的 ISO 格式"""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _extract_date(text: str) -> str:
    """从文本中提取日期（YYYY-MM-DD 或 YYYY年M月D日），失败返回占位符"""
    # 尝试 ISO 格式
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", text)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"

    # 尝试中文格式
    m = re.search(r"(\d{4})年(\d{1,2})月(\d{1,2})日", text)
    if m:
        y, mo, d = m.group(1), m.group(2), m.group(3)
        return f"{y}-{int(mo):02d}-{int(d):02d}"

    return "[需核实:date]"


def _extract_title(text: str) -> str:
    """提取标题：优先取第一个句号前的内容（去除日期前缀），失败返回占位符"""
    # 去掉日期前缀
    cleaned = re.sub(r"^\d{4}年\d{1,2}月\d{1,2}日[，,]?\s*", "", text)
    # 取第一句
    m = re.search(r"^(.{2,50}?)[。！？!?]", cleaned)
    if m:
        return m.group(1).strip()
    if len(cleaned) > 2:
        return cleaned[:30]
    return "[需核实:title]"


def _extract_category(text: str) -> str:
    """提取分类：匹配常见分类词，失败返回占位符"""
    keywords = ["评审", "会议", "报告", "设计", "开发", "测试", "部署", "优化", "方案"]
    for kw in keywords:
        if kw in text:
            return kw
    return "[需核实:category]"


def _extract_summary(text: str, max_len: int = 200) -> str:
    """生成摘要：取全文前 max_len 字"""
    summary = text.strip().replace("\n", " ")
    if len(summary) > max_len:
        summary = summary[:max_len] + "..."
    return summary if summary else "[需核实:summary]"


def _extract_url(text: str) -> str:
    """提取 URL，失败返回占位符"""
    m = re.search(r"https?://[^\s]+", text)
    if m:
        return m.group(0)
    return "[需核实:url]"


def _parse_single_record(text: str, fields: list, record_id: int) -> dict:
    """解析单条记录为结构化字段"""
    text = text.strip()
    if not text:
        raise ToolkitError("E001")

    field_values = {}
    for field in fields:
        if field == "title":
            field_values[field] = _extract_title(text)
        elif field == "date":
            field_values[field] = _extract_date(text)
        elif field == "category":
            field_values[field] = _extract_category(text)
        elif field == "summary":
            field_values[field] = _extract_summary(text)
        elif field == "url":
            field_values[field] = _extract_url(text)
        else:
            # 自定义字段：尝试匹配 "字段名:值" 模式
            m = re.search(rf"{field}[：:]\s*([^\s，,。；;]+)", text)
            field_values[field] = m.group(1) if m else f"[需核实:{field}]"

    # 置信度评估
    filled = sum(1 for v in field_values.values() if not v.startswith("[需核实"))
    total = len(fields)
    if filled == total:
        confidence = "high"
    elif filled >= total * 0.5:
        confidence = "medium"
    else:
        confidence = "low"

    return {
        "id": record_id,
        "fields": field_values,
        "confidence": confidence,
        "source": "用户提供文本",
    }


def _split_input(text: str) -> list:
    """将输入文本按行或空行拆分为多条记录"""
    # 先尝试按空行拆分
    blocks = re.split(r"\n\s*\n", text)
    if len(blocks) > 1:
        return [b.strip() for b in blocks if b.strip()]

    # 否则按行拆分
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    return lines if lines else [text.strip()]


def process_text(text: str, fields: list = None, fmt: str = "json") -> str:
    """核心处理函数：文本 -> 结构化输出"""
    fields = fields or DEFAULT_FIELDS
    fmt = fmt.lower()

    # 输入校验
    if not text or not text.strip():
        raise ToolkitError("E001")
    if len(text.encode("utf-8")) > MAX_FILE_SIZE:
        raise ToolkitError("E002")

    # 拆分记录
    records_raw = _split_input(text)
    if len(records_raw) > MAX_RECORDS:
        raise ToolkitError("E002")

    # 逐条解析
    records = []
    errors = []
    for idx, raw in enumerate(records_raw, 1):
        try:
            rec = _parse_single_record(raw, fields, idx)
            records.append(rec)
        except ToolkitError as e:
            errors.append({"record": idx, "error": e.code})

    # 格式输出
    output_data = {
        "records": records,
        "meta": {
            "total": len(records),
            "processed_at": _now_iso(),
            "errors": errors if errors else None,
        },
    }

    if fmt == "json":
        return json.dumps(output_data, ensure_ascii=False, indent=2)

    elif fmt == "markdown":
        return _to_markdown(output_data)

    elif fmt == "csv":
        return _to_csv(output_data)

    else:
        raise ToolkitError("E004")


def _to_markdown(data: dict) -> str:
    """转换为 Markdown 表格"""
    if not data["records"]:
        return "| 无记录 |\n|--------|"

    fields = list(data["records"][0]["fields"].keys())
    lines = ["| ID | " + " | ".join(fields) + " | 置信度 |", "|----|" + "|".join(["----"] * len(fields)) + "|--------|"]

    for rec in data["records"]:
        row = [str(rec["id"])]
        for f in fields:
            row.append(rec["fields"].get(f, ""))
        row.append(rec["confidence"])
        lines.append("| " + " | ".join(row) + " |")

    return "\n".join(lines)


def _to_csv(data: dict) -> str:
    """转换为 CSV 格式"""
    if not data["records"]:
        return "id,confidence\n"

    fields = list(data["records"][0]["fields"].keys())
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id"] + fields + ["confidence"])

    for rec in data["records"]:
        row = [rec["id"]]
        for f in fields:
            row.append(rec["fields"].get(f, ""))
        row.append(rec["confidence"])
        writer.writerow(row)

    return output.getvalue()


def process_file(file_path: str, fields: list = None, fmt: str = "json") -> str:
    """处理本地文件"""
    try:
        path = Path(file_path)
        if not path.exists():
            raise ToolkitError("E001", f"文件不存在: {file_path}")
        if path.stat().st_size > MAX_FILE_SIZE:
            raise ToolkitError("E002")

        content = path.read_text(encoding="utf-8", errors="replace")
        return process_text(content, fields, fmt)
    except ToolkitError:
        raise
    except Exception as e:
        raise ToolkitError("E006", f"读取文件失败: {str(e)}")


def process_url(url: str, fields: list = None, fmt: str = "json") -> str:
    """处理 URL（仅做协议校验，不实际访问）"""
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise ToolkitError("E007", f"无效的 URL: {url}")

    # 规格要求不访问网络，这里返回占位提示
    placeholder = f"[需核实:url内容] 无法离线访问 {url}"
    return process_text(placeholder, fields, fmt)


def _selftest() -> int:
    """内置自检函数：使用硬编码样例数据验证核心逻辑"""
    print("=== agent-toolkit 自检开始 ===")

    # 测试样例 1：单条文本
    sample1 = "2024年3月15日，张三在项目评审会上提出性能优化方案，涉及模块A和模块B。"
    try:
        result1 = json.loads(process_text(sample1))
        assert len(result1["records"]) == 1, "样例1应产生1条记录"
        rec = result1["records"][0]
        assert rec["fields"]["date"] == "2024-03-15", "日期提取失败"
        assert rec["confidence"] in ("high", "medium", "low"), "置信度等级非法"
        assert rec["id"] == 1, "ID 应为1"
        print("  [通过] 单条文本处理")
    except Exception as e:
        print(f"  [失败] 单条文本处理: {e}")
        return 1

    # 测试样例 2：批量处理
    sample2 = "第一条记录内容，无日期。\n\n2023年5月20日，第二条记录。"
    try:
        result2 = json.loads(process_text(sample2))
        assert 1 <= len(result2["records"]) <= 2, "批量记录数异常"
        assert result2["meta"]["total"] == len(result2["records"]), "总数不一致"
        print("  [通过] 批量处理")
    except Exception as e:
        print(f"  [失败] 批量处理: {e}")
        return 1

    # 测试样例 3：Markdown 输出
    try:
        md = process_text(sample1, fmt="markdown")
        assert "|" in md and "置信度" in md, "Markdown 格式异常"
        print("  [通过] Markdown 输出")
    except Exception as e:
        print(f"  [失败] Markdown 输出: {e}")
        return 1

    # 测试样例 4：CSV 输出
    try:
        csv_out = process_text(sample1, fmt="csv")
        assert "id" in csv_out and "confidence" in csv_out, "CSV 格式异常"
        print("  [通过] CSV 输出")
    except Exception as e:
        print(f"  [失败] CSV 输出: {e}")
        return 1

    # 测试样例 5：空输入错误处理
    try:
        process_text("")
        print("  [失败] 空输入应抛出错误")
        return 1
    except ToolkitError as e:
        assert e.code == "E001", f"错误码应为 E001，实际 {e.code}"
        print("  [通过] 空输入错误处理")

    # 测试样例 6：自定义字段
    try:
        custom_fields = ["title", "date", "category", "summary", "url", "author"]
        result6 = json.loads(process_text(sample1, fields=custom_fields))
        assert "author" in result6["records"][0]["fields"], "自定义字段缺失"
        assert result6["records"][0]["fields"]["author"].startswith("[需核实"), "自定义字段应为占位符"
        print("  [通过] 自定义字段")
    except Exception as e:
        print(f"  [失败] 自定义字段: {e}")
        return 1

    # 测试样例 7：非法格式
    try:
        process_text(sample1, fmt="xml")
        print("  [失败] 非法格式应抛出错误")
        return 1
    except ToolkitError as e:
        assert e.code == "E004", f"错误码应为 E004，实际 {e.code}"
        print("  [通过] 非法格式错误处理")

    print("=== 自检全部通过 ===")
    return 0


def main() -> int:
    """命令行入口"""
    parser = argparse.ArgumentParser(
        description="agent-toolkit 技能编排与数据转换工具",
        epilog="示例: python main.py -i input.txt -f json",
    )
    parser.add_argument("--selftest", action="store_true", help="运行内置自检")
    parser.add_argument("-i", "--input", help="输入文本、文件路径或URL")
    parser.add_argument("-f", "--format", default="json", choices=["json", "markdown", "csv"], help="输出格式")
    parser.add_argument("--fields", help="自定义字段列表，逗号分隔")
    parser.add_argument("--file", help="处理本地文件")
    parser.add_argument("--url", help="处理URL")

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        return _selftest()

    # 参数校验
    if not args.input and not args.file and not args.url:
        print("错误: 必须提供输入内容（-i/--input, --file 或 --url）", file=sys.stderr)
        print("使用 --selftest 运行自检", file=sys.stderr)
        return 1

    try:
        fields = args.fields.split(",") if args.fields else DEFAULT_FIELDS

        if args.file:
            output = process_file(args.file, fields, args.format)
        elif args.url:
            output = process_url(args.url, fields, args.format)
        else:
            output = process_text(args.input, fields, args.format)

        print(output)
        return 0

    except ToolkitError as e:
        print(f"错误 {e.code}: {e.message}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"错误 E010: 内部错误 - {str(e)}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
