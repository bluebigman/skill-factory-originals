#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
import json
import re
import os
from typing import List, Dict, Any, Optional

def parse_csv(text: str) -> List[Dict[str, str]]:
    """Parse CSV/TSV text into list of dicts."""
    if not text or not text.strip():
        return []
    
    lines = text.strip().split('\n')
    if not lines:
        return []
    
    # Detect delimiter
    first_line = lines[0]
    if '\t' in first_line:
        delimiter = '\t'
    else:
        delimiter = ','
    
    # Parse header
    header = [h.strip() for h in first_line.split(delimiter)]
    
    # Parse data rows
    result = []
    for line in lines[1:]:
        if not line.strip():
            continue
        values = [v.strip() for v in line.split(delimiter)]
        # Pad or truncate to match header length
        while len(values) < len(header):
            values.append('')
        row = {}
        for i, col_name in enumerate(header):
            row[col_name] = values[i] if i < len(values) else ''
        result.append(row)
    
    return result

def parse_json_array(text: str) -> List[Dict[str, str]]:
    """Parse JSON array of objects into list of dicts with string values."""
    try:
        data = json.loads(text)
        if not isinstance(data, list):
            return []
        result = []
        for item in data:
            if isinstance(item, dict):
                row = {}
                for key, value in item.items():
                    if isinstance(value, (str, int, float, bool)):
                        row[str(key)] = str(value)
                    elif value is None:
                        row[str(key)] = ''
                    else:
                        row[str(key)] = str(value)
                result.append(row)
            elif isinstance(item, (str, int, float, bool)):
                result.append({"value": str(item)})
        return result
    except (json.JSONDecodeError, TypeError):
        return []

def parse_data(text: str) -> List[Dict[str, str]]:
    """Parse input data, trying JSON first then CSV."""
    if not text or not text.strip():
        return []
    
    # Try JSON array first
    json_result = parse_json_array(text)
    if json_result:
        return json_result
    
    # Fall back to CSV/TSV
    return parse_csv(text)

def generate_chart(data: List[Dict[str, str]], chart_type: str = "bar") -> str:
    """Generate ASCII chart from data."""
    if not data:
        return "无数据"
    
    # Get first numeric column for values
    numeric_cols = []
    for key in data[0].keys():
        try:
            float(data[0][key])
            numeric_cols.append(key)
        except (ValueError, TypeError):
            continue
    
    if not numeric_cols:
        return "无数值列"
    
    value_col = numeric_cols[0]
    label_col = None
    for key in data[0].keys():
        if key != value_col:
            label_col = key
            break
    
    values = []
    labels = []
    for row in data:
        try:
            val = float(row.get(value_col, 0))
            values.append(val)
            labels.append(row.get(label_col, '') if label_col else '')
        except (ValueError, TypeError):
            continue
    
    if not values:
        return "无有效数值"
    
    max_val = max(values) if values else 1
    if max_val == 0:
        max_val = 1
    
    chart_width = 40
    chart = []
    
    if chart_type == "bar":
        chart.append(f"{value_col} 柱状图:")
        for i, (label, val) in enumerate(zip(labels, values)):
            bar_len = int((val / max_val) * chart_width)
            bar = '█' * bar_len
            label_str = str(label)[:10] if label else f"行{i+1}"
            chart.append(f"{label_str}: {bar} {val}")
    elif chart_type == "line":
        chart.append(f"{value_col} 折线图:")
        for i, (label, val) in enumerate(zip(labels, values)):
            pos = int((val / max_val) * chart_width)
            line = ' ' * pos + '●'
            label_str = str(label)[:10] if label else f"行{i+1}"
            chart.append(f"{label_str}: {line} {val}")
    else:
        chart.append(f"{value_col} 图表:")
        for i, (label, val) in enumerate(zip(labels, values)):
            bar_len = int((val / max_val) * 20)
            bar = '█' * bar_len
            label_str = str(label)[:10] if label else f"行{i+1}"
            chart.append(f"{label_str}: {bar} {val}")
    
    return '\n'.join(chart)

def generate_insight(data: List[Dict[str, str]]) -> str:
    """Generate text insight from data."""
    if not data:
        return "数据为空"
    
    insights = []
    insights.append(f"数据包含 {len(data)} 行记录")
    
    # Check numeric columns
    for key in data[0].keys():
        try:
            values = [float(row[key]) for row in data if row.get(key)]
            if values:
                insights.append(f"列 '{key}': 最小值={min(values):.2f}, 最大值={max(values):.2f}, 平均值={sum(values)/len(values):.2f}")
        except (ValueError, TypeError):
            continue
    
    return '\n'.join(insights)

def process_input(text: str) -> str:
    """Process input and return analysis result."""
    data = parse_data(text)
    if not data:
        return "无法解析数据"
    
    chart = generate_chart(data)
    insight = generate_insight(data)
    
    return f"数据解析结果:\n共 {len(data)} 行\n\n图表:\n{chart}\n\n解读:\n{insight}"

def selftest() -> bool:
    """Run self-tests."""
    tests = [
        ("", []),  # Empty input
        ("name,age\nAlice,25\nBob,30", [{"name": "Alice", "age": "25"}, {"name": "Bob", "age": "30"}]),
        ("date,value\n2024-01,10\n2024-02,", [{"date": "2024-01", "value": "10"}, {"date": "2024-02", "value": ""}]),
        ("姓名,年龄\n张三,25\n李四,30", [{"姓名": "张三", "年龄": "25"}, {"姓名": "李四", "年龄": "30"}]),
        ("name\tage\nAlice\t25\nBob\t30", [{"name": "Alice", "age": "25"}, {"name": "Bob", "age": "30"}]),
        ('[{"name":"Alice","age":25},{"name":"Bob","age":30}]', [{"name": "Alice", "age": "25"}, {"name": "Bob", "age": "30"}]),
        ("col1,col2\nval0,num0\nval1,num1", [{"col1": "val0", "col2": "num0"}, {"col1": "val1", "col2": "num1"}]),
        ("name,color\nAlice,red\nBob,blue", [{"name": "Alice", "color": "red"}, {"name": "Bob", "color": "blue"}]),
        ("a,b\n1,2", [{"a": "1", "b": "2"}]),
    ]
    
    for i, (input_text, expected) in enumerate(tests):
        result = parse_data(input_text)
        if result != expected:
            print(f"[FAIL] 测试: {input_text[:30]}... - 期望{expected}, 实际{result}")
            return False
        print(f"[PASS] 测试: {input_text[:30]}...")
    
    # Test chart generation
    data = [{"name": "Alice", "age": "25"}, {"name": "Bob", "age": "30"}]
    chart = generate_chart(data)
    if not chart or "柱状图" not in chart:
        print("[FAIL] 图表类型")
        return False
    print("[PASS] 图表类型")
    
    # Test insight generation
    insight = generate_insight(data)
    if not insight or "2 行" not in insight:
        print("[FAIL] 解读生成")
        return False
    print("[PASS] 解读生成")
    
    # Test Chinese data
    cn_data = [{"姓名": "张三", "年龄": "25"}, {"姓名": "李四", "年龄": "30"}]
    if not generate_chart(cn_data) or not generate_insight(cn_data):
        print("[FAIL] 中文数据")
        return False
    print("[PASS] 中文数据")
    
    # Test TSV format
    tsv_data = parse_data("name\tage\nAlice\t25\nBob\t30")
    if len(tsv_data) != 2:
        print("[FAIL] TSV格式")
        return False
    print("[PASS] TSV格式")
    
    # Basic CSV test
    basic_data = parse_data("name,age\nAlice,25\nBob,30")
    if len(basic_data) != 2:
        print("[FAIL] 基本CSV解析")
        return False
    print("[PASS] 基本CSV解析")
    
    print(f"\n总计: {len(tests) + 5} 通过, 0 失败")
    return True

def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--selftest":
        success = selftest()
        sys.exit(0 if success else 1)
    
    # Read from stdin or file
    if len(sys.argv) > 1:
        try:
            with open(sys.argv[1], 'r', encoding='utf-8') as f:
                text = f.read()
        except FileNotFoundError:
            text = sys.argv[1]
    else:
        text = sys.stdin.read()
    
    result = process_input(text)
    print(result)

if __name__ == "__main__":
    main()
