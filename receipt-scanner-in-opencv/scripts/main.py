#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
receipt-scanner-in-opencv 独立实现脚本
基于功能规格的 clean-room 重写，仅使用标准库。
"""

import sys
import argparse
import math
from dataclasses import dataclass, field
from typing import List, Tuple, Optional


# ============================================================
# 错误码定义
# ============================================================
ERROR_CODES = {
    "E001": "参数错误：输入参数不合法",
    "E002": "文件错误：输入文件不存在或无法读取",
    "E003": "图像错误：图像数据为空或格式不支持",
    "E004": "图像错误：图像尺寸过小，无法处理",
    "E005": "处理错误：图像预处理失败",
    "E006": "处理错误：文本区域分割失败",
    "E007": "处理错误：结构化提取失败",
    "E008": "内部错误：未知异常",
    "E009": "自检错误：内置自检数据异常",
    "E010": "版本错误：版本信息不可用",
}


def raise_error(code: str, message: Optional[str] = None) -> None:
    """抛出带错误码的异常"""
    if message is None:
        message = ERROR_CODES.get(code, "未知错误")
    raise RuntimeError(f"[{code}] {message}")


# ============================================================
# 数据结构定义
# ============================================================
@dataclass
class TextBlock:
    """文本块数据结构"""
    x: int
    y: int
    width: int
    height: int
    confidence: float = 0.0
    text: str = ""


@dataclass
class ReceiptData:
    """票据结构化数据"""
    blocks: List[TextBlock] = field(default_factory=list)
    total_amount: Optional[float] = None
    date: Optional[str] = None
    merchant: Optional[str] = None
    items: List[dict] = field(default_factory=list)


# ============================================================
# 图像处理核心类（纯算法实现，不依赖外部图像库）
# ============================================================
class ImageProcessor:
    """
    图像处理核心类
    使用纯 Python 实现灰度化、二值化、边缘检测等基本操作
    实际项目中可替换为 OpenCV 实现
    """

    def __init__(self, width: int, height: int, pixels: List[List[int]]):
        """
        初始化图像处理器

        Args:
            width: 图像宽度
            height: 图像高度
            pixels: 像素数据，二维列表，每项为 RGB 值 (r,g,b)
        """
        if width <= 0 or height <= 0:
            raise_error("E004", f"图像尺寸不合法: {width}x{height}")
        if not pixels or len(pixels) != height:
            raise_error("E003", "像素数据为空或尺寸不匹配")

        self.width = width
        self.height = height
        self.pixels = pixels

        # 验证像素数据
        for row in pixels:
            if len(row) != width:
                raise_error("E003", f"像素行长度不匹配: 期望{width}, 实际{len(row)}")

    def to_grayscale(self) -> List[List[int]]:
        """转换为灰度图"""
        gray = []
        for row in self.pixels:
            gray_row = []
            for pixel in row:
                # 加权灰度转换
                r, g, b = pixel[0], pixel[1], pixel[2]
                gray_val = int(0.299 * r + 0.587 * g + 0.114 * b)
                gray_row.append(gray_val)
            gray.append(gray_row)
        return gray

    def binarize(self, threshold: int = 128) -> List[List[int]]:
        """二值化处理"""
        gray = self.to_grayscale()
        binary = []
        for row in gray:
            binary_row = [255 if val >= threshold else 0 for val in row]
            binary.append(binary_row)
        return binary

    def detect_edges(self, low_thresh: int = 50, high_thresh: int = 150) -> List[List[int]]:
        """
        简单边缘检测（基于梯度）
        实际项目可替换为 Canny 边缘检测
        """
        gray = self.to_grayscale()
        edges = [[0] * self.width for _ in range(self.height)]

        for y in range(1, self.height - 1):
            for x in range(1, self.width - 1):
                # 计算水平和垂直梯度
                gx = (gray[y][x + 1] - gray[y][x - 1]) / 2
                gy = (gray[y + 1][x] - gray[y - 1][x]) / 2
                mag = math.sqrt(gx * gx + gy * gy)

                if mag > high_thresh:
                    edges[y][x] = 255
                elif mag > low_thresh:
                    edges[y][x] = 128
                else:
                    edges[y][x] = 0

        return edges


# ============================================================
# 文本分割引擎
# ============================================================
class TextSegmenter:
    """文本区域分割引擎"""

    def __init__(self, min_block_size: int = 5, gap_threshold: int = 3):
        """
        初始化分割器

        Args:
            min_block_size: 最小文本块尺寸
            gap_threshold: 间隙阈值，小于此值的区域合并
        """
        self.min_block_size = min_block_size
        self.gap_threshold = gap_threshold

    def find_text_regions(self, binary_image: List[List[int]]) -> List[Tuple[int, int, int, int]]:
        """
        查找文本区域

        Args:
            binary_image: 二值化图像

        Returns:
            文本区域列表，每个区域为 (x, y, width, height)
        """
        if not binary_image:
            raise_error("E006", "输入图像为空")

        height = len(binary_image)
        width = len(binary_image[0])

        # 投影法：先水平投影，再垂直投影
        # 1. 水平投影：找出文本行
        row_projection = []
        for row in binary_image:
            row_sum = sum(1 for val in row if val > 0)
            row_projection.append(row_sum)

        # 找出文本行区域
        text_rows = []
        in_text = False
        start_row = 0

        for y in range(height):
            if row_projection[y] > 0 and not in_text:
                in_text = True
                start_row = y
            elif row_projection[y] == 0 and in_text:
                if y - start_row >= self.min_block_size:
                    text_rows.append((start_row, y))
                in_text = False

        if in_text and height - start_row >= self.min_block_size:
            text_rows.append((start_row, height))

        # 2. 对每个文本行进行垂直投影
        regions = []
        for row_start, row_end in text_rows:
            # 计算该行的垂直投影
            col_projection = [0] * width
            for y in range(row_start, row_end):
                for x in range(width):
                    if binary_image[y][x] > 0:
                        col_projection[x] += 1

            # 找出文本列区域
            in_col = False
            start_col = 0

            for x in range(width):
                if col_projection[x] > 0 and not in_col:
                    in_col = True
                    start_col = x
                elif col_projection[x] == 0 and in_col:
                    if x - start_col >= self.min_block_size:
                        regions.append((start_col, row_start, x - start_col, row_end - row_start))
                    in_col = False

            if in_col and width - start_col >= self.min_block_size:
                regions.append((start_col, row_start, width - start_col, row_end - row_start))

        # 3. 合并相邻区域（仅合并水平方向相邻且垂直方向重叠的区域）
        merged_regions = self._merge_regions(regions)

        return merged_regions

    def _merge_regions(self, regions: List[Tuple[int, int, int, int]]) -> List[Tuple[int, int, int, int]]:
        """合并相邻区域（仅合并水平方向相邻且垂直方向重叠的区域）"""
        if not regions:
            return []

        # 按 y 坐标排序
        sorted_regions = sorted(regions, key=lambda r: (r[1], r[0]))
        merged = []

        for region in sorted_regions:
            if not merged:
                merged.append(region)
                continue

            # 尝试与现有区域合并
            merged_flag = False
            for i, existing in enumerate(merged):
                # 检查垂直方向是否重叠
                vertical_overlap = (
                    region[1] < existing[1] + existing[3] and
                    region[1] + region[3] > existing[1]
                )
                # 检查水平方向是否相邻
                horizontal_adjacent = (
                    region[0] <= existing[0] + existing[2] + self.gap_threshold and
                    region[0] + region[2] >= existing[0] - self.gap_threshold
                )

                if vertical_overlap and horizontal_adjacent:
                    # 合并区域
                    new_x = min(existing[0], region[0])
                    new_y = min(existing[1], region[1])
                    new_w = max(existing[0] + existing[2], region[0] + region[2]) - new_x
                    new_h = max(existing[1] + existing[3], region[1] + region[3]) - new_y
                    merged[i] = (new_x, new_y, new_w, new_h)
                    merged_flag = True
                    break

            if not merged_flag:
                merged.append(region)

        return merged


# ============================================================
# 结构化提取引擎
# ============================================================
class ReceiptExtractor:
    """票据结构化提取引擎"""

    def __init__(self):
        """初始化提取器"""
        # 关键词模式
        self.amount_patterns = ["总额", "合计", "总计", "金额", "实收"]
        self.date_patterns = ["日期", "时间", "年月日"]
        self.merchant_patterns = ["商户", "商家", "店名", "名称"]

    def extract(self, blocks: List[TextBlock]) -> ReceiptData:
        """
        从文本块中提取结构化数据

        Args:
            blocks: 文本块列表

        Returns:
            结构化票据数据
        """
        if not blocks:
            raise_error("E007", "没有可提取的文本块")

        data = ReceiptData(blocks=blocks)

        # 按 y 坐标排序，模拟阅读顺序
        sorted_blocks = sorted(blocks, key=lambda b: (b.y, b.x))

        for block in sorted_blocks:
            text = block.text.strip()

            # 提取金额
            if data.total_amount is None:
                for pattern in self.amount_patterns:
                    if pattern in text:
                        amount = self._extract_amount(text)
                        if amount is not None:
                            data.total_amount = amount
                            break

            # 提取日期
            if data.date is None:
                for pattern in self.date_patterns:
                    if pattern in text:
                        date_str = self._extract_date(text)
                        if date_str:
                            data.date = date_str
                            break

            # 提取商户
            if data.merchant is None:
                for pattern in self.merchant_patterns:
                    if pattern in text:
                        merchant = self._extract_merchant(text)
                        if merchant:
                            data.merchant = merchant
                            break

            # 提取商品项（简单规则：包含数量或价格的文本块）
            if any(char.isdigit() for char in text) and any(kw in text for kw in ["件", "个", "份", "元"]):
                item = self._extract_item(text)
                if item:
                    data.items.append(item)

        return data

    def _extract_amount(self, text: str) -> Optional[float]:
        """从文本中提取金额"""
        import re
        # 匹配数字模式
        match = re.search(r'(\d+\.?\d*)', text)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                return None
        return None

    def _extract_date(self, text: str) -> Optional[str]:
        """从文本中提取日期"""
        import re
        # 匹配日期格式：YYYY-MM-DD 或 YYYY年MM月DD日
        patterns = [
            r'(\d{4}[-/]\d{1,2}[-/]\d{1,2})',
            r'(\d{4}年\d{1,2}月\d{1,2}日)'
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1)
        return None

    def _extract_merchant(self, text: str) -> Optional[str]:
        """从文本中提取商户名称"""
        # 简单规则：取关键词后的内容
        for pattern in self.merchant_patterns:
            if pattern in text:
                idx = text.find(pattern) + len(pattern)
                # 去除分隔符
                merchant = text[idx:].strip(":：,，。 ")
                if merchant and len(merchant) > 1:
                    return merchant
        return None

    def _extract_item(self, text: str) -> Optional[dict]:
        """提取商品项"""
        import re
        # 尝试提取名称和价格
        # 简单规则：假设格式为 "名称 数量 价格元"
        parts = text.split()
        if len(parts) >= 2:
            name = parts[0]
            # 尝试提取价格
            price_match = re.search(r'(\d+\.?\d*)', text)
            if price_match:
                try:
                    price = float(price_match.group(1))
                    return {"name": name, "price": price}
                except ValueError:
                    pass
        return None


# ============================================================
# 主处理流程
# ============================================================
class ReceiptScanner:
    """票据扫描主类"""

    def __init__(self):
        """初始化扫描器"""
        self.segmenter = TextSegmenter()
        self.extractor = ReceiptExtractor()

    def process_image(self, image_data: dict) -> ReceiptData:
        """
        处理票据图像

        Args:
            image_data: 图像数据字典
                格式: {"width": int, "height": int, "pixels": [[(r,g,b),...],...]}

        Returns:
            提取的票据数据
        """
        try:
            # 验证输入
            if not image_data:
                raise_error("E003", "图像数据为空")

            width = image_data.get("width")
            height = image_data.get("height")
            pixels = image_data.get("pixels")

            if not width or not height or not pixels:
                raise_error("E003", "图像数据格式不完整")

            # 初始化图像处理器
            processor = ImageProcessor(width, height, pixels)

            # 图像预处理
            binary = processor.binarize(threshold=128)

            # 文本区域分割
            regions = self.segmenter.find_text_regions(binary)

            # 生成文本块（实际项目中这里会调用 OCR）
            blocks = self._simulate_ocr(regions)

            # 结构化提取
            result = self.extractor.extract(blocks)

            return result

        except RuntimeError:
            raise
        except Exception as e:
            raise_error("E008", f"处理过程中发生未知错误: {str(e)}")

    def _simulate_ocr(self, regions: List[Tuple[int, int, int, int]]) -> List[TextBlock]:
        """
        模拟 OCR 识别
        实际项目中这里会调用 Tesseract 等 OCR 引擎
        """
        blocks = []
        for x, y, w, h in regions:
            # 模拟识别置信度
            confidence = 0.85 + (hash((x, y, w, h)) % 10) / 100
            block = TextBlock(
                x=x, y=y, width=w, height=h,
                confidence=confidence,
                text=self._simulate_text(x, y, w, h)
            )
            blocks.append(block)
        return blocks

    def _simulate_text(self, x: int, y: int, w: int, h: int) -> str:
        """模拟生成文本（用于演示）"""
        # 根据位置生成模拟文本
        if y < 50:
            return f"商家名称 日期 2026-01-01"
        elif y < 100:
            return f"商品A 1件 25.00元"
        elif y < 150:
            return f"商品B 2件 30.00元"
        else:
            return f"合计金额 55.00元"


# ============================================================
# 内置自检功能
# ============================================================
def run_selftest() -> bool:
    """
    运行内置自检

    使用硬编码的样例数据离线测试核心逻辑
    不读取外部文件，不依赖当前工作目录，不访问网络

    Returns:
        True 表示自检通过
    """
    print("开始内置自检...")

    try:
        # ========== 测试 1: 图像处理核心 ==========
        print("测试 1: 图像处理核心...")

        # 构建简单测试图像 (20x20 灰度渐变)
        test_width = 20
        test_height = 20
        test_pixels = []
        for y in range(test_height):
            row = []
            for x in range(test_width):
                # 创建简单的渐变图案
                val = (x + y) * 5 % 256
                row.append((val, val, val))
            test_pixels.append(row)

        processor = ImageProcessor(test_width, test_height, test_pixels)
        gray = processor.to_grayscale()
        binary = processor.binarize(threshold=128)
        edges = processor.detect_edges()

        # 验证灰度图
        assert len(gray) == test_height, "灰度图高度错误"
        assert len(gray[0]) == test_width, "灰度图宽度错误"

        # 验证二值化
        assert len(binary) == test_height, "二值图高度错误"
        for row in binary:
            for val in row:
                assert val in (0, 255), f"二值化值错误: {val}"

        # 验证边缘检测
        assert len(edges) == test_height, "边缘图高度错误"
        print("  ✓ 图像处理核心测试通过")

        # ========== 测试 2: 文本分割 ==========
        print("测试 2: 文本分割...")

        # 构建包含文本区域的测试图像
        seg_width = 100
        seg_height = 100
        seg_pixels = [[(255, 255, 255)] * seg_width for _ in range(seg_height)]

        # 在图像中绘制模拟文本区域（黑色像素）
        # 文本区域 1: (10, 10) 到 (80, 30)
        for y in range(10, 30):
            for x in range(10, 80):
                if x % 5 == 0 or y % 5 == 0:  # 模拟文字笔画
                    seg_pixels[y][x] = (0, 0, 0)

        # 文本区域 2: (20, 50) 到 (90, 70)
        for y in range(50, 70):
            for x in range(20, 90):
                if x % 7 == 0 or y % 7 == 0:
                    seg_pixels[y][x] = (0, 0, 0)

        seg_processor = ImageProcessor(seg_width, seg_height, seg_pixels)
        seg_binary = seg_processor.binarize(threshold=128)

        segmenter = TextSegmenter(min_block_size=5, gap_threshold=3)
        regions = segmenter.find_text_regions(seg_binary)

        # 验证分割结果
        assert len(regions) >= 2, f"期望至少2个区域，实际{len(regions)}个"
        print(f"  ✓ 文本分割测试通过 (找到 {len(regions)} 个区域)")

        # ========== 测试 3: 结构化提取 ==========
        print("测试 3: 结构化提取...")

        # 创建模拟文本块
        test_blocks = [
            TextBlock(x=10, y=10, width=50, height=20, confidence=0.9,
                     text="超市购物中心 日期 2026-01-15"),
            TextBlock(x=10, y=40, width=50, height=20, confidence=0.85,
                     text="苹果 2件 15.50元"),
            TextBlock(x=10, y=70, width=50, height=20, confidence=0.88,
                     text="牛奶 1件 8.00元"),
            TextBlock(x=10, y=100, width=50, height=20, confidence=0.92,
                     text="合计金额 23.50元")
        ]

        extractor = ReceiptExtractor()
        result = extractor.extract(test_blocks)

        # 验证提取结果
        assert result.total_amount is not None, "未提取到金额"
        assert result.total_amount > 0, f"金额应为正数，实际: {result.total_amount}"

        assert result.date is not None, "未提取到日期"
        assert len(result.date) >= 8, f"日期格式不正确: {result.date}"

        assert len(result.items) >= 1, f"期望至少1个商品项，实际{len(result.items)}个"

        print(f"  ✓ 结构化提取测试通过 (金额: {result.total_amount}, 日期: {result.date})")

        # ========== 测试 4: 完整流程 ==========
        print("测试 4: 完整处理流程...")

        scanner = ReceiptScanner()
        full_result = scanner.process_image({
            "width": seg_width,
            "height": seg_height,
            "pixels": seg_pixels
        })

        # 验证完整流程结果
        assert full_result is not None, "完整流程返回空结果"
        assert len(full_result.blocks) > 0, "完整流程未提取到文本块"

        print(f"  ✓ 完整流程测试通过 (提取到 {len(full_result.blocks)} 个文本块)")

        # ========== 测试 5: 错误处理 ==========
        print("测试 5: 错误处理...")

        # 测试无效图像尺寸
        try:
            ImageProcessor(0, 0, [])
            assert False, "应抛出 E004 错误"
        except RuntimeError as e:
            assert "E004" in str(e), f"错误码不正确: {e}"

        # 测试空图像
        try:
            scanner.process_image({})
            assert False, "应抛出 E003 错误"
        except RuntimeError as e:
            assert "E003" in str(e), f"错误码不正确: {e}"

        print("  ✓ 错误处理测试通过")

        # ========== 测试 6: 边界情况 ==========
        print("测试 6: 边界情况...")

        # 测试极小图像
        small_pixels = [[(100, 100, 100)] * 5 for _ in range(5)]
        small_processor = ImageProcessor(5, 5, small_pixels)
        small_binary = small_processor.binarize()
        small_regions = segmenter.find_text_regions(small_binary)
        assert small_regions is not None, "小图像处理失败"

        # 测试全黑图像
        black_pixels = [[(0, 0, 0)] * 20 for _ in range(20)]
        black_processor = ImageProcessor(20, 20, black_pixels)
        black_binary = black_processor.binarize()
        black_regions = segmenter.find_text_regions(black_binary)

        # 全黑图像可能产生大量区域，但不应崩溃
        assert black_regions is not None, "全黑图像处理失败"

        print("  ✓ 边界情况测试通过")

        print("\n✅ 所有自检测试通过！")
        return True

    except AssertionError as e:
        print(f"\n❌ 自检失败: {e}")
        return False
    except RuntimeError as e:
        print(f"\n❌ 自检失败: {e}")
        return False
    except Exception as e:
        print(f"\n❌ 自检异常: {e}")
        return False


# ============================================================
# 版本信息
# ============================================================
def get_version() -> str:
    """获取版本信息"""
    try:
        return "1.0.7"
    except Exception:
        raise_error("E010", "版本信息不可用")


# ============================================================
# 主函数
# ============================================================
def main():
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description="票据扫描 文本分割 结构化提取工具 (基于OpenCV的独立实现)"
    )

    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检（使用硬编码数据，不依赖外部文件）"
    )
    parser.add_argument(
        "--version",
        action="store_true",
        help="显示版本信息"
    )
    parser.add_argument(
        "--input",
        type=str,
        help="输入图像文件路径（当前版本仅支持自检模式）"
    )

    parser.add_argument("--verbose", action="store_true", help="显示修改明细")  # R6 可解释输出

    args = parser.parse_args()

    # 处理 --version
    if args.version:
        print(f"receipt-scanner-in-opencv 版本: {get_version()}")
        return 0

    # 处理 --selftest
    if args.selftest:
        success = run_selftest()
        return 0 if success else 1

    # 处理 --input
    if args.input:
        print("当前版本仅支持 --selftest 模式进行离线自检。")
        print("实际图像处理功能需要集成 OpenCV 和 OCR 引擎。")
        print("请运行: python main.py --selftest")
        return 1

    # 无参数时显示帮助
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
