#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py — glooit 技能核心逻辑独立实现（clean-room 重写）

本脚本仅依据功能规格文档独立编写，不包含任何既有实现代码。
提供命令行入口与 --selftest 离线自检功能。
"""

import argparse
import json
import sys
import re
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# 常量定义
# ---------------------------------------------------------------------------
ERROR_CODES = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：输入来源或输出格式要求",
    "E003": "输入格式不符合要求，示例：JSON 数组或逗号分隔字符串",
    "E004": "这超出了本工具的能力范围，建议使用专用工具处理",
    "E005": "结果无法确定，建议：提供更多上下文或人工复核",
    "E006": "内部处理错误，请联系开发者",
    "E007": "批量处理中部分条目失败",
    "E008": "输出格式不受支持",
    "E009": "输入内容超过单次处理上限",
    "E010": "无效的置信度阈值参数",
}

# 默认处理阈值
CONFIDENCE_HIGH = 0.90
CONFIDENCE_MEDIUM = 0.85

# 支持的关键字段（用于结构化识别）
KEY_FIELDS = ["名称", "类型", "数量", "日期", "金额", "状态", "描述"]

# 批量处理最大条目数
MAX_BATCH_ITEMS = 100


# ---------------------------------------------------------------------------
# 数据模型
# ---------------------------------------------------------------------------
class ProcessingResult:
    """处理结果数据类"""

    def __init__(self, data: Any, confidence: float, warnings: Optional[List[str]] = None):
        self.data = data
        self.confidence = confidence
        self.warnings = warnings or []

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "data": self.data,
            "confidence": self.confidence,
            "warnings": self.warnings,
        }


# ---------------------------------------------------------------------------
# 核心处理逻辑
# ---------------------------------------------------------------------------
def validate_input(raw_input: str) -> Tuple[bool, Optional[str]]:
    """
    校验输入是否有效
    返回 (是否有效, 错误码或None)
    """
    if not raw_input or not raw_input.strip():
        return False, "E001"
    return True, None


def parse_input(raw_input: str) -> Tuple[Optional[Any], Optional[str]]:
    """
    解析输入内容（支持 JSON / 逗号分隔 / 纯文本）
    返回 (解析结果, 错误码或None)
    """
    text = raw_input.strip()

    # 尝试 JSON 解析
    if text.startswith(("{", "[")):
        try:
            return json.loads(text), None
        except json.JSONDecodeError:
            return None, "E003"

    # 尝试逗号分隔
    if "," in text:
        parts = [p.strip() for p in text.split(",") if p.strip()]
        if parts:
            return parts, None

    # 按纯文本处理
    return text, None


def extract_key_fields(data: Any) -> Tuple[Dict[str, Any], float]:
    """
    从输入中识别关键信息并结构化
    返回 (结构化结果, 置信度)
    """
    result: Dict[str, Any] = {}
    found_fields = 0

    if isinstance(data, dict):
        # 字典输入：先尝试精确匹配
        for field in KEY_FIELDS:
            if field in data:
                result[field] = data[field]
                found_fields += 1
        
        # 如果精确匹配的字段较少，尝试模糊匹配（但避免重复匹配同一个键）
        if found_fields < 2:
            used_keys = set()
            for field in KEY_FIELDS:
                if field in result:
                    continue
                # 寻找最匹配的键
                best_match = None
                best_score = 0
                for key in data.keys():
                    if key in used_keys or key in result:
                        continue
                    # 计算匹配分数
                    score = 0
                    if field in key:
                        score = 2
                    elif key in field:
                        score = 1
                    elif field[:2] in key or key[:2] in field:
                        score = 0.5
                    
                    if score > best_score:
                        best_score = score
                        best_match = key
                
                if best_match and best_score >= 1:
                    result[field] = data[best_match]
                    used_keys.add(best_match)
                    found_fields += 1

    elif isinstance(data, list):
        # 列表输入：尝试按位置映射
        for i, item in enumerate(data):
            if i < len(KEY_FIELDS):
                result[KEY_FIELDS[i]] = item
                found_fields += 1

    elif isinstance(data, str):
        # 字符串输入：尝试提取常见模式
        # 日期模式
        date_match = re.search(r"\d{4}-\d{2}-\d{2}", data)
        if date_match:
            result["日期"] = date_match.group()
            found_fields += 1

        # 金额模式
        amount_match = re.search(r"(?:¥|￥|RMB)?\s*(\d+(?:\.\d{1,2})?)", data)
        if amount_match:
            result["金额"] = amount_match.group(1)
            found_fields += 1

        # 状态关键词
        for status in ["完成", "进行中", "待处理", "已取消"]:
            if status in data:
                result["状态"] = status
                found_fields += 1
                break

    else:
        # 其他类型
        result["内容"] = str(data)
        found_fields = 1

    # 计算置信度
    if isinstance(data, dict):
        total_fields = max(len(KEY_FIELDS), 1)
        confidence = found_fields / total_fields
    elif isinstance(data, list):
        confidence = min(1.0, found_fields / 3)  # 至少识别3个字段才给高置信度
    else:
        confidence = 0.7 if found_fields > 0 else 0.3

    # 置信度范围限制
    confidence = max(0.0, min(1.0, confidence))

    return result, confidence


def format_output(result: ProcessingResult, output_format: str = "json") -> Tuple[Optional[str], Optional[str]]:
    """
    按指定格式输出结果
    返回 (输出内容, 错误码或None)
    """
    if output_format == "json":
        return json.dumps(result.to_dict(), ensure_ascii=False, indent=2), None
    elif output_format == "text":
        lines = []
        lines.append(f"置信度: {result.confidence:.1%}")
        if result.warnings:
            lines.append(f"警告: {'; '.join(result.warnings)}")
        lines.append("数据:")
        if isinstance(result.data, dict):
            for key, value in result.data.items():
                lines.append(f"  {key}: {value}")
        else:
            lines.append(f"  {result.data}")
        return "\n".join(lines), None
    else:
        return None, "E008"


def process_item(item: Any) -> ProcessingResult:
    """
    处理单个条目
    """
    structured, confidence = extract_key_fields(item)
    warnings = []

    # 置信度标注
    if confidence < CONFIDENCE_MEDIUM:
        warnings.append("[需核实] 置信度过低，请人工复核")
    elif confidence < CONFIDENCE_HIGH:
        warnings.append("建议复核")

    return ProcessingResult(structured, confidence, warnings)


def process_batch(items: List[Any]) -> Tuple[List[ProcessingResult], List[int]]:
    """
    批量处理多个条目
    返回 (结果列表, 失败索引列表)
    """
    results = []
    failed_indices = []

    for idx, item in enumerate(items):
        if idx >= MAX_BATCH_ITEMS:
            failed_indices.extend(range(idx, len(items)))
            break
        try:
            results.append(process_item(item))
        except Exception:
            failed_indices.append(idx)
            results.append(ProcessingResult(None, 0.0, ["处理失败"]))

    return results, failed_indices


def main_process(input_text: str, output_format: str = "json") -> Tuple[Optional[str], Optional[str]]:
    """
    主处理流程
    返回 (输出内容, 错误码或None)
    """
    # Step 1: 输入校验
    valid, error_code = validate_input(input_text)
    if not valid:
        return None, error_code

    # Step 2: 解析输入
    parsed, parse_error = parse_input(input_text)
    if parse_error:
        return None, parse_error

    # Step 3: 处理数据
    if isinstance(parsed, list):
        # 批量处理
        results, failed_indices = process_batch(parsed)
        if failed_indices and len(failed_indices) == len(parsed):
            return None, "E007"

        # 汇总结果
        combined_result = ProcessingResult(
            data=[r.to_dict() for r in results],
            confidence=sum(r.confidence for r in results) / max(len(results), 1),
            warnings=[f"条目 {i} 处理失败" for i in failed_indices]
        )
    else:
        # 单条处理
        combined_result = process_item(parsed)

    # Step 4: 格式化输出
    output, format_error = format_output(combined_result, output_format)
    if format_error:
        return None, format_error

    return output, None


# ---------------------------------------------------------------------------
# 自检模块（--selftest）
# ---------------------------------------------------------------------------
def run_selftest() -> bool:
    """
    离线自检核心逻辑，使用内置硬编码数据
    不访问网络、不读文件、不依赖当前目录
    """
    print("=== glooit 自检开始 ===")

    # 测试用例 1: 空输入
    print("\n[1/5] 测试空输入处理...")
    output, error = main_process("")
    assert error == "E001", f"期望 E001，实际 {error}"
    assert output is None, "空输入不应有输出"
    print("  通过 ✓")

    # 测试用例 2: 单条字典输入
    print("\n[2/5] 测试字典输入处理...")
    test_dict = {
        "名称": "示例项目",
        "类型": "开发任务",
        "数量": 3,
        "日期": "2026-01-15",
        "金额": 999.99,
        "状态": "进行中"
    }
    output, error = main_process(json.dumps(test_dict, ensure_ascii=False))
    assert error is None, f"不应有错误，实际 {error}"
    assert output is not None, "应有输出"
    result = json.loads(output)
    assert result["data"]["data"]["名称"] == "示例项目", "名称字段提取失败"
    assert result["data"]["confidence"] > 0.5, "置信度应大于0.5"
    print("  通过 ✓")

    # 测试用例 3: 批量列表输入
    print("\n[3/5] 测试批量输入处理...")
    test_list = [
        {"名称": "任务A", "状态": "完成"},
        {"名称": "任务B", "状态": "进行中"},
        {"名称": "任务C", "状态": "待处理"}
    ]
    output, error = main_process(json.dumps(test_list, ensure_ascii=False))
    assert error is None, f"不应有错误，实际 {error}"
    assert output is not None, "应有输出"
    result = json.loads(output)
    assert len(result["data"]["data"]) == 3, "应处理3个条目"
    print("  通过 ✓")

    # 测试用例 4: 文本输入
    print("\n[4/5] 测试文本输入处理...")
    test_text = "2026-03-20 完成项目 金额 1500 元"
    output, error = main_process(test_text, "text")
    assert error is None, f"不应有错误，实际 {error}"
    assert output is not None, "应有输出"
    assert "置信度" in output, "文本输出应包含置信度"
    print("  通过 ✓")

    # 测试用例 5: 错误输入
    print("\n[5/5] 测试格式错误输入...")
    bad_json = "{invalid json content"
    output, error = main_process(bad_json)
    assert error == "E003", f"期望 E003，实际 {error}"
    print("  通过 ✓")

    print("\n=== 全部自检通过 ===")
    return True


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------
def main() -> int:
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description="glooit - 通用数据处理工具（clean-room 独立实现）",
        epilog="示例: python main.py --input '数据内容' --format text"
    )
    parser.add_argument("--input", "-i", type=str, help="待处理的数据内容")
    parser.add_argument("--format", "-f", choices=["json", "text"], default="json",
                        help="输出格式 (默认: json)")
    parser.add_argument("--selftest", action="store_true",
                        help="运行离线自检（不读取外部数据）")
    parser.add_argument("--version", "-v", action="version", version="glooit 1.0.0")

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        try:
            success = run_selftest()
            return 0 if success else 1
        except AssertionError as e:
            print(f"自检失败: {e}")
            return 1

    # 正常处理模式
    if not args.input:
        print(f"错误 [E001]: {ERROR_CODES['E001']}", file=sys.stderr)
        print("提示: 使用 --input 参数提供数据，或使用 --selftest 运行自检", file=sys.stderr)
        return 1

    try:
        output, error_code = main_process(args.input, args.format)
        if error_code:
            print(f"错误 [{error_code}]: {ERROR_CODES.get(error_code, '未知错误')}", file=sys.stderr)
            return 1

        print(output)
        return 0

    except Exception as e:
        print(f"错误 [E006]: {ERROR_CODES['E006']} - {str(e)}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
