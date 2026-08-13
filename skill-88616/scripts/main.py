#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
反欺诈识别与风险分析工具 - 独立实现脚本

本脚本依据功能规格独立实现，用于反欺诈场景的批量数据处理：
识别、整理、生成与校验，输出可直接使用的结果文件。

仅使用 Python 标准库，无第三方依赖。
"""

import argparse
import csv
import json
import math
import os
import sys
import time
import traceback
from collections import Counter
from datetime import datetime
from pathlib import Path

# ============================================================
# 错误码定义
# ============================================================
ERROR_CODES = {
    "E001": "文件格式不支持，仅支持 CSV、Excel、JSON 格式",
    "E002": "未找到唯一标识字段（id 或 order_no）",
    "E003": "规则 JSON 解析失败，请检查语法",
    "E004": "数据量过大，建议分片或增加内存",
    "E005": "分片处理失败，已回退至单线程",
    "E006": "输出目录无权限，无法写入结果文件",
    "E007": "输入文件不存在或无法读取",
    "E008": "输入参数校验失败",
    "E009": "数据解析失败，请检查文件内容格式",
    "E010": "内部逻辑错误，请联系开发者",
}

# ============================================================
# 内置默认规则集
# ============================================================
DEFAULT_RULES = {
    "rules": [
        {
            "name": "金额异常波动",
            "field": "amount",
            "operator": "gt",
            "threshold": 100000,
            "logic": "or",
            "weight": 0.4,
        },
        {
            "name": "高频交易检测",
            "field": "transaction_count",
            "operator": "gt",
            "threshold": 50,
            "logic": "or",
            "weight": 0.3,
        },
        {
            "name": "短时多地登录",
            "field": "login_count",
            "operator": "gt",
            "threshold": 5,
            "logic": "or",
            "weight": 0.2,
        },
        {
            "name": "设备指纹异常",
            "field": "device_count",
            "operator": "gt",
            "threshold": 3,
            "logic": "or",
            "weight": 0.1,
        },
    ],
    "risk_levels": {"high": 80, "medium": 50, "low": 0},
}

# ============================================================
# 字段映射表（中文 -> 英文）
# ============================================================
FIELD_ALIASES = {
    "手机号": "phone",
    "手机号码": "phone",
    "电话": "phone",
    "金额": "amount",
    "交易金额": "amount",
    "用户id": "user_id",
    "用户ID": "user_id",
    "用户编号": "user_id",
    "订单号": "order_no",
    "订单编号": "order_no",
    "交易次数": "transaction_count",
    "登录次数": "login_count",
    "设备数": "device_count",
    "设备数量": "device_count",
    "时间": "timestamp",
    "日期": "timestamp",
    "时间戳": "timestamp",
}


# ============================================================
# 输入校验
# ============================================================
def validate_input_file(file_path):
    """校验输入文件是否存在且格式支持。"""
    if not file_path:
        raise ValueError(f"E008: {ERROR_CODES['E008']} - 未提供输入文件路径")
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"E007: {ERROR_CODES['E007']} - {file_path}")
    if not path.is_file():
        raise ValueError(f"E007: {ERROR_CODES['E007']} - {file_path} 不是文件")
    ext = path.suffix.lower()
    if ext not in (".csv", ".json", ".xlsx"):
        raise ValueError(f"E001: {ERROR_CODES['E001']} - 文件后缀为 {ext}")
    return path


def validate_rules_file(rules_path):
    """校验规则文件是否存在且为合法 JSON。"""
    if not rules_path:
        return None
    path = Path(rules_path)
    if not path.exists():
        raise FileNotFoundError(f"E007: {ERROR_CODES['E007']} - 规则文件 {rules_path}")
    try:
        with open(path, "r", encoding="utf-8") as f:
            rules = json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"E003: {ERROR_CODES['E003']} - 第 {e.lineno} 行: {e.msg}")
    except UnicodeDecodeError:
        # 尝试 GBK 编码
        try:
            with open(path, "r", encoding="gbk") as f:
                rules = json.load(f)
        except Exception as e:
            raise ValueError(f"E003: {ERROR_CODES['E003']} - 编码解析失败: {e}")
    return rules


def validate_output_dir(output_dir):
    """校验输出目录是否存在或可创建。"""
    if not output_dir:
        return Path.cwd()
    path = Path(output_dir)
    if not path.exists():
        try:
            path.mkdir(parents=True, exist_ok=True)
        except PermissionError:
            raise PermissionError(f"E006: {ERROR_CODES['E006']} - {output_dir}")
    if not os.access(path, os.W_OK):
        raise PermissionError(f"E006: {ERROR_CODES['E006']} - {output_dir}")
    return path


# ============================================================
# 数据加载与清洗
# ============================================================
def read_csv_with_encoding(file_path):
    """读取 CSV 文件，支持多编码 fallback。"""
    encodings = ["utf-8", "gbk", "gb18030"]
    for enc in encodings:
        try:
            with open(file_path, "r", encoding=enc, newline="") as f:
                reader = csv.DictReader(f)
                rows = [dict(row) for row in reader]
                if rows:
                    return rows, reader.fieldnames
        except (UnicodeDecodeError, csv.Error):
            continue
    # 最后尝试 errors="replace"
    try:
        with open(file_path, "r", encoding="utf-8", errors="replace", newline="") as f:
            reader = csv.DictReader(f)
            rows = [dict(row) for row in reader]
            return rows, reader.fieldnames
    except Exception as e:
        raise ValueError(f"E009: {ERROR_CODES['E009']} - CSV 解析失败: {e}")


def read_json_with_encoding(file_path):
    """读取 JSON 文件，支持多编码 fallback。"""
    encodings = ["utf-8", "gbk", "gb18030"]
    for enc in encodings:
        try:
            with open(file_path, "r", encoding=enc) as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
                if isinstance(data, dict) and "data" in data:
                    return data["data"]
                raise ValueError("JSON 顶层必须是数组或包含 data 字段的对象")
        except (UnicodeDecodeError, json.JSONDecodeError):
            continue
    raise ValueError(f"E009: {ERROR_CODES['E009']} - JSON 解析失败")


def load_data(file_path):
    """根据文件扩展名加载数据。"""
    ext = Path(file_path).suffix.lower()
    if ext == ".csv":
        rows, fieldnames = read_csv_with_encoding(file_path)
        return rows, fieldnames
    elif ext == ".json":
        rows = read_json_with_encoding(file_path)
        if not rows:
            return [], []
        return rows, list(rows[0].keys())
    elif ext == ".xlsx":
        # 简化处理：提示不支持，实际可用 pandas 但为保持零依赖，此处报错
        raise ValueError(f"E001: {ERROR_CODES['E001']} - Excel 支持需要 pandas，请转换为 CSV 或 JSON")
    else:
        raise ValueError(f"E001: {ERROR_CODES['E001']}")


def normalize_field_names(rows):
    """标准化字段名：中文映射为英文，统一小写。"""
    normalized_rows = []
    for row in rows:
        new_row = {}
        for key, value in row.items():
            clean_key = key.strip().lower()
            mapped_key = FIELD_ALIASES.get(clean_key, clean_key)
            new_row[mapped_key] = value
        normalized_rows.append(new_row)
    return normalized_rows


def clean_numeric(value):
    """清洗数值字段：去除千分位逗号，转换为 float。"""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    str_val = str(value).strip().replace(",", "")
    try:
        return float(str_val)
    except ValueError:
        return None


def normalize_timestamp(value):
    """统一日期格式为 YYYY-MM-DD HH:mm:ss。"""
    if value is None:
        return None
    str_val = str(value).strip()
    if not str_val:
        return None
    # 尝试多种格式
    formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
        "%Y/%m/%d %H:%M:%S",
        "%Y/%m/%d",
        "%Y%m%d",
    ]
    for fmt in formats:
        try:
            dt = datetime.strptime(str_val, fmt)
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            continue
    return f"[需核实:日期格式] {str_val}"


def clean_data(rows):
    """数据清洗：字段对齐、类型转换、缺失值标记。"""
    cleaned_rows = []
    for row in rows:
        new_row = dict(row)
        # 统一标识字段
        if "id" not in new_row and "order_no" in new_row:
            new_row["id"] = new_row["order_no"]
        if "order_no" not in new_row and "id" in new_row:
            new_row["order_no"] = new_row["id"]
        # 数值字段清洗
        for num_field in ["amount", "transaction_count", "login_count", "device_count"]:
            if num_field in new_row:
                val = clean_numeric(new_row[num_field])
                if val is None:
                    new_row[num_field] = f"[需核实:{num_field}]"
                else:
                    new_row[num_field] = val
        # 时间字段清洗
        if "timestamp" in new_row:
            new_row["timestamp"] = normalize_timestamp(new_row["timestamp"])
        # 关键字段缺失标记
        for key_field in ["amount", "user_id"]:
            if key_field not in new_row or new_row[key_field] is None or str(new_row[key_field]).strip() == "":
                new_row[key_field] = f"[需核实:{key_field}]"
        cleaned_rows.append(new_row)
    return cleaned_rows


# ============================================================
# 规则评估
# ============================================================
def evaluate_operator(operator, field_value, threshold):
    """执行单个操作符比较。"""
    if operator == "eq":
        return field_value == threshold
    elif operator == "neq":
        return field_value != threshold
    elif operator == "gt":
        return field_value > threshold
    elif operator == "gte":
        return field_value >= threshold
    elif operator == "lt":
        return field_value < threshold
    elif operator == "lte":
        return field_value <= threshold
    elif operator == "in":
        return field_value in threshold if isinstance(threshold, list) else False
    elif operator == "contains":
        return str(threshold) in str(field_value)
    return False


def evaluate_single_rule(rule, row):
    """评估单条规则是否命中。"""
    field = rule.get("field", "")
    operator = rule.get("operator", "eq")
    threshold = rule.get("threshold", 0)
    field_value = row.get(field)
    if field_value is None:
        return False, f"[需核实:规则字段]"
    if isinstance(field_value, str) and field_value.startswith("[需核实"):
        return False, field_value
    try:
        if operator in ("gt", "gte", "lt", "lte"):
            if isinstance(field_value, str):
                field_value = clean_numeric(field_value)
            if field_value is None:
                return False, "[需核实:数值]"
            threshold = float(threshold)
        result = evaluate_operator(operator, field_value, threshold)
        return result, None
    except (TypeError, ValueError):
        return False, "[需核实:类型]"


def evaluate_rules(rows, rules_config):
    """对每条记录执行规则评估，计算风险分。"""
    rules = rules_config.get("rules", [])
    risk_levels = rules_config.get("risk_levels", {"high": 80, "medium": 50, "low": 0})
    results = []
    for row in rows:
        new_row = dict(row)
        hit_rules = []
        total_score = 0.0
        total_weight = 0.0
        for rule in rules:
            hit, warning = evaluate_single_rule(rule, row)
            rule_name = rule.get("name", "未命名规则")
            new_row[f"rule_{rule_name}"] = "命中" if hit else "未命中"
            if hit:
                hit_rules.append(rule_name)
                weight = float(rule.get("weight", 0.1))
                total_score += 100 * weight
                total_weight += weight
        # 归一化风险分
        if total_weight > 0:
            risk_score = min(100, int(total_score / total_weight))
        else:
            risk_score = 0
        new_row["risk_score"] = risk_score
        # 风险等级
        if risk_score >= risk_levels.get("high", 80):
            new_row["risk_level"] = "高"
        elif risk_score >= risk_levels.get("medium", 50):
            new_row["risk_level"] = "中"
        else:
            new_row["risk_level"] = "低"
        new_row["hit_rules"] = "|".join(hit_rules) if hit_rules else ""
        results.append(new_row)
    return results


# ============================================================
# 分片处理
# ============================================================
def split_chunks(data, chunk_size=5000):
    """将数据按指定大小分片。"""
    for i in range(0, len(data), chunk_size):
        yield data[i : i + chunk_size]


def process_chunk(chunk, rules_config):
    """处理单个分片。"""
    return evaluate_rules(chunk, rules_config)


# ============================================================
# 输出格式化
# ============================================================
def format_summary(results, chunk_count, elapsed, output_dir):
    """生成汇总统计信息。"""
    total = len(results)
    risk_counter = Counter()
    rule_counter = Counter()
    for row in results:
        risk_counter[row.get("risk_level", "低")] += 1
        hit_rules = row.get("hit_rules", "")
        if hit_rules:
            for rule_name in hit_rules.split("|"):
                rule_counter[rule_name] += 1
    summary = {
        "处理总量": total,
        "分片数": chunk_count,
        "风险分布": dict(risk_counter),
        "规则命中统计": dict(rule_counter),
        "耗时(秒)": round(elapsed, 2),
        "输出目录": str(output_dir),
        "生成时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    return summary


def write_results(results, summary, output_dir, dry):
    """写入结果文件。"""
    if dry:
        print(f"[DRY-RUN] 将写入以下文件到 {output_dir}:")
        print(f"  - fraud_analysis_summary.json")
        print(f"  - result_part_001.csv")
        print("[DRY-RUN] 未实际写入任何文件")
        return
    try:
        # 写入汇总 JSON
        summary_path = Path(output_dir) / "fraud_analysis_summary.json"
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        # 写入分片结果 CSV
        if results:
            fieldnames = list(results[0].keys())
            result_path = Path(output_dir) / "result_part_001.csv"
            with open(result_path, "w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(results)
        print(f"结果已写入: {output_dir}")
    except PermissionError:
        raise PermissionError(f"E006: {ERROR_CODES['E006']} - {output_dir}")


# ============================================================
# 校验报告
# ============================================================
def generate_validation_report(results, original_rows):
    """生成数据质量校验报告。"""
    issues = []
    # 检查缺失值
    for i, row in enumerate(results):
        for key, value in row.items():
            if isinstance(value, str) and value.startswith("[需核实"):
                issues.append(f"第{i+1}行字段[{key}]存在缺失或异常: {value}")
    # 检查唯一标识
    ids = [row.get("id", row.get("order_no", "")) for row in results]
    if not any(ids):
        issues.append("未找到唯一标识字段(id/order_no)")
    report_lines = [
        "# 数据校验报告",
        "",
        f"检查时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"总记录数: {len(results)}",
        f"发现异常: {len(issues)} 项",
        "",
        "## 异常清单",
        "",
    ]
    if issues:
        for issue in issues[:50]:  # 最多显示 50 条
            report_lines.append(f"- {issue}")
        if len(issues) > 50:
            report_lines.append(f"- ... 等 {len(issues) - 50} 项未显示")
    else:
        report_lines.append("- 无异常")
    report_lines.append("")
    report_lines.append("## 修正建议")
    report_lines.append("")
    report_lines.append("- 对标记为 [需核实] 的字段，请确认原始数据后重新处理")
    report_lines.append("- 确保唯一标识字段(id/order_no)不为空")
    report_lines.append("- 数值字段建议使用标准格式，避免千分位逗号")
    return "\n".join(report_lines)


# ============================================================
# 核心处理流程
# ============================================================
def process_fraud_analysis(file_path, rules_path=None, output_dir=None, dry=False, verbose=False):
    """主处理流程：加载 -> 清洗 -> 评估 -> 输出。"""
    start_time = time.time()
    # 1. 输入校验
    input_path = validate_input_file(file_path)
    rules_config = validate_rules_file(rules_path) if rules_path else DEFAULT_RULES
    out_dir = validate_output_dir(output_dir)
    # 2. 加载数据
    rows, fieldnames = load_data(str(input_path))
    if not rows:
        raise ValueError(f"E009: {ERROR_CODES['E009']} - 文件为空或无数据")
    if len(rows) > 100000:
        raise ValueError(f"E004: {ERROR_CODES['E004']} - 当前 {len(rows)} 条，超过上限")
    # 3. 字段标准化与清洗
    normalized = normalize_field_names(rows)
    cleaned = clean_data(normalized)
    if verbose:
        print(f"[VERBOSE] 加载 {len(cleaned)} 条记录")
        print(f"[VERBOSE] 字段: {list(cleaned[0].keys())}")
    # 4. 规则评估（分片处理）
    all_results = []
    chunk_count = 0
    for chunk in split_chunks(cleaned, chunk_size=5000):
        chunk_count += 1
        try:
            chunk_results = process_chunk(chunk, rules_config)
            all_results.extend(chunk_results)
            if verbose:
                print(f"[VERBOSE] 分片 {chunk_count} 处理完成: {len(chunk_results)} 条")
        except Exception as e:
            print(f"E005: {ERROR_CODES['E005']} - {e}", file=sys.stderr)
            # 回退到单线程逐条处理
            chunk_results = []
            for row in chunk:
                chunk_results.extend(evaluate_rules([row], rules_config))
            all_results.extend(chunk_results)
    # 5. 生成汇总与校验报告
    elapsed = time.time() - start_time
    summary = format_summary(all_results, chunk_count, elapsed, out_dir)
    validation_report = generate_validation_report(all_results, cleaned)
    if verbose:
        print(f"[VERBOSE] 风险分布: {summary['风险分布']}")
        print(f"[VERBOSE] 规则命中: {summary['规则命中统计']}")
    # 6. 输出
    write_results(all_results, summary, out_dir, dry)
    # 写入校验报告
    if not dry:
        report_path = Path(out_dir) / "validation_report.md"
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(validation_report)
    return summary, all_results


# ============================================================
# 自检模块
# ============================================================
def run_selftest():
    """内置硬编码样例数据自检核心逻辑。"""
    print("=" * 60)
    print("开始自检 (selftest)")
    print("=" * 60)
    # 样例数据 1：正常数据
    sample_rows = [
        {"id": "1", "amount": "100.50", "transaction_count": "10", "login_count": "2", "device_count": "1"},
        {"id": "2", "amount": "200000", "transaction_count": "100", "login_count": "10", "device_count": "5"},
        {"id": "3", "amount": "50", "transaction_count": "5", "login_count": "1", "device_count": "1"},
        {"id": "4", "amount": "1,000,000", "transaction_count": "200", "login_count": "20", "device_count": "8"},
    ]
    # 测试 1：字段标准化
    normalized = normalize_field_names(sample_rows)
    assert len(normalized) == 4, "字段标准化失败"
    assert "amount" in normalized[0], "金额字段映射失败"
    print("[PASS] 字段标准化")
    # 测试 2：数据清洗
    cleaned = clean_data(normalized)
    assert cleaned[1]["amount"] == 200000.0, "数值清洗失败"
    assert cleaned[3]["amount"] == 1000000.0, "千分位清洗失败"
    print("[PASS] 数据清洗")
    # 测试 3：规则评估
    results = evaluate_rules(cleaned, DEFAULT_RULES)
    assert len(results) == 4, "规则评估数量错误"
    # 风险分应在 0-100 之间
    for row in results:
        assert 0 <= row["risk_score"] <= 100, "风险分超出范围"
    # 高风险记录应存在
    high_risk = [r for r in results if r["risk_level"] == "高"]
    assert len(high_risk) >= 1, "应至少有一条高风险记录"
    print("[PASS] 规则评估")
    # 测试 4：分片
    chunks = list(split_chunks(cleaned, chunk_size=2))
    assert len(chunks) == 2, "分片数量错误"
    assert len(chunks[0]) == 2, "分片大小错误"
    print("[PASS] 分片处理")
    # 测试 5：中文标点与编码
    chinese_row = [{"id": "5", "金额": "88.8", "交易次数": "3", "登录次数": "1", "设备数": "1"}]
    norm_cn = normalize_field_names(chinese_row)
    assert "amount" in norm_cn[0], "中文字段映射失败"
    print("[PASS] 中文字段映射")
    # 测试 6：空输入
    empty_result = evaluate_rules([], DEFAULT_RULES)
    assert empty_result == [], "空输入应返回空列表"
    print("[PASS] 空输入处理")
    # 测试 7：缺失值标记
    missing_row = [{"id": "6", "amount": "", "transaction_count": "1"}]
    norm_missing = normalize_field_names(missing_row)
    clean_missing = clean_data(norm_missing)
    assert str(clean_missing[0]["amount"]).startswith("[需核实"), "缺失值未标记"
    print("[PASS] 缺失值标记")
    # 测试 8：超长输入（模拟 10000 条）
    big_data = []
    for i in range(10000):
        big_data.append({"id": str(i), "amount": str(i * 10), "transaction_count": "5"})
    norm_big = normalize_field_names(big_data)
    clean_big = clean_data(norm_big)
    big_results = evaluate_rules(clean_big, DEFAULT_RULES)
    assert len(big_results) == 10000, "大数据处理失败"
    print("[PASS] 大数据处理 (10000条)")
    # 测试 9：汇总统计
    summary = format_summary(results, 1, 0.1, Path("."))
    assert summary["处理总量"] == 4, "汇总统计失败"
    assert "风险分布" in summary, "风险分布缺失"
    print("[PASS] 汇总统计")
    # 测试 10：校验报告
    report = generate_validation_report(results, cleaned)
    assert "校验报告" in report, "校验报告生成失败"
    print("[PASS] 校验报告")
    print("=" * 60)
    print("所有自检通过！")
    print("=" * 60)
    return 0


# ============================================================
# CLI 入口
# ============================================================
def main():
    """命令行入口。"""
    parser = argparse.ArgumentParser(
        description="反欺诈识别与风险分析工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python main.py data.csv                          # 使用默认规则处理
  python main.py data.csv -r rules.json            # 使用自定义规则
  python main.py data.csv -o output/               # 指定输出目录
  python main.py data.csv --dry-run                # 预览不写盘
  python main.py data.csv --verbose                # 显示处理明细
  python main.py --selftest                        # 运行自检
        """,
    )
    parser.add_argument("file", nargs="?", help="输入数据文件 (CSV/JSON)")
    parser.add_argument("-r", "--rules", help="自定义规则 JSON 文件")
    parser.add_argument("-o", "--output", help="输出目录")
    parser.add_argument("--dry-run", action="store_true", help="预览模式，不写盘")
    parser.add_argument("--force", action="store_true", help="强制执行写盘（需配合 --dry-run 使用）")
    parser.add_argument("--verbose", action="store_true", help="显示处理明细")
    parser.add_argument("--selftest", action="store_true", help="运行内置自检")
    parser.add_argument("--version", action="version", version="反欺诈工具 1.0.1")
    args = parser.parse_args()
    # 自检模式
    if args.selftest:
        try:
            return run_selftest()
        except AssertionError as e:
            print(f"自检失败: {e}", file=sys.stderr)
            return 1
    # 正常模式
    if not args.file:
        parser.print_help()
        return 1
    # dry-run 与 force 逻辑
    dry = args.dry_run and not args.force
    try:
        summary, _ = process_fraud_analysis(
            file_path=args.file,
            rules_path=args.rules,
            output_dir=args.output,
            dry=dry,
            verbose=args.verbose,
        )
        if dry:
            print("\n[DRY-RUN] 预览完成，未写入任何文件。")
            print("[DRY-RUN] 如需实际写入，请添加 --force 参数。")
        else:
            print(f"\n处理完成！")
            print(f"总记录数: {summary['处理总量']}")
            print(f"分片数: {summary['分片数']}")
            print(f"风险分布: {summary['风险分布']}")
            print(f"耗时: {summary['耗时(秒)']} 秒")
        return 0
    except (ValueError, FileNotFoundError, PermissionError) as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"E010: {ERROR_CODES['E010']} - {e}", file=sys.stderr)
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
