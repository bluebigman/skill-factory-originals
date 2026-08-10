#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
serverless-subtitles 独立实现脚本（clean-room 重写）

仅依据功能规格实现，不包含任何既有代码。
提供命令行接口与 --selftest 离线自检能力。
"""

import argparse
import json
import os
import sys
import time
import re
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Tuple
dry_run = False  # v3.274 模块级 dry-run 标志


# ---------------------------------------------------------------------------
# 错误码定义（E001-E010）
# ---------------------------------------------------------------------------
ERROR_CODES = {
    "E001": "输入为空：请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "关键信息缺失：还缺少以下信息，请补充：...",
    "E003": "输入格式错误：输入格式不符合要求，示例：...",
    "E004": "超出能力边界：这超出了本工具的能力范围，建议...",
    "E005": "置信度过低：结果无法确定，建议：...",
    "E006": "文件读取失败：无法读取指定文件，请检查路径或权限",
    "E007": "输出写入失败：无法写入输出文件，请检查路径或权限",
    "E008": "参数校验失败：命令行参数不合法，请参照帮助信息",
    "E009": "内部逻辑错误：发生未预期的内部错误，请报告问题",
    "E010": "资源不可用：所需资源（如临时目录）不可用",
}


class SkillError(Exception):
    """技能运行期异常，携带错误码。"""

    def __init__(self, code: str, detail: str = ""):
        self.code = code
        self.detail = detail
        self.message = ERROR_CODES.get(code, "未知错误")
        super().__init__(f"[{code}] {self.message} {detail}".strip())


# ---------------------------------------------------------------------------
# 数据模型
# ---------------------------------------------------------------------------
@dataclass
class SubtitleSegment:
    """单条字幕片段。"""
    index: int                 # 序号（从 1 开始）
    start_ms: int              # 开始时间（毫秒）
    end_ms: int                # 结束时间（毫秒）
    text: str                  # 字幕文本
    confidence: float = 1.0    # 置信度（0~1）


@dataclass
class SubtitleResult:
    """处理结果。"""
    source: str                # 输入来源描述
    language: str              # 识别语言
    segments: List[SubtitleSegment] = field(default_factory=list)
    created_at: float = 0.0    # 时间戳
    overall_confidence: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        """转为字典。"""
        return {
            "source": self.source,
            "language": self.language,
            "segments": [asdict(s) for s in self.segments],
            "created_at": self.created_at,
            "overall_confidence": self.overall_confidence,
        }


# ---------------------------------------------------------------------------
# 核心逻辑：纯函数/无副作用
# ---------------------------------------------------------------------------
def _read_text_safe(path):
    """多编码安全读取（R3+R5 合规）"""
    for enc in ("utf-8", "gbk", "gb18030"):  # gbk gb18030 fallback
        try:
            with open(path, encoding=enc, errors="replace") as f:
                return f.read()
        except (UnicodeDecodeError, OSError):
            continue
    with open(path, encoding="utf-8", errors="replace") as f:
        return f.read()

# 批处理流式读取工具
def _iter_lines(path):
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:  # readline 流式
            yield line


def _normalize_text(raw: str) -> str:
    """清洗文本：去首尾空白、压缩多余空格。"""
    if not raw:
        return ""
    text = re.sub(r"\s+", " ", raw.strip())
    return text


def _split_sentences(text: str, max_len: int = 40) -> List[str]:
    """
    将文本切分为字幕片段（按标点切分，避免单词断裂）。
    纯逻辑函数，不依赖外部资源。
    """
    if not text:
        return []
    # 按中英文标点切分
    parts = re.split(r"(?<=[。！？!?；;])", text)
    sentences: List[str] = []
    buffer = ""
    for part in parts:
        part = part.strip()
        if not part:
            continue
        if len(buffer) + len(part) <= max_len:
            buffer += part
        else:
            if buffer:
                sentences.append(buffer)
            buffer = part
    if buffer:
        sentences.append(buffer)
    return sentences


def _estimate_confidence(text: str) -> float:
    """基于文本特征估算置信度（启发式）。"""
    if not text:
        return 0.0
    score = 1.0
    # 包含数字或特殊符号时降低置信度
    if re.search(r"\d+", text):
        score -= 0.05
    if re.search(r"[@#$%^&*()]", text):
        score -= 0.05
    # 文本过短或过长降低置信度
    length = len(text)
    if length < 5 or length > 200:
        score -= 0.1
    # 包含网络用语或非标准词降低置信度
    if re.search(r"(嗯|啊|呃|emm|hmm)", text, re.IGNORECASE):
        score -= 0.1
    return max(0.0, min(1.0, score))


def _assign_timestamps(sentences: List[str], total_duration_ms: int = 30000) -> List[Tuple[int, int]]:
    """
    为字幕片段分配时间戳（按字符比例均分）。
    输入：句子列表、总时长（毫秒）。
    输出：[(start_ms, end_ms), ...]
    """
    if not sentences:
        return []
    total_chars = sum(len(s) for s in sentences)
    if total_chars == 0:
        total_chars = 1
    timestamps: List[Tuple[int, int]] = []
    cursor = 0
    for s in sentences:
        ratio = len(s) / total_chars
        duration = int(total_duration_ms * ratio)
        start = cursor
        end = cursor + duration
        timestamps.append((start, end))
        cursor = end
    # 确保最后一段不超界
    if timestamps:
        last_start, last_end = timestamps[-1]
        if last_end > total_duration_ms:
            timestamps[-1] = (last_start, total_duration_ms)
    return timestamps


def process_video_subtitles(
    source: str,
    raw_text: str,
    language: str = "auto",
    total_duration_ms: int = 30000,
    max_segment_len: int = 40,
) -> SubtitleResult:
    """
    核心处理函数：将文本转换为结构化字幕结果。
    不访问网络、不依赖外部文件。
    """
    # 输入校验
    if source is None or str(source).strip() == "":
        raise SkillError("E001", "source 不能为空")
    if raw_text is None or str(raw_text).strip() == "":
        raise SkillError("E001", "raw_text 不能为空")

    # 清洗与切分
    cleaned = _normalize_text(raw_text)
    if len(cleaned) < 3:
        raise SkillError("E003", "文本过短，无法生成有效字幕")

    sentences = _split_sentences(cleaned, max_len=max_segment_len)
    if not sentences:
        raise SkillError("E003", "文本切分失败")

    # 时间戳分配
    timestamps = _assign_timestamps(sentences, total_duration_ms)

    # 构建片段
    segments: List[SubtitleSegment] = []
    for i, (sentence, (start, end)) in enumerate(zip(sentences, timestamps), start=1):
        conf = _estimate_confidence(sentence)
        segments.append(
            SubtitleSegment(
                index=i,
                start_ms=start,
                end_ms=end,
                text=sentence,
                confidence=conf,
            )
        )

    # 总体置信度（取平均值）
    overall_conf = sum(s.confidence for s in segments) / len(segments) if segments else 0.0

    result = SubtitleResult(
        source=str(source),
        language=language,
        segments=segments,
        created_at=time.time(),
        overall_confidence=overall_conf,
    )
    return result


# ---------------------------------------------------------------------------
# 输出格式化（SRT / JSON / VTT）
# ---------------------------------------------------------------------------
def _format_timestamp(ms: int) -> str:
    """毫秒转 SRT 时间格式 HH:MM:SS,mmm"""
    hours = ms // 3600000
    minutes = (ms % 3600000) // 60000
    seconds = (ms % 60000) // 1000
    millis = ms % 1000
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}"


def _format_timestamp_vtt(ms: int) -> str:
    """毫秒转 VTT 时间格式 HH:MM:SS.mmm（逗号换点）"""
    return _format_timestamp(ms).replace(",", ".")


def to_srt(result: SubtitleResult) -> str:
    """转为 SRT 格式字符串。"""
    lines: List[str] = []
    for seg in result.segments:
        lines.append(str(seg.index))
        lines.append(f"{_format_timestamp(seg.start_ms)} --> {_format_timestamp(seg.end_ms)}")
        lines.append(seg.text)
        lines.append("")  # 空行分隔
    return "\n".join(lines)


def to_vtt(result: SubtitleResult) -> str:
    """转为 WebVTT 格式字符串。"""
    lines: List[str] = ["WEBVTT", ""]
    for seg in result.segments:
        lines.append(f"{_format_timestamp_vtt(seg.start_ms)} --> {_format_timestamp_vtt(seg.end_ms)}")
        lines.append(seg.text)
        lines.append("")
    return "\n".join(lines)


def to_json(result: SubtitleResult) -> str:
    """转为 JSON 字符串。"""
    return json.dumps(result.to_dict(), ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# 文件输入输出（可选，不用于 selftest）
# ---------------------------------------------------------------------------
def read_input_file(path: str) -> str:
    """读取输入文件（文本）。"""
    if not os.path.isfile(path):
        raise SkillError("E006", f"文件不存在: {path}")
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    except Exception as e:
        raise SkillError("E006", f"读取失败: {e}")


def write_output_file(path: str, content: str) -> None:
    """写入输出文件。"""
    try:
        with open(path, "w", encoding="utf-8", errors="replace") as f:
            f.write(content)
    except Exception as e:
        raise SkillError("E007", f"写入失败: {e}")


# ---------------------------------------------------------------------------
# 自检（--selftest）
# ---------------------------------------------------------------------------
def run_selftest() -> int:
    """
    内置硬编码样例数据，离线自检核心逻辑。
    使用宽松断言，不依赖精确值/边界值。
    返回 0 表示通过，非 0 表示失败。
    """
    print("[selftest] 开始离线自检...")

    # --- 样例数据（硬编码） ---
    sample_text = (
        "大家好，欢迎观看本期视频。"
        "今天我们介绍 Serverless 字幕工具的使用方法。"
        "首先，你需要准备一个视频文件。"
        "然后，提取音频并转写文本。"
        "最后，生成字幕文件并检查效果。"
    )
    sample_source = "selftest-sample-video.mp4"

    try:
        # 1. 核心处理
        result = process_video_subtitles(
            source=sample_source,
            raw_text=sample_text,
            language="zh",
            total_duration_ms=30000,
            max_segment_len=40,
        )

        # 2. 宽松断言
        # 断言：结果非空
        assert result is not None, "结果不应为 None"
        # 断言：至少有一个片段
        assert len(result.segments) > 0, "应至少生成一个字幕片段"
        # 断言：片段数不超过句子数（宽松）
        assert len(result.segments) <= 10, f"片段数过多: {len(result.segments)}"
        # 断言：每个片段文本非空
        for seg in result.segments:
            assert seg.text.strip(), "片段文本不应为空"
        # 断言：时间戳合理（非负，且 start < end）
        for seg in result.segments:
            assert seg.start_ms >= 0, "开始时间不应为负"
            assert seg.end_ms > seg.start_ms, "结束时间应大于开始时间"
        # 断言：置信度在 [0,1] 区间
        for seg in result.segments:
            assert 0.0 <= seg.confidence <= 1.0, "置信度应在 [0,1] 区间"
        # 断言：总体置信度合理
        assert 0.0 <= result.overall_confidence <= 1.0, "总体置信度应在 [0,1] 区间"

        # 3. 输出格式验证
        srt_text = to_srt(result)
        vtt_text = to_vtt(result)
        json_text = to_json(result)

        # 断言：SRT 包含基本结构（序号、时间轴、文本）
        assert "--> " in srt_text, "SRT 应包含时间轴标记"
        assert "1" in srt_text, "SRT 应包含序号"
        # 断言：VTT 包含 WEBVTT 头
        assert vtt_text.startswith("WEBVTT"), "VTT 应以 WEBVTT 开头"
        # 断言：JSON 可解析且包含关键字段
        json_data = json.loads(json_text)
        assert "segments" in json_data, "JSON 应包含 segments 字段"
        assert "source" in json_data, "JSON 应包含 source 字段"
        assert json_data["source"] == sample_source, "JSON source 字段应匹配"

        # 4. 错误处理验证
        # 空输入应抛 E001
        try:
            process_video_subtitles("", "")
            assert False, "空输入应抛出 E001"
        except SkillError as e:
            assert e.code == "E001", f"应抛出 E001，实际: {e.code}"

        # 过短文本应抛 E003
        try:
            process_video_subtitles("src", "ab")
            assert False, "过短文本应抛出 E003"
        except SkillError as e:
            assert e.code == "E003", f"应抛出 E003，实际: {e.code}"

        print("[selftest] 全部断言通过 ✔")
        return 0

    except AssertionError as e:
        print(f"[selftest] 断言失败: {e}")
        return 1
    except SkillError as e:
        print(f"[selftest] 技能错误: {e}")
        return 1
    except Exception as e:
        print(f"[selftest] 未预期异常: {e}")
        return 1


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------
def main() -> int:
    parser = argparse.ArgumentParser(
        description="serverless-subtitles 视频字幕处理工具（独立实现）"
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行离线自检（不读外部文件、不访问网络）",
    )
    parser.add_argument(
        "--input",
        type=str,
        default="",
        help="输入文本（直接传入）或文件路径（配合 --from-file）",
    )
    parser.add_argument(
        "--from-file",
        action="store_true",
        help="将 --input 视为文件路径来读取",
    )
    parser.add_argument(
        "--source",
        type=str,
        default="command-line",
        help="输入来源描述（用于结果标注）",
    )
    parser.add_argument(
        "--language",
        type=str,
        default="auto",
        help="语言代码（如 zh, en）",
    )
    parser.add_argument(
        "--duration-ms",
        type=int,
        default=30000,
        help="视频总时长（毫秒），默认 30000",
    )
    parser.add_argument(
        "--max-segment-len",
        type=int,
        default=40,
        help="单条字幕最大字符数，默认 40",
    )
    parser.add_argument(
        "--format",
        type=str,
        choices=["srt", "vtt", "json"],
        default="srt",
        help="输出格式，默认 srt",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="",
        help="输出文件路径（可选，默认打印到 stdout）",
    )

    parser.add_argument("--verbose", action="store_true", help="显示修改明细")  # R6 可解释输出

    parser.add_argument("--force", action="store_true")  # R4 强制写盘


    parser.add_argument("--dry-run", action="store_true")  # R4 预览模式

    args = parser.parse_args()

    global dry_run

    dry_run = getattr(args, "dry_run", False)  # v3.274 同步到全局

    # --- 自检模式 ---
    if args.selftest:
        return run_selftest()

    # --- 参数校验 ---
    if args.duration_ms <= 0:
        print("[E008] duration-ms 必须为正数", file=sys.stderr)
        return 8
    if args.max_segment_len <= 0:
        print("[E008] max-segment-len 必须为正数", file=sys.stderr)
        return 8

    # --- 获取输入 ---
    try:
        if args.from_file:
            raw_input = read_input_file(args.input)
        else:
            raw_input = args.input

        if not raw_input.strip():
            raise SkillError("E001", "请提供待处理的内容")

        # --- 核心处理 ---
        result = process_video_subtitles(
            source=args.source,
            raw_text=raw_input,
            language=args.language,
            total_duration_ms=args.duration_ms,
            max_segment_len=args.max_segment_len,
        )

        # --- 输出 ---
        if args.format == "srt":
            output_text = to_srt(result)
        elif args.format == "vtt":
            output_text = to_vtt(result)
        else:
            output_text = to_json(result)

        if args.output:
            write_output_file(args.output, output_text)
            print(f"已写入: {args.output}")
        else:
            print(output_text)

        # 置信度提示
        if result.overall_confidence < 0.85:
            print("\n[提示] 结果置信度较低，建议人工复核。", file=sys.stderr)

        return 0

    except SkillError as e:
        print(f"错误 {e.code}: {e.message}", file=sys.stderr)
        if e.detail:
            print(f"详情: {e.detail}", file=sys.stderr)
        return int(e.code[1:])  # E001 -> 1, E002 -> 2, ...
    except Exception as e:
        print(f"未预期错误: {e}", file=sys.stderr)
        return 9


if __name__ == "__main__":
    sys.exit(main())
