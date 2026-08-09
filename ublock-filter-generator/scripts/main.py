#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import re
import sys
import json
import argparse
from urllib.parse import urlparse

def parse_rule(text):
    """
    解析规则文本，生成规则字典。
    支持格式：
    - 正则规则: /pattern/action
    - 中文描述: 提取[选择器]从[域名]
    - 网络拦截: 拦截[域名]的[选择器]
    """
    if not text or not text.strip():
        return {'success': False, 'error': 'EMPTY_INPUT', 'error_code': 400}
    
    text = text.strip()
    
    # 正则规则格式: /pattern/action
    regex_match = re.match(r'^/(.+)/(\w+)$', text)
    if regex_match:
        pattern = regex_match.group(1)
        action = regex_match.group(2)
        return {
            'success': True,
            'rule': {
                'pattern': pattern,
                'action': action,
                'type': 'regex'
            }
        }
    
    # 中文描述格式
    # 提取[选择器]从[域名] 或 拦截[域名]的[选择器]
    extract_match = re.match(r'^提取\[(.+?)\]从\[(.+?)\]$', text)
    if extract_match:
        selector = extract_match.group(1)
        domain = extract_match.group(2)
        if not domain:
            return {'success': False, 'error': 'EMPTY_DOMAIN', 'error_code': 400}
        if not selector:
            return {'success': False, 'error': 'EMPTY_SELECTOR', 'error_code': 400}
        return {
            'success': True,
            'rule': {
                'domain': domain,
                'selector': selector,
                'type': 'css',
                'action': 'extract'
            }
        }
    
    intercept_match = re.match(r'^拦截\[(.+?)\]的\[(.+?)\]$', text)
    if intercept_match:
        domain = intercept_match.group(1)
        selector = intercept_match.group(2)
        if not domain:
            return {'success': False, 'error': 'EMPTY_DOMAIN', 'error_code': 400}
        if not selector:
            return {'success': False, 'error': 'EMPTY_SELECTOR', 'error_code': 400}
        return {
            'success': True,
            'rule': {
                'domain': domain,
                'selector': selector,
                'type': 'css',
                'action': 'intercept'
            }
        }
    
    # 网络拦截格式: 拦截 域名 选择器
    net_match = re.match(r'^拦截\s+(\S+)\s+(\S+)$', text)
    if net_match:
        domain = net_match.group(1)
        selector = net_match.group(2)
        if not domain:
            return {'success': False, 'error': 'EMPTY_DOMAIN', 'error_code': 400}
        if not selector:
            return {'success': False, 'error': 'EMPTY_SELECTOR', 'error_code': 400}
        return {
            'success': True,
            'rule': {
                'domain': domain,
                'selector': selector,
                'type': 'css',
                'action': 'intercept'
            }
        }
    
    return {'success': False, 'error': 'INVALID_FORMAT', 'error_code': 422}

def selftest():
    """自检函数，验证核心功能"""
    tests = [
        # (输入, 期望成功, 期望错误码或None)
        ("/test/.*/extract", True, None),
        ("提取[.title]从[example.com]", True, None),
        ("拦截 example.com .ad-banner", True, None),
        ("", False, "EMPTY_INPUT"),
        ("提取[.content]从[]", False, "EMPTY_DOMAIN"),
        ("提取[]从[example.com]", False, "EMPTY_SELECTOR"),
        ("拦截[example.com]的[.ad]", True, None),
        ("提取【.title】从【example.com】", False, "INVALID_FORMAT"),
        ("拦截 example.com .ad-banner " * 10, True, None),
        ("提取[.content]从[example.com]", True, None),
        ("测试中文编码", False, "INVALID_FORMAT"),
    ]
    
    passed = 0
    failed = 0
    
    for test_input, expected_success, expected_error in tests:
        result = parse_rule(test_input)
        if expected_success:
            if result.get('success'):
                passed += 1
                print(f"[PASS] {test_input[:30]}")
            else:
                failed += 1
                print(f"[FAIL] {test_input[:30]}: 期望成功，但得到 {result}")
        else:
            if not result.get('success') and result.get('error') == expected_error:
                passed += 1
                print(f"[PASS] {test_input[:30]}")
            else:
                failed += 1
                print(f"[FAIL] {test_input[:30]}: 期望失败，但得到 {result}")
    
    print(f"\n=== 自检结果: {passed} 通过, {failed} 失败 ===")
    return failed == 0

def main():
    parser = argparse.ArgumentParser(description='规则解析器')
    parser.add_argument('--selftest', action='store_true', help='运行自检')
    parser.add_argument('--input', type=str, help='输入规则文本')
    args = parser.parse_args()
    
    if args.selftest:
        success = selftest()
        sys.exit(0 if success else 1)
    
    if args.input:
        result = parse_rule(args.input)
        print(json.dumps(result, ensure_ascii=False))
    else:
        # 交互模式
        for line in sys.stdin:
            line = line.strip()
            if not line:
                break
            result = parse_rule(line)
            print(json.dumps(result, ensure_ascii=False))

if __name__ == '__main__':
    main()
