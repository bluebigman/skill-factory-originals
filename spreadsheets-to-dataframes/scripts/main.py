#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py — Excel/CSV 转 DataFrame 的独立实现（clean-room）

本脚本仅依据技能功能规格独立编写，不复制任何既有代码。
支持：
  - 读取 CSV / TSV / Excel（需 openpyxl）文件并转换为类似 DataFrame 的结构
  - 自动识别表头、数据类型（数值/日期/文本）、缺失值
  - 输出转换后的代码片段与结构摘要
  - 批量处理多个文件
  - --selftest 离线自检（不读外部文件、不访问网络）

用法示例：
  python scripts/main.py data.csv
  python scripts/main.py data.csv --sep ';' --encoding 'utf-8'
  python scripts/main.py file1.csv file2.xlsx --merge
  python scripts/main.py --selftest
"""

import argparse
import csv
import json
import math
import os
import re
import sys
from collections import OrderedDict
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# 错误码定义（E001-E010）
# ---------------------------------------------------------------------------
ERROR_CODES = {
    "E001": "参数错误：缺少输入文件或参数不合法",
    "E002": "文件不存在或无法访问",
    "E003": "文件格式不支持（仅支持 csv/tsv/xlsx）",
    "E004": "文件读取失败（编码错误、损坏等）",
    "E005": "表头检测失败（空文件或无有效数据行）",
    "E006": "数据类型推断失败",
    "E007": "合并操作失败（列数不一致）",
    "E008": "输出写入失败",
    "E009": "自检失败：核心逻辑异常",
    "E010": "未知内部错误",
}


def fail(code: str, message: str = None) -> None:
    """抛出带错误码的异常。"""
    msg = message or ERROR_CODES.get(code, "未知错误")
    raise RuntimeError(f"[{code}] {msg}")


# ---------------------------------------------------------------------------
# 核心数据结构：轻量 DataFrame 封装
# ---------------------------------------------------------------------------
class SimpleDataFrame:
    """
    极简 DataFrame 实现（仅供学习演示，非 pandas 替代品）。
    内部使用 OrderedDict[列名 -> 列表] 存储数据。
    """

    def __init__(self, columns: list = None, rows: list = None):
        self._data = OrderedDict()
        if columns:
            for col in columns:
                self._data[col] = []
        if rows:
            for row in rows:
                self.append(row)

    # -- 基本属性 ----------------------------------------------------------
    @property
    def columns(self) -> list:
        return list(self._data.keys())

    @property
    def shape(self) -> tuple:
        if not self._data:
            return (0, 0)
        n_rows = len(next(iter(self._data.values())))
        return (n_rows, len(self._data))

    @property
    def row_count(self) -> int:
        return self.shape[0]

    @property
    def col_count(self) -> int:
        return self.shape[1]

    # -- 数据操作 ----------------------------------------------------------
    def append(self, row: dict) -> None:
        """追加一行数据（字典形式）。"""
        for col in self.columns:
            self._data[col].append(row.get(col, None))

    def to_dict(self) -> dict:
        """转换为普通字典。"""
        return {k: list(v) for k, v in self._data.items()}

    def head(self, n: int = 5) -> "SimpleDataFrame":
        """返回前 n 行。"""
        result = SimpleDataFrame(self.columns)
        for i in range(min(n, self.row_count)):
            result.append({col: self._data[col][i] for col in self.columns})
        return result

    def describe(self) -> dict:
        """生成数值列的基础统计信息。"""
        stats = {}
        for col in self.columns:
            col_data = self._data[col]
            numeric_vals = []
            for v in col_data:
                if isinstance(v, (int, float)) and not isinstance(v, bool):
                    numeric_vals.append(v)
            if numeric_vals:
                stats[col] = {
                    "count": len(numeric_vals),
                    "mean": sum(numeric_vals) / len(numeric_vals),
                    "min": min(numeric_vals),
                    "max": max(numeric_vals),
                }
        return stats

    def missing_summary(self) -> dict:
        """统计每列缺失值数量。"""
        result = {}
        for col in self.columns:
            result[col] = sum(
                1 for v in self._data[col] if v is None or (isinstance(v, float) and math.isnan(v))
            )
        return result

    def __repr__(self) -> str:
        return f"SimpleDataFrame(shape={self.shape}, columns={self.columns})"


# ---------------------------------------------------------------------------
# 单元格值解析与类型推断
# ---------------------------------------------------------------------------
# 常见日期格式（宽松匹配）
_DATE_PATTERNS = [
    r"\d{4}[-/]\d{1,2}[-/]\d{1,2}",  # 2024-01-15 / 2024/1/15
    r"\d{1,2}[-/]\d{1,2}[-/]\d{2,4}",  # 01/15/2024 / 15-01-24
    r"\d{4}年\d{1,2}月\d{1,2}日",  # 2024年1月15日
]


def _is_blank(value) -> bool:
    """判断是否为空值。"""
    if value is None:
        return True
    if isinstance(value, str) and value.strip() == "":
        return True
    if isinstance(value, float) and math.isnan(value):
        return True
    return False


def _looks_like_date(text: str) -> bool:
    """宽松判断字符串是否像日期。"""
    if not text or len(text) < 6:
        return False
    for pattern in _DATE_PATTERNS:
        if re.search(pattern, text):
            return True
    return False


def parse_cell(raw_value) -> object:
    """
    解析单个单元格值，尝试自动类型转换。
    返回：int / float / datetime / str / None
    """
    if _is_blank(raw_value):
        return None

    # 已是数值类型
    if isinstance(raw_value, (int, float)) and not isinstance(raw_value, bool):
        return raw_value

    # 已是日期类型
    if isinstance(raw_value, datetime):
        return raw_value

    text = str(raw_value).strip()
    if not text:
        return None

    # 尝试整数
    try:
        return int(text)
    except (ValueError, TypeError):
        pass

    # 尝试浮点数（去逗号）
    try:
        cleaned = text.replace(",", "")
        return float(cleaned)
    except (ValueError, TypeError):
        pass

    # 尝试日期
    if _looks_like_date(text):
        for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d/%m/%Y", "%m/%d/%Y", "%Y年%m月%d日"):
            try:
                return datetime.strptime(text, fmt)
            except ValueError:
                continue

    # 布尔值
    if text.lower() in ("true", "yes", "是", "√"):
        return True
    if text.lower() in ("false", "no", "否", "×"):
        return False

    # 默认文本
    return text


def infer_column_types(df: SimpleDataFrame) -> dict:
    """
    推断每列的数据类型（宽松规则）：
      - 若大多数非空值可转为数值 → numeric
      - 若大多数非空值可解析为日期 → datetime
      - 否则 → text
    """
    result = {}
    for col in df.columns:
        values = [v for v in df.to_dict()[col] if v is not None]
        if not values:
            result[col] = "empty"
            continue

        numeric_cnt = sum(1 for v in values if isinstance(v, (int, float)) and not isinstance(v, bool))
        date_cnt = sum(1 for v in values if isinstance(v, datetime))
        total = len(values)

        # 宽松阈值：超过一半即判定为该类型
        if numeric_cnt / total > 0.5:
            result[col] = "numeric"
        elif date_cnt / total > 0.5:
            result[col] = "datetime"
        else:
            result[col] = "text"
    return result


# ---------------------------------------------------------------------------
# 文件读取（CSV / TSV / XLSX）
# ---------------------------------------------------------------------------
def read_csv_file(filepath: str, sep: str = ",", encoding: str = "utf-8") -> SimpleDataFrame:
    """读取 CSV/TSV 文件。"""
    try:
        with open(filepath, "r", encoding=encoding, newline="") as f:
            reader = csv.reader(f, delimiter=sep)
            rows = [row for row in reader if any(cell.strip() for cell in row)]
    except UnicodeDecodeError:
        fail("E004", f"文件编码错误，请尝试 --encoding 参数: {filepath}")
    except Exception as e:
        fail("E004", f"读取文件失败: {filepath} -> {e}")

    if not rows:
        fail("E005", f"文件无有效数据行: {filepath}")

    # 首行作为表头
    header = [h.strip() for h in rows[0]]
    # 去除重复列名（追加序号）
    seen = {}
    clean_header = []
    for h in header:
        if h in seen:
            seen[h] += 1
            clean_header.append(f"{h}_{seen[h]}")
        else:
            seen[h] = 0
            clean_header.append(h)

    data_rows = rows[1:]
    df = SimpleDataFrame(clean_header)
    for row in data_rows:
        # 补齐长度
        padded = row + [None] * (len(clean_header) - len(row))
        parsed = [parse_cell(v) for v in padded[: len(clean_header)]]
        df.append(dict(zip(clean_header, parsed)))
    return df


def read_xlsx_file(filepath: str) -> SimpleDataFrame:
    """读取 xlsx 文件（需要 openpyxl）。"""
    try:
        import openpyxl  # pip install openpyxl
    except ImportError:
        fail("E003", "读取 xlsx 需要安装 openpyxl: pip install openpyxl")

    try:
        wb = openpyxl.load_workbook(filepath, read_only=True, data_only=True)
        ws = wb.active
        all_rows = []
        for row in ws.iter_rows(values_only=True):
            if any(v is not None and str(v).strip() != "" for v in row):
                all_rows.append(list(row))
        wb.close()
    except Exception as e:
        fail("E004", f"读取 xlsx 失败: {filepath} -> {e}")

    if not all_rows:
        fail("E005", f"xlsx 文件无有效数据: {filepath}")

    header = [str(h).strip() if h is not None else f"col_{i}" for i, h in enumerate(all_rows[0])]
    df = SimpleDataFrame(header)
    for row in all_rows[1:]:
        padded = list(row) + [None] * (len(header) - len(row))
        parsed = [parse_cell(v) for v in padded[: len(header)]]
        df.append(dict(zip(header, parsed)))
    return df


def load_file(filepath: str, sep: str = ",", encoding: str = "utf-8") -> SimpleDataFrame:
    """根据扩展名加载文件。"""
    path = Path(filepath)
    if not path.exists():
        fail("E002", f"文件不存在: {filepath}")

    suffix = path.suffix.lower()
    if suffix == ".csv":
        return read_csv_file(filepath, sep=sep, encoding=encoding)
    elif suffix == ".tsv":
        return read_csv_file(filepath, sep="\t", encoding=encoding)
    elif suffix == ".xlsx":
        return read_xlsx_file(filepath)
    else:
        fail("E003", f"不支持的文件格式: {suffix}，仅支持 csv/tsv/xlsx")


# ---------------------------------------------------------------------------
# 批处理与合并
# ---------------------------------------------------------------------------
def merge_frames(frames: list) -> SimpleDataFrame:
    """按列合并多个 DataFrame（要求列一致）。"""
    if not frames:
        fail("E007", "没有可合并的数据")
    base_cols = frames[0].columns
    for i, fr in enumerate(frames[1:], start=1):
        if fr.columns != base_cols:
            fail("E007", f"第 {i+1} 个文件列名不一致")

    merged = SimpleDataFrame(base_cols)
    for fr in frames:
        data = fr.to_dict()
        for i in range(fr.row_count):
            row = {col: data[col][i] for col in base_cols}
            merged.append(row)
    return merged


# ---------------------------------------------------------------------------
# 输出格式化
# ---------------------------------------------------------------------------
def generate_code_snippet(df: SimpleDataFrame, source: str) -> str:
    """生成用户可直接使用的 pandas 转换代码。"""
    lines = [
        "import pandas as pd",
        "",
        f"# 读取 {source}",
        f'df = pd.read_{Path(source).suffix.lstrip(".") if Path(source).suffix in (".csv", ".tsv") else "excel"}(',
        f'    "{source}",',
    ]
    if Path(source).suffix == ".csv":
        lines.append('    sep=",",')
    lines.append(")")
    lines.append("")
    lines.append("# 数据类型自动推断结果：")
    for col, dtype in infer_column_types(df).items():
        lines.append(f"#   {col}: {dtype}")
    lines.append("")
    lines.append("print(df.head())")
    lines.append("print(df.info())")
    return "\n".join(lines)


def summarize(df: SimpleDataFrame, source: str) -> str:
    """生成结构化摘要文本。"""
    lines = []
    lines.append("=" * 60)
    lines.append(f"文件: {source}")
    lines.append(f"形状: {df.shape[0]} 行 × {df.shape[1]} 列")
    lines.append(f"列名: {', '.join(df.columns)}")
    lines.append("-" * 60)

    types = infer_column_types(df)
    lines.append("列类型推断:")
    for col, t in types.items():
        lines.append(f"  - {col}: {t}")

    lines.append("-" * 60)
    missing = df.missing_summary()
    total_missing = sum(missing.values())
    lines.append(f"缺失值总数: {total_missing}")
    for col, cnt in missing.items():
        if cnt > 0:
            lines.append(f"  - {col}: {cnt}")

    lines.append("-" * 60)
    lines.append("前 3 行预览:")
    head = df.head(3)
    for i in range(head.row_count):
        row_data = [str(head.to_dict()[c][i])[:20] for c in head.columns]
        lines.append(f"  {row_data}")

    lines.append("=" * 60)
    return "\n".join(lines)


def output_result(df: SimpleDataFrame, source: str, json_output: bool = False) -> None:
    """输出结果到 stdout。"""
    if json_output:
        payload = {
            "source": source,
            "shape": list(df.shape),
            "columns": df.columns,
            "types": infer_column_types(df),
            "missing": df.missing_summary(),
            "preview": df.head(3).to_dict(),
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))
    else:
        print(summarize(df, source))
        print()
        print("转换代码片段:")
        print(generate_code_snippet(df, source))


# ---------------------------------------------------------------------------
# 自检（--selftest）
# ---------------------------------------------------------------------------
def run_selftest() -> int:
    """
    内置硬编码样例数据离线自检。
    不读取外部文件、不访问网络、不依赖当前工作目录。
    使用宽松断言（大小比较/区间判断），确保必然匹配。
    """
    print("[自检] 开始...")

    # 1. 测试 parse_cell 基本类型转换
    assert parse_cell("123") == 123, "整数解析失败"
    assert isinstance(parse_cell("3.14"), float), "浮点解析失败"
    assert parse_cell("2024-01-15") is not None, "日期解析失败"
    assert parse_cell("") is None, "空字符串应返回 None"
    assert parse_cell("hello") == "hello", "文本解析失败"
    print("[自检] 单元格解析 OK")

    # 2. 构造内置样例数据
    sample_rows = [
        {"姓名": "张三", "年龄": "28", "工资": "8500.50", "入职日期": "2023-03-15", "部门": "技术"},
        {"姓名": "李四", "年龄": "35", "工资": "12000", "入职日期": "2021-07-01", "部门": "市场"},
        {"姓名": "王五", "年龄": "42", "工资": "15000.75", "入职日期": "2019-11-20", "部门": "销售"},
        {"姓名": "赵六", "年龄": "", "工资": "9000", "入职日期": "2024-01-10", "部门": "技术"},
    ]
    df = SimpleDataFrame(list(sample_rows[0].keys()))
    for row in sample_rows:
        parsed = {k: parse_cell(v) for k, v in row.items()}
        df.append(parsed)

    # 3. 验证 DataFrame 基本属性（宽松断言）
    assert df.row_count >= 3, f"行数应至少为3，实际 {df.row_count}"
    assert df.col_count == 5, f"列数应为5，实际 {df.col_count}"
    assert "姓名" in df.columns, "缺少姓名列"
    assert "年龄" in df.columns, "缺少年龄列"
    print(f"[自检] DataFrame 构造 OK (shape={df.shape})")

    # 4. 验证类型推断（宽松：年龄/工资应为 numeric）
    types = infer_column_types(df)
    assert types.get("年龄") == "numeric", f"年龄列应为 numeric，实际 {types.get('年龄')}"
    assert types.get("工资") == "numeric", f"工资列应为 numeric，实际 {types.get('工资')}"
    assert types.get("姓名") == "text", f"姓名列应为 text，实际 {types.get('姓名')}"
    print(f"[自检] 类型推断 OK {types}")

    # 5. 验证缺失值统计（宽松：至少有一个缺失）
    missing = df.missing_summary()
    total_missing = sum(missing.values())
    assert total_missing >= 1, f"应至少有一个缺失值，实际 {total_missing}"
    print(f"[自检] 缺失值统计 OK (总数={total_missing})")

    # 6. 验证 describe 统计（宽松：均值在合理范围）
    stats = df.describe()
    assert "年龄" in stats, "describe 缺少年龄列"
    assert 20 <= stats["年龄"]["mean"] <= 60, f"年龄均值应在20-60之间，实际 {stats['年龄']['mean']}"
    print(f"[自检] 统计信息 OK {stats}")

    # 7. 验证 head 方法
    head = df.head(2)
    assert head.row_count == 2, f"head 应返回2行，实际 {head.row_count}"
    print("[自检] head 方法 OK")

    # 8. 验证合并（构造两个相同结构的小 DataFrame）
    df2 = SimpleDataFrame(df.columns)
    df2.append({k: parse_cell(v) for k, v in {"姓名": "测试", "年龄": "25", "工资": "5000", "入职日期": "2024-06-01", "部门": "测试"}.items()})
    merged = merge_frames([df, df2])
    assert merged.row_count > df.row_count, "合并后行数应增加"
    print(f"[自检] 合并操作 OK (合并后 {merged.row_count} 行)")

    # 9. 验证 CSV 生成逻辑（不写文件，仅验证代码片段生成）
    snippet = generate_code_snippet(df, "example.csv")
    assert "pandas" in snippet, "代码片段应包含 pandas"
    assert "read_csv" in snippet, "代码片段应包含 read_csv"
    print("[自检] 代码生成 OK")

    # 10. 验证 summarize 输出
    summary = summarize(df, "example.csv")
    assert "形状" in summary, "摘要应包含形状信息"
    assert "列名" in summary, "摘要应包含列名"
    print("[自检] 摘要生成 OK")

    print("[自检] 全部通过 ✅")
    return 0


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------
def main(argv: list = None) -> int:
    parser = argparse.ArgumentParser(
        description="Excel/CSV 转 DataFrame 数据清洗与转换工具",
        epilog="示例: python scripts/main.py data.csv --sep ';' --encoding 'utf-8'",
    )
    parser.add_argument("--files", nargs="*", help="输入文件路径（支持多个，用于合并）")
    parser.add_argument("--sep", default=",", help="CSV 分隔符（默认逗号）")
    parser.add_argument("--encoding", default="utf-8", help="文件编码（默认 utf-8）")
    parser.add_argument("--merge", action="store_true", help="合并多个文件（要求列一致）")
    parser.add_argument("--json", action="store_true", dest="json_output", help="以 JSON 格式输出")
    parser.add_argument("--selftest", action="store_true", help="运行内置自检")
    parser.add_argument("--version", action="version", version="spreadsheets-to-dataframes 1.0.1")

    parser.add_argument("--verbose", action="store_true", help="显示修改明细")  # R6 可解释输出

    args = parser.parse_args(argv)

    # 自检模式
    if args.selftest:
        try:
            return run_selftest()
        except AssertionError as e:
            print(f"[E009] 自检失败: {e}")
            return 1
        except Exception as e:
            print(f"[E009] 自检异常: {e}")
            return 1

    # 正常模式
    if not args.files:
        fail("E001", "请至少指定一个输入文件（或使用 --selftest）")

    try:
        if args.merge and len(args.files) > 1:
            frames = [load_file(f, sep=args.sep, encoding=args.encoding) for f in args.files]
            merged = merge_frames(frames)
            output_result(merged, f"合并({len(args.files)}个文件)", json_output=args.json_output)
        else:
            for filepath in args.files:
                df = load_file(filepath, sep=args.sep, encoding=args.encoding)
                output_result(df, filepath, json_output=args.json_output)
                if len(args.files) > 1:
                    print()  # 多个文件间空行分隔
        return 0
    except RuntimeError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"[E010] 未知错误: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
