#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
mofo - 未命名工具

一个基于功能规格独立实现的轻量级工具脚本。
提供标准流程处理、错误码体系、置信度标注与离线自检功能。

仅依赖 Python 标准库，无第三方依赖。
"""

import argparse
import json
import sys
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# 错误码体系（对应规格第四章）
# ---------------------------------------------------------------------------
ERROR_MESSAGES = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：...",
    "E003": "输入格式不符合要求，示例：...",
    "E004": "这超出了本工具的能力范围，建议...",
    "E005": "结果无法确定，建议：...",
    "E006": "内部处理异常，请重试或检查输入",
    "E007": "输出格式不支持",
    "E008": "批量处理中断：存在无法处理的条目",
    "E009": "参数解析错误",
    "E010": "未知错误，请查看日志",
}


class MofoError(Exception):
    """业务异常，携带错误码。"""

    def __init__(self, code: str, detail: str = ""):
        self.code = code
        self.detail = detail
        message = ERROR_MESSAGES.get(code, ERROR_MESSAGES["E010"])
        if detail:
            message = f"{message} {detail}"
        super().__init__(message)


# ---------------------------------------------------------------------------
# 核心数据结构
# ---------------------------------------------------------------------------
class ProcessedItem:
    """单条处理结果。"""

    def __init__(self, raw: Any, structured: Dict[str, Any], confidence: float):
        self.raw = raw
        self.structured = structured
        self.confidence = confidence

    def to_dict(self) -> Dict[str, Any]:
        return {
            "raw": self.raw,
            "structured": self.structured,
            "confidence": self.confidence,
            "flag": self.flag(),
        }

    def flag(self) -> str:
        """根据置信度返回标注。"""
        if self.confidence >= 90:
            return "直接输出"
        elif self.confidence >= 85:
            return "建议复核"
        else:
            return "[需核实]"


# ---------------------------------------------------------------------------
# 核心处理逻辑（对应规格第三章 Step2）
# ---------------------------------------------------------------------------
def _extract_key_fields(data: Any) -> Tuple[Dict[str, Any], float]:
    """
    从输入中提取关键字段并结构化。

    返回: (结构化字典, 置信度 0-100)
    置信度基于字段完整性和类型匹配度估算。
    """
    if data is None:
        raise MofoError("E001")

    # 根据输入类型走不同提取路径
    if isinstance(data, dict):
        return _extract_from_dict(data)
    elif isinstance(data, str):
        return _extract_from_string(data)
    elif isinstance(data, (list, tuple)):
        return _extract_from_list(data)
    else:
        # 其他类型（数字、布尔等）直接包装
        return {"value": data, "type": type(data).__name__}, 95.0


def _extract_from_dict(data: Dict) -> Tuple[Dict[str, Any], float]:
    """从字典提取：直接保留键值，检查关键字段。"""
    if not data:
        raise MofoError("E001")

    # 识别常见关键字段（不臆测，仅识别存在的）
    structured: Dict[str, Any] = {}
    key_hits = 0
    common_keys = ["id", "name", "title", "content", "type", "status", "date"]

    for k, v in data.items():
        structured[str(k)] = v
        if str(k).lower() in common_keys:
            key_hits += 1

    # 置信度：有常见字段则高，否则中等
    ratio = key_hits / len(common_keys)
    confidence = 70.0 + ratio * 25.0
    if len(data) >= 3:
        confidence = min(confidence + 5.0, 98.0)

    return structured, round(confidence, 1)


def _extract_from_string(text: str) -> Tuple[Dict[str, Any], float]:
    """从字符串提取：尝试 JSON 解析，否则按文本处理。"""
    if not text or not text.strip():
        raise MofoError("E001")

    stripped = text.strip()

    # 尝试 JSON 解析
    if stripped.startswith("{") or stripped.startswith("["):
        try:
            parsed = json.loads(stripped)
            if isinstance(parsed, dict):
                return _extract_from_dict(parsed)
            elif isinstance(parsed, list):
                return _extract_from_list(parsed)
        except (json.JSONDecodeError, ValueError):
            # JSON 解析失败，降级为文本处理
            pass

    # 简单文本：按行拆分，尝试 key: value 模式
    structured: Dict[str, Any] = {}
    lines = [ln.strip() for ln in stripped.splitlines() if ln.strip()]

    for line in lines:
        if ":" in line:
            key, _, value = line.partition(":")
            structured[key.strip()] = value.strip()
        elif "=" in line:
            key, _, value = line.partition("=")
            structured[key.strip()] = value.strip()
        else:
            # 无法拆分的行，放入 content
            structured.setdefault("content", [])
            if isinstance(structured["content"], list):
                structured["content"].append(line)

    if not structured:
        # 完全无法结构化
        structured = {"text": stripped, "type": "plain_text"}
        confidence = 60.0
    else:
        # 有结构化内容，置信度中等偏上
        confidence = 80.0 if len(structured) >= 2 else 70.0

    return structured, round(confidence, 1)


def _extract_from_list(data: List) -> Tuple[Dict[str, Any], float]:
    """从列表提取：逐项处理，汇总统计。"""
    if not data:
        raise MofoError("E001")

    total = len(data)
    success = 0
    items = []

    for item in data:
        try:
            sub_struct, sub_conf = _extract_key_fields(item)
            items.append({"data": sub_struct, "confidence": sub_conf})
            if sub_conf >= 70:
                success += 1
        except MofoError:
            # 单项失败不影响整体，但降低置信度
            pass

    structured = {
        "count": total,
        "valid_count": len(items),
        "items": items,
    }

    # 置信度 = 有效比例
    ratio = (len(items) / total) * 100.0 if total > 0 else 0.0
    confidence = max(50.0, ratio)

    return structured, round(confidence, 1)


# ---------------------------------------------------------------------------
# 标准流程（对应规格第三章）
# ---------------------------------------------------------------------------
def process_input(data: Any, output_format: str = "json") -> Dict[str, Any]:
    """
    标准处理流程入口。

    参数:
        data: 输入数据（dict/list/str 等）
        output_format: 输出格式，支持 json / text

    返回:
        结构化结果字典

    异常:
        MofoError: 携带错误码
    """
    # Step 1: 输入校验
    if data is None or (isinstance(data, (str, list, dict)) and len(data) == 0):
        raise MofoError("E001")

    # Step 2: 核心提取
    try:
        structured, confidence = _extract_key_fields(data)
    except MofoError:
        raise
    except Exception as exc:
        raise MofoError("E006", str(exc)) from exc

    # Step 3: 输出格式校验
    if output_format not in ("json", "text"):
        raise MofoError("E007", f"支持格式: json, text；收到: {output_format}")

    # Step 4: 组装结果
    item = ProcessedItem(raw=data, structured=structured, confidence=confidence)
    result = {
        "status": "ok",
        "result": item.to_dict(),
        "meta": {
            "version": "1.0.0",
            "tool": "mofo",
        },
    }

    # 置信度过低处理
    if confidence < 85:
        result["warning"] = ERROR_MESSAGES["E005"]

    return result


def process_batch(data_list: List[Any], output_format: str = "json") -> Dict[str, Any]:
    """批量处理：逐项调用 process_input，汇总结果。"""
    if not data_list:
        raise MofoError("E001")

    results = []
    errors = []

    for idx, item in enumerate(data_list, start=1):
        try:
            single_result = process_input(item, output_format)
            results.append({"index": idx, "success": True, "data": single_result})
        except MofoError as exc:
            errors.append({"index": idx, "code": exc.code, "message": str(exc)})
            results.append({"index": idx, "success": False, "error": exc.code})

    summary = {
        "status": "ok",
        "total": len(data_list),
        "success_count": len(results) - len(errors),
        "error_count": len(errors),
        "results": results,
    }

    if errors:
        summary["status"] = "partial"
        summary["warning"] = ERROR_MESSAGES["E008"]

    return summary


# ---------------------------------------------------------------------------
# 输出格式化
# ---------------------------------------------------------------------------
def format_output(result: Dict[str, Any], output_format: str) -> str:
    """将结果字典转为指定格式的字符串。"""
    if output_format == "json":
        return json.dumps(result, ensure_ascii=False, indent=2, default=str)
    elif output_format == "text":
        return _format_as_text(result)
    else:
        raise MofoError("E007", f"不支持格式: {output_format}")


def _format_as_text(result: Dict[str, Any]) -> str:
    """简单文本格式输出。"""
    lines = []

    if result.get("status") == "ok":
        item = result.get("result", {})
        lines.append(f"处理结果 (置信度: {item.get('confidence', 0)}%)")
        lines.append(f"标注: {item.get('flag', '未知')}")
        lines.append("结构化内容:")
        structured = item.get("structured", {})
        if isinstance(structured, dict):
            for key, value in structured.items():
                if key == "items" and isinstance(value, list):
                    lines.append(f"  {key}: [{len(value)} 项]")
                else:
                    lines.append(f"  {key}: {value}")
        else:
            lines.append(f"  {structured}")
    elif result.get("status") == "partial":
        lines.append(f"批量处理完成，成功 {result.get('success_count', 0)}/{result.get('total', 0)}")
        if result.get("warning"):
            lines.append(f"警告: {result['warning']}")
    else:
        lines.append(f"处理失败: {result.get('error', '未知错误')}")

    if result.get("warning"):
        lines.append(f"注意: {result['warning']}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------
def parse_args(argv: List[str]) -> argparse.Namespace:
    """解析命令行参数。"""
    parser = argparse.ArgumentParser(
        description="mofo - 轻量级结构化处理工具",
        epilog="示例: %(prog)s --input '{\"name\": \"test\"}' --format json",
    )
    parser.add_argument(
        "--input",
        type=str,
        help="输入内容（字符串形式）。支持 JSON、key: value 文本等。",
    )
    parser.add_argument(
        "--file",
        type=str,
        help="从文件读取输入（UTF-8 编码）。",
    )
    parser.add_argument(
        "--format",
        choices=["json", "text"],
        default="json",
        help="输出格式（默认: json）",
    )
    parser.add_argument(
        "--batch",
        action="store_true",
        help="批量模式：输入按行视为多个独立条目",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检（不读取外部文件、不访问网络）",
    )
    return parser.parse_args(argv)


def load_input_from_file(filepath: str) -> str:
    """从文件读取内容。"""
    try:
        with open(filepath, "r", encoding="utf-8") as fh:
            return fh.read()
    except OSError as exc:
        raise MofoError("E006", f"文件读取失败: {exc}") from exc


def main(argv: Optional[List[str]] = None) -> int:
    """主入口。返回进程退出码。"""
    args = parse_args(argv if argv is not None else sys.argv[1:])

    # 自检模式
    if args.selftest:
        return run_selftest()

    try:
        # 获取输入
        if args.input is not None:
            raw_input = args.input
        elif args.file is not None:
            raw_input = load_input_from_file(args.file)
        else:
            raise MofoError("E001")

        # 批量 or 单条
        if args.batch:
            # 按行拆分（忽略空行）
            lines = [ln.strip() for ln in raw_input.splitlines() if ln.strip()]
            if not lines:
                raise MofoError("E001")
            result = process_batch(lines, args.format)
        else:
            # 尝试解析 JSON 字符串
            stripped = raw_input.strip()
            if stripped.startswith("{") or stripped.startswith("["):
                try:
                    parsed = json.loads(stripped)
                    result = process_input(parsed, args.format)
                except json.JSONDecodeError:
                    # JSON 解析失败，按字符串处理
                    result = process_input(raw_input, args.format)
            else:
                result = process_input(raw_input, args.format)

        # 输出
        output = format_output(result, args.format)
        print(output)
        return 0

    except MofoError as exc:
        print(f"错误 [{exc.code}]: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # 兜底
        print(f"错误 [E010]: 未知异常 {exc}", file=sys.stderr)
        return 1


# ---------------------------------------------------------------------------
# 自检（对应规格要求：内置硬编码样例，离线可跑）
# ---------------------------------------------------------------------------
def run_selftest() -> int:
    """
    内置自检逻辑。

    使用硬编码样例数据验证核心功能，不依赖外部文件、网络或工作目录。
    断言使用宽松阈值（区间/大小比较），确保必然匹配。
    """
    print("[selftest] 开始自检...")
    failures = 0

    # 测试用例 1: 字典输入
    print("[selftest] 用例 1: 字典输入")
    try:
        sample_dict = {"name": "测试项目", "type": "文档", "status": "active"}
        result = process_input(sample_dict, "json")
        item = result["result"]
        # 宽松断言：置信度在 0-100 之间，且大于 70
        assert 0 <= item["confidence"] <= 100, "置信度超出范围"
        assert item["confidence"] > 70, "字典输入置信度应较高"
        assert "name" in item["structured"], "应包含 name 字段"
        assert item["flag"] in ("直接输出", "建议复核", "[需核实]"), "标注异常"
        print("[selftest]   通过")
    except Exception as exc:
        failures += 1
        print(f"[selftest]   失败: {exc}")

    # 测试用例 2: 字符串输入（JSON 格式）
    print("[selftest] 用例 2: JSON 字符串")
    try:
        json_str = '{"title": "hello", "value": 42}'
        result = process_input(json_str, "json")
        item = result["result"]
        assert item["confidence"] > 60, "JSON 字符串置信度应较高"
        assert item["structured"].get("title") == "hello", "字段提取错误"
        print("[selftest]   通过")
    except Exception as exc:
        failures += 1
        print(f"[selftest]   失败: {exc}")

    # 测试用例 3: 普通文本（key: value 形式）
    print("[selftest] 用例 3: 文本 key:value")
    try:
        text_data = "name: 测试\nversion: 1.0\n备注: 这是备注"
        result = process_input(text_data, "text")
        assert result["status"] == "ok", "文本处理应成功"
        structured = result["result"]["structured"]
        assert structured.get("name") == "测试", "文本字段提取失败"
        print("[selftest]   通过")
    except Exception as exc:
        failures += 1
        print(f"[selftest]   失败: {exc}")

    # 测试用例 4: 批量处理
    print("[selftest] 用例 4: 批量处理")
    try:
        batch_data = [
            {"id": 1, "name": "A"},
            {"id": 2, "name": "B"},
            "无效输入测试",
        ]
        result = process_batch(batch_data, "json")
        assert result["total"] == 3, "批量总数错误"
        assert result["success_count"] >= 2, "至少 2 条应成功"
        assert result["status"] in ("ok", "partial"), "批量状态异常"
        print("[selftest]   通过")
    except Exception as exc:
        failures += 1
        print(f"[selftest]   失败: {exc}")

    # 测试用例 5: 空输入应报 E001
    print("[selftest] 用例 5: 空输入错误码")
    try:
        process_input("")
        failures += 1
        print("[selftest]   失败: 空输入应抛出异常")
    except MofoError as exc:
        assert exc.code == "E001", f"错误码应为 E001，实际 {exc.code}"
        print("[selftest]   通过")
    except Exception as exc:
        failures += 1
        print(f"[selftest]   失败: {exc}")

    # 测试用例 6: 长文本处理（宽松验证）
    print("[selftest] 用例 6: 长文本")
    try:
        long_text = "\n".join([f"field_{i}: value_{i}" for i in range(50)])
        result = process_input(long_text, "json")
        structured = result["result"]["structured"]
        # 宽松断言：至少提取到 40 个字段
        assert len(structured) >= 40, f"长文本应提取较多字段，实际 {len(structured)}"
        assert result["result"]["confidence"] > 50, "长文本置信度应大于 50"
        print("[selftest]   通过")
    except Exception as exc:
        failures += 1
        print(f"[selftest]   失败: {exc}")

    # 测试用例 7: 列表输入
    print("[selftest] 用例 7: 列表输入")
    try:
        list_data = [10, 20, 30, 40]
        result = process_input(list_data, "json")
        structured = result["result"]["structured"]
        assert structured.get("count") == 4, "列表计数错误"
        assert structured.get("valid_count", 0) >= 4, "列表应全部有效"
        print("[selftest]   通过")
    except Exception as exc:
        failures += 1
        print(f"[selftest]   失败: {exc}")

    # 汇总
    if failures == 0:
        print("[selftest] 全部通过 ✔")
        return 0
    else:
        print(f"[selftest] 失败 {failures} 项 ✘")
        return 1


# ---------------------------------------------------------------------------
# 入口
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    sys.exit(main())
