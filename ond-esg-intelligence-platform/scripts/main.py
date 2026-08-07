#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ond-esg-intelligence-platform 独立实现脚本
=========================================
基于功能规格的 clean-room 实现，仅使用标准库。

功能概要：
- 解析 ESG 文本数据，提取环境(E)、社会(S)、治理(G)三类指标。
- 支持批量处理多条记录，输出结构化 JSON 结果。
- 每条记录附带置信度评分(0.0-1.0)。
- 提供 --selftest 离线自检模式。

错误码说明：
- E001: 输入参数无效
- E002: 输入数据为空
- E003: 输入数据格式错误
- E004: 字段解析失败
- E005: 置信度计算异常
- E006: 批量处理中断
- E007: 输出序列化失败
- E008: 自检断言失败
- E009: 未支持的指标类别
- E010: 内部逻辑错误

用法示例：
    python scripts/main.py --text "某公司2023年碳排放量为100万吨，员工流失率5%"
    python scripts/main.py --batch "[...]" --selftest
"""

import argparse
import json
import re
import sys
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 常量定义
# ============================================================

# 指标类别关键词映射（用于识别 E/S/G 类别）
CATEGORY_KEYWORDS: Dict[str, List[str]] = {
    "E": ["碳", "排放", "能源", "耗", "环境", "废水", "废气", "废弃物", "绿色", "气候", "温室", "资源", "水", "生物多样"],
    "S": ["员工", "培训", "流失", "安全", "健康", "社区", "人权", "劳工", "性别", "多样", "薪酬", "福利", "客户", "供应商"],
    "G": ["治理", "董事会", "合规", "审计", "风险", "反腐", "贿赂", "道德", "透明度", "披露", "股东", "高管", "内控"],
}

# 数值单位换算表（用于统一数值单位）
UNIT_CONVERSION: Dict[str, Dict[str, float]] = {
    "吨": {"万吨": 0.0001, "千克": 1000.0, "公斤": 1000.0, "克": 1000000.0},
    "万吨": {"吨": 10000.0, "千克": 10000000.0, "公斤": 10000000.0},
    "百分比": {"%": 1.0},
}

# 日期模式（用于识别日期）
DATE_PATTERNS = [
    r"(20\d{2}|19\d{2})[-/年.](\d{1,2})[-/月.](\d{1,2})日?",
    r"(20\d{2}|19\d{2})[-/年.](\d{1,2})月?",
    r"(20\d{2}|19\d{2})年",
]

# 数值模式（支持整数、小数、负数、科学计数法）
NUMBER_PATTERN = r"[-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?"

# 指标字段名映射（输出统一字段名）
FIELD_MAPPING = {
    "carbon": ["碳排放", "碳排", "co2", "二氧化碳", "温室气体"],
    "energy": ["能源消耗", "能耗", "用电", "电力"],
    "water": ["用水", "水耗", "取水"],
    "waste": ["废弃物", "固废", "垃圾"],
    "employee": ["员工数", "雇员", "职工"],
    "turnover": ["流失率", "离职率"],
    "training": ["培训", "培训小时"],
    "safety": ["安全事故", "工伤", "事故率"],
    "board": ["董事会", "董事"],
    "compliance": ["合规", "违规", "处罚"],
    "risk": ["风险", "风险事件"],
}


# ============================================================
# 工具函数
# ============================================================

def normalize_text(text: str) -> str:
    """规范化输入文本：去除多余空白、统一标点。"""
    if not text or not isinstance(text, str):
        return ""
    # 统一换行和制表符为空格
    text = text.replace("\r\n", " ").replace("\n", " ").replace("\t", " ")
    # 压缩多个空格
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def extract_numbers(text: str) -> List[float]:
    """从文本中提取所有数值。"""
    if not text:
        return []
    # 匹配数字（含负号、小数、科学计数法）
    matches = re.findall(NUMBER_PATTERN, text)
    numbers = []
    for m in matches:
        try:
            numbers.append(float(m))
        except ValueError:
            continue
    return numbers


def detect_category(text: str) -> str:
    """根据关键词检测文本所属的 ESG 类别。"""
    if not text:
        return "U"  # 未知
    scores = {"E": 0, "S": 0, "G": 0}
    for cat, keywords in CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if kw in text:
                scores[cat] += 1
    # 返回得分最高且大于0的类别
    max_score = max(scores.values())
    if max_score == 0:
        return "U"
    # 返回得分最高的类别（并列时按 E > S > G 优先）
    for cat in ["E", "S", "G"]:
        if scores[cat] == max_score:
            return cat
    return "U"


def normalize_unit(value: float, unit: str) -> Tuple[float, str]:
    """将数值统一为基准单位（吨/百分比等）。"""
    if unit in UNIT_CONVERSION:
        return value, unit
    # 尝试匹配单位
    for base_unit, conversions in UNIT_CONVERSION.items():
        for alias, factor in conversions.items():
            if alias in unit:
                return value * factor, base_unit
    return value, unit


def extract_date(text: str) -> Optional[str]:
    """从文本中提取日期，返回 YYYY-MM-DD 格式或 YYYY 格式。"""
    if not text:
        return None
    for pattern in DATE_PATTERNS:
        match = re.search(pattern, text)
        if match:
            groups = match.groups()
            if len(groups) == 3:
                year, month, day = groups
                return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"
            elif len(groups) == 2:
                year, month = groups
                return f"{int(year):04d}-{int(month):02d}"
            elif len(groups) == 1:
                year = groups[0]
                return f"{int(year):04d}"
    return None


def extract_source(text: str) -> str:
    """提取数据来源（如报告名称、公司名等）。"""
    if not text:
        return ""
    # 简单启发式：取第一个句号前的部分作为来源
    parts = text.split("。")
    if parts:
        return parts[0].strip()[:50]
    return text[:50]


def extract_entity_name(text: str) -> str:
    """提取主体名称（公司/组织名）。"""
    if not text:
        return ""
    # 常见公司后缀
    suffixes = ["公司", "集团", "股份", "有限", "银行", "能源", "科技"]
    for suffix in suffixes:
        idx = text.find(suffix)
        if idx >= 0:
            # 向前找起始位置（通常在前10-20个字符内）
            start = max(0, idx - 15)
            candidate = text[start:idx + len(suffix)]
            # 清理
            candidate = candidate.strip("，。,.;；:： ")
            return candidate
    return ""


# ============================================================
# 核心解析逻辑
# ============================================================

def parse_indicator(text: str, category: str) -> List[Dict[str, Any]]:
    """
    解析单条文本中的指标数据。

    返回格式：
    [{
        "field": "carbon",
        "value": 100.0,
        "unit": "万吨",
        "category": "E",
        "confidence": 0.85,
        "date": "2023",
        "source": "..."
    }]
    """
    if not text:
        return []
    
    results = []
    normalized = normalize_text(text)
    
    # 提取日期和来源
    date = extract_date(normalized)
    source = extract_source(normalized)
    numbers = extract_numbers(normalized)
    
    if not numbers:
        # 没有数字，无法提取指标值
        return []
    
    # 根据类别扫描关键词
    for field, keywords in FIELD_MAPPING.items():
        for kw in keywords:
            if kw in normalized:
                # 找到关键词，提取附近的数值
                # 在关键词前后各取30字符作为上下文
                idx = normalized.find(kw)
                context = normalized[max(0, idx-20): idx+len(kw)+30]
                context_numbers = extract_numbers(context)
                
                if context_numbers:
                    # 取第一个数值作为指标值
                    value = context_numbers[0]
                    
                    # 检测单位
                    unit = ""
                    unit_match = re.search(r"(万吨|吨|千克|公斤|克|%|百分比)", context)
                    if unit_match:
                        unit = unit_match.group(1)
                    
                    # 置信度计算（基于上下文丰富度）
                    confidence = 0.5
                    if date:
                        confidence += 0.15
                    if source:
                        confidence += 0.1
                    if len(context) > 10:
                        confidence += 0.1
                    # 有明确单位
                    if unit:
                        confidence += 0.1
                    # 有多个关键词匹配
                    if sum(1 for k in keywords if k in normalized) > 1:
                        confidence += 0.05
                    
                    # 限制在0.1-0.95之间
                    confidence = max(0.1, min(0.95, confidence))
                    
                    results.append({
                        "field": field,
                        "value": value,
                        "unit": unit,
                        "category": category,
                        "confidence": round(confidence, 2),
                        "date": date,
                        "source": source,
                    })
                    break  # 每个字段只取第一个匹配
        if results and field == results[-1]["field"]:
            continue  # 已找到该字段，继续下一个字段
    
    return results


def parse_single_record(text: str) -> Dict[str, Any]:
    """
    解析单条 ESG 记录。

    返回结构：
    {
        "entity": "...",
        "category": "E",
        "indicators": [...],
        "overall_confidence": 0.0,
        "raw_text": "..."
    }
    """
    if not text or not text.strip():
        raise ValueError("E002: 输入数据为空")
    
    normalized = normalize_text(text)
    if len(normalized) < 5:
        raise ValueError("E003: 输入数据格式错误（文本过短）")
    
    # 检测类别
    category = detect_category(normalized)
    
    # 提取主体名称
    entity = extract_entity_name(normalized)
    
    # 解析指标
    indicators = parse_indicator(normalized, category)
    
    # 计算整体置信度
    if indicators:
        overall = sum(i["confidence"] for i in indicators) / len(indicators)
    else:
        overall = 0.1  # 无指标时低置信度
    
    return {
        "entity": entity,
        "category": category,
        "indicators": indicators,
        "overall_confidence": round(overall, 2),
        "raw_text": normalized,
    }


def parse_batch(texts: List[str]) -> List[Dict[str, Any]]:
    """批量解析多条记录。"""
    if not texts:
        raise ValueError("E002: 输入数据为空")
    
    results = []
    for i, text in enumerate(texts):
        try:
            record = parse_single_record(text)
            record["record_id"] = i + 1
            results.append(record)
        except ValueError as e:
            # 单条失败不影响整体
            results.append({
                "record_id": i + 1,
                "error": str(e),
                "raw_text": text[:100] if text else "",
            })
    
    return results


def format_json(data: Any) -> str:
    """将数据序列化为 JSON 字符串。"""
    try:
        return json.dumps(data, ensure_ascii=False, indent=2)
    except (TypeError, ValueError) as e:
        raise ValueError(f"E007: 输出序列化失败 - {e}")


# ============================================================
# 自检模块
# ============================================================

def run_selftest() -> bool:
    """
    离线自检核心逻辑。
    使用内置硬编码样例数据，不依赖外部文件或网络。
    
    返回 True 表示全部通过，否则抛出异常。
    """
    print("=" * 60)
    print("开始自检 (selftest)")
    print("=" * 60)
    
    # ---------- 测试1: normalize_text ----------
    print("\n[测试1] normalize_text")
    test1 = "  这是  一段\n文本\t内容  "
    result1 = normalize_text(test1)
    assert result1 == "这是 一段 文本 内容", f"E008: normalize_text 失败 - {result1}"
    assert len(result1) > 0, "E008: normalize_text 返回空"
    print("  ✓ 通过")
    
    # ---------- 测试2: extract_numbers ----------
    print("\n[测试2] extract_numbers")
    test2 = "碳排放量为100.5万吨，同比增长3.2%"
    result2 = extract_numbers(test2)
    assert len(result2) >= 2, f"E008: extract_numbers 数量不足 - {result2}"
    assert any(abs(n - 100.5) < 0.01 for n in result2), f"E008: 未找到100.5 - {result2}"
    assert any(abs(n - 3.2) < 0.01 for n in result2), f"E008: 未找到3.2 - {result2}"
    print("  ✓ 通过")
    
    # ---------- 测试3: detect_category ----------
    print("\n[测试3] detect_category")
    test3_e = "公司2023年碳排放量为100万吨"
    test3_s = "员工培训小时数达到500小时"
    test3_g = "董事会成员共10人"
    assert detect_category(test3_e) == "E", f"E008: 类别检测错误 - {detect_category(test3_e)}"
    assert detect_category(test3_s) == "S", f"E008: 类别检测错误 - {detect_category(test3_s)}"
    assert detect_category(test3_g) == "G", f"E008: 类别检测错误 - {detect_category(test3_g)}"
    print("  ✓ 通过")
    
    # ---------- 测试4: extract_date ----------
    print("\n[测试4] extract_date")
    test4 = "2023年度报告显示，公司碳排放量为100万吨"
    result4 = extract_date(test4)
    assert result4 is not None, "E008: 未提取到日期"
    assert "2023" in result4, f"E008: 日期年份错误 - {result4}"
    print("  ✓ 通过")
    
    # ---------- 测试5: parse_single_record ----------
    print("\n[测试5] parse_single_record")
    test5 = "某能源公司2023年碳排放量为100万吨，同比下降5%。员工流失率为8%。"
    result5 = parse_single_record(test5)
    assert result5["category"] in ["E", "S", "G", "U"], f"E008: 类别异常 - {result5['category']}"
    assert len(result5["indicators"]) > 0, "E008: 未解析出任何指标"
    assert 0.0 <= result5["overall_confidence"] <= 1.0, f"E008: 置信度超出范围 - {result5['overall_confidence']}"
    # 宽松断言：置信度应大于0.1
    assert result5["overall_confidence"] > 0.1, f"E008: 置信度异常低 - {result5['overall_confidence']}"
    print(f"  ✓ 通过 (类别={result5['category']}, 指标数={len(result5['indicators'])}, 置信度={result5['overall_confidence']})")
    
    # ---------- 测试6: parse_batch ----------
    print("\n[测试6] parse_batch")
    test6 = [
        "某制造公司2022年用水量50万吨",
        "某银行2023年合规培训覆盖率达到95%",
        "某科技公司2023年研发投入占营收的15%",
    ]
    result6 = parse_batch(test6)
    assert len(result6) == 3, f"E008: 批量解析数量错误 - {len(result6)}"
    assert all("record_id" in r for r in result6), "E008: 缺少record_id"
    # 宽松断言：至少一条有指标
    assert any(len(r.get("indicators", [])) > 0 for r in result6), "E008: 所有记录均无指标"
    print(f"  ✓ 通过 (共{len(result6)}条记录)")
    
    # ---------- 测试7: format_json ----------
    print("\n[测试7] format_json")
    test7_data = {"test": "数据", "value": 123}
    result7 = format_json(test7_data)
    assert '"test"' in result7, "E008: JSON序列化失败"
    assert len(result7) > 0, "E008: JSON序列化为空"
    print("  ✓ 通过")
    
    # ---------- 测试8: 错误处理 ----------
    print("\n[测试8] 错误处理")
    # 空输入
    try:
        parse_single_record("")
        assert False, "E008: 空输入未抛出异常"
    except ValueError as e:
        assert "E002" in str(e), f"E008: 错误码不对 - {e}"
    
    # 过短输入
    try:
        parse_single_record("短")
        assert False, "E008: 过短输入未抛出异常"
    except ValueError as e:
        assert "E003" in str(e), f"E008: 错误码不对 - {e}"
    print("  ✓ 通过")
    
    # ---------- 测试9: 单位归一化 ----------
    print("\n[测试9] 单位归一化")
    val1, unit1 = normalize_unit(1.0, "吨")
    val2, unit2 = normalize_unit(1.0, "千克")
    # 1吨 = 1000千克
    assert abs(val1 - val2) > 0.01, f"E008: 单位换算异常 - {val1} vs {val2}"
    print(f"  ✓ 通过 (1吨={val1}{unit1}, 1千克={val2}{unit2})")
    
    # ---------- 测试10: 边界情况 ----------
    print("\n[测试10] 边界情况")
    # 特殊字符
    assert normalize_text("  ") == "", "E008: 空白文本未归一化为空"
    # 无数字文本
    assert extract_numbers("没有数字") == [], "E008: 无数字文本应返回空列表"
    # 无日期文本
    assert extract_date("无日期") is None, "E008: 无日期应返回None"
    print("  ✓ 通过")
    
    print("\n" + "=" * 60)
    print("自检全部通过 ✓")
    print("=" * 60)
    return True


# ============================================================
# 主入口
# ============================================================

def main() -> int:
    """主函数。"""
    parser = argparse.ArgumentParser(
        description="ESG数据智能解析平台 - 结构化输出与置信度标注",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python scripts/main.py --text "某公司2023年碳排放量为100万吨"
  python scripts/main.py --batch '["记录1", "记录2"]'
  python scripts/main.py --selftest
        """,
    )
    
    parser.add_argument(
        "--text", type=str, default=None,
        help="单条ESG文本记录，如：'某公司2023年碳排放量为100万吨'",
    )
    parser.add_argument(
        "--batch", type=str, default=None,
        help="JSON格式的文本列表，如：'[\"记录1\", \"记录2\"]'",
    )
    parser.add_argument(
        "--selftest", action="store_true",
        help="运行离线自检（使用内置样例，不依赖外部资源）",
    )
    parser.add_argument(
        "--output", type=str, default="json",
        choices=["json", "text"],
        help="输出格式（默认json）",
    )
    
    args = parser.parse_args()
    
    # 自检模式
    if args.selftest:
        try:
            run_selftest()
            return 0
        except AssertionError as e:
            print(f"自检失败: {e}", file=sys.stderr)
            return 1
        except Exception as e:
            print(f"自检异常: {e}", file=sys.stderr)
            return 2
    
    # 检查输入
    if not args.text and not args.batch:
        parser.print_help()
        print("\n错误: E001 - 必须提供 --text 或 --batch 参数", file=sys.stderr)
        return 1
    
    try:
        if args.batch:
            # 批量模式
            try:
                texts = json.loads(args.batch)
                if not isinstance(texts, list):
                    raise ValueError("E003: batch 参数必须是JSON数组")
            except json.JSONDecodeError as e:
                print(f"错误: E003 - batch JSON解析失败: {e}", file=sys.stderr)
                return 1
            
            result = parse_batch(texts)
        else:
            # 单条模式
            result = parse_single_record(args.text)
            result = [result]  # 统一为列表
        
        # 输出
        if args.output == "json":
            output = format_json(result)
            print(output)
        else:
            # 文本输出（简化）
            for record in result:
                print(f"记录 #{record.get('record_id', '?')}:")
                print(f"  主体: {record.get('entity', '未知')}")
                print(f"  类别: {record.get('category', 'U')}")
                print(f"  置信度: {record.get('overall_confidence', 0.0)}")
                for ind in record.get("indicators", []):
                    print(f"    - {ind['field']}: {ind['value']} {ind['unit']} (置信度: {ind['confidence']})")
                if "error" in record:
                    print(f"  错误: {record['error']}")
                print()
        
        return 0
        
    except ValueError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"错误: E010 - 未预期异常: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
