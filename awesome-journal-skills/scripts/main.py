#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py — Journal-sp 技能核心逻辑（全新独立实现）

本脚本依据《awesome-journal-skills》功能规格独立编写，
不复制任何既有代码。提供命令行入口与离线自检能力。
"""

import argparse
import json
import os
import sys
import re
from typing import Any, Dict, List, Optional, Tuple

# ------------------------------------------------------------
# 常量定义
# ------------------------------------------------------------
SLUG = "awesome-journal-skills"
NAME = "Journal-sp"
VERSION = "1.0.0"

# 错误码 → 标准话术映射（依据规格第四章）
ERROR_MESSAGES = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：...（逐项追问）",
    "E003": "输入格式不符合要求，示例：...",
    "E004": "这超出了本工具的能力范围，建议...",
    "E005": "结果无法确定，建议：...",
    "E006": "内部处理异常，请重试或检查输入。",
    "E007": "输出序列化失败，请检查数据完整性。",
    "E008": "自检失败，核心逻辑存在缺陷。",
    "E009": "参数解析错误，请检查命令行参数。",
    "E010": "未知错误，请查看日志。",
}

# 置信度阈值（依据规格第三章）
CONFIDENCE_HIGH = 0.90       # ≥90% 直接输出
CONFIDENCE_MEDIUM = 0.85     # 85%-90% 建议复核
CONFIDENCE_LOW = 0.85        # <85% 标注[需核实]

# 支持的关键字段（依据规格：识别并保留输入中的关键信息）
KEY_FIELDS = [
    "title",        # 标题
    "author",       # 作者
    "journal",      # 期刊名称
    "year",         # 年份
    "doi",          # DOI 标识
    "abstract",     # 摘要
    "keywords",     # 关键词
]


# ------------------------------------------------------------
# 核心数据结构
# ------------------------------------------------------------
class ProcessingResult:
    """处理结果封装，包含结构化数据与置信度标注。"""

    def __init__(self, data: Dict[str, Any], confidence: float, notes: List[str] = None):
        self.data = data
        self.confidence = confidence
        self.notes = notes if notes is not None else []

    def to_dict(self) -> Dict[str, Any]:
        """转为字典格式，便于序列化输出。"""
        return {
            "data": self.data,
            "confidence": self.confidence,
            "confidence_label": self._confidence_label(),
            "notes": self.notes,
        }

    def _confidence_label(self) -> str:
        """根据置信度生成标注标签（依据规格 Step 2）。"""
        if self.confidence >= CONFIDENCE_HIGH:
            return "直接输出"
        elif self.confidence >= CONFIDENCE_MEDIUM:
            return "建议复核"
        else:
            return "[需核实]"


# ------------------------------------------------------------
# 核心处理逻辑
# ------------------------------------------------------------
def validate_input(raw_input: str) -> None:
    """
    校验输入合法性。
    对应错误码：E001（输入为空）、E003（格式错误）
    """
    if raw_input is None or raw_input.strip() == "":
        raise ValueError("E001")

    # 基础格式检查：仅允许可打印字符（含中文、标点、换行）
    if not re.match(r"^[\w\s\.,;:!?()\[\]{}\-—–&%$#@+/\\\"'<>《》【】，。；：！？、·\n\r\t]+$",
                    raw_input, flags=re.UNICODE):
        raise ValueError("E003")


def extract_key_fields(text: str) -> Dict[str, Any]:
    """
    从输入文本中提取关键字段（依据规格 Step 2）。
    使用正则与启发式规则，不依赖外部库。
    """
    fields: Dict[str, Any] = {}

    # 标题提取：通常为第一行非空内容
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    if lines:
        fields["title"] = lines[0]

    # 作者提取：常见模式 "作者: xxx" 或 "by xxx"
    author_match = re.search(r"(?:作者|by|author)[:\s]+([^\n]+)", text, re.IGNORECASE)
    if author_match:
        fields["author"] = author_match.group(1).strip()

    # 期刊提取：常见模式 "期刊: xxx" 或 "journal: xxx"
    journal_match = re.search(r"(?:期刊|journal)[:\s]+([^\n]+)", text, re.IGNORECASE)
    if journal_match:
        fields["journal"] = journal_match.group(1).strip()

    # 年份提取：4位数字
    year_match = re.search(r"\b(19|20)\d{2}\b", text)
    if year_match:
        fields["year"] = int(year_match.group(0))

    # DOI 提取：标准 DOI 格式
    doi_match = re.search(r"\b10\.\d{4,9}/[-._;()/:A-Z0-9]+\b", text, re.IGNORECASE)
    if doi_match:
        fields["doi"] = doi_match.group(0)

    # 摘要提取：常见模式 "摘要: xxx" 或 "abstract: xxx"
    abstract_match = re.search(r"(?:摘要|abstract)[:\s]+(.+)", text, re.IGNORECASE | re.DOTALL)
    if abstract_match:
        fields["abstract"] = abstract_match.group(1).strip()

    # 关键词提取：常见模式 "关键词: a, b, c"
    keywords_match = re.search(r"(?:关键词|keywords)[:\s]+(.+)", text, re.IGNORECASE)
    if keywords_match:
        raw_kw = keywords_match.group(1).strip()
        fields["keywords"] = [k.strip() for k in re.split(r"[,，;；]", raw_kw) if k.strip()]

    return fields


def compute_confidence(fields: Dict[str, Any]) -> Tuple[float, List[str]]:
    """
    计算置信度并生成标注说明（依据规格 Step 2）。
    规则：字段覆盖率越高，置信度越高。
    """
    if not fields:
        return 0.0, ["未提取到任何关键字段"]

    filled = sum(1 for key in KEY_FIELDS if fields.get(key))
    ratio = filled / len(KEY_FIELDS)

    # 基础置信度 = 字段覆盖率，加上少量修正
    confidence = ratio * 1.0

    notes = []
    if confidence < CONFIDENCE_LOW:
        notes.append("关键信息提取不完整，请人工补充")
    if confidence < CONFIDENCE_MEDIUM:
        notes.append("存在低置信度字段，请核实")

    # 特殊规则：DOI 存在则提升置信度（DOI 是强标识）
    if fields.get("doi"):
        confidence = min(confidence + 0.05, 1.0)

    return round(confidence, 3), notes


def process_input(raw_input: str) -> ProcessingResult:
    """
    核心处理流程（依据规格 Step 2）：
    1. 校验输入
    2. 提取关键字段
    3. 计算置信度
    4. 生成结果
    """
    # Step 1: 输入校验
    validate_input(raw_input)

    # Step 2: 提取字段
    fields = extract_key_fields(raw_input)

    # 检查关键信息缺失（对应 E002）
    if not fields:
        raise ValueError("E002")

    # Step 3: 置信度计算
    confidence, notes = compute_confidence(fields)

    # Step 4: 生成结果
    return ProcessingResult(data=fields, confidence=confidence, notes=notes)


def format_output(result: ProcessingResult, output_format: str = "json") -> str:
    """
    按指定格式输出结果（依据规格 Step 3）。
    支持 json / text 两种格式。
    """
    result_dict = result.to_dict()

    if output_format == "json":
        try:
            return json.dumps(result_dict, ensure_ascii=False, indent=2)
        except (TypeError, ValueError) as e:
            raise ValueError("E007") from e

    elif output_format == "text":
        lines = []
        lines.append(f"=== {NAME} 处理结果 ===")
        lines.append(f"置信度: {result.confidence:.1%} ({result_dict['confidence_label']})")

        for key, value in result.data.items():
            if isinstance(value, list):
                lines.append(f"{key}: {', '.join(value)}")
            else:
                lines.append(f"{key}: {value}")

        if result.notes:
            lines.append("说明:")
            for note in result.notes:
                lines.append(f"  - {note}")

        return "\n".join(lines)

    else:
        raise ValueError("E003")


# ------------------------------------------------------------
# 批量处理（依据规格第六章：批量处理）
# ------------------------------------------------------------
def batch_process(inputs: List[str], output_format: str = "json") -> List[Dict[str, Any]]:
    """批量处理多个输入，返回结果列表。"""
    results = []
    for raw_input in inputs:
        try:
            result = process_input(raw_input)
            results.append(result.to_dict())
        except ValueError as e:
            code = str(e)
            results.append({
                "error": code,
                "message": ERROR_MESSAGES.get(code, ERROR_MESSAGES["E010"]),
                "input_preview": raw_input[:50] + ("..." if len(raw_input) > 50 else ""),
            })
    return results


# ------------------------------------------------------------
# 自检模块（依据要求：内置硬编码样例数据离线自检）
# ------------------------------------------------------------
def run_selftest() -> int:
    """
    离线自检核心逻辑。
    使用内置硬编码数据，不读外部文件、不访问网络。
    返回 0 表示通过，非 0 表示失败。
    """
    print("[自检] 开始...")

    # 样例 1: 完整学术引用（高置信度场景）
    sample_full = (
        "标题: 经济学研究的新范式\n"
        "作者: 张三, 李四\n"
        "期刊: 经济研究\n"
        "年份: 2023\n"
        "DOI: 10.1234/abc.2023.001\n"
        "摘要: 本文探讨了现代经济学研究的新方法论。\n"
        "关键词: 经济学, 方法论, 研究范式"
    )

    # 样例 2: 部分信息（低置信度场景）
    sample_partial = "某篇关于细胞生物学的文章，提到了 Nature 期刊 2021 年的内容。"

    # 样例 3: 空输入（错误码场景）
    sample_empty = "   "

    # ---- 测试 1: 完整输入处理 ----
    try:
        result = process_input(sample_full)
        assert result.confidence >= 0.9, f"置信度应≥90%，实际: {result.confidence}"
        assert result.data.get("title") is not None, "标题未提取"
        assert result.data.get("author") is not None, "作者未提取"
        assert result.data.get("journal") is not None, "期刊未提取"
        assert result.data.get("year") is not None, "年份未提取"
        assert result.data.get("doi") is not None, "DOI未提取"
        print(f"[自检] 完整输入处理 ✓ (置信度: {result.confidence:.1%})")
    except Exception as e:
        print(f"[自检] 完整输入处理 ✗: {e}")
        return 1

    # ---- 测试 2: 部分输入处理 ----
    try:
        result = process_input(sample_partial)
        assert result.confidence < 0.9, f"置信度应<90%，实际: {result.confidence}"
        print(f"[自检] 部分输入处理 ✓ (置信度: {result.confidence:.1%})")
    except Exception as e:
        print(f"[自检] 部分输入处理 ✗: {e}")
        return 1

    # ---- 测试 3: 空输入错误处理 ----
    try:
        process_input(sample_empty)
        print("[自检] 空输入错误处理 ✗: 未抛出异常")
        return 1
    except ValueError as e:
        assert str(e) == "E001", f"错误码应为E001，实际: {e}"
        print("[自检] 空输入错误处理 ✓ (E001)")

    # ---- 测试 4: 批量处理 ----
    try:
        results = batch_process([sample_full, sample_partial, sample_empty])
        assert len(results) == 3, f"批量结果数量应为3，实际: {len(results)}"
        assert results[0].get("data") is not None, "第一条结果无数据"
        assert results[2].get("error") == "E001", "第三条应返回E001错误"
        print("[自检] 批量处理 ✓")
    except Exception as e:
        print(f"[自检] 批量处理 ✗: {e}")
        return 1

    # ---- 测试 5: 输出格式 ----
    try:
        result = process_input(sample_full)
        json_output = format_output(result, "json")
        assert json.loads(json_output)["confidence"] >= 0.9, "JSON输出置信度不符"
        text_output = format_output(result, "text")
        assert "置信度" in text_output, "文本输出缺少置信度"
        print("[自检] 输出格式 ✓")
    except Exception as e:
        print(f"[自检] 输出格式 ✗: {e}")
        return 1

    # ---- 测试 6: 错误码完整性 ----
    try:
        for code in ["E001", "E002", "E003", "E004", "E005", "E006", "E007", "E008", "E009", "E010"]:
            assert code in ERROR_MESSAGES, f"缺少错误码 {code}"
        print("[自检] 错误码完整性 ✓")
    except Exception as e:
        print(f"[自检] 错误码完整性 ✗: {e}")
        return 1

    print("[自检] 全部通过 ✓")
    return 0


# ------------------------------------------------------------
# CLI 入口
# ------------------------------------------------------------
def create_parser() -> argparse.ArgumentParser:
    """创建命令行参数解析器。"""
    parser = argparse.ArgumentParser(
        prog="main.py",
        description=f"{NAME} - 学术期刊数据智能处理工具 (v{VERSION})",
        epilog=f"示例: python main.py --input '标题: xxx 作者: xxx' --format json"
    )
    parser.add_argument(
        "--input", "-i",
        type=str,
        help="待处理的输入内容（支持文本或文件路径）"
    )
    parser.add_argument(
        "--format", "-f",
        type=str,
        choices=["json", "text"],
        default="json",
        help="输出格式 (默认: json)"
    )
    parser.add_argument(
        "--batch",
        type=str,
        help="批量处理文件路径（每行一个输入）"
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行离线自检并退出"
    )
    return parser


def read_input_source(source: str) -> str:
    """
    读取输入内容。
    支持直接文本或文件路径（自动检测）。
    """
    # 检查是否为文件路径
    if os.path.isfile(source):
        try:
            with open(source, "r", encoding="utf-8") as f:
                return f.read()
        except (IOError, OSError) as e:
            raise ValueError("E006") from e
    else:
        # 视为直接文本输入
        return source


def main() -> int:
    """主程序入口。"""
    parser = create_parser()
    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        return run_selftest()

    # 参数校验
    if not args.input and not args.batch:
        parser.print_help()
        print(f"\n[错误] {ERROR_MESSAGES['E001']}", file=sys.stderr)
        return 1

    try:
        # 批量模式
        if args.batch:
            try:
                with open(args.batch, "r", encoding="utf-8") as f:
                    inputs = [line.strip() for line in f if line.strip()]
            except (IOError, OSError) as e:
                print(f"[错误] {ERROR_MESSAGES['E006']}: {e}", file=sys.stderr)
                return 1

            if not inputs:
                print(f"[错误] {ERROR_MESSAGES['E001']}", file=sys.stderr)
                return 1

            results = batch_process(inputs, args.format)
            print(json.dumps(results, ensure_ascii=False, indent=2))
            return 0

        # 单条模式
        raw_input = read_input_source(args.input)
        result = process_input(raw_input)
        output = format_output(result, args.format)
        print(output)
        return 0

    except ValueError as e:
        code = str(e)
        message = ERROR_MESSAGES.get(code, ERROR_MESSAGES["E010"])
        print(f"[错误 {code}] {message}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"[错误 E010] 未知异常: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
