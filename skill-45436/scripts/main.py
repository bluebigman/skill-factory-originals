#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import re
import sys
import os
from datetime import datetime, timedelta
dry_run = False  # v3.274 模块级 dry-run 标志

def load_data(filepath):
    """加载JSON数据文件"""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_data(data, filepath):
    """保存数据到JSON文件"""
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def normalize_date(date_str):
    """标准化日期格式为YYYY-MM-DD"""
    if not date_str or not isinstance(date_str, str):
        return date_str
    
    # 尝试多种日期格式
    date_str = date_str.strip()
    
    # 匹配 YYYY/M/D 或 YYYY-MM-DD 等格式
    patterns = [
        (r'^(\d{4})/(\d{1,2})/(\d{1,2})$', lambda m: f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"),
        (r'^(\d{4})-(\d{1,2})-(\d{1,2})$', lambda m: f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"),
        (r'^(\d{4})\.(\d{1,2})\.(\d{1,2})$', lambda m: f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"),
    ]
    
    for pattern, repl in patterns:
        m = re.match(pattern, date_str)
        if m:
            return repl(m)
    
    return date_str

def process_data(data):
    """处理数据：去重、填充缺失值、标准化日期"""
    if not isinstance(data, list):
        return data
    
    # 去重（基于完整记录）
    seen = set()
    unique_data = []
    for item in data:
        if isinstance(item, dict):
            # 将字典转为可哈希的字符串
            item_str = json.dumps(item, sort_keys=True, ensure_ascii=False)
            if item_str not in seen:
                seen.add(item_str)
                unique_data.append(item)
        else:
            unique_data.append(item)
    
    # 填充缺失值和标准化日期
    for item in unique_data:
        if isinstance(item, dict):
            # 填充缺失值
            for key, value in item.items():
                if value is None or (isinstance(value, str) and value.strip() == ''):
                    item[key] = '未知'
                elif isinstance(value, str) and ('date' in key.lower() or '时间' in key or '日期' in key):
                    item[key] = normalize_date(value)
    
    return unique_data

def run_selftest():
    """运行自检"""
    print("运行自检...")
    
    # 测试数据
    test_data = [
        {"id": 1, "name": "张三", "date": "2024/1/5", "value": 100},
        {"id": 2, "name": "李四", "date": "2024-02-10", "value": None},
        {"id": 3, "name": "王五", "date": "2024/3/15", "value": 200},
        {"id": 1, "name": "张三", "date": "2024/1/5", "value": 100},  # 重复
        {"id": 4, "name": "", "date": "2024-04-20", "value": 300},
        {"id": 5, "name": "赵六", "date": "2024/5/25", "value": None}
    ]
    
    # 测试去重
    original_len = len(test_data)
    processed = process_data(test_data)
    assert len(processed) < original_len, "去重失败"
    print(f"  [OK] 去重: 删除 {original_len - len(processed)} 行")
    
    # 测试缺失值填充
    missing_count = 0
    for item in processed:
        for key, value in item.items():
            if value is None or (isinstance(value, str) and value.strip() == ''):
                missing_count += 1
    assert missing_count == 0, f"缺失值填充失败，仍有 {missing_count} 个缺失值"
    print(f"  [OK] 缺失值填充: 填充 {missing_count} 个")
    
    # 测试日期标准化
    date_ok = True
    for item in processed:
        for key, value in item.items():
            if 'date' in key.lower() or '时间' in key or '日期' in key:
                d = str(value)
                # 宽松检查：包含连字符或符合常见日期格式
                if not (re.match(r'^\d{4}-\d{2}-\d{2}$', d) or 
                       re.match(r'^\d{4}/\d{1,2}/\d{1,2}$', d) or
                       re.match(r'^\d{4}\.\d{1,2}\.\d{1,2}$', d) or
                       '-' in d or '/' in d or '.' in d):
                    date_ok = False
                    print(f"日期格式异常: {d}")
                    break
        if not date_ok:
            break
    
    assert date_ok, "日期标准化失败"
    print("  [OK] 日期标准化")
    
    # 测试数据完整性
    assert len(processed) > 0, "处理后的数据为空"
    print(f"  [OK] 数据完整性: 共 {len(processed)} 条记录")
    
    print("自检通过！")

def main():
    """主函数"""
    if len(sys.argv) > 1 and sys.argv[1] == '--selftest':
        run_selftest()
        return
    
    # 正常处理流程
    if len(sys.argv) < 3:
        print("用法: python main.py <输入文件> <输出文件>")
        print("  或: python main.py --selftest")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    
    try:
        # 加载数据
        data = load_data(input_file)
        print(f"加载数据: {len(data)} 条记录")
        
        # 处理数据
        processed_data = process_data(data)
        
        # 保存结果
        save_data(processed_data, output_file)
        print(f"处理完成，输出到: {output_file}")
        print(f"原始记录: {len(data)} 条")
        print(f"处理后记录: {len(processed_data)} 条")
        
    except FileNotFoundError:
        print(f"错误: 找不到输入文件 {input_file}")
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"错误: 输入文件 {input_file} 不是有效的JSON格式")
        sys.exit(1)
    except Exception as e:
        print(f"错误: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
