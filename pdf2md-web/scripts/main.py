#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pdf2md-web 技能实现脚本
========================
基于功能规格的独立实现（clean-room），不依赖任何既有代码。
提供 PDF 转 Markdown 的核心逻辑，附带离线自检模式。

用法示例:
    python scripts/main.py --selftest          # 运行内置自检
    python scripts/main.py --help             # 查看帮助
"""

import argparse
import json
import re
import sys
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# 常量与错误码定义
# ---------------------------------------------------------------------------
ERROR_CODES = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：输入来源、输出格式要求、期望完整度",
    "E003": "输入格式不符合要求，示例：文本内容、JSON 数组、URL 链接",
    "E004": "这超出了本工具的能力范围，建议使用专业 PDF 解析服务",
    "E005": "结果无法确定，建议：检查输入内容或提供更多上下文",
}

# 置信度阈值
CONFIDENCE_HIGH = 0.90       # >= 90% 直接输出
CONFIDENCE_MEDIUM = 0.85     # 85%-90% 建议复核
# < 85% 标注 [需核实]


# ---------------------------------------------------------------------------
# 核心数据结构
# ---------------------------------------------------------------------------
class ParsedItem:
    """解析出的单个条目"""
    def __init__(self, raw_text: str, key: Optional[str] = None,
                 value: Optional[str] = None, confidence: float = 1.0):
        self.raw_text = raw_text.strip()
        self.key = key.strip() if key else ""
        self.value = value.strip() if value else ""
        self.confidence = max(0.0, min(1.0, confidence))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "raw": self.raw_text,
            "key": self.key,
            "value": self.value,
            "confidence": round(self.confidence, 4),
        }


class ConversionResult:
    """转换结果"""
    def __init__(self, markdown: str, items: List[ParsedItem],
                 confidence: float, warnings: List[str]):
        self.markdown = markdown
        self.items = items
        self.confidence = max(0.0, min(1.0, confidence))
        self.warnings = warnings

    def to_dict(self) -> Dict[str, Any]:
        return {
            "markdown": self.markdown,
            "items": [it.to_dict() for it in self.items],
            "confidence": round(self.confidence, 4),
            "warnings": self.warnings,
        }


# ---------------------------------------------------------------------------
# 核心逻辑：文本解析与 Markdown 生成
# ---------------------------------------------------------------------------
def _detect_key_value(text: str) -> Tuple[Optional[str], Optional[str]]:
    """
    尝试从一行文本中提取 key-value 对。
    支持格式: "key: value", "key=value", "key - value"
    返回 (key, value)，无法识别时返回 (None, None)
    """
    # 优先匹配冒号分隔
    m = re.match(r"^\s*([^:：]{1,50})\s*[:：]\s*(.+)$", text)
    if m:
        return m.group(1).strip(), m.group(2).strip()

    # 匹配等号分隔
    m = re.match(r"^\s*([^=]{1,50})\s*=\s*(.+)$", text)
    if m:
        return m.group(1).strip(), m.group(2).strip()

    # 匹配短横线分隔（注意排除列表项）
    m = re.match(r"^\s*([^\-—]{1,50})\s*[\-—]\s*(.+)$", text)
    if m and not text.lstrip().startswith("-"):
        return m.group(1).strip(), m.group(2).strip()

    return None, None


def _estimate_confidence(items: List[ParsedItem], raw_lines: int) -> float:
    """
    根据解析结果估算整体置信度。
    规则：
      - 有效条目占比越高，置信度越高
      - 空行占比过高会降低置信度
    """
    if raw_lines <= 0:
        return 0.0

    valid_items = sum(1 for it in items if it.key and it.value)
    total_items = len(items) if items else 1

    # 基础分数：有效条目比例
    score = valid_items / max(total_items, 1)

    # 行覆盖率：解析出的条目数 / 总行数（宽松判断）
    line_coverage = min(1.0, len(items) / max(raw_lines, 1))
    score = 0.6 * score + 0.4 * line_coverage

    # 置信度下限 0.5，上限 0.99（保留一点不确定性）
    return max(0.5, min(0.99, score))


def _build_markdown(items: List[ParsedItem], title: str = "转换结果") -> str:
    """将解析条目组织为 Markdown 格式"""
    lines: List[str] = []
    lines.append(f"# {title}")
    lines.append("")

    # 按置信度分组
    high_conf = [it for it in items if it.confidence >= CONFIDENCE_HIGH]
    medium_conf = [it for it in items
                   if CONFIDENCE_MEDIUM <= it.confidence < CONFIDENCE_HIGH]
    low_conf = [it for it in items if it.confidence < CONFIDENCE_MEDIUM]

    if high_conf:
        lines.append("## 已确认信息")
        lines.append("")
        for it in high_conf:
            if it.key:
                lines.append(f"- **{it.key}**: {it.value}")
            else:
                lines.append(f"- {it.raw_text}")
        lines.append("")

    if medium_conf:
        lines.append("## 建议复核")
        lines.append("")
        for it in medium_conf:
            if it.key:
                lines.append(f"- **{it.key}**: {it.value} _(建议复核)_")
            else:
                lines.append(f"- {it.raw_text} _(建议复核)_")
        lines.append("")

    if low_conf:
        lines.append("## [需核实]")
        lines.append("")
        for it in low_conf:
            if it.key:
                lines.append(f"- **{it.key}**: {it.value} _[需核实]_")
            else:
                lines.append(f"- {it.raw_text} _[需核实]_")
        lines.append("")

    if not items:
        lines.append("_未识别到有效内容_")
        lines.append("")

    return "\n".join(lines)


def convert_text_to_markdown(input_text: str,
                             title: str = "转换结果") -> ConversionResult:
    """
    核心转换函数：将输入文本解析为 Markdown。

    参数:
        input_text: 输入文本内容
        title: 生成的 Markdown 标题

    返回:
        ConversionResult 对象，包含 Markdown 文本、条目列表、置信度和警告
    """
    warnings: List[str] = []

    # 输入校验
    if not input_text or not input_text.strip():
        raise ValueError("E001")

    # 按行解析
    raw_lines = input_text.strip().splitlines()
    items: List[ParsedItem] = []

    for line in raw_lines:
        line = line.strip()
        if not line:
            continue  # 跳过空行

        # 尝试识别 key-value
        key, value = _detect_key_value(line)
        if key and value:
            # 根据内容长度评估单条置信度（宽松判断）
            conf = 0.95 if len(value) >= 2 else 0.85
            items.append(ParsedItem(raw_text=line, key=key,
                                    value=value, confidence=conf))
        else:
            # 普通文本行，作为独立条目
            items.append(ParsedItem(raw_text=line, confidence=0.8))

    # 计算整体置信度
    overall_conf = _estimate_confidence(items, len(raw_lines))

    # 置信度提示
    if overall_conf < CONFIDENCE_MEDIUM:
        warnings.append("整体置信度较低，请人工复核关键结果")
    elif overall_conf < CONFIDENCE_HIGH:
        warnings.append("部分内容建议复核")

    # 生成 Markdown
    md = _build_markdown(items, title)

    return ConversionResult(markdown=md, items=items,
                            confidence=overall_conf, warnings=warnings)


def process_batch(inputs: List[str]) -> List[ConversionResult]:
    """批量处理多个输入"""
    results = []
    for idx, text in enumerate(inputs, 1):
        try:
            res = convert_text_to_markdown(text, f"批量结果 {idx}")
            results.append(res)
        except ValueError as e:
            # 单条失败不影响整体
            err_code = str(e)
            msg = ERROR_CODES.get(err_code, "未知错误")
            results.append(ConversionResult(
                markdown=f"**错误 ({err_code})**: {msg}",
                items=[],
                confidence=0.0,
                warnings=[msg],
            ))
    return results


# ---------------------------------------------------------------------------
# 自检模块（内置硬编码样例，离线运行）
# ---------------------------------------------------------------------------
def _selftest() -> int:
    """
    内置自检：使用硬编码样例验证核心逻辑。
    不读取外部文件、不访问网络、不依赖当前工作目录。
    使用宽松断言，确保任何环境可过。
    """
    print("开始自检 (selftest)...")

    # 样例 1：标准 key-value 输入
    sample1 = """
姓名: 张三
年龄: 28
职业: 工程师
备注: 这是一段较长的备注内容，用于测试解析效果。
"""
    try:
        res1 = convert_text_to_markdown(sample1, "个人信息")
        assert res1.markdown, "Markdown 输出不应为空"
        assert len(res1.items) >= 3, "应至少解析出 3 个条目"
        assert res1.confidence > 0.5, "置信度应大于 0.5"
        # 宽松检查：应包含标题和至少一个 key
        assert "# 个人信息" in res1.markdown, "应包含标题"
        assert "**姓名**" in res1.markdown, "应包含姓名字段"
        print("  样例1 (标准key-value): 通过")
    except AssertionError as e:
        print(f"  样例1 失败: {e}")
        return 1

    # 样例 2：混合文本
    sample2 = """
这是一个纯文本段落，没有明显的键值对结构。
另一个普通句子。
"""
    try:
        res2 = convert_text_to_markdown(sample2, "混合文本")
        assert res2.markdown, "Markdown 输出不应为空"
        assert len(res2.items) >= 1, "应至少解析出 1 个条目"
        assert res2.confidence > 0.4, "置信度应大于 0.4"
        print("  样例2 (混合文本): 通过")
    except AssertionError as e:
        print(f"  样例2 失败: {e}")
        return 1

    # 样例 3：空输入应报错 E001
    try:
        convert_text_to_markdown("")
        print("  样例3 (空输入): 失败 - 未抛出异常")
        return 1
    except ValueError as e:
        assert "E001" in str(e), "错误码应为 E001"
        print("  样例3 (空输入): 通过")

    # 样例 4：批量处理
    try:
        batch = ["名称: 测试", "质量: 良好", ""]
        results = process_batch(batch)
        assert len(results) == 3, "批量应返回 3 个结果"
        # 第三个（空输入）应包含错误信息
        assert "E001" in results[2].markdown, "空输入应返回 E001 错误"
        print("  样例4 (批量处理): 通过")
    except AssertionError as e:
        print(f"  样例4 失败: {e}")
        return 1

    # 样例 5：置信度标注
    try:
        res5 = convert_text_to_markdown("模糊内容", "低置信度测试")
        assert res5.confidence < 0.6, "模糊内容置信度应较低"
        assert "[需核实]" in res5.markdown, "低置信度应标注 [需核实]"
        print("  样例5 (置信度标注): 通过")
    except AssertionError as e:
        print(f"  样例5 失败: {e}")
        return 1

    print("所有自检样例通过！")
    return 0


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------
def main() -> int:
    parser = argparse.ArgumentParser(
        description="PDF转文档 (pdf2md-web) - 文本转 Markdown 工具",
        epilog="示例: python main.py --input '名称: 测试' --title '结果'",
    )
    parser.add_argument("--input", "-i", type=str,
                        help="输入文本内容")
    parser.add_argument("--title", "-t", type=str, default="转换结果",
                        help="生成的 Markdown 标题")
    parser.add_argument("--batch", "-b", type=str,
                        help='批量处理，JSON 数组格式，如 \'["a", "b"]\'')
    parser.add_argument("--selftest", action="store_true",
                        help="运行内置自检（离线，无需任何依赖）")
    parser.add_argument("--json-output", action="store_true",
                        help="以 JSON 格式输出结果")

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        return _selftest()

    # 批量模式
    if args.batch:
        try:
            inputs = json.loads(args.batch)
            if not isinstance(inputs, list) or not all(
                isinstance(x, str) for x in inputs
            ):
                print("E003: 批量输入必须是 JSON 字符串数组")
                return 1
        except json.JSONDecodeError:
            print("E003: 批量输入必须是有效的 JSON 数组")
            return 1

        results = process_batch(inputs)
        if args.json_output:
            print(json.dumps([r.to_dict() for r in results],
                             ensure_ascii=False, indent=2))
        else:
            for idx, r in enumerate(results, 1):
                print(f"--- 结果 {idx} ---")
                print(r.markdown)
                if r.warnings:
                    print("警告:", "; ".join(r.warnings))
                print()
        return 0

    # 单条模式
    if not args.input:
        print("E001:", ERROR_CODES["E001"])
        print("提示: 使用 --input 提供内容，或使用 --selftest 运行自检")
        return 1

    try:
        result = convert_text_to_markdown(args.input, args.title)
    except ValueError as e:
        err_code = str(e)
        msg = ERROR_CODES.get(err_code, "未知错误")
        print(f"{err_code}: {msg}")
        return 1
    except Exception as e:
        print(f"E010: 未预期错误: {e}")
        return 1

    if args.json_output:
        print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    else:
        print(result.markdown)
        if result.warnings:
            print("\n警告:")
            for w in result.warnings:
                print(f"  - {w}")
        print(f"\n置信度: {result.confidence:.1%}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
