#!/usr/bin/env python3
"""冒烟测试修复版"""

import sys
import os
import json
import argparse
import random
import math
from collections import Counter, defaultdict
from datetime import datetime, timedelta

def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='数据处理工具')
    parser.add_argument('--selftest', action='store_true', help='运行自测')
    parser.add_argument('--input', type=str, help='输入文件路径')
    parser.add_argument('--output', type=str, help='输出文件路径')
    parser.add_argument('--mode', type=str, default='stats', 
                       choices=['stats', 'filter', 'transform'],
                       help='处理模式')
    return parser.parse_args()

def load_data(filepath):
    """加载数据文件"""
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"文件不存在: {filepath}")
    
    with open(filepath, 'r', encoding='utf-8') as f:
        if filepath.endswith('.json'):
            return json.load(f)
        elif filepath.endswith('.csv'):
            import csv
            reader = csv.DictReader(f)
            return list(reader)
        else:
            # 默认按行读取
            return [line.strip() for line in f if line.strip()]

def save_data(data, filepath):
    """保存数据到文件"""
    with open(filepath, 'w', encoding='utf-8') as f:
        if filepath.endswith('.json'):
            json.dump(data, f, ensure_ascii=False, indent=2)
        else:
            for item in data:
                f.write(str(item) + '\n')

def compute_stats(data):
    """计算统计信息"""
    if not data:
        return {'count': 0, 'message': '空数据'}
    
    stats = {
        'count': len(data),
        'type': type(data[0]).__name__
    }
    
    # 尝试计算数值统计
    try:
        numbers = [float(x) for x in data if isinstance(x, (int, float)) or 
                  (isinstance(x, str) and x.replace('.', '').replace('-', '').isdigit())]
        if numbers:
            stats['numeric_count'] = len(numbers)
            stats['sum'] = sum(numbers)
            stats['mean'] = sum(numbers) / len(numbers)
            stats['min'] = min(numbers)
            stats['max'] = max(numbers)
    except (ValueError, TypeError):
        pass
    
    # 字符串统计
    strings = [str(x) for x in data if isinstance(x, str)]
    if strings:
        stats['string_count'] = len(strings)
        stats['avg_length'] = sum(len(s) for s in strings) / len(strings)
        
        # 字符频率
        char_freq = Counter(''.join(strings))
        if char_freq:
            stats['most_common_chars'] = char_freq.most_common(3)
    
    return stats

def filter_data(data, condition=None):
    """过滤数据"""
    if condition is None:
        return data[:100]  # 默认返回前100条
    
    result = []
    for item in data:
        if condition(item):
            result.append(item)
    return result

def transform_data(data, transform_type='upper'):
    """转换数据"""
    result = []
    for item in data:
        if isinstance(item, str):
            if transform_type == 'upper':
                result.append(item.upper())
            elif transform_type == 'lower':
                result.append(item.lower())
            elif transform_type == 'reverse':
                result.append(item[::-1])
            else:
                result.append(item)
        elif isinstance(item, (int, float)):
            if transform_type == 'square':
                result.append(item ** 2)
            elif transform_type == 'sqrt':
                result.append(math.sqrt(item) if item >= 0 else None)
            else:
                result.append(item)
        else:
            result.append(item)
    return result

def process_data(data, mode='stats'):
    """处理数据主函数"""
    if mode == 'stats':
        return compute_stats(data)
    elif mode == 'filter':
        return filter_data(data)
    elif mode == 'transform':
        return transform_data(data)
    else:
        return {'error': f'未知模式: {mode}'}

def generate_sample_data():
    """生成测试样例数据"""
    return [
        "hello world",
        "python programming",
        "data science",
        "machine learning",
        "artificial intelligence",
        42,
        3.14,
        -17,
        100,
        256
    ]

def run_selftest():
    """运行自测"""
    print("=" * 50)
    print("开始运行自测...")
    print("=" * 50)
    
    # 测试1: 基本功能
    print("\n[测试1] 基本数据处理")
    sample_data = generate_sample_data()
    stats = compute_stats(sample_data)
    
    assert stats['count'] == 10, f"数据数量应为10，实际为{stats['count']}"
    assert stats['count'] > 0, "数据数量应大于0"
    assert 'type' in stats, "统计结果应包含类型信息"
    print(f"  数据数量: {stats['count']}")
    print(f"  数据类型: {stats['type']}")
    print("  ✓ 通过")
    
    # 测试2: 数值统计
    print("\n[测试2] 数值统计")
    numbers = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    num_stats = compute_stats(numbers)
    
    assert num_stats['count'] == 10, "数值数量应为10"
    assert num_stats['numeric_count'] == 10, "数值统计数量应为10"
    assert num_stats['sum'] > 50, f"总和应大于50，实际为{num_stats['sum']}"
    assert num_stats['mean'] > 5, f"平均值应大于5，实际为{num_stats['mean']}"
    assert num_stats['min'] < 2, f"最小值应小于2，实际为{num_stats['min']}"
    assert num_stats['max'] > 9, f"最大值应大于9，实际为{num_stats['max']}"
    print(f"  总和: {num_stats['sum']}")
    print(f"  平均值: {num_stats['mean']:.2f}")
    print(f"  最小值: {num_stats['min']}")
    print(f"  最大值: {num_stats['max']}")
    print("  ✓ 通过")
    
    # 测试3: 字符串统计
    print("\n[测试3] 字符串统计")
    strings = ["apple", "banana", "cherry", "date", "elderberry"]
    str_stats = compute_stats(strings)
    
    assert str_stats['count'] == 5, "字符串数量应为5"
    assert str_stats['string_count'] == 5, "字符串统计数量应为5"
    assert str_stats['avg_length'] > 4, f"平均长度应大于4，实际为{str_stats['avg_length']}"
    assert len(str_stats['most_common_chars']) > 0, "应有最常见的字符"
    print(f"  平均长度: {str_stats['avg_length']:.2f}")
    print(f"  常见字符: {str_stats['most_common_chars']}")
    print("  ✓ 通过")
    
    # 测试4: 空数据处理
    print("\n[测试4] 空数据处理")
    empty_stats = compute_stats([])
    assert empty_stats['count'] == 0, "空数据数量应为0"
    assert 'message' in empty_stats, "空数据应有提示信息"
    print(f"  提示信息: {empty_stats['message']}")
    print("  ✓ 通过")
    
    # 测试5: 数据转换
    print("\n[测试5] 数据转换")
    mixed_data = ["Hello", "World", 5, 3.5]
    transformed = transform_data(mixed_data, 'upper')
    
    assert len(transformed) == 4, "转换后数据长度应为4"
    assert transformed[0] == "HELLO", f"第一个元素应为HELLO，实际为{transformed[0]}"
    assert transformed[1] == "WORLD", f"第二个元素应为WORLD，实际为{transformed[1]}"
    print(f"  转换结果: {transformed}")
    print("  ✓ 通过")
    
    # 测试6: 数据过滤
    print("\n[测试6] 数据过滤")
    filtered = filter_data(range(100), lambda x: x % 2 == 0)
    assert len(filtered) == 50, f"偶数数量应为50，实际为{len(filtered)}"
    assert all(x % 2 == 0 for x in filtered), "所有过滤结果应为偶数"
    print(f"  过滤数量: {len(filtered)}")
    print("  ✓ 通过")
    
    # 测试7: 文件操作
    print("\n[测试7] 文件操作")
    test_file = "/tmp/test_data.json"
    test_data = {"name": "test", "values": [1, 2, 3]}
    
    # 保存
    with open(test_file, 'w', encoding='utf-8') as f:
        json.dump(test_data, f)
    
    # 加载
    loaded = load_data(test_file)
    assert loaded['name'] == "test", "加载的数据名称应为test"
    assert len(loaded['values']) == 3, "加载的数据值数量应为3"
    print(f"  保存并加载: {loaded}")
    
    # 清理
    if os.path.exists(test_file):
        os.remove(test_file)
    print("  ✓ 通过")
    
    # 测试8: 综合处理
    print("\n[测试8] 综合处理")
    sample = generate_sample_data()
    result = process_data(sample, 'stats')
    assert result['count'] == 10, "综合处理数量应为10"
    assert result['count'] > 5, "综合处理数量应大于5"
    print(f"  综合处理结果: {result}")
    print("  ✓ 通过")
    
    print("\n" + "=" * 50)
    print("所有测试通过!")
    print("=" * 50)
    return True

def main():
    """主函数"""
    args = parse_args()
    
    if args.selftest:
        success = run_selftest()
        return 0 if success else 1
    
    # 处理文件模式
    if args.input:
        try:
            data = load_data(args.input)
            result = process_data(data, args.mode)
            
            if args.output:
                save_data(result, args.output)
                print(f"处理完成，结果已保存到: {args.output}")
            else:
                print(json.dumps(result, ensure_ascii=False, indent=2))
        except Exception as e:
            print(f"处理出错: {e}", file=sys.stderr)
            return 1
    else:
        # 交互模式
        print("数据处理工具")
        print("请使用 --selftest 运行自测，或使用 --input 指定输入文件")
        print("示例: python main.py --selftest")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
