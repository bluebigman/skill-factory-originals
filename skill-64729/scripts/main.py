#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""文本处理工具：分段、改写、相似度计算、摘要生成"""

import argparse
import hashlib
import json
import math
import re
import sys
from collections import Counter
from typing import Dict, List, Optional, Tuple
dry_run = False  # v3.274 模块级 dry-run 标志


def segment_text(text: str, max_length: int = 100) -> List[str]:
    """将文本按段落或长度分段"""
    if not text or not text.strip():
        return []
    
    # 先按段落分割
    paragraphs = [p.strip() for p in re.split(r'\n+', text) if p.strip()]
    segments = []
    
    for para in paragraphs:
        if len(para) <= max_length:
            segments.append(para)
        else:
            # 按句子分割长段落
            sentences = re.split(r'(?<=[。！？!?])', para)
            current = ""
            for sent in sentences:
                if not sent.strip():
                    continue
                if len(current) + len(sent) <= max_length:
                    current += sent
                else:
                    if current:
                        segments.append(current.strip())
                    current = sent
            if current:
                segments.append(current.strip())
    
    return segments


def rewrite_text(text: str, style: str = "formal") -> str:
    """文本改写（简化版：调整标点和格式）"""
    if not text:
        return text
    
    if style == "formal":
        # 正式风格：确保句子以句号结尾
        text = re.sub(r'[！？!?]+', '。', text)
        text = re.sub(r'[，,]+', '，', text)
    elif style == "concise":
        # 简洁风格：去除冗余空格和重复标点
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'([。！？!?])\1+', r'\1', text)
    elif style == "friendly":
        # 友好风格：添加语气词
        text = re.sub(r'。', '哦。', text)
    
    # 确保以标点结尾
    if text and text[-1] not in '。！？!?':
        text += '。'
    
    return text


def calculate_similarity(text1: str, text2: str) -> float:
    """计算两段文本的相似度（基于字符n-gram）"""
    if not text1 or not text2:
        return 0.0
    
    def get_ngrams(text: str, n: int = 3) -> Counter:
        text = re.sub(r'\s+', '', text)
        if len(text) < n:
            return Counter([text])
        return Counter(text[i:i+n] for i in range(len(text) - n + 1))
    
    grams1 = get_ngrams(text1)
    grams2 = get_ngrams(text2)
    
    if not grams1 or not grams2:
        return 0.0
    
    # 计算Jaccard相似度
    intersection = sum((grams1 & grams2).values())
    union = sum((grams1 | grams2).values())
    
    if union == 0:
        return 0.0
    
    return intersection / union


def generate_summary(text: str, max_length: int = 100) -> str:
    """生成文本摘要（提取关键句子）"""
    if not text:
        return ""
    
    # 按句子分割
    sentences = [s.strip() for s in re.split(r'(?<=[。！？!?])', text) if s.strip()]
    
    if not sentences:
        return text[:max_length]
    
    if len(sentences) == 1:
        return sentences[0][:max_length]
    
    # 计算句子得分（基于词频）
    words = re.findall(r'[\u4e00-\u9fff]+|[a-zA-Z]+', text)
    word_freq = Counter(words)
    
    # 计算每个句子的得分
    sentence_scores = []
    for i, sent in enumerate(sentences):
        sent_words = re.findall(r'[\u4e00-\u9fff]+|[a-zA-Z]+', sent)
        if not sent_words:
            score = 0
        else:
            score = sum(word_freq.get(w, 0) for w in sent_words) / len(sent_words)
        # 位置加权：开头和结尾的句子得分更高
        position_weight = 1.0
        if i == 0 or i == len(sentences) - 1:
            position_weight = 1.5
        sentence_scores.append((score * position_weight, sent))
    
    # 按得分排序，选择得分最高的句子
    sentence_scores.sort(key=lambda x: x[0], reverse=True)
    
    # 选择句子直到达到摘要长度
    summary = ""
    for _, sent in sentence_scores:
        if len(summary) + len(sent) <= max_length:
            summary += sent
        else:
            break
    
    # 如果摘要为空，取第一个句子
    if not summary:
        summary = sentences[0][:max_length]
    
    return summary


def process_text(text: str, max_segment_length: int = 100, 
                 rewrite_style: str = "formal", 
                 summary_length: int = 100) -> Dict:
    """完整处理流程"""
    try:
        # 分段
        segments = segment_text(text, max_segment_length)
        
        if not segments:
            return {"error": "E001", "message": "文本为空或无法分段"}
        
        # 改写
        rewritten = [rewrite_text(seg, rewrite_style) for seg in segments]
        
        # 相似度计算（相邻段落间）
        similarities = []
        for i in range(len(segments) - 1):
            sim = calculate_similarity(segments[i], segments[i+1])
            similarities.append(sim)
        
        # 摘要生成
        full_text = "".join(segments)
        summary = generate_summary(full_text, summary_length)
        
        return {
            "segments": segments,
            "rewritten": rewritten,
            "similarities": similarities,
            "summary": summary,
            "segment_count": len(segments)
        }
    except Exception as e:
        return {"error": "E009", "message": str(e)}


def run_selftest() -> bool:
    """自检函数"""
    print("=" * 60)
    print("自检开始 (selftest)")
    print("=" * 60)
    
    test_text = """人工智能是计算机科学的一个分支。
它企图了解智能的实质，并生产出一种新的能以人类智能相似的方式做出反应的智能机器。
该领域的研究包括机器人、语言识别、图像识别、自然语言处理和专家系统等。
人工智能从诞生以来，理论和技术日益成熟，应用领域也不断扩大。
可以设想，未来人工智能带来的科技产品，将会是人类智慧的容器。"""
    
    # 测试1: 输入校验
    print("\n[测试1] 输入校验")
    if not test_text or not isinstance(test_text, str):
        print("  ✗ 输入校验失败")
        return False
    print("  ✓ 输入校验通过")
    
    # 测试2: 分段功能
    print("\n[测试2] 分段功能")
    segments = segment_text(test_text)
    if not segments or len(segments) < 2:
        print(f"  ✗ 分段失败，共 {len(segments)} 段")
        return False
    print(f"  ✓ 分段成功，共 {len(segments)} 段")
    
    # 测试3: 改写功能
    print("\n[测试3] 改写功能")
    try:
        rewritten = rewrite_text(test_text)
        if not rewritten or len(rewritten) < 10:
            print("  ✗ 改写失败")
            return False
        print("  ✓ 改写功能正常")
    except Exception as e:
        print(f"  ✗ 改写异常: {e}")
        return False
    
    # 测试4: 相似度计算
    print("\n[测试4] 相似度计算")
    try:
        sim = calculate_similarity("人工智能是计算机科学", "人工智能是未来科技")
        if sim < 0 or sim > 1:
            print(f"  ✗ 相似度超出范围: {sim}")
            return False
        print(f"  ✓ 相似度计算正常 (示例值: {sim:.2f})")
    except Exception as e:
        print(f"  ✗ 相似度计算异常: {e}")
        return False
    
    # 测试5: 摘要生成
    print("\n[测试5] 摘要生成")
    try:
        summary = generate_summary(test_text, 100)
        if not summary or len(summary) < 20:
            print(f"  ✗ 摘要生成失败 (长度: {len(summary)})")
            return False
        print(f"  ✓ 摘要生成正常 (长度: {len(summary)})")
    except Exception as e:
        print(f"  ✗ 摘要生成异常: {e}")
        return False
    
    # 测试6: 完整处理流程
    print("\n[测试6] 完整处理流程")
    try:
        result = process_text(test_text)
        if "error" in result:
            print(f"  ✗ 处理出错: {result['error']}")
            return False
        if result["segment_count"] < 2:
            print(f"  ✗ 分段数量不足: {result['segment_count']}")
            return False
        if not result["summary"]:
            print("  ✗ 摘要为空")
            return False
        print(f"  ✓ 完整处理成功 (分段: {result['segment_count']}, 摘要长度: {len(result['summary'])})")
    except Exception as e:
        print(f"  ✗ 完整处理异常: {e}")
        return False
    
    print("\n" + "=" * 60)
    print("所有测试通过!")
    print("=" * 60)
    return True


def main():
    parser = argparse.ArgumentParser(description="文本处理工具")
    parser.add_argument("--text", type=str, help="输入文本")
    parser.add_argument("--file", type=str, help="输入文件路径")
    parser.add_argument("--max-segment-length", type=int, default=100, help="最大分段长度")
    parser.add_argument("--rewrite-style", type=str, default="formal", 
                       choices=["formal", "concise", "friendly"], help="改写风格")
    parser.add_argument("--summary-length", type=int, default=100, help="摘要长度")
    parser.add_argument("--selftest", action="store_true", help="运行自检")
    parser.add_argument("--output", type=str, help="输出文件路径")
    
    parser.add_argument("--force", action="store_true")  # R4 强制写盘

    
    parser.add_argument("--dry-run", action="store_true")  # R4 预览模式
    
    args = parser.parse_args()
    
    global dry_run
    
    dry_run = getattr(args, "dry_run", False)  # v3.274 同步到全局
    
    if args.selftest:
        success = run_selftest()
        sys.exit(0 if success else 1)
    
    # 获取输入文本
    text = args.text
    if args.file:
        try:
            with open(args.file, 'r', encoding='utf-8') as f:
                text = f.read()
        except Exception as e:
            print(f"读取文件失败: {e}")
            sys.exit(1)
    
    if not text:
        print("请提供输入文本 (--text 或 --file)")
        sys.exit(1)
    
    # 处理文本
    result = process_text(text, args.max_segment_length, args.rewrite_style, args.summary_length)
    
    if "error" in result:
        print(f"处理失败: {result['error']} - {result.get('message', '')}")
        sys.exit(1)
    
    # 输出结果
    output = {
        "segments": result["segments"],
        "rewritten": result["rewritten"],
        "similarities": result["similarities"],
        "summary": result["summary"],
        "segment_count": result["segment_count"]
    }
    
    if args.output:
        try:
            with open(args.output, 'w', encoding='utf-8') as f:
                json.dump(output, f, ensure_ascii=False, indent=2)
            print(f"结果已保存到 {args.output}")
        except Exception as e:
            print(f"保存文件失败: {e}")
            sys.exit(1)
    else:
        print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
