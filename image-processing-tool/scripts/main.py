#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图像批处理工具（image-processing-tool）v1.0.5
批量调整尺寸、压缩体积、转换格式。
仅依赖标准库，支持 --selftest 离线自检。
"""

import argparse
import base64
import io
import os
import struct
import sys
import zlib
import urllib.request
import urllib.error
from datetime import datetime, timezone

# 错误码定义
ERROR_CODES = {
    "E001": "参数错误：输入路径无效或不存在",
    "E002": "参数错误：不支持的图片格式",
    "E003": "处理错误：图片解码失败（文件损坏或格式不支持）",
    "E004": "处理错误：图片编码失败",
    "E005": "处理错误：尺寸调整失败",
    "E006": "处理错误：压缩失败",
    "E007": "处理错误：输出目录不可写",
    "E008": "处理错误：动图（GIF/APNG）不支持",
    "E009": "处理错误：网络请求失败（URL 拉取）",
    "E010": "内部错误：未知异常",
}


# ---------------------------------------------------------------------------
# 极简 PNG 编解码（支持灰度、RGB、RGBA、调色板类型）
# 不依赖 Pillow，使用标准库 zlib/struct 实现
# ---------------------------------------------------------------------------

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def _png_chunk(chunk_type: bytes, data: bytes) -> bytes:
    """构造一个 PNG chunk（长度 + 类型 + 数据 + CRC32）"""
    length = struct.pack(">I", len(data))
    crc = struct.pack(">I", zlib.crc32(chunk_type + data) & 0xFFFFFFFF)
    return length + chunk_type + data + crc


def _parse_png(data: bytes):
    """解析 PNG 数据，返回 (宽度, 高度, 颜色类型, 位深, 原始图像数据, 所有 chunk)"""
    if not data.startswith(PNG_SIGNATURE):
        raise ValueError("非 PNG 文件")
    pos = 8
    width = height = color_type = bit_depth = None
    chunks = []
    idat_data = b""
    palette = None
    trns_data = None

    while pos < len(data):
        length = struct.unpack(">I", data[pos:pos + 4])[0]
        chunk_type = data[pos + 4:pos + 8]
        chunk_data = data[pos + 8:pos + 8 + length]
        chunks.append((chunk_type, chunk_data))

        if chunk_type == b"IHDR":
            width, height, bit_depth, color_type = struct.unpack(">IIBB", chunk_data[:10])
        elif chunk_type == b"IDAT":
            idat_data += chunk_data
        elif chunk_type == b"PLTE":
            palette = chunk_data
        elif chunk_type == b"tRNS":
            trns_data = chunk_data

        pos += 12 + length

    if width is None or height is None:
        raise ValueError("PNG 缺少 IHDR")

    # 检查是否 interlaced
    if len(chunks) > 0:
        for ct, cd in chunks:
            if ct == b"IHDR" and len(cd) >= 13:
                interlace = cd[12]
                if interlace != 0:
                    raise ValueError("不支持 interlaced PNG")

    # 解压 IDAT（修复：使用 decompressobj 连续喂入所有 IDAT 块）
    decompressor = zlib.decompressobj()
    raw = b""
    for ct, cd in chunks:
        if ct == b"IDAT":
            try:
                raw += decompressor.decompress(cd)
            except zlib.error as e:
                raise ValueError(f"IDAT 解压失败: {e}")

    # 处理剩余的解压数据
    try:
        raw += decompressor.flush()
    except zlib.error as e:
        raise ValueError(f"IDAT 解压失败: {e}")

    # 根据颜色类型计算每像素字节数
    if color_type == 0:  # 灰度
        channels = 1
        bytes_per_pixel = channels * (bit_depth // 8)
    elif color_type == 2:  # 真彩 RGB
        channels = 3
        bytes_per_pixel = channels * (bit_depth // 8)
    elif color_type == 3:  # 调色板
        channels = 1
        bytes_per_pixel = 1
    elif color_type == 4:  # 灰度+alpha
        channels = 2
        bytes_per_pixel = channels * (bit_depth // 8)
    elif color_type == 6:  # RGBA
        channels = 4
        bytes_per_pixel = channels * (bit_depth // 8)
    else:
        raise ValueError(f"不支持的 PNG 颜色类型: {color_type}")

    # 校验解压后数据长度
    expected_len = height * (1 + width * bytes_per_pixel)
    if len(raw) != expected_len:
        raise ValueError(
            f"PNG 数据长度不匹配: 期望 {expected_len} 字节, 实际 {len(raw)} 字节"
        )

    # 解析滤波后的扫描线
    stride = width * bytes_per_pixel
    pixels = bytearray()
    prev_line = bytearray(stride)

    pos = 0
    for y in range(height):
        if pos >= len(raw):
            raise ValueError("PNG 数据不完整")
        filter_type = raw[pos]
        pos += 1
        line = bytearray(raw[pos:pos + stride])
        pos += stride

        # 反滤波
        if filter_type == 0:  # None
            pass
        elif filter_type == 1:  # Sub
            for i in range(bytes_per_pixel, stride):
                line[i] = (line[i] + line[i - bytes_per_pixel]) & 0xFF
        elif filter_type == 2:  # Up
            for i in range(stride):
                line[i] = (line[i] + prev_line[i]) & 0xFF
        elif filter_type == 3:  # Average
            for i in range(stride):
                left = line[i - bytes_per_pixel] if i >= bytes_per_pixel else 0
                up = prev_line[i]
                line[i] = (line[i] + ((left + up) >> 1)) & 0xFF
        elif filter_type == 4:  # Paeth
            for i in range(stride):
                left = line[i - bytes_per_pixel] if i >= bytes_per_pixel else 0
                up = prev_line[i]
                up_left = prev_line[i - bytes_per_pixel] if i >= bytes_per_pixel else 0
                p = left + up - up_left
                pa = abs(p - left)
                pb = abs(p - up)
                pc = abs(p - up_left)
                if pa <= pb and pa <= pc:
                    pred = left
                elif pb <= pc:
                    pred = up
                else:
                    pred = up_left
                line[i] = (line[i] + pred) & 0xFF
        else:
            raise ValueError(f"未知 PNG 滤波类型: {filter_type}")

        pixels.extend(line)
        prev_line = line

    return width, height, color_type, bit_depth, bytes(pixels), chunks, palette, trns_data


def _encode_png(width: int, height: int, pixels: bytes, color_type: int = 2,
                bit_depth: int = 8) -> bytes:
    """将原始像素编码为 PNG 数据。pixels 为 RGB（color_type=2）或 RGBA（color_type=6）"""
    channels = 3 if color_type == 2 else 4
    bytes_per_pixel = channels * (bit_depth // 8)
    stride = width * bytes_per_pixel

    # 添加滤波类型字节（全部用 None 滤波）
    raw = bytearray()
    for y in range(height):
        raw.append(0)  # filter type 0 (None)
        start = y * stride
        raw.extend(pixels[start:start + stride])

    compressed = zlib.compress(bytes(raw))

    ihdr_data = struct.pack(">IIBBBBB", width, height, bit_depth, color_type, 0, 0, 0)
    chunks = [
        b"\x89PNG\r\n\x1a\n",
        _png_chunk(b"IHDR", ihdr_data),
        _png_chunk(b"IDAT", compressed),
        _png_chunk(b"IEND", b""),
    ]
    return b"".join(chunks)


# ---------------------------------------------------------------------------
# 极简 JPEG 解析（仅用于识别，不做完整解码）
# ---------------------------------------------------------------------------

def _is_jpeg(data: bytes) -> bool:
    """检测是否为 JPEG 文件（仅检查 SOI 和 EOI 标记）"""
    return len(data) > 4 and data[0:2] == b"\xff\xd8" and data[-2:] == b"\xff\xd9"


def _jpeg_dimensions(data: bytes):
    """从 JPEG 数据中提取宽高（解析 SOF 标记）"""
    pos = 2
    while pos < len(data) - 1:
        if data[pos] != 0xFF:
            pos += 1
            continue
        marker = data[pos + 1]
        if marker in (0xD8, 0xD9) or 0xD0 <= marker <= 0xD7:
            pos += 2
            continue
        if pos + 4 > len(data):
            break
        seg_len = struct.unpack(">H", data[pos + 2:pos + 4])[0]
        if marker in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
            if pos + 9 <= len(data):
                height = struct.unpack(">H", data[pos + 5:pos + 7])[0]
                width = struct.unpack(">H", data[pos + 7:pos + 9])[0]
                return width, height
        pos += 2 + seg_len
    raise ValueError("无法解析 JPEG 尺寸")


# ---------------------------------------------------------------------------
# 极简 BMP 编解码（24 位真彩）
# ---------------------------------------------------------------------------

def _is_bmp(data: bytes) -> bool:
    return len(data) > 2 and data[0:2] == b"BM"


def _parse_bmp(data: bytes):
    """解析 24 位 BMP，返回 (宽度, 高度, RGB像素)"""
    if not _is_bmp(data):
        raise ValueError("非 BMP 文件")
    # 读取文件头
    pixel_offset = struct.unpack("<I", data[10:14])[0]
    width = struct.unpack("<i", data[18:22])[0]
    height = struct.unpack("<i", data[22:26])[0]
    bpp = struct.unpack("<H", data[28:30])[0]

    if bpp != 24:
        raise ValueError(f"仅支持 24 位 BMP，当前: {bpp}")

    abs_height = abs(height)
    row_size = ((width * 3 + 3) // 4) * 4
    pixels = bytearray()

    for y in range(abs_height):
        # BMP 行序：自底向上（height>0）或自顶向下（height<0）
        src_y = y if height < 0 else abs_height - 1 - y
        row_start = pixel_offset + src_y * row_size
        row = data[row_start:row_start + width * 3]
        # BGR -> RGB
        for i in range(width):
            b, g, r = row[i * 3], row[i * 3 + 1], row[i * 3 + 2]
            pixels.extend((r, g, b))

    return width, abs_height, bytes(pixels)


def _encode_bmp(width: int, height: int, rgb_pixels: bytes) -> bytes:
    """将 RGB 像素编码为 24 位 BMP"""
    row_size = ((width * 3 + 3) // 4) * 4
    padding = row_size - width * 3
    pixel_data_size = row_size * height
    file_size = 54 + pixel_data_size

    header = bytearray()
    header.extend(b"BM")
    header.extend(struct.pack("<I", file_size))
    header.extend(struct.pack("<H", 0))
    header.extend(struct.pack("<H", 0))
    header.extend(struct.pack("<I", 54))
    header.extend(struct.pack("<I", 40))
    header.extend(struct.pack("<i", width))
    header.extend(struct.pack("<i", height))
    header.extend(struct.pack("<H", 1))
    header.extend(struct.pack("<H", 24))
    header.extend(struct.pack("<I", 0))
    header.extend(struct.pack("<I", pixel_data_size))
    header.extend(struct.pack("<i", 2835))
    header.extend(struct.pack("<i", 2835))
    header.extend(struct.pack("<I", 0))
    header.extend(struct.pack("<I", 0))

    # 像素数据（自底向上）
    pixel_data = bytearray()
    for y in range(height - 1, -1, -1):
        row_start = y * width * 3
        for i in range(width):
            r, g, b = rgb_pixels[row_start + i * 3], rgb_pixels[row_start + i * 3 + 1], rgb_pixels[row_start + i * 3 + 2]
            pixel_data.extend((b, g, r))
        pixel_data.extend(b"\x00" * padding)

    return bytes(header) + bytes(pixel_data)


# ---------------------------------------------------------------------------
# 核心图像类
# ---------------------------------------------------------------------------

class Image:
    """统一图像表示：RGB 像素 + 宽高"""

    def __init__(self, width: int, height: int, rgb_pixels: bytes):
        self.width = width
        self.height = height
        self.rgb_pixels = rgb_pixels  # 每像素 3 字节 RGB

    @classmethod
    def from_bytes(cls, data: bytes) -> "Image":
        """从字节数据解码图片"""
        try:
            if data.startswith(PNG_SIGNATURE):
                w, h, ct, bd, pixels, chunks, palette, trns = _parse_png(data)
                if ct == 0:  # 灰度转 RGB
                    rgb = bytearray()
                    for p in pixels:
                        rgb.extend((p, p, p))
                    return cls(w, h, bytes(rgb))
                elif ct == 2:  # RGB
                    return cls(w, h, pixels)
                elif ct == 3:  # 调色板
                    if palette is None:
                        raise ValueError("调色板 PNG 缺少 PLTE chunk")
                    rgb = bytearray()
                    for idx in pixels:
                        if idx * 3 + 2 < len(palette):
                            r, g, b = palette[idx * 3], palette[idx * 3 + 1], palette[idx * 3 + 2]
                            rgb.extend((r, g, b))
                        else:
                            raise ValueError("调色板索引越界")
                    return cls(w, h, bytes(rgb))
                elif ct == 4:  # 灰度+alpha 转 RGB
                    rgb = bytearray()
                    for i in range(0, len(pixels), 2):
                        gray = pixels[i]
                        rgb.extend((gray, gray, gray))
                    return cls(w, h, bytes(rgb))
                elif ct == 6:  # RGBA 转 RGB（丢弃 alpha）
                    rgb = bytearray()
                    for i in range(0, len(pixels), 4):
                        rgb.extend(pixels[i:i + 3])
                    return cls(w, h, bytes(rgb))
                else:
                    raise ValueError(f"不支持的颜色类型: {ct}")
            elif _is_jpeg(data):
                w, h = _jpeg_dimensions(data)
                raise ValueError("JPEG 解码需要 Pillow 库：pip install Pillow")
            elif _is_bmp(data):
                w, h, pixels = _parse_bmp(data)
                return cls(w, h, pixels)
            else:
                raise ValueError("无法识别的图片格式")
        except ValueError as e:
            raise ValueError(f"{ERROR_CODES['E003']}: {e}")

    def to_bytes(self, fmt: str, quality: int = 85) -> bytes:
        """编码为指定格式。fmt: png/bmp/jpeg"""
        fmt = fmt.lower()
        if fmt == "png":
            return _encode_png(self.width, self.height, self.rgb_pixels, color_type=2)
        elif fmt == "bmp":
            return _encode_bmp(self.width, self.height, self.rgb_pixels)
        elif fmt in ("jpg", "jpeg"):
            raise ValueError("JPEG 编码需要 Pillow 库：pip install Pillow")
        else:
            raise ValueError(ERROR_CODES["E002"])

    def resize(self, width: int, height: int) -> "Image":
        """最近邻缩放"""
        if width <= 0 or height <= 0:
            raise ValueError(ERROR_CODES["E005"])
        src_w, src_h = self.width, self.height
        dst = bytearray(width * height * 3)
        for y in range(height):
            src_y = min(int(y * src_h / height), src_h - 1)
            for x in range(width):
                src_x = min(int(x * src_w / width), src_w - 1)
                src_idx = (src_y * src_w + src_x) * 3
                dst_idx = (y * width + x) * 3
                dst[dst_idx] = self.rgb_pixels[src_idx]
                dst[dst_idx + 1] = self.rgb_pixels[src_idx + 1]
                dst[dst_idx + 2]
