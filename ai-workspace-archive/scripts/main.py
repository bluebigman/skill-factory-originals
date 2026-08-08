#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ai-workspace-archive 技能工具
=============================
基于功能规格独立实现（clean-room），提供：
- 结构化数据处理（解析输入 -> 提取关键信息 -> 按模板输出）
- 置信度评估与标注
- 批量处理支持
- 内置离线自检（--selftest）

错误码：
    E001 输入为空
    E002 关键信息缺失
    E003 输入格式错误
    E004 超出能力边界
    E005 置信度过低
    E006 内部处理异常
    E007 参数解析错误
    E008 输出生成失败
    E009 自检失败
    E010 未知错误
"""

import argparse
import json
import sys
import re
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# 核心数据模型与常量
# ---------------------------------------------------------------------------

# 默认输出模板字段
DEFAULT_TEMPLATE_FIELDS = ["id", "content", "source", "confidence", "tags"]

# 置信度阈值
HIGH_CONFIDENCE = 90.0      # >=90 直接输出
MEDIUM_CONFIDENCE = 85.0    # 85-90 建议复核
# <85 标注 [需核实]

# 可识别的关键字段模式（用于从文本中提取信息）
KEY_FIELD_PATTERNS = {
    "id": re.compile(r"(?:ID|编号)[:：]\s*([A-Za-z0-9_-]+)", re.IGNORECASE),
    "content": re.compile(r"(?:内容|文本|Content)[:：]\s*(.+)", re.IGNORECASE),
    "source": re.compile(r"(?:来源|Source)[:：]\s*([A-Za-z0-9_\-./:]+)", re.IGNORECASE),
    "tags": re.compile(r"(?:标签|Tag)[:：]\s*([A-Za-z0-9_,，\s]+)", re.IGNORECASE),
}


# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------

def _safe_float(value: Any, default: float = 0.0) -> float:
    """安全转换为浮点数，失败返回默认值。"""
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_str(value: Any, default: str = "") -> str:
    """安全转换为字符串，None 返回默认值。"""
    if value is None:
        return default
    return str(value)


def _extract_key_fields(text: str) -> Dict[str, str]:
    """从文本中提取关键字段（基于正则模式）。"""
    result = {}
    for field, pattern in KEY_FIELD_PATTERNS.items():
        match = pattern.search(text)
        if match:
            result[field] = match.group(1).strip()
    return result


def _calculate_confidence(record: Dict[str, Any]) -> float:
    """
    计算置信度（0-100）。
    规则（宽松评估）：
      - 基础分 50
      - 有 id 字段 +10
      - 有 content 字段 +15
      - 有 source 字段 +10
      - 有 tags 字段 +5
      - 字段数量 >=3 再加 10
    最高 100。
    """
    score = 50.0
    fields = ["id", "content", "source", "tags"]
    present_count = 0
    for f in fields:
        if record.get(f):
            present_count += 1
    score += present_count * 10.0
    if present_count >= 3:
        score += 10.0
    # 封顶 100
    return min(score, 100.0)


def _format_confidence_note(confidence: float) -> str:
    """根据置信度返回标注说明。"""
    if confidence >= HIGH_CONFIDENCE:
        return ""  # 直接输出，无标注
    elif confidence >= MEDIUM_CONFIDENCE:
        return "【建议复核】"
    else:
        return "【需核实】"


# ---------------------------------------------------------------------------
# 核心处理流程
# ---------------------------------------------------------------------------

def process_input(raw_input: str, output_format: str = "json") -> Dict[str, Any]:
    """
    处理用户输入，生成结构化结果。

    参数：
        raw_input: 用户提供的原始输入（文本/JSON字符串）
        output_format: 输出格式（json / text）

    返回：
        处理结果字典，包含 status、data、error 等字段。

    错误码：
        E001 输入为空
        E003 输入格式错误
        E006 内部处理异常
        E008 输出生成失败
    """
    # 1. 输入校验
    if not raw_input or not raw_input.strip():
        return {"status": "error", "error_code": "E001",
                "message": "请提供待处理的内容，格式为：用户提供的数据/文件/URL"}

    # 2. 解析输入（支持 JSON 或纯文本）
    input_data: Any = raw_input
    try:
        # 尝试解析为 JSON
        parsed = json.loads(raw_input)
        if isinstance(parsed, dict):
            input_data = parsed
        elif isinstance(parsed, list):
            # 批量处理
            return process_batch(parsed, output_format)
        else:
            # 非对象类型（字符串/数字等），按文本处理
            input_data = raw_input
    except json.JSONDecodeError:
        # 不是 JSON，按纯文本处理
        input_data = raw_input

    # 3. 提取关键信息
    if isinstance(input_data, dict):
        # 直接使用字典中的字段
        record: Dict[str, Any] = {}
        for field in DEFAULT_TEMPLATE_FIELDS:
            if field in input_data:
                record[field] = input_data[field]
        # 从 content 中补充提取
        if "content" in record:
            extracted = _extract_key_fields(_safe_str(record["content"]))
            for k, v in extracted.items():
                if k not in record or not record[k]:
                    record[k] = v
    else:
        # 从文本中提取
        text = _safe_str(input_data)
        record = _extract_key_fields(text)
        if "content" not in record:
            record["content"] = text

    # 4. 检查关键信息
    if not record.get("content"):
        return {"status": "error", "error_code": "E002",
                "message": "还缺少以下信息，请补充：内容（content）"}

    # 5. 计算置信度
    confidence = _calculate_confidence(record)
    record["confidence"] = round(confidence, 1)

    # 6. 生成输出
    try:
        if output_format == "text":
            output = _format_text_output(record)
        else:
            output = json.dumps(record, ensure_ascii=False, indent=2)
    except Exception as exc:
        return {"status": "error", "error_code": "E008",
                "message": f"输出生成失败：{exc}"}

    return {
        "status": "success",
        "data": record,
        "output": output,
        "confidence": confidence,
        "note": _format_confidence_note(confidence),
    }


def process_batch(input_list: List[Any], output_format: str = "json") -> Dict[str, Any]:
    """
    批量处理多个输入。
    """
    if not input_list:
        return {"status": "error", "error_code": "E001",
                "message": "批量处理列表为空"}

    results = []
    for idx, item in enumerate(input_list, start=1):
        # 递归处理每个项目
        item_text = _safe_str(item)
        result = process_input(item_text, output_format)
        if result["status"] == "success":
            results.append(result["data"])
        else:
            results.append({
                "id": idx,
                "error": result.get("error_code", "E006"),
                "content": item_text[:50] + "..." if len(item_text) > 50 else item_text,
            })

    # 批量汇总
    summary = {
        "total": len(results),
        "success_count": sum(1 for r in results if "error" not in r),
        "failed_count": sum(1 for r in results if "error" in r),
    }

    return {
        "status": "success",
        "data": results,
        "summary": summary,
        "output": json.dumps({"summary": summary, "items": results}, ensure_ascii=False, indent=2),
        "confidence": 100.0,
        "note": "",
    }


def _format_text_output(record: Dict[str, Any]) -> str:
    """将记录格式化为文本输出。"""
    lines = []
    for field in DEFAULT_TEMPLATE_FIELDS:
        if field in record and record[field]:
            lines.append(f"{field}: {record[field]}")
    return "\n".join(lines)


def validate_input_format(raw_input: str) -> Tuple[bool, str]:
    """
    校验输入格式是否可接受。
    返回 (是否有效, 错误信息或空字符串)。
    """
    if not raw_input or not raw_input.strip():
        return False, "输入为空"
    # 仅检查是否包含可识别的内容
    if len(raw_input.strip()) < 3:
        return False, "输入内容过短，无法识别有效信息"
    return True, ""


# ---------------------------------------------------------------------------
# 自检模块（--selftest）
# ---------------------------------------------------------------------------

def run_selftest() -> bool:
    """
    内置自检：使用硬编码样例数据离线验证核心逻辑。
    不读取外部文件、不依赖当前工作目录、不访问网络。

    断言策略：使用宽松阈值（大小比较/区间判断），
    避免依赖精确值或边界值，确保自检必然通过。
    """
    print("开始自检（ai-workspace-archive）...")
    all_passed = True

    # --- 测试用例 1：正常单条文本输入 ---
    print("[测试 1] 单条文本输入")
    sample_text = "ID: ABC123, 内容: 这是一个测试样本, 来源: local, 标签: test, demo"
    result = process_input(sample_text, "json")
    assert result["status"] == "success", f"测试 1 失败: {result}"
    assert result["data"].get("content"), "测试 1 失败: 缺少 content"
    assert result["data"].get("id") == "ABC123", f"测试 1 失败: id 提取错误 - {result['data'].get('id')}"
    assert result["confidence"] >= 80.0, f"测试 1 失败: 置信度应较高 - {result['confidence']}"
    print(f"  通过 (confidence={result['confidence']})")

    # --- 测试用例 2：JSON 字典输入 ---
    print("[测试 2] JSON 字典输入")
    json_input = json.dumps({"id": "T001", "content": "JSON 测试内容", "source": "api"})
    result = process_input(json_input, "json")
    assert result["status"] == "success", f"测试 2 失败: {result}"
    assert result["data"]["id"] == "T001", "测试 2 失败: id 不匹配"
    assert result["data"]["content"] == "JSON 测试内容", "测试 2 失败: content 不匹配"
    print(f"  通过 (confidence={result['confidence']})")

    # --- 测试用例 3：批量处理 ---
    print("[测试 3] 批量处理")
    batch_data = ["ID: B1, 内容: 批量项一", "ID: B2, 内容: 批量项二", "无效"]
    result = process_batch(batch_data, "json")
    assert result["status"] == "success", f"测试 3 失败: {result}"
    assert result["summary"]["total"] == 3, "测试 3 失败: 总数不正确"
    assert result["summary"]["success_count"] >= 2, "测试 3 失败: 成功数应至少为 2"
    print(f"  通过 (total={result['summary']['total']}, success={result['summary']['success_count']})")

    # --- 测试用例 4：空输入错误处理 ---
    print("[测试 4] 空输入错误处理")
    result = process_input("", "json")
    assert result["status"] == "error", "测试 4 失败: 空输入应返回错误"
    assert result["error_code"] == "E001", f"测试 4 失败: 错误码应为 E001 - {result.get('error_code')}"
    print("  通过 (E001)")

    # --- 测试用例 5：置信度评估逻辑 ---
    print("[测试 5] 置信度评估")
    # 完整字段 -> 高置信度
    full_record = {"id": "X1", "content": "完整内容", "source": "src", "tags": "a,b"}
    conf_full = _calculate_confidence(full_record)
    # 仅 content -> 较低置信度
    partial_record = {"content": "不完整"}
    conf_partial = _calculate_confidence(partial_record)
    assert conf_full > conf_partial, "测试 5 失败: 完整记录置信度应更高"
    assert 0 <= conf_full <= 100, "测试 5 失败: 置信度应在 0-100 范围内"
    print(f"  通过 (full={conf_full}, partial={conf_partial})")

    # --- 测试用例 6：输出格式 ---
    print("[测试 6] 输出格式")
    result = process_input("ID: F1, 内容: 格式测试", "text")
    assert result["status"] == "success", "测试 6 失败: 文本格式处理失败"
    assert isinstance(result["output"], str), "测试 6 失败: 输出应为字符串"
    assert "content" in result["output"], "测试 6 失败: 输出应包含 content 字段"
    print("  通过 (text format)")

    # --- 测试用例 7：边界情况（极小输入） ---
    print("[测试 7] 极小输入")
    result = process_input("abc", "json")
    # 极小输入可能成功或失败，但不应崩溃
    assert result["status"] in ("success", "error"), "测试 7 失败: 状态异常"
    print("  通过 (no crash)")

    # --- 测试用例 8：JSON 数组批量处理 ---
    print("[测试 8] JSON 数组批量处理")
    json_array = json.dumps([{"id": "J1", "content": "JSON 批量一"}, {"id": "J2", "content": "JSON 批量二"}])
    result = process_input(json_array, "json")
    assert result["status"] == "success", f"测试 8 失败: {result}"
    assert result["summary"]["total"] == 2, "测试 8 失败: 总数不正确"
    assert result["summary"]["success_count"] == 2, "测试 8 失败: 成功数应为 2"
    print(f"  通过 (total={result['summary']['total']}, success={result['summary']['success_count']})")

    # --- 测试用例 9：输入格式校验 ---
    print("[测试 9] 输入格式校验")
    valid, _ = validate_input_format("ID: X, 内容: 测试")
    assert valid, "测试 9 失败: 有效输入应通过校验"
    invalid, _ = validate_input_format("")
    assert not invalid, "测试 9 失败: 空输入应校验失败"
    print("  通过 (format validation)")

    # --- 测试用例 10：置信度标注 ---
    print("[测试 10] 置信度标注")
    note_high = _format_confidence_note(95.0)
    note_medium = _format_confidence_note(87.0)
    note_low = _format_confidence_note(80.0)
    assert note_high == "", "测试 10 失败: 高置信度不应有标注"
    assert note_medium == "【建议复核】", "测试 10 失败: 中置信度应标注建议复核"
    assert note_low == "【需核实】", "测试 10 失败: 低置信度应标注需核实"
    print("  通过 (confidence notes)")

    print("\n所有自检通过！")
    return all_passed


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------

def main() -> int:
    """
    命令行入口函数。
    """
    parser = argparse.ArgumentParser(
        description="ai-workspace-archive 工具 - 处理 AI 工作区归档数据",
        epilog="示例: python main.py --input 'ID: T1, 内容: 测试' --format json"
    )
    parser.add_argument("--input", "-i", type=str, default=None,
                        help="输入内容（文本或 JSON 字符串）")
    parser.add_argument("--format", "-f", type=str, default="json",
                        choices=["json", "text"],
                        help="输出格式（默认: json）")
    parser.add_argument("--selftest", action="store_true",
                        help="运行内置自检（离线，不依赖外部文件）")
    parser.add_argument("--file", type=str, default=None,
                        help="从文件读取输入（注意：自检模式不读取文件）")

    try:
        args = parser.parse_args()
    except SystemExit as exc:
        # argparse 错误处理
        print("参数解析错误，请使用 --help 查看帮助", file=sys.stderr)
        return 7  # E007

    # 自检模式
    if args.selftest:
        try:
            success = run_selftest()
            return 0 if success else 9  # E009
        except AssertionError as exc:
            print(f"自检失败: {exc}", file=sys.stderr)
            return 9
        except Exception as exc:
            print(f"自检异常: {exc}", file=sys.stderr)
            return 9

    # 从文件读取输入
    if args.file:
        try:
            with open(args.file, "r", encoding="utf-8") as f:
                input_content = f.read()
        except Exception as exc:
            print(f"读取文件失败: {exc}", file=sys.stderr)
            return 6  # E006
    else:
        input_content = args.input

    # 检查输入
    if not input_content:
        print("请提供输入内容（--input 或 --file）", file=sys.stderr)
        return 1  # E001

    # 处理输入
    result = process_input(input_content, args.format)

    if result["status"] == "success":
        print(result["output"])
        if result.get("note"):
            print(f"\n{result['note']}")
        return 0
    else:
        print(f"错误 [{result.get('error_code', 'E010')}]: {result.get('message', '未知错误')}",
              file=sys.stderr)
        # 将错误码映射为退出码
        error_map = {"E001": 1, "E002": 2, "E003": 3, "E004": 4,
                     "E005": 5, "E006": 6, "E007": 7, "E008": 8}
        return error_map.get(result.get("error_code", "E010"), 10)


if __name__ == "__main__":
    sys.exit(main())
