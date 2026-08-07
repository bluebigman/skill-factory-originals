#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
年报速读 · 财务透视 · 决策辅助
================================
基于功能规格独立实现的 clean-room 版本。

仅依据《annual-report-summary》功能规格文档进行设计，
不参考或复制任何既有代码。

用法示例:
    python scripts/main.py --selftest
    python scripts/main.py --input report.json --output summary.json

错误码:
    E001 参数错误
    E002 文件不存在
    E003 文件格式不支持
    E004 JSON 解析失败
    E005 数据缺失必要字段
    E006 数据字段类型错误
    E007 计算异常
    E008 输出写入失败
    E009 自检失败
    E010 未知异常
"""

import argparse
import json
import os
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# 常量定义
# ---------------------------------------------------------------------------

# 核心财务指标字段名（中英文对照，用于输出标准化）
KEY_METRICS = {
    "revenue": "营业收入",
    "net_profit": "净利润",
    "gross_margin": "毛利率",
    "debt_ratio": "资产负债率",
    "roe": "净资产收益率",
    "operating_cash_flow": "经营活动现金流",
}

# 风险信号关键词（用于异常项标记）
RISK_KEYWORDS = [
    "非经常性损益",
    "保留意见",
    "无法表示意见",
    "否定意见",
    "关联交易",
    "诉讼",
    "质押",
    "商誉减值",
    "应收账款",
]

# 章节关键词（用于年报结构识别）
SECTION_KEYWORDS = {
    "经营情况讨论与分析": ["经营情况", "主营业务", "行业情况"],
    "财务报告": ["合并资产负债表", "利润表", "现金流量表"],
    "附注": ["会计政策", "会计估计", "报表项目注释"],
    "公司治理": ["董事会", "监事会", "股东大会"],
    "重要事项": ["重大合同", "对外担保", "承诺事项"],
}


# ---------------------------------------------------------------------------
# 数据模型与校验
# ---------------------------------------------------------------------------

class AnnualReportData:
    """年报数据模型，负责数据的加载与基础校验。"""

    def __init__(self, raw_data: Dict[str, Any]):
        self.raw = raw_data
        self.company_name = raw_data.get("company_name", "未知公司")
        self.report_year = raw_data.get("report_year")
        self.financials = raw_data.get("financials", {})
        self.texts = raw_data.get("texts", {})
        self.notes = raw_data.get("notes", [])

    def validate(self) -> None:
        """校验数据完整性，缺失必要字段时抛出异常。"""
        if not self.report_year:
            raise ValueError("E005: 缺少报告年份 (report_year)")
        if not isinstance(self.report_year, int):
            raise ValueError("E006: 报告年份必须为整数")
        if not self.financials:
            raise ValueError("E005: 缺少财务数据 (financials)")
        if not isinstance(self.financials, dict):
            raise ValueError("E006: financials 必须为字典")

        # 校验核心指标是否存在
        for field in KEY_METRICS.keys():
            if field not in self.financials:
                raise ValueError(f"E005: 缺少核心财务指标 {field}")


# ---------------------------------------------------------------------------
# 核心分析引擎
# ---------------------------------------------------------------------------

class ReportAnalyzer:
    """年报分析引擎，负责核心逻辑处理。"""

    def __init__(self, data: AnnualReportData):
        self.data = data

    def analyze(self) -> Dict[str, Any]:
        """执行完整分析流程，返回结构化结果。"""
        result = {
            "company_name": self.data.company_name,
            "report_year": self.data.report_year,
            "generated_at": datetime.now().isoformat(),
            "sections": self._parse_sections(),
            "metrics": self._extract_metrics(),
            "trends": self._analyze_trends(),
            "risks": self._detect_risks(),
            "summary": self._generate_summary(),
        }
        return result

    def _parse_sections(self) -> List[Dict[str, Any]]:
        """C1: 年报结构解析 - 识别章节结构。"""
        sections = []
        text_content = self.data.texts.get("full_text", "")
        for section_name, keywords in SECTION_KEYWORDS.items():
            found = any(kw in text_content for kw in keywords)
            sections.append({
                "name": section_name,
                "found": found,
                "keywords_matched": [kw for kw in keywords if kw in text_content],
            })
        return sections

    def _extract_metrics(self) -> Dict[str, Any]:
        """C2: 关键财务指标提取 - 从三大报表中提取核心指标。"""
        metrics = {}
        for field, label in KEY_METRICS.items():
            value = self.data.financials.get(field)
            if value is None:
                metrics[field] = {"label": label, "value": None, "unit": "N/A"}
            else:
                metrics[field] = {
                    "label": label,
                    "value": value,
                    "unit": "%" if field in ("gross_margin", "debt_ratio", "roe") else "万元",
                }
        return metrics

    def _analyze_trends(self) -> Dict[str, Any]:
        """C3: 同比/环比趋势判断 - 对比近2-3年数据。"""
        trends = {}
        historical = self.data.financials.get("historical", {})

        for field in KEY_METRICS.keys():
            current = self.data.financials.get(field)
            prev = historical.get(field) if historical else None

            if current is None or prev is None or prev == 0:
                trends[field] = {"direction": "unknown", "change_pct": None}
                continue

            change_pct = ((current - prev) / abs(prev)) * 100
            direction = "up" if change_pct > 0 else ("down" if change_pct < 0 else "flat")
            trends[field] = {
                "direction": direction,
                "change_pct": round(change_pct, 2),
            }
        return trends

    def _detect_risks(self) -> List[Dict[str, str]]:
        """C4: 异常项标记 - 识别风险信号。"""
        risks = []
        text_content = self.data.texts.get("full_text", "")
        audit_opinion = self.data.texts.get("audit_opinion", "")

        # 审计意见检查
        if "保留" in audit_opinion:
            risks.append({"type": "审计意见", "detail": "保留意见", "level": "high"})
        if "无法表示" in audit_opinion:
            risks.append({"type": "审计意见", "detail": "无法表示意见", "level": "high"})
        if "否定" in audit_opinion:
            risks.append({"type": "审计意见", "detail": "否定意见", "level": "high"})

        # 关键词扫描
        for keyword in RISK_KEYWORDS:
            if keyword in text_content:
                risks.append({"type": "关键词", "detail": keyword, "level": "medium"})

        # 用户自定义注释中的风险
        for note in self.data.notes:
            if isinstance(note, dict) and note.get("type") == "risk":
                risks.append({"type": "用户标注", "detail": note.get("content", ""), "level": "medium"})

        return risks

    def _generate_summary(self) -> Dict[str, Any]:
        """C5: 结构化摘要输出 - 生成一页纸决策摘要。"""
        metrics = self._extract_metrics()
        trends = self._analyze_trends()
        risks = self._detect_risks()

        # 计算综合评级（仅供信息参考，不构成投资建议）
        score = 0
        for field, trend in trends.items():
            if trend["direction"] == "up":
                score += 1
            elif trend["direction"] == "down":
                score -= 1

        rating = "积极" if score >= 3 else ("中性" if score >= 0 else "谨慎")

        return {
            "rating": rating,
            "score": score,
            "key_findings": self._build_findings(metrics, trends),
            "risk_count": len(risks),
            "disclaimer": "本摘要由AI自动生成，仅供学习参考，不构成任何投资建议。",
        }

    def _build_findings(self, metrics: Dict, trends: Dict) -> List[str]:
        """构建关键发现列表。"""
        findings = []
        for field in KEY_METRICS.keys():
            metric = metrics[field]
            trend = trends[field]
            if metric["value"] is not None:
                direction_cn = {"up": "上升", "down": "下降", "flat": "持平", "unknown": "未知"}[trend["direction"]]
                change = f"（{direction_cn} {abs(trend['change_pct']):.1f}%）" if trend["change_pct"] is not None else ""
                findings.append(f"{metric['label']}: {metric['value']}{metric['unit']}{change}")
        return findings


# ---------------------------------------------------------------------------
# 输入输出处理
# ---------------------------------------------------------------------------

def load_input(filepath: str) -> Dict[str, Any]:
    """加载输入文件，支持 JSON 格式。"""
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"E002: 文件不存在 - {filepath}")

    ext = os.path.splitext(filepath)[1].lower()
    if ext != ".json":
        raise ValueError(f"E003: 不支持的格式 {ext}，仅支持 .json")

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"E004: JSON 解析失败 - {e}") from e


def save_output(data: Dict[str, Any], filepath: str) -> None:
    """保存输出结果到文件。"""
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except OSError as e:
        raise OSError(f"E008: 写入失败 - {e}") from e


def print_result(data: Dict[str, Any]) -> None:
    """控制台输出分析结果。"""
    print(f"\n{'='*60}")
    print(f"公司: {data['company_name']} ({data['report_year']}年)")
    print(f"生成时间: {data['generated_at']}")
    print(f"{'='*60}")

    print(f"\n【章节结构】")
    for section in data["sections"]:
        status = "✓" if section["found"] else "✗"
        print(f"  {status} {section['name']}")

    print(f"\n【核心指标】")
    for field, metric in data["metrics"].items():
        if metric["value"] is not None:
            print(f"  {metric['label']}: {metric['value']}{metric['unit']}")

    print(f"\n【趋势分析】")
    for field, trend in data["trends"].items():
        if trend["change_pct"] is not None:
            direction = {"up": "↑", "down": "↓", "flat": "→"}[trend["direction"]]
            print(f"  {KEY_METRICS[field]}: {direction} {trend['change_pct']:.1f}%")

    print(f"\n【风险提示】")
    if data["risks"]:
        for risk in data["risks"]:
            print(f"  [{risk['level']}] {risk['type']}: {risk['detail']}")
    else:
        print("  未发现明显风险信号")

    print(f"\n【决策摘要】")
    summary = data["summary"]
    print(f"  综合评级: {summary['rating']} (得分: {summary['score']})")
    print(f"  关键发现:")
    for finding in summary["key_findings"]:
        print(f"    - {finding}")
    print(f"\n  ⚠️ 免责声明: {summary['disclaimer']}")
    print(f"{'='*60}\n")


# ---------------------------------------------------------------------------
# 自检模块
# ---------------------------------------------------------------------------

def run_selftest() -> bool:
    """内置样例数据自检，不依赖外部文件/网络。"""
    print("开始自检...")

    # 构造内置测试数据
    sample_data = {
        "company_name": "示例科技股份有限公司",
        "report_year": 2025,
        "financials": {
            "revenue": 120000,
            "net_profit": 15000,
            "gross_margin": 35.5,
            "debt_ratio": 48.2,
            "roe": 12.8,
            "operating_cash_flow": 20000,
            "historical": {
                "revenue": 100000,
                "net_profit": 12000,
                "gross_margin": 33.0,
                "debt_ratio": 52.0,
                "roe": 11.0,
                "operating_cash_flow": 15000,
            },
        },
        "texts": {
            "full_text": "公司主营业务为软件开发，经营情况良好。董事会报告显示营业收入增长。"
                        "存在关联交易和应收账款风险。",
            "audit_opinion": "标准无保留意见",
        },
        "notes": [
            {"type": "risk", "content": "商誉减值风险"},
        ],
    }

    try:
        # 构建数据模型
        data = AnnualReportData(sample_data)
        data.validate()

        # 执行分析
        analyzer = ReportAnalyzer(data)
        result = analyzer.analyze()

        # 验证关键结果
        assert result["company_name"] == "示例科技股份有限公司", "公司名称解析失败"
        assert result["report_year"] == 2025, "报告年份解析失败"
        assert len(result["metrics"]) == 6, "核心指标数量不正确"
        assert result["trends"]["revenue"]["direction"] == "up", "营收趋势判断错误"
        assert result["trends"]["debt_ratio"]["direction"] == "down", "负债率趋势判断错误"
        assert len(result["risks"]) >= 2, "风险检测数量不足"
        assert result["summary"]["rating"] in ("积极", "中性", "谨慎"), "评级无效"

        # 验证输出结构完整性
        required_keys = ["company_name", "report_year", "generated_at", "sections",
                         "metrics", "trends", "risks", "summary"]
        for key in required_keys:
            assert key in result, f"缺少输出字段: {key}"

        # 验证趋势计算正确性
        assert result["trends"]["revenue"]["change_pct"] == 20.0, "营收增长率计算错误"
        assert result["trends"]["net_profit"]["change_pct"] == 25.0, "净利润增长率计算错误"

        print("✓ 自检通过: 所有断言验证成功")
        return True

    except Exception as e:
        print(f"✗ 自检失败: {e}")
        return False


# ---------------------------------------------------------------------------
# 主程序入口
# ---------------------------------------------------------------------------

def main() -> int:
    """主函数，处理命令行参数并执行分析。"""
    parser = argparse.ArgumentParser(
        description="年报速读 · 财务透视 · 决策辅助",
        epilog="示例: python main.py --input report.json --output summary.json"
    )
    parser.add_argument("--input", "-i", type=str, help="输入年报数据文件 (JSON格式)")
    parser.add_argument("--output", "-o", type=str, help="输出结果文件 (JSON格式)")
    parser.add_argument("--selftest", action="store_true", help="运行内置自检")

    args = parser.parse_args()

    try:
        # 自检模式
        if args.selftest:
            success = run_selftest()
            return 0 if success else 1

        # 正常处理模式
        if not args.input:
            raise ValueError("E001: 请指定输入文件 (--input) 或使用 --selftest")

        # 加载数据
        raw_data = load_input(args.input)
        data = AnnualReportData(raw_data)
        data.validate()

        # 执行分析
        analyzer = ReportAnalyzer(data)
        result = analyzer.analyze()

        # 输出结果
        if args.output:
            save_output(result, args.output)
            print(f"分析完成，结果已保存至: {args.output}")
        else:
            print_result(result)

        return 0

    except FileNotFoundError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1
    except ValueError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1
    except OSError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"E010: 未知异常 - {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
