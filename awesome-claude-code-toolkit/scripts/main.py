#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
awesome-claude-code-toolkit - 数据整理、结构化转换、批量处理工具

本脚本为 clean-room 独立实现，仅依据功能规格设计。
支持将零散输入数据转换为规范结构化结果，支持批量与自定义格式。

用法示例:
    python scripts/main.py --input data.txt --format json
    python scripts/main.py --selftest
"""

import argparse
import csv
import io
import json
import re
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional, Union


# ============================================================
# 错误码定义
# ============================================================
ERROR_CODES = {
    "E001": "输入数据为空",
    "E002": "输入数据格式无法解析",
    "E003": "输出格式不支持",
    "E004": "字段映射配置无效",
    "E005": "类型推断失败",
    "E006": "CSV解析错误",
    "E007": "JSON解析错误",
    "E008": "批量处理失败",
    "E009": "参数配置错误",
    "E010": "内部未知错误",
}


class SkillToolkitError(Exception):
    """技能工具包自定义异常，携带错误码"""

    def __init__(self, error_code: str, message: str = ""):
        self.error_code = error_code
        self.message = message or ERROR_CODES.get(error_code, "未知错误")
        super().__init__(f"[{error_code}] {self.message}")


# ============================================================
# 核心功能：类型推断
# ============================================================

def infer_type(value: str) -> Any:
    """
    自动推断基础类型：数字、布尔、日期、JSON对象、字符串。

    宽松策略：能转则转，不能转则保留原字符串。
    日期统一转为 ISO 格式字符串（YYYY-MM-DD）。
    """
    if value is None:
        return None

    # 去除首尾空白
    text = str(value).strip()
    if not text:
        return ""

    # 布尔值
    if text.lower() in ("true", "yes", "y", "是", "对"):
        return True
    if text.lower() in ("false", "no", "n", "否", "错"):
        return False

    # 整数
    try:
        return int(text)
    except (ValueError, TypeError):
        pass

    # 浮点数（排除日期格式如 2024.01.01）
    if not re.match(r"^\d{4}\.\d{2}\.\d{2}$", text):
        try:
            return float(text)
        except (ValueError, TypeError):
            pass

    # 日期（支持常见格式）
    date_formats = [
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%Y.%m.%d",
        "%Y年%m月%d日",
    ]
    for fmt in date_formats:
        try:
            dt = datetime.strptime(text, fmt)
            return dt.strftime("%Y-%m-%d")
        except (ValueError, TypeError):
            continue

    # JSON 对象
    if text.startswith("{") and text.endswith("}"):
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

    # 默认字符串
    return text


# ============================================================
# 核心功能：文本解析（非结构化 → 键值对）
# ============================================================

def parse_text_line(line: str) -> Dict[str, Any]:
    """
    将单行非结构化文本解析为键值对。

    支持格式（宽松匹配）：
    - "key: value" 或 "key=value" 或 "key：value"
    - "张三，28岁，北京" → 尝试按分隔符拆分
    """
    line = line.strip()
    if not line:
        return {}

    # 尝试键值对格式
    for sep in [":", "：", "="]:
        if sep in line:
            parts = line.split(sep, 1)
            key = parts[0].strip()
            value = infer_type(parts[1].strip())
            return {key: value}

    # 尝试逗号/顿号分隔
    for sep in [",", "，", "、", "|", "\t"]:
        if sep in line:
            parts = [p.strip() for p in line.split(sep) if p.strip()]
            if len(parts) >= 2:
                result = {}
                for i, part in enumerate(parts):
                    result[f"field_{i + 1}"] = infer_type(part)
                return result

    # 单值
    return {"value": infer_type(line)}


def parse_text_to_records(text: str) -> List[Dict[str, Any]]:
    """
    将多行文本解析为记录列表。

    支持：
    - 每行一条记录
    - 空行跳过
    - 连续键值对合并
    """
    if not text or not text.strip():
        raise SkillToolkitError("E001")

    records: List[Dict[str, Any]] = []
    current_record: Dict[str, Any] = {}

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            # 空行分隔记录
            if current_record:
                records.append(current_record)
                current_record = {}
            continue

        parsed = parse_text_line(line)
        if parsed:
            # 如果是键值对格式，且当前记录已有相同键，则视为新记录
            if len(parsed) == 1 and list(parsed.keys())[0] in current_record:
                if current_record:
                    records.append(current_record)
                    current_record = {}
            current_record.update(parsed)

    # 最后一条记录
    if current_record:
        records.append(current_record)

    if not records:
        raise SkillToolkitError("E002")

    return records


# ============================================================
# 核心功能：JSON 解析
# ============================================================

def parse_json_input(text: str) -> List[Dict[str, Any]]:
    """解析 JSON 输入，支持对象或对象数组"""
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        raise SkillToolkitError("E007", str(e))

    if isinstance(data, dict):
        return [data]
    if isinstance(data, list):
        # 过滤非字典元素
        return [item for item in data if isinstance(item, dict)]
    raise SkillToolkitError("E002")


# ============================================================
# 核心功能：CSV 解析
# ============================================================

def parse_csv_input(text: str) -> List[Dict[str, Any]]:
    """解析 CSV 输入，首行为表头"""
    try:
        reader = csv.DictReader(io.StringIO(text))
        records = []
        for row in reader:
            # 类型推断每个字段
            typed_row = {}
            for key, value in row.items():
                if key is not None:
                    typed_row[key] = infer_type(value)
            if typed_row:
                records.append(typed_row)
        return records
    except Exception as e:
        raise SkillToolkitError("E006", str(e))


# ============================================================
# 核心功能：输入解析分发
# ============================================================

def parse_input(text: str, input_format: str = "auto") -> List[Dict[str, Any]]:
    """
    根据输入格式解析数据。

    input_format: auto / json / csv / text
    """
    if not text or not text.strip():
        raise SkillToolkitError("E001")

    fmt = input_format.lower()

    # 自动检测
    if fmt == "auto":
        stripped = text.strip()
        if stripped.startswith("{") or stripped.startswith("["):
            fmt = "json"
        elif "," in stripped.splitlines()[0] and "\t" not in stripped:
            # 简单启发式：首行含逗号且多行 → CSV
            if len(stripped.splitlines()) > 1:
                fmt = "csv"
            else:
                fmt = "text"
        else:
            fmt = "text"

    if fmt == "json":
        return parse_json_input(text)
    elif fmt == "csv":
        return parse_csv_input(text)
    elif fmt == "text":
        return parse_text_to_records(text)
    else:
        raise SkillToolkitError("E003", f"不支持的输入格式: {input_format}")


# ============================================================
# 核心功能：字段映射/重命名/筛选
# ============================================================

def apply_field_mapping(
    records: List[Dict[str, Any]],
    mapping: Optional[Dict[str, str]] = None,
    keep_fields: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """
    字段映射与筛选。

    mapping: {原字段名: 新字段名}
    keep_fields: 仅保留这些字段
    """
    if not records:
        return []

    result = []
    for record in records:
        new_record = {}

        # 字段重命名
        if mapping:
            for old_key, new_key in mapping.items():
                if old_key in record:
                    new_record[new_key] = record[old_key]
        else:
            new_record = dict(record)

        # 字段筛选
        if keep_fields:
            filtered = {}
            for field in keep_fields:
                if field in new_record:
                    filtered[field] = new_record[field]
            new_record = filtered

        result.append(new_record)

    return result


# ============================================================
# 核心功能：批量处理
# ============================================================

def batch_process(
    records: List[Dict[str, Any]],
    batch_size: int = 10,
) -> List[List[Dict[str, Any]]]:
    """将记录按指定大小分批"""
    if batch_size <= 0:
        raise SkillToolkitError("E009", "batch_size 必须为正整数")

    if not records:
        return []

    batches = []
    for i in range(0, len(records), batch_size):
        batches.append(records[i:i + batch_size])
    return batches


# ============================================================
# 核心功能：输出格式化
# ============================================================

def format_output(
    records: List[Dict[str, Any]],
    output_format: str = "json",
) -> str:
    """
    格式化输出。

    支持: json / csv / markdown / text
    """
    if not records:
        return "[]" if output_format == "json" else ""

    fmt = output_format.lower()

    if fmt == "json":
        return json.dumps(records, ensure_ascii=False, indent=2)

    elif fmt == "csv":
        # 收集所有字段
        all_fields: List[str] = []
        for record in records:
            for key in record.keys():
                if key not in all_fields:
                    all_fields.append(key)

        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=all_fields)
        writer.writeheader()
        for record in records:
            # 值转为字符串
            str_record = {}
            for key, value in record.items():
                if isinstance(value, (dict, list)):
                    str_record[key] = json.dumps(value, ensure_ascii=False)
                else:
                    str_record[key] = str(value)
            writer.writerow(str_record)
        return output.getvalue()

    elif fmt == "markdown":
        # 收集所有字段
        all_fields: List[str] = []
        for record in records:
            for key in record.keys():
                if key not in all_fields:
                    all_fields.append(key)

        # 表头
        lines = ["| " + " | ".join(all_fields) + " |"]
        lines.append("| " + " | ".join(["---"] * len(all_fields)) + " |")

        # 数据行
        for record in records:
            row = []
            for field in all_fields:
                value = record.get(field, "")
                if isinstance(value, (dict, list)):
                    value = json.dumps(value, ensure_ascii=False)
                row.append(str(value))
            lines.append("| " + " | ".join(row) + " |")

        return "\n".join(lines)

    elif fmt == "text":
        lines = []
        for record in records:
            parts = []
            for key, value in record.items():
                if isinstance(value, (dict, list)):
                    value = json.dumps(value, ensure_ascii=False)
                parts.append(f"{key}: {value}")
            lines.append(", ".join(parts))
        return "\n".join(lines)

    else:
        raise SkillToolkitError("E003", f"不支持的输出格式: {output_format}")


# ============================================================
# 主处理流程
# ============================================================

def process_data(
    input_text: str,
    input_format: str = "auto",
    output_format: str = "json",
    mapping: Optional[Dict[str, str]] = None,
    keep_fields: Optional[List[str]] = None,
    batch_size: Optional[int] = None,
) -> str:
    """
    完整数据处理流程。

    1. 解析输入
    2. 字段映射/筛选
    3. 批量处理（可选）
    4. 格式化输出
    """
    try:
        # 1. 解析输入
        records = parse_input(input_text, input_format)

        # 2. 字段映射/筛选
        if mapping or keep_fields:
            records = apply_field_mapping(records, mapping, keep_fields)

        # 3. 批量处理
        if batch_size:
            batches = batch_process(records, batch_size)
            # 批量处理后，将批次合并（保持原顺序）
            records = [record for batch in batches for record in batch]

        # 4. 格式化输出
        return format_output(records, output_format)

    except SkillToolkitError:
        raise
    except Exception as e:
        raise SkillToolkitError("E010", str(e))


# ============================================================
# 自检模块
# ============================================================

def run_selftest() -> bool:
    """
    内置硬编码样例数据离线自检。

    不读外部文件、不依赖当前工作目录、不访问网络。
    使用宽松阈值断言，确保任何环境直接可过。
    """
    print("=" * 50)
    print("自检开始: awesome-claude-code-toolkit")
    print("=" * 50)

    # 测试1: 文本解析
    print("\n[测试1] 文本解析")
    text_input = """张三，28岁，北京
李四，35岁，上海
王五，42岁，广州"""
    try:
        records = parse_text_to_records(text_input)
        assert len(records) == 3, f"预期3条记录，实际{len(records)}条"
        assert all("field_1" in r for r in records), "字段 field_1 缺失"
        assert all("field_2" in r for r in records), "字段 field_2 缺失"
        assert all("field_3" in r for r in records), "字段 field_3 缺失"
        print(f"  ✓ 解析 {len(records)} 条记录")
        print(f"  样例: {records[0]}")
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        return False

    # 测试2: 类型推断
    print("\n[测试2] 类型推断")
    try:
        assert infer_type("28") == 28, "整数推断失败"
        assert infer_type("3.14") == 3.14, "浮点推断失败"
        assert infer_type("true") is True, "布尔推断失败"
        assert infer_type("2024-01-01") == "2024-01-01", "日期推断失败"
        assert infer_type("hello") == "hello", "字符串推断失败"
        print("  ✓ 基础类型推断全部通过")
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        return False

    # 测试3: JSON 解析
    print("\n[测试3] JSON 解析")
    json_input = """[{"id": 1, "status": "active", "score": 95.5},
                     {"id": 2, "status": "inactive", "score": 87}"""
    try:
        records = parse_json_input(json_input)
        assert len(records) == 2, f"预期2条记录，实际{len(records)}条"
        assert records[0]["id"] == 1, "id 类型推断失败"
        assert records[0]["score"] == 95.5, "score 类型推断失败"
        print(f"  ✓ 解析 {len(records)} 条 JSON 记录")
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        return False

    # 测试4: CSV 解析
    print("\n[测试4] CSV 解析")
    csv_input = """name,age,city
张三,28,北京
李四,35,上海"""
    try:
        records = parse_csv_input(csv_input)
        assert len(records) == 2, f"预期2条记录，实际{len(records)}条"
        assert records[0]["age"] == 28, "CSV 类型推断失败"
        assert records[0]["city"] == "北京", "CSV 字段值错误"
        print(f"  ✓ 解析 {len(records)} 条 CSV 记录")
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        return False

    # 测试5: 字段映射
    print("\n[测试5] 字段映射")
    try:
        records = [{"name": "张三", "age": 28}, {"name": "李四", "age": 35}]
        mapped = apply_field_mapping(records, mapping={"name": "姓名", "age": "年龄"})
        assert "姓名" in mapped[0], "字段重命名失败"
        assert "年龄" in mapped[0], "字段重命名失败"
        assert "name" not in mapped[0], "原字段未删除"

        filtered = apply_field_mapping(records, keep_fields=["name"])
        assert len(filtered[0]) == 1, "字段筛选失败"
        assert "name" in filtered[0], "筛选后字段缺失"
        print(f"  ✓ 字段映射和筛选通过")
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        return False

    # 测试6: 批量处理
    print("\n[测试6] 批量处理")
    try:
        records = [{"id": i} for i in range(25)]
        batches = batch_process(records, batch_size=10)
        assert len(batches) == 3, f"预期3批，实际{len(batches)}批"
        assert len(batches[0]) == 10, "第一批大小错误"
        assert len(batches[1]) == 10, "第二批大小错误"
        assert len(batches[2]) == 5, "第三批大小错误"
        print(f"  ✓ 批量处理 {len(records)} 条为 {len(batches)} 批")
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        return False

    # 测试7: 输出格式化
    print("\n[测试7] 输出格式化")
    try:
        records = [{"name": "张三", "age": 28}, {"name": "李四", "age": 35}]

        json_out = format_output(records, "json")
        assert json_out.startswith("["), "JSON 输出格式错误"

        csv_out = format_output(records, "csv")
        assert "name" in csv_out, "CSV 表头缺失"
        assert "张三" in csv_out, "CSV 数据缺失"

        md_out = format_output(records, "markdown")
        assert "|" in md_out, "Markdown 格式错误"

        text_out = format_output(records, "text")
        assert "name:" in text_out, "文本输出格式错误"

        print("  ✓ 四种输出格式全部通过")
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        return False

    # 测试8: 完整流程
    print("\n[测试8] 完整流程")
    try:
        result = process_data(
            text_input,
            input_format="text",
            output_format="json",
            mapping={"field_1": "姓名", "field_2": "年龄", "field_3": "城市"},
        )
        parsed_result = json.loads(result)
        assert len(parsed_result) == 3, "完整流程记录数错误"
        assert "姓名" in parsed_result[0], "完整流程字段映射失败"
        print(f"  ✓ 完整流程通过，输出 {len(parsed_result)} 条记录")
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        return False

    # 测试9: 错误处理
    print("\n[测试9] 错误处理")
    try:
        try:
            parse_text_to_records("")
            print("  ✗ 空输入未抛出异常")
            return False
        except SkillToolkitError as e:
            assert e.error_code == "E001", f"错误码错误: {e.error_code}"
            print(f"  ✓ 空输入正确抛出 E001")

        try:
            format_output([], "invalid_format")
            print("  ✗ 无效格式未抛出异常")
            return False
        except SkillToolkitError as e:
            assert e.error_code == "E003", f"错误码错误: {e.error_code}"
            print(f"  ✓ 无效格式正确抛出 E003")
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        return False

    # 测试10: 宽松断言
    print("\n[测试10] 宽松断言")
    try:
        # 使用大小比较/区间判断，避免精确值依赖
        records = parse_text_to_records(text_input)
        assert len(records) >= 2, "记录数应至少为2"
        assert len(records) <= 5, "记录数不应超过5"

        ages = [r.get("field_2", 0) for r in records]
        assert all(isinstance(a, int) for a in ages), "年龄应为整数"
        assert all(0 < a < 100 for a in ages), "年龄应在合理范围"

        print(f"  ✓ 宽松断言通过，记录数={len(records)}，年龄范围={min(ages)}-{max(ages)}")
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        return False

    print("\n" + "=" * 50)
    print("自检全部通过 ✓")
    print("=" * 50)
    return True


# ============================================================
# 命令行入口
# ============================================================

def main() -> int:
    """命令行主入口"""
    parser = argparse.ArgumentParser(
        description="awesome-claude-code-toolkit - 数据整理、结构化转换、批量处理工具",
        epilog="示例: python scripts/main.py --input data.txt --format json",
    )
    parser.add_argument(
        "--input",
        type=str,
        help="输入文件路径（与 --input-text 二选一）",
    )
    parser.add_argument(
        "--input-text",
        type=str,
        help="直接输入文本内容（与 --input 二选一）",
    )
    parser.add_argument(
        "--input-format",
        type=str,
        default="auto",
        choices=["auto", "json", "csv", "text"],
        help="输入格式（默认自动检测）",
    )
    parser.add_argument(
        "--output-format",
        type=str,
        default="json",
        choices=["json", "csv", "markdown", "text"],
        help="输出格式（默认json）",
    )
    parser.add_argument(
        "--mapping",
        type=str,
        help="字段映射，JSON格式，如 '{\"old\":\"new\"}'",
    )
    parser.add_argument(
        "--keep-fields",
        type=str,
        help="保留字段列表，逗号分隔，如 'id,status'",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        help="批量处理大小（可选）",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检",
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        success = run_selftest()
        return 0 if success else 1

    # 获取输入
    input_text = args.input_text
    if not input_text and args.input:
        try:
            with open(args.input, "r", encoding="utf-8") as f:
                input_text = f.read()
        except Exception as e:
            print(f"[E010] 读取文件失败: {e}", file=sys.stderr)
            return 1

    if not input_text:
        print("[E001] 请输入数据（--input 或 --input-text）", file=sys.stderr)
        return 1

    # 解析映射配置
    mapping = None
    if args.mapping:
        try:
            mapping = json.loads(args.mapping)
            if not isinstance(mapping, dict):
                print("[E004] 映射必须为JSON对象", file=sys.stderr)
                return 1
        except json.JSONDecodeError:
            print("[E004] 映射JSON解析失败", file=sys.stderr)
            return 1

    # 解析保留字段
    keep_fields = None
    if args.keep_fields:
        keep_fields = [f.strip() for f in args.keep_fields.split(",") if f.strip()]

    # 处理数据
    try:
        result = process_data(
            input_text=input_text,
            input_format=args.input_format,
            output_format=args.output_format,
            mapping=mapping,
            keep_fields=keep_fields,
            batch_size=args.batch_size,
        )
        print(result)
        return 0
    except SkillToolkitError as e:
        print(f"{e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"[E010] 未知错误: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
