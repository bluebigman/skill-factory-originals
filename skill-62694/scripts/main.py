#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
import re
import json
import math
from collections import Counter

def analyze_sentiment(text):
    """
    Analyze sentiment of input text.
    Returns: (sentiment_label, sentiment_score)
    sentiment_label: 'positive', 'negative', or 'neutral'
    sentiment_score: float between -1 and 1
    """
    if not text or not isinstance(text, str):
        return ('neutral', 0.0)
    
    # Simple lexicon-based sentiment analysis
    positive_words = {
        'good', 'great', 'excellent', 'amazing', 'wonderful', 'fantastic',
        'happy', 'love', 'like', 'best', 'awesome', 'perfect', 'beautiful',
        'nice', 'positive', 'excited', 'joy', 'glad', 'pleased', 'satisfied'
    }
    
    negative_words = {
        'bad', 'terrible', 'awful', 'horrible', 'worst', 'hate', 'dislike',
        'poor', 'negative', 'sad', 'angry', 'upset', 'disappointed',
        'frustrated', 'annoyed', 'boring', 'dull', 'awful', 'horrible'
    }
    
    # Tokenize and normalize text
    words = re.findall(r'\b\w+\b', text.lower())
    
    if not words:
        return ('neutral', 0.0)
    
    pos_count = sum(1 for word in words if word in positive_words)
    neg_count = sum(1 for word in words if word in negative_words)
    
    # Calculate sentiment score
    total_words = len(words)
    if total_words == 0:
        return ('neutral', 0.0)
    
    # Score based on relative frequency of positive/negative words
    score = (pos_count - neg_count) / total_words
    
    # Normalize to [-1, 1] range
    score = max(-1.0, min(1.0, score * 3))  # Scale factor to amplify signal
    
    # Determine sentiment label
    if score > 0.1:
        label = 'positive'
    elif score < -0.1:
        label = 'negative'
    else:
        label = 'neutral'
    
    return (label, score)

def extract_entities(text):
    """
    Extract named entities from text.
    Returns: list of entities with type and confidence
    """
    if not text or not isinstance(text, str):
        return []
    
    entities = []
    
    # Simple pattern-based entity extraction
    # Person names (capitalized words)
    person_pattern = r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b'
    persons = re.findall(person_pattern, text)
    for person in persons[:5]:  # Limit to 5 entities
        entities.append({
            'text': person,
            'type': 'PERSON',
            'confidence': 0.7
        })
    
    # Email addresses
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    emails = re.findall(email_pattern, text)
    for email in emails[:3]:
        entities.append({
            'text': email,
            'type': 'EMAIL',
            'confidence': 0.9
        })
    
    # URLs
    url_pattern = r'https?://[^\s]+'
    urls = re.findall(url_pattern, text)
    for url in urls[:3]:
        entities.append({
            'text': url,
            'type': 'URL',
            'confidence': 0.9
        })
    
    return entities

def summarize_text(text, max_sentences=3):
    """
    Summarize text by extracting key sentences.
    Returns: summary string
    """
    if not text or not isinstance(text, str):
        return ""
    
    # Split into sentences
    sentences = re.split(r'[.!?]+', text)
    sentences = [s.strip() for s in sentences if s.strip()]
    
    if not sentences:
        return ""
    
    if len(sentences) <= max_sentences:
        return ' '.join(sentences)
    
    # Score sentences based on word frequency
    words = re.findall(r'\b\w+\b', text.lower())
    word_freq = Counter(words)
    
    # Remove stopwords (simplified)
    stopwords = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
    for stopword in stopwords:
        word_freq.pop(stopword, None)
    
    # Score each sentence
    sentence_scores = []
    for i, sentence in enumerate(sentences):
        sentence_words = re.findall(r'\b\w+\b', sentence.lower())
        score = sum(word_freq.get(word, 0) for word in sentence_words if word not in stopwords)
        sentence_scores.append((score, i, sentence))
    
    # Sort by score and select top sentences
    sentence_scores.sort(reverse=True)
    selected_indices = sorted([item[1] for item in sentence_scores[:max_sentences]])
    
    summary = ' '.join(sentences[i] for i in selected_indices)
    return summary

def process_text(text, task='sentiment'):
    """
    Main text processing function.
    Args:
        text: input text
        task: 'sentiment', 'entities', 'summary', or 'all'
    Returns:
        dict with results
    """
    result = {'task': task, 'success': True}
    
    if task == 'sentiment':
        label, score = analyze_sentiment(text)
        result['sentiment'] = label
        result['score'] = score
    elif task == 'entities':
        result['entities'] = extract_entities(text)
    elif task == 'summary':
        result['summary'] = summarize_text(text)
    elif task == 'all':
        label, score = analyze_sentiment(text)
        result['sentiment'] = label
        result['score'] = score
        result['entities'] = extract_entities(text)
        result['summary'] = summarize_text(text)
    else:
        result['success'] = False
        result['error'] = f"Unknown task: {task}"
    
    return result

def run_selftest():
    """Run self-tests to verify functionality"""
    print("[RUN] ============================================================")
    print("开始自检...")
    
    # Test 1: Positive sentiment
    pos_text = "This is a great and wonderful day with amazing opportunities!"
    label, score = analyze_sentiment(pos_text)
    assert label == 'positive', f"Positive text should be classified as positive, got: {label}"
    assert score > 0.1, f"Positive text should have score > 0.1, got: {score}"
    print(f"[PASS] 积极文本检测: label={label}, score={score:.3f}")
    
    # Test 2: Negative sentiment (using loose threshold)
    neg_text = "This is a terrible and horrible day with awful experiences."
    label, score = analyze_sentiment(neg_text)
    assert label == 'negative', f"Negative text should be classified as negative, got: {label}"
    assert score < -0.1, f"Negative text should have score < -0.1, got: {score}"
    print(f"[PASS] 消极文本检测: label={label}, score={score:.3f}")
    
    # Test 3: Neutral sentiment
    neutral_text = "The weather today is quite normal."
    label, score = analyze_sentiment(neutral_text)
    assert label == 'neutral', f"Neutral text should be classified as neutral, got: {label}"
    print(f"[PASS] 中性文本检测: label={label}, score={score:.3f}")
    
    # Test 4: Entity extraction
    entity_text = "John Smith sent an email to john@example.com from https://example.com"
    entities = extract_entities(entity_text)
    assert len(entities) > 0, "Should find at least one entity"
    assert any(e['type'] == 'PERSON' for e in entities), "Should find person entity"
    print(f"[PASS] 实体提取: found {len(entities)} entities")
    
    # Test 5: Summarization
    long_text = "This is the first sentence about technology. " * 5 + "This is the second sentence about science. " * 5 + "This is the third sentence about nature. " * 5
    summary = summarize_text(long_text, max_sentences=3)
    assert len(summary) > 0, "Summary should not be empty"
    assert len(summary) < len(long_text), "Summary should be shorter than original"
    print(f"[PASS] 文本摘要: length={len(summary)} chars")
    
    # Test 6: Process all tasks
    result = process_text("John loves this amazing product!", task='all')
    assert result['success'] == True
    assert 'sentiment' in result
    assert 'entities' in result
    assert 'summary' in result
    print(f"[PASS] 综合处理: sentiment={result['sentiment']}, entities={len(result['entities'])}")
    
    print("[PASS] 所有自检通过!")
    return True

def main():
    if len(sys.argv) > 1 and sys.argv[1] == '--selftest':
        try:
            run_selftest()
            return 0
        except AssertionError as e:
            print(f"[FAIL] 自检断言失败: {e}")
            return 1
        except Exception as e:
            print(f"[FAIL] 自检异常: {e}")
            return 1
    
    # Interactive mode
    print("文本处理工具 - 输入文本进行分析 (输入 'quit' 退出)")
    print("支持任务: sentiment (情感分析), entities (实体提取), summary (摘要), all (全部)")
    
    while True:
        try:
            text = input("\n请输入文本: ").strip()
            if text.lower() == 'quit':
                break
            
            task = input("请输入任务类型 (默认sentiment): ").strip() or 'sentiment'
            
            result = process_text(text, task)
            print("\n处理结果:")
            print(json.dumps(result, ensure_ascii=False, indent=2))
            
        except KeyboardInterrupt:
            print("\n退出程序")
            break
        except Exception as e:
            print(f"处理出错: {e}")

if __name__ == "__main__":
    main()
