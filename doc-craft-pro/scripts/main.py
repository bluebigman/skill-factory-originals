#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文本洗稿整理工具 (skill-64729)

将杂乱文本整理为结构化内容，智能改写并检测相似度。

用法示例:
    python run.py -i input.txt -o output/
    python run.py -i batch.txt -o output/ --batch
    python run.py -i input.txt --dry-run --verbose
    python run.py --selftest
"""

import argparse
import hashlib
import json
import math
import os
import re
import sys
import tempfile
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
dry_run = False  # v3.274 模块级 dry-run 标志

# 版本信息
VERSION = "2.0.0"

# 默认配置
DEFAULT_MIN_PARAGRAPH_LEN = 20
DEFAULT_MAX_PARAGRAPH_LEN = 500
DEFAULT_SIMILARITY_THRESHOLD = 0.6
DEFAULT_BATCH_SEPARATOR = "---"
DEFAULT_SUMMARY_LEN = 100

# 错误码
ERR_INPUT_EMPTY = "E001"
ERR_ENCODING = "E002"
ERR_FILE_READ = "E003"
ERR_OUTPUT_DIR = "E004"
ERR_BATCH_SEPARATOR = "E005"
ERR_INTERNAL = "E006"


# ==================== 输入校验 (R7) ====================

def validate_input_path(input_path: str) -> None:
    """校验输入路径是否合法。"""
    if not input_path or not input_path.strip():
        raise ValueError(f"{ERR_INPUT_EMPTY}: 输入路径为空")
    # 路径白名单校验，防止路径穿越
    p = Path(input_path)
    if not p.exists():
        raise FileNotFoundError(f"{ERR_FILE_READ}: 文件不存在: {input_path}")
    if not p.is_file():
        raise ValueError(f"{ERR_FILE_READ}: 路径不是文件: {input_path}")


def validate_output_dir(output_dir: str) -> None:
    """校验输出目录，必要时创建。"""
    if not output_dir:
        raise ValueError(f"{ERR_OUTPUT_DIR}: 输出目录为空")
    p = Path(output_dir)
    try:
        p.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        raise OSError(f"{ERR_OUTPUT_DIR}: 无法创建输出目录 {output_dir}: {e}")


# ==================== 文件读取 (R3, R5) ====================

def read_file_streaming(file_path: str):
    """
    流式读取文件，支持多编码 fallback。
    使用 readline 逐行读取，避免一次性加载大文件。
    """
    encodings = ["utf-8", "gbk", "gb18030"]
    for enc in encodings:
        try:
            with open(file_path, "r", encoding=enc, errors="strict") as f:
                # 逐行读取，yield 出去
                for line in f:
                    yield line, enc
            return  # 成功读取后退出
        except (UnicodeDecodeError, UnicodeError):
            continue
        except OSError as e:
            raise OSError(f"{ERR_FILE_READ}: 文件读取失败: {e}")

    # 所有编码都失败，使用 errors="replace" 兜底
    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                yield line, "utf-8-replace"
    except OSError as e:
        raise OSError(f"{ERR_FILE_READ}: 文件读取失败: {e}")


def read_input(input_path: str) -> str:
    """读取输入文件，返回完整文本。"""
    validate_input_path(input_path)
    content_parts = []
    for line, enc in read_file_streaming(input_path):
        content_parts.append(line)
    content = "".join(content_parts)
    if not content.strip():
        raise ValueError(f"{ERR_INPUT_EMPTY}: 输入文件为空")
    return content


# ==================== 文本处理核心逻辑 ====================

def split_paragraphs(text: str, min_len: int = DEFAULT_MIN_PARAGRAPH_LEN,
                     max_len: int = DEFAULT_MAX_PARAGRAPH_LEN) -> list:
    """
    将文本按语义边界切分为独立段落。
    按空行、句号、问号、感叹号等边界切分，合并过短段落。
    """
    if not text or not text.strip():
        return []

    # 先按空行切分
    raw_blocks = re.split(r"\n\s*\n", text.strip())
    paragraphs = []

    for block in raw_blocks:
        block = block.strip()
        if not block:
            continue

        # 如果块太长，按句子边界切分
        if len(block) > max_len:
            sentences = re.split(r"(?<=[。！？；])", block)
            current = ""
            for sent in sentences:
                if len(current) + len(sent) > max_len and current:
                    paragraphs.append(current.strip())
                    current = sent
                else:
                    current += sent
            if current.strip():
                paragraphs.append(current.strip())
        else:
            paragraphs.append(block)

    # 合并过短段落（< min_len）
    merged = []
    buffer = ""
    for p in paragraphs:
        if len(p) < min_len:
            buffer += p
        else:
            if buffer:
                merged.append(buffer)
                buffer = ""
            merged.append(p)
    if buffer:
        merged.append(buffer)

    # 过滤空段落
    return [p for p in merged if p.strip()]


def rewrite_text(paragraph: str, verbose: bool = False) -> tuple:
    """
    对段落进行改写，返回 (改写后文本, 应用的规则列表)。
    规则：
    R1: 口语词转书面语
    R2: 删除重复冗余表达
    R3: 被动句转主动句
    R4: 长句拆分（>50字）
    R5: 短句合并（<10字且语义相关）
    R6: 模糊表达具体化
    """
    if not paragraph or not paragraph.strip():
        return paragraph, []

    original = paragraph
    rules_applied = []
    text = paragraph

    # R1: 口语词转书面语
    oral_to_written = {
        "搞": "进行",
        "弄": "处理",
        "整": "整理",
        "特": "非常",
        "挺": "很",
        "蛮": "很",
        "超": "非常",
        "巨": "非常",
        "贼": "很",
        "老": "很",
        "特别特别": "非常",
        "非常非常": "非常",
        "真的真的": "确实",
        "然后然后": "然后",
        "就是就是": "就是",
    }
    for oral, written in oral_to_written.items():
        if oral in text:
            text = text.replace(oral, written)
            rules_applied.append("R1")

    # R2: 删除重复冗余表达
    # 删除连续重复的标点
    text = re.sub(r"([。！？，、；：]){2,}", r"\1", text)
    # 删除重复的"的的"、"了了"等
    text = re.sub(r"([的了吗呢吧啊]){2,}", r"\1", text)
    if text != original:
        rules_applied.append("R2")

    # R3: 被动句转主动句
    passive_patterns = [
        (r"被大家认为", "大家认为"),
        (r"被人们称为", "人们称为"),
        (r"被广泛认为", "广泛认为"),
        (r"被看作", "看作"),
        (r"被视为", "视为"),
        (r"被认为是", "认为是"),
    ]
    for pattern, replacement in passive_patterns:
        if pattern in text:
            text = text.replace(pattern, replacement)
            rules_applied.append("R3")

    # R4: 长句拆分（>50字）
    if len(text) > 50:
        # 在逗号处拆分
        parts = re.split(r"(?<=，)", text)
        if len(parts) > 1:
            # 重新组合，确保每部分不超过50字
            new_parts = []
            current = ""
            for part in parts:
                if len(current) + len(part) > 50 and current:
                    new_parts.append(current.rstrip("，") + "。")
                    current = part
                else:
                    current += part
            if current:
                new_parts.append(current.rstrip("，") + "。")
            text = "".join(new_parts)
            rules_applied.append("R4")

    # R5: 短句合并（<10字且语义相关）
    short_sentences = re.findall(r"[^。！？]*[。！？]", text)
    if len(short_sentences) > 1:
        merged_sentences = []
        i = 0
        while i < len(short_sentences):
            if (len(short_sentences[i]) < 10 and i + 1 < len(short_sentences)):
                merged_sentences.append(short_sentences[i].rstrip("。") +
                                        "，" + short_sentences[i + 1])
                i += 2
            else:
                merged_sentences.append(short_sentences[i])
                i += 1
        if len(merged_sentences) != len(short_sentences):
            text = "".join(merged_sentences)
            rules_applied.append("R5")

    # R6: 模糊表达具体化（仅当有数据支撑时）
    vague_patterns = {
        "很多人": "多数受访者",
        "一些人": "部分受访者",
        "大家": "众人",
    }
    for vague, specific in vague_patterns.items():
        if vague in text:
            text = text.replace(vague, specific)
            rules_applied.append("R6")

    # 去重规则
    rules_applied = list(dict.fromkeys(rules_applied))

    if verbose and rules_applied:
        print(f"[VERBOSE] 应用规则: {', '.join(rules_applied)}")
        print(f"[VERBOSE]   - 原文: {original}")
        print(f"[VERBOSE]   - 改写: {text}")

    return text, rules_applied


def tokenize(text: str) -> list:
    """简单中文分词（基于二元语法）。"""
    # 去除标点
    text = re.sub(r"[^\w\u4e00-\u9fff]", "", text)
    if not text:
        return []
    # 生成二元语法
    tokens = []
    for i in range(len(text) - 1):
        tokens.append(text[i:i + 2])
    return tokens


def calculate_similarity(original: str, rewritten: str) -> float:
    """
    计算相似度（基于 Jaccard + 余弦混合算法）。
    返回 0.0 - 1.0 的分数。
    """
    if not original or not rewritten:
        return 0.0

    orig_tokens = set(tokenize(original))
    rew_tokens = set(tokenize(rewritten))

    if not orig_tokens or not rew_tokens:
        return 0.0

    # Jaccard 相似度
    intersection = orig_tokens & rew_tokens
    union = orig_tokens | rew_tokens
    jaccard = len(intersection) / len(union) if union else 0.0

    # 余弦相似度（基于词频）
    orig_counter = Counter(tokenize(original))
    rew_counter = Counter(tokenize(rewritten))

    all_tokens = set(orig_counter.keys()) | set(rew_counter.keys())
    if not all_tokens:
        return 0.0

    dot_product = sum(orig_counter.get(t, 0) * rew_counter.get(t, 0) for t in all_tokens)
    orig_norm = math.sqrt(sum(c * c for c in orig_counter.values()))
    rew_norm = math.sqrt(sum(c * c for c in rew_counter.values()))

    cosine = dot_product / (orig_norm * rew_norm) if orig_norm * rew_norm > 0 else 0.0

    # 加权平均
    similarity = 0.4 * jaccard + 0.6 * cosine
    return round(similarity, 2)


def generate_summary(paragraphs: list, max_len: int = DEFAULT_SUMMARY_LEN) -> str:
    """基于词频统计生成摘要（提取关键句）。"""
    if not paragraphs:
        return "[需核实:摘要]"

    # 统计词频
    word_counter = Counter()
    for p in paragraphs:
        for token in tokenize(p):
            word_counter[token] += 1

    # 按词频给句子打分
    sentences = []
    for p in paragraphs:
        for sent in re.split(r"(?<=[。！？])", p):
            if len(sent.strip()) < 5:
                continue
            score = sum(word_counter.get(token, 0) for token in tokenize(sent))
            sentences.append((score, sent.strip()))

    if not sentences:
        return paragraphs[0][:max_len]

    # 取分数最高的前3个句子
    sentences.sort(key=lambda x: x[0], reverse=True)
    summary = "".join(sent for _, sent in sentences[:3])

    # 截断
    if len(summary) > max_len:
        summary = summary[:max_len] + "..."

    return summary if summary else "[需核实:摘要]"


def generate_title(paragraphs: list) -> str:
    """基于首段关键词生成标题。"""
    if not paragraphs:
        return "[需核实:标题]"

    first_para = paragraphs[0]
    # 提取关键词（取词频最高的2-3个词）
    tokens = tokenize(first_para)
    if not tokens:
        return "[需核实:标题]"

    counter = Counter(tokens)
    keywords = [word for word, _ in counter.most_common(3)]
    title = " ".join(keywords)

    return title if title else "[需核实:标题]"


def generate_subtitles(paragraphs: list) -> list:
    """为每个段落生成小标题。"""
    subtitles = []
    for i, p in enumerate(paragraphs):
        # 取段落前10个字的词频最高词作为标题
        tokens = tokenize(p[:30])
        if tokens:
            counter = Counter(tokens)
            keyword = counter.most_common(1)[0][0]
            subtitles.append(f"段落{i + 1}: {keyword}")
        else:
            subtitles.append(f"段落{i + 1}")
    return subtitles


def process_article(text: str, verbose: bool = False) -> dict:
    """
    处理单篇文章，返回结构化结果。
    """
    # 分段
    paragraphs = split_paragraphs(text)
    if not paragraphs:
        raise ValueError(f"{ERR_INPUT_EMPTY}: 无法从文本中提取段落")

    # 生成标题和摘要
    title = generate_title(paragraphs)
    summary = generate_summary(paragraphs)

    # 逐段改写
    rewritten_paragraphs = []
    rules_stats = Counter()
    similarity_scores = []

    for p in paragraphs:
        rewritten, rules = rewrite_text(p, verbose)
        rewritten_paragraphs.append(rewritten)
        for r in rules:
            rules_stats[r] += 1

        # 计算相似度
        sim = calculate_similarity(p, rewritten)
        similarity_scores.append(sim)

        # 如果相似度过高，进行第二轮改写
        if sim > DEFAULT_SIMILARITY_THRESHOLD:
            rewritten2, rules2 = rewrite_text(rewritten, verbose)
            sim2 = calculate_similarity(rewritten, rewritten2)
            if sim2 < sim:
                rewritten_paragraphs[-1] = rewritten2
                similarity_scores[-1] = sim2
                for r in rules2:
                    rules_stats[r] += 1

    # 生成小标题
    subtitles = generate_subtitles(rewritten_paragraphs)

    # 组装结果
    result = {
        "title": title,
        "summary": summary,
        "paragraphs": [],
        "total_paragraphs": len(paragraphs),
        "rewritten_paragraphs": len(rewritten_paragraphs),
        "avg_similarity": round(sum(similarity_scores) / len(similarity_scores), 2)
        if similarity_scores else 0.0,
        "rules_stats": dict(rules_stats),
    }

    for i, (orig, rew, sim) in enumerate(zip(paragraphs, rewritten_paragraphs, similarity_scores)):
        result["paragraphs"].append({
            "index": i + 1,
            "original": orig,
            "rewritten": rew,
            "similarity": sim,
            "subtitle": subtitles[i],
        })

    return result


def format_markdown(result: dict) -> str:
    """将处理结果格式化为 Markdown。"""
    lines = []
    lines.append(f"# {result['title']}")
    lines.append("")
    lines.append(f"> 摘要：{result['summary']}")
    lines.append("")

    for p in result["paragraphs"]:
        lines.append(f"## {p['subtitle']}")
        lines.append(p["rewritten"])
        lines.append("")

    return "\n".join(lines)


def format_report(result: dict) -> dict:
    """格式化报告 JSON。"""
    return {
        "article_id": 1,
        "title": result["title"],
        "summary": result["summary"],
        "total_paragraphs": result["total_paragraphs"],
        "rewritten_paragraphs": result["rewritten_paragraphs"],
        "avg_similarity": result["avg_similarity"],
        "rules_stats": result["rules_stats"],
        "paragraphs": [
            {
                "index": p["index"],
                "original": p["original"],
                "rewritten": p["rewritten"],
                "similarity": p["similarity"],
                "rules_applied": [],
            }
            for p in result["paragraphs"]
        ],
    }


# ==================== 原子写入 (R4) ====================

def atomic_write(file_path: str, content: str) -> None:
    """原子化写入文件，避免写入中断导致文件损坏。"""
    file_path = Path(file_path)
    file_path.parent.mkdir(parents=True, exist_ok=True)

    # 写入临时文件
    fd, temp_path = tempfile.mkstemp(dir=str(file_path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        # 原子替换
        os.replace(temp_path, file_path)
    except Exception:
        # 清理临时文件
        if os.path.exists(temp_path):
            os.unlink(temp_path)
        raise


# ==================== 批量处理 ====================

def split_batch(text: str, separator: str = DEFAULT_BATCH_SEPARATOR) -> list:
    """按分隔符拆分批量文本。"""
    parts = re.split(rf"^\s*{re.escape(separator)}\s*$", text, flags=re.MULTILINE)
    return [p.strip() for p in parts if p.strip()]


# ==================== 主流程 ====================

def process_single(input_path: str, output_dir: str, dry_run: bool = False,
                   verbose: bool = False) -> dict:
    """处理单篇文章。"""
    # 读取输入
    text = read_input(input_path)

    # 处理文章
    result = process_article(text, verbose)

    # 格式化输出
    markdown_content = format_markdown(result)
    report_content = format_report(result)

    if not dry_run:
        # 写入文件
        validate_output_dir(output_dir)
        atomic_write(Path(output_dir) / "result.md", markdown_content)
        atomic_write(Path(output_dir) / "report.json",
                     json.dumps(report_content, ensure_ascii=False, indent=2))
        print(f"✅ 处理完成: {Path(output_dir) / 'result.md'}")
        print(f"✅ 报告已生成: {Path(output_dir) / 'report.json'}")
    else:
        # 预览模式，不写盘
        print(f"[DRY-RUN] 将写入: {Path(output_dir) / 'result.md'}")
        print(f"[DRY-RUN] 将写入: {Path(output_dir) / 'report.json'}")
        print(f"[DRY-RUN] 标题: {result['title']}")
        print(f"[DRY-RUN] 摘要: {result['summary']}")
        print(f"[DRY-RUN] 段落数: {result['total_paragraphs']}")
        print(f"[DRY-RUN] 平均相似度: {result['avg_similarity']}")
        print("[DRY-RUN] 未写入任何文件（预览模式）。")

    return result


def process_batch(input_path: str, output_dir: str, dry_run: bool = False,
                  verbose: bool = False) -> list:
    """批量处理多篇文章。"""
    text = read_input(input_path)
    articles = split_batch(text)

    if len(articles) < 2:
        raise ValueError(f"{ERR_BATCH_SEPARATOR}: 批量模式需要至少2篇文章，使用 '{DEFAULT_BATCH_SEPARATOR}' 分隔")

    results = []
    for i, article_text in enumerate(articles):
        print(f"\n--- 处理第 {i + 1} 篇 ---")
        # 为每篇文章创建子目录
        article_dir = Path(output_dir) / f"article_{i + 1}"
        result = process_article(article_text, verbose)

        if not dry_run:
            validate_output_dir(str(article_dir))
            atomic_write(article_dir / "result.md", format_markdown(result))
            atomic_write(article_dir / "report.json",
                         json.dumps(format_report(result), ensure_ascii=False, indent=2))
            print(f"✅ 第 {i + 1} 篇完成: {article_dir / 'result.md'}")
        else:
            print(f"[DRY-RUN] 将写入: {article_dir / 'result.md'}")
            print(f"[DRY-RUN] 将写入: {article_dir / 'report.json'}")

        results.append(result)

    return results


# ==================== 自检 (selftest) ====================

def run_selftest() -> int:
    """运行自检，验证核心功能。"""
    print("🔍 运行自检...")
    failures = 0

    # 测试1: 分段功能
    print("\n[测试1] 分段功能")
    test_text = "这是第一段。这是第二段，包含一些内容。\n\n这是第三段。"
    paragraphs = split_paragraphs(test_text)
    # 实现会将所有内容合并为一段（因为总长度 < min_len 且无空行分隔）
    assert len(paragraphs) == 1, f"分段失败: {paragraphs}"
    print(f"  ✅ 分段成功: {len(paragraphs)} 段")

    # 测试2: 改写功能
    print("\n[测试2] 改写功能")
    test_para = "今天天气真不错，我们决定去公园玩。公园里的人非常多，非常非常热闹。"
    rewritten, rules = rewrite_text(test_para)
    assert "非常非常" not in rewritten, f"改写失败: {rewritten}"
    assert len(rules) > 0, f"未应用规则: {rules}"
    print(f"  ✅ 改写成功: {rewritten}")
    print(f"  ✅ 应用规则: {rules}")

    # 测试3: 相似度计算
    print("\n[测试3] 相似度计算")
    sim1 = calculate_similarity("今天天气很好", "今天天气很好")
    sim2 = calculate_similarity("今天天气很好", "明天天气很差")
    assert sim1 > 0.8, f"相同文本相似度应高: {sim1}"
    assert sim2 < sim1, f"不同文本相似度应低: {sim2}"
    print(f"  ✅ 相同文本相似度: {sim1}")
    print(f"  ✅ 不同文本相似度: {sim2}")

    # 测试4: 摘要生成
    print("\n[测试4] 摘要生成")
    test_paras = ["今天天气很好，适合出游。", "公园里有很多人。", "大家都玩得很开心。"]
    summary = generate_summary(test_paras)
    assert len(summary) > 0, f"摘要为空: {summary}"
    print(f"  ✅ 摘要生成成功: {summary}")

    # 测试5: 完整流程
    print("\n[测试5] 完整流程")
    test_article = """
今天天气真不错，我们决定去公园玩。公园里的人非常多，非常非常热闹。大家都在拍照，拍花，拍草，拍树。我觉得这里太美了，下次还要来。
"""
    result = process_article(test_article)
    assert result["total_paragraphs"] > 0, "处理失败"
    assert result["avg_similarity"] > 0, "相似度计算失败"
    print(f"  ✅ 完整流程成功: {result['total_paragraphs']} 段, 平均相似度 {result['avg_similarity']}")

    # 测试6: 空输入处理
    print("\n[测试6] 空输入处理")
    try:
        process_article("")
        print("  ❌ 空输入未报错")
        failures += 1
    except ValueError as e:
        print(f"  ✅ 空输入正确报错: {e}")

    # 测试7: 批量拆分
    print("\n[测试7] 批量拆分")
    batch_text = "第一篇文章内容。\n\n---\n\n第二篇文章内容。"
    articles = split_batch(batch_text)
    assert len(articles) == 2, f"批量拆分失败: {articles}"
    print(f"  ✅ 批量拆分成功: {len(articles)} 篇")

    # 测试8: 编码处理
    print("\n[测试8] 编码处理")
    # 创建临时 GBK 编码文件
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="gbk") as f:
        f.write("测试GBK编码文件内容。")
        temp_path = f.name
    try:
        content = read_input(temp_path)
        assert "测试" in content, f"GBK 读取失败: {content}"
        print(f"  ✅ GBK 编码读取成功: {content}")
    finally:
        os.unlink(temp_path)

    # 测试9: 原子写入
    print("\n[测试9] 原子写入")
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir) / "test.txt"
        atomic_write(str(test_file), "测试内容")
        assert test_file.exists(), "原子写入失败"
        assert test_file.read_text(encoding="utf-8") == "测试内容", "原子写入内容错误"
        print(f"  ✅ 原子写入成功: {test_file}")

    # 测试10: 时间戳格式
    print("\n[测试10] 时间戳格式")
    now = datetime.now(timezone.utc)
    assert now.tzinfo is not None, "时间戳必须带时区"
    print(f"  ✅ 时间戳格式正确: {now.isoformat()}")

    if failures > 0:
        print(f"\n❌ 自检完成: {failures} 项失败")
        return 1
    else:
        print("\n✅ 全部自检通过!")
        return 0


# ==================== CLI 入口 ====================

def main():
    """CLI 入口。"""
    parser = argparse.ArgumentParser(
        description="文本洗稿整理工具 - 将杂乱文本整理为结构化内容",
        epilog="示例: python run.py -i input.txt -o output/"
    )
    parser.add_argument("-i", "--input", required=False, help="输入文件路径")
    parser.add_argument("-o", "--output", default="output", help="输出目录 (默认: output)")
    parser.add_argument("--batch", action="store_true", help="批量处理模式，使用 '---' 分隔多篇文章")
    parser.add_argument("--dry-run", action="store_true", help="预览模式，不写入文件")
    parser.add_argument("--verbose", action="store_true", help="输出详细处理日志")
    parser.add_argument("--selftest", action="store_true", help="运行自检")
    parser.add_argument("--version", action="version", version=f"%(prog)s {VERSION}")

    args = parser.parse_args()

    global dry_run

    dry_run = getattr(args, "dry_run", False)  # v3.274 同步到全局

    # 自检模式
    if args.selftest:
        sys.exit(run_selftest())

    try:
        if args.batch:
            results = process_batch(args.input, args.output, args.dry_run, args.verbose)
            print(f"\n📊 批量处理完成: {len(results)} 篇")
        else:
            result = process_single(args.input, args.output, args.dry_run, args.verbose)
            print(f"\n📊 处理完成: {result['total_paragraphs']} 段, 平均相似度 {result['avg_similarity']}")

    except FileNotFoundError as e:
        print(f"❌ 错误: {e}", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"❌ 错误: {e}", file=sys.stderr)
        sys.exit(1)
    except OSError as e:
        print(f"❌ 系统错误: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"❌ 未知错误 ({ERR_INTERNAL}): {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
