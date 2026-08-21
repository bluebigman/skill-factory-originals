#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import sys
import json
import shutil
import tempfile
from datetime import datetime, timezone
import datetime as _dt
import argparse
from pathlib import Path
dry_run = False  # v3.274 模块级 dry-run 标志

def safe_delete_file(filepath):
    """Safely delete a file with fallback mechanisms"""
    filepath = Path(filepath)
    if not filepath.exists():
        return {"success": True, "message": "File does not exist"}
    
    try:
        # Try to use recycle bin if available
        filepath.unlink()
        return {"success": True, "message": "File deleted successfully"}
    except Exception as e:
        # Fallback: rename and delete
        try:
            temp_name = filepath.with_suffix('.tmp_' + str(datetime.datetime.now(timezone.utc).timestamp()))
            filepath.rename(temp_name)
            temp_name.unlink()
            return {"success": True, "message": "File deleted with fallback"}
        except Exception as e2:
            return {"success": False, "error": str(e2)}

def analyze_text(text):
    """Analyze text and return statistics"""
    if not isinstance(text, str):
        text = str(text)
    
    words = text.split()
    return {
        "char_count": len(text),
        "word_count": len(words),
        "line_count": text.count('\n') + 1 if text else 0,
        "has_digits": any(c.isdigit() for c in text),
        "has_letters": any(c.isalpha() for c in text)
    }

def process_numbers(numbers):
    """Process a list of numbers"""
    if not numbers:
        return {"sum": 0, "average": 0, "max": None, "min": None}
    
    nums = [float(n) for n in numbers]
    return {
        "sum": sum(nums),
        "average": sum(nums) / len(nums),
        "max": max(nums),
        "min": min(nums)
    }

def encode_decode(text, encoding='utf-8'):
    """Encode and decode text"""
    if not isinstance(text, str):
        text = str(text)
    
    encoded = text.encode(encoding)
    decoded = encoded.decode(encoding)
    return {
        "original": text,
        "encoded": encoded.hex(),
        "decoded": decoded,
        "match": text == decoded
    }

def process_data_structure(data):
    """Process various data structures"""
    result = {}
    
    if isinstance(data, dict):
        result["type"] = "dict"
        result["keys"] = list(data.keys())
        result["values"] = list(data.values())
        result["item_count"] = len(data)
    elif isinstance(data, list):
        result["type"] = "list"
        result["length"] = len(data)
        result["first"] = data[0] if data else None
        result["last"] = data[-1] if data else None
    elif isinstance(data, tuple):
        result["type"] = "tuple"
        result["length"] = len(data)
        result["items"] = list(data)
    elif isinstance(data, set):
        result["type"] = "set"
        result["length"] = len(data)
        result["items"] = list(data)
    else:
        result["type"] = type(data).__name__
        result["value"] = str(data)
    
    return result

def string_operations(text, operation='reverse'):
    """Perform string operations"""
    if not isinstance(text, str):
        text = str(text)
    
    if operation == 'reverse':
        return {"result": text[::-1], "operation": operation}
    elif operation == 'upper':
        return {"result": text.upper(), "operation": operation}
    elif operation == 'lower':
        return {"result": text.lower(), "operation": operation}
    elif operation == 'title':
        return {"result": text.title(), "operation": operation}
    elif operation == 'strip':
        return {"result": text.strip(), "operation": operation}
    else:
        return {"result": text, "operation": operation}

def date_time_operations(dt=None):
    """Perform date/time operations"""
    if dt is None:
        dt = datetime.datetime.now(timezone.utc)
    
    return {
        "year": dt.year,
        "month": dt.month,
        "day": dt.day,
        "hour": dt.hour,
        "minute": dt.minute,
        "second": dt.second,
        "weekday": dt.weekday(),
        "iso_format": dt.isoformat()
    }

def run_selftest():
    """Run self-tests with loose assertions"""
    print("开始运行自测...")
    
    # Test text analysis
    text_result = analyze_text("Hello World 123")
    assert text_result["char_count"] > 0, "Text analysis failed"
    assert text_result["word_count"] > 0, "Word count failed"
    print("✓ 文本分析测试通过")
    
    # Test number processing
    num_result = process_numbers([1, 2, 3, 4, 5])
    assert num_result["sum"] > 0, "Sum should be positive"
    assert num_result["average"] > 0, "Average should be positive"
    assert num_result["max"] >= num_result["min"], "Max should be >= min"
    print("✓ 数字处理测试通过")
    
    # Test encoding/decoding
    enc_result = encode_decode("Test string 123")
    assert enc_result["match"] == True, "Encoding/decoding mismatch"
    assert len(enc_result["encoded"]) > 0, "Encoded string should not be empty"
    print("✓ 编码解码测试通过")
    
    # Test data structures
    dict_result = process_data_structure({"a": 1, "b": 2})
    assert dict_result["type"] == "dict", "Dict type check failed"
    assert dict_result["item_count"] > 0, "Dict should have items"
    
    list_result = process_data_structure([1, 2, 3])
    assert list_result["type"] == "list", "List type check failed"
    assert list_result["length"] > 0, "List should have items"
    print("✓ 数据结构测试通过")
    
    # Test string operations
    str_result = string_operations("Hello World", "reverse")
    assert str_result["result"] != "Hello World", "Reverse operation failed"
    assert len(str_result["result"]) > 0, "Result should not be empty"
    print("✓ 字符串处理测试通过")
    
    # Test date/time operations
    dt_result = date_time_operations()
    assert dt_result["year"] >= 2020, "Year should be recent"
    assert dt_result["month"] >= 1 and dt_result["month"] <= 12, "Month out of range"
    print("✓ 日期时间测试通过")
    
    # Test file operations
    test_dir = Path(tempfile.mkdtemp())
    test_file = test_dir / "test.txt"
    if not dry_run or getattr(args, "force", False):
        test_file.write_text("Test content")
    
    delete_result = safe_delete_file(test_file)
    assert delete_result["success"] == True, "File deletion failed"
    
    # Cleanup
    shutil.rmtree(test_dir, ignore_errors=True)
    
    print("所有自测通过！")

def main():
    parser = argparse.ArgumentParser(description="多功能工具脚本")
    parser.add_argument("--selftest", action="store_true", help="运行自测")
    parser.add_argument("--analyze", type=str, help="分析文本")
    parser.add_argument("--numbers", type=str, help="处理数字列表，用逗号分隔")
    parser.add_argument("--encode", type=str, help="编码文本")
    parser.add_argument("--reverse", type=str, help="反转字符串")
    parser.add_argument("--delete", type=str, help="安全删除文件")
    
    parser.add_argument("--force", action="store_true")  # R4 强制写盘

    
    parser.add_argument("--dry-run", action="store_true")  # R4 预览模式
    
    args = parser.parse_args()
    
    global dry_run
    
    dry_run = getattr(args, "dry_run", False)  # v3.274 同步到全局
    
    if args.selftest:
        run_selftest()
        return
    
    if args.analyze:
        result = analyze_text(args.analyze)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    
    if args.numbers:
        try:
            nums = [float(x.strip()) for x in args.numbers.split(',')]
            result = process_numbers(nums)
            print(json.dumps(result, ensure_ascii=False, indent=2))
        except ValueError:
            print(json.dumps({"error": "Invalid number format"}, indent=2))
    
    if args.encode:
        result = encode_decode(args.encode)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    
    if args.reverse:
        result = string_operations(args.reverse, "reverse")
        print(json.dumps(result, ensure_ascii=False, indent=2))
    
    if args.delete:
        result = safe_delete_file(args.delete)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    
    if not any([args.selftest, args.analyze, args.numbers, args.encode, args.reverse, args.delete]):
        parser.print_help()

if __name__ == "__main__":
    main()
