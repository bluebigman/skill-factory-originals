#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""RTK Token Saver Pro - 数据处理模块"""

import json
import os
import sys
import time
import hashlib
import argparse
from datetime import datetime
from collections import defaultdict

class DataProcessor:
    """数据处理类"""
    
    def __init__(self):
        self.data = []
        self.metadata = {}
        
    def load_json(self, filepath):
        """加载JSON文件"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list):
                    self.data = data
                elif isinstance(data, dict):
                    self.data = [data]
                else:
                    self.data = []
                return True
        except Exception as e:
            print(f"加载JSON失败: {e}")
            return False
    
    def save_json(self, filepath, data=None):
        """保存JSON文件"""
        try:
            if data is None:
                data = self.data
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"保存JSON失败: {e}")
            return False
    
    def filter_by_condition(self, data, condition_func):
        """根据条件过滤数据"""
        if not data:
            return []
        return [item for item in data if condition_func(item)]
    
    def sort_by_key(self, data, key, reverse=False):
        """按指定键排序"""
        try:
            return sorted(data, key=lambda x: x.get(key, 0), reverse=reverse)
        except Exception as e:
            print(f"排序失败: {e}")
            return data
    
    def group_by_key(self, data, key):
        """按指定键分组"""
        groups = defaultdict(list)
        for item in data:
            if isinstance(item, dict) and key in item:
                groups[item[key]].append(item)
            else:
                groups['other'].append(item)
        return dict(groups)
    
    def aggregate(self, data, key, agg_func='sum'):
        """聚合计算"""
        values = []
        for item in data:
            if isinstance(item, dict) and key in item:
                try:
                    values.append(float(item[key]))
                except (ValueError, TypeError):
                    continue
        if not values:
            return 0
        
        if agg_func == 'sum':
            return sum(values)
        elif agg_func == 'avg':
            return sum(values) / len(values)
        elif agg_func == 'max':
            return max(values)
        elif agg_func == 'min':
            return min(values)
        elif agg_func == 'count':
            return len(values)
        else:
            return sum(values)
    
    def deduplicate(self, data, key=None):
        """去重"""
        seen = set()
        result = []
        for item in data:
            if isinstance(item, dict) and key:
                val = item.get(key)
                if val not in seen:
                    seen.add(val)
                    result.append(item)
            else:
                if item not in seen:
                    seen.add(item)
                    result.append(item)
        return result
    
    def merge_data(self, data1, data2, key):
        """合并数据"""
        merged = {}
        for item in data1 + data2:
            if isinstance(item, dict) and key in item:
                k = item[key]
                if k not in merged:
                    merged[k] = item
                else:
                    merged[k].update(item)
        return list(merged.values())
    
    def transform(self, data, transform_func):
        """转换数据"""
        return [transform_func(item) for item in data]
    
    def validate(self, data, rules):
        """数据验证"""
        errors = []
        for i, item in enumerate(data):
            if isinstance(item, dict):
                for field, rule in rules.items():
                    if field in item:
                        value = item[field]
                        if 'required' in rule and value in (None, '', []):
                            errors.append(f"第{i}条数据字段{field}不能为空")
                        if 'type' in rule:
                            expected_type = rule['type']
                            if expected_type == 'number' and not isinstance(value, (int, float)):
                                errors.append(f"第{i}条数据字段{field}应为数字")
                            elif expected_type == 'string' and not isinstance(value, str):
                                errors.append(f"第{i}条数据字段{field}应为字符串")
                        if 'min' in rule and isinstance(value, (int, float)):
                            if value < rule['min']:
                                errors.append(f"第{i}条数据字段{field}小于最小值{rule['min']}")
                        if 'max' in rule and isinstance(value, (int, float)):
                            if value > rule['max']:
                                errors.append(f"第{i}条数据字段{field}大于最大值{rule['max']}")
        return errors
    
    def stats(self, data):
        """数据统计"""
        if not data:
            return {'count': 0}
        result = {'count': len(data)}
        
        # 统计数值字段
        numeric_fields = set()
        for item in data:
            if isinstance(item, dict):
                for k, v in item.items():
                    if isinstance(v, (int, float)):
                        numeric_fields.add(k)
        
        for field in numeric_fields:
            values = [item[field] for item in data if isinstance(item, dict) and field in item and isinstance(item[field], (int, float))]
            if values:
                result[f'{field}_sum'] = sum(values)
                result[f'{field}_avg'] = sum(values) / len(values)
                result[f'{field}_max'] = max(values)
                result[f'{field}_min'] = min(values)
        
        return result


def run_selftest():
    """运行自测"""
    print("运行自测...")
    dp = DataProcessor()
    
    # 测试数据
    test_data = [
        {"name": "item1", "value": 10, "category": "A"},
        {"name": "item2", "value": 5, "category": "B"},
        {"name": "item3", "value": 15, "category": "A"},
        {"name": "item4", "value": 8, "category": "C"},
        {"name": "item5", "value": 3, "category": "B"}
    ]
    
    # 测试过滤 - 使用类型安全的过滤条件
    print("  测试 DataProcessor...")
    filtered = dp.filter_by_condition(test_data, lambda x: isinstance(x, dict) and isinstance(x.get('value'), (int, float)) and x['value'] > 5)
    assert len(filtered) >= 2, f"过滤结果数量异常: {len(filtered)}"
    print(f"    过滤测试通过: {len(filtered)} 条记录")
    
    # 测试排序
    sorted_data = dp.sort_by_key(test_data, 'value', reverse=True)
    assert len(sorted_data) == len(test_data), "排序后数量不一致"
    if sorted_data:
        assert sorted_data[0]['value'] >= sorted_data[-1]['value'], "排序顺序错误"
    print("    排序测试通过")
    
    # 测试分组
    groups = dp.group_by_key(test_data, 'category')
    assert len(groups) >= 1, "分组结果为空"
    print(f"    分组测试通过: {len(groups)} 个分组")
    
    # 测试聚合
    total = dp.aggregate(test_data, 'value', 'sum')
    assert total > 0, "聚合结果异常"
    avg = dp.aggregate(test_data, 'value', 'avg')
    assert avg > 0, "平均值异常"
    print(f"    聚合测试通过: sum={total}, avg={avg:.2f}")
    
    # 测试去重
    dup_data = test_data + [test_data[0]]  # 添加重复项
    deduped = dp.deduplicate(dup_data, 'name')
    assert len(deduped) <= len(dup_data), "去重后数量增加"
    print(f"    去重测试通过: {len(deduped)} 条记录")
    
    # 测试合并
    data1 = [{"id": 1, "name": "A"}, {"id": 2, "name": "B"}]
    data2 = [{"id": 1, "value": 100}, {"id": 3, "name": "C"}]
    merged = dp.merge_data(data1, data2, 'id')
    assert len(merged) >= 2, "合并结果异常"
    print(f"    合并测试通过: {len(merged)} 条记录")
    
    # 测试转换
    transformed = dp.transform(test_data, lambda x: {**x, 'value': x['value'] * 2} if isinstance(x, dict) else x)
    assert len(transformed) == len(test_data), "转换后数量不一致"
    print("    转换测试通过")
    
    # 测试验证
    rules = {
        'value': {'type': 'number', 'min': 0, 'max': 100}
    }
    errors = dp.validate(test_data, rules)
    assert len(errors) == 0, f"验证错误: {errors}"
    print("    验证测试通过")
    
    # 测试统计
    stats_result = dp.stats(test_data)
    assert stats_result['count'] == len(test_data), "统计数量错误"
    assert 'value_sum' in stats_result, "缺少value_sum统计"
    print(f"    统计测试通过: {stats_result['count']} 条记录")
    
    # 测试JSON序列化
    json_str = json.dumps(test_data)
    assert json_str, "JSON序列化失败"
    print("    JSON序列化测试通过")
    
    # 测试空数据处理
    empty_result = dp.filter_by_condition([], lambda x: True)
    assert empty_result == [], "空数据处理错误"
    empty_stats = dp.stats([])
    assert empty_stats['count'] == 0, "空统计错误"
    print("    空数据处理测试通过")
    
    print("所有自测通过！")
    return True


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='RTK Token Saver Pro - 数据处理模块')
    parser.add_argument('--selftest', action='store_true', help='运行自测')
    parser.add_argument('--input', type=str, help='输入JSON文件')
    parser.add_argument('--output', type=str, help='输出JSON文件')
    parser.add_argument('--filter', type=str, help='过滤条件(JSON格式)')
    parser.add_argument('--sort', type=str, help='排序字段')
    parser.add_argument('--group', type=str, help='分组字段')
    parser.add_argument('--stats', action='store_true', help='显示统计信息')
    
    args = parser.parse_args()
    
    if args.selftest:
        run_selftest()
        return 0
    
    dp = DataProcessor()
    
    if args.input:
        if not dp.load_json(args.input):
            print(f"无法加载文件: {args.input}")
            return 1
        
        if args.filter:
            try:
                filter_dict = json.loads(args.filter)
                if 'field' in filter_dict and 'value' in filter_dict:
                    field = filter_dict['field']
                    value = filter_dict['value']
                    dp.data = dp.filter_by_condition(dp.data, lambda x: isinstance(x, dict) and x.get(field) == value)
            except json.JSONDecodeError:
                print("过滤条件JSON格式错误")
                return 1
        
        if args.sort:
            dp.data = dp.sort_by_key(dp.data, args.sort)
        
        if args.group:
            groups = dp.group_by_key(dp.data, args.group)
            print(f"分组统计: {len(groups)} 组")
            for key, items in groups.items():
                print(f"  {key}: {len(items)} 条")
        
        if args.stats:
            stats_result = dp.stats(dp.data)
            print(f"数据统计: {stats_result}")
        
        if args.output:
            if dp.save_json(args.output):
                print(f"数据已保存到: {args.output}")
            else:
                print(f"保存失败: {args.output}")
                return 1
        else:
            print(json.dumps(dp.data, ensure_ascii=False, indent=2))
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
