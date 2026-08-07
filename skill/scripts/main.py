#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py — 内容转换 结构化输出 置信度标注

功能概述：
  本脚本将非结构化或半结构化输入（文本、文件内容或URL内容）转换为
  结构化结果（JSON），并针对每个提取字段标注置信度（high/medium/low）。

  核心能力：
    1. 从文本中提取关键实体（人名、日期、金额、编号等）
    2. 按照用户指定字段或默认字段结构重组输出
    3. 对每个输出字段基于信息完整度给出置信度标注
    4. 支持批处理（多条记录循环处理）

  错误码约定：
    E001 参数错误
    E002 输入为空
    E003 输入类型不支持
    E004 文件读取失败
    E005 URL获取失败
    E006 JSON解析失败
    E007 字段结构无效
    E008 批处理数据格式错误
    E009 内部逻辑错误
    E010 未知异常

  自检模式：
    python scripts/main.py --selftest
    使用内置硬编码样例数据离线验证核心逻辑，不依赖外部文件或网络。
"""

import sys
import os
import json
import re
import argparse
import datetime
from typing import Any, Dict, List, Optional, Tuple, Union


# ============================================================
# 常量定义
# ============================================================

DEFAULT_FIELDS = ["name", "date", "amount", "id", "conclusion"]

CONFIDENCE_HIGH = "high"
CONFIDENCE_MEDIUM = "medium"
CONFIDENCE_LOW = "low"

ERROR_MESSAGES = {
    "E001": "参数错误：请检查命令行参数",
    "E002": "输入为空：未提供有效输入内容",
    "E003": "输入类型不支持：仅支持文本、文件路径或URL",
    "E004": "文件读取失败：无法读取指定文件",
    "E005": "URL获取失败：无法获取URL内容",
    "E006": "JSON解析失败：输入内容不是有效JSON",
    "E007": "字段结构无效：字段列表为空或格式错误",
    "E008": "批处理数据格式错误：输入不是数组或数组为空",
    "E009": "内部逻辑错误：发生未预期的情况",
    "E010": "未知异常：发生未分类的错误",
}

# 字段别名映射
FIELD_ALIASES = {
    "name": ["name", "姓名", "名称", "标题", "联系人", "负责人"],
    "date": ["date", "日期", "时间", "到期日", "创建日期"],
    "amount": ["amount", "金额", "价格", "费用", "总额", "总价"],
    "id": ["id", "编号", "号码", "流水号", "订单号", "合同号"],
    "conclusion": ["conclusion", "结论", "结果", "判断", "状态"],
}


# ============================================================
# 工具函数
# ============================================================

def _now_timestamp() -> str:
    """返回当前时间戳字符串"""
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _safe_json_dumps(data: Any) -> str:
    """安全地将数据转为JSON字符串"""
    return json.dumps(data, ensure_ascii=False, indent=2)


def _is_valid_url(text: str) -> bool:
    """判断字符串是否像URL"""
    return text.startswith(("http://", "https://"))


def _is_file_path(text: str) -> bool:
    """判断字符串是否像文件路径"""
    return os.path.exists(text) and os.path.isfile(text)


def _detect_input_type(text: str) -> str:
    """
    检测输入类型
    返回: "json" | "text" | "url" | "file"
    """
    if not text or not text.strip():
        return "empty"
    stripped = text.strip()
    if _is_valid_url(stripped):
        return "url"
    if _is_file_path(stripped):
        return "file"
    if stripped.startswith("["):
        return "json"
    return "text"


def _read_file_content(file_path: str) -> str:
    """读取文件内容"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        # 尝试其他编码
        try:
            with open(file_path, "r", encoding="gbk") as f:
                return f.read()
        except Exception as e:
            raise RuntimeError("E004") from e


def _fetch_url_content(url: str) -> str:
    """
    获取URL内容
    注意：标准库实现，仅支持简单场景；复杂场景建议使用requests
    """
    # 使用标准库urllib
    try:
        from urllib.request import urlopen, Request
        req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urlopen(req, timeout=10) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        raise RuntimeError("E005") from e


def _get_field_aliases(field_name: str) -> List[str]:
    """获取字段的所有别名"""
    field_name_lower = field_name.lower().strip()
    # 检查是否在已知字段中
    for canonical_field, aliases in FIELD_ALIASES.items():
        if field_name_lower == canonical_field or field_name_lower in aliases:
            return aliases
    # 如果是自定义字段，返回字段名本身及其常见变体
    return [field_name, field_name_lower]


# ============================================================
# 核心提取逻辑
# ============================================================

def _extract_name(text: str) -> Optional[str]:
    """提取人名/标题"""
    patterns = [
        r"(?:姓名|名称|标题|联系人|负责人)[:：]\s*([^\s,，。；;]+)",
        r"([\u4e00-\u9fa5]{2,4})先生",
        r"([\u4e00-\u9fa5]{2,4})女士",
        r"(?:联系人|负责人)[:：]\s*([^\s,，。；;]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1).strip()
    return None


def _extract_date(text: str) -> Optional[str]:
    """提取日期"""
    patterns = [
        r"(?:日期|时间|到期日|创建日期)[:：]\s*(\d{4}[-/年]\d{1,2}[-/月]\d{1,2}日?)",
        r"(\d{4}[-/年]\d{1,2}[-/月]\d{1,2}日?)",
        r"(\d{4}年\d{1,2}月\d{1,2}日)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1).strip()
    return None


def _extract_amount(text: str) -> Optional[str]:
    """提取金额"""
    patterns = [
        r"(?:金额|价格|费用|总额|总价)[:：]\s*([¥￥]?\d+(?:\.\d+)?[元块]?)",
        r"([¥￥]\d+(?:\.\d+)?)",
        r"(\d+(?:\.\d+)?元)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1).strip()
    return None


def _extract_id(text: str) -> Optional[str]:
    """提取编号"""
    patterns = [
        r"(?:编号|号码|ID|订单号|合同号|流水号)[:：]\s*([A-Za-z0-9\-_]+)",
        r"(?:编号|号码)\s*[:：]?\s*([A-Za-z0-9\-_]{4,})",
        r"([A-Z]{2,}\d{4,})",
        r"(?:订单|合同|流水)[号]\s*[:：]?\s*([A-Za-z0-9\-_]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1).strip()
    return None


def _extract_conclusion(text: str) -> Optional[str]:
    """提取结论"""
    patterns = [
        r"(?:结论|结果|判断|状态)[:：]\s*([^\n。;；]+)",
        r"(通过|不通过|成功|失败|有效|无效|批准|拒绝|进行中|已完成)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            result = match.group(1).strip()
            # 限制长度
            if len(result) > 50:
                result = result[:50]
            return result
    return None


def _extract_custom_field(field_name: str, text: str) -> Optional[str]:
    """提取自定义字段"""
    # 尝试直接匹配字段名
    patterns = [
        rf"{re.escape(field_name)}[:：]\s*([^\s,，。；;]+)",
        rf"{re.escape(field_name)}\s*[:：]?\s*([^\s,，。；;]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1).strip()
    return None


def _extract_field(field_name: str, text: str) -> Optional[str]:
    """根据字段名提取对应信息"""
    field_name_lower = field_name.lower().strip()
    
    # 获取字段的所有别名
    aliases = _get_field_aliases(field_name)
    
    # 检查是否是已知字段类型
    if field_name_lower in ["name", "姓名", "名称", "标题", "联系人", "负责人"]:
        return _extract_name(text)
    if field_name_lower in ["date", "日期", "时间", "到期日", "创建日期"]:
        return _extract_date(text)
    if field_name_lower in ["amount", "金额", "价格", "费用", "总额", "总价"]:
        return _extract_amount(text)
    if field_name_lower in ["id", "编号", "号码", "流水号", "订单号", "合同号"]:
        return _extract_id(text)
    if field_name_lower in ["conclusion", "结论", "结果", "判断", "状态"]:
        return _extract_conclusion(text)
    
    # 自定义字段
    return _extract_custom_field(field_name, text)


def _calculate_confidence(value: Optional[str]) -> str:
    """根据提取结果计算置信度"""
    if value is None:
        return CONFIDENCE_LOW
    # 有值且长度合理，视为中等置信度
    if len(value) >= 2:
        return CONFIDENCE_MEDIUM
    return CONFIDENCE_LOW


# ============================================================
# 主处理逻辑
# ============================================================

def process_text(text: str, fields: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    处理单条文本，返回结构化结果
    """
    if not text or not text.strip():
        raise ValueError("E002")

    if fields is None:
        fields = DEFAULT_FIELDS

    if not isinstance(fields, list) or len(fields) == 0:
        raise ValueError("E007")

    extracted: Dict[str, Any] = {}
    confidences: Dict[str, str] = {}

    for field in fields:
        value = _extract_field(field, text)
        extracted[field] = value
        confidences[field] = _calculate_confidence(value)

    result = {
        "status": "success",
        "timestamp": _now_timestamp(),
        "input_type": "text",
        "extracted_data": extracted,
        "confidence": confidences,
        "overall_confidence": _calculate_overall_confidence(confidences),
    }
    return result


def _calculate_overall_confidence(confidences: Dict[str, str]) -> str:
    """计算整体置信度"""
    if not confidences:
        return CONFIDENCE_LOW
    values = list(confidences.values())
    if all(v == CONFIDENCE_HIGH for v in values):
        return CONFIDENCE_HIGH
    if all(v == CONFIDENCE_LOW for v in values):
        return CONFIDENCE_LOW
    return CONFIDENCE_MEDIUM


def process_json(json_text: str, fields: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    处理JSON输入（支持单条或批处理）
    """
    try:
        data = json.loads(json_text)
    except json.JSONDecodeError as e:
        raise ValueError("E006") from e

    # 批处理（数组）
    if isinstance(data, list):
        if len(data) == 0:
            raise ValueError("E008")
        results = []
        for item in data:
            if isinstance(item, str):
                results.append(process_text(item, fields))
            elif isinstance(item, dict):
                # 对字典中的值进行字段提取
                if fields is None:
                    fields = DEFAULT_FIELDS
                extracted = {}
                confidences = {}
                for field in fields:
                    # 先检查字典中是否有对应键
                    value = None
                    for key in _get_field_aliases(field):
                        if key in item:
                            value = item[key]
                            break
                    if value is None:
                        # 尝试从值中提取
                        for val in item.values():
                            if isinstance(val, str):
                                extracted_val = _extract_field(field, val)
                                if extracted_val:
                                    value = extracted_val
                                    break
                    
                    extracted[field] = value
                    confidences[field] = _calculate_confidence(value if isinstance(value, str) else str(value) if value else None)
                
                results.append({
                    "status": "success",
                    "timestamp": _now_timestamp(),
                    "input_type": "json-object",
                    "extracted_data": extracted,
                    "confidence": confidences,
                    "overall_confidence": _calculate_overall_confidence(confidences),
                })
            else:
                raise ValueError("E008")
        return {
            "status": "success",
            "timestamp": _now_timestamp(),
            "input_type": "json-batch",
            "count": len(results),
            "results": results,
        }

    # 单个对象
    if isinstance(data, dict):
        if fields is None:
            fields = DEFAULT_FIELDS
        extracted = {}
        confidences = {}
        for field in fields:
            # 先检查字典中是否有对应键
            value = None
            for key in _get_field_aliases(field):
                if key in data:
                    value = data[key]
                    break
            if value is None:
                # 尝试从值中提取
                for val in data.values():
                    if isinstance(val, str):
                        extracted_val = _extract_field(field, val)
                        if extracted_val:
                            value = extracted_val
                            break
            
            extracted[field] = value
            confidences[field] = _calculate_confidence(value if isinstance(value, str) else str(value) if value else None)
        
        return {
            "status": "success",
            "timestamp": _now_timestamp(),
            "input_type": "json-object",
            "extracted_data": extracted,
            "confidence": confidences,
            "overall_confidence": _calculate_overall_confidence(confidences),
        }

    # 其他类型
    raise ValueError("E003")


def process_input(content: str, fields: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    统一入口处理各种类型的输入
    """
    input_type = _detect_input_type(content)

    if input_type == "empty":
        raise ValueError("E002")

    if input_type == "file":
        file_content = _read_file_content(content.strip())
        return process_input(file_content, fields)

    if input_type == "url":
        url_content = _fetch_url_content(content.strip())
        return process_input(url_content, fields)

    if input_type == "json":
        return process_json(content.strip(), fields)

    # 普通文本
    return process_text(content, fields)


# ============================================================
# 自检逻辑
# ============================================================

def run_selftest() -> int:
    """
    内置自检：使用硬编码样例数据验证核心逻辑
    返回 0 表示通过，非 0 表示失败
    """
    print("=" * 60)
    print("自检模式启动 (--selftest)")
    print("=" * 60)

    test_cases = [
        {
            "name": "单条文本提取",
            "input": "姓名：张三，日期：2024年3月15日，金额：￥1234.56元，编号：ORD2024001，结论：通过",
            "type": "text",
            "checks": [
                ("提取姓名", lambda r: r["extracted_data"].get("name") is not None),
                ("提取日期", lambda r: r["extracted_data"].get("date") is not None),
                ("提取金额", lambda r: r["extracted_data"].get("amount") is not None),
                ("提取编号", lambda r: r["extracted_data"].get("id") is not None),
                ("提取结论", lambda r: r["extracted_data"].get("conclusion") is not None),
            ],
        },
        {
            "name": "JSON批处理",
            "input": '["姓名：李四，日期：2024-05-20，金额：99元", "姓名：王五，日期：2024-06-01，金额：200元"]',
            "type": "json",
            "checks": [
                ("批处理返回结果", lambda r: r.get("count") == 2),
                ("每条结果有效", lambda r: all(x.get("status") == "success" for x in r.get("results", []))),
            ],
        },
        {
            "name": "JSON对象输入",
            "input": '{"name": "测试对象", "value": 42}',
            "type": "json",
            "checks": [
                ("对象解析成功", lambda r: r.get("status") == "success"),
                ("数据保留", lambda r: r["extracted_data"].get("name") == "测试对象"),
            ],
        },
        {
            "name": "空输入处理",
            "input": "",
            "type": "error",
            "checks": [
                ("抛出E002错误", lambda r: r == "E002"),
            ],
        },
        {
            "name": "置信度标注",
            "input": "姓名：赵六，日期：2024年7月1日",
            "type": "text",
            "checks": [
                ("存在置信度字段", lambda r: "confidence" in r),
                ("置信度为中或高", lambda r: r["confidence"].get("name") in (CONFIDENCE_MEDIUM, CONFIDENCE_HIGH)),
                ("缺失字段为低", lambda r: r["confidence"].get("amount") == CONFIDENCE_LOW),
            ],
        },
    ]

    all_passed = True

    for idx, case in enumerate(test_cases):
        case_name = case["name"]
        print(f"\n[用例 {idx + 1}] {case_name}")

        try:
            if case["type"] == "error":
                try:
                    process_input(case["input"])
                    # 不应到达这里
                    print("  ✗ 错误：未抛出预期异常")
                    all_passed = False
                    continue
                except ValueError as e:
                    error_code = str(e)
                    # 验证错误码
                    if error_code == "E002":
                        print("  ✓ 正确抛出错误码:", error_code)
                    else:
                        print("  ✗ 错误码不匹配:", error_code)
                        all_passed = False
                    continue

            result = process_input(case["input"])

            for check_name, check_func in case["checks"]:
                try:
                    if check_func(result):
                        print(f"  ✓ {check_name}")
                    else:
                        print(f"  ✗ {check_name} 失败")
                        all_passed = False
                except Exception as e:
                    print(f"  ✗ {check_name} 异常: {e}")
                    all_passed = False

        except Exception as e:
            print(f"  ✗ 用例异常: {e}")
            all_passed = False

    # 额外验证：自定义字段
    print("\n[附加测试] 自定义字段提取")
    try:
        custom_result = process_text(
            "联系人：钱七，到期日：2024年12月31日，总额：5000元",
            fields=["联系人", "到期日", "总额"],
        )
        if custom_result["extracted_data"].get("联系人") is not None:
            print("  ✓ 自定义字段'联系人'提取成功")
        else:
            print("  ✗ 自定义字段'联系人'提取失败")
            all_passed = False
    except Exception as e:
        print(f"  ✗ 自定义字段测试异常: {e}")
        all_passed = False

    # 最终结果
    print("\n" + "=" * 60)
    if all_passed:
        print("✅ 自检全部通过")
        return 0
    else:
        print("❌ 自检存在失败项")
        return 1


# ============================================================
# 命令行入口
# ============================================================

def main() -> int:
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description="内容转换 结构化输出 置信度标注 — 将非结构化输入转为结构化结果",
        epilog="示例: python main.py --text '姓名：张三，金额：100元' 或 python main.py --file input.txt",
    )

    # 输入来源（三选一）
    input_group = parser.add_mutually_exclusive_group()
    input_group.add_argument("--text", type=str, help="直接输入文本内容")
    input_group.add_argument("--file", type=str, help="输入文件路径")
    input_group.add_argument("--url", type=str, help="输入URL地址")

    # 可选参数
    parser.add_argument("--fields", type=str, help="自定义字段列表，逗号分隔，如: name,date,amount")
    parser.add_argument("--selftest", action="store_true", help="运行内置自检")
    parser.add_argument("--output", type=str, help="输出到文件（JSON格式）")
    parser.add_argument("--verbose", action="store_true", help="显示详细信息")

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        return run_selftest()

    # 检查输入
    if not args.text and not args.file and not args.url:
        print("错误: 必须提供输入 (--text, --file 或 --url)", file=sys.stderr)
        print("提示: 使用 --selftest 运行自检", file=sys.stderr)
        return 1

    # 解析字段
    fields = None
    if args.fields:
        fields = [f.strip() for f in args.fields.split(",") if f.strip()]
        if len(fields) == 0:
            print("错误: E007 字段列表为空", file=sys.stderr)
            return 1

    try:
        # 准备输入内容
        if args.text:
            content = args.text
        elif args.file:
            try:
                content = _read_file_content(args.file)
            except RuntimeError as e:
                print(f"错误: {e} 文件读取失败", file=sys.stderr)
                return 1
        elif args.url:
            try:
                content = _fetch_url_content(args.url)
            except RuntimeError as e:
                print(f"错误: {e} URL获取失败", file=sys.stderr)
                return 1
        else:
            print("错误: E001 参数错误", file=sys.stderr)
            return 1

        # 处理输入
        result = process_input(content, fields)

        # 输出结果
        output_json = _safe_json_dumps(result)

        # 输出到文件或标准输出
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(output_json)
            if args.verbose:
                print(f"结果已写入: {args.output}")
        else:
            print(output_json)

        return 0

    except ValueError as e:
        error_code = str(e)
        error_msg = ERROR_MESSAGES.get(error_code, f"未知错误码: {error_code}")
        print(f"错误: {error_code} {error_msg}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"错误: E010 未知异常: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
