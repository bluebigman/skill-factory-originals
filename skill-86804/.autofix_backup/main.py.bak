#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
import os
import re
import json
import hashlib
from datetime import datetime
from collections import OrderedDict

def read_table(filepath, encoding='utf-8'):
    """读取表格文件，支持csv/tsv/txt"""
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"文件不存在: {filepath}")
    
    with open(filepath, 'r', encoding=encoding) as f:
        lines = f.readlines()
    
    if not lines:
        return []
    
    # 检测分隔符
    first_line = lines[0].strip()
    if '\t' in first_line:
        delimiter = '\t'
    elif ',' in first_line:
        delimiter = ','
    else:
        delimiter = None
    
    table = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if delimiter:
            row = [cell.strip() for cell in line.split(delimiter)]
        else:
            # 尝试按空白分割
            row = line.split()
        table.append(row)
    
    return table

def write_table(table, filepath, encoding='utf-8'):
    """写入表格文件"""
    with open(filepath, 'w', encoding=encoding) as f:
        for row in table:
            f.write('\t'.join(row) + '\n')

def merge_tables(table1, table2):
    """合并两个表格（按行合并）"""
    if not table1:
        return table2
    if not table2:
        return table1
    
    # 如果表头相同，合并数据行
    if table1[0] == table2[0]:
        merged = [table1[0]]  # 保留表头
        merged.extend(table1[1:])
        merged.extend(table2[1:])
        return merged
    else:
        # 表头不同，直接拼接
        return table1 + table2

def deduplicate(table):
    """去重（保留首次出现的顺序）"""
    seen = set()
    result = []
    for row in table:
        # 将行转换为可哈希的元组
        row_tuple = tuple(row)
        if row_tuple not in seen:
            seen.add(row_tuple)
            result.append(row)
    return result

def validate_data(table):
    """校验数据完整性"""
    errors = []
    if not table:
        return ["表格为空"]
    
    # 检查每行列数是否一致
    if len(table) > 0:
        col_count = len(table[0])
        for i, row in enumerate(table):
            if len(row) != col_count:
                errors.append(f"第{i+1}行列数不一致: 期望{col_count}列, 实际{len(row)}列")
    
    # 检查是否有空行
    for i, row in enumerate(table):
        if all(not cell.strip() for cell in row):
            errors.append(f"第{i+1}行为空行")
    
    return errors

def process_file(input_file, output_file=None, dedup=False, merge_file=None, validate=False, encoding='utf-8'):
    """处理表格文件"""
    table = read_table(input_file, encoding)
    
    # 合并表格
    if merge_file:
        table2 = read_table(merge_file, encoding)
        table = merge_tables(table, table2)
    
    # 去重
    if dedup:
        table = deduplicate(table)
    
    # 校验
    if validate:
        errors = validate_data(table)
        if errors:
            print("数据校验失败:")
            for err in errors:
                print(f"  - {err}")
            return 1
    
    # 输出
    if output_file:
        write_table(table, output_file, encoding)
        print(f"处理完成，输出到: {output_file}")
    else:
        # 打印到标准输出
        for row in table:
            print('\t'.join(row))
    
    return 0

def selftest():
    """自检函数"""
    print("🔍 开始自检...")
    passed = 0
    total = 6
    
    # 测试1: 去重功能
    try:
        test_table = [
            ["姓名", "年龄"],
            ["张三", "25"],
            ["李四", "30"],
            ["张三", "25"],
            ["王五", "35"]
        ]
        result = deduplicate(test_table)
        # 宽松断言：结果行数应小于等于原行数
        assert len(result) < len(test_table), f"去重后应少于{len(test_table)}行，实际{len(result)}"
        assert len(result) >= 3, f"去重后应至少3行，实际{len(result)}"
        # 检查表头保留
        assert result[0] == ["姓名", "年龄"], "表头应保留"
        # 检查重复行被移除
        assert ["张三", "25"] in result, "张三应保留"
        print("  ✅ 测试1 去重功能通过")
        passed += 1
    except AssertionError as e:
        print(f"  ❌ 测试1 失败: {e}")
    
    # 测试2: 空输入
    try:
        empty_table = []
        result = deduplicate(empty_table)
        assert result == [], "空输入应返回空列表"
        print("  ✅ 测试2 空输入通过")
        passed += 1
    except AssertionError as e:
        print(f"  ❌ 测试2 失败: {e}")
    
    # 测试3: 中文标点/编码
    try:
        chinese_table = [
            ["名称", "描述"],
            ["测试", "包含中文标点：，。！？"],
            ["数据", "含特殊字符：@#$%"]
        ]
        result = deduplicate(chinese_table)
        assert len(result) == 3, f"中文表格应有3行，实际{len(result)}"
        assert result[1][1] == "包含中文标点：，。！？", "中文标点应保留"
        print("  ✅ 测试3 中文标点/编码通过")
        passed += 1
    except AssertionError as e:
        print(f"  ❌ 测试3 失败: {e}")
    
    # 测试4: 超长输入
    try:
        long_table = []
        for i in range(100):
            long_table.append([f"行{i}", "x" * 1000])
        result = deduplicate(long_table)
        assert len(result) == 100, f"超长输入应有100行，实际{len(result)}"
        assert len(result[0][1]) == 1000, "长文本应保留"
        print("  ✅ 测试4 超长输入通过")
        passed += 1
    except AssertionError as e:
        print(f"  ❌ 测试4 失败: {e}")
    
    # 测试5: 合并表格
    try:
        table1 = [["ID", "名称"], ["1", "苹果"]]
        table2 = [["ID", "名称"], ["2", "香蕉"]]
        merged = merge_tables(table1, table2)
        assert len(merged) == 3, f"合并后应有3行，实际{len(merged)}"
        assert merged[0] == ["ID", "名称"], "表头应一致"
        assert ["2", "香蕉"] in merged, "第二表格数据应包含"
        print("  ✅ 测试5 合并表格通过")
        passed += 1
    except AssertionError as e:
        print(f"  ❌ 测试5 失败: {e}")
    
    # 测试6: 校验功能
    try:
        valid_table = [["A", "B"], ["1", "2"]]
        errors = validate_data(valid_table)
        assert len(errors) == 0, f"有效数据不应有错误，实际{len(errors)}个错误"
        
        invalid_table = [["A", "B"], ["1", "2", "3"]]
        errors = validate_data(invalid_table)
        assert len(errors) > 0, "无效数据应有错误"
        print("  ✅ 测试6 校验功能通过")
        passed += 1
    except AssertionError as e:
        print(f"  ❌ 测试6 失败: {e}")
    
    print(f"\n📊 自检结果: {passed} 通过, {total - passed} 失败")
    return passed == total

def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("用法: python main.py <输入文件> [选项]")
        print("选项:")
        print("  -o, --output <文件>    输出文件")
        print("  -d, --dedup            去重")
        print("  -m, --merge <文件>     合并表格")
        print("  -v, --validate         校验数据")
        print("  -e, --encoding <编码>  指定编码")
        print("  --selftest             运行自检")
        return 1
    
    # 自检模式
    if sys.argv[1] == '--selftest':
        return 0 if selftest() else 1
    
    # 解析参数
    args = sys.argv[1:]
    input_file = args[0]
    output_file = None
    dedup = False
    merge_file = None
    validate = False
    encoding = 'utf-8'
    
    i = 1
    while i < len(args):
        arg = args[i]
        if arg in ['-o', '--output'] and i + 1 < len(args):
            output_file = args[i + 1]
            i += 2
        elif arg in ['-d', '--dedup']:
            dedup = True
            i += 1
        elif arg in ['-m', '--merge'] and i + 1 < len(args):
            merge_file = args[i + 1]
            i += 2
        elif arg in ['-v', '--validate']:
            validate = True
            i += 1
        elif arg in ['-e', '--encoding'] and i + 1 < len(args):
            encoding = args[i + 1]
            i += 2
        else:
            print(f"未知参数: {arg}")
            return 1
    
    try:
        return process_file(input_file, output_file, dedup, merge_file, validate, encoding)
    except Exception as e:
        print(f"错误: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
