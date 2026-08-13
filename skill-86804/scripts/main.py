#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
import csv
import json
import argparse
from datetime import datetime
from collections import OrderedDict
from itertools import zip_longest


def format_date(date_str, input_format="%Y-%m-%d", output_format="%Y/%m/%d"):
    """格式化日期字符串"""
    try:
        dt = datetime.strptime(date_str, input_format)
        return dt.strftime(output_format)
    except (ValueError, TypeError):
        return date_str


def format_number(num_str, decimal_places=2):
    """格式化数字，保留指定小数位"""
    try:
        num = float(num_str)
        return f"{num:.{decimal_places}f}"
    except (ValueError, TypeError):
        return num_str


def deduplicate(data_list, key=None):
    """数据去重，保持原始顺序"""
    seen = set()
    result = []
    for item in data_list:
        if key:
            item_key = key(item)
        else:
            item_key = item
        if item_key not in seen:
            seen.add(item_key)
            result.append(item)
    return result


def merge_vertical(list1, list2):
    """纵向合并两个列表"""
    return list1 + list2


def merge_horizontal(list1, list2, on_key):
    """横向关联两个列表，基于指定键"""
    dict2 = {}
    for item in list2:
        if on_key in item:
            dict2[item[on_key]] = item

    result = []
    for item1 in list1:
        if on_key in item1 and item1[on_key] in dict2:
            merged = dict(item1)
            merged.update(dict2[item1[on_key]])
            result.append(merged)
        else:
            result.append(dict(item1))
    return result


def validate_data(data_list, required_fields=None):
    """数据校验，检查必填字段"""
    if required_fields is None:
        required_fields = []
    errors = []
    for i, item in enumerate(data_list):
        if isinstance(item, dict):
            for field in required_fields:
                if field not in item or item[field] in (None, ""):
                    errors.append(f"第{i+1}行缺少字段: {field}")
    return errors


def read_csv(file_path):
    """读取CSV文件"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            return list(reader)
    except FileNotFoundError:
        return []
    except Exception:
        return []


def write_csv(file_path, data, fieldnames=None):
    """写入CSV文件"""
    if not data:
        return
    if fieldnames is None:
        fieldnames = list(data[0].keys()) if isinstance(data[0], dict) else []
    try:
        with open(file_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data)
    except Exception:
        pass


def main():
    parser = argparse.ArgumentParser(description='数据处理工具')
    parser.add_argument('--selftest', action='store_true', help='运行自检')
    parser.add_argument('--input', help='输入文件路径')
    parser.add_argument('--output', help='输出文件路径')
    parser.add_argument('--operation', choices=['dedup', 'merge_v', 'merge_h', 'validate'],
                        help='操作类型')
    args = parser.parse_args()

    if args.selftest:
        run_selftest()
        return

    if not args.input or not args.output:
        print("请指定输入和输出文件路径")
        return

    data = read_csv(args.input)
    if not data:
        print("输入文件为空或不存在")
        return

    if args.operation == 'dedup':
        result = deduplicate(data)
    elif args.operation == 'merge_v':
        # 简单示例：将同一文件内容纵向合并
        result = merge_vertical(data, data)
    elif args.operation == 'merge_h':
        # 简单示例：基于第一个字段横向关联
        if data and isinstance(data[0], dict):
            key = list(data[0].keys())[0]
            result = merge_horizontal(data, data, key)
        else:
            result = data
    elif args.operation == 'validate':
        errors = validate_data(data)
        if errors:
            print("数据校验失败:")
            for err in errors:
                print(f"  {err}")
            return
        result = data
    else:
        result = data

    write_csv(args.output, result)


def run_selftest():
    """运行自检"""
    print("开始自检...")
    passed = 0
    total = 0

    # 测试日期格式化
    total += 1
    try:
        result = format_date("2024-01-15")
        assert result == "2024/01/15", f"日期格式化失败: {result}"
        print("  [PASS] 日期格式化")
        passed += 1
    except AssertionError as e:
        print(f"  [FAIL] 日期格式化: {e}")

    # 测试数字格式化
    total += 1
    try:
        result = format_number("123.456")
        assert abs(float(result) - 123.46) < 0.01, f"数字格式化失败: {result}"
        print("  [PASS] 数字格式化")
        passed += 1
    except AssertionError as e:
        print(f"  [FAIL] 数字格式化: {e}")

    # 测试数据去重
    total += 1
    try:
        test_data = [1, 2, 2, 3, 3, 3, 4]
        result = deduplicate(test_data)
        assert len(result) == 4, f"去重失败: {result}"
        assert result[0] == 1 and result[-1] == 4, f"去重顺序错误: {result}"
        print("  [PASS] 数据去重")
        passed += 1
    except AssertionError as e:
        print(f"  [FAIL] 数据去重: {e}")

    # 测试纵向合并
    total += 1
    try:
        list1 = [1, 2, 3]
        list2 = [4, 5, 6]
        result = merge_vertical(list1, list2)
        assert len(result) == 6, f"纵向合并失败: {result}"
        assert result[0] == 1 and result[-1] == 6, f"纵向合并顺序错误: {result}"
        print("  [PASS] 纵向合并")
        passed += 1
    except AssertionError as e:
        print(f"  [FAIL] 纵向合并: {e}")

    # 测试横向关联
    total += 1
    try:
        list1 = [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]
        list2 = [{"id": 1, "age": 30}, {"id": 2, "age": 25}]
        result = merge_horizontal(list1, list2, "id")
        assert len(result) == 2, f"横向关联失败: {result}"
        assert "age" in result[0], f"横向关联缺少字段: {result}"
        print("  [PASS] 横向关联")
        passed += 1
    except AssertionError as e:
        print(f"  [FAIL] 横向关联: {e}")

    # 测试数据校验
    total += 1
    try:
        test_data = [{"name": "Alice", "age": 30}, {"name": "Bob"}]
        errors = validate_data(test_data, ["name", "age"])
        assert len(errors) == 1, f"数据校验失败: {errors}"
        print("  [PASS] 数据校验")
        passed += 1
    except AssertionError as e:
        print(f"  [FAIL] 数据校验: {e}")

    # 测试空输入
    total += 1
    try:
        result = deduplicate([])
        assert result == [], f"空输入处理失败: {result}"
        result = merge_vertical([], [])
        assert result == [], f"空输入纵向合并失败: {result}"
        result = merge_horizontal([], [], "id")
        assert result == [], f"空输入横向关联失败: {result}"
        print("  [PASS] 空输入校验")
        passed += 1
    except AssertionError as e:
        print(f"  [FAIL] 空输入校验: {e}")

    print(f"\n自检完成: {passed}/{total} 通过")
    if passed == total:
        print("全部通过!")
    else:
        print(f"有 {total - passed} 项失败")
        sys.exit(1)


if __name__ == "__main__":
    main()
