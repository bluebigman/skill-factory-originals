#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
awesome-copilot-agents: 智能体资源导航 · 清单整理与归档 Skill
Version: 1.0.2
License: MIT
Copyright (c) 2026 SkillForge Lab

独立实现脚本，仅依据功能规格编写（clean-room）。
"""

import argparse
import json
import re
import sys
from typing import Any, Dict, List, Optional, Tuple

# ============================================================
# 常量定义
# ============================================================
MAX_RESOURCES = 200          # 单次处理上限
MAX_DESC_LENGTH = 200        # 简介长度上限
ERROR_PREFIX = "E"           # 错误码前缀

# 错误码
ERR_INVALID_INPUT = "E001"   # 输入无效或为空
ERR_TOO_MANY = "E002"        # 超过处理上限
ERR_URL_MISSING = "E003"     # 缺少有效URL
ERR_BAD_FORMAT = "E004"      # 输出格式不支持
ERR_DESC_TOO_LONG = "E005"   # 简介超长
ERR_DUP_DETECT = "E006"      # 重复条目处理异常
ERR_GITHUB_LINK = "E007"     # GitHub链接解析失败
ERR_JSON_SERIALIZE = "E008"  # JSON序列化失败
ERR_FILE_IO = "E009"         # 文件读写失败
ERR_INTERNAL = "E010"        # 内部未知错误

# 资源类型关键词映射（用于自动归类）
TYPE_KEYWORDS: Dict[str, List[str]] = {
    "agent": ["agent", "assistant", "copilot", "bot"],
    "framework": ["framework", "sdk", "library", "api"],
    "tool": ["tool", "cli", "utility", "plugin"],
    "dataset": ["dataset", "data", "corpus"],
    "tutorial": ["tutorial", "guide", "docs", "documentation"],
}

# 输出格式
FORMAT_MARKDOWN = "markdown"
FORMAT_JSON = "json"


# ============================================================
# 工具函数
# ============================================================
def _normalize_url(url: str) -> str:
    """标准化URL：去除首尾空格，忽略末尾斜杠（用于重复判定）。"""
    if not url:
        return ""
    url = url.strip()
    # 忽略末尾斜杠（保留协议后的双斜杠）
    if url.endswith("/") and not url.endswith("//"):
        url = url[:-1]
    return url


def _is_github_url(url: str) -> bool:
    """判断是否为GitHub链接。"""
    if not url:
        return False
    pattern = re.compile(r"^https?://(www\.)?github\.com/", re.IGNORECASE)
    return bool(pattern.match(url.strip()))


def _extract_urls(text: str) -> List[str]:
    """从文本中提取所有URL。"""
    if not text:
        return []
    # 匹配 http/https 链接
    pattern = re.compile(r"https?://[^\s<>\"']+")
    return pattern.findall(text)


def _truncate_desc(desc: str) -> Tuple[str, bool]:
    """截断简介，返回(截断后文本, 是否被截断)。"""
    if not desc:
        return "", False
    desc = desc.strip()
    if len(desc) > MAX_DESC_LENGTH:
        return desc[:MAX_DESC_LENGTH], True
    return desc, False


def _guess_type(name: str, desc: str) -> str:
    """根据名称和简介猜测资源类型。"""
    combined = f"{name} {desc}".lower()
    for type_name, keywords in TYPE_KEYWORDS.items():
        for kw in keywords:
            if kw in combined:
                return type_name
    return "uncategorized"


def _deduplicate(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """基于URL完全匹配去重（忽略末尾斜杠）。"""
    seen = set()
    result = []
    for item in items:
        url = _normalize_url(item.get("url", ""))
        if not url or url in seen:
            continue
        seen.add(url)
        result.append(item)
    return result


def _format_markdown(items: List[Dict[str, Any]]) -> str:
    """生成Markdown表格。"""
    if not items:
        return "（无资源条目）"

    lines = ["| 序号 | 名称 | 链接 | 简介 | 类型 |", "|------|------|------|------|------|"]
    for idx, item in enumerate(items, start=1):
        name = item.get("name", "[需核实:名称]")
        url = item.get("url", "")
        desc = item.get("desc", "")
        type_name = item.get("type", "uncategorized")
        lines.append(f"| {idx} | {name} | {url} | {desc} | {type_name} |")
    return "\n".join(lines)


def _format_json(items: List[Dict[str, Any]]) -> str:
    """生成JSON字符串。"""
    try:
        return json.dumps(items, ensure_ascii=False, indent=2)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{ERROR_PREFIX}{ERR_JSON_SERIALIZE}: JSON序列化失败: {exc}")


# ============================================================
# 核心处理逻辑
# ============================================================
def process_input(
    text: str,
    output_format: str = FORMAT_MARKDOWN,
) -> str:
    """
    处理输入文本，提取GitHub资源并输出结构化清单。

    参数:
        text: 包含URL或GitHub链接的文本
        output_format: 输出格式（markdown/json）

    返回:
        格式化后的清单字符串

    异常:
        ValueError: 带错误码的错误信息
    """
    try:
        # 1. 输入校验
        if not text or not text.strip():
            raise ValueError(f"{ERROR_PREFIX}{ERR_INVALID_INPUT}: 输入为空")

        # 2. 提取URL
        urls = _extract_urls(text)
        if not urls:
            raise ValueError(f"{ERROR_PREFIX}{ERR_URL_MISSING}: 未找到任何URL")

        # 3. 过滤GitHub链接
        github_urls = [u for u in urls if _is_github_url(u)]
        if not github_urls:
            raise ValueError(f"{ERROR_PREFIX}{ERR_GITHUB_LINK}: 未找到GitHub链接")

        # 4. 数量限制检查
        if len(github_urls) > MAX_RESOURCES:
            raise ValueError(
                f"{ERROR_PREFIX}{ERR_TOO_MANY}: 资源数量 {len(github_urls)} 超过上限 {MAX_RESOURCES}"
            )

        # 5. 构建资源条目
        items: List[Dict[str, Any]] = []
        for url in github_urls:
            # 尝试从URL中提取名称（取最后一段路径）
            path_part = url.rstrip("/").split("/")[-1] if "/" in url else ""
            name = path_part if path_part and path_part != "github.com" else "[需核实:名称]"

            # 从输入文本中尝试提取简介（简化处理：取URL前后的短文本）
            desc = ""
            # 此处简化：不自动生成简介，标注占位符
            desc = "[需核实:简介]"

            items.append({
                "name": name,
                "url": _normalize_url(url),
                "desc": desc,
                "type": _guess_type(name, desc),
            })

        # 6. 去重
        items = _deduplicate(items)

        # 7. 格式化输出
        if output_format == FORMAT_JSON:
            return _format_json(items)
        elif output_format == FORMAT_MARKDOWN:
            return _format_markdown(items)
        else:
            raise ValueError(f"{ERROR_PREFIX}{ERR_BAD_FORMAT}: 不支持的输出格式: {output_format}")

    except ValueError as exc:
        # 已带错误码，直接抛出
        raise
    except Exception as exc:
        # 未知错误包装为E010
        raise ValueError(f"{ERROR_PREFIX}{ERR_INTERNAL}: 内部错误: {exc}")


# ============================================================
# 自检模块（--selftest）
# ============================================================
def _run_selftest() -> int:
    """内置硬编码样例数据离线自检核心逻辑。"""
    print("=== 自检开始 ===")
    failures = 0

    # ---- 测试1: 基本GitHub链接提取与格式化 ----
    print("测试1: 基本GitHub链接提取")
    try:
        sample = (
            "推荐几个好用的GitHub项目：\n"
            "https://github.com/openai/codex\n"
            "https://github.com/microsoft/copilot-docs\n"
            "https://github.com/example/awesome-agents"
        )
        result = process_input(sample, FORMAT_MARKDOWN)
        # 宽松断言：结果包含三个URL
        assert "openai/codex" in result, "缺少第一个GitHub链接"
        assert "microsoft/copilot-docs" in result, "缺少第二个GitHub链接"
        assert "example/awesome-agents" in result, "缺少第三个GitHub链接"
        # 表格应有表头
        assert "| 序号 |" in result, "缺少表格表头"
        print("  PASS")
    except AssertionError as exc:
        print(f"  FAIL: {exc}")
        failures += 1
    except Exception as exc:
        print(f"  FAIL: 异常 {exc}")
        failures += 1

    # ---- 测试2: JSON格式输出 ----
    print("测试2: JSON格式输出")
    try:
        sample = "https://github.com/test/repo-one"
        result = process_input(sample, FORMAT_JSON)
        parsed = json.loads(result)
        assert isinstance(parsed, list), "JSON输出应为列表"
        assert len(parsed) >= 1, "应至少有一条记录"
        assert "url" in parsed[0], "记录应包含url字段"
        print("  PASS")
    except AssertionError as exc:
        print(f"  FAIL: {exc}")
        failures += 1
    except Exception as exc:
        print(f"  FAIL: 异常 {exc}")
        failures += 1

    # ---- 测试3: 去重功能 ----
    print("测试3: URL去重")
    try:
        sample = (
            "https://github.com/same/repo\n"
            "https://github.com/same/repo/\n"  # 末尾斜杠应视为重复
            "https://github.com/different/repo"
        )
        items = []
        for url in _extract_urls(sample):
            if _is_github_url(url):
                items.append({
                    "name": url.split("/")[-1],
                    "url": _normalize_url(url),
                    "desc": "",
                    "type": "uncategorized",
                })
        deduped = _deduplicate(items)
        # 宽松断言：去重后数量小于等于去重前，且至少1条
        assert len(deduped) <= len(items), "去重后不应比原数量多"
        assert len(deduped) >= 1, "至少保留一条"
        # 验证没有完全相同的URL
        urls = [i["url"] for i in deduped]
        assert len(urls) == len(set(urls)), "不应有重复URL"
        print("  PASS")
    except AssertionError as exc:
        print(f"  FAIL: {exc}")
        failures += 1
    except Exception as exc:
        print(f"  FAIL: 异常 {exc}")
        failures += 1

    # ---- 测试4: 错误处理 ----
    print("测试4: 错误处理")
    try:
        # 空输入
        try:
            process_input("")
            raise AssertionError("空输入应抛出异常")
        except ValueError as exc:
            assert str(exc).startswith(f"{ERROR_PREFIX}{ERR_INVALID_INPUT}"), f"错误码不匹配: {exc}"

        # 非GitHub链接
        try:
            process_input("https://gitlab.com/example/project")
            raise AssertionError("非GitHub链接应抛出异常")
        except ValueError as exc:
            assert str(exc).startswith(f"{ERROR_PREFIX}{ERR_GITHUB_LINK}"), f"错误码不匹配: {exc}"

        # 不支持的格式
        try:
            process_input("https://github.com/test/repo", output_format="xml")
            raise AssertionError("不支持的格式应抛出异常")
        except ValueError as exc:
            assert str(exc).startswith(f"{ERROR_PREFIX}{ERR_BAD_FORMAT}"), f"错误码不匹配: {exc}"

        print("  PASS")
    except AssertionError as exc:
        print(f"  FAIL: {exc}")
        failures += 1
    except Exception as exc:
        print(f"  FAIL: 异常 {exc}")
        failures += 1

    # ---- 测试5: 简介截断 ----
    print("测试5: 简介截断")
    try:
        long_desc = "长" * 300
        truncated, was_truncated = _truncate_desc(long_desc)
        assert was_truncated, "超长简介应标记为截断"
        assert len(truncated) <= MAX_DESC_LENGTH, "截断后长度不应超过上限"
        print("  PASS")
    except AssertionError as exc:
        print(f"  FAIL: {exc}")
        failures += 1
    except Exception as exc:
        print(f"  FAIL: 异常 {exc}")
        failures += 1

    # ---- 测试6: 类型猜测 ----
    print("测试6: 类型猜测")
    try:
        type1 = _guess_type("copilot-agent", "AI assistant")
        assert type1 == "agent", f"应识别为agent，实际为: {type1}"
        type2 = _guess_type("some-framework", "SDK library")
        assert type2 == "framework", f"应识别为framework，实际为: {type2}"
        type3 = _guess_type("unknown-project", "nothing relevant")
        assert type3 == "uncategorized", f"应识别为uncategorized，实际为: {type3}"
        print("  PASS")
    except AssertionError as exc:
        print(f"  FAIL: {exc}")
        failures += 1
    except Exception as exc:
        print(f"  FAIL: 异常 {exc}")
        failures += 1

    # ---- 测试7: 数量上限 ----
    print("测试7: 数量上限")
    try:
        many_urls = "\n".join(f"https://github.com/test/repo{i}" for i in range(MAX_RESOURCES + 1))
        try:
            process_input(many_urls)
            raise AssertionError("超过上限应抛出异常")
        except ValueError as exc:
            assert str(exc).startswith(f"{ERROR_PREFIX}{ERR_TOO_MANY}"), f"错误码不匹配: {exc}"
        print("  PASS")
    except AssertionError as exc:
        print(f"  FAIL: {exc}")
        failures += 1
    except Exception as exc:
        print(f"  FAIL: 异常 {exc}")
        failures += 1

    # ---- 汇总 ----
    print("=== 自检结束 ===")
    if failures:
        print(f"结果: {failures} 项失败")
        return 1
    else:
        print("结果: 全部通过")
        return 0


# ============================================================
# 命令行入口
# ============================================================
def main() -> int:
    """主函数。"""
    parser = argparse.ArgumentParser(
        description="智能体资源导航 · 清单整理与归档 Skill",
        epilog="示例: python main.py 'https://github.com/openai/codex' --format json",
    )
    parser.add_argument(
        "input",
        nargs="?",
        default=None,
        help="包含GitHub链接的文本或URL（至少一个）",
    )
    parser.add_argument(
        "--format",
        choices=[FORMAT_MARKDOWN, FORMAT_JSON],
        default=FORMAT_MARKDOWN,
        help="输出格式，默认为markdown",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检（离线，无需外部输入）",
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        return _run_selftest()

    # 正常处理模式
    if not args.input:
        parser.print_help()
        return 0

    try:
        result = process_input(args.input, args.format)
        print(result)
        return 0
    except ValueError as exc:
        print(f"错误: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"错误: {ERROR_PREFIX}{ERR_INTERNAL}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
