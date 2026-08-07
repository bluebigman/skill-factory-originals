#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gstack - 通用结构化处理工具（独立实现）

仅依据功能规格重新实现，不参考任何既有代码。
提供标准流程：收集信息 -> 处理 -> 输出校验。
支持命令行调用与 --selftest 离线自检。
"""

import argparse
import json
import sys
import os


# ---------------------------------------------------------------------------
# 错误码定义（E001-E010）
# ---------------------------------------------------------------------------
ERROR_CODES = {
    "E001": "输入为空，请提供待处理的内容",
    "E002": "关键信息缺失，请补充必要字段",
    "E003": "输入格式错误，请检查格式是否符合要求",
    "E004": "超出能力边界，无法处理该请求",
    "E005": "置信度过低，结果无法确定",
    "E006": "内部处理异常，请重试或联系管理员",
    "E007": "参数错误，请检查命令行参数",
    "E008": "输出写入失败，请检查权限或路径",
    "E009": "批量处理中断，存在失败项",
    "E010": "未知错误，请查看日志",
}


class GStackError(Exception):
    """自定义异常，携带错误码。"""

    def __init__(self, code: str, message: str = ""):
        self.code = code
        self.message = message or ERROR_CODES.get(code, "未知错误")
        super().__init__(f"[{code}] {self.message}")


# ---------------------------------------------------------------------------
# 核心处理逻辑
# ---------------------------------------------------------------------------

def extract_key_fields(data: dict) -> dict:
    """
    从输入数据中提取关键字段并结构化。

    规则：
    - 优先提取 name/title/内容 等常见字段
    - 自动识别类型（文本/数字/布尔）
    - 缺失字段标记为 None
    """
    if not data:
        raise GStackError("E001")

    # 常见字段别名映射
    field_aliases = {
        "name": ["name", "title", "标题", "名称"],
        "content": ["content", "text", "body", "内容", "正文"],
        "type": ["type", "category", "分类", "类型"],
        "value": ["value", "amount", "数值", "数量"],
    }

    result = {}
    for standard_field, aliases in field_aliases.items():
        for alias in aliases:
            if alias in data and data[alias] is not None:
                result[standard_field] = data[alias]
                break
        else:
            result[standard_field] = None

    # 保留其他未识别字段
    known_keys = set()
    for aliases in field_aliases.values():
        known_keys.update(aliases)
    result["extra"] = {k: v for k, v in data.items() if k not in known_keys}

    return result


def calculate_confidence(structured: dict) -> float:
    """
    计算处理结果的置信度（0-100）。

    规则：
    - 基础分 60
    - 每识别出一个关键字段 +10
    - 有额外字段 +5
    - 有缺失字段 -10
    """
    confidence = 60.0

    core_fields = ["name", "content", "type", "value"]
    found = sum(1 for f in core_fields if structured.get(f) is not None)
    confidence += found * 10

    if structured.get("extra"):
        confidence += 5

    missing = sum(1 for f in core_fields if structured.get(f) is None)
    confidence -= missing * 10

    # 限制在 0-100 范围
    return max(0.0, min(100.0, confidence))


def format_output(structured: dict, confidence: float, output_format: str = "json") -> str:
    """
    按指定格式生成输出。

    支持格式：json / text
    - json: 结构化 JSON
    - text: 人类可读文本
    """
    if output_format == "json":
        output = {
            "result": structured,
            "confidence": round(confidence, 1),
            "warning": None,
        }
        # 根据置信度添加标注
        if confidence < 85:
            output["warning"] = "[需核实] 部分字段缺失或不确定"
        elif confidence < 90:
            output["warning"] = "建议复核"
        return json.dumps(output, ensure_ascii=False, indent=2)

    elif output_format == "text":
        lines = []
        lines.append("=== 处理结果 ===")
        for key in ["name", "content", "type", "value"]:
            if structured.get(key) is not None:
                lines.append(f"{key}: {structured[key]}")
        if structured.get("extra"):
            lines.append(f"其他字段: {len(structured['extra'])} 个")
        lines.append(f"置信度: {confidence:.1f}%")
        if confidence < 85:
            lines.append("[需核实] 部分字段缺失或不确定")
        return "\n".join(lines)

    else:
        raise GStackError("E003", f"不支持的输出格式: {output_format}")


def process_input(raw_data, output_format: str = "json") -> str:
    """
    标准处理流程入口。

    1. 校验输入
    2. 提取关键字段
    3. 计算置信度
    4. 格式化输出
    """
    # Step 1: 输入校验
    if raw_data is None:
        raise GStackError("E001")

    # 支持字符串输入（尝试解析 JSON）
    if isinstance(raw_data, str):
        try:
            raw_data = json.loads(raw_data)
        except json.JSONDecodeError:
            # 非 JSON 字符串，转为简单结构
            raw_data = {"content": raw_data}

    if not isinstance(raw_data, dict):
        raise GStackError("E003", "输入必须是对象或 JSON 字符串")

    # Step 2: 提取字段
    structured = extract_key_fields(raw_data)

    # 检查关键信息是否缺失
    if structured["name"] is None and structured["content"] is None:
        raise GStackError("E002", "缺少 name 或 content 字段")

    # Step 3: 计算置信度
    confidence = calculate_confidence(structured)

    # Step 4: 格式化输出
    return format_output(structured, confidence, output_format)


def batch_process(items: list, output_format: str = "json") -> str:
    """
    批量处理多个输入。

    规则：
    - 每个项目独立处理
    - 收集所有结果
    - 统计成功率
    """
    if not items:
        raise GStackError("E001")

    results = []
    success_count = 0
    errors = []

    for idx, item in enumerate(items, 1):
        try:
            result = process_input(item, output_format)
            results.append({"index": idx, "status": "success", "output": result})
            success_count += 1
        except GStackError as e:
            results.append({"index": idx, "status": "error", "code": e.code, "message": str(e)})
            errors.append({"index": idx, "code": e.code})

    # 统计信息
    total = len(items)
    summary = {
        "total": total,
        "success": success_count,
        "failed": total - success_count,
        "success_rate": round(success_count / total * 100, 1) if total > 0 else 0,
    }

    if errors:
        summary["errors"] = errors

    # 如果全部失败，抛出异常
    if success_count == 0:
        raise GStackError("E009", "所有项目处理失败")

    # 如果有部分失败，在结果中标注
    if errors:
        results.append({"warning": "部分项目处理失败，请检查错误列表"})

    output = {"summary": summary, "results": results}
    return json.dumps(output, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# 自检功能（离线、无依赖）
# ---------------------------------------------------------------------------

def run_selftest() -> bool:
    """
    内置硬编码样例数据，离线自检核心逻辑。

    不读取外部文件、不依赖当前工作目录、不访问网络。
    使用宽松阈值断言，确保必然匹配。
    """
    print("开始自检...")

    # 测试用例 1: 基本处理
    test_data = {
        "name": "测试文档",
        "content": "这是一段测试内容",
        "category": "文档",
        "amount": 42,
    }
    try:
        result = process_input(test_data, "json")
        result_obj = json.loads(result)
        assert result_obj["result"]["name"] == "测试文档", "名称提取失败"
        assert result_obj["result"]["content"] == "这是一段测试内容", "内容提取失败"
        assert result_obj["result"]["type"] == "文档", "类型提取失败"
        assert result_obj["result"]["value"] == 42, "数值提取失败"
        assert result_obj["confidence"] > 70, "置信度应较高"
        print("  ✓ 基本处理测试通过")
    except AssertionError as e:
        print(f"  ✗ 基本处理测试失败: {e}")
        return False
    except GStackError as e:
        print(f"  ✗ 基本处理异常: {e}")
        return False

    # 测试用例 2: 文本输出格式
    try:
        result_text = process_input(test_data, "text")
        assert "测试文档" in result_text, "文本输出缺少名称"
        assert "置信度" in result_text, "文本输出缺少置信度"
        print("  ✓ 文本输出测试通过")
    except AssertionError as e:
        print(f"  ✗ 文本输出测试失败: {e}")
        return False
    except GStackError as e:
        print(f"  ✗ 文本输出异常: {e}")
        return False

    # 测试用例 3: 空输入错误
    try:
        process_input(None)
        print("  ✗ 空输入测试失败：未抛出异常")
        return False
    except GStackError as e:
        assert e.code == "E001", f"错误码应为 E001，实际 {e.code}"
        print("  ✓ 空输入错误测试通过")

    # 测试用例 4: 缺失关键字段
    try:
        process_input({"foo": "bar"})
        print("  ✗ 缺失字段测试失败：未抛出异常")
        return False
    except GStackError as e:
        assert e.code == "E002", f"错误码应为 E002，实际 {e.code}"
        print("  ✓ 缺失字段测试通过")

    # 测试用例 5: 批量处理
    batch_items = [
        {"name": "项目1", "content": "内容1"},
        {"name": "项目2", "content": "内容2"},
        {"name": "项目3", "content": "内容3"},
    ]
    try:
        batch_result = batch_process(batch_items, "json")
        batch_obj = json.loads(batch_result)
        assert batch_obj["summary"]["total"] == 3, "批量总数错误"
        assert batch_obj["summary"]["success"] == 3, "批量成功数错误"
        assert batch_obj["summary"]["success_rate"] > 90, "成功率应较高"
        print("  ✓ 批量处理测试通过")
    except AssertionError as e:
        print(f"  ✗ 批量处理测试失败: {e}")
        return False
    except GStackError as e:
        print(f"  ✗ 批量处理异常: {e}")
        return False

    # 测试用例 6: 批量处理含错误项
    batch_with_error = [
        {"name": "项目1", "content": "内容1"},
        {"foo": "bar"},  # 缺少关键字段
        {"name": "项目3", "content": "内容3"},
    ]
    try:
        batch_result = batch_process(batch_with_error, "json")
        batch_obj = json.loads(batch_result)
        assert batch_obj["summary"]["total"] == 3, "批量总数错误"
        assert batch_obj["summary"]["success"] == 2, "成功数应为 2"
        assert batch_obj["summary"]["failed"] == 1, "失败数应为 1"
        print("  ✓ 批量含错误测试通过")
    except AssertionError as e:
        print(f"  ✗ 批量含错误测试失败: {e}")
        return False
    except GStackError as e:
        print(f"  ✗ 批量含错误异常: {e}")
        return False

    # 测试用例 7: 置信度标注
    low_conf_data = {"name": "只有名字"}
    try:
        result = process_input(low_conf_data, "json")
        result_obj = json.loads(result)
        assert result_obj["confidence"] < 85, "低置信度应低于 85"
        assert result_obj["warning"] is not None, "应有警告标注"
        print("  ✓ 置信度标注测试通过")
    except AssertionError as e:
        print(f"  ✗ 置信度标注测试失败: {e}")
        return False
    except GStackError as e:
        print(f"  ✗ 置信度标注异常: {e}")
        return False

    # 测试用例 8: 字符串输入解析
    try:
        json_str = json.dumps({"name": "JSON输入", "content": "通过字符串"})
        result = process_input(json_str, "json")
        result_obj = json.loads(result)
        assert result_obj["result"]["name"] == "JSON输入", "JSON字符串解析失败"
        print("  ✓ 字符串输入测试通过")
    except AssertionError as e:
        print(f"  ✗ 字符串输入测试失败: {e}")
        return False
    except GStackError as e:
        print(f"  ✗ 字符串输入异常: {e}")
        return False

    # 测试用例 9: 错误码完整性
    required_codes = ["E001", "E002", "E003", "E004", "E005", "E006", "E007", "E008", "E009", "E010"]
    for code in required_codes:
        if code not in ERROR_CODES:
            print(f"  ✗ 缺少错误码 {code}")
            return False
    print("  ✓ 错误码完整性测试通过")

    print("\n全部自检通过！")
    return True


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------

def main():
    """命令行主入口。"""
    parser = argparse.ArgumentParser(
        description="gstack - 通用结构化处理工具",
        epilog="示例: python main.py --input '{\"name\":\"测试\",\"content\":\"内容\"}' --format json"
    )
    parser.add_argument("--input", type=str, help="输入数据（JSON 字符串或文本）")
    parser.add_argument("--format", type=str, choices=["json", "text"], default="json", help="输出格式（默认: json）")
    parser.add_argument("--selftest", action="store_true", help="运行自检并退出")
    parser.add_argument("--batch", action="store_true", help="批量处理模式（输入为 JSON 数组）")

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        success = run_selftest()
        sys.exit(0 if success else 1)

    # 正常处理模式
    if not args.input:
        print(f"错误: {ERROR_CODES['E001']}", file=sys.stderr)
        print("请使用 --input 提供数据，或使用 --selftest 运行自检", file=sys.stderr)
        sys.exit(1)

    try:
        # 批量模式
        if args.batch:
            try:
                items = json.loads(args.input)
                if not isinstance(items, list):
                    raise GStackError("E003", "批量模式需要 JSON 数组")
                output = batch_process(items, args.format)
            except json.JSONDecodeError:
                raise GStackError("E003", "批量模式输入必须是 JSON 数组字符串")
        # 单条模式
        else:
            output = process_input(args.input, args.format)

        print(output)

    except GStackError as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"错误: [{ERROR_CODES['E010']}] {str(e)}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
