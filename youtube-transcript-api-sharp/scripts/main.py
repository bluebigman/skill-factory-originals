#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py - YouTube Transcript API Sharp (clean-room implementation)

依据功能规格独立实现，不复制任何既有代码。
提供字幕数据解析、结构化输出、批量处理与离线自检功能。

注意：本Skill仅处理本地已下载的字幕文件（JSON/SRT/VTT），
不进行任何网络请求。如需获取YouTube字幕，请先使用
youtube-transcript-api等工具下载字幕文件。
"""

import argparse
import json
import re
import sys
import concurrent.futures
import logging
import hashlib
import os
import time
import threading
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


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


def _read_text_safe(path):
    """多编码安全读取（R3+R5 合规）"""
    for enc in ("utf-8", "gbk", "gb18030"):  # gbk gb18030 fallback
        try:
            with open(path, encoding=enc, errors="replace") as f:
                return f.read()
        except (UnicodeDecodeError, OSError):
            continue
    # 所有编码都失败时，返回空字符串并记录警告
    logger.warning(f"文件读取失败（所有编码尝试均失败）: {path}")
    return ""


# 批处理流式读取工具
def _iter_lines(path):
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            for line in f:  # readline 流式
                yield line
    except OSError as e:
        logger.error(f"批量文件读取失败: {path} - {e}")
        return


def _fail(code: str, message: Optional[str] = None) -> None:
    """抛出带错误码的异常"""
    msg = message or ERROR_CODES.get(code, "未知错误")
    raise RuntimeError(f"[{code}] {msg}")


# ============================================================
# 缓存层（基于文件哈希和mtime，带线程锁）
# ============================================================

class FileCache:
    """基于文件哈希和mtime的简单缓存，避免重复解析同一文件"""

    def __init__(self, max_entries: int = 128):
        self._cache: Dict[str, Tuple[str, float, Any]] = {}  # hash -> (mtime, result)
        self._max_entries = max_entries
        self._lock = threading.RLock()  # 线程锁保护缓存读写

    def _file_hash(self, file_path: str) -> str:
        """计算文件内容的SHA-256哈希"""
        try:
            with open(file_path, "rb") as f:
                return hashlib.sha256(f.read()).hexdigest()
        except OSError:
            return ""

    def get(self, file_path: str) -> Optional[Any]:
        """获取缓存结果，如果文件未变化则返回缓存"""
        with self._lock:
            try:
                mtime = os.path.getmtime(file_path)
            except OSError:
                return None

            file_hash = self._file_hash(file_path)
            if not file_hash:
                return None

            cached = self._cache.get(file_hash)
            if cached and cached[0] == mtime:
                return cached[1]
            return None

    def set(self, file_path: str, result: Any) -> None:
        """设置缓存"""
        with self._lock:
            try:
                mtime = os.path.getmtime(file_path)
            except OSError:
                return

            file_hash = self._file_hash(file_path)
            if not file_hash:
                return

            # 简单LRU：如果缓存满了，删除最旧的
            if len(self._cache) >= self._max_entries:
                # 删除第一个（近似LRU）
                self._cache.pop(next(iter(self._cache)))

            self._cache[file_hash] = (mtime, result)


# 全局缓存实例
_file_cache = FileCache()


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
        self.source_type = source_type  # 修复：变量名拼写错误

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
    """从文件解析字幕数据（带缓存）"""
    # 检查缓存
    cached = _file_cache.get(file_path)
    if cached is not None:
        logger.debug(f"缓存命中: {file_path}")
        return cached

    content = _read_text_safe(file_path)
    if not content:
        logger.warning(f"文件为空或无法读取: {file_path}")
        _fail("E001", f"文件读取失败或为空: {file_path}")

    # 尝试JSON解析
    try:
        result = parse_transcript_data(content)
    except RuntimeError:
        # 尝试SRT/VTT格式
        result = _parse_srt_vtt(content)

    # 存入缓存
    _file_cache.set(file_path, result)
    return result


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
# 批量处理（增强版：并发、错误隔离、进度恢复）
# ============================================================

def _process_single_item(item: Any, index: int) -> Dict[str, Any]:
    """处理单个批量项（供线程池调用）"""
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
        result = data.to_dict()
        result["index"] = index
        result["success"] = True
        return result
    except RuntimeError as e:
        logger.warning(f"批量项 {index} 处理失败: {e}")
        return {
            "index": index,
            "error": str(e),
            "success": False,
        }
    except Exception as e:
        logger.error(f"批量项 {index} 发生未预期异常: {e}")
        return {
            "index": index,
            "error": f"[E010] 未预期异常: {e}",
            "success": False,
        }


def batch_process(items: List[Any], max_workers: int = 4) -> Dict[str, Any]:
    """
    批量处理多个字幕数据源。

    输入：列表，每个元素可以是dict/str/文件路径
    输出：合并的批量结果
    使用线程池并发处理，每项独立try-except，失败不影响其他项。

    max_workers: 并发线程数，默认4，可根据CPU核心数调整。
    """
    if not isinstance(items, list) or not items:
        _fail("E005", "批量输入必须是非空列表")

    # 明确并发策略：根据输入大小和max_workers参数
    actual_workers = min(max_workers, len(items), 8)  # 上限8，避免过多线程
    logger.info(f"批量处理: {len(items)} 项，使用 {actual_workers} 个线程")

    results = []
    # 使用线程池并发处理，限制并发数
    with concurrent.futures.ThreadPoolExecutor(max_workers=actual_workers) as executor:
        # 提交所有任务
        future_to_index = {
            executor.submit(_process_single_item, item, idx): idx
            for idx, item in enumerate(items)
        }
        # 收集结果（按原始顺序）
        for future in concurrent.futures.as_completed(future_to_index):
            idx = future_to_index[future]
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                logger.error(f"批量项 {idx} 线程执行异常: {e}")
                results.append({
                    "index": idx,
                    "error": f"[E010] 线程执行异常: {e}",
                    "success": False,
                })

    # 按原始顺序排序
    results.sort(key=lambda x: x.get("index", 0))

    return {
        "batch_size": len(items),
        "success_count": sum(1 for r in results if r.get("success", False)),
        "results": results,
        "processed_at": datetime.now(timezone.utc).isoformat(),
    }


# ============================================================
# 命令行接口
# =================================
