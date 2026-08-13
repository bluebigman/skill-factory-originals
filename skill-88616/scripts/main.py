#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
反欺诈识别与风险分析工具 - 独立实现脚本

本脚本依据功能规格独立实现，提供反欺诈数据处理的完整流程：
数据加载、字段对齐、规则评估、风险评分、分片处理、汇总统计与校验报告。

仅依赖 Python 标准库，无需安装第三方包。

用法示例:
    python main.py --input data.csv --output results/
    python main.py --input data.json --rules custom_rules.json --verbose
    python main.py --selftest
    python main.py --version
"""

import argparse
import csv
import json
import math
import os
import re
import sys
import time
import traceback
from collections import Counter
from datetime import datetime
from pathlib import Path

# ============================================================
# 常量定义
# ============================================================

SUPPORTED_EXTENSIONS = {".csv", ".json"}
DEFAULT_CHUNK_SIZE = 5000
MAX_RECORDS_LIMIT = 100000
DEFAULT_RULES = {
    "rules": [
        {
            "name": "金额异常波动",
            "field": "amount",
            "operator": "gt",
            "threshold": 100000,
            "logic": "or",
            "weight": 0.4
        },
        {
            "name": "高频交易检测",
            "field": "transaction_count",
            "operator": "gt",
            "threshold": 50,
            "logic": "or",
            "weight": 0.3
        },
        {
            "name": "短时多地登录",
            "field": "login_locations",
            "operator": "contains",
            "threshold": "多个",
            "logic": "or",
            "weight": 0.2
        },
        {
            "name": "设备指纹异常",
            "field": "device_fingerprint",
            "operator": "eq",
            "threshold": "unknown",
            "logic": "or",
            "weight": 0.1
        }
    ],
    "risk_levels": {
        "high": 80,
        "medium": 50,
        "low": 0
    }
}

FIELD_ALIASES = {
    "手机号": "phone",
    "电话": "phone",
    "手机": "phone",
    "金额": "amount",
    "交易金额": "amount",
    "订单金额": "amount",
    "用户ID": "user_id",
    "用户id": "user_id",
    "用户编号": "user_id",
    "订单号": "order_no",
    "订单编号": "order_no",
    "交易次数": "transaction_count",
    "登录地点": "login_locations",
    "设备指纹": "device_fingerprint",
    "日期": "date",
    "时间": "date",
    "交易时间": "date",
    "创建时间": "date"
}

OPERATORS = {
    "eq": lambda v, t: v == t,
    "neq": lambda v, t: v != t,
    "gt": lambda v, t: _safe_compare(v, t, lambda a, b: a > b),
    "gte": lambda v, t: _safe_compare(v, t, lambda a, b: a >= b),
    "lt": lambda v, t: _safe_compare(v, t, lambda a, b: a < b),
    "lte": lambda v, t: _safe_compare(v, t, lambda a, b: a <= b),
    "in": lambda v, t: v in t if isinstance(t, list) else False,
    "contains": lambda v, t: str(t) in str(v) if v is not None else False
}


# ============================================================
# 错误码定义
# ============================================================

ERROR_CODES = {
    "E001": "文件格式不支持，仅支持 CSV、JSON 格式",
    "E002": "未找到唯一标识字段（id 或 order_no）",
    "E003": "规则 JSON 解析失败，请检查规则文件格式",
    "E004": "数据量过大，超过 10 万条上限",
    "E005": "并行处理失败，已回退至单线程模式",
    "E006": "输出目录无权限，无法写入结果文件",
    "E007": "输入文件不存在或无法读取",
    "E008": "字段映射失败，无法识别必要字段",
    "E009": "日期格式无法解析",
    "E010": "未知异常，请查看错误日志"
}


# ============================================================
# 工具函数
# ============================================================

def _safe_compare(value, threshold, comparator):
    """安全比较函数，处理类型转换失败的情况。"""
    try:
        return comparator(float(value), float(threshold))
    except (ValueError, TypeError):
        return False


def _read_file_with_encoding(filepath):
    """多编码读取文件，依次尝试 utf-8、gbk、gb18030。"""
    encodings = ["utf-8", "gbk", "gb18030"]
    for enc in encodings:
        try:
            with open(filepath, "r", encoding=enc) as f:
                return f.read(), enc
        except (UnicodeDecodeError, UnicodeError):
            continue
        except FileNotFoundError:
            raise
    # 最后兜底：使用 errors="replace"
    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        return f.read(), "utf-8(replace)"


def _normalize_field_name(name):
    """标准化字段名，去除空格、转小写、映射别名。"""
    if name is None:
        return ""
    stripped = str(name).strip().lower()
    # 先查别名映射
    if stripped in FIELD_ALIASES:
        return FIELD_ALIASES[stripped]
    # 去除非字母数字字符
    normalized = re.sub(r"[^a-z0-9_]", "_", stripped)
    return normalized.strip("_")


def _normalize_date(value):
    """统一日期格式为 YYYY-MM-DD HH:mm:ss。"""
    if value is None or str(value).strip() == "":
        return "[需核实:日期格式]"
    text = str(value).strip()
    # 尝试多种常见格式
    formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
        "%Y/%m/%d %H:%M:%S",
        "%Y/%m/%d",
        "%Y年%m月%d日 %H:%M:%S",
        "%Y年%m月%d日"
    ]
    for fmt in formats:
        try:
            dt = datetime.strptime(text, fmt)
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            continue
    return "[需核实:日期格式]"


def _normalize_number(value):
    """数值字段去除千分位逗号并转为 float。"""
    if value is None:
        return None
    text = str(value).strip()
    if text == "":
        return None
    # 去除千分位逗号和货币符号
    text = text.replace(",", "").replace("¥", "").replace("$", "")
    try:
        return float(text)
    except ValueError:
        return None


# ============================================================
# 输入校验模块
# ============================================================

def validate_input_file(filepath):
    """校验输入文件存在且格式支持。"""
    if not os.path.exists(filepath):
        print(f"错误 E007: {ERROR_CODES['E007']} - {filepath}")
        raise FileNotFoundError(f"E007: {filepath}")
    ext = os.path.splitext(filepath)[1].lower()
    if ext not in SUPPORTED_EXTENSIONS:
        print(f"错误 E001: {ERROR_CODES['E001']} - 实际格式: {ext}")
        raise ValueError(f"E001: 不支持的文件格式 {ext}")
    return filepath


def validate_rules_file(filepath):
    """校验规则文件存在且 JSON 格式正确。"""
    if filepath is None:
        return DEFAULT_RULES
    if not os.path.exists(filepath):
        print(f"错误 E007: {ERROR_CODES['E007']} - 规则文件 {filepath}")
        raise FileNotFoundError(f"E007: 规则文件不存在 {filepath}")
    try:
        content, _ = _read_file_with_encoding(filepath)
        rules = json.loads(content)
        if "rules" not in rules:
            raise ValueError("规则文件缺少 'rules' 字段")
        return rules
    except json.JSONDecodeError as e:
        print(f"错误 E003: {ERROR_CODES['E003']} - 第 {e.lineno} 行")
        raise ValueError(f"E003: 规则 JSON 解析失败: {e}")


def validate_output_dir(dirpath):
    """校验输出目录存在或可创建。"""
    if dirpath is None:
        return None
    path = Path(dirpath)
    if not path.exists():
        try:
            path.mkdir(parents=True, exist_ok=True)
        except PermissionError:
            print(f"错误 E006: {ERROR_CODES['E006']} - {dirpath}")
            raise PermissionError(f"E006: 无法创建输出目录 {dirpath}")
    if not os.access(str(path), os.W_OK):
        print(f"错误 E006: {ERROR_CODES['E006']} - {dirpath}")
        raise PermissionError(f"E006: 输出目录无写权限 {dirpath}")
    return str(path)


# ============================================================
# 数据加载模块
# ============================================================

def load_data(filepath):
    """加载 CSV 或 JSON 数据文件。"""
    ext = os.path.splitext(filepath)[1].lower()
    content, encoding = _read_file_with_encoding(filepath)
    if ext == ".csv":
        return _parse_csv(content)
    elif ext == ".json":
        return _parse_json(content)
    else:
        raise ValueError(f"E001: 不支持的文件格式 {ext}")


def _parse_csv(content):
    """解析 CSV 内容为记录列表。"""
    try:
        reader = csv.DictReader(content.splitlines())
        records = []
        for row in reader:
            record = {key.strip(): value for key, value in row.items() if key is not None}
            records.append(record)
        return records
    except Exception as e:
        print(f"警告: CSV 解析异常: {e}")
        return []


def _parse_json(content):
    """解析 JSON 内容为记录列表。"""
    try:
        data = json.loads(content)
        if isinstance(data, list):
            return data
        elif isinstance(data, dict):
            # 尝试常见包装结构
            for key in ["data", "records", "items", "rows"]:
                if key in data and isinstance(data[key], list):
                    return data[key]
            return [data]
        else:
            return []
    except json.JSONDecodeError as e:
        print(f"错误 E003: {ERROR_CODES['E003']} - 第 {e.lineno} 行")
        raise ValueError(f"E003: JSON 解析失败: {e}")


def align_fields(records):
    """字段对齐：标准化字段名，统一格式。"""
    if not records:
        return []
    aligned = []
    for record in records:
        new_record = {}
        for key, value in record.items():
            norm_key = _normalize_field_name(key)
            if norm_key == "date":
                new_record[norm_key] = _normalize_date(value)
            elif norm_key == "amount":
                new_record[norm_key] = _normalize_number(value)
            else:
                new_record[norm_key] = value
        aligned.append(new_record)
    return aligned


def check_unique_id(records):
    """检查记录中是否包含唯一标识字段。"""
    if not records:
        return False
    first = records[0]
    return "id" in first or "order_no" in first


# ============================================================
# 规则评估模块
# ============================================================

def evaluate_rules(record, rules_config):
    """对单条记录执行规则评估，返回命中规则列表和风险分。"""
    hits = []
    total_weight = 0.0
    risk_score = 0.0

    rules = rules_config.get("rules", [])
    for rule in rules:
        field = rule.get("field", "")
        operator = rule.get("operator", "eq")
        threshold = rule.get("threshold")
        weight = float(rule.get("weight", 0.1))

        if field not in record:
            # 规则字段缺失，标记需核实
            hits.append({
                "rule": rule.get("name", "未知规则"),
                "hit": False,
                "missing_field": field
            })
            continue

        value = record[field]
        op_func = OPERATORS.get(operator)
        if op_func is None:
            continue

        try:
            is_hit = op_func(value, threshold)
        except Exception:
            is_hit = False

        if is_hit:
            hits.append({
                "rule": rule.get("name", "未知规则"),
                "hit": True,
                "field": field,
                "value": value,
                "threshold": threshold
            })
            total_weight += weight
            risk_score += weight * 100

    # 归一化风险分到 0-100
    if total_weight > 0:
        risk_score = min(100.0, risk_score / max(total_weight, 0.01))
    else:
        risk_score = 0.0

    return hits, risk_score


def determine_risk_level(score, rules_config):
    """根据风险分确定风险等级。"""
    levels = rules_config.get("risk_levels", {"high": 80, "medium": 50, "low": 0})
    if score >= levels.get("high", 80):
        return "高"
    elif score >= levels.get("medium", 50):
        return "中"
    else:
        return "低"


def process_chunk(chunk, rules_config):
    """处理一个数据分片，返回带评分的结果。"""
    results = []
    for record in chunk:
        hits, score = evaluate_rules(record, rules_config)
        level = determine_risk_level(score, rules_config)
        result = dict(record)
        result["_risk_score"] = round(score, 2)
        result["_risk_level"] = level
        result["_hit_rules"] = [h["rule"] for h in hits if h["hit"]]
        result["_missing_fields"] = [h["missing_field"] for h in hits if "missing_field" in h]
        results.append(result)
    return results


# ============================================================
# 分片与并行处理模块
# ============================================================

def chunk_records(records, chunk_size=DEFAULT_CHUNK_SIZE):
    """将记录列表切分为多个分片。"""
    for i in range(0, len(records), chunk_size):
        yield records[i:i + chunk_size]


def process_all_records(records, rules_config, use_parallel=True):
    """处理所有记录，支持分片与并行。"""
    if len(records) > MAX_RECORDS_LIMIT:
        print(f"错误 E004: {ERROR_CODES['E004']} - 当前 {len(records)} 条")
        raise ValueError(f"E004: 数据量超过 {MAX_RECORDS_LIMIT} 条上限")

    all_results = []
    chunk_count = 0

    for chunk in chunk_records(records):
        chunk_count += 1
        try:
            if use_parallel and len(chunk) > 1000:
                results = _process_chunk_parallel(chunk, rules_config)
            else:
                results = process_chunk(chunk, rules_config)
            all_results.extend(results)
        except Exception as e:
            print(f"警告 E005: {ERROR_CODES['E005']} - {e}")
            # 回退至单线程
            results = process_chunk(chunk, rules_config)
            all_results.extend(results)

    return all_results, chunk_count


def _process_chunk_parallel(chunk, rules_config):
    """并行处理分片（简化实现，实际可替换为 multiprocessing）。"""
    # 为保持标准库兼容和稳定性，此处使用串行实现
    # 实际部署可替换为 multiprocessing.Pool
    return process_chunk(chunk, rules_config)


# ============================================================
# 输出与汇总模块
# ============================================================

def write_results(results, output_dir, dry=False):
    """写入分片结果文件。"""
    if output_dir is None:
        return []

    written_files = []
    chunk_size = DEFAULT_CHUNK_SIZE

    for idx, chunk_start in enumerate(range(0, len(results), chunk_size)):
        chunk = results[chunk_start:chunk_start + chunk_size]
        filename = f"result_part_{idx + 1:03d}.csv"
        filepath = os.path.join(output_dir, filename)

        if dry:
            print(f"[dry-run] 将写入 {filepath} ({len(chunk)} 条)")
            written_files.append(filepath)
            continue

        try:
            with open(filepath, "w", encoding="utf-8-sig", newline="") as f:
                if chunk:
                    fieldnames = list(chunk[0].keys())
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(chunk)
            written_files.append(filepath)
        except PermissionError:
            print(f"错误 E006: {ERROR_CODES['E006']} - {filepath}")
            raise

    return written_files


def generate_summary(results, chunk_count, elapsed_time):
    """生成汇总统计信息。"""
    total = len(results)
    if total == 0:
        return {
            "total_records": 0,
            "chunk_count": 0,
            "risk_distribution": {"高": 0, "中": 0, "低": 0},
            "hit_rule_stats": {},
            "elapsed_seconds": round(elapsed_time, 2)
        }

    risk_counter = Counter(r.get("_risk_level", "低") for r in results)
    hit_rules = []
    for r in results:
        hit_rules.extend(r.get("_hit_rules", []))
    rule_stats = Counter(hit_rules)

    return {
        "total_records": total,
        "chunk_count": chunk_count,
        "risk_distribution": dict(risk_counter),
        "hit_rule_stats": dict(rule_stats),
        "elapsed_seconds": round(elapsed_time, 2)
    }


def write_summary(summary, output_dir, dry=False):
    """写入汇总统计 JSON 文件。"""
    if output_dir is None:
        return None

    filepath = os.path.join(output_dir, "fraud_analysis_summary.json")
    if dry:
        print(f"[dry-run] 将写入 {filepath}")
        return filepath

    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        return filepath
    except PermissionError:
        print(f"错误 E006: {ERROR_CODES['E006']} - {filepath}")
        raise


def generate_validation_report(results, output_dir, dry=False):
    """生成校验报告 Markdown 文件。"""
    if output_dir is None:
        return None

    filepath = os.path.join(output_dir, "validation_report.md")
    if dry:
        print(f"[dry-run] 将写入 {filepath}")
        return filepath

    total = len(results)
    missing_fields = []
    for r in results:
        for field in r.get("_missing_fields", []):
            missing_fields.append(field)

    lines = [
        "# 数据校验报告",
        "",
        f"- 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"- 总记录数: {total}",
        f"- 缺失字段记录数: {len(missing_fields)}",
        "",
        "## 缺失字段清单",
        ""
    ]
    if missing_fields:
        counter = Counter(missing_fields)
        for field, count in counter.most_common():
            lines.append(f"- `{field}`: {count} 条记录缺失")
    else:
        lines.append("- 无缺失字段")

    lines.extend(["", "## 修正建议", ""])
    if missing_fields:
        lines.append("- 请补充缺失字段的原始数据后重新处理")
        lines.append("- 或调整规则配置，避免引用缺失字段")
    else:
        lines.append("- 数据质量良好，无需修正")

    try:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        return filepath
    except PermissionError:
        print(f"错误 E006: {ERROR_CODES['E006']} - {filepath}")
        raise


# ============================================================
# 主处理流程
# ============================================================

def run_analysis(input_file, rules_file=None, output_dir=None, dry=False, verbose=False):
    """执行完整反欺诈分析流程。"""
    start_time = time.time()

    # 1. 输入校验
    validate_input_file(input_file)
    rules_config = validate_rules_file(rules_file)
    out_path = validate_output_dir(output_dir)

    # 2. 数据加载与字段对齐
    print(f"加载数据: {input_file}")
    records = load_data(input_file)
    if not records:
        print("警告: 输入文件为空或无有效记录")
        return None

    print(f"原始记录数: {len(records)}")
    records = align_fields(records)

    if not check_unique_id(records):
        print(f"错误 E002: {ERROR_CODES['E002']}")
        raise ValueError("E002: 未找到唯一标识字段")

    # 3. 规则评估与风险评分
    print("执行规则评估...")
    results, chunk_count = process_all_records(records, rules_config)

    if verbose:
        _print_verbose_details(results, rules_config)

    # 4. 输出结果
    written_files = write_results(results, out_path, dry=dry)
    elapsed = time.time() - start_time
    summary = generate_summary(results, chunk_count, elapsed)
    summary_file = write_summary(summary, out_path, dry=dry)
    report_file = generate_validation_report(results, out_path, dry=dry)

    # 5. 打印汇总
    print(f"\n处理完成，耗时 {elapsed:.2f} 秒")
    print(f"总记录数: {summary['total_records']}")
    print(f"分片数: {summary['chunk_count']}")
    print(f"风险分布: {summary['risk_distribution']}")
    if written_files:
        print(f"结果文件: {written_files}")
    if summary_file:
        print(f"汇总文件: {summary_file}")
    if report_file:
        print(f"校验报告: {report_file}")

    return summary


def _print_verbose_details(results, rules_config):
    """打印详细的修改决策明细。"""
    print("\n===== 详细处理明细 =====")
    for idx, r in enumerate(results[:20], 1):
        print(f"\n[{idx}] 记录 ID: {r.get('id', r.get('order_no', 'N/A'))}")
        print(f"  风险评分: {r.get('_risk_score', 0)} | 等级: {r.get('_risk_level', '未知')}")
        hits = r.get("_hit_rules", [])
        if hits:
            print(f"  命中规则: {', '.join(hits)}")
        missing = r.get("_missing_fields", [])
        if missing:
            print(f"  缺失字段: {', '.join(missing)}")
    if len(results) > 20:
        print(f"\n... 其余 {len(results) - 20} 条记录略")


# ============================================================
# 自检模块
# ============================================================

def run_selftest():
    """内置硬编码样例数据自检核心逻辑。"""
    print("开始自检...")
    passed = 0
    failed = 0

    # 测试用例 1: 基本规则评估
    try:
        record = {"id": "001", "amount": 150000, "transaction_count": 10}
        hits, score = evaluate_rules(record, DEFAULT_RULES)
        assert score > 0, "金额异常规则应命中"
        assert len(hits) > 0, "应至少命中一条规则"
        passed += 1
        print("  [通过] 规则评估: 金额异常检测")
    except AssertionError as e:
        failed += 1
        print(f"  [失败] 规则评估: {e}")

    # 测试用例 2: 中文标点与编码
    try:
        content = 'id,金额,备注\n001,"1,000.50","测试,中文标点"\n'
        records = _parse_csv(content)
        assert len(records) == 1, "应解析出 1 条记录"
        assert records[0]["金额"] == "1,000.50", "金额字段应保留原始值"
        passed += 1
        print("  [通过] CSV 解析: 中文标点与千分位")
    except AssertionError as e:
        failed += 1
        print(f"  [失败] CSV 解析: {e}")

    # 测试用例 3: 空输入处理
    try:
        records = []
        aligned = align_fields(records)
        assert aligned == [], "空输入应返回空列表"
        passed += 1
        print("  [通过] 空输入处理")
    except AssertionError as e:
        failed += 1
        print(f"  [失败] 空输入处理: {e}")

    # 测试用例 4: 字段对齐与日期标准化
    try:
        record = {"手机号": "13800138000", "金额": "1,000.50", "日期": "2024-01-15"}
        aligned = align_fields([record])[0]
        assert "phone" in aligned, "手机号应映射为 phone"
        assert aligned["amount"] == 1000.5, "金额应转为数值"
        assert aligned["date"] == "2024-01-15 00:00:00", "日期应标准化"
        passed += 1
        print("  [通过] 字段对齐与类型转换")
    except AssertionError as e:
        failed += 1
        print(f"  [失败] 字段对齐: {e}")

    # 测试用例 5: 超长输入与分片
    try:
        records = [{"id": f"id_{i}", "amount": i * 100, "transaction_count": i} for i in range(12000)]
        chunks = list(chunk_records(records, 5000))
        assert len(chunks) == 3, "12000 条应分为 3 片"
        assert sum(len(c) for c in chunks) == 12000, "分片总数应等于原记录数"
        passed += 1
        print("  [通过] 分片处理: 12000 条记录")
    except AssertionError as e:
        failed += 1
        print(f"  [失败] 分片处理: {e}")

    # 测试用例 6: 风险等级判定
    try:
        level_high = determine_risk_level(90, DEFAULT_RULES)
        level_medium = determine_risk_level(60, DEFAULT_RULES)
        level_low = determine_risk_level(10, DEFAULT_RULES)
        assert level_high == "高", "90 分应为高风险"
        assert level_medium == "中", "60 分应为中风险"
        assert level_low == "低", "10 分应为低风险"
        passed += 1
        print("  [通过] 风险等级判定")
    except AssertionError as e:
        failed += 1
        print(f"  [失败] 风险等级判定: {e}")

    # 测试用例 7: 缺失值处理
    try:
        record = {"id": "002", "amount": None, "transaction_count": 5}
        hits, score = evaluate_rules(record, DEFAULT_RULES)
        assert score == 0, "缺失金额不应产生风险分"
        passed += 1
        print("  [通过] 缺失值处理")
    except AssertionError as e:
        failed += 1
        print(f"  [失败] 缺失值处理: {e}")

    # 测试用例 8: 操作符覆盖
    try:
        assert OPERATORS["eq"](5, 5) is True
        assert OPERATORS["neq"](5, 6) is True
        assert OPERATORS["gt"](10, 5) is True
        assert OPERATORS["gte"](5, 5) is True
        assert OPERATORS["lt"](3, 5) is True
        assert OPERATORS["lte"](5, 5) is True
        assert OPERATORS["in"]("a", ["a", "b"]) is True
        assert OPERATORS["contains"]("hello world", "world") is True
        passed += 1
        print("  [通过] 操作符覆盖测试")
    except AssertionError as e:
        failed += 1
        print(f"  [失败] 操作符覆盖: {e}")

    # 测试用例 9: 编码兼容（GBK 内容模拟）
    try:
        # 模拟 GBK 编码的 CSV 内容
        gbk_content = "id,金额\n001,100\n".encode("gbk").decode("gbk")
        records = _parse_csv(gbk_content)
        assert len(records) == 1, "GBK 内容应正常解析"
        passed += 1
        print("  [通过] 编码兼容测试")
    except AssertionError as e:
        failed += 1
        print(f"  [失败] 编码兼容: {e}")

    # 测试用例 10: 完整流程（小数据集）
    try:
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            test_csv = os.path.join(tmpdir, "test.csv")
            with open(test_csv, "w", encoding="utf-8") as f:
                f.write("id,amount,transaction_count\n001,150000,60\n002,100,5\n003,200000,80\n")
            summary = run_analysis(test_csv, output_dir=tmpdir, dry=False)
            assert summary is not None, "应生成汇总"
            assert summary["total_records"] == 3, "应处理 3 条记录"
            assert summary["risk_distribution"]["高"] >= 1, "应至少 1 条高风险"
            passed += 1
            print("  [通过] 完整流程测试")
    except Exception as e:
        failed += 1
        print(f"  [失败] 完整流程: {e}")

    print(f"\n自检完成: {passed} 通过, {failed} 失败")
    return 0 if failed == 0 else 1


# ============================================================
# CLI 入口
# ============================================================

def main():
    """命令行入口函数。"""
    parser = argparse.ArgumentParser(
        description="反欺诈识别与风险分析工具",
        epilog="示例: python main.py --input data.csv --output results/"
    )
    parser.add_argument("--input", "-i", help="输入数据文件 (CSV/JSON)")
    parser.add_argument("--output", "-o", help="输出目录")
    parser.add_argument("--rules", "-r", help="自定义规则 JSON 文件")
    parser.add_argument("--dry-run", action="store_true", help="只打印 diff 不写盘")
    parser.add_argument("--force", action="store_true", help="真正落盘（需与 --dry-run 配合）")
    parser.add_argument("--verbose", "-v", action="store_true", help="输出详细处理明细")
    parser.add_argument("--selftest", action="store_true", help="运行内置自检")
    parser.add_argument("--version", action="version", version="skill-88616 v1.0.1")

    args = parser.parse_args()

    if args.selftest:
        sys.exit(run_selftest())

    if not args.input:
        parser.error("必须指定 --input 参数")

    # dry-run 与 force 逻辑：默认 dry-run 为 True（安全模式）
    # 只有显式 --force 才真正写盘
    dry = not args.force
    if args.dry_run:
        dry = True

    try:
        run_analysis(
            input_file=args.input,
            rules_file=args.rules,
            output_dir=args.output,
            dry=dry,
            verbose=args.verbose
        )
    except FileNotFoundError as e:
        print(f"错误: {e}")
        sys.exit(1)
    except ValueError as e:
        print(f"错误: {e}")
        sys.exit(1)
    except PermissionError as e:
        print(f"错误: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"错误 E010: {ERROR_CODES['E010']}")
        print(f"详细信息: {traceback.format_exc()}")
        sys.exit(1)


if __name__ == "__main__":
    main()
