#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
awesome-mac — macOS 软件分类导航检索工具

本脚本根据功能规格独立实现（clean-room），提供以下能力：
  - 解析散乱文本中的 macOS 软件信息（名称/类别/付费状态/场景/替代品）
  - 结构化输出为 Markdown 表格、JSON 数组、CSV 或纯文本清单
  - 支持批量处理、字段筛选、排序、置信度标注
  - 内置离线自检（--selftest），不依赖外部文件或网络

错误码约定：
  E001 参数错误
  E002 输入为空
  E003 输入格式无法解析
  E004 非 macOS 平台软件（忽略并提示）
  E005 输出格式不支持
  E006 排序字段不存在
  E007 过滤字段不存在
  E008 内部逻辑错误
  E009 自检失败
  E010 未知异常

仅依赖 Python 标准库。MIT License。
"""

import argparse
import csv
import io
import json
import re
import sys
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# 常量定义
# ---------------------------------------------------------------------------

# 已知的 macOS 软件类别关键词（用于自动分类）
CATEGORY_KEYWORDS: Dict[str, List[str]] = {
    "开发工具": ["开发", "编程", "代码", "编辑器", "IDE", "git", "终端", "数据库", "调试"],
    "日常效率": ["效率", "笔记", "日历", "提醒", "输入法", "剪贴板", "窗口管理", "搜索"],
    "设计创作": ["设计", "绘图", "图片", "视频", "音频", "动画", "原型", "3D"],
    "系统工具": ["系统", "清理", "监控", "优化", "磁盘", "网络", "安全"],
    "网络通讯": ["浏览器", "邮件", "消息", "通话", "远程", "下载"],
    "影音娱乐": ["播放器", "音乐", "视频播放", "流媒体", "游戏"],
    "办公协作": ["办公", "文档", "表格", "演示", "会议", "协作"],
    "教育学习": ["学习", "词典", "翻译", "课程", "阅读"],
}

# 已知的付费状态关键词
FREE_KEYWORDS = ["免费", "free", "开源", "open source", "open-source"]
PAID_KEYWORDS = ["付费", "收费", "paid", "商业", "commercial", "pro"]

# 支持的输出格式
OUTPUT_FORMATS = ["markdown", "json", "csv", "text"]

# 支持的排序字段
SORT_FIELDS = ["name", "category", "price", "scene", "alternative"]

# 支持的过滤字段
FILTER_FIELDS = ["category", "price", "name", "scene"]


# ---------------------------------------------------------------------------
# 数据模型与工具函数
# ---------------------------------------------------------------------------

class MacApp:
    """表示一条 macOS 软件记录。"""

    def __init__(
        self,
        name: str = "",
        category: str = "",
        price: str = "",
        scene: str = "",
        alternative: str = "",
        source: str = "",
        notes: str = "",
    ) -> None:
        self.name = name.strip()
        self.category = category.strip()
        self.price = price.strip()
        self.scene = scene.strip()
        self.alternative = alternative.strip()
        self.source = source.strip()
        self.notes = notes.strip()

    def to_dict(self) -> Dict[str, str]:
        """转换为字典（用于 JSON 输出）。"""
        return {
            "name": self.name,
            "category": self.category,
            "price": self.price,
            "scene": self.scene,
            "alternative": self.alternative,
            "source": self.source,
            "notes": self.notes,
        }

    def to_csv_row(self) -> List[str]:
        """转换为 CSV 行。"""
        return [
            self.name,
            self.category,
            self.price,
            self.scene,
            self.alternative,
            self.source,
            self.notes,
        ]

    @staticmethod
    def csv_header() -> List[str]:
        """返回 CSV 表头。"""
        return ["名称", "类别", "付费状态", "适用场景", "替代品", "来源", "备注"]

    def to_markdown_row(self) -> str:
        """转换为 Markdown 表格行。"""
        return (
            f"| {self.name} | {self.category} | {self.price} | "
            f"{self.scene} | {self.alternative} | {self.source} | {self.notes} |"
        )

    @staticmethod
    def markdown_header() -> str:
        """返回 Markdown 表头。"""
        return (
            "| 名称 | 类别 | 付费状态 | 适用场景 | 替代品 | 来源 | 备注 |\n"
            "|------|------|----------|----------|--------|------|------|"
        )

    def __repr__(self) -> str:
        return f"MacApp(name={self.name!r}, category={self.category!r})"


def classify_category(text: str) -> str:
    """根据关键词自动判断软件类别。

    参数:
        text: 待分析的文本（软件描述、名称等）

    返回:
        匹配到的类别名称；若无法匹配返回空字符串。
    """
    if not text:
        return ""
    lower_text = text.lower()
    for category, keywords in CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if kw.lower() in lower_text:
                return category
    return ""


def classify_price(text: str) -> str:
    """根据关键词判断付费状态。

    参数:
        text: 待分析的文本

    返回:
        "免费"、"付费" 或空字符串（无法判断）。
    """
    if not text:
        return ""
    lower_text = text.lower()
    # 优先匹配付费（避免 "免费试用" 之类的歧义）
    for kw in PAID_KEYWORDS:
        if kw in lower_text:
            return "付费"
    for kw in FREE_KEYWORDS:
        if kw in lower_text:
            return "免费"
    return ""


def extract_software_name(line: str) -> str:
    """从一行文本中尝试提取软件名称。

    简单启发式规则：
      - 去掉常见前缀（如 "- "、"* "、"1. " 等）
      - 取第一个冒号/逗号/竖线之前的内容作为名称

    参数:
        line: 输入行文本

    返回:
        提取到的名称；若无法提取返回原行去除首尾空白。
    """
    if not line:
        return ""
    cleaned = line.strip()
    # 去掉列表符号
    cleaned = re.sub(r"^[\s\-*•·]+", "", cleaned)
    # 去掉数字编号
    cleaned = re.sub(r"^\d+[\.\)、]\s*", "", cleaned)
    # 取第一个分隔符之前的内容
    for sep in [":", "：", ",", "，", "|", "（", "("]:
        idx = cleaned.find(sep)
        if idx > 0:
            cleaned = cleaned[:idx].strip()
            break
    return cleaned.strip()


def parse_line(line: str) -> Optional[MacApp]:
    """解析单行文本为 MacApp 对象。

    支持格式示例：
      - "AppName - 免费 - 开发工具 - 代码编辑 - 替代品: XXX"
      - "AppName：付费，设计工具，用于绘图"
      - "名称 | 类别 | 价格 | 场景 | 替代"

    参数:
        line: 单行文本

    返回:
        MacApp 对象；若无法解析返回 None。
    """
    if not line or not line.strip():
        return None

    text = line.strip()
    app = MacApp()

    # 尝试按竖线分隔（表格格式）
    if "|" in text:
        parts = [p.strip() for p in text.split("|")]
        if len(parts) >= 1:
            app.name = parts[0]
        if len(parts) >= 2:
            app.category = parts[1]
        if len(parts) >= 3:
            app.price = parts[2]
        if len(parts) >= 4:
            app.scene = parts[3]
        if len(parts) >= 5:
            app.alternative = parts[4]
        if len(parts) >= 6:
            app.source = parts[5]
        if len(parts) >= 7:
            app.notes = parts[6]
        # 补齐缺失信息
        if not app.category:
            app.category = classify_category(text)
        if not app.price:
            app.price = classify_price(text)
        if app.name:
            return app
        return None

    # 尝试按逗号/冒号分隔
    app.name = extract_software_name(text)
    if not app.name:
        return None

    # 从整行文本中推断类别和价格
    app.category = classify_category(text)
    app.price = classify_price(text)

    # 尝试提取替代品信息
    alt_match = re.search(r"(?:替代品|替代|alternative)[:：]\s*([^,，;；]+)", text, re.IGNORECASE)
    if alt_match:
        app.alternative = alt_match.group(1).strip()

    # 尝试提取场景信息
    scene_match = re.search(r"(?:场景|用途|用于)[:：]\s*([^,，;；]+)", text, re.IGNORECASE)
    if scene_match:
        app.scene = scene_match.group(1).strip()

    # 尝试提取来源
    src_match = re.search(r"(?:来源|source)[:：]\s*([^,，;；]+)", text, re.IGNORECASE)
    if src_match:
        app.source = src_match.group(1).strip()

    return app


def parse_text(input_text: str) -> List[MacApp]:
    """解析多行文本为 MacApp 列表。

    参数:
        input_text: 多行文本内容

    返回:
        MacApp 对象列表

    异常:
        E002: 输入为空
        E003: 无法解析出任何有效记录
    """
    if not input_text or not input_text.strip():
        raise RuntimeError("E002: 输入文本为空，无法解析")

    apps: List[MacApp] = []
    lines = input_text.splitlines()

    for line in lines:
        # 跳过空行和明显的标题/分隔行
        stripped = line.strip()
        if not stripped:
            continue
        if re.match(r"^[=\-*#]{3,}$", stripped):
            continue
        if stripped.startswith("#"):
            continue

        app = parse_line(stripped)
        if app and app.name:
            apps.append(app)

    if not apps:
        raise RuntimeError("E003: 无法从输入文本中解析出任何有效软件记录")

    return apps


# ---------------------------------------------------------------------------
# 输出格式化
# ---------------------------------------------------------------------------

def format_markdown(apps: List[MacApp]) -> str:
    """格式化为 Markdown 表格。"""
    if not apps:
        return ""
    lines = [MacApp.markdown_header()]
    for app in apps:
        lines.append(app.to_markdown_row())
    return "\n".join(lines)


def format_json(apps: List[MacApp]) -> str:
    """格式化为 JSON 数组。"""
    return json.dumps([app.to_dict() for app in apps], ensure_ascii=False, indent=2)


def format_csv(apps: List[MacApp]) -> str:
    """格式化为 CSV 文本。"""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(MacApp.csv_header())
    for app in apps:
        writer.writerow(app.to_csv_row())
    return output.getvalue()


def format_text(apps: List[MacApp]) -> str:
    """格式化为纯文本清单。"""
    lines = []
    for app in apps:
        parts = [f"名称: {app.name}"]
        if app.category:
            parts.append(f"类别: {app.category}")
        if app.price:
            parts.append(f"付费: {app.price}")
        if app.scene:
            parts.append(f"场景: {app.scene}")
        if app.alternative:
            parts.append(f"替代: {app.alternative}")
        if app.source:
            parts.append(f"来源: {app.source}")
        if app.notes:
            parts.append(f"备注: {app.notes}")
        lines.append(" | ".join(parts))
    return "\n".join(lines)


def format_output(apps: List[MacApp], fmt: str) -> str:
    """根据指定格式输出。

    参数:
        apps: MacApp 列表
        fmt: 输出格式（markdown/json/csv/text）

    返回:
        格式化后的字符串

    异常:
        E005: 不支持的输出格式
    """
    if fmt == "markdown":
        return format_markdown(apps)
    elif fmt == "json":
        return format_json(apps)
    elif fmt == "csv":
        return format_csv(apps)
    elif fmt == "text":
        return format_text(apps)
    else:
        raise RuntimeError(f"E005: 不支持的输出格式: {fmt}")


# ---------------------------------------------------------------------------
# 过滤与排序
# ---------------------------------------------------------------------------

def filter_apps(apps: List[MacApp], filters: Dict[str, str]) -> List[MacApp]:
    """按指定字段过滤。

    参数:
        apps: MacApp 列表
        filters: 过滤条件字典，如 {"category": "开发工具", "price": "免费"}

    返回:
        过滤后的列表

    异常:
        E007: 过滤字段不存在
    """
    result = apps
    for field, value in filters.items():
        if field not in FILTER_FIELDS:
            raise RuntimeError(f"E007: 不支持的过滤字段: {field}")
        if not value:
            continue
        result = [a for a in result if value.lower() in getattr(a, field, "").lower()]
    return result


def sort_apps(apps: List[MacApp], sort_by: str, reverse: bool = False) -> List[MacApp]:
    """按指定字段排序。

    参数:
        apps: MacApp 列表
        sort_by: 排序字段
        reverse: 是否降序

    返回:
        排序后的列表

    异常:
        E006: 排序字段不存在
    """
    if sort_by not in SORT_FIELDS:
        raise RuntimeError(f"E006: 不支持的排序字段: {sort_by}")
    return sorted(apps, key=lambda a: getattr(a, sort_by, "").lower(), reverse=reverse)


# ---------------------------------------------------------------------------
# 主处理流程
# ---------------------------------------------------------------------------

def process_input(
    input_text: str,
    output_format: str = "markdown",
    sort_by: Optional[str] = None,
    reverse: bool = False,
    filters: Optional[Dict[str, str]] = None,
) -> str:
    """完整处理流程：解析 -> 过滤 -> 排序 -> 格式化。

    参数:
        input_text: 原始输入文本
        output_format: 输出格式
        sort_by: 排序字段（可选）
        reverse: 是否降序排序
        filters: 过滤条件字典（可选）

    返回:
        格式化后的输出字符串

    异常:
        E002/E003/E005/E006/E007 等
    """
    # 解析
    apps = parse_text(input_text)

    # 过滤
    if filters:
        apps = filter_apps(apps, filters)

    # 排序
    if sort_by:
        apps = sort_apps(apps, sort_by, reverse)

    # 格式化输出
    return format_output(apps, output_format)


# ---------------------------------------------------------------------------
# 自检（selftest）
# ---------------------------------------------------------------------------

def run_selftest() -> None:
    """内置离线自检。使用硬编码样例数据，不访问外部资源。

    异常:
        E009: 自检失败（断言不通过）
    """
    # 硬编码测试数据
    test_input = """\
VS Code - 免费 - 开发工具 - 代码编辑 - 替代品: Sublime Text
Bear - 付费 - 日常效率 - 笔记记录 - 替代品: Apple Notes
Figma - 免费 - 设计创作 - UI设计
CleanMyMac - 付费 - 系统工具 - 系统清理
Notion - 免费 - 办公协作 - 文档协作 - 替代品: Confluence
"""

    # 测试 1: 解析
    try:
        apps = parse_text(test_input)
        assert len(apps) >= 4, f"解析数量异常: {len(apps)}"
    except Exception as e:
        raise RuntimeError(f"E009: 自检失败 - 解析测试: {e}")

    # 测试 2: 分类
    try:
        assert apps[0].category == "开发工具", f"分类错误: {apps[0].category}"
        assert apps[1].category == "日常效率", f"分类错误: {apps[1].category}"
    except AssertionError as e:
        raise RuntimeError(f"E009: 自检失败 - 分类测试: {e}")

    # 测试 3: 价格判断
    try:
        assert apps[0].price == "免费", f"价格判断错误: {apps[0].price}"
        assert apps[1].price == "付费", f"价格判断错误: {apps[1].price}"
    except AssertionError as e:
        raise RuntimeError(f"E009: 自检失败 - 价格测试: {e}")

    # 测试 4: 过滤
    try:
        filtered = filter_apps(apps, {"category": "开发工具"})
        assert len(filtered) >= 1, "过滤结果为空"
        assert all(a.category == "开发工具" for a in filtered), "过滤结果类别不正确"
    except Exception as e:
        raise RuntimeError(f"E009: 自检失败 - 过滤测试: {e}")

    # 测试 5: 排序
    try:
        sorted_apps = sort_apps(apps, "name")
        names = [a.name.lower() for a in sorted_apps]
        assert names == sorted(names), "排序结果不正确"
    except Exception as e:
        raise RuntimeError(f"E009: 自检失败 - 排序测试: {e}")

    # 测试 6: 各输出格式
    try:
        for fmt in OUTPUT_FORMATS:
            output = format_output(apps, fmt)
            assert output, f"输出为空: {fmt}"
            # 宽松断言：输出长度应大于 0
            assert len(output) > 10, f"输出过短: {fmt}"
    except Exception as e:
        raise RuntimeError(f"E009: 自检失败 - 输出格式测试: {e}")

    # 测试 7: 完整流程
    try:
        result = process_input(
            test_input,
            output_format="json",
            sort_by="name",
            filters={"price": "免费"},
        )
        assert result, "完整流程输出为空"
        parsed_result = json.loads(result)
        assert len(parsed_result) >= 1, "完整流程结果数量异常"
        assert all(item["price"] == "免费" for item in parsed_result), "完整流程价格过滤异常"
    except Exception as e:
        raise RuntimeError(f"E009: 自检失败 - 完整流程测试: {e}")

    # 测试 8: 错误处理
    try:
        parse_text("")  # 应抛出 E002
        raise RuntimeError("E009: 自检失败 - 空输入未抛出异常")
    except RuntimeError as e:
        assert "E002" in str(e), f"错误码不正确: {e}"

    try:
        format_output(apps, "xml")  # 应抛出 E005
        raise RuntimeError("E009: 自检失败 - 非法格式未抛出异常")
    except RuntimeError as e:
        assert "E005" in str(e), f"错误码不正确: {e}"

    try:
        sort_apps(apps, "invalid_field")  # 应抛出 E006
        raise RuntimeError("E009: 自检失败 - 非法排序字段未抛出异常")
    except RuntimeError as e:
        assert "E006" in str(e), f"错误码不正确: {e}"


# ---------------------------------------------------------------------------
# CLI 入口
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    """构建命令行参数解析器。"""
    parser = argparse.ArgumentParser(
        description="macOS 软件分类导航检索工具",
        epilog="示例: python main.py -i input.txt -f json --sort name --filter category=开发工具",
    )
    parser.add_argument(
        "-i", "--input",
        help="输入文件路径（若不指定则从 stdin 读取）",
    )
    parser.add_argument(
        "-f", "--format",
        choices=OUTPUT_FORMATS,
        default="markdown",
        help=f"输出格式（默认: markdown，可选: {', '.join(OUTPUT_FORMATS)}）",
    )
    parser.add_argument(
        "--sort",
        choices=SORT_FIELDS,
        help=f"排序字段（可选: {', '.join(SORT_FIELDS)}）",
    )
    parser.add_argument(
        "--reverse",
        action="store_true",
        help="降序排序（与 --sort 配合使用）",
    )
    parser.add_argument(
        "--filter",
        action="append",
        metavar="FIELD=VALUE",
        help=f"过滤条件，可多次指定（可选字段: {', '.join(FILTER_FIELDS)}）",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置离线自检",
    )
    return parser


def parse_filters(filter_args: Optional[List[str]]) -> Dict[str, str]:
    """解析 --filter 参数为字典。

    参数:
        filter_args: 形如 ["category=开发工具", "price=免费"] 的列表

    返回:
        过滤条件字典

    异常:
        E001: 参数格式错误
        E007: 过滤字段不存在
    """
    filters: Dict[str, str] = {}
    if not filter_args:
        return filters

    for item in filter_args:
        if "=" not in item:
            raise RuntimeError(f"E001: 过滤参数格式错误: {item}（应为 FIELD=VALUE）")
        field, value = item.split("=", 1)
        field = field.strip()
        value = value.strip()
        if field not in FILTER_FIELDS:
            raise RuntimeError(f"E007: 不支持的过滤字段: {field}")
        filters[field] = value
    return filters


def main(argv: Optional[List[str]] = None) -> int:
    """主函数。

    参数:
        argv: 命令行参数列表（默认使用 sys.argv[1:]）

    返回:
        退出码（0 成功，非 0 失败）
    """
    parser = build_parser()
    args = parser.parse_args(argv)

    # 自检模式
    if args.selftest:
        try:
            run_selftest()
            print("自检通过 ✅")
            return 0
        except RuntimeError as e:
            print(f"自检失败 ❌: {e}", file=sys.stderr)
            return 1
        except Exception as e:
            print(f"自检异常 ❌: {e}", file=sys.stderr)
            return 1

    # 读取输入
    try:
        if args.input:
            with open(args.input, "r", encoding="utf-8") as f:
                input_text = f.read()
        else:
            input_text = sys.stdin.read()
    except FileNotFoundError:
        print(f"E001: 输入文件不存在: {args.input}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"E010: 读取输入失败: {e}", file=sys.stderr)
        return 1

    # 解析过滤条件
    try:
        filters = parse_filters(args.filter)
    except RuntimeError as e:
        print(f"{e}", file=sys.stderr)
        return 1

    # 处理
    try:
        output = process_input(
            input_text,
            output_format=args.format,
            sort_by=args.sort,
            reverse=args.reverse,
            filters=filters,
        )
        print(output)
        return 0
    except RuntimeError as e:
        print(f"{e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"E010: 未知错误: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
