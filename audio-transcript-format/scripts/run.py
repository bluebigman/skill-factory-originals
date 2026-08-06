#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Skill: audio-transcript-format (v2.2.0)
将口语化音频转录文本整理为结构化书面语。

v2.2 升级（响应第三方评审，v3.150 工厂标准）：
  [架构] 真·阶段注册表：@stage("name") 装饰器注册，主流程自动遍历 STAGES，
         新增处理阶段零改动主流程（兑现 v2.1 的"可插拔"承诺）
  [清理] 移除死代码 load_spec/match_trigger；版本号收敛为 __version__ 常量
  [算法] 句尾语气词"呢/吧/吗"一律保留（修复"可以吧→可以""你说呢→你说"误删）
  [算法] 分句保护扩展：中文引号“”‘’、英文圆括号()、方括号[]、【】
  [算法] 段落分割：无关键词句（纯单字/符号）沿用当前段，防碎片化
  [算法] 列表化保守化：仅"标点后连续枚举标记"才转列表，防叙事误伤；
         行内编号(1. 2. 3.)列表识别修复（原实现对单段文本失效）
  [健壮] CLI 全局异常处理：文件不存在/编码错误 → 友好提示 + 错误码 10/11
  [可调] 输入长度上限可配置（--max-len，默认 10000）

接口完全兼容 v2.1：--input/--output/--format/--terms/--headings/--selftest
"""

import re
import sys
import json
import argparse
import os
import tempfile
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

__version__ = "2.2.0"

# 输入长度上限（可经 --max-len 覆盖）
MAX_INPUT_CHARS = 10000

# ── 阶段注册表（真·可插拔）────────────────────────────────────────────
# 每个阶段 = (名称, 处理函数)。handler 统一签名 handler(payload, ctx) -> Any：
#   payload 为上一阶段输出（str 或 List[str]），ctx 为共享上下文
#   （terms/add_headings 等运行时参数 + 阶段间传递的报告）。
# 新增处理阶段只需用 @stage("name") 注册新函数，主流程自动按定义顺序遍历执行。
STAGES: List[Tuple[str, Callable[[Any, Dict[str, Any]], Any]]] = []


def stage(name: str) -> Callable:
    """阶段注册装饰器：将处理函数登记到 STAGES（按定义顺序执行）"""
    def deco(fn: Callable) -> Callable:
        STAGES.append((name, fn))
        return fn
    return deco


def split_sentences(text: str) -> List[str]:
    """健壮分句：保护缩写词、引号、括号内容，按中文句末标点分割"""
    # 保护常见缩写（如 Dr.、Mr.、e.g. 中的点号）
    abbreviations = [
        r'\b(?:Dr|Mr|Mrs|Ms|Prof|St|e\.g|i\.e|etc|vs)\.',
        r'\b[A-Z]\.',  # 单字母缩写
    ]
    placeholders = []
    for i, abbr in enumerate(abbreviations):
        pattern = re.compile(abbr)
        text = pattern.sub(lambda m, i=i: _placeholder(i, placeholders, m.group(0)), text)

    # 保护引号内容（中文引号“”‘’ + 英文双/单引号，避免引号内的句号导致错误分句）
    _qcount = [0]
    def protect_quotes(match):
        placeholder = f"__QUOTE{_qcount[0]}__"
        _qcount[0] += 1
        placeholders.append((placeholder, match.group(0)))
        return placeholder

    # 保护括号内容（中文全角（）+ 英文圆括号 + 方括号 + 书名号【】）
    _pcount = [0]
    def protect_parens(match):
        placeholder = f"__PAREN{_pcount[0]}__"
        _pcount[0] += 1
        placeholders.append((placeholder, match.group(0)))
        return placeholder

    quote_pattern = re.compile(r'“[^”]*”|‘[^’]*’|"[^"]*"|\'[^\']*\'')
    paren_pattern = re.compile(r'（[^）]*）|\([^)]*\)|\[[^\]]*\]|【[^】]*】')
    text = quote_pattern.sub(protect_quotes, text)
    text = paren_pattern.sub(protect_parens, text)

    # 按中文句末标点分割（不分割缩写点号）
    sentences = re.split(r'(?<=[。！？])(?![。！？])', text)

    # 恢复被保护的片段
    result = []
    for sentence in sentences:
        for placeholder, original in placeholders:
            sentence = sentence.replace(placeholder, original)
        result.append(sentence)
    return result


def _placeholder(i: int, store: list, original: str = "") -> str:
    """为缩写生成占位符并记录原文（恢复时替换回去）"""
    p = f"__AB{i}__"
    store.append((p, original or p))
    return p


# ══════════════════════ 阶段 1：填充词清理（上下文感知）══════════════════════

# 纯口头填充词（删除；"那个/这个"句首指代场景由 _is_demonstrative_reference 保护）
FILLERS = ["嗯嗯", "啊啊", "然后呢", "就是呢", "那个那个", "这个这个",
           "然后", "就是", "那个", "这个", "嗯", "啊", "呃", "哦", "呀"]
FILLERS.sort(key=len, reverse=True)

# 指代保留：句首"那个/这个"后直接跟名词性成分（无标点）→ 是指代，保留
DEMONSTRATIVES = ["那个", "这个"]

# 连接词边界：出现这些词 → 大概率新主题段（段落分割线索）
TOPIC_TRANSITIONS = ["但是", "不过", "然而", "另一方面", "接下来", "另外",
                     "此外", "还有", "首先", "其次", "最后", "所以", "因此",
                     "总的来说", "总而言之", "回到", "顺便"]

# 注意：句尾语气词"呢/吧/吗"一律保留 —— v2.2 起不再做句尾删除。
# 理由（第三方评审实锤）："可以吧"→"可以"、"你说呢"→"你说" 等启发式误删
# 会丢失疑问语气、改变语义；这些词是疑问/语气的实词成分，删除收益极小、风险大。


def _is_demonstrative_reference(sentence: str, filler: str) -> bool:
    """句首'那个/这个'是指代用法（后接名词短语）→ 保留"""
    if filler not in DEMONSTRATIVES:
        return False
    rest = sentence[len(filler):].lstrip()
    if not rest:
        return False
    # 后接逗号/停顿 → 填充用法（"那个，我们走"）→ 可删
    if rest[0] in "，,、。.!！?？ ":
        return False
    # 后直接接汉字名词成分 → 指代（"那个项目""这个方案"）→ 保留
    if re.match(r'^[\u4e00-\u9fff]', rest):
        return True
    # 后接数字/量词（"那个三号""这个 3 号"）→ 指代，保留
    if re.match(r'^[\d０-９一二三四五六七八九十]+', rest):
        return True
    return False


@stage("filler_clean")
def clean_fillers(payload: str, ctx: Dict[str, Any]) -> str:
    """删除口语填充词。报告写入 ctx["filler_report"]，返回清洗后文本。

    上下文感知规则：
      - 句首/中间的纯填充词删除（词边界保护，实词绝不入列）
      - 句首"那个/这个"后接名词短语 = 指代 → 保留
      - 句尾语气词"呢/吧/吗"一律保留（v2.2 修复误删）
    """
    report = {"removed_chars": 0, "removed_words": {}, "removed_sentences": 0}
    text = payload
    sentences = split_sentences(text)
    cleaned_sentences = []

    for sentence in sentences:
        if not sentence:
            continue
        removed_in_sentence = 0

        def _record(filler: str):
            nonlocal removed_in_sentence
            removed_in_sentence += len(filler)
            report["removed_words"][filler] = report["removed_words"].get(filler, 0) + 1

        # 句首填充词（上下文感知：指代保留）
        for filler in FILLERS:
            if sentence.startswith(filler):
                if _is_demonstrative_reference(sentence, filler):
                    break  # 指代用法，保留
                sentence = sentence[len(filler):].lstrip()
                _record(filler)
                break
        # 句中填充词（词边界正则保护，绝不删实词子串）
        for filler in FILLERS:
            pattern = (r'(?<![a-zA-Z0-9\u4e00-\u9fff])' + re.escape(filler)
                       + r'(?![a-zA-Z0-9\u4e00-\u9fff])')
            new_s, n = re.subn(pattern, '', sentence)
            if n:
                _record(filler)
                sentence = new_s
        # 多余空格清理
        sentence = re.sub(r'\s+', ' ', sentence).strip()
        if sentence:
            cleaned_sentences.append(sentence)
        else:
            report["removed_sentences"] += 1

    report["removed_chars"] = sum(
        len(w) * c for w, c in report["removed_words"].items())
    ctx["filler_report"] = report
    return ''.join(cleaned_sentences)


# ══════════════════════ 阶段 2：标点修复 ══════════════════════

@stage("punct_fix")
def fix_punctuation(payload: str, ctx: Dict[str, Any]) -> str:
    """合并重复标点、修正粘连、英文/数字前补空格（中文排版不加空格）"""
    text = payload
    text = re.sub(r'([。！？；，])\1+', r'\1', text)
    text = re.sub(r'\s+([。！？；，])', r'\1', text)
    # 中文标点后只在英文/数字前补空格（中文后不补，保持中文排版）
    text = re.sub(r'([。！？；，])(?=[a-zA-Z0-9])', r'\1 ', text)
    return text.strip()


# ══════════════════════ 阶段 3：术语规范化 ══════════════════════

@stage("term_norm")
def normalize_terms(payload: str, ctx: Dict[str, Any]) -> str:
    """术语统一（旧词→新词，大小写不敏感）"""
    text = payload
    for old, new in (ctx.get("terms") or {}).items():
        text = re.sub(re.escape(old), new, text, flags=re.IGNORECASE)
    return text


# ══════════════════════ 阶段 4：段落分割（滑动窗口主题漂移）══════════════════════

def extract_keywords(sentence: str) -> List[str]:
    """提取句子关键词（中文长串按 2-gram 近似拆分，英文按 ≥3 字母词）。

    无分词器依赖的代价是：整串连续汉字会被当作一个"词"，
    导致相邻句几乎无重叠、滑动窗口主题漂移退化为假实现。
    因此对 >4 字中文串按滑动二元组拆分，保证局部词重叠信号存在。
    """
    words: List[str] = []
    for run in re.findall(r'[\u4e00-\u9fff]{2,}|[a-zA-Z]{3,}', sentence):
        if run[0] >= '\u4e00' and len(run) > 4:
            words.extend(run[i:i + 2] for i in range(len(run) - 1))
        else:
            words.append(run)
    return [w.lower() for w in words[:8]]


def _jaccard(a: List[str], b: List[str]) -> float:
    """两关键词集合的 Jaccard 相似度"""
    sa, sb = set(a), set(b)
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


@stage("paragraph_split")
def split_paragraphs(payload: str, ctx: Dict[str, Any]) -> List[str]:
    """段落分割：滑动窗口主题漂移 + 连接词边界（v2.1 升级，v2.2 防碎片）。

    原实现用"单句关键词 vs 当前主题集合取交集"，主题一换就碎；
    v2.1 维护最近 3 句滑动窗口主题，结合连接词线索判断边界；
    v2.2 对无关键词句（纯单字/符号）不再强制分段，沿用当前段防碎片化。
    """
    text = payload
    if not text:
        return []
    sentences = split_sentences(text)
    sentences = [s.strip() for s in sentences if s.strip()]
    if len(sentences) <= 2:  # 2 句及以下不分割（3 句起才走滑动窗口逻辑）
        return [text]

    WINDOW = 3  # 滑动窗口句数
    paragraphs = []
    current_para = []
    window_keywords: List[List[str]] = []  # 最近 WINDOW 句的关键词

    def _flush():
        nonlocal current_para, window_keywords
        if current_para:
            paragraphs.append(''.join(current_para))
        current_para, window_keywords = [], []

    for sentence in sentences:
        kw = extract_keywords(sentence)
        is_transition = any(t in sentence for t in TOPIC_TRANSITIONS)

        # 无关键词（纯单字中文/纯符号句）：弱信号 → 沿用当前段，防碎片化
        if not kw and current_para:
            current_para.append(sentence)
            continue

        if not current_para:
            current_para.append(sentence)
            window_keywords.append(kw)
            continue

        # 连接词线索 → 硬边界（新主题；段首即触发，防止"但是/另外"被吞）
        if is_transition and len(current_para) >= 1:
            _flush()
            current_para.append(sentence)
            window_keywords.append(kw)
            continue

        # 滑动窗口：与最近窗口任意句的主题重叠 → 同段
        # （阈值 0.1 适配 2-gram 信号：重叠 1 个二元组即 ≈0.1+，主题漂移仍敏感）
        overlap = max((_jaccard(kw, wk) for wk in window_keywords), default=0.0)
        if overlap >= 0.1:
            current_para.append(sentence)
            window_keywords.append(kw)
            window_keywords = window_keywords[-WINDOW:]
        elif len(current_para) >= 2:
            # 主题漂移且当前段已 ≥2 句 → 开新段（窗口记忆随 _flush 清空）
            _flush()
            current_para.append(sentence)
            window_keywords.append(kw)
        else:
            # 当前段仅 1 句且无重叠：再观察一句，防单句碎段
            current_para.append(sentence)
            window_keywords.append(kw)
            window_keywords = window_keywords[-WINDOW:]

    _flush()
    return paragraphs if paragraphs else [text]


# ══════════════════════ 阶段 5：列表化 ══════════════════════

# 枚举标记：位于句首或标点后（枚举语境），如 "首先…，其次…，最后…"
SEQ_MARKERS = ["第一", "第二", "第三", "第四", "第五", "首先", "其次", "再次", "最后"]
_SEQ_CONTEXT = re.compile(r'(?:^|[，,。！？；;])\s*(' + '|'.join(SEQ_MARKERS) + r')')


@stage("listify")
def convert_to_lists(payload: List[str], ctx: Dict[str, Any]) -> List[str]:
    """识别并列项转为列表（"第一/第二…"、"首先/其次…"或行内编号 1. 2. 3.）。

    v2.2 保守化：仅当≥2 个枚举标记出现在句首/标点后（真枚举语境）才转换，
    防叙事误伤（如"这是第一点。第二点更重要"保持原文）。
    """
    result = []
    for para in payload:
        # 顺序词枚举（第一/第二/首先/其次…）→ 列表
        markers = _SEQ_CONTEXT.findall(para)
        if len(markers) >= 2:
            items = re.split(r'(?:^|[，,。！？；;])\s*(?=' + '|'.join(SEQ_MARKERS) + r')', para)
            items = [item.strip() for item in items if item.strip()]
            if len(items) >= 2:
                result.append('\n'.join(f"{idx}. {item}" for idx, item in enumerate(items, 1)))
                continue
        # 行内编号枚举（1. xxx 2. yyy …
