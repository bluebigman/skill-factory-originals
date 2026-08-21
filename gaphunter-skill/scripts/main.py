#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gaphunter-skill 独立实现脚本

基于功能规格的 clean-room 重写，不参考任何既有代码。
提供竞品差距分析、过滤与报告生成能力。
"""

import argparse
import html
import json
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Optional
dry_run = False  # v3.274 模块级 dry-run 标志


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


def fail(code: str, message: Optional[str] = None) -> None:
    """以指定错误码终止程序。"""
    text = ERROR_CODES.get(code, ERROR_CODES["E010"])
    if message:
        text = f"{text}: {message}"
    print(f"[错误 {code}] {text}", file=sys.stderr)
    sys.exit(1)


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
                pass

        # 尝试 CSV / 表格
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        if not lines:
            fail("E001")

        # 检查是否像 CSV（含逗号或制表符）
        if any(("," in ln or "\t" in ln) for ln in lines):
            return DataParser._from_csv(lines)

        # 尝试 Markdown 表格
        if lines[0].startswith("|") and "---" in lines[1]:
            return DataParser._from_markdown(lines)

        # 尝试简单键值文本
        return DataParser._from_keyvalue(text)

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
                    # 部分覆盖 = 基准有且竞品有（简化处理，实际可更精细）
                    # 这里定义为基准有且竞品有但描述不同；因无描述比较，视为已覆盖
                    # 为保留语义，部分覆盖与已覆盖在此简化实现中相同
                    keep = True
                    break
            if keep:
                filtered_features.append(feat)
        report.all_features = filtered_features

    return report


# ============================================================
# 报告生成（HTML / 文本）
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


# ============================================================
# 导出功能（PDF 简化实现）
# ============================================================
def export_report(report: AnalysisReport, fmt: str, output_path: Optional[str] = None) -> str:
    """
    导出报告。支持 txt / html / pdf（pdf 为简化实现，输出 HTML 并提示）。
    返回输出文件路径。
    """
    if fmt == "html":
        content = generate_html_report(report)
        path = output_path or "gap_report.html"
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return path
    elif fmt == "txt":
        content = generate_text_report(report)
        path = output_path or "gap_report.txt"
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return path
    elif fmt == "pdf":
        # 简化实现：生成 HTML 并提示用户手动打印为 PDF
        content = generate_html_report(report)
        path = output_path or "gap_report_pdf.html"
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        print("提示：PDF 导出为简化实现，已生成 HTML 文件，请用浏览器打印为 PDF。")
        return path
    else:
        fail("E006", f"不支持的格式: {fmt}")


# ============================================================
# 内置自检（selftest）
# ============================================================
def run_selftest() -> int:
    """使用内置硬编码数据执行离线自检。不访问网络、不读外部文件。"""
    print("开始自检...")

    # 硬编码测试数据
    test_text = """
    基准产品, 登录, 支持密码登录
    基准产品, 双因素认证, 支持 TOTP
    基准产品, 数据导出, 支持 CSV
    竞品A, 登录, 支持密码登录
    竞品A, 数据导出, 支持 CSV
    竞品B, 登录, 支持密码登录
    竞品B, 双因素认证, 支持短信
    竞品B, 实时协作, 支持多人编辑
    """

    # 1. 解析测试
    products = DataParser.parse(test_text)
    assert len(products) >= 3, "应至少解析出3个产品"
    assert products[0].name == "基准产品", "第一个产品应为基准"
    print(f"[通过] 解析 {len(products)} 个产品")

    # 2. 分析测试
    analyzer = GapAnalyzer(products)
    report = analyzer.analyze()
    assert len(report.all_features) >= 4, "应至少有4个功能点"
    assert len(report.comparisons) == 2, "应有2个竞品"
    print(f"[通过] 分析完成，功能数={len(report.all_features)}")

    # 3. 过滤测试
    filtered = filter_report(report, status="未覆盖")
    assert len(filtered.all_features) >= 1, "应至少有1个未覆盖功能"
    filtered2 = filter_report(report, competitor="竞品A")
    assert filtered2.competitor_names == ["竞品A"], "应只保留竞品A"
    print(f"[通过] 过滤正常，未覆盖功能数={len(filtered.all_features)}")

    # 4. 报告生成测试
    html_report = generate_html_report(report)
    assert "<table>" in html_report, "HTML报告应包含表格"
    text_report = generate_text_report(report)
    assert "竞品" in text_report, "文本报告应包含竞品信息"
    print("[通过] 报告生成正常")

    # 5. 宽松断言：检查基本逻辑一致性
    for comp in report.comparisons:
        for feat in report.all_features:
            has_base, has_comp = comp.feature_status[feat]
            # 检查状态一致性
            assert isinstance(has_base, bool), "基准状态应为布尔"
            assert isinstance(has_comp, bool), "竞品状态应为布尔"
    print("[通过] 状态一致性检查")

    # 6. 边界测试
    try:
        DataParser.parse("")
        assert False, "空输入应报错"
    except SystemExit:
        pass
    print("[通过] 空输入错误处理")

    print("\n所有自检通过！")
    return 0


# ============================================================
# 主入口
# ============================================================
def main():
    parser = argparse.ArgumentParser(
        description="gaphunter-skill：竞品差距分析工具",
        epilog="示例：python main.py --input data.csv --filter 未覆盖 --export html"
    )
    parser.add_argument("--input", "-i", help="输入文件路径（支持 CSV/JSON/Markdown/文本）")
    parser.add_argument("--text", "-t", help="直接输入文本数据")
    parser.add_argument("--filter", "-f", choices=["已覆盖", "未覆盖", "部分覆盖"],
                        help="按覆盖状态过滤")
    parser.add_argument("--competitor", "-c", help="按竞品名称过滤")
    parser.add_argument("--export", "-e", choices=["txt", "html", "pdf"],
                        default="txt", help="导出格式")
    parser.add_argument("--output", "-o", help="输出文件路径")
    parser.add_argument("--selftest", action="store_true", help="运行内置自检")
    parser.add_argument("--force", action="store_true")  # R4 强制写盘

    parser.add_argument("--dry-run", action="store_true")  # R4 预览模式
    args = parser.parse_args()
    global dry_run
    dry_run = getattr(args, "dry_run", False)  # v3.274 同步到全局

    # 自检模式
    if args.selftest:
        sys.exit(run_selftest())

    # 获取输入数据
    if args.input:
        try:
            with open(args.input, "r", encoding="utf-8") as f:
                text = f.read()
        except Exception as e:
            fail("E001", f"读取文件失败: {e}")
    elif args.text:
        text = args.text
    else:
        parser.print_help()
        fail("E001", "必须提供 --input 或 --text 或 --selftest")

    # 解析数据
    products = DataParser.parse(text)

    # 执行分析
    analyzer = GapAnalyzer(products)
    report = analyzer.analyze()

    # 过滤
    report = filter_report(report, status=args.filter, competitor=args.competitor)

    # 导出
    try:
        path = export_report(report, args.export, args.output)
        print(f"报告已生成：{path}")
    except SystemExit:
        raise
    except Exception as e:
        fail("E009", f"导出失败: {e}")


if __name__ == "__main__":
    main()
