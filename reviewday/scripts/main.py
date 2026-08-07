#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
reviewday — 代码审查报告生成器（独立实现）

根据功能规格实现的干净房间版本，仅依赖标准库。
支持将审查数据转换为结构化报告，批量处理，置信度标注，分类聚合与多格式导出。
"""

import argparse
import json
import os
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

# 错误码定义
ERROR_CODES = {
    "E001": "输入文件不存在",
    "E002": "输入文件格式不支持（仅支持 .json/.csv/.txt）",
    "E003": "JSON 解析失败",
    "E004": "CSV 解析失败",
    "E005": "无效的严重级别（应为 blocker/critical/major/suggestion）",
    "E006": "输出目录无法创建",
    "E007": "输出格式不支持（仅支持 markdown/json/html）",
    "E008": "输入路径既不是文件也不是目录",
    "E009": "输入目录中无有效审查文件",
    "E010": "内部数据处理错误",
}

# 严重级别映射（用于排序与聚合）
SEVERITY_ORDER = ["blocker", "critical", "major", "suggestion"]
SEVERITY_ORDER_REVERSE = {s: i for i, s in enumerate(SEVERITY_ORDER)}

# 置信度判定阈值
CONFIDENCE_HIGH_MIN_FIELDS = 5  # 字段完整度 >= 5 为高置信
CONFIDENCE_MED_MIN_FIELDS = 3  # 字段完整度 >= 3 为中置信


def _error_exit(code: str, message: str) -> None:
    """输出错误信息并以非零状态退出"""
    print(f"[ERROR] {code}: {message}", file=sys.stderr)
    sys.exit(1)


def _now_timestamp() -> str:
    """获取当前时间字符串（用于报告头部）"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _read_file_content(file_path: Path) -> str:
    """读取文件内容，处理编码异常"""
    try:
        return file_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        try:
            return file_path.read_text(encoding="gbk")
        except Exception:
            _error_exit("E001", f"无法读取文件（编码不识别）: {file_path}")
    except Exception:
        _error_exit("E001", f"文件读取失败: {file_path}")
    return ""


def parse_json_content(content: str) -> list:
    """解析 JSON 内容为审查记录列表"""
    try:
        data = json.loads(content)
        if isinstance(data, dict):
            # 支持 { "reviews": [...] } 或 { "items": [...] } 包装格式
            if "reviews" in data:
                data = data["reviews"]
            elif "items" in data:
                data = data["items"]
            else:
                data = [data]
        if not isinstance(data, list):
            _error_exit("E003", "JSON 根节点应为数组或包含 reviews/items 数组的对象")
        return data
    except json.JSONDecodeError as e:
        _error_exit("E003", f"JSON 解析失败: {e}")
    return []


def parse_csv_content(content: str) -> list:
    """解析简单 CSV 内容（支持表头）"""
    import csv
    import io

    try:
        reader = csv.DictReader(io.StringIO(content))
        records = []
        for row in reader:
            # 去除空字段
            record = {k.strip(): v.strip() for k, v in row.items() if k and v.strip()}
            if record:
                records.append(record)
        return records
    except Exception as e:
        _error_exit("E004", f"CSV 解析失败: {e}")
    return []


def parse_txt_content(content: str) -> list:
    """解析纯文本格式（每行一条记录，格式: 严重级别|标题|位置|描述|建议）"""
    records = []
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = [p.strip() for p in line.split("|")]
        if len(parts) < 2:
            continue
        record = {
            "severity": parts[0].lower(),
            "title": parts[1],
        }
        if len(parts) > 2:
            record["location"] = parts[2]
        if len(parts) > 3:
            record["description"] = parts[3]
        if len(parts) > 4:
            record["suggestion"] = parts[4]
        records.append(record)
    return records


def _normalize_record(record: dict) -> dict:
    """规范化单条审查记录，填充默认字段"""
    normalized = {}
    # 严重级别（必须）
    severity = str(record.get("severity", record.get("level", "suggestion"))).lower()
    if severity not in SEVERITY_ORDER:
        severity = "suggestion"
    normalized["severity"] = severity

    # 标题（必须）
    normalized["title"] = str(record.get("title", record.get("message", "未命名问题")))

    # 可选字段
    normalized["location"] = str(record.get("location", record.get("file", record.get("line", ""))))
    normalized["description"] = str(record.get("description", record.get("detail", "")))
    normalized["suggestion"] = str(record.get("suggestion", record.get("fix", "")))
    normalized["category"] = str(record.get("category", record.get("type", "general")))

    # 置信度计算（基于字段完整度）
    field_count = sum(
        1 for field in ["severity", "title", "location", "description", "suggestion", "category"]
        if normalized.get(field)
    )
    if field_count >= CONFIDENCE_HIGH_MIN_FIELDS:
        confidence = "high"
    elif field_count >= CONFIDENCE_MED_MIN_FIELDS:
        confidence = "medium"
    else:
        confidence = "low"
    normalized["confidence"] = confidence

    # 附加元数据
    normalized["source"] = str(record.get("source", "unknown"))
    normalized["reviewer"] = str(record.get("reviewer", "unknown"))
    normalized["timestamp"] = str(record.get("timestamp", _now_timestamp()))

    return normalized


def normalize_records(raw_records: list) -> list:
    """规范化所有记录，过滤无效记录"""
    result = []
    for raw in raw_records:
        if not isinstance(raw, dict):
            continue
        try:
            normalized = _normalize_record(raw)
            if normalized["title"]:
                result.append(normalized)
        except Exception:
            continue  # 跳过无法处理的记录
    return result


def classify_by_severity(records: list) -> dict:
    """按严重级别分类聚合"""
    classified = defaultdict(list)
    for record in records:
        classified[record["severity"]].append(record)
    return dict(classified)


def generate_markdown_report(records: list, meta: dict) -> str:
    """生成 Markdown 格式报告"""
    lines = []
    lines.append(f"# 代码审查报告")
    lines.append(f"")
    lines.append(f"- **项目**: {meta.get('project', '未知')}")
    lines.append(f"- **生成时间**: {meta.get('generated_at', '')}")
    lines.append(f"- **审查记录数**: {len(records)}")
    lines.append(f"")
    lines.append(f"## 汇总统计")
    lines.append(f"")
    lines.append(f"| 严重级别 | 数量 |")
    lines.append(f"|----------|------|")
    for sev in SEVERITY_ORDER:
        count = sum(1 for r in records if r["severity"] == sev)
        lines.append(f"| {sev} | {count} |")
    lines.append(f"")

    # 按严重级别分组输出
    classified = classify_by_severity(records)
    for sev in SEVERITY_ORDER:
        sev_records = classified.get(sev, [])
        if not sev_records:
            continue
        lines.append(f"## {sev.upper()} 级别问题（{len(sev_records)} 条）")
        lines.append(f"")
        lines.append(f"| # | 标题 | 位置 | 置信度 | 建议 |")
        lines.append(f"|---|------|------|--------|------|")
        for idx, rec in enumerate(sev_records, 1):
            confidence_mark = {"high": "高", "medium": "中", "low": "低"}.get(rec["confidence"], "未知")
            suggestion = rec["suggestion"][:50] + "..." if len(rec["suggestion"]) > 50 else rec["suggestion"]
            lines.append(f"| {idx} | {rec['title']} | {rec['location']} | {confidence_mark} | {suggestion} |")
        lines.append(f"")

    lines.append(f"---")
    lines.append(f"*报告由 reviewday 自动生成*")
    return "\n".join(lines)


def generate_json_report(records: list, meta: dict) -> str:
    """生成 JSON 格式报告"""
    report = {
        "meta": meta,
        "summary": {
            "total": len(records),
            "by_severity": {sev: sum(1 for r in records if r["severity"] == sev) for sev in SEVERITY_ORDER},
        },
        "records": records,
    }
    return json.dumps(report, ensure_ascii=False, indent=2)


def generate_html_report(records: list, meta: dict) -> str:
    """生成 HTML 格式报告"""
    markdown = generate_markdown_report(records, meta)
    # 简单转义
    html_content = markdown.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>代码审查报告 - {meta.get('project', '未知')}</title>
    <style>
        body {{ font-family: sans-serif; margin: 40px; }}
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
    </style>
</head>
<body>
    <h1>代码审查报告</h1>
    <p>生成时间: {meta.get('generated_at', '')}</p>
    <p>记录总数: {len(records)}</p>
    <hr>
    <pre>{html_content}</pre>
</body>
</html>"""
    return html


def process_file(file_path: Path) -> list:
    """处理单个审查数据文件"""
    if not file_path.exists():
        _error_exit("E001", f"文件不存在: {file_path}")

    ext = file_path.suffix.lower()
    content = _read_file_content(file_path)

    if ext == ".json":
        raw_records = parse_json_content(content)
    elif ext == ".csv":
        raw_records = parse_csv_content(content)
    elif ext == ".txt":
        raw_records = parse_txt_content(content)
    else:
        _error_exit("E002", f"不支持的文件格式: {ext} (file: {file_path})")

    records = normalize_records(raw_records)
    # 标记来源
    for rec in records:
        rec["source"] = str(file_path)
    return records


def process_input(input_path: Path) -> list:
    """处理输入路径（文件或目录），返回所有记录"""
    if input_path.is_file():
        return process_file(input_path)
    elif input_path.is_dir():
        all_records = []
        # 支持常见扩展名
        supported_exts = {".json", ".csv", ".txt"}
        for ext in supported_exts:
            for file_path in sorted(input_path.glob(f"*{ext}")):
                if file_path.is_file():
                    all_records.extend(process_file(file_path))
        if not all_records:
            _error_exit("E009", f"目录中无有效审查文件: {input_path}")
        return all_records
    else:
        _error_exit("E008", f"输入路径既不是文件也不是目录: {input_path}")
    return []


def export_report(records: list, output_path: Path, format_type: str, meta: dict) -> None:
    """导出报告到指定格式"""
    if format_type == "markdown":
        content = generate_markdown_report(records, meta)
    elif format_type == "json":
        content = generate_json_report(records, meta)
    elif format_type == "html":
        content = generate_html_report(records, meta)
    else:
        _error_exit("E007", f"不支持的输出格式: {format_type}")

    # 确保输出目录存在
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
    except Exception:
        _error_exit("E006", f"无法创建输出目录: {output_path.parent}")

    try:
        output_path.write_text(content, encoding="utf-8")
    except Exception as e:
        _error_exit("E010", f"写入输出文件失败: {e}")


def run_selftest() -> int:
    """内置自检，使用硬编码样例数据验证核心逻辑"""
    print("[SELFTEST] 开始自检...")

    # 硬编码测试数据
    test_records_raw = [
        {
            "severity": "blocker",
            "title": "空指针异常风险",
            "location": "src/main.py:42",
            "description": "变量未初始化即使用",
            "suggestion": "初始化变量或添加判空",
            "category": "bug",
        },
        {
            "severity": "critical",
            "title": "内存泄漏",
            "location": "src/utils.py:88",
            "description": "循环中创建对象未释放",
            "suggestion": "使用上下文管理器",
            "category": "performance",
        },
        {
            "severity": "major",
            "title": "代码重复",
            "location": "src/helpers.py:15",
            "description": "相同逻辑出现多处",
            "suggestion": "抽取公共函数",
            "category": "refactor",
        },
        {
            "severity": "suggestion",
            "title": "命名不规范",
            "location": "src/constants.py:3",
            "description": "变量名使用拼音",
            "suggestion": "改用英文命名",
            "category": "style",
        },
        # 缺少部分字段的记录（用于测试置信度）
        {
            "severity": "major",
            "title": "缺少异常处理",
            "location": "src/api.py:20",
        },
    ]

    # 测试规范化
    normalized = normalize_records(test_records_raw)
    assert len(normalized) == 5, f"规范化记录数应为5，实际{len(normalized)}"
    assert all(r["severity"] in SEVERITY_ORDER for r in normalized), "严重级别不合法"
    assert all(r["confidence"] in ["high", "medium", "low"] for r in normalized), "置信度不合法"

    # 测试置信度：完整记录应为 high，残缺记录应为 medium 或 low
    complete_records = [r for r in normalized if len(r["title"]) > 5 and r["location"] and r["description"]]
    incomplete_records = [r for r in normalized if not r.get("description")]
    assert all(r["confidence"] == "high" for r in complete_records), "完整记录置信度应为 high"
    assert all(r["confidence"] in ["medium", "low"] for r in incomplete_records), "残缺记录置信度不应为 high"

    # 测试分类聚合
    classified = classify_by_severity(normalized)
    assert len(classified) >= 3, f"应有至少3个严重级别分类，实际{len(classified)}"
    assert "blocker" in classified, "缺少 blocker 分类"
    assert len(classified["blocker"]) == 1, "blocker 应只有1条"

    # 测试 Markdown 报告生成
    meta = {"project": "selftest", "generated_at": "2026-01-01 00:00:00"}
    md_report = generate_markdown_report(normalized, meta)
    assert "代码审查报告" in md_report, "Markdown 报告缺少标题"
    assert "blocker" in md_report, "Markdown 报告缺少 blocker 级别"

    # 测试 JSON 报告生成
    json_report = generate_json_report(normalized, meta)
    json_data = json.loads(json_report)
    assert json_data["summary"]["total"] == 5, "JSON 报告总数错误"
    assert json_data["summary"]["by_severity"]["blocker"] == 1, "JSON 报告 blocker 数错误"

    # 测试 HTML 报告生成
    html_report = generate_html_report(normalized, meta)
    assert "<html" in html_report, "HTML 报告缺少 html 标签"
    assert "代码审查报告" in html_report, "HTML 报告缺少标题"

    # 测试 TXT 解析
    txt_content = "critical|数据库连接失败|db.py:10|连接超时|增加重试机制\nmajor|日志过多|log.py:5|无|限制日志级别"
    txt_records = parse_txt_content(txt_content)
    assert len(txt_records) == 2, f"TXT 解析应得2条记录，实际{len(txt_records)}"
    assert txt_records[0]["severity"] == "critical", "TXT 第一条严重级别错误"

    # 测试 CSV 解析
    csv_content = "severity,title,location,description,suggestion\nmajor,CSV测试,test.py:1,描述,建议"
    csv_records = parse_csv_content(csv_content)
    assert len(csv_records) == 1, f"CSV 解析应得1条记录，实际{len(csv_records)}"
    assert csv_records[0]["title"] == "CSV测试", "CSV 标题解析错误"

    # 测试 JSON 解析
    json_content = json.dumps({"reviews": test_records_raw})
    json_records = parse_json_content(json_content)
    assert len(json_records) == 5, f"JSON 解析应得5条记录，实际{len(json_records)}"

    print("[SELFTEST] 全部断言通过 ✅")
    return 0


def main() -> int:
    """主入口"""
    parser = argparse.ArgumentParser(
        description="reviewday - 代码审查报告生成器",
        epilog="示例: python main.py -i reviews/ -o report.md -f markdown",
    )
    parser.add_argument("-i", "--input", type=str, help="输入文件或目录路径")
    parser.add_argument("-o", "--output", type=str, default="review_report.md", help="输出文件路径")
    parser.add_argument(
        "-f", "--format",
        choices=["markdown", "json", "html"],
        default="markdown",
        help="输出格式（默认: markdown）",
    )
    parser.add_argument("-p", "--project", type=str, default="未知项目", help="项目名称")
    parser.add_argument("--selftest", action="store_true", help="运行内置自检")

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        return run_selftest()

    # 正常处理模式
    if not args.input:
        _error_exit("E010", "必须指定输入路径（使用 -i 参数）或使用 --selftest 自检")

    # 处理输入
    input_path = Path(args.input)
    records = process_input(input_path)

    if not records:
        _error_exit("E010", "未获取到任何有效审查记录")

    # 生成报告元数据
    meta = {
        "project": args.project,
        "generated_at": _now_timestamp(),
        "total_records": len(records),
        "source": str(input_path),
    }

    # 导出报告
    output_path = Path(args.output)
    export_report(records, output_path, args.format, meta)

    print(f"✅ 报告已生成: {output_path}")
    print(f"   共处理 {len(records)} 条审查记录")

    # 输出简单统计
    counter = Counter(r["severity"] for r in records)
    for sev in SEVERITY_ORDER:
        if counter.get(sev):
            print(f"   {sev}: {counter[sev]} 条")

    return 0


if __name__ == "__main__":
    sys.exit(main())
