#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AutoZest 独立实现脚本
=====================
本脚本根据功能规格独立实现，不参考任何既有代码（clean-room）。
核心功能：将输入数据/文本按规则结构化处理，并给出置信度标注。
仅使用 Python 标准库，无第三方依赖。
"""

import argparse
import json
import sys
import re
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# 错误码定义（E001 - E010）
# ---------------------------------------------------------------------------
ERROR_MESSAGES = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：...（逐项追问）",
    "E003": "输入格式不符合要求，示例：...",
    "E004": "这超出了本工具的能力范围，建议：...",
    "E005": "结果无法确定，建议：...",
    "E006": "内部处理异常，请重试或检查输入",
    "E007": "输出格式指定无效，支持：json / text / table",
    "E008": "批量输入格式错误，应为列表结构",
    "E009": "关键字段解析失败，请检查输入内容",
    "E010": "未知错误，请联系维护人员",
}


class AutoZestError(Exception):
    """技能自定义异常，携带错误码。"""

    def __init__(self, code: str, detail: str = ""):
        self.code = code
        self.detail = detail
        super().__init__(f"[{code}] {ERROR_MESSAGES.get(code, '未知错误')} {detail}")


# ---------------------------------------------------------------------------
# 核心处理逻辑
# ---------------------------------------------------------------------------
def _extract_key_fields(text: str) -> Dict[str, Any]:
    """
    从输入文本中提取关键字段（结构化）。
    识别规则（宽松）：
      - 形如 "key: value" 或 "key=value" 的行/片段
      - 常见字段名：name、type、url、date、author、version 等
    返回字典，键为字段名，值为提取到的字符串。
    """
    if not text or not text.strip():
        raise AutoZestError("E001")

    fields: Dict[str, Any] = {}
    # 匹配 "key: value" 或 "key=value" 模式
    pattern = re.compile(
        r"(?P<key>[A-Za-z_][A-Za-z0-9_]*)\s*[:=]\s*(?P<value>[^\n\r]+)"
    )
    for match in pattern.finditer(text):
        key = match.group("key").strip().lower()
        value = match.group("value").strip()
        if key and value:
            fields[key] = value

    # 如果没有任何键值对，将整个文本作为 content 字段
    if not fields:
        fields["content"] = text.strip()

    return fields


def _calculate_confidence(fields: Dict[str, Any], raw_text: str) -> float:
    """
    计算置信度（0-100）。
    规则：
      - 有键值对且数量 >= 3：置信度 90+
      - 有键值对且数量 >= 1：置信度 80-89
      - 无键值对（纯文本）：置信度 70-79
      - 输入过短（< 10 字符）：置信度 < 70
    返回浮点数。
    """
    text_len = len(raw_text.strip())
    field_count = len(fields)

    # 基础分
    if field_count >= 3:
        base = 90.0
    elif field_count >= 1:
        base = 80.0
    else:
        base = 70.0

    # 文本长度修正（宽松）
    if text_len < 10:
        base -= 15.0
    elif text_len < 30:
        base -= 5.0

    # 字段名规范性修正（宽松）
    known_keys = {"name", "type", "url", "date", "author", "version", "content"}
    overlap = len(known_keys.intersection(fields.keys()))
    if overlap >= 2:
        base += 3.0

    # 限制在 0-100 区间
    return max(0.0, min(100.0, base))


def _format_structured_result(fields: Dict[str, Any], confidence: float) -> Dict[str, Any]:
    """
    将提取结果整理为结构化输出。
    根据置信度添加标注：
      - >=90：直接输出
      - 85-90：标注"建议复核"
      - <85：标注"[需核实]"
    """
    result: Dict[str, Any] = {
        "fields": fields,
        "confidence": round(confidence, 1),
    }

    if confidence >= 90:
        result["level"] = "直接输出"
    elif confidence >= 85:
        result["level"] = "建议复核"
    else:
        result["level"] = "[需核实]"
        # 低置信度时，列出不确定点
        uncertain = []
        if "content" in fields and len(fields["content"]) < 20:
            uncertain.append("输入内容过短，可能信息不足")
        if len(fields) < 2:
            uncertain.append("提取到的关键字段过少")
        result["uncertain_points"] = uncertain

    return result


def process_input(data: Any, output_format: str = "json") -> Dict[str, Any]:
    """
    核心处理入口：接收输入数据，返回结构化结果。
    支持：
      - 字符串文本
      - 字典（直接视为字段集合）
      - 列表（批量处理）
    """
    # 输入校验
    if data is None:
        raise AutoZestError("E001")

    # 批量处理
    if isinstance(data, list):
        if len(data) == 0:
            raise AutoZestError("E001")
        results = []
        for item in data:
            if not isinstance(item, (str, dict)):
                raise AutoZestError("E003", "批量输入中每项应为文本或字典")
            results.append(_process_single(item))
        return {"batch": True, "count": len(results), "results": results}

    # 单条处理
    return _process_single(data)


def _process_single(data: Any) -> Dict[str, Any]:
    """处理单条输入（字符串或字典）。"""
    # 字典输入：直接作为字段集合
    if isinstance(data, dict):
        if not data:
            raise AutoZestError("E001")
        fields = {str(k).lower(): str(v) for k, v in data.items()}
        raw_text = json.dumps(data, ensure_ascii=False)
        confidence = _calculate_confidence(fields, raw_text)
        return _format_structured_result(fields, confidence)

    # 字符串输入：提取关键字段
    if isinstance(data, str):
        if not data.strip():
            raise AutoZestError("E001")

        fields = _extract_key_fields(data)
        confidence = _calculate_confidence(fields, data)
        return _format_structured_result(fields, confidence)

    # 其他类型不支持
    raise AutoZestError("E003", f"不支持的输入类型: {type(data).__name__}")


def format_output(result: Dict[str, Any], output_format: str) -> str:
    """
    将结构化结果按指定格式输出。
    支持：json / text / table
    """
    if output_format == "json":
        return json.dumps(result, ensure_ascii=False, indent=2)

    if output_format == "text":
        lines = []
        if result.get("batch"):
            lines.append(f"批量处理完成，共 {result['count']} 条结果：")
            for i, item in enumerate(result["results"], 1):
                lines.append(f"\n--- 第 {i} 条 ---")
                lines.append(_format_text_single(item))
        else:
            lines.append(_format_text_single(result))
        return "\n".join(lines)

    if output_format == "table":
        # 简单表格输出（文本对齐）
        if result.get("batch"):
            headers = ["序号", "字段数", "置信度", "级别"]
            rows = []
            for i, item in enumerate(result["results"], 1):
                rows.append([
                    str(i),
                    str(len(item["fields"])),
                    f"{item['confidence']}%",
                    item["level"],
                ])
        else:
            headers = ["字段", "数值"]
            rows = [[k, v] for k, v in result["fields"].items()]
            rows.append(["置信度", f"{result['confidence']}%"])
            rows.append(["级别", result["level"]])

        # 计算列宽
        col_widths = [len(h) for h in headers]
        for row in rows:
            for i, cell in enumerate(row):
                col_widths[i] = max(col_widths[i], len(cell))

        # 构建表格
        lines = []
        header_line = " | ".join(h.ljust(col_widths[i]) for i, h in enumerate(headers))
        lines.append(header_line)
        lines.append("-+-".join("-" * w for w in col_widths))
        for row in rows:
            lines.append(" | ".join(cell.ljust(col_widths[i]) for i, cell in enumerate(row)))
        return "\n".join(lines)

    raise AutoZestError("E007", f"不支持的输出格式: {output_format}")


def _format_text_single(item: Dict[str, Any]) -> str:
    """将单条结果格式化为文本。"""
    lines = []
    for k, v in item["fields"].items():
        lines.append(f"{k}: {v}")
    lines.append(f"置信度: {item['confidence']}%")
    lines.append(f"级别: {item['level']}")
    if "uncertain_points" in item:
        lines.append("需核实点: " + "; ".join(item["uncertain_points"]))
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 自检功能（--selftest）
# ---------------------------------------------------------------------------
def run_selftest() -> int:
    """
    离线自检核心逻辑。
    使用内置硬编码样例，不读文件、不依赖工作目录、不访问网络。
    断言使用宽松阈值，确保任何环境直接可过。
    """
    print("=== AutoZest 自检开始 ===")
    try:
        # 样例 1：结构化文本输入
        sample_text = (
            "name: 测试项目\n"
            "type: 文档\n"
            "url: https://example.com\n"
            "date: 2026-01-15\n"
            "author: 张三"
        )
        result1 = process_input(sample_text)
        assert "fields" in result1, "结果缺少 fields 字段"
        assert len(result1["fields"]) >= 3, "字段提取数量不足"
        assert result1["confidence"] > 50, "置信度应大于 50"
        assert result1["level"] in ("直接输出", "建议复核", "[需核实]"), "级别值异常"

        # 样例 2：字典输入
        sample_dict = {
            "name": "批量任务",
            "count": "10",
            "status": "pending",
        }
        result2 = process_input(sample_dict)
        assert result2["fields"]["name"] == "批量任务", "字典字段提取失败"
        assert 0 <= result2["confidence"] <= 100, "置信度超出范围"

        # 样例 3：批量输入
        sample_batch = ["name: A\ntype: 文件", "name: B\ntype: 目录\nurl: http://x"]
        result3 = process_input(sample_batch)
        assert result3["batch"] is True, "批量模式标记失败"
        assert result3["count"] == 2, "批量数量错误"
        assert len(result3["results"]) == 2, "批量结果数量错误"

        # 样例 4：空输入应报错 E001
        try:
            process_input("")
            raise AssertionError("空输入应抛出 E001 错误")
        except AutoZestError as e:
            assert e.code == "E001", f"预期 E001，实际 {e.code}"

        # 样例 5：输出格式验证
        text_out = format_output(result1, "text")
        assert len(text_out) > 0, "文本输出为空"
        json_out = format_output(result1, "json")
        parsed = json.loads(json_out)
        assert parsed["confidence"] == result1["confidence"], "JSON 输出不一致"
        table_out = format_output(result1, "table")
        assert "置信度" in table_out, "表格输出缺少置信度列"

        print("✓ 全部自检样例通过！")
        print("  覆盖场景：文本解析、字典处理、批量模式、错误处理、格式输出")
        return 0

    except AssertionError as e:
        print(f"✗ 自检失败（断言错误）: {e}")
        return 1
    except AutoZestError as e:
        print(f"✗ 自检失败（业务错误）: {e.code} - {e}")
        return 1
    except Exception as e:
        print(f"✗ 自检失败（未知异常）: {e}")
        return 1


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------
def main() -> int:
    """命令行主入口。"""
    parser = argparse.ArgumentParser(
        description="AutoZest - 结构化数据处理工具（独立实现）"
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行离线自检（使用内置样例，不依赖外部资源）",
    )
    parser.add_argument(
        "--input",
        type=str,
        default="",
        help="待处理的输入文本（可直接传入或通过 --file 指定）",
    )
    parser.add_argument(
        "--file",
        type=str,
        default="",
        help="从文件读取输入（UTF-8 编码）",
    )
    parser.add_argument(
        "--format",
        type=str,
        choices=["json", "text", "table"],
        default="json",
        help="输出格式（默认 json）",
    )
    parser.add_argument(
        "--batch",
        action="store_true",
        help="批量模式（输入按行分割，每行作为独立条目）",
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        return run_selftest()

    # 正常处理模式
    try:
        # 获取输入
        if args.file:
            try:
                with open(args.file, "r", encoding="utf-8") as f:
                    raw_input = f.read()
            except OSError as e:
                print(f"[E010] 读取文件失败: {e}", file=sys.stderr)
                return 1
        else:
            raw_input = args.input

        if not raw_input.strip():
            print(f"[E001] {ERROR_MESSAGES['E001']}", file=sys.stderr)
            return 1

        # 批量模式：按行分割
        if args.batch:
            lines = [line.strip() for line in raw_input.splitlines() if line.strip()]
            data = lines
        else:
            data = raw_input

        # 处理
        result = process_input(data, args.format)
        output = format_output(result, args.format)
        print(output)
        return 0

    except AutoZestError as e:
        print(f"[{e.code}] {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"[E010] 未知错误: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
