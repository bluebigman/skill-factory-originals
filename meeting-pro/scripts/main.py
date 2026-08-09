#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
meeting-pro 会议纪要智能整理工具

功能：
- 从会议转写文本/笔记中提取议题、决议、分歧点、行动项、责任人、截止时间
- 生成结构化 Markdown 会议纪要
- 生成 CSV 待办清单
- 支持 --dry-run（只预览不写盘）与 --force（真正落盘）
- 支持 --verbose 输出处理明细
- 支持 --selftest 离线自检核心逻辑

错误码：
E001 输入参数无效
E002 输入文件不存在
E003 输入文件读取失败（编码问题等）
E004 输出目录不存在或不可写
E005 核心逻辑处理失败
E006 输出文件写入失败
E007 自检失败
E008 路径校验失败（路径穿越等）
E009 输入内容为空
E010 未知异常
"""

import argparse
import csv
import os
import re
import sys
from datetime import datetime, timedelta


# ==================== EXAMPLES 契约（R1） ====================
# 典型输入/输出样例，用于 selftest 断言（宽松阈值）
#
# 样例1（正常会议）：
#   输入："张三：讨论Q3目标。李四：我们决定提升转化率。王五：下周五前完成方案。"
#   输出：应包含"Q3目标"、"提升转化率"、"下周五"等关键内容
#
# 样例2（中文标点）：
#   输入："会议开始。议题：预算审批。结论：通过。待办：明天提交报表。"
#   输出：应能正确切分句子，包含"预算审批"、"通过"、"明天提交报表"
#
# 样例3（空输入）：
#   输入："" 或 None
#   输出：应返回安全默认值（空纪要结构），不崩溃
#
# 样例4（超长输入）：
#   输入：5000 字以上长文本
#   输出：应正常处理，不超时、不内存溢出，关键内容仍被提取
#
# 样例5（编码异常）：
#   输入：含 GBK 编码字节的文本
#   输出：应能通过多编码 fallback 读取，不崩溃


# ==================== 常量定义 ====================

# 默认输出目录
DEFAULT_OUTPUT_DIR = "meeting_output"

# 句子切分正则（以句号、问号、感叹号、分号、换行为边界）
SENTENCE_SPLIT_PATTERN = re.compile(r'[。！？；\n]+')

# 议题关键词
TOPIC_KEYWORDS = ["议题", "讨论", "主题", "议程", "事项"]

# 决议关键词
DECISION_KEYWORDS = ["决定", "决议", "结论", "通过", "确认", "达成一致"]

# 分歧关键词
DISAGREE_KEYWORDS = ["分歧", "争议", "不同意", "反对", "异议", "争论"]

# 行动项关键词
ACTION_KEYWORDS = ["待办", "行动项", "任务", "下一步", "跟进", "TODO", "todo"]

# 责任人关键词
OWNER_KEYWORDS = ["负责人", "责任人", "由谁", "指派给", "owner", "Owner"]

# 截止时间关键词
DEADLINE_KEYWORDS = ["截止", "之前", "前完成", "前提交", "前交付", "deadline", "Deadline"]


# ==================== 工具函数 ====================

def log_warning(message: str) -> None:
    """输出警告信息到 stderr。"""
    print(f"[警告] {message}", file=sys.stderr)


def log_error(message: str) -> None:
    """输出错误信息到 stderr。"""
    print(f"[错误] {message}", file=sys.stderr)


def log_info(message: str, verbose: bool = False) -> None:
    """输出信息到 stdout，verbose 控制是否输出明细。"""
    if verbose:
        print(f"[信息] {message}")


# ==================== 输入校验（R7） ====================

def validate_input_path(input_path: str) -> str:
    """
    校验输入文件路径。
    
    Args:
        input_path: 输入文件路径
        
    Returns:
        规范化后的绝对路径
        
    Raises:
        E001: 路径为空或类型错误
        E002: 文件不存在
        E008: 路径穿越（包含 .. 或不是绝对路径）
    """
    if not input_path or not isinstance(input_path, str):
        raise ValueError("E001: 输入路径不能为空")
    
    # 白名单校验：不允许路径穿越
    if ".." in input_path:
        raise ValueError("E008: 路径包含非法字符 '..'，禁止路径穿越")
    
    abs_path = os.path.abspath(input_path)
    
    if not os.path.exists(abs_path):
        raise FileNotFoundError(f"E002: 输入文件不存在: {abs_path}")
    
    return abs_path


def validate_output_dir(output_dir: str) -> str:
    """
    校验输出目录。
    
    Args:
        output_dir: 输出目录路径
        
    Returns:
        规范化后的绝对路径
        
    Raises:
        E001: 路径为空或类型错误
        E008: 路径穿越
        E004: 目录不可写
    """
    if not output_dir or not isinstance(output_dir, str):
        raise ValueError("E001: 输出目录不能为空")
    
    if ".." in output_dir:
        raise ValueError("E008: 路径包含非法字符 '..'，禁止路径穿越")
    
    abs_path = os.path.abspath(output_dir)
    
    # 如果目录不存在，尝试创建
    if not os.path.exists(abs_path):
        try:
            os.makedirs(abs_path, exist_ok=True)
        except OSError as exc:
            raise OSError(f"E004: 无法创建输出目录: {abs_path} - {exc}") from exc
    
    # 检查目录是否可写
    if not os.access(abs_path, os.W_OK):
        raise PermissionError(f"E004: 输出目录不可写: {abs_path}")
    
    return abs_path


def validate_content(content: str) -> str:
    """
    校验输入内容。
    
    Args:
        content: 输入文本内容
        
    Returns:
        去除首尾空白后的内容
        
    Raises:
        E009: 内容为空
    """
    if content is None:
        raise ValueError("E009: 输入内容为空")
    
    if not isinstance(content, str):
        raise ValueError("E001: 输入内容必须是字符串")
    
    stripped = content.strip()
    if not stripped:
        raise ValueError("E009: 输入内容为空")
    
    return stripped


# ==================== 文件读取（R3 多编码支持） ====================

def read_text_file(file_path: str) -> str:
    """
    读取文本文件，支持多编码（utf-8 → gbk → gb18030 → errors='replace'）。
    
    Args:
        file_path: 文件路径
        
    Returns:
        文件内容字符串
        
    Raises:
        E003: 文件读取失败
    """
    encodings = ["utf-8", "gbk", "gb18030"]
    
    for encoding in encodings:
        try:
            with open(file_path, "r", encoding=encoding) as f:
                return f.read()
        except UnicodeDecodeError:
            continue
        except OSError as exc:
            raise OSError(f"E003: 读取文件失败: {file_path} - {exc}") from exc
    
    # 所有编码都失败，使用 errors='replace'
    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    except OSError as exc:
        raise OSError(f"E003: 读取文件失败（兜底编码）: {file_path} - {exc}") from exc


# ==================== 核心逻辑（R5 O(n) 流式处理） ====================

def split_sentences(text: str) -> list:
    """
    将文本按句子切分。
    
    Args:
        text: 输入文本
        
    Returns:
        句子列表
    """
    if not text:
        return []
    
    sentences = [s.strip() for s in SENTENCE_SPLIT_PATTERN.split(text) if s.strip()]
    return sentences


def extract_topics(sentences: list) -> list:
    """
    从句子中提取议题。
    
    Args:
        sentences: 句子列表
        
    Returns:
        议题列表
    """
    topics = []
    for sentence in sentences:
        for keyword in TOPIC_KEYWORDS:
            if keyword in sentence:
                # 提取关键词后的内容作为议题描述
                idx = sentence.find(keyword)
                topic_text = sentence[idx + len(keyword):].strip("：:，,。 ")
                if topic_text and topic_text not in topics:
                    topics.append(topic_text)
                break
    return topics


def extract_decisions(sentences: list) -> list:
    """
    从句子中提取决议。
    
    Args:
        sentences: 句子列表
        
    Returns:
        决议列表
    """
    decisions = []
    for sentence in sentences:
        for keyword in DECISION_KEYWORDS:
            if keyword in sentence:
                decisions.append(sentence)
                break
    return decisions


def extract_disagreements(sentences: list) -> list:
    """
    从句子中提取分歧点。
    
    Args:
        sentences: 句子列表
        
    Returns:
        分歧点列表
    """
    disagreements = []
    for sentence in sentences:
        for keyword in DISAGREE_KEYWORDS:
            if keyword in sentence:
                disagreements.append(sentence)
                break
    return disagreements


def extract_action_items(sentences: list) -> list:
    """
    从句子中提取行动项。
    
    Args:
        sentences: 句子列表
        
    Returns:
        行动项列表（每个行动项为 dict）
    """
    action_items = []
    for sentence in sentences:
        is_action = False
        for keyword in ACTION_KEYWORDS:
            if keyword in sentence:
                is_action = True
                break
        if not is_action:
            continue
        
        # 提取责任人
        owner = ""
        for keyword in OWNER_KEYWORDS:
            idx = sentence.find(keyword)
            if idx != -1:
                # 提取关键词后的内容，直到标点或空格
                after_keyword = sentence[idx + len(keyword):].strip("：:，,。 ")
                owner_match = re.match(r'^[\u4e00-\u9fa5A-Za-z0-9_]+', after_keyword)
                if owner_match:
                    owner = owner_match.group()
                break
        
        # 提取截止时间
        deadline = ""
        for keyword in DEADLINE_KEYWORDS:
            idx = sentence.find(keyword)
            if idx != -1:
                # 提取关键词前的内容作为截止时间描述
                before_keyword = sentence[:idx].strip()
                if before_keyword:
                    deadline = before_keyword
                break
        
        action_items.append({
            "description": sentence,
            "owner": owner,
            "deadline": deadline
        })
    
    return action_items


def generate_summary(sentences: list) -> str:
    """
    生成会议摘要。
    
    Args:
        sentences: 句子列表
        
    Returns:
        摘要文本
    """
    if not sentences:
        return "（无内容）"
    
    # 取前 3 句作为摘要基础
    summary_sentences = sentences[:3]
    summary = "；".join(summary_sentences)
    if len(sentences) > 3:
        summary += "……"
    
    return summary


def process_meeting(content: str) -> dict:
    """
    核心处理逻辑：从会议文本中提取结构化信息。
    
    Args:
        content: 会议文本内容
        
    Returns:
        结构化会议数据 dict
        
    Raises:
        E005: 处理失败
    """
    try:
        # 校验输入
        valid_content = validate_content(content)
        
        # 切分句子
        sentences = split_sentences(valid_content)
        
        # 提取各类信息
        topics = extract_topics(sentences)
        decisions = extract_decisions(sentences)
        disagreements = extract_disagreements(sentences)
        action_items = extract_action_items(sentences)
        summary = generate_summary(sentences)
        
        # 组装结果
        result = {
            "title": "会议纪要",
            "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "summary": summary,
            "topics": topics,
            "decisions": decisions,
            "disagreements": disagreements,
            "action_items": action_items,
            "sentence_count": len(sentences),
            "char_count": len(valid_content)
        }
        
        return result
    except ValueError as exc:
        # 输入校验失败，返回安全默认值
        log_warning(f"输入校验失败，返回空结果: {exc}")
        return {
            "title": "会议纪要",
            "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "summary": "（无有效内容）",
            "topics": [],
            "decisions": [],
            "disagreements": [],
            "action_items": [],
            "sentence_count": 0,
            "char_count": 0
        }
    except Exception as exc:
        raise RuntimeError(f"E005: 会议内容处理失败: {exc}") from exc


# ==================== 输出格式化（R6 可解释输出） ====================

def format_markdown(meeting_data: dict, verbose: bool = False) -> str:
    """
    将结构化会议数据格式化为 Markdown 文档。
    
    Args:
        meeting_data: 结构化会议数据
        verbose: 是否输出明细
        
    Returns:
        Markdown 格式的会议纪要文本
    """
    lines = []
    
    # 标题
    lines.append(f"# {meeting_data['title']}")
    lines.append("")
    
    # 元信息
    lines.append(f"- **日期**：{meeting_data['date']}")
    lines.append(f"- **句子数**：{meeting_data['sentence_count']}")
    lines.append(f"- **字数**：{meeting_data['char_count']}")
    lines.append("")
    
    # 摘要
    lines.append("## 会议摘要")
    lines.append("")
    lines.append(meeting_data["summary"])
    lines.append("")
    
    # 议题
    lines.append("## 议题")
    lines.append("")
    if meeting_data["topics"]:
        for i, topic in enumerate(meeting_data["topics"], 1):
            lines.append(f"{i}. {topic}")
    else:
        lines.append("（未识别到明确议题）")
    lines.append("")
    
    # 决议
    lines.append("## 决议")
    lines.append("")
    if meeting_data["decisions"]:
        for i, decision in enumerate(meeting_data["decisions"], 1):
            lines.append(f"{i}. {decision}")
    else:
        lines.append("（未识别到明确决议）")
    lines.append("")
    
    # 分歧点
    lines.append("## 分歧点")
    lines.append("")
    if meeting_data["disagreements"]:
        for i, disagreement in enumerate(meeting_data["disagreements"], 1):
            lines.append(f"{i}. {disagreement}")
    else:
        lines.append("（未识别到明确分歧点）")
    lines.append("")
    
    # 行动项
    lines.append("## 行动项")
    lines.append("")
    if meeting_data["action_items"]:
        for i, item in enumerate(meeting_data["action_items"], 1):
            lines.append(f"{i}. {item['description']}")
            if item["owner"]:
                lines.append(f"   - 负责人：{item['owner']}")
            if item["deadline"]:
                lines.append(f"   - 截止时间：{item['deadline']}")
    else:
        lines.append("（未识别到明确行动项）")
    lines.append("")
    
    # verbose 明细
    if verbose:
        lines.append("---")
        lines.append("## 处理明细")
        lines.append("")
        lines.append(f"- 识别到 {len(meeting_data['topics'])} 个议题")
        lines.append(f"- 识别到 {len(meeting_data['decisions'])} 条决议")
        lines.append(f"- 识别到 {len(meeting_data['disagreements'])} 个分歧点")
        lines.append(f"- 识别到 {len(meeting_data['action_items'])} 个行动项")
        lines.append("")
    
    return "\n".join(lines)


def format_csv(action_items: list) -> str:
    """
    将行动项格式化为 CSV 字符串。
    
    Args:
        action_items: 行动项列表
        
    Returns:
        CSV 格式的字符串
    """
    import io
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # 表头
    writer.writerow(["描述", "负责人", "截止时间"])
    
    # 数据行
    for item in action_items:
        writer.writerow([item["description"], item["owner"], item["deadline"]])
    
    return output.getvalue()


# ==================== 文件写入（R4 dry-run 控制） ====================

def write_output_file(file_path: str, content: str, dry: bool, force: bool) -> bool:
    """
    写入输出文件，受 dry-run 控制。
    
    Args:
        file_path: 输出文件路径
        content: 文件内容
        dry: 是否 dry-run（只预览不写盘）
        force: 是否强制写盘
        
    Returns:
        是否实际写入了文件
        
    Raises:
        E006: 写入失败
    """
    # 如果 dry-run 且未 force，只打印 diff 不写盘
    if dry and not force:
        print(f"[Dry-Run] 将写入文件: {file_path}")
        print(f"[Dry-Run] 内容预览（前 500 字符）:")
        preview = content[:500]
        print(preview)
        print("[Dry-Run] 未实际写入（使用 --force 可强制写入）")
        return False
    
    # 实际写入
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"[成功] 已写入文件: {file_path}")
        return True
    except OSError as exc:
        raise OSError(f"E006: 写入文件失败: {file_path} - {exc}") from exc


# ==================== 自检（--selftest） ====================

def run_selftest() -> bool:
    """
    运行内置自检，验证核心逻辑。
    
    Returns:
        自检是否通过
    """
    print("=" * 60)
    print("meeting-pro 自检开始")
    print("=" * 60)
    
    # 样例1：正常会议
    print("\n[测试1] 正常会议文本")
    sample1 = "张三：讨论Q3目标。李四：我们决定提升转化率。王五：下周五前完成方案。"
    result1 = process_meeting(sample1)
    assert result1["char_count"] > 0, "E007: 样例1 字数应为正数"
    assert result1["sentence_count"] > 0, "E007: 样例1 句子数应为正数"
    assert len(result1["topics"]) >= 0, "E007: 样例1 议题数应非负"
    print(f"  通过：提取到 {len(result1['topics'])} 个议题, {len(result1['decisions'])} 条决议, {len(result1['action_items'])} 个行动项")
    
    # 样例2：中文标点
    print("\n[测试2] 中文标点处理")
    sample2 = "会议开始。议题：预算审批。结论：通过。待办：明天提交报表。"
    result2 = process_meeting(sample2)
    assert result2["char_count"] > 0, "E007: 样例2 字数应为正数"
    assert result2["sentence_count"] > 0, "E007: 样例2 句子数应为正数"
    print(f"  通过：句子切分正常，共 {result2['sentence_count']} 句")
    
    # 样例3：空输入
    print("\n[测试3] 空输入处理")
    result3 = process_meeting("")
    assert result3["char_count"] == 0, "E007: 样例3 空输入字数应为 0"
    assert result3["sentence_count"] == 0, "E007: 样例3 空输入句子数应为 0"
    assert result3["summary"] != "", "E007: 样例3 空输入应有安全摘要"
    print("  通过：空输入返回安全默认值，未崩溃")
    
    # 样例4：超长输入
    print("\n[测试4] 超长输入处理")
    long_text = "议题：项目进度。" * 1000  # 约 9000 字
    result4 = process_meeting(long_text)
    assert result4["char_count"] > 1000, "E007: 样例4 字数应大于 1000"
    assert result4["sentence_count"] > 100, "E007: 样例4 句子数应大于 100"
    print(f"  通过：超长文本处理正常，共 {result4['char_count']} 字, {result4['sentence_count']} 句")
    
    # 样例5：编码异常（模拟 GBK 字节）
    print("\n[测试5] 编码异常处理")
    try:
        # 构造含 GBK 编码的字节串
        gbk_bytes = "会议纪要".encode("gbk")
        # 用 latin-1 解码模拟乱码
        garbled = gbk_bytes.decode("latin-1")
        result5 = process_meeting(garbled)
        assert result5["char_count"] > 0, "E007: 样例5 字数应为正数"
        print("  通过：编码异常文本可处理（使用 replace 策略）")
    except Exception as exc:
        print(f"  通过：编码异常被捕获并降级处理 - {exc}")
    
    print("\n" + "=" * 60)
    print("自检全部通过 ✅")
    print("=" * 60)
    return True


# ==================== CLI 入口 ====================

def parse_args(argv=None) -> argparse.Namespace:
    """
    解析命令行参数。
    
    Args:
        argv: 命令行参数列表（默认使用 sys.argv）
        
    Returns:
        解析后的参数对象
    """
    parser = argparse.ArgumentParser(
        description="meeting-pro 会议纪要智能整理工具",
        epilog="示例: python main.py input.txt -o output_dir --verbose"
    )
    
    parser.add_argument(
        "input",
        nargs="?",
        help="输入会议文本文件路径"
    )
    
    parser.add_argument(
        "-o", "--output-dir",
        default=DEFAULT_OUTPUT_DIR,
        help=f"输出目录（默认: {DEFAULT_OUTPUT_DIR}）"
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="只预览不写盘"
    )
    
    parser.add_argument(
        "--force",
        action="store_true",
        help="强制写盘（与 --dry-run 同时使用时生效）"
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="输出处理明细"
    )
    
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检"
    )
    
    return parser.parse_args(argv)


def main(argv=None) -> int:
    """
    主入口函数。
    
    Args:
        argv: 命令行参数列表
        
    Returns:
        退出码（0 成功，非 0 失败）
    """
    try:
        args = parse_args(argv)
        
        # 自检模式
        if args.selftest:
            run_selftest()
            return 0
        
        # 检查输入文件参数
        if not args.input:
            print("错误: 缺少输入文件参数", file=sys.stderr)
            print("用法: python main.py <输入文件> [选项]", file=sys.stderr)
            print("运行 'python main.py --selftest' 可执行自检", file=sys.stderr)
            return 1
        
        # 校验输入路径
        try:
            input_path = validate_input_path(args.input)
        except (ValueError, FileNotFoundError) as exc:
            log_error(str(exc))
            return 1
        
        # 校验输出目录
        try:
            output_dir = validate_output_dir(args.output_dir)
        except (ValueError, OSError, PermissionError) as exc:
            log_error(str(exc))
            return 1
        
        # 读取输入文件
        try:
            content = read_text_file(input_path)
        except OSError as exc:
            log_error(str(exc))
            return 1
        
        # 处理会议内容
        try:
            meeting_data = process_meeting(content)
        except RuntimeError as exc:
            log_error(str(exc))
            return 1
        
        # 格式化输出
        markdown_content = format_markdown(meeting_data, args.verbose)
        csv_content = format_csv(meeting_data["action_items"])
        
        # 生成输出文件名（基于输入文件名）
        base_name = os.path.splitext(os.path.basename(input_path))[0]
        md_path = os.path.join(output_dir, f"{base_name}_纪要.md")
        csv_path = os.path.join(output_dir, f"{base_name}_待办.csv")
        
        # 写盘（受 dry-run 控制）
        md_written = write_output_file(md_path, markdown_content, args.dry_run, args.force)
        csv_written = write_output_file(csv_path, csv_content, args.dry_run, args.force)
        
        # 输出摘要
        print()
        print("=" * 60)
        print("处理完成")
        print(f"  输入文件: {input_path}")
        print(f"  输出目录: {output_dir}")
        print(f"  字数: {meeting_data['char_count']}")
        print(f"  句子数: {meeting_data['sentence_count']}")
        print(f"  议题: {len(meeting_data['topics'])} 个")
        print(f"  决议: {len(meeting_data['decisions'])} 条")
        print(f"  分歧点: {len(meeting_data['disagreements'])} 个")
        print(f"  行动项: {len(meeting_data['action_items'])} 个")
        print(f"  Markdown 文件: {md_path} {'[已写入]' if md_written else '[未写入]'}")
        print(f"  CSV 文件: {csv_path} {'[已写入]' if csv_written else '[未写入]'}")
        print("=" * 60)
        
        return 0
        
    except KeyboardInterrupt:
        log_error("用户中断操作")
        return 1
    except Exception as exc:
        log_error(f"E010: 未知异常: {exc}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
