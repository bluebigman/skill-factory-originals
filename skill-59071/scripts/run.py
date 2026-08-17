#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
手机教程全流程处理 Skill 主脚本
将零散手机截图与文字素材自动整理为结构化 Markdown 教程文档。
"""

import argparse
import os
import re
import sys
import shutil
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

try:
    from PIL import Image
    from PIL.ExifTags import TAGS
except ImportError:
    Image = None
    TAGS = None

try:
    import pytesseract
except ImportError:
    pytesseract = None

# 版本信息
VERSION = "2.1.0"

# 错误码定义
ERROR_CODES = {
    "E001": "素材格式不支持",
    "E002": "缺少操作目标描述",
    "E003": "截图顺序混乱",
    "E004": "OCR识别率过低",
    "E005": "输出路径无效",
    "E006": "OCR引擎不可用",
    "E007": "输入路径不存在",
}

# 支持的图片格式
SUPPORTED_IMAGE_FORMATS = {".png", ".jpg", ".jpeg"}

# 设备品牌特征关键词
DEVICE_BRAND_KEYWORDS = {
    "华为": ["华为", "HUAWEI", "HarmonyOS", "EMUI"],
    "小米": ["小米", "Xiaomi", "MIUI", "Redmi"],
    "苹果": ["iPhone", "iOS", "Apple"],
    "OPPO": ["OPPO", "ColorOS"],
    "vivo": ["vivo", "Funtouch", "OriginOS"],
    "三星": ["三星", "Samsung", "One UI"],
}

# OCR 配置
OCR_TIMEOUT = 10  # 秒
OCR_MAX_RETRIES = 3
OCR_RETRY_DELAY = 2  # 秒


class SkillError(Exception):
    """Skill 业务异常基类"""

    def __init__(self, error_code: str, message: str):
        self.error_code = error_code
        self.message = message
        super().__init__(f"[{error_code}] {message}")


class MaterialPreprocessor:
    """素材预检与基础处理"""

    @staticmethod
    def validate_image_format(file_path: str) -> bool:
        """校验图片格式是否为支持的格式"""
        ext = Path(file_path).suffix.lower()
        return ext in SUPPORTED_IMAGE_FORMATS

    @staticmethod
    def read_text_file(file_path: str) -> str:
        """读取文字文件，支持多编码"""
        encodings = ["utf-8", "gbk", "gb18030"]
        for encoding in encodings:
            try:
                with open(file_path, "r", encoding=encoding) as f:
                    return f.read()
            except UnicodeDecodeError:
                continue
            except FileNotFoundError:
                raise SkillError("E007", f"输入路径不存在: {file_path}")
        raise SkillError("E007", f"无法解码文件（尝试了 utf-8/gbk/gb18030）: {file_path}")

    @staticmethod
    def list_images(directory: str) -> List[str]:
        """列出目录下所有支持的图片文件，按文件名排序"""
        if not os.path.isdir(directory):
            raise SkillError("E007", f"输入路径不存在: {directory}")
        images = []
        for f in sorted(os.listdir(directory)):
            full_path = os.path.join(directory, f)
            if os.path.isfile(full_path) and MaterialPreprocessor.validate_image_format(full_path):
                images.append(full_path)
        return images


class DeviceIdentifier:
    """设备品牌与系统版本识别"""

    @staticmethod
    def identify_from_text(text: str) -> Tuple[Optional[str], Optional[str]]:
        """从文本中识别设备品牌与系统版本"""
        brand = None
        system = None
        for b, keywords in DEVICE_BRAND_KEYWORDS.items():
            for kw in keywords:
                if kw.lower() in text.lower():
                    brand = b
                    break
            if brand:
                break

        # 尝试识别系统版本
        version_patterns = [
            r"(HarmonyOS\s*[\d.]+)",
            r"(EMUI\s*[\d.]+)",
            r"(MIUI\s*[\d.]+)",
            r"(iOS\s*[\d.]+)",
            r"(ColorOS\s*[\d.]+)",
            r"(OriginOS\s*[\d.]+)",
            r"(One\s*UI\s*[\d.]+)",
        ]
        for pattern in version_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                system = match.group(1)
                break
        return brand, system

    @staticmethod
    def identify_from_image(image_path: str) -> Tuple[Optional[str], Optional[str]]:
        """从图片 EXIF 或 OCR 文本中识别设备信息"""
        brand = None
        system = None

        # 尝试从 EXIF 读取
        if Image is not None and TAGS is not None:
            try:
                with Image.open(image_path) as img:
                    exif_data = img._getexif()
                    if exif_data:
                        for tag_id, value in exif_data.items():
                            tag_name = TAGS.get(tag_id, tag_id)
                            if tag_name == "Make" and isinstance(value, str):
                                brand = value.strip()
                            elif tag_name == "Model" and isinstance(value, str):
                                if brand:
                                    brand = f"{brand} {value.strip()}"
                                else:
                                    brand = value.strip()
            except Exception as e:
                print(f"[WARN] 降级处理: {e}", file=sys.stderr)  # R2 降级输出  # EXIF 读取失败不影响主流程

        # 尝试从 OCR 文本识别
        if pytesseract is not None:
            try:
                ocr_text = pytesseract.image_to_string(Image.open(image_path))
                b, s = DeviceIdentifier.identify_from_text(ocr_text)
                if b and not brand:
                    brand = b
                if s and not system:
                    system = s
            except Exception as e:
                print(f"[WARN] 降级处理: {e}", file=sys.stderr)  # R2 降级输出  # OCR 失败不影响主流程

        return brand, system


class OCRProcessor:
    """OCR 文字提取处理器"""

    @staticmethod
    def extract_text(image_path: str) -> str:
        """从图片中提取文字，带重试机制"""
        if pytesseract is None:
            raise SkillError("E006", "OCR引擎不可用，请安装 pytesseract 和 tesseract")

        for attempt in range(OCR_MAX_RETRIES):
            try:
                with Image.open(image_path) as img:
                    text = pytesseract.image_to_string(img, timeout=OCR_TIMEOUT)
                    return text.strip()
            except Exception as e:
                if attempt < OCR_MAX_RETRIES - 1:
                    time.sleep(OCR_RETRY_DELAY * (2 ** attempt))  # 指数退避
                else:
                    raise SkillError("E004", f"OCR识别失败: {str(e)}")
        return ""


class TutorialGenerator:
    """教程文档生成器"""

    def __init__(self, device_brand: Optional[str], system_version: Optional[str],
                 operation_goal: Optional[str], verbose: bool = False):
        self.device_brand = device_brand
        self.system_version = system_version
        self.operation_goal = operation_goal
        self.verbose = verbose

    def generate(self, steps: List[Dict], notes: List[str], troubleshooting: List[Dict]) -> str:
        """生成 Markdown 教程文档"""
        lines = []
        goal = self.operation_goal or "[需核实:操作目标]"
        brand = self.device_brand or "[需核实:设备型号]"
        system = self.system_version or "[需核实:系统版本]"

        lines.append(f"# 《{goal}》教程 — {brand} ({system})")
        lines.append("")
        lines.append("## 适用环境")
        lines.append(f"- 设备型号：{brand}")
        lines.append(f"- 系统版本：{system}")
        lines.append("- 适用人群：新手")
        lines.append("")
        lines.append("## 操作步骤")
        lines.append("")

        for i, step in enumerate(steps, 1):
            title = step.get("title", f"步骤 {i}")
            desc = step.get("description", "[需核实:操作说明]")
            expected = step.get("expected", "[需核实:预期结果]")
            image = step.get("image", f"images/step{i}.png")

            lines.append(f"### 步骤 {i}：{title}")
            lines.append(f"![截图占位：步骤{i}截图]({image})")
            lines.append(f"**操作说明**：{desc}")
            lines.append(f"**预期结果**：{expected}")
            lines.append("")

        if notes:
            lines.append("## 注意事项")
            lines.append("")
            for note in notes:
                lines.append(f"- {note}")
            lines.append("")

        if troubleshooting:
            lines.append("## 故障排查")
            lines.append("")
            lines.append("| 问题现象 | 可能原因 | 解决方法 |")
            lines.append("|----------|----------|----------|")
            for item in troubleshooting:
                lines.append(f"| {item.get('phenomenon', '')} | {item.get('cause', '')} | {item.get('solution', '')} |")
            lines.append("")

        return "\n".join(lines)


class ConfidenceCalculator:
    """置信度计算器"""

    @staticmethod
    def calculate_placeholder_ratio(text: str) -> float:
        """计算占位符在文本中的比例"""
        placeholder_pattern = r"\[需核实:[^\]]+\]"
        matches = re.findall(placeholder_pattern, text)
        if not matches:
            return 0.0
        # 占位符数量 / 总行数（粗略估计）
        total_lines = max(len(text.splitlines()), 1)
        return len(matches) / total_lines

    @staticmethod
    def get_confidence_level(ratio: float) -> str:
        """根据占位符比例返回置信度等级"""
        if ratio < 0.1:
            return "高"
        elif ratio < 0.3:
            return "中"
        else:
            return "低"


def atomic_write(file_path: str, content: str, dry_run: bool = False) -> None:
    """原子化写入文件（先写临时文件再重命名）"""
    if dry_run:
        print(f"[DRY-RUN] 将写入: {file_path}")
        print(f"[DRY-RUN] 内容摘要: {len(content)} 字符, {len(content.splitlines())} 行")
        return

    directory = os.path.dirname(os.path.abspath(file_path))
    if not os.path.isdir(directory):
        raise SkillError("E005", f"输出路径无效: {directory}")

    fd, temp_path = tempfile.mkstemp(dir=directory, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(temp_path, file_path)
    except Exception:
        if os.path.exists(temp_path):
            os.unlink(temp_path)
        raise


def process_material(images: List[str], text: Optional[str],
                     verbose: bool = False) -> Tuple[str, Dict]:
    """处理素材，返回教程文档与元信息"""
    if verbose:
        print(f"[INFO] 处理 {len(images)} 张图片, 文字素材: {'有' if text else '无'}")

    # 1. 收集所有文本（图片 OCR + 文字文件）
    all_text = text or ""
    ocr_texts = []
    for img_path in images:
        if pytesseract is not None:
            try:
                ocr_text = OCRProcessor.extract_text(img_path)
                ocr_texts.append(ocr_text)
                all_text += "\n" + ocr_text
            except SkillError as e:
                if verbose:
                    print(f"[WARN] {e.message}")
        else:
            if verbose:
                print("[WARN] OCR 引擎不可用，跳过图片文字提取")

    # 2. 识别设备
    brand, system = None, None
    for img_path in images:
        b, s = DeviceIdentifier.identify_from_image(img_path)
        if b and not brand:
            brand = b
        if s and not system:
            system = s
        if brand and system:
            break

    if not brand and all_text:
        brand, _ = DeviceIdentifier.identify_from_text(all_text)
    if not system and all_text:
        _, system = DeviceIdentifier.identify_from_text(all_text)

    # 3. 提取操作目标（从文字素材中）
    operation_goal = None
    if text:
        # 尝试从文字中提取操作目标（第一行或包含"设置/开启/关闭"的行）
        for line in text.splitlines():
            line = line.strip()
            if any(kw in line for kw in ["设置", "开启", "关闭", "配置", "安装", "卸载"]):
                operation_goal = line[:50]
                break

    # 4. 构建步骤
    steps = []
    for i, img_path in enumerate(images, 1):
        step = {
            "title": f"操作步骤 {i}",
            "description": f"参考截图 {os.path.basename(img_path)} 进行操作",
            "expected": "[需核实:预期结果]",
            "image": f"images/step{i}.png",
        }
        if i < len(ocr_texts) and ocr_texts[i - 1]:
            # 从 OCR 文本中提取可能的操作描述
            first_line = ocr_texts[i - 1].splitlines()[0] if ocr_texts[i - 1].splitlines() else ""
            if first_line and len(first_line) < 50:
                step["description"] = first_line
        steps.append(step)

    # 5. 生成文档
    generator = TutorialGenerator(brand, system, operation_goal, verbose)
    doc = generator.generate(steps, [], [])

    # 6. 计算置信度
    ratio = ConfidenceCalculator.calculate_placeholder_ratio(doc)
    level = ConfidenceCalculator.get_confidence_level(ratio)

    meta = {
        "device_brand": brand,
        "system_version": system,
        "operation_goal": operation_goal,
        "step_count": len(steps),
        "placeholder_ratio": ratio,
        "confidence_level": level,
    }
    return doc, meta


def run_selftest() -> int:
    """运行自检，验证核心功能"""
    print("[SELFTEST] 开始自检...")
    failures = 0

    # 测试 1: 设备识别
    print("[SELFTEST] 测试设备识别...")
    brand, system = DeviceIdentifier.identify_from_text("HUAWEI Mate 60 Pro HarmonyOS 4.0")
    if brand != "华为":
        print(f"[FAIL] 品牌识别失败: 期望 '华为', 实际 '{brand}'")
        failures += 1
    else:
        print("[PASS] 品牌识别")

    # 测试 2: 占位符比例计算
    print("[SELFTEST] 测试置信度计算...")
    test_doc = "正常内容\n[需核实:设备型号]\n正常内容\n[需核实:系统版本]"
    ratio = ConfidenceCalculator.calculate_placeholder_ratio(test_doc)
    if ratio <= 0:
        print(f"[FAIL] 占位符比例计算异常: {ratio}")
        failures += 1
    else:
        print(f"[PASS] 占位符比例计算: {ratio:.2f}")

    # 测试 3: 文档生成
    print("[SELFTEST] 测试文档生成...")
    gen = TutorialGenerator("华为", "HarmonyOS 4.0", "设置双卡", verbose=False)
    steps = [{"title": "打开设置", "description": "点击设置图标", "expected": "进入设置界面"}]
    doc = gen.generate(steps, ["注意备份"], [])
    if "设置双卡" not in doc or "打开设置" not in doc:
        print("[FAIL] 文档生成内容缺失")
        failures += 1
    else:
        print("[PASS] 文档生成")

    # 测试 4: 素材预检
    print("[SELFTEST] 测试素材预检...")
    if not MaterialPreprocessor.validate_image_format("test.png"):
        print("[FAIL] PNG 格式校验失败")
        failures += 1
    else:
        print("[PASS] PNG 格式校验")

    # 测试 5: 文字文件读取（多编码）
    print("[SELFTEST] 测试文字文件读取...")
    with tempfile.NamedTemporaryFile(mode="w", encoding="gbk", suffix=".txt", delete=False) as f:
        f.write("设置双卡双待\n")
        temp_path = f.name
    try:
        content = MaterialPreprocessor.read_text_file(temp_path)
        if "设置双卡" not in content:
            print("[FAIL] GBK 编码读取失败")
            failures += 1
        else:
            print("[PASS] GBK 编码读取")
    finally:
        os.unlink(temp_path)

    # 测试 6: 原子写入
    print("[SELFTEST] 测试原子写入...")
    with tempfile.TemporaryDirectory() as tmpdir:
        out_path = os.path.join(tmpdir, "test.md")
        atomic_write(out_path, "# 测试文档\n", dry_run=False)
        if not os.path.exists(out_path):
            print("[FAIL] 原子写入失败")
            failures += 1
        else:
            with open(out_path, "r", encoding="utf-8") as f:
                if f.read() != "# 测试文档\n":
                    print("[FAIL] 原子写入内容错误")
                    failures += 1
                else:
                    print("[PASS] 原子写入")

    # 测试 7: 完整流程（使用临时目录）
    print("[SELFTEST] 测试完整流程...")
    with tempfile.TemporaryDirectory() as tmpdir:
        # 创建测试图片（如果 PIL 可用）
        if Image is not None:
            img_path = os.path.join(tmpdir, "01.png")
            img = Image.new("RGB", (100, 100), color="white")
            img.save(img_path)
            images = [img_path]
        else:
            images = []

        text_path = os.path.join(tmpdir, "notes.txt")
        with open(text_path, "w", encoding="utf-8") as f:
            f.write("设置双卡双待\n")

        try:
            doc, meta = process_material(images, "设置双卡双待", verbose=False)
            if meta["step_count"] != len(images):
                print(f"[FAIL] 步骤数不匹配: 期望 {len(images)}, 实际 {meta['step_count']}")
                failures += 1
            elif not doc:
                print("[FAIL] 文档为空")
                failures += 1
            else:
                print(f"[PASS] 完整流程 (步骤数: {meta['step_count']}, 置信度: {meta['confidence_level']})")
        except SkillError as e:
            print(f"[FAIL] 完整流程异常: {e.message}")
            failures += 1

    if failures == 0:
        print("[SELFTEST] 全部通过 ✓")
        return 0
    else:
        print(f"[SELFTEST] {failures} 项失败 ✗")
        return 1


def main():
    """CLI 入口"""
    parser = argparse.ArgumentParser(
        description="手机教程全流程处理：将截图与文字素材整理为 Markdown 教程文档",
        epilog=f"版本 {VERSION} | 错误码: {', '.join(ERROR_CODES.keys())}"
    )
    parser.add_argument("--images", type=str, help="截图目录路径（包含 PNG/JPG 文件）")
    parser.add_argument("--text", type=str, help="文字素材文件路径（支持 utf-8/gbk/gb18030）")
    parser.add_argument("--output", type=str, default="./tutorial.md", help="输出 Markdown 文件路径")
    parser.add_argument("--dry-run", action="store_true", help="预览模式：只打印将写入的内容，不写盘")
    parser.add_argument("--verbose", action="store_true", help="输出详细处理日志")
    parser.add_argument("--selftest", action="store_true", help="运行自检并退出")
    parser.add_argument("--version", action="version", version=f"%(prog)s {VERSION}")

    args = parser.parse_args()

    if args.selftest:
        sys.exit(run_selftest())

    # 输入校验
    if not args.images and not args.text:
        parser.error("至少需要 --images 或 --text 之一")

    images = []
    if args.images:
        try:
            images = MaterialPreprocessor.list_images(args.images)
        except SkillError as e:
            print(f"错误: {e.message}", file=sys.stderr)
            sys.exit(1)

    text = None
    if args.text:
        try:
            text = MaterialPreprocessor.read_text_file(args.text)
        except SkillError as e:
            print(f"错误: {e.message}", file=sys.stderr)
            sys.exit(1)

    if not images and not text:
        print("错误: 未找到任何有效素材（图片或文字）", file=sys.stderr)
        sys.exit(1)

    # 处理素材
    try:
        doc, meta = process_material(images, text, verbose=args.verbose)
    except SkillError as e:
        print(f"错误: {e.message}", file=sys.stderr)
        sys.exit(1)

    # 输出摘要
    if args.verbose:
        print(f"[INFO] 设备: {meta['device_brand'] or '未知'}")
        print(f"[INFO] 系统: {meta['system_version'] or '未知'}")
        print(f"[INFO] 操作目标: {meta['operation_goal'] or '未知'}")
        print(f"[INFO] 步骤数: {meta['step_count']}")
        print(f"[INFO] 占位符比例: {meta['placeholder_ratio']:.2%}")
        print(f"[INFO] 置信度: {meta['confidence_level']}")

    # 写入文件
    try:
        atomic_write(args.output, doc, dry_run=args.dry_run)
        if not args.dry_run:
            print(f"教程已生成: {args.output}")
            print(f"置信度: {meta['confidence_level']} (占位符比例 {meta['placeholder_ratio']:.2%})")
        else:
            print("[DRY-RUN] 预览完成，未写入任何文件。")
    except SkillError as e:
        print(f"错误: {e.message}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
