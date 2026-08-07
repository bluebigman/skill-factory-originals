#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py — CanvasXpress 数据分析与可视化 Skill（独立实现）

本脚本依据功能规格独立编写（clean-room 实现），
提供数据解析、图表推荐、审计追踪、批量输出等核心能力。

用法示例：
    python scripts/main.py --selftest          # 离线自检
    python scripts/main.py --input data.csv    # 解析 CSV 并输出审计摘要
    python scripts/main.py --input data.tsv --recommend   # 推荐图表类型
"""

import argparse
import csv
import json
import os
import sys
import tempfile
import traceback
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# 错误码定义（E001-E010）
# ---------------------------------------------------------------------------
ERROR_CODES = {
    "E001": "参数错误：缺少必要参数或参数值非法",
    "E002": "文件不存在或无法访问",
    "E003": "文件格式不支持（仅支持 CSV/TSV/JSON）",
    "E004": "数据解析失败：文件内容格式错误",
    "E005": "数据为空或缺少必要列",
    "E006": "图表推荐失败：无法确定合适的图表类型",
    "E007": "审计日志写入失败",
    "E008": "输出目录不存在或无法创建",
    "E009": "内部逻辑错误（未预期异常）",
    "E010": "自检失败：核心功能未通过验证",
}


def fail(code: str, message: str = None) -> None:
    """抛出带错误码的异常。"""
    msg = message or ERROR_CODES.get(code, "未知错误")
    raise RuntimeError(f"[{code}] {msg}")


# ---------------------------------------------------------------------------
# 数据解析模块
# ---------------------------------------------------------------------------
def parse_csv_tsv(file_path: str, delimiter: str = None) -> list:
    """
    解析 CSV 或 TSV 文件，返回字典列表（每行一个字典）。
    自动识别分隔符（逗号或制表符）。
    """
    try:
        with open(file_path, "r", encoding="utf-8-sig") as f:
            sample = f.read(4096)
            f.seek(0)
            if delimiter is None:
                # 简单启发式：统计逗号和制表符数量
                comma_count = sample.count(",")
                tab_count = sample.count("\t")
                delimiter = "," if comma_count >= tab_count else "\t"
            reader = csv.DictReader(f, delimiter=delimiter)
            rows = [dict(row) for row in reader]
            if not rows:
                fail("E005", "CSV/TSV 文件无数据行")
            return rows
    except FileNotFoundError:
        fail("E002", f"文件不存在: {file_path}")
    except csv.Error as e:
        fail("E004", f"CSV/TSV 解析失败: {e}")
    except Exception as e:
        fail("E009", f"解析文件时发生未预期错误: {e}")


def parse_json(file_path: str) -> list:
    """解析 JSON 文件，支持对象数组或单对象。"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            # 尝试提取常见键（如 data、rows、records）
            for key in ("data", "rows", "records", "items"):
                if key in data and isinstance(data[key], list):
                    return data[key]
            # 单个对象包装为列表
            return [data]
        if isinstance(data, list):
            return data
        fail("E005", "JSON 数据格式不支持（应为对象数组）")
    except FileNotFoundError:
        fail("E002", f"文件不存在: {file_path}")
    except json.JSONDecodeError as e:
        fail("E004", f"JSON 解析失败: {e}")
    except Exception as e:
        fail("E009", f"解析 JSON 时发生未预期错误: {e}")


def load_data(file_path: str) -> list:
    """根据文件扩展名自动选择解析器。"""
    ext = Path(file_path).suffix.lower()
    if ext in (".csv", ".tsv"):
        return parse_csv_tsv(file_path)
    if ext == ".json":
        return parse_json(file_path)
    fail("E003", f"不支持的文件格式: {ext or '无扩展名'}")


# ---------------------------------------------------------------------------
# 字段类型识别与图表推荐
# ---------------------------------------------------------------------------
def infer_field_types(rows: list) -> dict:
    """
    推断每列的数据类型。
    返回 {列名: 'numeric' | 'categorical' | 'datetime' | 'unknown'}
    """
    if not rows:
        return {}
    field_types = {}
    keys = list(rows[0].keys())
    for key in keys:
        # 收集该列的所有非空值
        values = []
        for row in rows:
            val = row.get(key)
            if val is not None and str(val).strip() != "":
                values.append(str(val).strip())
        if not values:
            field_types[key] = "unknown"
            continue
        # 尝试转换为数字
        numeric_count = 0
        for v in values:
            try:
                float(v)
                numeric_count += 1
            except ValueError:
                pass
        if numeric_count == len(values):
            field_types[key] = "numeric"
        else:
            # 简单日期检测
            date_count = 0
            for v in values:
                try:
                    datetime.fromisoformat(v.replace("Z", "+00:00"))
                    date_count += 1
                except ValueError:
                    pass
            if date_count == len(values):
                field_types[key] = "datetime"
            else:
                field_types[key] = "categorical"
    return field_types


def recommend_chart_type(rows: list, field_types: dict = None) -> str:
    """
    根据数据特征推荐图表类型。
    返回推荐结果字符串。
    """
    if not rows:
        fail("E005", "无数据可推荐图表")
    if field_types is None:
        field_types = infer_field_types(rows)

    keys = list(field_types.keys())
    num_cols = sum(1 for v in field_types.values() if v == "numeric")
    cat_cols = sum(1 for v in field_types.values() if v == "categorical")
    date_cols = sum(1 for v in field_types.values() if v == "datetime")

    # 推荐逻辑（宽松规则）
    if num_cols >= 2 and cat_cols >= 1:
        return "散点图（Scatter Plot）"
    if num_cols >= 1 and cat_cols >= 1:
        return "柱状图（Bar Chart）"
    if num_cols >= 2:
        return "折线图（Line Chart）"
    if cat_cols >= 2:
        return "热力图（Heatmap）"
    if date_cols >= 1 and num_cols >= 1:
        return "时间序列图（Time Series）"
    if num_cols == 1:
        return "箱线图（Box Plot）"
    # 兜底
    return "表格视图（Table View）"


# ---------------------------------------------------------------------------
# 审计追踪模块
# ---------------------------------------------------------------------------
class AuditLogger:
    """记录操作日志的简易审计器。"""

    def __init__(self, log_path: str = None):
        self.entries = []
        self.log_path = log_path

    def log(self, action: str, detail: str = "") -> None:
        """记录一条审计日志。"""
        ts = datetime.now(timezone.utc).isoformat()
        entry = {
            "timestamp": ts,
            "action": action,
            "detail": detail,
        }
        self.entries.append(entry)

    def save(self, file_path: str = None) -> str:
        """将审计日志写入文件（JSON 格式），返回文件路径。"""
        target = file_path or self.log_path
        if not target:
            # 默认写入临时目录
            tmp = tempfile.NamedTemporaryFile(
                mode="w", suffix=".json", delete=False, prefix="audit_"
            )
            target = tmp.name
            tmp.close()
        try:
            with open(target, "w", encoding="utf-8") as f:
                json.dump(self.entries, f, ensure_ascii=False, indent=2)
            self.log_path = target
            return target
        except Exception as e:
            fail("E007", f"审计日志写入失败: {e}")

    def summary(self) -> str:
        """返回审计摘要文本。"""
        lines = [f"审计日志共 {len(self.entries)} 条记录："]
        for i, entry in enumerate(self.entries, 1):
            lines.append(f"  {i}. [{entry['timestamp']}] {entry['action']} - {entry['detail']}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# 批量输出模块
# ---------------------------------------------------------------------------
def generate_html_report(rows: list, title: str = "数据分析报告") -> str:
    """
    生成简单的 HTML 数据报告（含表格预览和审计信息占位）。
    返回 HTML 字符串。
    """
    if not rows:
        fail("E005", "无数据可生成报告")
    headers = list(rows[0].keys())
    table_rows = ""
    for row in rows[:20]:  # 最多预览 20 行
        tds = "".join(f"<td>{str(row.get(h, ''))}</td>" for h in headers)
        table_rows += f"<tr>{tds}</tr>\n"
    thead = "".join(f"<th>{h}</th>" for h in headers)
    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>{title}</title>
<style>
body {{ font-family: sans-serif; margin: 2rem; }}
table {{ border-collapse: collapse; width: 100%; }}
th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
th {{ background-color: #f2f2f2; }}
</style>
</head>
<body>
<h1>{title}</h1>
<p>生成时间: {datetime.now().isoformat()}</p>
<p>数据行数: {len(rows)}</p>
<h2>数据预览（前 {min(20, len(rows))} 行）</h2>
<table>
<thead><tr>{thead}</tr></thead>
<tbody>
{table_rows}
</tbody>
</table>
</body>
</html>"""
    return html


def output_batch(rows_list: list, out_dir: str) -> list:
    """
    批量输出多个数据集为 HTML 报告文件。
    返回生成的文件路径列表。
    """
    if not rows_list:
        fail("E005", "无数据可输出")
    out_path = Path(out_dir)
    if not out_path.exists():
        try:
            out_path.mkdir(parents=True, exist_ok=True)
        except Exception:
            fail("E008", f"无法创建输出目录: {out_dir}")
    generated = []
    for idx, rows in enumerate(rows_list, 1):
        title = f"报告_{idx}"
        html = generate_html_report(rows, title)
        file_path = out_path / f"report_{idx}.html"
        try:
            file_path.write_text(html, encoding="utf-8")
            generated.append(str(file_path))
        except Exception as e:
            fail("E008", f"写入报告失败: {e}")
    return generated


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------
def process_data(file_path: str, out_dir: str = None, recommend: bool = False) -> dict:
    """
    核心处理流程：
    1. 加载数据
    2. 推断字段类型
    3. 可选：推荐图表
    4. 生成审计日志
    5. 可选：批量输出
    返回结果字典。
    """
    # 初始化审计
    audit = AuditLogger()
    audit.log("流程启动", f"输入文件: {file_path}")

    # 1. 加载数据
    rows = load_data(file_path)
    audit.log("数据加载", f"共 {len(rows)} 行数据")

    # 2. 字段类型推断
    field_types = infer_field_types(rows)
    type_summary = "; ".join(f"{k}={v}" for k, v in field_types.items())
    audit.log("字段类型识别", type_summary)

    # 3. 可选图表推荐
    recommendation = None
    if recommend:
        recommendation = recommend_chart_type(rows, field_types)
        audit.log("图表推荐", recommendation)

    # 4. 输出目录处理
    output_files = []
    if out_dir:
        output_files = output_batch([rows], out_dir)
        audit.log("批量输出", f"生成 {len(output_files)} 个文件")

    # 5. 保存审计日志
    audit_path = audit.save()
    audit.log("审计保存", audit_path)

    result = {
        "rows_count": len(rows),
        "field_types": field_types,
        "recommendation": recommendation,
        "audit_path": audit_path,
        "output_files": output_files,
        "audit_summary": audit.summary(),
    }
    return result


# ---------------------------------------------------------------------------
# 自检模块（--selftest）
# ---------------------------------------------------------------------------
def run_selftest() -> int:
    """
    离线自检核心逻辑，使用内置硬编码数据。
    返回 0 表示通过，非 0 表示失败。
    """
    print("=== CanvasXpress Skill 自检开始 ===")
    try:
        # --- 测试数据 1：CSV 风格数据（模拟） ---
        rows1 = [
            {"城市": "北京", "销量": "120", "利润": "30"},
            {"城市": "上海", "销量": "150", "利润": "45"},
            {"城市": "广州", "销量": "90", "利润": "20"},
            {"城市": "深圳", "销量": "110", "利润": "35"},
        ]
        # --- 测试数据 2：混合类型 ---
        rows2 = [
            {"日期": "2024-01-01", "温度": "5.2", "湿度": "80"},
            {"日期": "2024-01-02", "温度": "6.1", "湿度": "75"},
            {"日期": "2024-01-03", "温度": "4.8", "湿度": "85"},
        ]
        # --- 测试数据 3：分类数据 ---
        rows3 = [
            {"产品": "A", "地区": "华东"},
            {"产品": "B", "地区": "华南"},
            {"产品": "C", "地区": "华北"},
        ]

        # 1. 测试字段类型推断
        print("[1/5] 测试字段类型推断...")
        ft1 = infer_field_types(rows1)
        assert ft1["销量"] == "numeric", "销量列应为 numeric"
        assert ft1["城市"] == "categorical", "城市列应为 categorical"
        ft2 = infer_field_types(rows2)
        assert ft2["日期"] == "datetime", "日期列应为 datetime"
        assert ft2["温度"] == "numeric", "温度列应为 numeric"
        ft3 = infer_field_types(rows3)
        assert ft3["产品"] == "categorical", "产品列应为 categorical"
        print("     通过")

        # 2. 测试图表推荐
        print("[2/5] 测试图表推荐...")
        rec1 = recommend_chart_type(rows1, ft1)
        assert rec1, "推荐结果不应为空"
        rec2 = recommend_chart_type(rows2, ft2)
        assert rec2, "推荐结果不应为空"
        rec3 = recommend_chart_type(rows3, ft3)
        assert rec3, "推荐结果不应为空"
        print(f"     通过（推荐结果: {rec1} / {rec2} / {rec3}）")

        # 3. 测试审计日志
        print("[3/5] 测试审计日志...")
        audit = AuditLogger()
        audit.log("测试操作", "自检数据")
        audit.log("另一操作", "更多详情")
        assert len(audit.entries) == 2, "审计条目数应为 2"
        summary = audit.summary()
        assert "2 条记录" in summary, "审计摘要应包含记录数"
        # 保存到临时文件
        tmp_path = audit.save()
        assert os.path.exists(tmp_path), "审计文件应已创建"
        os.unlink(tmp_path)  # 清理
        print("     通过")

        # 4. 测试 HTML 报告生成
        print("[4/5] 测试 HTML 报告生成...")
        html = generate_html_report(rows1, "自检报告")
        assert "<table>" in html, "HTML 应包含表格"
        assert "北京" in html, "HTML 应包含数据内容"
        print("     通过")

        # 5. 测试批量输出
        print("[5/5] 测试批量输出...")
        with tempfile.TemporaryDirectory() as tmpdir:
            files = output_batch([rows1, rows2], tmpdir)
            assert len(files) == 2, "应生成 2 个文件"
            for f in files:
                assert os.path.exists(f), f"文件应存在: {f}"
        print("     通过")

        print("=== 自检全部通过 ===")
        return 0

    except Exception as e:
        print(f"自检失败: {e}")
        traceback.print_exc()
        return 1


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------
def main(argv=None) -> int:
    """主入口函数。"""
    parser = argparse.ArgumentParser(
        description="CanvasXpress 数据分析与可视化 Skill（独立实现）",
        epilog="示例: python scripts/main.py --input data.csv --recommend",
    )
    parser.add_argument("--input", "-i", help="输入数据文件（CSV/TSV/JSON）")
    parser.add_argument("--output", "-o", help="输出目录（用于批量 HTML 报告）")
    parser.add_argument("--recommend", "-r", action="store_true", help="推荐图表类型")
    parser.add_argument("--selftest", action="store_true", help="运行离线自检")
    parser.add_argument("--version", action="version", version="canvasxpress 1.0.1")

    args = parser.parse_args(argv)

    # 自检模式
    if args.selftest:
        return run_selftest()

    # 正常处理模式
    if not args.input:
        parser.print_help()
        fail("E001", "必须提供 --input 参数或使用 --selftest")

    try:
        result = process_data(
            file_path=args.input,
            out_dir=args.output,
            recommend=args.recommend,
        )
        # 输出结果摘要
        print(f"数据行数: {result['rows_count']}")
        print(f"字段类型: {result['field_types']}")
        if result["recommendation"]:
            print(f"图表推荐: {result['recommendation']}")
        print(f"审计日志: {result['audit_path']}")
        if result["output_files"]:
            print("输出文件:")
            for f in result["output_files"]:
                print(f"  - {f}")
        print("\n审计摘要:")
        print(result["audit_summary"])
        return 0
    except RuntimeError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"未预期错误: {e}", file=sys.stderr)
        traceback.print_exc()
        fail("E009", str(e))
        return 1


if __name__ == "__main__":
    sys.exit(main())
