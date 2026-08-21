#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
iforgor — 代码语法速查命令行助手
版本: 1.0.1
许可证: MIT
"""

import argparse
import sys
import json
from difflib import get_close_matches

# 错误码定义
ERROR_CODES = {
    "E001": "未知错误",
    "E002": "无效命令行参数",
    "E003": "未找到匹配的语法条目",
    "E004": "语言不支持",
    "E005": "关键词为空",
    "E006": "内置知识库损坏",
    "E007": "自检失败",
    "E008": "输出格式错误",
    "E009": "输入参数缺失",
    "E010": "内部逻辑错误",
}

# 内置语法知识库（硬编码，不依赖外部文件）
SYNTAX_KB = {
    "python": {
        "list-comprehension": {
            "syntax": "[expression for item in iterable if condition]",
            "params": {
                "expression": "对每个元素执行的表达式",
                "item": "迭代变量名",
                "iterable": "可迭代对象",
                "condition": "可选过滤条件"
            },
            "example": "[x**2 for x in range(10) if x % 2 == 0]",
            "note": "列表推导式比循环更简洁，但复杂嵌套可读性差"
        },
        "lambda": {
            "syntax": "lambda arguments: expression",
            "params": {
                "arguments": "逗号分隔的参数列表",
                "expression": "单行表达式"
            },
            "example": "add = lambda x, y: x + y",
            "note": "lambda 只能包含单行表达式，不能包含语句"
        },
        "decorator": {
            "syntax": "@decorator_name\ndef function_name(...): ...",
            "params": {
                "decorator_name": "装饰器函数名",
                "function_name": "被装饰的函数"
            },
            "example": "@staticmethod\ndef my_method(): pass",
            "note": "装饰器在函数定义时执行，常用于日志、权限等"
        }
    },
    "javascript": {
        "arrow-function": {
            "syntax": "const func = (params) => expression",
            "params": {
                "params": "参数列表",
                "expression": "返回值表达式"
            },
            "example": "const double = x => x * 2",
            "note": "箭头函数没有自己的 this 绑定"
        },
        "async-await": {
            "syntax": "async function foo() { await bar(); }",
            "params": {
                "foo": "异步函数名",
                "bar": "返回 Promise 的函数"
            },
            "example": "async function fetchData() { const res = await fetch(url); }",
            "note": "await 只能在 async 函数内使用"
        }
    },
    "go": {
        "goroutine": {
            "syntax": "go functionName(args)",
            "params": {
                "functionName": "要并发执行的函数",
                "args": "函数参数"
            },
            "example": "go handleRequest(w, r)",
            "note": "goroutine 轻量级，但要注意并发安全"
        },
        "defer": {
            "syntax": "defer functionCall()",
            "params": {
                "functionCall": "延迟执行的函数调用"
            },
            "example": "defer file.Close()",
            "note": "defer 在函数返回前执行，适合资源清理"
        }
    },
    "rust": {
        "ownership": {
            "syntax": "let s = String::from(\"hello\");",
            "params": {
                "s": "所有权变量"
            },
            "example": "let s1 = String::from(\"a\"); let s2 = s1;",
            "note": "每个值同时只能有一个所有者"
        },
        "match": {
            "syntax": "match value { pattern => expression, ... }",
            "params": {
                "value": "要匹配的值",
                "pattern": "匹配模式",
                "expression": "匹配后执行的表达式"
            },
            "example": "match x { 1 => \"one\", _ => \"other\" }",
            "note": "match 必须穷尽所有可能"
        }
    },
    "java": {
        "lambda": {
            "syntax": "(params) -> expression",
            "params": {
                "params": "参数列表",
                "expression": "表达式或代码块"
            },
            "example": "(a, b) -> a + b",
            "note": "Java 8+ 支持，函数式接口可用"
        },
        "stream": {
            "syntax": "list.stream().filter(...).map(...).collect(...)",
            "params": {
                "list": "集合对象",
                "filter": "过滤条件",
                "map": "映射函数",
                "collect": "收集结果"
            },
            "example": "list.stream().filter(x -> x > 0).collect(Collectors.toList())",
            "note": "Stream 是惰性求值，终端操作才执行"
        }
    },
    "cpp": {
        "smart-pointer": {
            "syntax": "std::unique_ptr<T> ptr = std::make_unique<T>(args);",
            "params": {
                "T": "类型",
                "args": "构造参数"
            },
            "example": "auto p = std::make_unique<Foo>(1, 2);",
            "note": "C++11 引入，自动管理内存"
        },
        "template": {
            "syntax": "template<typename T> T func(T arg) { ... }",
            "params": {
                "T": "模板类型参数",
                "arg": "函数参数"
            },
            "example": "template<typename T> T max(T a, T b) { return a > b ? a : b; }",
            "note": "模板在编译时实例化"
        }
    }
}

# 语言别名映射（模糊匹配）
LANGUAGE_ALIASES = {
    "python": ["python", "py", "python3"],
    "javascript": ["javascript", "js", "node"],
    "go": ["go", "golang"],
    "rust": ["rust", "rs"],
    "java": ["java"],
    "cpp": ["cpp", "c++", "cplusplus", "cxx"],
}

# 关键词别名映射
KEYWORD_ALIASES = {
    "list-comprehension": ["list-comprehension", "listcomp", "list comp"],
    "lambda": ["lambda", "anonymous function", "匿名函数"],
    "decorator": ["decorator", "装饰器"],
    "arrow-function": ["arrow-function", "arrow", "箭头函数"],
    "async-await": ["async-await", "async", "异步"],
    "goroutine": ["goroutine", "go routine", "协程"],
    "defer": ["defer", "延迟"],
    "ownership": ["ownership", "所有权"],
    "match": ["match", "匹配"],
    "stream": ["stream", "流"],
    "smart-pointer": ["smart-pointer", "smart pointer", "智能指针"],
    "template": ["template", "模板"],
}


def normalize_language(lang: str) -> str | None:
    """将用户输入的语言标准化为知识库中的键名"""
    if not lang:
        return None
    lang_lower = lang.strip().lower()
    for canonical, aliases in LANGUAGE_ALIASES.items():
        if lang_lower in aliases:
            return canonical
    return None


def normalize_keyword(keyword: str) -> str | None:
    """将用户输入的关键词标准化为知识库中的键名"""
    if not keyword:
        return None
    keyword_lower = keyword.strip().lower()
    for canonical, aliases in KEYWORD_ALIASES.items():
        if keyword_lower in aliases:
            return canonical
    return None


def search_syntax(lang: str, keyword: str) -> dict | None:
    """
    在知识库中搜索语法条目
    
    返回:
        dict: 包含语法信息的字典
        None: 未找到
    """
    canonical_lang = normalize_language(lang)
    if canonical_lang is None:
        return None
    
    canonical_keyword = normalize_keyword(keyword)
    if canonical_keyword is None:
        return None
    
    lang_entries = SYNTAX_KB.get(canonical_lang, {})
    if canonical_keyword in lang_entries:
        entry = lang_entries[canonical_keyword].copy()
        entry["language"] = canonical_lang
        entry["keyword"] = canonical_keyword
        return entry
    
    return None


def get_suggestions(lang: str, keyword: str, limit: int = 3) -> list[str]:
    """获取模糊匹配建议"""
    canonical_lang = normalize_language(lang)
    if canonical_lang is None:
        return []
    
    lang_entries = SYNTAX_KB.get(canonical_lang, {})
    if not lang_entries:
        return []
    
    # 使用 difflib 进行模糊匹配
    available_keywords = list(lang_entries.keys())
    matches = get_close_matches(keyword, available_keywords, n=limit, cutoff=0.4)
    
    # 加上别名匹配
    alias_matches = []
    for canonical, aliases in KEYWORD_ALIASES.items():
        if canonical in available_keywords and canonical not in matches:
            for alias in aliases:
                if keyword.lower() in alias or alias in keyword.lower():
                    alias_matches.append(canonical)
                    break
    
    # 合并结果，去重，保留顺序
    suggestions = []
    for item in matches + alias_matches:
        if item not in suggestions:
            suggestions.append(item)
    
    return suggestions[:limit]


def format_output(entry: dict) -> str:
    """格式化语法条目输出"""
    lines = []
    lines.append("=" * 50)
    lines.append(f"语言: {entry['language']}")
    lines.append(f"语法: {entry['keyword']}")
    lines.append("=" * 50)
    lines.append(f"语法结构:")
    lines.append(f"  {entry['syntax']}")
    lines.append("")
    lines.append(f"参数说明:")
    for param, desc in entry['params'].items():
        lines.append(f"  {param}: {desc}")
    lines.append("")
    lines.append(f"示例:")
    lines.append(f"  {entry['example']}")
    lines.append("")
    lines.append(f"注意事项:")
    lines.append(f"  {entry['note']}")
    lines.append("=" * 50)
    return "\n".join(lines)


def run_selftest() -> bool:
    """
    内置自检函数，使用硬编码样例数据
    不访问网络、不读取外部文件
    """
    print("开始自检...")
    
    # 测试1: 语言标准化
    assert normalize_language("python") == "python", "E007: Python 语言标准化失败"
    assert normalize_language("py") == "python", "E007: py 别名失败"
    assert normalize_language("js") == "javascript", "E007: js 别名失败"
    assert normalize_language("golang") == "go", "E007: golang 别名失败"
    assert normalize_language("c++") == "cpp", "E007: c++ 别名失败"
    print("  [PASS] 语言标准化")
    
    # 测试2: 关键词标准化
    assert normalize_keyword("list-comprehension") == "list-comprehension", "E007: 关键词标准化失败"
    assert normalize_keyword("listcomp") == "list-comprehension", "E007: listcomp 别名失败"
    assert normalize_keyword("arrow") == "arrow-function", "E007: arrow 别名失败"
    print("  [PASS] 关键词标准化")
    
    # 测试3: 搜索功能
    result = search_syntax("python", "list-comprehension")
    assert result is not None, "E007: 搜索 python list-comprehension 失败"
    assert "syntax" in result, "E007: 搜索结果缺少 syntax 字段"
    assert "example" in result, "E007: 搜索结果缺少 example 字段"
    assert "note" in result, "E007: 搜索结果缺少 note 字段"
    assert len(result["syntax"]) > 0, "E007: syntax 为空"
    assert len(result["example"]) > 0, "E007: example 为空"
    print("  [PASS] 搜索功能")
    
    # 测试4: 多语言覆盖
    test_cases = [
        ("go", "goroutine"),
        ("rust", "ownership"),
        ("java", "lambda"),
        ("cpp", "smart-pointer"),
        ("javascript", "async-await"),
    ]
    for lang, keyword in test_cases:
        result = search_syntax(lang, keyword)
        assert result is not None, f"E007: 搜索 {lang} {keyword} 失败"
        assert result["language"] == lang, f"E007: 语言不匹配 {lang}"
    print("  [PASS] 多语言覆盖")
    
    # 测试5: 模糊匹配建议
    suggestions = get_suggestions("python", "list")
    assert isinstance(suggestions, list), "E007: 建议返回类型错误"
    assert len(suggestions) >= 1, "E007: 应有至少一个建议"
    assert "list-comprehension" in suggestions, "E007: 建议中应包含 list-comprehension"
    print("  [PASS] 模糊匹配建议")
    
    # 测试6: 输出格式化
    result = search_syntax("python", "lambda")
    output = format_output(result)
    assert "lambda" in output, "E007: 输出中应包含关键词"
    assert "参数说明" in output, "E007: 输出中应包含参数说明"
    assert "示例" in output, "E007: 输出中应包含示例"
    assert len(output) > 50, "E007: 输出内容过短"
    print("  [PASS] 输出格式化")
    
    # 测试7: 错误处理
    assert normalize_language("nonexistent") is None, "E007: 不存在的语言应返回 None"
    assert normalize_keyword("nonexistent") is None, "E007: 不存在的关键词应返回 None"
    assert search_syntax("nonexistent", "nonexistent") is None, "E007: 不存在的组合应返回 None"
    print("  [PASS] 错误处理")
    
    # 测试8: 知识库完整性
    for lang, entries in SYNTAX_KB.items():
        assert len(entries) >= 2, f"E007: 语言 {lang} 至少应有 2 个条目"
        for keyword, entry in entries.items():
            assert "syntax" in entry, f"E007: {lang}/{keyword} 缺少 syntax"
            assert "example" in entry, f"E007: {lang}/{keyword} 缺少 example"
            assert "note" in entry, f"E007: {lang}/{keyword} 缺少 note"
            assert "params" in entry, f"E007: {lang}/{keyword} 缺少 params"
            assert len(entry["syntax"]) > 0, f"E007: {lang}/{keyword} syntax 为空"
            assert len(entry["example"]) > 0, f"E007: {lang}/{keyword} example 为空"
    print("  [PASS] 知识库完整性")
    
    print("所有自检通过！")
    return True


def main():
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description="iforgor - 代码语法速查命令行助手",
        epilog="示例: iforgor python list-comprehension"
    )
    parser.add_argument(
        "--args",
        nargs="*",
        help="语言和关键词，如: python list-comprehension"
    )
    parser.add_argument(
        "--version",
        action="store_true",
        help="显示版本信息"
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检"
    )
    parser.add_argument(
        "--languages",
        action="store_true",
        help="列出支持的语言"
    )
    
    try:
        args = parser.parse_args()
    except SystemExit as e:
        if e.code != 0:
            print(f"错误 E002: {ERROR_CODES['E002']}")
        return 1
    
    # 处理 --version
    if args.version:
        print("iforgor 版本 1.0.1")
        print("许可证: MIT")
        return 0
    
    # 处理 --selftest
    if args.selftest:
        try:
            success = run_selftest()
            return 0 if success else 1
        except AssertionError as e:
            print(f"自检失败: {e}")
            return 1
        except Exception as e:
            print(f"错误 E001: {ERROR_CODES['E001']} - {e}")
            return 1
    
    # 处理 --languages
    if args.languages:
        print("支持的语言:")
        for lang in SYNTAX_KB.keys():
            print(f"  - {lang}")
        return 0
    
    # 处理查询参数
    if len(args.args) == 0:
        print("用法: iforgor <语言> <关键词>")
        print("示例: iforgor python list-comprehension")
        print("运行 'iforgor --help' 查看帮助")
        print("运行 'iforgor --languages' 查看支持的语言")
        return 1
    
    if len(args.args) < 2:
        print(f"错误 E009: {ERROR_CODES['E009']} - 需要提供语言和关键词")
        return 1
    
    lang = args.args[0]
    keyword = args.args[1]
    
    # 检查语言是否支持
    canonical_lang = normalize_language(lang)
    if canonical_lang is None:
        print(f"错误 E004: {ERROR_CODES['E004']} - 不支持的语言: {lang}")
        print(f"支持的语言: {', '.join(SYNTAX_KB.keys())}")
        return 1
    
    # 检查关键词是否为空
    if not keyword.strip():
        print(f"错误 E005: {ERROR_CODES['E005']}")
        return 1
    
    # 搜索语法
    result = search_syntax(lang, keyword)
    if result is None:
        suggestions = get_suggestions(lang, keyword)
        if suggestions:
            print(f"错误 E003: {ERROR_CODES['E003']} - 未找到 '{keyword}'")
            print(f"您是否想查找: {', '.join(suggestions)}")
        else:
            print(f"错误 E003: {ERROR_CODES['E003']} - 未找到 '{keyword}'")
            print(f"在 {canonical_lang} 中可用的关键词: {', '.join(SYNTAX_KB[canonical_lang].keys())}")
        return 1
    
    # 格式化并输出
    try:
        output = format_output(result)
        print(output)
        return 0
    except Exception as e:
        print(f"错误 E008: {ERROR_CODES['E008']} - {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
