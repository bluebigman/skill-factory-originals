#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py — 科研数据智能解析与结构化输出（独立实现）

本脚本根据功能规格独立实现，不参考任何既有代码。
功能：将科研数据（文本、CSV/TSV、JSON、Markdown 表格）转换为结构化 JSON 输出。
支持：关键字段提取、单位归一化、数值范围校验、置信度标注。
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
    "E002": "输入格式不支持",
    "E003": "JSON 解析失败",
    "E004": "CSV/TSV 解析失败",
    "E005": "Markdown 表格解析失败",
    "E006": "记录数超过上限（50条）",
    "E007": "数值转换失败",
    "E008": "单位归一化失败",
    "E009": "数值范围校验失败",
    "E010": "输出格式不支持",
}

# 常量
MAX_RECORDS = 50
SUPPORTED_INPUT_FORMATS = {"text", "csv", "tsv", "json", "markdown", "md"}
SUPPORTED_OUTPUT_FORMATS = {"json", "csv", "markdown"}

# 单位归一化映射表（常见科研单位）
UNIT_NORMALIZATION_MAP = {
    # 长度
    "m": "m", "meter": "m", "meters": "m", "米": "m",
    "cm": "cm", "centimeter": "cm", "centimeters": "cm", "厘米": "cm",
    "mm": "mm", "millimeter": "mm", "millimeters": "mm", "毫米": "mm",
    "km": "km", "kilometer": "km", "kilometers": "km", "千米": "km",
    # 质量
    "g": "g", "gram": "g", "grams": "g", "克": "g",
    "kg": "kg", "kilogram": "kg", "kilograms": "kg", "千克": "kg",
    "mg": "mg", "milligram": "mg", "milligrams": "mg", "毫克": "mg",
    # 时间
    "s": "s", "sec": "s", "second": "s", "seconds": "s", "秒": "s",
    "min": "min", "minute": "min", "minutes": "min", "分钟": "min",
    "h": "h", "hr": "h", "hour": "h", "hours": "h", "小时": "h",
    "d": "d", "day": "d", "days": "d", "天": "d",
    # 温度
    "c": "°C", "celsius": "°C", "摄氏度": "°C",
    "f": "°F", "fahrenheit": "°F", "华氏度": "°F",
    "k": "K", "kelvin": "K", "开尔文": "K",
    # 浓度
    "m": "M", "mol/l": "M", "molar": "M", "摩尔/升": "M",
    "mm": "mM", "mmol/l": "mM", "毫摩尔/升": "mM",
    "um": "μM", "umol/l": "μM", "微摩尔/升": "μM",
    # 体积
    "l": "L", "liter": "L", "liters": "L", "升": "L",
    "ml": "mL", "milliliter": "mL", "milliliters": "mL", "毫升": "mL",
    "ul": "μL", "microliter": "μL", "microliters": "μL", "微升": "μL",
}


class SkillError(Exception):
    """技能执行异常，携带错误码。"""

    def __init__(self, code: str, message: str = ""):
        self.code = code
        self.message = message or ERROR_CODES.get(code, "未知错误")
        super().__init__(f"[{code}] {self.message}")


def extract_numeric_value(value: Any) -> Tuple[Optional[float], Optional[str]]:
    """从字符串或数字中提取数值和单位。

    返回 (数值, 单位)。无法解析时返回 (None, None)。
    """
    if value is None:
        return None, None
    if isinstance(value, (int, float)):
        return float(value), None
    if not isinstance(value, str):
        return None, None

    text = value.strip()
    if not text:
        return None, None

    # 匹配形如 "12.5 mg"、"100℃"、"3.0e-4 M" 等
    pattern = r"^\s*([+-]?\d+\.?\d*(?:[eE][+-]?\d+)?)\s*([a-zA-Z°μµ]+)?\s*$"
    match = re.match(pattern, text)
    if match:
        try:
            number = float(match.group(1))
            unit = match.group(2)
            return number, unit
        except ValueError:
            return None, None

    # 尝试纯数字
    try:
        return float(text), None
    except ValueError:
        return None, None


def normalize_unit(unit: Optional[str]) -> Optional[str]:
    """将单位归一化为标准形式。"""
    if not unit:
        return None
    unit_lower = unit.strip().lower()

    # 直接映射
    if unit_lower in UNIT_NORMALIZATION_MAP:
        return UNIT_NORMALIZATION_MAP[unit_lower]

    # 尝试去掉常见前后缀
    cleaned = unit_lower.replace("°", "").replace("℃", "c").replace("℉", "f")
    if cleaned in UNIT_NORMALIZATION_MAP:
        return UNIT_NORMALIZATION_MAP[cleaned]

    # 无法归一化时返回原单位（小写）
    return unit_lower


def validate_numeric_range(value: float, min_val: Optional[float] = None, max_val: Optional[float] = None) -> bool:
    """数值范围校验。"""
    if min_val is not None and value < min_val:
        return False
    if max_val is not None and value > max_val:
        return False
    return True


def parse_text_input(text: str) -> List[Dict[str, Any]]:
    """解析纯文本输入，提取关键字段。

    支持形如 "key: value" 或 "key=value" 的行。
    """
    if not text or not text.strip():
        raise SkillError("E001")

    records: List[Dict[str, Any]] = []
    current_record: Dict[str, Any] = {}
    confidence_sum = 0.0
    field_count = 0

    for line in text.splitlines():
        line = line.strip()
        if not line:
            if current_record:
                # 计算置信度（基于字段数量和值完整性）
                confidence = min(0.95, 0.5 + field_count * 0.1)
                current_record["confidence"] = round(confidence, 2)
                records.append(current_record)
                current_record = {}
                confidence_sum = 0.0
                field_count = 0
            continue

        # 匹配 "key: value" 或 "key=value"
        match = re.match(r"^([^:=]+)[:=]\s*(.+)$", line)
        if match:
            key = match.group(1).strip()
            value = match.group(2).strip()
            current_record[key] = value
            field_count += 1

    # 处理最后一条记录
    if current_record:
        confidence = min(0.95, 0.5 + field_count * 0.1)
        current_record["confidence"] = round(confidence, 2)
        records.append(current_record)

    if not records:
        raise SkillError("E001")

    return records


def parse_csv_input(text: str, delimiter: str = ",") -> List[Dict[str, Any]]:
    """解析 CSV/TSV 输入。"""
    if not text or not text.strip():
        raise SkillError("E001")

    try:
        reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
        records = []
        for row in reader:
            if not row:
                continue
            # 清理空值
            cleaned = {k.strip(): v.strip() for k, v in row.items() if k and v}
            if cleaned:
                cleaned["confidence"] = 0.85  # CSV 结构化数据置信度较高
                records.append(cleaned)
    except Exception as exc:
        raise SkillError("E004", str(exc))

    if not records:
        raise SkillError("E001")

    return records


def parse_json_input(text: str) -> List[Dict[str, Any]]:
    """解析 JSON 输入。"""
    if not text or not text.strip():
        raise SkillError("E001")

    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise SkillError("E003", str(exc))

    # 支持单对象或对象数组
    if isinstance(data, dict):
        records = [data]
    elif isinstance(data, list):
        records = data
    else:
        raise SkillError("E002")

    # 确保每条记录是字典
    cleaned_records = []
    for rec in records:
        if isinstance(rec, dict):
            rec.setdefault("confidence", 0.9)  # JSON 结构数据置信度高
            cleaned_records.append(rec)

    if not cleaned_records:
        raise SkillError("E001")

    return cleaned_records


def parse_markdown_table(text: str) -> List[Dict[str, Any]]:
    """解析 Markdown 表格。"""
    if not text or not text.strip():
        raise SkillError("E001")

    lines = text.strip().splitlines()
    table_lines = []
    in_table = False

    for line in lines:
        line = line.strip()
        if line.startswith("|") and line.endswith("|"):
            if not in_table:
                in_table = True
            table_lines.append(line)
        else:
            if in_table:
                break

    if len(table_lines) < 2:  # 至少需要表头 + 分隔行
        raise SkillError("E005")

    # 提取表头
    header_line = table_lines[0].strip("|")
    headers = [h.strip() for h in header_line.split("|")]

    # 跳过分隔行（--- 或 :---:）
    records = []
    for line in table_lines[2:]:
        line = line.strip("|")
        cells = [c.strip() for c in line.split("|")]
        if len(cells) != len(headers):
            continue
        record = {}
        for i, header in enumerate(headers):
            if header and cells[i]:
                record[header] = cells[i]
        if record:
            record["confidence"] = 0.8  # Markdown 表格置信度中等
            records.append(record)

    if not records:
        raise SkillError("E005")

    return records


def detect_input_format(text: str) -> str:
    """自动检测输入格式。"""
    if not text or not text.strip():
        raise SkillError("E001")

    text = text.strip()

    # JSON 检测
    if text.startswith("{") or text.startswith("["):
        try:
            json.loads(text)
            return "json"
        except json.JSONDecodeError:
            pass

    # Markdown 表格检测
    if "|" in text and "---" in text:
        return "markdown"

    # CSV/TSV 检测
    first_line = text.splitlines()[0]
    if "," in first_line:
        return "csv"
    if "\t" in first_line:
        return "tsv"

    # 默认按纯文本处理
    return "text"


def process_scientific_data(
    input_text: str,
    input_format: Optional[str] = None,
    output_format: str = "json",
    normalize_units: bool = True,
    validate_ranges: bool = True,
) -> str:
    """核心处理函数：解析科研数据并输出结构化结果。"""
    # 检测输入格式
    if not input_format:
        input_format = detect_input_format(input_text)
    input_format = input_format.lower()

    if input_format not in SUPPORTED_INPUT_FORMATS:
        raise SkillError("E002")

    # 解析输入
    if input_format == "text":
        records = parse_text_input(input_text)
    elif input_format == "csv":
        records = parse_csv_input(input_text, delimiter=",")
    elif input_format == "tsv":
        records = parse_csv_input(input_text, delimiter="\t")
    elif input_format == "json":
        records = parse_json_input(input_text)
    elif input_format in ("markdown", "md"):
        records = parse_markdown_table(input_text)
    else:
        raise SkillError("E002")

    # 批量限制
    if len(records) > MAX_RECORDS:
        raise SkillError("E006")

    # 后处理：单位归一化和数值范围校验
    processed_records = []
    for record in records:
        processed = dict(record)

        # 单位归一化
        if normalize_units:
            for key, value in list(processed.items()):
                if key == "confidence":
                    continue
                num, unit = extract_numeric_value(value)
                if num is not None and unit:
                    normalized = normalize_unit(unit)
                    if normalized and normalized != unit:
                        processed[key] = f"{num} {normalized}"

        # 数值范围校验（对明显的数值字段）
        if validate_ranges:
            for key, value in list(processed.items()):
                if key == "confidence":
                    continue
                num, _ = extract_numeric_value(value)
                if num is not None:
                    # 基础范围检查：温度 -273 到 10000，浓度 0 到 1000，其他 0 到 1e12
                    if "temp" in key.lower() or "温度" in key:
                        if not validate_numeric_range(num, -273.15, 10000):
                            raise SkillError("E009", f"字段 '{key}' 温度值超出合理范围: {value}")
                    elif "conc" in key.lower() or "浓度" in key:
                        if not validate_numeric_range(num, 0, 1000):
                            raise SkillError("E009", f"字段 '{key}' 浓度值超出合理范围: {value}")

        processed_records.append(processed)

    # 输出格式化
    if output_format == "json":
        return json.dumps(processed_records, ensure_ascii=False, indent=2)
    elif output_format == "csv":
        if not processed_records:
            return ""
        headers = list(processed_records[0].keys())
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=headers)
        writer.writeheader()
        for rec in processed_records:
            writer.writerow(rec)
        return output.getvalue()
    elif output_format == "markdown":
        if not processed_records:
            return ""
        headers = list(processed_records[0].keys())
        lines = ["| " + " | ".join(headers) + " |", "|" + "|".join(["---"] * len(headers)) + "|"]
        for rec in processed_records:
            lines.append("| " + " | ".join(str(rec.get(h, "")) for h in headers) + " |")
        return "\n".join(lines)
    else:
        raise SkillError("E010")


def run_selftest() -> bool:
    """内置自检：使用硬编码样例数据离线验证核心逻辑。"""
    print("正在运行自检...")

    # 测试1：文本解析
    try:
        text_data = """实验名称: 光合作用速率测定
温度: 25°C
光照强度: 800 μmol/m²/s
CO2浓度: 400 ppm

实验名称: 酶活性分析
温度: 37°C
pH: 7.4
底物浓度: 5 mM"""
        result = process_scientific_data(text_data, input_format="text")
        records = json.loads(result)
        assert len(records) == 2, f"文本解析应返回2条记录，实际{len(records)}"
        assert records[0]["confidence"] > 0.5, "置信度应大于0.5"
        print("✓ 文本解析测试通过")
    except Exception as exc:
        print(f"✗ 文本解析测试失败: {exc}")
        return False

    # 测试2：JSON 解析与单位归一化
    try:
        json_data = json.dumps([
            {"sample": "A", "weight": "10.5 mg", "length": "2 cm"},
            {"sample": "B", "weight": "3.2 g", "length": "15 mm"},
        ])
        result = process_scientific_data(json_data, input_format="json")
        records = json.loads(result)
        assert len(records) == 2
        # 单位归一化后应包含标准单位
        assert "mg" in records[0]["weight"] or "mg" in str(records[0])
        print("✓ JSON 解析测试通过")
    except Exception as exc:
        print(f"✗ JSON 解析测试失败: {exc}")
        return False

    # 测试3：CSV 解析
    try:
        csv_data = "name,value,unit\nsample1,10.5,mg\nsample2,20.3,g\n"
        result = process_scientific_data(csv_data, input_format="csv")
        records = json.loads(result)
        assert len(records) == 2, f"CSV解析应返回2条记录，实际{len(records)}"
        assert records[0]["name"] == "sample1"
        print("✓ CSV 解析测试通过")
    except Exception as exc:
        print(f"✗ CSV 解析测试失败: {exc}")
        return False

    # 测试4：Markdown 表格解析
    try:
        md_data = """| 样品 | 浓度 | 温度 |
|------|------|------|
| A | 10 mM | 25°C |
| B | 5 mM | 37°C |"""
        result = process_scientific_data(md_data, input_format="markdown")
        records = json.loads(result)
        assert len(records) == 2, f"Markdown解析应返回2条记录，实际{len(records)}"
        assert records[0]["浓度"] is not None
        print("✓ Markdown 表格解析测试通过")
    except Exception as exc:
        print(f"✗ Markdown 表格解析测试失败: {exc}")
        return False

    # 测试5：数值提取与单位归一化
    try:
        num, unit = extract_numeric_value("25.5 mg")
        assert num is not None and abs(num - 25.5) < 0.01, "数值提取失败"
        assert normalize_unit(unit) == "mg", f"单位归一化失败: {unit}"
        print("✓ 数值提取与单位归一化测试通过")
    except Exception as exc:
        print(f"✗ 数值提取与单位归一化测试失败: {exc}")
        return False

    # 测试6：错误处理
    try:
        process_scientific_data("", input_format="text")
        print("✗ 空输入应抛出 E001")
        return False
    except SkillError as exc:
        assert exc.code == "E001", f"预期 E001，实际 {exc.code}"
        print("✓ 错误处理测试通过")

    # 测试7：批量限制
    try:
        many_records = [{"i": str(i)} for i in range(60)]
        process_scientific_data(json.dumps(many_records), input_format="json")
        print("✗ 超过50条记录应抛出 E006")
        return False
    except SkillError as exc:
        assert exc.code == "E006", f"预期 E006，实际 {exc.code}"
        print("✓ 批量限制测试通过")

    # 测试8：输出格式
    try:
        csv_data = "name,value\ns1,10\ns2,20\n"
        result_csv = process_scientific_data(csv_data, input_format="csv", output_format="csv")
        assert "name" in result_csv, "CSV 输出应包含表头"
        result_md = process_scientific_data(csv_data, input_format="csv", output_format="markdown")
        assert "|" in result_md, "Markdown 输出应包含表格"
        print("✓ 输出格式测试通过")
    except Exception as exc:
        print(f"✗ 输出格式测试失败: {exc}")
        return False

    print("\n所有自检通过！")
    return True


def main():
    """命令行入口。"""
    parser = argparse.ArgumentParser(
        description="科研数据智能解析与结构化输出",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python main.py --input data.txt --input-format text --output-format json
  python main.py --input data.csv --input-format csv --output-format markdown
  python main.py --selftest
        """,
    )
    parser.add_argument("--input", "-i", help="输入文件路径（与 --text 二选一）")
    parser.add_argument("--text", "-t", help="直接输入文本内容")
    parser.add_argument("--input-format", choices=sorted(SUPPORTED_INPUT_FORMATS),
                        help="输入格式（默认自动检测）")
    parser.add_argument("--output-format", "-o", choices=sorted(SUPPORTED_OUTPUT_FORMATS),
                        default="json", help="输出格式（默认 json）")
    parser.add_argument("--no-normalize-units", action="store_true", help="禁用单位归一化")
    parser.add_argument("--no-validate-ranges", action="store_true", help="禁用数值范围校验")
    parser.add_argument("--selftest", action="store_true", help="运行内置自检")

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        success = run_selftest()
        sys.exit(0 if success else 1)

    # 获取输入
    input_text = ""
    if args.text:
        input_text = args.text
    elif args.input:
        try:
            with open(args.input, "r", encoding="utf-8") as f:
                input_text = f.read()
        except FileNotFoundError:
            print("错误: 输入文件不存在", file=sys.stderr)
            sys.exit(1)
        except Exception as exc:
            print(f"错误: 读取文件失败: {exc}", file=sys.stderr)
            sys.exit(1)
    else:
        # 从标准输入读取
        input_text = sys.stdin.read()

    if not input_text:
        print("错误: 未提供输入数据", file=sys.stderr)
        sys.exit(1)

    # 处理数据
    try:
        result = process_scientific_data(
            input_text,
            input_format=args.input_format,
            output_format=args.output_format,
            normalize_units=not args.no_normalize_units,
            validate_ranges=not args.no_validate_ranges,
        )
        print(result)
    except SkillError as exc:
        print(f"处理失败: {exc}", file=sys.stderr)
        sys.exit(1)
    except Exception as exc:
        print(f"未预期错误: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
