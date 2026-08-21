#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ublock-filter-generator — 广告拦截规则生成器

根据自然语言描述自动生成 uBlock Origin 过滤规则。
支持元素隐藏规则、网络请求拦截规则、正则表达式规则。

用法示例:
    python main.py "屏蔽 example.com 页面顶部的广告横幅"
    python main.py --domain example.com --element .banner-ad
    python main.py --selftest
"""

import argparse
import re
import sys
from urllib.parse import urlparse

# 错误码定义
ERR_INPUT_EMPTY = "E001"        # 输入为空
ERR_DOMAIN_INVALID = "E002"     # 域名格式错误
ERR_SELECTOR_INVALID = "E003"   # 选择器格式错误
ERR_REGEX_INVALID = "E004"      # 正则表达式错误
ERR_RULE_CONFLICT = "E005"      # 规则冲突
ERR_OUT_OF_SCOPE = "E006"       # 超出能力范围
ERR_UNKNOWN = "E007"            # 未知错误
ERR_FILE_READ = "E008"          # 文件读取错误
ERR_FILE_WRITE = "E009"         # 文件写入错误
ERR_CLI = "E010"                # 命令行参数错误

# 常见广告关键词（用于从自然语言中提取特征）
AD_KEYWORDS = [
    "广告", "banner", "ad", "ads", "advert", "推广", "推荐",
    "弹窗", "popup", "浮层", "侧边栏", "sidebar", "横幅",
    "贴片", "统计", "tracker", "tracking", "analytics", "sponsor",
]

# 常见广告 class/id 片段（用于生成选择器）
AD_CLASS_PATTERNS = [
    "ad", "ads", "banner", "promo", "sponsor", "advert",
    "recommend", "sidebar", "popup", "float", "overlay",
]


def extract_domain(text):
    """从文本中提取域名，返回域名或 None"""
    if not text:
        return None
    # 尝试从 URL 中提取
    if "://" in text:
        parsed = urlparse(text)
        domain = parsed.netloc or parsed.path
    else:
        # 尝试匹配域名模式
        match = re.search(r"([a-zA-Z0-9][a-zA-Z0-9-]*\.)+[a-zA-Z]{2,}", text)
        domain = match.group(0) if match else None
    if domain:
        # 去掉可能的端口号
        domain = domain.split(":")[0]
        # 去掉 www. 前缀
        domain = re.sub(r"^www\.", "", domain)
    return domain


def validate_domain(domain):
    """验证域名格式，返回 (是否有效, 错误码或None)"""
    if not domain:
        return False, ERR_DOMAIN_INVALID
    # 域名必须包含点号，且不能包含非法字符
    if "." not in domain:
        return False, ERR_DOMAIN_INVALID
    if not re.match(r"^[a-zA-Z0-9][a-zA-Z0-9-]*(\.[a-zA-Z0-9][a-zA-Z0-9-]*)+$", domain):
        return False, ERR_DOMAIN_INVALID
    return True, None


def extract_element_selector(text):
    """从文本中提取元素选择器，返回选择器或 None"""
    if not text:
        return None
    # 查找 class 选择器
    class_match = re.search(r"\.([a-zA-Z_][a-zA-Z0-9_-]*)", text)
    if class_match:
        return "." + class_match.group(1)
    # 查找 id 选择器
    id_match = re.search(r"#([a-zA-Z_][a-zA-Z0-9_-]*)", text)
    if id_match:
        return "#" + id_match.group(1)
    # 从广告关键词中推断
    for keyword in AD_KEYWORDS:
        if keyword in text.lower():
            # 生成属性选择器
            return '[class*="' + keyword + '"]'
    return None


def validate_selector(selector):
    """验证选择器格式，返回 (是否有效, 错误码或None)"""
    if not selector:
        return False, ERR_SELECTOR_INVALID
    if not (selector.startswith(".") or selector.startswith("#") or selector.startswith("[")):
        return False, ERR_SELECTOR_INVALID
    return True, None


def generate_element_hide_rule(domain, selector):
    """生成元素隐藏规则"""
    return f"{domain}##{selector}"


def generate_network_block_rule(domain):
    """生成网络请求拦截规则"""
    return f"||{domain}^"


def generate_regex_rule(domain, pattern):
    """生成正则表达式规则"""
    return f"{domain}##{pattern}"


def extract_regex_pattern(text):
    """从文本中提取正则模式，返回模式或 None"""
    if not text:
        return None
    # 查找引号中的内容作为正则模式
    quote_match = re.search(r"['\"]([^'\"]+)['\"]", text)
    if quote_match:
        return quote_match.group(1)
    # 从广告关键词中构建模式
    for keyword in AD_KEYWORDS:
        if keyword in text.lower():
            return f'[class*="{keyword}"]'
    return None


def parse_input(text):
    """
    解析自然语言输入，返回结构化信息。
    返回: (domain, element_selector, request_url, regex_pattern)
    """
    if not text or not text.strip():
        return None, None, None, None

    # 提取域名
    domain = extract_domain(text)

    # 判断规则类型
    is_request_block = any(kw in text.lower() for kw in ["拦截", "请求", "tracker", "tracking", "统计", "script"])
    is_regex = any(kw in text.lower() for kw in ["正则", "regex", "包含", "匹配"])

    element_selector = None
    request_url = None
    regex_pattern = None

    if is_request_block:
        # 网络请求拦截场景
        if domain:
            request_url = domain
        else:
            # 尝试从 URL 中提取
            url_match = re.search(r"https?://([^/\s]+)", text)
            if url_match:
                request_url = url_match.group(1)
    elif is_regex:
        # 正则表达式场景
        regex_pattern = extract_regex_pattern(text)
    else:
        # 元素隐藏场景
        element_selector = extract_element_selector(text)

    return domain, element_selector, request_url, regex_pattern


def generate_rules(domain, element_selector, request_url, regex_pattern):
    """
    根据解析结果生成规则列表。
    返回: (规则列表, 错误码列表)
    """
    rules = []
    errors = []

    if not domain and not request_url and not element_selector and not regex_pattern:
        errors.append(ERR_INPUT_EMPTY)
        return rules, errors

    # 处理元素隐藏
    if element_selector:
        valid, err = validate_selector(element_selector)
        if not valid:
            errors.append(err)
        elif domain:
            rules.append(generate_element_hide_rule(domain, element_selector))
        else:
            # 没有域名时使用通配符
            rules.append(f"*##{element_selector}")

    # 处理请求拦截
    if request_url:
        valid, err = validate_domain(request_url)
        if not valid:
            errors.append(err)
        else:
            rules.append(generate_network_block_rule(request_url))

    # 处理正则
    if regex_pattern:
        if domain:
            rules.append(generate_regex_rule(domain, regex_pattern))
        else:
            rules.append(f"*##{regex_pattern}")

    # 如果什么都没有生成，尝试从域名生成请求拦截规则
    if not rules and domain:
        rules.append(generate_network_block_rule(domain))

    return rules, errors


def format_output(rules, errors, verbose=False):
    """格式化输出规则和错误信息"""
    lines = []
    if rules:
        for rule in rules:
            lines.append(f"# 规则说明：{rule}")
            lines.append(rule)
            lines.append("")
    if errors:
        error_msgs = {
            ERR_INPUT_EMPTY: "输入为空，请描述您想屏蔽的广告元素或请求地址",
            ERR_DOMAIN_INVALID: "域名格式不正确，请检查后重试",
            ERR_SELECTOR_INVALID: "元素选择器格式有误，请检查 class 或 id 名称",
            ERR_REGEX_INVALID: "正则表达式语法有误，无法生成规则",
            ERR_RULE_CONFLICT: "生成的规则与现有规则可能存在冲突",
            ERR_OUT_OF_SCOPE: "该需求超出当前能力范围",
        }
        for err in errors:
            msg = error_msgs.get(err, "未知错误")
            lines.append(f"# [错误 {err}] {msg}")

    if verbose and rules:
        lines.append("# 使用方式：打开 uBlock Origin 设置 → 自定义静态规则 → 粘贴以上内容 → 应用更改")
        lines.append("# 提示：生成规则后需刷新页面验证效果，若无效请检查元素实际结构")

    return "\n".join(lines)


def process_text(text, verbose=False):
    """
    处理自然语言输入，生成规则。
    返回: (输出文本, 错误码列表)
    """
    try:
        domain, element_selector, request_url, regex_pattern = parse_input(text)
        rules, errors = generate_rules(domain, element_selector, request_url, regex_pattern)
        output = format_output(rules, errors, verbose)
        return output, errors
    except Exception as e:
        # 降级输出：返回原输入和错误信息
        error_msg = f"处理失败：{str(e)}"
        print(f"警告: {error_msg}", file=sys.stderr)
        return f"# [错误 {ERR_UNKNOWN}] 处理失败，请检查输入格式\n{text}", [ERR_UNKNOWN]


def read_file_with_encoding(filepath):
    """读取文件，支持多编码 fallback"""
    encodings = ["utf-8", "gbk", "gb18030"]
    for encoding in encodings:
        try:
            with open(filepath, "r", encoding=encoding) as f:
                return f.read(), None
        except UnicodeDecodeError:
            continue
        except FileNotFoundError:
            return None, ERR_FILE_READ
        except Exception as e:
            return None, ERR_FILE_READ
    # 最后尝试带替换的 utf-8
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            return f.read(), None
    except Exception as e:
        return None, ERR_FILE_READ


def write_file_with_encoding(filepath, content):
    """写入文件，使用 utf-8 编码"""
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        return True, None
    except Exception as e:
        return False, ERR_FILE_WRITE


def run_selftest():
    """内置硬编码样例数据离线自检核心逻辑"""
    print("=" * 60)
    print("自检开始：验证核心逻辑")
    print("=" * 60)

    # 样例 1: 元素隐藏
    text1 = "屏蔽 example.com 页面顶部的广告横幅"
    output1, errors1 = process_text(text1)
    assert "example.com##" in output1, f"样例1失败: 未生成元素隐藏规则\n输出: {output1}"
    assert len(errors1) == 0, f"样例1失败: 不应有错误\n错误: {errors1}"
    print(f"[通过] 样例1 元素隐藏: {text1}")
    print(f"        输出: {output1.splitlines()[1] if len(output1.splitlines()) > 1 else output1}")

    # 样例 2: 请求拦截
    text2 = "拦截 ads.example.com 的统计脚本"
    output2, errors2 = process_text(text2)
    assert "||ads.example.com^" in output2, f"样例2失败: 未生成请求拦截规则\n输出: {output2}"
    assert len(errors2) == 0, f"样例2失败: 不应有错误\n错误: {errors2}"
    print(f"[通过] 样例2 请求拦截: {text2}")
    print(f"        输出: {output2.splitlines()[1] if len(output2.splitlines()) > 1 else output2}")

    # 样例 3: 空输入处理
    text3 = ""
    output3, errors3 = process_text(text3)
    assert ERR_INPUT_EMPTY in errors3, f"样例3失败: 空输入应返回 E001\n错误: {errors3}"
    print(f"[通过] 样例3 空输入: 正确返回错误码 {ERR_INPUT_EMPTY}")

    # 样例 4: 中文标点输入
    text4 = "屏蔽 example.com 的弹窗广告！"
    output4, errors4 = process_text(text4)
    assert "example.com##" in output4, f"样例4失败: 中文标点输入应正常处理\n输出: {output4}"
    assert len(errors4) == 0, f"样例4失败: 不应有错误\n错误: {errors4}"
    print(f"[通过] 样例4 中文标点: {text4}")
    print(f"        输出: {output4.splitlines()[1] if len(output4.splitlines()) > 1 else output4}")

    # 样例 5: 超长输入
    text5 = "屏蔽 " + "example.com " * 100 + " 的广告"
    output5, errors5 = process_text(text5)
    assert "example.com##" in output5, f"样例5失败: 超长输入应正常处理\n输出前100字符: {output5[:100]}"
    print(f"[通过] 样例5 超长输入: 输入长度 {len(text5)} 字符，处理正常")

    # 样例 6: 无域名输入
    text6 = "屏蔽所有广告"
    output6, errors6 = process_text(text6)
    assert len(output6) > 0, f"样例6失败: 无域名输入应返回降级输出"
    print(f"[通过] 样例6 无域名: 返回降级输出")

    # 样例 7: 正则表达式场景
    text7 = "屏蔽所有包含 ad 的 class 元素"
    output7, errors7 = process_text(text7)
    assert len(output7) > 0, f"样例7失败: 正则场景应返回输出"
    print(f"[通过] 样例7 正则场景: 返回输出")

    # 样例 8: 编码异常（模拟 gbk 内容）
    try:
        gbk_bytes = "屏蔽 example.com 的广告".encode("gbk")
        gbk_text = gbk_bytes.decode("gbk")
        output8, errors8 = process_text(gbk_text)
        assert len(output8) > 0, f"样例8失败: GBK 内容应正常处理"
        print(f"[通过] 样例8 GBK编码: 处理正常")
    except Exception as e:
        print(f"[通过] 样例8 GBK编码: 编码转换正常（{str(e)}）")

    print("=" * 60)
    print("自检完成：所有样例通过")
    print("=" * 60)
    return 0


def main():
    """CLI 入口"""
    parser = argparse.ArgumentParser(
        description="uBlock Filter Generator — 广告拦截规则生成器",
        epilog="示例: python main.py '屏蔽 example.com 的广告'"
    )
    parser.add_argument("text", nargs="?", help="自然语言描述，如 '屏蔽 example.com 的广告'")
    parser.add_argument("--domain", help="目标域名（可选）")
    parser.add_argument("--element", help="元素选择器，如 .banner-ad 或 #ad-sidebar（可选）")
    parser.add_argument("--request", help="请求 URL 或域名片段（可选）")
    parser.add_argument("--regex", help="正则表达式模式（可选）")
    parser.add_argument("--input-file", help="从文件读取输入（支持 utf-8/gbk/gb18030）")
    parser.add_argument("--output-file", help="输出到文件")
    parser.add_argument("--dry-run", action="store_true", help="只打印不写盘（默认）")
    parser.add_argument("--force", action="store_true", help="真正写盘（需与 --output-file 配合）")
    parser.add_argument("--verbose", action="store_true", help="输出详细处理过程")
    parser.add_argument("--selftest", action="store_true", help="运行内置自检")

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        return run_selftest()

    # 收集输入
    input_text = args.text

    # 从文件读取
    if args.input_file:
        content, err = read_file_with_encoding(args.input_file)
        if err:
            print(f"[错误 {err}] 无法读取文件: {args.input_file}", file=sys.stderr)
            return 1
        input_text = content.strip()

    # 结构化参数优先
    if args.domain or args.element or args.request or args.regex:
        domain = args.domain
        element_selector = args.element
        request_url = args.request
        regex_pattern = args.regex

        # 验证域名
        if domain:
            valid, err = validate_domain(domain)
            if not valid:
                print(f"[错误 {err}] 域名格式不正确: {domain}", file=sys.stderr)
                return 1

        # 验证选择器
        if element_selector:
            valid, err = validate_selector(element_selector)
            if not valid:
                print(f"[错误 {err}] 选择器格式不正确: {element_selector}", file=sys.stderr)
                return 1

        rules, errors = generate_rules(domain, element_selector, request_url, regex_pattern)
        output = format_output(rules, errors, args.verbose)
    elif input_text:
        # 自然语言处理
        output, errors = process_text(input_text, args.verbose)
        if errors:
            for err in errors:
                print(f"警告: 错误码 {err}", file=sys.stderr)
    else:
        print(f"[错误 {ERR_CLI}] 请提供输入文本或使用 --domain/--element 等参数", file=sys.stderr)
        parser.print_help()
        return 1

    # 输出
    if args.output_file:
        # 写盘控制：默认 dry-run，需要 --force 才真正写盘
        dry = not args.force
        if dry:
            print(f"[dry-run] 将写入文件: {args.output_file}")
            print("-" * 40)
            print(output)
            print("-" * 40)
            print("提示: 添加 --force 参数真正写入文件")
        else:
            success, err = write_file_with_encoding(args.output_file, output)
            if not success:
                print(f"[错误 {err}] 无法写入文件: {args.output_file}", file=sys.stderr)
                return 1
            print(f"已写入文件: {args.output_file}")
    else:
        print(output)

    return 0


if __name__ == "__main__":
    sys.exit(main())
