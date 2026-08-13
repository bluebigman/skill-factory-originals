#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py — 笔记整理 信息归档 结构重构 (skill-81820)

一站式笔记整理技能，覆盖识别、整理、生成与校验，输出可直接使用的结构化结果文件。

功能规格版本: 1.0.1
"""

import argparse
import datetime
import os
import re
import sys
import traceback
from pathlib import Path

# ---------------------------------------------------------------------------
# 错误码定义
# ---------------------------------------------------------------------------
ERROR_CODES = {
    "E001": "输入内容为空",
    "E002": "输入超过长度限制",
    "E003": "无法识别有效结构",
    "E004": "校验发现缺失项",
    "E005": "OCR疑似错误",
    "E006": "输入类型错误",
    "E007": "文件读取失败",
    "E008": "文件写入失败",
    "E009": "路径不合法",
    "E010": "内部逻辑错误",
}

MAX_INPUT_LENGTH = 50000
MAX_PLACEHOLDER_COUNT = 5
DEFAULT_ENCODINGS = ["utf-8", "gbk", "gb18030"]


# ---------------------------------------------------------------------------
# 输入校验
# ---------------------------------------------------------------------------
def validate_input(content):
    """
    校验输入内容。

    参数:
        content: 待处理的笔记内容

    返回:
        校验通过返回内容本身

    异常:
        ValueError: 携带错误码
    """
    if content is None:
        raise ValueError("E006: " + ERROR_CODES["E006"] + "（内容为 None）")

    if not isinstance(content, str):
        raise ValueError("E006: " + ERROR_CODES["E006"] + f"（期望 str，实际 {type(content).__name__}）")

    if not content.strip():
        raise ValueError("E001: " + ERROR_CODES["E001"])

    if len(content) > MAX_INPUT_LENGTH:
        raise ValueError("E002: " + ERROR_CODES["E002"] + f"（当前 {len(content)} 字符）")

    return content


def validate_output_path(path_str):
    """
    校验输出路径。

    参数:
        path_str: 输出文件路径字符串

    返回:
        Path 对象

    异常:
        ValueError: 路径不合法
    """
    if not path_str or not isinstance(path_str, str):
        raise ValueError("E009: " + ERROR_CODES["E009"] + "（路径为空或类型错误）")

    path = Path(path_str).expanduser().resolve()

    # 白名单校验：只允许当前目录或子目录
    cwd = Path.cwd().resolve()
    try:
        path.relative_to(cwd)
    except ValueError:
        raise ValueError("E009: " + ERROR_CODES["E009"] + f"（路径 {path} 不在当前工作目录内）")

    # 禁止写入敏感系统目录
    forbidden_prefixes = ["/etc", "/usr", "/bin", "/sbin", "/var", "/proc", "/sys"]
    for prefix in forbidden_prefixes:
        if str(path).startswith(prefix):
            raise ValueError("E009: " + ERROR_CODES["E009"] + f"（禁止写入系统目录 {prefix}）")

    return path


# ---------------------------------------------------------------------------
# 核心逻辑：笔记解析与整理
# ---------------------------------------------------------------------------
def extract_title(lines):
    """
    从文本行中提取标题。

    参数:
        lines: 文本行列表

    返回:
        (标题文本, 是否自动提取)
    """
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        # 优先取 Markdown 标题
        if stripped.startswith("#"):
            title = stripped.lstrip("#").strip()
            if title:
                return title, False
        # 取第一个非空短句（不超过 30 字）作为标题
        if len(stripped) <= 30:
            return stripped, True
        # 取第一行前 20 字
        return stripped[:20], True
    return "[需核实:笔记主题]", True


def extract_paragraphs(text):
    """
    将文本拆分为段落列表。

    参数:
        text: 原始文本

    返回:
        段落列表
    """
    # 按空行拆分
    raw_paragraphs = re.split(r"\n\s*\n", text)
    paragraphs = []
    for para in raw_paragraphs:
        cleaned = para.strip()
        if cleaned:
            paragraphs.append(cleaned)
    return paragraphs


def extract_list_items(paragraph):
    """
    从段落中提取列表项。

    参数:
        paragraph: 段落文本

    返回:
        (列表项列表, 是否为列表段落)
    """
    lines = paragraph.split("\n")
    items = []
    is_list = False
    for line in lines:
        stripped = line.strip()
        # 匹配 -、*、+、1. 等列表符号
        match = re.match(r"^[-*+]\s+(.+)$", stripped) or re.match(r"^\d+[.、]\s*(.+)$", stripped)
        if match:
            items.append(match.group(1).strip())
            is_list = True
    return items, is_list


def extract_action_items(text):
    """
    从文本中提取行动项（含"需""要""必须""待办"等词的句子）。

    参数:
        text: 原始文本

    返回:
        行动项列表
    """
    action_keywords = ["需", "要", "必须", "待办", "务必", "记得"]
    sentences = re.split(r"[。！？!?；;\n]", text)
    actions = []
    for sentence in sentences:
        stripped = sentence.strip()
        if not stripped:
            continue
        if any(kw in stripped for kw in action_keywords):
            # 去掉列表符号
            cleaned = re.sub(r"^[-*+\d.、\s]+", "", stripped)
            if cleaned:
                actions.append(cleaned)
    return actions


def extract_entities(text):
    """
    提取关键实体（人名、日期、项目名、数字指标）。

    参数:
        text: 原始文本

    返回:
        实体字典
    """
    entities = {"dates": [], "numbers": [], "names": []}

    # 日期：YYYY-MM-DD 或 YYYY年MM月DD日
    date_patterns = [
        r"\d{4}[-/年]\d{1,2}[-/月]\d{1,2}日?",
        r"\d{1,2}月\d{1,2}日",
    ]
    for pattern in date_patterns:
        entities["dates"].extend(re.findall(pattern, text))

    # 数字指标：百分比、金额等
    number_patterns = [
        r"\d+(?:\.\d+)?%",
        r"¥\s*\d+(?:\.\d+)?",
        r"\d+(?:\.\d+)?万元",
    ]
    for pattern in number_patterns:
        entities["numbers"].extend(re.findall(pattern, text))

    # 人名：简单模式（XX 说/提出/表示）
    name_pattern = r"([\u4e00-\u9fa5]{2,4})(?:说|提出|表示|认为|强调)"
    entities["names"] = re.findall(name_pattern, text)

    # 去重
    for key in entities:
        entities[key] = list(dict.fromkeys(entities[key]))

    return entities


def organize_notes(text):
    """
    核心整理逻辑：将杂乱笔记整理为结构化 Markdown。

    参数:
        text: 原始笔记内容

    返回:
        (整理后的 Markdown 文本, 校验报告字典)
    """
    # 校验输入
    try:
        validate_input(text)
    except ValueError as e:
        raise

    lines = text.split("\n")
    paragraphs = extract_paragraphs(text)

    # 提取标题
    title, auto_title = extract_title(lines)

    # 提取实体
    entities = extract_entities(text)

    # 提取行动项
    action_items = extract_action_items(text)

    # 分类段落
    background_paras = []
    core_paras = []
    reference_paras = []
    unclassified_paras = []

    for para in paragraphs:
        lower_para = para.lower()
        # 背景：含背景/上下文/引言/概述
        if any(kw in para for kw in ["背景", "上下文", "引言", "概述", "前言"]):
            background_paras.append(para)
        # 参考：含参考/链接/引用/来源
        elif any(kw in para for kw in ["参考", "链接", "引用", "来源", "备注"]):
            reference_paras.append(para)
        # 核心内容：含列表或较长段落
        else:
            items, is_list = extract_list_items(para)
            if is_list or len(para) > 20:
                core_paras.append(para)
            else:
                unclassified_paras.append(para)

    # 构建整理结果
    result_lines = []

    # 标题
    if auto_title:
        result_lines.append(f"# {title} [自动提取]")
    else:
        result_lines.append(f"# {title}")
    result_lines.append("")

    # 背景
    result_lines.append("## 背景与上下文")
    result_lines.append("")
    if background_paras:
        for para in background_paras:
            result_lines.append(para)
            result_lines.append("")
    else:
        result_lines.append("（原文未提供明确的背景信息）")
        result_lines.append("")

    # 核心内容
    result_lines.append("## 核心内容")
    result_lines.append("")
    if core_paras:
        for i, para in enumerate(core_paras, 1):
            items, is_list = extract_list_items(para)
            if is_list:
                # 列表段落直接保留
                result_lines.append(para)
                result_lines.append("")
            else:
                # 普通段落作为子主题
                sub_title = para[:15] + ("..." if len(para) > 15 else "")
                result_lines.append(f"### 子主题 {i}：{sub_title}")
                result_lines.append("")
                result_lines.append(para)
                result_lines.append("")
    else:
        result_lines.append("（原文未提供核心内容）")
        result_lines.append("")

    # 行动项
    result_lines.append("## 行动项 / 待办")
    result_lines.append("")
    if action_items:
        for item in action_items:
            result_lines.append(f"- [ ] {item}")
        result_lines.append("")
    else:
        result_lines.append("- [ ] （原文未识别出明确的行动项）")
        result_lines.append("")

    # 参考与备注
    result_lines.append("## 参考与备注")
    result_lines.append("")
    if reference_paras:
        for para in reference_paras:
            result_lines.append(f"> {para}")
            result_lines.append("")
    else:
        result_lines.append("（原文未提供参考或备注信息）")
        result_lines.append("")

    # 未分类内容
    if unclassified_paras:
        result_lines.append("### 其他备注")
        result_lines.append("")
        for para in unclassified_paras:
            result_lines.append(para)
            result_lines.append("")

    # 实体信息
    if entities["dates"] or entities["numbers"] or entities["names"]:
        result_lines.append("### 关键信息提取")
        result_lines.append("")
        if entities["dates"]:
            result_lines.append(f"- 日期：{', '.join(entities['dates'])}")
        if entities["numbers"]:
            result_lines.append(f"- 数字指标：{', '.join(entities['numbers'])}")
        if entities["names"]:
            result_lines.append(f"- 人名：{', '.join(entities['names'])}")
        result_lines.append("")

    # 校验报告
    report = {
        "missing_title": auto_title,
        "unparsed_list_count": len(unclassified_paras),
        "unparsed_list_lines": [],
        "ocr_suspected": False,
        "placeholder_count": 0,
    }

    # 检查 OCR 疑似错误（乱码特征）
    garbled_patterns = [
        r"[\ufffd]",
        r"[锟斤拷]",
        r"[\x00-\x08\x0b\x0c\x0e-\x1f]",
    ]
    for pattern in garbled_patterns:
        if re.search(pattern, text):
            report["ocr_suspected"] = True
            break

    # 统计占位符
    report["placeholder_count"] = len(re.findall(r"\[需核实:[^\]]+\]", "\n".join(result_lines)))

    # 添加占位符提示
    if report["placeholder_count"] > MAX_PLACEHOLDER_COUNT:
        result_lines.append("")
        result_lines.append("> ⚠️ 本结果含多处待核实信息，建议人工复核后再使用。")
        result_lines.append("")

    result_text = "\n".join(result_lines)
    return result_text, report


# ---------------------------------------------------------------------------
# 文件读写
# ---------------------------------------------------------------------------
def read_file_with_encoding(file_path):
    """
    读取文件，支持多编码。

    参数:
        file_path: 文件路径

    返回:
        文件内容字符串

    异常:
        ValueError: 文件读取失败
    """
    path = Path(file_path)
    if not path.exists():
        raise ValueError("E007: " + ERROR_CODES["E007"] + f"（文件不存在：{path}）")

    # 尝试多种编码
    for encoding in DEFAULT_ENCODINGS:
        try:
            with open(path, "r", encoding=encoding) as f:
                return f.read()
        except UnicodeDecodeError:
            continue
        except Exception as e:
            raise ValueError("E007: " + ERROR_CODES["E007"] + f"（读取失败：{e}）")

    # 最后尝试 replace 模式
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
            print(f"警告：文件 {path} 使用 utf-8 替换模式读取，可能存在乱码。", file=sys.stderr)
            return content
    except Exception as e:
        raise ValueError("E007: " + ERROR_CODES["E007"] + f"（所有编码尝试失败：{e}）")


def write_file_with_encoding(file_path, content):
    """
    写入文件，使用 UTF-8 编码。

    参数:
        file_path: 文件路径
        content: 内容字符串

    异常:
        ValueError: 文件写入失败
    """
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
    except Exception as e:
        raise ValueError("E008: " + ERROR_CODES["E008"] + f"（写入失败：{e}）")


# ---------------------------------------------------------------------------
# 输出格式化
# ---------------------------------------------------------------------------
def format_verification_report(report):
    """
    格式化校验报告。

    参数:
        report: 校验报告字典

    返回:
        格式化后的报告字符串
    """
    lines = ["校验报告："]
    lines.append(f"- 缺失标题：{'有（自动提取）' if report['missing_title'] else '无'}")
    lines.append(f"- 未解析列表：{report['unparsed_list_count']} 处")
    if report["unparsed_list_lines"]:
        lines.append(f"  （位置：{', '.join(str(x) for x in report['unparsed_list_lines'][:5])}）")
    lines.append(f"- 建议人工复核：{'是（OCR 疑似错误）' if report['ocr_suspected'] else '否'}")
    lines.append(f"- 待核实占位符：{report['placeholder_count']} 处")
    if report["placeholder_count"] > MAX_PLACEHOLDER_COUNT:
        lines.append("  ⚠️ 本结果含多处待核实信息，建议人工复核后再使用。")
    return "\n".join(lines)


def generate_output_filename():
    """
    生成输出文件名。

    返回:
        文件名字符串
    """
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"整理结果_{timestamp}.md"


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------
def process_text(text, verbose=False):
    """
    处理文本：整理笔记并返回结果。

    参数:
        text: 原始笔记内容
        verbose: 是否输出详细过程

    返回:
        (整理结果, 校验报告)
    """
    try:
        # 输入校验
        validate_input(text)

        if verbose:
            print(f"[处理] 输入 {len(text)} 字符，开始解析...", file=sys.stderr)

        # 核心整理
        result, report = organize_notes(text)

        if verbose:
            print(f"[处理] 整理完成，生成 {len(result)} 字符输出。", file=sys.stderr)
            print(f"[处理] 校验报告：缺失标题={report['missing_title']}, "
                  f"未解析列表={report['unparsed_list_count']}, "
                  f"OCR疑似={report['ocr_suspected']}", file=sys.stderr)

        return result, report

    except ValueError as e:
        print(f"错误 {str(e)}", file=sys.stderr)
        raise
    except Exception as e:
        print(f"E010: {ERROR_CODES['E010']}（{e}）", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        raise


def process_file(input_path, output_path=None, dry=False, force=False, verbose=False):
    """
    处理文件：读取、整理、写入。

    参数:
        input_path: 输入文件路径
        output_path: 输出文件路径（None 时自动生成）
        dry: 仅预览不写盘
        force: 强制写盘（dry 为 True 时无效）
        verbose: 详细输出

    返回:
        (输出路径, 校验报告)
    """
    # 校验输入路径
    input_file = validate_output_path(input_path)

    # 读取文件
    try:
        content = read_file_with_encoding(input_file)
        if verbose:
            print(f"[读取] 文件 {input_file} 读取成功，{len(content)} 字符。", file=sys.stderr)
    except ValueError as e:
        print(f"错误 {str(e)}", file=sys.stderr)
        raise

    # 处理内容
    result, report = process_text(content, verbose)

    # 确定输出路径
    if output_path:
        output_file = validate_output_path(output_path)
    else:
        output_file = Path.cwd() / generate_output_filename()

    # 预览模式
    if dry:
        print("=== 预览模式（不写盘）===")
        print(f"输入文件：{input_file}")
        print(f"输出文件：{output_file}")
        print(f"输出长度：{len(result)} 字符")
        print("--- 输出内容预览（前 2000 字符）---")
        print(result[:2000])
        if len(result) > 2000:
            print(f"...（省略 {len(result) - 2000} 字符）")
        print("--- 校验报告 ---")
        print(format_verification_report(report))
        return output_file, report

    # 写盘
    if not force:
        print("提示：未指定 --force，不执行写盘。使用 --dry-run 预览，或加 --force 执行写盘。", file=sys.stderr)
        return output_file, report

    try:
        write_file_with_encoding(output_file, result)
        if verbose:
            print(f"[写入] 已写入 {output_file}", file=sys.stderr)
    except ValueError as e:
        print(f"错误 {str(e)}", file=sys.stderr)
        raise

    return output_file, report


# ---------------------------------------------------------------------------
# 自检
# ---------------------------------------------------------------------------
def run_selftest():
    """
    运行内置自检，验证核心逻辑。

    返回:
        0 表示成功，非 0 表示失败
    """
    print("=== 自检开始 ===")
    failures = 0

    # 样例 1：正常中文笔记
    sample1 = """# 产品需求评审会议记录

2024年3月15日 下午2:00 会议室A

背景：讨论Q2季度产品迭代计划。

参与人：张三、李四、王五

讨论要点：
- 用户反馈首页加载速度慢，需要优化
- 新功能"智能推荐"计划在4月底上线
- 需要增加数据看板功能

决议：
1. 性能优化由张三负责，必须在本月底完成
2. 智能推荐功能由李四跟进
3. 数据看板需求由王五整理

待办事项：
- 下周三前完成性能测试报告
- 需要准备产品演示视频
- 记得更新项目文档

参考链接：https://example.com/roadmap
"""
    try:
        result1, report1 = process_text(sample1, verbose=False)
        assert result1 is not None and len(result1) > 0, "样例1：输出为空"
        assert "# " in result1, "样例1：缺少标题"
        assert "## " in result1, "样例1：缺少二级标题"
        assert "- [ ]" in result1, "样例1：缺少行动项"
        assert report1["placeholder_count"] <= MAX_PLACEHOLDER_COUNT, "样例1：占位符过多"
        print("✓ 样例1（正常中文笔记）通过")
    except AssertionError as e:
        print(f"✗ 样例1 失败：{e}")
        failures += 1
    except Exception as e:
        print(f"✗ 样例1 异常：{e}")
        failures += 1

    # 样例 2：中文标点 + 空行
    sample2 = """零散想法记录……

今天想到几个点子：
- 做一款笔记工具
- 支持多端同步
- 要简洁好用

另外，关于读书：
读完了《原子习惯》，收获很大。
需要整理读书笔记。

还有，周末计划：
去爬山、看电影。
"""
    try:
        result2, report2 = process_text(sample2, verbose=False)
        assert result2 is not None and len(result2) > 0, "样例2：输出为空"
        assert "## " in result2, "样例2：缺少二级标题"
        assert "- [ ]" in result2, "样例2：缺少行动项"
        print("✓ 样例2（中文标点+空行）通过")
    except AssertionError as e:
        print(f"✗ 样例2 失败：{e}")
        failures += 1
    except Exception as e:
        print(f"✗ 样例2 异常：{e}")
        failures += 1

    # 样例 3：空输入（应报错）
    try:
        process_text("", verbose=False)
        print("✗ 样例3（空输入）未抛出异常")
        failures += 1
    except ValueError as e:
        assert "E001" in str(e), f"样例3：错误码不正确，实际 {e}"
        print("✓ 样例3（空输入）通过")
    except Exception as e:
        print(f"✗ 样例3 异常：{e}")
        failures += 1

    # 样例 4：超长输入（应报错）
    try:
        process_text("a" * (MAX_INPUT_LENGTH + 100), verbose=False)
        print("✗ 样例4（超长输入）未抛出异常")
        failures += 1
    except ValueError as e:
        assert "E002" in str(e), f"样例4：错误码不正确，实际 {e}"
        print("✓ 样例4（超长输入）通过")
    except Exception as e:
        print(f"✗ 样例4 异常：{e}")
        failures += 1

    # 样例 5：OCR 乱码文本
    sample5 = """会议记录

讨论内容：
- 项目进度汇报
- 下一步计划

数据：¥1,234.56 万元，增长 15.7%

参会人：张\uFFFD三、李四

日期：2024年6月1日
"""
    try:
        result5, report5 = process_text(sample5, verbose=False)
        assert result5 is not None and len(result5) > 0, "样例5：输出为空"
        # OCR 疑似可能为 True（含替换字符）
        print("✓ 样例5（OCR乱码）通过")
    except AssertionError as e:
        print(f"✗ 样例5 失败：{e}")
        failures += 1
    except Exception as e:
        print(f"✗ 样例5 异常：{e}")
        failures += 1

    # 样例 6：英文 + 数字混合
    sample6 = """Meeting Notes 2024-03-20

Agenda:
- Review Q1 metrics
- Plan Q2 roadmap

Action items:
- Send report by Friday
- Schedule next meeting

Reference: https://example.com/docs
"""
    try:
        result6, report6 = process_text(sample6, verbose=False)
        assert result6 is not None and len(result6) > 0, "样例6：输出为空"
        assert "## " in result6, "样例6：缺少二级标题"
        print("✓ 样例6（英文+数字）通过")
    except AssertionError as e:
        print(f"✗ 样例6 失败：{e}")
        failures += 1
    except Exception as e:
        print(f"✗ 样例6 异常：{e}")
        failures += 1

    # 样例 7：None 输入（应报错）
    try:
        process_text(None, verbose=False)
        print("✗ 样例7（None输入）未抛出异常")
        failures += 1
    except ValueError as e:
        assert "E006" in str(e), f"样例7：错误码不正确，实际 {e}"
        print("✓ 样例7（None输入）通过")
    except Exception as e:
        print(f"✗ 样例7 异常：{e}")
        failures += 1

    print(f"\n=== 自检结束：{7 - failures}/7 通过 ===")
    return 0 if failures == 0 else 1


# ---------------------------------------------------------------------------
# CLI 入口
# ---------------------------------------------------------------------------
def main():
    """
    命令行入口。
    """
    parser = argparse.ArgumentParser(
        description="笔记整理 信息归档 结构重构 — 一站式笔记整理工具",
        epilog="示例：python main.py input.txt --output result.md --force"
    )
    parser.add_argument("input", nargs="?", help="输入笔记文件路径（.txt 或 .md）")
    parser.add_argument("--output", "-o", help="输出文件路径（默认自动生成）")
    parser.add_argument("--dry-run", action="store_true", help="仅预览不写盘")
    parser.add_argument("--force", action="store_true", help="强制写盘（配合 --dry-run 无效）")
    parser.add_argument("--verbose", "-v", action="store_true", help="输出详细处理过程")
    parser.add_argument("--selftest", action="store_true", help="运行内置自检")
    parser.add_argument("--version", action="version", version="skill-81820 1.0.1")

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        sys.exit(run_selftest())

    # 处理文件模式
    if not args.input:
        print("错误：请提供输入文件路径，或使用 --selftest 运行自检。", file=sys.stderr)
        parser.print_help()
        sys.exit(1)

    try:
        output_path, report = process_file(
            args.input,
            output_path=args.output,
            dry=args.dry_run,
            force=args.force,
            verbose=args.verbose,
        )

        if not args.dry_run and args.force:
            print(f"处理完成，输出文件：{output_path}")
            print(format_verification_report(report))
        elif args.dry_run:
            print("预览完成（未写盘）。如需写盘，请加 --force 参数。")
        else:
            print("处理完成（未写盘）。如需写盘，请加 --force 参数。")
            print(format_verification_report(report))

    except ValueError as e:
        print(f"错误：{e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"E010: {ERROR_CODES['E010']}（{e}）", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
