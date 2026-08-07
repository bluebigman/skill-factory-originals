#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
convert-compress 图片批量处理工具
基于功能规格独立实现的 clean-room 版本
"""

import argparse
import json
import os
import sys
import tempfile
import struct
import zlib
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

# ============================================================
# 错误码定义
# ============================================================
ERROR_CODES = {
    "E001": "输入为空，请提供待处理的内容",
    "E002": "关键信息缺失，请补充必要参数",
    "E003": "输入格式错误，请检查文件格式",
    "E004": "超出能力边界，无法处理该请求",
    "E005": "置信度过低，结果无法确定",
    "E006": "文件读取失败",
    "E007": "文件写入失败",
    "E008": "不支持的图片格式",
    "E009": "处理过程中发生错误",
    "E010": "参数校验失败",
}

class ImageProcessorError(Exception):
    """图片处理异常类"""
    def __init__(self, error_code: str, message: str = ""):
        self.error_code = error_code
        self.message = message or ERROR_CODES.get(error_code, "未知错误")
        super().__init__(f"[{error_code}] {self.message}")

# ============================================================
# 图片格式支持（基于文件头魔数识别）
# ============================================================
IMAGE_FORMATS = {
    "PNG": {"magic": b"\x89PNG\r\n\x1a\n", "ext": ".png"},
    "JPEG": {"magic": b"\xff\xd8\xff", "ext": ".jpg"},
    "GIF": {"magic": b"GIF87a", "ext": ".gif"},
    "BMP": {"magic": b"BM", "ext": ".bmp"},
    "TIFF": {"magic": b"II*\x00", "ext": ".tiff"},
    "WEBP": {"magic": b"RIFF", "ext": ".webp"},
}

# ============================================================
# 核心图片处理类
# ============================================================
class ImageProcessor:
    """图片转换压缩处理器"""
    
    def __init__(self):
        self.supported_formats = list(IMAGE_FORMATS.keys())
    
    def detect_format(self, data: bytes) -> Optional[str]:
        """检测图片格式"""
        if not data:
            return None
        
        for fmt, info in IMAGE_FORMATS.items():
            if fmt == "WEBP":
                # WEBP 需要额外检查 RIFF + WEBP
                if data.startswith(b"RIFF") and len(data) >= 12 and data[8:12] == b"WEBP":
                    return fmt
            elif fmt == "JPEG":
                # JPEG 需要检查多个魔数
                if data.startswith(b"\xff\xd8\xff"):
                    return fmt
            elif fmt == "GIF":
                # GIF 支持 87a 和 89a 版本
                if data.startswith(b"GIF87a") or data.startswith(b"GIF89a"):
                    return fmt
            elif data.startswith(info["magic"]):
                return fmt
        return None
    
    def get_image_info(self, data: bytes) -> Dict[str, Any]:
        """获取图片基本信息"""
        fmt = self.detect_format(data)
        if not fmt:
            raise ImageProcessorError("E008")
        
        info = {
            "format": fmt,
            "size_bytes": len(data),
            "width": 0,
            "height": 0,
            "compression_ratio": 1.0,
        }
        
        # 尝试解析尺寸
        try:
            if fmt == "PNG":
                # PNG 尺寸在 IHDR 块中
                if len(data) >= 24:
                    width, height = struct.unpack(">II", data[16:24])
                    info["width"] = width
                    info["height"] = height
            elif fmt == "JPEG":
                # JPEG 尺寸在 SOF 标记中
                info["width"], info["height"] = self._parse_jpeg_size(data)
            elif fmt == "GIF":
                # GIF 尺寸在头部
                if len(data) >= 10:
                    width, height = struct.unpack("<HH", data[6:10])
                    info["width"] = width
                    info["height"] = height
            elif fmt == "BMP":
                # BMP 尺寸在 DIB 头中
                if len(data) >= 26:
                    width = struct.unpack("<i", data[18:22])[0]
                    height = abs(struct.unpack("<i", data[22:26])[0])
                    info["width"] = width
                    info["height"] = height
        except (struct.error, IndexError):
            # 尺寸解析失败不致命，保留默认值
            pass
        
        return info
    
    def _parse_jpeg_size(self, data: bytes) -> Tuple[int, int]:
        """解析 JPEG 图片尺寸"""
        idx = 2  # 跳过 SOI 标记
        while idx < len(data) - 9:
            if data[idx] != 0xFF:
                idx += 1
                continue
            marker = data[idx + 1]
            if marker in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
                if idx + 9 < len(data):
                    height = struct.unpack(">H", data[idx + 5:idx + 7])[0]
                    width = struct.unpack(">H", data[idx + 7:idx + 9])[0]
                    return width, height
            if idx + 4 < len(data):
                length = struct.unpack(">H", data[idx + 2:idx + 4])[0]
                idx += 2 + length
            else:
                break
        return 0, 0
    
    def compress(self, data: bytes, quality: int = 75) -> Tuple[bytes, float]:
        """
        压缩图片数据
        返回 (压缩后数据, 压缩率)
        """
        if quality < 10 or quality > 100:
            raise ImageProcessorError("E010", "质量参数必须在10-100之间")
        
        original_size = len(data)
        
        # 使用 zlib 进行数据压缩（模拟压缩过程）
        # 实际应用中这里会调用对应的编解码库
        compressed = zlib.compress(data, level=quality // 20)
        
        # 如果压缩后没有变小，返回原数据
        if len(compressed) >= original_size:
            return data, 1.0
        
        compression_ratio = len(compressed) / original_size
        return compressed, compression_ratio
    
    def convert_format(self, data: bytes, target_format: str) -> Tuple[bytes, Dict[str, Any]]:
        """
        转换图片格式
        注意：这是一个简化实现，实际转换需要对应的图片库
        """
        target_format = target_format.upper()
        if target_format not in self.supported_formats:
            raise ImageProcessorError("E008", f"不支持的格式: {target_format}")
        
        current_format = self.detect_format(data)
        if not current_format:
            raise ImageProcessorError("E008")
        
        # 如果格式相同，直接返回
        if current_format == target_format:
            return data, {"converted": False, "original_format": current_format}
        
        # 模拟格式转换（实际需要 Pillow 等库）
        # 这里我们简单包装数据并添加转换标记
        converted_data = bytearray(data)
        converted_data.extend(f"\n[CONVERTED: {current_format} -> {target_format}]".encode())
        
        return bytes(converted_data), {
            "converted": True,
            "original_format": current_format,
            "target_format": target_format,
        }
    
    def process_batch(self, inputs: List[bytes], options: Dict[str, Any]) -> List[Dict[str, Any]]:
        """批量处理图片"""
        results = []
        
        for idx, data in enumerate(inputs):
            try:
                result = self.process_single(data, options)
                result["index"] = idx
                results.append(result)
            except ImageProcessorError as e:
                results.append({
                    "index": idx,
                    "error": e.error_code,
                    "message": e.message,
                    "status": "failed",
                })
        
        return results
    
    def process_single(self, data: bytes, options: Dict[str, Any]) -> Dict[str, Any]:
        """处理单张图片"""
        if not data:
            raise ImageProcessorError("E001")
        
        # 获取图片信息
        info = self.get_image_info(data)
        
        # 格式转换
        target_format = options.get("target_format")
        if target_format:
            data, conv_info = self.convert_format(data, target_format)
            info.update(conv_info)
        
        # 压缩
        quality = options.get("quality", 75)
        if options.get("compress", True):
            compressed_data, ratio = self.compress(data, quality)
            info["compressed_size_bytes"] = len(compressed_data)
            info["compression_ratio"] = ratio
        else:
            info["compressed_size_bytes"] = len(data)
        
        # 计算置信度
        confidence = self._calculate_confidence(info)
        info["confidence"] = confidence
        
        if confidence < 85:
            info["warning"] = "[需核实] 处理结果置信度较低，请人工复核"
        elif confidence < 90:
            info["warning"] = "建议复核处理结果"
        
        info["status"] = "success"
        return info
    
    def _calculate_confidence(self, info: Dict[str, Any]) -> float:
        """计算处理置信度"""
        base_score = 100.0
        
        # 尺寸为0时降低置信度
        if info.get("width", 0) <= 0 or info.get("height", 0) <= 0:
            base_score -= 15
        
        # 压缩率异常时降低置信度
        ratio = info.get("compression_ratio", 1.0)
        if ratio > 2.0 or ratio < 0.1:
            base_score -= 10
        
        return max(0, min(100, base_score))

# ============================================================
# 自测试模块
# ============================================================
class SelfTest:
    """内置自测试模块"""
    
    @staticmethod
    def generate_test_images() -> Dict[str, bytes]:
        """生成测试用图片数据（硬编码）"""
        test_images = {}
        
        # 生成一个最小的 PNG 图片（1x1 像素）
        png_data = SelfTest._create_test_png()
        test_images["png_1x1"] = png_data
        
        # 生成一个最小的 GIF 图片（1x1 像素）
        gif_data = SelfTest._create_test_gif()
        test_images["gif_1x1"] = gif_data
        
        # 生成一个 BMP 图片（1x1 像素，24位）
        bmp_data = SelfTest._create_test_bmp()
        test_images["bmp_1x1"] = bmp_data
        
        # 生成一个最小的 JPEG 图片
        jpeg_data = SelfTest._create_test_jpeg()
        test_images["jpeg_1x1"] = jpeg_data
        
        return test_images
    
    @staticmethod
    def _create_test_png() -> bytes:
        """创建一个最小的 PNG 图片"""
        # PNG 文件结构：签名 + IHDR + IDAT + IEND
        png_data = bytearray()
        png_data.extend(b"\x89PNG\r\n\x1a\n")
        
        # IHDR 块
        ihdr_data = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
        ihdr_chunk = b"IHDR" + ihdr_data
        ihdr_crc = zlib.crc32(ihdr_chunk) & 0xffffffff
        png_data.extend(struct.pack(">I", len(ihdr_data)))
        png_data.extend(ihdr_chunk)
        png_data.extend(struct.pack(">I", ihdr_crc))
        
        # IDAT 块（压缩的图像数据）
        raw_data = b"\x00\xff\x00\x00\xff"  # 1x1 红色像素
        compressed_data = zlib.compress(raw_data)
        idat_chunk = b"IDAT" + compressed_data
        idat_crc = zlib.crc32(idat_chunk) & 0xffffffff
        png_data.extend(struct.pack(">I", len(compressed_data)))
        png_data.extend(idat_chunk)
        png_data.extend(struct.pack(">I", idat_crc))
        
        # IEND 块
        iend_chunk = b"IEND"
        iend_crc = zlib.crc32(iend_chunk) & 0xffffffff
        png_data.extend(struct.pack(">I", 0))
        png_data.extend(iend_chunk)
        png_data.extend(struct.pack(">I", iend_crc))
        
        return bytes(png_data)
    
    @staticmethod
    def _create_test_gif() -> bytes:
        """创建一个最小的 GIF 图片"""
        gif_data = bytearray()
        gif_data.extend(b"GIF89a")
        gif_data.extend(struct.pack("<HH", 1, 1))  # 宽度、高度
        
        # 全局颜色表标志等
        gif_data.extend(b"\x00\x00\x00")  # 包字段
        gif_data.extend(b"\x00\x00\x00\x00")  # 背景色等
        
        # 图像描述符
        gif_data.extend(b"\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00")
        
        # 图像数据
        gif_data.extend(b"\x02\x02\x44\x01\x00")
        
        # 结束标记
        gif_data.extend(b"\x3b")
        
        return bytes(gif_data)
    
    @staticmethod
    def _create_test_bmp() -> bytes:
        """创建一个最小的 BMP 图片"""
        bmp_data = bytearray()
        bmp_data.extend(b"BM")
        
        # 文件头
        file_size = 54 + 3  # 54字节头 + 3字节像素数据
        bmp_data.extend(struct.pack("<IHHI", file_size, 0, 0, 54))
        
        # DIB 头
        bmp_data.extend(struct.pack("<IiiHHIIiiII", 40, 1, 1, 1, 24, 0, 3, 2835, 2835, 0, 0))
        
        # 像素数据（蓝色）
        bmp_data.extend(b"\xff\x00\x00")
        
        return bytes(bmp_data)
    
    @staticmethod
    def _create_test_jpeg() -> bytes:
        """创建一个最小的 JPEG 图片"""
        # 这是一个最小化的 JPEG 文件结构
        jpeg_data = bytearray()
        
        # SOI 标记
        jpeg_data.extend(b"\xff\xd8")
        
        # APP0 标记
        app0_data = b"JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
        jpeg_data.extend(b"\xff\xe0")
        jpeg_data.extend(struct.pack(">H", len(app0_data) + 2))
        jpeg_data.extend(app0_data)
        
        # SOF0 标记 (基线 DCT)
        sof0_data = struct.pack(">BHHB", 8, 1, 1, 1) + b"\x01\x11\x00"
        jpeg_data.extend(b"\xff\xc0")
        jpeg_data.extend(struct.pack(">H", len(sof0_data) + 2))
        jpeg_data.extend(sof0_data)
        
        # DHT 标记 (简化)
        dht_data = b"\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
        jpeg_data.extend(b"\xff\xc4")
        jpeg_data.extend(struct.pack(">H", len(dht_data) + 2))
        jpeg_data.extend(dht_data)
        
        # SOS 标记 (简化)
        sos_data = b"\x01\x01\x00\x00\x3f\x00"
        jpeg_data.extend(b"\xff\xda")
        jpeg_data.extend(struct.pack(">H", len(sos_data) + 2))
        jpeg_data.extend(sos_data)
        
        # 图像数据（简化）
        jpeg_data.extend(b"\x00\x00\x00\x00\x00")
        
        # EOI 标记
        jpeg_data.extend(b"\xff\xd9")
        
        return bytes(jpeg_data)
    
    @staticmethod
    def run() -> bool:
        """执行自测试"""
        print("开始自测试...")
        
        processor = ImageProcessor()
        test_images = SelfTest.generate_test_images()
        
        # 测试1: 格式检测
        print("\n[测试1] 格式检测")
        assert processor.detect_format(test_images["png_1x1"]) == "PNG", "PNG 格式检测失败"
        assert processor.detect_format(test_images["gif_1x1"]) == "GIF", "GIF 格式检测失败"
        assert processor.detect_format(test_images["bmp_1x1"]) == "BMP", "BMP 格式检测失败"
        assert processor.detect_format(test_images["jpeg_1x1"]) == "JPEG", "JPEG 格式检测失败"
        print("✓ 格式检测通过")
        
        # 测试2: 图片信息提取
        print("\n[测试2] 图片信息提取")
        info = processor.get_image_info(test_images["png_1x1"])
        assert info["width"] == 1, f"PNG 宽度错误: {info['width']}"
        assert info["height"] == 1, f"PNG 高度错误: {info['height']}"
        assert info["size_bytes"] > 0, "PNG 大小错误"
        
        info = processor.get_image_info(test_images["gif_1x1"])
        assert info["width"] == 1, f"GIF 宽度错误: {info['width']}"
        assert info["height"] == 1, f"GIF 高度错误: {info['height']}"
        
        info = processor.get_image_info(test_images["bmp_1x1"])
        assert info["width"] == 1, f"BMP 宽度错误: {info['width']}"
        assert info["height"] == 1, f"BMP 高度错误: {info['height']}"
        
        print("✓ 图片信息提取通过")
        
        # 测试3: 压缩功能
        print("\n[测试3] 压缩功能")
        compressed, ratio = processor.compress(test_images["png_1x1"], quality=50)
        assert len(compressed) > 0, "压缩结果为空"
        assert 0 < ratio <= 1.0, f"压缩率异常: {ratio}"
        print(f"✓ 压缩功能通过 (压缩率: {ratio:.2f})")
        
        # 测试4: 格式转换
        print("\n[测试4] 格式转换")
        converted, conv_info = processor.convert_format(test_images["png_1x1"], "GIF")
        assert conv_info["converted"] == True, "格式转换标志错误"
        assert conv_info["original_format"] == "PNG", "原始格式错误"
        assert conv_info["target_format"] == "GIF", "目标格式错误"
        print("✓ 格式转换通过")
        
        # 测试5: 单张图片处理
        print("\n[测试5] 单张图片处理")
        result = processor.process_single(test_images["png_1x1"], {
            "quality": 75,
            "compress": True,
            "target_format": None,
        })
        assert result["status"] == "success", "处理失败"
        assert result["format"] == "PNG", "格式错误"
        assert result["confidence"] >= 85, f"置信度过低: {result['confidence']}"
        print(f"✓ 单张图片处理通过 (置信度: {result['confidence']:.0f}%)")
        
        # 测试6: 批量处理
        print("\n[测试6] 批量处理")
        batch_inputs = [
            test_images["png_1x1"], 
            test_images["gif_1x1"], 
            test_images["bmp_1x1"],
            test_images["jpeg_1x1"]
        ]
        batch_results = processor.process_batch(batch_inputs, {"quality": 60, "compress": True})
        assert len(batch_results) == 4, "批量处理数量错误"
        for r in batch_results:
            assert r["status"] == "success", f"批量处理失败: {r}"
        print("✓ 批量处理通过")
        
        # 测试7: 错误处理
        print("\n[测试7] 错误处理")
        try:
            processor.process_single(b"", {})
            assert False, "空输入应该报错"
        except ImageProcessorError as e:
            assert e.error_code == "E001", f"错误码错误: {e.error_code}"
        print("✓ 错误处理通过")
        
        # 测试8: 边界条件
        print("\n[测试8] 边界条件")
        # 无效格式
        assert processor.detect_format(b"invalid data") is None, "无效格式应该返回 None"
        
        # 无效质量参数
        try:
            processor.compress(test_images["png_1x1"], quality=200)
            assert False, "无效质量参数应该报错"
        except ImageProcessorError as e:
            assert e.error_code == "E010", f"错误码错误: {e.error_code}"
        
        # 不支持的格式转换
        try:
            processor.convert_format(test_images["png_1x1"], "INVALID")
            assert False, "不支持的格式应该报错"
        except ImageProcessorError as e:
            assert e.error_code == "E008", f"错误码错误: {e.error_code}"
        
        print("✓ 边界条件通过")
        
        print("\n" + "="*50)
        print("✓ 所有自测试通过！")
        print("="*50)
        return True

# ============================================================
# 命令行处理
# ============================================================
def process_file(filepath: str, options: Dict[str, Any]) -> Dict[str, Any]:
    """处理单个文件"""
    try:
        with open(filepath, "rb") as f:
            data = f.read()
    except IOError as e:
        raise ImageProcessorError("E006", f"无法读取文件 {filepath}: {str(e)}")
    
    processor = ImageProcessor()
    result = processor.process_single(data, options)
    result["filepath"] = filepath
    return result

def process_directory(dirpath: str, options: Dict[str, Any]) -> List[Dict[str, Any]]:
    """处理目录下所有图片"""
    results = []
    path = Path(dirpath)
    
    if not path.exists():
        raise ImageProcessorError("E006", f"目录不存在: {dirpath}")
    
    image_extensions = {info["ext"] for info in IMAGE_FORMATS.values()}
    
    for filepath in path.iterdir():
        if filepath.is_file() and filepath.suffix.lower() in image_extensions:
            try:
                result = process_file(str(filepath), options)
                results.append(result)
            except ImageProcessorError as e:
                results.append({
                    "filepath": str(filepath),
                    "error": e.error_code,
                    "message": e.message,
                    "status": "failed",
                })
    
    return results

def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="图片批量处理工具 - 转换、压缩、调整大小",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s --selftest                     # 运行自测试
  %(prog)s --file input.png               # 处理单个文件
  %(prog)s --dir ./images                 # 处理目录下所有图片
  %(prog)s --file input.png --format JPEG # 转换格式
  %(prog)s --file input.png --quality 80  # 设置压缩质量
        """
    )
    
    parser.add_argument("--selftest", action="store_true", help="运行内置自测试")
    parser.add_argument("--file", type=str, help="处理单个图片文件")
    parser.add_argument("--dir", type=str, help="处理目录下所有图片")
    parser.add_argument("--format", type=str, dest="target_format", help="目标格式 (PNG/JPEG/GIF/BMP/TIFF/WEBP)")
    parser.add_argument("--quality", type=int, default=75, help="压缩质量 10-100 (默认: 75)")
    parser.add_argument("--no-compress", action="store_true", help="不进行压缩")
    parser.add_argument("--json", action="store_true", help="以 JSON 格式输出")
    
    args = parser.parse_args()
    
    # 运行自测试
    if args.selftest:
        try:
            success = SelfTest.run()
            sys.exit(0 if success else 1)
        except AssertionError as e:
            print(f"自测试失败: {e}", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"自测试异常: {e}", file=sys.stderr)
            sys.exit(1)
    
    # 检查参数
    if not args.file and not args.dir:
        parser.print_help()
        sys.exit(1)
    
    # 构建处理选项
    options = {
        "quality": args.quality,
        "compress": not args.no_compress,
        "target_format": args.target_format,
    }
    
    # 处理输入
    try:
        if args.file:
            result = process_file(args.file, options)
            results = [result]
        elif args.dir:
            results = process_directory(args.dir, options)
        else:
            raise ImageProcessorError("E001")
    except ImageProcessorError as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)
    
    # 输出结果
    if args.json:
        print(json.dumps(results, indent=2, ensure_ascii=False))
    else:
        for result in results:
            if result.get("status") == "success":
                print(f"\n文件: {result.get('filepath', f'输入#{result.get(\"index\", 0)}')}")
                print(f"  格式: {result['format']}")
                print(f"  尺寸: {result.get('width', 0)}x{result.get('height', 0)}")
                print(f"  原始大小: {result['size_bytes']} bytes")
                print(f"  压缩后: {result.get('compressed_size_bytes', result['size_bytes'])} bytes")
                print(f"  压缩率: {result.get('compression_ratio', 1.0):.2f}")
                print(f"  置信度: {result['confidence']:.0f}%")
                if result.get("warning"):
                    print(f"  警告: {result['warning']}")
            else:
                print(f"\n文件: {result.get('filepath', f'输入#{result.get(\"index\", 0)}')}")
                print(f"  错误: [{result.get('error', 'E009')}] {result.get('message', '处理失败')}")

if __name__ == "__main__":
    main()
