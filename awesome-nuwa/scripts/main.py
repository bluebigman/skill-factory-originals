#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
awesome-nuwa — 人物思维框架蒸馏与复用工具
功能：将人物资料文本蒸馏为结构化思维框架卡（JSON格式）
版本：1.2.1
"""

import argparse
import json
import os
import re
import sys
import time
import threading
import hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 错误码定义
# ============================================================
ERROR_CODES = {
    "E001": "输入文本为空",
    "E002": "输入文本格式无效（非字符串）",
    "E003": "文本长度超出限制（最大100000字符）",
    "E004": "JSON序列化失败",
    "E005": "输出目录不可写",
    "E006": "人物名称提取失败",
    "E007": "文本分段失败",
    "E008": "关键信息提取失败",
    "E009": "框架生成失败",
    "E010": "未知错误",
    "E011": "文件读取失败",
    "E012": "批量处理失败",
}


class NuwaError(Exception):
    """自定义异常类，携带错误码"""
    def __init__(self, code: str, message: str = ""):
        self.code = code
        self.message = message or ERROR_CODES.get(code, "未知错误")
        super().__init__(f"[{code}] {self.message}")


# ============================================================
# 核心功能：文本处理与信息提取
# ============================================================

# 文件读取缓存（直接缓存内容，哈希仅用于变更校验）
_CACHE_TTL = 300  # 5分钟缓存有效期
_cache_store: Dict[str, Tuple[float, str, str]] = {}  # path -> (timestamp, content_hash, content)
_cache_lock = threading.Lock()


def _compute_content_hash(content: str) -> str:
    """计算内容哈希用于缓存验证"""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _read_text_safe(path: str) -> str:
    """多编码安全读取，带内容缓存，失败时抛出NuwaError"""
    normalized_path = os.path.realpath(os.path.abspath(path))
    
    # 检查缓存
    with _cache_lock:
        if normalized_path in _cache_store:
            timestamp, cached_hash, cached_content = _cache_store[normalized_path]
            if time.time() - timestamp < _CACHE_TTL:
                # 验证文件内容是否变化
                try:
                    with open(normalized_path, "rb") as f:
                        current_hash = hashlib.sha256(f.read()).hexdigest()
                    if current_hash == cached_hash:
                        # 缓存有效，直接返回缓存内容
                        return cached_content
                except OSError:
                    pass
            # 缓存过期或内容变化，删除缓存
            del _cache_store[normalized_path]
    
    # 读取文件（完整编码回退列表）
    last_error = None
    for enc in ("utf-8", "gbk", "gb18030", "latin-1"):
        try:
            with open(normalized_path, encoding=enc, errors="strict") as f:
                content = f.read()
                # 更新缓存（直接存储内容）
                with _cache_lock:
                    _cache_store[normalized_path] = (time.time(), _compute_content_hash(content), content)
                return content
        except UnicodeDecodeError as e:
            last_error = e
            continue
        except OSError as e:
            last_error = e
            break
    raise NuwaError("E011", f"无法读取文件 {path}: {last_error}")


def _iter_lines(path: str):
    """流式读取文件行"""
    try:
        with open(path, encoding="utf-8", errors="strict") as f:
            for line in f:
                yield line
    except UnicodeDecodeError as e:
        raise NuwaError("E011", f"文件编码错误 {path}: {e}")
    except OSError as e:
        raise NuwaError("E011", f"无法读取文件 {path}: {e}")


def validate_input(text: Any) -> str:
    """验证输入文本，返回清洗后的字符串"""
    if text is None:
        raise NuwaError("E001")
    if not isinstance(text, str):
        if isinstance(text, (bytes, bytearray)):
            try:
                text = text.decode("utf-8")
            except UnicodeDecodeError:
                raise NuwaError("E002")
        else:
            raise NuwaError("E002")
    text = text.strip()
    if not text:
        raise NuwaError("E001")
    if len(text) > 100000:
        raise NuwaError("E003")
    return text


def split_paragraphs(text: str) -> List[str]:
    """将文本按段落分割，过滤空段落"""
    try:
        raw_paras = re.split(r"\n\s*\n", text)
        paras = [p.strip() for p in raw_paras if p.strip()]
        if not paras:
            # 如果没有空行分隔，按单行分割
            paras = [p.strip() for p in text.split("\n") if p.strip()]
        if not paras:
            raise NuwaError("E007")
        return paras
    except NuwaError:
        raise
    except Exception as e:
        raise NuwaError("E007", str(e))


def extract_person_name(text: str) -> str:
    """从文本中提取人物名称（启发式规则）"""
    # 匹配常见模式：XXX是/作为/在...
    patterns = [
        r"^([\u4e00-\u9fa5A-Za-z]{2,10})(?:是|作为|在|的|，|。|：)",
        r"人物[：:]\s*([\u4e00-\u9fa5A-Za-z]{2,10})",
        r"姓名[：:]\s*([\u4e00-\u9fa5A-Za-z]{2,10})",
    ]
    for pat in patterns:
        m = re.search(pat, text)
        if m:
            return m.group(1).strip()
    # 取第一个非空段落的前几个词
    paras = split_paragraphs(text)
    if paras:
        first = paras[0]
        words = re.findall(r"[\u4e00-\u9fa5A-Za-z]+", first)
        if words:
            return words[0][:10]
    raise NuwaError("E006")


def extract_key_info(text: str) -> Dict[str, Any]:
    """从文本中提取关键信息字段（基于规则的蒸馏算法）"""
    paras = split_paragraphs(text)
    info = {
        "decisions": [],      # 决策习惯
        "thinking": [],       # 思维偏好
        "values": [],         # 价值排序
        "traits": [],         # 性格特征
        "keywords": [],       # 关键词
        "confidence": "medium",  # 置信度
    }

    # 关键词提取（TF-IDF简化版：词频 + 位置权重）
    word_freq: Dict[str, int] = {}
    all_words = re.findall(r"[\u4e00-\u9fa5]{2,6}", text)
    stop_words = {"我们", "他们", "这个", "那个", "什么", "没有", "一个", "可以", "因为", "所以", "但是", "如果", "就是", "不是", "还是", "或者", "以及", "对于", "关于", "通过", "进行", "已经", "现在", "时候", "可能", "需要", "应该", "能够", "这样", "那样", "这些", "那些", "自己", "别人", "大家", "所有", "一些", "很多", "非常", "特别", "比较", "更加", "最", "更", "很", "太", "真", "好", "坏", "大", "小", "高", "低"}
    for w in all_words:
        if len(w) >= 2 and w not in stop_words:
            word_freq[w] = word_freq.get(w, 0) + 1
    
    # 位置权重：出现在段落开头或结尾的词权重更高
    for i, para in enumerate(paras):
        para_words = re.findall(r"[\u4e00-\u9fa5]{2,6}", para)
        for w in para_words:
            if w not in stop_words and len(w) >= 2:
                if i == 0 or i == len(paras) - 1:
                    word_freq[w] = word_freq.get(w, 0) + 2  # 首尾段落权重加倍
                else:
                    word_freq[w] = word_freq.get(w, 0) + 1
    
    top_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:10]
    info["keywords"] = [w for w, _ in top_words]

    # 决策习惯提取（基于语义模式）
    decision_patterns = [
        (r"(?:习惯|倾向于|总是|经常|喜欢)[^。；\n]{2,30}", "habit"),
        (r"(?:决策|选择|判断)[^。；\n]{2,30}", "decision"),
        (r"(?:在做|进行)[^。；\n]{0,10}(?:决策|选择|判断)[^。；\n]{2,30}", "decision_process"),
    ]
    for pat, _ in decision_patterns:
        matches = re.findall(pat, text)
        for m in matches[:5]:
            clean = m.strip()
            if clean and clean not in info["decisions"]:
                info["decisions"].append(clean)

    # 思维偏好提取
    thinking_patterns = [
        (r"(?:认为|相信|觉得|主张)[^。；\n]{2,30}", "belief"),
        (r"(?:思考|思维|逻辑|直觉)[^。；\n]{2,30}", "thinking_style"),
        (r"(?:倾向于|偏好|喜欢)[^。；\n]{0,10}(?:思考|思维|逻辑)[^。；\n]{2,30}", "thinking_preference"),
    ]
    for pat, _ in thinking_patterns:
        matches = re.findall(pat, text)
        for m in matches[:5]:
            clean = m.strip()
            if clean and clean not in info["thinking"]:
                info["thinking"].append(clean)

    # 价值排序提取
    value_patterns = [
        (r"(?:重视|看重|注重|优先)[^。；\n]{2,30}", "value"),
        (r"(?:价值观|原则|信念)[：:][^。；\n]{2,30}", "value_statement"),
        (r"(?:把|将)[^。；\n]{0,10}(?:放在|视为|当作)[^。；\n]{2,30}", "value_priority"),
    ]
    for pat, _ in value_patterns:
        matches = re.findall(pat, text)
        for m in matches[:5]:
            clean = m.strip()
            if clean and clean not in info["values"]:
                info["values"].append(clean)

    # 性格特征提取
    trait_patterns = [
        (r"(?:性格|为人|行事|作风)[^。；\n]{2,30}", "trait"),
        (r"(?:果断|谨慎|乐观|悲观|激进|保守|理性|感性|严谨|随和|独立|合作)[^。；\n]{0,20}", "trait_word"),
        (r"(?:是一个|是个)[^。；\n]{0,10}(?:果断|谨慎|乐观|悲观|激进|保守|理性|感性|严谨|随和|独立|合作)[^。；\n]{0,20}", "trait_description"),
    ]
    for pat, _ in trait_patterns:
        matches = re.findall(pat, text)
        for m in matches[:5]:
            clean = m.strip()
            if clean and clean not in info["traits"]:
                info["traits"].append(clean)

    # 置信度评估：基于信息完整度和关键词数量
    filled_count = sum(1 for lst in [info["decisions"], info["thinking"], info["values"], info["traits"]] if lst)
    keyword_score = min(len(info["keywords"]) / 5, 1.0)  # 关键词数量归一化
    
    if filled_count >= 3 and keyword_score >= 0.6:
        info["confidence"] = "high"
    elif filled_count >= 1 and keyword_score >= 0.3:
        info["confidence"] = "medium"
    else:
        info["confidence"] = "low"

    if not any([info["decisions"], info["thinking"], info["values"], info["traits"]]):
        raise NuwaError("E008")

    return info


def generate_framework(name: str, info: Dict[str, Any]) -> Dict[str, Any]:
    """生成思维框架卡（基于规则的真实蒸馏算法）"""
    try:
        # 构建思维框架卡
        framework = {
            "schema_version": "1.0.0",
            "person": name,
            "extracted_at": datetime.now(timezone.utc).isoformat(),
            "confidence": info.get("confidence", "low"),
            "dimensions": {
                "decision_habits": info.get("decisions", []),
                "thinking_preferences": info.get("thinking", []),
                "value_priorities": info.get("values", []),
                "personality_traits": info.get("traits", []),
            },
            "keywords": info.get("keywords", []),
            "source_type": "text",
            "metadata": {
                "skill": "awesome-nuwa",
                "version": "1.2.1",
                "distillation_method": "heuristic-rule-based",
                "distillation_algorithm": "pattern-matching-and-frequency-analysis",
            },
        }
        
        # 添加推理摘要（基于提取的信息生成）
        reasoning = []
        if info.get("decisions"):
            reasoning.append(f"根据文本中的决策模式，识别出{len(info['decisions'])}条决策习惯")
        if info.get("thinking"):
            reasoning.append(f"根据文本中的思维表达，识别出{len(info['thinking'])}条思维偏好")
        if info.get("values"):
            reasoning.append(f"根据文本中的价值陈述，识别出{len(info['values'])}条价值排序")
        if info.get("traits"):
            reasoning.append(f"根据文本中的性格描述，识别出{len(info['traits'])}条性格特征")
        framework["reasoning"] = reasoning
        
        return framework
    except Exception as e:
        raise NuwaError("E009", str(e))


def distill(text: str) -> Dict[str, Any]:
    """主蒸馏流程：文本 -> 思维框架卡"""
    try:
        clean_text = validate_input(text)
        name = extract_person_name(clean_text)
        info = extract_key_info(clean_text)
        framework = generate_framework(name, info)
        return framework
    except NuwaError:
        raise
    except Exception as e:
        raise NuwaError("E010", str(e))


# ============================================================
# 批量处理功能（带重试、退避和降级策略）
# ============================================================

def _process_file_with_retry(filepath: str, max_retries: int = 3, base_delay: float = 1.0) -> Dict[str, Any]:
    """处理单个文件，带指数退避重试"""
    for attempt in range(max_retries):
        try:
            text = _read_text_safe(filepath)
            framework = distill(text)
            return {"file": filepath, "success": True, "framework": framework}
        except NuwaError as e:
            if attempt < max_retries - 1 and e.code == "E011":  # 文件读取错误可重试
                delay = base_delay * (2 ** attempt)  # 指数退避
                time.sleep(delay)
                continue
            return {"file": filepath, "success": False, "error": f"[{e.code}] {e.message}"}
        except Exception as e:
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)
                time.sleep(delay)
                continue
            return {"file": filepath, "success": False, "error": f"[E010] {str(e)}"}
    return {"file": filepath, "success": False, "error": "[E010] 重试次数耗尽"}


def process_batch(input_files: List[str], output_dir: Optional[str] = None, max_workers: int = 4) -> List[Dict[str, Any]]:
    """批量处理多个文件，支持并发，带重试和降级策略"""
    results = []
    errors = []

    def process_file(filepath: str) -> Dict[str, Any]:
        return _process_file_with_retry(filepath)

    try:
        # 尝试并发处理
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_file = {executor.submit(process_file, f): f for f in input_files}
            total = len(input_files)
            completed = 0
            for future in as_completed(future_to_file):
                result = future.result()
                completed += 1
                # 进度反馈
                print(f"进度: {completed}/{total} 完成", file=sys.stderr)
                
                if result["success"]:
                    results.append(result)
                    if output_dir:
                        os.makedirs(output_dir, exist_ok=True)
                        output_path = os.path.join(output_dir, os.path.basename(result["file"]).replace(".txt", ".json"))
                        save_json(result["framework"], output_path)
                else:
                    errors.append(result)
    except Exception as e:
        # 降级策略：并发失败时回退到单线程处理
        print(f"警告：并发处理失败（{e}），降级到单线程模式...", file=sys.stderr)
        results = []
        errors = []
