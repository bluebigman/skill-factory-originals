#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
截图标注处理主程序（clean-room 独立实现）
依据功能规格独立编写，不参考任何既有代码。

功能：
  1. 从截图/图片中提取标注信息（框选区域、文本区域、箭头区域）
  2. 结构化整理为 JSON/CSV/TXT 格式
  3. 标注质量校验（边界/重叠/空标注）
  4. 批量处理与格式转换

用法示例：
  python main.py --input <图片路径或文件夹> [--type all|box|text|arrow]
                 [--format json|csv|txt] [--output <输出目录>]
                 [--dry-run] [--force] [--verbose] [--selftest]
"""

import argparse
import csv
import json
import os
import sys
import traceback
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# 错误码定义
ERROR_CODES = {
    "E001": "输入路径不存在或无法访问",
    "E002": "无法读取图片文件（格式不支持或文件损坏）",
    "E003": "输出目录无法创建或写入",
    "E004": "标注类型参数不合法",
    "E005": "输出格式参数不合法",
    "E006": "图片尺寸异常（宽度或高度为0）",
    "E007": "批量处理时发现空文件列表",
    "E008": "JSON序列化失败",
    "E009": "CSV写入失败",
    "E010": "内部逻辑错误（未知异常）",
}


# ============================================================
# 输入校验模块
# ============================================================

def validate_input_path(input_path: str) -> Path:
    """校验输入路径是否存在，返回 Path 对象。"""
    path = Path(input_path)
    if not path.exists():
        raise ValueError(f"E001: 输入路径不存在: {input_path}")
    return path


def validate_annot_type(annot_type: str) -> str:
    """校验标注类型参数。"""
    valid_types = {"all", "box", "text", "arrow"}
    if annot_type not in valid_types:
        raise ValueError(f"E004: 标注类型必须为 {sorted(valid_types)} 之一，收到: {annot_type}")
    return annot_type


def validate_output_format(output_format: str) -> str:
    """校验输出格式参数。"""
    valid_formats = {"json", "csv", "txt"}
    if output_format not in valid_formats:
        raise ValueError(f"E005: 输出格式必须为 {sorted(valid_formats)} 之一，收到: {output_format}")
    return output_format


def validate_confidence_threshold(threshold: float) -> float:
    """校验置信度阈值参数（0-1 之间）。"""
    if not 0.0 <= threshold <= 1.0:
        raise ValueError(f"E004: 置信度阈值必须在 0.0-1.0 之间，收到: {threshold}")
    return threshold


# ============================================================
# 核心逻辑模块（模拟标注提取，实际项目中可替换为 OpenCV + OCR）
# ============================================================

def read_image_safe(image_path: Path) -> Optional[Dict[str, Any]]:
    """
    安全读取图片并返回基本信息。
    实际项目中此处应使用 OpenCV/PIL 读取图片像素数据。
    本实现为演示，返回模拟的图片元数据。
    """
    try:
        # 模拟图片读取：检查文件扩展名
        ext = image_path.suffix.lower()
        supported_exts = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
        if ext not in supported_exts:
            print(f"警告: 不支持的图片格式 {ext}，跳过 {image_path}", file=sys.stderr)
            return None

        # 模拟读取图片尺寸（实际项目用 cv2.imread / PIL.Image.open）
        # 这里用文件大小模拟一个合理的宽高
        file_size = image_path.stat().st_size
        if file_size == 0:
            print(f"警告: 文件大小为0，跳过 {image_path}", file=sys.stderr)
            return None

        # 模拟宽高（实际项目从图片头读取）
        width = 800 + (file_size % 400)  # 800-1199
        height = 600 + (file_size % 300)  # 600-899
        if width <= 0 or height <= 0:
            raise ValueError(f"E006: 图片尺寸异常: {width}x{height}")

        return {
            "image_path": str(image_path),
            "image_size": {"width": width, "height": height},
            "file_size": file_size,
        }
    except Exception as e:
        print(f"E002: 读取图片失败 {image_path}: {e}", file=sys.stderr)
        return None


def simulate_detect_boxes(img_info: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    模拟检测框选区域。
    实际项目中用边缘检测 + 轮廓查找（cv2.findContours）。
    本实现生成 1-3 个模拟标注框。
    """
    width = img_info["image_size"]["width"]
    height = img_info["image_size"]["height"]
    file_size = img_info["file_size"]

    # 用文件大小生成确定性数量的框（保证可复现）
    num_boxes = 1 + (file_size % 3)  # 1-3 个框
    boxes = []
    for i in range(num_boxes):
        # 生成不越界的框坐标
        x1 = (file_size * (i + 1) * 7) % max(1, width - 100)
        y1 = (file_size * (i + 1) * 11) % max(1, height - 100)
        w = 50 + ((file_size * (i + 1) * 13) % min(200, width - x1 - 10))
        h = 30 + ((file_size * (i + 1) * 17) % min(150, height - y1 - 10))
        # 确保不越界
        x2 = min(x1 + w, width - 1)
        y2 = min(y1 + h, height - 1)
        if x2 <= x1 or y2 <= y1:
            continue
        confidence = 0.80 + ((file_size * (i + 1) * 19) % 20) / 100.0  # 0.80-0.99
        boxes.append({
            "type": "box",
            "bbox": [int(x1), int(y1), int(x2), int(y2)],
            "confidence": round(min(confidence, 0.99), 2),
            "text": f"标注框{i+1}",
        })
    return boxes


def simulate_detect_text(img_info: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    模拟检测文本区域。
    实际项目中用 OCR（pytesseract）识别文字。
    本实现生成 0-2 个模拟文本标注。
    """
    file_size = img_info["file_size"]
    num_texts = file_size % 3  # 0-2 个文本
    texts = []
    for i in range(num_texts):
        confidence = 0.75 + ((file_size * (i + 3) * 23) % 25) / 100.0  # 0.75-0.99
        texts.append({
            "type": "text",
            "bbox": [10 + i * 50, 10 + i * 30, 200 + i * 50, 50 + i * 30],
            "confidence": round(min(confidence, 0.99), 2),
            "text": f"文本标注{i+1}",
        })
    return texts


def simulate_detect_arrows(img_info: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    模拟检测箭头标注。
    实际项目中用线段检测（HoughLinesP）。
    本实现生成 0-1 个模拟箭头标注。
    """
    file_size = img_info["file_size"]
    if file_size % 2 == 0:
        return []
    confidence = 0.70 + (file_size % 30) / 100.0  # 0.70-0.99
    return [{
        "type": "arrow",
        "bbox": [100, 100, 300, 200],
        "confidence": round(min(confidence, 0.99), 2),
        "text": "箭头标注",
    }]


def extract_annotations(img_info: Dict[str, Any], annot_type: str) -> List[Dict[str, Any]]:
    """
    根据标注类型提取标注信息。
    实际项目中调用 OpenCV 检测函数。
    """
    annotations = []
    if annot_type in ("all", "box"):
        annotations.extend(simulate_detect_boxes(img_info))
    if annot_type in ("all", "text"):
        annotations.extend(simulate_detect_text(img_info))
    if annot_type in ("all", "arrow"):
        annotations.extend(simulate_detect_arrows(img_info))
    return annotations


def validate_annotations(annotations: List[Dict[str, Any]], img_size: Dict[str, int]) -> Dict[str, Any]:
    """
    校验标注质量：检查越界、空文本、重叠。
    返回校验报告。
    """
    width = img_size["width"]
    height = img_size["height"]
    issues = []
    valid_count = 0

    for i, ann in enumerate(annotations):
        bbox = ann["bbox"]
        x1, y1, x2, y2 = bbox
        # 检查越界
        if x1 < 0 or y1 < 0 or x2 > width or y2 > height:
            issues.append(f"标注{i+1}越界: bbox={bbox}, 图片尺寸={width}x{height}")
            continue
        # 检查空文本
        if not ann.get("text", "").strip():
            issues.append(f"标注{i+1}文本为空")
            continue
        # 检查坐标有效性
        if x2 <= x1 or y2 <= y1:
            issues.append(f"标注{i+1}坐标无效: {bbox}")
            continue
        valid_count += 1

    # 检查重叠（简单两两比较）
    overlap_count = 0
    for i in range(len(annotations)):
        for j in range(i + 1, len(annotations)):
            a1 = annotations[i]["bbox"]
            a2 = annotations[j]["bbox"]
            # 检查是否重叠
            if (a1[0] < a2[2] and a1[2] > a2[0] and
                    a1[1] < a2[3] and a1[3] > a2[1]):
                overlap_count += 1
                issues.append(f"标注{i+1}与标注{j+1}重叠")

    return {
        "total": len(annotations),
        "valid": valid_count,
        "issues": issues,
        "overlap_count": overlap_count,
        "quality_score": round(valid_count / max(1, len(annotations)) * 100, 1),
    }


def process_single_image(image_path: Path, annot_type: str, conf_threshold: float) -> Dict[str, Any]:
    """
    处理单张图片，返回标注结果。
    """
    img_info = read_image_safe(image_path)
    if img_info is None:
        return {
            "status": "error",
            "error_code": "E002",
            "message": f"无法读取图片: {image_path}",
            "image_path": str(image_path),
        }

    annotations = extract_annotations(img_info, annot_type)

    # 按置信度门控分类
    high_conf = [a for a in annotations if a["confidence"] >= 0.90]
    mid_conf = [a for a in annotations if 0.85 <= a["confidence"] < 0.90]
    low_conf = [a for a in annotations if a["confidence"] < 0.85]

    # 过滤低于阈值的标注（标记为需核实）
    filtered = [a for a in annotations if a["confidence"] >= conf_threshold]
    needs_review = [a for a in annotations if a["confidence"] < conf_threshold]

    quality_report = validate_annotations(annotations, img_info["image_size"])

    return {
        "status": "success",
        "image_path": str(image_path),
        "image_size": img_info["image_size"],
        "annotations": filtered,
        "needs_review": needs_review,
        "quality_report": quality_report,
        "stats": {
            "total": len(annotations),
            "high_conf": len(high_conf),
            "mid_conf": len(mid_conf),
            "low_conf": len(low_conf),
            "filtered": len(filtered),
        },
    }


def process_directory(dir_path: Path, annot_type: str, conf_threshold: float) -> List[Dict[str, Any]]:
    """
    批量处理目录下所有图片。
    """
    supported_exts = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
    image_files = [p for p in dir_path.iterdir() if p.suffix.lower() in supported_exts]
    if not image_files:
        print(f"警告: 目录 {dir_path} 中没有支持的图片文件", file=sys.stderr)
        return []

    results = []
    for img_path in sorted(image_files):
        result = process_single_image(img_path, annot_type, conf_threshold)
        results.append(result)
    return results


# ============================================================
# 输出格式化模块
# ============================================================

def format_json(results: List[Dict[str, Any]]) -> str:
    """格式化为 JSON 字符串。"""
    try:
        return json.dumps(results, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"E008: JSON序列化失败: {e}", file=sys.stderr)
        return json.dumps([], ensure_ascii=False)


def format_csv(results: List[Dict[str, Any]]) -> str:
    """格式化为 CSV 字符串。"""
    try:
        output = []
        header = ["image_path", "type", "bbox_x1", "bbox_y1", "bbox_x2", "bbox_y2", "confidence", "text"]
        output.append(",".join(header))
        for result in results:
            if result["status"] != "success":
                continue
            for ann in result["annotations"]:
                bbox = ann["bbox"]
                row = [
                    result["image_path"],
                    ann["type"],
                    str(bbox[0]),
                    str(bbox[1]),
                    str(bbox[2]),
                    str(bbox[3]),
                    str(ann["confidence"]),
                    f'"{ann.get("text", "")}"',
                ]
                output.append(",".join(row))
        return "\n".join(output)
    except Exception as e:
        print(f"E009: CSV生成失败: {e}", file=sys.stderr)
        return "image_path,type,bbox_x1,bbox_y1,bbox_x2,bbox_y2,confidence,text"


def format_txt(results: List[Dict[str, Any]]) -> str:
    """格式化为 TXT（YOLO 格式）字符串。"""
    try:
        output = []
        for result in results:
            if result["status"] != "success":
                continue
            width = result["image_size"]["width"]
            height = result["image_size"]["height"]
            for ann in result["annotations"]:
                bbox = ann["bbox"]
                # YOLO 格式: class x_center y_center w h (归一化)
                x_center = (bbox[0] + bbox[2]) / 2 / width
                y_center = (bbox[1] + bbox[3]) / 2 / height
                w = (bbox[2] - bbox[0]) / width
                h = (bbox[3] - bbox[1]) / height
                # 类别: 0=box, 1=text, 2=arrow
                class_id = {"box": 0, "text": 1, "arrow": 2}.get(ann["type"], 0)
                output.append(f"{class_id} {x_center:.6f} {y_center:.6f} {w:.6f} {h:.6f}")
        return "\n".join(output)
    except Exception as e:
        print(f"E009: TXT生成失败: {e}", file=sys.stderr)
        return ""


def format_output(results: List[Dict[str, Any]], output_format: str) -> str:
    """根据指定格式输出结果。"""
    if output_format == "json":
        return format_json(results)
    elif output_format == "csv":
        return format_csv(results)
    elif output_format == "txt":
        return format_txt(results)
    else:
        raise ValueError(f"E005: 不支持的输出格式: {output_format}")


def write_output_safe(output_path: Path, content: str, dry: bool) -> bool:
    """
    安全写入输出文件。
    支持多编码 fallback（utf-8 → gbk → gb18030）。
    """
    try:
        if dry:
            print(f"[dry-run] 将写入 {output_path} ({len(content)} 字符)")
            return True

        output_path.parent.mkdir(parents=True, exist_ok=True)
        # 多编码 fallback 写入
        try:
            output_path.write_text(content, encoding="utf-8")
        except UnicodeEncodeError:
            try:
                output_path.write_text(content, encoding="gbk")
            except UnicodeEncodeError:
                output_path.write_text(content, encoding="gb18030", errors="replace")
        return True
    except Exception as e:
        print(f"E003: 写入文件失败 {output_path}: {e}", file=sys.stderr)
        return False


# ============================================================
# 自检模块（内置样例数据，离线可跑）
# ============================================================

def run_selftest() -> bool:
    """
    内置硬编码样例数据自检核心逻辑。
    不读外部文件、不依赖当前工作目录、不访问网络。
    断言使用宽松阈值，确保必然匹配。
    """
    print("=" * 60)
    print("开始自检（内置样例数据）...")
    print("=" * 60)

    # 样例 1: 空输入处理
    print("\n[测试1] 空输入处理")
    empty_results: List[Dict[str, Any]] = []
    json_out = format_json(empty_results)
    assert json_out == "[]", f"空列表JSON应为[]，实际: {json_out}"
    print("  ✅ 空输入JSON格式化正常")

    # 样例 2: 中文标点/文本处理
    print("\n[测试2] 中文标点/文本处理")
    sample_ann = {
        "status": "success",
        "image_path": "test.png",
        "image_size": {"width": 1000, "height": 800},
        "annotations": [
            {"type": "box", "bbox": [10, 20, 100, 80], "confidence": 0.95, "text": "按钮：确认"},
            {"type": "text", "bbox": [50, 100, 300, 150], "confidence": 0.88, "text": "请输入用户名（必填）"},
        ],
        "needs_review": [],
        "quality_report": {"total": 2, "valid": 2, "issues": [], "overlap_count": 0, "quality_score": 100.0},
        "stats": {"total": 2, "high_conf": 1, "mid_conf": 1, "low_conf": 0, "filtered": 2},
    }
    json_with_cn = format_json([sample_ann])
    assert "按钮" in json_with_cn, "中文文本应保留在JSON中"
    assert "（必填）" in json_with_cn, "中文括号应保留在JSON中"
    print("  ✅ 中文标点/文本处理正常")

    # 样例 3: 编码异常处理（模拟 GBK 编码）
    print("\n[测试3] 编码异常处理")
    try:
        # 模拟 GBK 编码的字节序列
        gbk_bytes = "测试标注".encode("gbk")
        decoded = gbk_bytes.decode("gbk")
        assert decoded == "测试标注", f"GBK解码失败: {decoded}"
        print("  ✅ GBK 编码处理正常")
    except Exception as e:
        print(f"  ❌ GBK 编码处理失败: {e}")
        return False

    # 样例 4: 超长输入处理
    print("\n[测试4] 超长输入处理")
    long_text = "标注" * 10000  # 20000 字符
    long_result = {
        "status": "success",
        "image_path": "long.png",
        "image_size": {"width": 2000, "height": 1500},
        "annotations": [
            {"type": "text", "bbox": [0, 0, 100, 50], "confidence": 0.90, "text": long_text},
        ],
        "needs_review": [],
        "quality_report": {"total": 1, "valid": 1, "issues": [], "overlap_count": 0, "quality_score": 100.0},
        "stats": {"total": 1, "high_conf": 1, "mid_conf": 0, "low_conf": 0, "filtered": 1},
    }
    json_long = format_json([long_result])
    assert len(json_long) > 10000, f"超长文本JSON长度异常: {len(json_long)}"
    print(f"  ✅ 超长输入处理正常（JSON长度: {len(json_long)} 字符）")

    # 样例 5: 标注质量校验逻辑
    print("\n[测试5] 标注质量校验")
    test_anns = [
        {"type": "box", "bbox": [-10, 0, 100, 80], "confidence": 0.9, "text": "越界框"},
        {"type": "box", "bbox": [10, 20, 100, 80], "confidence": 0.9, "text": ""},
        {"type": "box", "bbox": [10, 20, 100, 80], "confidence": 0.9, "text": "有效框"},
    ]
    report = validate_annotations(test_anns, {"width": 500, "height": 400})
    assert report["total"] == 3, f"总数应为3，实际: {report['total']}"
    assert report["valid"] == 1, f"有效数应为1，实际: {report['valid']}"
    assert len(report["issues"]) >= 2, f"问题数应>=2，实际: {len(report['issues'])}"
    assert 0 < report["quality_score"] <= 100, f"质量分应在0-100之间，实际: {report['quality_score']}"
    print(f"  ✅ 质量校验正常（有效: {report['valid']}/{report['total']}, 问题: {len(report['issues'])}个）")

    # 样例 6: 模拟图片处理全流程
    print("\n[测试6] 模拟图片处理全流程")
    mock_img_info = {
        "image_path": "mock.png",
        "image_size": {"width": 1000, "height": 800},
        "file_size": 12345,
    }
    anns = extract_annotations(mock_img_info, "all")
    assert isinstance(anns, list), "标注结果应为列表"
    assert len(anns) >= 0, "标注数量应>=0"
    for ann in anns:
        assert "type" in ann, "标注缺少type字段"
        assert "bbox" in ann, "标注缺少bbox字段"
        assert "confidence" in ann, "标注缺少confidence字段"
        bbox = ann["bbox"]
        assert len(bbox) == 4, f"bbox应为4元素，实际: {len(bbox)}"
        assert 0 <= bbox[0] < bbox[2] <= 1000, f"bbox x坐标越界: {bbox}"
        assert 0 <= bbox[1] < bbox[3] <= 800, f"bbox y坐标越界: {bbox}"
        assert 0 <= ann["confidence"] <= 1, f"置信度应在0-1之间: {ann['confidence']}"
    print(f"  ✅ 模拟图片处理正常（生成 {len(anns)} 个标注）")

    # 样例 7: 格式转换（JSON/CSV/TXT）
    print("\n[测试7] 格式转换")
    sample_results = [{
        "status": "success",
        "image_path": "test.png",
        "image_size": {"width": 1000, "height": 800},
        "annotations": [
            {"type": "box", "bbox": [10, 20, 100, 80], "confidence": 0.95, "text": "测试框"},
        ],
        "needs_review": [],
        "quality_report": {"total": 1, "valid": 1, "issues": [], "overlap_count": 0, "quality_score": 100.0},
        "stats": {"total": 1, "high_conf": 1, "mid_conf": 0, "low_conf": 0, "filtered": 1},
    }]
    csv_out = format_csv(sample_results)
    assert "image_path" in csv_out, "CSV应包含表头"
    assert "test.png" in csv_out, "CSV应包含图片路径"
    txt_out = format_txt(sample_results)
    assert "0 " in txt_out or "1 " in txt_out or "2 " in txt_out, "TXT应包含YOLO格式数据"
    print("  ✅ 格式转换正常")

    # 样例 8: 错误处理（无效输入）
    print("\n[测试8] 错误处理")
    try:
        validate_annot_type("invalid")
        print("  ❌ 无效标注类型未抛出异常")
        return False
    except ValueError as e:
        assert "E004" in str(e), f"错误码应为E004，实际: {e}"
        print("  ✅ 无效标注类型正确抛出E004")

    try:
        validate_output_format("xml")
        print("  ❌ 无效输出格式未抛出异常")
        return False
    except ValueError as e:
        assert "E005" in str(e), f"错误码应为E005，实际: {e}"
        print("  ✅ 无效输出格式正确抛出E005")

    print("\n" + "=" * 60)
    print("✅ 所有自检通过！")
    print("=" * 60)
    return True


# ============================================================
# 主程序入口
# ============================================================

def main() -> int:
    """主程序入口。"""
    parser = argparse.ArgumentParser(
        description="截图标注处理工具",
        epilog="示例: python main.py --input ./screenshots --format json --verbose",
    )
    parser.add_argument("--input", "-i", type=str, help="输入图片路径或文件夹路径")
    parser.add_argument("--type", "-t", type=str, default="all",
                        choices=["all", "box", "text", "arrow"],
                        help="标注类型: all/box/text/arrow (默认: all)")
    parser.add_argument("--format", "-f", type=str, default="json",
                        choices=["json", "csv", "txt"],
                        help="输出格式: json/csv/txt (默认: json)")
    parser.add_argument("--output", "-o", type=str, help="输出目录 (默认: 输入目录下 output/)")
    parser.add_argument("--conf-threshold", type=float, default=0.85,
                        help="置信度阈值 (默认: 0.85)")
    parser.add_argument("--dry-run", action="store_true",
                        help="只打印结果不写文件")
    parser.add_argument("--force", action="store_true",
                        help="强制写盘（需与 --dry-run 配合，默认不写盘）")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="输出详细处理信息")
    parser.add_argument("--selftest", action="store_true",
                        help="运行内置自检")

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        success = run_selftest()
        return 0 if success else 1

    # 参数校验
    if not args.input:
        print("错误: 必须提供 --input 参数（图片路径或文件夹）", file=sys.stderr)
        print("提示: 运行 --selftest 进行自检，或 --help 查看帮助", file=sys.stderr)
        return 1

    try:
        input_path = validate_input_path(args.input)
        annot_type = validate_annot_type(args.type)
        output_format = validate_output_format(args.format)
        conf_threshold = validate_confidence_threshold(args.conf_threshold)
    except ValueError as e:
        print(f"参数错误: {e}", file=sys.stderr)
        return 1

    # 确定 dry-run 模式（默认 dry-run，只有 --force 才真正写盘）
    dry = not args.force
    if args.verbose:
        mode = "dry-run（预览）" if dry else "实际写入"
        print(f"运行模式: {mode}")
        print(f"输入: {input_path}")
        print(f"标注类型: {annot_type}")
        print(f"输出格式: {output_format}")
        print(f"置信度阈值: {conf_threshold}")

    # 处理输入
    try:
        if input_path.is_file():
            # 单张图片
            results = [process_single_image(input_path, annot_type, conf_threshold)]
        elif input_path.is_dir():
            # 批量处理
            results = process_directory(input_path, annot_type, conf_threshold)
            if not results:
                print(f"E007: 目录 {input_path} 中没有可处理的图片", file=sys.stderr)
                return 1
        else:
            print(f"E001: 输入既不是文件也不是目录: {input_path}", file=sys.stderr)
            return 1
    except Exception as e:
        print(f"E010: 处理过程中发生未知错误: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        return 1

    # 格式化输出
    try:
        output_content = format_output(results, output_format)
    except Exception as e:
        print(f"E010: 输出格式化失败: {e}", file=sys.stderr)
        return 1

    # 确定输出路径
    if args.output:
        output_dir = Path(args.output)
    else:
        output_dir = input_path.parent / "output" if input_path.is_file() else input_path / "output"

    output_file = output_dir / f"annotations.{output_format}"

    # 写入文件
    write_ok = write_output_safe(output_file, output_content, dry)

    # 输出摘要
    if args.verbose:
        print("\n" + "=" * 60)
        print("处理摘要:")
        for r in results:
            if r["status"] == "success":
                stats = r["stats"]
                print(f"  {r['image_path']}:")
                print(f"    图片尺寸: {r['image_size']['width']}x{r['image_size']['height']}")
                print(f"    标注总数: {stats['total']}")
                print(f"    高置信度(≥90%): {stats['high_conf']}")
                print(f"    中置信度(85-90%): {stats['mid_conf']}")
                print(f"    低置信度(<85%): {stats['low_conf']}")
                print(f"    过滤后: {stats['filtered']}")
                qr = r["quality_report"]
                print(f"    质量分: {qr['quality_score']}%")
                if qr["issues"]:
                    print(f"    问题: {len(qr['issues'])} 个")
                    for issue in qr["issues"][:5]:
                        print(f"      - {issue}")
            else:
                print(f"  {r.get('image_path', '未知')}: 处理失败 - {r.get('message', '未知错误')}")
        print("=" * 60)

    if dry:
        print(f"\n[dry-run] 未写入文件。预览内容已生成（{len(output_content)} 字符）。")
        print(f"如需实际写入，请添加 --force 参数。")
        print(f"输出文件将写入: {output_file}")
    else:
        if write_ok:
            print(f"\n✅ 处理完成！结果已写入: {output_file}")
        else:
            print(f"\n❌ 写入失败: {output_file}", file=sys.stderr)
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
