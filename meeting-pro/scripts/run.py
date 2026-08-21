#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
meeting-pro: 一站式会议处理工具
录音转文字、纪要生成、行动项提取与校验。
"""

import argparse
import csv
import os
import re
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple
dry_run = False  # v3.274 模块级 dry-run 标志

# ========== 常量定义 ==========
VERSION = "2.0.0"
SUPPORTED_ENCODINGS = ["utf-8", "gbk", "gb18030"]
MIN_TEXT_LENGTH = 50
MAX_BATCH_FILES = 20
CONFIDENCE_THRESHOLD_HIGH = 0.85
CONFIDENCE_THRESHOLD_MEDIUM = 0.70
CONFIDENCE_THRESHOLD_LOW = 0.50

# ========== 错误码定义 ==========
ERROR_CODES = {
    "E-1001": "输入文件不存在",
    "E-1002": "输入文件为空",
    "E-1003": "输入文件编码不支持",
    "E-2001": "输出目录创建失败",
    "E-3001": "批量处理目录不存在",
    "E-3002": "批量处理无有效文件",
    "E-4001": "任务类型不支持",
    "E-5001": "自检失败",
}


class MeetingProError(Exception):
    """会议处理自定义异常"""

    def __init__(self, error_code: str, message: str = ""):
        self.error_code = error_code
        self.message = message or ERROR_CODES.get(error_code, "未知错误")
        super().__init__(f"[{error_code}] {self.message}")


# ========== 输入校验 ==========
def validate_input_file(filepath: str) -> str:
    """校验输入文件，返回文件内容"""
    if not filepath:
        raise MeetingProError("E-1001", "未指定输入文件")

    path = Path(filepath)
    if not path.exists():
        raise MeetingProError("E-1001", f"文件不存在: {filepath}")
    if not path.is_file():
        raise MeetingProError("E-1001", f"不是文件: {filepath}")

    content = read_text_file(filepath)
    if not content.strip():
        raise MeetingProError("E-1002", f"文件为空: {filepath}")

    return content


def validate_output_dir(output_dir: str) -> Path:
    """校验输出目录，必要时创建"""
    if not output_dir:
        raise MeetingProError("E-2001", "未指定输出目录")

    path = Path(output_dir)
    try:
        path.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        raise MeetingProError("E-2001", f"创建输出目录失败: {e}")

    return path


def validate_batch_dir(batch_dir: str) -> List[Path]:
    """校验批量处理目录，返回有效文件列表"""
    if not batch_dir:
        raise MeetingProError("E-3001", "未指定批量处理目录")

    path = Path(batch_dir)
    if not path.exists() or not path.is_dir():
        raise MeetingProError("E-3001", f"目录不存在: {batch_dir}")

    files = [f for f in path.iterdir() if f.is_file() and f.suffix.lower() in (".txt", ".md")]
    if not files:
        raise MeetingProError("E-3002", f"目录内无有效文本文件: {batch_dir}")

    if len(files) > MAX_BATCH_FILES:
        files = files[:MAX_BATCH_FILES]

    return files


# ========== 文件读写 ==========
def read_text_file(filepath: str) -> str:
    """多编码安全读取文本文件"""
    for enc in SUPPORTED_ENCODINGS:
        try:
            with open(filepath, "r", encoding=enc) as f:
                return f.read()
        except UnicodeDecodeError:
            continue
        except OSError as e:
            raise MeetingProError("E-1003", f"读取文件失败: {e}")

    # 最后尝试使用 errors='replace'
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    except OSError as e:
        raise MeetingProError("E-1003", f"读取文件失败: {e}")


def write_text_file(filepath: Path, content: str, dry_run: bool = False) -> None:
    """原子化写入文本文件"""
    if dry_run:
        print(f"[DRY-RUN] 将写入: {filepath}")
        return

    try:
        # 原子写入：先写临时文件，再替换
        fd, temp_path = tempfile.mkstemp(dir=str(filepath.parent), suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(content)
            os.replace(temp_path, str(filepath))
        except Exception:
            # 清理临时文件
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            raise
    except OSError as e:
        raise MeetingProError("E-2001", f"写入文件失败: {e}")


def write_csv_file(filepath: Path, rows: List[Dict], dry_run: bool = False) -> None:
    """原子化写入 CSV 文件"""
    if dry_run:
        print(f"[DRY-RUN] 将写入: {filepath}")
        return

    try:
        fd, temp_path = tempfile.mkstemp(dir=str(filepath.parent), suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8-sig", newline="") as f:
                if rows:
                    writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
                    writer.writeheader()
                    writer.writerows(rows)
            os.replace(temp_path, str(filepath))
        except Exception:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            raise
    except OSError as e:
        raise MeetingProError("E-2001", f"写入 CSV 失败: {e}")


# ========== 文本处理 ==========
def clean_text(text: str) -> str:
    """清洗文本：去除多余空白、重复段落"""
    if not text:
        return ""

    # 去除多余空白行
    lines = [line.strip() for line in text.splitlines()]
    cleaned_lines = []
    prev_empty = False
    for line in lines:
        if not line:
            if not prev_empty:
                cleaned_lines.append("")
            prev_empty = True
        else:
            cleaned_lines.append(line)
            prev_empty = False

    # 去除重复段落（连续相同行）
    unique_lines = []
    for line in cleaned_lines:
        if not unique_lines or line != unique_lines[-1]:
            unique_lines.append(line)

    return "\n".join(unique_lines).strip()


def extract_meeting_info(text: str) -> Dict:
    """提取会议基本信息"""
    info = {
        "topic": "未命名会议",
        "participants": [],
        "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
    }

    # 提取主题
    topic_match = re.search(r"(?:会议主题|主题)[：:]\s*(.+)", text)
    if topic_match:
        info["topic"] = topic_match.group(1).strip()

    # 提取参会人
    participants_match = re.search(r"(?:参会人|参会人员|出席人员)[：:]\s*(.+)", text)
    if participants_match:
        participants = [p.strip() for p in participants_match.group(1).split("、")]
        info["participants"] = participants

    return info


def extract_topics(text: str) -> List[str]:
    """提取核心议题"""
    topics = []
    lines = text.splitlines()

    for line in lines:
        # 匹配议题标题
        if re.match(r"^(?:议题|讨论|主题)\s*\d*[：:]\s*", line):
            topic = re.sub(r"^(?:议题|讨论|主题)\s*\d*[：:]\s*", "", line).strip()
            if topic and topic not in topics:
                topics.append(topic)

    # 如果没有明确议题，从内容中提取
    if not topics:
        # 查找包含"讨论"或"议题"的句子
        for line in lines:
            if "讨论" in line and len(line) > 10:
                topic = line.strip()[:50]
                if topic not in topics:
                    topics.append(topic)
                if len(topics) >= 5:
                    break

    return topics[:5]


def extract_conclusions(text: str) -> List[str]:
    """提取关键结论"""
    conclusions = []
    lines = text.splitlines()

    for line in lines:
        # 匹配包含结论关键词的句子
        if re.search(r"(?:决定|确认|同意|通过|确定)", line):
            conclusion = line.strip()
            if conclusion and conclusion not in conclusions:
                conclusions.append(conclusion)

    return conclusions[:5]


def extract_action_items(text: str) -> List[Dict]:
    """提取行动项"""
    action_items = []
    lines = text.splitlines()

    for line in lines:
        # 匹配行动项模式：责任人 + 负责/跟进/完成 + 任务
        match = re.search(r"([\u4e00-\u9fa5]{2,4})(?:负责|跟进|完成|处理|协调)(.+)", line)
        if match:
            person = match.group(1)
            task = match.group(2).strip()
            action_items.append({
                "task": task,
                "owner": person,
                "deadline": "未指定",
                "priority": "中",
            })

    # 如果没有匹配到，尝试更宽松的模式
    if not action_items:
        for line in lines:
            if "负责" in line:
                parts = line.split("负责")
                if len(parts) == 2:
                    person = parts[0].strip()
                    task = parts[1].strip()
                    if person and task:
                        action_items.append({
                            "task": task,
                            "owner": person,
                            "deadline": "未指定",
                            "priority": "中",
                        })

    return action_items[:10]


def calculate_confidence(text: str, topics: List[str], conclusions: List[str], action_items: List[Dict]) -> float:
    """计算置信度评分"""
    if not text:
        return 0.0

    # 文本覆盖率（30%）
    total_chars = len(text)
    meaningful_chars = len(re.sub(r"\s+", "", text))
    coverage = meaningful_chars / total_chars if total_chars > 0 else 0

    # 语义连贯性（25%）
    sentences = re.split(r"[。！？!?]", text)
    sentences = [s.strip() for s in sentences if s.strip()]
    coherence = min(1.0, len(sentences) / 10) if sentences else 0

    # 要素完整度（25%）
    expected_elements = 3  # 议题、结论、行动项
    actual_elements = 0
    if topics:
        actual_elements += 1
    if conclusions:
        actual_elements += 1
    if action_items:
        actual_elements += 1
    completeness = actual_elements / expected_elements

    # 时间戳准确率（20%）
    timestamp_accuracy = 1.0  # 文本输入默认准确

    confidence = (
        coverage * 0.30 +
        coherence * 0.25 +
        completeness * 0.25 +
        timestamp_accuracy * 0.20
    )

    return round(min(1.0, max(0.0, confidence)), 2)


def generate_minutes(text: str, verbose: bool = False) -> str:
    """生成会议纪要"""
    info = extract_meeting_info(text)
    topics = extract_topics(text)
    conclusions = extract_conclusions(text)
    action_items = extract_action_items(text)

    if verbose:
        print(f"[VERBOSE] 提取到 {len(topics)} 个议题")
        print(f"[VERBOSE] 提取到 {len(conclusions)} 个结论")
        print(f"[VERBOSE] 提取到 {len(action_items)} 个行动项")

    minutes = []
    minutes.append("# 会议纪要\n")
    minutes.append("## 会议信息")
    minutes.append(f"- 主题：{info['topic']}")
    minutes.append(f"- 日期：{info['date']}")
    if info["participants"]:
        minutes.append(f"- 参会人：{'、'.join(info['participants'])}")
    minutes.append("")

    if topics:
        minutes.append("## 议题与结论")
        for i, topic in enumerate(topics, 1):
            minutes.append(f"### 议题 {i}：{topic}")
            minutes.append(f"- 讨论要点：{topic}")
            if i <= len(conclusions):
                minutes.append(f"- 结论：{conclusions[i-1]}")
            minutes.append("")

    if action_items:
        minutes.append("## 行动项")
        minutes.append("| 序号 | 任务描述 | 责任人 | 截止时间 | 优先级 |")
        minutes.append("|------|----------|--------|----------|--------|")
        for i, item in enumerate(action_items, 1):
            minutes.append(f"| {i} | {item['task']} | {item['owner']} | {item['deadline']} | {item['priority']} |")
        minutes.append("")

    # 待确认事项
    pending = []
    if not conclusions:
        pending.append("未提取到明确结论，请确认会议决策")
    if not action_items:
        pending.append("未提取到行动项，请确认是否有待办事项")

    if pending:
        minutes.append("## 待确认事项")
        for item in pending:
            minutes.append(f"- [需核实] {item}")
        minutes.append("")

    return "\n".join(minutes)


def generate_validation_report(text: str, verbose: bool = False) -> str:
    """生成校验报告"""
    topics = extract_topics(text)
    conclusions = extract_conclusions(text)
    action_items = extract_action_items(text)
    confidence = calculate_confidence(text, topics, conclusions, action_items)

    report = []
    report.append("# 校验报告\n")
    report.append(f"- 生成时间：{datetime.now(timezone.utc).isoformat()}")
    report.append(f"- 置信度评分：{confidence}")
    report.append("")

    report.append("## 完整性检查")
    report.append(f"- 议题提取：{'✓' if topics else '✗'} ({len(topics)} 个)")
    report.append(f"- 结论提取：{'✓' if conclusions else '✗'} ({len(conclusions)} 个)")
    report.append(f"- 行动项提取：{'✓' if action_items else '✗'} ({len(action_items)} 个)")
    report.append("")

    report.append("## 一致性检查")
    if confidence >= CONFIDENCE_THRESHOLD_HIGH:
        report.append("- 状态：通过")
        report.append("- 建议：可直接交付")
    elif confidence >= CONFIDENCE_THRESHOLD_MEDIUM:
        report.append("- 状态：部分通过")
        report.append("- 建议：需人工复核存疑项")
    elif confidence >= CONFIDENCE_THRESHOLD_LOW:
        report.append("- 状态：需补充")
        report.append("- 建议：请补充更多会议素材")
    else:
        report.append("- 状态：不通过")
        report.append("- 建议：素材质量不足，请重新提供")

    return "\n".join(report)


# ========== 任务处理 ==========
def process_single_file(input_file: str, output_dir: str, task: str, dry_run: bool = False, verbose: bool = False) -> Dict:
    """处理单个文件"""
    result = {"input": input_file, "status": "success", "outputs": []}

    try:
        # 读取输入
        content = validate_input_file(input_file)
        if verbose:
            print(f"[VERBOSE] 读取文件: {input_file} ({len(content)} 字符)")

        # 清洗文本
        cleaned = clean_text(content)
        if verbose:
            print(f"[VERBOSE] 清洗后: {len(cleaned)} 字符")

        # 创建输出目录
        out_path = validate_output_dir(output_dir)

        # 根据任务类型处理
        if task in ("minutes", "all"):
            minutes = generate_minutes(cleaned, verbose)
            minutes_file = out_path / "meeting_minutes.md"
            write_text_file(minutes_file, minutes, dry_run)
            result["outputs"].append(str(minutes_file))

        if task in ("action-items", "all"):
            action_items = extract_action_items(cleaned)
            if action_items:
                csv_file = out_path / "action_items.csv"
                write_csv_file(csv_file, action_items, dry_run)
                result["outputs"].append(str(csv_file))

        if task in ("validate", "all"):
            report = generate_validation_report(cleaned, verbose)
            report_file = out_path / "validation_report.md"
            write_text_file(report_file, report, dry_run)
            result["outputs"].append(str(report_file))

        if task not in ("minutes", "action-items", "validate", "all"):
            raise MeetingProError("E-4001", f"不支持的任务类型: {task}")

    except MeetingProError as e:
        result["status"] = "error"
        result["error"] = str(e)
        print(f"错误: {e}", file=sys.stderr)

    except Exception as e:
        result["status"] = "error"
        result["error"] = f"未知错误: {e}"
        print(f"未知错误: {e}", file=sys.stderr)

    return result


def process_batch(batch_dir: str, output_dir: str, task: str, dry_run: bool = False, verbose: bool = False) -> Dict:
    """批量处理目录内所有文件"""
    result = {"status": "success", "files": [], "summary": []}

    try:
        files = validate_batch_dir(batch_dir)
        out_path = validate_output_dir(output_dir)

        if verbose:
            print(f"[VERBOSE] 找到 {len(files)} 个文件待处理")

        for file in files:
            file_result = process_single_file(str(file), str(out_path / file.stem), task, dry_run, verbose)
            result["files"].append(file_result)

            if file_result["status"] == "success":
                result["summary"].append({
                    "file": file.name,
                    "status": "success",
                    "outputs": "; ".join(file_result["outputs"]),
                })
            else:
                result["summary"].append({
                    "file": file.name,
                    "status": "error",
                    "outputs": file_result.get("error", "未知错误"),
                })

        # 生成批量汇总
        if result["summary"]:
            summary_file = out_path / "batch_summary.csv"
            write_csv_file(summary_file, result["summary"], dry_run)
            result["outputs"] = [str(summary_file)]

    except MeetingProError as e:
        result["status"] = "error"
        result["error"] = str(e)
        print(f"错误: {e}", file=sys.stderr)

    except Exception as e:
        result["status"] = "error"
        result["error"] = f"未知错误: {e}"
        print(f"未知错误: {e}", file=sys.stderr)

    return result


# ========== 自检 ==========
def run_selftest() -> bool:
    """运行自检，验证核心功能"""
    print("=" * 60)
    print("meeting-pro 自检开始")
    print("=" * 60)

    test_cases = [
        {
            "name": "基本纪要生成",
            "content": "会议主题：Q3 产品规划\n参会人：张伟、李娜、王强\n讨论内容：确定 Q3 产品路线图，讨论预算分配。\n结论：确认 10 月上线，预算 50 万。\n行动项：李娜负责市场调研，王强负责技术开发。",
            "expect_topics": True,
            "expect_conclusions": True,
            "expect_action_items": True,
        },
        {
            "name": "空输入处理",
            "content": "",
            "expect_topics": False,
            "expect_conclusions": False,
            "expect_action_items": False,
        },
        {
            "name": "中文标点",
            "content": "会议主题：测试会议。参会人：张三、李四。讨论：项目进度。结论：确认延期。行动项：张三负责测试。",
            "expect_topics": True,
            "expect_conclusions": True,
            "expect_action_items": True,
        },
        {
            "name": "超长输入",
            "content": "会议主题：长会议\n" + "讨论内容：这是第{}个议题的详细讨论。\n" * 100,
            "expect_topics": True,
            "expect_conclusions": False,
            "expect_action_items": False,
        },
    ]

    all_passed = True

    for i, case in enumerate(test_cases, 1):
        print(f"\n测试 {i}: {case['name']}")
        try:
            content = case["content"]
            topics = extract_topics(content)
            conclusions = extract_conclusions(content)
            action_items = extract_action_items(content)

            # 断言
            assert bool(topics) == case["expect_topics"], f"议题提取失败: {topics}"
            assert bool(conclusions) == case["expect_conclusions"], f"结论提取失败: {conclusions}"
            assert bool(action_items) == case["expect_action_items"], f"行动项提取失败: {action_items}"

            # 额外验证
            minutes = generate_minutes(content)
            assert "会议纪要" in minutes, "纪要生成失败"

            confidence = calculate_confidence(content, topics, conclusions, action_items)
            assert 0.0 <= confidence <= 1.0, f"置信度超出范围: {confidence}"

            print(f"  ✓ 通过 (置信度: {confidence})")

        except AssertionError as e:
            print(f"  ✗ 失败: {e}")
            all_passed = False
        except Exception as e:
            print(f"  ✗ 异常: {e}")
            all_passed = False

    # 测试文件读写
    print("\n测试 5: 文件读写")
    try:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
            f.write("测试内容：文件读写验证。")
            temp_file = f.name

        content = read_text_file(temp_file)
        assert "文件读写" in content, "文件读取失败"

        # 测试 GBK 编码
        gbk_file = temp_file + ".gbk"
        with open(gbk_file, "w", encoding="gbk") as f:
            f.write("GBK 编码测试内容。")
        content = read_text_file(gbk_file)
        assert "GBK" in content, "GBK 编码读取失败"

        os.unlink(temp_file)
        os.unlink(gbk_file)
        print("  ✓ 通过")

    except Exception as e:
        print(f"  ✗ 失败: {e}")
        all_passed = False

    # 测试批量处理
    print("\n测试 6: 批量处理")
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建测试文件
            for j in range(3):
                file_path = Path(tmpdir) / f"meeting_{j}.txt"
                if not dry_run:
                    file_path.write_text(f"会议主题：批量会议 {j}\n讨论内容：测试批量处理。\n结论：确认完成。", encoding="utf-8")

            files = validate_batch_dir(tmpdir)
            assert len(files) == 3, f"批量文件数量错误: {len(files)}"

            print("  ✓ 通过")

    except Exception as e:
        print(f"  ✗ 失败: {e}")
        all_passed = False

    print("\n" + "=" * 60)
    if all_passed:
        print("自检全部通过 ✓")
    else:
        print("自检存在失败项 ✗")
    print("=" * 60)

    return all_passed


# ========== 主入口 ==========
def main():
    parser = argparse.ArgumentParser(
        description="meeting-pro: 一站式会议处理工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python run.py --input meeting.txt --output out/
  python run.py --batch ./meetings/ --output out/
  python run.py --input meeting.txt --task action-items
  python run.py --selftest
        """,
    )

    parser.add_argument("--input", "-i", help="输入文件路径")
    parser.add_argument("--batch", "-b", help="批量处理目录")
    parser.add_argument("--output", "-o", default="./output", help="输出目录 (默认: ./output)")
    parser.add_argument("--task", "-t", choices=["minutes", "action-items", "validate", "all"], default="all", help="任务类型 (默认: all)")
    parser.add_argument("--dry-run", action="store_true", help="预览模式，不实际写入文件")
    parser.add_argument("--verbose", "-v", action="store_true", help="显示详细处理日志")
    parser.add_argument("--selftest", action="store_true", help="运行自检")
    parser.add_argument("--version", action="version", version=f"meeting-pro {VERSION}")

    args = parser.parse_args()

    global dry_run

    dry_run = getattr(args, "dry_run", False)  # v3.274 同步到全局

    # 自检模式
    if args.selftest:
        success = run_selftest()
        sys.exit(0 if success else 1)

    # 参数校验
    if not args.input and not args.batch:
        parser.error("必须指定 --input 或 --batch")

    if args.input and args.batch:
        parser.error("--input 和 --batch 不能同时使用")

    # 执行任务
    if args.batch:
        result = process_batch(args.batch, args.output, args.task, args.dry_run, args.verbose)
    else:
        result = process_single_file(args.input, args.output, args.task, args.dry_run, args.verbose)

    # 输出结果
    if result["status"] == "success":
        print("处理完成 ✓")
        if "outputs" in result and result["outputs"]:
            print("生成文件:")
            for output in result["outputs"]:
                print(f"  - {output}")
        if "files" in result:
            success_count = sum(1 for f in result["files"] if f["status"] == "success")
            print(f"批量处理: {success_count}/{len(result['files'])} 个文件成功")
    else:
        print(f"处理失败 ✗: {result.get('error', '未知错误')}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
