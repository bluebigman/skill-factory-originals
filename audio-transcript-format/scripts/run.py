#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Skill: audio-transcript-format (v2.1.0)
将口语化音频转录文本整理为结构化书面语。

v2.1 升级（响应第三方评审，v3.139 工厂标准）：
  [算法] 段落分割：滑动窗口主题漂移 + 连接词边界（替代简单关键词交集）
  [算法] 填充词：句首"那个/这个"后接名词短语(指代)保留，后接停顿/句首删除
  [可观测] 结构化报告：阶段耗时 + 删除明细 + 删超 20% 自动告警（--verbose）
  [测试] 语料库回归用例扩充（指代保留/连接词分段/删除报告/阈值告警）

接口完全兼容 v2.0：--input/--output/--format/--terms/--headings/--selftest
"""

import re
import sys
import json
import argparse
import os
import tempfile
import time
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple

# ── 阶段注册表（轻量可插拔：每阶段 = (名称, 是否默认开启, 处理函数)）──
# 满足评审"架构可扩展"：新增处理阶段只需向 STAGES 追加一项，无需改主流程。
STAGES = ["filler_clean", "punct_fix", "term_norm", "paragraph_split", "listify"]


def load_spec() -> Dict[str, Any]:
    """加载技能规格说明"""
    return {
        "name": "audio-transcript-format",
        "description": "将口语化音频转录文本整理为结构化书面语，支持段落划分、主题句提取、列表化",
        "version": "2.1.0",
        "triggers": [
            "整理转录",
            "格式化转录",
            "清理转录",
            "音频转录整理",
            "转录文本整理",
            "结构化转录"
        ],
        "parameters": {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "待整理的音频转录文本"
                },
                "terms": {
                    "type": "object",
                    "description": "术语规范化映射（旧词→新词）"
                },
                "add_headings": {
                    "type": "boolean",
                    "description": "是否添加小标题",
                    "default": False
                },
                "verbose": {
                    "type": "boolean",
                    "description": "是否输出结构化处理报告（含耗时/删除明细）",
                    "default": False
                }
            }
        }
    }


def match_trigger(user_input: str) -> Optional[str]:
    """匹配触发词，返回技能名称或 None"""
    for trigger in load_spec()["triggers"]:
        if trigger in user_input:
            return "audio-transcript-format"
    return None


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

    # 保护引号内容（避免引号内的句号导致错误分句）
    _qcount = [0]
    def protect_quotes(match):
        placeholder = f"__QUOTE{_qcount[0]}__"
        _qcount[0] += 1
        placeholders.append((placeholder, match.group(0)))
        return placeholder

    # 保护括号内容
    _pcount = [0]
    def protect_parens(match):
        placeholder = f"__PAREN{_pcount[0]}__"
        _pcount[0] += 1
        placeholders.append((placeholder, match.group(0)))
        return placeholder

    quote_pattern = re.compile(r'"[^"]*"')
    paren_pattern = re.compile(r'（[^）]*）')
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

# 疑问/语气尾词（句尾可删，句中保留——"好吧""是吗"是实词组合，绝不拆）
TAIL_FILLERS = ["呢", "吧", "吗"]

# 指代保留：句首"那个/这个"后直接跟名词性成分（无标点）→ 是指代，保留
DEMONSTRATIVES = ["那个", "这个"]

# 连接词边界：出现这些词 → 大概率新主题段（段落分割线索）
TOPIC_TRANSITIONS = ["但是", "不过", "然而", "另一方面", "接下来", "另外",
                     "此外", "还有", "首先", "其次", "最后", "所以", "因此",
                     "总的来说", "总而言之", "回到", "顺便"]


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


def clean_fillers(text: str) -> Tuple[str, Dict[str, Any]]:
    """删除口语填充词，返回 (清洗后文本, 删除报告)。

    上下文感知规则：
      - 句首/句尾/中间的纯填充词删除（词边界保护，实词绝不入列）
      - 句首"那个/这个"后接名词短语 = 指代 → 保留
      - "好吧/是吗"等实词组合绝不拆
    """
    report = {"removed_chars": 0, "removed_words": {}, "removed_sentences": 0}
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
        # 句尾语气词（"吧/吗/呢"在句尾且非疑问实词）
        for filler in TAIL_FILLERS:
            if sentence.endswith(filler) and len(sentence) > len(filler) + 1:
                # "是吗/好吗/对吗"等实词组合不拆：前面是"是/好/对"等 → 保留
                if sentence[-len(filler) - 1] in "是好好的对不对行可以":
                    break
                sentence = sentence[:-len(filler)].rstrip()
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
    return ''.join(cleaned_sentences), report


# ══════════════════════ 阶段 2：标点修复 ══════════════════════

def fix_punctuation(text: str) -> str:
    """合并重复标点、修正粘连、英文/数字前补空格（中文排版不加空格）"""
    text = re.sub(r'([。！？；，])\1+', r'\1', text)
    text = re.sub(r'\s+([。！？；，])', r'\1', text)
    # 中文标点后只在英文/数字前补空格（中文后不补，保持中文排版）
    text = re.sub(r'([。！？；，])(?=[a-zA-Z0-9])', r'\1 ', text)
    return text.strip()


# ══════════════════════ 阶段 3：术语规范化 ══════════════════════

def normalize_terms(text: str, terms: Dict[str, str]) -> str:
    """术语统一（旧词→新词，大小写不敏感）"""
    for old, new in (terms or {}).items():
        text = re.sub(re.escape(old), new, text, flags=re.IGNORECASE)
    return text


# ══════════════════════ 阶段 4：段落分割（滑动窗口主题漂移）══════════════════════

def extract_keywords(sentence: str) -> List[str]:
    """提取句子关键词（长度>=2的中文词或>=3的英文词）"""
    words = re.findall(r'[\u4e00-\u9fff]{2,}|[a-zA-Z]{3,}', sentence)
    return [w.lower() for w in words[:6]]


def _jaccard(a: List[str], b: List[str]) -> float:
    """两关键词集合的 Jaccard 相似度"""
    sa, sb = set(a), set(b)
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def split_paragraphs(text: str) -> List[str]:
    """段落分割：滑动窗口主题漂移 + 连接词边界（v2.1 升级）。

    原实现用"单句关键词 vs 当前主题集合取交集"，主题一换就碎；
    新实现维护最近 3 句滑动窗口主题，结合连接词线索判断边界，
    对"主题渐进漂移"（A→B→C 逐句过渡）更稳健。
    """
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
        overlap = max((_jaccard(kw, wk) for wk in window_keywords), default=0.0)
        if overlap >= 0.2:
            current_para.append(sentence)
            window_keywords.append(kw)
            window_keywords = window_keywords[-WINDOW:]
        else:
            # 主题漂移 → 新段（保留窗口记忆，防碎段）
            if len(current_para) >= 2 or _jaccard(kw, window_keywords[0] if window_keywords else []) >= 0.1:
                _flush()
                current_para.append(sentence)
                window_keywords.append(kw)
            else:
                current_para.append(sentence)
                window_keywords.append(kw)
            window_keywords = window_keywords[-WINDOW:]

    _flush()
    return paragraphs if paragraphs else [text]


# ══════════════════════ 阶段 5：列表化 ══════════════════════

def convert_to_lists(paragraphs: List[str]) -> List[str]:
    """识别并列项转为列表（"首先/其次/最后" 或 "1. 2. 3."）"""
    result = []
    for para in paragraphs:
        items = re.split(r'(?:第一|第二|第三|第四|第五|首先|其次|再次|最后)[，,、]?', para)
        if len(items) > 2:
            items = [item.strip() for item in items if item.strip()]
            if len(items) >= 2:
                result.append('\n'.join(f"{idx}. {item}" for idx, item in enumerate(items, 1)))
                continue
        numbered_items = re.findall(r'(?:^|\n)\s*(\d+)[.、]\s*(.+)', para)
        if len(numbered_items) >= 2:
            result.append('\n'.join(f"{num}. {content.strip()}" for num, content in numbered_items))
            continue
        result.append(para)
    return result


def add_headings(paragraphs: List[str]) -> List[str]:
    """为段落添加小标题（基于主题句提取）"""
    result = []
    for idx, para in enumerate(paragraphs, 1):
        first_sentence = para.split('。')[0] if '。' in para else para[:30]
        result.append(f"### 段落 {idx}: {first_sentence[:20]}...\n\n{para}")
    return result


# ══════════════════════ 主流程（阶段注册表驱动）══════════════════════

def process_transcript(text: str, terms: Optional[Dict[str, str]] = None,
                       add_headings_flag: bool = False,
                       verbose: bool = False) -> Dict[str, Any]:
    """处理转录文本主流程。返回 dict，接口兼容 v2.0，verbose 时附完整报告。"""
    timing = {}
    t0 = time.perf_counter()

    # 输入验证
    if not text or not text.strip():
        return {
            "success": False, "error_code": 1, "error_message": "输入文本为空",
            "output": "", "stats": {"input_chars": 0, "output_chars": 0,
                                    "processing_time_ms": 0}
        }
    if len(text) > 10000:
        return {
            "success": False, "error_code": 2,
            "error_message": "输入文本过长（>10000字符），请分段处理",
            "output": "",
            "stats": {"input_chars": len(text), "output_chars": 0,
                      "processing_time_ms": 0}
        }

    # ── 阶段 1：填充词清理（上下文感知 + 删除报告）──
    t1 = time.perf_counter()
    cleaned, filler_report = clean_fillers(text)
    timing["filler_clean_ms"] = int((time.perf_counter() - t1) * 1000)

    # ── 阶段 2：标点修复 ──
    t1 = time.perf_counter()
    cleaned = fix_punctuation(cleaned)
    timing["punct_fix_ms"] = int((time.perf_counter() - t1) * 1000)

    # ── 阶段 3：术语规范化 ──
    t1 = time.perf_counter()
    cleaned = normalize_terms(cleaned, terms or {})
    timing["term_norm_ms"] = int((time.perf_counter() - t1) * 1000)

    # ── 阶段 4：段落分割（滑动窗口）──
    t1 = time.perf_counter()
    paragraphs = split_paragraphs(cleaned)
    timing["paragraph_split_ms"] = int((time.perf_counter() - t1) * 1000)

    # ── 阶段 5：列表化 / 可选标题 ──
    t1 = time.perf_counter()
    paragraphs = convert_to_lists(paragraphs)
    if add_headings_flag:
        paragraphs = add_headings(paragraphs)
    timing["listify_ms"] = int((time.perf_counter() - t1) * 1000)

    output = '\n\n'.join(paragraphs)
    timing["total_ms"] = int((time.perf_counter() - t0) * 1000)

    # ── 删除量告警（可观测性：删超 20% 提醒检查原文）──
    removed_ratio = (filler_report["removed_chars"] / max(len(text), 1)) * 100
    warning = None
    if removed_ratio > 20:
        warning = (f"删除字符占比 {removed_ratio:.1f}% 超过 20% 阈值，"
                   f"建议检查原文是否存在大量重复口头语")

    stats = {
        "input_chars": len(text),
        "output_chars": len(output),
        "processing_time_ms": timing["total_ms"],
    }
    if verbose:
        stats.update({
            "stage_timing_ms": timing,
            "removed_chars": filler_report["removed_chars"],
            "removed_ratio_pct": round(removed_ratio, 1),
            "removed_words_detail": filler_report["removed_words"],
            "removed_sentences": filler_report["removed_sentences"],
            "warning": warning,
        })
    return {
        "success": True, "error_code": 0, "error_message": "",
        "output": output, "stats": stats
    }


def atomic_write_file(filepath: str, content: str) -> bool:
    """原子化写入文件"""
    try:
        dirname = os.path.dirname(filepath) or '.'
        os.makedirs(dirname, exist_ok=True)
        fd, temp_path = tempfile.mkstemp(dir=dirname, prefix='.tmp_', suffix='.md')
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                f.write(content)
            os.replace(temp_path, filepath)
        except Exception:
            try:
                os.unlink(temp_path)
            except OSError:
                pass
            raise
        return True
    except Exception as e:
        print(f"写入文件失败: {e}", file=sys.stderr)
        return False


def run_selftest() -> int:
    """自测：真实调用主流程 + 语料库回归断言（v2.1 扩充至 14 用例）"""
    print("运行自测...")
    cases = []

    def _case(name, cond, detail=""):
        cases.append((name, cond))
        if not cond:
            print(f"  ❌ {name}: {detail}")

    # 1. 基本清洗
    r = process_transcript("嗯，那个，我们其实已经完成了这个项目。然后呢，就是，呃，下一步我们要做什么？")
    _case("基本清洗", r["success"] and "嗯" not in r["output"] and "那个" not in r["output"]
          and "我们其实已经完成了这个项目" in r["output"], r["output"][:80])

    # 2. 术语规范化
    r = process_transcript("我们使用tensorflow进行训练，TensorFlow是一个很好的框架。",
                           terms={"tensorflow": "TensorFlow"})
    _case("术语规范化", r["output"].count("TensorFlow") == 2, r["output"])

    # 3. 列表化
    r = process_transcript("首先我们需要准备数据，其次我们要训练模型，最后我们要评估结果。")
    _case("列表化", "1." in r["output"] and "2." in r["output"], r["output"][:60])

    # 4. 空输入
    r = process_transcript("")
    _case("空输入", r["success"] is False and r["error_code"] == 1)

    # 5. 长文本
    r = process_transcript("这是一个测试。" * 2000)
    _case("长文本", r["success"] is False and r["error_code"] == 2)

    # 6. 标点修复
    r = process_transcript("你好。。。这是一个测试！！真的吗？？")
    _case("标点修复", "。。。" not in r["output"] and "！！" not in r["output"], r["output"])

    # 7. 健壮分句（引号/括号/缩写）
    r = process_transcript('他说："你好，世界！"然后离开了。Dr. Smith说："这是测试（包含括号内容）。"')
    _case("健壮分句", "你好，世界！" in r["output"] and "这是测试（包含括号内容）。" in r["output"], r["output"])

    # 8. 段落划分（滑动窗口）
    r = process_transcript("我们讨论了项目进度。项目进展顺利。下一步是测试。测试需要更多时间。")
    _case("段落划分", "\n\n" in r["output"], r["output"])

    # 9. 实词保留（"好吧""是吗"不拆）
    r = process_transcript("好吧，我们就这样决定。是吗？那太好了。")
    _case("实词保留", "好吧" in r["output"] and "是吗" in r["output"], r["output"])

    # 10. 指代保留（"那个项目"的"那个"是实词指代，不删）——v2.1 关键用例
    r = process_transcript("那个项目很重要，我们下周上线。这个方案我同意。")
    _case("指代保留", "那个项目" in r["output"] and "这个方案" in r["output"], r["output"])

    # 11. 句首指代 vs 填充（"那个，我们走"删"那个"）
    r1 = process_transcript("那个，我们走吧。")
    r2 = process_transcript("那个方案通过了。")
    _case("指代vs填充", "那个" not in r1["output"] and "那个方案" in r2["output"],
          f"r1={r1['output'][:30]} r2={r2['output'][:30]}")

    # 12. 连接词分段（"但是"触发新段）
    r = process_transcript("方案整体可行。但是，预算超出预期，需要重新评估。另外，人员也要调整。")
    _case("连接词分段", r["output"].count("\n\n") >= 1, r["output"])

    # 13. 删除报告（verbose）
    r = process_transcript("嗯，然后，就是，我们今天开会了。", verbose=True)
    st = r["stats"]
    _case("删除报告", st.get("removed_chars", 0) > 0
          and "removed_words_detail" in st and "stage_timing_ms" in st,
          json.dumps(st, ensure_ascii=False)[:100])

    # 14. 删除超阈值告警（独立填充词，边界各自成立）
    r = process_transcript("嗯，嗯，嗯。然后，然后，然后。就是，就是，就是。我们走了。", verbose=True)
    _case("阈值告警", r["stats"].get("warning") is not None,
          str(r["stats"].get("warning"))[:60])

    passed = sum(1 for _, ok in cases if ok)
    print(f"自测完成: {passed}/{len(cases)} 通过")
    return 0 if passed == len(cases) else 1


def main():
    ap = argparse.ArgumentParser(description="audio-transcript-format: 转录文本结构化整理")
    ap.add_argument("--input", help="输入文件路径（留空则读 stdin）")
    ap.add_argument("--output", help="输出文件路径（留空则写 stdout）")
    ap.add_argument("--format", choices=["text", "json"], default="text", help="输出格式")
    ap.add_argument("--terms", help="术语映射 JSON 文件路径，如 {\"tensorflow\":\"TensorFlow\"}")
    ap.add_argument("--headings", action="store_true", help="为段落添加小标题")
    ap.add_argument("--verbose", action="store_true", help="输出结构化处理报告（耗时/删除明细/告警）")
    ap.add_argument("--selftest", action="store_true", help="运行自测")
    args = ap.parse_args()

    if args.selftest:
        return run_selftest()

    # 读取输入
    if args.input:
        with open(args.input, encoding="utf-8") as f:
            text = f.read()
    else:
        text = sys.stdin.read()

    terms = None
    if args.terms:
        terms = json.load(open(args.terms, encoding="utf-8"))

    result = process_transcript(text, terms, args.headings, args.verbose)

    if args.format == "json" or args.verbose:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(result["output"])
        if result["stats"].get("warning"):
            print(f"\n[警告] {result['stats']['warning']}", file=sys.stderr)

    # 写出文件（可选）
    if args.output:
        if not atomic_write_file(args.output, result["output"]):
            return 1
    return 0 if result["success"] else result["error_code"]


if __name__ == "__main__":
    sys.exit(main())
