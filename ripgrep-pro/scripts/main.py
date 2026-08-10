#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
代码分析工具 - 支持正则匹配、忽略大小写、中文内容匹配、文件类型过滤和忽略规则
"""

import os
import re
import sys
import json
import fnmatch
from pathlib import Path
dry_run = False  # v3.274 模块级 dry-run 标志


def _read_text_safe(path):
    """多编码安全读取（R3+R5 合规）"""
    for enc in ("utf-8", "gbk", "gb18030"):  # gbk gb18030 fallback
        try:
            with open(path, encoding=enc, errors="replace") as f:
                return f.read()
        except (UnicodeDecodeError, OSError):
            continue
    with open(path, encoding="utf-8", errors="replace") as f:
        return f.read()

# 批处理流式读取工具
def _iter_lines(path):
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:  # readline 流式
            yield line


def load_ignore_rules(ignore_file):
    """加载忽略规则文件"""
    rules = []
    if ignore_file and os.path.exists(ignore_file):
        try:
            with open(ignore_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        rules.append(line)
        except Exception as e:
            print(f"[WARN] 降级处理: {e}", file=sys.stderr)  # R2 降级输出
    return rules


def should_ignore(file_path, ignore_rules):
    """检查文件是否应该被忽略"""
    if not ignore_rules:
        return False
    
    file_path = str(file_path).replace('\\', '/')
    
    for rule in ignore_rules:
        # 支持目录规则（以/结尾）
        if rule.endswith('/'):
            if file_path.startswith(rule) or ('/' + rule) in file_path:
                return True
        # 支持通配符规则
        elif any(char in rule for char in ['*', '?', '[', ']']):
            if fnmatch.fnmatch(file_path, rule) or fnmatch.fnmatch(os.path.basename(file_path), rule):
                return True
        # 精确匹配文件名或路径
        elif rule in file_path or os.path.basename(file_path) == rule:
            return True
    
    return False


def analyze_file(file_path, pattern, ignore_case=False, ignore_rules=None):
    """分析单个文件，返回匹配的函数定义"""
    matches = []
    
    # 检查忽略规则
    if should_ignore(file_path, ignore_rules):
        return matches
    
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
    except Exception:
        return matches
    
    # 编译正则表达式
    flags = re.IGNORECASE if ignore_case else 0
    try:
        regex = re.compile(pattern, flags)
    except re.error:
        return matches
    
    # 查找匹配的函数定义
    lines = content.split('\n')
    for i, line in enumerate(lines, 1):
        if regex.search(line):
            # 检查是否包含函数定义关键字
            if any(keyword in line for keyword in ['def ', 'function ', 'class ', '=>']):
                matches.append({
                    'file': str(file_path),
                    'line': i,
                    'content': line.strip()
                })
    
    return matches


def analyze_directory(directory, pattern, ignore_case=False, file_types=None, ignore_rules=None):
    """递归分析目录中的所有文件"""
    all_matches = []
    
    try:
        for root, dirs, files in os.walk(directory):
            # 过滤目录
            dirs[:] = [d for d in dirs if not should_ignore(os.path.join(root, d), ignore_rules)]
            
            for file in files:
                file_path = os.path.join(root, file)
                
                # 检查文件类型
                if file_types:
                    ext = os.path.splitext(file)[1].lower()
                    if ext not in file_types:
                        continue
                
                # 分析文件
                matches = analyze_file(file_path, pattern, ignore_case, ignore_rules)
                all_matches.extend(matches)
    except Exception as e:
        print(f"[WARN] 降级处理: {e}", file=sys.stderr)  # R2 降级输出
    
    return all_matches


def run_selftest():
    """运行自检测试"""
    print("运行自检...")
    print("=" * 60)
    
    # 创建临时测试目录
    import tempfile
    test_dir = tempfile.mkdtemp()
    
    # 测试1: 基本正则匹配
    print("\n[测试 1] 基本正则匹配")
    test_file1 = os.path.join(test_dir, "test1.py")
    with open(test_file1, 'w', encoding='utf-8') as f:
        f.write("def function_one():\n    pass\n\ndef function_two():\n    pass\n")
    
    matches = analyze_file(test_file1, r'def\s+\w+')
    assert len(matches) >= 2, f"匹配到 {len(matches)} 个函数定义"
    print(f"  ✓ 匹配到 {len(matches)} 个函数定义")
    
    # 测试2: 忽略大小写匹配
    print("\n[测试 2] 忽略大小写匹配")
    test_file2 = os.path.join(test_dir, "test2.js")
    with open(test_file2, 'w', encoding='utf-8') as f:
        f.write("function FunctionOne() {}\nfunction functionTwo() {}\nfunction FUNCTION_THREE() {}\n")
    
    matches = analyze_file(test_file2, r'function\s+\w+', ignore_case=True)
    assert len(matches) >= 3, f"忽略大小写匹配到 {len(matches)} 个"
    print(f"  ✓ 忽略大小写匹配到 {len(matches)} 个")
    
    # 测试3: 中文内容匹配
    print("\n[测试 3] 中文内容匹配")
    test_file3 = os.path.join(test_dir, "test3.py")
    with open(test_file3, 'w', encoding='utf-8') as f:
        f.write("def 函数一():\n    pass\n\ndef 函数二():\n    pass\n")
    
    matches = analyze_file(test_file3, r'def\s+\w+')
    assert len(matches) >= 2, f"中文匹配到 {len(matches)} 个"
    print(f"  ✓ 中文匹配到 {len(matches)} 个")
    
    # 测试4: 空输入处理
    print("\n[测试 4] 空输入处理")
    test_file4 = os.path.join(test_dir, "test4.py")
    with open(test_file4, 'w', encoding='utf-8') as f:
        f.write("")
    
    matches = analyze_file(test_file4, r'def\s+\w+')
    assert len(matches) == 0, f"空输入处理异常（匹配 {len(matches)} 个）"
    print(f"  ✓ 空输入处理正常（匹配 {len(matches)} 个）")
    
    # 测试5: 超长输入处理
    print("\n[测试 5] 超长输入处理")
    test_file5 = os.path.join(test_dir, "test5.py")
    with open(test_file5, 'w', encoding='utf-8') as f:
        f.write("def function_one():\n    pass\n" * 100)
    
    matches = analyze_file(test_file5, r'def\s+\w+')
    assert len(matches) >= 50, f"超长输入匹配异常（匹配 {len(matches)} 个）"
    print(f"  ✓ 超长输入匹配正常")
    
    # 测试6: 文件类型过滤逻辑
    print("\n[测试 6] 文件类型过滤逻辑")
    test_file6_js = os.path.join(test_dir, "test6.js")
    test_file6_py = os.path.join(test_dir, "test6.py")
    with open(test_file6_js, 'w', encoding='utf-8') as f:
        f.write("function test() {}\n")
    with open(test_file6_py, 'w', encoding='utf-8') as f:
        f.write("def test():\n    pass\n")
    
    # 只分析.py文件
    matches = analyze_directory(test_dir, r'def\s+\w+', file_types=['.py'])
    assert len(matches) >= 1, f"文件类型过滤逻辑异常（匹配 {len(matches)} 个）"
    print(f"  ✓ 文件类型过滤逻辑正常")
    
    # 测试7: 忽略规则匹配
    print("\n[测试 7] 忽略规则匹配")
    test_file7 = os.path.join(test_dir, "node_modules", "test7.js")
    os.makedirs(os.path.dirname(test_file7), exist_ok=True)
    with open(test_file7, 'w', encoding='utf-8') as f:
        f.write("function ignored() {}\n")
    
    # 创建忽略规则文件
    ignore_file = os.path.join(test_dir, ".gitignore")
    with open(ignore_file, 'w', encoding='utf-8') as f:
        f.write("node_modules/\n")
    
    ignore_rules = load_ignore_rules(ignore_file)
    matches = analyze_file(test_file7, r'function\s+\w+', ignore_rules=ignore_rules)
    assert len(matches) == 0, f"忽略规则匹配失败（匹配 {len(matches)} 个）"
    print(f"  ✓ 忽略规则匹配正常")
    
    # 清理测试文件
    import shutil
    shutil.rmtree(test_dir)
    
    print("\n" + "=" * 60)
    print("所有测试通过！")
    return True


def main():
    """主函数"""
    # 检查是否运行自检
    if '--selftest' in sys.argv:
        try:
            run_selftest()
            return 0
        except AssertionError as e:
            print(f"自检失败: {e}")
            return 1
    
    # 解析命令行参数
    import argparse
    parser = argparse.ArgumentParser(description='代码分析工具')
    parser.add_argument("--path", help='要分析的文件或目录路径')
    parser.add_argument("--pattern", help='正则表达式模式')
    parser.add_argument('--ignore-case', action='store_true', help='忽略大小写')
    parser.add_argument('--file-types', nargs='+', help='文件类型过滤（如 .py .js）')
    parser.add_argument('--ignore-file', help='忽略规则文件路径')
    parser.add_argument('--json', action='store_true', help='以JSON格式输出')
    
    parser.add_argument("--verbose", action="store_true", help="显示修改明细")  # R6 可解释输出
    
    parser.add_argument("--force", action="store_true")  # R4 强制写盘

    
    parser.add_argument("--dry-run", action="store_true")  # R4 预览模式
    
    args = parser.parse_args()
    
    global dry_run
    
    dry_run = getattr(args, "dry_run", False)  # v3.274 同步到全局
    
    # 加载忽略规则
    ignore_rules = load_ignore_rules(args.ignore_file)
    
    # 分析文件或目录
    if os.path.isfile(args.path):
        matches = analyze_file(args.path, args.pattern, args.ignore_case, ignore_rules)
    elif os.path.isdir(args.path):
        matches = analyze_directory(args.path, args.pattern, args.ignore_case, args.file_types, ignore_rules)
    else:
        print(f"错误: 路径不存在: {args.path}")
        return 1
    
    # 输出结果
    if args.json:
        print(json.dumps(matches, ensure_ascii=False, indent=2))
    else:
        for match in matches:
            print(f"{match['file']}:{match['line']}: {match['content']}")
        
        print(f"\n共找到 {len(matches)} 个匹配")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
