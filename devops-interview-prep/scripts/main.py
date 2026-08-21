#!/usr/bin/env python3
"""冒烟测试修复版本 - 使用标准库实现简单功能"""

import sys
import json
import argparse
from typing import Any, Dict, List, Optional
dry_run = False  # v3.274 模块级 dry-run 标志


def process_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """处理输入数据，返回统计结果"""
    result = {
        "count": 0,
        "sum": 0,
        "average": 0,
        "max": None,
        "min": None,
        "keys": []
    }
    
    if not data or "values" not in data:
        return result
    
    values = data["values"]
    if not isinstance(values, list):
        return result
    
    # 只处理数字类型
    numbers = [v for v in values if isinstance(v, (int, float)) and not isinstance(v, bool)]
    
    if numbers:
        result["count"] = len(numbers)
        result["sum"] = sum(numbers)
        result["average"] = result["sum"] / result["count"]
        result["max"] = max(numbers)
        result["min"] = min(numbers)
    
    result["keys"] = list(data.keys())
    return result


def format_output(result: Dict[str, Any]) -> str:
    """格式化输出结果"""
    lines = []
    lines.append(f"Count: {result['count']}")
    lines.append(f"Sum: {result['sum']}")
    lines.append(f"Average: {result['average']:.2f}")
    
    if result["max"] is not None:
        lines.append(f"Max: {result['max']}")
        lines.append(f"Min: {result['min']}")
    
    lines.append(f"Keys: {', '.join(result['keys'])}")
    return "\n".join(lines)


def run_selftest() -> bool:
    """运行自测"""
    test_data = {
        "values": [1, 2, 3, 4, 5],
        "name": "test",
        "active": True
    }
    
    result = process_data(test_data)
    
    # 使用宽松断言
    assert result["count"] == 5, f"Expected count 5, got {result['count']}"
    assert result["sum"] == 15, f"Expected sum 15, got {result['sum']}"
    assert result["average"] > 2.9 and result["average"] < 3.1, \
        f"Average should be around 3, got {result['average']}"
    assert result["max"] == 5, f"Expected max 5, got {result['max']}"
    assert result["min"] == 1, f"Expected min 1, got {result['min']}"
    assert len(result["keys"]) == 3, f"Expected 3 keys, got {len(result['keys'])}"
    
    # 测试空数据
    empty_result = process_data({})
    assert empty_result["count"] == 0
    assert empty_result["sum"] == 0
    
    # 测试非数字数据
    mixed_result = process_data({"values": [1, "two", 3.5, None, True]})
    assert mixed_result["count"] == 2, f"Expected 2 numbers, got {mixed_result['count']}"
    assert mixed_result["sum"] > 4.4 and mixed_result["sum"] < 4.6, \
        f"Sum should be around 4.5, got {mixed_result['sum']}"
    
    print("All selftests passed!")
    return True


def main() -> int:
    """主函数"""
    parser = argparse.ArgumentParser(description="数据处理工具")
    parser.add_argument("--selftest", action="store_true", help="运行自测")
    parser.add_argument("--input", type=str, help="输入JSON文件路径")
    parser.add_argument("--output", type=str, help="输出文件路径")
    
    parser.add_argument("--force", action="store_true")  # R4 强制写盘

    
    parser.add_argument("--dry-run", action="store_true")  # R4 预览模式
    
    args = parser.parse_args()
    
    global dry_run
    
    dry_run = getattr(args, "dry_run", False)  # v3.274 同步到全局
    
    if args.selftest:
        run_selftest()
        return 0
    
    # 处理输入
    if args.input:
        try:
            with open(args.input, 'r', encoding='utf-8') as f:
                data = json.load(f)
            result = process_data(data)
            output_text = format_output(result)
            
            if args.output:
                with open(args.output, 'w', encoding='utf-8') as f:
                    f.write(output_text)
            else:
                print(output_text)
        except Exception as e:
            print(f"Error processing input: {e}", file=sys.stderr)
            return 1
    else:
        # 交互模式
        print("No input file specified. Use --input <file> or --selftest")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
