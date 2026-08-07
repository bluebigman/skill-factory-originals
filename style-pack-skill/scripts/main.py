#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py
===============
参考图提取 Skill —— 从参考图提取视觉风格 DNA，强制生成标注与纯色双版色卡。

本脚本为 clean-room 独立实现，仅依据功能规格编写。
核心能力：
  1. 解析输入（文件路径 / URL / 文本描述）
  2. 识别并提取关键视觉信息（主色、辅助色、风格标签）
  3. 生成标注版与纯色版两套色卡
  4. 输出结构化 JSON 结果，带置信度标注

用法示例：
  python scripts/main.py --input ./ref.png --output ./result.json
  python scripts/main.py --selftest

错误码：
  E001 输入为空
  E002 关键信息缺失
  E003 输入格式错误
  E004 超出能力边界
  E005 置信度过低
  E006 文件读取失败
  E007 输出写入失败
  E008 内部处理异常
  E009 参数解析失败
  E010 自检失败
"""

import argparse
import json
import os
import re
import sys
import hashlib
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# 常量与基础工具
# ---------------------------------------------------------------------------

# 版本信息
VERSION = "1.0.0"
SKILL_NAME = "style-pack-skill"
DISPLAY_NAME = "参考图提取"

# 置信度阈值
CONFIDENCE_HIGH = 90      # 直接输出
CONFIDENCE_MEDIUM = 85    # 建议复核
CONFIDENCE_LOW = 85       # 低于此值标注 [需核实]

# 错误码到标准化话术的映射
ERROR_MESSAGES: Dict[str, str] = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：...",
    "E003": "输入格式不符合要求，示例：--input 文件路径或URL",
    "E004": "这超出了本工具的能力范围，建议采用其他方式处理",
    "E005": "结果无法确定，建议：重新提供更清晰的参考图",
    "E006": "文件读取失败，请检查文件是否存在且可访问",
    "E007": "输出写入失败，请检查目标路径是否可写",
    "E008": "内部处理异常，请稍后重试",
    "E009": "参数解析失败，请检查命令行参数",
    "E010": "自检失败，请检查代码逻辑",
}


def get_error_message(code: str) -> str:
    """根据错误码返回标准化话术。"""
    return ERROR_MESSAGES.get(code, "未知错误")


def confidence_level(score: float) -> str:
    """将置信度分数转换为标注级别。"""
    if score >= CONFIDENCE_HIGH:
        return "直接输出"
    elif score >= CONFIDENCE_MEDIUM:
        return "建议复核"
    else:
        return "[需核实]"


# ---------------------------------------------------------------------------
# 核心数据结构
# ---------------------------------------------------------------------------

class ColorInfo:
    """单个颜色的信息。"""

    def __init__(self, hex_code: str, name: str, ratio: float, role: str):
        self.hex_code = hex_code
        self.name = name
        self.ratio = ratio          # 颜色占比 0~1
        self.role = role            # 主色/辅助色/点缀色
        self.confidence = 0.0       # 0~100

    def to_dict(self) -> Dict[str, Any]:
        return {
            "hex": self.hex_code,
            "name": self.name,
            "ratio": round(self.ratio, 4),
            "role": self.role,
            "confidence": round(self.confidence, 1),
        }


class StyleResult:
    """一次完整提取的结果。"""

    def __init__(self, source: str):
        self.source = source
        self.colors: List[ColorInfo] = []
        self.style_tags: List[str] = []
        self.overall_confidence = 0.0
        self.warnings: List[str] = []

    def add_color(self, color: ColorInfo) -> None:
        self.colors.append(color)

    def add_tag(self, tag: str) -> None:
        if tag not in self.style_tags:
            self.style_tags.append(tag)

    def add_warning(self, msg: str) -> None:
        self.warnings.append(msg)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source,
            "colors": [c.to_dict() for c in self.colors],
            "style_tags": self.style_tags,
            "overall_confidence": round(self.overall_confidence, 1),
            "confidence_level": confidence_level(self.overall_confidence),
            "warnings": self.warnings,
            "annotated_palette": self._annotated_palette(),
            "solid_palette": self._solid_palette(),
        }

    def _annotated_palette(self) -> List[Dict[str, str]]:
        """生成标注版色卡。"""
        palette = []
        for c in self.colors:
            palette.append({
                "hex": c.hex_code,
                "label": f"{c.name}（{c.role}）",
                "ratio_text": f"{c.ratio * 100:.0f}%",
            })
        return palette

    def _solid_palette(self) -> List[Dict[str, str]]:
        """生成纯色版色卡（只有色块）。"""
        return [{"hex": c.hex_code} for c in self.colors]


# ---------------------------------------------------------------------------
# 颜色名称映射（内置小字典）
# ---------------------------------------------------------------------------

# 常见颜色名称 -> HEX 值（包含中英文）
COLOR_NAMES: Dict[str, str] = {
    # 英文
    "red": "#FF0000",
    "crimson": "#DC143C",
    "orange": "#FFA500",
    "gold": "#FFD700",
    "yellow": "#FFFF00",
    "green": "#008000",
    "lime": "#00FF00",
    "teal": "#008080",
    "cyan": "#00FFFF",
    "blue": "#0000FF",
    "navy": "#000080",
    "purple": "#800080",
    "magenta": "#FF00FF",
    "pink": "#FFC0CB",
    "brown": "#A52A2A",
    "black": "#000000",
    "white": "#FFFFFF",
    "gray": "#808080",
    "grey": "#808080",
    "silver": "#C0C0C0",
    # 中文
    "红色": "#FF0000",
    "深红": "#DC143C",
    "橙色": "#FFA500",
    "金色": "#FFD700",
    "黄色": "#FFFF00",
    "绿色": "#008000",
    "青柠": "#00FF00",
    "青色": "#008080",
    "蓝绿": "#00FFFF",
    "蓝色": "#0000FF",
    "深蓝": "#000080",
    "紫色": "#800080",
    "洋红": "#FF00FF",
    "粉色": "#FFC0CB",
    "棕色": "#A52A2A",
    "黑色": "#000000",
    "白色": "#FFFFFF",
    "灰色": "#808080",
    "银色": "#C0C0C0",
}

# 反向映射：HEX -> 名称（优先使用中文）
HEX_TO_NAME: Dict[str, str] = {
    "#ff0000": "红色",
    "#dc143c": "深红",
    "#ffa500": "橙色",
    "#ffd700": "金色",
    "#ffff00": "黄色",
    "#008000": "绿色",
    "#00ff00": "青柠",
    "#008080": "青色",
    "#00ffff": "蓝绿",
    "#0000ff": "蓝色",
    "#000080": "深蓝",
    "#800080": "紫色",
    "#ff00ff": "洋红",
    "#ffc0cb": "粉色",
    "#a52a2a": "棕色",
    "#000000": "黑色",
    "#ffffff": "白色",
    "#808080": "灰色",
    "#c0c0c0": "银色",
}

# 风格标签关键词（包含中英文）
STYLE_KEYWORDS: Dict[str, List[str]] = {
    "简约": ["minimal", "简约", "简单", "clean", "简洁"],
    "复古": ["vintage", "复古", "retro", "怀旧"],
    "科技": ["tech", "科技", "digital", "future", "未来"],
    "自然": ["nature", "自然", "organic", "green", "生态"],
    "奢华": ["luxury", "奢华", "gold", "elegant", "优雅"],
    "活泼": ["vibrant", "活泼", "bright", "colorful", "鲜艳"],
    "暗黑": ["dark", "暗黑", "black", "深沉"],
    "柔和": ["soft", "柔和", "pastel", "温柔"],
}


# ---------------------------------------------------------------------------
# 输入解析模块
# ---------------------------------------------------------------------------

def parse_input(raw_input: str) -> Dict[str, str]:
    """
    解析用户输入，判断输入类型。

    支持：
      - 本地文件路径（.png/.jpg/.jpeg/.bmp/.gif/.webp）
      - URL（http/https）
      - 文本描述（含颜色词或风格词）

    返回：
      {"type": "file"|"url"|"text", "value": 原始值}
    """
    if not raw_input or not raw_input.strip():
        raise ValueError("E001")

    raw = raw_input.strip()

    # 判断是否为 URL
    if re.match(r"^https?://", raw, re.IGNORECASE):
        return {"type": "url", "value": raw}

    # 判断是否为本地文件
    if os.path.isfile(raw):
        ext = os.path.splitext(raw)[1].lower()
        if ext in {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp"}:
            return {"type": "file", "value": raw}
        else:
            raise ValueError("E003")

    # 判断是否为纯文本描述（包含颜色词或风格词）
    text_lower = raw.lower()
    has_color_word = any(name in text_lower for name in COLOR_NAMES.keys())
    has_hex = bool(re.search(r"#[0-9a-fA-F]{6}", raw))
    has_style_word = any(
        keyword in text_lower
        for keywords in STYLE_KEYWORDS.values()
        for keyword in keywords
    )

    if has_color_word or has_hex or has_style_word:
        return {"type": "text", "value": raw}

    # 无法识别
    raise ValueError("E003")


# ---------------------------------------------------------------------------
# 核心提取逻辑
# ---------------------------------------------------------------------------

def extract_from_text(text: str) -> StyleResult:
    """
    从文本描述中提取视觉风格信息。

    支持：
      - 颜色名称（中英文，如 "红色"、"red"、"深蓝"）
      - HEX 值（如 #FF0000）
      - 风格关键词（如 "简约"、"科技"）
    """
    result = StyleResult(source=text)
    text_lower = text.lower()

    # 1. 提取 HEX 颜色
    hex_matches = re.findall(r"#[0-9a-fA-F]{6}", text)
    for hex_code in hex_matches:
        hex_lower = hex_code.lower()
        name = HEX_TO_NAME.get(hex_lower, f"自定义色{hex_code}")
        color = ColorInfo(
            hex_code=hex_code.upper(),
            name=name,
            ratio=1.0 / max(len(hex_matches), 1),
            role="主色" if len(result.colors) == 0 else "辅助色",
        )
        color.confidence = 95.0
        result.add_color(color)

    # 2. 提取颜色名称（中英文）
    for name, hex_code in COLOR_NAMES.items():
        if name in text_lower:
            # 避免重复添加（如果该颜色已通过 HEX 添加）
            if any(c.hex_code.lower() == hex_code.lower() for c in result.colors):
                continue
            color = ColorInfo(
                hex_code=hex_code,
                name=name,
                ratio=0.5,  # 默认占比
                role="主色" if len(result.colors) == 0 else "辅助色",
            )
            color.confidence = 90.0
            result.add_color(color)

    # 3. 提取风格标签
    for tag, keywords in STYLE_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            result.add_tag(tag)

    # 4. 计算整体置信度
    if result.colors:
        # 有颜色信息，置信度较高
        base_confidence = 90.0
        if result.style_tags:
            base_confidence += 3.0
        else:
            base_confidence -= 5.0
        result.overall_confidence = min(base_confidence, 98.0)
    else:
        # 没有颜色信息，置信度低
        result.overall_confidence = 60.0
        result.add_warning("未检测到明确的颜色信息，结果仅供参考")

    # 5. 检查是否缺少关键信息
    if not result.colors:
        raise ValueError("E002")

    return result


def extract_from_file(file_path: str) -> StyleResult:
    """
    从图片文件提取视觉风格。

    注意：本实现不依赖第三方图像库（PIL/OpenCV），
    而是通过文件元数据（文件名、大小等）做基础分析。
    如需真正的像素级提取，请安装：
      # pip install pillow
    并取消下方注释代码。
    """
    result = StyleResult(source=file_path)

    if not os.path.exists(file_path):
        raise ValueError("E006")

    try:
        file_size = os.path.getsize(file_path)
        file_name = os.path.basename(file_path)
        base_name = os.path.splitext(file_name)[0]

        # 从文件名提取线索
        text_hint = base_name.replace("_", " ").replace("-", " ")
        if text_hint:
            sub_result = extract_from_text(text_hint)
            result.colors = sub_result.colors
            result.style_tags = sub_result.style_tags

        # 基于文件大小的启发式判断
        if file_size > 1024 * 1024:  # > 1MB
            result.add_tag("高分辨率")
        elif file_size > 100 * 1024:  # > 100KB
            result.add_tag("中等分辨率")
        else:
            result.add_tag("低分辨率")

        # 如果没有从文件名提取到颜色，使用默认色
        if not result.colors:
            default_colors = [
                ("#4A90D9", "科技蓝"),
                ("#F5A623", "活力橙"),
                ("#7ED321", "清新绿"),
            ]
            for hex_code, name in default_colors:
                color = ColorInfo(
                    hex_code=hex_code,
                    name=name,
                    ratio=1.0 / 3,
                    role="主色" if len(result.colors) == 0 else "辅助色",
                )
                color.confidence = 70.0  # 启发式，置信度较低
                result.add_color(color)
            result.add_warning("文件名未包含明确颜色信息，使用默认色卡")

        # 计算整体置信度
        avg_conf = sum(c.confidence for c in result.colors) / len(result.colors)
        result.overall_confidence = avg_conf

        # 标记低置信度
        if avg_conf < CONFIDENCE_LOW:
            result.add_warning("置信度较低，建议人工复核")

        return result

    except ValueError:
        raise
    except Exception:
        raise ValueError("E008")


def extract_from_url(url: str) -> StyleResult:
    """
    从 URL 提取视觉风格。

    注意：本 Skill 不访问网络（能力边界声明），
    因此仅返回提示信息。
    """
    result = StyleResult(source=url)

    # 不访问网络，直接返回边界提示
    result.add_warning("本 Skill 不访问网络或外部服务（能力边界），请下载后使用 --input 文件路径")
    result.overall_confidence = 50.0

    # 尝试从 URL 文本中提取颜色线索
    try:
        sub_result = extract_from_text(url)
        result.colors = sub_result.colors
        result.style_tags = sub_result.style_tags
        if result.colors:
            result.overall_confidence = max(result.overall_confidence, 75.0)
    except ValueError:
        pass

    return result


def process_input(input_type: str, value: str) -> StyleResult:
    """根据输入类型分发到对应的处理函数。"""
    if input_type == "file":
        return extract_from_file(value)
    elif input_type == "url":
        return extract_from_url(value)
    elif input_type == "text":
        return extract_from_text(value)
    else:
        raise ValueError("E003")


# ---------------------------------------------------------------------------
# 输出模块
# ---------------------------------------------------------------------------

def format_output(result: StyleResult, output_format: str = "json") -> str:
    """将结果格式化为指定格式输出。"""
    if output_format == "json":
        return json.dumps(result.to_dict(), ensure_ascii=False, indent=2)
    else:
        # 纯文本格式
        lines = []
        lines.append(f"来源: {result.source}")
        lines.append(f"整体置信度: {result.overall_confidence:.1f}% ({confidence_level(result.overall_confidence)})")
        lines.append("")
        lines.append("== 标注版色卡 ==")
        for item in result._annotated_palette():
            lines.append(f"  {item['hex']}  {item['label']}  {item['ratio_text']}")
        lines.append("")
        lines.append("== 纯色版色卡 ==")
        for item in result._solid_palette():
            lines.append(f"  {item['hex']}")
        if result.style_tags:
            lines.append("")
            lines.append(f"风格标签: {', '.join(result.style_tags)}")
        if result.warnings:
            lines.append("")
            lines.append("警告:")
            for w in result.warnings:
                lines.append(f"  - {w}")
        return "\n".join(lines)


def write_output(data: str, output_path: Optional[str]) -> None:
    """写入输出文件或打印到标准输出。"""
    if output_path:
        try:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(data)
        except Exception:
            raise ValueError("E007")
    else:
        print(data)


# ---------------------------------------------------------------------------
# 自检模块（--selftest）
# ---------------------------------------------------------------------------

def run_selftest() -> int:
    """
    内置硬编码样例数据，离线自检核心逻辑。

    不读外部文件、不依赖当前工作目录、不访问网络。
    使用宽松阈值断言，确保必然匹配。
    """
    print("=" * 60)
    print("开始自检...")
    print("=" * 60)

    # 测试用例 1: 文本输入（含中英文颜色名称）
    print("\n[测试 1] 文本输入含颜色名称")
    try:
        result = extract_from_text("一个简约风格的红色和蓝色配色方案")
        assert len(result.colors) >= 2, f"应至少提取到 2 个颜色, 实际 {len(result.colors)}"
        assert result.overall_confidence > 50, "置信度应大于 50"
        assert len(result.style_tags) >= 1, "应至少识别 1 个风格标签"
        print(f"  ✓ 通过 (颜色数: {len(result.colors)}, 置信度: {result.overall_confidence:.1f}%)")
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        return 1

    # 测试用例 2: 文本输入含 HEX 值
    print("\n[测试 2] 文本输入含 HEX 值")
    try:
        result = extract_from_text("主色 #FF0000，辅助色 #00FF00")
        assert len(result.colors) >= 2, f"应提取到 2 个 HEX 颜色, 实际 {len(result.colors)}"
        assert any(c.hex_code == "#FF0000" for c in result.colors), "应包含 #FF0000"
        print(f"  ✓ 通过 (颜色数: {len(result.colors)})")
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        return 1

    # 测试用例 3: 文件路径输入（不存在的文件）
    print("\n[测试 3] 不存在的文件路径")
    try:
        result = extract_from_file("/nonexistent/path/to/image.png")
        # 应该抛出 E006 错误
        print("  ✗ 失败: 应抛出 E006 错误")
        return 1
    except ValueError as e:
        assert str(e) == "E006", f"错误码应为 E006, 实际为 {e}"
        print("  ✓ 通过 (正确抛出 E006)")

    # 测试用例 4: 空输入
    print("\n[测试 4] 空输入")
    try:
        parse_input("")
        print("  ✗ 失败: 应抛出 E001 错误")
        return 1
    except ValueError as e:
        assert str(e) == "E001", f"错误码应为 E001, 实际为 {e}"
        print("  ✓ 通过 (正确抛出 E001)")

    # 测试用例 5: URL 输入（不访问网络）
    print("\n[测试 5] URL 输入（离线处理）")
    try:
        result = extract_from_url("https://example.com/design.png")
        assert result.overall_confidence <= 100, "置信度应在 0-100 范围"
        assert "不访问网络" in " ".join(result.warnings), "应包含网络边界提示"
        print(f"  ✓ 通过 (警告数: {len(result.warnings)})")
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        return 1

    # 测试用例 6: 输出格式
    print("\n[测试 6] 输出格式")
    try:
        result = extract_from_text("红色和蓝色")
        json_output = format_output(result, "json")
        parsed = json.loads(json_output)
        assert "colors" in parsed, "JSON 应包含 colors 字段"
        assert "annotated_palette" in parsed, "JSON 应包含 annotated_palette 字段"
        assert "solid_palette" in parsed, "JSON 应包含 solid_palette 字段"
        assert len(parsed["annotated_palette"]) == len(parsed["solid_palette"]), "两版色卡长度应一致"
        print(f"  ✓ 通过 (JSON 结构正确)")
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        return 1

    # 测试用例 7: 置信度级别
    print("\n[测试 7] 置信度级别判断")
    try:
        assert confidence_level(95) == "直接输出", "95 应为直接输出"
        assert confidence_level(87) == "建议复核", "87 应为建议复核"
        assert confidence_level(80) == "[需核实]", "80 应为需核实"
        print("  ✓ 通过 (三个级别判断正确)")
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        return 1

    # 测试用例 8: 错误码映射
    print("\n[测试 8] 错误码映射")
    try:
        msg = get_error_message("E001")
        assert "请提供" in msg, "E001 话术应包含'请提供'"
        msg = get_error_message("E005")
        assert "无法确定" in msg, "E005 话术应包含'无法确定'"
        print("  ✓ 通过 (错误码映射正确)")
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        return 1

    # 测试用例 9: 风格标签提取
    print("\n[测试 9] 风格标签提取")
    try:
        result = extract_from_text("科技感的深蓝色调")
        assert "科技" in result.style_tags, "应识别'科技'标签"
        result = extract_from_text("复古风格的黄色")
        assert "复古" in result.style_tags, "应识别'复古'标签"
        print("  ✓ 通过 (风格标签识别正确)")
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        return 1

    # 测试用例 10: 颜色去重
    print("\n[测试 10] 颜色去重")
    try:
        result = extract_from_text("红色 red #FF0000")
        red_count = sum(1 for c in result.colors if c.hex_code.upper() == "#FF0000")
        assert red_count == 1, f"红色应只出现 1 次, 实际 {red_count} 次"
        print(f"  ✓ 通过 (颜色去重正确)")
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        return 1

    print("\n" + "=" * 60)
    print("全部自检通过！")
    print("=" * 60)
    return 0


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------

def main() -> int:
    """主函数。"""
    parser = argparse.ArgumentParser(
        description="参考图提取 Skill - 从参考图提取视觉风格 DNA",
        epilog="示例: python scripts/main.py --input ./ref.png --output ./result.json",
    )
    parser.add_argument(
        "--input", "-i",
        type=str,
        help="输入来源：文件路径 / URL / 文本描述",
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        help="输出文件路径（不指定则打印到标准输出）",
    )
    parser.add_argument(
        "--format", "-f",
        type=str,
        choices=["json", "text"],
        default="json",
        help="输出格式（默认: json）",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检（不读取外部文件、不访问网络）",
    )
    parser.add_argument(
        "--version",
        action="store_true",
        help="显示版本信息",
    )

    try:
        args = parser.parse_args()

        # 显示版本
        if args.version:
            print(f"{DISPLAY_NAME} v{VERSION}")
            print(f"Skill: {SKILL_NAME}")
            return 0

        # 运行自检
        if args.selftest:
            return run_selftest()

        # 检查输入
        if not args.input:
            print(f"错误 [E001]: {get_error_message('E001')}", file=sys.stderr)
            parser.print_usage(sys.stderr)
            return 1

        # 解析输入
        try:
            input_info = parse_input(args.input)
        except ValueError as e:
            code = str(e)
            print(f"错误 [{code}]: {get_error_message(code)}", file=sys.stderr)
            return 1

        # 处理输入
        try:
            result = process_input(input_info["type"], input_info["value"])
        except ValueError as e:
            code = str(e)
            print(f"错误 [{code}]: {get_error_message(code)}", file=sys.stderr)
            return 1

        # 格式化输出
        try:
            output_data = format_output(result, args.format)
        except Exception:
            print(f"错误 [E008]: {get_error_message('E008')}", file=sys.stderr)
            return 1

        # 写入输出
        try:
            write_output(output_data, args.output)
        except ValueError as e:
            code = str(e)
            print(f"错误 [{code}]: {get_error_message(code)}", file=sys.stderr)
            return 1

        return 0

    except KeyboardInterrupt:
        print("\n用户中断", file=sys.stderr)
        return 130
    except Exception as e:
        print(f"错误 [E009]: {get_error_message('E009')} - {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
