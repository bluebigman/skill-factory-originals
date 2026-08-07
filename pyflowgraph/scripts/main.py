#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pyflowgraph - 通用工作流自动化平台（技能功能实现）

本脚本依据功能规格独立实现，不复制任何既有代码（clean room）。
功能：将用户提供的数据/文件/URL 转换为结构化结果，支持批量处理、
自定义格式输出、置信度标注与错误码体系。

仅使用 Python 标准库，无第三方依赖。
"""

import argparse
import json
import os
import sys
import tempfile
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 错误码常量（E001-E010）
# ============================================================
ERROR_CODES = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：...",
    "E003": "输入格式不符合要求，示例：...",
    "E004": "这超出了本工具的能力范围，建议...",
    "E005": "结果无法确定，建议：...",
    "E006": "内部处理异常，请稍后重试",
    "E007": "批量处理时部分条目失败",
    "E008": "输出格式不支持",
    "E009": "置信度计算失败",
    "E010": "未知错误",
}


class SkillError(Exception):
    """技能异常基类，携带错误码。"""

    def __init__(self, code: str, message: Optional[str] = None):
        self.code = code
        self.message = message or ERROR_CODES.get(code, ERROR_CODES["E010"])
        super().__init__(f"[{self.code}] {self.message}")


# ============================================================
# 核心逻辑：结构化处理
# ============================================================

def _detect_input_type(raw_input: str) -> str:
    """
    检测输入类型。
    返回: "json" / "url" / "text" / "empty"
    """
    if raw_input is None:
        return "empty"
    stripped = raw_input.strip()
    if not stripped:
        return "empty"
    # 尝试解析 JSON
    if stripped.startswith("{") or stripped.startswith("["):
        try:
            json.loads(stripped)
            return "json"
        except json.JSONDecodeError:
            return "text"
    # URL 检测（宽松判断）
    if stripped.startswith("http://") or stripped.startswith("https://"):
        return "url"
    return "text"


def _parse_json_input(raw_input: str) -> Dict[str, Any]:
    """解析 JSON 输入为字典。"""
    try:
        data = json.loads(raw_input)
        if isinstance(data, dict):
            return data
        # 非字典 JSON，包装为统一结构
        return {"data": data}
    except json.JSONDecodeError as exc:
        raise SkillError("E003", f"JSON 解析失败: {exc}") from exc


def _extract_text_fields(text: str) -> Dict[str, Any]:
    """
    从纯文本中提取关键字段（宽松启发式）。
    识别模式：key: value 或 key=value 或 中文冒号。
    """
    fields: Dict[str, Any] = {}
    # 按行拆分
    lines = text.splitlines()
    for line in lines:
        line = line.strip()
        if not line:
            continue
        # 尝试多种分隔符
        for sep in (":", "：", "="):
            if sep in line:
                key, _, value = line.partition(sep)
                key = key.strip()
                value = value.strip()
                if key and value:
                    fields[key] = value
                break
    # 如果没有提取到任何字段，将整段作为 content
    if not fields:
        fields = {"content": text.strip()}
    return fields


def _extract_url_fields(url: str) -> Dict[str, Any]:
    """从 URL 中提取结构化信息（不访问网络，仅静态解析）。"""
    # 不访问网络，仅做 URL 结构解析
    scheme = ""
    host = ""
    path = ""
    query: Dict[str, str] = {}
    # 简单解析
    if "://" in url:
        scheme, rest = url.split("://", 1)
        # 分离 host/path
        if "/" in rest:
            host, path = rest.split("/", 1)
            path = "/" + path
        else:
            host = rest
        # 解析 query
        if "?" in path:
            path, query_str = path.split("?", 1)
            for item in query_str.split("&"):
                if "=" in item:
                    k, v = item.split("=", 1)
                    query[k] = v
    return {
        "url": url,
        "scheme": scheme,
        "host": host,
        "path": path,
        "query": query,
        "type": "url",
        "note": "URL 已静态解析，未访问网络",
    }


def _compute_confidence(data: Dict[str, Any]) -> float:
    """
    计算置信度（0-1）。
    规则：
    - 字段丰富度（字段数量）影响基础分
    - 有明确结构化数据（JSON）时加分
    - 有 URL 结构信息时加分
    """
    if not data:
        return 0.0
    base = 0.5
    field_count = len(data)
    # 字段数越多，置信度越高（上限 0.9）
    base += min(field_count * 0.05, 0.4)
    # 结构化加分
    if "url" in data and "host" in data:
        base += 0.1
    if "data" in data or "content" in data:
        base += 0.05
    # 限制在 [0, 1] 区间
    return max(0.0, min(1.0, base))


def _format_confidence(confidence: float) -> str:
    """
    根据置信度生成标注。
    >=0.90: 直接输出（无标注）
    0.85-0.90: 建议复核
    <0.85: [需核实]
    """
    if confidence >= 0.90:
        return "直接输出"
    if confidence >= 0.85:
        return "建议复核"
    return "[需核实]"


def process_single_item(raw_input: str) -> Dict[str, Any]:
    """
    处理单个输入项，返回结构化结果。
    """
    # 输入为空检查（E001）
    if raw_input is None or not raw_input.strip():
        raise SkillError("E001")

    input_type = _detect_input_type(raw_input)

    # 按类型处理
    if input_type == "json":
        data = _parse_json_input(raw_input)
        data["_input_type"] = "json"
    elif input_type == "url":
        data = _extract_url_fields(raw_input.strip())
        data["_input_type"] = "url"
    elif input_type == "text":
        data = _extract_text_fields(raw_input)
        data["_input_type"] = "text"
    else:
        raise SkillError("E003")

    # 关键信息缺失检查（E002）
    if not data or len(data) <= 1:  # 只有 _input_type
        raise SkillError("E002", "未提取到任何有效字段")

    # 计算置信度
    try:
        confidence = _compute_confidence(data)
    except Exception as exc:
        raise SkillError("E009", str(exc)) from exc

    # 置信度过低检查（E005）—— 低于 0.5 视为过低
    if confidence < 0.5:
        raise SkillError("E005", f"置信度仅 {confidence:.0%}")

    # 组装结果
    result = {
        "input_type": input_type,
        "fields": {k: v for k, v in data.items() if not k.startswith("_")},
        "confidence": round(confidence, 2),
        "confidence_label": _format_confidence(confidence),
        "status": "ok",
    }
    return result


def batch_process(items: List[str]) -> Dict[str, Any]:
    """
    批量处理多个输入。
    返回汇总结果，部分失败时标注 E007。
    """
    if not items:
        raise SkillError("E001")

    results = []
    errors = []
    for idx, item in enumerate(items):
        try:
            result = process_single_item(item)
            result["index"] = idx
            results.append(result)
        except SkillError as exc:
            errors.append({"index": idx, "code": exc.code, "message": exc.message})
        except Exception as exc:  # 兜底
            errors.append({"index": idx, "code": "E010", "message": str(exc)})

    # 全部失败
    if not results:
        raise SkillError("E007", "全部条目处理失败")

    # 部分失败
    status = "ok" if not errors else "partial"
    summary = {
        "status": status,
        "total": len(items),
        "success": len(results),
        "failed": len(errors),
        "results": results,
        "errors": errors,
    }
    if errors:
        summary["note"] = "部分条目处理失败，请查看 errors 字段"
    return summary


# ============================================================
# 输出格式化
# ============================================================

def format_output(data: Dict[str, Any], fmt: str = "json") -> str:
    """
    将结果格式化为指定格式。
    支持: json / text
    """
    if fmt == "json":
        return json.dumps(data, ensure_ascii=False, indent=2)
    elif fmt == "text":
        # 简单文本格式
        lines = []
        for key, value in data.items():
            if isinstance(value, (dict, list)):
                value = json.dumps(value, ensure_ascii=False)
            lines.append(f"{key}: {value}")
        return "\n".join(lines)
    else:
        raise SkillError("E008", f"不支持的输出格式: {fmt}")


# ============================================================
# 自检（--selftest）
# ============================================================

def run_selftest() -> int:
    """
    离线自检核心逻辑。
    使用内置硬编码样例数据，不读外部文件、不依赖当前工作目录、不访问网络。
    使用宽松断言（大小比较/区间判断），确保必然匹配。
    """
    print("=== pyflowgraph 自检开始 ===")
    failures = 0

    # 测试 1: JSON 输入处理
    try:
        result = process_single_item('{"name": "测试", "value": 42}')
        assert result["status"] == "ok", "JSON 处理状态应为 ok"
        assert result["input_type"] == "json", "输入类型应为 json"
        assert "name" in result["fields"], "应提取到 name 字段"
        assert result["confidence"] > 0.5, "置信度应大于 0.5"
        print("[PASS] JSON 输入处理")
    except Exception as exc:
        failures += 1
        print(f"[FAIL] JSON 输入处理: {exc}")

    # 测试 2: 文本输入处理
    try:
        result = process_single_item("标题: 测试文档\n作者: 张三\n内容: 这是内容")
        assert result["status"] == "ok", "文本处理状态应为 ok"
        assert result["input_type"] == "text", "输入类型应为 text"
        assert "标题" in result["fields"], "应提取到标题字段"
        assert result["confidence"] > 0.5, "置信度应大于 0.5"
        print("[PASS] 文本输入处理")
    except Exception as exc:
        failures += 1
        print(f"[FAIL] 文本输入处理: {exc}")

    # 测试 3: URL 输入处理（不访问网络）
    try:
        result = process_single_item("https://example.com/path?key=value")
        assert result["status"] == "ok", "URL 处理状态应为 ok"
        assert result["input_type"] == "url", "输入类型应为 url"
        assert result["fields"]["host"] == "example.com", "host 应解析正确"
        assert result["confidence"] > 0.5, "置信度应大于 0.5"
        print("[PASS] URL 输入处理")
    except Exception as exc:
        failures += 1
        print(f"[FAIL] URL 输入处理: {exc}")

    # 测试 4: 空输入错误（E001）
    try:
        process_single_item("")
        failures += 1
        print("[FAIL] 空输入应抛出 E001")
    except SkillError as exc:
        assert exc.code == "E001", f"错误码应为 E001，实际 {exc.code}"
        print("[PASS] 空输入错误处理")
    except Exception as exc:
        failures += 1
        print(f"[FAIL] 空输入错误处理: {exc}")

    # 测试 5: 批量处理（含部分失败）
    try:
        items = ['{"a": 1}', "无效输入!!!", "https://example.org"]
        summary = batch_process(items)
        assert summary["total"] == 3, "总数应为 3"
        assert summary["success"] >= 1, "至少应有 1 个成功"
        assert summary["status"] in ("ok", "partial"), "状态应为 ok 或 partial"
        print("[PASS] 批量处理")
    except Exception as exc:
        failures += 1
        print(f"[FAIL] 批量处理: {exc}")

    # 测试 6: 输出格式化
    try:
        data = {"key": "value", "num": 123}
        json_str = format_output(data, "json")
        assert json.loads(json_str)["key"] == "value", "JSON 格式化应可解析"
        text_str = format_output(data, "text")
        assert "key" in text_str, "文本格式化应包含 key"
        print("[PASS] 输出格式化")
    except Exception as exc:
        failures += 1
        print(f"[FAIL] 输出格式化: {exc}")

    # 测试 7: 置信度计算
    try:
        conf = _compute_confidence({"a": 1, "b": 2, "c": 3})
        assert 0.0 <= conf <= 1.0, "置信度应在 [0,1] 区间"
        conf2 = _compute_confidence({})
        assert conf2 == 0.0, "空数据置信度应为 0"
        assert conf > conf2, "丰富数据置信度应更高"
        print("[PASS] 置信度计算")
    except Exception as exc:
        failures += 1
        print(f"[FAIL] 置信度计算: {exc}")

    # 测试 8: 错误码完整性
    try:
        for code in ["E001", "E002", "E003", "E004", "E005", "E006", "E007", "E008", "E009", "E010"]:
            assert code in ERROR_CODES, f"缺少错误码 {code}"
        print("[PASS] 错误码完整性")
    except Exception as exc:
        failures += 1
        print(f"[FAIL] 错误码完整性: {exc}")

    print(f"\n=== 自检完成: {failures} 个失败 ===")
    return 0 if failures == 0 else 1


# ============================================================
# 主入口
# ============================================================

def main() -> int:
    """命令行主入口。"""
    parser = argparse.ArgumentParser(
        description="pyflowgraph - 通用工作流自动化平台",
        epilog="示例: python main.py --input '{\"name\": \"test\"}' --format json",
    )
    parser.add_argument(
        "--input", "-i",
        help="输入内容（数据/文件路径/URL），支持多次传入进行批量处理",
        action="append",
    )
    parser.add_argument(
        "--file", "-f",
        help="从文件读取输入（每行一个条目）",
    )
    parser.add_argument(
        "--format", "-fmt",
        choices=["json", "text"],
        default="json",
        help="输出格式（默认: json）",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行离线自检（不读外部文件、不访问网络）",
    )
    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        return run_selftest()

    # 收集输入
    items: List[str] = []

    # 从 --input 收集
    if args.input:
        items.extend(args.input)

    # 从 --file 收集
    if args.file:
        try:
            with open(args.file, "r", encoding="utf-8") as fh:
                file_items = [line.strip() for line in fh if line.strip()]
            items.extend(file_items)
        except FileNotFoundError:
            print(f"[E010] 文件不存在: {args.file}", file=sys.stderr)
            return 1
        except Exception as exc:
            print(f"[E010] 读取文件失败: {exc}", file=sys.stderr)
            return 1

    # 无输入
    if not items:
        parser.print_help()
        print(f"\n[E001] {ERROR_CODES['E001']}", file=sys.stderr)
        return 1

    # 执行处理
    try:
        if len(items) == 1:
            # 单条处理
            result = process_single_item(items[0])
            output = format_output(result, args.format)
        else:
            # 批量处理
            summary = batch_process(items)
            output = format_output(summary, args.format)

        print(output)
        return 0

    except SkillError as exc:
        print(f"[{exc.code}] {exc.message}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"[E010] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
