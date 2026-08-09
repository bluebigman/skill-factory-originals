#!/usr/bin/env python3
"""冒烟测试示例：数组求和与平均值计算"""

import sys
import json
import argparse
from typing import List, Union


def calculate_stats(numbers: List[Union[int, float]]) -> dict:
    """
    计算数字列表的总和和平均值
    
    Args:
        numbers: 数字列表
        
    Returns:
        包含总和和平均值的字典
    """
    if not numbers:
        return {"sum": 0, "average": 0}
    
    total = sum(numbers)
    average = total / len(numbers)
    
    return {"sum": total, "average": average}


def process_input(data: dict) -> dict:
    """
    处理输入数据并返回统计结果
    
    Args:
        data: 包含数字列表的字典
        
    Returns:
        统计结果字典
    """
    numbers = data.get("numbers", [])
    return calculate_stats(numbers)


def run_selftest() -> bool:
    """
    运行自测函数，验证代码正确性
    
    Returns:
        测试是否通过
    """
    # 测试空列表
    result = calculate_stats([])
    assert result["sum"] == 0, "空列表总和应为0"
    assert result["average"] == 0, "空列表平均值应为0"
    
    # 测试正常列表
    test_numbers = [1, 2, 3, 4, 5]
    result = calculate_stats(test_numbers)
    assert result["sum"] == 15, "1-5的总和应为15"
    assert 2.5 < result["average"] < 3.5, "平均值应在3附近"
    
    # 测试负数
    test_numbers = [-5, 5, -10, 10]
    result = calculate_stats(test_numbers)
    assert result["sum"] == 0, "正负数相抵总和应为0"
    assert -1 < result["average"] < 1, "平均值应在0附近"
    
    # 测试浮点数
    test_numbers = [1.5, 2.5, 3.5]
    result = calculate_stats(test_numbers)
    assert 7.0 < result["sum"] < 8.0, "浮点数总和应在7.5附近"
    assert 2.0 < result["average"] < 3.0, "浮点数平均值应在2.5附近"
    
    # 测试process_input
    test_data = {"numbers": [10, 20, 30]}
    result = process_input(test_data)
    assert result["sum"] == 60, "10+20+30应为60"
    assert 19.0 < result["average"] < 21.0, "平均值应在20附近"
    
    print("所有自测通过!")
    return True


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="数组统计工具")
    parser.add_argument("--selftest", action="store_true", help="运行自测")
    parser.add_argument("--input", type=str, help="输入JSON文件路径")
    parser.add_argument("--output", type=str, help="输出JSON文件路径")
    
    args = parser.parse_args()
    
    # 运行自测
    if args.selftest:
        success = run_selftest()
        sys.exit(0 if success else 1)
    
    # 处理输入
    if args.input:
        try:
            with open(args.input, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            result = process_input(data)
            
            # 输出结果
            if args.output:
                with open(args.output, 'w', encoding='utf-8') as f:
                    json.dump(result, f, ensure_ascii=False, indent=2)
                print(f"结果已保存到 {args.output}")
            else:
                print(json.dumps(result, ensure_ascii=False, indent=2))
                
        except FileNotFoundError:
            print(f"错误: 文件 {args.input} 不存在", file=sys.stderr)
            sys.exit(1)
        except json.JSONDecodeError:
            print(f"错误: 文件 {args.input} 不是有效的JSON", file=sys.stderr)
            sys.exit(1)
    else:
        # 交互模式
        print("请输入数字列表（用逗号分隔），或输入'quit'退出:")
        while True:
            try:
                user_input = input("> ").strip()
                if user_input.lower() == 'quit':
                    break
                
                numbers = [float(x.strip()) for x in user_input.split(',') if x.strip()]
                result = calculate_stats(numbers)
                print(f"总和: {result['sum']}")
                print(f"平均值: {result['average']:.2f}")
                
            except KeyboardInterrupt:
                print("\n再见!")
                break
            except ValueError:
                print("错误: 请输入有效的数字列表")


if __name__ == "__main__":
    main()
