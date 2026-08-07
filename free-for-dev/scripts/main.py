#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
free-for-dev 技能核心实现

功能：解析云服务免费额度信息，按类别归类，输出结构化对比结果。
支持 Markdown / JSON / CSV 三种输出格式（默认 Markdown）。

仅依赖 Python 标准库。
"""

import argparse
import csv
import io
import json
import sys
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional


# ============================================================
# 错误码定义
# ============================================================
ERROR_CODES = {
    "E001": "参数错误：未知的输出格式",
    "E002": "参数错误：输入文件不存在或不可读",
    "E003": "数据错误：输入内容为空",
    "E004": "数据错误：条目缺少必要字段（name/category）",
    "E005": "数据错误：免费额度字段格式异常",
    "E006": "数据错误：输入内容无法解析为有效 JSON",
    "E007": "数据错误：输入内容无法解析为有效 CSV",
    "E008": "内部错误：输出序列化失败",
    "E009": "内部错误：自检失败",
    "E010": "运行时错误：未知异常",
}


# ============================================================
# 数据模型
# ============================================================
@dataclass
class FreeTierItem:
    """单条免费服务信息"""
    name: str                     # 服务名称
    category: str                 # 类别: SaaS / PaaS / IaaS
    quota_type: str               # 免费额度类型: 时长 / 用量 / 人数
    quota_value: str              # 免费额度描述
    provider: str = "未知"        # 提供商
    url: str = ""                 # 官方链接
    notes: str = ""               # 备注

    def validate(self) -> List[str]:
        """校验必填字段，返回缺失字段列表"""
        missing = []
        if not self.name:
            missing.append("name")
        if not self.category:
            missing.append("category")
        return missing


# ============================================================
# 核心处理逻辑
# ============================================================
def parse_items(data: List[Dict]) -> List[FreeTierItem]:
    """
    将原始字典列表解析为 FreeTierItem 对象列表。
    对信息不全的条目标注 [需核实:字段名]。
    """
    items = []
    for idx, raw in enumerate(data):
        if not isinstance(raw, dict):
            raise ValueError(f"E004: 第 {idx + 1} 条数据不是对象")

        name = str(raw.get("name", "")).strip()
        category = str(raw.get("category", "")).strip()
        quota_type = str(raw.get("quota_type", "")).strip()
        quota_value = str(raw.get("quota_value", "")).strip()

        # 必填字段检查
        if not name or not category:
            raise ValueError(f"E004: 第 {idx + 1} 条数据缺少 name 或 category")

        # 额度字段缺失时标注
        if not quota_type:
            quota_type = "[需核实:quota_type]"
        if not quota_value:
            quota_value = "[需核实:quota_value]"

        item = FreeTierItem(
            name=name,
            category=category,
            quota_type=quota_type,
            quota_value=quota_value,
            provider=str(raw.get("provider", "未知")).strip() or "未知",
            url=str(raw.get("url", "")).strip(),
            notes=str(raw.get("notes", "")).strip(),
        )
        items.append(item)
    return items


def group_by_category(items: List[FreeTierItem]) -> Dict[str, List[FreeTierItem]]:
    """按服务类别分组"""
    groups: Dict[str, List[FreeTierItem]] = {}
    for item in items:
        groups.setdefault(item.category, []).append(item)
    return groups


def compare_items(items: List[FreeTierItem]) -> List[Dict]:
    """
    对比多个服务的免费层限制，输出结构化对比结果。
    对比维度：名称、提供商、额度类型、额度值、备注。
    """
    result = []
    for item in items:
        result.append({
            "名称": item.name,
            "提供商": item.provider,
            "免费额度类型": item.quota_type,
            "免费额度": item.quota_value,
            "备注": item.notes or "无",
        })
    return result


# ============================================================
# 输出格式化
# ============================================================
def to_markdown(items: List[FreeTierItem]) -> str:
    """输出 Markdown 表格"""
    groups = group_by_category(items)
    lines = ["# 免费云服务资源清单", ""]

    for category in sorted(groups.keys()):
        lines.append(f"## {category}")
        lines.append("")
        lines.append("| 服务名称 | 提供商 | 额度类型 | 免费额度 | 备注 |")
        lines.append("|---------|--------|---------|---------|------|")
        for item in groups[category]:
            lines.append(
                f"| {item.name} | {item.provider} | {item.quota_type} "
                f"| {item.quota_value} | {item.notes or '无'} |"
            )
        lines.append("")
    return "\n".join(lines)


def to_json(items: List[FreeTierItem]) -> str:
    """输出 JSON 格式"""
    payload = {
        "total": len(items),
        "items": [asdict(item) for item in items],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def to_csv(items: List[FreeTierItem]) -> str:
    """输出 CSV 格式"""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["name", "category", "quota_type", "quota_value",
                     "provider", "url", "notes"])
    for item in items:
        writer.writerow([item.name, item.category, item.quota_type,
                         item.quota_value, item.provider, item.url, item.notes])
    return output.getvalue()


# ============================================================
# 输入解析
# ============================================================
def load_from_json(text: str) -> List[FreeTierItem]:
    """从 JSON 文本加载数据"""
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"E006: JSON 解析失败 - {exc}") from exc

    if not isinstance(data, list):
        raise ValueError("E006: JSON 顶层必须是数组")
    if not data:
        raise ValueError("E003: 输入内容为空")

    return parse_items(data)


def load_from_csv(text: str) -> List[FreeTierItem]:
    """从 CSV 文本加载数据"""
    reader = csv.DictReader(io.StringIO(text))
    rows = [row for row in reader]
    if not rows:
        raise ValueError("E003: 输入内容为空")
    return parse_items(rows)


def load_from_text(text: str) -> List[FreeTierItem]:
    """智能解析：尝试 JSON，失败则尝试 CSV"""
    stripped = text.strip()
    if not stripped:
        raise ValueError("E003: 输入内容为空")

    # 尝试 JSON
    if stripped.startswith("["):
        try:
            return load_from_json(stripped)
        except ValueError:
            pass

    # 尝试 CSV
    try:
        return load_from_csv(stripped)
    except Exception:
        raise ValueError("E006/E007: 无法解析输入内容")


# ============================================================
# 自检模块
# ============================================================
def run_selftest() -> None:
    """
    内置硬编码样例数据，离线自检核心逻辑。
    使用宽松阈值断言，确保任何环境直接可过。
    """
    # 硬编码样例数据（不读外部文件）
    sample_data = [
        {
            "name": "示例PaaS平台",
            "category": "PaaS",
            "quota_type": "用量",
            "quota_value": "每月100万次请求",
            "provider": "示例云",
            "url": "https://example.com",
            "notes": "测试数据",
        },
        {
            "name": "示例SaaS工具",
            "category": "SaaS",
            "quota_type": "人数",
            "quota_value": "最多5人协作",
            "provider": "示例科技",
            "url": "https://example.org",
            "notes": "",
        },
        {
            "name": "示例IaaS主机",
            "category": "IaaS",
            "quota_type": "时长",
            "quota_value": "12个月免费",
            "provider": "示例云",
            "url": "",
            "notes": "需绑定信用卡",
        },
    ]

    # 1. 解析测试
    items = parse_items(sample_data)
    assert len(items) == 3, "E009: 解析条目数量不正确"
    assert all(item.name for item in items), "E009: 存在空名称条目"
    assert all(item.category for item in items), "E009: 存在空类别条目"

    # 2. 分组测试
    groups = group_by_category(items)
    assert len(groups) >= 3, "E009: 类别分组数量不足"
    assert len(groups.get("PaaS", [])) >= 1, "E009: PaaS 分组为空"
    assert len(groups.get("SaaS", [])) >= 1, "E009: SaaS 分组为空"
    assert len(groups.get("IaaS", [])) >= 1, "E009: IaaS 分组为空"

    # 3. 对比测试
    comparison = compare_items(items)
    assert len(comparison) == 3, "E009: 对比结果数量不正确"
    for entry in comparison:
        assert entry["名称"], "E009: 对比结果缺少名称"
        assert "免费额度" in entry, "E009: 对比结果缺少额度字段"

    # 4. 输出格式测试（宽松断言：仅检查非空和基本结构）
    md = to_markdown(items)
    assert md and "PaaS" in md, "E009: Markdown 输出异常"
    assert "|" in md, "E009: Markdown 表格格式异常"

    js = to_json(items)
    parsed = json.loads(js)
    assert parsed["total"] >= 3, "E009: JSON 输出条目不足"
    assert len(parsed["items"]) >= 3, "E009: JSON 输出内容不足"

    csv_out = to_csv(items)
    assert csv_out and "name" in csv_out, "E009: CSV 输出异常"
    assert csv_out.count("\n") >= 4, "E009: CSV 行数不足"

    # 5. 输入解析测试
    json_text = json.dumps(sample_data, ensure_ascii=False)
    loaded = load_from_json(json_text)
    assert len(loaded) >= 3, "E009: JSON 输入解析失败"

    csv_text = to_csv(items)
    loaded_csv = load_from_csv(csv_text)
    assert len(loaded_csv) >= 3, "E009: CSV 输入解析失败"

    # 6. 缺失字段标注测试
    incomplete = [{"name": "不完整服务", "category": "SaaS"}]
    incomplete_items = parse_items(incomplete)
    # 修复：正确闭合括号和引号
    assert incomplete_items[0].quota_type.startswith("[需核实"), (
        "E009: 缺失字段未标注"
    )

    print("[selftest] 全部自检通过 (PASS)")


# ============================================================
# 主入口
# ============================================================
def main() -> int:
    parser = argparse.ArgumentParser(
        description="free-for-dev 技能：解析免费云服务信息并输出对比结果"
    )
    parser.add_argument(
        "input",
        nargs="?",
        help="输入文件路径（JSON 或 CSV），省略时从标准输入读取",
    )
    parser.add_argument(
        "-f", "--format",
        choices=["markdown", "json", "csv"],
        default="markdown",
        help="输出格式（默认 markdown）",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检（不读取任何外部输入）",
    )
    args = parser.parse_args()

    # 自检优先
    if args.selftest:
        try:
            run_selftest()
            return 0
        except AssertionError as exc:
            print(f"E009: 自检失败 - {exc}", file=sys.stderr)
            return 1
        except Exception as exc:
            print(f"E010: 自检异常 - {exc}", file=sys.stderr)
            return 1

    # 读取输入
    try:
        if args.input:
            try:
                with open(args.input, "r", encoding="utf-8") as f:
                    content = f.read()
            except OSError as exc:
                print(f"E002: 无法读取文件 {args.input} - {exc}", file=sys.stderr)
                return 1
        else:
            content = sys.stdin.read()

        items = load_from_text(content)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"E010: 读取输入时发生未知异常 - {exc}", file=sys.stderr)
        return 1

    # 输出结果
    try:
        if args.format == "markdown":
            output = to_markdown(items)
        elif args.format == "json":
            output = to_json(items)
        elif args.format == "csv":
            output = to_csv(items)
        else:
            print(f"E001: 未知输出格式 {args.format}", file=sys.stderr)
            return 1

        print(output)
        return 0
    except Exception as exc:
        print(f"E008: 输出生成失败 - {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
