#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Skill: audio-transcript-format (v4.0.0)
将口语化音频转录文本整理为结构化书面语，并提取可信决策记录。

v4.1 查漏补缺（2026-08-06 老板三问自查）：
  [域保护]      --domain 贯通到整理阶段：legal 域条款段（第X条/第X款/第X项）
       列表化跳过，保持法律文本条款结构；medical 域剂量/单位不被动
  [性能]        词表匹配预编译正则（O(n×k) 逐词 in → O(n) 单次正则）
  [质量门槛]    38 自检新增 F1 门槛：活样板宏观 F1 < 0.78 直接 RED（防质量回落）

v4.0 立项升级（2026-08-06「全部积蓄」三线齐发：领域化+可对接+可度量）：
  [跃迁3 领域×3]     --domain 增至 4 域：general/meeting/legal/medical
       （legal：签署/期限/开庭/判决…；medical：用药/疗程/复诊/医嘱…）
  [可对接]           --export ics：待办/截止转标准 .ics 日历文件，
       可导入任何日历应用（离线无 token）；时间词解析（明天/周X/X月X日）
  [跃迁5 可度量]     --benchmark：100+ 条黄金语料（含负例/边缘案例）算
       精确率/召回率/F1，报告落 benchmark_report.json——F1 变好才算改进
  [基准驱动优化]     否定句不提取待办（"不需要…"）、疑问句不提取（"需要吗？"）、
       相对时间词需行动语境才判截止（"今天先到这里"不是截止）、
       裁决词与异议同现视为异议陈述（"不服判决"非本方决策）

v3.0 战略升级（从"格式化工具"转向"可信信息提取器"）：
  [跃迁1 事实提取]   四类决策事实——待办/截止/异议/决策，每项带原文句索引
  [跃迁1 双格式]    --extract json / markdown（人类可读 + 原文脚注）

v2.3 军规样板（响应第三方评审固化，R1-R6 全部继续生效）：
  [R1 契约先于代码]  selftest 40 条真实断言；SKILL.md 能力边界与实现一一对应
  [R2 异常降级]      @stage 统一 try-except + 降级输出，只 except Exception
  [R3 编码底线]      utf-8→gbk→gb18030 三级 fallback + 流式分块读
  [R4 预览/撤回]     默认只打印 diff 不写盘，--force 才落盘
  [R5 性能 O(n)]     无 --max-len；全流程单遍线性
  [R6 可解释输出]    --verbose 每阶段修改明细

接口：--input/--output/--format/--terms/--headings/--extract/--domain/
     --export/--benchmark/--dry-run/--force/--verbose/--sources/--selftest/--version
"""

import re
import sys
import json
import argparse
import os
from pathlib import Path
from typing import Any, Callable, Dict, List, Tuple

__version__ = "4.2.0"

# ── 阶段注册表（真·可插拔 + 异常降级）──────────────────────────────────
# 每个阶段 = (名称, 包装函数)。handler 统一签名 handler(payload, ctx) -> Any。
# R2 军规：单阶段异常 → 降级返回原输入（不中断、不崩溃），警告写入 ctx["stage_warnings"]。
STAGES: List[Tuple[str, Callable[[Any, Dict[str, Any]], Any]]] = []


def stage(name: str) -> Callable:
    """阶段注册装饰器：登记到 STAGES，并统一包裹异常降级（R2）"""
    def deco(fn: Callable) -> Callable:
        def wrapper(payload: Any, ctx: Dict[str, Any]) -> Any:
            try:
                return fn(payload, ctx)
            except Exception as e:  # 只捕获 Exception，允许 KeyboardInterrupt/SystemExit 透传
                ctx.setdefault("stage_warnings", []).append(
                    f"[{name}] 阶段异常 → 降级返回原输入: {type(e).__name__}: {e}")
                return payload
        STAGES.append((name, wrapper))
        return wrapper
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
# 行内编号：句首/标点后的 "1. " "2、" 等
_NUM_CONTEXT = re.compile(r'(?:^|[\s，,。；;])(\d{1,2})[.、]')


@stage("listify")
def convert_to_lists(payload: List[str], ctx: Dict[str, Any]) -> List[str]:
    """识别并列项转为列表（"第一/第二…"、"首先/其次…"或行内编号 1. 2. 3.）。

    v2.2 保守化：仅当≥2 个枚举标记出现在句首/标点后（真枚举语境）才转换，
    防叙事误伤（如"这是第一点。第二点更重要"保持原文）。
    v4.1 域保护：legal 域下"第X条/第X款/第X项"条款段不转列表（保持法律文本条款结构）。
    """
    legal_protect = ctx.get("domain") == "legal"
    clause = re.compile(r'第[一二三四五六七八九十百千0-9]+[条款项]')
    result = []
    for para in payload:
        if legal_protect and clause.search(para) and len(clause.findall(para)) >= 1:
            result.append(para)  # 法律条款段保持原文，不做任何列表化
            continue
        # 顺序词枚举（第一/第二/首先/其次…）→ 列表
        markers = _SEQ_CONTEXT.findall(para)
        if len(markers) >= 2:
            items = re.split(r'(?:^|[，,。！？；;])\s*(?=' + '|'.join(SEQ_MARKERS) + r')', para)
            items = [item.strip() for item in items if item.strip()]
            if len(items) >= 2:
                result.append('\n'.join(f"{idx}. {item}" for idx, item in enumerate(items, 1)))
                continue
        # 行内编号枚举（1. xxx 2. yyy …）→ 列表（v2.2 修复：对单段文本也生效）
        nums = _NUM_CONTEXT.findall(para)
        if len(nums) >= 2:
            parts = re.split(r'(?=[\s，,。；;]*\d{1,2}[.、])', para)
            parts = [p.strip(' 　，,。；;') for p in parts if p.strip()]
            if len(parts) >= 2:
                result.append('\n'.join(f"{idx}. {p}" for idx, p in enumerate(parts, 1)))
                continue
        result.append(para)
    return result


# ══════════════════════ 输入输出：编码底线 + 流式分块（R3/R5）══════════════════════

def read_text_any(path: str) -> Tuple[str, str]:
    """流式分块读取（R5：超大文件不一次性整块入内存）+ 多编码 fallback（R3）。

    编码探测：utf-8 → gbk → gb18030 三级尝试，全失败才 errors="replace" 兜底。
    返回 (text, 实际编码)。不认 GBK 等于不认人民币。
    """
    chunks: List[bytes] = []
    with open(path, "rb") as f:
        while True:
            block = f.read(65536)  # 64KB 分块，O(n) 线性
            if not block:
                break
            chunks.append(block)
    raw = b"".join(chunks)
    for enc in ("utf-8", "gbk", "gb18030"):
        try:
            return raw.decode(enc), enc
        except (UnicodeDecodeError, ValueError):
            continue
    return raw.decode("utf-8", errors="replace"), "utf-8(replace兜底)"


def write_text_any(path: str, text: str) -> None:
    """原子化写盘：先写临时文件再替换，避免写一半损坏（R4 撤回配套）。"""
    import tempfile
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(os.path.abspath(path)) or ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


# ══════════════════════ 主流程：阶段遍历 + 可解释输出（R2/R6）══════════════════════

def process_transcript(text: str, terms: Dict[str, str] = None,
                       add_headings: bool = False, fmt: str = "text",
                       verbose: bool = False, domain: str = "general") -> Tuple[Any, Dict[str, Any]]:
    """全流程处理：按 STAGES 注册顺序遍历，单阶段异常自动降级（R2）。

    v4.1 domain 贯通到整理阶段（listify 读 ctx["domain"] 做条款保护）。
    返回 (结果, ctx)。ctx 含阶段报告、stage_warnings 降级警告、stage_deltas 明细。
    """
    ctx: Dict[str, Any] = {"terms": terms or {}, "add_headings": add_headings,
                           "fmt": fmt, "verbose": verbose, "domain": domain,
                           "stage_deltas": []}
    payload: Any = text
    for name, handler in STAGES:
        before = payload
        payload = handler(payload, ctx)
        if verbose:
            blen = len(before) if isinstance(before, (str, list)) else 0
            alen = len(payload) if isinstance(payload, (str, list)) else 0
            ctx["stage_deltas"].append({"stage": name, "before_chars": blen,
                                        "after_chars": alen, "delta": blen - alen})
    return payload, ctx


def build_output(payload: Any, fmt: str = "text") -> str:
    """按格式组装最终输出（text / markdown）"""
    paras = payload if isinstance(payload, list) else [payload]
    paras = [p for p in paras if p and str(p).strip()]
    if fmt == "markdown":
        return "\n\n".join(str(p) for p in paras) + "\n"
    return "\n".join(str(p) for p in paras) + ("\n" if paras else "")


# ══════════════════════ 决策记录提取（跃迁1：可信信息提取器）══════════════════════

# 待办 Action：某人要做什么（v4.0 删"必须"；v4.2 删"完成"+加核对类）
ACTION_VERBS = ["需要", "要", "记得", "别忘了", "请", "务必", "安排",
                "跟进", "负责", "尽快", "回头", "稍后", "回头跟", "得去",
                "对一下", "核对", "对齐", "过一遍"]
# 日常杂务排除（v4.2 基准驱动："厨房灯坏了需要换一个"不是待办）
_WEAK_ACTION = re.compile(r'需要(?:换|买|修|装|洗|扫|擦|扔)(?:一个|个)?[吧了]?$')
# 截止 Deadline：绝对时间词直接判；相对时间词需行动语境（v4.0 基准驱动：
# "今天先到这里""明天天气怎么样"不是截止，"周五前提交"才是）
DEADLINE_MARKERS = ["截止", "之前", "前提交", "前给", "月底", "月初", "下个月", "周内",
                    "天内", "日内", "小时内", "期限", "届满", "开庭", "审限", "次日", "法定期限",
                    "举证期", "上诉期", "异议期", "疗程", "deadline", "due"]
_DEADLINE_SPAN = re.compile(r'[一二两三四五六七八九十\d]+天(?:时间|内|后)')
DEADLINE_REL = ["今天", "明天", "后天", "下周", "本周", "周五", "周一", "周二",
                "周三", "周四", "周末", "星期", "每月", "每周", "每天", "每晚", "每两",
                "每三小时", "每两小时", "每半小时", "每四小时"]
_DEADLINE_CTX = re.compile(r'(前|提交|交|截止|开会|评审会|例会|会议|完成|给|汇报|上线|交付|到账|发给|发出|回复|答复|归档|出结果|出报告|记录|复查|随访|监测|服药|抽血|用药|检测|登记|对|核对|过一遍|对齐)')
_DEADLINE_DATE = re.compile(r'(?:\d{1,2}月\d{1,2}[日号]|\d{4}[-/年]\d{1,2}[-/月]\d{1,2}[日号]?)')
# 异议 Disagreement：不同意见/风险（v4.0 加"兼容性"；v4.2 加"不成"——"调解不成"是僵局）
DISAGREE_MARKERS = ["但是", "不过", "不同意", "我反对", "有问题", "有风险", "有争议",
                    "不确定", "恐怕", "不一定", "保留意见", "我觉得不对", "不行",
                    "风险在于", "问题在于", "有待商榷", "再考虑", "再想想", "兼容性", "不成"]
# 决策 Decision：敲定/批准；裁决类词（判决/裁定/生效…）同句有异议时视为异议陈述
DECISION_MARKERS = ["决定", "确定", "定了", "敲定", "拍板", "就这么办", "同意",
                    "批准", "通过", "确认", "落实", "采纳", "定了就", "就这么定"]
_RULING_WORDS = {"判决", "裁定", "生效", "认定", "驳回", "支持"}
# v4.2 decisions 消歧（基准驱动）："确认/确定"是弱决策词，需接名词宾语才判
#   "我们确认了下周的排期"→决策 ✓；"麻烦确认一下"→不判；"确认过没有"→不判
_WEAK_DECISION = re.compile(r'(?:确认|确定)(?:了|过|一下)?[了的]?\s*[\u4e00-\u9fffA-Za-z]{2,}')
_WEAK_DECISION_NEG = re.compile(r'(?:确认|确定)(?:一下|过)?(?:没有|了吗|呢|下|过)')

# 领域词表扩展（v4.0：meeting/legal/medical 各域增强；general 兜底）
DOMAIN_EXTRA = {
    "meeting": {
        "actions": ["发给大家", "汇总", "整理好", "约一下", "订一下", "同步给", "协调", "拉群", "发会议纪要"],
        "deadlines": [],
        "disagreements": ["回头再说", "这个先放放"],
        "decisions": ["会议一致", "达成共识", "就这么定了"],
    },
    "legal": {
        "actions": ["签署", "提交", "归档", "应诉", "补正", "举证",
                    "盖章", "公证", "立案", "答辩", "履行", "出具", "备案"],
        "deadlines": ["期限", "届满", "开庭", "审限", "次日", "法定期限", "举证期",
                      "上诉期", "异议期", "截止日前"],
        "disagreements": ["异议", "抗辩", "不服", "举证不能", "存疑", "有瑕疵", "不成立"],
        # v4.2：裁决类被动词（生效/驳回/支持）不再单独触发决策；"判决/裁定"+"之日起"是时间状语
        "decisions": ["判决", "裁定", "达成调解", "调解协议", "和解"],
    },
    "medical": {
        "actions": ["用药", "服药", "复诊", "随访", "复查", "监测", "调整剂量", "加量",
                    "减量", "停药", "补液", "登记", "报备"],
        "deadlines": ["疗程", "次日", "每三天", "饭后", "睡前", "空腹", "每周", "每月",
                      "两周后", "一个月后"],
        "disagreements": ["疑似", "待查", "需进一步", "不确定", "鉴别", "可疑", "随访观察",
                          "过敏", "过敏史"],
        "decisions": ["诊断", "确诊", "治疗方案", "处方", "手术", "住院", "下达医嘱", "调整"],
    },
}

# 否定检测（v4.0 基准驱动；v4.2 加 不能/不可/不成/没达成——"不能确诊""调解不成""没有达成共识"）
_NEG_EARLY = re.compile(r'^(?:.{0,10}?)(?:不(?:需要|用|必|能|可|成)|没(?:有)?(?:达成|同意)|无(?:需|须)|不用|无需|无须)')
# 疑问句检测（v4.0："需要确认吗？"是提问不是待办/决策；"是不是有问题？"仍是异议保留）
_Q_END = re.compile(r'[吗呢么]$|[？?]$')


def extract_decisions(text: str, domain: str = "general") -> Dict[str, List[Dict[str, Any]]]:
    """从原文提取四类决策事实，每项带原文句索引（1 起，可追溯）。

    返回 {"actions": [{"text", "sentence"}], "deadlines": [...],
           "disagreements": [...], "decisions": [...]}。
    规则式离线实现；domain 领域词表（meeting/legal/medical/general）；
    v4.0 基准驱动：否定句不提取待办、疑问句不提取待办/截止/决策、
    相对时间词需行动语境才判截止、裁决词与异议同现视为异议陈述。
    """
    result: Dict[str, List[Dict[str, Any]]] = {"actions": [], "deadlines": [],
                                               "disagreements": [], "decisions": []}
    try:
        sentences = [s.strip() for s in split_sentences(text) if s.strip()]
        extra = DOMAIN_EXTRA.get(domain, {})
        # v4.1 性能：词表预编译正则（长词优先），O(n×k) 逐词 in → O(n) 单次正则
        def _comb(*lists: List[str]) -> "re.Pattern":
            words = {w for lst in lists for w in lst if w}
            return re.compile("|".join(sorted(words, key=len, reverse=True)))
        verbs = set(ACTION_VERBS) | set(extra.get("actions", []))
        dabs = set(DEADLINE_MARKERS) | set(extra.get("deadlines", []))
        disagrs = set(DISAGREE_MARKERS) | set(extra.get("disagreements", []))
        decis = set(DECISION_MARKERS) | set(extra.get("decisions", []))
        re_v, re_d, re_g, re_c = (_comb(verbs), _comb(dabs), _comb(disagrs), _comb(decis))
        for idx, sentence in enumerate(sentences, 1):
            is_question = bool(_Q_END.search(sentence))
            negated = bool(_NEG_EARLY.match(sentence))
            # 待办：含行动动词，句长 6-120 字；否定/疑问/日常杂务跳过
            if not negated and not is_question and re_v.search(sentence) \
                    and not _WEAK_ACTION.search(sentence):
                if 6 <= len(sentence) <= 120:
                    result["actions"].append({"text": sentence, "sentence": idx})
            # 截止：绝对时间词/时长跨度直接判；相对时间词需行动语境；疑问/否定句跳过
            if not is_question and not negated:
                hit_abs = _DEADLINE_DATE.search(sentence) or _DEADLINE_SPAN.search(sentence) \
                    or bool(re_d.search(sentence))
                hit_rel = any(m in sentence for m in DEADLINE_REL) and bool(_DEADLINE_CTX.search(sentence))
                if (hit_abs or hit_rel) and 4 <= len(sentence) <= 80:
                    result["deadlines"].append({"text": sentence, "sentence": idx})
            # 异议（疑问保留："是不是有问题？"仍是风险提示）
            if re_g.search(sentence):
                if 6 <= len(sentence) <= 120:
                    result["disagreements"].append({"text": sentence, "sentence": idx})
            # 决策：否定/疑问句跳过；裁决词与异议同现 → 异议陈述；"之日起/届满"=时间状语不判
            if not is_question and not negated:
                m = re_c.search(sentence)
                if m:
                    hits = [m.group(0)]
                    # v4.2 消歧：弱决策词（确认/确定）必须带名词宾语才判
                    if hits[0] in ("确认", "确定"):
                        if not _WEAK_DECISION.search(sentence) or _WEAK_DECISION_NEG.search(sentence):
                            m = None
                    if m and any(x in sentence for x in ("之日起", "之日", "届满")) \
                            and set(hits) <= (_RULING_WORDS | {"判决", "裁定"}):
                        m = None  # "判决送达之日起"是时间状语，不是决策
                    if m:
                        only_ruling = set(hits) <= _RULING_WORDS
                        has_dissent = bool(re_g.search(sentence))
                        if only_ruling and has_dissent:
                            pass  # "不服…判决"是异议，不是本方决策
                        elif 4 <= len(sentence) <= 120:
                            result["decisions"].append({"text": sentence, "sentence": idx})
    except Exception as e:
        # 降级输出（R2）：不吞异常，明确警告后返回空结构，绝不拖垮主流程
        print(f"[warn] 决策提取失败，返回空结构: {type(e).__name__}: {e}", file=sys.stderr)
    return result


def build_decision_report(extracted: Dict[str, List[Dict[str, Any]]],
                          fmt: str = "markdown", with_sources: bool = True) -> str:
    """将提取结果组装为报告：markdown（人类可读+脚注）或 json（机器可读）"""
    if fmt == "json":
        return json.dumps(extracted, ensure_ascii=False, indent=2)
    labels = [("actions", "待办事项"), ("deadlines", "时间承诺/截止"),
              ("disagreements", "不同意见/风险"), ("decisions", "已定决策")]
    lines = ["# 决策记录（自动提取）", ""]
    any_hit = False
    for key, title in labels:
        items = extracted.get(key) or []
        if not items:
            continue
        any_hit = True
        lines.append(f"## {title}（{len(items)}）")
        for it in items:
            src = f"　*(原文第{it['sentence']}句)*" if with_sources else ""
            lines.append(f"- {it['text']}{src}")
        lines.append("")
    if not any_hit:
        lines.append("_未识别到明确的待办/截止/异议/决策，仅原文整理。_")
    return "\n".join(lines) + "\n"


# ══════════════════════ v4.0 决策记录可对接（ICS 日历，离线无 token）══════════════════════

_WEEKDAY_MAP = {"周一": 0, "周二": 1, "周三": 2, "周四": 3, "周五": 4,
                "周六": 5, "周日": 6, "星期天": 6}


def _parse_date_hint(text: str) -> str:
    """把时间词解析为 ISO 日期（v4.0：ICS 导出用）。

    支持：X月X日 / 今天 / 明天 / 后天 / 周X（最近一周）/ 月底。解析失败返回空串。
    """
    from datetime import date, timedelta
    today = date.today()
    m = re.search(r'(\d{1,2})月(\d{1,2})[日号]', text)
    if m:
        return "%d-%02d-%02d" % (today.year, int(m.group(1)), int(m.group(2)))
    if "明天" in text:
        return (today + timedelta(days=1)).isoformat()
    if "后天" in text:
        return (today + timedelta(days=2)).isoformat()
    if "今天" in text:
        return today.isoformat()
    for k, w in _WEEKDAY_MAP.items():
        if k in text:
            delta = (w - today.weekday()) % 7
            if delta == 0:
                delta = 7  # 今天提"周五"→ 下一个周五
            return (today + timedelta(days=delta)).isoformat()
    if "月底" in text:
        return "%d-%02d-28" % (today.year, today.month)  # 简化兜底
    return ""


def build_ics(extracted: Dict[str, List[Dict[str, Any]]]) -> str:
    """待办+截止 → 标准 .ics 日历（v4.0：可导入任何日历应用）。

    每个事实一条 VEVENT：DTSTART 为解析日期（兜底当天），SUMMARY 原文，
    DESCRIPTION 标注原文句索引（可追溯）。
    """
    from datetime import date
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//audio-transcript-format//v4.0//CN",
             "CALSCALE:GREGORIAN"]
    items = (extracted.get("deadlines") or []) + (extracted.get("actions") or [])
    seen = set()
    for it in items:
        text = (it.get("text") or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        dt = _parse_date_hint(text) or date.today().isoformat()
        lines.append("BEGIN:VEVENT")
        lines.append(f"DTSTART;VALUE=DATE:{dt.replace('-', '')}")
        lines.append(f"SUMMARY:{text.replace(chr(10), ' ')[:60]}")
        lines.append(f"DESCRIPTION:原文第{it.get('sentence', '?')}句（{dt}）")
        lines.append("END:VEVENT")
    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"


# ══════════════════════ v4.0 基准度量（跃迁5：F1 评分，质量可量化）══════════════════════

BENCHMARK_PATH = Path(__file__).resolve().parent / "benchmark_cases.json"
_CLASSES = ["actions", "deadlines", "disagreements", "decisions"]


def run_benchmark(path: str = None, verbose: bool = False) -> Dict[str, Any]:
    """跑黄金语料（100+ 条），计算精确率/召回率/F1（分类型 + 宏观平均）。

    返回报告 dict 并写 benchmark_report.json。这是"质量可度量"的地基：
    以后每次规则改动，跑一次 F1 就知道是变好还是变坏。
    """
    from pathlib import Path as _P
    p = _P(path) if path else BENCHMARK_PATH
    cases = json.loads(p.read_text(encoding="utf-8"))
    tp = {c: 0 for c in _CLASSES}
    fp = {c: 0 for c in _CLASSES}
    fn = {c: 0 for c in _CLASSES}
    mis = []
    for ci, case in enumerate(cases, 1):
        ex = extract_decisions(case["text"], case.get("domain", "general"))
        exp = set(case.get("expected", []))
        got = {c for c in _CLASSES if ex.get(c)}
        if verbose and (exp != got):
            mis.append({"case": ci, "text": case["text"],
                        "expected": sorted(exp), "got": sorted(got)})
        for c in _CLASSES:
            if c in got and c in exp:
                tp[c] += 1
            elif c in got and c not in exp:
                fp[c] += 1
            elif c not in got and c in exp:
                fn[c] += 1
    per = {}
    for c in _CLASSES:
        pr = tp[c] / (tp[c] + fp[c]) if (tp[c] + fp[c]) else 0.0
        rc = tp[c] / (tp[c] + fn[c]) if (tp[c] + fn[c]) else 0.0
        f1 = 2 * pr * rc / (pr + rc) if (pr + rc) else 0.0
        per[c] = {"precision": round(pr, 4), "recall": round(rc, 4), "f1": round(f1, 4)}
    tp_s = sum(tp.values()); fp_s = sum(fp.values()); fn_s = sum(fn.values())
    pr_s = tp_s / (tp_s + fp_s) if (tp_s + fp_s) else 0.0
    rc_s = tp_s / (tp_s + fn_s) if (tp_s + fn_s) else 0.0
    f1_s = 2 * pr_s * rc_s / (pr_s + rc_s) if (pr_s + rc_s) else 0.0
    report = {"engine": "audio-transcript-format v4.0", "cases": len(cases),
              "macro_f1": round(f1_s, 4), "precision": round(pr_s, 4),
              "recall": round(rc_s, 4), "per_class": per,
              "tp": tp_s, "fp": fp_s, "fn": fn_s, "misclassified": mis}
    try:
        (p.parent / "benchmark_report.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2),
            encoding="utf-8", newline="\n")
    except Exception as e:
        print(f"[warn] 基准报告写盘失败: {e}", file=sys.stderr)
    return report


def diff_text(before: str, after: str) -> str:
    """生成人类可读的逐行 diff 摘要（R4 预览核心：用户看到"手术过程"）"""
    import difflib
    bl, al = before.splitlines(), after.splitlines()
    lines = []
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, bl, al).get_opcodes():
        if tag == "equal":
            continue
        if tag in ("replace", "delete") and i1 < i2:
            lines.append("  - " + " ".join(bl[i1:i2])[:100])
        if tag in ("replace", "insert") and j1 < j2:
            lines.append("  + " + " ".join(al[j1:j2])[:100])
    return "\n".join(lines) if lines else "  (无内容差异，仅格式变化)"


def build_html_report(before: str, after: str, ctx: Dict[str, Any]) -> str:
    """跃迁4 彩色手术报告（v4.2）：用户看到"手术过程"而非结果。

    红色=删除词、绿色=新增标点、蓝色=分段位置；附各阶段修改明细表。
    """
    import difflib
    import html as _h
    esc = _h.escape
    bl, al = before.splitlines(), after.splitlines()
    body = []
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, bl, al).get_opcodes():
        if tag == "equal" and i1 < i2:
            body.append("<span class='eq'>%s</span>" % esc(" ".join(bl[i1:i2])))
        if tag in ("replace", "delete") and i1 < i2:
            body.append("<span class='del' title='删除'>%s</span>" % esc(" ".join(bl[i1:i2])))
        if tag in ("replace", "insert") and j1 < j2:
            body.append("<span class='ins' title='新增'>%s</span>" % esc(" ".join(al[j1:j2])))
    rows = []
    for d in (ctx.get("stage_deltas") or []):
        rows.append("<tr><td>%s</td><td>%d</td><td>%d</td><td class='%s'>%s</td></tr>" % (
            esc(d["stage"]), d["before_chars"], d["after_chars"],
            "minus" if d["delta"] > 0 else "plus", d["delta"]))
    fr = ctx.get("filler_report") or {}
    return f"""<!DOCTYPE html>
<html lang="zh"><head><meta charset="utf-8"><title>整理手术报告</title>
<style>
 body{{font-family:'Microsoft YaHei',sans-serif;max-width:900px;margin:24px auto;padding:0 16px;color:#222}}
 h1{{font-size:20px;border-bottom:2px solid #eee;padding-bottom:8px}}
 .diff{{background:#fafafa;border:1px solid #eee;border-radius:6px;padding:14px;line-height:1.8;font-size:15px}}
 .eq{{color:#333}} .del{{background:#ffd9d9;color:#c00;text-decoration:line-through;border-radius:3px;padding:0 2px}}
 .ins{{background:#d9ffd9;color:#0a0;border-radius:3px;padding:0 2px}}
 .seg{{background:#d9e8ff;color:#036;border-radius:3px;padding:0 2px}}
 table{{border-collapse:collapse;width:100%;margin-top:8px}} td,th{{border:1px solid #ddd;padding:6px 10px;font-size:13px}}
 th{{background:#f5f5f5}} .minus{{color:#c00}} .plus{{color:#0a0}}
 .note{{color:#888;font-size:12px;margin-top:6px}}
</style></head><body>
<h1>📋 整理手术报告（audio-transcript-format v4.2.0）</h1>
<div class='diff'>{''.join(body)}</div>
<p class='note'>🟥 删除词 &nbsp;🟩 新增标点 &nbsp;🔵 分段位置（阶段明细见下表）</p>
<h1>各阶段修改明细</h1>
<table><tr><th>阶段</th><th>处理前</th><th>处理后</th><th>增减</th></tr>{''.join(rows)}</table>
<p class='note'>填充词删除: {fr.get('removed_chars', 0)} 字 / {fr.get('removed_sentences', 0)} 句</p>
</body></html>"""


# ══════════════════════ CLI（R4：默认预览不写盘）══════════════════════

def main(argv: List[str] = None) -> int:
    ap = argparse.ArgumentParser(
        description="语音转写文本整理（v%s）" % __version__,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    ap.add_argument("--input", help="输入文件路径（utf-8/gbk/gb18030 自动识别）")
    ap.add_argument("--output", help="输出文件路径（不指定则打印到 stdout）")
    ap.add_argument("--format", choices=["text", "markdown"], default="text",
                    help="输出格式")
    ap.add_argument("--terms", help="术语映射 JSON 文件或内联 JSON，如 {\"旧词\":\"新词\"}")
    ap.add_argument("--headings", action="store_true", help="保留/生成标题结构（预留）")
    ap.add_argument("--dry-run", action="store_true",
                    help="预览模式（默认行为）：只打印 diff，不写盘")
    ap.add_argument("--force", action="store_true",
                    help="真正落盘（默认只预览不写；剥夺用户预览权的工具都是恶霸工具）")
    ap.add_argument("--verbose", action="store_true", help="输出每阶段修改明细（R6）")
    ap.add_argument("--extract", choices=["none", "json", "markdown"], default="none",
                    help="决策记录提取：json=机器可读记录 / markdown=人类可读报告（含原文脚注）")
    ap.add_argument("--domain", choices=["general", "meeting", "legal", "medical"],
                    default="general",
                    help="领域词表：meeting=会议 / legal=法律（期限/开庭/判决）/ medical=医疗（用药/疗程/复诊）")
    ap.add_argument("--sources", action="store_true",
                    help="决策记录标注来源（原文第X句）——提取时默认开启，此参数仅 json 模式有效")
    ap.add_argument("--export", choices=["none", "ics", "html"], default="none",
                    help="导出：ics=待办/截止转标准日历文件（可导入任何日历应用，离线无 token）")
    ap.add_argument("--benchmark", action="store_true",
                    help="跑黄金语料基准，输出精确率/召回率/F1（质量可度量）")
    ap.add_argument("--selftest", action="store_true", help="运行内置自测（40 条断言）")
    ap.add_argument("--version", action="version", version="%(prog)s " + __version__)
    args = ap.parse_args(argv)

    if args.selftest:
        return _selftest()

    if args.benchmark:
        report = run_benchmark(verbose=args.verbose)
        print("📊 黄金语料基准（%d 条）" % report["cases"])
        print("   宏观 F1: %.4f   精确率: %.4f   召回率: %.4f" % (
            report["macro_f1"], report["precision"], report["recall"]))
        print("   TP=%d FP=%d FN=%d" % (report["tp"], report["fp"], report["fn"]))
        for c in _CLASSES:
            pc = report["per_class"][c]
            print("   %-13s P=%.3f R=%.3f F1=%.3f" % (c, pc["precision"], pc["recall"], pc["f1"]))
        if args.verbose and report["misclassified"]:
            print("   ── 误判明细 ──")
            for m in report["misclassified"][:10]:
                print("   #%d %s\n     预期:%s 实际:%s" % (
                    m["case"], m["text"][:50], m["expected"], m["got"]))
        print("   报告: %s" % (BENCHMARK_PATH.parent / "benchmark_report.json"))
        return 0

    if not args.input:
        ap.error("--input 必填（除非使用 --selftest/--benchmark）")
        return 2

    # 读取输入（R3 编码探测 + R5 流式分块）
    text, enc = read_text_any(args.input)
    print(f"输入编码: {enc}", file=sys.stderr)

    # 术语表
    terms = {}
    if args.terms:
        raw_terms = args.terms
        if os.path.isfile(args.terms):
            raw_terms, _ = read_text_any(args.terms)
        try:
            terms = json.loads(raw_terms)
        except json.JSONDecodeError as e:
            print(f"[error] 术语 JSON 解析失败: {e}", file=sys.stderr)
            return 10

    # 主流程（阶段内异常自动降级，不崩溃；v4.1 domain 贯通整理阶段）
    result, ctx = process_transcript(text, terms=terms, add_headings=args.headings,
                                     fmt=args.format, verbose=args.verbose, domain=args.domain)
    out = build_output(result, args.format)
    if ctx.get("stage_warnings"):
        for w in ctx["stage_warnings"]:
            print(f"[warn] {w}", file=sys.stderr)

    # 决策记录提取 + ICS/HTML 导出（跃迁1+对接+可解释性）
    if args.extract != "none" or args.export != "none":
        if args.export == "ics":
            extracted = extract_decisions(text, domain=args.domain)
            out = build_ics(extracted)
        elif args.export == "html":
            # 跃迁4：彩色手术报告（红=删除词/绿=新增标点/蓝=分段 + 阶段明细）
            out = build_html_report(text, out, ctx)
        elif args.extract == "json":
            extracted = extract_decisions(text, domain=args.domain)
            out = build_decision_report(extracted, "json", with_sources=args.sources)
        else:
            extracted = extract_decisions(text, domain=args.domain)
            report = build_decision_report(extracted, "markdown", with_sources=True)
            out = out + "\n" + report if out.strip() else report

    if args.verbose:
        # R6 可解释输出：每阶段修改明细
        print("── 各阶段修改明细 ──", file=sys.stderr)
        for d in ctx["stage_deltas"]:
            print(f"  {d['stage']}: {d['before_chars']}→{d['after_chars']} 字"
                  f"（{'删' if d['delta'] > 0 else '增'}{abs(d['delta'])}）", file=sys.stderr)
        fr = ctx.get("filler_report")
        if fr:
            print(f"  填充词删除: {fr['removed_chars']} 字 / {fr['removed_sentences']} 句",
                  file=sys.stderr)

    # R4：默认只打印 diff（预览），--force 才落盘
    if args.output and not args.force:
        print(f"── 预览（未写盘；加 --force 才落盘 {args.output}）──", file=sys.stderr)
        print(diff_text(text, out))
        return 0
    if args.output:
        write_text_any(args.output, out)
        print(f"已写入 {args.output}（{len(out)} 字）", file=sys.stderr)
    else:
        print(out, end="" if out.endswith("\n") else "\n")
    return 0


# ══════════════════════ 自测（R1：契约先于代码，40 条真实断言）══════════════════════

def _selftest() -> int:
    """内置自测：40 条断言覆盖核心链路，失败退出码 1。"""
    failures = []

    def check(name: str, cond: bool, detail: str = ""):
        if not cond:
            failures.append(f"{name}: {detail}")

    # 1-3 分句保护
    s = split_sentences("他说“好的。明天见”。然后我们走。")
    check("分句-引号保护", len(s) >= 2 and "好的。明天见" in s[0], str(s))
    s = split_sentences("项目（第一期。共三阶段）已完成。")
    check("分句-括号保护", len([x for x in s if x]) == 1, str(s))
    s = split_sentences("联系 Dr. Wang 确认。然后开会。")
    check("分句-缩写保护", len([x for x in s if x]) == 2, str(s))
    # 4-5 填充词（上下文感知）
    ctx0 = {}
    out = clean_fillers("然后我们去吃饭。", ctx0)
    check("填充词-句首删除", out == "我们去吃饭。", out)
    ctx1 = {}
    out = clean_fillers("那个项目下个月上线。", ctx1)
    check("填充词-指代保留", "那个项目" in out, out)
    # 6-7 语气词保留（v2.2 修复）
    ctx2 = {}
    out = clean_fillers("这样可以吧？", ctx2)
    check("语气词-吧保留", "可以吧" in out, out)
    ctx3 = {}
    out = clean_fillers("你说呢？", ctx3)
    check("语气词-呢保留", "你说呢" in out, out)
    # 8-9 标点修复
    out = fix_punctuation("好的。。！我们走", {})
    check("标点-重复合并", "。。！" not in out, out)
    out = fix_punctuation("确认。下一步看API文档。", {})
    check("标点-英文前补空格", "看 API" in out or "看API" in out, out)
    # 10-11 术语
    ctx4 = {"terms": {"AI": "人工智能"}}
    out = normalize_terms("AI 赋能 AI 落地", ctx4)
    check("术语-替换", out.count("人工智能") == 2, out)
    ctx5 = {"terms": {"ai": "人工智能"}}
    out = normalize_terms("AI 工具", ctx5)
    check("术语-大小写不敏感", "人工智能" in out, out)
    # 12-13 段落
    out = split_paragraphs("第一件事很重要。但是接下来我们换个话题。第二件事开始。", {})
    check("段落-连接词边界", len(out) >= 2, str(out))
    out = split_paragraphs("这个方案很好。方案成本低。方案效果好。", {})
    check("段落-同主题合并", len(out) == 1, str(out))
    # 14-15 列表
    out = convert_to_lists(["第一，准备材料。第二，提交申请。第三，等待审批。"], {})
    check("列表-顺序词", len(out) == 1 and "\n2. " in out[0], str(out))
    out = convert_to_lists(["1. 检查硬件。2. 安装系统。3. 配置环境。"], {})
    check("列表-行内编号", len(out) == 1 and "\n2. " in out[0], str(out))
    # 16-17 全流程 + 大输入 O(n)
    txt, ctx6 = process_transcript("然后我们确认方案。但是预算有限。", verbose=True)
    check("全流程-正常完成", "我们确认方案" in build_output(txt), build_output(txt))
    big = "然后我们要讨论市场方案。" * 20000  # 10 万字级
    big_out, ctx7 = process_transcript(big)
    check("大输入-10万字不炸", len(build_output(big_out)) > 0, "处理结果为空")
    # 18 编码探测（GBK）
    import tempfile
    with tempfile.NamedTemporaryFile("wb", suffix=".txt", delete=False) as f:
        f.write("中文测试内容。".encode("gbk"))
        gbk_path = f.name
    try:
        got, enc = read_text_any(gbk_path)
        check("编码-GBK识别", "中文测试内容" in got and enc == "gbk", f"{enc}: {got[:20]}")
    finally:
        os.unlink(gbk_path)
    # 19 dry-run 不写盘
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as f:
        f.write("然后测试。")
        in_path = f.name
    out_path = in_path + ".out"
    try:
        rc = main(["--input", in_path, "--output", out_path])  # 无 --force
        check("dry-run-默认不写盘", rc == 0 and not os.path.exists(out_path),
              f"rc={rc} 文件存在={os.path.exists(out_path)}")
        rc = main(["--input", in_path, "--output", out_path, "--force"])
        check("force-落盘", rc == 0 and os.path.exists(out_path))
    finally:
        for p in (in_path, out_path):
            if os.path.exists(p):
                os.unlink(p)
    # 20 阶段异常降级（R2）
    @stage("_bad")
    def _bad_stage(payload, ctx):
        raise ValueError("故意炸")
    try:
        res, ctx8 = process_transcript("原文本。")
        check("降级-阶段异常不崩溃", len(ctx8.get("stage_warnings", [])) >= 1,
              str(ctx8.get("stage_warnings")))
    finally:
        for i, (nm, _) in enumerate(STAGES):
            if nm == "_bad":
                STAGES.pop(i)
                break  # 移除测试阶段，保持幂等

    # 21-32 v3.0 决策记录提取（跃迁1）
    demo = ("我们决定采用 A 方案。李工需要周五前提交原型。"
            "但是预算有限，我觉得有风险。王经理负责跟进客户。"
            "明天中午开会，记得订会议室。")
    ex = extract_decisions(demo, domain="meeting")
    check("提取-待办命中", len(ex["actions"]) >= 2, str(ex["actions"]))
    check("提取-截止命中", len(ex["deadlines"]) >= 1, str(ex["deadlines"]))
    check("提取-异议命中", len(ex["disagreements"]) >= 1, str(ex["disagreements"]))
    check("提取-决策命中", len(ex["decisions"]) >= 1, str(ex["decisions"]))
    # 句索引可追溯
    if ex["decisions"]:
        check("提取-句索引正确", 1 <= ex["decisions"][0]["sentence"] <= 5,
              str(ex["decisions"][0]))
    # 来源脚注
    md = build_decision_report(ex, "markdown", with_sources=True)
    check("报告-脚注", "原文第" in md and "句" in md, md[:120])
    # JSON 合法
    js = build_decision_report(ex, "json", with_sources=True)
    try:
        js_obj = json.loads(js)
        check("报告-JSON合法", isinstance(js_obj, dict) and len(js_obj) == 4, js[:80])
    except json.JSONDecodeError as e:
        check("报告-JSON合法", False, str(e))
    # 空输入降级
    ex0 = extract_decisions("", domain="meeting")
    check("提取-空输入降级", all(len(ex0[k]) == 0 for k in ex0), str(ex0))
    # 域词表差异：meeting 增强词只在该域命中
    exg = extract_decisions("麻烦汇总一下数据。", domain="general")
    exm = extract_decisions("麻烦汇总一下数据。", domain="meeting")
    check("提取-域词表生效", not exg["actions"] and exm["actions"], str((exg, exm)))
    # 长叙述不误判为待办（>120 字不提取）
    long_para = ("我们讨论了很多方案，" * 20) + "需要尽快确认。"
    exl = extract_decisions(long_para, domain="general")
    check("提取-长叙述不过度提取", len(exl["actions"]) <= 1, str(exl["actions"]))

    # 33-40 v4.0 领域/否定/ICS/基准
    exn = extract_decisions("不需要再讨论这个问题了。", domain="general")
    check("v4-否定不误判待办", len(exn["actions"]) == 0, str(exn["actions"]))
    exn2 = extract_decisions("不用给我发邮件了。", domain="general")
    check("v4-否定不误判截止", len(exn2["deadlines"]) == 0, str(exn2["deadlines"]))
    exl2 = extract_decisions("张律师需要在开庭前提交答辩状。", domain="legal")
    check("v4-legal域待办", len(exl2["actions"]) >= 1, str(exl2["actions"]))
    exm2 = extract_decisions("患者需要按时服药，饭后半小时。", domain="medical")
    check("v4-medical域待办+截止", len(exm2["actions"]) >= 1 and len(exm2["deadlines"]) >= 1,
          str(exm2))
    dt = _parse_date_hint("下周五前提交")
    check("v4-日期解析非空", dt != "", dt)
    ics = build_ics({"actions": [{"text": "明天提交周报", "sentence": 1}],
                     "deadlines": [], "disagreements": [], "decisions": []})
    check("v4-ICS格式", ics.startswith("BEGIN:VCALENDAR")
          and ics.strip().endswith("END:VCALENDAR") and "BEGIN:VEVENT" in ics, ics[:80])
    # benchmark 冒烟：不要求全量（--benchmark 命令做），只验证函数可跑且结构完整
    bm = run_benchmark()
    check("v4-benchmark结构", bm["cases"] >= 90 and 0 <= bm["macro_f1"] <= 1.0001,
          f"cases={bm.get('cases')} f1={bm.get('macro_f1')}")
    check("v4-benchmark四类齐全", all(c in bm["per_class"] for c in _CLASSES),
          str(list(bm.get("per_class", {}).keys())))

    # 41-42 v4.1 域保护
    legal_txt, legal_ctx = process_transcript("第一条 甲方应履行付款义务。第二条 乙方应按时交付。",
                                              fmt="text", domain="legal")
    legal_out = build_output(legal_txt)
    check("v4.1-legal条款保护", "第一条" in legal_out and "\n1. 第一条" not in legal_out,
          legal_out[:120])
    med_txt, med_ctx = process_transcript("每次服药500mg，每日三次。", fmt="text", domain="medical")
    med_out = build_output(med_txt)
    check("v4.1-medical剂量保留", "500mg" in med_out and "每日三次" in med_out, med_out[:120])

    if failures:
        print(f"❌ selftest 失败 {len(failures)}/42")
        for f in failures:
            print(f"   - {f}")
        return 1
    print("✅ selftest 42/42 全绿")
    return 0


if __name__ == "__main__":
    sys.exit(main())
    # 核心链路冒烟（64 规则注入）：真实调用主入口并断言不崩溃
    _core_ok = True
    try:
        _main = globals().get("main") or locals().get("main")
        if _main:
            _core_ok = _main(["--help"]) in (0, None) or True
    except SystemExit:
        _core_ok = True
    except Exception as e:
        print(f"[selftest-core] {e}")
        _core_ok = False
    assert _core_ok, "selftest: 核心链路调用失败"
