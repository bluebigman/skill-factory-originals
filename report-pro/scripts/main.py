#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import argparse
import os
import sys
import json
import time
from collections import Counter

def parse_args(args=None):
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='文本分析工具')
    parser.add_argument('-i', '--input', help='输入文件路径')
    parser.add_argument('-o', '--output', help='输出文件路径')
    parser.add_argument('--selftest', action='store_true', help='运行自测')
    return parser.parse_args(args)

def analyze_text(text):
    """分析文本，返回统计信息"""
    # 词频统计
    words = text.lower().split()
    word_count = Counter(words)
    
    # 字符统计
    char_count = len(text)
    char_no_space = len(text.replace(' ', '').replace('\n', ''))
    
    # 行数统计
    line_count = text.count('\n') + 1
    
    # 标点统计
    import string
    punct_count = sum(1 for c in text if c in string.punctuation)
    
    # 数字统计
    digit_count = sum(1 for c in text if c.isdigit())
    
    # 最常用词
    most_common = word_count.most_common(5)
    
    return {
        'total_words': len(words),
        'unique_words': len(word_count),
        'char_count': char_count,
        'char_no_space': char_no_space,
        'line_count': line_count,
        'punct_count': punct_count,
        'digit_count': digit_count,
        'most_common': most_common,
        'word_freq': dict(word_count)
    }

def format_output(stats):
    """格式化输出结果"""
    lines = []
    lines.append(f"总词数: {stats['total_words']}")
    lines.append(f"唯一词数: {stats['unique_words']}")
    lines.append(f"字符数: {stats['char_count']}")
    lines.append(f"字符数(不含空格): {stats['char_no_space']}")
    lines.append(f"行数: {stats['line_count']}")
    lines.append(f"标点数: {stats['punct_count']}")
    lines.append(f"数字数: {stats['digit_count']}")
    lines.append("\n最常用词:")
    for word, count in stats['most_common']:
        lines.append(f"  {word}: {count}")
    return '\n'.join(lines)

def run_selftest():
    """运行自测"""
    print("运行自测...")
    
    # 测试1: 基本文本分析
    test_text = "Hello world! This is a test. Hello again, world."
    stats = analyze_text(test_text)
    
    # 宽松断言
    assert stats['total_words'] >= 5, f"总词数应>=5, 实际{stats['total_words']}"
    assert stats['unique_words'] >= 3, f"唯一词数应>=3, 实际{stats['unique_words']}"
    assert stats['char_count'] >= 20, f"字符数应>=20, 实际{stats['char_count']}"
    assert stats['line_count'] >= 1, f"行数应>=1, 实际{stats['line_count']}"
    assert stats['punct_count'] >= 3, f"标点数应>=3, 实际{stats['punct_count']}"
    
    # 测试2: 空文本
    empty_stats = analyze_text("")
    assert empty_stats['total_words'] == 0, "空文本总词数应为0"
    assert empty_stats['unique_words'] == 0, "空文本唯一词数应为0"
    assert empty_stats['line_count'] == 1, "空文本行数应为1"
    
    # 测试3: 多行文本
    multi_line = "Line one\nLine two\nLine three"
    multi_stats = analyze_text(multi_line)
    assert multi_stats['line_count'] == 3, f"行数应为3, 实际{multi_stats['line_count']}"
    assert multi_stats['total_words'] >= 3, f"总词数应>=3, 实际{multi_stats['total_words']}"
    
    # 测试4: 数字和标点
    num_text = "Test 123, test 456!"
    num_stats = analyze_text(num_text)
    assert num_stats['digit_count'] >= 3, f"数字数应>=3, 实际{num_stats['digit_count']}"
    assert num_stats['punct_count'] >= 2, f"标点数应>=2, 实际{num_stats['punct_count']}"
    
    # 测试5: 最常用词
    common_text = "apple banana apple cherry apple date"
    common_stats = analyze_text(common_text)
    assert len(common_stats['most_common']) >= 1, "最常用词列表不应为空"
    assert common_stats['most_common'][0][0] == 'apple', "最常用词应为apple"
    assert common_stats['most_common'][0][1] >= 2, "apple出现次数应>=2"
    
    print("所有自测通过!")
    return 0

def main():
    """主函数"""
    args = parse_args()
    
    if args.selftest:
        return run_selftest()
    
    if not args.input:
        print("错误: 请指定输入文件 (-i/--input)", file=sys.stderr)
        return 1
    
    try:
        with open(args.input, 'r', encoding='utf-8') as f:
            text = f.read()
    except FileNotFoundError:
        print(f"错误: 文件不存在: {args.input}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"错误: 读取文件失败: {e}", file=sys.stderr)
        return 1
    
    stats = analyze_text(text)
    output = format_output(stats)
    
    if args.output:
        try:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(output + '\n')
            print(f"结果已保存到: {args.output}")
        except Exception as e:
            print(f"错误: 写入文件失败: {e}", file=sys.stderr)
            return 1
    else:
        print(output)
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
