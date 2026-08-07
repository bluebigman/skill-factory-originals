#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
meetily — 隐私优先的 AI 会议助手（clean-room 独立实现）

本脚本仅依据功能规格独立编写，不复制任何既有代码。
提供核心能力：音频转写模拟、说话人分离、纪要生成、本地模型推理接口。

用法:
    python scripts/main.py --selftest    # 内置离线自检
    python scripts/main.py --transcribe <file>
    python scripts/main.py --summarize <text> [--model <name>]
"""

import argparse
import json
import os
import re
import sys
import tempfile
import wave
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple

# 错误码定义
ERROR_CODES = {
    "E001": "参数错误或缺少必要参数",
    "E002": "文件不存在或无法读取",
    "E003": "不支持的音频格式",
    "E004": "转写引擎初始化失败",
    "E005": "说话人分离失败",
    "E006": "纪要生成失败",
    "E007": "本地模型调用失败",
    "E008": "输出写入失败",
    "E009": "自检失败",
    "E010": "未知内部错误",
}


# ---------- 数据结构 ----------
@dataclass
class Segment:
    """带时间戳和说话人的文本片段"""
    start: float          # 开始时间（秒）
    end: float            # 结束时间（秒）
    speaker: str          # 说话人标识，如 "SPEAKER_00"
    text: str             # 转写文本


@dataclass
class Transcript:
    """完整转写结果"""
    segments: List[Segment] = field(default_factory=list)
    language: str = "zh"
    
    def to_dict(self) -> Dict:
        return {
            "language": self.language,
            "segments": [asdict(s) for s in self.segments],
        }


@dataclass
class MeetingMinutes:
    """结构化会议纪要"""
    topics: List[str] = field(default_factory=list)       # 议题列表
    decisions: List[str] = field(default_factory=list)    # 决议列表
    action_items: List[Dict] = field(default_factory=list)  # 待办事项列表
    
    def to_dict(self) -> Dict:
        return asdict(self)


# ---------- 核心引擎（模拟实现，便于离线自检） ----------
class TranscriptionEngine:
    """转写引擎（模拟）—— 实际项目中可替换为 whisper 等本地模型"""
    
    def __init__(self, model_name: str = "mock-whisper"):
        self.model_name = model_name
        # 模拟内置词库，用于自检
        self._mock_lexicon = {
            "hello": "你好",
            "world": "世界",
            "meeting": "会议",
            "action": "行动",
            "item": "项目",
            "decision": "决定",
            "topic": "议题",
        }
    
    def transcribe(self, audio_path: str) -> Transcript:
        """执行转写（模拟实现）"""
        # 实际项目中此处调用本地 whisper 模型
        # 这里仅做文件存在性检查并返回模拟结果
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"音频文件不存在: {audio_path}")
        
        # 模拟转写结果
        transcript = Transcript()
        transcript.segments = [
            Segment(0.0, 2.5, "SPEAKER_00", "大家好，我们开始今天的会议。"),
            Segment(2.8, 5.2, "SPEAKER_01", "好的，我们先讨论一下项目进度。"),
            Segment(5.5, 8.0, "SPEAKER_00", "我建议把 deadline 提前两周。"),
            Segment(8.3, 11.0, "SPEAKER_01", "同意，但需要增加人手。"),
        ]
        return transcript


class DiarizationEngine:
    """说话人分离引擎（模拟）"""
    
    def __init__(self, num_speakers: int = 2):
        self.num_speakers = num_speakers
    
    def separate(self, segments: List[Segment]) -> List[Segment]:
        """对片段进行说话人标注（模拟）"""
        # 实际项目中此处调用 pyannote 等模型
        # 这里简单交替分配说话人
        result = []
        for i, seg in enumerate(segments):
            new_seg = Segment(
                start=seg.start,
                end=seg.end,
                speaker=f"SPEAKER_{i % self.num_speakers:02d}",
                text=seg.text,
            )
            result.append(new_seg)
        return result


class MinutesGenerator:
    """会议纪要生成器（基于规则）"""
    
    def __init__(self, model_name: Optional[str] = None):
        self.model_name = model_name
    
    def generate(self, transcript: Transcript) -> MeetingMinutes:
        """从转写文本提取结构化纪要"""
        full_text = " ".join(seg.text for seg in transcript.segments)
        
        minutes = MeetingMinutes()
        
        # 议题提取：包含"讨论"、"议题"等关键词的句子
        for seg in transcript.segments:
            if any(kw in seg.text for kw in ["讨论", "议题", "topic"]):
                minutes.topics.append(seg.text.strip())
        
        # 决议提取：包含"决定"、"同意"、"decision"等关键词
        for seg in transcript.segments:
            if any(kw in seg.text for kw in ["决定", "同意", "decision", "agree"]):
                minutes.decisions.append(seg.text.strip())
        
        # 待办事项提取：包含"待办"、"需要"、"action"等关键词
        for seg in transcript.segments:
            if any(kw in seg.text for kw in ["需要", "待办", "action", "should"]):
                minutes.action_items.append({
                    "task": seg.text.strip(),
                    "assignee": seg.speaker,
                    "status": "pending",
                })
        
        # 兜底：若没有提取到任何内容，给出通用结构
        if not minutes.topics:
            minutes.topics.append("（未识别到明确议题）")
        if not minutes.decisions:
            minutes.decisions.append("（未识别到明确决议）")
        if not minutes.action_items:
            minutes.action_items.append({
                "task": "（未识别到明确待办事项）",
                "assignee": "unknown",
                "status": "pending",
            })
        
        return minutes


class LocalLLMClient:
    """本地大模型客户端（Ollama 接口模拟）"""
    
    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url
    
    def summarize(self, text: str, model: str = "llama3") -> str:
        """调用本地模型生成摘要（模拟）"""
        # 实际项目中此处调用 Ollama API
        # 这里返回基于规则的模拟摘要
        sentences = re.split(r'[。！？.!?]', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        if not sentences:
            return "（无内容可摘要）"
        # 取前两句作为摘要
        summary = "；".join(sentences[:2])
        return f"[{model} 本地摘要] {summary}"


# ---------- 主应用类 ----------
class MeetilyApp:
    """主应用：整合各引擎并提供统一接口"""
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.transcriber = TranscriptionEngine(
            model_name=self.config.get("stt_model", "mock-whisper")
        )
        self.diarizer = DiarizationEngine(
            num_speakers=self.config.get("num_speakers", 2)
        )
        self.minutes_gen = MinutesGenerator(
            model_name=self.config.get("llm_model")
        )
        self.llm_client = LocalLLMClient(
            base_url=self.config.get("ollama_url", "http://localhost:11434")
        )
    
    def process_audio(self, audio_path: str) -> Dict:
        """完整处理流程：转写 → 分离 → 纪要"""
        # 1. 转写
        transcript = self.transcriber.transcribe(audio_path)
        # 2. 说话人分离
        transcript.segments = self.diarizer.separate(transcript.segments)
        # 3. 生成纪要
        minutes = self.minutes_gen.generate(transcript)
        
        return {
            "transcript": transcript.to_dict(),
            "minutes": minutes.to_dict(),
        }
    
    def summarize_text(self, text: str, model: str = "llama3") -> str:
        """对给定文本生成摘要"""
        return self.llm_client.summarize(text, model=model)


# ---------- 自检模块 ----------
def run_selftest() -> bool:
    """
    内置离线自检：使用硬编码样例数据验证核心逻辑。
    不读取外部文件、不依赖当前目录、不访问网络。
    """
    print("[SELFTEST] 开始自检...")
    
    try:
        # ---- 测试 1: 转写引擎 ----
        print("[SELFTEST] 测试转写引擎...")
        # 创建临时音频文件（模拟）
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            temp_path = f.name
        try:
            # 写入一个最小 WAV 文件头
            with wave.open(temp_path, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(16000)
                wf.writeframes(b"\x00\x00" * 1600)  # 0.1秒静音
        except Exception as e:
            print(f"[SELFTEST] 创建测试音频失败: {e}")
            return False
        
        engine = TranscriptionEngine()
        try:
            transcript = engine.transcribe(temp_path)
            # 宽松断言：至少有一个片段
            assert len(transcript.segments) > 0, "转写结果为空"
            # 每个片段必须有时间戳和文本
            for seg in transcript.segments:
                assert seg.end > seg.start, "时间戳无效"
                assert len(seg.text) > 0, "文本为空"
            print(f"[SELFTEST] 转写引擎通过 (片段数: {len(transcript.segments)})")
        finally:
            os.unlink(temp_path)
        
        # ---- 测试 2: 说话人分离 ----
        print("[SELFTEST] 测试说话人分离...")
        test_segments = [
            Segment(0.0, 1.0, "unknown", "第一段"),
            Segment(1.0, 2.0, "unknown", "第二段"),
            Segment(2.0, 3.0, "unknown", "第三段"),
        ]
        diarizer = DiarizationEngine(num_speakers=2)
        separated = diarizer.separate(test_segments)
        # 宽松断言：所有片段都有说话人标注
        assert all(seg.speaker.startswith("SPEAKER_") for seg in separated), "说话人标注缺失"
        # 至少有两种不同说话人
        speakers = set(seg.speaker for seg in separated)
        assert len(speakers) >= 2, "说话人数量不足"
        print(f"[SELFTEST] 说话人分离通过 (识别到 {len(speakers)} 位说话人)")
        
        # ---- 测试 3: 纪要生成 ----
        print("[SELFTEST] 测试纪要生成...")
        test_transcript = Transcript()
        test_transcript.segments = [
            Segment(0.0, 2.0, "SPEAKER_00", "今天我们讨论项目进度。"),
            Segment(2.0, 4.0, "SPEAKER_01", "我决定把截止日期提前。"),
            Segment(4.0, 6.0, "SPEAKER_00", "我们需要增加测试人员。"),
        ]
        minutes_gen = MinutesGenerator()
        minutes = minutes_gen.generate(test_transcript)
        # 宽松断言：三个字段都有内容
        assert len(minutes.topics) > 0, "议题为空"
        assert len(minutes.decisions) > 0, "决议为空"
        assert len(minutes.action_items) > 0, "待办为空"
        print(f"[SELFTEST] 纪要生成通过 (议题:{len(minutes.topics)}, 决议:{len(minutes.decisions)}, 待办:{len(minutes.action_items)})")
        
        # ---- 测试 4: 本地模型摘要 ----
        print("[SELFTEST] 测试本地模型摘要...")
        llm = LocalLLMClient()
        summary = llm.summarize("今天讨论了三个议题。第一是项目进度。第二是人员安排。", model="test-model")
        assert len(summary) > 0, "摘要为空"
        assert "test-model" in summary, "模型名未出现在摘要中"
        print(f"[SELFTEST] 本地模型摘要通过")
        
        # ---- 测试 5: 完整流程 ----
        print("[SELFTEST] 测试完整处理流程...")
        app = MeetilyApp()
        # 使用临时音频文件
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            temp_path = f.name
        try:
            with wave.open(temp_path, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(16000)
                wf.writeframes(b"\x00\x00" * 16000)  # 1秒静音
            result = app.process_audio(temp_path)
            # 宽松断言：结果包含转写和纪要
            assert "transcript" in result, "缺少转写结果"
            assert "minutes" in result, "缺少纪要结果"
            assert len(result["transcript"]["segments"]) > 0, "转写片段为空"
            print("[SELFTEST] 完整流程通过")
        finally:
            os.unlink(temp_path)
        
        print("[SELFTEST] ✅ 所有自检通过")
        return True
        
    except AssertionError as e:
        print(f"[SELFTEST] ❌ 断言失败: {e}")
        return False
    except Exception as e:
        print(f"[SELFTEST] ❌ 自检异常: {e}")
        return False


# ---------- 命令行入口 ----------
def main() -> int:
    """命令行入口"""
    parser = argparse.ArgumentParser(
        description="meetily - 隐私优先的AI会议助手 (clean-room实现)"
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置离线自检（不依赖外部文件/网络）",
    )
    parser.add_argument(
        "--transcribe",
        metavar="FILE",
        help="转写音频/视频文件（模拟实现）",
    )
    parser.add_argument(
        "--summarize",
        metavar="TEXT",
        help="对给定文本生成摘要",
    )
    parser.add_argument(
        "--model",
        default="llama3",
        help="本地模型名称（默认: llama3）",
    )
    parser.add_argument(
        "--output",
        metavar="FILE",
        help="输出结果到JSON文件",
    )
    
    args = parser.parse_args()
    
    # 自检模式
    if args.selftest:
        success = run_selftest()
        return 0 if success else 1
    
    # 创建应用实例
    app = MeetilyApp()
    
    try:
        # 转写模式
        if args.transcribe:
            if not os.path.exists(args.transcribe):
                print(f"错误 [{ERROR_CODES['E002']}]: 文件不存在: {args.transcribe}")
                return 1
            result = app.process_audio(args.transcribe)
            output = json.dumps(result, ensure_ascii=False, indent=2)
            print(output)
            if args.output:
                with open(args.output, "w", encoding="utf-8") as f:
                    f.write(output)
            return 0
        
        # 摘要模式
        if args.summarize:
            summary = app.summarize_text(args.summarize, model=args.model)
            print(summary)
            if args.output:
                with open(args.output, "w", encoding="utf-8") as f:
                    f.write(json.dumps({"summary": summary}, ensure_ascii=False, indent=2))
            return 0
        
        # 未指定操作
        parser.print_help()
        return 0
        
    except FileNotFoundError as e:
        print(f"错误 [{ERROR_CODES['E002']}]: {e}")
        return 1
    except Exception as e:
        print(f"错误 [{ERROR_CODES['E010']}]: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
