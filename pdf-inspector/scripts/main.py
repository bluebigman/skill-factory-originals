#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pdf-inspector: PDF文档检测与分类
=================================
快速检测PDF文件类型（扫描版或文本版），提取文本内容，
为后续处理（如OCR、转换）提供智能路由决策。

本脚本为 clean-room 独立实现，仅依据功能规格编写。

用法示例:
    python scripts/main.py path/to/file.pdf
    python scripts/main.py --selftest
    python scripts/main.py path/to/file.pdf --output-format json

错误码:
    E001: 输入为空
    E002: 关键信息缺失
    E003: 输入格式错误
    E004: 超出能力边界
    E005: 置信度过低
    E006: 文件不存在
    E007: 无法读取PDF内容
    E008: PDF文件损坏或无效
    E009: 不支持的参数
    E010: 内部逻辑错误
"""

import sys
import os
import re
import argparse
import zlib
import json
import tempfile
import time
import threading
import base64
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone

# 尝试导入第三方库（仅用于增强解析，非必需）
try:
    import pypdf  # pip install pypdf
    _HAS_PYPDF = True
except ImportError:
    _HAS_PYPDF = False


# ============================================================
# 核心数据结构
# ============================================================

class PDFInspectionResult:
    """PDF检测结果的数据结构"""
    
    def __init__(self):
        self.file_name: str = ""
        self.file_size: int = 0
        self.page_count: int = 0
        self.pdf_type: str = "unknown"  # "text" / "scanned" / "mixed" / "unknown"
        self.text_preview: str = ""
        self.confidence: float = 0.0
        self.is_encrypted: bool = False
        self.has_text_layer: bool = False
        self.has_images: bool = False
        self.warnings: List[str] = []
        self.raw_metadata: Dict[str, Any] = {}
        self.inspection_time: str = ""
        self.degraded: bool = False  # 标记是否降级处理
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "file_name": self.file_name,
            "file_size": self.file_size,
            "page_count": self.page_count,
            "pdf_type": self.pdf_type,
            "text_preview": self.text_preview[:200] if self.text_preview else "",
            "confidence": round(self.confidence, 2),
            "is_encrypted": self.is_encrypted,
            "has_text_layer": self.has_text_layer,
            "has_images": self.has_images,
            "warnings": self.warnings,
            "metadata": self.raw_metadata,
            "inspection_time": self.inspection_time,
            "degraded": self.degraded
        }
    
    def __repr__(self) -> str:
        return f"<PDFInspectionResult type={self.pdf_type} pages={self.page_count} conf={self.confidence:.2f}>"


# ============================================================
# PDF解析核心函数（纯Python实现，不依赖pypdf）
# ============================================================

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


def _parse_pdf_header(data: bytes) -> Dict[str, Any]:
    """
    解析PDF文件头信息
    
    参数:
        data: PDF文件字节数据
    
    返回:
        包含PDF版本等信息的字典
    """
    header_info = {
        "version": "",
        "is_valid": False
    }
    
    if data.startswith(b"%PDF-"):
        # 提取版本号
        version_match = re.match(rb"%PDF-(\d+\.\d+)", data[:16])
        if version_match:
            header_info["version"] = version_match.group(1).decode("utf-8")
            header_info["is_valid"] = True
    
    return header_info


def _extract_text_from_stream(stream: bytes) -> List[str]:
    """
    从PDF流中提取文本（纯Python实现）
    
    参数:
        stream: PDF流数据
    
    返回:
        提取的文本片段列表
    """
    text_parts: List[str] = []
    
    # 尝试zlib解压
    try:
        decompressed = zlib.decompress(stream)
        # 查找文本操作符
        text_patterns = [
            rb"\((.*?)\)\s*Tj",       # Tj 操作符
            rb"\[(.*?)\]\s*TJ",       # TJ 操作符
            rb"\((.*?)\)\s*'",        # 单引号字符串
            rb"\((.*?)\)\s*\"",       # 双引号字符串
        ]
        
        for pattern in text_patterns:
            matches = re.findall(pattern, decompressed, re.DOTALL)
            for match in matches:
                if isinstance(match, bytes):
                    # 处理转义字符
                    cleaned = match.replace(b"\\(", b"(").replace(b"\\)", b")")
                    cleaned = cleaned.replace(b"\\\\", b"\\")
                    cleaned = cleaned.replace(b"\\n", b" ")
                    try:
                        text = cleaned.decode("utf-8", errors="ignore")
                        if text.strip():
                            text_parts.append(text)
                    except Exception as e:
                        print(f"[WARN] 降级处理: {e}", file=sys.stderr)
    
    except zlib.error:
        # 不是压缩流，尝试直接解析
        try:
            # 查找文本操作符
            matches = re.findall(rb"\((.*?)\)\s*Tj", stream, re.DOTALL)
            for match in matches:
                cleaned = match.replace(b"\\(", b"(").replace(b"\\)", b")")
                cleaned = cleaned.replace(b"\\\\", b"\\")
                try:
                    text = cleaned.decode("utf-8", errors="ignore")
                    if text.strip():
                        text_parts.append(text)
                except Exception as e:
                    print(f"[WARN] 降级处理: {e}", file=sys.stderr)
        except Exception as e:
            print(f"[WARN] 降级处理: {e}", file=sys.stderr)
    
    return text_parts


def _parse_xref_table(data: bytes) -> Dict[int, Tuple[int, int]]:
    """
    解析PDF xref表（纯Python实现）
    
    参数:
        data: PDF文件字节数据
    
    返回:
        对象编号到(偏移量, 生成号)的映射
    """
    xref_map: Dict[int, Tuple[int, int]] = {}
    
    # 查找xref表位置
    xref_positions = [m.start() for m in re.finditer(rb"xref", data)]
    
    for pos in xref_positions:
        # 尝试解析xref表
        try:
            # 查找起始对象号
            lines = data[pos:pos+1000].split(b"\n")
            if len(lines) < 2:
                continue
            
            # 解析对象号
            first_obj_match = re.match(rb"(\d+)\s+(\d+)", lines[1])
            if not first_obj_match:
                continue
            
            first_obj = int(first_obj_match.group(1))
            count = int(first_obj_match.group(2))
            
            # 解析每个对象条目
            for i in range(count):
                line_idx = 2 + i
                if line_idx >= len(lines):
                    break
                entry_match = re.match(rb"(\d{10})\s+(\d{5})\s+([nf])", lines[line_idx])
                if entry_match:
                    offset = int(entry_match.group(1))
                    gen = int(entry_match.group(2))
                    obj_num = first_obj + i
                    xref_map[obj_num] = (offset, gen)
        except Exception:
            continue
    
    return xref_map


def _parse_pdf_objects(data: bytes) -> Dict[int, bytes]:
    """
    解析PDF对象（纯Python实现）
    
    参数:
        data: PDF文件字节数据
    
    返回:
        对象编号到对象内容的映射
    """
    objects: Dict[int, bytes] = {}
    
    # 查找所有对象
    obj_pattern = rb"(\d+)\s+(\d+)\s+obj\s+(.*?)\s+endobj"
    matches = re.finditer(obj_pattern, data, re.DOTALL)
    
    for match in matches:
        obj_num = int(match.group(1))
        obj_content = match.group(3)
        objects[obj_num] = obj_content
    
    return objects


def _extract_text_from_pdf_bytes(data: bytes) -> Tuple[str, Dict[str, Any]]:
    """
    从PDF字节数据中提取文本信息（纯标准库实现）
    
    返回:
        (提取到的文本, 元信息字典)
    """
    text_parts: List[str] = []
    metadata: Dict[str, Any] = {
        "has_images": False,
        "has_text": False,
        "page_count": 0,
        "is_encrypted": False,
        "stream_count": 0,
        "image_count": 0,
        "version": "",
        "has_forms": False,
        "has_annotations": False,
    }
    
    # 解析文件头
    header_info = _parse_pdf_header(data)
    metadata["version"] = header_info["version"]
    
    if not header_info["is_valid"]:
        raise ValueError("E008: 不是有效的PDF文件")
    
    # 解析xref表
    xref_map = _parse_xref_table(data)
    
    # 解析所有对象
    objects = _parse_pdf_objects(data)
    
    # 查找所有流对象
    stream_pattern = rb"stream\r?\n(.*?)\r?\nendstream"
    streams = re.findall(stream_pattern, data, re.DOTALL)
    metadata["stream_count"] = len(streams)
    
    # 统计图片对象
    image_pattern = rb"/Subtype\s*/Image"
    images = re.findall(image_pattern, data)
    metadata["image_count"] = len(images)
    metadata["has_images"] = len(images) > 0
    
    # 检查加密
    if b"/Encrypt" in data:
        metadata["is_encrypted"] = True
    
    # 统计页面数量（通过解析Page对象）
    page_count = 0
    for obj_num, obj_content in objects.items():
        if b"/Type" in obj_content and b"/Page" in obj_content:
            # 确保不是Pages对象
            if not re.search(rb"/Type\s*/Pages", obj_content):
                page_count += 1
    
    metadata["page_count"] = page_count if page_count > 0 else len(re.findall(rb"/Type\s*/Page[^s]", data))
    
    # 检查表单和注释
    if b"/AcroForm" in data or b"/BBox" in data:
        metadata["has_forms"] = True
    if b"/Annots" in data:
        metadata["has_annotations"] = True
    
    # 提取文本（从流对象中）
    for stream in streams:
        text_parts.extend(_extract_text_from_stream(stream))
    
    # 合并文本
    full_text = " ".join(text_parts)
    metadata["has_text"] = len(full_text.strip()) > 0
    
    return full_text, metadata


def _analyze_pdf_content(data: bytes) -> PDFInspectionResult:
    """
    分析PDF内容，确定类型
    
    返回:
        PDFInspectionResult 对象
    """
    result = PDFInspectionResult()
    result.inspection_time = datetime.now(timezone.utc).isoformat()
    
    try:
        # 使用标准库解析（纯Python实现）
        text, metadata = _extract_text_from_pdf_bytes(data)
        
        result.page_count = metadata.get("page_count", 0)
        result.is_encrypted = metadata.get("is_encrypted", False)
        result.has_images = metadata.get("has_images", False)
        result.text_preview = text[:500] if text else ""
        result.raw_metadata = metadata
        
        # 判断PDF类型
        text_len = len(text.strip())
        image_count = metadata.get("image_count", 0)
        
        # 更精确的类型判断逻辑
        if text_len > 0 and image_count > 0:
            # 混合类型：根据文本和图片比例调整置信度
            result.pdf_type = "mixed"
            if text_len > 1000:
                result.confidence = 0.88
            elif text_len > 100:
                result.confidence = 0.85
            else:
                result.confidence = 0.82
        elif text_len > 0:
            # 纯文本类型
            result.pdf_type = "text"
            if text_len > 100:
                result.confidence = 0.95
            elif text_len > 0:
                result.confidence = 0.90
        elif image_count > 0:
            # 扫描类型
            result.pdf_type = "scanned"
            if image_count >= 2:
                result.confidence = 0.92
            else:
                result.confidence = 0.90
        else:
            # 无法确定类型
            result.pdf_type = "unknown"
            result.confidence = 0.50
            result.warnings.append("无法确定PDF类型，可能为空文档或格式特殊")
        
        result.has_text_layer = text_len > 0
        
        # 添加额外警告
        if metadata.get("is_encrypted", False):
            result.warnings.append("PDF文件已加密，可能无法完整解析")
        
        if metadata.get("has_forms", False):
            result.warnings.append("PDF包含表单元素")
        
        if metadata.get("has_annotations", False):
            result.warnings.append("PDF包含注释元素")
        
        if result.page_count == 0:
            result.warnings.append("未检测到页面对象")
        
    except Exception as e:
        result.pdf_type = "unknown"
        result.confidence = 0.1
        result.warnings.append(f"解析失败: {str(e)}")
    
    return result


def _read_file_with_timeout(file_path: str, timeout: int = 10) -> bytes:
    """
    带超时读取文件
    
    参数:
        file_path: 文件路径
        timeout: 超时秒数
    
    返回:
        文件字节数据
    """
    result = []
    error = []
    
    def _read():
        try:
            with open(file_path, "rb") as f:
                result.append(f.read())
        except Exception as e:
            error.append(e)
    
    thread = threading.Thread(target=_read)
    thread.daemon = True
    thread.start()
    thread.join(timeout)
    
    if thread.is_alive():
        raise TimeoutError(f"读取文件超时（{timeout}秒）: {file_path}")
    
    if error:
        raise error[0]
    
    if not result:
        raise ValueError("文件读取失败")
    
    return result[0]


def inspect_pdf_file(file_path: str, timeout: int = 10, max_retries: int = 3) -> PDFInspectionResult:
    """
    检测PDF文件的主入口函数
    
    参数:
        file_path: PDF文件路径
        timeout: 读取超时秒数
        max_retries: 最大重试次数
    
    返回:
        PDFInspectionResult 对象
    
    错误码:
        E001: 输入为空
        E006: 文件不存在
        E007: 无法读取PDF内容
        E008: PDF文件损坏或无效
    """
    # E001: 输入为空
    if not file_path or not file_path.strip():
        raise ValueError("E001: 请提供待处理的PDF文件路径")
    
    # E006: 文件不存在
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"E006: 文件不存在: {file_path}")
    
    # 带重试机制读取文件
    data = None
    for attempt in range(max_retries):
        try:
            data = _read_file_with_timeout(file_path, timeout)
            break
        except TimeoutError:
            if attempt == max_retries - 1:
                raise TimeoutError(f"E007: 读取文件超时（{timeout}秒）: {file_path}")
            # 指数退避
            wait_time = 2 ** attempt
            print(f"[WARN] 读取超时，{wait_time}秒后重试（{attempt+1}/{max_retries}）", file=sys.stderr)
            time.sleep(wait_time)
        except Exception as e:
            if attempt == max_retries - 1:
                raise IOError(f"E007: 无法读取PDF内容: {str(e)}")
            wait_time = 2 ** attempt
            print(f"[WARN] 读取失败，{wait_time}秒后重试（{attempt+1}/{max_retries}）: {e}", file=sys.stderr)
            time.sleep(wait_time)
    
    if data is None:
        raise IOError("E007: 无法读取PDF内容")
    
    # 检查文件大小
    file_size = len(data)
    if file_size == 0:
        raise ValueError("E008: PDF文件为空")
    
    # 检查PDF文件头
    if not data.startswith(b"%PDF"):
        raise ValueError("E008: 不是有效的PDF文件")
