#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
meeting-pro 会议纪要智能整理与行动项提取工具

本脚本为 clean-room 独立实现，仅依据功能规格设计。
功能：接收会议文本素材，输出结构化会议纪要（Markdown）、行动项（CSV）与质量校验报告。
"""

import argparse
import csv
import io
import json
import os
import re
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

# ---------------------------------------------------------------------------
# 错误码定义
# ---------------------------------------------------------------------------
ERROR_CODES = {
    "E001": "素材格式不支持，请转换为 txt/srt/vtt 或 mp3/wav/m4a",
    "E002": "音频质量过低，可能影响识别效果",
    "E003": "素材内容不足以生成完整纪要（少于100字）",
    "E004": "无法区分不同发言人，将统一标注",
    "E005": "检测到时间线存在矛盾，已标记",
    "E006": "部分行动项缺少负责人或截止时间",
    "E007": "输入文件不存在或无法读取",
    "E008": "输出目录不存在或无法写入",
    "E009": "内部逻辑错误（未知异常）",
    "E010": "参数校验失败",
}

# ---------------------------------------------------------------------------
# 内置硬编码样例数据（用于 --selftest）
# ---------------------------------------------------------------------------
SAMPLE_TEXT = """今天下午3点我们开了项目周会，参会人有张伟、李娜、王强。
张伟说：上周的登录模块已经完成开发，本周进入测试阶段。
李娜提出：用户反馈首页加载速度有点慢，需要优化性能。
王强建议：下周三之前完成性能测试报告。
会议决定：采用 Vue3 重构前端框架，由张伟负责技术选型。
李娜负责跟进性能优化，需要在本周五输出优化方案。
王强负责整理测试用例，下周一前完成。
另外，大家一致同意下周二下午2点再开一次评审会。"""

SAMPLE_EXPECTED_ACTIONS = 4  # 期望至少提取出4个行动项
SAMPLE_EXPECTED_DECISIONS = 1  # 期望至少提取出1个决策


# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------
def safe_read_text(file_path: str) -> str:
    """安全读取文本文件，支持多编码（utf-8 -> gbk -> gb18030 -> replace）。"""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"E007: 文件不存在 - {file_path}")
    # 尝试多种编码
    for encoding in ["utf-8", "gbk", "gb18030"]:
        try:
            return path.read_text(encoding=encoding)
        except (UnicodeDecodeError, UnicodeError):
            continue
    # 最后兜底：replace 模式
    return path.read_text(encoding="utf-8", errors="replace")


def safe_write_text(file_path: str, content: str) -> None:
    """安全写入文本文件，使用 utf-8 编码。"""
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def log_warning(message: str) -> None:
    """输出警告信息到 stderr。"""
    print(f"[警告] {message}", file=sys.stderr)


def log_error(message: str) -> None:
    """输出错误信息到 stderr。"""
    print(f"[错误] {message}", file=sys.stderr)


# ---------------------------------------------------------------------------
# 输入校验
# ---------------------------------------------------------------------------
def validate_input(text: str) -> str:
    """校验输入文本，返回清洗后的文本。"""
    if text is None:
        raise ValueError("E010: 输入文本不能为 None")
    if not isinstance(text, str):
        raise ValueError("E010: 输入文本必须是字符串类型")
    # 去除首尾空白
    text = text.strip()
    # 空输入检查
    if not text:
        raise ValueError("E003: 素材内容不足以生成完整纪要（空输入）")
    # 长度检查（少于100字提示但允许继续）
    if len(text) < 100:
        log_warning("E003: 素材内容较少（少于100字），可能影响纪要完整性")
    return text


def validate_output_dir(output_dir: str) -> Path:
    """校验输出目录，不存在则创建。"""
    if not output_dir:
        raise ValueError("E010: 输出目录不能为空")
    path = Path(output_dir)
    try:
        path.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise PermissionError(f"E008: 无法创建输出目录 - {exc}") from exc
    if not path.is_dir():
        raise ValueError(f"E008: 输出路径不是目录 - {output_dir}")
    return path


# ---------------------------------------------------------------------------
# 核心逻辑：文本解析
# ---------------------------------------------------------------------------
def split_sentences(text: str) -> list:
    """将文本按句号、问号、感叹号切分为句子列表。"""
    # 使用正则切分，保留标点
    parts = re.split(r"([。！？!?])", text)
    sentences = []
    current = ""
    for part in parts:
        current += part
        if part in "。！？!?":
            sentences.append(current.strip())
            current = ""
    if current.strip():
        sentences.append(current.strip())
    return sentences


def extract_speaker(sentence: str) -> str:
    """从句子中提取发言人（格式：'某某说：' 或 '某某提出：'）。"""
    match = re.search(r"^([\u4e00-\u9fa5A-Za-z0-9]{1,10})(?:说|提出|建议|认为|表示)[:：]", sentence)
    if match:
        return match.group(1)
    return ""


def extract_date(text: str) -> str:
    """从文本中提取日期，格式 YYYY-MM-DD 或 YYYY年M月D日。"""
    match = re.search(r"(\d{4})[年/-](\d{1,2})[月/-](\d{1,2})日?", text)
    if match:
        year, month, day = match.groups()
        return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"
    # 相对日期（今天/明天/下周X）
    today = datetime.now()
    if "今天" in text:
        return today.strftime("%Y-%m-%d")
    if "明天" in text:
        return (today + timedelta(days=1)).strftime("%Y-%m-%d")
    if "下周" in text:
        return (today + timedelta(days=7)).strftime("%Y-%m-%d")
    return ""


def extract_time(text: str) -> str:
    """从文本中提取时间，格式 HH:MM。"""
    match = re.search(r"(\d{1,2})[点时:](\d{1,2})分?", text)
    if match:
        hour, minute = match.groups()
        return f"{int(hour):02d}:{int(minute):02d}"
    return ""


def classify_sentence(sentence: str) -> str:
    """将句子分类为：decision（决策）/ action（行动项）/ discussion（讨论）/ other（其他）。"""
    # 决策关键词
    decision_keywords = ["决定", "一致同意", "确认", "通过", "批准"]
    # 行动项关键词
    action_keywords = ["负责", "跟进", "完成", "输出", "提交", "整理", "准备", "安排"]
    # 时间相关（行动项通常有时间）
    time_pattern = r"(周[一二三四五六日天]|周[1-7]|\d{1,2}月\d{1,2}日|明天|下周|今天)"

    if any(kw in sentence for kw in decision_keywords):
        return "decision"
    if any(kw in sentence for kw in action_keywords) or re.search(time_pattern, sentence):
        return "action"
    if "说" in sentence or "提出" in sentence or "建议" in sentence:
        return "discussion"
    return "other"


def parse_meeting_text(text: str) -> dict:
    """解析会议文本，提取结构化信息。"""
    sentences = split_sentences(text)
    decisions = []
    actions = []
    discussions = []
    speakers = set()
    timeline = []

    for idx, sentence in enumerate(sentences):
        if len(sentence) < 2:
            continue
        speaker = extract_speaker(sentence)
        if speaker:
            speakers.add(speaker)
        category = classify_sentence(sentence)
        # 提取时间
        date_str = extract_date(sentence)
        time_str = extract_time(sentence)

        item = {
            "id": f"{category[0].upper()}{len(decisions) + len(actions) + len(discussions) + 1}",
            "content": sentence,
            "speaker": speaker if speaker else "[需核实:发言人]",
            "date": date_str if date_str else "",
            "time": time_str if time_str else "",
            "confidence": "高" if speaker else "中",
        }

        if category == "decision":
            decisions.append(item)
        elif category == "action":
            actions.append(item)
        elif category == "discussion":
            discussions.append(item)

        if date_str or time_str:
            timeline.append({"time": f"{date_str} {time_str}".strip(), "content": sentence[:50]})

    # 生成摘要（取前3个句子拼接，不超过200字）
    summary = "".join(sentences[:3])[:200]

    return {
        "decisions": decisions,
        "actions": actions,
        "discussions": discussions,
        "speakers": list(speakers) if speakers else ["发言人1", "发言人2"],
        "timeline": timeline,
        "summary": summary,
        "raw_sentences": sentences,
    }


# ---------------------------------------------------------------------------
# 核心逻辑：行动项增强
# ---------------------------------------------------------------------------
def enhance_actions(actions: list) -> list:
    """为行动项补充负责人、截止日期、优先级（若缺失则标记）。"""
    enhanced = []
    for idx, action in enumerate(actions):
        # 负责人：从句子中提取或标记
        owner = action["speaker"]
        if owner == "[需核实:发言人]":
            # 尝试从句子中提取
            match = re.search(r"由([\u4e00-\u9fa5]{1,5})负责", action["content"])
            if match:
                owner = match.group(1)
            else:
                owner = "[需核实:负责人]"
                log_warning("E006: 行动项缺少负责人")

        # 截止日期
        deadline = action["date"]
        if not deadline:
            # 尝试提取相对时间
            if "下周" in action["content"]:
                deadline = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
            elif "明天" in action["content"]:
                deadline = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
            elif "周" in action["content"]:
                # 粗略估算：本周五
                today = datetime.now()
                days_until_friday = (4 - today.weekday()) % 7
                deadline = (today + timedelta(days=days_until_friday)).strftime("%Y-%m-%d")
            else:
                deadline = "[需核实:截止日期]"
                log_warning("E006: 行动项缺少截止日期")

        # 优先级：根据关键词判断
        priority = "中"
        if "紧急" in action["content"] or "立即" in action["content"]:
            priority = "高"
        elif "尽快" in action["content"] or "优先" in action["content"]:
            priority = "高"
        elif "有空" in action["content"] or "稍后" in action["content"]:
            priority = "低"

        enhanced.append({
            "id": f"A{idx + 1}",
            "task": action["content"],
            "owner": owner,
            "deadline": deadline,
            "priority": priority,
            "status": "未开始",
        })
    return enhanced


# ---------------------------------------------------------------------------
# 核心逻辑：质量校验
# ---------------------------------------------------------------------------
def validate_quality(parsed: dict, actions: list) -> dict:
    """对纪要质量进行三维评分（完整性/一致性/可执行性）。"""
    # 完整性：覆盖主题数
    discussion_topics = len(parsed["discussions"])
    decision_count = len(parsed["decisions"])
    completeness_score = min(100, 30 + discussion_topics * 15 + decision_count * 20)

    # 一致性：检查是否有明显矛盾（简化版）
    consistency_score = 90  # 默认较高
    sentences = parsed["raw_sentences"]
    for i in range(len(sentences) - 1):
        if "但是" in sentences[i] and "同意" in sentences[i + 1]:
            consistency_score -= 10

    # 可执行性：行动项是否完整
    executable_score = 0
    if actions:
        has_owner = sum(1 for a in actions if a["owner"] != "[需核实:负责人]")
        has_deadline = sum(1 for a in actions if a["deadline"] != "[需核实:截止日期]")
        executable_score = int((has_owner + has_deadline) / (len(actions) * 2) * 100)

    return {
        "completeness": completeness_score,
        "consistency": max(0, consistency_score),
        "executability": executable_score,
        "overall": int((completeness_score + consistency_score + executable_score) / 3),
    }


# ---------------------------------------------------------------------------
# 输出格式化
# ---------------------------------------------------------------------------
def format_markdown(parsed: dict, actions: list, quality: dict) -> str:
    """生成 Markdown 格式的会议纪要。"""
    lines = []
    lines.append("# 会议纪要：[自动归纳主题]")
    lines.append("")
    lines.append("## 会议信息")
    lines.append("- 日期：2026-08-09")
    speakers_str = "、".join(parsed["speakers"])
    lines.append(f"- 参会人：{speakers_str}")
    lines.append("- 会议时长：[需核实:时长]")
    lines.append("")
    lines.append("## 会议摘要")
    lines.append(parsed["summary"] if parsed["summary"] else "[需核实:摘要]")
    lines.append("")
    lines.append("## 决策记录")
    lines.append("| 编号 | 决策内容 | 决策人 | 置信度 |")
    lines.append("|------|----------|--------|--------|")
    if parsed["decisions"]:
        for d in parsed["decisions"]:
            lines.append(f"| {d['id']} | {d['content']} | {d['speaker']} | {d['confidence']} |")
    else:
        lines.append("| - | 无明确决策 | - | - |")
    lines.append("")
    lines.append("## 讨论要点")
    for i, disc in enumerate(parsed["discussions"], 1):
        lines.append(f"### 主题{i}")
        lines.append(f"- {disc['content']}")
    if not parsed["discussions"]:
        lines.append("### 主题1")
        lines.append("- 无详细讨论记录")
    lines.append("")
    lines.append("## 行动项")
    lines.append("| 编号 | 任务描述 | 负责人 | 截止日期 | 优先级 |")
    lines.append("|------|----------|--------|----------|--------|")
    for a in actions:
        lines.append(f"| {a['id']} | {a['task']} | {a['owner']} | {a['deadline']} | {a['priority']} |")
    if not actions:
        lines.append("| - | 无行动项 | - | - | - |")
    lines.append("")
    lines.append("## 待确认事项")
    lines.append("- [需核实:具体内容]")
    lines.append("")
    lines.append("## 质量评分")
    lines.append(f"- 完整性：{quality['completeness']}/100")
    lines.append(f"- 一致性：{quality['consistency']}/100")
    lines.append(f"- 可执行性：{quality['executability']}/100")
    lines.append(f"- 综合评分：{quality['overall']}/100")
    return "\n".join(lines)


def format_csv(actions: list) -> str:
    """生成行动项 CSV 内容。"""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["任务编号", "任务描述", "负责人", "截止日期", "优先级", "状态"])
    for a in actions:
        writer.writerow([a["id"], a["task"], a["owner"], a["deadline"], a["priority"], a["status"]])
    return output.getvalue()


def format_quality_report(quality: dict) -> str:
    """生成质量校验报告（JSON 格式）。"""
    return json.dumps(quality, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------
def process_meeting(text: str, verbose: bool = False) -> dict:
    """处理会议文本，返回结构化结果。"""
    # 输入校验
    text = validate_input(text)

    # 解析
    parsed = parse_meeting_text(text)

    # 行动项增强
    actions = enhance_actions(parsed["actions"])

    # 质量校验
    quality = validate_quality(parsed, actions)

    # 输出格式化
    markdown = format_markdown(parsed, actions, quality)
    csv_content = format_csv(actions)
    quality_report = format_quality_report(quality)

    if verbose:
        print(f"[详细] 解析出 {len(parsed['decisions'])} 个决策，{len(actions)} 个行动项，{len(parsed['discussions'])} 个讨论要点")
        for a in actions:
            print(f"[详细] 行动项 {a['id']}: {a['task'][:30]}... 负责人={a['owner']} 截止={a['deadline']} 优先级={a['priority']}")

    return {
        "markdown": markdown,
        "csv": csv_content,
        "quality": quality_report,
        "parsed": parsed,
        "actions": actions,
    }


def write_outputs(result: dict, output_dir: str, dry: bool = True) -> None:
    """将结果写入文件。dry=True 时只打印不写盘。"""
    out_path = validate_output_dir(output_dir)
    files = {
        "meeting_notes.md": result["markdown"],
        "actions.csv": result["csv"],
        "quality_report.json": result["quality"],
    }
    for filename, content in files.items():
        filepath = out_path / filename
        if dry:
            print(f"[模拟] 将写入 {filepath} ({len(content)} 字符)")
        else:
            safe_write_text(str(filepath), content)
            print(f"[写入] {filepath}")


# ---------------------------------------------------------------------------
# 自检功能
# ---------------------------------------------------------------------------
def run_selftest() -> bool:
    """运行内置自检，验证核心逻辑正确性。"""
    print("=" * 60)
    print("meeting-pro 自检开始")
    print("=" * 60)

    # 测试1：正常文本解析
    try:
        result = process_meeting(SAMPLE_TEXT, verbose=False)
        assert len(result["actions"]) >= SAMPLE_EXPECTED_ACTIONS, f"行动项数量不足: {len(result['actions'])} < {SAMPLE_EXPECTED_ACTIONS}"
        assert len(result["parsed"]["decisions"]) >= SAMPLE_EXPECTED_DECISIONS, "决策数量不足"
        assert len(result["markdown"]) > 500, "Markdown 输出过短"
        assert "行动项" in result["markdown"], "Markdown 缺少行动项部分"
        print("[通过] 正常文本解析")
    except AssertionError as exc:
        log_error(f"自检失败: {exc}")
        return False
    except Exception as exc:
        log_error(f"自检异常: {exc}")
        return False

    # 测试2：空输入处理
    try:
        try:
            process_meeting("", verbose=False)
            log_error("自检失败: 空输入未抛出异常")
            return False
        except ValueError:
            print("[通过] 空输入正确抛出异常")
    except Exception as exc:
        log_error(f"自检异常: {exc}")
        return False

    # 测试3：中文标点处理
    try:
        chinese_text = "张三说：项目进展顺利。李四提出：需要增加测试。大家决定：下周一上线。"
        result = process_meeting(chinese_text, verbose=False)
        assert len(result["actions"]) > 0, "中文标点文本未提取出行动项"
        print("[通过] 中文标点处理")
    except AssertionError as exc:
        log_error(f"自检失败: {exc}")
        return False
    except Exception as exc:
        log_error(f"自检异常: {exc}")
        return False

    # 测试4：超长文本（性能测试，O(n)）
    try:
        long_text = SAMPLE_TEXT * 100  # 约 10 万字
        import time
        start = time.time()
        result = process_meeting(long_text, verbose=False)
        elapsed = time.time() - start
        assert elapsed < 10, f"超长文本处理超时: {elapsed:.2f}s"
        assert len(result["actions"]) > 0, "超长文本未提取出行动项"
        print(f"[通过] 超长文本处理（{len(long_text)} 字符，耗时 {elapsed:.2f}s）")
    except AssertionError as exc:
        log_error(f"自检失败: {exc}")
        return False
    except Exception as exc:
        log_error(f"自检异常: {exc}")
        return False

    # 测试5：None 输入
    try:
        try:
            process_meeting(None, verbose=False)
            log_error("自检失败: None 输入未抛出异常")
            return False
        except ValueError:
            print("[通过] None 输入正确抛出异常")
    except Exception as exc:
        log_error(f"自检异常: {exc}")
        return False

    print("=" * 60)
    print("全部自检通过！")
    print("=" * 60)
    return True


# ---------------------------------------------------------------------------
# CLI 入口
# ---------------------------------------------------------------------------
def main() -> int:
    """命令行入口。"""
    parser = argparse.ArgumentParser(
        description="meeting-pro 会议纪要智能整理与行动项提取工具",
        epilog="示例: python main.py -i input.txt -o output/ --force",
    )
    parser.add_argument("-i", "--input", help="输入文件路径（txt/srt/vtt）")
    parser.add_argument("-o", "--output", default="./output", help="输出目录（默认 ./output）")
    parser.add_argument("--dry-run", action="store_true", help="只打印不写盘")
    parser.add_argument("--force", action="store_true", help="真正写盘（需与 --dry-run 配合）")
    parser.add_argument("--verbose", action="store_true", help="输出详细处理过程")
    parser.add_argument("--selftest", action="store_true", help="运行内置自检")
    parser.add_argument("--version", action="version", version="meeting-pro 1.0.1")

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        success = run_selftest()
        return 0 if success else 1

    # 参数校验
    if not args.input:
        log_error("E010: 必须提供输入文件（-i）或使用 --selftest")
        parser.print_help()
        return 1

    # 读取输入
    try:
        text = safe_read_text(args.input)
    except FileNotFoundError as exc:
        log_error(str(exc))
        return 1
    except Exception as exc:
        log_error(f"E007: 读取文件失败 - {exc}")
        return 1

    # 处理
    try:
        result = process_meeting(text, verbose=args.verbose)
    except ValueError as exc:
        log_error(str(exc))
        return 1
    except Exception as exc:
        log_error(f"E009: 处理失败 - {exc}")
        return 1

    # 输出
    dry = not args.force  # 默认 dry-run，除非显式 --force
    try:
        write_outputs(result, args.output, dry=dry)
    except Exception as exc:
        log_error(f"E008: 写入失败 - {exc}")
        return 1

    if dry:
        print("\n[提示] 当前为 dry-run 模式，未写盘。加 --force 参数真正写入。")

    return 0


if __name__ == "__main__":
    sys.exit(main())
