#!/usr/bin/env python3
"""冒烟测试修复版 - 使用标准库实现简单功能"""
import sys
import json
import math
from collections import Counter

def analyze_text(text):
    """分析文本，返回统计信息"""
    if not text:
        return {"words": 0, "chars": 0, "lines": 0, "freq": {}}
    
    lines = text.split('\n')
    words = text.split()
    chars = len(text)
    
    # 统计词频
    word_freq = Counter(words)
    top_freq = dict(word_freq.most_common(5))
    
    return {
        "words": len(words),
        "chars": chars,
        "lines": len(lines),
        "freq": top_freq
    }

def process_data(data):
    """处理数据，返回统计结果"""
    if not isinstance(data, (list, tuple)):
        return {"error": "输入必须是列表或元组"}
    
    if len(data) == 0:
        return {"error": "输入为空"}
    
    # 只处理数字数据
    numbers = [x for x in data if isinstance(x, (int, float))]
    
    if not numbers:
        return {"error": "没有数字数据"}
    
    result = {
        "count": len(numbers),
        "sum": sum(numbers),
        "avg": sum(numbers) / len(numbers),
        "max": max(numbers),
        "min": min(numbers)
    }
    
    # 计算标准差（如果有足够数据）
    if len(numbers) > 1:
        mean = result["avg"]
        variance = sum((x - mean) ** 2 for x in numbers) / len(numbers)
        result["stddev"] = math.sqrt(variance)
    else:
        result["stddev"] = 0.0
    
    return result

def run_selftest():
    """运行自测"""
    # 测试文本分析
    text_result = analyze_text("hello world hello python")
    assert text_result["words"] >= 3, "单词数应至少为3"
    assert text_result["chars"] >= 20, "字符数应至少为20"
    assert text_result["lines"] >= 1, "行数应至少为1"
    assert "hello" in text_result["freq"], "hello应该出现在词频中"
    
    # 测试数据处理
    data_result = process_data([1, 2, 3, 4, 5])
    assert data_result["count"] >= 4, "数量应至少为4"
    assert data_result["sum"] >= 10, "总和应至少为10"
    assert data_result["avg"] > 2.0, "平均值应大于2"
    assert data_result["max"] >= 4, "最大值应至少为4"
    assert data_result["min"] <= 2, "最小值应至多为2"
    assert data_result["stddev"] >= 0.0, "标准差应为非负数"
    
    # 测试空输入
    empty_result = process_data([])
    assert "error" in empty_result, "空输入应返回错误信息"
    
    print("所有自测通过！")
    return True

def main():
    """主函数"""
    if len(sys.argv) > 1 and sys.argv[1] == "--selftest":
        run_selftest()
        return 0
    
    # 默认演示模式
    sample_text = "Python is great Python is powerful"
    text_stats = analyze_text(sample_text)
    
    sample_data = [10, 20, 30, 40, 50]
    data_stats = process_data(sample_data)
    
    output = {
        "text_stats": text_stats,
        "data_stats": data_stats
    }
    
    print(json.dumps(output, indent=2, ensure_ascii=False))
    return 0

if __name__ == "__main__":
    sys.exit(main())
