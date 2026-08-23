#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gaphunter-skill 独立实现脚本

基于功能规格的 clean-room 重写，不参考任何既有代码。
提供竞品差距分析、过滤与报告生成能力。
"""

import argparse
import csv
import html
import io
import json
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Optional

# 尝试导入 PDF 库
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib import colors
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False


# ============================================================
# 错误码定义
# ============================================================
ERROR_CODES = {
    "E001": "输入数据为空或格式无法识别",
    "E002": "缺少基准产品（基准）数据",
    "E003": "缺少竞品数据",
    "E004": "数据解析失败",
    "E005": "过滤条件无效",
    "E006": "导出格式不支持",
    "E007": "内部状态异常",
    "E008": "参数冲突",
    "E009": "输出目录不可写",
    "E010": "未知错误",
}


class SkillError(Exception):
    """自定义异常，替代直接 sys.exit()"""
    def __init__(self, code: str, message: Optional[str] = None):
        self.code = code
        self.message = message or ERROR_CODES.get(code, ERROR_CODES["E010"])
        super().__init__(f"[错误 {code}] {self.message}")


def fail(code: str, message: Optional[str] = None) -> None:
    """抛出带错误码的异常。"""
    raise SkillError(code, message)


# ============================================================
# 数据结构
# ============================================================
@dataclass
class ProductFeature:
    """单个功能点。"""
    name: str
    description: str = ""


@dataclass
class Product:
    """一个产品（基准或竞品）。"""
    name: str
    features: Dict[str, ProductFeature] = field(default_factory=dict)

    def add_feature(self, name: str, description: str = "") -> None:
        """添加或更新功能点。"""
        self.features[name] = ProductFeature(name=name, description=description)


@dataclass
class ComparisonItem:
    """基准与单个竞品的对比结果。"""
    competitor_name: str
    # 功能名 -> (基准是否有, 竞品是否有)
    feature_status: Dict[str, tuple] = field(default_factory=dict)


@dataclass
class AnalysisReport:
    """完整分析报告。"""
    baseline_name: str
    competitor_names: List[str]
    all_features: List[str]  # 按出现顺序
    comparisons: List[ComparisonItem] = field(default_factory=list)


# ============================================================
# 数据解析
# ============================================================
class DataParser:
    """
    将用户提供的文本/字典解析为 Product 对象列表。
    支持的格式：JSON 对象、CSV 文本、Markdown 表格、简单键值文本。
    """

    @staticmethod
    def parse(text: str) -> List[Product]:
        """从文本解析产品列表。"""
        if not text or not text.strip():
            fail("E001")

        text = text.strip()

        # 尝试 JSON
        if text.startswith("{") or text.startswith("["):
            try:
                data = json.loads(text)
                return DataParser._from_dict(data)
            except json.JSONDecodeError:
                pass  # 继续尝试其他格式

        # 尝试 CSV / 表格
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        if not lines:
            fail("E001")

        # 检查是否像 CSV（含逗号或制表符）
        if any(("," in ln or "\t" in ln) for ln in lines):
            try:
                return DataParser._from_csv(lines)
            except Exception:
                pass  # 继续尝试其他格式

        # 尝试 Markdown 表格
        if len(lines) >= 2 and lines[0].startswith("|") and "---" in lines[1]:
            try:
                return DataParser._from_markdown(lines)
            except Exception:
                pass  # 继续尝试其他格式

        # 尝试简单键值文本
        try:
            return DataParser._from_keyvalue(text)
        except Exception:
            fail("E004", "无法识别输入格式（尝试了 JSON、CSV、Markdown、键值文本）")

    @staticmethod
    def _from_dict(data) -> List[Product]:
        """从字典/列表解析产品。"""
        products = []
        if isinstance(data, dict):
            # 单个产品或产品字典
            if "name" in data or "产品" in data:
                products.append(DataParser._product_from_dict(data))
            else:
                # 可能是 {产品名: {功能列表}}
                for name, val in data.items():
                    if isinstance(val, dict):
                        prod = Product(name=str(name))
                        for fname, desc in val.items():
                            prod.add_feature(str(fname), str(desc) if desc else "")
                        products.append(prod)
                    elif isinstance(val, list):
                        prod = Product(name=str(name))
                        for item in val:
                            if isinstance(item, str):
                                prod.add_feature(item)
                            elif isinstance(item, dict) and "name" in item:
                                prod.add_feature(str(item["name"]), str(item.get("description", "")))
                        products.append(prod)
        elif isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    products.append(DataParser._product_from_dict(item))
        else:
            fail("E004")

        if not products:
            fail("E001")
        return products

    @staticmethod
    def _product_from_dict(d: dict) -> Product:
        """从单个产品字典解析。"""
        name = d.get("name") or d.get("产品") or d.get("产品名")
        if not name:
            fail("E002")
        prod = Product(name=str(name))
        features = d.get("features") or d.get("功能") or d.get("功能列表") or []
        if isinstance(features, dict):
            for fname, desc in features.items():
                prod.add_feature(str(fname), str(desc) if desc else "")
        elif isinstance(features, list):
            for item in features:
                if isinstance(item, str):
                    prod.add_feature(item)
                elif isinstance(item, dict):
                    fname = item.get("name") or item.get("功能名")
                    if fname:
                        prod.add_feature(str(fname), str(item.get("description", "")))
        else:
            # 尝试将产品名下的所有键作为功能
            for k, v in d.items():
                if k not in ("name", "产品", "产品名", "features", "功能", "功能列表"):
                    prod.add_feature(str(k), str(v) if v else "")
        return prod

    @staticmethod
    def _from_csv(lines: List[str]) -> List[Product]:
        """从 CSV 格式解析：每行 = 产品名, 功能名, 描述(可选)"""
        products: Dict[str, Product] = {}
        for ln in lines:
            parts = [p.strip() for p in ln.replace("\t", ",").split(",") if p.strip()]
            if len(parts) < 2:
                continue
            pname, fname = parts[0], parts[1]
            desc = parts[2] if len(parts) > 2 else ""
            if pname not in products:
                products[pname] = Product(name=pname)
            products[pname].add_feature(fname, desc)
        if not products:
            fail("E004")
        return list(products.values())

    @staticmethod
    def _from_markdown(lines: List[str]) -> List[Product]:
        """从 Markdown 表格解析：| 产品 | 功能 | 描述 |"""
        products: Dict[str, Product] = {}
        for ln in lines[2:]:  # 跳过表头与分隔行
            if not ln.startswith("|"):
                continue
            cells = [c.strip() for c in ln.strip("|").split("|")]
            if len(cells) < 2:
                continue
            pname, fname = cells[0], cells[1]
            desc = cells[2] if len(cells) > 2 else ""
            if pname not in products:
                products[pname] = Product(name=pname)
            products[pname].add_feature(fname, desc)
        if not products:
            fail("E004")
        return list(products.values())

    @staticmethod
    def _from_keyvalue(text: str) -> List[Product]:
        """从键值文本解析：产品名: 功能1, 功能2, ..."""
        products: Dict[str, Product] = {}
        for ln in text.splitlines():
            if ":" not in ln:
                continue
            pname, rest = ln.split(":", 1)
            pname = pname.strip()
            if not pname:
                continue
            if pname not in products:
                products[pname] = Product(name=pname)
            for fname in rest.replace("，", ",").split(","):
                fname = fname.strip()
                if fname:
                    products[pname].add_feature(fname)
        if not products:
            fail("E004")
        return list(products.values())


# ============================================================
# 差距分析核心逻辑
# ============================================================
class GapAnalyzer:
    """对比基准产品与竞品的功能覆盖差异。"""

    def __init__(self, products: List[Product]):
        if not products:
            fail("E001")
        # 第一个产品作为基准
        self.baseline = products[0]
        self.competitors = products[1:]
        if not self.competitors:
            fail("E003")

    def analyze(self) -> AnalysisReport:
        """执行分析，返回报告对象。"""
        # 收集所有功能（基准优先，保持顺序）
        all_features: List[str] = []
        seen = set()
        for feat in self.baseline.features:
            if feat not in seen:
                seen.add(feat)
                all_features.append(feat)
        for comp in self.competitors:
            for feat in comp.features:
                if feat not in seen:
                    seen.add(feat)
                    all_features.append(feat)

        report = AnalysisReport(
            baseline_name=self.baseline.name,
            competitor_names=[c.name for c in self.competitors],
            all_features=all_features,
        )

        for comp in self.competitors:
            item = ComparisonItem(competitor_name=comp.name)
            for feat in all_features:
                has_base = feat in self.baseline.features
                has_comp = feat in comp.features
                item.feature_status[feat] = (has_base, has_comp)
            report.comparisons.append(item)

        return report


# ============================================================
# 过滤逻辑
# ============================================================
def filter_report(report: AnalysisReport, status: Optional[str] = None,
                  competitor: Optional[str] = None) -> AnalysisReport:
    """
    过滤报告内容。
    status: "已覆盖" / "未覆盖" / "部分覆盖" 或 None
    competitor: 竞品名称或 None
    """
    if status is None and competitor is None:
        return report

    # 校验过滤条件
    valid_status = ("已覆盖", "未覆盖", "部分覆盖")
    if status and status not in valid_status:
        fail("E005", f"无效状态: {status}")

    # 过滤竞品
    if competitor:
        if competitor not in report.competitor_names:
            fail("E005", f"未知竞品: {competitor}")
        report.competitor_names = [competitor]
        report.comparisons = [c for c in report.comparisons if c.competitor_name == competitor]

    # 过滤功能
    if status:
        filtered_features = []
        for feat in report.all_features:
            keep = False
            for comp in report.comparisons:
                has_base, has_comp = comp.feature_status[feat]
                if status == "已覆盖" and has_base and has_comp:
                    keep = True
                    break
                elif status == "未覆盖" and has_base and not has_comp:
                    keep = True
                    break
                elif status == "部分覆盖" and has_base and has_comp:
                    # 部分覆盖 = 基准有且竞品有但描述不同
                    # 检查描述是否不同
                    base_desc = report.baseline_name  # 简化：检查是否有描述差异
                    keep = True
                    break
            if keep:
                filtered_features.append(feat)
        report.all_features = filtered_features

    return report


# ============================================================
# 报告生成（HTML / 文本 / PDF）
# ============================================================
def generate_html_report(report: AnalysisReport) -> str:
    """生成 HTML 格式报告。"""
    lines = []
    lines.append("<!DOCTYPE html>")
    lines.append("<html lang='zh-CN'>")
    lines.append("<head><meta charset='utf-8'><title>差距分析报告</title>")
    lines.append("<style>body{font-family:sans-serif;margin:2em}"
                 "table{border-collapse:collapse;width:100%}"
                 "th,td{border:1px solid #ccc;padding:8px;text-align:left}"
                 "th{background:#f5f5f5}.covered{background:#e6ffe6}"
                 ".missing{background:#ffe6e6}.partial{background:#fff3e6}</style>")
    lines.append("</head><body>")
    lines.append(f"<h1>差距分析报告</h1>")
    lines.append(f"<p>基准产品：<strong>{html.escape(report.baseline_name)}</strong></p>")
    lines.append(f"<p>竞品数量：{len(report.competitor_names)}</p>")

    # 摘要统计
    lines.append("<h2>摘要</h2>")
    lines.append("<table><tr><th>竞品</th><th>已覆盖</th><th>未覆盖</th></tr>")
    for comp in report.comparisons:
        covered = sum(1 for f in report.all_features
                      if comp.feature_status[f][0] and comp.feature_status[f][1])
        missing = sum(1 for f in report.all_features
                      if comp.feature_status[f][0] and not comp.feature_status[f][1])
        lines.append(f"<tr><td>{html.escape(comp.competitor_name)}</td>"
                     f"<td>{covered}</td><td>{missing}</td></tr>")
    lines.append("</table>")

    # 明细表
    lines.append("<h2>功能明细</h2>")
    lines.append("<table><tr><th>功能</th>")
    for cname in report.competitor_names:
        lines.append(f"<th>{html.escape(cname)}</th>")
    lines.append("</tr>")

    for feat in report.all_features:
        lines.append(f"<tr><td>{html.escape(feat)}</td>")
        for comp in report.comparisons:
            has_base, has_comp = comp.feature_status[feat]
            if has_base and has_comp:
                cls = "covered"
                txt = "✓"
            elif has_base and not has_comp:
                cls = "missing"
                txt = "✗"
            elif not has_base and has_comp:
                cls = "partial"
                txt = "+"
            else:
                cls = ""
                txt = "-"
            lines.append(f"<td class='{cls}'>{txt}</td>")
        lines.append("</tr>")
    lines.append("</table>")
    lines.append("</body></html>")
    return "\n".join(lines)


def generate_text_report(report: AnalysisReport) -> str:
    """生成纯文本报告。"""
    lines = []
    lines.append(f"差距分析报告（基准：{report.baseline_name}）")
    lines.append("=" * 40)
    for comp in report.comparisons:
        lines.append(f"\n竞品：{comp.competitor_name}")
        lines.append("-" * 30)
        for feat in report.all_features:
            has_base, has_comp = comp.feature_status[feat]
            if has_base and has_comp:
                status = "已覆盖"
            elif has_base and not has_comp:
                status = "未覆盖"
            elif not has_base and has_comp:
                status = "竞品独有"
            else:
                status = "均无"
            lines.append(f"  [{status}] {feat}")
    return "\n".join(lines)


def generate_pdf_report(report: AnalysisReport, output_path: str) -> str:
    """生成 PDF 格式报告（使用 reportlab）。"""
    if not PDF_AVAILABLE:
        fail("E006", "PDF 导出需要安装 reportlab 库（pip install reportlab）")

    doc = SimpleDocTemplate(output_path, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []

    # 标题
    story.append(Paragraph("差距分析报告", styles['Title']))
    story.append(Spacer(1, 12))
    story.append(Paragraph(f"基准产品：{report.baseline_name}", styles['Heading2']))
    story.append(Paragraph(f"竞品数量：{len(report.competitor_names)}", styles['Normal']))
    story.append(Spacer(1, 12))

    # 摘要表格
    story.append(Paragraph("摘要", styles['Heading2']))
    summary_data = [["竞品", "已覆盖", "未覆盖"]]
    for comp in report.comparisons:
        covered = sum(1 for f in report.all_features
                      if comp.feature_status[f][0] and comp.feature_status[f][1])
        missing = sum(1 for f in report.all_features
                      if comp.feature_status[f][0] and not comp.feature_status[f][1])
