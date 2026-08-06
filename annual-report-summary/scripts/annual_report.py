#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
annual-report-summary Skill v2.0.0
从年报文本中提取关键财务指标并生成结构化决策简报

用法:
    python run.py --text "年报文本"
    python run.py --file annual_report.txt
    python run.py --json --text "年报文本"
    python run.py --selftest
"""

import re
import json
import argparse
import sys
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timezone
from pathlib import Path

__version__ = "2.0.0"

# ============================================================
# 常量定义
# ============================================================

CORE_INDICATORS = ["roe", "net_profit_growth", "revenue", "gross_margin", "operating_cashflow"]

ERROR_CODES = {
    "SUCCESS": 0,
    "PARAM_ERROR": 1,
    "EMPTY_INPUT": 2,
    "NO_MATCH": 3,
    "FILE_ERROR": 4,
    "INTERNAL_ERROR": 5,
}

# ============================================================
# 指标提取器
# ============================================================

class IndicatorExtractor:
    """从年报文本中提取财务指标"""
    
    def __init__(self, text: str):
        self.text = text
        self.results: Dict[str, Dict[str, Any]] = {}
    
    def _extract(self, patterns: List[str], key: str, label: str, 
                 normalize: bool = True) -> Optional[str]:
        """通用提取方法"""
        for pattern in patterns:
            match = re.search(pattern, self.text, re.IGNORECASE)
            if match:
                value = match.group(1).strip()
                if normalize:
                    value = self._normalize_value(value)
                self.results[key] = {
                    "label": label,
                    "value": value,
                    "raw": match.group(0),
                    "confidence": "HIGH" if len(patterns) > 2 else "MEDIUM"
                }
                return value
        return None
    
    def _normalize_value(self, value: str) -> str:
        """标准化数值：去除多余空格，统一单位"""
        value = value.strip()
        # 去除百分号前的空格
        value = re.sub(r'\s+%', '%', value)
        # 统一负号
        value = value.replace('（', '(').replace('）', ')')
        return value
    
    def extract_roe(self) -> Optional[str]:
        """提取ROE（净资产收益率）"""
        patterns = [
            r'加权平均净资产收益率[：:为\s]*([-+]?\d+\.?\d*\s*%?)',
            r'净资产收益率\s*[（(]ROE[）)]\s*[：:为\s]*([-+]?\d+\.?\d*\s*%?)',
            r'ROE\s*[（(]净资产收益率[）)]\s*[：:为\s]*([-+]?\d+\.?\d*\s*%?)',
            r'净资产收益率[：:为\s]*([-+]?\d+\.?\d*\s*%?)',
            r'ROE[：:为\s]*([-+]?\d+\.?\d*\s*%?)',
            r'扣非加权平均净资产收益率[：:为\s]*([-+]?\d+\.?\d*\s*%?)',
        ]
        return self._extract(patterns, "roe", "净资产收益率(ROE)")
    
    def extract_net_profit_growth(self) -> Optional[str]:
        """提取净利润增长率"""
        patterns = [
            r'净利润增长率[：:为\s]*([-+]?\d+\.?\d*\s*%?)',
            r'净利润同比增长[：:为\s]*([-+]?\d+\.?\d*\s*%?)',
            r'净利润同比变化[：:为\s]*([-+]?\d+\.?\d*\s*%?)',
            r'净利润同比[：:为\s]*([-+]?\d+\.?\d*\s*%?)',
        ]
        return self._extract(patterns, "net_profit_growth", "净利润增长率")
    
    def extract_revenue(self) -> Tuple[Optional[str], Optional[str]]:
        """提取营业收入及增长率"""
        # 提取营收金额
        revenue_patterns = [
            r'营业收入[：:为\s]*([-+]?\d+\.?\d*\s*[万亿千百]?元?)',
            r'营收[：:为\s]*([-+]?\d+\.?\d*\s*[万亿千百]?元?)',
            r'营业总收入[：:为\s]*([-+]?\d+\.?\d*\s*[万亿千百]?元?)',
        ]
        revenue = self._extract(revenue_patterns, "revenue", "营业收入")
        
        # 提取营收增长率
        growth_patterns = [
            r'营业收入增长率[：:为\s]*([-+]?\d+\.?\d*\s*%?)',
            r'营收增长率[：:为\s]*([-+]?\d+\.?\d*\s*%?)',
            r'营业收入同比增长[：:为\s]*([-+]?\d+\.?\d*\s*%?)',
            r'营收同比增长[：:为\s]*([-+]?\d+\.?\d*\s*%?)',
        ]
        growth = self._extract(growth_patterns, "revenue_growth", "营收增长率")
        
        return revenue, growth
    
    def extract_gross_margin(self) -> Optional[str]:
        """提取毛利率"""
        patterns = [
            r'毛利率[：:为\s]*([-+]?\d+\.?\d*\s*%?)',
            r'销售毛利率[：:为\s]*([-+]?\d+\.?\d*\s*%?)',
            r'综合毛利率[：:为\s]*([-+]?\d+\.?\d*\s*%?)',
        ]
        return self._extract(patterns, "gross_margin", "毛利率")
    
    def extract_net_margin(self) -> Optional[str]:
        """提取净利率"""
        patterns = [
            r'净利率[：:为\s]*([-+]?\d+\.?\d*\s*%?)',
            r'销售净利率[：:为\s]*([-+]?\d+\.?\d*\s*%?)',
        ]
        return self._extract(patterns, "net_margin", "净利率")
    
    def extract_debt_ratio(self) -> Optional[str]:
        """提取资产负债率"""
        patterns = [
            r'资产负债率[：:为\s]*([-+]?\d+\.?\d*\s*%?)',
            r'负债率[：:为\s]*([-+]?\d+\.?\d*\s*%?)',
        ]
        return self._extract(patterns, "debt_ratio", "资产负债率")
    
    def extract_operating_cashflow(self) -> Optional[str]:
        """提取经营现金流净额"""
        patterns = [
            r'经营活动产生的现金流量净额[：:为\s]*([-+]?\d+\.?\d*\s*[万亿千百]?元?)',
            r'经营现金流净额[：:为\s]*([-+]?\d+\.?\d*\s*[万亿千百]?元?)',
            r'经营性现金流[：:为\s]*([-+]?\d+\.?\d*\s*[万亿千百]?元?)',
        ]
        return self._extract(patterns, "operating_cashflow", "经营现金流净额")
    
    def extract_eps(self) -> Optional[str]:
        """提取每股收益"""
        patterns = [
            r'基本每股收益[：:为\s]*([-+]?\d+\.?\d*\s*元?)',
            r'每股收益[：:为\s]*([-+]?\d+\.?\d*\s*元?)',
            r'EPS[：:为\s]*([-+]?\d+\.?\d*\s*元?)',
        ]
        return self._extract(patterns, "eps", "每股收益(EPS)")
    
    def extract_rd_ratio(self) -> Optional[str]:
        """提取研发费用率"""
        patterns = [
            r'研发费用率[：:为\s]*([-+]?\d+\.?\d*\s*%?)',
            r'研发投入占比[：:为\s]*([-+]?\d+\.?\d*\s*%?)',
            r'研发费用占营业收入比例[：:为\s]*([-+]?\d+\.?\d*\s*%?)',
        ]
        return self._extract(patterns, "rd_ratio", "研发费用率")
    
    def extract_goodwill(self) -> Optional[str]:
        """提取商誉"""
        patterns = [
            r'商誉[：:为\s]*([-+]?\d+\.?\d*\s*[万亿千百]?元?)',
            r'商誉账面价值[：:为\s]*([-+]?\d+\.?\d*\s*[万亿千百]?元?)',
        ]
        return self._extract(patterns, "goodwill", "商誉")
    
    def extract_audit_opinion(self) -> Optional[str]:
        """提取审计意见类型"""
        patterns = [
            r'审计意见[：:为\s]*([^。；\n]+)',
            r'审计报告意见类型[：:为\s]*([^。；\n]+)',
        ]
        for pattern in patterns:
            match = re.search(pattern, self.text)
            if match:
                opinion = match.group(1).strip()
                # 判断意见类型
                if "标准" in opinion or "无保留" in opinion:
                    opinion_type = "标准无保留意见"
                elif "保留" in opinion:
                    opinion_type = "保留意见"
                elif "否定" in opinion:
                    opinion_type = "否定意见"
                elif "无法表示" in opinion:
                    opinion_type = "无法表示意见"
                else:
                    opinion_type = opinion
                
                self.results["audit_opinion"] = {
                    "label": "审计意见",
                    "value": opinion_type,
                    "raw": match.group(0),
                    "confidence": "HIGH"
                }
                return opinion_type
        return None
    
    def extract_all(self) -> Dict[str, Dict[str, Any]]:
        """执行所有提取"""
        self.extract_roe()
        self.extract_net_profit_growth()
        self.extract_revenue()
        self.extract_gross_margin()
        self.extract_net_margin()
        self.extract_debt_ratio()
        self.extract_operating_cashflow()
        self.extract_eps()
        self.extract_rd_ratio()
        self.extract_goodwill()
        self.extract_audit_opinion()
        return self.results


# ============================================================
# 摘要生成器
# ============================================================

class SummaryGenerator:
    """生成人类可读的摘要"""
    
    def __init__(self, results: Dict[str, Dict[str, Any]]):
        self.results = results
    
    def generate_text(self) -> str:
        """生成文本摘要"""
        if not self.results:
            return "未提取到任何财务指标，请检查输入文本。"
        
        lines = ["=" * 50, "年报财务摘要", "=" * 50]
        
        # 核心指标
        core_found = 0
        for key in CORE_INDICATORS:
            if key in self.results:
                core_found += 1
                item = self.results[key]
                lines.append(f"  {item['label']}: {item['value']}")
        
        # 其他指标
        other_keys = [k for k in self.results.keys() if k not in CORE_INDICATORS]
        if other_keys:
            lines.append("-" * 50)
            lines.append("其他指标:")
            for key in other_keys:
                item = self.results[key]
                lines.append(f"  {item['label']}: {item['value']}")
        
        # 置信度评估
        lines.append("-" * 50)
        if core_found >= 5:
            confidence = "HIGH - 数据完整"
        elif core_found >= 2:
            confidence = "MEDIUM - 部分指标未提取"
        else:
            confidence = "LOW - 数据不足，请检查输入文本"
        lines.append(f"置信度: {confidence}")
        
        lines.append("=" * 50)
        lines.append("免责声明: 本摘要仅供学习参考，不构成投资建议。")
        
        return "\n".join(lines)
    
    def generate_json(self) -> str:
        """生成JSON摘要"""
        output = {
            "version": __version__,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "indicators": {},
            "confidence": "UNKNOWN"
        }
        
        # 统计核心指标
        core_found = sum(1 for k in CORE_INDICATORS if k in self.results)
        if core_found >= 5:
            output["confidence"] = "HIGH"
        elif core_found >= 2:
            output["confidence"] = "MEDIUM"
        else:
            output["confidence"] = "LOW"
        
        # 填充指标
        for key, item in self.results.items():
            output["indicators"][key] = {
                "label": item["label"],
                "value": item["value"],
                "confidence": item["confidence"]
            }
        
        return json.dumps(output, ensure_ascii=False, indent=2)


# ============================================================
# 主程序
# ============================================================

def parse_args() -> argparse.Namespace:
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="年报速读 - 从年报文本中提取关键财务指标",
        epilog="示例: python run.py --file annual_report.txt --json"
    )
    parser.add_argument("--text", type=str, help="年报文本内容")
    parser.add_argument("--file", type=str, help="年报文本文件路径")
    parser.add_argument("--json", action="store_true", help="输出JSON格式")
    parser.add_argument("--selftest", action="store_true", help="运行自检")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser.parse_args()


def read_input(args: argparse.Namespace) -> Tuple[str, int]:
    """读取输入文本，返回(文本, 错误码)"""
    if args.text:
        text = args.text.strip()
    elif args.file:
        try:
            text = Path(args.file).read_text(encoding="utf-8").strip()
        except Exception as e:
            print(f"错误: 无法读取文件 {args.file}: {e}", file=sys.stderr)
            return "", ERROR_CODES["FILE_ERROR"]
    else:
        print("错误: 必须提供 --text 或 --file 参数", file=sys.stderr)
        return "", ERROR_CODES["PARAM_ERROR"]
    
    if len(text) < 10:
        print("错误: 输入文本过短（至少10个字符）", file=sys.stderr)
        return "", ERROR_CODES["EMPTY_INPUT"]
    
    return text, ERROR_CODES["SUCCESS"]


def run_selftest() -> int:
    """运行自检，验证核心功能"""
    print("=" * 60)
    print("运行自检...")
    print("=" * 60)
    
    # 测试用例
    test_cases = [
        {
            "name": "完整年报示例",
            "text": """
            公司2023年度报告显示，营业收入为12.5亿元，同比增长18.2%。
            净利润增长率为23.5%，净资产收益率(ROE)为15.2%。
            毛利率为35.7%，净利率为12.1%，资产负债率为58.3%。
            经营活动产生的现金流量净额为8.5亿元，基本每股收益为1.25元。
            研发费用率为7.2%，商誉为3.2亿元。
            审计意见为标准无保留意见。
            """,
            "expected": {
                "roe": "15.2%",
                "net_profit_growth": "23.5%",
                "revenue": "12.5亿元",
                "gross_margin": "35.7%",
                "operating_cashflow": "8.5亿元"
            }
        },
        {
            "name": "部分指标示例",
            "text": "公司ROE为10.5%，净利润同比增长5.2%。",
            "expected": {
                "roe": "10.5%",
                "net_profit_growth": "5.2%"
            }
        },
        {
            "name": "无匹配示例",
            "text": "这是一段没有财务指标的年报文本内容。",
            "expected": {}
        }
    ]
    
    all_passed = True
    
    for i, case in enumerate(test_cases, 1):
        print(f"\n测试 {i}: {case['name']}")
        extractor = IndicatorExtractor(case["text"])
        results = extractor.extract_all()
        
        # 验证预期指标
        for key, expected_value in case["expected"].items():
            if key in results:
                actual_value = results[key]["value"]
                if actual_value == expected_value:
                    print(f"  ✓ {key}: {actual_value}")
                else:
                    print(f"  ✗ {key}: 期望 {expected_value}, 实际 {actual_value}")
                    all_passed = False
            else:
                print(f"  ✗ {key}: 未提取到")
                all_passed = False
        
        # 验证不应存在的指标
        for key in case["expected"]:
            if key not in results and key in case["expected"]:
                pass  # 已在上面处理
    
    # 验证JSON输出
    print("\n验证JSON输出...")
    extractor = IndicatorExtractor(test_cases[0]["text"])
    results = extractor.extract_all()
    generator = SummaryGenerator(results)
    json_output = generator.generate_json()
    try:
        json_data = json.loads(json_output)
        if "timestamp" in json_data and "indicators" in json_data:
            print("  ✓ JSON格式正确")
        else:
            print("  ✗ JSON缺少必要字段")
            all_passed = False
    except json.JSONDecodeError as e:
        print(f"  ✗ JSON解析失败: {e}")
        all_passed = False
    
    # 验证文本输出
    print("\n验证文本输出...")
    text_output = generator.generate_text()
    if "年报财务摘要" in text_output:
        print("  ✓ 文本摘要格式正确")
    else:
        print("  ✗ 文本摘要格式错误")
        all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("自检通过 ✓")
        return ERROR_CODES["SUCCESS"]
    else:
        print("自检失败 ✗")
        return ERROR_CODES["INTERNAL_ERROR"]


def main() -> int:
    """主函数"""
    args = parse_args()
    
    # 自检模式
    if args.selftest:
        return run_selftest()
    
    # 读取输入
    text, error_code = read_input(args)
    if error_code != ERROR_CODES["SUCCESS"]:
        return error_code
    
    try:
        # 提取指标
        extractor = IndicatorExtractor(text)
        results = extractor.extract_all()
        
        if not results:
            print("警告: 未提取到任何财务指标，请检查输入文本是否包含相关数据。", file=sys.stderr)
            return ERROR_CODES["NO_MATCH"]
        
        # 生成输出
        generator = SummaryGenerator(results)
        if args.json:
            print(generator.generate_json())
        else:
            print(generator.generate_text())
        
        return ERROR_CODES["SUCCESS"]
    
    except Exception as e:
        print(f"错误: 处理过程中发生异常: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return ERROR_CODES["INTERNAL_ERROR"]


if __name__ == "__main__":
    sys.exit(main())
