#!/usr/bin/env python3
"""冒烟测试修复 - 输出完整可编译代码"""

import sys
import os
import json
import math
import random
import time
import argparse
from typing import List, Dict, Any, Optional, Tuple, Set, Union


class DataProcessor:
    """数据处理核心类"""
    
    def __init__(self, data: Optional[List[Dict[str, Any]]] = None):
        """初始化处理器"""
        self.data = data if data is not None else []
        self.processed_count = 0
        self.errors = []
        self.start_time = time.time()
    
    def load_json(self, filepath: str) -> bool:
        """从JSON文件加载数据"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                self.data = json.load(f)
            return True
        except Exception as e:
            self.errors.append(f"加载失败: {e}")
            return False
    
    def save_json(self, filepath: str) -> bool:
        """保存数据到JSON文件"""
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            self.errors.append(f"保存失败: {e}")
            return False
    
    def filter_by_key(self, key: str, value: Any) -> List[Dict[str, Any]]:
        """按指定键值过滤数据"""
        result = [item for item in self.data if item.get(key) == value]
        self.processed_count += len(result)
        return result
    
    def sort_by_key(self, key: str, reverse: bool = False) -> List[Dict[str, Any]]:
        """按指定键排序"""
        return sorted(self.data, key=lambda x: x.get(key, 0), reverse=reverse)
    
    def aggregate(self, key: str, agg_type: str = "sum") -> float:
        """聚合计算"""
        values = [item.get(key, 0) for item in self.data]
        if agg_type == "sum":
            return sum(values)
        elif agg_type == "avg":
            return sum(values) / len(values) if values else 0
        elif agg_type == "max":
            return max(values) if values else 0
        elif agg_type == "min":
            return min(values) if values else 0
        return 0
    
    def deduplicate(self, keys: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """去重"""
        seen = set()
        result = []
        for item in self.data:
            if keys:
                identifier = tuple(item.get(k) for k in keys)
            else:
                identifier = tuple(sorted(item.items()))
            if identifier not in seen:
                seen.add(identifier)
                result.append(item)
        return result
    
    def merge(self, other_data: List[Dict[str, Any]], key: str = "id") -> List[Dict[str, Any]]:
        """合并数据"""
        merged = {}
        for item in self.data + other_data:
            k = item.get(key)
            if k not in merged:
                merged[k] = item
            else:
                merged[k].update(item)
        return list(merged.values())
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "total": len(self.data),
            "processed": self.processed_count,
            "errors": len(self.errors),
            "elapsed": time.time() - self.start_time
        }


class DataAnalyzer:
    """数据分析类"""
    
    def __init__(self, data: List[Dict[str, Any]]):
        self.data = data
    
    def calculate_mean(self, key: str) -> float:
        """计算平均值"""
        values = [item.get(key, 0) for item in self.data]
        return sum(values) / len(values) if values else 0
    
    def calculate_median(self, key: str) -> float:
        """计算中位数"""
        values = sorted([item.get(key, 0) for item in self.data])
        n = len(values)
        if n == 0:
            return 0
        if n % 2 == 1:
            return values[n // 2]
        return (values[n // 2 - 1] + values[n // 2]) / 2
    
    def calculate_std(self, key: str) -> float:
        """计算标准差"""
        mean = self.calculate_mean(key)
        values = [item.get(key, 0) for item in self.data]
        variance = sum((x - mean) ** 2 for x in values) / len(values) if values else 0
        return math.sqrt(variance)
    
    def find_outliers(self, key: str, threshold: float = 2.0) -> List[Dict[str, Any]]:
        """找出异常值"""
        mean = self.calculate_mean(key)
        std = self.calculate_std(key)
        if std == 0:
            return []
        return [item for item in self.data if abs(item.get(key, 0) - mean) > threshold * std]
    
    def correlation(self, key1: str, key2: str) -> float:
        """计算相关系数"""
        n = len(self.data)
        if n == 0:
            return 0
        x = [item.get(key1, 0) for item in self.data]
        y = [item.get(key2, 0) for item in self.data]
        mean_x = sum(x) / n
        mean_y = sum(y) / n
        cov = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(x, y)) / n
        std_x = math.sqrt(sum((xi - mean_x) ** 2 for xi in x) / n)
        std_y = math.sqrt(sum((yi - mean_y) ** 2 for yi in y) / n)
        if std_x == 0 or std_y == 0:
            return 0
        return cov / (std_x * std_y)


class DataVisualizer:
    """数据可视化类"""
    
    @staticmethod
    def generate_chart(data: List[float], title: str = "Chart") -> str:
        """生成ASCII图表"""
        if not data:
            return "无数据"
        max_val = max(data)
        min_val = min(data)
        chart = [f"{title}:"]
        for i, val in enumerate(data):
            bar_length = int((val - min_val) / (max_val - min_val + 0.0001) * 50)
            chart.append(f"{i:3d} | {'#' * bar_length} {val:.2f}")
        return "\n".join(chart)
    
    @staticmethod
    def generate_histogram(data: List[float], bins: int = 10) -> str:
        """生成直方图"""
        if not data:
            return "无数据"
        min_val = min(data)
        max_val = max(data)
        bin_width = (max_val - min_val) / bins if max_val > min_val else 1
        counts = [0] * bins
        for val in data:
            idx = min(int((val - min_val) / bin_width), bins - 1)
            counts[idx] += 1
        result = ["直方图:"]
        for i, count in enumerate(counts):
            bar = "#" * count
            result.append(f"[{min_val + i * bin_width:.1f}-{min_val + (i + 1) * bin_width:.1f}]: {bar} ({count})")
        return "\n".join(result)


def generate_sample_data(n: int = 100) -> List[Dict[str, Any]]:
    """生成样例数据"""
    random.seed(42)
    data = []
    for i in range(n):
        data.append({
            "id": i,
            "name": f"item_{i}",
            "value": random.randint(1, 100),
            "category": random.choice(["A", "B", "C"]),
            "score": random.uniform(0, 100)
        })
    return data


def run_selftest() -> bool:
    """运行自测"""
    print("开始自测...")
    
    # 测试1: 数据处理
    data = generate_sample_data(50)
    processor = DataProcessor(data)
    assert len(processor.data) == 50
    assert processor.processed_count == 0
    
    # 测试2: 过滤
    filtered = processor.filter_by_key("category", "A")
    assert len(filtered) > 0
    assert all(item["category"] == "A" for item in filtered)
    
    # 测试3: 排序
    sorted_data = processor.sort_by_key("value", reverse=True)
    assert len(sorted_data) == 50
    for i in range(len(sorted_data) - 1):
        assert sorted_data[i]["value"] >= sorted_data[i + 1]["value"]
    
    # 测试4: 聚合
    total = processor.aggregate("value", "sum")
    avg = processor.aggregate("value", "avg")
    assert total > 0
    assert avg > 0
    
    # 测试5: 去重
    dup_data = data + data[:10]
    dedup = DataProcessor(dup_data).deduplicate(["id"])
    assert len(dedup) == 50
    
    # 测试6: 统计分析
    analyzer = DataAnalyzer(data)
    mean = analyzer.calculate_mean("value")
    median = analyzer.calculate_median("value")
    std = analyzer.calculate_std("value")
    assert mean > 0
    assert median > 0
    assert std >= 0
    
    # 测试7: 可视化
    values = [item["value"] for item in data]
    chart = DataVisualizer.generate_chart(values)
    assert len(chart) > 0
    hist = DataVisualizer.generate_histogram(values)
    assert len(hist) > 0
    
    # 测试8: 文件操作
    temp_file = "/tmp/test_data.json"
    assert processor.save_json(temp_file)
    new_processor = DataProcessor()
    assert new_processor.load_json(temp_file)
    assert len(new_processor.data) == 50
    
    print("所有自测通过!")
    return True


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="数据处理工具")
    parser.add_argument("--selftest", action="store_true", help="运行自测")
    parser.add_argument("--input", type=str, help="输入文件")
    parser.add_argument("--output", type=str, help="输出文件")
    parser.add_argument("--filter", type=str, help="过滤条件 key=value")
    parser.add_argument("--sort", type=str, help="排序键")
    parser.add_argument("--stats", action="store_true", help="显示统计信息")
    
    args = parser.parse_args()
    
    if args.selftest:
        success = run_selftest()
        sys.exit(0 if success else 1)
    
    # 加载数据
    processor = DataProcessor()
    if args.input:
        if not processor.load_json(args.input):
            print(f"错误: {processor.errors[-1] if processor.errors else '加载失败'}")
            sys.exit(1)
    else:
        processor.data = generate_sample_data()
    
    # 处理数据
    if args.filter:
        key, value = args.filter.split("=", 1)
        processor.data = processor.filter_by_key(key, value)
    
    if args.sort:
        processor.data = processor.sort_by_key(args.sort)
    
    # 输出
    if args.output:
        processor.save_json(args.output)
    
    if args.stats:
        stats = processor.get_stats()
        print(json.dumps(stats, indent=2))
    
    # 显示前5条数据
    for item in processor.data[:5]:
        print(json.dumps(item, ensure_ascii=False))


if __name__ == "__main__":
    main()
