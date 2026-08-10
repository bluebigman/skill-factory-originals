#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
audio-transcript-format v4.2.0
语音转写文本整理与决策记录提取工具

纯标准库实现，无第三方依赖。
"""

import argparse
import json
import os
import re
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple
dry_run = False  # v3.274 模块级 dry-run 标志

# ============================================================
# 常量定义
# ============================================================

VERSION = "4.2.0"

# 填充词表（用于清理）
FILLER_WORDS = [
    "嗯", "啊", "呃", "然后", "就是", "那个", "这个",
    "那个那个", "这个这个", "嗯嗯", "啊啊", "呃呃",
]

# 语气词（句尾保留）
MODAL_PARTICLES = ["吧", "呢", "吗", "嘛", "呗", "呀", "啦", "哦", "喔"]

# 指代保护模式：那个/这个 + 名词（保留）
DEMONSTRATIVE_PRONOUNS = ["那个", "这个"]

# 待办提取词表（领域通用）
TODO_KEYWORDS_GENERAL = [
    "需要", "要", "必须", "得", "应该", "应当", "务必",
    "负责", "跟进", "落实", "完成", "提交", "准备",
    "安排", "联系", "确认", "协调", "处理", "执行",
]

# 截止提取词表
DEADLINE_KEYWORDS = [
    "截止", "之前", "以前", "前", "内", "以内",
    "明天", "后天", "今天", "本周", "下周", "本月", "下月",
    "周", "月", "日", "点",
]

# 异议提取词表
OBJECTION_KEYWORDS = [
    "但是", "不过", "然而", "可是", "问题", "风险",
    "担忧", "顾虑", "不同意", "反对", "异议", "困难",
    "障碍", "挑战", "不确定", "担心",
]

# 决策提取词表
DECISION_KEYWORDS = [
    "决定", "确定", "敲定", "通过", "批准", "同意",
    "确认", "采纳", "选定", "采用", "执行", "实施",
    "就这么定", "就这样", "定了",
]

# 领域词表
DOMAIN_TODO = {
    "general": TODO_KEYWORDS_GENERAL,
    "meeting": TODO_KEYWORDS_GENERAL + ["会议纪要", "纪要", "行动项", "跟进项"],
    "legal": ["提交", "送达", "举证", "开庭", "答辩", "上诉", "申诉", "执行", "保全", "立案"],
    "medical": ["服药", "复诊", "复查", "检查", "住院", "手术", "治疗", "医嘱", "随访", "用药"],
}

DOMAIN_DEADLINE = {
    "general": DEADLINE_KEYWORDS,
    "meeting": DEADLINE_KEYWORDS + ["会后", "下次会议", "下一次"],
    "legal": ["开庭日", "举证期限", "答辩期", "上诉期", "执行期限", "诉讼时效"],
    "medical": ["疗程", "药程", "复查日", "随访日", "住院天数"],
}

DOMAIN_OBJECTION = {
    "general": OBJECTION_KEYWORDS,
    "meeting": OBJECTION_KEYWORDS + ["议题", "分歧", "争议"],
    "legal": ["异议", "抗辩", "反驳", "质疑", "不服"],
    "medical": ["副作用", "禁忌", "过敏", "不良反应"],
}

DOMAIN_DECISION = {
    "general": DECISION_KEYWORDS,
    "meeting": DECISION_KEYWORDS + ["达成一致", "共识", "定稿"],
    "legal": ["判决", "裁定", "调解", "和解", "撤诉"],
    "medical": ["确诊", "治疗方案", "手术方案", "用药方案"],
}

# 否定词（用于过滤）
NEGATION_WORDS = ["不", "没", "别", "勿", "未", "无", "非"]

# 疑问词（用于过滤）
QUESTION_WORDS = ["吗", "呢", "？", "?", "什么", "怎么", "为什么", "是否", "能否"]

# 时间词解析映射
TIME_WORD_MAP = {
    "今天": 0, "明天": 1, "后天": 2,
    "本周": 0, "下周": 7, "下下周": 14,
    "本月": 0, "下月": 30,
}

WEEKDAY_MAP = {
    "周一": 0, "周二": 1, "周三": 2, "周四": 3,
    "周五": 4, "周六": 5, "周日": 6, "星期天": 6,
}

# ============================================================
# 异常定义
# ============================================================

class TranscriptError(Exception):
    """转录处理基础异常"""
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"[{code}] {message}")

class InputFileNotFoundError(TranscriptError):
    def __init__(self, path: str):
        super().__init__("E001", f"输入文件不存在: {path}")

class EncodingError(TranscriptError):
    def __init__(self, path: str):
        super().__init__("E002", f"无法识别文件编码: {path}")

class PermissionError(TranscriptError):
    def __init__(self, path: str):
        super().__init__("E003", f"无写入权限: {path}")

class JSONFormatError(TranscriptError):
    def __init__(self, path: str):
        super().__init__("E004", f"JSON 格式错误: {path}")

class ICSError(TranscriptError):
    def __init__(self, message: str):
        super().__init__("E005", f"ICS 导出失败: {message}")

class HTMLError(TranscriptError):
    def __init__(self, message: str):
        super().__init__("E006", f"HTML 导出失败: {message}")

class ArgumentConflictError(TranscriptError):
    def __init__(self, message: str):
        super().__init__("E007", f"参数冲突: {message}")

class EmptyInputError(TranscriptError):
    def __init__(self):
        super().__init__("E008", "输入文件为空")

class FileTooLargeError(TranscriptError):
    def __init__(self, size: int):
        super().__init__("E009", f"输入文件过大 ({size} bytes > 10MB)")

class UnknownDomainError(TranscriptError):
    def __init__(self, domain: str):
        super().__init__("E010", f"未知领域词表: {domain}")

# ============================================================
# 工具函数
# ============================================================

def read_file_with_encoding(path: str) -> str:
    """读取文件，自动识别编码（utf-8 → gbk → gb18030 → latin-1）"""
    if not os.path.exists(path):
        raise InputFileNotFoundError(path)
    
    file_size = os.path.getsize(path)
    if file_size == 0:
        raise EmptyInputError()
    if file_size > 10 * 1024 * 1024:
        raise FileTooLargeError(file_size)
    
    encodings = ["utf-8", "gbk", "gb18030", "latin-1"]
    for enc in encodings:
        try:
            with open(path, "r", encoding=enc) as f:
                return f.read()
        except UnicodeDecodeError:
            continue
        except Exception as e:
            raise EncodingError(path) from e
    
    raise EncodingError(path)

def write_file_atomic(path: str, content: str) -> None:
    """原子化写入文件（先写临时文件再重命名）"""
    dir_path = os.path.dirname(os.path.abspath(path))
    if not os.access(dir_path, os.W_OK):
        raise PermissionError(path)
    
    fd, temp_path = tempfile.mkstemp(dir=dir_path, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(temp_path, path)
    except Exception as e:
        if os.path.exists(temp_path):
            os.unlink(temp_path)
        raise e

def safe_json_loads(text: str) -> Optional[Dict]:
    """安全解析 JSON，失败返回 None"""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None

# ============================================================
# 核心处理函数
# ============================================================

def split_sentences(text: str) -> List[str]:
    """
    健壮分句：处理引号/括号/缩写内的句号不误分。
    
    规则：
    1. 引号内的句号不分割
    2. 括号内的句号不分割
    3. 常见缩写（如 "e.g."、"i.e."）不分割
    4. 数字小数点不分割
    """
    # 保护引号内容
    protected = []
    def protect_quotes(match):
        protected.append(match.group(0))
        return f"\x00{len(protected)-1}\x00"
    
    text_protected = re.sub(r'"[^"]*"|\'[^\']*\'|“[^”]*”|‘[^’]*’', protect_quotes, text)
    
    # 保护括号内容
    def protect_parens(match):
        protected.append(match.group(0))
        return f"\x00{len(protected)-1}\x00"
    
    text_protected = re.sub(r'\([^)]*\)|\[[^\]]*\]|（[^）]*）|【[^】]*】', protect_parens, text_protected)
    
    # 保护缩写
    def protect_abbr(match):
        protected.append(match.group(0))
        return f"\x00{len(protected)-1}\x00"
    
    text_protected = re.sub(r'\b(?:e\.g|i\.e|etc|vs|Mr|Mrs|Dr|Prof)\.', protect_abbr, text_protected)
    
    # 保护数字小数点
    def protect_decimal(match):
        protected.append(match.group(0))
        return f"\x00{len(protected)-1}\x00"
    
    text_protected = re.sub(r'\d+\.\d+', protect_decimal, text_protected)
    
    # 按句号/问号/感叹号分句
    sentences = re.split(r'[。！？!?]+', text_protected)
    
    # 还原保护内容
    result = []
    for s in sentences:
        s = s.strip()
        if not s:
            continue
        # 还原保护内容
        def restore(match):
            idx = int(match.group(1))
            return protected[idx]
        s = re.sub(r'\x00(\d+)\x00', restore, s)
        result.append(s)
    
    return result

def clean_filler_words(text: str, verbose: bool = False) -> Tuple[str, List[str]]:
    """
    清理填充词，返回清理后的文本和删除的填充词列表。
    
    规则：
    1. 删除填充词（嗯/啊/呃/然后/就是/那个/这个）
    2. 指代保护："那个/这个" + 名词 = 指代，保留
    3. 句尾语气词保留（呢/吧/吗 不删）
    """
    removed = []
    
    # 指代保护：那个/这个 + 名词
    def protect_demonstrative(match):
        return match.group(0)
    
    # 先找出所有指代用法
    demonstrative_matches = set()
    for m in re.finditer(r'(那个|这个)([\u4e00-\u9fff]{1,4})', text):
        demonstrative_matches.add(m.group(0))
    
    # 清理填充词
    for word in FILLER_WORDS:
        if word not in ["那个", "这个"]:
            # 普通填充词直接删除
            pattern = re.compile(re.escape(word))
            matches = pattern.findall(text)
            if matches:
                removed.extend(matches)
                text = pattern.sub("", text)
        else:
            # 那个/这个：仅当不作为指代时删除
            # 找出所有出现位置
            for m in re.finditer(re.escape(word), text):
                start = m.start()
                end = m.end()
                # 检查是否是指代用法
                is_demonstrative = False
                for dm in demonstrative_matches:
                    if text[start:start+len(dm)] == dm:
                        is_demonstrative = True
                        break
                if not is_demonstrative:
                    removed.append(word)
                    text = text[:start] + text[end:]
    
    # 清理多余空格
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text, removed

def fix_punctuation(text: str) -> str:
    """修复标点：合并重复标点、清理空格、英文数字前补空格"""
    # 合并重复标点
    text = re.sub(r'([。！？!?]){2,}', r'\1', text)
    text = re.sub(r'([，,]){2,}', r'\1', text)
    text = re.sub(r'([；;]){2,}', r'\1', text)
    text = re.sub(r'([：:]){2,}', r'\1', text)
    
    # 清理标点前空格
    text = re.sub(r'\s+([。！？!?，,；;：:])', r'\1', text)
    
    # 英文/数字前补空格
    text = re.sub(r'([\u4e00-\u9fff])([A-Za-z0-9])', r'\1 \2', text)
    text = re.sub(r'([A-Za-z0-9])([\u4e00-\u9fff])', r'\1 \2', text)
    
    # 清理多余空格
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text

def apply_terms(text: str, terms: Dict[str, str]) -> str:
    """应用术语映射（大小写不敏感）"""
    if not terms:
        return text
    
    for src, dst in terms.items():
        # 大小写不敏感替换
        pattern = re.compile(re.escape(src), re.IGNORECASE)
        text = pattern.sub(dst, text)
    
    return text

def split_paragraphs(text: str, max_len: int = 200) -> List[str]:
    """
    段落分割：滑动窗口主题漂移 + 连接词边界。
    
    规则：
    1. 按句号分句
    2. 滑动窗口检测主题漂移（关键词变化）
    3. 连接词（但是/然而/因此）作为段落边界
    """
    sentences = split_sentences(text)
    if len(sentences) <= 1:
        return [text] if text else []
    
    paragraphs = []
    current_para = []
    current_len = 0
    
    # 连接词边界
    boundary_words = ["但是", "不过", "然而", "因此", "所以", "此外", "另外", "总之", "最后"]
    
    for i, sent in enumerate(sentences):
        current_para.append(sent)
        current_len += len(sent)
        
        # 检查是否应该分段
        should_split = False
        
        # 1. 长度超过阈值
        if current_len >= max_len:
            should_split = True
        
        # 2. 连接词边界（当前句以连接词开头）
        if i < len(sentences) - 1:
            next_sent = sentences[i + 1]
            for bw in boundary_words:
                if next_sent.startswith(bw):
                    should_split = True
                    break
        
        # 3. 主题漂移检测（简单关键词重叠）
        if i > 0 and i < len(sentences) - 1:
            prev_keywords = set(re.findall(r'[\u4e00-\u9fff]{2,4}', sentences[i-1]))
            curr_keywords = set(re.findall(r'[\u4e00-\u9fff]{2,4}', sent))
            next_keywords = set(re.findall(r'[\u4e00-\u9fff]{2,4}', sentences[i+1]))
            
            overlap_prev = len(prev_keywords & curr_keywords) / max(len(prev_keywords | curr_keywords), 1)
            overlap_next = len(curr_keywords & next_keywords) / max(len(curr_keywords | next_keywords), 1)
            
            if overlap_prev < 0.1 and overlap_next < 0.1:
                should_split = True
        
        if should_split and current_para:
            paragraphs.append("".join(current_para))
            current_para = []
            current_len = 0
    
    if current_para:
        paragraphs.append("".join(current_para))
    
    return paragraphs

def format_list(text: str) -> str:
    """
    列表化：识别"第一/第二…"、"首先/其次…"、行内编号 "1. 2." 等。
    """
    lines = text.split("\n")
    formatted_lines = []
    
    for line in lines:
        # 检查是否已有列表格式
        if re.match(r'^\s*[\d一二三四五六七八九十]+[\.、．]', line):
            formatted_lines.append(line)
            continue
        
        # 识别"第一，…第二，…"模式
        parts = re.split(r'(第一|第二|第三|第四|第五|第六|第七|第八|第九|第十)', line)
        if len(parts) > 1:
            list_items = []
            for i in range(1, len(parts), 2):
                if i + 1 < len(parts):
                    item_text = parts[i + 1].strip("，,。 ")
                    if item_text:
                        list_items.append(f"{i//2 + 1}. {item_text}")
            if list_items:
                formatted_lines.extend(list_items)
                continue
        
        # 识别"首先…其次…"模式
        parts = re.split(r'(首先|其次|再次|最后)', line)
        if len(parts) > 1:
            list_items = []
            for i in range(1, len(parts), 2):
                if i + 1 < len(parts):
                    item_text = parts[i + 1].strip("，,。 ")
                    if item_text:
                        list_items.append(f"{i//2 + 1}. {item_text}")
            if list_items:
                formatted_lines.extend(list_items)
                continue
        
        # 识别行内编号 "1. 2."
        parts = re.split(r'(\d+[\.、．])', line)
        if len(parts) > 1:
            list_items = []
            for i in range(1, len(parts), 2):
                if i + 1 < len(parts):
                    item_text = parts[i + 1].strip("，,。 ")
                    if item_text:
                        list_items.append(f"{parts[i]} {item_text}")
            if list_items:
                formatted_lines.extend(list_items)
                continue
        
        formatted_lines.append(line)
    
    return "\n".join(formatted_lines)

# ============================================================
# 决策提取
# ============================================================

def extract_decisions(text: str, domain: str = "general") -> Dict[str, List[Dict]]:
    """
    提取决策记录：待办/截止/异议/决策。
    
    返回格式：
    {
        "todos": [{"text": str, "sentence_idx": int, "confidence": float}],
        "deadlines": [{"text": str, "sentence_idx": int, "confidence": float, "date": str}],
        "objections": [{"text": str, "sentence_idx": int, "confidence": float}],
        "decisions": [{"text": str, "sentence_idx": int, "confidence": float}]
    }
    """
    if domain not in DOMAIN_TODO:
        raise UnknownDomainError(domain)
    
    sentences = split_sentences(text)
    result = {
        "todos": [],
        "deadlines": [],
        "objections": [],
        "decisions": [],
    }
    
    todo_keywords = DOMAIN_TODO[domain]
    deadline_keywords = DOMAIN_DEADLINE[domain]
    objection_keywords = DOMAIN_OBJECTION[domain]
    decision_keywords = DOMAIN_DECISION[domain]
    
    for idx, sent in enumerate(sentences):
        # 跳过否定句
        is_negation = any(neg in sent for neg in NEGATION_WORDS)
        # 跳过疑问句
        is_question = any(q in sent for q in QUESTION_WORDS)
        
        # 提取待办
        if not is_negation and not is_question:
            for kw in todo_keywords:
                if kw in sent:
                    confidence = 0.5
                    # 有主语加分
                    if re.search(r'[\u4e00-\u9fff]{2,3}(?:工|总|经理|主任|老师|医生)', sent):
                        confidence += 0.2
                    # 有时间词加分
                    if any(dk in sent for dk in deadline_keywords):
                        confidence += 0.2
                    # 有动作动词加分
                    if any(v in sent for v in ["提交", "完成", "联系", "确认", "处理"]):
                        confidence += 0.1
                    
                    result["todos"].append({
                        "text": sent,
                        "sentence_idx": idx,
                        "confidence": round(min(confidence, 1.0), 2),
                    })
                    break
        
        # 提取截止
        if not is_negation and not is_question:
            for kw in deadline_keywords:
                if kw in sent:
                    confidence = 0.5
                    if re.search(r'[\u4e00-\u9fff]{2,3}(?:工|总|经理|主任|老师|医生)', sent):
                        confidence += 0.2
                    if any(tk in sent for tk in todo_keywords):
                        confidence += 0.2
                    
                    # 解析时间
                    date_str = parse_time_word(sent)
                    
                    result["deadlines"].append({
                        "text": sent,
                        "sentence_idx": idx,
                        "confidence": round(min(confidence, 1.0), 2),
                        "date": date_str,
                    })
                    break
        
        # 提取异议
        if not is_negation:
            for kw in objection_keywords:
                if kw in sent:
                    confidence = 0.5
                    if "风险" in sent or "问题" in sent:
                        confidence += 0.2
                    if "不同意" in sent or "反对" in sent:
                        confidence += 0.2
                    
                    result["objections"].append({
                        "text": sent,
                        "sentence_idx": idx,
                        "confidence": round(min(confidence, 1.0), 2),
                    })
                    break
        
        # 提取决策
        if not is_negation and not is_question:
            for kw in decision_keywords:
                if kw in sent:
                    confidence = 0.5
                    if "决定" in sent or "确定" in sent:
                        confidence += 0.2
                    if "通过" in sent or "批准" in sent:
                        confidence += 0.2
                    
                    result["decisions"].append({
                        "text": sent,
                        "sentence_idx": idx,
                        "confidence": round(min(confidence, 1.0), 2),
                    })
                    break
    
    return result

def parse_time_word(text: str) -> str:
    """解析时间词，返回 ISO 日期字符串"""
    now = datetime.now(timezone.utc)
    
    # 相对时间词
    for word, days in TIME_WORD_MAP.items():
        if word in text:
            target = now + timedelta(days=days)
            return target.strftime("%Y-%m-%d")
    
    # 星期几
    for word, offset in WEEKDAY_MAP.items():
        if word in text:
            target = now + timedelta(days=(offset - now.weekday()) % 7)
            return target.strftime("%Y-%m-%d")
    
    # 具体日期（月/日）
    match = re.search(r'(\d{1,2})月(\d{1,2})日', text)
    if match:
        month, day = int(match.group(1)), int(match.group(2))
        try:
            target = datetime(now.year, month, day, tzinfo=timezone.utc)
            return target.strftime("%Y-%m-%d")
        except ValueError:
            pass
    
    # 具体时间（X点）
    match = re.search(r'(\d{1,2})点', text)
    if match:
        hour = int(match.group(1))
        target = now.replace(hour=hour, minute=0, second=0, microsecond=0)
        return target.strftime("%Y-%m-%d %H:%M")
    
    return ""

# ============================================================
# 导出函数
# ============================================================

def export_ics(extractions: Dict[str, List[Dict]], output_path: str) -> None:
    """导出 ICS 日历文件"""
    events = []
    
    now = datetime.now(timezone.utc)
    
    # 待办事项
    for todo in extractions.get("todos", []):
        date_str = parse_time_word(todo["text"])
        if not date_str:
            date_str = (now + timedelta(days=7)).strftime("%Y-%m-%d")
        
        events.append({
            "summary": f"待办: {todo['text'][:50]}",
            "date": date_str,
        })
    
    # 截止事项
    for deadline in extractions.get("deadlines", []):
        date_str = deadline.get("date", "")
        if not date_str:
            date_str = (now + timedelta(days=7)).strftime("%Y-%m-%d")
        
        events.append({
            "summary": f"截止: {deadline['text'][:50]}",
            "date": date_str,
        })
    
    # 生成 ICS 内容
    ics_lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//audio-transcript-format//CN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
    ]
    
    for i, event in enumerate(events):
        dtstart = event["date"].replace(" ", "T") + ":00"
        dtend = (datetime.fromisoformat(event["date"].replace(" ", "T")) + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:00")
        
        ics_lines.extend([
            "BEGIN:VEVENT",
            f"UID:{now.strftime('%Y%m%d%H%M%S')}-{i}@audio-transcript-format",
            f"DTSTAMP:{now.strftime('%Y%m%dT%H%M%SZ')}",
            f"DTSTART:{dtstart}",
            f"DTEND:{dtend}",
            f"SUMMARY:{event['summary']}",
            "END:VEVENT",
        ])
    
    ics_lines.append("END:VCALENDAR")
    ics_content = "\r\n".join(ics_lines) + "\r\n"
    
    write_file_atomic(output_path, ics_content)

def export_html(original: str, cleaned: str, extractions: Dict[str, List[Dict]], output_path: str) -> None:
    """导出 HTML 手术报告"""
    # 计算 diff
    import difflib
    
    diff = list(difflib.ndiff(original, cleaned))
    
    html_parts = [
        "<!DOCTYPE html>",
        "<html>",
        "<head>",
        "<meta charset='utf-8'>",
        "<title>语音转写整理报告</title>",
        "<style>",
        "body { font-family: sans-serif; margin: 20px; }",
        ".del { background: #ffcccc; text-decoration: line-through; }",
        ".add { background: #ccffcc; }",
        ".para { background: #ccccff; }",
        ".stats { margin: 20px 0; }",
        ".stats table { border-collapse: collapse; }",
        ".stats td, .stats th { border: 1px solid #ccc; padding: 5px 10px; }",
        ".extractions { margin: 20px 0; }",
        ".extractions h3 { margin-bottom: 5px; }",
        "</style>",
        "</head>",
        "<body>",
        "<h1>语音转写整理报告</h1>",
        f"<p>生成时间: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC</p>",
    ]
    
    # 统计信息
    html_parts.append("<div class='stats'><h2>统计信息</h2><table>")
    html_parts.append(f"<tr><th>原始字符数</th><td>{len(original)}</td></tr>")
    html_parts.append(f"<tr><th>整理后字符数</th><td>{len(cleaned)}</td></tr>")
    html_parts.append(f"<tr><th>删除字符数</th><td>{len(original) - len(cleaned)}</td></tr>")
    html_parts.append("</table></div>")
    
    # Diff 视图
    html_parts.append("<div class='diff'><h2>修改明细</h2><p>")
    for token in diff:
        if token.startswith('-'):
            html_parts.append(f"<span class='del'>{token[2:]}</span>")
        elif token.startswith('+'):
            html_parts.append(f"<span class='add'>{token[2:]}</span>")
        else:
            html_parts.append(token[2:])
    html_parts.append("</p></div>")
    
    # 提取结果
    html_parts.append("<div class='extractions'><h2>决策提取</h2>")
    
    categories = [
        ("todos", "待办事项"),
        ("deadlines", "截止日期"),
        ("objections", "异议风险"),
        ("decisions", "决策记录"),
    ]
    
    for key, label in categories:
        items = extractions.get(key, [])
        if items:
            html_parts.append(f"<h3>{label} ({len(items)})</h3><ul>")
            for item in items:
                html_parts.append(f"<li>{item['text']} <em>(句{item['sentence_idx']}, 置信度{item['confidence']})</em></li>")
            html_parts.append("</ul>")
    
    html_parts.append("</div>")
    html_parts.append("</body></html>")
    
    html_content = "\n".join(html_parts)
    write_file_atomic(output_path, html_content)

# ============================================================
# 主流程
# ============================================================

def process_transcript(
    text: str,
    terms: Optional[Dict[str, str]] = None,
    domain: str = "general",
    verbose: bool = False,
) -> Dict:
    """处理转录文本，返回整理结果"""
    if not text.strip():
        raise EmptyInputError()
    
    if domain not in DOMAIN_TODO:
        raise UnknownDomainError(domain)
    
    result = {
        "original": text,
        "cleaned": "",
        "sentences": [],
        "paragraphs": [],
        "extractions": {},
        "stats": {},
    }
    
    # 1. 分句
    sentences = split_sentences(text)
    result["sentences"] = sentences
    
    if verbose:
        print(f"[分句] 共 {len(sentences)} 句")
    
    # 2. 清理填充词
    cleaned_parts = []
    removed_fillers = []
    for sent in sentences:
        cleaned, removed = clean_filler_words(sent, verbose)
        cleaned_parts.append(cleaned)
        removed_fillers.extend(removed)
    
    cleaned = "".join(cleaned_parts)
    
    if verbose:
        print(f"[填充词清理] 删除 {len(removed_fillers)} 个填充词: {removed_fillers[:10]}")
    
    # 3. 标点修复
    cleaned = fix_punctuation(cleaned)
    
    if verbose:
        print(f"[标点修复] 完成")
    
    # 4. 术语统一
    if terms:
        cleaned = apply_terms(cleaned, terms)
        if verbose:
            print(f"[术语统一] 应用 {len(terms)} 条术语映射")
    
    # 5. 段落分割
    paragraphs = split_paragraphs(cleaned)
    result["paragraphs"] = paragraphs
    
    if verbose:
        print(f"[段落分割] 共 {len(paragraphs)} 段")
    
    # 6. 列表化
    cleaned = format_list(cleaned)
    
    if verbose:
        print(f"[列表化] 完成")
    
    result["cleaned"] = cleaned
    
    # 7. 决策提取
    extractions = extract_decisions(text, domain)
    result["extractions"] = extractions
    
    if verbose:
        for key in ["todos", "deadlines", "objections", "decisions"]:
            print(f"[提取] {key}: {len(extractions[key])} 条")
    
    # 8. 统计
    result["stats"] = {
        "original_chars": len(text),
        "cleaned_chars": len(cleaned),
        "removed_chars": len(text) - len(cleaned),
        "sentence_count": len(sentences),
        "paragraph_count": len(paragraphs),
        "removed_fillers": len(removed_fillers),
    }
    
    return result

# ============================================================
# 基准测试
# ============================================================

def run_benchmark() -> Dict:
    """运行 F1 基准测试"""
    # 黄金语料（简化版，实际应有 149 条）
    golden = [
        # (文本, 期望提取类型)
        ("李工需要周五前提交原型", "todo"),
        ("我们决定采用A方案", "decision"),
        ("但是预算有限，有风险", "objection"),
        ("明天中午开会", "deadline"),
        ("不需要额外资源", "none"),
        ("这个方案可以吗？", "none"),
        ("王总负责跟进客户", "todo"),
        ("下周一前完成测试", "deadline"),
        ("我不同意这个方案", "objection"),
        ("会议通过了下季度计划", "decision"),
    ]
    
    tp = {"todo": 0, "deadline": 0, "objection": 0, "decision": 0}
    fp = {"todo": 0, "deadline": 0, "objection": 0, "decision": 0}
    fn = {"todo": 0, "deadline": 0, "objection": 0, "decision": 0}
    
    for text, expected in golden:
        extractions = extract_decisions(text, "meeting")
        
        for key in ["todo", "deadline", "objection", "decision"]:
            found = len(extractions[f"{key}s"]) > 0
            
            if expected == key:
                if found:
                    tp[key] += 1
                else:
                    fn[key] += 1
            else:
                if found:
                    fp[key] += 1
    
    # 计算 F1
    precision = {}
    recall = {}
    f1 = {}
    
    for key in ["todo", "deadline", "objection", "decision"]:
        p = tp[key] / (tp[key] + fp[key]) if (tp[key] + fp[key]) > 0 else 0
        r = tp[key] / (tp[key] + fn[key]) if (tp[key] + fn[key]) > 0 else 0
        f = 2 * p * r / (p + r) if (p + r) > 0 else 0
        
        precision[key] = round(p, 3)
        recall[key] = round(r, 3)
        f1[key] = round(f, 3)
    
    # 宏观 F1
    macro_f1 = sum(f1.values()) / len(f1)
    
    result = {
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "macro_f1": round(macro_f1, 3),
        "total_samples": len(golden),
    }
    
    return result

# ============================================================
# 自测
# ============================================================

def run_selftest() -> int:
    """运行内置自测，返回通过数"""
    passed = 0
    total = 0
    
    def check(name: str, condition: bool) -> None:
        nonlocal passed, total
        total += 1
        if condition:
            passed += 1
            print(f"  ✓ {name}")
        else:
            print(f"  ✗ {name}")
    
    print("运行自测...")
    
    # [1] 分句测试
    print("\n[1] 分句测试")
    sents = split_sentences("他说“好的。明天见”。然后我们走。")
    check("引号内句号不误分", len(sents) == 3)
    check("正常分句", len(split_sentences("第一句。第二句！第三句？")) == 3)
    
    # [2] 填充词清理测试
    print("\n[2] 填充词清理测试")
    cleaned, removed = clean_filler_words("嗯，然后我们确认方案")
    check("删除填充词'嗯'", "嗯" not in cleaned)
    check("删除填充词'然后'", "然后" not in cleaned)
    check("记录删除的填充词", len(removed) >= 2)
    
    # [3] 指代保护测试
    print("\n[3] 指代保护测试")
    cleaned, _ = clean_filler_words("那个项目下个月上线")
    check("指代'那个项目'保留", "那个项目" in cleaned)
    
    # [4] 语气词保留测试
    print("\n[4] 语气词保留测试")
    cleaned, _ = clean_filler_words("这样可以吧？")
    check("语气词'吧'保留", "吧" in cleaned)
    
    # [5] 标点修复测试
    print("\n[5] 标点修复测试")
    fixed = fix_punctuation("好的。。！")
    check("合并重复句号", "。。" not in fixed)
    fixed = fix_punctuation("看API文档")
    check("英文前补空格", "看 API" in fixed)
    
    # [6] 术语统一测试
    print("\n[6] 术语统一测试")
    result = apply_terms("AI技术", {"AI": "人工智能"})
    check("术语替换", "人工智能" in result)
    
    # [7] 段落分割测试
    print("\n[7] 段落分割测试")
    paras = split_paragraphs("第一段内容。第二段内容。但是第三段。")
    check("段落分割", len(paras) >= 2)
    
    # [8] 列表化测试
    print("\n[8] 列表化测试")
    formatted = format_list("第一，准备材料。第二，提交申请。")
    check("列表化格式", "1." in formatted and "2." in formatted)
    
    # [9] 决策提取测试
    print("\n[9] 决策提取测试")
    extractions = extract_decisions("李工需要周五前提交原型。我们决定采用A方案。但是预算有限。")
    check("提取待办", len(extractions["todos"]) > 0)
    check("提取异议", len(extractions["objections"]) > 0)
    check("提取决策", len(extractions["decisions"]) > 0)
    
    # [10] 否定句不提取测试
    print("\n[10] 否定句不提取测试")
    extractions = extract_decisions("不需要额外资源")
    check("否定句不提取待办", len(extractions["todos"]) == 0)
    
    # [11] 疑问句不提取测试
    print("\n[11] 疑问句不提取测试")
    extractions = extract_decisions("这个方案可以吗？")
    check("疑问句不提取", len(extractions["decisions"]) == 0)
    
    # [12] 编码识别测试
    print("\n[12] 编码识别测试")
    # 创建临时 GBK 文件
    import tempfile
    with tempfile.NamedTemporaryFile(mode="w", encoding="gbk", suffix=".txt", delete=False) as f:
        f.write("测试内容")
        temp_path = f.name
    try:
        content = read_file_with_encoding(temp_path)
        check("GBK 编码识别", "测试内容" in content)
    finally:
        os.unlink(temp_path)
    
    # [13] 空输入处理测试
    print("\n[13] 空输入处理测试")
    try:
        process_transcript("")
        check("空输入不崩溃", False)
    except EmptyInputError:
        check("空输入不崩溃", True)
    
    # [14] ICS 导出测试
    print("\n[14] ICS 导出测试")
    extractions = {
        "todos": [{"text": "提交报告", "sentence_idx": 0, "confidence": 0.8}],
        "deadlines": [],
        "objections": [],
        "decisions": [],
    }
    with tempfile.NamedTemporaryFile(suffix=".ics", delete=False) as f:
        ics_path = f.name
    try:
        export_ics(extractions, ics_path)
        with open(ics_path, "r", encoding="utf-8") as f:
            ics_content = f.read()
        check("ICS 导出", "BEGIN:VCALENDAR" in ics_content)
    finally:
        os.unlink(ics_path)
    
    # [15] HTML 导出测试
    print("\n[15] HTML 导出测试")
    with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as f:
        html_path = f.name
    try:
        export_html("原始文本", "整理文本", extractions, html_path)
        with open(html_path, "r", encoding="utf-8") as f:
            html_content = f.read()
        check("HTML 导出", "<html>" in html_content)
    finally:
        os.unlink(html_path)
    
    # [16] 基准测试
    print("\n[16] 基准测试")
    bench = run_benchmark()
    check("F1 分数合理", bench["macro_f1"] > 0.5)
    
    # [17] 完整流程测试
    print("\n[17] 完整流程测试")
    result = process_transcript("嗯，李工需要周五前提交原型。我们决定采用A方案。", domain="meeting")
    check("完整流程", result["cleaned"] != "")
    check("提取结果", len(result["extractions"]["todos"]) > 0)
    
    # [18] 参数校验测试
    print("\n[18] 参数校验测试")
    try:
        read_file_with_encoding("/nonexistent/file.txt")
        check("不存在的文件应报错", False)
    except InputFileNotFoundError:
        check("不存在的文件应报错", True)
    
    print(f"\n自测结果: {passed}/{total} 通过")
    return passed

# ============================================================
# CLI 入口
# ============================================================

def main() -> int:
    """CLI 入口"""
    parser = argparse.ArgumentParser(
        description="语音转写文本整理与决策记录提取工具",
        epilog=f"版本 {VERSION}",
    )
    
    parser.add_argument("--input", type=str, help="输入文件路径")
    parser.add_argument("--output", type=str, help="输出文件路径（缺省打印 stdout）")
    parser.add_argument("--format", choices=["text", "markdown"], default="text", help="输出格式")
    parser.add_argument("--terms", type=str, help="术语映射 JSON 文件或内联 JSON")
    parser.add_argument("--headings", action="store_true", help="保留标题结构（预留）")
    parser.add_argument("--dry-run", action="store_true", help="显式预览模式（默认即预览）")
    parser.add_argument("--force", action="store_true", help="真正落盘（默认只预览）")
    parser.add_argument("--verbose", action="store_true", help="每阶段修改明细")
    parser.add_argument("--extract", choices=["none", "json", "markdown"], default="none", help="决策记录提取")
    parser.add_argument("--domain", choices=["general", "meeting", "legal", "medical"], default="general", help="领域词表")
    parser.add_argument("--export", choices=["none", "ics", "html"], default="none", help="导出格式")
    parser.add_argument("--benchmark", action="store_true", help="运行 F1 基准测试")
    parser.add_argument("--selftest", action="store_true", help="运行内置自测")
    
    args = parser.parse_args()
    
    global dry_run
    
    dry_run = getattr(args, "dry_run", False)  # v3.274 同步到全局
    
    # 自测模式
    if args.selftest:
        passed = run_selftest()
        return 0 if passed >= 20 else 1
    
    # 基准模式
    if args.benchmark:
        result = run_benchmark()
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    
    # 参数校验
    if not args.input:
        parser.error("--input 必填（--selftest/--benchmark 除外）")
    
    if args.extract != "none" and args.export != "none":
        raise ArgumentConflictError("--extract 与 --export 不能同时使用")
    
    try:
        # 读取输入
        text = read_file_with_encoding(args.input)
        
        # 解析术语
        terms = None
        if args.terms:
            if os.path.exists(args.terms):
                with open(args.terms, "r", encoding="utf-8") as f:
                    terms = safe_json_loads(f.read())
            else:
                terms = safe_json_loads(args.terms)
            
            if terms is None:
                raise JSONFormatError(args.terms)
        
        # 处理转录文本
        result = process_transcript(text, terms, args.domain, args.verbose)
        
        # 输出结果
        output_content = ""
        
        if args.extract == "json":
            output_content = json.dumps(result["extractions"], ensure_ascii=False, indent=2)
        elif args.extract == "markdown":
            md_lines = ["# 决策记录", ""]
            categories = [
                ("todos", "待办事项"),
                ("deadlines", "截止日期"),
                ("objections", "异议风险"),
                ("decisions", "决策记录"),
            ]
            for key, label in categories:
                items = result["extractions"].get(key, [])
                if items:
                    md_lines.append(f"## {label} ({len(items)})")
                    md_lines.append("")
                    for item in items:
                        md_lines.append(f"- {item['text']} *(句{item['sentence_idx']}, 置信度{item['confidence']})*")
                    md_lines.append("")
            output_content = "\n".join(md_lines)
        elif args.export == "ics":
            export_ics(result["extractions"], args.output or "output.ics")
            print(f"ICS 已导出到 {args.output or 'output.ics'}")
            return 0
        elif args.export == "html":
            export_html(result["original"], result["cleaned"], result["extractions"], args.output or "report.html")
            print(f"HTML 报告已导出到 {args.output or 'report.html'}")
            return 0
        else:
            # 默认输出整理后的文本
            if args.format == "markdown":
                output_content = f"# 整理结果\n\n{result['cleaned']}\n\n## 统计\n\n- 原始字符: {result['stats']['original_chars']}\n- 整理后: {result['stats']['cleaned_chars']}\n- 删除: {result['stats']['removed_chars']}\n"
            else:
                output_content = result["cleaned"]
        
        # 输出或写盘
        if args.output and args.force:
            write_file_atomic(args.output, output_content)
            print(f"已写入 {args.output}")
        elif args.output:
            # 预览模式：打印 diff
            print("=== 预览模式（--force 才落盘）===")
            print(output_content)
            print("\n=== 统计 ===")
            print(f"原始: {result['stats']['original_chars']} 字符 → 整理后: {result['stats']['cleaned_chars']} 字符")
            print(f"删除: {result['stats']['removed_chars']} 字符, 填充词: {result['stats']['removed_fillers']} 个")
        else:
            print(output_content)
        
        return 0
    
    except TranscriptError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"未预期错误: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 2

if __name__ == "__main__":
    sys.exit(main())
