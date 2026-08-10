#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py - moltdirectory 技能市场目录检索能力导航

本脚本实现技能市场目录的浏览、检索、详情呈现与批量查询功能。
仅依据功能规格独立实现（clean-room），不复制任何既有代码。

功能范围：
  - 技能目录浏览（按分类或关键词组织）
  - 技能信息检索（按名称、关键词或描述定位）
  - 技能详情呈现（元信息输出）
  - 结构化结果输出（统一字段结构）
  - 批量查询支持（一次请求多个技能）

错误码约定：
  E001 - 参数解析失败
  E002 - 未知命令
  E003 - 缺少必要参数
  E004 - 查询关键词为空
  E005 - 未找到匹配技能
  E006 - 批量查询无有效输入
  E007 - 内部数据异常
  E008 - 输出格式错误
  E009 - 自检失败
  E010 - 未知运行时错误
"""

import argparse
import json
import sys
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# 内置技能目录数据（离线快照）
# 注意：此数据为硬编码样例，仅用于演示与自检。
#       实际使用中可由外部数据源替换（本脚本不负责同步远端）。
# ---------------------------------------------------------------------------
SKILL_CATALOG: List[Dict[str, Any]] = [
    {
        "id": "skill-001",
        "name": "moltdirectory",
        "display_name": "技能市场 目录检索 能力导航",
        "version": "1.0.1",
        "description": "浏览并检索 MoltBot 技能市场，快速定位可用技能与能力说明。",
        "category": "导航检索",
        "trigger_words": ["moltdirectory", "技能市场", "技能目录", "能力导航", "技能检索"],
        "dependencies": [],
        "license": "MIT",
        "author": "SkillForge Studio",
        "capabilities": ["目录浏览", "信息检索", "详情呈现", "结构化输出", "批量查询"],
    },
    {
        "id": "skill-002",
        "name": "websearch",
        "display_name": "网络搜索 信息获取",
        "version": "0.9.3",
        "description": "执行网络搜索并返回结果摘要，支持多引擎切换。",
        "category": "信息获取",
        "trigger_words": ["搜索", "网络", "信息获取", "websearch"],
        "dependencies": ["requests"],
        "license": "MIT",
        "author": "Community",
        "capabilities": ["搜索", "摘要生成", "多引擎"],
    },
    {
        "id": "skill-003",
        "name": "codeformatter",
        "display_name": "代码格式化 美化工具",
        "version": "2.1.0",
        "description": "对多种编程语言代码进行格式化与风格统一。",
        "category": "开发工具",
        "trigger_words": ["格式化", "美化", "代码风格", "codeformatter"],
        "dependencies": ["black", "prettier"],
        "license": "Apache-2.0",
        "author": "DevTeam",
        "capabilities": ["格式化", "风格检查", "多语言"],
    },
    {
        "id": "skill-004",
        "name": "dataviz",
        "display_name": "数据可视化 图表生成",
        "version": "3.2.1",
        "description": "根据结构化数据生成各类图表，支持导出图片与交互式视图。",
        "category": "数据分析",
        "trigger_words": ["图表", "可视化", "绘图", "dataviz"],
        "dependencies": ["matplotlib", "plotly"],
        "license": "BSD-3-Clause",
        "author": "DataLab",
        "capabilities": ["图表生成", "交互视图", "导出"],
    },
    {
        "id": "skill-005",
        "name": "textsummarizer",
        "display_name": "文本摘要 内容提炼",
        "version": "1.4.0",
        "description": "对长文本进行自动摘要，提取关键信息与要点。",
        "category": "文本处理",
        "trigger_words": ["摘要", "提炼", "总结", "textsummarizer"],
        "dependencies": ["transformers"],
        "license": "MIT",
        "author": "NLPGroup",
        "capabilities": ["摘要", "关键词提取", "要点归纳"],
    },
]


# ---------------------------------------------------------------------------
# 核心逻辑：目录检索与信息呈现
# ---------------------------------------------------------------------------

def _normalize_text(text: str) -> str:
    """将文本统一转为小写并去除首尾空白，用于模糊匹配。"""
    return text.strip().lower()


def _skill_matches_keyword(skill: Dict[str, Any], keyword: str) -> bool:
    """
    判断技能是否与关键词匹配。
    匹配范围：名称、显示名、描述、分类、触发词、能力列表。
    使用宽松子串匹配（不区分大小写）。
    """
    kw = _normalize_text(keyword)
    if not kw:
        return False

    # 收集所有可搜索字段
    searchable_fields = [
        skill.get("name", ""),
        skill.get("display_name", ""),
        skill.get("description", ""),
        skill.get("category", ""),
        skill.get("author", ""),
    ]
    # 列表字段逐项加入
    for list_field in ("trigger_words", "dependencies", "capabilities"):
        searchable_fields.extend(skill.get(list_field, []))

    # 宽松匹配：任一字段包含关键词即视为匹配
    for field in searchable_fields:
        if kw in _normalize_text(str(field)):
            return True
    return False


def list_skills(category: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    技能目录浏览。
    按分类过滤（可选），返回技能列表（不含详情字段，仅基本信息）。
    """
    if category:
        cat = _normalize_text(category)
        result = [s for s in SKILL_CATALOG if _normalize_text(s.get("category", "")) == cat]
    else:
        result = list(SKILL_CATALOG)

    # 返回精简信息（不含完整描述与依赖等）
    return [
        {
            "id": s["id"],
            "name": s["name"],
            "display_name": s["display_name"],
            "version": s["version"],
            "category": s["category"],
            "trigger_words": s.get("trigger_words", []),
        }
        for s in result
    ]


def search_skills(keyword: str) -> List[Dict[str, Any]]:
    """
    技能信息检索。
    根据关键词在名称、描述、触发词等字段中查找匹配技能。
    返回完整技能信息列表。
    """
    kw = _normalize_text(keyword)
    if not kw:
        raise ValueError("E004: 查询关键词为空")

    matched = [s for s in SKILL_CATALOG if _skill_matches_keyword(s, kw)]
    if not matched:
        # 返回空列表而非异常，由调用方决定处理方式
        return []
    return matched


def get_skill_detail(skill_id: str) -> Optional[Dict[str, Any]]:
    """技能详情呈现。根据技能ID返回完整元信息，不存在时返回 None。"""
    for skill in SKILL_CATALOG:
        if skill.get("id") == skill_id:
            # 返回深拷贝，避免外部修改内部数据
            return json.loads(json.dumps(skill))
    return None


def batch_query(queries: List[str]) -> Dict[str, List[Dict[str, Any]]]:
    """
    批量查询支持。
    输入多个关键词（或技能ID），返回多条目结果集。
    结果按查询词分组。
    """
    results: Dict[str, List[Dict[str, Any]]] = {}
    for q in queries:
        q_str = str(q).strip()
        if not q_str:
            continue
        # 先尝试按ID精确匹配，再退化为关键词搜索
        detail = get_skill_detail(q_str)
        if detail:
            results[q_str] = [detail]
        else:
            matches = search_skills(q_str)
            if matches:
                results[q_str] = matches
            else:
                results[q_str] = []
    return results


def format_output(data: Any, output_format: str = "json") -> str:
    """
    结构化结果输出。
    支持 json 与 text 两种格式。
    """
    if output_format == "json":
        return json.dumps(data, ensure_ascii=False, indent=2)
    elif output_format == "text":
        # 文本格式：简单呈现
        lines: List[str] = []
        if isinstance(data, list):
            for item in data:
                lines.append(f"[{item.get('id', '?')}] {item.get('name', '?')} "
                             f"(v{item.get('version', '?')}) - {item.get('display_name', '?')}")
        elif isinstance(data, dict):
            # 处理批量查询结果
            for key, items in data.items():
                lines.append(f"查询: {key}")
                for item in items:
                    lines.append(f"  [{item.get('id', '?')}] {item.get('name', '?')} "
                                 f"(v{item.get('version', '?')})")
        else:
            lines.append(str(data))
        return "\n".join(lines)
    else:
        raise ValueError(f"E008: 不支持的输出格式: {output_format}")


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    """构建命令行参数解析器。"""
    parser = argparse.ArgumentParser(
        prog="moltdirectory",
        description="技能市场目录检索能力导航",
        epilog="示例: main.py list --category 导航检索 | main.py search --keyword 搜索 | main.py detail --id skill-001",
    )
    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # list 命令
    list_parser = subparsers.add_parser("list", help="浏览技能目录")
    list_parser.add_argument("--category", type=str, default=None, help="按分类过滤")

    # search 命令
    search_parser = subparsers.add_parser("search", help="检索技能")
    search_parser.add_argument("--keyword", type=str, required=False, help="搜索关键词")

    # detail 命令
    detail_parser = subparsers.add_parser("detail", help="查看技能详情")
    detail_parser.add_argument("--id", type=str, required=False, help="技能ID")

    # batch 命令
    batch_parser = subparsers.add_parser("batch", help="批量查询")
    batch_parser.add_argument("--queries", type=str, nargs="+", required=False, help="多个查询词或ID")

    # 全局输出格式选项
    parser.add_argument("--format", type=str, choices=["json", "text"], default="json",
                        help="输出格式（默认 json）")

    # 自检参数
    parser.add_argument("--selftest", action="store_true", help="运行内置自检")

    return parser


def run_command(args: argparse.Namespace) -> int:
    """执行具体命令，返回进程退出码。"""
    try:
        if args.command == "list":
            data = list_skills(args.category)
            print(format_output(data, args.format))
        elif args.command == "search":
            if not args.keyword.strip():
                raise ValueError("E004: 查询关键词为空")
            data = search_skills(args.keyword)
            if not data:
                print(f"E005: 未找到与 '{args.keyword}' 匹配的技能")
                return 5  # 返回非零退出码表示未找到
            print(format_output(data, args.format))
        elif args.command == "detail":
            data = get_skill_detail(args.id)
            if data is None:
                print(f"E005: 未找到ID为 '{args.id}' 的技能")
                return 5
            print(format_output(data, args.format))
        elif args.command == "batch":
            if not args.queries:
                raise ValueError("E006: 批量查询无有效输入")
            data = batch_query(args.queries)
            # 过滤空结果
            non_empty = {k: v for k, v in data.items() if v}
            if not non_empty:
                print("E006: 批量查询无有效结果")
                return 5
            print(format_output(non_empty, args.format))
        else:
            raise ValueError(f"E002: 未知命令: {args.command}")
        return 0
    except ValueError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"E010: 运行时错误: {e}", file=sys.stderr)
        return 10


# ---------------------------------------------------------------------------
# 自检逻辑（离线，使用内置硬编码样例数据）
# ---------------------------------------------------------------------------

def run_selftest() -> int:
    """
    内置自检。使用硬编码样例数据验证核心逻辑。
    不读取外部文件、不依赖当前工作目录、不访问网络。
    断言使用宽松阈值（大小比较/区间判断），避免精确值依赖。
    """
    try:
        # 1. 目录浏览测试
        all_skills = list_skills()
        assert len(all_skills) >= 3, "目录浏览应返回至少3个技能"

        # 按分类过滤
        nav_skills = list_skills("导航检索")
        assert len(nav_skills) >= 1, "导航检索分类应至少包含1个技能"
        assert nav_skills[0]["name"] == "moltdirectory", "分类过滤结果应包含 moltdirectory"

        # 不存在的分类应返回空
        empty_cat = list_skills("不存在的分类xyz")
        assert len(empty_cat) == 0, "不存在的分类应返回空列表"

        # 2. 关键词检索测试
        # 用宽松匹配：搜索"技能"应至少匹配1个
        search_results = search_skills("技能")
        assert len(search_results) >= 1, "关键词'技能'应至少匹配1个技能"

        # 搜索具体名称
        mdir_results = search_skills("moltdirectory")
        assert len(mdir_results) >= 1, "关键词'moltdirectory'应匹配到技能"
        assert mdir_results[0]["name"] == "moltdirectory", "应匹配到 moltdirectory 技能"

        # 搜索不存在的关键词应返回空
        no_results = search_skills("完全不存在的关键词xyz")
        assert len(no_results) == 0, "不存在的关键词应返回空列表"

        # 3. 详情获取测试
        detail = get_skill_detail("skill-001")
        assert detail is not None, "skill-001 的详情应存在"
        assert detail["name"] == "moltdirectory", "skill-001 名称应为 moltdirectory"
        assert "version" in detail, "详情应包含版本信息"
        assert len(detail.get("trigger_words", [])) >= 3, "触发词列表应至少3个"

        # 不存在的ID应返回 None
        no_detail = get_skill_detail("skill-999")
        assert no_detail is None, "不存在的ID应返回 None"

        # 4. 批量查询测试
        batch_results = batch_query(["moltdirectory", "skill-002", "不存在xyz"])
        assert "moltdirectory" in batch_results, "批量查询应包含 moltdirectory 键"
        assert "skill-002" in batch_results, "批量查询应包含 skill-002 键"
        assert "不存在xyz" in batch_results, "批量查询应包含不存在的键（空列表）"
        assert len(batch_results["moltdirectory"]) >= 1, "moltdirectory 查询应有结果"
        assert len(batch_results["skill-002"]) >= 1, "skill-002 查询应有结果"
        assert len(batch_results["不存在xyz"]) == 0, "不存在的查询应返回空列表"

        # 5. 输出格式测试
        json_out = format_output(all_skills, "json")
        assert json_out.startswith("["), "JSON输出应以[开头"
        parsed = json.loads(json_out)
        assert isinstance(parsed, list), "JSON输出应可解析为列表"

        text_out = format_output(all_skills, "text")
        assert len(text_out) > 0, "文本输出不应为空"

        # 6. 字段完整性检查（对每个技能）
        for skill in SKILL_CATALOG:
            required_fields = ["id", "name", "display_name", "version",
                               "description", "category", "trigger_words", "license"]
            for field in required_fields:
                assert field in skill, f"技能 {skill.get('id', '?')} 缺少字段 {field}"

        print("自检通过: 所有核心逻辑验证成功")
        return 0
    except AssertionError as e:
        print(f"E009: 自检失败 - {e}", file=sys.stderr)
        return 9
    except Exception as e:
        print(f"E009: 自检异常 - {e}", file=sys.stderr)
        return 9


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------

def main() -> int:
    """主函数。解析参数并执行相应操作。"""
    parser = build_parser()
    try:
        parser.add_argument("--verbose", action="store_true", help="显示修改明细")  # R6 可解释输出
        args = parser.parse_args()
    except SystemExit as e:
        # argparse 在 -h 或错误参数时退出
        if e.code == 0:
            return 0
        print(f"E001: 参数解析失败", file=sys.stderr)
        return 1

    # 自检模式
    if args.selftest:
        if args.command is not None:
            print("E003: --selftest 不能与其他命令同时使用", file=sys.stderr)
            return 3
        return run_selftest()

    # 无命令时显示帮助
    if args.command is None:
        parser.print_help()
        return 0

    return run_command(args)


if __name__ == "__main__":
    sys.exit(main())
