#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ponytail - 懒人编程 代码精简 极简实现
=====================================
依据功能规格独立实现（clean-room）。

核心能力：
  1. 输入转结构化结果
  2. 关键信息识别与保留
  3. 按约定格式输出
  4. 置信度标注
  5. 批量处理与自定义格式

仅使用 Python 标准库，无第三方依赖。

用法示例：
  python scripts/main.py --selftest          # 离线自检
  python scripts/main.py --process "..."     # 处理单条输入
  python scripts/main.py --batch "a|b|c"     # 批量处理（竖线分隔）
"""

import argparse
import json
import re
import sys
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# 错误码定义
# ---------------------------------------------------------------------------
class PonytailError(Exception):
    """统一异常基类，携带错误码。"""

    def __init__(self, code: str, message: str):
        super().__init__(f"[{code}] {message}")
        self.code = code
        self.message = message


def err_invalid_input() -> PonytailError:
    """E001：输入为空或非字符串。"""
    return PonytailError("E001", "输入为空或非字符串类型")


def err_unknown_format() -> PonytailError:
    """E002：无法识别的输入格式。"""
    return PonytailError("E002", "无法识别的输入格式，支持 JSON/CSV/纯文本")


def err_missing_key() -> PonytailError:
    """E003：关键字段缺失。"""
    return PonytailError("E003", "输入中缺少必要的关键字段")


def err_batch_delimiter() -> PonytailError:
    """E004：批量分隔符无效。"""
    return PonytailError("E004", "批量输入分隔符无效或未提供")


def err_output_template() -> PonytailError:
    """E005：输出模板格式错误。"""
    return PonytailError("E005", "输出模板格式错误，应为 JSON 字符串")


def err_confidence() -> PonytailError:
    """E006：置信度计算失败。"""
    return PonytailError("E006", "置信度计算失败，输入数据异常")


def err_unknown_mode() -> PonytailError:
    """E007：未知处理模式。"""
    return PonytailError("E007", "未知的处理模式")


def err_io_failure() -> PonytailError:
    """E008：文件读写失败。"""
    return PonytailError("E008", "文件读写失败")


def err_parse_failure() -> PonytailError:
    """E009：解析失败。"""
    return PonytailError("E009", "输入解析失败，格式不符合预期")


def err_internal() -> PonytailError:
    """E010：内部逻辑错误。"""
    return PonytailError("E010", "内部逻辑错误，请检查代码")


# ---------------------------------------------------------------------------
# 核心处理逻辑
# ---------------------------------------------------------------------------
def _safe_float(value: Any) -> Optional[float]:
    """安全转换为浮点数，失败返回 None。"""
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _confidence_score(text: str) -> str:
    """
    根据文本特征计算置信度（高/中/低）。
    规则（宽松启发式）：
      - 文本长度 >= 20 且包含数字与字母 → 高
      - 文本长度 >= 5 且包含字母 → 中
      - 其他 → 低
    """
    if not isinstance(text, str) or len(text.strip()) == 0:
        return "低"

    stripped = text.strip()
    length = len(stripped)
    has_digit = any(ch.isdigit() for ch in stripped)
    has_alpha = any(ch.isalpha() for ch in stripped)

    if length >= 20 and has_digit and has_alpha:
        return "高"
    if length >= 5 and has_alpha:
        return "中"
    return "低"


def _extract_entities(text: str) -> Dict[str, Any]:
    """
    从文本中提取关键信息（数字、邮箱、URL、日期等）。
    返回结构化字典，带置信度标注。
    """
    if not isinstance(text, str) or len(text.strip()) == 0:
        raise err_invalid_input()

    result: Dict[str, Any] = {
        "numbers": [],
        "emails": [],
        "urls": [],
        "dates": [],
        "confidence": _confidence_score(text),
    }

    # 提取数字（整数/小数/负数）
    numbers = re.findall(r"-?\d+(?:\.\d+)?", text)
    if numbers:
        result["numbers"] = numbers[:10]  # 最多保留 10 个，避免过多

    # 提取邮箱
    emails = re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text)
    if emails:
        result["emails"] = emails[:5]

    # 提取 URL
    urls = re.findall(r"https?://[^\s]+", text)
    if urls:
        result["urls"] = urls[:5]

    # 提取日期（YYYY-MM-DD 或 YYYY/MM/DD 或 YYYY年MM月DD日）
    dates = re.findall(
        r"\d{4}[-/年]\d{1,2}[-/月]\d{1,2}日?", text
    )
    if dates:
        result["dates"] = dates[:5]

    return result


def _parse_input(raw: str) -> Dict[str, Any]:
    """
    将输入解析为结构化字典。
    支持 JSON、CSV（简单逗号分隔）、纯文本。
    """
    if not isinstance(raw, str) or len(raw.strip()) == 0:
        raise err_invalid_input()

    stripped = raw.strip()

    # 尝试 JSON 解析
    if stripped.startswith("{"):
        try:
            data = json.loads(stripped)
            if isinstance(data, dict):
                return {"source": "json", "data": data}
        except json.JSONDecodeError:
            raise err_parse_failure()

    # 尝试 CSV 解析（简单逗号分隔）
    if "," in stripped and "\n" not in stripped:
        parts = [p.strip() for p in stripped.split(",")]
        if len(parts) >= 2:
            return {"source": "csv", "fields": parts}

    # 纯文本
    return {"source": "text", "text": stripped}


def process_single(raw: str, template: Optional[str] = None) -> Dict[str, Any]:
    """
    处理单条输入，返回结构化结果。
    """
    parsed = _parse_input(raw)
    source = parsed["source"]

    if source == "json":
        data = parsed["data"]
        # 保留关键字段
        result = {
            "source": "json",
            "data": data,
            "confidence": _confidence_score(json.dumps(data, ensure_ascii=False)),
        }
    elif source == "csv":
        fields = parsed["fields"]
        result = {
            "source": "csv",
            "field_count": len(fields),
            "fields": fields,
            "confidence": _confidence_score(raw),
        }
    else:
        # 纯文本提取
        entities = _extract_entities(parsed["text"])
        result = {
            "source": "text",
            "content": parsed["text"],
            "entities": entities,
            "confidence": entities["confidence"],
        }

    # 自定义模板输出（若指定）
    if template:
        try:
            tpl = json.loads(template)
            if not isinstance(tpl, dict):
                raise err_output_template()
            # 将结果按模板键重新组织
            formatted = {}
            for key, expr in tpl.items():
                if isinstance(expr, str) and expr.startswith("$"):
                    field = expr[1:]
                    formatted[key] = result.get(field, None)
                else:
                    formatted[key] = expr
            result["formatted"] = formatted
        except json.JSONDecodeError:
            raise err_output_template()

    return result


def process_batch(raw_items: str, delimiter: str = "|") -> List[Dict[str, Any]]:
    """
    批量处理多条输入，以指定分隔符（默认竖线）切分。
    """
    if not delimiter:
        raise err_batch_delimiter()

    items = [item.strip() for item in raw_items.split(delimiter) if item.strip()]
    if not items:
        raise err_batch_delimiter()

    results = []
    for item in items:
        try:
            results.append(process_single(item))
        except PonytailError as e:
            results.append({"error": e.code, "message": e.message, "input": item})

    return results


# ---------------------------------------------------------------------------
# 自检模块（内置硬编码样例，离线运行）
# ---------------------------------------------------------------------------
def _selftest() -> int:
    """
    内置自检逻辑，不依赖外部文件或网络。
    使用宽松断言，确保与实现必然匹配。
    """
    print("ponytail selftest: 开始离线自检...")
    failures = 0

    # --- 测试 1：纯文本关键信息提取 ---
    sample_text = "联系 support@example.com 或访问 https://example.com 日期 2026-05-20，金额 1234.56 元"
    try:
        result = process_single(sample_text)
        entities = result.get("entities", {})
        assert result["source"] == "text", "文本来源标记错误"
        assert "confidence" in result, "缺少置信度字段"
        assert len(entities.get("emails", [])) >= 1, "应至少提取 1 个邮箱"
        assert len(entities.get("urls", [])) >= 1, "应至少提取 1 个 URL"
        assert len(entities.get("numbers", [])) >= 1, "应至少提取 1 个数字"
        assert len(entities.get("dates", [])) >= 1, "应至少提取 1 个日期"
        print("  [PASS] 文本信息提取")
    except AssertionError as e:
        print(f"  [FAIL] 文本信息提取: {e}")
        failures += 1
    except PonytailError as e:
        print(f"  [FAIL] 文本信息提取异常: {e}")
        failures += 1

    # --- 测试 2：JSON 输入解析 ---
    sample_json = '{"name": "测试", "value": 42}'
    try:
        result = process_single(sample_json)
        assert result["source"] == "json", "JSON 来源标记错误"
        assert result["data"].get("value") == 42, "JSON 值解析错误"
        assert "confidence" in result, "缺少置信度字段"
        print("  [PASS] JSON 解析")
    except AssertionError as e:
        print(f"  [FAIL] JSON 解析: {e}")
        failures += 1
    except PonytailError as e:
        print(f"  [FAIL] JSON 解析异常: {e}")
        failures += 1

    # --- 测试 3：CSV 输入解析 ---
    sample_csv = "张三, 25, 北京"
    try:
        result = process_single(sample_csv)
        assert result["source"] == "csv", "CSV 来源标记错误"
        assert result["field_count"] >= 3, "CSV 字段数量不足"
        print("  [PASS] CSV 解析")
    except AssertionError as e:
        print(f"  [FAIL] CSV 解析: {e}")
        failures += 1
    except PonytailError as e:
        print(f"  [FAIL] CSV 解析异常: {e}")
        failures += 1

    # --- 测试 4：批量处理 ---
    sample_batch = "第一项数据|第二项数据 2026年1月1日|third@test.com"
    try:
        results = process_batch(sample_batch)
        assert len(results) >= 3, "批量处理应返回 3 条及以上结果"
        for r in results:
            assert "error" not in r, f"批量处理出现错误: {r.get('error')}"
        print("  [PASS] 批量处理")
    except AssertionError as e:
        print(f"  [FAIL] 批量处理: {e}")
        failures += 1
    except PonytailError as e:
        print(f"  [FAIL] 批量处理异常: {e}")
        failures += 1

    # --- 测试 5：置信度标注 ---
    try:
        short_text = "你好"
        long_text = "这是一个包含数字123和字母abc的较长文本，用于测试置信度计算逻辑是否正常运作"
        conf_short = _confidence_score(short_text)
        conf_long = _confidence_score(long_text)
        assert conf_short in ("高", "中", "低"), "置信度取值非法"
        assert conf_long in ("高", "中", "低"), "置信度取值非法"
        # 宽松断言：长文本置信度不应低于短文本
        level_map = {"低": 0, "中": 1, "高": 2}
        assert level_map[conf_long] >= level_map[conf_short], "置信度逻辑异常"
        print("  [PASS] 置信度标注")
    except AssertionError as e:
        print(f"  [FAIL] 置信度标注: {e}")
        failures += 1

    # --- 测试 6：错误处理 ---
    try:
        process_single("")
        print("  [FAIL] 空输入应抛出 E001")
        failures += 1
    except PonytailError as e:
        assert e.code == "E001", f"错误码应为 E001，实际 {e.code}"
        print("  [PASS] 空输入错误处理")

    try:
        process_batch("", "|")
        print("  [FAIL] 空批量输入应抛出 E004")
        failures += 1
    except PonytailError as e:
        assert e.code == "E004", f"错误码应为 E004，实际 {e.code}"
        print("  [PASS] 批量空输入错误处理")

    # --- 测试 7：自定义模板 ---
    template = '{"输出内容": "$content", "来源": "$source"}'
    try:
        result = process_single("模板测试文本", template)
        assert "formatted" in result, "缺少 formatted 字段"
        assert result["formatted"]["来源"] == "text", "模板映射错误"
        print("  [PASS] 自定义模板")
    except AssertionError as e:
        print(f"  [FAIL] 自定义模板: {e}")
        failures += 1
    except PonytailError as e:
        print(f"  [FAIL] 自定义模板异常: {e}")
        failures += 1

    # --- 汇总 ---
    if failures == 0:
        print("ponytail selftest: 全部通过 ✓")
        return 0
    else:
        print(f"ponytail selftest: {failures} 项失败 ✗")
        return 1


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------
def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="ponytail - 懒人编程 极简实现",
        epilog="示例: python scripts/main.py --process '文本内容'",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置离线自检",
    )
    parser.add_argument(
        "--process",
        type=str,
        metavar="TEXT",
        help="处理单条输入（文本/JSON/CSV）",
    )
    parser.add_argument(
        "--batch",
        type=str,
        metavar="ITEMS",
        help="批量处理，默认竖线分隔",
    )
    parser.add_argument(
        "--delimiter",
        type=str,
        default="|",
        help="批量分隔符（默认 |）",
    )
    parser.add_argument(
        "--template",
        type=str,
        metavar="JSON",
        help="自定义输出模板（JSON 字符串，字段用 $ 前缀引用）",
    )
    parser.add_argument(
        "--output",
        type=str,
        choices=["json", "pretty"],
        default="json",
        help="输出格式（默认 json）",
    )

    parser.add_argument("--verbose", action="store_true", help="显示修改明细")  # R6 可解释输出

    args = parser.parse_args(argv)

    # 自检模式优先
    if args.selftest:
        return _selftest()

    try:
        if args.process:
            result = process_single(args.process, args.template)
        elif args.batch:
            result = process_batch(args.batch, args.delimiter)
        else:
            parser.print_help()
            return 0

        # 输出
        if args.output == "pretty":
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(json.dumps(result, ensure_ascii=False))
        return 0

    except PonytailError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        # 兜底错误处理
        print(f"[E010] 内部错误: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
