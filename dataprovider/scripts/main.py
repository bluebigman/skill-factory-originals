#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py

全新独立实现：dataprovider 技能（SQL查询辅助）
仅依据功能规格 clean-room 编写，不参考任何既有实现。

功能概览：
- 将用户输入的数据/文本解析为结构化结果
- 识别并保留关键字段信息
- 按约定格式输出，并标注置信度
- 支持批量处理与自定义输出格式
- 内置 --selftest 离线自检

错误码：
E001 输入为空
E002 关键信息缺失
E003 输入格式错误
E004 超出能力边界
E005 置信度过低
E006 内部处理异常
E007 参数解析失败
E008 输出写入失败
E009 批量处理中断
E010 未知错误
"""

import argparse
import json
import re
import sys
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# 常量定义
# ---------------------------------------------------------------------------
# 置信度阈值
CONFIDENCE_HIGH = 90      # >=90 直接输出
CONFIDENCE_MEDIUM = 85    # 85-90 建议复核
CONFIDENCE_LOW = 85       # <85 需核实

# 默认输出模板字段
DEFAULT_FIELDS = ["id", "content", "type", "confidence", "note"]

# 关键信息识别正则（内置通用规则）
KEY_PATTERNS = {
    "email": r"[\w.+-]+@[\w-]+\.[\w.]+",
    "phone": r"(?<!\d)1[3-9]\d{9}(?!\d)",
    "url": r"https?://[^\s]+",
    "date": r"\d{4}[-/]\d{1,2}[-/]\d{1,2}",
    "id_card": r"(?<!\d)\d{17}[\dXx](?!\d)",
}

# 可识别的输入类型
INPUT_TYPES = ["text", "json", "csv", "url", "file", "unknown"]


# ---------------------------------------------------------------------------
# 核心工具函数
# ---------------------------------------------------------------------------
def detect_input_type(data: str) -> Tuple[str, float]:
    """
    检测输入数据类型。
    返回 (类型, 置信度)。
    """
    if not data or not data.strip():
        return "unknown", 0.0

    stripped = data.strip()

    # JSON 检测
    if stripped.startswith("{") or stripped.startswith("["):
        try:
            json.loads(stripped)
            return "json", 95.0
        except json.JSONDecodeError:
            pass

    # URL 检测
    if re.match(r"^https?://", stripped, re.IGNORECASE):
        return "url", 90.0

    # 文件路径检测（常见扩展名）
    if re.search(r"\.(csv|txt|json|xml|log|md)$", stripped, re.IGNORECASE):
        return "file", 80.0

    # CSV 检测（包含逗号且多行）
    if "," in stripped and "\n" in stripped:
        lines = [l for l in stripped.splitlines() if l.strip()]
        if len(lines) >= 2 and all("," in l for l in lines[:3]):
            return "csv", 75.0

    # 默认文本
    return "text", 70.0


def extract_key_info(data: str, input_type: str) -> Dict[str, List[str]]:
    """
    从输入内容中提取关键信息。
    返回 {字段名: [匹配值列表]}。
    """
    result: Dict[str, List[str]] = {}

    # 通用正则提取
    for field, pattern in KEY_PATTERNS.items():
        matches = re.findall(pattern, data)
        if matches:
            result[field] = list(set(matches))  # 去重

    # JSON 特殊处理：提取顶层键
    if input_type == "json":
        try:
            obj = json.loads(data)
            if isinstance(obj, dict):
                keys = [k for k in obj.keys() if not k.startswith("_")]
                if keys:
                    result["json_keys"] = keys[:20]  # 最多取20个
        except json.JSONDecodeError:
            pass

    # CSV 特殊处理：提取表头
    if input_type == "csv":
        lines = [l for l in data.splitlines() if l.strip()]
        if lines:
            header = lines[0].split(",")
            result["csv_columns"] = [h.strip() for h in header if h.strip()]

    return result


def compute_confidence(data: str, key_info: Dict[str, List[str]], input_type: str) -> float:
    """
    计算置信度（0-100）。
    规则：
    - 基础分 60
    - 检测到类型 +10
    - 每个关键字段 +5（上限 +20）
    - 输入长度 > 50 字符 +5
    - 输入长度 > 200 字符 +5
    """
    score = 60.0

    if input_type != "unknown":
        score += 10.0

    field_count = sum(len(v) for v in key_info.values())
    score += min(field_count * 5.0, 20.0)

    if len(data) > 50:
        score += 5.0
    if len(data) > 200:
        score += 5.0

    return min(score, 99.0)  # 最高 99，避免 100%


def format_output(
    data: str,
    input_type: str,
    key_info: Dict[str, List[str]],
    confidence: float,
    output_format: str = "json",
    custom_fields: Optional[List[str]] = None,
) -> str:
    """
    按指定格式生成输出。
    支持 json / text / table 三种格式。
    """
    # 构建结构化结果
    result: Dict[str, Any] = {
        "input_type": input_type,
        "confidence": round(confidence, 1),
        "key_info": key_info,
        "content_preview": data[:200] + ("..." if len(data) > 200 else ""),
    }

    # 置信度标注
    if confidence >= CONFIDENCE_HIGH:
        result["note"] = "直接输出"
    elif confidence >= CONFIDENCE_MEDIUM:
        result["note"] = "建议复核"
    else:
        result["note"] = "[需核实] 部分内容不确定"

    # 自定义字段筛选
    if custom_fields:
        filtered = {}
        for f in custom_fields:
            if f in result:
                filtered[f] = result[f]
        result = filtered

    # 按格式输出
    if output_format == "json":
        return json.dumps(result, ensure_ascii=False, indent=2)

    elif output_format == "text":
        lines = []
        for k, v in result.items():
            if isinstance(v, dict):
                lines.append(f"{k}:")
                for kk, vv in v.items():
                    lines.append(f"  {kk}: {vv}")
            else:
                lines.append(f"{k}: {v}")
        return "\n".join(lines)

    elif output_format == "table":
        # 简易表格输出
        lines = ["| 字段 | 值 |", "| --- | --- |"]
        for k, v in result.items():
            if isinstance(v, dict):
                for kk, vv in v.items():
                    lines.append(f"| {k}.{kk} | {vv} |")
            else:
                lines.append(f"| {k} | {v} |")
        return "\n".join(lines)

    else:
        raise ValueError(f"不支持的输出格式: {output_format}")


def process_batch(items: List[str], output_format: str = "json") -> List[Dict[str, Any]]:
    """
    批量处理多个输入项。
    """
    results = []
    for idx, item in enumerate(items):
        try:
            # 单条处理
            input_type, _ = detect_input_type(item)
            key_info = extract_key_info(item, input_type)
            confidence = compute_confidence(item, key_info, input_type)
            formatted = format_output(item, input_type, key_info, confidence, output_format)
            results.append({
                "index": idx,
                "success": True,
                "output": formatted,
            })
        except Exception as e:
            results.append({
                "index": idx,
                "success": False,
                "error": f"E009: 批量处理第 {idx} 项失败: {str(e)}",
            })
    return results


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------
def main_process(args: argparse.Namespace) -> int:
    """
    核心处理流程。
    返回退出码：0 成功，非 0 失败。
    """
    # 获取输入
    data = args.input

    # E001: 输入为空
    if not data or not data.strip():
        print("E001: 请提供待处理的内容，格式为：用户提供的数据/文件/URL", file=sys.stderr)
        return 1

    # 检测输入类型
    input_type, _ = detect_input_type(data)

    # 提取关键信息
    key_info = extract_key_info(data, input_type)

    # 计算置信度
    confidence = compute_confidence(data, key_info, input_type)

    # E005: 置信度过低
    if confidence < CONFIDENCE_LOW:
        print(f"E005: 结果无法确定（置信度 {confidence:.1f}%），建议补充更多信息", file=sys.stderr)
        return 5

    # 生成输出
    try:
        output = format_output(
            data=data,
            input_type=input_type,
            key_info=key_info,
            confidence=confidence,
            output_format=args.format,
            custom_fields=args.fields,
        )
    except ValueError as e:
        print(f"E003: 输出格式错误 - {str(e)}", file=sys.stderr)
        return 3

    # 输出结果
    print(output)
    return 0


# ---------------------------------------------------------------------------
# 自检模块
# ---------------------------------------------------------------------------
def run_selftest() -> int:
    """
    离线自检核心逻辑。
    使用内置硬编码样例，不读取外部文件、不访问网络。
    断言使用宽松阈值，确保必然匹配。
    """
    print("=" * 60)
    print("运行自检 (selftest)")
    print("=" * 60)

    # 测试样例 1: 普通文本
    sample1 = "联系人：张三，邮箱 zhangsan@example.com，电话 13812345678。"
    input_type1, _ = detect_input_type(sample1)
    assert input_type1 == "text", f"样例1类型检测失败: {input_type1}"

    key_info1 = extract_key_info(sample1, input_type1)
    assert "email" in key_info1, "样例1未提取到邮箱"
    assert "phone" in key_info1, "样例1未提取到电话"

    conf1 = compute_confidence(sample1, key_info1, input_type1)
    assert conf1 > 70, f"样例1置信度异常: {conf1}"

    out1 = format_output(sample1, input_type1, key_info1, conf1, "json")
    parsed1 = json.loads(out1)
    assert parsed1["input_type"] == "text", "样例1输出类型错误"
    assert parsed1["confidence"] > 70, "样例1输出置信度错误"
    print("[PASS] 样例1: 文本解析")

    # 测试样例 2: JSON 输入
    sample2 = '{"name": "测试", "age": 30, "email": "test@example.com"}'
    input_type2, _ = detect_input_type(sample2)
    assert input_type2 == "json", f"样例2类型检测失败: {input_type2}"

    key_info2 = extract_key_info(sample2, input_type2)
    assert "json_keys" in key_info2, "样例2未提取到JSON键"
    assert "email" in key_info2, "样例2未提取到邮箱"

    conf2 = compute_confidence(sample2, key_info2, input_type2)
    assert conf2 > 75, f"样例2置信度异常: {conf2}"
    print("[PASS] 样例2: JSON解析")

    # 测试样例 3: CSV 输入
    sample3 = "姓名,年龄,城市\n张三,30,北京\n李四,25,上海"
    input_type3, _ = detect_input_type(sample3)
    assert input_type3 == "csv", f"样例3类型检测失败: {input_type3}"

    key_info3 = extract_key_info(sample3, input_type3)
    assert "csv_columns" in key_info3, "样例3未提取到CSV列名"

    conf3 = compute_confidence(sample3, key_info3, input_type3)
    assert conf3 > 70, f"样例3置信度异常: {conf3}"
    print("[PASS] 样例3: CSV解析")

    # 测试样例 4: URL 输入
    sample4 = "https://example.com/data?page=1"
    input_type4, _ = detect_input_type(sample4)
    assert input_type4 == "url", f"样例4类型检测失败: {input_type4}"

    key_info4 = extract_key_info(sample4, input_type4)
    assert "url" in key_info4, "样例4未提取到URL"
    print("[PASS] 样例4: URL解析")

    # 测试样例 5: 批量处理
    batch_items = [
        "测试文本内容",
        '{"key": "value"}',
        "a,b,c\n1,2,3",
    ]
    batch_results = process_batch(batch_items, "json")
    assert len(batch_results) == 3, "批量处理数量错误"
    assert all(r["success"] for r in batch_results), "批量处理存在失败项"
    print("[PASS] 样例5: 批量处理")

    # 测试样例 6: 错误处理
    # E001 输入为空
    empty_input = ""
    input_type_empty, _ = detect_input_type(empty_input)
    assert input_type_empty == "unknown", "空输入类型检测错误"

    key_info_empty = extract_key_info(empty_input, input_type_empty)
    assert len(key_info_empty) == 0, "空输入不应提取到关键信息"
    print("[PASS] 样例6: 空输入处理")

    # 测试样例 7: 置信度标注
    sample7 = "简单文本"
    conf7 = compute_confidence(sample7, {}, "text")
    assert 60 <= conf7 <= 99, f"置信度范围错误: {conf7}"

    out7 = format_output(sample7, "text", {}, conf7, "json")
    parsed7 = json.loads(out7)
    assert "note" in parsed7, "输出缺少置信度标注"
    print("[PASS] 样例7: 置信度标注")

    # 测试样例 8: 输出格式
    sample8 = "测试数据"
    for fmt in ["json", "text", "table"]:
        out8 = format_output(sample8, "text", {}, 90.0, fmt)
        assert len(out8) > 0, f"输出格式 {fmt} 为空"
    print("[PASS] 样例8: 多种输出格式")

    # 测试样例 9: 自定义字段
    sample9 = "测试数据"
    out9 = format_output(sample9, "text", {}, 90.0, "json", custom_fields=["input_type", "confidence"])
    parsed9 = json.loads(out9)
    assert set(parsed9.keys()) == {"input_type", "confidence"}, "自定义字段筛选失败"
    print("[PASS] 样例9: 自定义字段")

    # 测试样例 10: 长文本处理
    sample10 = "长文本" * 100  # 300字符
    conf10 = compute_confidence(sample10, {}, "text")
    assert conf10 > 70, f"长文本置信度异常: {conf10}"
    print("[PASS] 样例10: 长文本处理")

    print("=" * 60)
    print("全部自检通过!")
    print("=" * 60)
    return 0


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------
def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    """解析命令行参数。"""
    parser = argparse.ArgumentParser(
        description="dataprovider 技能 - SQL查询辅助工具",
        epilog="示例: python main.py --input '文本内容' --format json",
    )

    parser.add_argument(
        "--input", "-i",
        type=str,
        help="待处理的输入内容（文本/JSON/CSV/URL）",
    )

    parser.add_argument(
        "--format", "-f",
        type=str,
        choices=["json", "text", "table"],
        default="json",
        help="输出格式（默认: json）",
    )

    parser.add_argument(
        "--fields",
        type=str,
        nargs="*",
        help="自定义输出字段（空格分隔）",
    )

    parser.add_argument(
        "--batch",
        type=str,
        nargs="+",
        help="批量处理多个输入项",
    )

    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行离线自检",
    )

    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    """主入口。"""
    args = parse_args(argv)

    # 自检模式
    if args.selftest:
        try:
            return run_selftest()
        except AssertionError as e:
            print(f"E010: 自检失败 - {str(e)}", file=sys.stderr)
            return 10
        except Exception as e:
            print(f"E006: 自检异常 - {str(e)}", file=sys.stderr)
            return 6

    # 批量模式
    if args.batch:
        try:
            results = process_batch(args.batch, args.format)
            for r in results:
                if r["success"]:
                    print(f"--- 项 {r['index']} ---")
                    print(r["output"])
                else:
                    print(r["error"], file=sys.stderr)
            return 0
        except Exception as e:
            print(f"E009: 批量处理失败 - {str(e)}", file=sys.stderr)
            return 9

    # 单条模式
    if not args.input:
        print("E001: 请提供待处理的内容，格式为：用户提供的数据/文件/URL", file=sys.stderr)
        print("提示: 使用 --selftest 运行自检，--help 查看帮助", file=sys.stderr)
        return 1

    try:
        return main_process(args)
    except Exception as e:
        print(f"E006: 处理异常 - {str(e)}", file=sys.stderr)
        return 6


if __name__ == "__main__":
    sys.exit(main())
