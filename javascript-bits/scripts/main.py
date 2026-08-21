#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
javascript-bits — JavaScript 实用代码片段速查与使用指南

本脚本基于功能规格独立实现（clean-room），不复制任何既有代码。
提供以下能力：
  1. 片段检索与推荐（按关键词匹配）
  2. 片段解析与讲解（返回原理、适用版本）
  3. 代码适配与改造（ES5 <-> ES6+ 转换示例）
  4. 片段组合与集成（如防抖+节流组合）
  5. 边界条件提示（特殊输入行为说明）

仅使用 Python 标准库，无第三方依赖。
"""

import argparse
import json
import sys
from typing import Dict, List, Optional, Tuple

# ========== 错误码定义 ==========
# E001: 参数解析错误
# E002: 未找到匹配片段
# E003: 片段数据格式错误
# E004: 无效的转换方向
# E005: 无效的组合请求
# E006: 输入参数类型错误
# E007: 内部数据不一致
# E008: 自检断言失败
# E009: 文件读写错误（预留）
# E010: 未知错误


class SkillError(Exception):
    """技能统一异常类，携带错误码。"""

    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"[{code}] {message}")


# ========== 内置片段数据库 ==========
# 结构说明：
#   id: 唯一标识
#   name: 片段名称
#   tags: 搜索标签
#   category: 分类（array/function/string/object/other）
#   es_version: 适用版本
#   description: 简要描述
#   code: 示例代码
#   explanation: 工作原理讲解
#   boundary: 边界条件提示
#   transform: 适配示例（es5_to_es6 / es6_to_es5）

_SNIPPETS: List[Dict] = [
    {
        "id": "arr-unique",
        "name": "数组去重",
        "tags": ["数组", "去重", "unique", "array", "重复"],
        "category": "array",
        "es_version": "ES6+",
        "description": "使用 Set 对数组进行去重。",
        "code": "const unique = (arr) => [...new Set(arr)];",
        "explanation": "Set 对象自动存储唯一值，展开运算符将 Set 转回数组。",
        "boundary": "空数组返回空数组；包含 NaN 时 Set 可正确去重（NaN===NaN 在 Set 中视为相等）。",
        "transform": {
            "es6_to_es5": "function unique(arr) { return arr.filter(function(v, i, a) { return a.indexOf(v) === i; }); }",
            "es5_to_es6": "const unique = (arr) => [...new Set(arr)];"
        }
    },
    {
        "id": "debounce",
        "name": "防抖",
        "tags": ["防抖", "debounce", "性能", "事件", "延迟"],
        "category": "function",
        "es_version": "ES5+",
        "description": "在事件触发后等待一段时间再执行，若期间再次触发则重新计时。",
        "code": "function debounce(fn, wait) { let t; return function(...args) { clearTimeout(t); t = setTimeout(() => fn.apply(this, args), wait); }; }",
        "explanation": "每次调用清除前一个定时器并重新设置，确保只在最后一次触发后执行。",
        "boundary": "wait 为 0 时仍为异步执行；this 绑定通过 apply 保留。",
        "transform": {
            "es6_to_es5": "function debounce(fn, wait) { var t; return function() { var args = arguments; var ctx = this; clearTimeout(t); t = setTimeout(function() { fn.apply(ctx, args); }, wait); }; }",
            "es5_to_es6": "const debounce = (fn, wait) => { let t; return (...args) => { clearTimeout(t); t = setTimeout(() => fn.apply(this, args), wait); }; };"
        }
    },
    {
        "id": "throttle",
        "name": "节流",
        "tags": ["节流", "throttle", "性能", "事件", "频率"],
        "category": "function",
        "es_version": "ES5+",
        "description": "限制函数在指定时间间隔内最多执行一次。",
        "code": "function throttle(fn, interval) { let last = 0; return function(...args) { const now = Date.now(); if (now - last >= interval) { last = now; fn.apply(this, args); } }; }",
        "explanation": "记录上次执行时间，只有间隔超过阈值才执行。",
        "boundary": "首次调用立即执行；interval 为 0 时每次调用都会执行。",
        "transform": {
            "es6_to_es5": "function throttle(fn, interval) { var last = 0; return function() { var args = arguments; var ctx = this; var now = Date.now(); if (now - last >= interval) { last = now; fn.apply(ctx, args); } }; }",
            "es5_to_es6": "const throttle = (fn, interval) => { let last = 0; return (...args) => { const now = Date.now(); if (now - last >= interval) { last = now; fn.apply(this, args); } }; };"
        }
    },
    {
        "id": "debounce-throttle",
        "name": "防抖+节流组合",
        "tags": ["防抖", "节流", "组合", "debounce", "throttle", "性能"],
        "category": "function",
        "es_version": "ES6+",
        "description": "结合防抖和节流的优点：在频繁触发时以固定频率执行，停止触发后延迟执行一次。",
        "code": "function debounceThrottle(fn, wait, maxWait) { let timer, lastRun = 0; return function(...args) { const now = Date.now(); clearTimeout(timer); if (now - lastRun >= maxWait) { lastRun = now; fn.apply(this, args); } else { timer = setTimeout(() => { lastRun = Date.now(); fn.apply(this, args); }, wait); } }; }",
        "explanation": "使用 maxWait 保证最大等待时间，wait 控制停止后的延迟执行。",
        "boundary": "maxWait 应大于 wait；若 maxWait 为 0 则退化为普通防抖。",
        "transform": {
            "es6_to_es5": "function debounceThrottle(fn, wait, maxWait) { var timer, lastRun = 0; return function() { var args = arguments; var ctx = this; var now = Date.now(); clearTimeout(timer); if (now - lastRun >= maxWait) { lastRun = now; fn.apply(ctx, args); } else { timer = setTimeout(function() { lastRun = Date.now(); fn.apply(ctx, args); }, wait); } }; }",
            "es5_to_es6": "const debounceThrottle = (fn, wait, maxWait) => { let timer, lastRun = 0; return (...args) => { const now = Date.now(); clearTimeout(timer); if (now - lastRun >= maxWait) { lastRun = now; fn.apply(this, args); } else { timer = setTimeout(() => { lastRun = Date.now(); fn.apply(this, args); }, wait); } }; };"
        }
    },
    {
        "id": "str-truncate",
        "name": "字符串截断",
        "tags": ["字符串", "截断", "truncate", "string", "省略"],
        "category": "string",
        "es_version": "ES6+",
        "description": "按长度截断字符串并添加省略号。",
        "code": "const truncate = (str, len) => str.length > len ? str.slice(0, len) + '...' : str;",
        "explanation": "比较长度后使用 slice 截取前 len 个字符并拼接省略号。",
        "boundary": "len 小于等于 3 时省略号可能被截断；空字符串直接返回。",
        "transform": {
            "es6_to_es5": "function truncate(str, len) { return str.length > len ? str.slice(0, len) + '...' : str; }",
            "es5_to_es6": "const truncate = (str, len) => str.length > len ? str.slice(0, len) + '...' : str;"
        }
    },
    {
        "id": "obj-pick",
        "name": "对象选取",
        "tags": ["对象", "选取", "pick", "object", "属性"],
        "category": "object",
        "es_version": "ES6+",
        "description": "从对象中选取指定属性组成新对象。",
        "code": "const pick = (obj, keys) => Object.fromEntries(keys.filter(k => k in obj).map(k => [k, obj[k]]));",
        "explanation": "过滤不存在的键，然后从 entries 构建新对象。",
        "boundary": "不存在的键会被忽略；obj 为 null 或 undefined 时抛出异常。",
        "transform": {
            "es6_to_es5": "function pick(obj, keys) { var result = {}; keys.forEach(function(k) { if (k in obj) result[k] = obj[k]; }); return result; }",
            "es5_to_es6": "const pick = (obj, keys) => Object.fromEntries(keys.filter(k => k in obj).map(k => [k, obj[k]]));"
        }
    }
]

# 分类元数据
_CATEGORIES = {
    "array": "数组相关",
    "function": "函数相关（性能优化）",
    "string": "字符串处理",
    "object": "对象操作",
    "other": "其他"
}

# 能力边界说明
_CAPABILITIES = {
    "can": [
        "代码片段检索与推荐",
        "片段解析与讲解",
        "代码适配与改造（ES5/ES6+ 互转）",
        "片段组合与集成",
        "边界条件提示"
    ],
    "cannot": [
        "不执行 JavaScript 代码（无运行时环境）",
        "不提供完整的项目脚手架或框架代码",
        "不替代官方文档（MDN、ECMAScript 规范）",
        "不保证代码在特定浏览器/Node 版本下的兼容性",
        "不提供安全审计或性能基准测试"
    ]
}


# ========== 核心逻辑函数 ==========

def search_snippets(query: str) -> List[Dict]:
    """
    根据关键词检索片段。

    参数:
        query: 搜索关键词

    返回:
        匹配的片段列表（按相关度排序）

    错误:
        E006: query 不是字符串
        E002: 无匹配结果
    """
    if not isinstance(query, str):
        raise SkillError("E006", "搜索关键词必须是字符串")

    query_lower = query.lower().strip()
    if not query_lower:
        raise SkillError("E002", "搜索关键词不能为空")

    results = []
    for snippet in _SNIPPETS:
        # 在标签、名称、描述中搜索
        searchable = " ".join([
            snippet["name"],
            snippet["description"],
            " ".join(snippet["tags"]),
            snippet["category"]
        ]).lower()

        if query_lower in searchable:
            results.append(snippet)

    if not results:
        raise SkillError("E002", f"未找到与 '{query}' 匹配的片段")

    return results


def explain_snippet(snippet_id: str) -> Dict:
    """
    解析并讲解指定片段。

    参数:
        snippet_id: 片段唯一标识

    返回:
        包含讲解信息的字典

    错误:
        E006: snippet_id 不是字符串
        E002: 未找到指定片段
    """
    if not isinstance(snippet_id, str):
        raise SkillError("E006", "片段 ID 必须是字符串")

    for snippet in _SNIPPETS:
        if snippet["id"] == snippet_id:
            return {
                "id": snippet["id"],
                "name": snippet["name"],
                "es_version": snippet["es_version"],
                "code": snippet["code"],
                "explanation": snippet["explanation"],
                "boundary": snippet["boundary"]
            }

    raise SkillError("E002", f"未找到 ID 为 '{snippet_id}' 的片段")


def transform_code(snippet_id: str, direction: str) -> Dict:
    """
    代码适配与改造（ES5/ES6+ 互转）。

    参数:
        snippet_id: 片段唯一标识
        direction: 转换方向（es5_to_es6 或 es6_to_es5）

    返回:
        包含转换结果的字典

    错误:
        E006: 参数类型错误
        E002: 未找到片段
        E004: 无效的转换方向
    """
    if not isinstance(snippet_id, str) or not isinstance(direction, str):
        raise SkillError("E006", "片段 ID 和转换方向必须是字符串")

    if direction not in ("es5_to_es6", "es6_to_es5"):
        raise SkillError("E004", f"无效的转换方向 '{direction}'，应为 es5_to_es6 或 es6_to_es5")

    for snippet in _SNIPPETS:
        if snippet["id"] == snippet_id:
            transform_map = snippet.get("transform", {})
            if direction not in transform_map:
                raise SkillError("E007", f"片段 '{snippet_id}' 缺少 {direction} 转换示例")
            return {
                "id": snippet_id,
                "direction": direction,
                "original": snippet["code"],
                "converted": transform_map[direction]
            }

    raise SkillError("E002", f"未找到 ID 为 '{snippet_id}' 的片段")


def combine_snippets(ids: List[str]) -> Dict:
    """
    片段组合与集成。

    参数:
        ids: 要组合的片段 ID 列表

    返回:
        组合后的片段信息

    错误:
        E006: ids 不是列表
        E005: 组合请求无效（少于 2 个片段或含重复）
        E002: 未找到指定片段
    """
    if not isinstance(ids, list):
        raise SkillError("E006", "片段 ID 列表必须是列表类型")

    if len(ids) < 2:
        raise SkillError("E005", "组合至少需要 2 个片段")

    if len(set(ids)) != len(ids):
        raise SkillError("E005", "组合请求包含重复片段 ID")

    selected = []
    for sid in ids:
        found = False
        for snippet in _SNIPPETS:
            if snippet["id"] == sid:
                selected.append(snippet)
                found = True
                break
        if not found:
            raise SkillError("E002", f"未找到 ID 为 '{sid}' 的片段")

    # 检查是否包含防抖和节流组合场景
    names = [s["name"] for s in selected]
    has_debounce = any("防抖" in n for n in names)
    has_throttle = any("节流" in n for n in names)

    combined_name = "+".join(names)
    combined_code = "\n".join([f"// {s['name']}\n{s['code']}" for s in selected])

    description = f"组合片段：{combined_name}"
    if has_debounce and has_throttle:
        description += "（防抖+节流组合可用于输入框搜索场景，兼顾响应速度和性能）"

    return {
        "name": combined_name,
        "description": description,
        "code": combined_code,
        "components": [s["id"] for s in selected]
    }


def get_boundary_info(snippet_id: str) -> Dict:
    """
    获取片段边界条件提示。

    参数:
        snippet_id: 片段唯一标识

    返回:
        包含边界信息的字典

    错误:
        E006: snippet_id 不是字符串
        E002: 未找到指定片段
    """
    if not isinstance(snippet_id, str):
        raise SkillError("E006", "片段 ID 必须是字符串")

    for snippet in _SNIPPETS:
        if snippet["id"] == snippet_id:
            return {
                "id": snippet_id,
                "name": snippet["name"],
                "boundary": snippet["boundary"]
            }

    raise SkillError("E002", f"未找到 ID 为 '{snippet_id}' 的片段")


def get_capabilities() -> Dict:
    """获取能力边界说明。"""
    return _CAPABILITIES


# ========== 自检函数 ==========

def _selftest() -> int:
    """
    内置自检逻辑，使用硬编码样例数据，不依赖外部环境。

    返回:
        0 表示全部通过，非 0 表示失败

    错误:
        E008: 自检断言失败
    """
    print("开始自检...")

    # 测试 1: 搜索功能
    try:
        results = search_snippets("去重")
        assert len(results) >= 1, "搜索'去重'应至少返回 1 个结果"
        assert results[0]["id"] == "arr-unique", "搜索结果第一条应为数组去重"
        print("  [PASS] 搜索功能")
    except AssertionError as e:
        raise SkillError("E008", f"搜索功能自检失败: {e}")

    # 测试 2: 搜索无结果
    try:
        try:
            search_snippets("不存在的关键词xyz")
            raise AssertionError("搜索不存在关键词应抛出 E002")
        except SkillError as e:
            assert e.code == "E002", f"错误码应为 E002，实际为 {e.code}"
        print("  [PASS] 搜索无结果错误处理")
    except AssertionError as e:
        raise SkillError("E008", f"搜索无结果自检失败: {e}")

    # 测试 3: 片段讲解
    try:
        info = explain_snippet("debounce")
        assert info["name"] == "防抖", "片段名称应为'防抖'"
        assert "Set" not in info["code"], "防抖代码不应包含 Set"
        assert "clearTimeout" in info["code"], "防抖代码应包含 clearTimeout"
        print("  [PASS] 片段讲解")
    except AssertionError as e:
        raise SkillError("E008", f"片段讲解自检失败: {e}")

    # 测试 4: 代码转换
    try:
        result = transform_code("arr-unique", "es6_to_es5")
        assert "filter" in result["converted"], "ES5 转换应使用 filter"
        assert "indexOf" in result["converted"], "ES5 转换应使用 indexOf"
        print("  [PASS] 代码转换")
    except AssertionError as e:
        raise SkillError("E008", f"代码转换自检失败: {e}")

    # 测试 5: 无效转换方向
    try:
        try:
            transform_code("arr-unique", "invalid_direction")
            raise AssertionError("无效转换方向应抛出 E004")
        except SkillError as e:
            assert e.code == "E004", f"错误码应为 E004，实际为 {e.code}"
        print("  [PASS] 无效转换方向错误处理")
    except AssertionError as e:
        raise SkillError("E008", f"无效转换方向自检失败: {e}")

    # 测试 6: 片段组合
    try:
        combined = combine_snippets(["debounce", "throttle"])
        assert len(combined["components"]) == 2, "组合应包含 2 个组件"
        assert "防抖" in combined["name"], "组合名称应包含'防抖'"
        assert "节流" in combined["name"], "组合名称应包含'节流'"
        print("  [PASS] 片段组合")
    except AssertionError as e:
        raise SkillError("E008", f"片段组合自检失败: {e}")

    # 测试 7: 边界条件
    try:
        boundary = get_boundary_info("str-truncate")
        assert "省略号" in boundary["boundary"], "边界说明应包含'省略号'"
        print("  [PASS] 边界条件")
    except AssertionError as e:
        raise SkillError("E008", f"边界条件自检失败: {e}")

    # 测试 8: 能力边界
    try:
        caps = get_capabilities()
        assert len(caps["can"]) >= 5, "能力清单应至少包含 5 项"
        assert len(caps["cannot"]) >= 5, "能力边界应至少包含 5 项"
        print("  [PASS] 能力边界")
    except AssertionError as e:
        raise SkillError("E008", f"能力边界自检失败: {e}")

    # 测试 9: 数据完整性
    try:
        for snippet in _SNIPPETS:
            required_keys = ["id", "name", "tags", "category", "es_version",
                             "description", "code", "explanation", "boundary", "transform"]
            for key in required_keys:
                assert key in snippet, f"片段 {snippet.get('id', 'unknown')} 缺少字段 {key}"
            # 检查 transform 包含两个方向
            assert "es5_to_es6" in snippet["transform"], f"片段 {snippet['id']} 缺少 es5_to_es6"
            assert "es6_to_es5" in snippet["transform"], f"片段 {snippet['id']} 缺少 es6_to_es5"
            # 检查分类有效
            assert snippet["category"] in _CATEGORIES, f"片段 {snippet['id']} 分类无效"
        print(f"  [PASS] 数据完整性（共 {len(_SNIPPETS)} 个片段）")
    except AssertionError as e:
        raise SkillError("E008", f"数据完整性自检失败: {e}")

    # 测试 10: 宽松断言 - 片段数量
    try:
        # 使用宽松阈值：至少 5 个片段
        assert len(_SNIPPETS) >= 5, f"片段数量应至少为 5，实际为 {len(_SNIPPETS)}"
        print(f"  [PASS] 片段数量（{len(_SNIPPETS)} >= 5）")
    except AssertionError as e:
        raise SkillError("E008", f"片段数量自检失败: {e}")

    # 测试 11: 宽松断言 - 搜索逻辑一致性
    try:
        # 搜索"数组"应返回至少 1 个结果
        arr_results = search_snippets("数组")
        assert len(arr_results) >= 1, "搜索'数组'应至少返回 1 个结果"
        # 搜索"性能"应返回至少 1 个结果
        perf_results = search_snippets("性能")
        assert len(perf_results) >= 1, "搜索'性能'应至少返回 1 个结果"
        print("  [PASS] 搜索逻辑一致性")
    except AssertionError as e:
        raise SkillError("E008", f"搜索逻辑一致性自检失败: {e}")

    # 测试 12: 宽松断言 - 组合功能
    try:
        # 任意两个不同片段组合都应成功
        ids = [s["id"] for s in _SNIPPETS]
        if len(ids) >= 2:
            combo = combine_snippets(ids[:2])
            assert len(combo["components"]) == 2, "组合组件数应为 2"
            assert combo["code"], "组合代码不应为空"
        print("  [PASS] 组合功能通用性")
    except AssertionError as e:
        raise SkillError("E008", f"组合功能通用性自检失败: {e}")

    print("自检全部通过！")
    return 0


# ========== 命令行接口 ==========

def _format_output(data: Dict, pretty: bool = True) -> str:
    """格式化输出为 JSON 字符串。"""
    if pretty:
        return json.dumps(data, ensure_ascii=False, indent=2)
    return json.dumps(data, ensure_ascii=False)


def main() -> int:
    """
    主入口函数。

    返回:
        进程退出码
    """
    parser = argparse.ArgumentParser(
        prog="javascript-bits",
        description="JavaScript 代码片段 实用工具集",
        epilog="示例: python main.py search 去重 | python main.py explain debounce"
    )

    # 子命令
    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # search 命令
    search_parser = subparsers.add_parser("search", help="搜索代码片段")
    search_parser.add_argument("--query", type=str, help="搜索关键词")

    # explain 命令
    explain_parser = subparsers.add_parser("explain", help="解析片段原理")
    explain_parser.add_argument("--snippet_id", type=str, help="片段 ID")

    # transform 命令
    transform_parser = subparsers.add_parser("transform", help="代码适配转换")
    transform_parser.add_argument("--snippet_id", type=str, help="片段 ID")
    transform_parser.add_argument("--direction", type=str, choices=["es5_to_es6", "es6_to_es5"],
                                  help="转换方向")

    # combine 命令
    combine_parser = subparsers.add_parser("combine", help="片段组合")
    combine_parser.add_argument("--ids", nargs="+", type=str, help="要组合的片段 ID 列表（至少 2 个）")

    # boundary 命令
    boundary_parser = subparsers.add_parser("boundary", help="查看边界条件")
    boundary_parser.add_argument("--snippet_id", type=str, help="片段 ID")

    # capabilities 命令
    subparsers.add_parser("capabilities", help="查看能力边界")

    # list 命令
    list_parser = subparsers.add_parser("list", help="列出所有片段")
    list_parser.add_argument("--category", type=str, choices=list(_CATEGORIES.keys()),
                             help="按分类过滤")

    # selftest 命令
    subparsers.add_parser("selftest", help="运行自检")

    # 全局参数
    parser.add_argument("--selftest", action="store_true", help="运行内置自检（无需其他参数）")

    args = parser.parse_args()

    # 自检优先
    if args.selftest:
        try:
            return _selftest()
        except SkillError as e:
            print(f"自检失败: {e.code}: {e.message}", file=sys.stderr)
            return 1

    # 无命令时打印帮助
    if not args.command:
        parser.print_help()
        return 0

    try:
        if args.command == "search":
            results = search_snippets(args.query)
            output = {
                "query": args.query,
                "count": len(results),
                "results": [
                    {
                        "id": r["id"],
                        "name": r["name"],
                        "category": _CATEGORIES.get(r["category"], r["category"]),
                        "es_version": r["es_version"],
                        "description": r["description"],
                        "code": r["code"]
                    }
                    for r in results
                ]
            }
            print(_format_output(output))

        elif args.command == "explain":
            info = explain_snippet(args.snippet_id)
            print(_format_output(info))

        elif args.command == "transform":
            result = transform_code(args.snippet_id, args.direction)
            print(_format_output(result))

        elif args.command == "combine":
            result = combine_snippets(args.ids)
            print(_format_output(result))

        elif args.command == "boundary":
            info = get_boundary_info(args.snippet_id)
            print(_format_output(info))

        elif args.command == "capabilities":
            caps = get_capabilities()
            output = {
                "can": caps["can"],
                "cannot": caps["cannot"]
            }
            print(_format_output(output))

        elif args.command == "list":
            snippets = _SNIPPETS
            if args.category:
                snippets = [s for s in snippets if s["category"] == args.category]
            output = {
                "count": len(snippets),
                "snippets": [
                    {
                        "id": s["id"],
                        "name": s["name"],
                        "category": _CATEGORIES.get(s["category"], s["category"]),
                        "es_version": s["es_version"],
                        "description": s["description"]
                    }
                    for s in snippets
                ]
            }
            print(_format_output(output))

        else:
            parser.print_help()
            return 0

    except SkillError as e:
        print(f"错误: {e.code}: {e.message}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"错误: E010: 未知错误: {e}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
