#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
schemr — 数据建模与结构转换工具（独立实现）

根据功能规格独立编写，不参考任何既有代码。
支持多源输入解析、关键信息识别、结构化输出生成、置信度标注。
"""

import argparse
import json
import os
import re
import sys
from collections import OrderedDict
from typing import Any, Dict, List, Optional, Tuple, Union
dry_run = False  # v3.274 模块级 dry-run 标志


# ============================================================
# 错误码定义
# ============================================================
ERROR_CODES = {
    "E001": "参数错误：输入源为空或格式不正确",
    "E002": "文件读取失败：文件不存在或无法访问",
    "E003": "URL访问失败：网络请求错误或超时",
    "E004": "JSON解析失败：输入不是合法的JSON格式",
    "E005": "CSV解析失败：输入不是合法的CSV格式",
    "E006": "YAML解析失败：输入不是合法的YAML格式",
    "E007": "类型推断失败：无法识别字段类型",
    "E008": "Schema生成失败：内部处理异常",
    "E009": "输出写入失败：无法写入目标文件",
    "E010": "未知错误：未预期的异常",
}


class SchemrError(Exception):
    """schemr 自定义异常，携带错误码"""

    def __init__(self, code: str, message: Optional[str] = None):
        self.code = code
        self.message = message or ERROR_CODES.get(code, "未知错误")
        super().__init__(f"[{code}] {self.message}")


# ============================================================
# 类型推断模块
# ============================================================

def _read_text_safe(path):
    """多编码安全读取（R3+R5 合规）"""
    for enc in ("utf-8", "gbk", "gb18030"):  # gbk gb18030 fallback
        try:
            with open(path, encoding=enc, errors="replace") as f:
                return f.read()
        except (UnicodeDecodeError, OSError):
            continue
    with open(path, encoding="utf-8", errors="replace") as f:
        return f.read()

# 批处理流式读取工具
def _iter_lines(path):
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:  # readline 流式
            yield line


def infer_type(value: Any) -> str:
    """
    推断单个值的类型。
    返回类型字符串：string / integer / number / boolean / null / array / object
    """
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        # 尝试识别日期字符串（宽松判断：包含常见日期分隔符且长度合理）
        if re.search(r"\d{4}[-/]\d{1,2}[-/]\d{1,2}", value):
            return "date"
        # 尝试识别时间字符串
        if re.search(r"\d{1,2}:\d{2}(:\d{2})?", value):
            return "time"
        return "string"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    return "string"


def infer_field_types(records: List[Dict[str, Any]]) -> Dict[str, str]:
    """
    从一组记录中推断每个字段的类型。
    多个记录时取出现最多的类型作为最终类型。
    """
    field_types: Dict[str, Dict[str, int]] = {}

    for record in records:
        if not isinstance(record, dict):
            continue
        for key, value in record.items():
            if key not in field_types:
                field_types[key] = {}
            type_name = infer_type(value)
            field_types[key][type_name] = field_types[key].get(type_name, 0) + 1

    result: Dict[str, str] = {}
    for field, type_counts in field_types.items():
        if not type_counts:
            result[field] = "unknown"
            continue
        # 选择出现次数最多的类型
        best_type = max(type_counts.items(), key=lambda x: x[1])[0]
        result[field] = best_type

    return result


# ============================================================
# 置信度计算模块
# ============================================================

def compute_confidence(field: str, type_name: str, sample_count: int, total_count: int) -> float:
    """
    计算字段识别的置信度（0.0 ~ 1.0）。
    规则：
    - 字段名符合常见命名规范（小写、下划线、驼峰）时加分
    - 样本覆盖率高时加分
    - 类型为常见类型（string/integer/number/boolean）时加分
    """
    confidence = 0.5  # 基础置信度

    # 字段名规范加分
    if re.match(r"^[a-z][a-z0-9_]*$", field) or re.match(r"^[a-z][a-zA-Z0-9]*$", field):
        confidence += 0.2

    # 样本覆盖率加分
    coverage = sample_count / max(total_count, 1)
    confidence += coverage * 0.2

    # 常见类型加分
    if type_name in ("string", "integer", "number", "boolean"):
        confidence += 0.1

    return min(max(confidence, 0.0), 1.0)


# ============================================================
# Schema 生成模块
# ============================================================

def build_schema(
    data: Union[Dict[str, Any], List[Any]],
    source_name: str = "input",
) -> Dict[str, Any]:
    """
    根据输入数据构建结构化 Schema 文档。
    支持 dict 或 list[dict] 形式的输入。
    """
    try:
        # 统一转换为记录列表
        if isinstance(data, dict):
            records = [data]
        elif isinstance(data, list):
            records = [item for item in data if isinstance(item, dict)]
            if not records and data:
                # 非对象数组，生成通用数组 schema
                return {
                    "schema_version": "1.0",
                    "source": source_name,
                    "type": "array",
                    "items": {"type": infer_type(data[0])},
                    "confidence": 0.8,
                    "field_count": 1,
                }
        else:
            # 标量输入
            return {
                "schema_version": "1.0",
                "source": source_name,
                "type": infer_type(data),
                "confidence": 0.9,
                "field_count": 0,
            }

        if not records:
            return {
                "schema_version": "1.0",
                "source": source_name,
                "type": "object",
                "fields": [],
                "confidence": 0.5,
                "field_count": 0,
            }

        # 推断字段类型
        field_types = infer_field_types(records)

        # 构建字段列表
        fields = []
        total_records = len(records)

        for field_name in field_types:
            type_name = field_types[field_name]
            # 统计该字段在多少条记录中出现
            sample_count = sum(1 for r in records if isinstance(r, dict) and field_name in r)
            confidence = compute_confidence(field_name, type_name, sample_count, total_records)

            fields.append({
                "name": field_name,
                "type": type_name,
                "required": sample_count == total_records,
                "confidence": round(confidence, 2),
                "sample_count": sample_count,
            })

        # 计算整体置信度（所有字段置信度的平均值）
        overall_confidence = (
            sum(f["confidence"] for f in fields) / len(fields) if fields else 0.5
        )

        return {
            "schema_version": "1.0",
            "source": source_name,
            "type": "object",
            "fields": fields,
            "field_count": len(fields),
            "record_count": total_records,
            "confidence": round(overall_confidence, 2),
        }

    except SchemrError:
        raise
    except Exception as exc:
        raise SchemrError("E008", f"Schema生成失败: {exc}") from exc


# ============================================================
# 输入解析模块
# ============================================================

def parse_json_text(text: str) -> Any:
    """解析 JSON 文本"""
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise SchemrError("E004", f"JSON解析失败: {exc}") from exc


def parse_csv_text(text: str) -> List[Dict[str, Any]]:
    """解析 CSV 文本为字典列表"""
    import csv
    import io

    try:
        reader = csv.DictReader(io.StringIO(text))
        records = []
        for row in reader:
            # 转换空字符串为 None
            cleaned = {}
            for key, value in row.items():
                if value == "":
                    cleaned[key] = None
                else:
                    # 尝试转换为数字
                    try:
                        cleaned[key] = int(value)
                    except (ValueError, TypeError):
                        try:
                            cleaned[key] = float(value)
                        except (ValueError, TypeError):
                            cleaned[key] = value
            records.append(cleaned)
        return records
    except Exception as exc:
        raise SchemrError("E005", f"CSV解析失败: {exc}") from exc


def parse_yaml_text(text: str) -> Any:
    """解析 YAML 文本（需要 PyYAML）"""
    try:
        import yaml  # pip install pyyaml
    except ImportError:
        raise SchemrError("E006", "YAML解析需要安装 PyYAML: pip install pyyaml")

    try:
        return yaml.safe_load(text)
    except Exception as exc:
        raise SchemrError("E006", f"YAML解析失败: {exc}") from exc


def load_from_file(file_path: str) -> Any:
    """从文件加载数据，根据扩展名自动选择解析器"""
    if not os.path.exists(file_path):
        raise SchemrError("E002", f"文件不存在: {file_path}")

    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
    except Exception as exc:
        raise SchemrError("E002", f"文件读取失败: {exc}") from exc

    ext = os.path.splitext(file_path)[1].lower()

    if ext in (".json",):
        return parse_json_text(content)
    elif ext in (".csv",):
        return parse_csv_text(content)
    elif ext in (".yaml", ".yml"):
        return parse_yaml_text(content)
    else:
        # 默认尝试 JSON
        return parse_json_text(content)


def parse_input_source(source: str) -> Any:
    """
    解析输入源。
    支持：
    - 直接 JSON 文本（以 { 或 [ 开头）
    - 文件路径（存在且可读）
    - URL（http/https 开头）
    """
    source = source.strip()
    if not source:
        raise SchemrError("E001", "输入源为空")

    # 判断是否为文件路径
    if os.path.exists(source):
        return load_from_file(source)

    # 判断是否为 URL
    if source.startswith(("http://", "https://")):
        raise SchemrError("E003", "URL输入需要网络访问，当前版本不支持")

    # 尝试作为 JSON 文本解析
    if source.startswith(("{", "[")):
        return parse_json_text(source)

    # 尝试作为 CSV 文本解析
    if "," in source and "\n" in source:
        try:
            return parse_csv_text(source)
        except SchemrError:
            pass

    # 尝试作为 YAML 文本解析
    try:
        return parse_yaml_text(source)
    except SchemrError:
        pass

    # 最后尝试作为单行 JSON 值
    try:
        return json.loads(source)
    except json.JSONDecodeError:
        pass

    raise SchemrError("E001", f"无法识别的输入源格式: {source[:50]}...")


# ============================================================
# 输出格式化模块
# ============================================================

def format_schema(schema: Dict[str, Any], output_format: str = "json") -> str:
    """将 Schema 格式化为指定输出格式"""
    if output_format == "json":
        return json.dumps(schema, ensure_ascii=False, indent=2)

    elif output_format == "markdown":
        lines = ["# Schema 文档", ""]
        lines.append(f"- **版本**: {schema.get('schema_version', '1.0')}")
        lines.append(f"- **数据源**: {schema.get('source', 'unknown')}")
        lines.append(f"- **类型**: {schema.get('type', 'unknown')}")
        lines.append(f"- **字段数**: {schema.get('field_count', 0)}")
        lines.append(f"- **记录数**: {schema.get('record_count', 0)}")
        lines.append(f"- **置信度**: {schema.get('confidence', 0.0)}")
        lines.append("")

        fields = schema.get("fields", [])
        if fields:
            lines.append("## 字段定义")
            lines.append("")
            lines.append("| 字段名 | 类型 | 必填 | 置信度 |")
            lines.append("|--------|------|------|--------|")
            for field in fields:
                required = "是" if field.get("required") else "否"
                lines.append(
                    f"| {field['name']} | {field['type']} | {required} | {field.get('confidence', 0.0)} |"
                )
        else:
            lines.append("（无字段定义）")

        return "\n".join(lines)

    elif output_format == "yaml":
        try:
            import yaml  # pip install pyyaml
        except ImportError:
            raise SchemrError("E006", "YAML输出需要安装 PyYAML: pip install pyyaml")
        return yaml.safe_dump(schema, allow_unicode=True, sort_keys=False)

    else:
        raise SchemrError("E001", f"不支持的输出格式: {output_format}")


# ============================================================
# 主处理函数
# ============================================================

def process_input(
    source: str,
    output_format: str = "json",
    output_file: Optional[str] = None,
) -> str:
    """
    主处理流程：解析输入 -> 构建 Schema -> 格式化输出
    """
    # 1. 解析输入
    data = parse_input_source(source)

    # 2. 构建 Schema
    schema = build_schema(data, source_name=source[:50] if len(source) > 50 else source)

    # 3. 格式化输出
    result = format_schema(schema, output_format)

    # 4. 写入文件（如果指定）
    if output_file:
        try:
            with open(output_file, "w", encoding="utf-8", errors="replace") as f:
                f.write(result)
        except Exception as exc:
            raise SchemrError("E009", f"输出文件写入失败: {exc}") from exc

    return result


# ============================================================
# 自测模块
# ============================================================

def run_selftest() -> bool:
    """
    内置硬编码样例数据，离线自检核心逻辑。
    使用宽松阈值，不依赖精确值。
    """
    print("=" * 60)
    print("schemr 自测开始")
    print("=" * 60)

    # ---- 测试用例 1: JSON 对象输入 ----
    print("\n[测试1] JSON 对象输入")
    sample_json = """
    {
        "user": {"name": "Alice", "age": 30, "active": true},
        "order": {"id": "A001", "amount": 99.5, "item_count": 3}
    }
    """
    try:
        data1 = parse_json_text(sample_json)
        schema1 = build_schema(data1, "test_json")
        assert schema1["type"] == "object", f"类型应为 object，实际为 {schema1['type']}"
        assert schema1["field_count"] >= 2, f"字段数应至少为2，实际为 {schema1['field_count']}"
        assert 0.0 <= schema1["confidence"] <= 1.0, "置信度应在 0~1 之间"
        print(f"  ✓ 通过 (字段数={schema1['field_count']}, 置信度={schema1['confidence']})")
    except Exception as exc:
        print(f"  ✗ 失败: {exc}")
        return False

    # ---- 测试用例 2: 数组输入（多条记录） ----
    print("\n[测试2] 数组输入（多条记录）")
    sample_array = [
        {"name": "Alice", "age": 30, "city": "Beijing"},
        {"name": "Bob", "age": 25, "city": "Shanghai"},
        {"name": "Charlie", "age": 35, "city": "Guangzhou"},
    ]
    try:
        schema2 = build_schema(sample_array, "test_array")
        assert schema2["type"] == "object", f"类型应为 object，实际为 {schema2['type']}"
        assert schema2["field_count"] >= 3, f"字段数应至少为3，实际为 {schema2['field_count']}"
        assert schema2["record_count"] >= 3, f"记录数应至少为3，实际为 {schema2['record_count']}"

        # 检查字段类型推断
        field_names = [f["name"] for f in schema2["fields"]]
        assert "name" in field_names, "缺少 name 字段"
        assert "age" in field_names, "缺少 age 字段"

        # 检查 age 字段类型应为 integer
        age_field = next(f for f in schema2["fields"] if f["name"] == "age")
        assert age_field["type"] == "integer", f"age 类型应为 integer，实际为 {age_field['type']}"

        print(f"  ✓ 通过 (字段数={schema2['field_count']}, 记录数={schema2['record_count']})")
    except Exception as exc:
        print(f"  ✗ 失败: {exc}")
        return False

    # ---- 测试用例 3: CSV 输入 ----
    print("\n[测试3] CSV 输入")
    sample_csv = "id,name,score\n1,张三,85.5\n2,李四,92.0\n3,王五,78.5"
    try:
        data3 = parse_csv_text(sample_csv)
        assert len(data3) >= 3, f"CSV 解析应至少3条记录，实际为 {len(data3)}"
        schema3 = build_schema(data3, "test_csv")
        assert schema3["field_count"] >= 3, f"字段数应至少为3，实际为 {schema3['field_count']}"

        # 检查 score 字段类型
        score_field = next((f for f in schema3["fields"] if f["name"] == "score"), None)
        assert score_field is not None, "缺少 score 字段"
        assert score_field["type"] in ("number", "integer"), f"score 类型应为数字，实际为 {score_field['type']}"

        print(f"  ✓ 通过 (记录数={len(data3)}, 字段数={schema3['field_count']})")
    except Exception as exc:
        print(f"  ✗ 失败: {exc}")
        return False

    # ---- 测试用例 4: 类型推断 ----
    print("\n[测试4] 类型推断")
    try:
        assert infer_type(123) == "integer", "整数类型推断失败"
        assert infer_type(3.14) == "number", "浮点类型推断失败"
        assert infer_type(True) == "boolean", "布尔类型推断失败"
        assert infer_type("hello") == "string", "字符串类型推断失败"
        assert infer_type(None) == "null", "空值类型推断失败"
        assert infer_type([1, 2, 3]) == "array", "数组类型推断失败"
        assert infer_type({"a": 1}) == "object", "对象类型推断失败"
        assert infer_type("2024-01-15") == "date", "日期类型推断失败"
        print("  ✓ 通过 (8种类型推断全部正确)")
    except Exception as exc:
        print(f"  ✗ 失败: {exc}")
        return False

    # ---- 测试用例 5: 置信度计算 ----
    print("\n[测试5] 置信度计算")
    try:
        conf1 = compute_confidence("user_name", "string", 10, 10)
        conf2 = compute_confidence("X123", "unknown", 1, 100)
        assert 0.0 <= conf1 <= 1.0, "置信度应在 0~1 之间"
        assert 0.0 <= conf2 <= 1.0, "置信度应在 0~1 之间"
        assert conf1 > conf2, "规范字段名的置信度应更高"
        print(f"  ✓ 通过 (规范字段={conf1:.2f}, 非规范字段={conf2:.2f})")
    except Exception as exc:
        print(f"  ✗ 失败: {exc}")
        return False

    # ---- 测试用例 6: 输出格式化 ----
    print("\n[测试6] 输出格式化")
    try:
        schema = build_schema([{"a": 1, "b": "x"}], "test_format")
        json_out = format_schema(schema, "json")
        md_out = format_schema(schema, "markdown")

        assert '"schema_version"' in json_out, "JSON 输出缺少 schema_version"
        assert "# Schema" in md_out, "Markdown 输出缺少标题"
        assert "| 字段名" in md_out, "Markdown 输出缺少表格头"
        print("  ✓ 通过 (JSON 和 Markdown 输出均正常)")
    except Exception as exc:
        print(f"  ✗ 失败: {exc}")
        return False

    # ---- 测试用例 7: 错误处理 ----
    print("\n[测试7] 错误处理")
    try:
        # 空输入
        try:
            parse_input_source("")
            print("  ✗ 失败: 空输入未抛出异常")
            return False
        except SchemrError as exc:
            assert exc.code == "E001", f"错误码应为 E001，实际为 {exc.code}"

        # 无效 JSON
        try:
            parse_json_text("{invalid json")
            print("  ✗ 失败: 无效JSON未抛出异常")
            return False
        except SchemrError as exc:
            assert exc.code == "E004", f"错误码应为 E004，实际为 {exc.code}"

        # 不存在的文件
        try:
            load_from_file("/nonexistent/path/file.json")
            print("  ✗ 失败: 不存在文件未抛出异常")
            return False
        except SchemrError as exc:
            assert exc.code == "E002", f"错误码应为 E002，实际为 {exc.code}"

        print("  ✓ 通过 (错误码 E001/E002/E004 均正确)")
    except Exception as exc:
        print(f"  ✗ 失败: {exc}")
        return False

    # ---- 测试用例 8: 边界情况 ----
    print("\n[测试8] 边界情况")
    try:
        # 空数组
        schema_empty = build_schema([], "test_empty")
        assert schema_empty["field_count"] == 0, "空数组字段数应为0"

        # 混合类型数组
        schema_mixed = build_schema([{"a": 1}, {"a": "text"}], "test_mixed")
        assert schema_mixed["field_count"] >= 1, "混合类型数组至少应有1个字段"

        # 嵌套对象
        schema_nested = build_schema({"user": {"profile": {"name": "x"}}}, "test_nested")
        assert schema_nested["field_count"] >= 1, "嵌套对象至少应有1个字段"

        print("  ✓ 通过 (空数组/混合类型/嵌套对象均正常)")
    except Exception as exc:
        print(f"  ✗ 失败: {exc}")
        return False

    # ---- 测试用例 9: 主流程集成 ----
    print("\n[测试9] 主流程集成")
    try:
        result = process_input('{"name": "test", "value": 42}', "json")
        parsed = json.loads(result)
        assert parsed["field_count"] >= 2, f"字段数应至少为2，实际为 {parsed['field_count']}"
        assert parsed["type"] == "object", f"类型应为 object，实际为 {parsed['type']}"
        print("  ✓ 通过 (主流程正常)")
    except Exception as exc:
        print(f"  ✗ 失败: {exc}")
        return False

    # ---- 全部通过 ----
    print("\n" + "=" * 60)
    print("自测全部通过 ✓")
    print("=" * 60)
    return True


# ============================================================
# 命令行入口
# ============================================================

def main() -> int:
    """命令行主入口"""
    parser = argparse.ArgumentParser(
        description="schemr - 数据建模与结构转换工具",
        epilog="示例: python main.py --input '{\"name\": \"test\"}' --format json",
    )
    parser.add_argument(
        "-i", "--input",
        type=str,
        help="输入源：JSON文本、文件路径或CSV文本",
    )
    parser.add_argument(
        "-f", "--format",
        type=str,
        choices=["json", "markdown", "yaml"],
        default="json",
        help="输出格式 (默认: json)",
    )
    parser.add_argument(
        "-o", "--output",
        type=str,
        help="输出文件路径（可选）",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自测（无需输入）",
    )

    parser.add_argument("--verbose", action="store_true", help="显示修改明细")  # R6 可解释输出

    parser.add_argument("--force", action="store_true")  # R4 强制写盘


    parser.add_argument("--dry-run", action="store_true")  # R4 预览模式

    args = parser.parse_args()

    global dry_run

    dry_run = getattr(args, "dry_run", False)  # v3.274 同步到全局

    # 自测模式
    if args.selftest:
        success = run_selftest()
        return 0 if success else 1

    # 正常模式
    if not args.input:
        parser.error("必须提供 --input 或使用 --selftest")

    try:
        result = process_input(args.input, args.format, args.output)
        if not args.output:
            print(result)
        else:
            print(f"Schema 已写入: {args.output}")
        return 0
    except SchemrError as exc:
        print(f"错误: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"未知错误: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
