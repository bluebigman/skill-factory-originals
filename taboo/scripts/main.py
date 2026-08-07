#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
taboo - 浏览器标签页管理工具（独立实现版）

本脚本根据功能规格独立编写，不依赖任何既有代码。
提供核心的标签页整理、去重、分组、统计功能。
"""

import argparse
import sys
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse


# ============================================================
# 错误码定义
# ============================================================
ERROR_CODES = {
    "E001": "输入为空，请提供待处理的内容",
    "E002": "关键信息缺失，请补充必要字段",
    "E003": "输入格式错误，请检查数据格式",
    "E004": "超出能力边界，无法处理该请求",
    "E005": "置信度过低，结果无法确定",
    "E006": "URL格式无效",
    "E007": "标签页数据不完整",
    "E008": "分组操作失败",
    "E009": "统计计算异常",
    "E010": "未知错误",
}


def get_error_message(code: str) -> str:
    """获取错误码对应的错误信息"""
    return ERROR_CODES.get(code, ERROR_CODES["E010"])


# ============================================================
# 数据模型
# ============================================================
class TabInfo:
    """标签页信息类"""

    def __init__(self, title: str, url: str, group: str = "默认"):
        self.title = title
        self.url = url
        self.group = group
        self.domain = self._extract_domain(url)

    @staticmethod
    def _extract_domain(url: str) -> str:
        """从URL中提取域名"""
        try:
            parsed = urlparse(url)
            if parsed.netloc:
                return parsed.netloc
            return ""
        except Exception:
            return ""

    def is_valid(self) -> bool:
        """检查标签页信息是否有效"""
        return bool(self.title and self.url and self.domain)

    def to_dict(self) -> Dict:
        """转换为字典格式"""
        return {
            "title": self.title,
            "url": self.url,
            "group": self.group,
            "domain": self.domain,
        }


# ============================================================
# 核心功能模块
# ============================================================
class TabManager:
    """标签页管理器"""

    def __init__(self):
        self.tabs: List[TabInfo] = []

    def add_tab(self, title: str, url: str, group: str = "默认") -> Optional[str]:
        """
        添加标签页
        返回错误码或None（成功）
        """
        if not title or not url:
            return "E001"
        if not self._is_valid_url(url):
            return "E006"

        tab = TabInfo(title, url, group)
        if not tab.is_valid():
            return "E007"

        self.tabs.append(tab)
        return None

    @staticmethod
    def _is_valid_url(url: str) -> bool:
        """验证URL格式"""
        try:
            parsed = urlparse(url)
            return bool(parsed.scheme and parsed.netloc)
        except Exception:
            return False

    def remove_duplicates(self) -> Tuple[int, int]:
        """
        去除重复标签页（基于URL）
        返回 (原有数量, 去重后数量)
        """
        original_count = len(self.tabs)
        seen = set()
        unique_tabs = []
        for tab in self.tabs:
            if tab.url not in seen:
                seen.add(tab.url)
                unique_tabs.append(tab)
        self.tabs = unique_tabs
        return original_count, len(self.tabs)

    def group_by_domain(self) -> Dict[str, List[TabInfo]]:
        """按域名分组标签页"""
        groups = {}
        for tab in self.tabs:
            if tab.domain not in groups:
                groups[tab.domain] = []
            groups[tab.domain].append(tab)
        return groups

    def group_by_custom(self, group_name: str) -> Dict[str, List[TabInfo]]:
        """按自定义分组标签页"""
        if not group_name:
            return {}

        groups = {}
        for tab in self.tabs:
            if tab.group == group_name:
                if group_name not in groups:
                    groups[group_name] = []
                groups[group_name].append(tab)
        return groups

    def get_statistics(self) -> Dict:
        """获取统计信息"""
        total = len(self.tabs)
        if total == 0:
            return {"total": 0, "unique_domains": 0, "groups": {}}

        domains = set(tab.domain for tab in self.tabs)
        group_counts = {}
        for tab in self.tabs:
            if tab.group not in group_counts:
                group_counts[tab.group] = 0
            group_counts[tab.group] += 1

        return {
            "total": total,
            "unique_domains": len(domains),
            "groups": group_counts,
        }

    def get_confidence_score(self) -> float:
        """
        计算处理结果的置信度
        基于数据完整性和有效性
        """
        if not self.tabs:
            return 0.0

        valid_count = sum(1 for tab in self.tabs if tab.is_valid())
        return valid_count / len(self.tabs) * 100

    def format_output(self) -> str:
        """格式化输出结果"""
        if not self.tabs:
            return "没有可处理的标签页数据"

        confidence = self.get_confidence_score()
        lines = [f"处理结果（置信度: {confidence:.1f}%）"]

        if confidence < 85:
            lines.append("[需核实] 部分数据可能不完整，请人工复核")
        elif confidence < 90:
            lines.append("建议复核")

        groups = self.group_by_domain()
        for domain, tabs in sorted(groups.items()):
            lines.append(f"\n📁 {domain} ({len(tabs)}个标签页)")
            for tab in tabs[:5]:  # 每个域名最多显示5个
                lines.append(f"  - {tab.title}")
            if len(tabs) > 5:
                lines.append(f"  ... 等{len(tabs)}个标签页")

        return "\n".join(lines)


# ============================================================
# 业务处理流程
# ============================================================
def process_tabs(tab_data: List[Dict]) -> Tuple[Optional[str], str]:
    """
    处理标签页数据主流程
    返回 (错误码, 处理结果)
    """
    if not tab_data:
        return "E001", f"E001: {get_error_message('E001')}"

    manager = TabManager()
    for item in tab_data:
        if not isinstance(item, dict):
            return "E003", f"E003: {get_error_message('E003')}"

        title = item.get("title", "")
        url = item.get("url", "")
        group = item.get("group", "默认")

        if not title or not url:
            return "E002", f"E002: {get_error_message('E002')}"

        error = manager.add_tab(title, url, group)
        if error:
            return error, f"{error}: {get_error_message(error)}"

    # 去重处理
    original_count, unique_count = manager.remove_duplicates()

    # 生成结果
    result_parts = [f"去重处理：{original_count} → {unique_count} 个标签页"]
    result_parts.append(manager.format_output())

    return None, "\n".join(result_parts)


# ============================================================
# 自测模块
# ============================================================
def run_selftest() -> bool:
    """
    内置自测逻辑，使用硬编码样例数据
    不依赖外部文件、网络或特定工作目录
    """
    print("开始自测...")

    # 测试数据
    test_data = [
        {"title": "示例网站A", "url": "https://example.com/page1", "group": "工作"},
        {"title": "示例网站B", "url": "https://example.org/page2", "group": "工作"},
        {"title": "示例网站C", "url": "https://example.com/page3", "group": "学习"},
        {"title": "重复示例", "url": "https://example.com/page1", "group": "工作"},
        {"title": "示例网站D", "url": "https://test.net/page4", "group": "学习"},
    ]

    # 测试1: 基本处理流程
    print("\n测试1: 基本处理流程")
    error, result = process_tabs(test_data)
    assert error is None, f"处理失败: {error}"
    assert "去重处理：5 → 4" in result, "去重数量不正确"
    print("✓ 基本处理流程通过")

    # 测试2: 空输入处理
    print("\n测试2: 空输入处理")
    error, result = process_tabs([])
    assert error == "E001", f"空输入应返回E001，实际: {error}"
    assert "E001" in result, "错误信息不包含错误码"
    assert "输入为空" in result, "错误信息不包含具体说明"
    print("✓ 空输入处理通过")

    # 测试3: URL验证
    print("\n测试3: URL验证")
    manager = TabManager()
    error = manager.add_tab("测试", "not-a-url")
    assert error == "E006", f"无效URL应返回E006，实际: {error}"
    print("✓ URL验证通过")

    # 测试4: 统计功能
    print("\n测试4: 统计功能")
    manager = TabManager()
    for item in test_data:
        error = manager.add_tab(item["title"], item["url"], item["group"])
        assert error is None, f"添加标签页失败: {error}"

    manager.remove_duplicates()
    stats = manager.get_statistics()
    assert stats["total"] > 0, "统计总数应为正数"
    assert stats["unique_domains"] > 0, "唯一域名数应为正数"
    assert len(stats["groups"]) > 0, "分组数应为正数"
    print(f"✓ 统计功能通过 (总数: {stats['total']}, 域名数: {stats['unique_domains']})")

    # 测试5: 置信度计算
    print("\n测试5: 置信度计算")
    confidence = manager.get_confidence_score()
    assert 0 < confidence <= 100, f"置信度应在(0, 100]范围内，实际: {confidence}"
    print(f"✓ 置信度计算通过 (置信度: {confidence:.1f}%)")

    # 测试6: 分组功能
    print("\n测试6: 分组功能")
    domain_groups = manager.group_by_domain()
    assert len(domain_groups) > 0, "域名分组应为非空"
    assert len(domain_groups) <= stats["unique_domains"], "分组数不应超过唯一域名数"
    print(f"✓ 分组功能通过 (分组数: {len(domain_groups)})")

    # 测试7: 错误处理
    print("\n测试7: 错误处理")
    error_msg = get_error_message("E999")
    assert error_msg == ERROR_CODES["E010"], "未知错误码应返回E010"
    print("✓ 错误处理通过")

    print("\n✅ 所有自测通过！")
    return True


# ============================================================
# 命令行入口
# ============================================================
def main():
    """命令行主入口"""
    parser = argparse.ArgumentParser(
        description="taboo - 浏览器标签页管理工具",
        epilog="示例: python main.py --selftest"
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自测（无需外部依赖）"
    )
    parser.add_argument(
        "--input",
        type=str,
        help="输入数据文件路径（JSON格式）"
    )
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="输出格式（默认: text）"
    )

    args = parser.parse_args()

    # 自测模式
    if args.selftest:
        success = run_selftest()
        sys.exit(0 if success else 1)

    # 无参数时显示帮助
    if not args.input:
        parser.print_help()
        sys.exit(0)

    # 文件输入模式
    try:
        import json
        with open(args.input, "r", encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, list):
            print(f"错误 E003: {get_error_message('E003')}")
            sys.exit(1)

        error, result = process_tabs(data)
        if error:
            print(f"错误 {result}")
            sys.exit(1)

        if args.format == "json":
            # 输出JSON格式
            import json as json_out
            manager = TabManager()
            for item in data:
                manager.add_tab(item.get("title", ""), item.get("url", ""), item.get("group", "默认"))
            manager.remove_duplicates()
            print(json_out.dumps(manager.get_statistics(), ensure_ascii=False, indent=2))
        else:
            print(result)

    except FileNotFoundError:
        print(f"错误 E001: 文件不存在: {args.input}")
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"错误 E003: 文件不是有效的JSON格式")
        sys.exit(1)
    except Exception as e:
        print(f"错误 E010: {get_error_message('E010')} - {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
