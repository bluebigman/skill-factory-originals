#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py - YouTube Transcript API Sharp (clean-room implementation)

依据功能规格独立实现，不复制任何既有代码。
提供字幕数据解析、结构化输出、批量处理与离线自检功能。
"""

import argparse
import json
import re
import sys
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 错误码定义
# ============================================================
ERROR_CODES = {
    "E001": "输入数据为空或格式无效",
    "E002": "无法从输入中识别视频ID",
    "E003": "字幕数据缺少必要字段",
    "E004": "时间戳格式无法解析",
    "E005": "批量输入格式错误",
    "E006": "JSON序列化失败",
    "E007": "语言代码无效",
    "E008": "置信度标注参数无效",
    "E009": "输入类型不受支持",
    "E010": "内部逻辑错误",
}


def _fail(code: str, message: Optional[str] = None) -> None:
    """抛出带错误码的异常"""
    msg = message or ERROR_CODES.get(code, "未知错误")
    raise RuntimeError(f"[{code}] {msg}")


# ============================================================
# 核心数据结构与常量
# ============================================================

# 支持的语言代码集合（宽松校验用）
SUPPORTED_LANGS = {"en", "zh", "zh-Hans", "zh-Hant", "ja", "ko", "es", "fr", "de", "ru", "pt", "it"}

# 置信度等级
CONFIDENCE_LEVELS = ("high", "medium", "low")


class TranscriptSegment:
    """单条字幕分段"""

    def __init__(self, start: float, duration: float, text: str):
        self.start = start
        self.duration = duration
        self.text = text

    def to_dict(self) -> Dict[str, Any]:
        return {
            "start": round(self.start, 3),
            "duration": round(self.duration, 3),
            "text": self.text,
        }


class TranscriptData:
    """解析后的完整转录数据"""

    def __init__(
        self,
        video_id: str,
        language: str,
        segments: List[TranscriptSegment],
        source_type: str = "unknown",
    ):
        self.video_id = video_id
        self.language = language
        self.segments = segments
        self.source_type = source_type

    def to_dict(self) -> Dict[str, Any]:
        return {
            "video_id": self.video_id,
            "language": self.language,
            "source_type": self.source_type,
            "segment_count": len(self.segments),
            "segments": [seg.to_dict() for seg in self.segments],
        }


# ============================================================
# 工具函数
# ============================================================

def _extract_video_id(url_or_text: str) -> Optional[str]:
    """从URL或文本中提取YouTube视频ID"""
    if not url_or_text:
        return None

    # 常见URL模式
    patterns = [
        r"(?:v=|/v/|youtu\.be/|/embed/|/shorts/)([A-Za-z0-9_-]{11})",
        r"^([A-Za-z0-9_-]{11})$",
    ]
    for pat in patterns:
        m = re.search(pat, url_or_text)
        if m:
            return m.group(1)

    # 宽松匹配：11位字符组合
    m = re.search(r"\b([A-Za-z0-9_-]{11})\b", url_or_text)
    if m:
        return m.group(1)
    return None


def _parse_timestamp(value: Any) -> Optional[float]:
    """解析时间戳为秒数（浮点）"""
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        value = value.strip()
        # 替换逗号为点（支持SRT格式的毫秒分隔符）
        value = value.replace(",", ".")
        # 支持 "HH:MM:SS.mmm"、"MM:SS.mmm"、"SS.mmm"、"SS"
        parts = value.split(":")
        try:
            if len(parts) == 3:
                return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
            elif len(parts) == 2:
                return int(parts[0]) * 60 + float(parts[1])
            elif len(parts) == 1:
                return float(parts[0])
        except (ValueError, TypeError):
            return None
    return None


def _validate_language(lang: str) -> str:
    """校验语言代码，返回规范化结果"""
    if not lang:
        _fail("E007", "语言代码不能为空")
    lang_norm = lang.strip().lower()
    # 宽松校验：仅检查基本格式
    if not re.match(r"^[a-z]{2,3}(-[A-Za-z]{2,4})?$", lang_norm):
        _fail("E007", f"语言代码格式无效: {lang}")
    return lang_norm


def _check_confidence(level: str) -> str:
    """校验置信度等级"""
    if level not in CONFIDENCE_LEVELS:
        _fail("E008", f"置信度等级必须是 {CONFIDENCE_LEVELS} 之一")
    return level


# ============================================================
# 解析器实现
# ============================================================

def parse_transcript_data(raw_data: Any) -> TranscriptData:
    """
    解析输入数据为 TranscriptData 对象。

    支持的输入格式：
    1. 字典：{"video_id": str, "language": str, "segments": [{"start": float, "duration": float, "text": str}]}
    2. JSON字符串（同上结构）
    3. 列表：分段列表，自动推断video_id和language
    """
    if raw_data is None:
        _fail("E001")

    # 如果是字符串，尝试JSON解析
    if isinstance(raw_data, str):
        try:
            raw_data = json.loads(raw_data)
        except json.JSONDecodeError:
            _fail("E001", "字符串不是有效JSON")

    # 处理列表格式
    if isinstance(raw_data, list):
        if not raw_data:
            _fail("E001", "分段列表为空")
        segments = []
        for item in raw_data:
            if not isinstance(item, dict):
                _fail("E003", f"分段项必须是字典: {item}")
            start = _parse_timestamp(item.get("start"))
            duration = _parse_timestamp(item.get("duration", 0))
            text = str(item.get("text", "")).strip()
            if start is None or duration is None:
                _fail("E004", f"时间戳解析失败: {item}")
            segments.append(TranscriptSegment(start, duration, text))
        return TranscriptData(
            video_id="unknown",
            language="en",
            segments=segments,
            source_type="list",
        )

    # 处理字典格式
    if isinstance(raw_data, dict):
        if "segments" not in raw_data:
            _fail("E003", "缺少segments字段")
        segments_raw = raw_data["segments"]
        if not isinstance(segments_raw, list) or not segments_raw:
            _fail("E003", "segments必须是非空列表")

        # 视频ID
        video_id = raw_data.get("video_id") or raw_data.get("id")
        if not video_id:
            # 尝试从其他字段提取
            url = raw_data.get("url") or raw_data.get("source_url")
            if url:
                video_id = _extract_video_id(str(url))
        if not video_id:
            _fail("E002", "无法识别视频ID")

        # 语言
        language = raw_data.get("language") or raw_data.get("lang") or "en"
        language = _validate_language(str(language))

        # 分段
        segments = []
        for item in segments_raw:
            if not isinstance(item, dict):
                _fail("E003", f"分段项必须是字典: {item}")
            start = _parse_timestamp(item.get("start"))
            duration = _parse_timestamp(item.get("duration", item.get("dur", 0)))
            text = str(item.get("text", item.get("content", ""))).strip()
            if start is None or duration is None:
                _fail("E004", f"时间戳解析失败: {item}")
            segments.append(TranscriptSegment(start, duration, text))

        # 按开始时间排序
        segments.sort(key=lambda s: s.start)

        return TranscriptData(
            video_id=str(video_id),
            language=language,
            segments=segments,
            source_type="dict",
        )

    _fail("E009", f"不支持的输入类型: {type(raw_data)}")


def parse_transcript_file(file_path: str) -> TranscriptData:
    """从文件解析字幕数据"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except OSError as e:
        _fail("E001", f"文件读取失败: {e}")

    # 尝试JSON解析
    try:
        return parse_transcript_data(content)
    except RuntimeError:
        # 尝试SRT/VTT格式
        return _parse_srt_vtt(content)


def _parse_srt_vtt(content: str) -> TranscriptData:
    """解析SRT或VTT格式的字幕"""
    if not content or not content.strip():
        _fail("E001", "字幕内容为空")

    lines = content.strip().splitlines()
    segments = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        # 跳过空行和序号
        if not line or line.isdigit():
            i += 1
            continue
        # 时间戳行
        if "-->" in line:
            time_part = line.split("-->")[0].strip()
            start = _parse_timestamp(time_part)
            if start is None:
                _fail("E004", f"时间戳解析失败: {time_part}")
            # 收集文本（直到空行或下一个时间戳）
            text_parts = []
            i += 1
            while i < len(lines) and lines[i].strip() and "-->" not in lines[i]:
                text_parts.append(lines[i].strip())
                i += 1
            text = " ".join(text_parts)
            # 估算duration（简单处理）
            duration = 2.0 if not text_parts else max(1.0, len(text) * 0.3)
            segments.append(TranscriptSegment(start, duration, text))
            continue
        i += 1

    if not segments:
        _fail("E003", "无法从字幕内容中解析出分段")

    return TranscriptData(
        video_id="unknown",
        language="en",
        segments=segments,
        source_type="srt/vtt",
    )


# ============================================================
# 批量处理
# ============================================================

def batch_process(items: List[Any]) -> Dict[str, Any]:
    """
    批量处理多个字幕数据源。

    输入：列表，每个元素可以是dict/str/文件路径
    输出：合并的批量结果
    """
    if not isinstance(items, list) or not items:
        _fail("E005", "批量输入必须是非空列表")

    results = []
    for idx, item in enumerate(items):
        try:
            if isinstance(item, str) and (item.endswith(".json") or item.endswith(".srt") or item.endswith(".vtt")):
                # 尝试作为文件路径
                try:
                    data = parse_transcript_file(item)
                except RuntimeError:
                    # 不是文件，当作原始数据
                    data = parse_transcript_data(item)
            else:
                data = parse_transcript_data(item)
            results.append(data.to_dict())
        except RuntimeError as e:
            results.append({
                "index": idx,
                "error": str(e),
                "success": False,
            })

    return {
        "batch_size": len(items),
        "success_count": sum(1 for r in results if "error" not in r),
        "results": results,
    }


# ============================================================
# 结构化输出
# ============================================================

def to_json(data: TranscriptData, pretty: bool = True) -> str:
    """将TranscriptData转换为JSON字符串"""
    try:
        if pretty:
            return json.dumps(data.to_dict(), ensure_ascii=False, indent=2)
        return json.dumps(data.to_dict(), ensure_ascii=False)
    except (TypeError, ValueError) as e:
        _fail("E006", f"JSON序列化失败: {e}")


def summarize(data: TranscriptData) -> Dict[str, Any]:
    """生成摘要信息"""
    if not data.segments:
        return {
            "video_id": data.video_id,
            "language": data.language,
            "segment_count": 0,
            "total_duration": 0.0,
            "total_chars": 0,
        }

    total_duration = sum(seg.duration for seg in data.segments)
    total_chars = sum(len(seg.text) for seg in data.segments)
    return {
        "video_id": data.video_id,
        "language": data.language,
        "segment_count": len(data.segments),
        "total_duration": round(total_duration, 2),
        "total_chars": total_chars,
    }


# ============================================================
# 置信度标注
# ============================================================

def annotate_confidence(data: TranscriptData, level: str = "medium") -> Dict[str, Any]:
    """为转录结果添加置信度标注"""
    level = _check_confidence(level)
    result = data.to_dict()
    result["confidence"] = {
        "level": level,
        "note": "由本地解析器自动标注",
    }
    return result


# ============================================================
# 命令行入口
# ============================================================

def _run_selftest() -> int:
    """离线自检核心逻辑（使用内置硬编码数据）"""
    print("开始自检...")

    # 测试数据1：标准字典格式
    sample_dict = {
        "video_id": "dQw4w9WgXcQ",
        "language": "en",
        "segments": [
            {"start": 0.5, "duration": 2.0, "text": "Hello world"},
            {"start": 3.0, "duration": 1.5, "text": "This is a test"},
            {"start": 5.0, "duration": 2.5, "text": "YouTube transcript"},
        ],
    }

    # 测试1：解析字典
    try:
        data = parse_transcript_data(sample_dict)
        assert data.video_id == "dQw4w9WgXcQ", "视频ID解析失败"
        assert data.language == "en", "语言解析失败"
        assert len(data.segments) == 3, "分段数量错误"
        assert data.segments[0].start < data.segments[1].start, "排序错误"
        print("[PASS] 字典解析")
    except AssertionError as e:
        print(f"[FAIL] 字典解析: {e}")
        return 1
    except RuntimeError as e:
        print(f"[FAIL] 字典解析异常: {e}")
        return 1

    # 测试2：JSON字符串解析
    try:
        json_str = json.dumps(sample_dict)
        data2 = parse_transcript_data(json_str)
        assert data2.video_id == "dQw4w9WgXcQ", "JSON解析视频ID失败"
        assert len(data2.segments) == 3, "JSON解析分段数量错误"
        print("[PASS] JSON字符串解析")
    except (AssertionError, RuntimeError) as e:
        print(f"[FAIL] JSON字符串解析: {e}")
        return 1

    # 测试3：时间戳格式解析
    try:
        assert _parse_timestamp("00:01:30.500") == 90.5, "HH:MM:SS格式解析失败"
        assert _parse_timestamp("01:30.5") == 90.5, "MM:SS格式解析失败"
        assert _parse_timestamp("90.5") == 90.5, "秒数格式解析失败"
        assert _parse_timestamp(90) == 90.0, "数字格式解析失败"
        assert _parse_timestamp("00:00:01,000") == 1.0, "SRT格式时间戳解析失败"
        print("[PASS] 时间戳解析")
    except AssertionError as e:
        print(f"[FAIL] 时间戳解析: {e}")
        return 1

    # 测试4：视频ID提取
    try:
        urls = [
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "https://youtu.be/dQw4w9WgXcQ",
            "https://www.youtube.com/embed/dQw4w9WgXcQ",
            "dQw4w9WgXcQ",
        ]
        for url in urls:
            vid = _extract_video_id(url)
            assert vid == "dQw4w9WgXcQ", f"URL提取失败: {url}"
        print("[PASS] 视频ID提取")
    except AssertionError as e:
        print(f"[FAIL] 视频ID提取: {e}")
        return 1

    # 测试5：批量处理
    try:
        batch_items = [
            sample_dict,
            {"video_id": "abc123XYZ789", "language": "zh", "segments": [
                {"start": 0, "duration": 1, "text": "测试"},
            ]},
        ]
        batch_result = batch_process(batch_items)
        assert batch_result["batch_size"] == 2, "批量大小错误"
        assert batch_result["success_count"] == 2, "批量成功数错误"
        assert len(batch_result["results"]) == 2, "批量结果数量错误"
        print("[PASS] 批量处理")
    except (AssertionError, RuntimeError) as e:
        print(f"[FAIL] 批量处理: {e}")
        return 1

    # 测试6：结构化输出
    try:
        data3 = parse_transcript_data(sample_dict)
        json_out = to_json(data3)
        parsed_back = json.loads(json_out)
        assert parsed_back["video_id"] == "dQw4w9WgXcQ", "JSON输出视频ID错误"
        assert parsed_back["segment_count"] == 3, "JSON输出分段数量错误"
        assert "segments" in parsed_back, "JSON输出缺少segments字段"

        summary = summarize(data3)
        assert summary["segment_count"] == 3, "摘要分段数量错误"
        assert summary["total_chars"] > 0, "摘要字符数错误"
        print("[PASS] 结构化输出与摘要")
    except (AssertionError, RuntimeError) as e:
        print(f"[FAIL] 结构化输出与摘要: {e}")
        return 1

    # 测试7：置信度标注
    try:
        annotated = annotate_confidence(data3, "high")
        assert annotated["confidence"]["level"] == "high", "置信度等级错误"
        annotated_low = annotate_confidence(data3, "low")
        assert annotated_low["confidence"]["level"] == "low", "置信度等级错误"
        print("[PASS] 置信度标注")
    except (AssertionError, RuntimeError) as e:
        print(f"[FAIL] 置信度标注: {e}")
        return 1

    # 测试8：错误处理
    try:
        parse_transcript_data(None)
        print("[FAIL] 错误处理：应抛出E001")
        return 1
    except RuntimeError as e:
        assert "E001" in str(e), f"错误码不正确: {e}"
        print("[PASS] 错误处理（E001）")

    try:
        parse_transcript_data({"segments": []})
        print("[FAIL] 错误处理：应抛出E003")
        return 1
    except RuntimeError as e:
        assert "E003" in str(e), f"错误码不正确: {e}"
        print("[PASS] 错误处理（E003）")

    # 测试9：SRT/VTT解析（简化）
    try:
        srt_content = """1
00:00:01,000 --> 00:00:03,000
Hello from SRT

2
00:00:04,000 --> 00:00:06,000
Second line
"""
        data_srt = _parse_srt_vtt(srt_content)
        assert len(data_srt.segments) == 2, "SRT解析分段数量错误"
        assert data_srt.segments[0].text == "Hello from SRT", "SRT解析文本错误"
        assert data_srt.segments[0].start == 1.0, "SRT解析开始时间错误"
        print("[PASS] SRT解析")
    except (AssertionError, RuntimeError) as e:
        print(f"[FAIL] SRT解析: {e}")
        return 1

    print("\n全部自检通过！")
    return 0


def main() -> int:
    """主入口"""
    parser = argparse.ArgumentParser(
        description="YouTube字幕解析工具（clean-room实现）",
        epilog="示例: python main.py --input data.json --output result.json",
    )
    parser.add_argument("--input", "-i", help="输入文件路径（JSON/SRT/VTT）或JSON字符串")
    parser.add_argument("--output", "-o", help="输出文件路径（默认为stdout）")
    parser.add_argument("--batch", "-b", help="批量处理文件（每行一个输入）")
    parser.add_argument("--lang", help="覆盖语言代码")
    parser.add_argument("--video-id", help="覆盖视频ID")
    parser.add_argument("--summary", action="store_true", help="输出摘要信息")
    parser.add_argument("--confidence", choices=CONFIDENCE_LEVELS, help="添加置信度标注")
    parser.add_argument("--pretty", action="store_true", default=True, help="美化JSON输出")
    parser.add_argument("--selftest", action="store_true", help="运行离线自检")

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        return _run_selftest()

    # 无输入参数
    if not args.input and not args.batch:
        parser.print_help()
        return 0

    try:
        # 批量模式
        if args.batch:
            try:
                with open(args.batch, "r", encoding="utf-8") as f:
                    lines = [line.strip() for line in f if line.strip()]
            except OSError as e:
                print(f"错误: [E001] 批量文件读取失败: {e}", file=sys.stderr)
                return 1

            result = batch_process(lines)
            output = json.dumps(result, ensure_ascii=False, indent=2 if args.pretty else None)
        else:
            # 单文件/字符串模式
            data = parse_transcript_file(args.input) if args.input.endswith((".json", ".srt", ".vtt")) else parse_transcript_data(args.input)

            # 覆盖字段
            if args.lang:
                data.language = _validate_language(args.lang)
            if args.video_id:
                data.video_id = args.video_id

            # 输出模式
            if args.summary:
                output = json.dumps(summarize(data), ensure_ascii=False, indent=2 if args.pretty else None)
            elif args.confidence:
                output = json.dumps(annotate_confidence(data, args.confidence), ensure_ascii=False, indent=2 if args.pretty else None)
            else:
                output = to_json(data, pretty=args.pretty)

        # 输出
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(output)
        else:
            print(output)

        return 0

    except RuntimeError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"错误: [E010] 未预期异常: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
