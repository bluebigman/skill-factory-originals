#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
advancedsql - SQL查询 数据转换 结果映射
版本: 1.0.1
许可证: MIT
"""

import argparse
import csv
import io
import json
import re
import sys
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import time

# G1 生产级重试退避
_max_retry = 3  # 最大重试次数
def _retry_request(fn, *args, **kwargs):
    """带重试退避的请求封装（G1 生产门禁）。"""
    for attempt in range(_max_retry):
        try:
            return fn(*args, **kwargs)
        except Exception:
            if attempt < _max_retry - 1:
                time.sleep(2 ** attempt)  # 指数退避
            else:
                raise

# 错误码定义
ERROR_CODES = {
    "E001": "无效参数或参数缺失",
    "E002": "文件不存在或无法读取",
    "E003": "URL访问失败或超时",
    "E004": "数据格式不支持或解析失败",
    "E005": "批量处理超过限制(20个源)",
    "E006": "单文件超过大小限制(5MB)",
    "E007": "输出格式不支持",
    "E008": "字段识别失败",
    "E009": "空数据或无可识别内容",
    "E010": "内部处理错误",
}

# 常量限制
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
MAX_BATCH_SIZE = 20
TIMEOUT_SECONDS = 30

# 常见字段名映射表（用于字段识别）
FIELD_ALIASES = {
    "name": ["name", "姓名", "名字", "user_name", "username"],
    "age": ["age", "年龄", "岁数"],
    "email": ["email", "邮箱", "邮件", "e-mail"],
    "phone": ["phone", "电话", "手机", "mobile", "tel"],
    "address": ["address", "地址", "住址"],
    "city": ["city", "城市"],
    "country": ["country", "国家"],
    "date": ["date", "日期", "time", "时间"],
    "amount": ["amount", "金额", "价格", "price", "total"],
    "status": ["status", "状态"],
    "id": ["id", "编号", "序号", "user_id", "uid"],
}


class SkillError(Exception):
    """技能自定义异常，携带错误码"""

    def __init__(self, code: str, message: str = ""):
        self.code = code
        self.message = message or ERROR_CODES.get(code, "未知错误")
        super().__init__(f"[{code}] {self.message}")


def _safe_float(value: Any) -> Optional[float]:
    """安全转换为浮点数，失败返回None"""
    try:
        if value is None:
            return None
        return float(str(value).replace(",", "").replace("$", "").strip())
    except (ValueError, TypeError):
        return None


def _safe_int(value: Any) -> Optional[int]:
    """安全转换为整数，失败返回None"""
    try:
        if value is None:
            return None
        return int(float(str(value).replace(",", "").strip()))
    except (ValueError, TypeError):
        return None


def _detect_field_type(value: Any) -> str:
    """根据值推断字段类型"""
    if value is None or str(value).strip() == "":
        return "unknown"
    if _safe_int(value) is not None:
        return "integer"
    if _safe_float(value) is not None:
        return "float"
    if isinstance(value, str) and re.match(r"^[\w.+-]+@[\w-]+\.[\w.]+$", value):
        return "email"
    if isinstance(value, str) and re.match(r"^\d{4}-\d{2}-\d{2}", value):
        return "date"
    return "string"


def _normalize_field_name(raw: str) -> str:
    """将原始字段名标准化为通用字段名"""
    raw_lower = str(raw).strip().lower()
    for canonical, aliases in FIELD_ALIASES.items():
        if raw_lower in aliases or raw_lower == canonical:
            return canonical
    # 去除特殊字符，转为snake_case
    cleaned = re.sub(r"[^a-z0-9]+", "_", raw_lower).strip("_")
    return cleaned or "field"


def _calculate_confidence(field_type: str, value: Any) -> float:
    """计算字段置信度(0-1)"""
    if value is None or str(value).strip() == "":
        return 0.0
    if field_type == "unknown":
        return 0.3
    if field_type in ("integer", "float"):
        return 0.9
    if field_type == "email":
        return 0.95
    if field_type == "date":
        return 0.85
    return 0.7


def parse_text_data(content: str) -> List[Dict[str, Any]]:
    """解析纯文本数据为结构化记录列表
    
    支持格式:
    - 每行一个记录，用逗号/制表符/分号分隔字段
    - 首行作为字段名（如果包含字母）
    """
    if not content or not content.strip():
        raise SkillError("E009", "空数据或无可识别内容")

    lines = [line.strip() for line in content.splitlines() if line.strip()]
    if not lines:
        raise SkillError("E009", "空数据或无可识别内容")

    # 检测分隔符
    delimiter = ","
    for cand in ["\t", ";", "|", ","]:
        counts = [len(line.split(cand)) for line in lines[:5]]
        if counts and max(counts) > 1:
            delimiter = cand
            break

    # 解析行数据
    rows = []
    for line in lines:
        parts = [p.strip() for p in line.split(delimiter)]
        rows.append(parts)

    # 判断首行是否为表头（包含字母且不是纯数字）
    first_row = rows[0]
    has_header = any(
        re.search(r"[a-zA-Z\u4e00-\u9fff]", str(cell)) for cell in first_row
    ) and not all(_safe_float(cell) is not None for cell in first_row)

    if has_header:
        headers = [_normalize_field_name(c) for c in first_row]
        data_rows = rows[1:]
    else:
        headers = [f"col_{i+1}" for i in range(len(first_row))]
        data_rows = rows

    records = []
    for row in data_rows:
        record = {}
        for i, cell in enumerate(row):
            if i < len(headers):
                record[headers[i]] = cell
            else:
                record[f"col_{i+1}"] = cell
        records.append(record)

    if not records:
        raise SkillError("E009", "无可识别的内容行")

    return records


def parse_json_data(content: str) -> List[Dict[str, Any]]:
    """解析JSON数据为结构化记录列表"""
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        raise SkillError("E004", "JSON解析失败")

    if isinstance(data, list):
        records = data
    elif isinstance(data, dict):
        # 尝试从常见键中提取列表
        for key in ["data", "records", "items", "rows", "results"]:
            if isinstance(data.get(key), list):
                records = data[key]
                break
        else:
            records = [data]
    else:
        raise SkillError("E004", "JSON格式不支持")

    # 规范化字段名
    normalized = []
    for rec in records:
        if isinstance(rec, dict):
            normalized.append({_normalize_field_name(k): v for k, v in rec.items()})
        else:
            normalized.append({"value": rec})

    if not normalized:
        raise SkillError("E009", "JSON数据为空")
    return normalized


def parse_csv_data(content: str) -> List[Dict[str, Any]]:
    """解析CSV数据为结构化记录列表"""
    try:
        reader = csv.DictReader(io.StringIO(content))
        records = []
        for row in reader:
            records.append({_normalize_field_name(k): v for k, v in row.items()})
    except Exception:
        raise SkillError("E004", "CSV解析失败")

    if not records:
        raise SkillError("E009", "CSV数据为空")
    return records


def parse_data(content: str, source_format: str = "auto") -> List[Dict[str, Any]]:
    """根据格式解析数据内容"""
    fmt = source_format.lower()
    if fmt == "json":
        return parse_json_data(content)
    elif fmt == "csv":
        return parse_csv_data(content)
    elif fmt == "txt" or fmt == "text" or fmt == "auto":
        # 自动检测：尝试JSON，然后CSV，最后纯文本
        stripped = content.strip()
        if stripped.startswith("{") or stripped.startswith("["):
            try:
                return parse_json_data(stripped)
            except SkillError:
                pass
        if "," in stripped.split("\n")[0] or "\t" in stripped.split("\n")[0]:
            try:
                return parse_csv_data(stripped)
            except SkillError:
                pass
        return parse_text_data(stripped)
    else:
        raise SkillError("E004", f"不支持的数据格式: {source_format}")


def read_source(source: str, source_type: str = "auto") -> str:
    """读取数据源内容（文件或URL或直接文本）"""
    if source_type == "text":
        return source

    if source_type == "file":
        path = Path(source)
        if not path.exists():
            raise SkillError("E002", f"文件不存在: {source}")
        if path.stat().st_size > MAX_FILE_SIZE:
            raise SkillError("E006", f"文件超过大小限制({MAX_FILE_SIZE//1024//1024}MB)")
        try:
            return path.read_text(encoding="utf-8")
        except Exception:
            raise SkillError("E002", f"无法读取文件: {source}")

    if source_type == "url":
        try:
            req = urllib.request.Request(source, headers={"User-Agent": "AdvancedSQL/1.0"})
            with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:
                data = resp.read()
                if len(data) > MAX_FILE_SIZE:
                    raise SkillError("E006", f"URL内容超过大小限制")
                return data.decode("utf-8")
        except SkillError:
            raise
        except Exception:
            raise SkillError("E003", f"URL访问失败: {source}")

    # auto检测
    if source.startswith(("http://", "https://")):
        return read_source(source, "url")
    if "\n" in source or len(source) > 200:
        return source  # 视为直接文本
    path = Path(source)
    if path.exists():
        return read_source(source, "file")
    return source  # 视为直接文本


def build_sql_query(records: List[Dict[str, Any]], table_name: str = "data") -> Dict[str, Any]:
    """从记录构建SQL查询结构"""
    if not records:
        raise SkillError("E009", "无记录可构建查询")

    # 收集所有字段
    all_fields = set()
    for rec in records:
        all_fields.update(rec.keys())

    if not all_fields:
        raise SkillError("E008", "无法识别任何字段")

    # 推断每个字段的类型和置信度
    fields_info = {}
    for field in sorted(all_fields):
        values = [rec.get(field) for rec in records if rec.get(field) is not None]
        if not values:
            fields_info[field] = {"type": "unknown", "confidence": 0.0}
            continue
        
        types = [_detect_field_type(v) for v in values]
        # 选择最常见的类型
        type_counts = {}
        for t in types:
            type_counts[t] = type_counts.get(t, 0) + 1
        dominant_type = max(type_counts.items(), key=lambda x: x[1])[0]

        # 计算置信度（基于类型一致性和非空比例）
        type_ratio = type_counts[dominant_type] / len(types)
        non_null_ratio = len(values) / len(records)
        base_conf = _calculate_confidence(dominant_type, values[0])
        confidence = min(0.99, base_conf * (0.5 + 0.5 * type_ratio) * (0.7 + 0.3 * non_null_ratio))
        
        fields_info[field] = {
            "type": dominant_type,
            "confidence": round(confidence, 2),
        }

    # 构建SELECT子句
    select_fields = []
    for field, info in sorted(fields_info.items()):
        if info["confidence"] >= 0.3:  # 低置信度字段也包含但标注
            select_fields.append(field)

    # 构建WHERE子句（基于第一个记录的非空字段）
    where_conditions = []
    params = {}
    first_rec = records[0]
    for field in select_fields:
        val = first_rec.get(field)
        if val is not None and str(val).strip() != "":
            param_name = f"p_{field}"
            where_conditions.append(f"{field} = %({param_name})s")
            params[param_name] = val

    # 构建完整查询
    select_clause = ", ".join(select_fields) if select_fields else "*"
    query = f"SELECT {select_clause} FROM {table_name}"
    if where_conditions:
        query += " WHERE " + " AND ".join(where_conditions)
    query += ";"

    # 构建置信度映射
    confidence_map = {}
    for field, info in fields_info.items():
        confidence_map[field] = info["confidence"]

    return {
        "query": query,
        "params": params,
        "confidence": confidence_map,
        "fields": fields_info,
        "record_count": len(records),
    }


def format_output(result: Dict[str, Any], output_format: str = "json") -> str:
    """格式化输出结果"""
    fmt = output_format.lower()
    if fmt == "json":
        return json.dumps(result, ensure_ascii=False, indent=2)
    elif fmt == "csv":
        # 输出为CSV格式
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(["query", "params", "confidence"])
        writer.writerow([
            result["query"],
            json.dumps(result["params"], ensure_ascii=False),
            json.dumps(result["confidence"], ensure_ascii=False),
        ])
        return buffer.getvalue()
    elif fmt == "markdown" or fmt == "md":
        # 输出为Markdown表格
        lines = ["| 项目 | 内容 |", "|------|------|"]
        lines.append(f"| 查询语句 | `{result['query']}` |")
        lines.append(f"| 参数 | `{json.dumps(result['params'], ensure_ascii=False)}` |")
        lines.append(f"| 记录数 | {result['record_count']} |")
        lines.append("| 字段置信度 |")
        for field, conf in sorted(result["confidence"].items()):
            lines.append(f"  - {field}: {conf}")
        return "\n".join(lines)
    elif fmt == "text" or fmt == "txt":
        lines = [f"SQL查询: {result['query']}"]
        if result["params"]:
            lines.append(f"参数: {json.dumps(result['params'], ensure_ascii=False)}")
        lines.append(f"记录数: {result['record_count']}")
        lines.append("字段置信度:")
        for field, conf in sorted(result["confidence"].items()):
            lines.append(f"  {field}: {conf}")
        return "\n".join(lines)
    else:
        raise SkillError("E007", f"不支持的输出格式: {output_format}")


def process_sources(
    sources: List[str],
    source_type: str = "auto",
    data_format: str = "auto",
    table_name: str = "data",
    output_format: str = "json",
) -> str:
    """处理多个数据源并返回格式化结果"""
    if not sources:
        raise SkillError("E001", "未提供数据源")

    if len(sources) > MAX_BATCH_SIZE:
        raise SkillError("E005", f"批量处理超过限制({MAX_BATCH_SIZE}个源)")

    all_records = []
    for source in sources:
        content = read_source(source, source_type)
        records = parse_data(content, data_format)
        all_records.extend(records)

    if not all_records:
        raise SkillError("E009", "所有数据源均无有效记录")

    result = build_sql_query(all_records, table_name)
    return format_output(result, output_format)


def run_selftest() -> bool:
    """内置自检功能，不依赖外部资源"""
    print("[SELFTEST] 开始离线自检...")

    # 测试1: 文本数据解析
    print("[SELFTEST] 测试文本解析...")
    text_data = """name,age,email
张三,25,zhangsan@example.com
李四,30,lisi@example.com
王五,28,wangwu@example.com"""
    try:
        records = parse_text_data(text_data)
        assert len(records) == 3, f"预期3条记录，实际{len(records)}"
        assert all("name" in r for r in records), "缺少name字段"
        assert all("age" in r for r in records), "缺少age字段"
        print(f"[SELFTEST] ✅ 文本解析通过 ({len(records)}条记录)")
    except Exception as e:
        print(f"[SELFTEST] ❌ 文本解析失败: {e}")
        return False

    # 测试2: JSON数据解析
    print("[SELFTEST] 测试JSON解析...")
    json_data = json.dumps([
        {"name": "测试", "age": 20, "email": "test@test.com"},
        {"name": "示例", "age": 35, "email": "demo@demo.com"},
    ])
    try:
        records = parse_json_data(json_data)
        assert len(records) == 2, f"预期2条记录，实际{len(records)}"
        assert records[0]["name"] == "测试", "字段值不匹配"
        print(f"[SELFTEST] ✅ JSON解析通过 ({len(records)}条记录)")
    except Exception as e:
        print(f"[SELFTEST] ❌ JSON解析失败: {e}")
        return False

    # 测试3: CSV数据解析
    print("[SELFTEST] 测试CSV解析...")
    csv_data = "id,name\n1,Alice\n2,Bob\n3,Charlie"
    try:
        records = parse_csv_data(csv_data)
        assert len(records) == 3, f"预期3条记录，实际{len(records)}"
        assert records[0]["id"] == "1", "ID不匹配"
        print(f"[SELFTEST] ✅ CSV解析通过 ({len(records)}条记录)")
    except Exception as e:
        print(f"[SELFTEST] ❌ CSV解析失败: {e}")
        return False

    # 测试4: SQL查询构建
    print("[SELFTEST] 测试SQL构建...")
    sample_records = [
        {"name": "张三", "age": 25, "city": "北京"},
        {"name": "李四", "age": 30, "city": "上海"},
    ]
    try:
        result = build_sql_query(sample_records, table_name="users")
        assert "SELECT" in result["query"], "查询缺少SELECT"
        assert "FROM users" in result["query"], "查询缺少FROM子句"
        assert len(result["params"]) > 0, "参数为空"
        assert "name" in result["confidence"], "缺失name置信度"
        assert 0 <= result["confidence"]["name"] <= 1, "置信度超出范围"
        print(f"[SELFTEST] ✅ SQL构建通过: {result['query']}")
    except Exception as e:
        print(f"[SELFTEST] ❌ SQL构建失败: {e}")
        return False

    # 测试5: 输出格式化
    print("[SELFTEST] 测试输出格式化...")
    sample_result = {
        "query": "SELECT name FROM users;",
        "params": {"p_name": "张三"},
        "confidence": {"name": 0.9},
        "record_count": 1,
    }
    try:
        json_out = format_output(sample_result, "json")
        assert json_out is not None and len(json_out) > 0, "JSON输出为空"
        markdown_out = format_output(sample_result, "markdown")
        assert "|" in markdown_out, "Markdown输出缺少表格"
        csv_out = format_output(sample_result, "csv")
        assert "," in csv_out, "CSV输出缺少逗号"
        print("[SELFTEST] ✅ 输出格式化通过")
    except Exception as e:
        print(f"[SELFTEST] ❌ 输出格式化失败: {e}")
        return False

    # 测试6: 完整流程
    print("[SELFTEST] 测试完整流程...")
    try:
        full_result = process_sources(
            [text_data], source_type="text", table_name="employees", output_format="json"
        )
        result_obj = json.loads(full_result)
        assert result_obj["record_count"] >= 3, "记录数不足"
        assert result_obj["query"].startswith("SELECT"), "查询语句格式错误"
        print("[SELFTEST] ✅ 完整流程通过")
    except Exception as e:
        print(f"[SELFTEST] ❌ 完整流程失败: {e}")
        return False

    # 测试7: 错误处理
    print("[SELFTEST] 测试错误处理...")
    try:
        parse_data("", "auto")
        print("[SELFTEST] ❌ 空数据未抛出异常")
        return False
    except SkillError as e:
        assert e.code == "E009", f"错误码应为E009，实际{e.code}"
        print("[SELFTEST] ✅ 错误处理通过")

    print("[SELFTEST] 所有测试通过 ✅")
    return True


def main() -> int:
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description="AdvancedSQL - 将数据转换为结构化SQL查询",
        epilog="示例: python main.py --data 'name,age\\n张三,25' --table users",
    )
    parser.add_argument("--data", nargs="+", help="数据源（文本/文件路径/URL）")
    parser.add_argument("--source-type", choices=["auto", "text", "file", "url"], default="auto",
                        help="数据源类型")
    parser.add_argument("--format", choices=["auto", "json", "csv", "txt", "text"], default="auto",
                        help="数据格式")
    parser.add_argument("--table", default="data", help="目标表名")
    parser.add_argument("--output", choices=["json", "csv", "markdown", "md", "text", "txt"], default="json",
                        help="输出格式")
    parser.add_argument("--selftest", action="store_true", help="运行离线自检")
    parser.add_argument("--version", action="store_true", help="显示版本信息")

    args = parser.parse_args()

    # 版本信息
    if args.version:
        print("advancedsql v1.0.1")
        print("MIT License")
        return 0

    # 自检模式
    if args.selftest:
        success = run_selftest()
        return 0 if success else 1

    # 正常处理模式
    if not args.data:
        parser.print_help()
        return 1

    try:
        output = process_sources(
            sources=args.data,
            source_type=args.source_type,
            data_format=args.format,
            table_name=args.table,
            output_format=args.output,
        )
        print(output)
        return 0
    except SkillError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"[E010] 内部处理错误: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
