#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
openmontage — 智能视频生产系统（独立实现）

本脚本依据功能规格独立编写（clean-room），仅使用 Python 标准库。
提供核心数据模型、管线编排、技能调度、结果校验等能力，
并支持 --selftest 离线自检。

错误码约定：
    E001: 输入参数错误
    E002: 输入数据格式错误
    E003: 管线不存在或不可用
    E004: 技能不存在或不可用
    E005: 数据转换失败
    E006: 关键信息提取失败
    E007: 管线执行失败
    E008: 结果校验失败
    E009: 输出格式错误
    E010: 内部未知错误

用法示例：
    python scripts/main.py --help
    python scripts/main.py --selftest
    python scripts/main.py --input sample.csv --pipeline rough_cut,color,subtitle
"""

import argparse
import csv
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
import urllib.error
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# 错误码与异常
# ---------------------------------------------------------------------------

class OpenMontageError(Exception):
    """openmontage 基础异常，携带错误码。"""

    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"[{code}] {message}")


def err(code: str, message: str) -> OpenMontageError:
    """快速构造错误异常。"""
    return OpenMontageError(code, message)


# ---------------------------------------------------------------------------
# 核心数据模型
# ---------------------------------------------------------------------------

@dataclass
class MediaItem:
    """素材条目（对应 C1 多源输入转换后的结构化中间结果）。"""
    source: str                # 来源（路径/URL/标识符）
    media_type: str            # 类型：video / audio / image / subtitle
    duration: float = 0.0      # 时长（秒），未知为 0
    width: int = 0             # 宽（像素），未知为 0
    height: int = 0            # 高（像素），未知为 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SceneInfo:
    """场景信息（对应 C2 关键信息提取）。"""
    scene_id: str
    start_time: float
    end_time: float
    content: str = ""
    characters: List[str] = field(default_factory=list)
    confidence: float = 1.0


@dataclass
class PipelineResult:
    """管线执行结果（对应 C5 结果校验输出）。"""
    pipeline_name: str
    status: str                # success / failed
    output_path: str = ""
    confidence: float = 1.0
    details: Dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# 内置技能库（C4：技能调度）
# ---------------------------------------------------------------------------

# 技能注册表：技能名 -> 可调用函数
# 每个技能函数接收参数 dict，返回 dict（结果）
SKILL_REGISTRY: Dict[str, Callable[[Dict[str, Any]], Dict[str, Any]]] = {}


def register_skill(name: str):
    """装饰器：注册一个技能。"""
    def decorator(func: Callable[[Dict[str, Any]], Dict[str, Any]]):
        SKILL_REGISTRY[name] = func
        return func
    return decorator


@register_skill("transition_effect")
def _skill_transition_effect(params: Dict[str, Any]) -> Dict[str, Any]:
    """转场特效技能：调用 ffmpeg 实现真实转场效果。"""
    input_path = params.get("input_path", "")
    output_path = params.get("output_path", "")
    effect_type = params.get("effect_type", "crossfade")
    duration = float(params.get("duration", 0.5))
    
    if not input_path or not output_path:
        return {
            "applied": False,
            "error": "缺少 input_path 或 output_path",
            "note": "转场特效未应用（缺少参数）",
        }
    
    # 使用 ffmpeg 实现转场效果
    try:
        # 构建 ffmpeg 命令（简化版：使用 xfade 滤镜）
        cmd = [
            "ffmpeg", "-y",
            "-i", input_path,
            "-vf", f"xfade=transition={effect_type}:duration={duration}",
            "-c:v", "libx264",
            "-preset", "fast",
            output_path
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            return {
                "applied": True,
                "effect": effect_type,
                "duration": duration,
                "output_path": output_path,
                "note": f"转场特效已应用（ffmpeg）",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        else:
            return {
                "applied": False,
                "error": result.stderr[-500:],
                "note": "转场特效应用失败",
            }
    except FileNotFoundError:
        return {
            "applied": False,
            "error": "ffmpeg 未安装",
            "note": "转场特效未应用（ffmpeg 不可用）",
        }
    except subprocess.TimeoutExpired:
        return {
            "applied": False,
            "error": "ffmpeg 执行超时",
            "note": "转场特效未应用（超时）",
        }


@register_skill("audio_denoise")
def _skill_audio_denoise(params: Dict[str, Any]) -> Dict[str, Any]:
    """音频降噪技能：调用 ffmpeg 实现真实降噪。"""
    input_path = params.get("input_path", "")
    output_path = params.get("output_path", "")
    strength = float(params.get("strength", 0.5))
    
    if not input_path or not output_path:
        return {
            "applied": False,
            "error": "缺少 input_path 或 output_path",
            "note": "音频降噪未应用（缺少参数）",
        }
    
    try:
        # 使用 ffmpeg 的 afftdn 滤镜进行降噪
        cmd = [
            "ffmpeg", "-y",
            "-i", input_path,
            "-af", f"afftdn=nf={strength}",
            "-c:a", "aac",
            output_path
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            return {
                "applied": True,
                "strength": strength,
                "output_path": output_path,
                "note": "音频降噪完成（ffmpeg）",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        else:
            return {
                "applied": False,
                "error": result.stderr[-500:],
                "note": "音频降噪失败",
            }
    except FileNotFoundError:
        return {
            "applied": False,
            "error": "ffmpeg 未安装",
            "note": "音频降噪未应用（ffmpeg 不可用）",
        }
    except subprocess.TimeoutExpired:
        return {
            "applied": False,
            "error": "ffmpeg 执行超时",
            "note": "音频降噪未应用（超时）",
        }


@register_skill("subtitle_generate")
def _skill_subtitle_generate(params: Dict[str, Any]) -> Dict[str, Any]:
    """字幕生成技能：从剧本提取时间轴生成 SRT 字幕。"""
    script_text = params.get("script_text", "")
    language = params.get("language", "zh")
    
    if not script_text:
        return {
            "applied": False,
            "error": "缺少 script_text",
            "note": "字幕生成未应用（缺少剧本）",
        }
    
    # 解析剧本中的场景和对话
    lines = script_text.strip().splitlines()
    subtitles = []
    current_time = 0.0
    
    for line_num, line in enumerate(lines, start=1):
        line = line.strip()
        if not line:
            continue
        
        # 匹配时间格式（如 00:00-00:05）
        time_match = re.search(r'(\d+):(\d+)-(\d+):(\d+)', line)
        if time_match:
            start = int(time_match.group(1)) * 60 + int(time_match.group(2))
            end = int(time_match.group(3)) * 60 + int(time_match.group(4))
        else:
            start = current_time
            end = current_time + 3.0
            current_time = end
        
        # 提取对话内容（去除场景标记）
        content = re.sub(r'^(场景|SCENE)\s*\d*\s*', '', line)
        content = re.sub(r'\[[^\]]*\]', '', content).strip()
        
        if content:
            subtitles.append({
                "index": len(subtitles) + 1,
                "start": start,
                "end": end,
                "text": content,
            })
    
    if not subtitles:
        return {
            "applied": False,
            "error": "未能从剧本中提取字幕",
            "note": "字幕生成未应用（无有效内容）",
        }
    
    # 生成 SRT 格式
    srt_lines = []
    for sub in subtitles:
        start_str = f"{int(sub['start']//60):02d}:{int(sub['start']%60):02d}:00,000"
        end_str = f"{int(sub['end']//60):02d}:{int(sub['end']%60):02d}:00,000"
        srt_lines.extend([
            str(sub["index"]),
            f"{start_str} --> {end_str}",
            sub["text"],
            "",
        ])
    
    srt_content = "\n".join(srt_lines)
    
    return {
        "applied": True,
        "language": language,
        "count": len(subtitles),
        "srt_content": srt_content,
        "note": "字幕生成完成（从剧本提取）",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ---------------------------------------------------------------------------
# 内置生产管线（C3：管线编排执行）
# ---------------------------------------------------------------------------

# 管线注册表：管线名 -> 管线定义（技能序列 + 元信息）
PIPELINE_REGISTRY: Dict[str, Dict[str, Any]] = {}


def register_pipeline(name: str, description: str, skills: List[str]):
    """注册一条生产管线。"""
    PIPELINE_REGISTRY[name] = {
        "name": name,
        "description": description,
        "skills": skills,
    }


# 注册 12 条标准管线
def _init_pipelines():
    register_pipeline("rough_cut", "粗剪：素材导入 + 基础剪辑", ["transition_effect"])
    register_pipeline("color", "调色：色彩校正与风格化", [])
    register_pipeline("subtitle", "字幕：自动生成与排版", ["subtitle_generate"])
    register_pipeline("audio", "音频：降噪与平衡", ["audio_denoise"])
    register_pipeline("export", "导出：格式转换与封装", [])
    register_pipeline("review", "审阅：生成预览与标注", [])
    register_pipeline("archive", "归档：素材与成片归档", [])
    register_pipeline("composite", "合成：多轨合成与特效", ["transition_effect"])
    register_pipeline("motion", "动效：动态图形与动画", [])
    register_pipeline("capture", "采集：多源素材采集", [])
    register_pipeline("transcode", "转码：分辨率与编码转换", [])
    register_pipeline("delivery", "交付：多平台分发准备", [])


_init_pipelines()


# ---------------------------------------------------------------------------
# 核心功能实现
# ---------------------------------------------------------------------------

class OpenMontageEngine:
    """openmontage 核心引擎。"""

    def __init__(self, dry_run: bool = False):
        self.media_items: List[MediaItem] = []
        self.scenes: List[SceneInfo] = []
        self.results: List[PipelineResult] = []
        self._temp_dir: Optional[str] = None
        self.dry_run = dry_run

    # ---- C1: 多源输入转换 ----

    def load_from_csv(self, csv_text: str) -> List[MediaItem]:
        """
        从 CSV 文本加载素材清单，转换为结构化 MediaItem 列表。
        支持列：source, media_type, duration, width, height
        """
        if not csv_text or not csv_text.strip():
            raise err("E002", "CSV 输入为空")

        items: List[MediaItem] = []
        try:
            reader = csv.DictReader(io.StringIO(csv_text))
            required = {"source", "media_type"}
            for row_num, row in enumerate(reader, start=2):
                # 检查必需列
                if not required.issubset(row.keys()):
                    missing = required - set(row.keys())
                    raise err("E002", f"CSV 缺少必需列: {missing} (第 {row_num} 行)")

                source = row["source"].strip()
                media_type = row["media_type"].strip().lower()
                if not source or not media_type:
                    raise err("E002", f"第 {row_num} 行 source/media_type 不能为空")

                # 可选列，宽松解析
                try:
                    duration = float(row.get("duration", 0) or 0)
                except (ValueError, TypeError):
                    duration = 0.0
                try:
                    width = int(float(row.get("width", 0) or 0))
                except (ValueError, TypeError):
                    width = 0
                try:
                    height = int(float(row.get("height", 0) or 0))
                except (ValueError, TypeError):
                    height = 0

                item = MediaItem(
                    source=source,
                    media_type=media_type,
                    duration=max(0.0, duration),
                    width=max(0, width),
                    height=max(0, height),
                )
                items.append(item)
        except csv.Error as e:
            raise err("E002", f"CSV 解析失败: {e}")
        except OpenMontageError:
            raise
        except Exception as e:
            raise err("E005", f"数据转换失败: {e}")

        if not items:
            raise err("E002", "CSV 未包含任何有效素材行")

        self.media_items = items
        return items

    def load_from_json(self, json_text: str) -> List[MediaItem]:
        """从 JSON 文本加载素材清单。"""
        if not json_text or not json_text.strip():
            raise err("E002", "JSON 输入为空")
        try:
            data = json.loads(json_text)
        except json.JSONDecodeError as e:
            raise err("E002", f"JSON 解析失败: {e}")

        if not isinstance(data, list):
            raise err("E002", "JSON 顶层必须是数组")

        items: List[MediaItem] = []
        for idx, entry in enumerate(data):
            if not isinstance(entry, dict):
                raise err("E002", f"第 {idx} 项不是对象")
            source = str(entry.get("source", "")).strip()
            media_type = str(entry.get("media_type", "")).strip().lower()
            if not source or not media_type:
                raise err("E002", f"第 {idx} 项缺少 source 或 media_type")
            items.append(MediaItem(
                source=source,
                media_type=media_type,
                duration=float(entry.get("duration", 0) or 0),
                width=int(entry.get("width", 0) or 0),
                height=int(entry.get("height", 0) or 0),
                metadata=entry.get("metadata", {}),
            ))

        if not items:
            raise err("E002", "JSON 未包含任何有效素材")
        self.media_items = items
        return items

    # ---- C2: 关键信息提取 ----

    def extract_scenes(self, script_text: str) -> List[SceneInfo]:
        """
        从剧本文本中提取场景信息（模拟实现）。
        识别模式：以 "场景" 或 "SCENE" 开头的行，后跟时间信息。
        """
        if not script_text or not script_text.strip():
            raise err("E002", "剧本输入为空")

        scenes: List[SceneInfo] = []
        lines = script_text.strip().splitlines()

        for line_num, line in enumerate(lines, start=1):
            line = line.strip()
            if not line:
                continue
            # 宽松匹配：包含 "场景" 或 "SCENE" 关键词
            upper = line.upper()
            if "场景" not in line and "SCENE" not in upper:
                continue

            # 尝试提取时间（格式如: 00:10-00:25 或 10-25）
            time_match = re.search(r'(\d+)[:：]?(\d+)?\s*[-–—]\s*(\d+)[:：]?(\d+)?', line)
            if time_match:
                try:
                    start = float(time_match.group(1)) * 60 + float(time_match.group(2) or 0)
                    end = float(time_match.group(3)) * 60 + float(time_match.group(4) or 0)
                except ValueError:
                    start, end = 0.0, 0.0
            else:
                start, end = 0.0, 0.0

            # 提取场景内容（去除时间标记）
            content
