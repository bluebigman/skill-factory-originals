#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
skill-81820 笔记整理 信息归档 结构重构
一站式笔记整理脚本：识别、整理、生成、校验，输出结构化 Markdown。
仅依赖标准库，支持 --selftest 离线自检。
"""

import argparse
import re
import sys
import os
from datetime import datetime
from pathlib import Path

# 错误码定义
ERROR_CODES = {
    "E001": "输入内容为空",
    "E002": "输入超过 50000 字符限制",
    "E003": "无法识别有效结构",
    "E004": "校验发现缺失项",
    "E005": "OCR 疑似错误",
    "E006": "文件读取失败",
    "E007": "文件写入失败",
    "E008": "参数校验失败",
    "E009": "内部逻辑错误",
    "E010": "未知异常",
}

MAX_INPUT_LENGTH = 50000
MAX_PLACEHOLDER_COUNT = 5

# 典型输入/输出契约（用于 selftest 断言）
EXAMPLES = [
    {
        "name": "中文标点与列表混合",
        "input": "会议记录：讨论项目进度。\n- 完成需求文档\n- 评审设计方案\n需要周五前提交。",
        "must_contain": ["#", "##", "- [ ]", "会议记录"],
    },
    {
        "name": "空输入",
        "input": "",
        "must_contain": ["E001"],
    },
    {
        "name": "超长输入",
        "input": "a" * (MAX_INPUT_LENGTH + 1),
        "must_contain": ["E002"],
    },
    {
        "name": "纯文本无列表",
        "input": "这是一段普通的文本内容，没有标题和列表。",
        "must_contain": ["#", "##"],
    },
]


def validate_input(content):
    """输入校验：检查类型、长度、空值。返回 (是否通过, 错误码或None)。"""
    if content is None:
        return False, "E001"
    if not isinstance(content, str):
        return False, "E008"
    if not content.strip():
        return False, "E001"
    if len(content) > MAX_INPUT_LENGTH:
        return False, "E002"
    return True, None


def read_file(file_path):
    """读取文件，支持多编码 fallback。返回 (内容, 错误码或None)。"""
    try:
        path = Path(file_path)
        # 白名单校验：只允许常规文件路径，禁止绝对路径穿越
        if path.is_absolute() or ".." in str(path):
            return None, "E008"
        if not path.exists():
            return None, "E006"
        # 多编码尝试：utf-8 → gbk → gb18030 → errors="replace"
        for encoding in ["utf-8", "gbk", "gb18030"]:
            try:
                with open(path, "r", encoding=encoding) as f:
                    return f.read(), None
            except (UnicodeDecodeError, UnicodeError):
                continue
        # 最后兜底：用 replace 模式读取
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.read(), None
    except Exception as e:
        print(f"警告: 文件读取失败 - {e}", file=sys.stderr)
        return None, "E006"


def extract_title(content):
    """提取笔记主题。优先使用第一个标题行，否则用前 20 字。"""
    lines = content.strip().split("\n")
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("#"):
            return stripped.lstrip("#").strip()
    # 无标题时取前 20 字
    plain_text = re.sub(r"[#*_`>]", "", content).strip()
    return plain_text[:20] + " [自动提取]" if plain_text else "[需核实:笔记主题]"


def extract_lists(content):
    """提取列表项。返回 (无序列表, 有序列表, 待办项)。"""
    unordered = []
    ordered = []
    todos = []
    lines = content.split("\n")
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("- [ ]"):
            todos.append((i + 1, stripped[5:].strip()))
        elif stripped.startswith("-") or stripped.startswith("*"):
            unordered.append((i + 1, stripped.lstrip("-* ").strip()))
        elif re.match(r"^\d+\.", stripped):
            ordered.append((i + 1, re.sub(r"^\d+\.\s*", "", stripped)))
    return unordered, ordered, todos


def extract_key_sentences(content):
    """提取关键句子（含需/要/必须/待办等词）。"""
    sentences = re.split(r"[。！？!?]", content)
    keywords = ["需", "要", "必须", "待办", "截止"]
    result = []
    for s in sentences:
        s = s.strip()
        if not s:
            continue
        if any(k in s for k in keywords):
            result.append(s)
    return result


def detect_ocr_issues(content):
    """检测 OCR 疑似错误（如乱码、异常字符）。返回问题行号列表。"""
    issues = []
    lines = content.split("\n")
    for i, line in enumerate(lines, 1):
        # 检测常见乱码模式
        if re.search(r"[\ufffd]", line):
            issues.append(i)
        elif re.search(r"[^\u4e00-\u9fff\u3000-\u303f\uff00-\uffef\w\s\d\.,;:!?()\[\]{}\"'-]", line):
            # 检测异常字符（非中英文、数字、常见标点）
            issues.append(i)
    return issues


def build_markdown(content, title, unordered, ordered, todos, key_sentences, ocr_issues):
    """构建结构化 Markdown。返回 (markdown文本, 校验报告)。"""
    md_lines = []
    md_lines.append(f"# {title}")
    md_lines.append("")
    md_lines.append("## 背景与上下文")
    md_lines.append("")
    # 提取背景段落（非列表、非标题的行）
    lines = content.split("\n")
    background = []
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and not stripped.startswith("-") and not stripped.startswith("*") and not re.match(r"^\d+\.", stripped):
            background.append(stripped)
    if background:
        md_lines.extend(background)
    else:
        md_lines.append("[需核实:背景信息]")
    md_lines.append("")
    md_lines.append("## 核心内容")
    md_lines.append("")
    if unordered:
        md_lines.append("### 要点列表")
        md_lines.append("")
        for _, item in unordered:
            md_lines.append(f"- {item}")
        md_lines.append("")
    if ordered:
        md_lines.append("### 有序内容")
        md_lines.append("")
        for i, (_, item) in enumerate(ordered, 1):
            md_lines.append(f"{i}. {item}")
        md_lines.append("")
    md_lines.append("## 行动项 / 待办")
    md_lines.append("")
    if todos:
        for _, item in todos:
            md_lines.append(f"- [ ] {item}")
    elif key_sentences:
        for s in key_sentences:
            md_lines.append(f"- [ ] {s}")
    else:
        md_lines.append("- [ ] [需核实:待办事项]")
    md_lines.append("")
    md_lines.append("## 参考与备注")
    md_lines.append("")
    if ocr_issues:
        md_lines.append(f"> 检测到 OCR 疑似错误，涉及行号: {', '.join(map(str, ocr_issues))}")
    md_lines.append("")
    md_text = "\n".join(md_lines)
    # 生成校验报告
    report_lines = ["校验报告："]
    report_lines.append(f"- 缺失标题：{'无' if title else '有'}")
    report_lines.append(f"- 未解析列表：{len(unordered) + len(ordered)} 处")
    if ocr_issues:
        report_lines.append(f"- 建议人工复核：OCR 识别段落（第 {', '.join(map(str, ocr_issues))} 行）")
    placeholder_count = md_text.count("[需核实")
    if placeholder_count > MAX_PLACEHOLDER_COUNT:
        report_lines.append("本结果含多处待核实信息，建议人工复核后再使用。")
    report = "\n".join(report_lines)
    return md_text, report


def organize_notes(content, verbose=False):
    """核心逻辑：整理笔记。返回 (markdown文本, 校验报告, 错误码或None)。"""
    try:
        # 输入校验
        valid, err_code = validate_input(content)
        if not valid:
            return None, None, err_code
        # 识别结构
        title = extract_title(content)
        unordered, ordered, todos = extract_lists(content)
        key_sentences = extract_key_sentences(content)
        ocr_issues = detect_ocr_issues(content)
        # 检查是否识别到有效结构
        if not title and not unordered and not ordered and not todos:
            return None, None, "E003"
        # 构建输出
        md_text, report = build_markdown(content, title, unordered, ordered, todos, key_sentences, ocr_issues)
        if verbose:
            print(f"识别到标题: {title}", file=sys.stderr)
            print(f"识别到无序列表: {len(unordered)} 项", file=sys.stderr)
            print(f"识别到有序列表: {len(ordered)} 项", file=sys.stderr)
            print(f"识别到待办: {len(todos)} 项", file=sys.stderr)
            print(f"识别到关键句子: {len(key_sentences)} 条", file=sys.stderr)
            if ocr_issues:
                print(f"OCR 疑似错误行: {ocr_issues}", file=sys.stderr)
        return md_text, report, None
    except Exception as e:
        print(f"警告: 整理过程发生异常 - {e}", file=sys.stderr)
        return None, None, "E009"


def write_output(md_text, report, output_path, dry=True):
    """写盘操作，支持 dry-run。返回 (是否成功, 错误码或None)。"""
    try:
        if dry:
            print("=== 预览模式（--dry-run），不写盘 ===")
            print("--- 整理结果 ---")
            print(md_text)
            print("--- 校验报告 ---")
            print(report)
            return True, None
        # 实际写盘
        path = Path(output_path)
        # 白名单校验
        if path.is_absolute() or ".." in str(path):
            return False, "E008"
        with open(path, "w", encoding="utf-8") as f:
            f.write(md_text)
        # 同时写校验报告
        report_path = path.with_suffix(".report.txt")
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report)
        return True, None
    except Exception as e:
        print(f"警告: 文件写入失败 - {e}", file=sys.stderr)
        return False, "E007"


def run_selftest():
    """离线自检：使用内置样例数据验证核心逻辑。返回 True/False。"""
    print("=== 自检开始 ===")
    all_passed = True
    for example in EXAMPLES:
        name = example["name"]
        content = example["input"]
        must_contain = example["must_contain"]
        print(f"\n--- 测试用例: {name} ---")
        md_text, report, err_code = organize_notes(content)
        if err_code:
            # 检查错误码是否在预期中
            if any(code in must_contain for code in [err_code]):
                print(f"通过: 返回错误码 {err_code}")
            else:
                print(f"失败: 预期 {must_contain}，实际错误码 {err_code}")
                all_passed = False
        else:
            # 检查输出内容
            if md_text is None:
                print("失败: 输出为空")
                all_passed = False
                continue
            # 宽松断言：检查关键结构存在
            checks = []
            for keyword in must_contain:
                if keyword.startswith("E"):
                    continue
                checks.append(keyword in md_text)
            if all(checks):
                print(f"通过: 输出包含 {len(must_contain)} 个关键结构")
            else:
                print(f"失败: 输出缺少部分关键结构")
                all_passed = False
            # 检查校验报告
            if report is None:
                print("失败: 校验报告为空")
                all_passed = False
    # 额外测试：空输入和 None 输入
    print("\n--- 边界测试 ---")
    for bad_input in [None, "", "   "]:
        md_text, report, err_code = organize_notes(bad_input)
        if err_code == "E001":
            print(f"通过: 空输入返回 E001")
        else:
            print(f"失败: 空输入预期 E001，实际 {err_code}")
            all_passed = False
    # 测试超长输入
    long_input = "x" * (MAX_INPUT_LENGTH + 1)
    md_text, report, err_code = organize_notes(long_input)
    if err_code == "E002":
        print("通过: 超长输入返回 E002")
    else:
        print(f"失败: 超长输入预期 E002，实际 {err_code}")
        all_passed = False
    print(f"\n=== 自检结束: {'全部通过' if all_passed else '存在失败'} ===")
    return all_passed


def main():
    """CLI 入口。"""
    parser = argparse.ArgumentParser(
        description="笔记整理 信息归档 结构重构 - 一站式笔记整理工具",
        epilog="示例: python main.py -i input.txt -o output.md --dry-run"
    )
    parser.add_argument("-i", "--input", help="输入文件路径（纯文本或 Markdown）")
    parser.add_argument("-o", "--output", help="输出文件路径（默认: 整理结果_时间戳.md）")
    parser.add_argument("--dry-run", action="store_true", help="预览模式，不写盘")
    parser.add_argument("--force", action="store_true", help="强制写盘（需与 --dry-run 配合）")
    parser.add_argument("--verbose", action="store_true", help="输出详细处理过程")
    parser.add_argument("--selftest", action="store_true", help="运行离线自检")
    parser.add_argument("--version", action="store_true", help="显示版本信息")
    args = parser.parse_args()

    if args.version:
        print("skill-81820 笔记整理工具 v1.0.1")
        return 0

    if args.selftest:
        return 0 if run_selftest() else 1

    # 参数校验
    if not args.input:
        print("错误: 请提供输入文件路径（使用 -i 参数）", file=sys.stderr)
        print("提示: 运行 --selftest 进行自检，或 --help 查看帮助", file=sys.stderr)
        return 1

    # 读取输入
    content, err_code = read_file(args.input)
    if err_code:
        print(f"错误 {err_code}: {ERROR_CODES.get(err_code, '未知错误')}", file=sys.stderr)
        return 1

    # 整理笔记
    md_text, report, err_code = organize_notes(content, verbose=args.verbose)
    if err_code:
        print(f"错误 {err_code}: {ERROR_CODES.get(err_code, '未知错误')}", file=sys.stderr)
        return 1

    # 确定输出路径
    output_path = args.output
    if not output_path:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = f"整理结果_{timestamp}.md"

    # 写盘控制：dry-run 默认开启，--force 才真正写盘
    dry = not args.force
    success, write_err = write_output(md_text, report, output_path, dry=dry)
    if not success:
        print(f"错误 {write_err}: {ERROR_CODES.get(write_err, '未知错误')}", file=sys.stderr)
        return 1

    if not dry:
        print(f"已生成整理结果: {output_path}")
        print(f"已生成校验报告: {Path(output_path).with_suffix('.report.txt')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
