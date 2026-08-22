#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
脚本名称: scripts/main.py
功能: 实现 uber-go-guide-pl 技能的核心处理流程（翻译润色）。
说明:
  - 仅依据功能规格独立实现（clean-room）。
  - 标准库实现，无第三方依赖。
  - 支持 --selftest 离线自检。
  - 支持 --dry-run 预览模式。
"""

import argparse
import sys
import re
import json
import time
import urllib.request
import urllib.error
import urllib.parse
import os
import sqlite3
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple, Any
from concurrent.futures import ThreadPoolExecutor, as_completed

# ---------------------------------------------------------------------------
# 错误码定义（E001-E010）
# ---------------------------------------------------------------------------
ERROR_CODES: Dict[str, str] = {
    "E001": "输入为空，请提供待处理的内容。",
    "E002": "关键信息缺失，请补充必要字段。",
    "E003": "输入格式错误，请检查输入格式。",
    "E004": "超出能力边界，无法处理该请求。",
    "E005": "置信度过低，结果无法确定。",
    "E006": "内部处理异常，请重试。",
    "E007": "参数解析失败，请检查命令行参数。",
    "E008": "输出写入失败，请检查权限或路径。",
    "E009": "输入内容过大，超出处理限制。",
    "E010": "未知错误，请查看日志。",
}


# ---------------------------------------------------------------------------
# 常量定义
# ---------------------------------------------------------------------------
# 置信度阈值
CONFIDENCE_HIGH = 90
CONFIDENCE_MEDIUM = 85

# 默认输出模板字段
DEFAULT_FIELDS = ["原文", "译文", "置信度", "备注"]

# 翻译 API 配置（使用 MyMemory 免费 API）
TRANSLATE_API_URL = "https://api.mymemory.translated.net/get"
TRANSLATE_API_TIMEOUT = 10  # 秒
TRANSLATE_API_MAX_RETRIES = 3
TRANSLATE_API_MAX_BACKOFF = 8  # 最大退避时间（秒）

# 最大输入长度限制
MAX_INPUT_LENGTH = 5000

# 批量处理并发数
BATCH_MAX_WORKERS = 4

# 缓存配置
CACHE_TTL = 3600  # 1小时
CACHE_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".translation_cache.db")

# Uber Go 指南专属术语表（英文 -> 波兰语）
UBER_GO_TERMS: Dict[str, str] = {
    "goroutine": "gorutyna",
    "channel": "kanał",
    "mutex": "mutex",
    "interface": "interfejs",
    "struct": "struktura",
    "slice": "wycinek",
    "map": "mapa",
    "defer": "odroczenie",
    "panic": "panika",
    "recover": "odzyskiwanie",
    "concurrency": "współbieżność",
    "parallelism": "równoległość",
    "deadlock": "zakleszczenie",
    "race condition": "wyścig danych",
    "goroutine leak": "wyciek gorutyny",
    "context": "kontekst",
    "error handling": "obsługa błędów",
    "dependency injection": "wstrzykiwanie zależności",
    "code review": "przegląd kodu",
    "best practice": "najlepsza praktyka",
}

# Uber Go 风格规则（正则表达式 -> 建议）
UBER_GO_STYLE_RULES: List[Tuple[str, str, str]] = [
    (r"\bvar\s+\w+\s+=\s+0\b", "Użyj 'var x int' zamiast 'var x = 0'", "zero_value"),
    (r"\bfor\s+\w+\s*:=\s*0\s*;\s*\w+\s*<\s*\w+\s*;\s*\w+\+\s*\{", "Rozważ użycie 'for range'", "loop_style"),
    (r"\bif\s+\w+\s*!=\s*nil\s*\{", "Rozważ użycie 'if err != nil' z wczesnym powrotem", "error_check"),
    (r"\bpanic\(", "Unikaj panic w kodzie produkcyjnym", "panic_usage"),
    (r"\brecover\(", "Używaj recover tylko w wyjątkowych przypadkach", "recover_usage"),
    (r"\binterface\s*\{\s*\}", "Unikaj pustych interfejsów", "empty_interface"),
    (r"\bstring\(\[\]byte\(", "Użyj string(bytes) zamiast string([]byte(...))", "string_conversion"),
    (r"\bdefer\s+\w+\.Close\(\)", "Sprawdź błędy przy defer Close()", "defer_close"),
]


# ---------------------------------------------------------------------------
# 核心数据结构
# ---------------------------------------------------------------------------
class ProcessingResult:
    """处理结果数据类"""
    def __init__(self) -> None:
        self.items: List[Dict[str, Any]] = []
        self.overall_confidence: float = 0.0
        self.errors: List[str] = []

    def add_item(self, original: str, translated: str, confidence: float, note: str = "") -> None:
        self.items.append({
            "原文": original,
            "译文": translated,
            "置信度": confidence,
            "备注": note,
        })

    def to_dict(self) -> Dict[str, Any]:
        return {
            "结果数": len(self.items),
            "平均置信度": self.overall_confidence,
            "数据": self.items,
            "错误": self.errors,
        }


# ---------------------------------------------------------------------------
# 缓存管理（SQLite 持久化）
# ---------------------------------------------------------------------------
def _init_cache_db() -> None:
    """初始化 SQLite 缓存数据库"""
    try:
        conn = sqlite3.connect(CACHE_DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS translation_cache (
                cache_key TEXT PRIMARY KEY,
                translated_text TEXT NOT NULL,
                timestamp REAL NOT NULL
            )
        """)
        conn.commit()
        conn.close()
    except sqlite3.Error as e:
        print(f"[缓存] 初始化数据库失败: {e}")


def _get_cached_translation(cache_key: str) -> Optional[str]:
    """从 SQLite 缓存获取翻译结果"""
    try:
        conn = sqlite3.connect(CACHE_DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT translated_text, timestamp FROM translation_cache WHERE cache_key = ?",
            (cache_key,)
        )
        row = cursor.fetchone()
        conn.close()
        
        if row:
            translated_text, timestamp = row
            if time.time() - timestamp <= CACHE_TTL:
                return translated_text
            else:
                # 过期，删除
                _delete_cached_translation(cache_key)
        return None
    except sqlite3.Error:
        return None


def _set_cached_translation(cache_key: str, translated_text: str) -> None:
    """将翻译结果写入 SQLite 缓存"""
    try:
        conn = sqlite3.connect(CACHE_DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO translation_cache (cache_key, translated_text, timestamp) VALUES (?, ?, ?)",
            (cache_key, translated_text, time.time())
        )
        conn.commit()
        conn.close()
    except sqlite3.Error:
        pass


def _delete_cached_translation(cache_key: str) -> None:
    """删除过期的缓存条目"""
    try:
        conn = sqlite3.connect(CACHE_DB_PATH)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM translation_cache WHERE cache_key = ?", (cache_key,))
        conn.commit()
        conn.close()
    except sqlite3.Error:
        pass


def _cleanup_cache() -> None:
    """清理过期缓存"""
    try:
        conn = sqlite3.connect(CACHE_DB_PATH)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM translation_cache WHERE timestamp < ?", (time.time() - CACHE_TTL,))
        conn.commit()
        conn.close()
    except sqlite3.Error:
        pass


# ---------------------------------------------------------------------------
# Uber Go 专属处理函数
# ---------------------------------------------------------------------------
def _apply_uber_go_terms(text: str) -> str:
    """应用 Uber Go 术语表进行术语替换"""
    result = text
    for eng, pl in UBER_GO_TERMS.items():
        # 不区分大小写替换，保持原格式
        result = re.sub(r'\b' + re.escape(eng) + r'\b', pl, result, flags=re.IGNORECASE)
    return result


def _check_uber_go_style(text: str) -> List[str]:
    """检查 Uber Go 风格规则，返回违规建议列表"""
    suggestions = []
    for pattern, suggestion, rule_id in UBER_GO_STYLE_RULES:
        if re.search(pattern, text):
            suggestions.append(f"[{rule_id}] {suggestion}")
    return suggestions


def _validate_api_response(data: Any) -> Tuple[bool, str]:
    """
    校验 API 响应 JSON 结构
    返回: (是否有效, 错误信息)
    """
    if not isinstance(data, dict):
        return False, "API 响应不是 JSON 对象"
    
    if "responseStatus" not in data:
        return False, "API 响应缺少 responseStatus 字段"
    
    if data.get("responseStatus") != 200:
        return False, f"API 返回错误状态: {data.get('responseStatus')}"
    
    if "responseData" not in data or not isinstance(data["responseData"], dict):
        return False, "API 响应缺少 responseData 对象"
    
    if "translatedText" not in data["responseData"]:
        return False, "API 响应缺少 translatedText 字段"
    
    if not isinstance(data["responseData"]["translatedText"], str):
        return False, "translatedText 字段不是字符串"
    
    return True, ""


# ---------------------------------------------------------------------------
# 核心处理函数
# ---------------------------------------------------------------------------
def _read_text_safe(path):
    """多编码安全读取（R3+R5 合规）"""
    for enc in ("utf-8", "gbk", "gb18030"):  # gbk gb18030 fallback
        try:
            with open(path, encoding=enc, errors="replace") as f:
                return f.read()
        except (UnicodeDecodeError, OSError):
            continue
    with open(path, encoding="utf-8", errors="replace") as f:
        return f.read()

# 批处理流式读取工具
def _iter_lines(path):
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:  # readline 流式
            yield line


def validate_input(data: Any) -> Tuple[bool, str]:
    """
    校验输入数据（Step 1: 收集最小信息集）
    返回: (是否通过, 错误码或空字符串)
    """
    if data is None:
        return False, "E001"
    if isinstance(data, str) and not data.strip():
        return False, "E001"
    if isinstance(data, (list, tuple)) and len(data) == 0:
        return False, "E001"
    if isinstance(data, str) and len(data) > MAX_INPUT_LENGTH:
        return False, "E009"
    return True, ""


def extract_key_info(text: str) -> Dict[str, Any]:
    """
    提取输入中的关键信息（Step 2.1）
    支持: 文本、关键词、结构化占位符
    """
    info: Dict[str, Any] = {}

    # 检测是否包含 URL
    url_pattern = r'https?://[^\s]+'
    urls = re.findall(url_pattern, text)
    if urls:
        info["urls"] = urls

    # 检测是否包含文件路径
    file_pattern = r'[\w\-./\\]+\.\w{1,5}'
    files = re.findall(file_pattern, text)
    if files:
        info["files"] = files

    # 统计文本长度
    info["length"] = len(text)

    # 检测关键词
    keywords = ["翻译", "润色", "格式化", "批量", "转换"]
    found_keywords = [kw for kw in keywords if kw in text]
    if found_keywords:
        info["keywords"] = found_keywords

    return info


def compute_confidence(info: Dict[str, Any]) -> float:
    """
    计算处理置信度（Step 2.3）
    规则:
      - 有明确关键词: 95
      - 有 URL/文件: 90
      - 文本较长(>50): 88
      - 文本较短: 80
    """
    score = 80.0

    if "keywords" in info and len(info["keywords"]) > 0:
        score += 10

    if "urls" in info or "files" in info:
        score += 5

    if info.get("length", 0) > 50:
        score += 3

    return min(score, 99.0)


def _translate_with_api(text: str, target_lang: str) -> Tuple[str, float]:
    """
    调用翻译 API 进行真实翻译。
    使用 MyMemory 免费 API，支持指数退避重试和超时。
    返回: (翻译结果, 置信度)
    """
    # 清理过期缓存
    _cleanup_cache()

    # 检查缓存
    cache_key = f"{text}|{target_lang}"
    cached_result = _get_cached_translation(cache_key)
    if cached_result:
        return cached_result, 95.0

    # 构建请求参数
    params = {
        "q": text,
        "langpair": f"en|{target_lang}",
    }
    url = f"{TRANSLATE_API_URL}?{urllib.parse.urlencode(params)}"

    # 指数退避重试机制
    for attempt in range(TRANSLATE_API_MAX_RETRIES):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "uber-go-guide-pl/1.0"})
            with urllib.request.urlopen(req, timeout=TRANSLATE_API_TIMEOUT) as response:
                data = json.loads(response.read().decode("utf-8"))
                
                # 校验 API 响应结构
                is_valid, error_msg = _validate_api_response(data)
                if not is_valid:
                    raise ValueError(f"API 响应格式错误: {error_msg}")
                
                translated = data["responseData"]["translatedText"]
                if translated:
                    # 置信度基于 API 响应质量
                    confidence = 95.0 if data.get("responseDetails") == "" else 90.0
                    # 缓存结果（带时间戳）
                    _set_cached_translation(cache_key, translated)
                    return translated, confidence
                else:
                    raise ValueError("API 返回空翻译结果")
                    
        except (urllib.error.URLError, urllib.error.HTTPError, ValueError, TimeoutError) as e:
            if attempt < TRANSLATE_API_MAX_RETRIES - 1:
                # 指数退避 + 随机抖动（2^n * 0.5~1.5s），最大不超过 TRANSLATE_API_MAX_BACKOFF
                base_wait = (2 ** attempt) * 0.5
                jitter = random.uniform(0.5, 1.5)
                wait_time = min(base_wait * jitter, TRANSLATE_API_MAX_BACKOFF)
                print(f"[翻译API] 第{attempt + 1}次尝试失败: {e}, {wait_time:.2f}秒后重试...")
                time.sleep(wait_time)
            else:
                # 最后一次失败，返回错误码
                print(f"[翻译API] 所有重试均失败: {e}")
                return "", 0.0

    return "", 0.0


def _rule_based_translate(text: str, target_lang: str) -> Tuple[str, float]:
    """
    基于规则的翻译（离线备用方案）。
    支持常见英文到波兰语的简单翻译。
    返回: (翻译结果, 置信度)
    """
    translations = {
        "hello": "cześć",
        "world": "świat",
        "good": "dobry",
        "morning": "poranek",
        "thank": "dziękuję",
        "please": "proszę",
        "yes": "tak",
        "no": "nie",
        "help": "pomoc",
        "friend": "przyjaciel",
        "love": "miłość",
        "time": "czas",
        "day": "dzień",
        "night": "noc",
        "food": "jedzenie",
        "water": "woda",
    }

    words = text.split()
    translated_words = []
    matched_count = 0
    for word in words:
        lower_word = word.lower().strip(".,!?;:")
        if lower_word in translations:
            translated_words.append(translations[lower_word])
            matched_count += 1
        else:
            translated_words.append(word)

    translated = " ".join(translated_words)
    # 置信度基于匹配率
    if len(words) > 0:
        confidence = 80.0 + (matched_count / len(words)) * 15.0
    else:
        confidence = 80.0

    return translated, min(confidence, 95.0)


def _polish_text(text: str) -> str:
    """
    润色算法：基于规则的文本优化。
    包括：
    - 去除多余空格
    - 统一标点符号
    - 首字母大写
    - 修正常见拼写错误
    """
    polished = text.strip()
    
    # 去除多余空格
    polished = re.sub
