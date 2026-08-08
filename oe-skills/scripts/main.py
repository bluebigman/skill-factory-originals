#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import json
import os
import sys
import tempfile
import shutil
from pathlib import Path


def analyze_text_file(file_path):
    """分析文本文件，返回结构化结果"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except UnicodeDecodeError:
        try:
            with open(file_path, 'r', encoding='gbk') as f:
                content = f.read()
        except UnicodeDecodeError:
            with open(file_path, 'r', encoding='latin-1') as f:
                content = f.read()
    except Exception as e:
        return {"type": "error", "message": str(e)}

    lines = content.splitlines()
    line_count = len(lines)
    char_count = len(content)

    result = {
        "type": "text",
        "lines": line_count,
        "characters": char_count,
        "structured": {
            "first_line": lines[0] if lines else "",
            "last_line": lines[-1] if lines else ""
        }
    }
    return result


def analyze_binary_file(file_path):
    """分析二进制文件，返回基本信息"""
    try:
        file_size = os.path.getsize(file_path)
        with open(file_path, 'rb') as f:
            header = f.read(16)
        return {
            "type": "binary",
            "size": file_size,
            "header_hex": header.hex()
        }
    except Exception as e:
        return {"type": "error", "message": str(e)}


def analyze_file(file_path):
    """分析文件，自动判断文本或二进制"""
    if not os.path.exists(file_path):
        return {"type": "error", "message": f"文件不存在: {file_path}"}

    try:
        with open(file_path, 'rb') as f:
            sample = f.read(1024)
    except Exception as e:
        return {"type": "error", "message": str(e)}

    if not sample:
        # 空文件按文本处理
        return analyze_text_file(file_path)

    try:
        sample.decode('utf-8')
        return analyze_text_file(file_path)
    except UnicodeDecodeError:
        try:
            sample.decode('gbk')
            return analyze_text_file(file_path)
        except UnicodeDecodeError:
            return analyze_binary_file(file_path)


def format_output(result):
    """格式化输出结果"""
    lines = []
    lines.append("文件分析结果:")
    if result.get("type") == "text":
        lines.append(f"  类型: 文本")
        lines.append(f"  行数: {result.get('lines', 0)}")
        lines.append(f"  字符数: {result.get('characters', 0)}")
        structured = result.get("structured", {})
        if structured.get("first_line"):
            lines.append(f"  首行: {structured['first_line'][:50]}")
        if structured.get("last_line"):
            lines.append(f"  末行: {structured['last_line'][:50]}")
    elif result.get("type") == "binary":
        lines.append(f"  类型: 二进制")
        lines.append(f"  大小: {result.get('size', 0)} 字节")
        lines.append(f"  头部(hex): {result.get('header_hex', '')}")
    elif result.get("type") == "error":
        lines.append(f"  错误: {result.get('message', '未知错误')}")
    else:
        lines.append(f"  未知类型")
    return "\n".join(lines)


def run_selftest():
    """运行自测试"""
    test_dir = tempfile.mkdtemp(prefix="oe_skills_test_")
    try:
        test_file = os.path.join(test_dir, "test.txt")

        # 创建测试文本文件
        test_content = "第一行\n第二行\n第三行\n"
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write(test_content)

        # 测试文本分析
        result = analyze_file(test_file)
        assert result["type"] == "text", "文本类型判断失败"
        assert result["lines"] == 3, f"行数错误: {result['lines']}"
        assert result["characters"] == len(test_content), f"字符数错误: {result['characters']}"
        assert result["structured"]["first_line"] == "第一行", "首行错误"
        assert result["structured"]["last_line"] == "第三行", "末行错误"

        # 测试二进制分析
        bin_file = os.path.join(test_dir, "test.bin")
        with open(bin_file, 'wb') as f:
            f.write(b'\x00\x01\x02\x03\xff')

        result = analyze_file(bin_file)
        assert result["type"] == "binary", "二进制类型判断失败"
        assert result["size"] == 5, f"二进制大小错误: {result['size']}"

        # 测试格式化输出
        output = format_output(result)
        assert "二进制" in output, "格式化输出错误"

        # 测试空文件
        empty_file = os.path.join(test_dir, "empty.txt")
        with open(empty_file, 'w', encoding='utf-8') as f:
            pass
        result = analyze_file(empty_file)
        assert result["type"] == "text", "空文件类型判断失败"
        assert result["lines"] == 0, f"空文件行数错误: {result['lines']}"
        assert result["characters"] == 0, f"空文件字符数错误: {result['characters']}"

        # 测试不存在的文件
        result = analyze_file(os.path.join(test_dir, "nonexistent.txt"))
        assert result["type"] == "error", "不存在文件应返回错误"

        # 测试错误处理
        output = format_output({"type": "error", "message": "测试错误"})
        assert "错误" in output, "错误格式化输出错误"

        # 测试JSON输出
        result = analyze_file(test_file)
        json_str = json.dumps(result, ensure_ascii=False)
        assert json_str, "JSON序列化失败"

        print("自测试通过")
        return 0
    finally:
        shutil.rmtree(test_dir, ignore_errors=True)


def main():
    parser = argparse.ArgumentParser(description="文件分析工具")
    parser.add_argument("file", nargs="?", help="要分析的文件路径")
    parser.add_argument("--selftest", action="store_true", help="运行自测试")
    parser.add_argument("--json", action="store_true", help="以JSON格式输出")
    args = parser.parse_args()

    if args.selftest:
        return run_selftest()

    if not args.file:
        print("错误: 请指定文件路径或使用 --selftest", file=sys.stderr)
        return 1

    if not os.path.exists(args.file):
        print(f"错误: 文件不存在: {args.file}", file=sys.stderr)
        return 1

    result = analyze_file(args.file)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        output = format_output(result)
        print(output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
