#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
humanizer-de — 德文文本去AI味改写器（独立实现）

本脚本根据功能规格独立实现，不参考任何既有代码。
仅使用 Python 标准库，无第三方依赖。

功能：
- 德文AI痕迹检测（基于规则模式扫描）
- 文本自然化改写（逐句处理）
- 多段文本批量处理（使用 '---' 分隔）
- 置信度标注（高/中/低）
- 内置自检模式（--selftest）

错误码：
E001 - 输入为空
E002 - 非德文文本（德文字符占比过低）
E003 - 文件读取失败
E004 - URL 访问失败
E005 - 无效参数
E006 - 输出写入失败
E007 - 内部处理异常
E008 - 自检失败
E009 - 不支持的输入类型
E010 - 未知错误
"""

import argparse
import json
import re
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone
from typing import Dict, List, Tuple, Optional


# ============================================================
# 常量定义
# ============================================================

# 德文特征字符
GERMAN_CHARS = set("äöüßÄÖÜ")

# 德文 AI 写作模式（完整模式列表）
AI_PATTERNS = [
    # 过度正式/模板化表达
    (r"\bes ist wichtig zu beachten\b", "Es sollte beachtet werden"),
    (r"\bes ist zu erwähnen\b", "Erwähnenswert ist"),
    (r"\bes sei darauf hingewiesen\b", "Hinweis:"),
    (r"\bim Folgenden\b", "nachfolgend"),
    (r"\bzusammenfassend lässt sich sagen\b", "Kurz gesagt"),
    (r"\bdes Weiteren\b", "Außerdem"),
    (r"\bdarüber hinaus\b", "Zudem"),
    (r"\baufgrund der Tatsache\b", "weil"),
    (r"\bin Bezug auf\b", "zu"),
    (r"\bmit Bezug auf\b", "zu"),
    # 机器翻译常见痕迹
    (r"\bum zu\b", "damit"),
    (r"\bwie bereits erwähnt\b", "wie gesagt"),
    (r"\bwie oben erwähnt\b", "wie erwähnt"),
    (r"\bwie folgt\b", "so"),
    (r"\bin der Lage sein\b", "können"),
    (r"\bdie Möglichkeit haben\b", "können"),
    (r"\bim Rahmen von\b", "bei"),
    (r"\bim Hinblick auf\b", "hinsichtlich"),
    (r"\bmit Hilfe von\b", "mittels"),
    (r"\bunter Berücksichtigung von\b", "angesichts"),
    # 过度书面化表达
    (r"\bsomit\b", "also"),
    (r"\bdaher\b", "deshalb"),
    (r"\bdementsprechend\b", "entsprechend"),
    (r"\bfolglich\b", "also"),
    (r"\binsofern\b", "insofern"),
    (r"\bgleichwohl\b", "trotzdem"),
    (r"\bnichtsdestotrotz\b", "trotzdem"),
    (r"\bzweifelsohne\b", "sicherlich"),
    (r"\bzweifellos\b", "sicher"),
    # 被动语态过度使用
    (r"\bwird durchgeführt\b", "führen wir durch"),
    (r"\bwird verwendet\b", "verwenden wir"),
    (r"\bwird benötigt\b", "brauchen wir"),
    (r"\bwird erwartet\b", "erwarten wir"),
    (r"\bwird betrachtet\b", "betrachten wir"),
    # 名词化过度
    (r"\bdie Durchführung\b", "das Durchführen"),
    (r"\bdie Verwendung\b", "das Verwenden"),
    (r"\bdie Erstellung\b", "das Erstellen"),
    (r"\bdie Bearbeitung\b", "das Bearbeiten"),
    (r"\bdie Berücksichtigung\b", "das Berücksichtigen"),
    # 连接词滥用
    (r"\bjedoch\b", "aber"),
    (r"\ballerdings\b", "aber"),
    (r"\bdennoch\b", "trotzdem"),
    (r"\bhingegen\b", "dagegen"),
    (r"\bwiederum\b", "andererseits"),
    # 其他常见AI痕迹
    (r"\bsehr geehrte\b", "Hallo"),
    (r"\bmit freundlichen Grüßen\b", "Viele Grüße"),
    (r"\bies ist klar\b", "klar"),
    (r"\bes ist offensichtlich\b", "offensichtlich"),
    (r"\bes ist ersichtlich\b", "ersichtlich"),
    (r"\bman kann sehen\b", "man sieht"),
    (r"\bman beachte\b", "beachten Sie"),
    (r"\bbitte beachten Sie\b", "beachten Sie"),
    (r"\bwir möchten\b", "wir wollen"),
    (r"\bwir würden\b", "wir würden"),
    (r"\bwürde gerne\b", "möchte"),
    (r"\bsollte beachtet werden\b", "sollte man beachten"),
    (r"\bmuss berücksichtigt werden\b", "muss man berücksichtigen"),
    (r"\bkann festgestellt werden\b", "kann man feststellen"),
    (r"\bwird angenommen\b", "nimmt man an"),
    (r"\bwird argumentiert\b", "argumentiert man"),
    (r"\bes gibt\b", "gibt es"),
    (r"\bhandelt sich um\b", "ist"),
    (r"\bbezüglich\b", "wegen"),
    (r"\bbzgl\.\b", "wegen"),
    (r"\bet al\.\b", "und andere"),
    (r"\betc\.\b", "usw."),
]

# 自然化改写规则（基于模式替换）
REWRITE_RULES: List[Tuple[str, str]] = [
    # 正式表达 → 自然表达
    (r"\bes ist wichtig zu beachten, dass\b", "wichtig ist, dass"),
    (r"\bes ist wichtig zu beachten\b", "wichtig ist"),
    (r"\bes ist zu erwähnen, dass\b", "erwähnenswert ist, dass"),
    (r"\bes ist zu erwähnen\b", "erwähnenswert"),
    (r"\bes sei darauf hingewiesen, dass\b", "hinweisen möchte ich auf"),
    (r"\bes sei darauf hingewiesen\b", "hinweisen möchte ich"),
    (r"\bim Folgenden\b", "nachfolgend"),
    (r"\bzusammenfassend lässt sich sagen, dass\b", "kurz gesagt"),
    (r"\bzusammenfassend lässt sich sagen\b", "kurz gesagt"),
    (r"\bdes Weiteren\b", "außerdem"),
    (r"\bdarüber hinaus\b", "zudem"),
    (r"\baufgrund der Tatsache, dass\b", "weil"),
    (r"\baufgrund der Tatsache\b", "weil"),
    (r"\bin Bezug auf\b", "zu"),
    (r"\bmit Bezug auf\b", "zu"),
    # 机器翻译痕迹
    (r"\bum zu\b", "damit"),
    (r"\bwie bereits erwähnt\b", "wie gesagt"),
    (r"\bwie oben erwähnt\b", "wie erwähnt"),
    (r"\bwie folgt\b", "so"),
    (r"\bin der Lage sein\b", "können"),
    (r"\bdie Möglichkeit haben\b", "können"),
    (r"\bim Rahmen von\b", "bei"),
    (r"\bim Hinblick auf\b", "hinsichtlich"),
    (r"\bmit Hilfe von\b", "mittels"),
    (r"\bunter Berücksichtigung von\b", "angesichts"),
    # 书面化 → 口语化
    (r"\bsomit\b", "also"),
    (r"\bdaher\b", "deshalb"),
    (r"\bdementsprechend\b", "entsprechend"),
    (r"\bfolglich\b", "also"),
    (r"\bgleichwohl\b", "trotzdem"),
    (r"\bnichtsdestotrotz\b", "trotzdem"),
    (r"\bzweifelsohne\b", "sicherlich"),
    (r"\bzweifellos\b", "sicher"),
    # 被动 → 主动
    (r"\bwird durchgeführt\b", "führen wir durch"),
    (r"\bwird verwendet\b", "verwenden wir"),
    (r"\bwird benötigt\b", "brauchen wir"),
    (r"\bwird erwartet\b", "erwarten wir"),
    (r"\bwird betrachtet\b", "betrachten wir"),
    # 名词化 → 动词化
    (r"\bdie Durchführung\b", "das Durchführen"),
    (r"\bdie Verwendung\b", "das Verwenden"),
    (r"\bdie Erstellung\b", "das Erstellen"),
    (r"\bdie Bearbeitung\b", "das Bearbeiten"),
    (r"\bdie Berücksichtigung\b", "das Berücksichtigen"),
    # 连接词简化
    (r"\bjedoch\b", "aber"),
    (r"\ballerdings\b", "aber"),
    (r"\bdennoch\b", "trotzdem"),
    (r"\bhingegen\b", "dagegen"),
    (r"\bwiederum\b", "andererseits"),
    # 其他
    (r"\bsehr geehrte\b", "hallo"),
    (r"\bmit freundlichen Grüßen\b", "viele Grüße"),
    (r"\bies ist klar\b", "klar"),
    (r"\bes ist offensichtlich\b", "offensichtlich"),
    (r"\bes ist ersichtlich\b", "ersichtlich"),
    (r"\bman kann sehen\b", "man sieht"),
    (r"\bman beachte\b", "beachten Sie"),
    (r"\bbitte beachten Sie\b", "beachten Sie"),
    (r"\bwir möchten\b", "wir wollen"),
    (r"\bwir würden\b", "wir würden"),
    (r"\bwürde gerne\b", "möchte"),
    (r"\bsollte beachtet werden\b", "sollte man beachten"),
    (r"\bmuss berücksichtigt werden\b", "muss man berücksichtigen"),
    (r"\bkann festgestellt werden\b", "kann man feststellen"),
    (r"\bwird angenommen\b", "nimmt man an"),
    (r"\bwird argumentiert\b", "argumentiert man"),
    (r"\bes gibt\b", "gibt es"),
    (r"\bhandelt sich um\b", "ist"),
    (r"\bbezüglich\b", "wegen"),
    (r"\bbzgl\.\b", "wegen"),
    (r"\bet al\.\b", "und andere"),
    (r"\betc\.\b", "usw."),
]


# ============================================================
# 核心功能类
# ============================================================

class HumanizerDE:
    """德文文本去AI味改写器主类"""

    def __init__(self):
        """初始化检测器和改写规则"""
        # 编译正则表达式（去重）
        seen_patterns = set()
        self.ai_patterns = []
        for pattern, replacement in AI_PATTERNS:
            if pattern not in seen_patterns:
                seen_patterns.add(pattern)
                self.ai_patterns.append((re.compile(pattern, re.IGNORECASE), replacement))
        
        seen_rewrites = set()
        self.rewrite_rules = []
        for pattern, replacement in REWRITE_RULES:
            if pattern not in seen_rewrites:
                seen_rewrites.add(pattern)
                self.rewrite_rules.append((re.compile(pattern, re.IGNORECASE), replacement))

    def is_german_text(self, text: str) -> bool:
        """
        检测文本是否以德文为主。
        德文字符（äöüßÄÖÜ）或常见德文词占比超过阈值则判定为德文。
        """
        if not text or len(text.strip()) == 0:
            return False

        # 移除标点和空白，但保留德文字符
        cleaned_text = re.sub(r'[^\w\säöüßÄÖÜ]', '', text)
        if len(cleaned_text.strip()) == 0:
            return False

        # 德文字符占比
        german_char_count = sum(1 for c in cleaned_text if c in GERMAN_CHARS)
        char_ratio = german_char_count / max(1, len(cleaned_text))

        # 常见德文单词检测
        common_words = ["der", "die", "das", "und", "ist", "nicht", "ein", "eine",
                        "mit", "auf", "für", "von", "den", "dem", "des", "sich",
                        "auch", "noch", "nach", "aus", "bei", "oder", "wenn"]
        
        # 分割单词（保留德文特殊字符）
        words = re.findall(r'\b[\wäöüßÄÖÜ]+\b', text.lower())
        if len(words) == 0:
            return False
            
        word_count = sum(1 for word in words if word in common_words)
        word_ratio = word_count / len(words)

        # 综合判断：德文字符占比 > 0.5% 或 常见词占比 > 15%
        return char_ratio > 0.005 or word_ratio > 0.15

    def detect_ai_patterns(self, text: str) -> List[Dict]:
        """
        检测文本中的AI写作模式。
        返回命中清单，每项包含模式、位置和替换建议。
        """
        hits = []
        for pattern, replacement in self.ai_patterns:
            for match in pattern.finditer(text):
                hits.append({
                    "pattern": match.group(0),
                    "position": match.start(),
                    "suggestion": replacement,
                    "confidence": self._estimate_confidence(match.group(0))
                })
        return hits

    def _estimate_confidence(self, matched_text: str) -> str:
        """根据匹配文本长度估算置信度"""
        length = len(matched_text)
        if length >= 15:
            return "高"
        elif length >= 8:
            return "中"
        else:
            return "低"

    def _check_german_syntax(self, text: str) -> bool:
        """
        简单的德语语法校验：检查动词位置。
        对于主句，动词应在第二位；对于从句，动词应在末尾。
        这里做宽松校验，只检查基本结构。
        """
        if not text or len(text.strip()) == 0:
            return False
        
        # 按句子分割
        sentences = re.split(r'[.!?]+', text)
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            
            # 跳过太短的句子
            words = sentence.split()
            if len(words) < 3:
                continue
            
            # 检查是否有动词（简单启发式：包含常见动词形式）
            common_verbs = ["ist", "sind", "war", "waren", "wird", "werden", "wurde",
                          "haben", "hat", "hatte", "können", "kann", "konnte",
                          "müssen", "muss", "musste", "sollen", "soll", "sollte",
                          "wollen", "will", "wollte", "dürfen", "darf", "durfte",
                          "gehen", "geht", "ging", "kommen", "kommt", "kam",
                          "machen", "macht", "machte", "sagen", "sagt", "sagte"]
            
            has_verb = any(word.lower() in common_verbs for word in words)
            if not has_verb:
                continue
            
            # 检查主句动词位置（第二位）
            # 跳过以连词开头的从句
            subjunctions = ["dass", "weil", "obwohl", "wenn", "als", "damit", "ob"]
            if words[0].lower() in subjunctions:
                # 从句：动词应在末尾
                if words[-1].lower() not in common_verbs:
                    return False
            else:
                # 主句：动词应在第二位（忽略可能的状语）
                if len(words) >= 2 and words[1].lower() not in common_verbs:
                    # 允许助动词在第二位的情况
                    if words[1].lower() not in ["haben", "sein", "werden", "können", "müssen", "sollen", "wollen", "dürfen", "mögen"]:
                        return False
        
        return True

    def rewrite_text(self, text: str) -> str:
        """
        对文本进行自然化改写。
        应用所有改写规则，返回改写后的文本。
        如果改写后语法校验失败，则保留原文。
        """
        result = text
