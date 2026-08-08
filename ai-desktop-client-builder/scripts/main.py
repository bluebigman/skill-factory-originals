#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""文本处理工具 - 支持编码检测、文本清洗和Diff生成"""

import argparse
import sys
import re
import difflib
import json
import os
from typing import List, Optional, Tuple, Dict, Any

def detect_encoding(text: str) -> str:
    """检测文本编码类型"""
    if text is None:
        return "unknown"
    
    # 检查是否包含中文字符
    if re.search(r'[\u4e00-\u9fff]', text):
        return "utf-8"
    
    # 检查是否包含其他Unicode字符
    if re.search(r'[^\x00-\x7f]', text):
        return "unicode"
    
    # 检查是否包含特殊字符
    if re.search(r'[\x80-\xff]', text):
        return "latin-1"
    
    return "ascii"

def clean_text(text: str) -> str:
    """清理文本：去除多余空白和特殊字符"""
    if text is None:
        return ""
    
    # 去除首尾空白
    text = text.strip()
    
    # 将多个连续空白替换为单个空格
    text = re.sub(r'\s+', ' ', text)
    
    # 去除控制字符
    text = ''.join(char for char in text if ord(char) >= 32 or char in '\n\t')
    
    return text

def generate_diff(text1: str, text2: str) -> str:
    """生成两个文本的差异"""
    if text1 is None:
        text1 = ""
    if text2 is None:
        text2 = ""
    
    lines1 = text1.splitlines()
    lines2 = text2.splitlines()
    
    diff = difflib.unified_diff(lines1, lines2, lineterm='')
    return '\n'.join(diff)

def process_text(text: str, operation: str = "clean") -> Dict[str, Any]:
    """处理文本并返回结果"""
    if text is None:
        text = ""
    
    result = {
        "original": text,
        "encoding": detect_encoding(text),
        "length": len(text),
        "operation": operation
    }
    
    if operation == "clean":
        result["result"] = clean_text(text)
    elif operation == "upper":
        result["result"] = text.upper()
    elif operation == "lower":
        result["result"] = text.lower()
    elif operation == "strip":
        result["result"] = text.strip()
    else:
        result["result"] = text
    
    return result

def process_batch(texts: List[str], operation: str = "clean") -> List[Dict[str, Any]]:
    """批量处理文本"""
    if texts is None:
        return []
    
    results = []
    for text in texts:
        results.append(process_text(text, operation))
    
    return results

def run_selftest() -> bool:
    """运行自测"""
    tests = [
        ("空输入", lambda: process_text("")["length"] == 0),
        ("None输入", lambda: process_text(None)["length"] == 0),
        ("英文文本", lambda: process_text("Hello World")["encoding"] == "ascii"),
        ("超长输入", lambda: process_text("x" * 10000)["length"] >= 10000),
        ("中文标点", lambda: detect_encoding("你好，世界！") == "utf-8"),
        ("混合编码", lambda: detect_encoding("Hello 你好 World") == "utf-8"),
        ("批量处理", lambda: len(process_batch(["a", "b", "c"])) == 3),
        ("中文编码", lambda: detect_encoding("中文测试") == "utf-8"),
        ("输出格式", lambda: isinstance(process_text("test"), dict)),
        ("Diff生成", lambda: len(generate_diff("line1\nline2", "line1\nline3")) > 0),
        ("错误码", lambda: process_text("")["operation"] == "clean")
    ]
    
    passed = 0
    failed = 0
    
    print("[RUN] 开始自检...")
    
    for name, test_func in tests:
        try:
            if test_func():
                print(f"[PASS] {name}")
                passed += 1
            else:
                print(f"[FAIL] {name}: 断言失败")
                failed += 1
        except Exception as e:
            print(f"[FAIL] {name}: {str(e)}")
            failed += 1
    
    print(f"\n自检完成: {passed} 通过, {failed} 失败")
    
    return failed == 0

def main():
    parser = argparse.ArgumentParser(description="文本处理工具")
    parser.add_argument("--selftest", action="store_true", help="运行自测")
    parser.add_argument("--text", type=str, help="要处理的文本")
    parser.add_argument("--operation", type=str, default="clean", 
                       choices=["clean", "upper", "lower", "strip"],
                       help="操作类型")
    parser.add_argument("--batch", type=str, help="批量处理，用逗号分隔")
    parser.add_argument("--diff", nargs=2, metavar=("TEXT1", "TEXT2"), 
                       help="生成两个文本的差异")
    parser.add_argument("--json", action="store_true", help="输出JSON格式")
    
    args = parser.parse_args()
    
    if args.selftest:
        success = run_selftest()
        sys.exit(0 if success else 1)
    
    if args.diff:
        diff = generate_diff(args.diff[0], args.diff[1])
        print(diff)
        return
    
    if args.batch:
        texts = args.batch.split(",")
        results = process_batch(texts, args.operation)
    elif args.text is not None:
        results = process_text(args.text, args.operation)
    else:
        # 从stdin读取
        text = sys.stdin.read()
        results = process_text(text, args.operation)
    
    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        if isinstance(results, list):
            for r in results:
                print(f"原始: {r['original'][:50]}...")
                print(f"结果: {r['result'][:50]}...")
                print(f"编码: {r['encoding']}, 长度: {r['length']}")
                print("---")
        else:
            print(f"原始: {results['original'][:50]}...")
            print(f"结果: {results['result'][:50]}...")
            print(f"编码: {results['encoding']}, 长度: {results['length']}")

if __name__ == "__main__":
    main()
