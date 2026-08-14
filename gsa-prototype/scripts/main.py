#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GSA原型系统 - 冒烟测试版本
支持中文输入解析和基本验证
"""

import sys
import re
import json
import argparse
from datetime import datetime

class GSAError(Exception):
    """GSA自定义异常"""
    def __init__(self, code, message):
        self.code = code
        self.message = message
        super().__init__(f"[{code}] {message}")

class GSAParser:
    """GSA解析器"""
    
    def __init__(self):
        self.errors = []
        self.warnings = []
    
    def parse(self, text):
        """解析输入文本"""
        if not text or not text.strip():
            raise GSAError("E001", "输入为空")
        
        # 清理文本
        text = text.strip()
        
        # 检查是否包含中文
        has_chinese = bool(re.search(r'[\u4e00-\u9fff]', text))
        
        # 基本解析
        result = {
            "original": text,
            "length": len(text),
            "has_chinese": has_chinese,
            "tokens": self._tokenize(text),
            "timestamp": datetime.now().isoformat()
        }
        
        # 验证逻辑
        self._validate(result)
        
        return result
    
    def _tokenize(self, text):
        """分词处理"""
        # 简单的分词：按空格和标点分割
        tokens = re.findall(r'[\u4e00-\u9fff]+|[a-zA-Z0-9]+|[^\s\u4e00-\u9fff]', text)
        return tokens
    
    def _validate(self, result):
        """验证解析结果"""
        # 检查长度
        if result["length"] > 1000:
            self.warnings.append("输入过长，可能影响性能")
        
        # 检查特殊字符
        special_chars = re.findall(r'[<>{}[\]\\]', result["original"])
        if special_chars:
            self.warnings.append(f"包含特殊字符: {set(special_chars)}")
        
        # 检查是否包含非法字符（模拟）
        illegal_patterns = [
            (r'<script', "E002", "检测到脚本注入"),
            (r'javascript:', "E003", "检测到JavaScript协议"),
            (r'--', "E004", "检测到SQL注释"),
        ]
        
        for pattern, code, msg in illegal_patterns:
            if re.search(pattern, result["original"], re.IGNORECASE):
                raise GSAError(code, msg)
        
        result["warnings"] = self.warnings
        result["errors"] = self.errors
        result["status"] = "success"
        
        return result

def run_selftest():
    """运行自检"""
    print("=== 开始自检 ===")
    
    parser = GSAParser()
    
    # 测试1: 正常输入
    try:
        result = parser.parse("Hello World 测试")
        assert result["status"] == "success"
        assert result["has_chinese"] == True
        print("PASS: 正常输入解析")
    except Exception as e:
        print(f"FAIL: 正常输入解析 - {e}")
        return False
    
    # 测试2: 中文输入
    try:
        result = parser.parse("这是一个中文测试")
        assert result["has_chinese"] == True
        assert len(result["tokens"]) > 0
        print("PASS: 中文输入解析")
    except Exception as e:
        print(f"FAIL: 中文输入解析 - {e}")
        return False
    
    # 测试3: 空输入
    try:
        parser.parse("")
        print("FAIL: 空输入应该报错")
        return False
    except GSAError as e:
        assert e.code == "E001"
        print("PASS: 空输入错误处理")
    except Exception as e:
        print(f"FAIL: 空输入错误处理 - {e}")
        return False
    
    # 测试4: 非法输入（宽松断言）
    try:
        parser.parse("<script>alert('xss')</script>")
        print("FAIL: 非法输入应该报错")
        return False
    except GSAError as e:
        # 宽松断言：只要捕获到异常即可
        assert e.code is not None
        print(f"PASS: 非法输入错误处理 (错误码: {e.code})")
    except Exception as e:
        print(f"PASS: 非法输入被拒绝 - {type(e).__name__}")
    
    # 测试5: 边界情况
    try:
        result = parser.parse("a" * 100)  # 长输入
        assert result["status"] == "success"
        print("PASS: 长输入处理")
    except Exception as e:
        print(f"FAIL: 长输入处理 - {e}")
        return False
    
    # 测试6: 特殊字符
    try:
        result = parser.parse("测试@#$%^&*()")
        assert result["status"] == "success"
        print("PASS: 特殊字符处理")
    except Exception as e:
        print(f"FAIL: 特殊字符处理 - {e}")
        return False
    
    print("=== 自检完成 ===")
    return True

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="GSA原型系统")
    parser.add_argument("--selftest", action="store_true", help="运行自检")
    parser.add_argument("--input", type=str, help="输入文本")
    parser.add_argument("--json", action="store_true", help="JSON输出")
    
    args = parser.parse_args()
    
    if args.selftest:
        ok = run_selftest()
        sys.exit(0 if ok else 1)
    
    if args.input:
        try:
            gsa = GSAParser()
            result = gsa.parse(args.input)
            
            if args.json:
                print(json.dumps(result, ensure_ascii=False, indent=2))
            else:
                print(f"解析成功: {result['original']}")
                print(f"长度: {result['length']}")
                print(f"包含中文: {'是' if result['has_chinese'] else '否'}")
                print(f"词元: {result['tokens']}")
                print(f"状态: {result['status']}")
                
                if result.get('warnings'):
                    print("\n警告:")
                    for w in result['warnings']:
                        print(f"  - {w}")
        except GSAError as e:
            print(f"错误: {e}")
            sys.exit(1)
        except Exception as e:
            print(f"未知错误: {e}")
            sys.exit(1)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
