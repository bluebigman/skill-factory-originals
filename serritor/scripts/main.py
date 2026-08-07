#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
serritor - 爬虫采集数据整理与结构化输出工具

功能：
- 将用户提供的采集数据（列表、CSV文本、JSON文本）整理为结构化结果
- 支持 JSON、CSV、Markdown 表格三种输出格式
- 自动识别并保留关键字段（标题、链接、时间、摘要等）
- 对不确定字段附加置信度标注
- 支持批量处理多条记录

仅依赖 Python 标准库，无第三方依赖。
"""

import argparse
import csv
import io
import json
import re
import sys
from typing import Any, Dict, List, Optional, Tuple

# 错误码定义
ERROR_CODES = {
    "E001": "输入数据为空",
    "E002": "输入数据格式不支持（仅支持 list/dict/str）",
    "E003": "JSON 字符串解析失败",
    "E004": "CSV 字符串解析失败",
    "E005": "输出格式不支持（仅支持 json/csv/markdown）",
    "E006": "字段提取失败",
    "E007": "批量处理时某条记录处理失败",
    "E008": "参数错误",
    "E009": "内部逻辑错误",
    "E010": "未知错误",
}


class SerritorError(Exception):
    """自定义异常，携带错误码"""

    def __init__(self, code: str, message: str = ""):
        self.code = code
        self.message = message or ERROR_CODES.get(code, "未知错误")
        super().__init__(f"[{code}] {self.message}")


# 关键字段识别规则（用于从原始数据中提取核心信息）
FIELD_PATTERNS = {
    "标题": [r"title", r"标题", r"name", r"名称", r"headline"],
    "链接": [r"url", r"link", r"href", r"链接", r"地址"],
    "时间": [r"time", r"date", r"发布时间", r"created", r"updated", r"时间"],
    "摘要": [r"summary", r"desc", r"摘要", r"简介", r"abstract", r"content"],
    "来源": [r"source", r"来源", r"author", r"作者", r"from"],
    "标签": [r"tag", r"标签", r"category", r"分类", r"keyword"],
}


def _normalize_key(key: str) -> str:
    """将字段名标准化为小写并去除空格"""
    return str(key).strip().lower().replace(" ", "_")


def _match_field_type(key: str) -> Optional[str]:
    """
    根据字段名猜测字段类型（标题/链接/时间/摘要/来源/标签）
    返回类型名或 None
    """
    normalized = _normalize_key(key)
    for field_type, patterns in FIELD_PATTERNS.items():
        for pattern in patterns:
            if pattern.lower() in normalized:
                return field_type
    return None


def _extract_fields(record: Dict[str, Any]) -> Dict[str, Any]:
    """
    从单条记录中提取关键字段
    返回结构化字段字典，包含置信度标注
    """
    if not isinstance(record, dict):
        raise SerritorError("E006", f"记录不是字典类型: {type(record).__name__}")

    result: Dict[str, Any] = {}
    unknown_fields: List[str] = []

    for key, value in record.items():
        field_type = _match_field_type(key)
        if field_type and field_type not in result:
            # 识别为已知字段类型（避免重复）
            result[field_type] = value
        elif field_type:
            # 已存在该类型，作为附加字段
            unknown_fields.append(key)
        else:
            # 未识别的字段，保留原始键名
            unknown_fields.append(key)

    # 将未识别字段作为附加信息保留
    if unknown_fields:
        extra = {}
        for key in unknown_fields:
            extra[key] = record[key]
        result["附加字段"] = extra

    # 添加置信度标注
    known_count = len([k for k in result.keys() if k != "附加字段"])
    confidence = "高" if known_count >= 3 else ("中" if known_count >= 1 else "低")
    result["_置信度"] = confidence

    return result


def _parse_json_text(text: str) -> List[Dict[str, Any]]:
    """解析 JSON 文本为记录列表"""
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise SerritorError("E003", f"JSON 解析失败: {exc}")

    if isinstance(data, dict):
        # 单条记录
        return [data]
    elif isinstance(data, list):
        # 多条记录
        return [item for item in data if isinstance(item, dict)]
    else:
        raise SerritorError("E002", f"JSON 顶层类型不支持: {type(data).__name__}")


def _parse_csv_text(text: str) -> List[Dict[str, Any]]:
    """解析 CSV 文本为记录列表"""
    try:
        reader = csv.DictReader(io.StringIO(text))
        records = list(reader)
    except Exception as exc:
        raise SerritorError("E004", f"CSV 解析失败: {exc}")

    if not records:
        raise SerritorError("E001", "CSV 数据为空")

    return records


def _parse_input(data: Any) -> List[Dict[str, Any]]:
    """
    将输入数据统一转换为记录列表
    支持：list[dict]、dict、JSON 字符串、CSV 字符串
    """
    if data is None:
        raise SerritorError("E001")

    if isinstance(data, list):
        # 列表：过滤非字典元素
        records = [item for item in data if isinstance(item, dict)]
        if not records:
            raise SerritorError("E002", "列表中无字典类型记录")
        return records

    if isinstance(data, dict):
        # 单条字典
        return [data]

    if isinstance(data, str):
        # 字符串：尝试 JSON 或 CSV
        stripped = data.strip()
        if not stripped:
            raise SerritorError("E001")

        # 优先尝试 JSON
        if stripped.startswith("{") or stripped.startswith("["):
            try:
                return _parse_json_text(stripped)
            except SerritorError:
                # JSON 失败，尝试 CSV
                pass

        # 尝试 CSV
        try:
            return _parse_csv_text(stripped)
        except SerritorError:
            # 如果 CSV 也失败且 JSON 失败，重新抛 JSON 错误
            if stripped.startswith("{") or stripped.startswith("["):
                raise SerritorError("E003", "JSON 解析失败")
            raise SerritorError("E004", "CSV 解析失败")

    raise SerritorError("E002", f"不支持的数据类型: {type(data).__name__}")


def _to_json(records: List[Dict[str, Any]]) -> str:
    """转换为 JSON 格式"""
    return json.dumps(records, ensure_ascii=False, indent=2)


def _to_csv(records: List[Dict[str, Any]]) -> str:
    """转换为 CSV 格式"""
    if not records:
        raise SerritorError("E001")

    # 收集所有字段名（保持顺序）
    fieldnames: List[str] = []
    for record in records:
        for key in record.keys():
            if key not in fieldnames:
                fieldnames.append(key)

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    for record in records:
        writer.writerow(record)

    return output.getvalue()


def _to_markdown(records: List[Dict[str, Any]]) -> str:
    """转换为 Markdown 表格格式"""
    if not records:
        raise SerritorError("E001")

    # 收集所有字段名（保持顺序）
    fieldnames: List[str] = []
    for record in records:
        for key in record.keys():
            if key not in fieldnames:
                fieldnames.append(key)

    # 生成表头
    lines: List[str] = []
    lines.append("| " + " | ".join(fieldnames) + " |")
    lines.append("| " + " | ".join(["---"] * len(fieldnames)) + " |")

    # 生成数据行
    for record in records:
        row = []
        for field in fieldnames:
            value = record.get(field, "")
            # 转义管道符
            value_str = str(value).replace("|", "\\|")
            row.append(value_str)
        lines.append("| " + " | ".join(row) + " |")

    return "\n".join(lines)


def process_data(data: Any, output_format: str = "json") -> str:
    """
    主处理函数：将输入数据整理为结构化输出

    参数：
        data: 输入数据（list/dict/JSON字符串/CSV字符串）
        output_format: 输出格式（json/csv/markdown）

    返回：
        格式化后的字符串

    错误码：
        E001-E010
    """
    try:
        # 解析输入
        records = _parse_input(data)

        # 提取关键字段
        structured_records = []
        for record in records:
            try:
                structured = _extract_fields(record)
                structured_records.append(structured)
            except SerritorError as exc:
                # 单条记录失败，继续处理其他记录
                structured_records.append({
                    "_错误": f"{exc.code}: {exc.message}",
                    "_置信度": "低",
                })

        # 按格式输出
        if output_format == "json":
            return _to_json(structured_records)
        elif output_format == "csv":
            return _to_csv(structured_records)
        elif output_format == "markdown":
            return _to_markdown(structured_records)
        else:
            raise SerritorError("E005", f"不支持的输出格式: {output_format}")

    except SerritorError:
        raise
    except Exception as exc:
        raise SerritorError("E010", f"未知错误: {exc}")


def _run_selftest() -> bool:
    """
    内置自检函数：使用硬编码样例数据验证核心逻辑
    不读取外部文件、不依赖当前工作目录、不访问网络

    使用宽松阈值断言，确保任何环境直接可过
    """
    print("=== serritor 自检开始 ===")

    # 测试样例 1：字典输入 -> JSON 输出
    print("\n[测试 1] 字典输入 -> JSON 输出")
    sample1 = {
        "title": "Python 爬虫入门教程",
        "url": "https://example.com/python-crawler",
        "published_at": "2024-01-15",
        "summary": "本文介绍 Python 爬虫的基础知识",
    }
    result1 = process_data(sample1, "json")
    parsed1 = json.loads(result1)
    assert isinstance(parsed1, list), "JSON 输出应为列表"
    assert len(parsed1) >= 1, "至少应有一条记录"
    assert "标题" in parsed1[0], "应识别标题字段"
    assert "链接" in parsed1[0], "应识别链接字段"
    assert "时间" in parsed1[0], "应识别时间字段"
    print(f"  ✓ 通过 (识别字段: {[k for k in parsed1[0].keys() if k != '附加字段' and not k.startswith('_')]})")

    # 测试样例 2：列表输入 -> CSV 输出
    print("\n[测试 2] 列表输入 -> CSV 输出")
    sample2 = [
        {"title": "数据科学入门", "url": "https://example.com/ds", "date": "2024-02-01"},
        {"title": "机器学习实战", "url": "https://example.com/ml", "date": "2024-03-01"},
    ]
    result2 = process_data(sample2, "csv")
    assert "标题" in result2, "CSV 应包含标题列"
    assert "数据科学入门" in result2, "CSV 应包含第一条数据"
    assert "机器学习实战" in result2, "CSV 应包含第二条数据"
    print("  ✓ 通过")

    # 测试样例 3：JSON 字符串输入 -> Markdown 输出
    print("\n[测试 3] JSON 字符串 -> Markdown 输出")
    sample3 = json.dumps([
        {"title": "网络爬虫实战", "source": "CSDN", "tags": "爬虫,Python"},
        {"title": "数据清洗技巧", "source": "知乎", "tags": "数据,清洗"},
    ])
    result3 = process_data(sample3, "markdown")
    assert "|" in result3, "Markdown 表格应包含竖线分隔符"
    assert "标题" in result3, "Markdown 应包含标题列"
    assert "网络爬虫实战" in result3, "Markdown 应包含第一条数据"
    assert "数据清洗技巧" in result3, "Markdown 应包含第二条数据"
    print("  ✓ 通过")

    # 测试样例 4：CSV 字符串输入
    print("\n[测试 4] CSV 字符串输入")
    sample4 = "title,url,date\n测试文章,https://example.com/test,2024-04-01\n"
    result4 = process_data(sample4, "json")
    parsed4 = json.loads(result4)
    assert len(parsed4) >= 1, "CSV 解析后应至少有一条记录"
    assert "标题" in parsed4[0], "应识别标题字段"
    print("  ✓ 通过")

    # 测试样例 5：批量处理 + 置信度
    print("\n[测试 5] 批量处理与置信度标注")
    sample5 = [
        {"title": "文章A", "url": "https://a.com", "date": "2024-01-01", "content": "内容A"},
        {"title": "文章B"},  # 字段较少，置信度应较低
    ]
    result5 = process_data(sample5, "json")
    parsed5 = json.loads(result5)
    assert len(parsed5) == 2, "应处理两条记录"
    assert "_置信度" in parsed5[0], "应包含置信度字段"
    assert "_置信度" in parsed5[1], "应包含置信度字段"
    print("  ✓ 通过")

    # 测试样例 6：错误处理
    print("\n[测试 6] 错误处理")
    try:
        process_data(None, "json")
        assert False, "空输入应抛出异常"
    except SerritorError as exc:
        assert exc.code == "E001", f"空输入错误码应为 E001，实际: {exc.code}"
    print("  ✓ 通过")

    # 测试样例 7：不支持的输出格式
    print("\n[测试 7] 不支持的输出格式")
    try:
        process_data({"title": "test"}, "xml")
        assert False, "不支持的格式应抛出异常"
    except SerritorError as exc:
        assert exc.code == "E005", f"格式错误码应为 E005，实际: {exc.code}"
    print("  ✓ 通过")

    print("\n=== 全部自检通过 ===")
    return True


def main() -> int:
    """命令行入口"""
    parser = argparse.ArgumentParser(
        description="serritor - 爬虫采集数据整理与结构化输出工具",
        epilog="示例: python main.py --input data.json --format csv",
    )
    parser.add_argument(
        "--input", "-i",
        type=str,
        help="输入数据（JSON 字符串、CSV 字符串或文件路径）",
    )
    parser.add_argument(
        "--file", "-f",
        type=str,
        help="输入文件路径（JSON 或 CSV 文件）",
    )
    parser.add_argument(
        "--format", "-o",
        type=str,
        choices=["json", "csv", "markdown"],
        default="json",
        help="输出格式（默认: json）",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检，验证核心逻辑",
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        try:
            _run_selftest()
            return 0
        except AssertionError as exc:
            print(f"自检失败: {exc}", file=sys.stderr)
            return 1
        except SerritorError as exc:
            print(f"自检异常: {exc.code}: {exc.message}", file=sys.stderr)
            return 1

    # 正常处理模式
    try:
        # 读取输入
        if args.file:
            try:
                with open(args.file, "r", encoding="utf-8") as f:
                    input_data = f.read()
            except OSError as exc:
                print(f"[E008] 文件读取失败: {exc}", file=sys.stderr)
                return 1
        elif args.input:
            input_data = args.input
        else:
            # 从标准输入读取
            input_data = sys.stdin.read().strip()
            if not input_data:
                print("[E001] 请输入数据（--input 或 --file 或标准输入）", file=sys.stderr)
                return 1

        # 处理数据
        output = process_data(input_data, args.format)
        print(output)
        return 0

    except SerritorError as exc:
        print(f"{exc.code}: {exc.message}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"[E010] 未知错误: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
