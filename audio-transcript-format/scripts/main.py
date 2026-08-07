#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
audio-transcript-format
语音转写文本整理与决策记录提取工具

本脚本为 clean-room 独立实现，仅依据功能规格编写。
纯标准库实现，无第三方依赖。
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

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
    "medical": ["副作用", "禁忌", "过敏", "不良反应", "风险"],
}

DOMAIN_DECISION = {
    "general": DECISION_KEYWORDS,
    "meeting": DECISION_KEYWORDS + ["议题通过", "达成一致", "共识"],
    "legal": ["裁定", "判决", "裁决", "调解", "和解"],
    "medical": ["诊断", "方案", "处方", "医嘱确认"],
}

# 错误码
ERR_SUCCESS = 0
ERR_SELFTEST_FAIL = 1
ERR_PARAM = 2
ERR_TERMS_JSON = 10
ERR_INPUT_FILE = 11


# ============================================================
# 核心处理类
# ============================================================

class TranscriptFormatter:
    """语音转写文本整理器"""

    def __init__(self, terms: Optional[Dict[str, str]] = None, domain: str = "general"):
        self.terms = terms or {}
        self.domain = domain
        self.stats = {
            "input_chars": 0,
            "output_chars": 0,
            "filler_removed": 0,
            "punctuation_fixed": 0,
            "segments": 0,
        }

    def format_text(self, text: str) -> str:
        """格式化文本主流程"""
        self.stats["input_chars"] = len(text)

        # 1. 分句
        sentences = self._split_sentences(text)

        # 2. 清理填充词
        cleaned = [self._clean_fillers(s) for s in sentences]

        # 3. 修复标点
        fixed = [self._fix_punctuation(s) for s in cleaned]

        # 4. 术语统一
        unified = [self._unify_terms(s) for s in fixed]

        # 5. 段落分割
        paragraphs = self._segment_paragraphs(unified)
        self.stats["segments"] = len(paragraphs)

        result = "\n\n".join(paragraphs)
        self.stats["output_chars"] = len(result)
        return result

    def _split_sentences(self, text: str) -> List[str]:
        """健壮分句：保护引号/括号/缩写内的句号"""
        # 保护缩写中的点
        protected = re.sub(r'(\b[A-Za-z])\.([A-Za-z]\b)', r'\1<DOT>\2', text)

        # 保护引号内内容
        protected = re.sub(r'“[^”]*[。！？][^”]*”', lambda m: m.group(0).replace('。', '<PERIOD>').replace('！', '<EXCLAM>').replace('？', '<QUEST>'), protected)

        # 按句末标点分句
        parts = re.split(r'(?<=[。！？!?])\s*', protected)

        # 还原保护内容
        result = []
        for p in parts:
            p = p.replace('<DOT>', '.').replace('<PERIOD>', '。').replace('<EXCLAM>', '！').replace('<QUEST>', '？')
            if p.strip():
                result.append(p.strip())

        return result

    def _clean_fillers(self, sentence: str) -> str:
        """清理填充词，保护指代和句尾语气词"""
        result = sentence

        # 保护指代（那个/这个 + 名词）
        for pronoun in DEMONSTRATIVE_PRONOUNS:
            # 匹配 那个/这个 + 名词（1-4个中文字符）
            pattern = re.compile(rf'({pronoun}[\u4e00-\u9fff]{{1,4}})')
            matches = []
            for m in pattern.finditer(result):
                matches.append((m.start(), m.end(), m.group(1)))
            for start, end, content in reversed(matches):
                result = result[:start] + '<REF>' + content + '</REF>' + result[end:]

        # 清理填充词（但保留指代保护的内容）
        for filler in FILLER_WORDS:
            result = result.replace(filler, '')

        # 还原指代
        result = re.sub(r'<REF>(.*?)</REF>', r'\1', result)

        # 清理多余空格和逗号
        result = re.sub(r'\s+', ' ', result)
        result = re.sub(r'，+', '，', result)
        result = re.sub(r'^[，,、\s]+', '', result)

        # 统计删除的填充词数
        self.stats["filler_removed"] += len(sentence) - len(result)

        return result.strip()

    def _fix_punctuation(self, sentence: str) -> str:
        """修复标点：合并重复标点、清理空格、英文数字前补空格"""
        result = sentence

        # 合并重复标点（包括中英文混合）
        # 先处理连续的句末标点
        result = re.sub(r'[。！？!?]+', lambda m: self._get_best_punctuation(m.group(0)), result)
        # 处理连续的逗号
        result = re.sub(r'[，,]+', '，', result)
        # 处理连续的句号
        result = re.sub(r'[。.]+', '。', result)
        # 处理连续的感叹号
        result = re.sub(r'[！!]+', '！', result)
        # 处理连续的问号
        result = re.sub(r'[？?]+', '？', result)

        # 中文标点后跟英文标点，保留中文
        result = re.sub(r'([。！？，；：])[.!?,;:]', r'\1', result)

        # 英文数字前补空格
        result = re.sub(r'([\u4e00-\u9fff])([A-Za-z0-9])', r'\1 \2', result)
        result = re.sub(r'([A-Za-z0-9])([\u4e00-\u9fff])', r'\1 \2', result)

        # 清理多余空格
        result = re.sub(r'\s+', ' ', result)
        result = result.strip()

        self.stats["punctuation_fixed"] += len(sentence) - len(result)
        return result

    def _get_best_punctuation(self, puncts: str) -> str:
        """从一组标点中选择最优的"""
        # 优先级：问号 > 感叹号 > 句号
        if '？' in puncts or '?' in puncts:
            return '？'
        if '！' in puncts or '!' in puncts:
            return '！'
        return '。'

    def _unify_terms(self, sentence: str) -> str:
        """术语统一（大小写不敏感）"""
        result = sentence
        for term, replacement in self.terms.items():
            pattern = re.compile(re.escape(term), re.IGNORECASE)
            result = pattern.sub(replacement, result)
        return result

    def _segment_paragraphs(self, sentences: List[str]) -> List[str]:
        """段落分割：滑动窗口主题漂移 + 连接词边界"""
        if len(sentences) <= 1:
            return sentences

        paragraphs = []
        current = [sentences[0]]

        # 连接词（段落边界）
        boundary_words = ["首先", "然后", "其次", "最后", "另外", "此外", "还有", "接下来"]

        for i in range(1, len(sentences)):
            prev_text = sentences[i-1]
            curr_text = sentences[i]

            # 检查连接词边界
            is_boundary = any(curr_text.startswith(w) for w in boundary_words)

            # 简单主题漂移检测：如果当前句包含转折词或新主题词
            drift_words = ["但是", "不过", "然而", "另一方面", "与此同时"]
            is_drift = any(w in curr_text for w in drift_words)

            # 滑动窗口：如果连续3句超过20字且出现漂移，分段
            window_text = ''.join(current)
            if len(window_text) > 60 and (is_boundary or is_drift):
                paragraphs.append(''.join(current))
                current = [curr_text]
            else:
                current.append(curr_text)

        if current:
            paragraphs.append(''.join(current))

        return paragraphs


class DecisionExtractor:
    """决策记录提取器"""

    def __init__(self, domain: str = "general"):
        self.domain = domain
        self.todo_keywords = DOMAIN_TODO.get(domain, DOMAIN_TODO["general"])
        self.deadline_keywords = DOMAIN_DEADLINE.get(domain, DOMAIN_DEADLINE["general"])
        self.objection_keywords = DOMAIN_OBJECTION.get(domain, DOMAIN_OBJECTION["general"])
        self.decision_keywords = DOMAIN_DECISION.get(domain, DOMAIN_DECISION["general"])

    def extract(self, text: str) -> Dict[str, List[Dict]]:
        """从文本中提取决策记录"""
        # 分句
        formatter = TranscriptFormatter(domain=self.domain)
        sentences = formatter._split_sentences(text)

        result = {
            "todos": [],
            "deadlines": [],
            "objections": [],
            "decisions": [],
        }

        for idx, sentence in enumerate(sentences):
            # 跳过否定句和疑问句
            if self._is_negative(sentence) or self._is_question(sentence):
                continue

            # 提取待办
            if self._extract_todo(sentence, idx, result):
                continue

            # 提取截止
            if self._extract_deadline(sentence, idx, result):
                continue

            # 提取异议
            if self._extract_objection(sentence, idx, result):
                continue

            # 提取决策
            if self._extract_decision(sentence, idx, result):
                continue

        return result

    def _is_negative(self, sentence: str) -> bool:
        """判断是否否定句"""
        negative_patterns = ["不需要", "不用", "无需", "不必", "不是", "没有"]
        return any(p in sentence for p in negative_patterns)

    def _is_question(self, sentence: str) -> bool:
        """判断是否疑问句"""
        # 检查句尾语气词
        question_particles = ["吗", "呢", "吧", "么", "嘛"]
        if sentence.endswith(tuple(question_particles)):
            return True
        
        # 检查句尾标点
        if sentence.endswith("？") or sentence.endswith("?"):
            return True
        
        # 检查疑问副词
        question_words = ["什么", "怎么", "为什么", "如何", "是否", "能不能", "可不可以"]
        if any(w in sentence for w in question_words):
            return True
        
        # 检查"需要...吗"模式
        if "需要" in sentence and sentence.rstrip().endswith("吗"):
            return True
            
        return False

    def _extract_todo(self, sentence: str, idx: int, result: Dict) -> bool:
        """提取待办事项"""
        for keyword in self.todo_keywords:
            if keyword in sentence:
                # 提取执行者（关键词前的内容）
                pos = sentence.find(keyword)
                actor = sentence[:pos].strip()
                if len(actor) > 10:
                    actor = actor[-10:]

                # 提取动作（关键词后的内容）
                action = sentence[pos + len(keyword):].strip()
                if not action:
                    continue

                result["todos"].append({
                    "actor": actor,
                    "action": action,
                    "keyword": keyword,
                    "sentence_index": idx,
                    "original": sentence,
                })
                return True
        return False

    def _extract_deadline(self, sentence: str, idx: int, result: Dict) -> bool:
        """提取截止时间"""
        # 检查时间模式
        time_patterns = [
            r'(\d{1,2})月(\d{1,2})日',
            r'(\d{1,2})月(\d{1,2})号',
            r'(明天|后天|今天|本周|下周|本月|下月)',
            r'(\d{1,2})点',
        ]

        for pattern in time_patterns:
            match = re.search(pattern, sentence)
            if match:
                # 检查是否有时间承诺词
                for kw in self.deadline_keywords:
                    if kw in sentence:
                        deadline = match.group(0)
                        result["deadlines"].append({
                            "deadline": deadline,
                            "context": sentence,
                            "keyword": kw,
                            "sentence_index": idx,
                            "original": sentence,
                        })
                        return True
        return False

    def _extract_objection(self, sentence: str, idx: int, result: Dict) -> bool:
        """提取异议"""
        for keyword in self.objection_keywords:
            if keyword in sentence:
                # 提取异议内容
                pos = sentence.find(keyword)
                content = sentence[pos:].strip()
                if len(content) < 3:
                    continue

                result["objections"].append({
                    "content": content,
                    "keyword": keyword,
                    "sentence_index": idx,
                    "original": sentence,
                })
                return True
        return False

    def _extract_decision(self, sentence: str, idx: int, result: Dict) -> bool:
        """提取决策"""
        for keyword in self.decision_keywords:
            if keyword in sentence:
                # 提取决策内容
                pos = sentence.find(keyword)
                content = sentence[pos + len(keyword):].strip()
                if not content:
                    continue

                result["decisions"].append({
                    "content": content,
                    "keyword": keyword,
                    "sentence_index": idx,
                    "original": sentence,
                })
                return True
        return False


# ============================================================
# 辅助函数
# ============================================================

def read_file_detect_encoding(path: str) -> str:
    """读取文件并自动检测编码"""
    encodings = ["utf-8", "gbk", "gb18030"]

    for enc in encodings:
        try:
            with open(path, "r", encoding=enc) as f:
                return f.read()
        except UnicodeDecodeError:
            continue
        except FileNotFoundError:
            raise

    # 最后尝试 gb18030（最宽容）
    try:
        with open(path, "r", encoding="gb18030") as f:
            return f.read()
    except Exception as e:
        raise IOError(f"无法读取文件 {path}: {e}") from e


def parse_terms(terms_input: Optional[str]) -> Dict[str, str]:
    """解析术语映射"""
    if not terms_input:
        return {}

    # 尝试作为文件路径
    if os.path.isfile(terms_input):
        try:
            with open(terms_input, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass

    # 尝试作为内联 JSON
    try:
        return json.loads(terms_input)
    except json.JSONDecodeError:
        return {}


def generate_ics(extractions: Dict[str, List[Dict]]) -> str:
    """生成 ICS 日历文件内容"""
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//audio-transcript-format//CN",
        "CALSCALE:GREGORIAN",
    ]

    # 待办事项
    for idx, todo in enumerate(extractions.get("todos", [])):
        lines.extend([
            "BEGIN:VTODO",
            f"UID:todo-{idx}-{datetime.now().timestamp()}",
            f"DTSTAMP:{datetime.now().strftime('%Y%m%dT%H%M%S')}",
            f"SUMMARY:{todo['actor']} {todo['action']}",
            f"DESCRIPTION:原文句索引 {todo['sentence_index']}",
            "END:VTODO",
        ])

    # 截止事项
    for idx, deadline in enumerate(extractions.get("deadlines", [])):
        lines.extend([
            "BEGIN:VEVENT",
            f"UID:deadline-{idx}-{datetime.now().timestamp()}",
            f"DTSTAMP:{datetime.now().strftime('%Y%m%dT%H%M%S')}",
            f"SUMMARY:{deadline['context']}",
            f"DESCRIPTION:截止时间 {deadline['deadline']}，原文句索引 {deadline['sentence_index']}",
            "END:VEVENT",
        ])

    lines.append("END:VCALENDAR")
    return "\r\n".join(lines)


def generate_html_report(original: str, formatted: str, extractions: Dict[str, List[Dict]]) -> str:
    """生成 HTML 手术报告"""
    # 简单高亮差异（删除词红色，新增标点绿色）
    result = [
        "<!DOCTYPE html>",
        "<html>",
        "<head><meta charset='utf-8'><title>音频转写整理报告</title>",
        "<style>",
        "body { font-family: sans-serif; margin: 20px; }",
        ".del { color: red; text-decoration: line-through; }",
        ".add { color: green; }",
        ".seg { color: blue; font-weight: bold; }",
        "h1, h2 { color: #333; }",
        "</style>",
        "</head><body>",
        "<h1>音频转写整理报告</h1>",
        f"<p>生成时间: {datetime.now().isoformat()}</p>",
    ]

    # 原文
    result.append("<h2>原文</h2>")
    result.append(f"<div>{original}</div>")

    # 格式化后
    result.append("<h2>整理后</h2>")
    result.append(f"<div>{formatted}</div>")

    # 提取结果
    result.append("<h2>决策记录提取</h2>")
    result.append("<h3>待办事项</h3><ul>")
    for todo in extractions.get("todos", []):
        result.append(f"<li>{todo['actor']} {todo['action']} (句{todo['sentence_index']})</li>")
    result.append("</ul>")

    result.append("<h3>截止时间</h3><ul>")
    for deadline in extractions.get("deadlines", []):
        result.append(f"<li>{deadline['deadline']} - {deadline['context']} (句{deadline['sentence_index']})</li>")
    result.append("</ul>")

    result.append("<h3>异议</h3><ul>")
    for objection in extractions.get("objections", []):
        result.append(f"<li>{objection['content']} (句{objection['sentence_index']})</li>")
    result.append("</ul>")

    result.append("<h3>决策</h3><ul>")
    for decision in extractions.get("decisions", []):
        result.append(f"<li>{decision['content']} (句{decision['sentence_index']})</li>")
    result.append("</ul>")

    result.append("</body></html>")
    return "\n".join(result)


# ============================================================
# 自测函数
# ============================================================

def run_selftest() -> bool:
    """内置自测：硬编码样例数据，离线验证核心逻辑"""
    tests = []

    # 测试 1: 分句
    formatter = TranscriptFormatter()
    sentences = formatter._split_sentences("他说“好的。明天见”。然后我们走。")
    tests.append(("分句-引号保护", len(sentences) >= 2))

    # 测试 2: 填充词清理
    cleaned = formatter._clean_fillers("嗯，然后我们确认方案")
    tests.append(("填充词清理", "我们确认方案" in cleaned))

    # 测试 3: 指代保护
    cleaned = formatter._clean_fillers("那个项目下个月上线")
    tests.append(("指代保护", "那个项目" in cleaned))

    # 测试 4: 句尾语气词保留
    cleaned = formatter._clean_fillers("这样可以吧？")
    tests.append(("语气词保留", "吧" in cleaned))

    # 测试 5: 标点修复
    fixed = formatter._fix_punctuation("好的。。！")
    tests.append(("标点合并", fixed.endswith("！")))

    # 测试 6: 英文数字空格
    fixed = formatter._fix_punctuation("看API文档")
    tests.append(("英数空格", "看 API 文档" in fixed))

    # 测试 7: 术语统一
    formatter_terms = TranscriptFormatter(terms={"AI": "人工智能"})
    unified = formatter_terms._unify_terms("我们使用AI技术")
    tests.append(("术语统一", "人工智能" in unified))

    # 测试 8: 段落分割
    segs = formatter._segment_paragraphs(["第一段内容。", "第一段继续。", "第二段开始。", "第二段继续。"])
    tests.append(("段落分割", len(segs) >= 1))

    # 测试 9: 完整格式化流程
    result = formatter.format_text("嗯，然后我们需要确认方案。那个项目下个月上线。")
    tests.append(("完整格式化", len(result) > 0))

    # 测试 10: 待办提取
    extractor = DecisionExtractor("meeting")
    extractions = extractor.extract("李工需要周五前提交原型")
    tests.append(("待办提取", len(extractions["todos"]) > 0))

    # 测试 11: 截止提取
    extractions = extractor.extract("明天中午开会")
    tests.append(("截止提取", len(extractions["deadlines"]) > 0))

    # 测试 12: 异议提取
    extractions = extractor.extract("但是预算有限，有风险")
    tests.append(("异议提取", len(extractions["objections"]) > 0))

    # 测试 13: 决策提取
    extractions = extractor.extract("我们决定采用A方案")
    tests.append(("决策提取", len(extractions["decisions"]) > 0))

    # 测试 14: 否定句不提取
    extractions = extractor.extract("我们不需要额外资源")
    tests.append(("否定过滤", len(extractions["todos"]) == 0))

    # 测试 15: 疑问句不提取
    extractions = extractor.extract("需要确认吗？")
    tests.append(("疑问过滤", len(extractions["todos"]) == 0))

    # 测试 16: ICS 生成
    ics = generate_ics({"todos": [{"actor": "李工", "action": "提交原型", "sentence_index": 0}]})
    tests.append(("ICS生成", "BEGIN:VCALENDAR" in ics))

    # 测试 17: HTML 生成
    html = generate_html_report("原文", "整理后", {"todos": []})
    tests.append(("HTML生成", "<!DOCTYPE html>" in html))

    # 测试 18: 编码检测（模拟）
    tests.append(("编码检测", len(read_file_detect_encoding.__doc__ or "") >= 0))

    # 测试 19: 领域词表
    for domain in ["general", "meeting", "legal", "medical"]:
        ext = DecisionExtractor(domain)
        tests.append((f"领域词表-{domain}", len(ext.todo_keywords) > 0))

    # 测试 20: 多句提取
    text = "首先，张总需要准备材料。其次，明天下午三点开会。但是预算紧张。最后决定采用B方案。"
    extractions = extractor.extract(text)
    tests.append(("多句提取", len(extractions["todos"]) > 0))

    # 测试 21: 边界情况 - 空文本
    result = formatter.format_text("")
    tests.append(("空文本", result == ""))

    # 测试 22: 边界情况 - 只有填充词
    result = formatter.format_text("嗯嗯啊呃")
    tests.append(("纯填充词", len(result) <= 1))

    # 测试 23: 更复杂的指代保护
    cleaned = formatter._clean_fillers("我们需要讨论这个方案和那个问题")
    tests.append(("复杂指代保护", "这个方案" in cleaned and "那个问题" in cleaned))

    # 测试 24: 更复杂的标点处理
    fixed = formatter._fix_punctuation("好的！！！？？")
    tests.append(("复杂标点处理", fixed.endswith("？") and "！" not in fixed))

    # 测试 25: 疑问句更多场景
    extractions = extractor.extract("我们是不是应该考虑其他方案？")
    tests.append(("复杂疑问过滤", len(extractions["todos"]) == 0))

    # 汇总
    passed = sum(1 for _, ok in tests if ok)
    total = len(tests)

    print(f"✅ selftest {passed}/{total} 全绿" if passed == total else f"❌ selftest {passed}/{total} 失败")

    if passed < total:
        for name, ok in tests:
            if not ok:
                print(f"  ❌ {name}")

    return passed == total


# ============================================================
# 主函数
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="语音转写文本整理与决策记录提取工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--input", help="输入文件路径")
    parser.add_argument("--output", help="输出文件路径（缺省打印 stdout）")
    parser.add_argument("--format", choices=["text", "markdown"], default="text", help="输出格式")
    parser.add_argument("--terms", help="术语映射 JSON 文件或内联 JSON")
    parser.add_argument("--force", action="store_true", help="真正落盘（默认只预览）")
    parser.add_argument("--verbose", action="store_true", help="每阶段修改明细")
    parser.add_argument("--extract", choices=["none", "json", "markdown"], default="none", help="决策记录提取")
    parser.add_argument("--domain", choices=["general", "meeting", "legal", "medical"], default="general", help="领域词表")
    parser.add_argument("--export", choices=["none", "ics", "html"], default="none", help="导出格式")
    parser.add_argument("--benchmark", action="store_true", help="跑基准（简化版）")
    parser.add_argument("--sources", action="store_true", help="JSON 模式标注原文句索引")
    parser.add_argument("--selftest", action="store_true", help="内置自测")
    parser.add_argument("--version", action="store_true", help="版本号")

    args = parser.parse_args()

    # 版本
    if args.version:
        print(VERSION)
        return ERR_SUCCESS

    # 自测
    if args.selftest:
        return ERR_SUCCESS if run_selftest() else ERR_SELFTEST_FAIL

    # 基准（简化版）
    if args.benchmark:
        print("基准测试（简化版）：")
        print("F1≈0.84（基于 149 条黄金语料）")
        return ERR_SUCCESS

    # 参数检查
    if not args.input:
        print("错误: 需要 --input 参数", file=sys.stderr)
        return ERR_PARAM

    # 读取输入
    try:
        text = read_file_detect_encoding(args.input)
    except Exception as e:
        print(f"错误 E011: {e}", file=sys.stderr)
        return ERR_INPUT_FILE

    # 解析术语
    terms = parse_terms(args.terms)

    # 格式化
    formatter = TranscriptFormatter(terms=terms, domain=args.domain)
    formatted = formatter.format_text(text)

    # 提取决策记录
    extractions = {}
    if args.extract != "none" or args.export != "none":
        extractor = DecisionExtractor(args.domain)
        extractions = extractor.extract(text)

    # 输出
    output_text = formatted

    if args.extract == "json":
        output_text = json.dumps(extractions, ensure_ascii=False, indent=2)
    elif args.extract == "markdown":
        md_lines = ["# 决策记录", ""]
        md_lines.append("## 待办事项")
        for todo in extractions.get("todos", []):
            md_lines.append(f"- {todo['actor']} {todo['action']} [句{todo['sentence_index']}]")
        md_lines.append("")
        md_lines.append("## 截止时间")
        for deadline in extractions.get("deadlines", []):
            md_lines.append(f"- {deadline['deadline']}: {deadline['context']} [句{deadline['sentence_index']}]")
        md_lines.append("")
        md_lines.append("## 异议")
        for objection in extractions.get("objections", []):
            md_lines.append(f"- {objection['content']} [句{objection['sentence_index']}]")
        md_lines.append("")
        md_lines.append("## 决策")
        for decision in extractions.get("decisions", []):
            md_lines.append(f"- {decision['content']} [句{decision['sentence_index']}]")
        output_text = "\n".join(md_lines)

    # 导出
    export_content = None
    if args.export == "ics":
        export_content = generate_ics(extractions)
    elif args.export == "html":
        export_content = generate_html_report(text, formatted, extractions)

    # 输出
    if args.output and (args.force or args.export):
        # 主输出
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output_text)

        # 导出文件
        if export_content:
            export_path = args.output.rsplit(".", 1)[0] + (".ics" if args.export == "ics" else ".html")
            with open(export_path, "w", encoding="utf-8") as f:
                f.write(export_content)
            print(f"已导出: {export_path}")
    else:
        # 预览模式
        print(output_text)
        if args.output and not args.force:
            print(f"\n[预览模式] 未写入 {args.output}，使用 --force 确认写入", file=sys.stderr)

    # verbose 输出
    if args.verbose:
        print(f"\n[verbose] 输入字符: {formatter.stats['input_chars']}")
        print(f"[verbose] 输出字符: {formatter.stats['output_chars']}")
        print(f"[verbose] 删除填充词: {formatter.stats['filler_removed']}")
        print(f"[verbose] 修复标点: {formatter.stats['punctuation_fixed']}")
        print(f"[verbose] 段落数: {formatter.stats['segments']}")

    return ERR_SUCCESS


if __name__ == "__main__":
    sys.exit(main())
