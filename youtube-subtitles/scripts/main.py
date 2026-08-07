#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py — youtube-subtitles 技能独立实现

本脚本依据《youtube-subtitles 功能规格》进行 clean-room 独立实现。
仅使用 Python 标准库，无第三方依赖。

功能概述：
    将用户提供的字幕数据（字符串/文件路径/URL文本）解析为结构化结果，
    支持时间轴（时:分:秒）区间提取、关键词搜索、置信度评估与批量处理。

用法示例：
    python scripts/main.py --selftest
    python scripts/main.py --input "00:01:23,456 --> 00:01:25,789 你好世界"
    python scripts/main.py --file subtitles.srt --keyword "hello" --format json
"""

import argparse
import json
import os
import re
import sys
import tempfile
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# 错误码定义（E001-E010）
# ---------------------------------------------------------------------------
ERR_INPUT_EMPTY = "E001"            # 输入为空
ERR_KEY_INFO_MISSING = "E002"       # 关键信息缺失
ERR_INPUT_FORMAT = "E003"           # 输入格式错误
ERR_OUT_OF_SCOPE = "E004"           # 超出能力边界
ERR_LOW_CONFIDENCE = "E005"         # 置信度过低
ERR_FILE_NOT_FOUND = "E006"         # 文件不存在
ERR_FILE_READ = "E007"              # 文件读取失败
ERR_URL_INVALID = "E008"            # URL 格式无效（本实现不访问网络）
ERR_BATCH_EMPTY = "E009"            # 批量输入为空
ERR_INTERNAL = "E010"               # 内部错误

# ---------------------------------------------------------------------------
# 数据结构
# ---------------------------------------------------------------------------
@dataclass
class SubtitleEntry:
    """单条字幕条目"""
    index: Optional[int] = None          # 序号（可选）
    start: str = ""                      # 开始时间（HH:MM:SS,mmm 或 HH:MM:SS）
    end: str = ""                        # 结束时间（同上）
    text: str = ""                       # 字幕文本
    confidence: float = 1.0              # 置信度 0~1

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ProcessResult:
    """处理结果"""
    entries: List[SubtitleEntry] = field(default_factory=list)
    total_count: int = 0
    matched_count: int = 0
    keyword: Optional[str] = None
    confidence: float = 1.0
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entries": [e.to_dict() for e in self.entries],
            "total_count": self.total_count,
            "matched_count": self.matched_count,
            "keyword": self.keyword,
            "confidence": round(self.confidence, 4),
            "warnings": self.warnings,
        }


# ---------------------------------------------------------------------------
# 核心解析逻辑
# ---------------------------------------------------------------------------
class SubtitleParser:
    """字幕解析器：支持 SRT 格式及简易文本（时间轴 + 文本）"""

    # 时间格式：支持 00:00:00,000 或 00:00:00
    TIME_PATTERN = re.compile(
        r"(\d{1,2}):(\d{2}):(\d{2})(?:[.,](\d{1,3}))?"
    )
    # 时间轴行：如 "00:01:23,456 --> 00:01:25,789"
    TIMELINE_PATTERN = re.compile(
        r"^\s*(\d{1,2}:\d{2}:\d{2}(?:[.,]\d{1,3})?)\s*-->\s*"
        r"(\d{1,2}:\d{2}:\d{2}(?:[.,]\d{1,3})?)\s*$"
    )
    # 序号行：纯数字
    INDEX_PATTERN = re.compile(r"^\s*\d+\s*$")

    def parse(self, content: str) -> List[SubtitleEntry]:
        """解析字幕内容为条目列表（支持 SRT 或简易格式）"""
        if not content or not content.strip():
            raise ValueError(ERR_INPUT_EMPTY)

        lines = content.splitlines()
        entries: List[SubtitleEntry] = []
        i = 0
        n = len(lines)

        while i < n:
            line = lines[i].strip()

            # 跳过空行
            if not line:
                i += 1
                continue

            # 尝试解析序号（可选）
            index = None
            if self.INDEX_PATTERN.match(line):
                try:
                    index = int(line)
                    i += 1
                    if i >= n:
                        break
                    line = lines[i].strip()
                except ValueError:
                    index = None

            # 尝试解析时间轴
            timeline_match = self.TIMELINE_PATTERN.match(line)
            if timeline_match:
                start = timeline_match.group(1).replace(",", ".")
                end = timeline_match.group(2).replace(",", ".")
                i += 1

                # 收集文本（直到空行或下一个时间轴/序号）
                text_lines: List[str] = []
                while i < n:
                    next_line = lines[i].strip()
                    if not next_line:
                        break
                    if self.TIMELINE_PATTERN.match(next_line):
                        break
                    if self.INDEX_PATTERN.match(next_line) and text_lines:
                        # 避免把下一段序号当作文本
                        break
                    text_lines.append(next_line)
                    i += 1

                text = " ".join(text_lines).strip()
                if text:
                    entries.append(SubtitleEntry(
                        index=index,
                        start=start,
                        end=end,
                        text=text,
                        confidence=0.95,  # 时间轴完整，置信度较高
                    ))
                else:
                    # 有时间轴但无文本，置信度降低
                    entries.append(SubtitleEntry(
                        index=index,
                        start=start,
                        end=end,
                        text="",
                        confidence=0.5,
                    ))
                # 跳过空行
                while i < n and not lines[i].strip():
                    i += 1
                continue

            # 简易格式：单行 "时间 文本" 或 "文本"
            # 尝试提取时间（如果行首有时间）
            time_match = self.TIME_PATTERN.match(line)
            if time_match:
                # 提取时间部分和剩余文本
                time_str = time_match.group(0)
                rest = line[time_match.end():].strip()
                # 尝试解析开始和结束时间（可能只有开始）
                start = time_str.replace(",", ".")
                end = ""
                # 如果后面还有 "-->" 或 "-" 分隔，尝试提取结束时间
                sep_match = re.search(r"-->\s*(\d{1,2}:\d{2}:\d{2}(?:[.,]\d{1,3})?)", line)
                if sep_match:
                    end = sep_match.group(1).replace(",", ".")
                else:
                    # 尝试 "开始-结束" 或 "开始 结束"
                    parts = line[time_match.end():].strip().split()
                    if parts and self.TIME_PATTERN.match(parts[0]):
                        end = parts[0].replace(",", ".")
                        rest = " ".join(parts[1:]).strip()
                entries.append(SubtitleEntry(
                    index=index,
                    start=start,
                    end=end,
                    text=rest,
                    confidence=0.8 if end else 0.6,
                ))
                i += 1
                continue

            # 纯文本行（无时间），置信度低
            entries.append(SubtitleEntry(
                index=index,
                start="",
                end="",
                text=line,
                confidence=0.4,
            ))
            i += 1

        return entries


# ---------------------------------------------------------------------------
# 搜索与过滤
# ---------------------------------------------------------------------------
def filter_by_keyword(entries: List[SubtitleEntry], keyword: str) -> List[SubtitleEntry]:
    """按关键词过滤条目（不区分大小写）"""
    if not keyword:
        return entries
    kw = keyword.lower()
    return [e for e in entries if kw in e.text.lower()]


def calculate_confidence(entries: List[SubtitleEntry]) -> float:
    """计算整体置信度（取平均）"""
    if not entries:
        return 0.0
    return sum(e.confidence for e in entries) / len(entries)


# ---------------------------------------------------------------------------
# 格式化输出
# ---------------------------------------------------------------------------
def format_text(result: ProcessResult) -> str:
    """文本格式输出"""
    if not result.entries:
        return "（无匹配结果）"

    lines = []
    for e in result.entries:
        time_str = ""
        if e.start:
            time_str = f"[{e.start}"
            if e.end:
                time_str += f" -> {e.end}"
            time_str += "] "
        conf_mark = ""
        if e.confidence < 0.85:
            conf_mark = " [需核实]"
        elif e.confidence < 0.9:
            conf_mark = " [建议复核]"
        lines.append(f"{time_str}{e.text}{conf_mark}")

    header = f"共 {result.total_count} 条，匹配 {result.matched_count} 条"
    if result.keyword:
        header += f"，关键词: {result.keyword}"
    header += f"，置信度: {result.confidence:.0%}"

    return header + "\n" + "\n".join(lines)


def format_json(result: ProcessResult) -> str:
    """JSON 格式输出"""
    return json.dumps(result.to_dict(), ensure_ascii=False, indent=2)


def format_srt(result: ProcessResult) -> str:
    """SRT 格式输出"""
    if not result.entries:
        return ""
    lines = []
    for idx, e in enumerate(result.entries, start=1):
        lines.append(str(idx))
        if e.start:
            start = e.start.replace(".", ",")
            end = e.end.replace(".", ",") if e.end else e.start.replace(".", ",")
            lines.append(f"{start} --> {end}")
        lines.append(e.text)
        lines.append("")  # 空行
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 主处理流程
# ---------------------------------------------------------------------------
def process_input(
    content: str,
    keyword: Optional[str] = None,
    output_format: str = "text",
) -> Tuple[str, Optional[str]]:
    """
    处理输入内容，返回 (结果字符串, 错误码或None)

    返回错误码时，结果字符串为错误提示。
    """
    try:
        # 输入校验
        if not content or not content.strip():
            return "请提供待处理的内容，格式为：用户提供的数据/文件/URL", ERR_INPUT_EMPTY

        # 解析
        parser = SubtitleParser()
        entries = parser.parse(content)

        if not entries:
            return "输入格式不符合要求，示例：00:01:23,456 --> 00:01:25,789 文本内容", ERR_INPUT_FORMAT

        # 关键词过滤
        matched = filter_by_keyword(entries, keyword) if keyword else entries

        # 构建结果
        result = ProcessResult(
            entries=matched,
            total_count=len(entries),
            matched_count=len(matched),
            keyword=keyword,
            confidence=calculate_confidence(matched) if matched else 0.0,
        )

        # 置信度过低提示
        if result.confidence < 0.85:
            result.warnings.append("结果置信度较低，建议人工复核关键内容")

        # 格式化输出
        if output_format == "json":
            output = format_json(result)
        elif output_format == "srt":
            output = format_srt(result)
        else:
            output = format_text(result)

        return output, None

    except ValueError as e:
        # 自定义错误码
        return str(e), str(e)
    except Exception as e:
        return f"内部错误: {e}", ERR_INTERNAL


# ---------------------------------------------------------------------------
# 文件与 URL 处理
# ---------------------------------------------------------------------------
def read_file(path: str) -> Tuple[str, Optional[str]]:
    """读取文件内容，返回 (内容, 错误码)"""
    if not os.path.exists(path):
        return f"文件不存在: {path}", ERR_FILE_NOT_FOUND
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.read(), None
    except Exception as e:
        return f"文件读取失败: {e}", ERR_FILE_READ


def validate_url(url: str) -> Tuple[bool, str]:
    """校验 URL 格式（不访问网络）"""
    # 简单 URL 格式校验
    pattern = re.compile(
        r"^(https?://)?([a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}(/\S*)?$"
    )
    if pattern.match(url):
        return True, ""
    return False, f"URL 格式无效: {url}"


# ---------------------------------------------------------------------------
# 批量处理
# ---------------------------------------------------------------------------
def process_batch(
    items: List[str],
    keyword: Optional[str] = None,
    output_format: str = "text",
) -> Tuple[str, Optional[str]]:
    """批量处理多个输入"""
    if not items:
        return "批量输入为空", ERR_BATCH_EMPTY

    results = []
    for idx, item in enumerate(items, start=1):
        output, err = process_input(item, keyword, output_format)
        if err:
            results.append(f"第 {idx} 项处理失败: {output}")
        else:
            results.append(f"第 {idx} 项:\n{output}")

    return "\n\n".join(results), None


# ---------------------------------------------------------------------------
# 自检模块（--selftest）
# ---------------------------------------------------------------------------
def run_selftest() -> bool:
    """内置硬编码样例数据离线自检核心逻辑"""
    print("=" * 60)
    print("自检开始（youtube-subtitles）")
    print("=" * 60)

    all_passed = True

    # --- 测试 1: 基本解析 ---
    print("\n[1] 基本解析测试")
    sample1 = """1
00:00:01,000 --> 00:00:03,000
你好世界

2
00:00:04,500 --> 00:00:06,000
hello world

3
00:00:07,000 --> 00:00:09,500
这是第三个测试"""
    output, err = process_input(sample1, output_format="text")
    if err:
        print(f"  失败: {err}")
        all_passed = False
    else:
        assert "你好世界" in output, "应包含第一条文本"
        assert "hello world" in output, "应包含第二条文本"
        assert "这是第三个测试" in output, "应包含第三条文本"
        assert "共 3 条" in output, "应显示总条数"
        print("  通过")

    # --- 测试 2: 关键词过滤 ---
    print("\n[2] 关键词过滤测试")
    output, err = process_input(sample1, keyword="hello", output_format="text")
    if err:
        print(f"  失败: {err}")
        all_passed = False
    else:
        assert "hello world" in output, "应匹配 hello"
        assert "你好世界" not in output, "不应匹配不相关文本"
        assert "匹配 1 条" in output, "应显示匹配条数"
        print("  通过")

    # --- 测试 3: JSON 输出 ---
    print("\n[3] JSON 输出测试")
    output, err = process_input(sample1, output_format="json")
    if err:
        print(f"  失败: {err}")
        all_passed = False
    else:
        try:
            data = json.loads(output)
            assert data["total_count"] == 3, "JSON total_count 应为 3"
            assert len(data["entries"]) == 3, "JSON entries 应为 3"
            assert data["entries"][0]["text"] == "你好世界", "第一条文本错误"
            print("  通过")
        except json.JSONDecodeError:
            print("  失败: JSON 解析错误")
            all_passed = False

    # --- 测试 4: SRT 输出 ---
    print("\n[4] SRT 输出测试")
    output, err = process_input(sample1, output_format="srt")
    if err:
        print(f"  失败: {err}")
        all_passed = False
    else:
        assert "-->" in output, "SRT 应包含时间轴"
        assert "你好世界" in output, "SRT 应包含文本"
        print("  通过")

    # --- 测试 5: 简易格式解析 ---
    print("\n[5] 简易格式解析测试")
    sample2 = """00:00:01 第一行文本
00:00:03 第二行文本
没有时间的文本"""
    output, err = process_input(sample2, output_format="text")
    if err:
        print(f"  失败: {err}")
        all_passed = False
    else:
        assert "第一行文本" in output, "应解析第一行"
        assert "第二行文本" in output, "应解析第二行"
        assert "没有时间的文本" in output, "应解析无时间行"
        print("  通过")

    # --- 测试 6: 空输入 ---
    print("\n[6] 空输入测试")
    output, err = process_input("")
    if err == ERR_INPUT_EMPTY:
        print("  通过")
    else:
        print(f"  失败: 期望 E001，实际 {err}")
        all_passed = False

    # --- 测试 7: 无效输入 ---
    print("\n[7] 无效输入测试")
    output, err = process_input("完全没有时间轴的普通文本")
    if err == ERR_INPUT_FORMAT:
        print("  通过")
    else:
        # 宽松判断：应能解析为条目或报格式错误
        if err is None and output:
            print("  通过（已解析为条目）")
        else:
            print(f"  失败: 期望 E003 或成功解析，实际 {err}")
            all_passed = False

    # --- 测试 8: 置信度计算 ---
    print("\n[8] 置信度计算测试")
    parser = SubtitleParser()
    entries = parser.parse(sample1)
    conf = calculate_confidence(entries)
    if 0.5 <= conf <= 1.0:
        print(f"  通过（置信度: {conf:.2f}）")
    else:
        print(f"  失败: 置信度超出范围 {conf}")
        all_passed = False

    # --- 测试 9: 批量处理 ---
    print("\n[9] 批量处理测试")
    batch = [sample1, sample2]
    output, err = process_batch(batch)
    if err:
        print(f"  失败: {err}")
        all_passed = False
    else:
        assert "第 1 项" in output, "应包含第一项"
        assert "第 2 项" in output, "应包含第二项"
        print("  通过")

    # --- 测试 10: 文件读取（临时文件） ---
    print("\n[10] 文件读取测试")
    try:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".srt", delete=False, encoding="utf-8") as f:
            f.write(sample1)
            tmp_path = f.name
        content, err = read_file(tmp_path)
        if err:
            print(f"  失败: {err}")
            all_passed = False
        else:
            output, perr = process_input(content, output_format="text")
            if perr:
                print(f"  失败: {perr}")
                all_passed = False
            else:
                assert "你好世界" in output, "文件内容应被解析"
                print("  通过")
        os.unlink(tmp_path)
    except Exception as e:
        print(f"  失败: {e}")
        all_passed = False

    # --- 汇总 ---
    print("\n" + "=" * 60)
    if all_passed:
        print("自检全部通过")
    else:
        print("自检存在失败项")
    print("=" * 60)
    return all_passed


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------
def main() -> int:
    """命令行入口"""
    parser = argparse.ArgumentParser(
        description="youtube-subtitles 视频字幕处理工具",
        epilog="示例: python scripts/main.py --input '00:01:23 你好' --keyword 你好"
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检（无需外部输入）"
    )
    parser.add_argument(
        "--input", "-i",
        type=str,
        help="输入内容（字幕文本或 URL）"
    )
    parser.add_argument(
        "--file", "-f",
        type=str,
        help="输入文件路径（如 .srt 文件）"
    )
    parser.add_argument(
        "--keyword", "-k",
        type=str,
        default=None,
        help="筛选关键词"
    )
    parser.add_argument(
        "--format", "-fmt",
        type=str,
        choices=["text", "json", "srt"],
        default="text",
        help="输出格式 (默认: text)"
    )
    parser.add_argument(
        "--batch", "-b",
        action="store_true",
        help="批量模式（从 stdin 读取多行，每行一个输入）"
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        return 0 if run_selftest() else 1

    # 收集输入
    content = None
    input_source = None

    if args.file:
        content, err = read_file(args.file)
        if err:
            print(f"错误 {err}: {content}", file=sys.stderr)
            return 1
        input_source = args.file
    elif args.input:
        # 检查是否为 URL
        if args.input.startswith(("http://", "https://")):
            valid, msg = validate_url(args.input)
            if not valid:
                print(f"错误 {ERR_URL_INVALID}: {msg}", file=sys.stderr)
                return 1
            # 本实现不访问网络，提示用户
            print(f"错误 {ERR_OUT_OF_SCOPE}: 本工具不访问网络，请下载字幕文件后使用 --file 参数", file=sys.stderr)
            return 1
        content = args.input
        input_source = "命令行输入"
    else:
        # 从 stdin 读取
        print("请输入字幕内容（Ctrl+D 结束）:", file=sys.stderr)
        content = sys.stdin.read().strip()
        if not content:
            print(f"错误 {ERR_INPUT_EMPTY}: 请提供待处理的内容", file=sys.stderr)
            return 1
        input_source = "标准输入"

    # 批量模式
    if args.batch:
        items = [line for line in content.splitlines() if line.strip()]
        output, err = process_batch(items, args.keyword, args.format)
    else:
        output, err = process_input(content, args.keyword, args.format)

    if err:
        print(f"错误 {err}: {output}", file=sys.stderr)
        return 1

    print(output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
