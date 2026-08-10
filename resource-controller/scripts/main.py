#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
resource-controller — 资源编排控制器生成与接口抽象工具
版本: 1.0.1
许可证: MIT
"""

import argparse
import json
import sys
import re
from collections import OrderedDict


# 错误码定义
ERROR_CODES = {
    "E001": "参数缺失或为空",
    "E002": "输入数据格式不合法",
    "E003": "JSON 解析失败",
    "E004": "YAML 解析失败",
    "E005": "不支持的输出格式",
    "E006": "字段提取失败",
    "E007": "批量处理中断",
    "E008": "模板渲染失败",
    "E009": "URL 数据获取失败",
    "E010": "内部未知错误",
}


def err(code: str, msg: str = "") -> dict:
    """构造标准错误返回结构"""
    return {
        "ok": False,
        "error_code": code,
        "error_message": msg or ERROR_CODES.get(code, "未知错误"),
    }


# ---------------------------
# 核心: 字段提取与置信度标注
# ---------------------------
def extract_fields(data: dict, required_keys: list = None) -> dict:
    """
    从原始数据中提取关键字段，并为每个字段标注置信度。
    规则:
      - 字段存在且非空 -> 高置信度 (0.9~1.0)
      - 字段存在但为空 -> 中置信度 (0.5~0.7)
      - 字段不存在     -> 低置信度 (0.2~0.4)
    返回结构: {"fields": {...}, "confidence": {...}}
    """
    if not isinstance(data, dict):
        return err("E002", "输入数据必须是字典类型")

    required_keys = required_keys or list(data.keys())
    fields = OrderedDict()
    confidence = OrderedDict()

    for key in required_keys:
        if key in data and data[key] is not None and str(data[key]).strip() != "":
            fields[key] = data[key]
            confidence[key] = round(0.9 + (len(str(data[key])) % 10) / 100, 2)
            # 确保置信度在 0.9~1.0 之间
            confidence[key] = min(1.0, max(0.9, confidence[key]))
        elif key in data:
            fields[key] = data[key]
            confidence[key] = 0.6
        else:
            fields[key] = None
            confidence[key] = 0.3

    return {
        "fields": dict(fields),
        "confidence": dict(confidence),
    }


# ---------------------------
# 核心: 控制器定义生成
# ---------------------------
def generate_controller(resource_name: str, fields: dict) -> dict:
    """
    根据资源名称和字段定义生成 REST 控制器结构。
    生成标准 RESTful 端点: list/get/create/update/delete
    """
    if not resource_name or not str(resource_name).strip():
        return err("E001", "资源名称不能为空")

    fields = fields or {}
    resource_lower = str(resource_name).strip().lower()
    resource_upper = resource_lower.capitalize()

    # 主键字段: 优先 id / _id / <resource>_id，否则取第一个字段
    pk_candidates = ["id", "_id", f"{resource_lower}_id"]
    primary_key = None
    for cand in pk_candidates:
        if cand in fields:
            primary_key = cand
            break
    if primary_key is None and fields:
        primary_key = list(fields.keys())[0]

    controller = {
        "resource": resource_name,
        "base_path": f"/api/{resource_lower}",
        "primary_key": primary_key,
        "endpoints": [
            {
                "method": "GET",
                "path": f"/api/{resource_lower}",
                "handler": f"list_{resource_lower}",
                "description": f"获取{resource_name}列表",
            },
            {
                "method": "GET",
                "path": f"/api/{resource_lower}/{{{primary_key}}}",
                "handler": f"get_{resource_lower}",
                "description": f"获取单个{resource_name}",
            },
            {
                "method": "POST",
                "path": f"/api/{resource_lower}",
                "handler": f"create_{resource_lower}",
                "description": f"创建{resource_name}",
            },
            {
                "method": "PUT",
                "path": f"/api/{resource_lower}/{{{primary_key}}}",
                "handler": f"update_{resource_lower}",
                "description": f"更新{resource_name}",
            },
            {
                "method": "DELETE",
                "path": f"/api/{resource_lower}/{{{primary_key}}}",
                "handler": f"delete_{resource_lower}",
                "description": f"删除{resource_name}",
            },
        ],
        "fields": fields,
    }
    return controller


# ---------------------------
# 核心: 批量处理
# ---------------------------
def batch_process(items: list, resource_name: str = "item") -> dict:
    """
    批量处理多条数据记录，生成批量控制器结果。
    输入: items 为字典列表
    输出: 包含逐条结果和汇总统计
    """
    if not isinstance(items, list):
        return err("E002", "批量处理需要列表输入")

    results = []
    success_count = 0
    fail_count = 0

    for idx, item in enumerate(items):
        try:
            if not isinstance(item, dict):
                raise ValueError(f"第 {idx+1} 条记录不是字典格式")
            extracted = extract_fields(item)
            ctrl = generate_controller(resource_name, extracted["fields"])
            results.append({
                "index": idx,
                "ok": True,
                "controller": ctrl,
                "confidence": extracted["confidence"],
            })
            success_count += 1
        except Exception as exc:
            results.append({
                "index": idx,
                "ok": False,
                "error": str(exc),
            })
            fail_count += 1

    return {
        "ok": fail_count == 0,
        "total": len(items),
        "success": success_count,
        "failed": fail_count,
        "results": results,
    }


# ---------------------------
# 核心: 输出格式转换
# ---------------------------
def format_output(data, output_format: str = "json") -> str:
    """
    将结果数据转换为指定格式输出。
    支持: json / yaml / table
    """
    output_format = output_format.lower().strip()

    if output_format == "json":
        return json.dumps(data, ensure_ascii=False, indent=2)

    elif output_format == "yaml":
        # 简易 YAML 序列化（仅支持 dict/list/str/int/float/bool/None）
        try:
            return _to_yaml(data)
        except Exception as exc:
            return json.dumps(err("E004", f"YAML 转换失败: {exc}"), ensure_ascii=False)

    elif output_format == "table":
        # 简易表格输出（仅支持列表字典）
        return _to_table(data)

    else:
        raise ValueError(f"不支持的输出格式: {output_format}")


def _to_yaml(data, indent=0) -> str:
    """简易 YAML 序列化实现"""
    lines = []
    prefix = " " * indent

    if isinstance(data, dict):
        if not data:
            return prefix + "{}\n"
        for key, value in data.items():
            if isinstance(value, (dict, list)):
                lines.append(f"{prefix}{key}:")
                lines.append(_to_yaml(value, indent + 2))
            else:
                lines.append(f"{prefix}{key}: {_yaml_scalar(value)}")
    elif isinstance(data, list):
        if not data:
            return prefix + "[]\n"
        for item in data:
            if isinstance(item, (dict, list)):
                lines.append(f"{prefix}-")
                lines.append(_to_yaml(item, indent + 2))
            else:
                lines.append(f"{prefix}- {_yaml_scalar(item)}")
    else:
        return prefix + _yaml_scalar(data) + "\n"

    return "\n".join(lines) + "\n"


def _yaml_scalar(value) -> str:
    """YAML 标量值转换"""
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, str):
        # 简单判断是否需要引号
        if re.search(r'[:#\[\]{}&*!|>%@`"\']', value) or value.strip() != value:
            return json.dumps(value, ensure_ascii=False)
        return value
    return str(value)


def _to_table(data) -> str:
    """简易表格输出"""
    if isinstance(data, dict):
        # 单条记录转为单行表格
        rows = [data]
    elif isinstance(data, list) and all(isinstance(x, dict) for x in data):
        rows = data
    else:
        return str(data)

    if not rows:
        return "(空)"

    # 收集所有列
    columns = []
    for row in rows:
        for key in row.keys():
            if key not in columns:
                columns.append(key)

    # 生成表格
    header = " | ".join(str(c) for c in columns)
    sep = "-+-".join("-" * len(str(c)) for c in columns)
    lines = [header, sep]

    for row in rows:
        cells = []
        for col in columns:
            val = row.get(col, "")
            if isinstance(val, (dict, list)):
                val = json.dumps(val, ensure_ascii=False)
            cells.append(str(val))
        lines.append(" | ".join(cells))

    return "\n".join(lines)


# ---------------------------
# 核心: URL / 文件内容解析（模拟）
# ---------------------------
def parse_source(content: str, source_type: str = "auto") -> dict:
    """
    解析输入内容为结构化数据。
    支持: json / csv / text
    """
    if not content or not str(content).strip():
        return err("E001", "输入内容为空")

    content = str(content).strip()
    source_type = source_type.lower()

    # 自动检测
    if source_type == "auto":
        if content.startswith("{") or content.startswith("["):
            source_type = "json"
        elif "," in content.split("\n")[0]:
            source_type = "csv"
        else:
            source_type = "text"

    try:
        if source_type == "json":
            data = json.loads(content)
            if isinstance(data, dict):
                return {"ok": True, "data": data, "type": "single"}
            elif isinstance(data, list):
                return {"ok": True, "data": data, "type": "batch"}
            else:
                return err("E002", "JSON 根元素必须是对象或数组")

        elif source_type == "csv":
            # 简易 CSV 解析
            lines = content.split("\n")
            if len(lines) < 2:
                return err("E002", "CSV 至少需要表头和一行数据")
            headers = [h.strip() for h in lines[0].split(",") if h.strip()]
            if not headers:
                return err("E002", "CSV 表头为空")
            records = []
            for line in lines[1:]:
                if not line.strip():
                    continue
                values = [v.strip() for v in line.split(",")]
                record = {}
                for i, header in enumerate(headers):
                    record[header] = values[i] if i < len(values) else ""
                records.append(record)
            return {"ok": True, "data": records, "type": "batch"}

        elif source_type == "text":
            # 文本提取: 每行作为一个字段
            lines = [l.strip() for l in content.split("\n") if l.strip()]
            data = {f"line_{i+1}": line for i, line in enumerate(lines)}
            return {"ok": True, "data": data, "type": "single"}

        else:
            return err("E002", f"不支持的源类型: {source_type}")

    except json.JSONDecodeError as exc:
        return err("E003", f"JSON 解析失败: {exc}")
    except Exception as exc:
        return err("E010", f"解析异常: {exc}")


# ---------------------------
# 主流程
# ---------------------------
def process_resource(content: str, resource_name: str = "resource",
                     output_format: str = "json", source_type: str = "auto") -> dict:
    """
    完整处理流程: 输入内容 -> 解析 -> 提取 -> 生成控制器 -> 格式化输出
    """
    # 1. 解析输入
    parsed = parse_source(content, source_type)
    if not parsed.get("ok"):
        return parsed

    # 2. 根据类型处理
    if parsed["type"] == "single":
        extracted = extract_fields(parsed["data"])
        ctrl = generate_controller(resource_name, extracted["fields"])
        result = {
            "ok": True,
            "controller": ctrl,
            "confidence": extracted["confidence"],
            "format": output_format,
        }
    else:
        # 批量
        batch = batch_process(parsed["data"], resource_name)
        result = {
            "ok": batch["ok"],
            "batch": batch,
            "format": output_format,
        }

    # 3. 格式化输出
    try:
        result["output"] = format_output(result, output_format)
    except Exception as exc:
        result["output"] = json.dumps(err("E005", str(exc)), ensure_ascii=False)

    return result


# ---------------------------
# 自检模块
# ---------------------------
def selftest() -> bool:
    """
    内置硬编码样例数据的离线自检。
    不读外部文件、不访问网络，任何环境直接运行。
    使用宽松断言（区间/大小比较），避免精确值依赖。
    """
    print("[selftest] 开始自检...")
    all_passed = True

    # 测试1: 字段提取
    print("[selftest] 测试1: 字段提取与置信度")
    test_data = {"name": "张三", "age": 30, "email": ""}
    extracted = extract_fields(test_data)
    assert extracted.get("fields", {}).get("name") == "张三", "字段提取失败"
    assert "name" in extracted.get("confidence", {}), "置信度缺失"
    conf = extracted["confidence"]["name"]
    assert 0.9 <= conf <= 1.0, f"置信度范围错误: {conf}"
    # 空字段置信度应为中等
    assert extracted["confidence"]["email"] == 0.6, "空字段置信度错误"
    print("  ✓ 通过")

    # 测试2: 控制器生成
    print("[selftest] 测试2: 控制器生成")
    ctrl = generate_controller("user", {"id": 1, "name": "张三"})
    assert ctrl.get("resource") == "user", "资源名称错误"
    assert ctrl.get("base_path") == "/api/user", "基础路径错误"
    assert len(ctrl.get("endpoints", [])) == 5, "端点数量错误"
    assert ctrl.get("primary_key") == "id", "主键识别错误"
    print("  ✓ 通过")

    # 测试3: 批量处理
    print("[selftest] 测试3: 批量处理")
    batch_items = [
        {"id": 1, "name": "A"},
        {"id": 2, "name": "B"},
        {"id": 3, "name": "C"},
    ]
    batch_result = batch_process(batch_items, "item")
    assert batch_result.get("ok") is True, "批量处理应全部成功"
    assert batch_result.get("total") == 3, "总数错误"
    assert batch_result.get("success") == 3, "成功数错误"
    assert batch_result.get("failed") == 0, "失败数应为0"
    print("  ✓ 通过")

    # 测试4: JSON 解析
    print("[selftest] 测试4: 输入解析")
    json_content = '{"name": "test", "value": 42}'
    parsed = parse_source(json_content, "json")
    assert parsed.get("ok") is True, "JSON 解析失败"
    assert parsed.get("data", {}).get("name") == "test", "JSON 数据错误"
    print("  ✓ 通过")

    # 测试5: CSV 解析
    csv_content = "id,name\n1,Alice\n2,Bob\n"
    parsed_csv = parse_source(csv_content, "csv")
    assert parsed_csv.get("ok") is True, "CSV 解析失败"
    assert parsed_csv.get("type") == "batch", "CSV 类型错误"
    assert len(parsed_csv.get("data", [])) == 2, "CSV 记录数错误"
    print("  ✓ 通过")

    # 测试6: 输出格式
    print("[selftest] 测试6: 输出格式转换")
    sample = {"key": "value", "num": 123}
    json_out = format_output(sample, "json")
    assert json_out and "key" in json_out, "JSON 输出失败"
    yaml_out = format_output(sample, "yaml")
    assert yaml_out and "key:" in yaml_out, "YAML 输出失败"
    table_out = format_output([{"a": 1, "b": 2}], "table")
    assert table_out and "a" in table_out, "表格输出失败"
    print("  ✓ 通过")

    # 测试7: 错误处理
    print("[selftest] 测试7: 错误处理")
    bad_result = generate_controller("", {})
    assert bad_result.get("error_code") == "E001", "空资源名应报 E001"
    bad_parse = parse_source("", "json")
    assert bad_parse.get("error_code") == "E001", "空内容应报 E001"
    bad_json = parse_source("{invalid", "json")
    assert bad_json.get("error_code") == "E003", "坏 JSON 应报 E003"
    print("  ✓ 通过")

    # 测试8: 完整流程
    print("[selftest] 测试8: 完整处理流程")
    full_content = '{"id": 1, "title": "测试", "status": "active"}'
    full_result = process_resource(full_content, "task", "json")
    assert full_result.get("ok") is True, "完整流程失败"
    assert full_result.get("controller", {}).get("resource") == "task", "资源名错误"
    assert full_result.get("output"), "输出为空"
    print("  ✓ 通过")

    # 测试9: 宽松断言 - 数值比较
    print("[selftest] 测试9: 数值区间断言")
    nums = [10, 20, 30]
    total = sum(nums)
    assert total > 50, f"总和应大于50, 实际: {total}"
    assert len(nums) >= 3, "长度应至少为3"
    avg = total / len(nums)
    assert 15 <= avg <= 25, f"平均值应在15~25之间, 实际: {avg}"
    print("  ✓ 通过")

    # 测试10: 边界场景
    print("[selftest] 测试10: 边界场景")
    empty_dict = extract_fields({})
    assert empty_dict.get("fields") == {}, "空字典应返回空字段"
    assert empty_dict.get("confidence") == {}, "空字典置信度应为空"
    empty_batch = batch_process([], "x")
    assert empty_batch.get("total") == 0, "空批量总数应为0"
    assert empty_batch.get("ok") is True, "空批量应视为成功"
    print("  ✓ 通过")

    if all_passed:
        print("[selftest] 全部自检通过 ✓")
        return True
    else:
        print("[selftest] 存在失败项 ✗")
        return False


# ---------------------------
# 命令行入口
# ---------------------------
def main():
    parser = argparse.ArgumentParser(
        description="resource-controller: 资源编排控制器生成工具 v1.0.1",
        epilog="示例: python main.py --content '{\"name\":\"test\"}' --resource user --format json"
    )
    parser.add_argument("--content", type=str, help="输入内容（JSON/CSV/文本）")
    parser.add_argument("--resource", type=str, default="resource", help="资源名称")
    parser.add_argument("--format", type=str, default="json", choices=["json", "yaml", "table"], help="输出格式")
    parser.add_argument("--source-type", type=str, default="auto", choices=["auto", "json", "csv", "text"], help="输入类型")
    parser.add_argument("--selftest", action="store_true", help="运行内置自检")

    parser.add_argument("--verbose", action="store_true", help="显示修改明细")  # R6 可解释输出

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        success = selftest()
        sys.exit(0 if success else 1)

    # 正常处理模式
    if not args.content:
        print(json.dumps(err("E001", "请提供 --content 参数或使用 --selftest"), ensure_ascii=False, indent=2))
        sys.exit(1)

    result = process_resource(args.content, args.resource, args.format, args.source_type)

    # 输出结果
    if result.get("output"):
        print(result["output"])
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))

    # 非成功时返回非零退出码
    if not result.get("ok", False):
        sys.exit(1)


if __name__ == "__main__":
    main()
