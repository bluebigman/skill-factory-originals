#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
mdv — 数据可视化技能核心实现（独立 clean-room 实现）

本脚本仅依据功能规格实现，不参考任何既有代码。
提供数据解析、结构化、置信度评估、错误处理与离线自检能力。
"""

import argparse
import json
import re
import sys
from typing import Any, Dict, List, Optional, Tuple, Union


# ---------------------------------------------------------------------------
# 常量定义
# ---------------------------------------------------------------------------

# 错误码与标准化话术映射（依据规格第五节）
ERROR_MESSAGES: Dict[str, str] = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：...（逐项追问缺失项）",
    "E003": "输入格式不符合要求，示例：...",
    "E004": "这超出了本工具的能力范围，建议：...",
    "E005": "结果无法确定，建议：...",
    "E006": "内部处理异常，请重试或检查输入",
    "E007": "输出序列化失败，请检查数据格式",
    "E008": "命令行参数不合法，请检查用法",
    "E009": "自检数据初始化失败，请联系维护者",
    "E010": "未知错误，请查看日志",
}

# 置信度阈值（依据规格第三节）
CONFIDENCE_HIGH = 90          # ≥90：直接输出
CONFIDENCE_MEDIUM_LOW = 85    # 85-90：建议复核
# <85：标注 [需核实]

# 可接受的关键字段集合（用于 E002 缺失判断）
REQUIRED_FIELDS = ["data", "format"]

# 支持的输出格式
SUPPORTED_FORMATS = ["json", "md", "html"]

# KV 分隔符模式
KV_SEPARATORS = [";", "&", "\n", ","]


# ---------------------------------------------------------------------------
# 核心工具函数
# ---------------------------------------------------------------------------

def _make_error(code: str, detail: str = "") -> Dict[str, Any]:
    """构造标准错误结构。"""
    message = ERROR_MESSAGES.get(code, ERROR_MESSAGES["E010"])
    if detail:
        message = f"{message}（{detail}）"
    return {"ok": False, "error_code": code, "message": message}


def _make_success(result: Any, confidence: int, note: str = "") -> Dict[str, Any]:
    """构造标准成功结构。"""
    return {
        "ok": True,
        "result": result,
        "confidence": confidence,
        "note": note,
    }


def _safe_json_dumps(data: Any) -> str:
    """安全的 JSON 序列化，处理非标准类型。"""
    def _default_handler(obj: Any) -> Any:
        """处理无法直接序列化的对象。"""
        if hasattr(obj, "__dict__"):
            return obj.__dict__
        return str(obj)
    
    return json.dumps(data, ensure_ascii=False, indent=2, default=_default_handler)


def parse_input(raw_input: str) -> Any:
    """
    解析输入内容。
    支持 JSON 字符串、简单 KV 文本或纯文本；无法解析时返回原字符串。
    """
    if not raw_input or not raw_input.strip():
        raise ValueError("E001")

    text = raw_input.strip()

    # 尝试 JSON 解析
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 尝试 KV 格式（支持多种分隔符）
    if "=" in text:
        kv: Dict[str, str] = {}
        # 尝试多种分隔符
        for sep in KV_SEPARATORS:
            if sep in text:
                parts = text.split(sep)
                kv = {}
                for part in parts:
                    part = part.strip()
                    if "=" in part:
                        key, _, value = part.partition("=")
                        key = key.strip()
                        value = value.strip()
                        # 尝试将值转换为数字或布尔
                        if value.lower() in ("true", "false"):
                            kv[key] = value.lower() == "true"
                        elif re.match(r"^-?\d+$", value):
                            kv[key] = int(value)
                        elif re.match(r"^-?\d+\.\d+$", value):
                            kv[key] = float(value)
                        else:
                            kv[key] = value
                if kv:
                    return kv
                break

    # 尝试解析 CSV 格式（逗号分隔的简单数据）
    if "," in text and not text.startswith("{"):
        items = [item.strip() for item in text.split(",")]
        if len(items) > 1:
            return {"data": items}

    # 默认按纯文本返回
    return text


def extract_key_fields(data: Any) -> Tuple[Dict[str, Any], List[str]]:
    """
    从解析后的数据中提取关键字段。
    返回 (字段字典, 缺失字段列表)。
    """
    if data is None:
        return {}, REQUIRED_FIELDS[:]

    if isinstance(data, dict):
        # 已有结构化数据，检查缺失
        missing = [f for f in REQUIRED_FIELDS if f not in data]
        return data, missing

    # 非字典：将其视为 data 字段，format 缺失
    return {"data": data}, ["format"]


def compute_confidence(data: Dict[str, Any], missing: List[str]) -> int:
    """
    根据缺失字段计算置信度（百分数）。
    无缺失 = 95；每缺一个字段减 10；数据为空再减 10。
    数据质量高（非空、有结构）可加分。
    下限 50。
    """
    base = 95
    penalty = len(missing) * 10
    
    # 数据质量评估
    data_value = data.get("data")
    if data_value is None or data_value == "":
        penalty += 10
    elif isinstance(data_value, (list, dict)) and len(data_value) > 0:
        base += 3  # 结构化数据加分
    elif isinstance(data_value, str) and len(data_value) > 10:
        base += 2  # 长文本加分
    
    # 格式字段存在且有效加分
    fmt = data.get("format")
    if fmt in SUPPORTED_FORMATS:
        base += 2
    
    return max(50, min(100, base - penalty))


def format_output(data: Dict[str, Any], fmt: str) -> str:
    """
    按指定格式生成输出。
    - json: JSON 字符串
    - md: Markdown 表格/列表
    - html: 简单 HTML 结构
    """
    if fmt == "json":
        return _safe_json_dumps(data)

    if fmt == "md":
        lines = ["# MDV 输出", ""]
        data_value = data.get("data")
        if isinstance(data_value, list):
            if data_value and isinstance(data_value[0], dict):
                # 列表包含字典，生成表格
                headers = list(data_value[0].keys())
                lines.append("| " + " | ".join(headers) + " |")
                lines.append("| " + " | ".join(["---"] * len(headers)) + " |")
                for item in data_value:
                    if isinstance(item, dict):
                        lines.append("| " + " | ".join(str(item.get(h, "")) for h in headers) + " |")
            else:
                # 简单列表
                lines.append("| 序号 | 值 |")
                lines.append("| --- | --- |")
                for i, item in enumerate(data_value, 1):
                    lines.append(f"| {i} | {item} |")
        else:
            lines.append(f"- 数据: {data_value}")
        
        fmt_value = data.get("format", "未指定")
        lines.append(f"- 格式: {fmt_value}")
        return "\n".join(lines)

    if fmt == "html":
        data_value = data.get("data", "")
        fmt_value = data.get("format", "未指定")
        
        # HTML 转义
        import html as html_module
        data_escaped = html_module.escape(str(data_value))
        fmt_escaped = html_module.escape(str(fmt_value))
        
        body = f"<p>数据: {data_escaped}</p>"
        body += f"<p>格式: {fmt_escaped}</p>"
        return f"<!DOCTYPE html><html><head><meta charset='utf-8'><title>MDV 输出</title></head><body>{body}</body></html>"

    return str(data)


def process(raw_input: str, output_format: Optional[str] = None) -> Dict[str, Any]:
    """
    标准处理流程（Step 2）：
    1. 解析输入
    2. 提取关键字段
    3. 计算置信度
    4. 生成输出
    """
    # 输入为空 → E001
    if not raw_input or not raw_input.strip():
        return _make_error("E001")

    # 解析输入（可能抛 ValueError）
    try:
        parsed = parse_input(raw_input)
    except ValueError as exc:
        code = str(exc)
        if code == "E001":
            return _make_error("E001")
        return _make_error("E003", str(exc))
    except Exception as exc:
        return _make_error("E006", f"解析失败: {str(exc)}")

    # 提取字段
    try:
        fields, missing = extract_key_fields(parsed)
    except Exception as exc:
        return _make_error("E006", f"字段提取失败: {str(exc)}")

    # 关键信息缺失 → E002
    if missing:
        detail = "、".join(missing)
        return _make_error("E002", f"缺少字段: {detail}")

    # 校验输出格式
    fmt = output_format or fields.get("format", "json")
    if fmt not in SUPPORTED_FORMATS:
        return _make_error("E003", f"不支持的格式: {fmt}，可选: {SUPPORTED_FORMATS}")

    # 计算置信度
    try:
        confidence = compute_confidence(fields, missing)
    except Exception as exc:
        return _make_error("E006", f"置信度计算失败: {str(exc)}")

    # 置信度过低 → E005
    if confidence < CONFIDENCE_MEDIUM_LOW:
        return _make_error("E005", f"置信度仅 {confidence}%")

    # 生成输出
    try:
        output = format_output(fields, fmt)
    except Exception as exc:
        return _make_error("E007", str(exc))

    # 组装结果（含置信度标注）
    note = ""
    if confidence < CONFIDENCE_HIGH:
        note = "建议复核" if confidence >= CONFIDENCE_MEDIUM_LOW else "[需核实]"

    return _make_success(output, confidence, note)


# ---------------------------------------------------------------------------
# 自检模块（--selftest）
# ---------------------------------------------------------------------------

def _selftest() -> int:
    """
    离线自检核心逻辑。
    使用内置硬编码样例，不读文件、不访问网络、不依赖工作目录。
    断言使用宽松阈值（区间/大小比较），不依赖精确值。
    """
    print("[selftest] 开始离线自检...")
    
    # 用例 1：正常 JSON 输入
    case1 = '{"data": [1, 2, 3], "format": "json"}'
    r1 = process(case1)
    assert r1["ok"] is True, "用例1失败：应成功"
    assert r1["confidence"] >= 85, "用例1失败：置信度应较高"
    assert r1["result"], "用例1失败：结果不应为空"
    print("[selftest] 用例1（正常JSON）通过")

    # 用例 2：空输入 → E001
    r2 = process("")
    assert r2["ok"] is False, "用例2失败：应失败"
    assert r2["error_code"] == "E001", "用例2失败：错误码应为E001"
    print("[selftest] 用例2（空输入）通过")

    # 用例 3：缺少 format 字段 → E002
    r3 = process('{"data": [1, 2]}')
    assert r3["ok"] is False, "用例3失败：应失败"
    assert r3["error_code"] == "E002", "用例3失败：错误码应为E002"
    print("[selftest] 用例3（缺字段）通过")

    # 用例 4：KV 格式输入 → 成功且置信度合理
    r4 = process("data=hello; format=md")
    assert r4["ok"] is True, "用例4失败：应成功"
    assert 50 <= r4["confidence"] <= 100, "用例4失败：置信度应在合理区间"
    print("[selftest] 用例4（KV格式）通过")

    # 用例 5：纯文本输入 → 成功（data 字段自动填充）
    r5 = process("简单文本内容")
    assert r5["ok"] is True, "用例5失败：应成功"
    assert r5["confidence"] >= 50, "用例5失败：置信度不应低于下限"
    print("[selftest] 用例5（纯文本）通过")

    # 用例 6：不支持的格式 → E003
    r6 = process('{"data": [1], "format": "xml"}')
    assert r6["ok"] is False, "用例6失败：应失败"
    assert r6["error_code"] == "E003", "用例6失败：错误码应为E003"
    print("[selftest] 用例6（非法格式）通过")

    # 用例 7：输出格式校验 — 三种格式均可用
    for fmt in SUPPORTED_FORMATS:
        r7 = process(f'{{"data": [10, 20], "format": "{fmt}"}}')
        assert r7["ok"] is True, f"用例7失败：格式 {fmt} 应支持"
        assert r7["result"], f"用例7失败：格式 {fmt} 输出不应为空"
    print("[selftest] 用例7（多格式输出）通过")

    # 用例 8：parse_input 对 JSON 数组的处理
    parsed = parse_input("[1, 2, 3]")
    assert isinstance(parsed, list), "用例8失败：应解析为列表"
    assert len(parsed) == 3, "用例8失败：列表长度应为3"
    print("[selftest] 用例8（JSON数组解析）通过")

    # 用例 9：置信度计算逻辑（宽松阈值）
    conf_high = compute_confidence({"data": [1, 2, 3], "format": "json"}, [])
    conf_low = compute_confidence({"data": None}, ["format", "extra"])
    assert conf_high > conf_low, "用例9失败：高置信度应大于低置信度"
    assert 0 <= conf_high <= 100, "用例9失败：置信度应在0-100区间"
    assert 0 <= conf_low <= 100, "用例9失败：置信度应在0-100区间"
    print("[selftest] 用例9（置信度计算）通过")

    # 用例 10：错误码体系完整性
    for code in ["E001", "E002", "E003", "E004", "E005", "E006", "E007", "E008", "E009", "E010"]:
        assert code in ERROR_MESSAGES, f"用例10失败：缺少错误码 {code}"
        assert ERROR_MESSAGES[code], f"用例10失败：错误码 {code} 话术为空"
    print("[selftest] 用例10（错误码体系）通过")

    # 用例 11：CSV 格式解析
    r11 = process("1, 2, 3, 4, 5")
    assert r11["ok"] is True, "用例11失败：CSV格式应成功"
    assert r11["confidence"] >= 50, "用例11失败：置信度应合理"
    print("[selftest] 用例11（CSV格式）通过")

    # 用例 12：特殊字符处理
    r12 = process('{"data": "包含\"引号\"和\\n换行", "format": "json"}')
    assert r12["ok"] is True, "用例12失败：特殊字符应成功处理"
    assert r12["result"], "用例12失败：输出不应为空"
    print("[selftest] 用例12（特殊字符）通过")

    # 用例 13：数值类型解析
    r13 = process("data=42; format=json")
    assert r13["ok"] is True, "用例13失败：数值解析应成功"
    assert r13["confidence"] >= 50, "用例13失败：置信度应合理"
    print("[selftest] 用例13（数值类型）通过")

    # 用例 14：布尔值解析
    r14 = process("data=true; format=md")
    assert r14["ok"] is True, "用例14失败：布尔值解析应成功"
    assert r14["confidence"] >= 50, "用例14失败：置信度应合理"
    print("[selftest] 用例14（布尔值）通过")

    # 用例 15：复杂 JSON 嵌套结构
    r15 = process('{"data": {"user": "张三", "age": 30, "tags": ["python", "data"]}, "format": "json"}')
    assert r15["ok"] is True, "用例15失败：复杂JSON应成功"
    assert r15["confidence"] >= 85, "用例15失败：置信度应较高"
    assert "张三" in r15["result"], "用例15失败：输出应包含嵌套数据"
    print("[selftest] 用例15（复杂JSON）通过")

    print("[selftest] 全部自检通过 ✅")
    return 0


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------

def main(argv: Optional[List[str]] = None) -> int:
    """命令行主入口。"""
    parser = argparse.ArgumentParser(
        description="mdv — 数据可视化技能核心实现",
        epilog="示例: python main.py '{\"data\": [1,2,3], \"format\": \"json\"}' --format md",
    )
    parser.add_argument(
        "input",
        nargs="?",
        default="",
        help="待处理的内容（JSON/KV/CSV/纯文本）",
    )
    parser.add_argument(
        "--format",
        choices=SUPPORTED_FORMATS,
        default=None,
        help="输出格式（默认取输入中的 format 字段，缺省为 json）",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行离线自检（不读外部文件、不访问网络）",
    )

    args = parser.parse_args(argv)

    # 自检模式
    if args.selftest:
        try:
            return _selftest()
        except AssertionError as exc:
            print(f"[selftest] 自检失败: {exc}", file=sys.stderr)
            return 1
        except Exception as exc:
            print(f"[selftest] 自检异常: {exc}", file=sys.stderr)
            return 1

    # 正常处理模式
    if not args.input:
        print(_make_error("E001"), file=sys.stderr)
        return 1

    result = process(args.input, args.format)

    if result["ok"]:
        print(result["result"])
        if result.get("note"):
            print(f"\n[提示] {result['note']}（置信度 {result['confidence']}%）", file=sys.stderr)
        return 0

    # 错误输出
    print(f"[{result['error_code']}] {result['message']}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
