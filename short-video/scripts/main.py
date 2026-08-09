#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
import re
import argparse
from datetime import timedelta

# 错误码定义
ERROR_CODES = {
    'E001': '输入为空',
    'E002': '文件不存在',
    'E003': 'SRT格式错误',
    'E004': '时间格式错误',
    'E005': '序号格式错误',
    'E006': '字幕内容为空',
    'E007': '时间顺序错误',
    'E008': '输入参数错误',
    'E009': '编码错误',
    'E010': '输出错误'
}

class SRTValidator:
    """SRT字幕文件验证器"""
    
    def __init__(self):
        self.errors = []
        self.blocks = []
    
    def validate(self, content):
        """验证SRT内容"""
        self.errors = []
        self.blocks = []
        
        if not content or not content.strip():
            self.errors.append(('E001', '输入为空'))
            return False
        
        # 按块分割
        blocks = re.split(r'\n\s*\n', content.strip())
        
        for block in blocks:
            if not block.strip():
                continue
            
            lines = block.strip().split('\n')
            if len(lines) < 3:
                self.errors.append(('E003', 'SRT格式错误'))
                continue
            
            # 检查序号
            if not lines[0].strip().isdigit():
                self.errors.append(('E005', f'序号格式错误: {lines[0]}'))
                continue
            
            # 检查时间格式
            time_pattern = r'(\d{1,2}:\d{2}:\d{2}[,.]\d{1,3})\s*-->\s*(\d{1,2}:\d{2}:\d{2}[,.]\d{1,3})'
            time_match = re.search(time_pattern, lines[1])
            if not time_match:
                self.errors.append(('E004', f'时间格式错误: {lines[1]}'))
                continue
            
            # 检查时间顺序
            start_time = self._parse_time(time_match.group(1))
            end_time = self._parse_time(time_match.group(2))
            if start_time is None or end_time is None:
                self.errors.append(('E004', f'时间解析错误: {lines[1]}'))
                continue
            
            if start_time > end_time:
                self.errors.append(('E007', f'时间顺序错误: {lines[1]}'))
                continue
            
            # 检查字幕内容
            text_lines = lines[2:]
            if not text_lines or not any(line.strip() for line in text_lines):
                self.errors.append(('E006', '字幕内容为空'))
                continue
            
            # 保存块信息
            self.blocks.append({
                'index': int(lines[0].strip()),
                'start': start_time,
                'end': end_time,
                'text': '\n'.join(text_lines)
            })
        
        return len(self.errors) == 0
    
    def _parse_time(self, time_str):
        """解析时间字符串为秒数"""
        try:
            # 处理逗号或点号
            time_str = time_str.replace(',', '.')
            parts = time_str.split(':')
            if len(parts) == 3:
                hours = int(parts[0])
                minutes = int(parts[1])
                seconds_parts = parts[2].split('.')
                seconds = int(seconds_parts[0])
                milliseconds = int(seconds_parts[1]) if len(seconds_parts) > 1 else 0
                return hours * 3600 + minutes * 60 + seconds + milliseconds / 1000.0
        except (ValueError, IndexError):
            pass
        return None
    
    def get_error_summary(self):
        """获取错误摘要"""
        if not self.errors:
            return "验证通过"
        
        summary = []
        for code, msg in self.errors:
            summary.append(f"[{code}] {msg}")
        return "; ".join(summary)

def read_file(filepath):
    """读取文件，支持多种编码"""
    encodings = ['utf-8', 'gbk', 'gb2312', 'latin-1']
    
    for encoding in encodings:
        try:
            with open(filepath, 'r', encoding=encoding) as f:
                return f.read(), encoding
        except UnicodeDecodeError:
            continue
        except FileNotFoundError:
            raise
    
    raise ValueError(f"无法解码文件: {filepath}")

def process_file(filepath):
    """处理SRT文件"""
    try:
        content, encoding = read_file(filepath)
    except FileNotFoundError:
        return {'success': False, 'error': 'E002', 'message': '文件不存在'}
    except ValueError as e:
        return {'success': False, 'error': 'E009', 'message': str(e)}
    
    validator = SRTValidator()
    is_valid = validator.validate(content)
    
    return {
        'success': is_valid,
        'error': validator.errors[0][0] if validator.errors else None,
        'message': validator.get_error_summary(),
        'encoding': encoding,
        'block_count': len(validator.blocks)
    }

def validate_input(input_str):
    """验证输入参数"""
    if not input_str or not input_str.strip():
        return False, 'E001', '输入为空'
    
    if len(input_str) > 1000000:
        return False, 'E008', '输入过长'
    
    return True, None, None

def run_selftest():
    """运行自检测试"""
    tests_passed = 0
    tests_failed = 0
    
    # 测试1: 基本SRT验证
    print("[测试 1] 基本SRT验证")
    try:
        valid_srt = """1
00:00:01,000 --> 00:00:03,000
Hello World

2
00:00:04,000 --> 00:00:06,000
Testing SRT"""
        validator = SRTValidator()
        assert validator.validate(valid_srt), "有效SRT应该通过验证"
        print("  ✓ 有效SRT通过验证")
        tests_passed += 1
    except AssertionError as e:
        print(f"  ✗ {e}")
        tests_failed += 1
    
    # 测试2: 无效SRT
    print("[测试 2] 无效SRT")
    try:
        invalid_srt = """1
invalid time format
Test content"""
        validator = SRTValidator()
        assert not validator.validate(invalid_srt), "无效SRT应该被拒绝"
        print("  ✓ 无效SRT被正确拒绝")
        tests_passed += 1
    except AssertionError as e:
        print(f"  ✗ {e}")
        tests_failed += 1
    
    # 测试3: 错误格式
    print("[测试 3] 错误格式")
    try:
        wrong_format = "This is not SRT format"
        validator = SRTValidator()
        assert not validator.validate(wrong_format), "错误格式应该被拒绝"
        print("  ✓ 错误格式被正确识别")
        tests_passed += 1
    except AssertionError as e:
        print(f"  ✗ {e}")
        tests_failed += 1
    
    # 测试4: 空输入
    print("[测试 4] 空输入处理")
    try:
        validator = SRTValidator()
        assert not validator.validate(""), "空输入应该被拒绝"
        print("  ✓ 空输入被正确拒绝")
        tests_passed += 1
    except AssertionError as e:
        print(f"  ✗ {e}")
        tests_failed += 1
    
    # 测试5: 中文标点
    print("[测试 5] 中文标点处理")
    try:
        chinese_srt = """1
00:00:01,000 --> 00:00:03,000
你好，世界！
测试中文字幕。"""
        validator = SRTValidator()
        assert validator.validate(chinese_srt), "中文SRT应该通过验证"
        print("  ✓ 中文标点 SRT 通过校验")
        tests_passed += 1
    except AssertionError as e:
        print(f"  ✗ {e}")
        tests_failed += 1
    
    # 测试6: 文件读写
    print("[测试 6] 文件读写")
    try:
        test_file = "/tmp/test_srt.srt"
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write(valid_srt)
        result = process_file(test_file)
        assert result['success'], "文件应该能正常读取"
        os.remove(test_file)
        print("  ✓ 文件读写正常")
        tests_passed += 1
    except AssertionError as e:
        print(f"  ✗ {e}")
        tests_failed += 1
    
    # 测试7: 输入校验
    print("[测试 7] 输入校验")
    try:
        is_valid, code, _ = validate_input("")
        assert not is_valid, "空输入应该无效"
        assert code == 'E001', f"错误码应为 E001，实际为 {code}"
        print("  ✓ 输入校验正常")
        tests_passed += 1
    except AssertionError as e:
        print(f"  ✗ 输入校验测试异常: {e}")
        tests_failed += 1
    
    # 测试8: 错误码完整性
    print("[测试 8] 错误码完整性")
    try:
        assert len(ERROR_CODES) == 10, f"应该有10个错误码，实际有{len(ERROR_CODES)}个"
        print("  ✓ 全部 10 个错误码已定义")
        tests_passed += 1
    except AssertionError as e:
        print(f"  ✗ {e}")
        tests_failed += 1
    
    # 测试9: 超长输入
    print("[测试 9] 超长输入处理")
    try:
        long_srt = ""
        for i in range(1, 1001):
            long_srt += f"{i}\n00:00:{i//60:02d},{i%60:03d} --> 00:00:{(i+1)//60:02d},{(i+1)%60:03d}\nLine {i}\n\n"
        validator = SRTValidator()
        assert validator.validate(long_srt), "超长SRT应该通过验证"
        print("  ✓ 超长 SRT（1000 块）通过校验")
        tests_passed += 1
    except AssertionError as e:
        print(f"  ✗ {e}")
        tests_failed += 1
    
    # 测试10: 编码异常
    print("[测试 10] 编码异常处理")
    try:
        test_file = "/tmp/test_gbk.srt"
        with open(test_file, 'w', encoding='gbk') as f:
            f.write("1\n00:00:01,000 --> 00:00:03,000\n测试GBK编码")
        result = process_file(test_file)
        assert result['encoding'] == 'gbk', f"应该检测到GBK编码，实际为{result['encoding']}"
        os.remove(test_file)
        print("  ✓ GBK 编码文件正确读取")
        tests_passed += 1
    except AssertionError as e:
        print(f"  ✗ {e}")
        tests_failed += 1
    
    print("=" * 60)
    print(f"自检完成: {tests_passed} 通过, {tests_failed} 失败")
    print("=" * 60)
    
    return tests_failed == 0

def main():
    parser = argparse.ArgumentParser(description='SRT字幕文件验证器')
    parser.add_argument('file', nargs='?', help='SRT文件路径')
    parser.add_argument('--selftest', action='store_true', help='运行自检测试')
    
    args = parser.parse_args()
    
    if args.selftest:
        success = run_selftest()
        sys.exit(0 if success else 1)
    
    if not args.file:
        print("错误: 请提供SRT文件路径或使用 --selftest 运行自检")
        sys.exit(1)
    
    result = process_file(args.file)
    
    if result['success']:
        print(f"验证通过: {result['message']}")
        print(f"编码: {result['encoding']}, 字幕块数: {result['block_count']}")
        sys.exit(0)
    else:
        print(f"验证失败: {result['message']}")
        sys.exit(1)

if __name__ == '__main__':
    main()
