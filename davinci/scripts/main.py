#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
davinci - 数据可视化 智能解析 图表生成

根据功能规格独立实现的 clean-room 版本。
仅依赖 Python 标准库。
"""

import argparse
import csv
import io
import json
import os
import re
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

# 错误码定义
ERROR_CODES = {
    "E001": "参数错误：输入参数缺失或格式不正确",
    "E002": "文件不存在：指定的文件路径无法访问",
    "E003": "文件过大：超过 50MB 限制",
    "E004": "URL 访问失败：无法获取远程数据",
    "E005": "格式不支持：无法识别的数据格式",
    "E006": "解析失败：数据内容不符合预期结构",
    "E007": "输出失败：无法写入输出文件",
    "E008": "字段识别失败：无法识别表头或关键字段",
    "E009": "批量处理失败：部分文件处理出错",
    "E010": "内部错误：未预期的异常",
}

# 能力边界常量
MAX_FILE_SIZE_MB = 50
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024


class DavinciError(Exception):
    """自定义异常，携带错误码"""

    def __init__(self, code: str, message: str = ""):
        self.code = code
        self.message = message or ERROR_CODES.get(code, "未知错误")
        super().__init__(f"[{code}] {self.message}")


def _safe_error(e: Exception) -> DavinciError:
    """将任意异常转换为内部错误"""
    return DavinciError("E010", str(e))


def parse_csv_content(text: str) -> list:
    """
    解析 CSV 文本内容为字典列表。

    参数:
        text: CSV 格式的文本

    返回:
        字典列表，每个字典代表一行数据

    异常:
        DavinciError: 当解析失败时抛出 E006
    """
    try:
        reader = csv.DictReader(io.StringIO(text))
        rows = []
        for row in reader:
            # 过滤全空行
            if any(v.strip() for v in row.values()):
                rows.append({k.strip(): v.strip() for k, v in row.items()})
        return rows
    except Exception as e:
        raise DavinciError("E006", f"CSV 解析失败: {e}") from e


def parse_json_content(text: str) -> list:
    """
    解析 JSON 文本内容为字典列表。

    参数:
        text: JSON 格式的文本

    返回:
        字典列表

    异常:
        DavinciError: 当解析失败时抛出 E006
    """
    try:
        data = json.loads(text)
        if isinstance(data, list):
            return data
        elif isinstance(data, dict):
            # 尝试从常见键中提取列表
            for key in ("data", "rows", "records", "items"):
                if isinstance(data.get(key), list):
                    return data[key]
            # 单条记录包装为列表
            return [data]
        else:
            raise DavinciError("E006", "JSON 顶层结构必须是对象或数组")
    except DavinciError:
        raise
    except Exception as e:
        raise DavinciError("E006", f"JSON 解析失败: {e}") from e


def detect_format(text: str) -> str:
    """
    检测数据格式类型。

    参数:
        text: 数据文本

    返回:
        格式名称: "csv" / "json"

    异常:
        DavinciError: 无法识别时抛出 E005
    """
    stripped = text.lstrip()
    if stripped.startswith("{"):
        return "json"
    if stripped.startswith("["):
        return "json"
    # 尝试 CSV 检测：包含逗号或制表符
    first_line = stripped.split("\n", 1)[0] if stripped else ""
    if "," in first_line or "\t" in first_line:
        return "csv"
    # 尝试 JSON 解析失败后按 CSV 处理
    try:
        json.loads(text)
        return "json"
    except json.JSONDecodeError:
        if first_line:
            return "csv"
    raise DavinciError("E005", "无法识别的数据格式")


def parse_data(text: str) -> list:
    """
    根据内容自动识别格式并解析为结构化数据。

    参数:
        text: 原始数据文本

    返回:
        字典列表

    异常:
        DavinciError: 解析失败时抛出对应错误码
    """
    fmt = detect_format(text)
    if fmt == "json":
        return parse_json_content(text)
    return parse_csv_content(text)


def _is_datetime_format(value: str) -> bool:
    """
    检查字符串是否为常见的时间格式。
    支持: 完整的 ISO 格式、日期、年月等。
    """
    if not value or not isinstance(value, str):
        return False
    
    value = value.strip()
    
    # 检查是否是纯数字（可能是年份或时间戳）
    if value.isdigit():
        # 4位数字可能是年份
        if len(value) == 4:
            return True
        # 长数字可能是时间戳
        if len(value) >= 10:
            return True
        return False
    
    # 支持的日期格式模式
    patterns = [
        # YYYY-MM-DD
        r'^\d{4}-\d{1,2}-\d{1,2}$',
        # YYYY-MM (月份)
        r'^\d{4}-\d{1,2}$',
        # YYYY/MM/DD
        r'^\d{4}/\d{1,2}/\d{1,2}$',
        # YYYY/MM
        r'^\d{4}/\d{1,2}$',
        # YYYY-MM-DD HH:MM:SS
        r'^\d{4}-\d{1,2}-\d{1,2}[ T]\d{1,2}:\d{2}:\d{2}',
        # YYYY-MM-DD HH:MM
        r'^\d{4}-\d{1,2}-\d{1,2}[ T]\d{1,2}:\d{2}$',
        # ISO 8601 with timezone
        r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+-]\d{2}:\d{2}$',
        # ISO 8601 with Z
        r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$',
        # MM/DD/YYYY
        r'^\d{1,2}/\d{1,2}/\d{4}$',
        # MM-DD-YYYY
        r'^\d{1,2}-\d{1,2}-\d{4}$',
        # 中文日期格式
        r'^\d{4}年\d{1,2}月\d{1,2}日$',
        r'^\d{4}年\d{1,2}月$',
        # 带时间的日期
        r'^\d{4}-\d{1,2}-\d{1,2} \d{1,2}:\d{2}:\d{2}$',
    ]
    
    for pattern in patterns:
        if re.match(pattern, value):
            return True
    
    # 尝试使用 datetime 解析
    try:
        # 先尝试完整 ISO 格式
        datetime.fromisoformat(value.replace("Z", "+00:00"))
        return True
    except ValueError:
        pass
    
    # 尝试其他常见格式
    date_formats = [
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%Y-%m",  # 年月
        "%Y/%m",
        "%Y年%m月",  # 中文年月
        "%Y年%m月%d日",
        "%m/%d/%Y",
        "%m-%d-%Y",
    ]
    
    for fmt in date_formats:
        try:
            datetime.strptime(value, fmt)
            return True
        except ValueError:
            continue
    
    return False


def infer_field_types(rows: list) -> dict:
    """
    推断字段类型（数值/时间/文本）。

    参数:
        rows: 数据行列表

    返回:
        字段名到类型名称的映射
    """
    if not rows:
        return {}

    field_types = {}
    for field in rows[0].keys():
        # 收集非空值
        values = []
        for row in rows:
            val = row.get(field, "")
            if val not in (None, ""):
                values.append(val)

        if not values:
            field_types[field] = "unknown"
            continue

        # 检查是否为数值
        numeric_count = 0
        for val in values:
            try:
                float(str(val))
                numeric_count += 1
            except (ValueError, TypeError):
                pass
        if numeric_count == len(values):
            field_types[field] = "numeric"
            continue

        # 检查是否为时间
        time_count = 0
        for val in values:
            if _is_datetime_format(str(val)):
                time_count += 1
        if time_count == len(values):
            field_types[field] = "temporal"
            continue

        # 默认文本
        field_types[field] = "text"

    return field_types


def calculate_confidence(rows: list, field_types: dict) -> dict:
    """
    为每个字段计算置信度等级。

    置信度规则:
        - 高: 字段无缺失值且类型明确
        - 中: 字段有少量缺失值或类型混合
        - 低: 字段大量缺失或类型模糊

    参数:
        rows: 数据行列表
        field_types: 字段类型映射

    返回:
        字段名到置信度等级("high"/"medium"/"low")的映射
    """
    if not rows:
        return {}

    total = len(rows)
    confidences = {}

    for field, ftype in field_types.items():
        missing = sum(1 for r in rows if r.get(field, "") in (None, ""))
        missing_ratio = missing / total if total > 0 else 1.0

        # 判定置信度
        if missing_ratio == 0 and ftype != "unknown":
            confidences[field] = "high"
        elif missing_ratio < 0.3 and ftype != "unknown":
            confidences[field] = "medium"
        else:
            confidences[field] = "low"

    return confidences


def build_structured_result(rows: list) -> dict:
    """
    构建统一的结构化输出结果。

    参数:
        rows: 解析后的数据行

    返回:
        结构化结果字典，包含数据、元信息和置信度
    """
    if not rows:
        raise DavinciError("E006", "数据为空")

    field_types = infer_field_types(rows)
    confidences = calculate_confidence(rows, field_types)

    result = {
        "meta": {
            "row_count": len(rows),
            "field_count": len(field_types),
            "fields": list(field_types.keys()),
            "field_types": field_types,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
        },
        "confidences": confidences,
        "data": rows,
    }
    return result


def read_file_content(filepath: str) -> str:
    """
    读取文件内容并检查大小限制。

    参数:
        filepath: 文件路径

    返回:
        文件文本内容

    异常:
        DavinciError: 文件不存在 E002 / 超过大小限制 E003
    """
    path = Path(filepath)
    if not path.exists():
        raise DavinciError("E002", f"文件不存在: {filepath}")

    size = path.stat().st_size
    if size > MAX_FILE_SIZE_BYTES:
        raise DavinciError("E003", f"文件超过 {MAX_FILE_SIZE_MB}MB 限制")

    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    except Exception as e:
        raise DavinciError("E006", f"文件读取失败: {e}") from e


def fetch_url_content(url: str) -> str:
    """
    从公开 URL 获取文本内容。

    参数:
        url: 公开访问的链接

    返回:
        文本内容

    异常:
        DavinciError: URL 访问失败 E004
    """
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            # 检查大小
            content_length = resp.headers.get("Content-Length")
            if content_length and int(content_length) > MAX_FILE_SIZE_BYTES:
                raise DavinciError("E003", f"远程文件超过 {MAX_FILE_SIZE_MB}MB 限制")
            return resp.read().decode("utf-8", errors="replace")
    except DavinciError:
        raise
    except Exception as e:
        raise DavinciError("E004", f"URL 访问失败: {e}") from e


def process_source(source: str) -> dict:
    """
    处理单一数据源（文件路径或 URL）。

    参数:
        source: 文件路径或 URL

    返回:
        结构化结果

    异常:
        DavinciError: 处理失败时抛出对应错误码
    """
    if re.match(r"^https?://", source):
        content = fetch_url_content(source)
    else:
        content = read_file_content(source)

    rows = parse_data(content)
    return build_structured_result(rows)


def batch_process(sources: list, output_path: str = "") -> dict:
    """
    批量处理多个数据源。

    参数:
        sources: 文件路径或 URL 列表
        output_path: 可选输出路径

    返回:
        批量处理结果

    异常:
        DavinciError: 批量处理失败 E009
    """
    results = {"success": [], "failed": []}

    for src in sources:
        try:
            result = process_source(src)
            results["success"].append({"source": src, "result": result})
        except DavinciError as e:
            results["failed"].append({"source": src, "error": e.code, "message": e.message})
        except Exception as e:
            results["failed"].append({"source": src, "error": "E010", "message": str(e)})

    if results["failed"] and not results["success"]:
        raise DavinciError("E009", "所有文件均处理失败")

    # 如果指定输出路径，写入结果
    if output_path:
        try:
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
        except Exception as e:
            raise DavinciError("E007", f"输出写入失败: {e}") from e

    return results


def run_selftest() -> bool:
    """
    内置自检逻辑，使用硬编码样例数据离线验证核心功能。

    返回:
        自检是否通过
    """
    print("开始自检...")

    # 样例 1: CSV 数据
    csv_sample = """区域,销售额,月份
华东,12000,2024-01
华南,9800,2024-01
华北,15000,2024-01
华东,13500,2024-02
华南,10200,2024-02
"""

    # 样例 2: JSON 数据
    json_sample = json.dumps({
        "data": [
            {"product": "A", "price": 99.5, "stock": 120},
            {"product": "B", "price": 149.9, "stock": 85},
            {"product": "C", "price": 59.9, "stock": 200},
        ]
    })

    # 测试 1: CSV 解析
    try:
        csv_rows = parse_csv_content(csv_sample)
        assert len(csv_rows) == 5, "CSV 行数应为 5"
        assert "区域" in csv_rows[0], "CSV 表头应包含'区域'"
        assert csv_rows[0]["销售额"] == "12000", "销售额解析错误"
        print("[PASS] CSV 解析")
    except AssertionError as e:
        print(f"[FAIL] CSV 解析: {e}")
        return False
    except DavinciError as e:
        print(f"[FAIL] CSV 解析: {e}")
        return False

    # 测试 2: JSON 解析
    try:
        json_rows = parse_json_content(json_sample)
        assert len(json_rows) == 3, "JSON 行数应为 3"
        assert json_rows[0]["product"] == "A", "JSON 数据错误"
        print("[PASS] JSON 解析")
    except AssertionError as e:
        print(f"[FAIL] JSON 解析: {e}")
        return False
    except DavinciError as e:
        print(f"[FAIL] JSON 解析: {e}")
        return False

    # 测试 3: 自动格式识别
    try:
        assert detect_format(csv_sample) == "csv", "CSV 格式识别失败"
        assert detect_format(json_sample) == "json", "JSON 格式识别失败"
        print("[PASS] 格式自动识别")
    except AssertionError as e:
        print(f"[FAIL] 格式识别: {e}")
        return False

    # 测试 4: 字段类型推断
    try:
        types = infer_field_types(csv_rows)
        assert types.get("销售额") == "numeric", "销售额应为数值类型"
        assert types.get("月份") == "temporal", "月份应为时间类型"
        assert types.get("区域") == "text", "区域应为文本类型"
        print("[PASS] 字段类型推断")
    except AssertionError as e:
        print(f"[FAIL] 字段类型推断: {e}")
        return False

    # 测试 5: 置信度计算
    try:
        conf = calculate_confidence(csv_rows, infer_field_types(csv_rows))
        assert conf.get("销售额") == "high", "销售额应高置信度"
        assert conf.get("区域") == "high", "区域应高置信度"
        print("[PASS] 置信度计算")
    except AssertionError as e:
        print(f"[FAIL] 置信度计算: {e}")
        return False

    # 测试 6: 完整处理流程
    try:
        result = build_structured_result(csv_rows)
        assert result["meta"]["row_count"] == 5, "元数据行数错误"
        assert result["meta"]["field_count"] == 3, "字段数错误"
        assert len(result["data"]) == 5, "数据行数错误"
        print("[PASS] 完整处理流程")
    except AssertionError as e:
        print(f"[FAIL] 完整处理流程: {e}")
        return False

    # 测试 7: 批量处理（模拟文件）
    try:
        # 创建临时文件测试批量处理
        import tempfile
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8") as f:
            f.write(csv_sample)
            tmp_path = f.name

        try:
            batch = batch_process([tmp_path])
            assert len(batch["success"]) == 1, "批量处理应有一个成功"
            assert batch["success"][0]["result"]["meta"]["row_count"] == 5, "批量处理行数错误"
            print("[PASS] 批量处理")
        finally:
            os.unlink(tmp_path)
    except AssertionError as e:
        print(f"[FAIL] 批量处理: {e}")
        return False
    except DavinciError as e:
        print(f"[FAIL] 批量处理: {e}")
        return False
    except Exception as e:
        print(f"[FAIL] 批量处理: {e}")
        return False

    # 测试 8: 错误处理
    try:
        # 不存在的文件
        try:
            read_file_content("/nonexistent/path/file.csv")
            assert False, "不应成功读取不存在的文件"
        except DavinciError as e:
            assert e.code == "E002", f"错误码应为 E002，实际 {e.code}"

        # 不支持的格式
        try:
            parse_data("这不是任何格式的数据")
            assert False, "不应成功解析无效数据"
        except DavinciError as e:
            assert e.code == "E005", f"错误码应为 E005，实际 {e.code}"

        print("[PASS] 错误处理")
    except AssertionError as e:
        print(f"[FAIL] 错误处理: {e}")
        return False

    print("\n所有自检项通过！")
    return True


def main():
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description="davinci - 数据可视化 智能解析 图表生成",
        epilog="示例: python main.py --file data.csv 或 python main.py --url https://example.com/data.json"
    )

    # 输入参数
    input_group = parser.add_mutually_exclusive_group()
    input_group.add_argument("--file", "-f", help="输入文件路径（CSV/JSON）")
    input_group.add_argument("--url", "-u", help="公开数据 URL")
    input_group.add_argument("--files", "-F", nargs="+", help="批量输入文件路径列表")

    # 输出参数
    parser.add_argument("--output", "-o", default="", help="输出 JSON 文件路径（可选）")

    # 功能参数
    parser.add_argument("--pretty", "-p", action="store_true", help="美化 JSON 输出")
    parser.add_argument("--selftest", action="store_true", help="运行内置自检")

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        success = run_selftest()
        sys.exit(0 if success else 1)

    # 校验输入
    if not (args.file or args.url or args.files):
        parser.error("请提供输入: --file, --url 或 --files")

    try:
        # 批量处理模式
        if args.files:
            if len(args.files) < 1:
                raise DavinciError("E001", "批量处理至少需要一个文件")
            result = batch_process(args.files, args.output)
        else:
            # 单文件/URL 模式
            source = args.file or args.url
            processed = process_source(source)

            # 构建输出
            result = {
                "source": source,
                "result": processed,
            }

            # 写入输出文件
            if args.output:
                try:
                    with open(args.output, "w", encoding="utf-8") as f:
                        json.dump(result, f, ensure_ascii=False, indent=2 if args.pretty else None)
                except Exception as e:
                    raise DavinciError("E007", f"输出写入失败: {e}") from e

        # 打印结果
        indent = 2 if args.pretty else None
        print(json.dumps(result, ensure_ascii=False, indent=indent))

    except DavinciError as e:
        print(f"错误 {e.code}: {e.message}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"错误 E010: 未预期的异常: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
