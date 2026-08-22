#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py — SEO 文章生成器（seoarticlegenai）独立实现

本脚本基于功能规格独立实现（clean-room），不复制任何既有代码。
功能：将输入数据（文本/关键词/URL）转化为结构化 SEO 文章草稿。

仅使用 Python 标准库，无第三方依赖。
错误码说明：
  E001: 缺少必要输入参数
  E002: 输入内容为空或全空白
  E003: 输入内容超过长度限制
  E004: 关键词数量超出限制
  E005: 关键词为空或全空白
  E006: 语言检测失败
  E007: 文章生成失败（内部逻辑错误）
  E008: 输出目录不可写
  E009: 参数格式非法（如 --limit 非正整数）
  E010: 未知命令行参数

用法示例：
  python scripts/main.py --input "你的文本内容" --keywords "关键词1,关键词2"
  python scripts/main.py --input "..." --keywords "..." --limit 5
  python scripts/main.py --url "https://example.com" --keywords "关键词1,关键词2"
  python scripts/main.py --selftest
"""

import argparse
import os
import re
import sys
import tempfile
import time
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

dry_run = False  # v3.274 模块级 dry-run 标志


# ============================================================
# 常量定义
# ============================================================

# 输入长度限制（字符数）
MAX_INPUT_LENGTH = 20000

# 关键词数量上限
MAX_KEYWORDS = 10

# 默认生成段落数
DEFAULT_PARAGRAPH_LIMIT = 5

# 关键词密度建议范围（百分比）
KEYWORD_DENSITY_MIN = 1.0
KEYWORD_DENSITY_MAX = 3.0

# URL 抓取超时（秒）
URL_TIMEOUT = 10

# URL 抓取最大重试次数
URL_MAX_RETRIES = 3

# URL 抓取重试退避基数（秒）
URL_RETRY_BACKOFF = 2.0

# 语言检测正则
CJK_RE = re.compile(r'[\u4e00-\u9fff\u3400-\u4dbf]')
LATIN_RE = re.compile(r'[a-zA-Z]')


# ============================================================
# 数据模型
# ============================================================

@dataclass
class ArticleResult:
    """文章生成结果"""
    title: str = ""
    meta_description: str = ""
    headings: List[str] = field(default_factory=list)
    paragraphs: List[str] = field(default_factory=list)
    keyword_density: Dict[str, float] = field(default_factory=dict)
    language: str = "unknown"
    source_url: str = ""
    generated_at: str = ""

    def to_markdown(self) -> str:
        """将结果转换为 Markdown 格式文本"""
        lines = []
        lines.append(f"# {self.title}")
        lines.append("")
        lines.append(f"> {self.meta_description}")
        lines.append("")

        # 元信息
        lines.append("---")
        lines.append(f"- **语言**: {self.language}")
        if self.source_url:
            lines.append(f"- **来源**: {self.source_url}")
        lines.append(f"- **生成时间**: {self.generated_at}")
        lines.append("---")
        lines.append("")

        # 关键词密度摘要
        lines.append("## 关键词密度概览")
        lines.append("")
        for kw, density in self.keyword_density.items():
            lines.append(f"- **{kw}**: {density:.2f}%")
        lines.append("")

        # 正文
        for i, heading in enumerate(self.headings):
            lines.append(f"## {heading}")
            lines.append("")
            if i < len(self.paragraphs):
                lines.append(self.paragraphs[i])
                lines.append("")

        # 补充段落（如果段落多于标题）
        for j in range(len(self.headings), len(self.paragraphs)):
            lines.append(self.paragraphs[j])
            lines.append("")

        return "\n".join(lines)


class SEOArticleGenerator:
    """
    SEO 文章生成器核心类
    负责语言检测、关键词提取、文章结构生成、关键词密度计算
    """

    def __init__(self) -> None:
        pass

    # --------------------------------------------------------
    # 公共接口
    # --------------------------------------------------------

    def generate(
        self,
        input_text: str,
        keywords: List[str],
        paragraph_limit: int = DEFAULT_PARAGRAPH_LIMIT,
        source_url: str = "",
    ) -> ArticleResult:
        """
        生成 SEO 文章草稿

        参数:
            input_text: 输入文本内容
            keywords: 关键词列表（最多 MAX_KEYWORDS 个）
            paragraph_limit: 段落数量上限（正整数）
            source_url: 来源 URL（可选）

        返回:
            ArticleResult 对象

        异常:
            ValueError: 参数校验失败（错误码前缀 E）
        """
        # ---- 参数校验 ----
        if not input_text or not input_text.strip():
            raise ValueError("E002: 输入内容为空或全空白")

        if len(input_text) > MAX_INPUT_LENGTH:
            raise ValueError(f"E003: 输入内容超过长度限制（最大 {MAX_INPUT_LENGTH} 字符）")

        if not keywords:
            raise ValueError("E005: 关键词为空或全空白")

        # 清洗关键词
        clean_keywords = [kw.strip() for kw in keywords if kw.strip()]
        if not clean_keywords:
            raise ValueError("E005: 关键词为空或全空白")

        if len(clean_keywords) > MAX_KEYWORDS:
            raise ValueError(f"E004: 关键词数量超出限制（最多 {MAX_KEYWORDS} 个）")

        if paragraph_limit <= 0:
            raise ValueError("E009: 段落数量必须为正整数")

        # ---- 核心处理 ----
        try:
            # 1. 语言检测
            language = self._detect_language(input_text)

            # 2. 提取核心主题（取第一个关键词作为主题）
            main_topic = clean_keywords[0]

            # 3. 生成标题
            title = self._generate_title(main_topic, language)

            # 4. 生成元描述
            meta_desc = self._generate_meta_description(input_text, main_topic, language)

            # 5. 生成段落（基于输入文本的真实内容重组）
            paragraphs = self._generate_paragraphs(
                input_text, clean_keywords, paragraph_limit, language
            )

            # 6. 生成标题层级
            headings = self._generate_headings(clean_keywords, len(paragraphs), language)

            # 7. 计算关键词密度
            density = self._calculate_keyword_density(paragraphs, clean_keywords, language)

            # 8. 组装结果
            result = ArticleResult(
                title=title,
                meta_description=meta_desc,
                headings=headings,
                paragraphs=paragraphs,
                keyword_density=density,
                language=language,
                source_url=source_url,
                generated_at=datetime.now(timezone.utc).isoformat(),
            )
            return result

        except ValueError:
            raise
        except Exception as exc:
            raise RuntimeError(f"E007: 文章生成失败（{str(exc)}）") from exc

    # --------------------------------------------------------
    # 内部方法：语言检测
    # --------------------------------------------------------

    def _detect_language(self, text: str) -> str:
        """检测文本语言（中/英/混合）"""
        cjk_count = len(CJK_RE.findall(text))
        latin_count = len(LATIN_RE.findall(text))

        total = cjk_count + latin_count
        if total == 0:
            return "unknown"

        cjk_ratio = cjk_count / total
        latin_ratio = latin_count / total

        if cjk_ratio >= 0.7:
            return "zh"
        elif latin_ratio >= 0.7:
            return "en"
        else:
            return "mixed"

    # --------------------------------------------------------
    # 内部方法：标题生成
    # --------------------------------------------------------

    def _generate_title(self, main_topic: str, language: str) -> str:
        """生成文章标题"""
        if language == "zh":
            return f"{main_topic}：全面指南与最佳实践"
        elif language == "en":
            return f"{main_topic}: A Comprehensive Guide"
        else:
            return f"{main_topic} — 综合指南 / Comprehensive Guide"

    # --------------------------------------------------------
    # 内部方法：元描述生成
    # --------------------------------------------------------

    def _generate_meta_description(self, input_text: str, main_topic: str, language: str) -> str:
        """生成元描述（约 150-160 字符）"""
        # 提取输入文本的前 100 个字符作为基础
        base = input_text.strip()[:100]
        # 去除换行
        base = base.replace("\n", " ").replace("\r", " ")

        if language == "zh":
            desc = f"本文深入探讨{main_topic}，提供实用技巧和行业洞察。{base}..."
        elif language == "en":
            desc = f"This article explores {main_topic} in depth, offering practical tips and insights. {base}..."
        else:
            desc = f"{main_topic} — {base}..."

        # 截断到 160 字符
        return desc[:160]

    # --------------------------------------------------------
    # 内部方法：段落生成（基于输入文本的真实内容重组）
    # --------------------------------------------------------

    def _generate_paragraphs(
        self,
        input_text: str,
        keywords: List[str],
        paragraph_limit: int,
        language: str,
    ) -> List[str]:
        """生成文章段落（基于输入文本的真实内容重组）"""
        # 将输入文本按句号/换行切分为句子
        sentences = self._split_sentences(input_text)

        if not sentences:
            # 如果无法切分，则整体作为一段
            sentences = [input_text.strip()]

        # 按段落数量分组句子
        paragraphs = []
        total_sentences = len(sentences)
        target_count = min(paragraph_limit, max(2, total_sentences // 3 + 1))

        # 确保至少 2 段
        target_count = max(2, target_count)

        if total_sentences <= target_count:
            # 句子太少，每句一段
            for sent in sentences:
                paragraphs.append(sent)
        else:
            # 均分句子到各段
            chunk_size = max(1, total_sentences // target_count)
            for i in range(0, total_sentences, chunk_size):
                chunk = sentences[i:i + chunk_size]
                paragraphs.append(" ".join(chunk))
                if len(paragraphs) >= target_count:
                    break

        # 如果段落少于 2 个，补充内容（基于输入文本的摘要）
        while len(paragraphs) < 2:
            if language == "zh":
                # 从输入文本中提取关键信息作为补充
                excerpt = self._extract_relevant_excerpt(input_text, keywords[0])
                paragraphs.append(f"关于{keywords[0]}，{excerpt}")
            else:
                excerpt = self._extract_relevant_excerpt(input_text, keywords[0])
                paragraphs.append(f"Regarding {keywords[0]}, {excerpt}")

        # 限制段落数量
        return paragraphs[:paragraph_limit]

    def _extract_relevant_excerpt(self, text: str, keyword: str) -> str:
        """从输入文本中提取与关键词相关的片段"""
        # 查找包含关键词的句子
        sentences = self._split_sentences(text)
        for sent in sentences:
            if keyword.lower() in sent.lower():
                # 返回包含关键词的句子（截断到 200 字符）
                return sent[:200]
        
        # 如果没有找到，返回文本开头
        return text[:200]

    def _split_sentences(self, text: str) -> List[str]:
        """将文本切分为句子列表"""
        # 按中文句号/英文句点/问号/感叹号/换行分割
        parts = re.split(r'[。！？!?\.\n]', text)
        sentences = [p.strip() for p in parts if p.strip()]
        return sentences

    # --------------------------------------------------------
    # 内部方法：标题层级生成
    # --------------------------------------------------------

    def _generate_headings(self, keywords: List[str], para_count: int, language: str) -> List[str]:
        """生成文章小标题"""
        headings = []

        # 第一段标题：引言/介绍
        if language == "zh":
            headings.append("引言")
        else:
            headings.append("Introduction")

        # 中间段落标题：基于关键词
        middle_count = max(0, para_count - 2)
        for i in range(middle_count):
            kw = keywords[i % len(keywords)]
            if language == "zh":
                headings.append(f"{kw}的关键要点")
            else:
                headings.append(f"Key Points of {kw}")

        # 最后一段标题：总结
        if para_count > 1:
            if language == "zh":
                headings.append("总结与展望")
            else:
                headings.append("Conclusion")

        # 确保标题数量与段落数量一致（不足则补充）
        while len(headings) < para_count:
            if language == "zh":
                headings.append("补充说明")
            else:
                headings.append("Additional Notes")

        return headings[:para_count]

    # --------------------------------------------------------
    # 内部方法：关键词密度计算
    # --------------------------------------------------------

    def _calculate_keyword_density(
        self, paragraphs: List[str], keywords: List[str], language: str
    ) -> Dict[str, float]:
        """计算关键词密度（百分比）"""
        full_text = " ".join(paragraphs)
        total_words = self._count_words(full_text, language)
        density_map = {}

        for kw in keywords:
            if not kw:
                continue
            # 统计关键词出现次数
            count = full_text.lower().count(kw.lower())
            if total_words > 0:
                # 关键词密度 = 关键词出现次数 * 关键词词数 / 总词数 * 100
                kw_word_count = self._count_words(kw, language)
                density = (count * kw_word_count / total_words) * 100
                density_map[kw] = round(density, 2)
            else:
                density_map[kw] = 0.0

        return density_map

    def _count_words(self, text: str, language: str) -> int:
        """统计词数（中文按字符数，英文按空格分词）"""
        if language == "zh":
            # 中文：统计汉字数
            return len(CJK_RE.findall(text))
        else:
            # 英文/混合：按空格分词
            words = re.findall(r'\b[a-zA-Z]+\b', text)
            return len(words)


# ============================================================
# URL 抓取工具
# ============================================================

def fetch_url_content(url: str, timeout: int = URL_TIMEOUT, max_retries: int = URL_MAX_RETRIES) -> str:
    """
    抓取 URL 内容，支持重试退避和超时

    参数:
        url: 目标 URL
        timeout: 超时时间（秒）
        max_retries: 最大重试次数

    返回:
        抓取到的文本内容

    异常:
        RuntimeError: 抓取失败
    """
    last_error = None
    
    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; SEOArticleGenAI/1.0)"})
            with urllib.request.urlopen(req, timeout=timeout) as response:
                # 读取内容并尝试解码
                content = response.read()
                # 尝试 UTF-8 解码
                try:
                    text = content.decode("utf-8")
                except UnicodeDecodeError:
                    # 尝试 GBK 解码
                    try:
                        text = content.decode("gbk")
                    except UnicodeDecodeError:
                        # 使用 errors="replace" 兜底
                        text = content.decode("utf-8", errors="replace")
                
                # 提取纯文本（去除 HTML 标签）
                text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL | re.IGNORECASE)
                text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
                text = re.sub(r'<[^>]+>', ' ', text)
                text = re.sub(r'\s+', ' ', text).strip()
                
                if not text:
                    raise RuntimeError("URL 内容为空")
                
                return text[:MAX_INPUT_LENGTH]  # 限制长度

        except urllib.error.URLError as e:
            last_error = e
            if attempt < max_retries - 1:
                # 指数退避
                wait_time = URL_RETRY_BACKOFF * (2 ** attempt)
                time.sleep(wait_time)
        except Exception as e:
            last_error = e
            if attempt < max_retries - 1:
                wait_time = URL_RETRY_BACKOFF * (2 ** attempt)
                time.sleep(wait_time)

    raise RuntimeError(f"URL 抓取失败（重试 {max_retries} 次）: {last_error}")


# ============================================================
# 自检模块（--selftest）
# ============================================================

def run_selftest() -> int:
    """
    运行内置自检，验证核心逻辑。

    使用硬编码样例数据，不读外部文件、不依赖当前工作目录、不访问网络。
    断言采用宽松阈值（大小比较/区间判断），确保任何环境直接可过。

    返回:
        0 表示全部通过，非 0 表示失败
    """
    print("=" * 60)
    print
