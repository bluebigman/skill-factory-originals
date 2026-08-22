#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pdf-to-markdown-gpt 技能实现脚本
================================
依据功能规格独立实现（clean-room），提供 PDF 转 Markdown 的核心处理逻辑。

功能概览:
  - 解析输入数据/文件/URL，提取关键信息
  - 按规格生成结构化 Markdown 输出
  - 置信度评估与标注
  - 批量处理支持
  - 内置离线自检（--selftest）

错误码:
  E001 - 输入为空
  E002 - 关键信息缺失
  E003 - 输入格式错误
  E004 - 超出能力边界
  E005 - 置信度过低
  E006 - 文件读取失败
  E007 - URL 解析失败
  E008 - 输出写入失败
  E009 - 内部逻辑错误
  E010 - 参数错误

仅使用 Python 标准库，无第三方依赖。
"""

import argparse
import json
import os
import re
import sys
import tempfile
import urllib.parse
import urllib.request
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# 模块级 dry-run 标志（保留但实际使用）
dry_run = False

# ============================================================
# 数据模型
# ============================================================

@dataclass
class InputContent:
    """标准化输入内容"""
    raw_text: str
    source_type: str  # 'text' | 'file' | 'url'
    source_name: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExtractedItem:
    """提取的关键信息条目"""
    key: str
    value: str
    confidence: float  # 0.0 - 1.0
    note: str = ""


@dataclass
class ProcessResult:
    """处理结果"""
    title: str
    items: List[ExtractedItem]
    markdown: str
    confidence: float
    warnings: List[str] = field(default_factory=list)


# ============================================================
# 核心处理逻辑
# ============================================================

class PDFToMarkdownConverter:
    """PDF 转 Markdown 核心转换器"""

    # 常见键名模式（用于识别关键信息）
    KEY_PATTERNS = {
        "标题": [r"标题[：:]\s*(.+)", r"^#\s*(.+)"],
        "作者": [r"作者[：:]\s*(.+)", r"著者[：:]\s*(.+)"],
        "日期": [r"日期[：:]\s*(\d{4}[-/]\d{1,2}[-/]\d{1,2})", r"时间[：:]\s*(.+)"],
        "摘要": [r"摘要[：:]\s*(.+)", r"概述[：:]\s*(.+)"],
        "关键词": [r"关键词[：:]\s*(.+)", r"关键字[：:]\s*(.+)"],
        "正文": [r"正文[：:]\s*(.+)", r"内容[：:]\s*(.+)"],
    }

    # 置信度阈值
    HIGH_CONFIDENCE = 0.90
    MEDIUM_CONFIDENCE = 0.85

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """初始化转换器"""
        self.config = config or {}
        self.warnings: List[str] = []

    # ---------- 主入口 ----------

    def process(self, input_content: InputContent) -> ProcessResult:
        """
        处理输入内容，生成 Markdown 输出

        Args:
            input_content: 标准化输入内容

        Returns:
            ProcessResult: 处理结果

        Raises:
            ValueError: 当输入无效时抛出，带错误码
        """
        # 重置警告
        self.warnings = []

        # 校验输入
        if not input_content or not input_content.raw_text:
            raise ValueError("E001: 请提供待处理的内容")

        # 解析内容
        items = self._extract_items(input_content.raw_text)

        # 检查关键信息
        if not items:
            raise ValueError("E002: 未从输入中识别到关键信息，请补充更详细的内容")

        # 生成 Markdown
        markdown = self._generate_markdown(input_content, items)

        # 计算整体置信度
        confidence = self._calculate_confidence(items)

        # 检查置信度
        if confidence < self.MEDIUM_CONFIDENCE:
            self.warnings.append("E005: 整体置信度较低，建议人工复核关键结果")

        # 构建标题
        title = self._extract_title(input_content, items)

        return ProcessResult(
            title=title,
            items=items,
            markdown=markdown,
            confidence=confidence,
            warnings=self.warnings
        )

    # ---------- 信息提取 ----------

    def _extract_items(self, text: str) -> List[ExtractedItem]:
        """从文本中提取关键信息"""
        items: List[ExtractedItem] = []
        lines = text.strip().split('\n')

        # 逐行扫描匹配键名模式
        for line in lines:
            line = line.strip()
            if not line:
                continue

            for key, patterns in self.KEY_PATTERNS.items():
                for pattern in patterns:
                    match = re.search(pattern, line)
                    if match:
                        value = match.group(1).strip()
                        if value:
                            # 计算单条置信度
                            conf = self._item_confidence(key, value)
                            items.append(ExtractedItem(
                                key=key,
                                value=value,
                                confidence=conf
                            ))
                            break
                else:
                    continue
                break

        # 去重（同一键名保留第一个）
        seen = set()
        unique_items = []
        for item in items:
            if item.key not in seen:
                seen.add(item.key)
                unique_items.append(item)

        return unique_items

    def _item_confidence(self, key: str, value: str) -> float:
        """评估单条信息的置信度"""
        # 基础置信度
        conf = 0.80

        # 根据值长度调整
        if len(value) >= 10:
            conf += 0.10
        elif len(value) >= 5:
            conf += 0.05

        # 根据键名调整
        if key in ("标题", "作者"):
            conf += 0.05

        # 根据内容特征调整
        if re.search(r'\d{4}', value):
            conf += 0.05  # 包含年份信息

        return min(conf, 0.98)

    def _calculate_confidence(self, items: List[ExtractedItem]) -> float:
        """计算整体置信度"""
        if not items:
            return 0.0

        # 加权平均
        weights = {
            "标题": 0.3,
            "作者": 0.2,
            "日期": 0.15,
            "摘要": 0.15,
            "关键词": 0.1,
            "正文": 0.1,
        }

        total_weight = 0.0
        weighted_sum = 0.0

        for item in items:
            w = weights.get(item.key, 0.1)
            total_weight += w
            weighted_sum += item.confidence * w

        if total_weight == 0:
            return sum(i.confidence for i in items) / len(items)

        return weighted_sum / total_weight

    # ---------- Markdown 生成 ----------

    def _generate_markdown(self, input_content: InputContent, items: List[ExtractedItem]) -> str:
        """生成 Markdown 格式输出"""
        md_lines = []

        # 标题
        title = self._extract_title(input_content, items)
        md_lines.append(f"# {title}")
        md_lines.append("")

        # 元信息
        md_lines.append(f"> 来源类型: {input_content.source_type}")
        md_lines.append(f"> 来源名称: {input_content.source_name}")
        md_lines.append(f"> 处理时间: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}")
        md_lines.append("")

        # 提取的信息
        md_lines.append("## 提取信息")
        md_lines.append("")

        for item in items:
            # 置信度标注
            if item.confidence >= self.HIGH_CONFIDENCE:
                marker = ""
            elif item.confidence >= self.MEDIUM_CONFIDENCE:
                marker = " *(建议复核)*"
            else:
                marker = " **[需核实]**"

            md_lines.append(f"### {item.key}{marker}")
            md_lines.append("")
            md_lines.append(item.value)
            md_lines.append("")

        # 置信度总结
        overall_conf = self._calculate_confidence(items)
        md_lines.append("---")
        md_lines.append("")
        md_lines.append(f"**整体置信度: {overall_conf:.0%}**")

        if overall_conf < self.MEDIUM_CONFIDENCE:
            md_lines.append("")
            md_lines.append("> ⚠️ 置信度较低，请人工复核关键结果。")

        return "\n".join(md_lines)

    def _extract_title(self, input_content: InputContent, items: List[ExtractedItem]) -> str:
        """提取文档标题"""
        # 优先使用提取到的标题
        for item in items:
            if item.key == "标题":
                return item.value

        # 其次使用来源名称
        if input_content.source_name:
            return Path(input_content.source_name).stem

        # 最后使用默认标题
        return "未命名文档"

    # ---------- 输入解析 ----------

    def parse_input(self, raw_input: str, source_type: str = "text") -> InputContent:
        """
        解析原始输入为标准化内容

        Args:
            raw_input: 原始输入（文本/文件路径/URL）
            source_type: 输入类型 ('text' | 'file' | 'url')

        Returns:
            InputContent: 标准化输入内容
        """
        if not raw_input or not raw_input.strip():
            raise ValueError("E001: 输入内容为空")

        raw_input = raw_input.strip()

        if source_type == "file":
            return self._parse_file(raw_input)
        elif source_type == "url":
            return self._parse_url(raw_input)
        elif source_type == "text":
            return InputContent(
                raw_text=raw_input,
                source_type="text",
                source_name="直接输入"
            )
        else:
            raise ValueError(f"E010: 不支持的输入类型: {source_type}")

    def _parse_file(self, file_path: str) -> InputContent:
        """解析文件输入"""
        try:
            path = Path(file_path)
            if not path.exists():
                raise ValueError(f"E006: 文件不存在: {file_path}")

            # 尝试读取为文本
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
            except UnicodeDecodeError:
                # 尝试二进制读取并提取文本
                with open(path, 'rb') as f:
                    binary_content = f.read()
                # 尝试解码为文本
                try:
                    content = binary_content.decode('utf-8', errors='replace')
                except:
                    # 如果是PDF文件，提取文本内容
                    if binary_content.startswith(b'%PDF'):
                        content = self._extract_pdf_text(binary_content)
                    else:
                        content = binary_content.decode('utf-8', errors='replace')

            return InputContent(
                raw_text=content,
                source_type="file",
                source_name=path.name
            )
        except ValueError:
            raise
        except Exception as e:
            raise ValueError(f"E006: 文件读取失败: {str(e)}")

    def _extract_pdf_text(self, pdf_binary: bytes) -> str:
        """
        从PDF二进制内容中提取文本（简化实现）
        实际生产环境应使用pdfplumber/PyMuPDF等库
        """
        try:
            # 简化实现：尝试提取PDF中的文本流
            text_parts = []
            # 查找文本流
            text_streams = re.findall(rb'stream\r?\n(.*?)\r?\nendstream', pdf_binary, re.DOTALL)
            for stream in text_streams:
                # 尝试解码
                try:
                    decoded = stream.decode('utf-8', errors='ignore')
                    # 过滤掉二进制内容
                    if decoded.isprintable() or '\n' in decoded:
                        text_parts.append(decoded)
                except:
                    continue
            
            if text_parts:
                return '\n'.join(text_parts)
            else:
                # 如果没有找到文本流，返回提示信息
                return "PDF文件包含二进制内容，无法直接提取文本。请使用文本格式输入。"
        except Exception as e:
            raise ValueError(f"E003: PDF解析失败: {str(e)}")

    def _parse_url(self, url: str) -> InputContent:
        """解析 URL 输入"""
        try:
            parsed = urllib.parse.urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                raise ValueError(f"E007: URL 格式无效: {url}")

            # 实际下载URL内容（带重试和超时）
            content = self._download_url(url)
            
            return InputContent(
                raw_text=content,
                source_type="url",
                source_name=url,
                metadata={"url": url, "domain": parsed.netloc}
            )
        except ValueError:
            raise
        except Exception as e:
            raise ValueError(f"E007: URL 解析失败: {str(e)}")

    def _download_url(self, url: str, max_retries: int = 3, timeout: int = 10) -> str:
        """
        下载URL内容，带重试退避和超时
        
        Args:
            url: URL地址
            max_retries: 最大重试次数
            timeout: 超时时间（秒）
            
        Returns:
            str: 下载的内容
        """
        for attempt in range(max_retries):
            try:
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, timeout=timeout) as response:
                    content = response.read().decode('utf-8', errors='replace')
                    return content
            except Exception as e:
                if attempt == max_retries - 1:
                    raise ValueError(f"E007: URL下载失败: {str(e)}")
                # 指数退避
                time.sleep(2 ** attempt)
        
        raise ValueError("E007: URL下载失败")

    # ---------- 批量处理 ----------

    def process_batch(self, inputs: List[Tuple[str, str]]) -> List[ProcessResult]:
        """
        批量处理多个输入

        Args:
            inputs: [(input_text, source_type), ...]

        Returns:
            List[ProcessResult]: 处理结果列表
        """
        results = []
        for input_text, source_type in inputs:
            try:
                content = self.parse_input(input_text, source_type)
                result = self.process(content)
                results.append(result)
            except ValueError as e:
                # 单条失败不影响其他
                self.warnings.append(f"批量处理跳过: {str(e)}")
                continue
        return results

    # ---------- 输出导出 ----------

    def export_markdown(self, result: ProcessResult, output_path: Optional[str] = None) -> str:
        """
        导出 Markdown 结果

        Args:
            result: 处理结果
            output_path: 输出文件路径（None 则返回字符串）

        Returns:
            str: Markdown 内容
        """
        if output_path:
            try:
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(result.markdown)
                return output_path
            except Exception as e:
                raise ValueError(f"E008: 输出写入失败: {str(e)}")
        return result.markdown

    def export_json(self, result: ProcessResult) -> str:
        """导出 JSON 格式结果"""
        data = {
            "title": result.title,
            "confidence": result.confidence,
            "warnings": result.warnings,
            "items": [
                {
                    "key": item.key,
                    "value": item.value,
                    "confidence": item.confidence,
                    "note": item.note
                }
                for item in result.items
            ]
        }
        return json.dumps(data, ensure_ascii=False, indent=2)


# ============================================================
# 自检模块
# ============================================================

class SelfTest:
    """内置自检逻辑（离线、无外部依赖）"""

    # 内置硬编码测试数据
    TEST_SAMPLES = [
        {
            "input": "标题：人工智能发展报告\n作者：张三\n日期：2024-03-15\n摘要：本报告分析了人工智能领域的最新进展和发展趋势。\n关键词：AI, 机器学习, 深度学习",
            "type": "text",
            "expected_keys": ["标题", "作者", "日期", "摘要", "关键词"],
            "min_confidence": 0.70
        },
        {
            "input": "# 量子计算研究综述\n\n著者：李四\n\n时间：2023-12-01\n概述：量子计算是当前计算机科学领域的前沿研究方向。",
            "type": "text",
            "expected_keys": ["标题", "作者", "日期", "摘要"],
            "min_confidence": 0.65
        },
        {
            "input": "这是一个没有明确结构的内容，只是随便写了一些文字，没有具体的键值对信息。",
            "type": "text",
            "expected_keys": [],
            "min_confidence": 0.0
        }
    ]

    @classmethod
    def run(cls) -> bool:
        """
        运行全部自检

        Returns:
            bool: 全部通过返回 True
        """
        print("=" * 60)
        print("开始自检 (SelfTest)")
        print("=" * 60)

        converter = PDFToMarkdownConverter()
        all_passed
