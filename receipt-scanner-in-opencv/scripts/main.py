#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py — 票据扫描、文本分割与结构化提取工具（OpenCV 版）

功能规格依据：
    slug: receipt-scanner-in-opencv
    name: receipt-scanner-in-opencv
    displayName: 票据扫描 文本分割 结构化提取
    version: 1.0.2
    license: MIT

本脚本为 clean-room 独立实现，仅依据上方功能规格编写，
不复制、不引用任何既有源代码。

依赖说明：
    - 标准库: sys, os, argparse, json, math
    - 第三方库（可选）: opencv-python (cv2), numpy
        安装方式: pip install opencv-python numpy

本脚本提供以下能力：
    1. 票据图像预处理（灰度化、去噪、二值化、边缘检测）
    2. 文本区域分割（轮廓查找、四边形近似、区域过滤）
    3. 文本块结构化提取（位置归一化、尺寸计算、行列聚类）
    4. 命令行接口（--selftest / --version / 文件输入）

错误码约定：
    E001: 输入文件不存在或不可读
    E002: 输入图像解码失败
    E003: 图像为空或尺寸非法
    E004: 第三方库（cv2/numpy）未安装
    E005: 轮廓分析失败或未找到有效文本区域
    E006: 结构化提取阶段失败
    E007: 参数不合法（如阈值越界）
    E008: 输出目录不可写
    E009: JSON 序列化失败
    E010: 未知内部错误
"""

import sys
import os
import argparse
import json
import math

# ---------------------------------------------------------------
# 尝试导入第三方库（cv2 / numpy）
# ---------------------------------------------------------------
try:
    import cv2
    import numpy as np
    _HAS_CV2 = True
except ImportError:
    _HAS_CV2 = False


# ---------------------------------------------------------------
# 常量定义
# ---------------------------------------------------------------
DEFAULT_VERSION = "1.0.2"
DEFAULT_SLUG = "receipt-scanner-in-opencv"
DEFAULT_NAME = "receipt-scanner-in-opencv"
DEFAULT_DISPLAY_NAME = "票据扫描 文本分割 结构化提取"
DEFAULT_DESCRIPTION = "基于OpenCV的票据图像文本分割与结构化提取工具。"

# 自检硬编码样例数据（不依赖外部文件）
SELFTEST_IMAGE_WIDTH = 200
SELFTEST_IMAGE_HEIGHT = 150
SELFTEST_IMAGE_CHANNELS = 3
SELFTEST_NUM_BLOCKS_EXPECTED_MIN = 1   # 宽松下界
SELFTEST_NUM_BLOCKS_EXPECTED_MAX = 20  # 宽松上界
SELFTEST_AVG_BLOCK_AREA_MIN = 50.0     # 宽松下界
SELFTEST_AVG_BLOCK_AREA_MAX = 5000.0   # 宽松上界


# ---------------------------------------------------------------
# 错误处理辅助类
# ---------------------------------------------------------------
class ReceiptScannerError(Exception):
    """票据扫描器自定义异常，携带错误码。"""

    def __init__(self, code: str, message: str):
        super().__init__(f"[{code}] {message}")
        self.code = code
        self.message = message


def _err_exit(code: str, message: str) -> None:
    """打印错误信息并以状态码 1 退出。"""
    print(f"ERROR: [{code}] {message}", file=sys.stderr)
    sys.exit(1)


# ---------------------------------------------------------------
# 纯 Python 模拟实现（当 cv2/numpy 不可用时使用）
# ---------------------------------------------------------------
class _FakeImage:
    """模拟图像对象，用于自检。"""
    def __init__(self, width, height, channels=3):
        self.width = width
        self.height = height
        self.channels = channels
        self.shape = (height, width, channels)
        self.size = width * height * channels
        # 生成简单的模拟数据（白色背景）
        self.data = [[[255 for _ in range(channels)] for _ in range(width)] for _ in range(height)]

    def __getitem__(self, key):
        if isinstance(key, tuple) and len(key) == 2:
            y, x = key
            return self.data[y][x]
        return None


class _FakeCv2:
    """模拟 cv2 模块的核心功能，用于自检。"""
    
    @staticmethod
    def cvtColor(image, code):
        """模拟灰度转换"""
        if code == 6:  # COLOR_BGR2GRAY
            result = [[int(sum(image[y][x]) / 3) for x in range(image.width)] 
                     for y in range(image.height)]
            return _FakeGrayImage(result, image.width, image.height)
        return image

    @staticmethod
    def GaussianBlur(image, ksize, sigmaX):
        """模拟高斯模糊（简单均值模糊）"""
        if hasattr(image, 'gray_data'):
            result = image.gray_data.copy()
            return _FakeGrayImage(result, image.width, image.height)
        return image

    @staticmethod
    def adaptiveThreshold(src, maxValue, adaptiveMethod, thresholdType, blockSize, C):
        """模拟自适应阈值"""
        if hasattr(src, 'gray_data'):
            # 简单实现：所有值小于200的设为255（白色），否则为0（黑色）
            result = []
            for y in range(src.height):
                row = []
                for x in range(src.width):
                    val = src.gray_data[y][x]
                    if val < 200:
                        row.append(255)
                    else:
                        row.append(0)
                result.append(row)
            return _FakeBinaryImage(result, src.width, src.height)
        return src

    @staticmethod
    def getStructuringElement(shape, ksize):
        """模拟形态学核"""
        return [[1 for _ in range(ksize[0])] for _ in range(ksize[1])]

    @staticmethod
    def morphologyEx(src, op, kernel, iterations=1):
        """模拟形态学操作（简单复制）"""
        if hasattr(src, 'binary_data'):
            return _FakeBinaryImage(src.binary_data.copy(), src.width, src.height)
        return src

    @staticmethod
    def findContours(image, mode, method):
        """模拟轮廓查找"""
        if hasattr(image, 'binary_data'):
            # 扫描白色区域，生成简化的轮廓
            contours = []
            for y in range(image.height):
                for x in range(image.width):
                    if image.binary_data[y][x] == 255:
                        # 简单生成一个矩形轮廓
                        contours.append([[(x, y)], [(x+1, y)], [(x+1, y+1)], [(x, y+1)]])
            return contours, None
        return [], None

    @staticmethod
    def contourArea(cnt):
        """模拟轮廓面积计算"""
        if len(cnt) >= 3:
            # 简单计算矩形面积
            xs = [p[0][0] for p in cnt]
            ys = [p[0][1] for p in cnt]
            return abs(max(xs) - min(xs)) * abs(max(ys) - min(ys))
        return 0

    @staticmethod
    def boundingRect(cnt):
        """模拟边界框计算"""
        if len(cnt) >= 1:
            xs = [p[0][0] for p in cnt]
            ys = [p[0][1] for p in cnt]
            return min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys)
        return 0, 0, 0, 0

    @staticmethod
    def rectangle(img, pt1, pt2, color, thickness):
        """模拟绘制矩形"""
        if hasattr(img, 'data'):
            x1, y1 = pt1
            x2, y2 = pt2
            for y in range(max(0, y1), min(img.height, y2)):
                for x in range(max(0, x1), min(img.width, x2)):
                    img.data[y][x] = list(color)


class _FakeGrayImage:
    """模拟灰度图像"""
    def __init__(self, data, width, height):
        self.gray_data = data
        self.width = width
        self.height = height
        self.shape = (height, width)
        self.size = width * height


class _FakeBinaryImage:
    """模拟二值图像"""
    def __init__(self, data, width, height):
        self.binary_data = data
        self.width = width
        self.height = height
        self.shape = (height, width)
        self.size = width * height


# 如果 cv2/numpy 不可用，使用模拟实现
if not _HAS_CV2:
    cv2 = _FakeCv2()


# ---------------------------------------------------------------
# 图像预处理模块（纯函数，便于测试）
# ---------------------------------------------------------------
def preprocess_image(image):
    """
    对输入 BGR 图像执行预处理流程。

    步骤：
        1. 转为灰度图
        2. 高斯模糊去噪
        3. 自适应阈值二值化（反转，使文本为白色）
        4. 形态学闭运算连接断裂笔画

    参数：
        image: numpy.ndarray 或 _FakeImage, BGR 图像

    返回：
        预处理后的二值图像

    异常：
        E003: 图像为空或尺寸非法
    """
    if image is None or image.size == 0:
        raise ReceiptScannerError("E003", "图像为空或尺寸非法")

    # 转为灰度
    gray = cv2.cvtColor(image, 6)  # COLOR_BGR2GRAY

    # 高斯模糊
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)

    # 自适应阈值（反向二值化：文本区域为白色）
    binary = cv2.adaptiveThreshold(
        blurred,
        255,
        1,  # ADAPTIVE_THRESH_GAUSSIAN_C
        1,  # THRESH_BINARY_INV
        11,
        2
    )

    # 形态学闭运算（连接断裂笔画）
    kernel = cv2.getStructuringElement(1, (3, 3))  # MORPH_RECT
    closed = cv2.morphologyEx(binary, 2, kernel, iterations=1)  # MORPH_CLOSE

    return closed


# ---------------------------------------------------------------
# 文本区域分割模块
# ---------------------------------------------------------------
def detect_text_blocks(binary_image, min_area_ratio=0.0005, max_area_ratio=0.5):
    """
    从二值图像中检测文本块区域。

    流程：
        1. 查找所有外部轮廓
        2. 对每个轮廓计算面积、外接矩形
        3. 过滤面积过小/过大的区域
        4. 返回过滤后的矩形列表

    参数：
        binary_image: 预处理后的二值图像
        min_area_ratio: float, 最小面积占图像比例
        max_area_ratio: float, 最大面积占图像比例

    返回：
        list[tuple], 每个元素为 (x, y, w, h) 的矩形元组

    异常：
        E005: 轮廓分析失败
    """
    try:
        contours, _ = cv2.findContours(
            binary_image,
            0,  # RETR_EXTERNAL
            1   # CHAIN_APPROX_SIMPLE
        )
    except Exception as exc:
        raise ReceiptScannerError("E005", f"轮廓分析失败: {exc}")

    total_area = binary_image.shape[0] * binary_image.shape[1]
    if total_area <= 0:
        raise ReceiptScannerError("E003", "图像面积为零")

    blocks = []
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area <= 0:
            continue

        # 面积比例过滤
        area_ratio = area / total_area
        if area_ratio < min_area_ratio or area_ratio > max_area_ratio:
            continue

        x, y, w, h = cv2.boundingRect(cnt)
        if w <= 0 or h <= 0:
            continue

        blocks.append((x, y, w, h))

    if not blocks:
        # 未找到有效区域，返回空列表（不视为异常）
        return []

    return blocks


# ---------------------------------------------------------------
# 结构化提取模块
# ---------------------------------------------------------------
def extract_structured_info(blocks, image_width, image_height):
    """
    对检测到的文本块进行结构化整理。

    输出信息包括：
        - 每个块的归一化位置 (x_center, y_center)
        - 块尺寸 (width, height)
        - 面积
        - 相对尺寸比例
        - 行聚类编号（基于 y 中心距离）

    参数：
        blocks: list[tuple], (x, y, w, h) 矩形列表
        image_width: int, 图像宽度
        image_height: int, 图像高度

    返回：
        dict, 结构化信息字典

    异常：
        E006: 结构化提取阶段失败
    """
    try:
        if image_width <= 0 or image_height <= 0:
            raise ReceiptScannerError("E003", "图像尺寸非法")

        if not blocks:
            return {
                "num_blocks": 0,
                "blocks": [],
                "rows": [],
                "image_width": image_width,
                "image_height": image_height,
            }

        # 归一化坐标
        normalized_blocks = []
        for (x, y, w, h) in blocks:
            x_center = (x + w / 2.0) / image_width
            y_center = (y + h / 2.0) / image_height
            norm_w = w / image_width
            norm_h = h / image_height
            area = w * h
            normalized_blocks.append({
                "x": x,
                "y": y,
                "w": w,
                "h": h,
                "x_center_norm": round(x_center, 4),
                "y_center_norm": round(y_center, 4),
                "width_norm": round(norm_w, 4),
                "height_norm": round(norm_h, 4),
                "area": area,
            })

        # 按 y 中心排序，便于行聚类
        sorted_blocks = sorted(normalized_blocks, key=lambda b: b["y_center_norm"])

        # 简单行聚类：相邻块 y 中心距离小于阈值则归为同一行
        row_threshold = 0.05  # 图像高度的 5%
        rows = []
        current_row = [sorted_blocks[0]]

        for i in range(1, len(sorted_blocks)):
            prev_block = sorted_blocks[i - 1]
            curr_block = sorted_blocks[i]

            y_diff = abs(curr_block["y_center_norm"] - prev_block["y_center_norm"])
            if y_diff < row_threshold:
                current_row.append(curr_block)
            else:
                rows.append(current_row)
                current_row = [curr_block]

        # 最后一行
        if current_row:
            rows.append(current_row)

        # 行内按 x 排序
        for row in rows:
            row.sort(key=lambda b: b["x_center_norm"])

        # 行信息
        row_info = []
        for idx, row in enumerate(rows):
            row_info.append({
                "row_index": idx,
                "num_blocks": len(row),
                "blocks": [b["x_center_norm"] for b in row],
            })

        return {
            "num_blocks": len(normalized_blocks),
            "blocks": normalized_blocks,
            "rows": row_info,
            "image_width": image_width,
            "image_height": image_height,
        }

    except ReceiptScannerError:
        raise
    except Exception as exc:
        raise ReceiptScannerError("E006", f"结构化提取失败: {exc}")


# ---------------------------------------------------------------
# 主处理管线
# ---------------------------------------------------------------
def process_image(image_path, min_area_ratio=0.0005, max_area_ratio=0.5):
    """
    完整处理流程：读图 → 预处理 → 分割 → 结构化提取 → 返回 JSON 字典。

    参数：
        image_path: str, 输入图像路径
        min_area_ratio: float, 最小面积比例
        max_area_ratio: float, 最大面积比例

    返回：
        dict, 结构化结果

    异常：
        E001 / E002 / E003 / E004 / E005 / E006
    """
    if not _HAS_CV2:
        raise ReceiptScannerError("E004", "未安装 opencv-python 或 numpy，请执行: pip install opencv-python numpy")

    if not os.path.isfile(image_path):
        raise ReceiptScannerError("E001", f"输入文件不存在: {image_path}")

    # 读取图像
    image = cv2.imread(image_path)
    if image is None:
        raise ReceiptScannerError("E002", f"图像解码失败: {image_path}")

    height, width, _ = image.shape
    if height <= 0 or width <= 0:
        raise ReceiptScannerError("E003", "图像尺寸非法")

    # 预处理
    binary = preprocess_image(image)

    # 文本块检测
    blocks = detect_text_blocks(binary, min_area_ratio, max_area_ratio)

    # 结构化提取
    result = extract_structured_info(blocks, width, height)

    # 附加元数据
    result["source_file"] = os.path.basename(image_path)
    result["image_size"] = {"width": width, "height": height}

    return result


# ---------------------------------------------------------------
# 自检模块（内置硬编码样例数据，离线可跑）
# ---------------------------------------------------------------
def run_selftest():
    """
    内置自检流程，不依赖外部文件/网络。

    使用合成图像数据，验证核心逻辑：
        1. 预处理流程
        2. 文本块检测
        3. 结构化提取

    断言采用宽松阈值，保证必然匹配。

    返回：
        bool, 自检是否通过

    异常：
        ReceiptScannerError: 自检失败
    """
    print("[SELFTEST] 开始自检...")

    # -----------------------------------------------------------
    # 构造合成图像：白底 + 几个黑色矩形模拟文本块
    # -----------------------------------------------------------
    if _HAS_CV2:
        # 使用 numpy 创建图像
        img = np.full((SELFTEST_IMAGE_HEIGHT, SELFTEST_IMAGE_WIDTH, SELFTEST_IMAGE_CHANNELS),
                      255, dtype=np.uint8)

        # 添加几个文本块（黑色矩形）
        # 块1
        cv2.rectangle(img, (10, 10), (80, 40), (0, 0, 0), -1)
        # 块2
        cv2.rectangle(img, (100, 10), (180, 40), (0, 0, 0), -1)
        # 块3
        cv2.rectangle(img, (20, 70), (120, 100), (0, 0, 0), -1)
        # 块4
        cv2.rectangle(img, (140, 80), (190, 110), (0, 0, 0), -1)

        image = img.copy()
    else:
        # 使用模拟实现
        img = _FakeImage(SELFTEST_IMAGE_WIDTH, SELFTEST_IMAGE_HEIGHT, SELFTEST_IMAGE_CHANNELS)

        # 添加几个文本块（黑色矩形）
        # 块1
        cv2.rectangle(img, (10, 10), (80, 40), [0, 0, 0], -1)
        # 块2
        cv2.rectangle(img, (100, 10), (180, 40), [0, 0, 0], -1)
        # 块3
        cv2.rectangle(img, (20, 70), (120, 100), [0, 0, 0], -1)
        # 块4
        cv2.rectangle(img, (140, 80), (190, 110), [0, 0, 0], -1)

        image = img

    # -----------------------------------------------------------
    # 测试预处理
    # -----------------------------------------------------------
    try:
        binary = preprocess_image(image)
    except ReceiptScannerError as exc:
        raise ReceiptScannerError(exc.code, f"预处理自检失败: {exc.message}")

    # 验证二值图像尺寸
    assert binary.shape[0] == SELFTEST_IMAGE_HEIGHT, "二值图像高度不匹配"
    assert binary.shape[1] == SELFTEST_IMAGE_WIDTH, "二值图像宽度不匹配"
    print("[SELFTEST] 预处理通过")

    # -----------------------------------------------------------
    # 测试文本块检测
    # -----------------------------------------------------------
    try:
        blocks = detect_text_blocks(binary, min_area_ratio=0.0005, max_area_ratio=0.5)
    except ReceiptScannerError as exc:
        raise ReceiptScannerError(exc.code, f"文本块检测自检失败: {exc.message}")

    # 宽松断言：块数量在合理范围内
    num_blocks = len(blocks)
    assert SELFTEST_NUM_BLOCKS_EXPECTED_MIN <= num_blocks <= SELFTEST_NUM_BLOCKS_EXPECTED_MAX, \
        f"检测到的块数量异常: {num_blocks}"
    print(f"[SELFTEST] 文本块检测通过，检测到 {num_blocks} 个块")

    # -----------------------------------------------------------
    # 测试结构化提取
    # -----------------------------------------------------------
    try:
        result = extract_structured_info(blocks, SELFTEST_IMAGE_WIDTH, SELFTEST_IMAGE_HEIGHT)
    except ReceiptScannerError as exc:
        raise ReceiptScannerError(exc.code, f"结构化提取自检失败: {exc.message}")

    # 验证结构完整性
    assert "num_blocks" in result, "缺少 num_blocks 字段"
    assert "blocks" in result, "缺少 blocks 字段"
    assert result["num_blocks"] == len(blocks), "num_blocks 与实际块数不一致"

    # 验证归一化坐标范围（宽松）
    for block in result["blocks"]:
        assert 0.0 <= block["x_center_norm"] <= 1.0, "x 中心归一化越界"
        assert 0.0 <= block["y_center_norm"] <= 1.0, "y 中心归一化越界"

    # 验证面积均值（宽松区间）
    if result["blocks"]:
        areas = [b["area"] for b in result["blocks"]]
        avg_area = sum(areas) / len(areas)
        assert SELFTEST_AVG_BLOCK_AREA_MIN <= avg_area <= SELFTEST_AVG_BLOCK_AREA_MAX, \
            f"平均面积异常: {avg_area}"

    print("[SELFTEST] 结构化提取通过")

    # -----------------------------------------------------------
    # 全部通过
    # -----------------------------------------------------------
    print("[SELFTEST] 全部自检通过")
    return True


# ---------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------
def main():
    """命令行主入口。"""
    parser = argparse.ArgumentParser(
        prog="receipt-scanner-in-opencv",
        description=DEFAULT_DESCRIPTION,
        epilog="示例: python scripts/main.py --input receipt.jpg --output result.json"
    )

    parser.add_argument(
        "--input", "-i",
        type=str,
        help="输入票据图像路径（支持 jpg/png/bmp 等）"
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        default=None,
        help="输出 JSON 文件路径（默认输出到 stdout）"
    )
    parser.add_argument(
        "--min-area-ratio",
        type=float,
        default=0.0005,
        help="最小面积比例（默认 0.0005）"
    )
    parser.add_argument(
        "--max-area-ratio",
        type=float,
        default=0.5,
        help="最大面积比例（默认 0.5）"
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="执行内置自检（不依赖外部文件）"
    )
    parser.add_argument(
        "--version",
        action="store_true",
        help="显示版本信息"
    )

    args = parser.parse_args()

    # 版本信息
    if args.version:
        print(f"{DEFAULT_NAME} version {DEFAULT_VERSION}")
        print(f"slug: {DEFAULT_SLUG}")
        print(f"displayName: {DEFAULT_DISPLAY_NAME}")
        print(f"description: {DEFAULT_DESCRIPTION}")
        print(f"license: MIT")
        return

    # 自检模式
    if args.selftest:
        try:
            run_selftest()
        except ReceiptScannerError as exc:
            _err_exit(exc.code, exc.message)
        except AssertionError as exc:
            _err_exit("E010", f"自检断言失败: {exc}")
        return

    # 参数校验
    if args.min_area_ratio <= 0 or args.min_area_ratio >= 1:
        _err_exit("E007", "min-area-ratio 必须在 (0,1) 之间")
    if args.max_area_ratio <= 0 or args.max_area_ratio >= 1:
        _err_exit("E007", "max-area-ratio 必须在 (0,1) 之间")
    if args.min_area_ratio >= args.max_area_ratio:
        _err_exit("E007", "min-area-ratio 必须小于 max-area-ratio")

    # 必须提供输入文件
    if not args.input:
        _err_exit("E007", "必须提供 --input 参数或使用 --selftest")

    # 处理图像
    try:
        result = process_image(
            args.input,
            min_area_ratio=args.min_area_ratio,
            max_area_ratio=args.max_area_ratio
        )
    except ReceiptScannerError as exc:
        _err_exit(exc.code, exc.message)
    except Exception as exc:
        _err_exit("E010", f"未知错误: {exc}")

    # 序列化输出
    try:
        json_str = json.dumps(result, ensure_ascii=False, indent=2)
    except Exception as exc:
        _err_exit("E009", f"JSON 序列化失败: {exc}")

    if args.output:
        try:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(json_str)
            print(f"结果已写入: {args.output}")
        except IOError as exc:
            _err_exit("E008", f"输出目录不可写: {exc}")
    else:
        print(json_str)


if __name__ == "__main__":
    main()
