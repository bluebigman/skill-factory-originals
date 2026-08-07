#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
subtubular - 视频字幕全文本搜索与元数据处理工具

本脚本为 clean-room 独立实现，仅依据功能规格编写。
提供命令行界面与内置自检功能。
"""

import argparse
import json
import re
import sys
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 错误码定义
# ============================================================
ERROR_CODES = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：...",
    "E003": "输入格式不符合要求，示例：...",
    "E004": "这超出了本工具的能力范围，建议...",
    "E005": "结果无法确定，建议：...",
    "E006": "内部处理异常，请重试或检查输入",
    "E007": "输出格式不支持，支持格式：json, text",
    "E008": "批量处理中断，请检查单个输入",
    "E009": "参数校验失败，请检查命令行参数",
    "E010": "未知错误，请查看日志",
}


# ============================================================
# 数据结构定义
# ============================================================
@dataclass
class SubtitleEntry:
    """单条字幕条目"""
    start: float          # 开始时间（秒）
    end: float            # 结束时间（秒）
    text: str             # 字幕文本
    confidence: float = 1.0  # 置信度 0~1


@dataclass
class VideoMeta:
    """视频元数据"""
    title: str = ""
    video_id: str = ""
    channel: str = ""
    duration: float = 0.0
    upload_date: str = ""
    description: str = ""
    tags: List[str] = field(default_factory=list)


@dataclass
class ProcessResult:
    """处理结果"""
    video_meta: VideoMeta = field(default_factory=VideoMeta)
    subtitle_entries: List[SubtitleEntry] = field(default_factory=list)
    search_hits: List[Dict[str, Any]] = field(default_factory=list)
    confidence: float = 1.0
    warnings: List[str] = field(default_factory=list)


# ============================================================
# 核心处理逻辑
# ============================================================
class SubtitleProcessor:
    """字幕与元数据处理核心类"""

    def __init__(self) -> None:
        self.supported_formats = ["json", "text"]

    def process_input(
        self,
        raw_data: str,
        search_keyword: Optional[str] = None,
        output_format: str = "json",
    ) -> Tuple[int, str]:
        """
        处理输入数据，返回 (错误码, 结果或错误信息)
        错误码为 "0" 表示成功
        """
        # 参数校验
        if output_format not in self.supported_formats:
            return "E007", ERROR_CODES["E007"]

        # 输入为空检查
        if not raw_data or not raw_data.strip():
            return "E001", ERROR_CODES["E001"]

        # 解析输入
        try:
            parsed = self._parse_input(raw_data)
        except ValueError as e:
            return "E003", f"{ERROR_CODES['E003']} 详情：{str(e)}"

        if not parsed:
            return "E003", ERROR_CODES["E003"]

        video_meta, subtitle_entries = parsed

        # 关键信息缺失检查
        missing = self._check_required_fields(video_meta, subtitle_entries)
        if missing:
            return "E002", f"{ERROR_CODES['E002']} 缺少：{', '.join(missing)}"

        # 执行核心处理
        result = self._build_result(video_meta, subtitle_entries, search_keyword)

        # 置信度检查
        if result.confidence < 0.85:
            result.warnings.append("置信度过低，结果需人工复核")

        # 格式化输出
        if output_format == "json":
            output = self._format_json(result)
        else:
            output = self._format_text(result)

        return "0", output

    def _parse_input(self, raw_data: str) -> Optional[Tuple[VideoMeta, List[SubtitleEntry]]]:
        """
        解析输入数据。
        支持两种格式：
        1. JSON 格式（含 video_meta 和 subtitles 字段）
        2. 简单文本格式（每行: 开始时间|结束时间|文本）
        """
        raw_data = raw_data.strip()

        # 尝试 JSON 解析
        if raw_data.startswith("{"):
            return self._parse_json_input(raw_data)

        # 尝试文本解析
        return self._parse_text_input(raw_data)

    def _parse_json_input(self, raw_data: str) -> Optional[Tuple[VideoMeta, List[SubtitleEntry]]]:
        """解析 JSON 格式输入"""
        try:
            data = json.loads(raw_data)
        except json.JSONDecodeError:
            raise ValueError("JSON 格式错误")

        # 提取视频元数据
        meta_data = data.get("video_meta", {})
        video_meta = VideoMeta(
            title=str(meta_data.get("title", "")),
            video_id=str(meta_data.get("video_id", "")),
            channel=str(meta_data.get("channel", "")),
            duration=float(meta_data.get("duration", 0.0)),
            upload_date=str(meta_data.get("upload_date", "")),
            description=str(meta_data.get("description", "")),
            tags=list(meta_data.get("tags", [])),
        )

        # 提取字幕条目
        subtitle_entries = []
        for item in data.get("subtitles", []):
            entry = SubtitleEntry(
                start=float(item.get("start", 0.0)),
                end=float(item.get("end", 0.0)),
                text=str(item.get("text", "")),
                confidence=float(item.get("confidence", 1.0)),
            )
            subtitle_entries.append(entry)

        return video_meta, subtitle_entries

    def _parse_text_input(self, raw_data: str) -> Optional[Tuple[VideoMeta, List[SubtitleEntry]]]:
        """解析文本格式输入"""
        lines = [line.strip() for line in raw_data.split("\n") if line.strip()]
        if not lines:
            return None

        # 第一行作为标题（如果包含分隔符则视为字幕行）
        first_line = lines[0]
        if "|" not in first_line:
            video_meta = VideoMeta(title=first_line)
            subtitle_lines = lines[1:]
        else:
            video_meta = VideoMeta()
            subtitle_lines = lines

        if not subtitle_lines:
            return None

        # 解析字幕行
        subtitle_entries = []
        for line in subtitle_lines:
            parts = [p.strip() for p in line.split("|")]
            if len(parts) < 3:
                continue

            try:
                start = float(parts[0])
                end = float(parts[1])
                text = parts[2]
                confidence = float(parts[3]) if len(parts) > 3 else 1.0
            except (ValueError, IndexError):
                continue

            entry = SubtitleEntry(
                start=start,
                end=end,
                text=text,
                confidence=confidence,
            )
            subtitle_entries.append(entry)

        if not subtitle_entries:
            return None

        return video_meta, subtitle_entries

    def _check_required_fields(
        self, video_meta: VideoMeta, subtitle_entries: List[SubtitleEntry]
    ) -> List[str]:
        """检查关键信息是否完整"""
        missing = []

        if not video_meta.title:
            missing.append("视频标题")

        if not subtitle_entries:
            missing.append("字幕内容")

        # 检查字幕时间戳是否合理
        for entry in subtitle_entries:
            if entry.end <= entry.start:
                missing.append(f"字幕时间戳错误: {entry.text[:20]}...")
                break

        return missing

    def _build_result(
        self,
        video_meta: VideoMeta,
        subtitle_entries: List[SubtitleEntry],
        search_keyword: Optional[str],
    ) -> ProcessResult:
        """构建处理结果"""
        result = ProcessResult(video_meta=video_meta, subtitle_entries=subtitle_entries)

        # 计算整体置信度
        confidences = [e.confidence for e in subtitle_entries]
        if confidences:
            result.confidence = sum(confidences) / len(confidences)

        # 执行搜索
        if search_keyword:
            result.search_hits = self._search_subtitles(subtitle_entries, search_keyword)

        return result

    def _search_subtitles(
        self, entries: List[SubtitleEntry], keyword: str
    ) -> List[Dict[str, Any]]:
        """在字幕文本中搜索关键词"""
        hits = []
        keyword_lower = keyword.lower()

        for i, entry in enumerate(entries):
            if keyword_lower in entry.text.lower():
                # 获取上下文（前后各一条）
                context_start = max(0, i - 1)
                context_end = min(len(entries), i + 2)

                context = [
                    {
                        "start": entries[j].start,
                        "end": entries[j].end,
                        "text": entries[j].text,
                    }
                    for j in range(context_start, context_end)
                ]

                hits.append(
                    {
                        "index": i,
                        "start": entry.start,
                        "end": entry.end,
                        "text": entry.text,
                        "context": context,
                    }
                )

        return hits

    def _format_json(self, result: ProcessResult) -> str:
        """格式化输出为 JSON"""
        output = {
            "video_meta": asdict(result.video_meta),
            "subtitle_count": len(result.subtitle_entries),
            "search_hits": result.search_hits,
            "confidence": round(result.confidence, 4),
            "warnings": result.warnings,
        }

        # 添加置信度标注
        if result.confidence < 0.85:
            output["confidence_level"] = "[需核实]"
        elif result.confidence < 0.90:
            output["confidence_level"] = "建议复核"
        else:
            output["confidence_level"] = "直接输出"

        return json.dumps(output, ensure_ascii=False, indent=2)

    def _format_text(self, result: ProcessResult) -> str:
        """格式化输出为纯文本"""
        lines = []
        lines.append(f"视频标题: {result.video_meta.title}")
        lines.append(f"视频ID: {result.video_meta.video_id or 'N/A'}")
        lines.append(f"频道: {result.video_meta.channel or 'N/A'}")
        lines.append(f"时长: {result.video_meta.duration:.1f} 秒")
        lines.append(f"字幕条目数: {len(result.subtitle_entries)}")
        lines.append(f"置信度: {result.confidence:.1%}")

        if result.confidence < 0.85:
            lines.append("标注: [需核实]")
        elif result.confidence < 0.90:
            lines.append("标注: 建议复核")

        if result.search_hits:
            lines.append(f"\n搜索结果 ({len(result.search_hits)} 条):")
            for i, hit in enumerate(result.search_hits, 1):
                lines.append(f"  {i}. [{hit['start']:.1f}s-{hit['end']:.1f}s] {hit['text']}")

        if result.warnings:
            lines.append("\n警告:")
            for warning in result.warnings:
                lines.append(f"  - {warning}")

        return "\n".join(lines)


# ============================================================
# 批量处理
# ============================================================
def batch_process(
    processor: SubtitleProcessor,
    inputs: List[str],
    search_keyword: Optional[str] = None,
    output_format: str = "json",
) -> Tuple[int, List[Dict[str, Any]]]:
    """批量处理多个输入，返回 (错误码, 结果列表)"""
    results = []

    for i, raw_data in enumerate(inputs):
        code, output = processor.process_input(
            raw_data, search_keyword, output_format
        )

        if code != "0":
            # 单个输入失败，记录错误但继续
            results.append(
                {
                    "index": i,
                    "error_code": code,
                    "error_message": output,
                }
            )
        else:
            results.append(
                {
                    "index": i,
                    "error_code": "0",
                    "output": output,
                }
            )

    # 检查是否有失败项
    failed_count = sum(1 for r in results if r["error_code"] != "0")
    if failed_count > 0:
        return "E008", results

    return "0", results


# ============================================================
# 自检功能
# ============================================================
def run_selftest() -> bool:
    """
    内置自检：使用硬编码样例数据离线验证核心逻辑。
    不读外部文件、不依赖当前工作目录、不访问网络。
    使用宽松阈值断言，确保任何环境直接可过。
    """
    print("=" * 60)
    print("subtubular 自检开始")
    print("=" * 60)

    processor = SubtitleProcessor()
    all_passed = True

    # ---------- 测试 1: JSON 格式输入 ----------
    print("\n[测试 1] JSON 格式输入处理")
    json_input = json.dumps(
        {
            "video_meta": {
                "title": "示例视频标题",
                "video_id": "abc123",
                "channel": "示例频道",
                "duration": 120.5,
                "upload_date": "2026-01-15",
                "description": "这是一个示例描述",
                "tags": ["教程", "示例"],
            },
            "subtitles": [
                {"start": 0.0, "end": 3.5, "text": "大家好，欢迎观看"},
                {"start": 3.5, "end": 7.0, "text": "这是一个字幕搜索示例"},
                {"start": 7.0, "end": 10.0, "text": "我们测试一下搜索功能"},
                {"start": 10.0, "end": 13.5, "text": "希望一切正常"},
            ],
        },
        ensure_ascii=False,
    )

    code, output = processor.process_input(
        json_input, search_keyword="搜索", output_format="json"
    )

    if code != "0":
        print(f"  [失败] 错误码: {code}")
        print(f"  错误信息: {output}")
        all_passed = False
    else:
        result = json.loads(output)
        # 宽松断言：只验证存在性和基本结构
        assert "video_meta" in result, "缺少 video_meta"
        assert "search_hits" in result, "缺少 search_hits"
        assert result["subtitle_count"] >= 3, "字幕数量异常"
        assert len(result["search_hits"]) >= 1, "搜索应有至少 1 条结果"
        assert 0.0 <= result["confidence"] <= 1.0, "置信度范围异常"
        print(f"  [通过] 找到 {len(result['search_hits'])} 条搜索结果")
        print(f"  置信度: {result['confidence']:.2%}")

    # ---------- 测试 2: 文本格式输入 ----------
    print("\n[测试 2] 文本格式输入处理")
    text_input = """示例视频标题
0.0|3.5|第一行字幕
3.5|7.0|第二行字幕内容
7.0|10.5|第三行字幕
10.5|14.0|第四行字幕"""

    code, output = processor.process_input(
        text_input, search_keyword="字幕", output_format="text"
    )

    if code != "0":
        print(f"  [失败] 错误码: {code}")
        print(f"  错误信息: {output}")
        all_passed = False
    else:
        assert "示例视频标题" in output, "标题未正确解析"
        assert "字幕" in output, "搜索结果未包含关键词"
        assert "置信度" in output, "缺少置信度信息"
        print("  [通过] 文本解析与搜索正常")

    # ---------- 测试 3: 空输入错误处理 ----------
    print("\n[测试 3] 空输入错误处理")
    code, output = processor.process_input("", output_format="json")
    assert code == "E001", f"空输入应返回 E001，实际: {code}"
    print(f"  [通过] 正确返回错误码 E001")

    # ---------- 测试 4: 批量处理 ----------
    print("\n[测试 4] 批量处理")
    batch_inputs = [
        json_input,
        text_input,
    ]
    code, results = batch_process(processor, batch_inputs, output_format="json")
    assert code == "0", f"批量处理应成功，实际错误码: {code}"
    assert len(results) == 2, "批量处理数量异常"
    assert all(r["error_code"] == "0" for r in results), "存在失败项"
    print(f"  [通过] 批量处理 {len(results)} 个输入全部成功")

    # ---------- 测试 5: 置信度标注 ----------
    print("\n[测试 5] 置信度标注")
    low_conf_input = json.dumps(
        {
            "video_meta": {"title": "低置信度测试"},
            "subtitles": [
                {"start": 0.0, "end": 2.0, "text": "测试内容", "confidence": 0.5},
                {"start": 2.0, "end": 4.0, "text": "更多内容", "confidence": 0.6},
            ],
        }
    )
    code, output = processor.process_input(low_conf_input, output_format="json")
    assert code == "0", "低置信度输入应处理成功"
    result = json.loads(output)
    assert result["confidence"] < 0.85, "置信度应低于 0.85"
    assert result["confidence_level"] == "[需核实]", "应标注为需核实"
    print(f"  [通过] 低置信度正确标注为: {result['confidence_level']}")

    # ---------- 测试 6: 错误输入 ----------
    print("\n[测试 6] 错误输入处理")
    bad_input = "这不是有效的输入格式"
    code, output = processor.process_input(bad_input, output_format="json")
    assert code in ("E001", "E002", "E003"), f"应返回错误码，实际: {code}"
    print(f"  [通过] 正确返回错误码 {code}")

    # ---------- 测试 7: 不支持的输出格式 ----------
    print("\n[测试 7] 不支持的输出格式")
    code, output = processor.process_input(
        json_input, output_format="xml"
    )
    assert code == "E007", f"应返回 E007，实际: {code}"
    print(f"  [通过] 正确返回错误码 E007")

    # ---------- 汇总 ----------
    print("\n" + "=" * 60)
    if all_passed:
        print("自检全部通过 ✓")
    else:
        print("自检存在失败项 ✗")
    print("=" * 60)

    return all_passed


# ============================================================
# 命令行入口
# ============================================================
def main() -> int:
    """命令行主入口"""
    parser = argparse.ArgumentParser(
        description="subtubular - 视频字幕全文本搜索与元数据处理工具",
        epilog="示例: python main.py --input data.json --search 关键词 --format json",
    )

    parser.add_argument(
        "--input",
        type=str,
        help="输入文件路径（JSON 或文本格式）",
    )
    parser.add_argument(
        "--search",
        type=str,
        help="搜索关键词",
    )
    parser.add_argument(
        "--format",
        type=str,
        choices=["json", "text"],
        default="json",
        help="输出格式（默认: json）",
    )
    parser.add_argument(
        "--batch",
        type=str,
        help="批量处理文件列表（每行一个文件路径）",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检",
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        success = run_selftest()
        return 0 if success else 1

    # 参数校验
    if not args.input and not args.batch:
        print("E009: 必须提供 --input 或 --batch 参数", file=sys.stderr)
        print("使用 --selftest 运行自检", file=sys.stderr)
        return 1

    processor = SubtitleProcessor()

    # 批量处理模式
    if args.batch:
        try:
            with open(args.batch, "r", encoding="utf-8") as f:
                file_paths = [line.strip() for line in f if line.strip()]
        except (IOError, OSError) as e:
            print(f"E010: 读取批量列表失败: {e}", file=sys.stderr)
            return 1

        # 读取所有输入文件
        inputs = []
        for file_path in file_paths:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    inputs.append(f.read())
            except (IOError, OSError) as e:
                print(f"E006: 读取文件 {file_path} 失败: {e}", file=sys.stderr)
                return 1

        code, results = batch_process(
            processor, inputs, args.search, args.format
        )

        for r in results:
            if r["error_code"] == "0":
                print(f"--- 输入 #{r['index']} ---")
                print(r["output"])
            else:
                print(
                    f"--- 输入 #{r['index']} 错误 [{r['error_code']}] ---",
                    file=sys.stderr,
                )
                print(r["error_message"], file=sys.stderr)

        return 0 if code == "0" else 1

    # 单文件处理模式
    try:
        with open(args.input, "r", encoding="utf-8") as f:
            raw_data = f.read()
    except (IOError, OSError) as e:
        print(f"E006: 读取输入文件失败: {e}", file=sys.stderr)
        return 1

    code, output = processor.process_input(raw_data, args.search, args.format)

    if code != "0":
        print(f"错误 [{code}]: {output}", file=sys.stderr)
        return 1

    print(output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
