#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
uBlock Filter Generator — 广告拦截规则生成器

根据自然语言描述自动生成uBlock Origin过滤规则，支持元素隐藏、网络请求拦截与正则表达式规则。
"""

import argparse
import os
import re
import sys
import tempfile
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Tuple
dry_run = False  # v3.274 模块级 dry-run 标志

# 版本信息
VERSION = "3.0.0"

# 错误码定义
ERROR_CODES = {
    "E001": "域名缺失",
    "E002": "选择器无效",
    "E003": "规则类型冲突",
    "E004": "正则语法错误",
    "E005": "超出能力范围",
    "E006": "信息矛盾",
}


class FilterGeneratorError(Exception):
    """过滤器生成器异常基类"""

    def __init__(self, error_code: str, message: str):
        self.error_code = error_code
        self.message = message
        super().__init__(f"{error_code}: {message}")


def validate_domain(domain: str) -> bool:
    """
    验证域名格式是否合法。

    Args:
        domain: 待验证的域名

    Returns:
        域名是否合法
    """
    if not domain or not isinstance(domain, str):
        return False
    # 域名格式：字母数字和连字符，至少一个点，或 localhost
    pattern = r"^(localhost|[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?)+)$"
    return bool(re.match(pattern, domain))


def validate_selector(selector: str) -> bool:
    """
    验证CSS选择器格式是否合法。

    Args:
        selector: 待验证的选择器

    Returns:
        选择器是否合法
    """
    if not selector or not isinstance(selector, str):
        return False
    # 选择器基本格式：.class、#id、tag、[attr]、tag[attr]
    # 支持中文、字母、数字、常见CSS选择器字符
    # 不允许空格（除非在引号内）
    # 放宽规则：允许单引号，允许空格在引号内
    pattern = r"^[a-zA-Z0-9#\.\[\]\*=\"\^\$\|\~:_\-\u4e00-\u9fff' ]+$"
    if not re.match(pattern, selector):
        return False
    # 检查引号是否配对
    if selector.count("'") % 2 != 0:
        return False
    if selector.count('"') % 2 != 0:
        return False
    # 检查空格是否在引号内
    if " " in selector:
        # 去掉引号内的空格
        no_quotes = re.sub(r"'[^']*'|\"[^\"]*\"", "", selector)
        if " " in no_quotes:
            return False
    return True


def validate_regex(pattern: str) -> bool:
    """
    验证正则表达式是否合法。

    Args:
        pattern: 待验证的正则表达式

    Returns:
        正则表达式是否合法
    """
    if not pattern or not isinstance(pattern, str):
        return False
    try:
        re.compile(pattern)
        return True
    except re.error:
        return False


def generate_hide_rule(domain: str, selector: str) -> str:
    """
    生成元素隐藏规则。

    Args:
        domain: 目标域名
        selector: CSS选择器

    Returns:
        生成的过滤规则

    Raises:
        FilterGeneratorError: 当域名或选择器无效时
    """
    if not validate_domain(domain):
        raise FilterGeneratorError("E001", "域名缺失或格式无效")
    if not validate_selector(selector):
        raise FilterGeneratorError("E002", "选择器无效")

    return f"{domain}##{selector}"


def generate_network_rule(domain: str, url: str) -> str:
    """
    生成网络请求拦截规则。

    Args:
        domain: 目标域名
        url: 请求地址

    Returns:
        生成的过滤规则

    Raises:
        FilterGeneratorError: 当域名或URL无效时
    """
    if not validate_domain(domain):
        raise FilterGeneratorError("E001", "域名缺失或格式无效")
    if not url or not isinstance(url, str):
        raise FilterGeneratorError("E006", "URL无效")

    # 从URL中提取主机名
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        hostname = parsed.hostname or ""
    except Exception:
        hostname = url

    # 如果URL包含协议，提取主机名
    if "://" in url:
        hostname = url.split("://")[1].split("/")[0]
    else:
        hostname = url.split("/")[0]

    # 移除端口号
    if ":" in hostname:
        hostname = hostname.split(":")[0]

    return f"||{hostname}^"


def generate_regex_rule(domain: str, pattern: str) -> str:
    """
    生成正则表达式规则。

    Args:
        domain: 目标域名
        pattern: 正则表达式模式

    Returns:
        生成的过滤规则

    Raises:
        FilterGeneratorError: 当域名或正则表达式无效时
    """
    if not validate_domain(domain):
        raise FilterGeneratorError("E001", "域名缺失或格式无效")
    if not validate_regex(pattern):
        raise FilterGeneratorError("E004", "正则语法错误")

    return f"{domain}##{pattern}"


def process_line(line: str, verbose: bool = False) -> Optional[str]:
    """
    处理单行输入，生成过滤规则。

    Args:
        line: 输入行
        verbose: 是否输出详细日志

    Returns:
        生成的规则，如果无法处理则返回None
    """
    line = line.strip()
    if not line or line.startswith("#"):
        return None

    # 支持格式：
    # 1. domain##selector (元素隐藏)
    # 2. ||domain^ (网络请求拦截)
    # 3. domain##[attr*="value"] (属性选择器)
    # 4. domain##/regex/ (正则表达式)

    try:
        # 检查是否已包含规则语法
        if "##" in line:
            parts = line.split("##", 1)
            domain = parts[0].strip()
            selector = parts[1].strip()
            if not validate_domain(domain):
                if verbose:
                    print(f"  [警告] 域名无效: {domain}", file=sys.stderr)
                return None
            if not validate_selector(selector):
                if verbose:
                    print(f"  [警告] 选择器无效: {selector}", file=sys.stderr)
                return None
            return line

        if line.startswith("||") and line.endswith("^"):
            domain = line[2:-1]
            if not validate_domain(domain):
                if verbose:
                    print(f"  [警告] 域名无效: {domain}", file=sys.stderr)
                return None
            return line

        # 尝试解析为 domain + selector 或 domain + url
        parts = line.split()
        if len(parts) >= 2:
            domain = parts[0]
            target = parts[1]

            if not validate_domain(domain):
                if verbose:
                    print(f"  [警告] 域名无效: {domain}", file=sys.stderr)
                return None

            # 判断是选择器还是URL
            if target.startswith("http://") or target.startswith("https://"):
                return generate_network_rule(domain, target)
            elif target.startswith(".") or target.startswith("#") or target.startswith("["):
                return generate_hide_rule(domain, target)
            elif target.startswith("/") and target.endswith("/"):
                pattern = target[1:-1]
                return generate_regex_rule(domain, pattern)
            else:
                if verbose:
                    print(f"  [警告] 无法识别的目标: {target}", file=sys.stderr)
                return None

        return None

    except FilterGeneratorError as e:
        if verbose:
            print(f"  [错误] {e.error_code}: {e.message}", file=sys.stderr)
        return None
    except Exception as e:
        if verbose:
            print(f"  [错误] 处理行时发生异常: {e}", file=sys.stderr)
        return None


def process_file(input_path: str, output_path: Optional[str] = None, dry_run: bool = False, verbose: bool = False) -> int:
    """
    处理输入文件，生成过滤规则。

    Args:
        input_path: 输入文件路径
        output_path: 输出文件路径（可选）
        dry_run: 是否只预览不写盘
        verbose: 是否输出详细日志

    Returns:
        成功处理的规则数量
    """
    try:
        input_file = Path(input_path)
        if not input_file.exists():
            print(f"错误: 输入文件不存在: {input_path}", file=sys.stderr)
            return 0

        # 读取输入文件（支持多编码）
        content = None
        encodings = ["utf-8", "gbk", "gb18030", "latin-1"]
        for encoding in encodings:
            try:
                content = input_file.read_text(encoding=encoding)
                if verbose:
                    print(f"  使用编码: {encoding}", file=sys.stderr)
                break
            except UnicodeDecodeError:
                continue
            except Exception as e:
                if verbose:
                    print(f"  读取文件失败 ({encoding}): {e}", file=sys.stderr)
                continue

        if content is None:
            print(f"错误: 无法读取输入文件: {input_path}", file=sys.stderr)
            return 0

        # 处理每一行
        rules = []
        for line in content.splitlines():
            rule = process_line(line, verbose)
            if rule:
                rules.append(rule)

        if verbose:
            print(f"  共处理 {len(rules)} 条规则", file=sys.stderr)

        # 输出结果
        if dry_run:
            # 预览模式，不写盘
            print("=== 预览模式（不写入文件）===")
            for rule in rules:
                print(rule)
            print(f"=== 共 {len(rules)} 条规则 ===")
        elif output_path:
            # 写入输出文件（原子写入）
            output_file = Path(output_path)
            temp_path = output_file.with_suffix(output_file.suffix + ".tmp")
            try:
                if not dry_run:
                    temp_path.write_text("\n".join(rules) + "\n", encoding="utf-8")
                # 原子替换
                temp_path.replace(output_file)
                if verbose:
                    print(f"  已写入 {len(rules)} 条规则到 {output_path}", file=sys.stderr)
            except Exception as e:
                print(f"错误: 写入文件失败: {e}", file=sys.stderr)
                # 清理临时文件
                if temp_path.exists():
                    temp_path.unlink()
                return 0
        else:
            # 输出到标准输出
            for rule in rules:
                print(rule)

        return len(rules)

    except Exception as e:
        print(f"错误: 处理文件时发生异常: {e}", file=sys.stderr)
        return 0


def run_selftest() -> int:
    """
    运行自检测试，验证核心功能。

    Returns:
        测试通过返回0，失败返回1
    """
    print("=== uBlock Filter Generator 自检测试 ===")
    failures = 0

    # 测试1: 元素隐藏规则生成
    print("\n[测试1] 元素隐藏规则生成")
    try:
        rule = generate_hide_rule("example.com", ".ad-banner")
        expected = "example.com##.ad-banner"
        if rule == expected:
            print(f"  ✓ 通过: {rule}")
        else:
            print(f"  ✗ 失败: 期望 {expected}, 实际 {rule}")
            failures += 1
    except FilterGeneratorError as e:
        print(f"  ✗ 失败: {e.error_code}: {e.message}")
        failures += 1

    # 测试2: 网络请求拦截规则生成
    print("\n[测试2] 网络请求拦截规则生成")
    try:
        rule = generate_network_rule("example.com", "https://tracker.example.com/t.js")
        expected = "||tracker.example.com^"
        if rule == expected:
            print(f"  ✓ 通过: {rule}")
        else:
            print(f"  ✗ 失败: 期望 {expected}, 实际 {rule}")
            failures += 1
    except FilterGeneratorError as e:
        print(f"  ✗ 失败: {e.error_code}: {e.message}")
        failures += 1

    # 测试3: 正则表达式规则生成
    print("\n[测试3] 正则表达式规则生成")
    try:
        rule = generate_regex_rule("example.com", "ad.*banner")
        expected = "example.com##ad.*banner"
        if rule == expected:
            print(f"  ✓ 通过: {rule}")
        else:
            print(f"  ✗ 失败: 期望 {expected}, 实际 {rule}")
            failures += 1
    except FilterGeneratorError as e:
        print(f"  ✗ 失败: {e.error_code}: {e.message}")
        failures += 1

    # 测试4: 域名验证
    print("\n[测试4] 域名验证")
    valid_domains = ["example.com", "sub.example.co.uk", "localhost"]
    invalid_domains = ["", "not_a_domain", "example", "example..com"]

    for domain in valid_domains:
        if validate_domain(domain):
            print(f"  ✓ 通过: {domain} 是有效域名")
        else:
            print(f"  ✗ 失败: {domain} 应被识别为有效域名")
            failures += 1

    for domain in invalid_domains:
        if not validate_domain(domain):
            print(f"  ✓ 通过: {domain} 是无效域名")
        else:
            print(f"  ✗ 失败: {domain} 应被识别为无效域名")
            failures += 1

    # 测试5: 选择器验证
    print("\n[测试5] 选择器验证")
    valid_selectors = [".ad-banner", "#header", "[class*='ad']", "div.ad"]
    invalid_selectors = ["", "invalid selector with spaces", "ad;banner"]

    for selector in valid_selectors:
        if validate_selector(selector):
            print(f"  ✓ 通过: {selector} 是有效选择器")
        else:
            print(f"  ✗ 失败: {selector} 应被识别为有效选择器")
            failures += 1

    for selector in invalid_selectors:
        if not validate_selector(selector):
            print(f"  ✓ 通过: {selector} 是无效选择器")
        else:
            print(f"  ✗ 失败: {selector} 应被识别为无效选择器")
            failures += 1

    # 测试6: 正则验证
    print("\n[测试6] 正则验证")
    valid_patterns = ["ad.*banner", "^ad", "ad[0-9]+"]
    invalid_patterns = ["[", "("]

    for pattern in valid_patterns:
        if validate_regex(pattern):
            print(f"  ✓ 通过: {pattern} 是有效正则")
        else:
            print(f"  ✗ 失败: {pattern} 应被识别为有效正则")
            failures += 1

    for pattern in invalid_patterns:
        if not validate_regex(pattern):
            print(f"  ✓ 通过: {pattern} 是无效正则")
        else:
            print(f"  ✗ 失败: {pattern} 应被识别为无效正则")
            failures += 1

    # 测试7: 单行处理
    print("\n[测试7] 单行处理")
    test_cases = [
        ("example.com##.ad-banner", "example.com##.ad-banner"),
        ("||tracker.example.com^", "||tracker.example.com^"),
        ("example.com .ad-banner", "example.com##.ad-banner"),
        ("example.com https://ads.example.com/t.js", "||ads.example.com^"),
        ("# 注释行", None),
        ("", None),
    ]

    for input_line, expected in test_cases:
        result = process_line(input_line, verbose=False)
        if expected is None:
            if result is None:
                print(f"  ✓ 通过: '{input_line}' -> None")
            else:
                print(f"  ✗ 失败: '{input_line}' 应返回 None, 实际 {result}")
                failures += 1
        else:
            if result == expected:
                print(f"  ✓ 通过: '{input_line}' -> {result}")
            else:
                print(f"  ✗ 失败: '{input_line}' 期望 {expected}, 实际 {result}")
                failures += 1

    # 测试8: 批量处理
    print("\n[测试8] 批量处理")
    test_input = """example.com##.ad-banner
||tracker.example.com^
example.com .ad-sidebar
example.com https://ads.example.com/t.js
# 注释行

example.com##[class*="ad"]
"""
    test_file = Path(tempfile.gettempdir()) / "ublock_test_input.txt"
    if not dry_run:
        test_file.write_text(test_input, encoding="utf-8")

    count = process_file(str(test_file), dry_run=True, verbose=False)
    if count == 5:
        print(f"  ✓ 通过: 处理了 {count} 条规则")
    else:
        print(f"  ✗ 失败: 期望 5 条规则, 实际 {count}")
        failures += 1

    # 清理测试文件
    test_file.unlink(missing_ok=True)

    # 测试9: 错误处理
    print("\n[测试9] 错误处理")
    try:
        generate_hide_rule("", ".ad-banner")
        print("  ✗ 失败: 空域名应抛出异常")
        failures += 1
    except FilterGeneratorError as e:
        if e.error_code == "E001":
            print(f"  ✓ 通过: 空域名抛出 E001")
        else:
            print(f"  ✗ 失败: 错误码应为 E001, 实际 {e.error_code}")
            failures += 1

    try:
        generate_hide_rule("example.com", "")
        print("  ✗ 失败: 空选择器应抛出异常")
        failures += 1
    except FilterGeneratorError as e:
        if e.error_code == "E002":
            print(f"  ✓ 通过: 空选择器抛出 E002")
        else:
            print(f"  ✗ 失败: 错误码应为 E002, 实际 {e.error_code}")
            failures += 1

    try:
        generate_regex_rule("example.com", "[")
        print("  ✗ 失败: 无效正则应抛出异常")
        failures += 1
    except FilterGeneratorError as e:
        if e.error_code == "E004":
            print(f"  ✓ 通过: 无效正则抛出 E004")
        else:
            print(f"  ✗ 失败: 错误码应为 E004, 实际 {e.error_code}")
            failures += 1

    # 测试10: 文件处理（写入模式）
    print("\n[测试10] 文件处理（写入模式）")
    test_output = Path(tempfile.gettempdir()) / "ublock_test_output.txt"
    test_input_file = Path(tempfile.gettempdir()) / "ublock_test_input2.txt"
    if not dry_run:
        test_input_file.write_text("example.com##.ad-banner\n||tracker.example.com^\n", encoding="utf-8")

    count = process_file(str(test_input_file), str(test_output), dry_run=False, verbose=False)
    if count == 2 and test_output.exists():
        content = test_output.read_text(encoding="utf-8")
        if "example.com##.ad-banner" in content and "||tracker.example.com^" in content:
            print(f"  ✓ 通过: 文件写入成功，包含 {count} 条规则")
        else:
            print(f"  ✗ 失败: 文件内容不正确")
            failures += 1
    else:
        print(f"  ✗ 失败: 文件写入失败，count={count}")
        failures += 1

    # 清理测试文件
    test_output.unlink(missing_ok=True)
    test_input_file.unlink(missing_ok=True)

    # 测试11: 原子写入
    print("\n[测试11] 原子写入")
    test_atomic = Path(tempfile.gettempdir()) / "ublock_test_atomic.txt"
    test_atomic.write_text("old content", encoding="utf-8")
    test_input_atomic = Path(tempfile.gettempdir()) / "ublock_test_input3.txt"
    test_input_atomic.write_text("example.com##.ad-banner\n", encoding="utf-8")

    count = process_file(str(test_input_atomic), str(test_atomic), dry_run=False, verbose=False)
    if count == 1 and test_atomic.exists():
        content = test_atomic.read_text(encoding="utf-8")
        if "example.com##.ad-banner" in content:
            print(f"  ✓ 通过: 原子写入成功")
        else:
            print(f"  ✗ 失败: 文件内容不正确")
            failures += 1
    else:
        print(f"  ✗ 失败: 原子写入失败")
        failures += 1

    # 清理测试文件
    test_atomic.unlink(missing_ok=True)
    test_input_atomic.unlink(missing_ok=True)

    # 测试12: 多编码支持
    print("\n[测试12] 多编码支持")
    test_gbk = Path(tempfile.gettempdir()) / "ublock_test_gbk.txt"
    # 写入GBK编码的中文注释
    gbk_content = "# 中文注释\n example.com##.ad-banner\n".encode("gbk")
    test_gbk.write_bytes(gbk_content)

    count = process_file(str(test_gbk), dry_run=True, verbose=False)
    if count == 1:
        print(f"  ✓ 通过: GBK编码文件处理成功")
    else:
        print(f"  ✗ 失败: GBK编码文件处理失败，count={count}")
        failures += 1

    test_gbk.unlink(missing_ok=True)

    # 总结
    print(f"\n=== 自检测试完成: {'全部通过' if failures == 0 else f'{failures} 项失败'} ===")
    return 0 if failures == 0 else 1


def main():
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description="uBlock Filter Generator - 广告拦截规则生成器",
        epilog="示例: python run.py --domain example.com --selector .ad-banner"
    )

    # 输入参数
    parser.add_argument("--domain", help="目标域名，如 example.com")
    parser.add_argument("--selector", help="CSS选择器，如 .ad-banner 或 #header")
    parser.add_argument("--url", help="网络请求URL，如 https://tracker.example.com/t.js")
    parser.add_argument("--type", choices=["hide", "network", "regex"], default="hide",
                        help="规则类型: hide(元素隐藏), network(网络拦截), regex(正则表达式)")
    parser.add_argument("--pattern", help="正则表达式模式（当 --type regex 时使用）")

    # 文件处理参数
    parser.add_argument("--input", help="输入文件路径（批量处理）")
    parser.add_argument("--output", help="输出文件路径（批量处理）")

    # 其他参数
    parser.add_argument("--dry-run", action="store_true", help="预览模式，不写入文件")
    parser.add_argument("--verbose", action="store_true", help="输出详细日志")
    parser.add_argument("--selftest", action="store_true", help="运行自检测试")
    parser.add_argument("--version", action="version", version=f"%(prog)s {VERSION}")

    args = parser.parse_args()

    global dry_run

    dry_run = getattr(args, "dry_run", False)  # v3.274 同步到全局

    # 自检测试模式
    if args.selftest:
        sys.exit(run_selftest())

    # 批量处理模式
    if args.input:
        count = process_file(args.input, args.output, args.dry_run, args.verbose)
        if count == 0:
            print("错误: 未生成任何规则", file=sys.stderr)
            sys.exit(1)
        sys.exit(0)

    # 单条规则生成模式
    try:
        if args.type == "hide":
            if not args.domain or not args.selector:
                print("错误: 元素隐藏规则需要 --domain 和 --selector 参数", file=sys.stderr)
                sys.exit(1)
            rule = generate_hide_rule(args.domain, args.selector)
            if args.verbose:
                print(f"生成元素隐藏规则:", file=sys.stderr)
                print(f"  域名: {args.domain}", file=sys.stderr)
                print(f"  选择器: {args.selector}", file=sys.stderr)
            print(rule)

        elif args.type == "network":
            if not args.domain or not args.url:
                print("错误: 网络拦截规则需要 --domain 和 --url 参数", file=sys.stderr)
                sys.exit(1)
            rule = generate_network_rule(args.domain, args.url)
            if args.verbose:
                print(f"生成网络拦截规则:", file=sys.stderr)
                print(f"  域名: {args.domain}", file=sys.stderr)
                print(f"  URL: {args.url}", file=sys.stderr)
            print(rule)

        elif args.type == "regex":
            if not args.domain:
                print("错误: 正则规则需要 --domain 参数", file=sys.stderr)
                sys.exit(1)
            pattern = args.pattern or args.selector
            if not pattern:
                print("错误: 正则规则需要 --pattern 或 --selector 参数", file=sys.stderr)
                sys.exit(1)
            rule = generate_regex_rule(args.domain, pattern)
            if args.verbose:
                print(f"生成正则规则:", file=sys.stderr)
                print(f"  域名: {args.domain}", file=sys.stderr)
                print(f"  模式: {pattern}", file=sys.stderr)
            print(rule)

    except FilterGeneratorError as e:
        print(f"错误: {e.error_code}: {e.message}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"错误: 发生未预期异常: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
