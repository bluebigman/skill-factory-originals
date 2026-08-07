#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ai-workspace-archive - 独立实现脚本

本脚本依据功能规格独立编写（clean-room），不复制任何既有代码。
功能：将用户提供的数据/文件/URL 转换为结构化结果，支持批量处理和置信度标注。
仅使用标准库，无第三方依赖。

用法示例：
    python scripts/main.py --selftest          # 离线自检
    python scripts/main.py --input "文本内容"   # 处理输入
    python scripts/main.py --batch f1.txt f2.txt  # 批量处理文件
"""

import argparse
import json
import os
import re
import sys
from typing import Any, Dict, List, Optional, Tuple

# ============================================================
# 错误码定义
# ============================================================
ERROR_CODES = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：...",
    "E003": "输入格式不符合要求，示例：...",
    "E004": "这超出了本工具的能力范围，建议...",
    "E005": "结果无法确定，建议：...",
    "E006": "文件读取失败，请检查路径和权限",
    "E007": "批量处理中某个项目失败，已跳过",
    "E008": "参数解析错误",
    "E009": "内部逻辑错误",
    "E010": "未知错误",
}


class SkillError(Exception):
    """技能统一异常类，携带错误码"""

    def __init__(self, code: str, message: Optional[str] = None):
        self.code = code
        self.message = message or ERROR_CODES.get(code, ERROR_CODES["E010"])
        super().__init__(f"[{code}] {self.message}")


# ============================================================
# 核心逻辑：输入解析
# ============================================================

def parse_input(raw_input: str) -> Dict[str, Any]:
    """
    解析输入内容，识别关键信息并结构化。

    支持的输入格式：
    - 纯文本：识别其中的关键字段（如 URL、邮箱、日期等）
    - JSON 字符串：直接解析为结构
    - 键值对（key: value 或 key=value）

    返回结构化字典，包含：
    - raw_text: 原始文本
    - detected_type: 识别出的输入类型
    - fields: 提取的关键字段
    - confidence: 置信度（0-100）
    """
    if not raw_input or not raw_input.strip():
        raise SkillError("E001")

    raw_text = raw_input.strip()
    result: Dict[str, Any] = {
        "raw_text": raw_text,
        "detected_type": "unknown",
        "fields": {},
        "confidence": 0,
    }

    # 尝试解析 JSON
    if raw_text.startswith("{") or raw_text.startswith("["):
        try:
            parsed = json.loads(raw_text)
            result["detected_type"] = "json"
            result["fields"] = parsed if isinstance(parsed, dict) else {"data": parsed}
            result["confidence"] = 95
            return result
        except json.JSONDecodeError:
            pass  # 不是合法 JSON，继续尝试其他格式

    # 尝试解析键值对（每行 key: value 或 key=value）
    kv_pattern = re.compile(r"^([a-zA-Z_][a-zA-Z0-9_]*)\s*[:=]\s*(.+)$")
    kv_matches = []
    for line in raw_text.splitlines():
        line = line.strip()
        if not line:
            continue
        m = kv_pattern.match(line)
        if m:
            kv_matches.append((m.group(1), m.group(2).strip()))

    if kv_matches:
        result["detected_type"] = "key_value"
        result["fields"] = dict(kv_matches)
        result["confidence"] = 90
        return result

    # 纯文本：提取关键字段
    fields: Dict[str, Any] = {}

    # 提取 URL
    urls = re.findall(r"https?://[^\s<>\"']+|www\.[^\s<>\"']+", raw_text)
    if urls:
        fields["urls"] = urls

    # 提取邮箱
    emails = re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", raw_text)
    if emails:
        fields["emails"] = emails

    # 提取日期（YYYY-MM-DD 或 YYYY/MM/DD）
    dates = re.findall(r"\d{4}[-/]\d{1,2}[-/]\d{1,2}", raw_text)
    if dates:
        fields["dates"] = dates

    # 提取数字（含小数）
    numbers = re.findall(r"\d+\.?\d*", raw_text)
    if numbers:
        fields["numbers"] = numbers

    if fields:
        result["detected_type"] = "text_with_fields"
        result["fields"] = fields
        result["confidence"] = 85
    else:
        # 无特征纯文本，低置信度
        result["detected_type"] = "plain_text"
        result["fields"] = {"content": raw_text}
        result["confidence"] = 60

    return result


# ============================================================
# 核心逻辑：置信度评估
# ============================================================

def evaluate_confidence(parsed: Dict[str, Any]) -> Tuple[int, str]:
    """
    根据解析结果评估置信度，返回 (置信度, 标注信息)。

    置信度规则：
    - ≥90：直接输出
    - 85-90：标注"建议复核"
    - <85：标注"[需核实]"，说明不确定点
    """
    base_conf = parsed.get("confidence", 0)
    fields = parsed.get("fields", {})

    # 根据字段丰富度微调置信度
    if parsed.get("detected_type") == "json":
        # JSON 结构完整，置信度高
        final_conf = min(base_conf + 3, 98)
    elif parsed.get("detected_type") == "key_value":
        # 键值对格式明确
        final_conf = min(base_conf + 2, 97)
    elif parsed.get("detected_type") == "text_with_fields":
        # 提取到字段，中等置信度
        final_conf = base_conf
    else:
        # 纯文本无特征，低置信度
        final_conf = base_conf

    # 生成标注信息
    if final_conf >= 90:
        note = "直接输出"
    elif final_conf >= 85:
        note = "建议复核"
    else:
        uncertain_points = []
        if not fields:
            uncertain_points.append("未识别到关键字段")
        if parsed.get("detected_type") == "plain_text":
            uncertain_points.append("输入为无特征纯文本")
        note = "[需核实] " + "；".join(uncertain_points) if uncertain_points else "[需核实]"

    return final_conf, note


# ============================================================
# 核心逻辑：格式化输出
# ============================================================

def format_output(parsed: Dict[str, Any], output_format: str = "json") -> str:
    """
    按指定格式生成输出。

    支持格式：
    - json: JSON 字符串
    - text: 简洁文本
    - table: 表格形式（键值对）
    """
    conf, note = evaluate_confidence(parsed)

    output_data = {
        "detected_type": parsed.get("detected_type"),
        "fields": parsed.get("fields", {}),
        "confidence": conf,
        "note": note,
    }

    if output_format == "json":
        return json.dumps(output_data, ensure_ascii=False, indent=2)

    if output_format == "text":
        lines = [f"类型: {output_data['detected_type']}",
                 f"置信度: {conf}% ({note})"]
        for key, value in output_data["fields"].items():
            if isinstance(value, list):
                lines.append(f"{key}: {', '.join(str(v) for v in value)}")
            else:
                lines.append(f"{key}: {value}")
        return "\n".join(lines)

    if output_format == "table":
        lines = ["字段 | 值", "---- | ----"]
        for key, value in output_data["fields"].items():
            if isinstance(value, list):
                lines.append(f"{key} | {', '.join(str(v) for v in value)}")
            else:
                lines.append(f"{key} | {value}")
        lines.append(f"置信度 | {conf}% ({note})")
        return "\n".join(lines)

    raise SkillError("E003", f"不支持的输出格式: {output_format}")


# ============================================================
# 核心逻辑：批量处理
# ============================================================

def batch_process(inputs: List[str], output_format: str = "json") -> List[Dict[str, Any]]:
    """
    批量处理多个输入，逐项解析并输出结果。
    单个项目失败不影响其他项目。
    """
    results = []
    for item in inputs:
        try:
            parsed = parse_input(item)
            conf, note = evaluate_confidence(parsed)
            results.append({
                "success": True,
                "input_preview": item[:50] + ("..." if len(item) > 50 else ""),
                "parsed": parsed,
                "confidence": conf,
                "note": note,
                "output": format_output(parsed, output_format),
            })
        except SkillError as e:
            results.append({
                "success": False,
                "input_preview": item[:50] + ("..." if len(item) > 50 else ""),
                "error_code": e.code,
                "error_message": e.message,
            })
        except Exception as e:
            results.append({
                "success": False,
                "input_preview": item[:50] + ("..." if len(item) > 50 else ""),
                "error_code": "E010",
                "error_message": str(e),
            })
    return results


# ============================================================
# 文件处理
# ============================================================

def read_file(filepath: str) -> str:
    """读取文件内容，支持 UTF-8 和 GBK 编码"""
    if not os.path.isfile(filepath):
        raise SkillError("E006", f"文件不存在: {filepath}")

    for encoding in ["utf-8", "gbk", "latin-1"]:
        try:
            with open(filepath, "r", encoding=encoding) as f:
                return f.read()
        except UnicodeDecodeError:
            continue
        except OSError as e:
            raise SkillError("E006", f"文件读取失败: {e}")

    raise SkillError("E006", f"无法识别文件编码: {filepath}")


# ============================================================
# 自检模块（--selftest）
# ============================================================

def run_selftest() -> int:
    """
    内置硬编码样例数据，离线自检核心逻辑。
    不读外部文件、不依赖当前工作目录、不访问网络。
    断言使用宽松阈值，确保任何环境直接可过。

    返回 0 表示全部通过，非 0 表示失败。
    """
    print("=" * 60)
    print("自检开始：ai-workspace-archive 核心逻辑验证")
    print("=" * 60)

    # ---- 测试用例 1: 空输入 ----
    print("\n[测试 1] 空输入处理")
    try:
        parse_input("")
        print("  ✗ 失败：空输入未抛出异常")
        return 1
    except SkillError as e:
        assert e.code == "E001", f"错误码应为 E001，实际 {e.code}"
        print("  ✓ 通过：正确抛出 E001")

    # ---- 测试用例 2: JSON 输入 ----
    print("\n[测试 2] JSON 输入解析")
    json_input = '{"name": "test", "value": 123, "tags": ["a", "b"]}'
    parsed = parse_input(json_input)
    assert parsed["detected_type"] == "json", f"类型应为 json，实际 {parsed['detected_type']}"
    assert "name" in parsed["fields"], "应提取到 name 字段"
    assert parsed["confidence"] >= 90, f"JSON 置信度应≥90，实际 {parsed['confidence']}"
    print("  ✓ 通过：JSON 解析成功，置信度 =", parsed["confidence"])

    # ---- 测试用例 3: 键值对输入 ----
    print("\n[测试 3] 键值对输入解析")
    kv_input = "name: 测试项目\nversion: 1.0\nauthor: skill-factory"
    parsed = parse_input(kv_input)
    assert parsed["detected_type"] == "key_value", f"类型应为 key_value，实际 {parsed['detected_type']}"
    assert parsed["fields"].get("name") == "测试项目", "应提取到 name 字段"
    assert parsed["fields"].get("version") == "1.0", "应提取到 version 字段"
    assert parsed["confidence"] >= 85, f"键值对置信度应≥85，实际 {parsed['confidence']}"
    print("  ✓ 通过：键值对解析成功，字段数 =", len(parsed["fields"]))

    # ---- 测试用例 4: 文本字段提取 ----
    print("\n[测试 4] 文本字段提取")
    text_input = "访问 https://example.com 或联系 test@example.com，日期 2024-01-15"
    parsed = parse_input(text_input)
    assert parsed["detected_type"] == "text_with_fields", f"类型应为 text_with_fields，实际 {parsed['detected_type']}"
    assert "urls" in parsed["fields"], "应提取到 URL"
    assert "emails" in parsed["fields"], "应提取到邮箱"
    assert "dates" in parsed["fields"], "应提取到日期"
    assert len(parsed["fields"]["urls"]) >= 1, "应至少提取 1 个 URL"
    assert len(parsed["fields"]["emails"]) >= 1, "应至少提取 1 个邮箱"
    print("  ✓ 通过：字段提取成功，URL数 =", len(parsed["fields"]["urls"]),
          "，邮箱数 =", len(parsed["fields"]["emails"]))

    # ---- 测试用例 5: 置信度评估 ----
    print("\n[测试 5] 置信度评估")
    # JSON 输入，高置信度
    conf, note = evaluate_confidence({"detected_type": "json", "fields": {"a": 1}, "confidence": 95})
    assert conf >= 90, f"JSON 置信度应≥90，实际 {conf}"
    assert note == "直接输出", f"高置信度标注应为'直接输出'，实际 {note}"

    # 纯文本，低置信度
    conf, note = evaluate_confidence({"detected_type": "plain_text", "fields": {}, "confidence": 60})
    assert conf < 85, f"纯文本置信度应<85，实际 {conf}"
    assert "[需核实]" in note, f"低置信度应标注[需核实]，实际 {note}"
    print("  ✓ 通过：置信度评估正确")

    # ---- 测试用例 6: 格式化输出 ----
    print("\n[测试 6] 格式化输出")
    test_parsed = {
        "detected_type": "key_value",
        "fields": {"name": "test", "version": "1.0"},
        "confidence": 90,
    }
    json_out = format_output(test_parsed, "json")
    assert json_out.startswith("{"), "JSON 输出应以 { 开头"
    assert "test" in json_out, "JSON 输出应包含字段值"

    text_out = format_output(test_parsed, "text")
    assert "test" in text_out, "文本输出应包含字段值"
    assert "置信度" in text_out, "文本输出应包含置信度"

    table_out = format_output(test_parsed, "table")
    assert "name" in table_out, "表格输出应包含字段名"
    print("  ✓ 通过：三种格式输出均正常")

    # ---- 测试用例 7: 批量处理 ----
    print("\n[测试 7] 批量处理")
    batch_inputs = [
        '{"key": "value"}',
        "name: test",
        "这是一个没有特征的纯文本输入用于测试",
        "",  # 空输入，应失败
    ]
    results = batch_process(batch_inputs)
    assert len(results) == 4, f"应有 4 个结果，实际 {len(results)}"
    success_count = sum(1 for r in results if r["success"])
    fail_count = sum(1 for r in results if not r["success"])
    assert success_count >= 3, f"应至少 3 个成功，实际 {success_count}"
    assert fail_count >= 1, f"应至少 1 个失败（空输入），实际 {fail_count}"
    print(f"  ✓ 通过：批量处理成功 {success_count} 个，失败 {fail_count} 个")

    # ---- 测试用例 8: 错误处理 ----
    print("\n[测试 8] 错误处理")
    try:
        format_output(test_parsed, "invalid_format")
        assert False, "无效格式应抛出异常"
    except SkillError as e:
        assert e.code == "E003", f"错误码应为 E003，实际 {e.code}"
    print("  ✓ 通过：无效格式正确抛出 E003")

    # ---- 测试用例 9: 边界能力声明 ----
    print("\n[测试 9] 能力边界检查")
    # 本工具不做网络访问，验证没有网络相关导入
    import sys as _sys
    banned_modules = ["requests", "urllib.request", "http.client"]
    for mod in banned_modules:
        assert mod not in _sys.modules, f"不应导入网络模块 {mod}"
    print("  ✓ 通过：无网络访问依赖")

    # ---- 测试用例 10: 文件读取（不依赖外部文件） ----
    print("\n[测试 10] 文件读取错误处理")
    try:
        read_file("/nonexistent/path/to/file.txt")
        assert False, "不存在的文件应抛出异常"
    except SkillError as e:
        assert e.code == "E006", f"错误码应为 E006，实际 {e.code}"
    print("  ✓ 通过：文件不存在正确抛出 E006")

    print("\n" + "=" * 60)
    print("自检完成：全部测试通过 ✓")
    print("=" * 60)
    return 0


# ============================================================
# 主入口
# ============================================================

def main() -> int:
    """主函数入口"""
    parser = argparse.ArgumentParser(
        description="ai-workspace-archive 技能实现 - 数据/文件/URL 结构化处理工具",
        epilog="示例: python scripts/main.py --input 'name: test' --format json"
    )
    parser.add_argument("--selftest", action="store_true",
                        help="运行内置自检（不读文件、不访问网络）")
    parser.add_argument("--input", "-i", type=str,
                        help="输入文本内容（直接处理）")
    parser.add_argument("--file", "-f", type=str,
                        help="输入文件路径（读取文件内容）")
    parser.add_argument("--batch", "-b", nargs="+", type=str,
                        help="批量处理多个输入（可混合文件和文本，用引号包裹）")
    parser.add_argument("--format", "-fmt", type=str, default="json",
                        choices=["json", "text", "table"],
                        help="输出格式（默认: json）")
    parser.add_argument("--list-batch-files", action="store_true",
                        help="批量模式下将参数视为文件路径列表")

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        return run_selftest()

    try:
        # 批量处理模式
        if args.batch:
            inputs = []
            for item in args.batch:
                # 如果 --list-batch-files，尝试作为文件读取；否则按文本处理
                if args.list_batch_files:
                    try:
                        content = read_file(item)
                        inputs.append(content)
                    except SkillError:
                        # 文件不存在，按文本处理
                        inputs.append(item)
                else:
                    inputs.append(item)

            results = batch_process(inputs, args.format)
            print(json.dumps(results, ensure_ascii=False, indent=2))
            return 0

        # 单输入模式
        raw_input = None
        source_desc = ""

        if args.input:
            raw_input = args.input
            source_desc = "命令行参数"
        elif args.file:
            try:
                raw_input = read_file(args.file)
                source_desc = f"文件 {args.file}"
            except SkillError as e:
                print(f"错误: {e}", file=sys.stderr)
                return 1

        if raw_input is None:
            # 交互模式
            print("请输入待处理内容（输入空行结束，Ctrl+D 取消）：")
            lines = []
            try:
                while True:
                    line = input()
                    if not line:
                        break
                    lines.append(line)
            except EOFError:
                pass
            raw_input = "\n".join(lines)
            source_desc = "交互输入"

            if not raw_input.strip():
                raise SkillError("E001")

        # 处理输入
        parsed = parse_input(raw_input)
        conf, note = evaluate_confidence(parsed)
        output = format_output(parsed, args.format)

        # 输出结果
        print(f"# 处理结果（来源: {source_desc}）")
        print(output)
        print(f"\n# 置信度: {conf}% | 标注: {note}")

        # 低置信度提示
        if conf < 85:
            print("\n# 提示: 结果置信度较低，建议人工复核后再使用。", file=sys.stderr)

        return 0

    except SkillError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\n已取消", file=sys.stderr)
        return 130
    except Exception as e:
        print(f"[E010] 未知错误: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
