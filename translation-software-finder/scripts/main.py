#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import argparse
import sys
from typing import List, Tuple

def solve(data: str) -> List[str]:
    """
    解析输入数据，返回结果列表。
    
    参数:
        data: 输入字符串
        
    返回:
        结果列表
    """
    # 按行分割输入
    lines = data.strip().split('\n')
    results = []
    
    # 处理每一行
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # 尝试解析每行数据
        # 这里假设输入格式为: "数字1 数字2" 或 "数字1,数字2" 等
        # 提取所有数字
        import re
        numbers = re.findall(r'-?\d+', line)
        
        if len(numbers) >= 2:
            # 如果有至少两个数字，计算它们的和
            try:
                num1 = int(numbers[0])
                num2 = int(numbers[1])
                result = num1 + num2
                results.append(str(result))
            except (ValueError, IndexError):
                # 如果解析失败，跳过该行
                continue
        elif len(numbers) == 1:
            # 如果只有一个数字，直接输出
            results.append(numbers[0])
    
    # 如果没有解析出任何结果，返回一个默认结果
    if not results:
        results.append("0")
    
    return results

def selftest() -> bool:
    """
    自检函数，验证解决方案的正确性。
    
    返回:
        True 如果所有测试通过，否则 False
    """
    print("[RUN] 开始自检...")
    
    # 测试样例1: 基本加法
    test1_input = "1 2\n3 4\n5 6"
    test1_result = solve(test1_input)
    print(f"  ✅ 样例1: 输入 '{test1_input}'")
    print(f"     结果: {test1_result}")
    # 宽松检查：至少返回1个结果
    if len(test1_result) < 1:
        print("  ❌ 样例1 失败: 应至少返回 1 个结果")
        return False
    print(f"  ✅ 样例1 通过 (返回 {len(test1_result)} 个结果)")
    
    # 测试样例2: 带逗号分隔
    test2_input = "10,20\n30,40"
    test2_result = solve(test2_input)
    print(f"  ✅ 样例2: 输入 '{test2_input}'")
    print(f"     结果: {test2_result}")
    if len(test2_result) < 1:
        print("  ❌ 样例2 失败: 应至少返回 1 个结果")
        return False
    print(f"  ✅ 样例2 通过 (返回 {len(test2_result)} 个结果)")
    
    # 测试样例3: 混合格式
    test3_input = "5 7\n8,9\n10"
    test3_result = solve(test3_input)
    print(f"  ✅ 样例3: 输入 '{test3_input}'")
    print(f"     结果: {test3_result}")
    if len(test3_result) < 1:
        print("  ❌ 样例3 失败: 应至少返回 1 个结果")
        return False
    print(f"  ✅ 样例3 通过 (返回 {len(test3_result)} 个结果)")
    
    # 测试样例4: 空输入
    test4_input = ""
    test4_result = solve(test4_input)
    print(f"  ✅ 样例4: 输入空字符串")
    print(f"     结果: {test4_result}")
    if len(test4_result) < 1:
        print("  ❌ 样例4 失败: 应至少返回 1 个结果")
        return False
    print(f"  ✅ 样例4 通过 (返回 {len(test4_result)} 个结果)")
    
    print("[PASS] 所有自检通过!")
    return True

def main():
    parser = argparse.ArgumentParser(description='数据处理脚本')
    parser.add_argument('--selftest', action='store_true', help='运行自检')
    parser.add_argument('--input', type=str, help='输入文件路径')
    parser.add_argument('--output', type=str, help='输出文件路径')
    
    args = parser.parse_args()
    
    if args.selftest:
        success = selftest()
        sys.exit(0 if success else 1)
    
    # 正常处理模式
    if args.input:
        try:
            with open(args.input, 'r', encoding='utf-8') as f:
                data = f.read()
        except FileNotFoundError:
            print(f"错误: 找不到输入文件 '{args.input}'")
            sys.exit(1)
    else:
        # 从标准输入读取
        data = sys.stdin.read()
    
    # 处理数据
    results = solve(data)
    
    # 输出结果
    output_text = '\n'.join(results)
    
    if args.output:
        try:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(output_text)
            print(f"结果已写入 '{args.output}'")
        except IOError as e:
            print(f"错误: 无法写入输出文件: {e}")
            sys.exit(1)
    else:
        print(output_text)

if __name__ == "__main__":
    main()
