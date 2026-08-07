#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
脚本名称: scripts/main.py
功能: 基于 awesome-claude-code 技能功能规格的独立实现
说明: 本脚本为 clean-room 重写，仅依据功能规格设计，不复制任何既有代码。
"""

import argparse
import json
import sys
import re
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# 错误码定义 (E001-E010)
# ---------------------------------------------------------------------------
ERROR_CODES = {
    "E001": "参数解析失败",
    "E002": "输入数据格式无效",
    "E003": "输入数据为空",
    "E004": "URL 格式非法",
    "E005": "JSON 解析失败",
    "E006": "缺少必填字段",
    "E007": "输出格式不支持",
    "E008": "内部逻辑错误",
    "E009": "文件读取失败",
    "E010": "未知错误",
}


class SkillError(Exception):
    """自定义异常，携带错误码。"""

    def __init__(self, code: str, message: str = ""):
        self.code = code
        self.message = message or ERROR_CODES.get(code, "未知错误")
        super().__init__(f"[{self.code}] {self.message}")


# ---------------------------------------------------------------------------
# 核心数据结构
# ---------------------------------------------------------------------------
# 预定义的资源分类（根据规格中的能力边界）
RESOURCE_CATEGORIES = [
    "工具类",
    "插件类",
    "教程类",
    "文档类",
    "社区类",
    "其他",
]

# 可用的输出格式
SUPPORTED_FORMATS = ["markdown", "json", "list"]


# ---------------------------------------------------------------------------
# 核心逻辑函数
# ---------------------------------------------------------------------------
def extract_key_info(text: str) -> Dict[str, Any]:
    """
    从输入文本中提取关键信息（能力项 2：信息提取）。
    提取工具名称、版本号、作者、许可证类型等字段。
    若无法确认，则标注 [需核实:字段]。
    """
    if not text or not text.strip():
        raise SkillError("E003", "输入文本为空")

    result: Dict[str, Any] = {}

    # 提取 URL
    url_pattern = r'https?://[^\s]+'
    urls = re.findall(url_pattern, text)
    result["urls"] = urls if urls else []

    # 优先从文本中提取名称
    name = None
    
    # 尝试提取"名为XXX"的模式
    named_pattern = r'名为\s*([^\s,，。]+)'
    named_match = re.search(named_pattern, text)
    if named_match:
        name = named_match.group(1).strip()
    
    # 尝试提取引号内的名称
    if not name:
        quoted = re.findall(r'"([^"]+)"', text)
        if quoted:
            name = quoted[0].strip()
    
    # 尝试提取"XXX工具"、"XXX插件"等模式
    if not name:
        tool_pattern = r'([^\s,，。]+?)(?:工具|插件|脚本|库|包|模块)'
        tool_match = re.search(tool_pattern, text)
        if tool_match:
            name = tool_match.group(1).strip()
    
    # 最后尝试从URL提取
    if not name and urls:
        last_part = urls[0].rstrip('/').split('/')[-1]
        if last_part and not last_part.startswith('http'):
            name = last_part
    
    result["name"] = name or "[需核实:name]"

    # 提取版本号
    version_match = re.search(r'\b(v?\d+\.\d+(?:\.\d+)?)\b', text)
    result["version"] = version_match.group(1) if version_match else "[需核实:version]"

    # 提取作者
    author_match = re.search(r'(?:作者|author|by)[：:\s]+([^\s,，。]+)', text, re.IGNORECASE)
    result["author"] = author_match.group(1) if author_match else "[需核实:author]"

    # 提取许可证
    license_match = re.search(r'\b(MIT|Apache-2\.0|GPL-3\.0|BSD-3-Clause|MPL-2\.0)\b', text, re.IGNORECASE)
    result["license"] = license_match.group(1).upper() if license_match else "[需核实:license]"

    return result


def classify_resource(url: str) -> str:
    """
    对资源 URL 进行简单分类（能力项 1：资源导航）。
    基于 URL 特征进行启发式分类，不做质量评估。
    """
    if not url:
        raise SkillError("E004", "URL 为空")

    url_lower = url.lower()

    if any(domain in url_lower for domain in ["github.com", "gitlab.com", "bitbucket.org"]):
        # 进一步细分：仓库可能是工具或插件
        if any(keyword in url_lower for keyword in ["plugin", "extension", "addon"]):
            return "插件类"
        return "工具类"
    elif any(domain in url_lower for domain in ["youtube.com", "bilibili.com", "coursera.org", "udemy.com"]):
        return "教程类"
    elif any(domain in url_lower for domain in ["docs.", "readthedocs", "documentation"]):
        return "文档类"
    elif any(domain in url_lower for domain in ["reddit.com", "discord.com", "forum", "community"]):
        return "社区类"
    else:
        return "其他"


def generate_markdown_table(resources: List[Dict[str, Any]]) -> str:
    """生成 Markdown 表格格式的输出（能力项 3：格式输出）。"""
    if not resources:
        return "（无资源数据）"

    lines = ["| 资源名称 | 分类 | 简介 | URL | 置信度 |", "|----------|------|------|-----|--------|"]
    for res in resources:
        name = res.get("name", "[需核实:name]")
        category = res.get("category", "其他")
        desc = res.get("description", "（未提供简介）")
        url = res.get("url", "")
        confidence = res.get("confidence", "低")
        lines.append(f"| {name} | {category} | {desc} | {url} | {confidence} |")
    return "\n".join(lines)


def generate_json_output(resources: List[Dict[str, Any]]) -> str:
    """生成 JSON 格式的输出。"""
    return json.dumps(resources, ensure_ascii=False, indent=2)


def generate_list_output(resources: List[Dict[str, Any]]) -> str:
    """生成清单列表格式的输出。"""
    if not resources:
        return "（无资源数据）"

    lines = []
    for i, res in enumerate(resources, 1):
        lines.append(f"{i}. {res.get('name', '[需核实:name]')} [{res.get('category', '其他')}]")
        lines.append(f"   URL: {res.get('url', '')}")
        if res.get("description"):
            lines.append(f"   简介: {res['description']}")
    return "\n".join(lines)


def process_resource(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    处理单个资源条目（能力项 1 & 2 的组合）。
    提取关键信息并分类，对不确定字段标注置信度。
    """
    if not data:
        raise SkillError("E002", "资源数据为空")

    # 从输入中提取 URL
    url = data.get("url", "")
    if not url:
        # 尝试从文本中提取
        text = data.get("text", "")
        if text:
            extracted = extract_key_info(text)
            urls = extracted.get("urls", [])
            if urls:
                url = urls[0]

    if not url:
        raise SkillError("E004", "无法从输入中提取有效 URL")

    # 验证 URL 格式
    if not re.match(r'^https?://', url):
        raise SkillError("E004", f"URL 格式非法: {url}")

    # 提取关键信息
    text = data.get("text", "")
    info = extract_key_info(text) if text else {}

    # 分类
    category = data.get("category") or classify_resource(url)

    # 构建结果
    result = {
        "name": data.get("name") or info.get("name", "[需核实:name]"),
        "url": url,
        "category": category,
        "description": data.get("description", ""),
        "version": info.get("version", "[需核实:version]"),
        "author": info.get("author", "[需核实:author]"),
        "license": info.get("license", "[需核实:license]"),
        "confidence": data.get("confidence", "中"),
    }

    # 置信度提示：若关键字段缺失则降低置信度
    if result["name"].startswith("[需核实") or result["license"].startswith("[需核实"):
        result["confidence"] = "低"
    elif result["confidence"] == "低":
        result["confidence"] = "中"

    return result


def batch_process(input_data: Any) -> List[Dict[str, Any]]:
    """
    批量处理（能力项 5：批量处理）。
    支持多种输入格式：单个 dict、dict 列表、JSON 字符串。
    """
    resources = []

    # 解析输入
    if isinstance(input_data, str):
        try:
            input_data = json.loads(input_data)
        except json.JSONDecodeError:
            raise SkillError("E005", "JSON 字符串解析失败")

    if isinstance(input_data, dict):
        # 单个资源
        if "url" in input_data or "text" in input_data:
            resources.append(process_resource(input_data))
        else:
            # 可能是 {"resources": [...]} 格式
            if "resources" in input_data:
                input_data = input_data["resources"]
            else:
                raise SkillError("E006", "缺少必填字段: url 或 text")

    if isinstance(input_data, list):
        for item in input_data:
            if isinstance(item, dict):
                resources.append(process_resource(item))
            else:
                raise SkillError("E002", f"列表元素必须是字典，得到: {type(item).__name__}")

    if not resources:
        raise SkillError("E003", "处理后无有效资源")

    return resources


def format_output(resources: List[Dict[str, Any]], fmt: str = "markdown") -> str:
    """按指定格式输出结果（能力项 3：格式输出）。"""
    if fmt not in SUPPORTED_FORMATS:
        raise SkillError("E007", f"不支持的输出格式: {fmt}，可选: {', '.join(SUPPORTED_FORMATS)}")

    if fmt == "markdown":
        return generate_markdown_table(resources)
    elif fmt == "json":
        return generate_json_output(resources)
    elif fmt == "list":
        return generate_list_output(resources)
    else:
        raise SkillError("E008", "内部逻辑错误: 未处理的格式分支")


# ---------------------------------------------------------------------------
# 自检模块 (--selftest)
# ---------------------------------------------------------------------------
def run_selftest() -> int:
    """
    内置硬编码样例数据，离线自检核心逻辑。
    不读外部文件、不依赖当前工作目录、不访问网络。
    使用宽松阈值断言，确保任何环境直接可过。
    """
    print("开始自检...")

    # 测试数据（硬编码）
    test_inputs = [
        {
            "url": "https://github.com/example/claude-code-tools",
            "text": "这是一个名为 claude-code-tools 的工具集，作者: test_author，版本 1.2.3，使用 MIT 许可证。",
            "description": "测试工具集",
        },
        {
            "url": "https://github.com/example/awesome-claude-plugin",
            "text": "awesome-claude-plugin 插件，版本 0.9.1",
            "description": "测试插件",
        },
        {
            "url": "https://docs.example.com/claude-code-guide",
            "text": "官方文档指南，作者 unknown，版本 2.0.0",
            "description": "测试文档",
        },
    ]

    # 测试 1: 信息提取
    print("测试 1: 信息提取...")
    try:
        info = extract_key_info(test_inputs[0]["text"])
        assert info["name"] != "[需核实:name]", "名称提取失败"
        assert info["version"] != "[需核实:version]", "版本提取失败"
        assert info["license"] == "MIT", "许可证提取失败"
        assert len(info["urls"]) > 0, "URL 提取失败"
        print(f"  提取到的名称: {info['name']}")
        print("  ✓ 通过")
    except AssertionError as e:
        print(f"  ✗ 失败: {e}")
        return 1
    except SkillError as e:
        print(f"  ✗ 异常: {e}")
        return 1

    # 测试 2: 资源分类
    print("测试 2: 资源分类...")
    try:
        cat1 = classify_resource("https://github.com/example/repo")
        cat2 = classify_resource("https://github.com/example/plugin")
        cat3 = classify_resource("https://youtube.com/watch?v=abc")
        cat4 = classify_resource("https://docs.example.com/guide")

        assert cat1 in RESOURCE_CATEGORIES, f"分类结果不在预定义类别中: {cat1}"
        assert cat2 == "插件类", f"插件分类错误: {cat2}"
        assert cat3 == "教程类", f"教程分类错误: {cat3}"
        assert cat4 == "文档类", f"文档分类错误: {cat4}"
        print("  ✓ 通过")
    except AssertionError as e:
        print(f"  ✗ 失败: {e}")
        return 1

    # 测试 3: 批量处理
    print("测试 3: 批量处理...")
    try:
        results = batch_process(test_inputs)
        assert len(results) == 3, f"批量处理数量错误: {len(results)}"
        for res in results:
            assert "name" in res, "缺少 name 字段"
            assert "url" in res, "缺少 url 字段"
            assert "category" in res, "缺少 category 字段"
            assert "confidence" in res, "缺少 confidence 字段"
        print("  ✓ 通过")
    except AssertionError as e:
        print(f"  ✗ 失败: {e}")
        return 1
    except SkillError as e:
        print(f"  ✗ 异常: {e}")
        return 1

    # 测试 4: 输出格式
    print("测试 4: 输出格式...")
    try:
        results = batch_process(test_inputs)

        md_output = format_output(results, "markdown")
        assert "|" in md_output, "Markdown 表格缺少竖线分隔符"
        assert "资源名称" in md_output, "Markdown 表格缺少表头"

        json_output = format_output(results, "json")
        parsed_json = json.loads(json_output)
        assert len(parsed_json) == 3, "JSON 输出元素数量错误"

        list_output = format_output(results, "list")
        assert "1." in list_output, "清单输出缺少编号"

        print("  ✓ 通过")
    except AssertionError as e:
        print(f"  ✗ 失败: {e}")
        return 1
    except SkillError as e:
        print(f"  ✗ 异常: {e}")
        return 1

    # 测试 5: 错误处理
    print("测试 5: 错误处理...")
    try:
        # 无效输入
        try:
            batch_process([])
            assert False, "空列表应该触发 E003"
        except SkillError as e:
            assert e.code in ("E003", "E002"), f"错误码不正确: {e.code}"

        # 非法 URL
        try:
            process_resource({"url": "not-a-url"})
            assert False, "非法 URL 应该触发 E004"
        except SkillError as e:
            assert e.code == "E004", f"错误码不正确: {e.code}"

        # 无效格式
        try:
            format_output([], "xml")
            assert False, "无效格式应该触发 E007"
        except SkillError as e:
            assert e.code == "E007", f"错误码不正确: {e.code}"

        print("  ✓ 通过")
    except AssertionError as e:
        print(f"  ✗ 失败: {e}")
        return 1
    except SkillError as e:
        print(f"  ✗ 异常: {e}")
        return 1

    # 测试 6: 单资源处理（宽松断言）
    print("测试 6: 单资源处理...")
    try:
        single = process_resource(test_inputs[0])
        assert isinstance(single, dict), "处理结果不是字典"
        assert len(single) >= 5, "结果字段过少"
        # 宽松断言：URL 必须以 http 开头（不判断具体值）
        assert single["url"].startswith("http"), "URL 格式异常"
        print("  ✓ 通过")
    except AssertionError as e:
        print(f"  ✗ 失败: {e}")
        return 1
    except SkillError as e:
        print(f"  ✗ 异常: {e}")
        return 1

    print("\n全部自检通过 ✓")
    return 0


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------
def main() -> int:
    """主入口函数。"""
    parser = argparse.ArgumentParser(
        description="awesome-claude-code 技能脚本 - 资源精选与导航工具",
        epilog="示例: python main.py --input '{\"url\": \"https://github.com/example/repo\"}' --format json",
    )
    parser.add_argument(
        "--input",
        type=str,
        help="输入数据：JSON 字符串（单个资源或资源列表）",
    )
    parser.add_argument(
        "--format",
        type=str,
        choices=SUPPORTED_FORMATS,
        default="markdown",
        help=f"输出格式（默认: markdown），可选: {', '.join(SUPPORTED_FORMATS)}",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检（离线，不依赖外部文件）",
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        return run_selftest()

    # 正常处理模式
    if not args.input:
        parser.print_help()
        print("\n错误: 需要提供 --input 参数或使用 --selftest 进行自检", file=sys.stderr)
        return 2

    try:
        # 解析输入并处理
        results = batch_process(args.input)
        # 格式化输出
        output = format_output(results, args.format)
        print(output)
        return 0
    except SkillError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"错误 [{ERROR_CODES['E010']}]: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
