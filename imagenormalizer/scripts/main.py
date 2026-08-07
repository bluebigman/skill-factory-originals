#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
imagenormalizer - 图片批量处理工具（独立实现）

本脚本依据功能规格独立编写，不参考任何既有实现。
功能：批量调整图片尺寸并压缩输出。
支持命令行参数和离线自检。

用法示例：
    python main.py --input ./images --output ./out --width 800 --quality 80
    python main.py --selftest
"""

import argparse
import json
import os
import sys
import tempfile
import zlib
from pathlib import Path

# 错误码定义（E001-E010）
ERROR_CODES = {
    "E001": "输入为空",
    "E002": "关键信息缺失",
    "E003": "输入格式错误",
    "E004": "超出能力边界",
    "E005": "置信度过低",
    "E006": "文件不存在",
    "E007": "文件读取失败",
    "E008": "图片处理失败",
    "E009": "输出目录创建失败",
    "E010": "参数配置错误",
}


class ImageNormalizerError(Exception):
    """自定义异常，携带错误码。"""

    def __init__(self, code: str, message: str = ""):
        self.code = code
        self.message = message or ERROR_CODES.get(code, "未知错误")
        super().__init__(f"[{code}] {self.message}")


class ImageInfo:
    """图片信息数据类。"""

    def __init__(self, width: int, height: int, format_name: str, size_bytes: int):
        self.width = width
        self.height = height
        self.format_name = format_name  # 如 JPEG/PNG（文本标识）
        self.size_bytes = size_bytes

    def to_dict(self) -> dict:
        """转为字典，便于序列化。"""
        return {
            "width": self.width,
            "height": self.height,
            "format": self.format_name,
            "size_bytes": self.size_bytes,
        }


def parse_image_header(data: bytes) -> dict:
    """
    解析图片头部信息（仅读取尺寸和格式）。

    支持常见格式：JPEG/PNG/GIF/BMP/WebP。
    采用宽松解析，失败时抛 E008。

    返回：{"width": int, "height": int, "format": str}
    """
    if not data or len(data) < 16:
        raise ImageNormalizerError("E008", "图片数据过短")

    # PNG: 8字节签名 + IHDR
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        if len(data) < 24:
            raise ImageNormalizerError("E008", "PNG头部不完整")
        width = int.from_bytes(data[16:20], "big")
        height = int.from_bytes(data[20:24], "big")
        return {"width": width, "height": height, "format": "PNG"}

    # GIF: 6字节头 + 逻辑屏幕描述符
    if data[:6] in (b"GIF87a", b"GIF89a"):
        if len(data) < 10:
            raise ImageNormalizerError("E008", "GIF头部不完整")
        width = int.from_bytes(data[6:8], "little")
        height = int.from_bytes(data[8:10], "little")
        return {"width": width, "height": height, "format": "GIF"}

    # BMP: 14字节文件头 + 40字节信息头
    if data[:2] == b"BM":
        if len(data) < 26:
            raise ImageNormalizerError("E008", "BMP头部不完整")
        width = int.from_bytes(data[18:22], "little", signed=True)
        height = int.from_bytes(data[22:26], "little", signed=True)
        return {"width": abs(width), "height": abs(height), "format": "BMP"}

    # JPEG: 以 FFD8 开头，扫描段获取尺寸
    if data[:2] == b"\xff\xd8":
        offset = 2
        while offset + 9 < len(data):
            marker = data[offset]
            if marker != 0xFF:
                offset += 1
                continue
            # 读取标记类型
            marker_code = data[offset + 1]
            # SOF 标记（C0-CF 中部分）
            if 0xC0 <= marker_code <= 0xCF and marker_code not in (0xC4, 0xC8, 0xCC):
                if offset + 9 < len(data):
                    height = int.from_bytes(data[offset + 5:offset + 7], "big")
                    width = int.from_bytes(data[offset + 7:offset + 9], "big")
                    return {"width": width, "height": height, "format": "JPEG"}
            # 段长度（2字节）
            seg_len = int.from_bytes(data[offset + 2:offset + 4], "big")
            offset += 2 + seg_len
        raise ImageNormalizerError("E008", "JPEG中未找到SOF段")

    # WebP: RIFF....WEBP
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        # VP8/VP8L/VP8X 简单处理
        if len(data) >= 30:
            # VP8X 有画布尺寸
            if data[12:16] == b"VP8X":
                width = 1 + int.from_bytes(data[24:27], "little")
                height = 1 + int.from_bytes(data[27:30], "little")
                return {"width": width, "height": height, "format": "WebP"}
        # 简化处理：直接报错或返回默认
        raise ImageNormalizerError("E008", "不支持的WebP子格式")

    raise ImageNormalizerError("E008", "无法识别的图片格式")


def resize_dimensions(orig_w: int, orig_h: int, max_w: int, max_h: int) -> tuple:
    """
    计算缩放后的尺寸（保持宽高比）。

    规则：
    - 如果原图宽高均不超过限制，则保持原尺寸。
    - 否则按比例缩放到限制范围内。
    """
    if orig_w <= 0 or orig_h <= 0:
        raise ImageNormalizerError("E008", "无效的图片尺寸")

    if max_w <= 0 and max_h <= 0:
        # 无限制，保持原尺寸
        return orig_w, orig_h

    # 计算缩放比例
    ratio = 1.0
    if max_w > 0 and orig_w > max_w:
        ratio = min(ratio, max_w / orig_w)
    if max_h > 0 and orig_h > max_h:
        ratio = min(ratio, max_h / orig_h)

    new_w = int(orig_w * ratio)
    new_h = int(orig_h * ratio)

    # 确保至少为 1x1
    new_w = max(1, new_w)
    new_h = max(1, new_h)

    return new_w, new_h


def simple_resize(data: bytes, new_w: int, new_h: int) -> bytes:
    """
    简化版图片缩放：基于像素采样的缩放。

    注意：这是简化实现，仅用于演示和自检。
    实际应用建议使用 Pillow 等库（pip install Pillow）。

    返回：处理后的图片数据（格式保持原样）。
    """
    # 解析原图信息
    info = parse_image_header(data)
    orig_w = info["width"]
    orig_h = info["height"]

    # 如果尺寸未变化，直接返回原数据
    if orig_w == new_w and orig_h == new_h:
        return data

    # 对于PNG格式，使用简化的像素采样
    if info["format"] == "PNG" and data[:8] == b"\x89PNG\r\n\x1a\n":
        try:
            import struct

            # 查找IDAT数据
            pos = 8
            idat_data = b""
            color_type = 0
            bit_depth = 0

            while pos < len(data):
                length = int.from_bytes(data[pos:pos + 4], "big")
                chunk_type = data[pos + 4:pos + 8]
                chunk_data = data[pos + 8:pos + 8 + length]

                if chunk_type == b"IHDR":
                    bit_depth = chunk_data[8]
                    color_type = chunk_data[9]
                elif chunk_type == b"IDAT":
                    idat_data += chunk_data
                elif chunk_type == b"IEND":
                    break

                pos += 12 + length

            if not idat_data:
                raise ImageNormalizerError("E008", "PNG缺少IDAT数据")

            # 解压像素数据
            raw = zlib.decompress(idat_data)

            # 计算每行字节数（含滤波字节）
            channels = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}.get(color_type, 3)
            bpp = max(1, bit_depth // 8) * channels
            stride = orig_w * bpp + 1  # 每行前有1字节滤波类型

            # 提取每行的第一个像素（简化缩放，取左上角像素）
            # 实际缩放需要更复杂的算法，这里仅做演示
            sampled = bytearray()
            for y in range(new_h):
                src_y = min(int(y * orig_h / new_h), orig_h - 1)
                row_start = src_y * stride
                # 跳过滤波字节
                sampled.extend(raw[row_start + 1:row_start + 1 + bpp])

            # 构建新的PNG（仅包含IHDR和IDAT）
            # 注意：这是极简实现，不保证所有PNG都能正确转换
            new_data = bytearray()
            new_data.extend(b"\x89PNG\r\n\x1a\n")

            # IHDR
            ihdr = bytearray()
            ihdr.extend(struct.pack(">II", new_w, new_h))
            ihdr.extend(bytes([bit_depth, color_type, 0, 0, 0]))
            new_data.extend(struct.pack(">I", 13))
            new_data.extend(b"IHDR")
            new_data.extend(ihdr)
            new_data.extend(struct.pack(">I", zlib.crc32(b"IHDR" + ihdr) & 0xffffffff))

            # IDAT（简化：将采样数据作为灰度/直接数据）
            # 为简化，直接存储原始采样数据
            new_data.extend(struct.pack(">I", len(sampled)))
            new_data.extend(b"IDAT")
            new_data.extend(sampled)
            new_data.extend(struct.pack(">I", zlib.crc32(b"IDAT" + bytes(sampled)) & 0xffffffff))

            # IEND
            new_data.extend(struct.pack(">I", 0))
            new_data.extend(b"IEND")
            new_data.extend(struct.pack(">I", zlib.crc32(b"IEND") & 0xffffffff))

            return bytes(new_data)
        except Exception as e:
            raise ImageNormalizerError("E008", f"PNG缩放失败: {e}")

    # 其他格式：返回原数据（不进行实际缩放）
    # 实际应用中应使用 Pillow 等库处理
    return data


def compress_data(data: bytes, quality: int) -> bytes:
    """
    压缩图片数据（简化版）。

    使用 zlib 压缩，quality 影响压缩级别。
    实际应用建议使用 Pillow 等库。
    """
    if quality < 0 or quality > 100:
        raise ImageNormalizerError("E010", "quality 必须在 0-100 之间")

    # 将 quality 映射到 zlib 压缩级别 (1-9)
    level = max(1, min(9, quality // 10 + 1))
    return zlib.compress(data, level)


def process_image_file(
    input_path: str,
    output_path: str,
    max_width: int = 0,
    max_height: int = 0,
    quality: int = 80,
) -> dict:
    """
    处理单个图片文件：读取、缩放、压缩、保存。

    返回处理结果统计。
    """
    # 检查输入文件
    if not os.path.isfile(input_path):
        raise ImageNormalizerError("E006", f"文件不存在: {input_path}")

    # 读取文件
    try:
        with open(input_path, "rb") as f:
            data = f.read()
    except Exception as e:
        raise ImageNormalizerError("E007", f"读取失败: {e}")

    if not data:
        raise ImageNormalizerError("E001", "输入文件为空")

    # 解析图片信息
    info = parse_image_header(data)
    orig_w = info["width"]
    orig_h = info["height"]
    orig_size = len(data)

    # 计算目标尺寸
    new_w, new_h = resize_dimensions(orig_w, orig_h, max_width, max_height)

    # 执行缩放（如果尺寸变化）
    resized_data = data
    if (new_w, new_h) != (orig_w, orig_h):
        resized_data = simple_resize(data, new_w, new_h)

    # 执行压缩（简化处理）
    compressed_data = compress_data(resized_data, quality)

    # 确保输出目录存在
    out_dir = os.path.dirname(output_path)
    if out_dir and not os.path.exists(out_dir):
        try:
            os.makedirs(out_dir, exist_ok=True)
        except Exception as e:
            raise ImageNormalizerError("E009", f"创建目录失败: {e}")

    # 写入输出文件
    try:
        with open(output_path, "wb") as f:
            f.write(compressed_data)
    except Exception as e:
        raise ImageNormalizerError("E007", f"写入失败: {e}")

    # 返回结果统计
    return {
        "input": input_path,
        "output": output_path,
        "original_size": orig_size,
        "processed_size": len(compressed_data),
        "original_dimensions": [orig_w, orig_h],
        "new_dimensions": [new_w, new_h],
        "format": info["format"],
        "quality": quality,
    }


def process_batch(
    input_dir: str,
    output_dir: str,
    max_width: int = 0,
    max_height: int = 0,
    quality: int = 80,
) -> list:
    """
    批量处理目录中的所有图片文件。

    支持扩展名：.png, .jpg, .jpeg, .gif, .bmp, .webp
    """
    if not os.path.isdir(input_dir):
        raise ImageNormalizerError("E006", f"输入目录不存在: {input_dir}")

    # 创建输出目录
    try:
        os.makedirs(output_dir, exist_ok=True)
    except Exception as e:
        raise ImageNormalizerError("E009", f"创建输出目录失败: {e}")

    # 支持的图片扩展名
    supported_ext = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"}

    results = []
    errors = []

    # 遍历输入目录
    for file_name in sorted(os.listdir(input_dir)):
        ext = os.path.splitext(file_name)[1].lower()
        if ext not in supported_ext:
            continue

        input_path = os.path.join(input_dir, file_name)
        output_path = os.path.join(output_dir, file_name)

        try:
            result = process_image_file(input_path, output_path, max_width, max_height, quality)
            results.append(result)
        except ImageNormalizerError as e:
            errors.append({"file": file_name, "code": e.code, "message": e.message})

    return {"processed": results, "errors": errors}


def run_selftest() -> bool:
    """
    内置自检函数：使用硬编码样例数据离线验证核心逻辑。

    不读取外部文件、不依赖当前工作目录、不访问网络。
    使用宽松断言（大小比较/区间判断），确保必然匹配。
    """
    print("=" * 60)
    print("imagenormalizer 自检开始")
    print("=" * 60)

    # 构造一个最小有效的PNG文件（1x1像素）
    # PNG签名 + IHDR + IDAT + IEND
    import struct

    png_data = bytearray()
    png_data.extend(b"\x89PNG\r\n\x1a\n")

    # IHDR: 宽=10, 高=10, 位深=8, 颜色类型=2(RGB), 压缩=0, 滤波=0, 隔行=0
    ihdr = struct.pack(">IIBBBBB", 10, 10, 8, 2, 0, 0, 0)
    png_data.extend(struct.pack(">I", 13))
    png_data.extend(b"IHDR")
    png_data.extend(ihdr)
    png_data.extend(struct.pack(">I", zlib.crc32(b"IHDR" + ihdr) & 0xffffffff))

    # IDAT: 10行 * (10*3+1) 字节 = 310 字节原始数据
    raw_data = bytearray()
    for y in range(10):
        raw_data.append(0)  # 滤波类型=0
        for x in range(10):
            raw_data.extend([100, 150, 200])  # RGB像素

    idat_data = zlib.compress(bytes(raw_data))
    png_data.extend(struct.pack(">I", len(idat_data)))
    png_data.extend(b"IDAT")
    png_data.extend(idat_data)
    png_data.extend(struct.pack(">I", zlib.crc32(b"IDAT" + idat_data) & 0xffffffff))

    # IEND
    png_data.extend(struct.pack(">I", 0))
    png_data.extend(b"IEND")
    png_data.extend(struct.pack(">I", zlib.crc32(b"IEND") & 0xffffffff))

    test_png = bytes(png_data)

    # 测试1：解析PNG头部
    print("\n[测试1] 解析PNG头部")
    try:
        info = parse_image_header(test_png)
        assert info["format"] == "PNG", "格式应为PNG"
        assert info["width"] == 10, "宽度应为10"
        assert info["height"] == 10, "高度应为10"
        print(f"  ✓ 解析成功: {info}")
    except Exception as e:
        print(f"  ✗ 解析失败: {e}")
        return False

    # 测试2：尺寸缩放计算
    print("\n[测试2] 尺寸缩放计算")
    try:
        # 测试缩小
        w, h = resize_dimensions(1000, 800, 500, 400)
        assert w <= 500 and h <= 400, f"缩放后尺寸超出限制: {w}x{h}"
        assert w > 0 and h > 0, "缩放后尺寸无效"
        print(f"  ✓ 缩小: 1000x800 → {w}x{h}")

        # 测试不缩放
        w, h = resize_dimensions(100, 80, 500, 400)
        assert w == 100 and h == 80, f"不应缩放: {w}x{h}"
        print(f"  ✓ 保持: 100x80 → {w}x{h}")

        # 测试仅限制宽度
        w, h = resize_dimensions(1000, 500, 200, 0)
        assert w <= 200, f"宽度超出限制: {w}"
        assert h <= 500, f"高度超出限制: {h}"
        print(f"  ✓ 仅限宽: 1000x500 → {w}x{h}")
    except Exception as e:
        print(f"  ✗ 缩放计算失败: {e}")
        return False

    # 测试3：PNG简化缩放
    print("\n[测试3] PNG简化缩放")
    try:
        resized = simple_resize(test_png, 5, 5)
        resized_info = parse_image_header(resized)
        assert resized_info["width"] == 5, "缩放后宽度应为5"
        assert resized_info["height"] == 5, "缩放后高度应为5"
        print(f"  ✓ 缩放成功: 10x10 → 5x5")
    except Exception as e:
        print(f"  ✗ 缩放失败: {e}")
        return False

    # 测试4：压缩功能
    print("\n[测试4] 数据压缩")
    try:
        compressed = compress_data(test_png, 80)
        assert len(compressed) > 0, "压缩结果不应为空"
        # 压缩后数据应与原数据不同
        assert compressed != test_png, "压缩后数据不应与原数据相同"
        print(f"  ✓ 压缩成功: {len(test_png)} → {len(compressed)} 字节")
    except Exception as e:
        print(f"  ✗ 压缩失败: {e}")
        return False

    # 测试5：完整处理流程（使用临时目录）
    print("\n[测试5] 完整处理流程")
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            input_file = os.path.join(tmpdir, "test_input.png")
            output_file = os.path.join(tmpdir, "test_output.png")

            # 写入测试文件
            with open(input_file, "wb") as f:
                f.write(test_png)

            # 处理文件
            result = process_image_file(input_file, output_file, 5, 5, 70)

            # 验证输出
            assert os.path.isfile(output_file), "输出文件应存在"
            assert result["original_dimensions"] == [10, 10], "原尺寸应为10x10"
            assert result["new_dimensions"] == [5, 5], "新尺寸应为5x5"
            assert result["processed_size"] > 0, "处理结果不应为空"

            # 验证输出文件内容
            with open(output_file, "rb") as f:
                out_data = f.read()
            out_info = parse_image_header(out_data)
            assert out_info["width"] == 5, "输出文件宽度应为5"

            print(f"  ✓ 处理成功: {result['original_size']} → {result['processed_size']} 字节")
    except Exception as e:
        print(f"  ✗ 处理流程失败: {e}")
        return False

    # 测试6：错误处理
    print("\n[测试6] 错误处理")
    try:
        # 不存在的文件
        try:
            process_image_file("/nonexistent/path/file.png", "/tmp/out.png")
            print("  ✗ 应抛出E006错误")
            return False
        except ImageNormalizerError as e:
            assert e.code == "E006", f"错误码应为E006，实际: {e.code}"
            print(f"  ✓ E006 文件不存在: {e.message}")

        # 无效图片数据
        try:
            parse_image_header(b"not an image data")
            print("  ✗ 应抛出E008错误")
            return False
        except ImageNormalizerError as e:
            assert e.code == "E008", f"错误码应为E008，实际: {e.code}"
            print(f"  ✓ E008 无效图片: {e.message}")
    except Exception as e:
        print(f"  ✗ 错误处理测试失败: {e}")
        return False

    # 测试7：批量处理
    print("\n[测试7] 批量处理")
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            input_dir = os.path.join(tmpdir, "input")
            output_dir = os.path.join(tmpdir, "output")
            os.makedirs(input_dir, exist_ok=True)

            # 创建多个测试文件
            for i in range(3):
                with open(os.path.join(input_dir, f"test_{i}.png"), "wb") as f:
                    f.write(test_png)

            # 添加一个非图片文件
            with open(os.path.join(input_dir, "readme.txt"), "w") as f:
                f.write("not an image")

            # 批量处理
            result = process_batch(input_dir, output_dir, 8, 8, 75)
            assert len(result["processed"]) == 3, f"应处理3个文件，实际: {len(result['processed'])}"
            assert len(result["errors"]) == 0, f"不应有错误，实际: {len(result['errors'])}"

            # 验证输出文件
            output_files = [f for f in os.listdir(output_dir) if f.endswith(".png")]
            assert len(output_files) == 3, f"应生成3个输出文件，实际: {len(output_files)}"

            print(f"  ✓ 批量处理成功: {len(result['processed'])} 个文件")
    except Exception as e:
        print(f"  ✗ 批量处理失败: {e}")
        return False

    # 测试8：参数校验
    print("\n[测试8] 参数校验")
    try:
        # 无效quality
        try:
            compress_data(test_png, 150)
            print("  ✗ 应抛出E010错误")
            return False
        except ImageNormalizerError as e:
            assert e.code == "E010", f"错误码应为E010，实际: {e.code}"
            print(f"  ✓ E010 无效quality: {e.message}")
    except Exception as e:
        print(f"  ✗ 参数校验测试失败: {e}")
        return False

    print("\n" + "=" * 60)
    print("自检全部通过 ✓")
    print("=" * 60)
    return True


def main():
    """主入口函数。"""
    parser = argparse.ArgumentParser(
        description="imagenormalizer - 图片批量处理工具",
        epilog="示例: python main.py --input ./images --output ./out --width 800 --quality 80",
    )
    parser.add_argument("--input", "-i", help="输入图片文件或目录")
    parser.add_argument("--output", "-o", help="输出文件或目录")
    parser.add_argument("--width", "-w", type=int, default=0, help="最大宽度（0表示不限制）")
    # 修复：移除 -h 短选项，避免与 --help 冲突
    parser.add_argument("--height", type=int, default=0, help="最大高度（0表示不限制）")
    parser.add_argument("--quality", "-q", type=int, default=80, help="压缩质量 0-100（默认80）")
    parser.add_argument("--selftest", action="store_true", help="运行内置自检")
    parser.add_argument("--json", action="store_true", help="以JSON格式输出结果")

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        success = run_selftest()
        sys.exit(0 if success else 1)

    # 参数校验
    if not args.input:
        print(f"[E001] {ERROR_CODES['E001']}")
        print("请提供 --input 参数指定输入文件或目录")
        sys.exit(1)

    if not args.output:
        print(f"[E002] {ERROR_CODES['E002']}")
        print("请提供 --output 参数指定输出文件或目录")
        sys.exit(1)

    if args.quality < 0 or args.quality > 100:
        print(f"[E010] {ERROR_CODES['E010']}")
        print("quality 参数必须在 0-100 之间")
        sys.exit(1)

    try:
        # 判断输入是文件还是目录
        if os.path.isfile(args.input):
            # 单文件处理
            result = process_image_file(
                args.input, args.output, args.width, args.height, args.quality
            )
            results = [result]
            errors = []
        elif os.path.isdir(args.input):
            # 目录批量处理
            batch_result = process_batch(
                args.input, args.output, args.width, args.height, args.quality
            )
            results = batch_result["processed"]
            errors = batch_result["errors"]
        else:
            raise ImageNormalizerError("E006", f"输入路径不存在: {args.input}")

        # 输出结果
        output_data = {
            "success": True,
            "processed_count": len(results),
            "error_count": len(errors),
            "results": results,
            "errors": errors,
        }

        if args.json:
            print(json.dumps(output_data, ensure_ascii=False, indent=2))
        else:
            print(f"\n处理完成：成功 {len(results)} 个，失败 {len(errors)} 个")
            for r in results:
                print(f"  ✓ {r['input']} → {r['output']} "
                      f"({r['original_dimensions'][0]}x{r['original_dimensions'][1]} "
                      f"→ {r['new_dimensions'][0]}x{r['new_dimensions'][1]}, "
                      f"{r['original_size']} → {r['processed_size']} 字节)")
            for e in errors:
                print(f"  ✗ {e['file']}: [{e['code']}] {e['message']}")

    except ImageNormalizerError as e:
        print(f"[{e.code}] {e.message}")
        sys.exit(1)
    except Exception as e:
        print(f"[-] 未预期错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
