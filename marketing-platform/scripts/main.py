#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
营销数据解析与合规审查 - 独立实现脚本
=====================================
依据功能规格独立开发，不参考任何既有实现。

功能概述:
    - C1: 将文本内容解析为结构化字段
    - C2: 提取关键实体（日期、金额、义务条款等）
    - C3: 按指定格式输出（默认 JSON）
    - C4: 置信度标注（高/中/低）
    - C5: 批量处理（多段文本）

错误码:
    E001: 输入为空
    E002: 输入不是字符串
    E003: 日期解析失败
    E004: 金额解析失败
    E005: 输出格式不支持
    E006: 批量输入格式错误
    E007: 文件名非法
    E008: 写入文件失败
    E009: 参数缺失
    E010: 未知错误

用法:
    python main.py --input "文本内容" [--format json|text]
    python main.py --batch '["文本1", "文本2"]'
    python main.py --selftest
"""

import argparse
import json
import re
import sys
import os
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union


# ============================================================
# 常量定义
# ============================================================

# 错误码映射
ERROR_CODES = {
    "E001": "输入为空",
    "E002": "输入不是字符串",
    "E003": "日期解析失败",
    "E004": "金额解析失败",
    "E005": "输出格式不支持",
    "E006": "批量输入格式错误",
    "E007": "文件名非法",
    "E008": "写入文件失败",
    "E009": "参数缺失",
    "E010": "未知错误",
}

# 置信度等级
CONFIDENCE_HIGH = "高"
CONFIDENCE_MEDIUM = "中"
CONFIDENCE_LOW = "低"

# 默认输出字段模板
DEFAULT_FIELDS = ["条款名称", "生效日期", "关键义务", "金额", "置信度"]


# ============================================================
# 工具函数
# ============================================================

def _now_str() -> str:
    """返回当前时间字符串"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _make_error(code: str, detail: str = "") -> Dict[str, str]:
    """构造错误信息字典"""
    msg = ERROR_CODES.get(code, "未知错误")
    result = {"error_code": code, "error_message": msg}
    if detail:
        result["detail"] = detail
    return result


def _safe_float(value: Any) -> Optional[float]:
    """安全转换为浮点数，失败返回 None"""
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def _safe_int(value: Any) -> Optional[int]:
    """安全转换为整数，失败返回 None"""
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def _is_valid_date_str(text: str) -> bool:
    """检查字符串是否为常见日期格式"""
    patterns = [
        r"\d{4}[-/年]\d{1,2}[-/月]\d{1,2}日?",
        r"\d{1,2}[-/]\d{1,2}[-/]\d{2,4}",
        r"\d{4}年\d{1,2}月\d{1,2}日",
    ]
    for pat in patterns:
        if re.search(pat, text):
            return True
    return False


def _extract_dates(text: str) -> List[str]:
    """从文本中提取日期字符串"""
    dates = []
    patterns = [
        r"\d{4}[-/年]\d{1,2}[-/月]\d{1,2}日?",
        r"\d{1,2}[-/]\d{1,2}[-/]\d{2,4}",
    ]
    for pat in patterns:
        matches = re.findall(pat, text)
        for m in matches:
            # 标准化格式
            normalized = m.replace("年", "-").replace("月", "-").replace("日", "")
            normalized = normalized.replace("/", "-")
            if normalized not in dates:
                dates.append(normalized)
    return dates


def _extract_amounts(text: str) -> List[Dict[str, Any]]:
    """从文本中提取金额信息"""
    amounts = []
    # 匹配人民币金额: 数字 + 万元/元/块
    pattern = r"([1-9]\d*(?:\.\d+)?)\s*(万元|元|块|人民币)"
    matches = re.findall(pattern, text)
    for num_str, unit in matches:
        num = _safe_float(num_str)
        if num is None:
            continue
        amount = num
        if unit == "万元":
            amount = num * 10000
        elif unit == "块":
            amount = num
        amounts.append({
            "原始值": f"{num_str}{unit}",
            "数值": amount,
            "单位": unit,
        })
    return amounts


def _extract_obligations(text: str) -> List[str]:
    """提取关键义务条款"""
    obligations = []
    # 常见义务关键词
    keywords = ["应当", "必须", "有义务", "需", "应", "不得", "禁止"]
    sentences = re.split(r"[。；;]", text)
    for sent in sentences:
        sent = sent.strip()
        if not sent:
            continue
        for kw in keywords:
            if kw in sent:
                obligations.append(sent)
                break
    return obligations


def _extract_clause_name(text: str) -> str:
    """提取条款名称"""
    # 常见条款标题模式
    patterns = [
        r"(?:第[一二三四五六七八九十\d]+[条章][^\n]{0,20})",
        r"(?:条款名称[：:]\s*([^\n]+))",
        r"(?:协议名称[：:]\s*([^\n]+))",
        r"(?:合同名称[：:]\s*([^\n]+))",
    ]
    for pat in patterns:
        match = re.search(pat, text)
        if match:
            # 如果有捕获组，取第一个
            if match.groups() and match.group(1):
                return match.group(1).strip()
            return match.group(0).strip()
    return "未命名条款"


# ============================================================
# 核心解析引擎
# ============================================================

class MarketingDataParser:
    """
    营销数据解析器
    
    将营销平台相关文本内容解析为结构化字段，
    并标注置信度。
    """

    def __init__(self, verbose: bool = False):
        self.verbose = verbose

    def parse(self, text: str) -> Dict[str, Any]:
        """
        解析单段文本
        
        参数:
            text: 输入文本
        
        返回:
            结构化字典
        """
        # 输入校验
        if text is None:
            return _make_error("E001", "输入为空")
        if not isinstance(text, str):
            return _make_error("E002", f"输入类型为 {type(text).__name__}")
        text = text.strip()
        if not text:
            return _make_error("E001", "输入为空")

        # 初始化结果
        result: Dict[str, Any] = {
            "解析时间": _now_str(),
            "输入长度": len(text),
        }

        # 提取条款名称
        clause_name = _extract_clause_name(text)
        result["条款名称"] = clause_name

        # 提取日期
        dates = _extract_dates(text)
        if dates:
            result["生效日期"] = dates[0]
            result["全部日期"] = dates
            date_conf = CONFIDENCE_HIGH
        else:
            result["生效日期"] = "[需核实:生效日期]"
            result["全部日期"] = []
            date_conf = CONFIDENCE_LOW

        # 提取金额
        amounts = _extract_amounts(text)
        if amounts:
            result["金额"] = amounts
            amount_conf = CONFIDENCE_HIGH
        else:
            result["金额"] = []
            amount_conf = CONFIDENCE_LOW

        # 提取义务条款
        obligations = _extract_obligations(text)
        if obligations:
            result["关键义务"] = obligations
            oblig_conf = CONFIDENCE_HIGH
        else:
            result["关键义务"] = []
            oblig_conf = CONFIDENCE_LOW

        # 置信度综合评估
        conf_scores = [date_conf, amount_conf, oblig_conf]
        if CONFIDENCE_LOW in conf_scores:
            overall_conf = CONFIDENCE_MEDIUM
        elif CONFIDENCE_HIGH in conf_scores:
            overall_conf = CONFIDENCE_HIGH
        else:
            overall_conf = CONFIDENCE_LOW

        result["置信度"] = overall_conf

        # 置信度明细
        result["置信度明细"] = {
            "日期": date_conf,
            "金额": amount_conf,
            "义务": oblig_conf,
        }

        # 数据完整性标记
        if not dates or not amounts or not obligations:
            result["数据完整性"] = "部分字段缺失，请人工核实"
        else:
            result["数据完整性"] = "完整"

        return result

    def parse_batch(self, texts: List[str]) -> List[Dict[str, Any]]:
        """
        批量解析多段文本
        
        参数:
            texts: 文本列表
        
        返回:
            结果列表
        """
        if not isinstance(texts, list):
            return [_make_error("E006", "批量输入必须是列表")]
        return [self.parse(t) for t in texts]

    def parse_with_template(
        self, text: str, fields: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        按自定义字段模板解析
        
        参数:
            text: 输入文本
            fields: 需要的字段列表
        
        返回:
            包含指定字段的结果
        """
        full_result = self.parse(text)
        if "error_code" in full_result:
            return full_result

        if fields is None:
            fields = DEFAULT_FIELDS

        filtered = {}
        for f in fields:
            if f in full_result:
                filtered[f] = full_result[f]
            else:
                filtered[f] = "[需核实:字段缺失]"
        return filtered


# ============================================================
# 输出格式化
# ============================================================

def format_output(data: Any, fmt: str = "json") -> str:
    """
    格式化输出
    
    参数:
        data: 数据
        fmt: 格式 (json / text)
    
    返回:
        格式化后的字符串
    """
    if fmt == "json":
        return json.dumps(data, ensure_ascii=False, indent=2)
    elif fmt == "text":
        if isinstance(data, dict):
            lines = []
            for k, v in data.items():
                if isinstance(v, (dict, list)):
                    lines.append(f"{k}: {json.dumps(v, ensure_ascii=False)}")
                else:
                    lines.append(f"{k}: {v}")
            return "\n".join(lines)
        return str(data)
    else:
        return json.dumps(_make_error("E005", f"不支持的格式: {fmt}"))


# ============================================================
# 自检模块
# ============================================================

def run_selftest() -> bool:
    """
    内置自检逻辑
    
    使用硬编码样例数据验证核心功能，
    不依赖外部文件、网络或当前工作目录。
    
    返回:
        True 表示全部通过
    """
    print("=" * 60)
    print("开始自检 (Self-Test)")
    print("=" * 60)

    parser = MarketingDataParser(verbose=False)

    # ---------- 测试用例 1: 基本解析 ----------
    print("\n[测试1] 基本解析")
    sample1 = (
        "营销平台服务协议\n"
        "生效日期：2024年3月15日\n"
        "甲方应当按时支付服务费用，违约金 5 万元。\n"
        "乙方必须保证数据安全，不得泄露用户信息。"
    )
    result1 = parser.parse(sample1)
    
    # 宽松断言
    assert "error_code" not in result1, f"测试1失败: {result1}"
    assert result1["条款名称"] != "", "条款名称不应为空"
    assert result1["生效日期"] != "[需核实:生效日期]", "应识别出生效日期"
    assert len(result1["关键义务"]) > 0, "应提取到义务条款"
    assert len(result1["金额"]) > 0, "应提取到金额"
    print("  ✓ 基本解析通过")
    print(f"    条款名称: {result1['条款名称']}")
    print(f"    生效日期: {result1['生效日期']}")
    print(f"    义务数: {len(result1['关键义务'])}")
    print(f"    金额数: {len(result1['金额'])}")

    # ---------- 测试用例 2: 空输入处理 ----------
    print("\n[测试2] 空输入处理")
    result2 = parser.parse("")
    assert "error_code" in result2, "空输入应返回错误"
    assert result2["error_code"] == "E001", "错误码应为 E001"
    print("  ✓ 空输入处理通过")

    # ---------- 测试用例 3: 非字符串输入 ----------
    print("\n[测试3] 非字符串输入")
    result3 = parser.parse(12345)
    assert "error_code" in result3, "非字符串应返回错误"
    assert result3["error_code"] == "E002", "错误码应为 E002"
    print("  ✓ 非字符串处理通过")

    # ---------- 测试用例 4: 批量解析 ----------
    print("\n[测试4] 批量解析")
    batch_input = [
        "合同A 违约金 10 万元，甲方应当履行义务。",
        "协议B 生效日期：2025年1月1日，乙方必须遵守规定。",
    ]
    batch_result = parser.parse_batch(batch_input)
    assert len(batch_result) == 2, "批量解析应返回2个结果"
    for r in batch_result:
        assert "error_code" not in r, f"批量解析失败: {r}"
    print("  ✓ 批量解析通过")

    # ---------- 测试用例 5: 自定义模板 ----------
    print("\n[测试5] 自定义模板")
    sample5 = "测试协议 甲方应支付 5000 元。"
    custom_fields = ["条款名称", "金额"]
    result5 = parser.parse_with_template(sample5, custom_fields)
    assert "error_code" not in result5, f"自定义模板失败: {result5}"
    assert "条款名称" in result5, "应包含条款名称"
    assert "金额" in result5, "应包含金额"
    assert "关键义务" not in result5, "不应包含未请求的字段"
    print("  ✓ 自定义模板通过")

    # ---------- 测试用例 6: 输出格式化 ----------
    print("\n[测试6] 输出格式化")
    json_out = format_output(result1, "json")
    assert isinstance(json_out, str), "JSON输出应为字符串"
    assert "条款名称" in json_out, "JSON输出应包含关键字段"
    
    text_out = format_output(result1, "text")
    assert isinstance(text_out, str), "文本输出应为字符串"
    assert "条款名称" in text_out, "文本输出应包含关键字段"
    
    invalid_out = format_output(result1, "xml")
    assert "E005" in invalid_out, "不支持格式应返回错误"
    print("  ✓ 输出格式化通过")

    # ---------- 测试用例 7: 金额提取 ----------
    print("\n[测试7] 金额提取")
    sample7 = "合同金额为 50 万元，另需支付手续费 2000 元。"
    amounts7 = _extract_amounts(sample7)
    assert len(amounts7) >= 2, "应提取到多个金额"
    # 验证万元转换
    wan_amounts = [a for a in amounts7 if a["单位"] == "万元"]
    assert len(wan_amounts) > 0, "应包含万元金额"
    if wan_amounts:
        assert wan_amounts[0]["数值"] == 500000, "50万元应转换为500000元"
    print("  ✓ 金额提取通过")

    # ---------- 测试用例 8: 日期提取 ----------
    print("\n[测试8] 日期提取")
    sample8 = "本协议自2024年6月30日起生效，有效期至2025年6月29日。"
    dates8 = _extract_dates(sample8)
    assert len(dates8) >= 2, "应提取到多个日期"
    print(f"  提取日期: {dates8}")
    print("  ✓ 日期提取通过")

    # ---------- 测试用例 9: 义务提取 ----------
    print("\n[测试9] 义务提取")
    sample9 = "甲方应当按时交付，乙方必须保密，双方不得违约。"
    obligations9 = _extract_obligations(sample9)
    assert len(obligations9) >= 3, "应提取到至少3条义务"
    print(f"  提取义务数: {len(obligations9)}")
    print("  ✓ 义务提取通过")

    # ---------- 测试用例 10: 错误码完整性 ----------
    print("\n[测试10] 错误码完整性")
    for code in ERROR_CODES:
        assert len(code) == 4, f"错误码格式错误: {code}"
        assert code.startswith("E0"), f"错误码前缀错误: {code}"
    assert len(ERROR_CODES) == 10, "应有10个错误码"
    print("  ✓ 错误码完整性通过")

    # ---------- 汇总 ----------
    print("\n" + "=" * 60)
    print("自检全部通过 ✓")
    print("=" * 60)
    return True


# ============================================================
# 命令行入口
# ============================================================

def main() -> int:
    """
    主入口函数
    
    返回:
        退出码 (0 成功, 非0 失败)
    """
    parser = argparse.ArgumentParser(
        description="营销数据解析与合规审查工具",
        epilog="示例: python main.py --input '合同文本...' --format json",
    )
    parser.add_argument(
        "--input", "-i",
        type=str,
        help="输入文本内容",
    )
    parser.add_argument(
        "--batch", "-b",
        type=str,
        help="批量输入，JSON数组字符串，如 '[\"文本1\", \"文本2\"]'",
    )
    parser.add_argument(
        "--format", "-f",
        type=str,
        default="json",
        choices=["json", "text"],
        help="输出格式 (默认: json)",
    )
    parser.add_argument(
        "--fields",
        type=str,
        help="自定义输出字段，逗号分隔，如 '条款名称,金额'",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="显示详细日志",
    )

    # 解析参数
    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        try:
            success = run_selftest()
            return 0 if success else 1
        except AssertionError as e:
            print(f"自检失败: {e}")
            return 1
        except Exception as e:
            print(f"自检异常: {e}")
            return 1

    # 检查是否提供了输入
    if not args.input and not args.batch:
        print("错误: 请提供 --input 或 --batch 参数")
        print(f"错误码: E009 - {ERROR_CODES['E009']}")
        print("使用 --selftest 运行自检")
        return 1

    # 创建解析器
    parser_engine = MarketingDataParser(verbose=args.verbose)

    # 处理批量输入
    if args.batch:
        try:
            texts = json.loads(args.batch)
            if not isinstance(texts, list):
                print(f"错误码: E006 - {ERROR_CODES['E006']}")
                return 1
            results = parser_engine.parse_batch(texts)
        except json.JSONDecodeError:
            print(f"错误码: E006 - {ERROR_CODES['E006']}")
            return 1
    else:
        # 处理单个输入
        results = parser_engine.parse(args.input)

    # 自定义字段过滤
    if args.fields:
        field_list = [f.strip() for f in args.fields.split(",") if f.strip()]
        if isinstance(results, list):
            results = [
                {k: v for k, v in r.items() if k in field_list}
                if "error_code" not in r
                else r
                for r in results
            ]
        elif isinstance(results, dict) and "error_code" not in results:
            results = {k: v for k, v in results.items() if k in field_list}

    # 输出结果
    output = format_output(results, args.format)
    print(output)

    return 0


if __name__ == "__main__":
    sys.exit(main())
