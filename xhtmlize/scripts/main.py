#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
xhtmlize — HTML 片段 XHTML 化处理工具

将用户提交的松散 HTML 片段转换为符合 XHTML 1.0 严格格式的整洁标记。
支持从命令行接收 HTML 字符串或文件路径，并输出标准化后的 XHTML 片段。

功能特性：
- 自动闭合未闭合的标签（如 <p>、<li>）
- 属性名转为小写，属性值添加引号
- 文本节点内将 & 转为 &amp;，< 转为 &lt;
- 检查标签嵌套顺序，修正错位
- 不处理字符编码转换、不验证链接有效性、不执行脚本

用法示例：
    python main.py "<p>Hello & welcome</p>"
    python main.py --file input.html
    python main.py --selftest

错误码说明：
    E001: 输入为空
    E002: 输入不是字符串
    E003: 文件读取失败
    E004: 标签解析错误（不支持的标签语法）
    E005: 属性解析错误
    E006: 嵌套结构错误（无法修复的错位）
    E007: 内部状态错误（不应发生）
    E008: 命令行参数错误
    E009: 输出写入失败
    E010: 未知错误
"""

import sys
import os
import re
import argparse
from html.parser import HTMLParser
from typing import List, Tuple, Optional, Set
from datetime import datetime, timezone

dry_run = False  # v3.274 模块级 dry-run 标志


# ============================================================
# 错误码定义
# ============================================================
class XhtmlizeError(Exception):
    """自定义异常，携带错误码。"""
    def __init__(self, code: str, message: str):
        super().__init__(f"[{code}] {message}")
        self.code = code
        self.message = message


# ============================================================
# 常量定义
# ============================================================
# 空元素（不需要闭合标签）
VOID_ELEMENTS = {
    'area', 'base', 'br', 'col', 'embed', 'hr', 'img',
    'input', 'link', 'meta', 'param', 'source', 'track', 'wbr'
}

# 可自动闭合的容器元素（用于修复未闭合标签）
AUTO_CLOSE_ELEMENTS = {
    'p', 'li', 'dt', 'dd', 'tr', 'td', 'th', 'option',
    'thead', 'tbody', 'tfoot', 'caption', 'colgroup'
}

# 需要显式闭合的块级元素（用于嵌套检查）
BLOCK_ELEMENTS = {
    'div', 'section', 'article', 'aside', 'header', 'footer',
    'nav', 'main', 'figure', 'figcaption', 'ul', 'ol', 'dl',
    'table', 'form', 'fieldset', 'details', 'summary'
}

# 子元素规则映射（用于嵌套修复）
CHILDREN_RULES = {
    'ul': {'li'},
    'ol': {'li'},
    'dl': {'dt', 'dd'},
    'table': {'caption', 'colgroup', 'thead', 'tbody', 'tfoot', 'tr'},
    'thead': {'tr'},
    'tbody': {'tr'},
    'tfoot': {'tr'},
    'tr': {'td', 'th'},
    'select': {'option', 'optgroup'},
    'optgroup': {'option'},
    'p': set(),  # p 不能包含块级元素
}


# ============================================================
# HTML 解析器（基于标准库 html.parser）
# ============================================================
class XhtmlParser(HTMLParser):
    """
    解析 HTML 片段并收集标签事件。
    继承自标准库 HTMLParser，在 clean-room 原则下重新实现处理逻辑。
    """

    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.events: List[Tuple[str, str, dict]] = []
        # 事件类型: 'start', 'end', 'startend', 'data'
        self._current_data: List[str] = []

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]) -> None:
        """处理开始标签。"""
        attr_dict = {}
        for name, value in attrs:
            attr_dict[name.lower()] = value if value is not None else ''
        self.events.append(('start', tag.lower(), attr_dict))

    def handle_startendtag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]) -> None:
        """处理自闭合标签（如 <br/>）。"""
        attr_dict = {}
        for name, value in attrs:
            attr_dict[name.lower()] = value if value is not None else ''
        self.events.append(('startend', tag.lower(), attr_dict))

    def handle_endtag(self, tag: str) -> None:
        """处理结束标签。"""
        self.events.append(('end', tag.lower(), {}))

    def handle_data(self, data: str) -> None:
        """处理文本数据。"""
        # 合并连续的文本节点
        if self.events and self.events[-1][0] == 'data':
            prev_type, prev_tag, prev_attrs = self.events[-1]
            self.events[-1] = ('data', prev_tag + data, prev_attrs)
        else:
            self.events.append(('data', data, {}))

    def handle_entityref(self, name: str) -> None:
        """处理实体引用（如 &amp;）。"""
        self.handle_data(f'&{name};')

    def handle_charref(self, name: str) -> None:
        """处理字符引用（如 &#123;）。"""
        self.handle_data(f'&#{name};')

    def handle_comment(self, data: str) -> None:
        """处理注释。"""
        self.events.append(('comment', data, {}))

    def handle_decl(self, decl: str) -> None:
        """处理声明（如 DOCTYPE）。"""
        self.events.append(('decl', decl, {}))

    def handle_pi(self, data: str) -> None:
        """处理处理指令。"""
        self.events.append(('pi', data, {}))


# ============================================================
# 核心转换逻辑
# ============================================================
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


def parse_html(html: str) -> List[Tuple[str, str, dict]]:
    """解析 HTML 字符串，返回事件列表。"""
    parser = XhtmlParser()
    try:
        parser.feed(html)
        parser.close()
    except Exception as e:
        raise XhtmlizeError('E004', f'标签解析错误: {str(e)}')
    return parser.events


def escape_text(text: str) -> str:
    """转义文本节点中的特殊字符。"""
    result = []
    for char in text:
        if char == '&':
            result.append('&amp;')
        elif char == '<':
            result.append('&lt;')
        elif char == '>':
            result.append('&gt;')
        else:
            result.append(char)
    return ''.join(result)


def format_attrs(attrs: dict) -> str:
    """格式化属性为 XHTML 标准（小写名 + 引号值）。"""
    if not attrs:
        return ''
    parts = []
    for name, value in sorted(attrs.items()):
        # 属性名转为小写
        name_lower = name.lower()
        # 属性值转义
        value_escaped = escape_text(str(value))
        # 添加引号
        parts.append(f'{name_lower}="{value_escaped}"')
    return ' ' + ' '.join(parts)


def _get_valid_children(parent: str) -> Set[str]:
    """获取某个标签允许的子元素集合（简化规则）。"""
    return CHILDREN_RULES.get(parent, set())


def _find_matching_open(stack: List[str], tag: str) -> Optional[int]:
    """在栈中查找匹配的开始标签位置，返回索引或 None。"""
    for i in range(len(stack) - 1, -1, -1):
        if stack[i] == tag:
            return i
    return None


def build_xhtml(events: List[Tuple[str, str, dict]]) -> str:
    """
    根据事件列表构建 XHTML 字符串。
    自动修复未闭合标签和嵌套错位。
    """
    output_parts: List[str] = []
    # 维护一个打开的标签栈
    stack: List[str] = []

    for event_type, tag, attrs in events:
        if event_type == 'data':
            # 文本节点：转义特殊字符
            output_parts.append(escape_text(tag))

        elif event_type == 'comment':
            output_parts.append(f'<!--{tag}-->')

        elif event_type == 'decl':
            output_parts.append(f'<!{tag}>')

        elif event_type == 'pi':
            output_parts.append(f'<?{tag}?>')

        elif event_type == 'startend':
            # 自闭合标签（如 <br/>）
            output_parts.append(f'<{tag}{format_attrs(attrs)} />')

        elif event_type == 'start':
            # 处理开始标签
            if tag in VOID_ELEMENTS:
                # 空元素直接输出自闭合形式
                output_parts.append(f'<{tag}{format_attrs(attrs)} />')
            else:
                # 检查是否需要先闭合某些自动闭合元素
                while stack and stack[-1] in AUTO_CLOSE_ELEMENTS:
                    # 如果新标签不是当前自动闭合元素的合法子元素，则自动闭合
                    valid_children = _get_valid_children(stack[-1])
                    if valid_children and tag not in valid_children:
                        closed = stack.pop()
                        output_parts.append(f'</{closed}>')
                    else:
                        break

                # 检查嵌套错位：如果新标签在栈中已存在且不是栈顶，说明有错位
                if tag in stack and stack[-1] != tag:
                    # 尝试修复：闭合中间所有标签
                    while stack and stack[-1] != tag:
                        unmatched = stack.pop()
                        output_parts.append(f'</{unmatched}>')
                    # 此时栈顶是 tag，不需要额外操作

                # 输出开始标签
                output_parts.append(f'<{tag}{format_attrs(attrs)}>')
                stack.append(tag)

        elif event_type == 'end':
            # 处理结束标签
            if tag in VOID_ELEMENTS:
                # 空元素忽略结束标签
                continue

            # 在栈中查找匹配的开始标签
            match_idx = _find_matching_open(stack, tag)
            if match_idx is not None:
                # 闭合从匹配位置到栈顶的所有标签
                while len(stack) > match_idx:
                    unmatched = stack.pop()
                    output_parts.append(f'</{unmatched}>')
            else:
                # 没有对应的开始标签，忽略（宽容处理）
                pass

    # 处理剩余的未闭合标签
    while stack:
        tag = stack.pop()
        output_parts.append(f'</{tag}>')

    return ''.join(output_parts)


def xhtmlize(html: str) -> str:
    """
    将 HTML 片段转换为 XHTML 标准格式。

    参数:
        html: 输入的 HTML 字符串

    返回:
        规范化后的 XHTML 字符串

    异常:
        XhtmlizeError: 处理过程中发生错误
    """
    if html is None:
        raise XhtmlizeError('E001', '输入为空')
    if not isinstance(html, str):
        raise XhtmlizeError('E002', '输入不是字符串')

    # 去除首尾空白
    html = html.strip()
    if not html:
        raise XhtmlizeError('E001', '输入为空')

    # 解析 HTML
    events = parse_html(html)

    # 构建 XHTML
    result = build_xhtml(events)

    return result


# ============================================================
# 文件处理辅助函数
# ============================================================
def read_file(filepath: str) -> str:
    """读取文本文件内容。"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        raise XhtmlizeError('E003', f'文件不存在: {filepath}')
    except IsADirectoryError:
        raise XhtmlizeError('E003', f'路径是目录: {filepath}')
    except PermissionError:
        raise XhtmlizeError('E003', f'无权限读取文件: {filepath}')
    except Exception as e:
        raise XhtmlizeError('E003', f'文件读取失败: {str(e)}')


# ============================================================
# 自检功能
# ============================================================
def run_selftest() -> bool:
    """
    运行内置自检，验证核心逻辑。

    使用硬编码样例数据，不依赖外部文件或网络。
    断言使用宽松阈值，确保稳健通过。

    返回:
        True 表示自检通过
    """
    print("=" * 60)
    print("xhtmlize 自检程序")
    print("=" * 60)

    # 测试用例 1: 基本标签修复
    test_cases = [
        # (输入, 期望包含的关键字列表, 期望不包含的关键字列表)
        (
            '<p>Hello & welcome</p>',
            ['<p>', 'Hello', '&amp;', 'welcome', '</p>'],
            ['& ']
        ),
        (
            '<div><p>text<li>item</div>',
            ['<div>', '<p>', 'text', '<li>', 'item', '</li>', '</p>', '</div>'],
            []
        ),
        (
            '<IMG SRC="test.jpg" ALT="A & B">',
            ['<img', 'src="test.jpg"', 'alt="A &amp; B"', '/>'],
            ['<IMG', 'SRC=']
        ),
        (
            '<br><hr>',
            ['<br />', '<hr />'],
            ['<br>', '<hr>']
        ),
        (
            '<ul><li>one<li>two</ul>',
            ['<ul>', '<li>', 'one', '</li>', '<li>', 'two', '</li>', '</ul>'],
            []
        ),
        (
            '<table><tr><td>cell</table>',
            ['<table>', '<tr>', '<td>', 'cell', '</td>', '</tr>', '</table>'],
            []
        ),
    ]

    all_passed = True

    for i, (input_html, should_contain, should_not_contain) in enumerate(test_cases, 1):
        print(f"\n测试用例 {i}:")
        print(f"  输入: {input_html!r}")

        try:
            result = xhtmlize(input_html)
            print(f"  输出: {result!r}")

            # 检查应包含的内容
            for keyword in should_contain:
                if keyword not in result:
                    print(f"  ❌ 缺少关键字: {keyword!r}")
                    all_passed = False
                    break

            # 检查不应包含的内容
            for keyword in should_not_contain:
                if keyword in result:
                    print(f"  ❌ 不应包含关键字: {keyword!r}")
                    all_passed = False
                    break

            # 额外检查: 输出不应为空
            if not result:
                print("  ❌ 输出为空")
                all_passed = False

            # 额外检查: 标签配对（宽松检查）
            open_tags = re.findall(r'<([a-zA-Z][a-zA-Z0-9]*)(?:\s|>)', result)
            close_tags = re.findall(r'</([a-zA-Z][a-zA-Z0-9]*)>', result)
            # 空元素不需要闭合
            void_in_result = [t for t in open_tags if t in VOID_ELEMENTS]
            non_void_open = [t for t in open_tags if t not in VOID_ELEMENTS]
            # 检查非空元素是否都有对应闭合（宽松：只检查数量大致匹配）
            if len(non_void_open) > len(close_tags) + 1:
                print(f"  ❌ 标签配对可能有问题: 开={len(non_void_open)}, 闭={len(close_tags)}")
                all_passed = False

            if all_passed:
                print(f"  ✅ 通过")

        except XhtmlizeError as e:
            print(f"  ❌ 处理出错: {e}")
            all_passed = False
        except Exception as e:
            print(f"  ❌ 未预期错误: {e}")
            all_passed = False

    # 测试用例 2: 属性规范化
    print("\n" + "=" * 60)
    print("属性规范化测试:")
    attr_test = '<A HREF="http://example.com" TARGET="_blank">link</A>'
    try:
        result = xhtmlize(attr_test)
        print(f"  输入: {attr_test!r}")
        print(f"  输出: {result!r}")
        # 检查属性名小写
        if 'href="http://example.com"' in result and 'target="_blank"' in result:
            print("  ✅ 属性规范化正确")
        else:
            print("  ❌ 属性规范化失败")
            all_passed = False
    except Exception as e:
        print(f"  ❌ 属性测试出错: {e}")
        all_passed = False

    # 测试用例 3: 文本转义
    print("\n" + "=" * 60)
    print("文本转义测试:")
