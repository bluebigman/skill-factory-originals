#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py — 插件目录检索 官方源 质量筛选（干净室独立实现）

本脚本仅依据功能规格文档独立编写，不参考任何既有实现。
提供命令行检索与离线自检两种模式。
"""

import argparse
import json
import sys
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional


# ---------------------------------------------------------------------------
# 错误码定义
# ---------------------------------------------------------------------------
class AppError(Exception):
    """应用级错误，携带错误码。"""
    def __init__(self, code: str, message: str):
        super().__init__(f"[{code}] {message}")
        self.code = code
        self.message = message


E_INVALID_ARGS = "E001"   # 命令行参数不合法
E_INPUT_MISSING = "E002"  # 缺少必要输入
E_PLUGIN_NOT_FOUND = "E003"  # 未找到插件
E_FILTER_FAIL = "E004"    # 筛选过程出错
E_RANK_FAIL = "E005"      # 排序过程出错
E_OUTPUT_FAIL = "E006"    # 输出失败
E_SELFTEST_FAIL = "E007"  # 自检失败
E_DATA_CORRUPT = "E008"   # 内置数据损坏
E_UNSUPPORTED = "E009"    # 不支持的操作
E_UNKNOWN = "E010"        # 未知错误


# ---------------------------------------------------------------------------
# 数据结构
# ---------------------------------------------------------------------------
@dataclass
class PluginInfo:
    """插件信息条目。"""
    name: str
    summary: str
    category: str                # 插件类型/分类
    tech_stack: List[str]        # 适用技术栈
    scenarios: List[str]         # 适用场景
    confidence: float = 0.0      # 匹配置信度 0~1
    match_reason: str = ""       # 匹配理由
    missing_fields: List[str] = field(default_factory=list)  # 缺失字段


@dataclass
class SearchResult:
    """检索结果。"""
    query: str
    plugins: List[PluginInfo]
    total_found: int
    message: str = ""


# ---------------------------------------------------------------------------
# 内置官方插件目录（硬编码样例数据）
# 注意：仅用于演示与自检，不代表真实官方目录。
# ---------------------------------------------------------------------------
BUILTIN_PLUGIN_CATALOG = [
    {
        "name": "code-reviewer",
        "summary": "自动进行代码审查，发现潜在问题与改进点。",
        "category": "开发工具",
        "tech_stack": ["Python", "JavaScript", "TypeScript"],
        "scenarios": ["代码质量检查", "团队协作", "CI集成"],
    },
    {
        "name": "doc-generator",
        "summary": "根据源码自动生成项目文档与API说明。",
        "category": "文档工具",
        "tech_stack": ["Python", "Java", "Go"],
        "scenarios": ["文档编写", "项目维护", "API设计"],
    },
    {
        "name": "test-helper",
        "summary": "辅助编写单元测试与集成测试用例。",
        "category": "测试工具",
        "tech_stack": ["Python", "JavaScript"],
        "scenarios": ["单元测试", "集成测试", "覆盖率检查"],
    },
    {
        "name": "deploy-assistant",
        "summary": "协助配置部署流程与自动化发布。",
        "category": "运维工具",
        "tech_stack": ["Docker", "Kubernetes", "Linux"],
        "scenarios": ["持续部署", "容器化", "云原生"],
    },
    {
        "name": "data-analyzer",
        "summary": "数据分析与可视化辅助工具。",
        "category": "数据分析",
        "tech_stack": ["Python", "R", "SQL"],
        "scenarios": ["数据挖掘", "报表生成", "商业智能"],
    },
]


# ---------------------------------------------------------------------------
# 核心检索与筛选逻辑
# ---------------------------------------------------------------------------
def validate_query(query: str) -> str:
    """校验检索关键词。"""
    if not query or not query.strip():
        raise AppError(E_INPUT_MISSING, "检索关键词不能为空")
    return query.strip()


def normalize_text(text: str) -> str:
    """文本归一化：小写、去空白。"""
    return " ".join(text.lower().split())


def calculate_match_score(plugin: Dict, query: str) -> float:
    """
    计算插件与查询的匹配分数（0~1）。
    规则：名称匹配 > 摘要匹配 > 场景匹配 > 技术栈匹配。
    """
    q = normalize_text(query)
    if not q:
        return 0.0

    score = 0.0
    reasons = []

    # 名称匹配（权重最高）
    if q in normalize_text(plugin.get("name", "")):
        score += 0.6
        reasons.append("名称匹配")

    # 摘要匹配
    if q in normalize_text(plugin.get("summary", "")):
        score += 0.3
        reasons.append("摘要匹配")

    # 场景匹配
    for scenario in plugin.get("scenarios", []):
        if q in normalize_text(scenario):
            score += 0.2
            reasons.append(f"场景匹配:{scenario}")
            break

    # 技术栈匹配
    for tech in plugin.get("tech_stack", []):
        if q in normalize_text(tech):
            score += 0.1
            reasons.append(f"技术栈匹配:{tech}")
            break

    # 置信度上限 1.0
    score = min(score, 1.0)
    return score, "; ".join(reasons) if reasons else "关键词匹配"


def search_plugins(query: str, catalog: Optional[List[Dict]] = None) -> SearchResult:
    """
    在插件目录中检索匹配的插件。
    返回结构化结果，包含匹配的插件列表与置信度标注。
    """
    try:
        q = validate_query(query)
        catalog = catalog if catalog is not None else BUILTIN_PLUGIN_CATALOG

        results: List[PluginInfo] = []
        for item in catalog:
            # 字段完整性检查
            missing = [k for k in ("name", "summary", "category") if not item.get(k)]
            if missing:
                plugin_info = PluginInfo(
                    name=item.get("name", "未知"),
                    summary=item.get("summary", ""),
                    category=item.get("category", "未知"),
                    tech_stack=item.get("tech_stack", []),
                    scenarios=item.get("scenarios", []),
                    confidence=0.0,
                    match_reason="字段缺失，无法评估",
                    missing_fields=missing,
                )
                results.append(plugin_info)
                continue

            score, reason = calculate_match_score(item, q)
            if score > 0.0:
                plugin_info = PluginInfo(
                    name=item["name"],
                    summary=item["summary"],
                    category=item["category"],
                    tech_stack=item.get("tech_stack", []),
                    scenarios=item.get("scenarios", []),
                    confidence=round(score, 2),
                    match_reason=reason,
                )
                results.append(plugin_info)

        # 按置信度降序排序
        results.sort(key=lambda p: p.confidence, reverse=True)

        return SearchResult(
            query=q,
            plugins=results,
            total_found=len(results),
            message=f"找到 {len(results)} 个匹配插件" if results else "未找到匹配插件",
        )

    except AppError:
        raise
    except Exception as exc:
        raise AppError(E_FILTER_FAIL, f"检索过程发生错误: {exc}") from exc


def format_output(result: SearchResult) -> str:
    """将检索结果格式化为可读文本。"""
    try:
        lines = [f"检索关键词: {result.query}", f"结果: {result.message}", ""]
        for i, plugin in enumerate(result.plugins, 1):
            lines.append(f"{i}. {plugin.name} (置信度: {plugin.confidence:.0%})")
            lines.append(f"   摘要: {plugin.summary}")
            lines.append(f"   分类: {plugin.category}")
            lines.append(f"   技术栈: {', '.join(plugin.tech_stack) if plugin.tech_stack else '未标注'}")
            lines.append(f"   场景: {', '.join(plugin.scenarios) if plugin.scenarios else '未标注'}")
            lines.append(f"   匹配理由: {plugin.match_reason}")
            if plugin.missing_fields:
                lines.append(f"   缺失字段: {', '.join(plugin.missing_fields)}")
            lines.append("")
        return "\n".join(lines)
    except Exception as exc:
        raise AppError(E_OUTPUT_FAIL, f"输出格式化失败: {exc}") from exc


# ---------------------------------------------------------------------------
# 自检模块（离线、硬编码样例、宽松断言）
# ---------------------------------------------------------------------------
def run_selftest() -> bool:
    """
    离线自检核心逻辑。
    使用内置硬编码数据，不访问外部资源。
    断言采用宽松阈值确保稳定性。
    """
    test_passed = True

    def check(condition: bool, message: str):
        nonlocal test_passed
        if not condition:
            print(f"  ✗ {message}")
            test_passed = False
        else:
            print(f"  ✓ {message}")

    print("开始自检...")

    # 测试1：正常检索
    print("\n[测试1] 正常检索")
    try:
        result = search_plugins("代码")
        check(result.total_found >= 0, "检索不报错")
        check(result.query == "代码", "查询关键词保留")
        # 置信度范围检查（宽松）
        for p in result.plugins:
            check(0.0 <= p.confidence <= 1.0, f"插件 {p.name} 置信度在[0,1]区间")
            check(bool(p.name), f"插件 {p.name} 名称非空")
    except Exception as exc:
        check(False, f"检索异常: {exc}")

    # 测试2：空查询
    print("\n[测试2] 空查询")
    try:
        search_plugins("   ")
        check(False, "空查询应报错")
    except AppError as exc:
        check(exc.code == E_INPUT_MISSING, f"空查询返回错误码 {exc.code}")
    except Exception:
        check(False, "空查询应抛出 AppError")

    # 测试3：无匹配查询
    print("\n[测试3] 无匹配查询")
    try:
        result = search_plugins("不存在的插件xyz")
        check(result.total_found == 0, "无匹配返回空列表")
        check(result.message != "", "无匹配时返回提示信息")
    except Exception as exc:
        check(False, f"无匹配查询异常: {exc}")

    # 测试4：匹配排序
    print("\n[测试4] 匹配排序")
    try:
        result = search_plugins("python")
        confidences = [p.confidence for p in result.plugins]
        # 宽松检查：置信度非递增
        check(all(confidences[i] >= confidences[i+1] for i in range(len(confidences)-1)),
              "插件按置信度降序排列")
    except Exception as exc:
        check(False, f"排序测试异常: {exc}")

    # 测试5：数据完整性
    print("\n[测试5] 数据完整性")
    try:
        check(len(BUILTIN_PLUGIN_CATALOG) >= 3, "内置目录至少3条记录")
        names = [p["name"] for p in BUILTIN_PLUGIN_CATALOG]
        check(len(set(names)) == len(names), "插件名称不重复")
        for p in BUILTIN_PLUGIN_CATALOG:
            check(bool(p.get("summary")), f"插件 {p['name']} 摘要非空")
            check(bool(p.get("category")), f"插件 {p['name']} 分类非空")
    except Exception as exc:
        check(False, f"数据完整性测试异常: {exc}")

    # 测试6：输出格式
    print("\n[测试6] 输出格式")
    try:
        result = search_plugins("测试")
        output = format_output(result)
        check(isinstance(output, str) and len(output) > 0, "输出为非空字符串")
        check("检索关键词" in output, "输出包含检索关键词")
        check("结果" in output, "输出包含结果说明")
    except Exception as exc:
        check(False, f"输出测试异常: {exc}")

    print(f"\n自检{'通过' if test_passed else '失败'}")
    return test_passed


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------
def main(argv: Optional[List[str]] = None) -> int:
    """命令行入口。"""
    parser = argparse.ArgumentParser(
        description="插件目录检索 官方源 质量筛选工具",
        epilog="示例: python main.py --query python --json",
    )
    parser.add_argument("--query", "-q", type=str, help="检索关键词")
    parser.add_argument("--json", action="store_true", help="以JSON格式输出")
    parser.add_argument("--selftest", action="store_true", help="运行离线自检")
    parser.add_argument("--version", action="version", version="claude-plugins-official 1.0.1")

    args = parser.parse_args(argv)

    try:
        # 自检模式
        if args.selftest:
            ok = run_selftest()
            return 0 if ok else 1

        # 检索模式
        if not args.query:
            raise AppError(E_INVALID_ARGS, "请提供 --query 参数（或使用 --selftest 自检）")

        result = search_plugins(args.query)

        if args.json:
            # JSON 输出
            output_data = {
                "query": result.query,
                "total_found": result.total_found,
                "message": result.message,
                "plugins": [asdict(p) for p in result.plugins],
            }
            print(json.dumps(output_data, ensure_ascii=False, indent=2))
        else:
            # 文本输出
            print(format_output(result))

        return 0

    except AppError as exc:
        print(f"错误: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\n用户中断", file=sys.stderr)
        return 130
    except Exception as exc:
        print(f"[{E_UNKNOWN}] 未知错误: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
