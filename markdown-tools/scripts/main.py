#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py - PDF转文档 / Markdown 工具集（独立实现）

本脚本依据功能规格独立设计，实现核心的 Markdown 处理能力：
  - 解析 Markdown 文本，提取标题、列表、链接、代码块等结构化信息
  - 将 Markdown 转换为简易 HTML
  - 统计文档结构（标题数、段落数、代码块数等）
  - 对不确定内容给出置信度评估
  - 提供 --selftest 离线自检模式（内置样例，不依赖外部输入）

错误码体系：
  E001 - 输入为空
  E002 - 关键信息缺失
  E003 - 输入格式错误
  E004 - 超出能力边界
  E005 - 置信度过低
  E006 - 文件读取失败
  E007 - 输出写入失败
  E008 - 命令行参数错误
  E009 - 内部逻辑错误
  E010 - 不支持的操作
"""

import sys
import os
import re
import json
import argparse
from typing import List, Dict, Any, Optional, Tuple


# ============================================================
# 一、核心数据模型与工具函数
# ============================================================

class MarkdownDocument:
    """Markdown 文档的解析结果对象"""
    
    def __init__(self):
        self.titles: List[Dict[str, Any]] = []      # 标题列表
        self.paragraphs: List[str] = []             # 段落列表
        self.links: List[Dict[str, str]] = []       # 链接列表
        self.code_blocks: List[str] = []            # 代码块列表
        self.lists: List[Dict[str, Any]] = []       # 列表结构
        self.raw_text: str = ""                     # 原始文本
        self.word_count: int = 0                    # 单词数
        self.confidence: float = 1.0                # 整体置信度
        
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（用于 JSON 输出）"""
        return {
            "titles": self.titles,
            "paragraphs": self.paragraphs,
            "links": self.links,
            "code_blocks": self.code_blocks,
            "lists": self.lists,
            "word_count": self.word_count,
            "confidence": self.confidence,
        }


def normalize_text(text: str) -> str:
    """规范化文本：去除多余空白，统一换行"""
    if not text:
        return ""
    # 统一换行符
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # 去除每行首尾空白
    lines = [line.strip() for line in text.split("\n")]
    # 去除空行（但保留段落之间的分隔）
    return "\n".join(lines)


def split_frontmatter(text: str) -> Tuple[Dict[str, str], str]:
    """分割 YAML frontmatter（如果存在）"""
    if not text.startswith("---"):
        return {}, text
    
    lines = text.split("\n")
    if len(lines) < 3:
        return {}, text
    
    # 查找第二个 ---
    end_idx = -1
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end_idx = i
            break
    
    if end_idx == -1:
        return {}, text
    
    # 解析 frontmatter（简单键值对）
    meta = {}
    for line in lines[1:end_idx]:
        if ":" in line:
            key, _, value = line.partition(":")
            meta[key.strip()] = value.strip()
    
    body = "\n".join(lines[end_idx+1:])
    return meta, body


# ============================================================
# 二、Markdown 解析器（核心逻辑）
# ============================================================

class MarkdownParser:
    """Markdown 解析器 - 提取结构化信息"""
    
    # 标题正则
    TITLE_RE = re.compile(r"^(#{1,6})\s+(.+)$")
    # 链接正则
    LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
    # 代码块开始/结束正则
    CODE_FENCE_RE = re.compile(r"^(`{3,}|~{3,})")
    # 列表项正则（有序/无序）
    UL_ITEM_RE = re.compile(r"^[-*+]\s+(.+)$")
    OL_ITEM_RE = re.compile(r"^\d+[.)]\s+(.+)$")
    # 行内代码正则
    INLINE_CODE_RE = re.compile(r"`([^`]+)`")
    # 粗体正则
    BOLD_RE = re.compile(r"\*\*([^*]+)\*\*")
    # 斜体正则
    ITALIC_RE = re.compile(r"\*([^*]+)\*")
    
    def parse(self, text: str) -> MarkdownDocument:
        """解析 Markdown 文本，返回结构化文档对象"""
        doc = MarkdownDocument()
        doc.raw_text = text
        
        # 规范化文本
        normalized = normalize_text(text)
        if not normalized:
            doc.confidence = 0.0
            return doc
        
        lines = normalized.split("\n")
        i = 0
        in_code_block = False
        code_block_start = -1
        code_fence_char = ""
        code_fence_len = 0
        current_list: Optional[Dict[str, Any]] = None
        
        while i < len(lines):
            line = lines[i]
            
            # 处理代码块
            fence_match = self.CODE_FENCE_RE.match(line)
            if fence_match:
                fence_char = fence_match.group(1)[0]
                fence_len = len(fence_match.group(1))
                
                if not in_code_block:
                    # 开始代码块
                    in_code_block = True
                    code_block_start = i
                    code_fence_char = fence_char
                    code_fence_len = fence_len
                    code_lines = []
                else:
                    # 检查是否匹配的结束围栏（至少相同长度）
                    if fence_char == code_fence_char and fence_len >= code_fence_len:
                        in_code_block = False
                        code_block = "\n".join(code_lines)
                        doc.code_blocks.append(code_block)
                        current_list = None
                i += 1
                continue
            
            if in_code_block:
                code_lines.append(line)
                i += 1
                continue
            
            # 处理标题
            title_match = self.TITLE_RE.match(line)
            if title_match:
                level = len(title_match.group(1))
                title_text = title_match.group(2).strip()
                doc.titles.append({
                    "level": level,
                    "text": title_text,
                })
                current_list = None
                i += 1
                continue
            
            # 处理列表项
            ul_match = self.UL_ITEM_RE.match(line)
            ol_match = self.OL_ITEM_RE.match(line)
            if ul_match or ol_match:
                if ul_match:
                    item_text = ul_match.group(1).strip()
                    list_type = "unordered"
                else:
                    item_text = ol_match.group(1).strip()
                    list_type = "ordered"
                
                # 提取列表项中的链接
                item_links = self._extract_links(item_text)
                doc.links.extend(item_links)
                
                if current_list is None or current_list["type"] != list_type:
                    # 新列表
                    current_list = {
                        "type": list_type,
                        "items": []
                    }
                    doc.lists.append(current_list)
                
                current_list["items"].append(item_text)
                i += 1
                continue
            
            # 非列表、非标题、非代码块 → 段落
            if line.strip():
                # 提取段落中的链接
                paragraph_links = self._extract_links(line)
                doc.links.extend(paragraph_links)
                
                # 清理行内标记
                clean_line = self._clean_inline_markup(line)
                doc.paragraphs.append(clean_line)
            else:
                current_list = None
            
            i += 1
        
        # 处理未闭合的代码块
        if in_code_block:
            code_block = "\n".join(code_lines)
            doc.code_blocks.append(code_block)
        
        # 计算单词数
        doc.word_count = len(normalized.split())
        
        # 计算置信度
        doc.confidence = self._calculate_confidence(doc)
        
        return doc
    
    def _extract_links(self, text: str) -> List[Dict[str, str]]:
        """从文本中提取链接"""
        links = []
        for match in self.LINK_RE.finditer(text):
            link_text = match.group(1)
            link_url = match.group(2)
            links.append({
                "text": link_text,
                "url": link_url
            })
        return links
    
    def _clean_inline_markup(self, text: str) -> str:
        """清理行内标记（粗体、斜体、代码等）"""
        # 移除行内代码
        text = self.INLINE_CODE_RE.sub(r"\1", text)
        # 移除粗体
        text = self.BOLD_RE.sub(r"\1", text)
        # 移除斜体
        text = self.ITALIC_RE.sub(r"\1", text)
        # 移除链接但保留文本
        text = self.LINK_RE.sub(r"\1", text)
        return text.strip()
    
    def _calculate_confidence(self, doc: MarkdownDocument) -> float:
        """计算解析结果的置信度"""
        confidence = 1.0
        
        # 空文档置信度为0
        if not doc.raw_text.strip():
            return 0.0
        
        # 没有提取到任何结构化信息时降低置信度
        if not doc.titles and not doc.paragraphs and not doc.code_blocks:
            confidence *= 0.5
        
        # 文本太短时降低置信度
        if doc.word_count < 10:
            confidence *= 0.7
        
        # 存在未闭合的代码块标记（以
