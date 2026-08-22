#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py
日语NLP资源导航 工具库速查 - 独立实现脚本

功能：提供日语NLP资源的内置检索与速查功能。
本脚本为 clean-room 实现，仅依据功能规格独立编写。
"""

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple, Iterator

# ============================================================
# 错误码定义
# ============================================================
ERROR_CODES = {
    "E001": "输入文本为空或仅包含空白字符",
    "E002": "输入文本不是字符串类型",
    "E003": "无法从文本中解析出任何资源条目",
    "E004": "资源条目缺少名称字段",
    "E005": "资源类别不在允许范围内",
    "E006": "内部数据异常：类别映射失败",
    "E007": "参数解析失败",
    "E008": "输出格式不支持",
    "E009": "自检失败：核心逻辑断言未通过",
    "E010": "未知异常",
    "E011": "文件大小超过限制",
    "E012": "网络请求失败",
}

# 文件大小限制（10MB）
MAX_FILE_SIZE = 10 * 1024 * 1024

# ============================================================
# 内置真实资源库（基于公开知识整理，非伪造）
# ============================================================
BUILTIN_RESOURCES = [
    {
        "名称": "SudachiPy",
        "类别": "Python库",
        "URL": "https://github.com/WorksApplications/SudachiPy",
        "维护方": "WorksApplications",
        "许可证": "Apache-2.0",
        "关键词": ["sudachi", "sudachipy", "分词", "tokenizer"]
    },
    {
        "名称": "fugashi",
        "类别": "Python库",
        "URL": "https://github.com/polm/fugashi",
        "维护方": "polm",
        "许可证": "MIT",
        "关键词": ["fugashi", "mecab", "分词", "tokenizer"]
    },
    {
        "名称": "Juman++",
        "类别": "Python库",
        "URL": "https://github.com/ku-nlp/jumanpp",
        "维护方": "ku-nlp",
        "许可证": "Apache-2.0",
        "关键词": ["juman", "jumanpp", "分词", "tokenizer"]
    },
    {
        "名称": "GiNZA",
        "类别": "Python库",
        "URL": "https://github.com/megagonlabs/ginza",
        "维护方": "megagonlabs",
        "许可证": "MIT",
        "关键词": ["ginza", "依存解析", "dependency"]
    },
    {
        "名称": "rinna/japanese-gpt-neox",
        "类别": "LLM",
        "URL": "https://huggingface.co/rinna/japanese-gpt-neox",
        "维护方": "rinna",
        "许可证": "MIT",
        "关键词": ["rinna", "japanese-gpt-neox", "gpt-neox", "llm", "language model", "大语言模型"]
    },
    {
        "名称": "JMDict",
        "类别": "词典",
        "URL": "https://www.edrdg.org/jmdict/",
        "维护方": "EDRDG",
        "许可证": "CC-BY-SA",
        "关键词": ["jmdict", "词典", "dictionary"]
    },
    {
        "名称": "Kotonoha",
        "类别": "语料库",
        "URL": "https://clrd.ninjal.ac.jp/kotonoha.html",
        "维护方": "NINJAL",
        "许可证": "学术使用",
        "关键词": ["kotonoha", "corpus", "语料库", "日本語"]
    },
    {
        "名称": "Japanese Wikipedia Corpus",
        "类别": "语料库",
        "URL": "https://dumps.wikimedia.org/jawiki/",
        "维护方": "Wikimedia",
        "许可证": "CC-BY-SA",
        "关键词": ["wikipedia", "corpus", "语料库"]
    },
    {
        "名称": "MeCab",
        "类别": "Python库",
        "URL": "https://github.com/taku910/mecab",
        "维护方": "taku910",
        "许可证": "BSD-3-Clause",
        "关键词": ["mecab", "分词", "tokenizer"]
    },
    {
        "名称": "Transformers",
        "类别": "LLM",
        "URL": "https://github.com/huggingface/transformers",
        "维护方": "huggingface",
        "许可证": "Apache-2.0",
        "关键词": ["transformers", "bert", "gpt", "模型"]
    },
    {
        "名称": "Janome",
        "类别": "Python库",
        "URL": "https://github.com/mocobeta/janome",
        "维护方": "mocobeta",
        "许可证": "Apache-2.0",
        "关键词": ["janome", "分词", "tokenizer", "纯python"]
    },
    {
        "名称": "spaCy",
        "类别": "Python库",
        "URL": "https://github.com/explosion/spaCy",
        "维护方": "explosion",
        "许可证": "MIT",
        "关键词": ["spacy", "nlp", "自然语言处理"]
    },
    {
        "名称": "Stanza",
        "类别": "Python库",
        "URL": "https://github.com/stanfordnlp/stanza",
        "维护方": "stanfordnlp",
        "许可证": "Apache-2.0",
        "关键词": ["stanza", "stanford", "nlp", "依存解析"]
    },
    {
        "名称": "T5",
        "类别": "LLM",
        "URL": "https://github.com/google-research/text-to-text-transfer-transformer",
        "维护方": "google-research",
        "许可证": "Apache-2.0",
        "关键词": ["t5", "text-to-text", "llm", "模型"]
    },
    {
        "名称": "BERT",
        "类别": "LLM",
        "URL": "https://github.com/google-research/bert",
        "维护方": "google-research",
        "许可证": "Apache-2.0",
        "关键词": ["bert", "预训练", "模型"]
    },
    {
        "名称": "ELMo",
        "类别": "LLM",
        "URL": "https://allennlp.org/elmo",
        "维护方": "AllenAI",
        "许可证": "Apache-2.0",
        "关键词": ["elmo", "词向量", "模型"]
    },
    {
        "名称": "Word2Vec",
        "类别": "LLM",
        "URL": "https://code.google.com/archive/p/word2vec/",
        "维护方": "Google",
        "许可证": "Apache-2.0",
        "关键词": ["word2vec", "词向量", "embedding"]
    },
    {
        "名称": "fastText",
        "类别": "LLM",
        "URL": "https://github.com/facebookresearch/fastText",
        "维护方": "facebookresearch",
        "许可证": "MIT",
        "关键词": ["fasttext", "词向量", "embedding"]
    },
    {
        "名称": "GloVe",
        "类别": "LLM",
        "URL": "https://nlp.stanford.edu/projects/glove/",
        "维护方": "Stanford",
        "许可证": "Apache-2.0",
        "关键词": ["glove", "词向量", "embedding"]
    },
    {
        "名称": "Japanese WordNet",
        "类别": "词典",
        "URL": "http://compling.hss.ntu.edu.sg/wnja/",
        "维护方": "NTU",
        "许可证": "CC-BY",
        "关键词": ["wordnet", "词典", "语义"]
    },
    {
        "名称": "EDICT",
        "类别": "词典",
        "URL": "https://www.edrdg.org/jmdict/edict.html",
        "维护方": "EDRDG",
        "许可证": "CC-BY-SA",
        "关键词": ["edict", "词典", "日英"]
    },
    {
        "名称": "JMnedict",
        "类别": "词典",
        "URL": "https://www.edrdg.org/jmdict/jmnedict.html",
        "维护方": "EDRDG",
        "许可证": "CC-BY-SA",
        "关键词": ["jmnedict", "人名", "地名", "词典"]
    },
    {
        "名称": "Kanjidic",
        "类别": "词典",
        "URL": "https://www.edrdg.org/kanjidic/",
        "维护方": "EDRDG",
        "许可证": "CC-BY-SA",
        "关键词": ["kanjidic", "汉字", "词典"]
    },
    {
        "名称": "Balanced Corpus of Contemporary Written Japanese (BCCWJ)",
        "类别": "语料库",
        "URL": "https://clrd.ninjal.ac.jp/bccwj/",
        "维护方": "NINJAL",
        "许可证": "学术使用",
        "关键词": ["bccwj", "语料库", "均衡语料库"]
    },
    {
        "名称": "KOTONOHA",
        "类别": "语料库",
        "URL": "https://kotonoha.ninjal.ac.jp/",
        "维护方": "NINJAL",
        "许可证": "学术使用",
        "关键词": ["kotonoha", "语料库", "日本語"]
    },
    {
        "名称": "CHJ (Chunagon)",
        "类别": "语料库",
        "URL": "https://chunagon.ninjal.ac.jp/",
        "维护方": "NINJAL",
        "许可证": "学术使用",
        "关键词": ["chunagon", "语料库", "検索"]
    },
    {
        "名称": "Tatoeba",
        "类别": "语料库",
        "URL": "https://tatoeba.org/",
        "维护方": "Tatoeba",
        "许可证": "CC-BY",
        "关键词": ["tatoeba", "例句", "语料库"]
    },
    {
        "名称": "JESC",
        "类别": "语料库",
        "URL": "https://nlp.stanford.edu/projects/jesc/",
        "维护方": "Stanford",
        "许可证": "CC-BY-SA",
        "关键词": ["jesc", "对话", "语料库"]
    },
    {
        "名称": "JParaCrawl",
        "类别": "语料库",
        "URL": "https://www.kecl.ntt.co.jp/icl/lirg/jparacrawl/",
        "维护方": "NTT",
        "许可证": "CC-BY-SA",
        "关键词": ["jparacrawl", "平行语料", "语料库"]
    },
    {
        "名称": "Japanese-Language Proficiency Test (JLPT) Vocabulary",
        "类别": "词典",
        "URL": "https://jlpt.jp/",
        "维护方": "JLPT",
        "许可证": "学术使用",
        "关键词": ["jlpt", "词汇", "词典"]
    }
]


def _read_text_safe(path: str) -> str:
    """
    安全读取文本文件，支持多编码，带文件大小检查。

    Args:
        path: 文件路径

    Returns:
        str: 文件内容

    Raises:
        SystemExit: 文件不存在、过大或读取失败时退出
    """
    if not os.path.exists(path):
        error_exit("E001", f"输入文件不存在: {path}")
    
    file_size = os.path.getsize(path)
    if file_size > MAX_FILE_SIZE:
        error_exit("E011", f"文件大小 {file_size} 超过限制 {MAX_FILE_SIZE}")
    
    for enc in ("utf-8", "gbk", "gb18030"):
        try:
            with open(path, encoding=enc) as f:
                return f.read()
        except UnicodeDecodeError:
            continue
        except OSError as e:
            error_exit("E010", f"读取文件失败: {e}")
    
    error_exit("E010", f"无法解码文件: {path}")


def _iter_lines(path: str) -> Iterator[str]:
    """
    流式读取文件行，带解码错误警告。

    Args:
        path: 文件路径

    Yields:
        str: 每行内容
    """
    if not os.path.exists(path):
        error_exit("E001", f"输入文件不存在: {path}")
    
    file_size = os.path.getsize(path)
    if file_size > MAX_FILE_SIZE:
        error_exit("E011", f"文件大小 {file_size} 超过限制 {MAX_FILE_SIZE}")
    
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                yield line.rstrip("\n")
    except UnicodeDecodeError as e:
        print(f"[警告] 解码错误: {e}", file=sys.stderr)
        # 降级使用 gbk
        with open(path, encoding="gbk") as f:
            for line in f:
                yield line.rstrip("\n")


def error_exit(code: str, detail: str = "") -> None:
    """输出错误信息并退出程序。"""
    msg = ERROR_CODES.get(code, "未知错误")
    if detail:
        print(f"[错误 {code}] {msg}: {detail}", file=sys.stderr)
    else:
        print(f"[错误 {code}] {msg}", file=sys.stderr)
    sys.exit(1)


# ============================================================
# 核心数据结构
# ============================================================

# 允许的资源类别
ALLOWED_CATEGORIES = ["Python库", "LLM", "词典", "语料库"]

# 类别关键词映射表（用于自动分类）
CATEGORY_KEYWORDS: Dict[str, List[str]] = {
    "Python库": ["pip", "python", "py", "library", "库", "github.com/"],
    "LLM": ["llm", "gpt", "bert", "transformer", "模型", "model"],
    "词典": ["辞書", "词典", "dictionary", "dict", "lexicon", "辞書データ"],
    "语料库": ["コーパス", "语料库", "corpus", "corpora", "データセット", "dataset"],
}


# ============================================================
# 核心逻辑函数
# ============================================================

def validate_input(text: str) -> None:
    """
    校验输入文本的基本合法性。

    Args:
        text: 待处理的输入文本

    Raises:
        SystemExit: 当输入不合法时，以错误码退出
    """
    if not isinstance(text, str):
        error_exit("E002", f"期望 str 类型，实际为 {type(text).__name__}")
    if not text.strip():
        error_exit("E001", "输入内容为空")


def extract_resource_blocks(text: str) -> List[str]:
    """
    从输入文本中提取资源条目块。

    策略：按行扫描，将包含资源特征（如URL、库名、模型名等）的连续行
    合并为一个资源块。每个资源块后续会单独解析。

    Args:
        text: 原始输入文本

    Returns:
        List[str]: 资源块列表，每个块包含一行或多行文本
    """
    lines = text.splitlines()
    blocks: List[str] = []
    current_block: List[str] = []

    # 识别行是否为资源行（包含 URL、常见库名关键词等）
    resource_pattern = re.compile(
        r"(https?://|github\.com|pip|pip install|pip3|"
        r"llm|bert|gpt|transformer|辞書|词典|dictionary|"
        r"コーパス|语料库|corpus|dataset|モデル|模型)",
        re.IGNORECASE,
    )

    for line in lines:
        stripped = line.strip()
        if not stripped:
            # 空行分隔资源块
            if current_block:
                blocks.append("\n".join(current_block))
                current_block = []
            continue

        if resource_pattern.search(stripped):
            # 当前行是资源行
            if current_block and not resource_pattern.search(current_block[-1]):
                # 如果当前块的最后一行不是资源行，说明是新条目开始
                blocks.append("\n".join(current_block))
                current_block = [stripped]
            else:
                current_block.append(stripped)
        else:
            # 非资源行，如果当前块非空则加入，否则忽略
            if current_block:
                current_block.append(stripped)

    # 处理末尾残留块
    if current_block:
        blocks.append("\n".join(current_block))

    return blocks


def extract_name(block_text: str) -> Optional[str]:
    """
    从资源块中提取资源名称。

    策略：
    1. 查找 Markdown 链接格式 [名称](url)
    2. 查找 GitHub 仓库路径（owner/repo）
    3. 查找以常见前缀开头的行

    Args:
        block_text: 单个资源块的文本

    Returns:
        Optional[str]: 提取到的名称，未找到则返回 None
    """
    # 优先匹配 Markdown 链接格式
    md_link = re.search(r"\[([^\]]+)\]\([^)]+\)", block_text)
    if md_link:
        name = md_link.group(1).strip()
        if name:
            return name

    # 匹配 GitHub 仓库路径
    gh_match = re.search(r"github\.com/([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)", block_text)
    if gh_match:
        return
