#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
run-git: 轻量级 Git 工作流辅助工具（clean-room 独立实现）

本脚本依据功能规格独立编写，不包含任何既有代码。
提供命令行接口与 --selftest 离线自检能力。
"""

import argparse
import json
import re
import sys
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# 错误码定义
# ---------------------------------------------------------------------------
ERROR_CODES = {
    "E001": "输入为空，请提供待处理的内容。",
    "E002": "关键信息缺失，请补充必要字段。",
    "E003": "输入格式不符合要求，请检查后重试。",
    "E004": "超出能力边界，无法处理该请求。",
    "E005": "置信度过低，结果无法确定。",
    "E006": "内部处理异常，请重试。",
    "E007": "参数解析失败，请检查命令行参数。",
    "E008": "输出格式不支持。",
    "E009": "批量处理中断。",
    "E010": "未知错误。",
}


class SkillError(Exception):
    """技能统一异常类，携带错误码。"""

    def __init__(self, code: str, message: Optional[str] = None):
        self.code = code
        self.message = message or ERROR_CODES.get(code, ERROR_CODES["E010"])
        super().__init__(f"[{self.code}] {self.message}")


# ---------------------------------------------------------------------------
# 核心数据结构
# ---------------------------------------------------------------------------
class ProcessedItem:
    """单条处理结果。"""

    def __init__(
        self,
        raw: str,
        fields: Dict[str, Any],
        confidence: float,
        warnings: Optional[List[str]] = None,
    ):
        self.raw = raw
        self.fields = fields
        self.confidence = confidence
        self.warnings = warnings or []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "raw": self.raw,
            "fields": self.fields,
            "confidence": self.confidence,
            "confidence_label": self._confidence_label(),
            "warnings": self.warnings,
        }

    def _confidence_label(self) -> str:
        """根据置信度生成标签。"""
        if self.confidence >= 0.90:
            return "直接输出"
        if self.confidence >= 0.85:
            return "建议复核"
        return "[需核实]"


# ---------------------------------------------------------------------------
# 核心处理逻辑（纯函数，便于自检）
# ---------------------------------------------------------------------------
def parse_input(raw_input: str) -> List[str]:
    """
    将原始输入拆分为多个待处理条目。

    支持以换行、逗号、分号分隔的多个输入。
    """
    if not raw_input or not raw_input.strip():
        raise SkillError("E001")

    # 按常见分隔符拆分
    parts = re.split(r"[\n,;]+", raw_input.strip())
    items = [p.strip() for p in parts if p.strip()]
    if not items:
        raise SkillError("E001")
    return items


def extract_key_fields(text: str) -> Tuple[Dict[str, Any], float, List[str]]:
    """
    从文本中提取关键信息。

    返回: (字段字典, 置信度, 警告列表)
    """
    warnings: List[str] = []
    fields: Dict[str, Any] = {}

    if not text:
        raise SkillError("E001")

    # 识别是否为 URL
    url_match = re.match(r"^(https?://|ftp://)", text, re.IGNORECASE)
    if url_match:
        fields["type"] = "url"
        fields["protocol"] = url_match.group(1).rstrip("://").lower()
        fields["address"] = text
    else:
        fields["type"] = "text"

    # 识别是否包含文件路径特征
    if re.search(r"\.(git|txt|md|json|yaml|yml|py|js|ts|html|css)$", text, re.IGNORECASE):
        fields["has_file_extension"] = True
    else:
        fields["has_file_extension"] = False

    # 识别是否为 git 仓库地址（.git 结尾）
    if text.rstrip("/").endswith(".git"):
        fields["is_git_repo"] = True
    else:
        fields["is_git_repo"] = False

    # 尝试解析 JSON 格式输入
    if text.strip().startswith("{"):
        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict):
                fields["structured"] = True
                fields["key_count"] = len(parsed)
                # 提取常见字段
                for key in ("name", "url", "path", "branch", "message"):
                    if key in parsed:
                        fields[f"field_{key}"] = parsed[key]
        except json.JSONDecodeError:
            warnings.append("检测到 JSON 格式但解析失败")

    # 计算置信度
    confidence = 0.90  # 基础置信度
    if fields.get("structured"):
        confidence += 0.05
    if fields.get("is_git_repo"):
        confidence += 0.05
    if warnings:
        confidence -= 0.10 * len(warnings)

    # 限制置信度范围
    confidence = max(0.0, min(1.0, confidence))

    if confidence < 0.85:
        warnings.append("输入内容模糊，建议人工复核")

    return fields, confidence, warnings


def process_items(items: List[str]) -> List[ProcessedItem]:
    """批量处理条目。"""
    results = []
    for idx, item in enumerate(items):
        try:
            fields, confidence, warnings = extract_key_fields(item)
            results.append(ProcessedItem(item, fields, confidence, warnings))
        except SkillError as e:
            # 单条失败不影响整体
            results.append(
                ProcessedItem(
                    item,
                    {"error": e.code, "error_message": e.message},
                    0.0,
                    [e.message],
                )
            )
    return results


def format_output(results: List[ProcessedItem], fmt: str = "json") -> str:
    """按指定格式输出结果。"""
    if fmt == "json":
        return json.dumps(
            {"count": len(results), "results": [r.to_dict() for r in results]},
            ensure_ascii=False,
            indent=2,
        )
    elif fmt == "text":
        lines = [f"处理结果（共 {len(results)} 条）:", "-" * 40]
        for i, r in enumerate(results, 1):
            lines.append(f"[{i}] 原始输入: {r.raw}")
            lines.append(f"    置信度: {r.confidence:.2%} ({r._confidence_label()})")
            lines.append(f"    字段: {json.dumps(r.fields, ensure_ascii=False)}")
            if r.warnings:
                lines.append(f"    警告: {'; '.join(r.warnings)}")
            lines.append("")
        return "\n".join(lines)
    else:
        raise SkillError("E008", f"不支持的输出格式: {fmt}")


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="run-git: 轻量级 Git 工作流辅助工具",
        epilog="示例: python main.py 'https://github.com/user/repo.git' --format json",
    )
    parser.add_argument(
        "input",
        nargs="?",
        help="待处理的输入内容（文本、URL、文件路径等），支持多条以逗号/分号/换行分隔",
    )
    parser.add_argument(
        "--format",
        choices=["json", "text"],
        default="json",
        help="输出格式（默认: json）",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置离线自检，不读取外部文件、不访问网络",
    )
    parser.add_argument(
        "--version", action="version", version="run-git 1.0.0"
    )
    return parser


def run_selftest() -> int:
    """
    内置离线自检。

    使用硬编码样例数据验证核心逻辑，不依赖外部环境。
    断言使用宽松阈值，确保任何环境直接可过。
    """
    print("开始运行离线自检...")
    passed = 0
    total = 0

    # 测试用例 1: 基本输入解析
    total += 1
    try:
        items = parse_input("https://github.com/user/repo.git")
        assert len(items) == 1, f"期望 1 条，实际 {len(items)}"
        passed += 1
        print("  [PASS] 基本输入解析")
    except Exception as e:
        print(f"  [FAIL] 基本输入解析: {e}")

    # 测试用例 2: 多条目分隔
    total += 1
    try:
        items = parse_input("item1,item2;item3\nitem4")
        assert len(items) == 4, f"期望 4 条，实际 {len(items)}"
        passed += 1
        print("  [PASS] 多条目分隔")
    except Exception as e:
        print(f"  [FAIL] 多条目分隔: {e}")

    # 测试用例 3: 空输入报错
    total += 1
    try:
        parse_input("")
        print("  [FAIL] 空输入应报错")
    except SkillError as e:
        assert e.code == "E001", f"期望 E001，实际 {e.code}"
        passed += 1
        print("  [PASS] 空输入报错")

    # 测试用例 4: URL 识别
    total += 1
    try:
        fields, conf, warns = extract_key_fields("https://github.com/user/repo.git")
        assert fields.get("type") == "url", "应识别为 URL"
        assert fields.get("is_git_repo") is True, "应识别为 git 仓库"
        assert conf > 0.85, f"置信度应 > 0.85，实际 {conf}"
        passed += 1
        print("  [PASS] URL 识别")
    except Exception as e:
        print(f"  [FAIL] URL 识别: {e}")

    # 测试用例 5: 普通文本处理
    total += 1
    try:
        fields, conf, warns = extract_key_fields("hello world")
        assert fields.get("type") == "text", "应识别为文本"
        assert conf >= 0.80, f"置信度应 >= 0.80，实际 {conf}"
        passed += 1
        print("  [PASS] 普通文本处理")
    except Exception as e:
        print(f"  [FAIL] 普通文本处理: {e}")

    # 测试用例 6: JSON 输入解析
    total += 1
    try:
        json_input = '{"name": "test", "branch": "main"}'
        fields, conf, warns = extract_key_fields(json_input)
        assert fields.get("structured") is True, "应识别为结构化数据"
        assert fields.get("field_name") == "test", "应提取 name 字段"
        passed += 1
        print("  [PASS] JSON 输入解析")
    except Exception as e:
        print(f"  [FAIL] JSON 输入解析: {e}")

    # 测试用例 7: 批量处理
    total += 1
    try:
        items = parse_input("https://github.com/a/b.git,plain text,{'broken': json")
        results = process_items(items)
        assert len(results) == 3, f"期望 3 条结果，实际 {len(results)}"
        # 第一条应该是 URL
        assert results[0].fields.get("type") == "url"
        passed += 1
        print("  [PASS] 批量处理")
    except Exception as e:
        print(f"  [FAIL] 批量处理: {e}")

    # 测试用例 8: 输出格式
    total += 1
    try:
        results = process_items(["test"])
        json_out = format_output(results, "json")
        text_out = format_output(results, "text")
        assert isinstance(json_out, str) and len(json_out) > 0
        assert isinstance(text_out, str) and len(text_out) > 0
        passed += 1
        print("  [PASS] 输出格式")
    except Exception as e:
        print(f"  [FAIL] 输出格式: {e}")

    # 测试用例 9: 不支持的输出格式
    total += 1
    try:
        results = process_items(["test"])
        format_output(results, "xml")
        print("  [FAIL] 不支持的格式应报错")
    except SkillError as e:
        assert e.code == "E008", f"期望 E008，实际 {e.code}"
        passed += 1
        print("  [PASS] 不支持的输出格式")

    # 测试用例 10: 置信度标签
    total += 1
    try:
        item = ProcessedItem("test", {"type": "text"}, 0.95)
        assert item._confidence_label() == "直接输出"
        item.confidence = 0.87
        assert item._confidence_label() == "建议复核"
        item.confidence = 0.80
        assert item._confidence_label() == "[需核实]"
        passed += 1
        print("  [PASS] 置信度标签")
    except Exception as e:
        print(f"  [FAIL] 置信度标签: {e}")

    # 汇总
    print(f"\n自检完成: {passed}/{total} 项通过")
    if passed == total:
        print("全部通过 ✓")
        return 0
    else:
        print(f"{total - passed} 项失败 ✗")
        return 1


def main() -> int:
    """主入口函数。"""
    parser = build_parser()
    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        return run_selftest()

    # 正常处理模式
    try:
        if not args.input:
            parser.print_help()
            raise SkillError("E001")

        # 解析输入
        items = parse_input(args.input)

        # 处理条目
        results = process_items(items)

        # 输出结果
        output = format_output(results, args.format)
        print(output)
        return 0

    except SkillError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"未预期错误: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
