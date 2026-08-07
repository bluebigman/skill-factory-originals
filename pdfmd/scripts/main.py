#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pdfmd - PDF转文档工具

基于功能规格独立实现（clean-room），不依赖任何既有代码。
提供智能标题检测、页眉页脚移除、孤立片段合并等核心能力。

用法:
    python main.py --selftest          # 运行内置自检
    python main.py --help              # 显示帮助
"""

import argparse
import re
import sys
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

# ============================================================
# 错误码定义（E001-E010）
# ============================================================
ERROR_CODES = {
    "E001": "输入为空",
    "E002": "关键信息缺失",
    "E003": "输入格式错误",
    "E004": "超出能力边界",
    "E005": "置信度过低",
    "E006": "文件读取失败",
    "E007": "输出写入失败",
    "E008": "参数错误",
    "E009": "内部处理错误",
    "E010": "未知错误",
}


class PdfmdError(Exception):
    """自定义异常，携带错误码"""

    def __init__(self, code: str, message: str = ""):
        self.code = code
        self.message = message or ERROR_CODES.get(code, "未知错误")
        super().__init__(f"[{self.code}] {self.message}")


# ============================================================
# 数据模型
# ============================================================
@dataclass
class TextBlock:
    """文本块"""
    text: str
    font_size: float = 0.0
    is_bold: bool = False
    position: Dict[str, float] = field(default_factory=dict)  # x, y, width, height
    page_num: int = 0


@dataclass
class ConversionResult:
    """转换结果"""
    markdown: str = ""
    confidence: float = 1.0
    warnings: List[str] = field(default_factory=list)
    stats: Dict[str, int] = field(default_factory=dict)


# ============================================================
# 核心处理器
# ============================================================
class PdfToMarkdownConverter:
    """PDF转Markdown核心处理器"""

    # 页眉页脚常见关键词（用于启发式检测）
    HEADER_FOOTER_KEYWORDS = [
        "page", "第", "页", "copyright", "©", "www.", "http",
        "confidential", "机密", "公司", "有限公司", "版权所有",
    ]

    # 标题特征：字号阈值（相对值）
    TITLE_SIZE_RATIO = 1.2  # 字号大于正文1.2倍视为标题
    SUBTITLE_SIZE_RATIO = 1.0  # 字号等于正文视为子标题

    def __init__(self):
        self.blocks: List[TextBlock] = []
        self.result: ConversionResult = ConversionResult()

    def convert(self, blocks: List[TextBlock]) -> ConversionResult:
        """执行转换主流程"""
        if not blocks:
            raise PdfmdError("E001", "输入为空，请提供待处理的文本块")

        self.blocks = blocks
        self.result = ConversionResult()

        try:
            # 1. 清洗：移除页眉页脚
            cleaned_blocks = self._remove_headers_footers(blocks)
            if len(cleaned_blocks) < len(blocks):
                self.result.warnings.append(
                    f"已移除 {len(blocks) - len(cleaned_blocks)} 个疑似页眉/页脚块"
                )

            # 2. 合并孤立片段（短文本合并到相邻块）
            merged_blocks = self._merge_orphan_fragments(cleaned_blocks)
            if len(merged_blocks) < len(cleaned_blocks):
                self.result.warnings.append(
                    f"已合并 {len(cleaned_blocks) - len(merged_blocks)} 个孤立片段"
                )

            # 3. 智能标题检测
            marked_blocks = self._detect_headings(merged_blocks)

            # 4. 生成Markdown
            markdown_lines = self._generate_markdown(marked_blocks)

            self.result.markdown = "\n".join(markdown_lines)
            self.result.stats = {
                "total_blocks": len(blocks),
                "cleaned_blocks": len(cleaned_blocks),
                "merged_blocks": len(merged_blocks),
                "headings_detected": sum(1 for b in marked_blocks if b.is_bold),
                "lines": len(markdown_lines),
            }

            # 5. 计算置信度
            self.result.confidence = self._calculate_confidence()

        except PdfmdError:
            raise
        except Exception as e:
            raise PdfmdError("E009", f"内部处理错误: {str(e)}")

        return self.result

    # --------------------------------------------------------
    # 步骤1：移除页眉页脚
    # --------------------------------------------------------
    def _remove_headers_footers(self, blocks: List[TextBlock]) -> List[TextBlock]:
        """启发式检测并移除页眉页脚"""
        if len(blocks) < 3:
            return blocks

        result_blocks = []
        total_blocks = len(blocks)

        for i, block in enumerate(blocks):
            # 页眉：通常位于页面顶部且内容短
            if block.position.get("y", 999) < 50 and len(block.text) < 50:
                if self._looks_like_header_footer(block.text):
                    continue

            # 页脚：通常位于页面底部且内容短
            if block.position.get("y", 0) > 750 and len(block.text) < 50:
                if self._looks_like_header_footer(block.text):
                    continue

            result_blocks.append(block)

        return result_blocks

    def _looks_like_header_footer(self, text: str) -> bool:
        """判断文本是否像页眉页脚"""
        text_lower = text.lower()
        for keyword in self.HEADER_FOOTER_KEYWORDS:
            if keyword.lower() in text_lower:
                return True
        # 纯数字页码
        if re.match(r"^\d{1,3}$", text.strip()):
            return True
        # 短文本且包含特殊符号
        if len(text.strip()) < 5 and any(c in text for c in "|/-_·•"):
            return True
        return False

    # --------------------------------------------------------
    # 步骤2：合并孤立片段
    # --------------------------------------------------------
    def _merge_orphan_fragments(self, blocks: List[TextBlock]) -> List[TextBlock]:
        """将短文本片段合并到相邻块"""
        if len(blocks) < 2:
            return blocks

        result: List[TextBlock] = []
        i = 0

        while i < len(blocks):
            current = blocks[i]

            # 如果当前块很短，尝试合并到前一个块
            if (
                len(current.text.strip()) < 15
                and result
                and current.page_num == result[-1].page_num
            ):
                # 检查是否在同一行区域
                y_diff = abs(
                    current.position.get("y", 0) - result[-1].position.get("y", 0)
                )
                if y_diff < 10:  # 同一行
                    result[-1].text += current.text
                    result[-1].position["width"] = (
                        current.position.get("x", 0)
                        + current.position.get("width", 0)
                        - result[-1].position.get("x", 0)
                    )
                else:
                    result.append(current)
            else:
                result.append(current)
            i += 1

        return result

    # --------------------------------------------------------
    # 步骤3：智能标题检测
    # --------------------------------------------------------
    def _detect_headings(self, blocks: List[TextBlock]) -> List[TextBlock]:
        """根据字号和样式检测标题"""
        if not blocks:
            return blocks

        # 计算基准字号（取中位数）
        font_sizes = [b.font_size for b in blocks if b.font_size > 0]
        if not font_sizes:
            return blocks

        font_sizes.sort()
        median_size = font_sizes[len(font_sizes) // 2]
        base_size = median_size if median_size > 0 else 12.0

        for block in blocks:
            # 标题特征：字号较大或加粗
            if block.font_size > base_size * self.TITLE_SIZE_RATIO:
                block.is_bold = True  # 标记为标题
            elif block.font_size > base_size * self.SUBTITLE_SIZE_RATIO and block.is_bold:
                # 已经是加粗状态，保持
                pass
            elif block.is_bold and len(block.text.strip()) < 100:
                # 加粗且较短，视为小标题
                pass
            else:
                block.is_bold = False

        return blocks

    # --------------------------------------------------------
    # 步骤4：生成Markdown
    # --------------------------------------------------------
    def _generate_markdown(self, blocks: List[TextBlock]) -> List[str]:
        """将文本块转换为Markdown格式"""
        lines: List[str] = []
        in_code_block = False
        list_counter = 0

        for i, block in enumerate(blocks):
            text = block.text.strip()
            if not text:
                continue

            # 标题处理
            if block.is_bold:
                # 根据字号决定标题级别
                if block.font_size >= 20:
                    prefix = "# "
                elif block.font_size >= 16:
                    prefix = "## "
                elif block.font_size >= 14:
                    prefix = "### "
                else:
                    prefix = "#### "
                lines.append(f"{prefix}{text}")
                lines.append("")  # 空行分隔
                continue

            # 代码块检测
            if text.startswith("
