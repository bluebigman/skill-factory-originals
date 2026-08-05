#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
competitor-analysis-ai Skill Runner
分析竞品信息，输出结构化报告
"""

import argparse
import json
import os
import sys
import re
from datetime import datetime
from typing import Dict, List, Optional, Any


def load_spec() -> Dict[str, Any]:
    """加载技能规格说明"""
    spec_path = os.path.join(os.path.dirname(__file__), "spec.json")
    with open(spec_path, "r", encoding="utf-8") as f:
        return json.load(f)


def match_trigger(user_input: str) -> bool:
    """判断输入是否匹配技能触发条件"""
    spec = load_spec()
    triggers = spec.get("triggers", [])
    for trigger in triggers:
        if trigger.lower() in user_input.lower():
            return True
    return False


class CompetitorAnalyzer:
    """竞品分析器"""

    def __init__(self, data: Dict[str, Any]):
        self.data = data
        self.competitors = data.get("competitors", [])
        self.metrics = data.get("metrics", [])
        self.thresholds = data.get("thresholds", {})

    def analyze(self) -> Dict[str, Any]:
        """执行分析，返回结构化结果"""
        analysis = {}
        analysis["generated_at"] = datetime.now().isoformat()
        analysis["total_competitors"] = len(self.competitors)
        analysis["competitor_names"] = [c.get("name", "未知") for c in self.competitors]

        # 分析每个竞品
        competitor_results = []
        for comp in self.competitors:
            comp_result = self._analyze_competitor(comp)
            competitor_results.append(comp_result)
        analysis["competitor_results"] = competitor_results

        # 汇总指标
        summary = self._generate_summary(competitor_results)
        analysis["summary"] = summary

        # 统计填充率
        filled = sum(1 for v in analysis.values() if v and not (isinstance(v, str) and v.startswith("[需核实")))
        total = len(analysis)
        analysis["completeness"] = f"{filled}/{total}"

        return analysis

    def _analyze_competitor(self, comp: Dict[str, Any]) -> Dict[str, Any]:
        """分析单个竞品"""
        result = {}
        result["name"] = comp.get("name", "未知")
        result["market_share"] = comp.get("market_share", "[需核实]")
        result["growth_rate"] = comp.get("growth_rate", "[需核实]")
        result["product_quality"] = comp.get("product_quality", "[需核实]")
        result["price_level"] = comp.get("price_level", "[需核实]")
        result["customer_satisfaction"] = comp.get("customer_satisfaction", "[需核实]")

        # 评分（可能是数字）
        score = comp.get("score")
        if score is not None:
            result["score"] = score
        else:
            result["score"] = "[需核实]"

        # 优势与劣势
        strengths = comp.get("strengths", [])
        weaknesses = comp.get("weaknesses", [])
        result["strengths"] = strengths if isinstance(strengths, list) else [strengths]
        result["weaknesses"] = weaknesses if isinstance(weaknesses, list) else [weaknesses]

        # 战略建议
        suggestions = comp.get("suggestions", [])
        result["suggestions"] = suggestions if isinstance(suggestions, list) else [suggestions]

        return result

    def _generate_summary(self, competitor_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """生成汇总信息"""
        summary = {}
        if not competitor_results:
            summary["status"] = "无竞品数据"
            return summary

        # 平均市场份额
        shares = []
        for r in competitor_results:
            share = r.get("market_share")
            if isinstance(share, (int, float)):
                shares.append(share)
        if shares:
            summary["avg_market_share"] = sum(shares) / len(shares)
        else:
            summary["avg_market_share"] = "[需核实]"

        # 平均增长率
        growths = []
        for r in competitor_results:
            growth = r.get("growth_rate")
            if isinstance(growth, (int, float)):
                growths.append(growth)
        if growths:
            summary["avg_growth_rate"] = sum(growths) / len(growths)
        else:
            summary["avg_growth_rate"] = "[需核实]"

        # 最高评分
        scores = []
        for r in competitor_results:
            score = r.get("score")
            if isinstance(score, (int, float)):
                scores.append(score)
        if scores:
            summary["max_score"] = max(scores)
            summary["best_competitor"] = competitor_results[scores.index(max(scores))]["name"]
        else:
            summary["max_score"] = "[需核实]"
            summary["best_competitor"] = "[需核实]"

        # 市场集中度
        if shares:
            total_share = sum(shares)
            if total_share > 0:
                top3 = sorted(shares, reverse=True)[:3]
                summary["market_concentration"] = sum(top3) / total_share
            else:
                summary["market_concentration"] = 0
        else:
            summary["market_concentration"] = "[需核实]"

        return summary


def selftest() -> int:
    """自检函数，验证技能功能"""
    print("Running selftest for competitor-analysis-ai...")

    # 测试数据
    test_data = {
        "competitors": [
            {
                "name": "竞品A",
                "market_share": 35.5,
                "growth_rate": 12.3,
                "product_quality": "高",
                "price_level": "中",
                "customer_satisfaction": 4.5,
                "score": 85,
                "strengths": ["品牌知名度高", "产品线丰富"],
                "weaknesses": ["价格偏高", "创新不足"],
                "suggestions": ["优化定价策略", "加大研发投入"]
            },
            {
                "name": "竞品B",
                "market_share": 28.2,
                "growth_rate": 8.7,
                "product_quality": "中",
                "price_level": "低",
                "customer_satisfaction": 4.0,
                "score": 78,
                "strengths": ["性价比高", "渠道覆盖广"],
                "weaknesses": ["品牌力弱", "售后服务一般"],
                "suggestions": ["提升品牌形象", "改善售后体验"]
            },
            {
                "name": "竞品C",
                "market_share": 15.8,
                "growth_rate": -3.2,
                "product_quality": "低",
                "price_level": "高",
                "customer_satisfaction": 3.2,
                "score": 62,
                "strengths": ["技术领先"],
                "weaknesses": ["价格过高", "市场定位模糊"],
                "suggestions": ["调整市场定位", "优化成本结构"]
            }
        ],
        "metrics": ["market_share", "growth_rate", "product_quality", "price_level", "customer_satisfaction"],
        "thresholds": {
            "market_share": 20,
            "growth_rate": 5,
            "customer_satisfaction": 4.0
        }
    }

    analyzer = CompetitorAnalyzer(test_data)
    results = analyzer.analyze()

    # 验证结果
    assert results["total_competitors"] == 3, "竞品数量错误"
    assert len(results["competitor_results"]) == 3, "竞品分析结果数量错误"
    assert "summary" in results, "缺少汇总信息"
    assert "completeness" in results, "缺少完整性统计"

    # 验证汇总数据
    summary = results["summary"]
    assert "avg_market_share" in summary, "缺少平均市场份额"
    assert "avg_growth_rate" in summary, "缺少平均增长率"
    assert "max_score" in summary, "缺少最高评分"
    assert "best_competitor" in summary, "缺少最佳竞品"

    # 验证竞品结果
    first_comp = results["competitor_results"][0]
    assert first_comp["name"] == "竞品A", "竞品名称错误"
    assert first_comp["score"] == 85, "评分错误"
    assert isinstance(first_comp["strengths"], list), "优势应为列表"
    assert isinstance(first_comp["weaknesses"], list), "劣势应为列表"

    # 验证完整性统计
    assert results["completeness"] != "0/0", "完整性统计异常"

    print("Selftest passed!")
    return 0


def main() -> int:
    """主入口"""
    parser = argparse.ArgumentParser(description="竞品分析工具")
    parser.add_argument("--selftest", action="store_true", help="运行自检")
    parser.add_argument("--input", type=str, help="输入JSON文件路径")
    parser.add_argument("--output", type=str, help="输出JSON文件路径")
    args = parser.parse_args()

    if args.selftest:
        return selftest()

    if args.input:
        try:
            with open(args.input, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            print(f"读取输入文件失败: {e}")
            return 1

        analyzer = CompetitorAnalyzer(data)
        results = analyzer.analyze()

        if args.output:
            try:
                with open(args.output, "w", encoding="utf-8") as f:
                    json.dump(results, f, ensure_ascii=False, indent=2)
                print(f"分析结果已保存到 {args.output}")
            except Exception as e:
                print(f"写入输出文件失败: {e}")
                return 1
        else:
            print(json.dumps(results, ensure_ascii=False, indent=2))
        return 0

    # 无参数时显示帮助
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
