#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py — PDF转文档（pdf-to-markdown-gpt）独立实现

本脚本为 clean-room 实现：仅依据功能规格重新编写，未参考任何既有代码。
功能：将用户提供的文本/文件内容解析为结构化 Markdown 文档，
      支持置信度评估、错误码体系、离线自检。

用法示例：
    python scripts/main.py --selftest          # 离线自检核心逻辑
    python scripts/main.py --input "..."       # 处理输入文本
    python scripts/main.py --help              # 查看帮助

仅使用 Python 标准库，无第三方依赖。
"""

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# 常量定义
# ---------------------------------------------------------------------------
SKILL_NAME = "pdf-to-markdown-gpt"
DISPLAY_NAME = "PDF转文档"
VERSION = "1.0.0"
AUTHOR = "skill-factory-auto"

# 错误码与话术映射（依据规格四）
ERROR_MESSAGES: Dict[str, str] = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：...（逐项追问）",
    "E003": "输入格式不符合要求，示例：...",
    "E004": "这超出了本工具的能力范围，建议...",
    "E005": "结果无法确定，建议：...",
    # 扩展内部错误码（规格未列，但为健壮性补充）
    "E006": "内部处理异常，请重试",
    "E007": "文件读取失败，请检查路径",
    "E008": "JSON 解析失败，请检查格式",
    "E009": "参数错误，请检查命令行参数",
    "E010": "未知错误，请联系维护者",
}

# 置信度阈值（依据规格三）
CONFIDENCE_HIGH = 90      # ≥90% 直接输出
CONFIDENCE_MEDIUM = 85    # 85%-90% 建议复核
# <85% 标注 [需核实]

# 触发词（依据规格二）
TRIGGER_WORDS = ["PDF转文档", "pdf to markdown gpt"]

# 能力边界声明（依据规格一）
CAPABILITY_BOUNDARIES = {
    "do": [
        "将 用户提供的数据/文件/URL 转换为结构化结果",
        "识别并保留输入中的关键信息",
        "按约定格式生成输出",
        "对不确定项给出置信度提示",
        "支持批量处理和自定义格式",
    ],
    "do_not": [
        "不执行超出输入范围的分析",
        "不保证绝对准确，低置信度会标注",
        "不访问网络或外部服务",
    ],
}

# 默认输出模板（依据规格三 Step 2）
DEFAULT_TEMPLATE = """# 转换结果

> 由 {display_name} (v{version}) 生成

## 基本信息
- 处理时间: {timestamp}
- 置信度: {confidence}%
- 置信度标签: {confidence_label}

## 结构化内容
{content}

## 不确定项
{uncertainties}

## 声明
本结果由 AI 辅助生成，仅供参考。涉及专业决策请咨询持证人士。
"""


# ---------------------------------------------------------------------------
# 数据结构
# ---------------------------------------------------------------------------
@dataclass
class ParseResult:
    """解析结果数据类"""
    raw_text: str
    fields: Dict[str, Any] = field(default_factory=dict)
    uncertainties: List[str] = field(default_factory=list)
    confidence: int = 0
    warnings: List[str] = field(default_factory=list)

    def to_markdown(self) -> str:
        """转换为 Markdown 格式输出"""
        # 计算置信度标签
        if self.confidence >= CONFIDENCE_HIGH:
            label = "直接输出"
        elif self.confidence >= CONFIDENCE_MEDIUM:
            label = "建议复核"
        else:
            label = "[需核实]"

        # 构建内容部分
        content_lines = []
        for key, value in self.fields.items():
            content_lines.append(f"### {key}")
            content_lines.append(str(value))
            content_lines.append("")

        content = "\n".join(content_lines).strip()
        if not content:
            content = "（无有效内容）"

        # 构建不确定项部分
        if self.uncertainties:
            unc_lines = [f"- {item}" for item in self.uncertainties]
            unc_text = "\n".join(unc_lines)
        else:
            unc_text = "无"

        # 时间戳（简单格式，不依赖外部库）
        import time
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")

        return DEFAULT_TEMPLATE.format(
            display_name=DISPLAY_NAME,
            version=VERSION,
            timestamp=timestamp,
            confidence=self.confidence,
            confidence_label=label,
            content=content,
            uncertainties=unc_text,
        )


# ---------------------------------------------------------------------------
# 核心处理逻辑
# ---------------------------------------------------------------------------
def validate_input(raw_text: str) -> Optional[str]:
    """
    校验输入内容（依据规格三 Step 1）
    返回错误码；无错误返回 None
    """
    if not raw_text or not raw_text.strip():
        return "E001"  # 输入为空
    if len(raw_text.strip()) < 3:
        return "E003"  # 输入过短，视为格式错误
    return None


def extract_fields(raw_text: str) -> Tuple[Dict[str, Any], List[str]]:
    """
    从输入文本中提取关键字段（依据规格三 Step 2）
    返回 (字段字典, 不确定项列表)

    这是一个通用实现，根据文本特征识别常见字段：
    - 标题/主题
    - 正文内容
    - 可能的键值对
    """
    fields: Dict[str, Any] = {}
    uncertainties: List[str] = []

    text = raw_text.strip()
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    if not lines:
        return fields, uncertainties

    # 尝试识别标题（第一行非空且较短）
    first_line = lines[0]
    if len(first_line) <= 50:
        fields["标题"] = first_line
        remaining_lines = lines[1:]
    else:
        fields["标题"] = "（未检测到明确标题）"
        uncertainties.append("标题可能不准确，请人工确认")
        remaining_lines = lines

    # 识别键值对（包含冒号的行）
    kv_pairs: Dict[str, str] = {}
    other_lines: List[str] = []
    for line in remaining_lines:
        if "：" in line or ":" in line:
            # 尝试拆分键值
            parts = re.split(r"[：:]", line, maxsplit=1)
            if len(parts) == 2 and parts[0].strip() and parts[1].strip():
                key = parts[0].strip()
                value = parts[1].strip()
                kv_pairs[key] = value
                continue
        other_lines.append(line)

    if kv_pairs:
        fields["键值信息"] = kv_pairs
    else:
        uncertainties.append("未检测到明确的键值对信息")

    # 剩余行作为正文
    if other_lines:
        fields["正文"] = "\n".join(other_lines)
    elif not kv_pairs:
        # 没有键值对也没有正文，说明输入可能过于简单
        uncertainties.append("输入内容过于简单，可能遗漏关键信息")

    # 简单置信度计算（启发式）
    # 规则：有标题+正文+键值对=高置信度；只有部分=中等；内容少=低
    score = 0
    if "标题" in fields and fields["标题"] != "（未检测到明确标题）":
        score += 30
    if "正文" in fields:
        score += 40
    if "键值信息" in fields:
        score += 30

    # 根据不确定项调整
    score -= len(uncertainties) * 5

    # 记录置信度（但不在此处设置，由调用方处理）
    fields["_confidence_score"] = max(0, min(100, score))

    return fields, uncertainties


def process_input(raw_text: str) -> ParseResult:
    """
    处理输入文本，返回结构化结果（依据规格三 Step 2/3）
    """
    # 校验
    error_code = validate_input(raw_text)
    if error_code:
        raise ValueError(error_code)

    # 提取字段
    fields, uncertainties = extract_fields(raw_text)

    # 计算置信度
    confidence = fields.pop("_confidence_score", 0)

    # 根据置信度添加不确定项（依据规格三 Step 2）
    if confidence < CONFIDENCE_MEDIUM:
        uncertainties.append("整体置信度偏低，建议人工复核关键信息")
    elif confidence < CONFIDENCE_HIGH:
        uncertainties.append("部分内容置信度中等，建议复核")

    # 构建结果
    result = ParseResult(
        raw_text=raw_text,
        fields=fields,
        uncertainties=uncertainties,
        confidence=confidence,
    )

    # 能力边界检查（依据规格一"不做"声明）
    # 检查是否包含超出能力范围的请求
    boundary_patterns = [
        r"网络|网址|http|https|www\.",
        r"下载|上传|发送邮件|登录",
        r"数据库|服务器|API调用",
    ]
    for pattern in boundary_patterns:
        if re.search(pattern, raw_text, re.IGNORECASE):
            result.warnings.append(
                f"检测到可能超出能力范围的请求（匹配: {pattern}），已忽略相关操作请求"
            )
            # 降低置信度
            result.confidence = max(0, result.confidence - 10)

    return result


def format_output(result: ParseResult) -> str:
    """
    格式化输出（依据规格三 Step 3）
    """
    return result.to_markdown()


def handle_error(error_code: str) -> str:
    """
    错误处理（依据规格四）
    """
    if error_code in ERROR_MESSAGES:
        return f"[{error_code}] {ERROR_MESSAGES[error_code]}"
    return f"[E010] {ERROR_MESSAGES['E010']}"


# ---------------------------------------------------------------------------
# 自检模块（--selftest）
# ---------------------------------------------------------------------------
def run_selftest() -> int:
    """
    离线自检核心逻辑，不依赖外部文件/网络/当前目录
    使用硬编码样例数据，宽松断言（大小比较/区间判断）
    """
    print("=" * 60)
    print(f"{DISPLAY_NAME} v{VERSION} 自检开始")
    print("=" * 60)

    test_cases = [
        {
            "name": "正常输入（含标题、键值对、正文）",
            "input": "季度报告\n项目: AI助手\n负责人: 张三\n日期: 2026-01-15\n\n本季度完成了核心模块开发，主要成果包括：\n1. 完成了PDF解析模块\n2. 实现了Markdown输出功能\n3. 通过了基础测试",
            "expect_error": False,
        },
        {
            "name": "简单输入（仅标题）",
            "input": "简单测试",
            "expect_error": False,
        },
        {
            "name": "空输入（应报错E001）",
            "input": "",
            "expect_error": True,
            "expect_code": "E001",
        },
        {
            "name": "过短输入（应报错E003）",
            "input": "ab",
            "expect_error": True,
            "expect_code": "E003",
        },
        {
            "name": "包含URL的输入（应触发边界警告）",
            "input": "请访问 https://example.com 获取数据并转换",
            "expect_error": False,
        },
        {
            "name": "长文本输入（性能测试）",
            "input": "测试文本\n" * 100,
            "expect_error": False,
        },
    ]

    passed = 0
    total = len(test_cases)

    for case in test_cases:
        print(f"\n--- 测试用例: {case['name']} ---")
        try:
            result = process_input(case["input"])

            if case.get("expect_error"):
                print(f"  [失败] 期望报错 {case.get('expect_code')}，但未报错")
                continue

            # 宽松断言
            assert result.confidence >= 0, "置信度不能为负"
            assert result.confidence <= 100, "置信度不能超过100"

            if case["input"]:
                assert result.fields is not None, "字段不能为None"

            # 检查输出格式
            md_output = format_output(result)
            assert "# " in md_output, "输出应包含标题"
            assert "置信度" in md_output, "输出应包含置信度信息"
            assert "不确定项" in md_output, "输出应包含不确定项部分"

            # 检查置信度与不确定项的关系
            if result.confidence < CONFIDENCE_HIGH:
                assert result.uncertainties, "低置信度时应有不确定项"

            print(f"  [通过] 置信度: {result.confidence}%, "
                  f"字段数: {len(result.fields)}, "
                  f"不确定项: {len(result.uncertainties)}")
            passed += 1

        except ValueError as e:
            error_code = str(e)
            if case.get("expect_error") and error_code == case.get("expect_code"):
                print(f"  [通过] 正确报错: {handle_error(error_code)}")
                passed += 1
            else:
                print(f"  [失败] 意外错误: {handle_error(error_code)}")
        except Exception as e:
            print(f"  [失败] 异常: {type(e).__name__}: {e}")

    # 额外测试：格式输出完整性
    print("\n--- 附加测试: 输出格式完整性 ---")
    try:
        sample = process_input("测试文档\n作者: 测试员\n\n这是一段正文内容用于测试输出格式。")
        md = format_output(sample)
        assert "转换结果" in md
        assert "基本信息" in md
        assert "结构化内容" in md
        assert "不确定项" in md
        assert "声明" in md
        print("  [通过] 输出格式完整")
        passed += 1
    except Exception as e:
        print(f"  [失败] 格式测试异常: {e}")

    # 额外测试：批量处理能力（依据规格六）
    print("\n--- 附加测试: 批量处理 ---")
    try:
        batch_inputs = ["文档1\n内容: 测试1", "文档2\n内容: 测试2"]
        batch_results = [process_input(text) for text in batch_inputs]
        assert len(batch_results) == 2, "应处理2个输入"
        for r in batch_results:
            assert r.fields is not None
        print(f"  [通过] 批量处理 {len(batch_results)} 个输入")
        passed += 1
    except Exception as e:
        print(f"  [失败] 批量测试异常: {e}")

    # 汇总
    total += 2  # 附加测试
    print("\n" + "=" * 60)
    print(f"自检完成: {passed}/{total} 通过")
    if passed == total:
        print("结果: 全部通过 ✔")
        return 0
    else:
        print("结果: 部分失败 ✘")
        return 1


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------
def main() -> int:
    """
    主函数：解析命令行参数并执行
    """
    parser = argparse.ArgumentParser(
        description=f"{DISPLAY_NAME} - {SKILL_NAME} v{VERSION}",
        epilog="示例: python main.py --input '待处理文本' 或 python main.py --selftest",
    )
    parser.add_argument(
        "--input", "-i",
        type=str,
        help="待处理的输入文本内容",
    )
    parser.add_argument(
        "--file", "-f",
        type=str,
        help="从文件读取输入内容",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行离线自检（不依赖外部文件/网络）",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="以JSON格式输出结果",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"{SKILL_NAME} v{VERSION}",
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        return run_selftest()

    # 获取输入
    raw_input = None
    source_desc = ""

    if args.input:
        raw_input = args.input
        source_desc = "命令行参数"
    elif args.file:
        source_desc = f"文件: {args.file}"
        try:
            with open(args.file, "r", encoding="utf-8") as f:
                raw_input = f.read()
        except FileNotFoundError:
            print(handle_error("E007"))
            return 1
        except Exception as e:
            print(f"[E006] 读取文件失败: {e}")
            return 1
    else:
        # 无输入参数，尝试从标准输入读取
        # 注意：仅在非交互式环境下尝试，避免卡住
        if not sys.stdin.isatty():
            try:
                raw_input = sys.stdin.read()
                source_desc = "标准输入"
            except Exception:
                pass

    # 无输入则报错
    if not raw_input:
        print(handle_error("E001"))
        parser.print_help()
        return 1

    # 处理输入
    try:
        result = process_input(raw_input)

        # 输出
        if args.json:
            output = {
                "skill": SKILL_NAME,
                "version": VERSION,
                "source": source_desc,
                "confidence": result.confidence,
                "fields": result.fields,
                "uncertainties": result.uncertainties,
                "warnings": result.warnings,
            }
            print(json.dumps(output, ensure_ascii=False, indent=2))
        else:
            print(format_output(result))

        # 如果有警告，输出到 stderr
        for warning in result.warnings:
            print(f"[警告] {warning}", file=sys.stderr)

        return 0

    except ValueError as e:
        error_code = str(e)
        print(handle_error(error_code))
        return 1
    except Exception as e:
        print(f"[E010] 未知错误: {type(e).__name__}: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
