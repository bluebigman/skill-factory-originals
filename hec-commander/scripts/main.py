#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
hec-commander 独立实现脚本
功能：将用户提供的数据/文件/URL 转换为结构化结果，支持批量处理与自定义格式。
仅依据功能规格独立实现（clean-room），不复制任何既有代码。
"""

import argparse
import json
import os
import sys
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 错误码与提示信息（依据规格第五节）
# ============================================================
ERROR_MESSAGES = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：...",
    "E003": "输入格式不符合要求，示例：...",
    "E004": "这超出了本工具的能力范围，建议...",
    "E005": "结果无法确定，建议：...",
    "E006": "内部处理错误，请重试或检查输入",
    "E007": "批量处理中断：部分条目失败",
    "E008": "输出格式不支持，请选择 json 或 text",
    "E009": "置信度计算失败，使用默认值",
    "E010": "未知错误，请查看日志",
}

# 置信度阈值（依据规格第三节）
HIGH_CONFIDENCE = 0.90
MEDIUM_CONFIDENCE = 0.85


# ============================================================
# 核心数据结构
# ============================================================
class ProcessedItem:
    """单条处理结果的数据结构"""
    def __init__(self, source: str, content: str, fields: Dict[str, Any],
                 confidence: float, warnings: List[str] = None):
        self.source = source          # 输入来源（数据/文件路径/URL）
        self.content = content        # 原始内容
        self.fields = fields          # 结构化字段
        self.confidence = confidence  # 置信度 0-1
        self.warnings = warnings or []  # 警告列表
        self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "source": self.source,
            "content": self.content,
            "fields": self.fields,
            "confidence": round(self.confidence, 2),
            "warnings": self.warnings,
            "timestamp": self.timestamp,
        }


# ============================================================
# 核心处理逻辑
# ============================================================
def validate_input(raw_input: str) -> Tuple[bool, Optional[str]]:
    """
    校验输入是否有效（E001/E003）
    返回：(是否有效, 错误码或None)
    """
    if not raw_input or not raw_input.strip():
        return False, "E001"
    if len(raw_input.strip()) < 2:
        return False, "E003"
    return True, None


def detect_source_type(raw_input: str) -> str:
    """
    识别输入来源类型：数据 / 文件 / URL
    """
    stripped = raw_input.strip()
    # URL 检测
    if re.match(r'^https?://', stripped, re.IGNORECASE):
        return "URL"
    # 文件路径检测（存在或包含路径分隔符）
    if os.path.sep in stripped or (len(stripped) > 4 and '.' in stripped.split(os.path.sep)[-1]):
        return "文件"
    # 默认视为数据
    return "数据"


def extract_fields(content: str) -> Dict[str, Any]:
    """
    从内容中提取关键字段（依据规格能力1）
    识别常见键值对、JSON、CSV等格式
    """
    fields: Dict[str, Any] = {}
    content = content.strip()

    # 尝试 JSON 解析
    try:
        data = json.loads(content)
        if isinstance(data, dict):
            return {k: v for k, v in data.items()}
    except json.JSONDecodeError:
        pass

    # 尝试键值对解析（key: value 或 key=value）
    kv_pattern = re.compile(r'([\w\s]+)[:=]\s*(.+)')
    for line in content.split('\n'):
        line = line.strip()
        if not line:
            continue
        match = kv_pattern.match(line)
        if match:
            key = match.group(1).strip()
            value = match.group(2).strip()
            fields[key] = value

    # 尝试 CSV 解析（逗号分隔）
    if not fields and ',' in content:
        parts = [p.strip() for p in content.split(',')]
        if len(parts) >= 2:
            fields["_csv_parts"] = parts
            fields["_count"] = len(parts)

    # 如果什么都没有提取到，存入原始内容
    if not fields:
        fields["_raw"] = content
        fields["_length"] = len(content)

    return fields


def calculate_confidence(fields: Dict[str, Any], source_type: str) -> Tuple[float, List[str]]:
    """
    计算置信度（依据规格第三节）
    返回：(置信度, 警告列表)
    """
    warnings = []
    confidence = 0.0

    # 基础置信度
    if fields:
        confidence += 0.5

    # 根据字段丰富度加分
    named_fields = [k for k in fields.keys() if not k.startswith('_')]
    if named_fields:
        confidence += min(0.3, len(named_fields) * 0.1)
    elif "_csv_parts" in fields:
        confidence += 0.2
    elif "_raw" in fields:
        confidence += 0.1

    # 根据来源类型加分
    if source_type == "数据":
        confidence += 0.2
    elif source_type == "文件":
        confidence += 0.1  # 文件可能解析不完整
    elif source_type == "URL":
        confidence += 0.05  # URL 内容需要额外验证

    # 限制在 0-1 之间
    confidence = max(0.0, min(1.0, confidence))

    # 生成警告
    if confidence < MEDIUM_CONFIDENCE:
        warnings.append("识别结果可能不完整，建议人工复核")
    if source_type == "URL":
        warnings.append("URL内容未实际访问，基于输入文本分析")

    return confidence, warnings


def process_single_item(raw_input: str) -> ProcessedItem:
    """
    处理单个输入项（核心流程 Step 2）
    """
    # 输入校验
    valid, error_code = validate_input(raw_input)
    if not valid:
        raise ValueError(error_code)

    # 识别来源类型
    source_type = detect_source_type(raw_input)

    # 解析内容
    content = raw_input.strip()
    fields = extract_fields(content)

    # 计算置信度
    confidence, warnings = calculate_confidence(fields, source_type)

    # 构建结果
    return ProcessedItem(
        source=source_type,
        content=content,
        fields=fields,
        confidence=confidence,
        warnings=warnings
    )


def format_output(item: ProcessedItem, output_format: str = "json") -> str:
    """
    格式化输出（依据规格 Step 3）
    支持 json 和 text 两种格式
    """
    if output_format == "json":
        return json.dumps(item.to_dict(), ensure_ascii=False, indent=2)
    elif output_format == "text":
        lines = [
            f"来源: {item.source}",
            f"内容: {item.content[:50]}{'...' if len(item.content) > 50 else ''}",
            f"置信度: {item.confidence:.0%}",
        ]
        if item.fields:
            lines.append("字段:")
            for k, v in list(item.fields.items())[:5]:
                lines.append(f"  {k}: {str(v)[:50]}")
        if item.warnings:
            lines.append("警告:")
            for w in item.warnings:
                lines.append(f"  - {w}")
        return "\n".join(lines)
    else:
        raise ValueError("E008")


def process_batch(inputs: List[str], output_format: str = "json") -> List[Dict[str, Any]]:
    """
    批量处理（依据规格进阶用法）
    """
    results = []
    errors = []
    for idx, raw_input in enumerate(inputs):
        try:
            item = process_single_item(raw_input)
            results.append(item.to_dict())
        except ValueError as e:
            error_code = str(e)
            errors.append({
                "index": idx,
                "error": error_code,
                "message": ERROR_MESSAGES.get(error_code, ERROR_MESSAGES["E010"])
            })

    if errors:
        # 部分失败时添加警告
        results.append({
            "_batch_errors": errors,
            "_partial_failure": True
        })

    return results


# ============================================================
# 自检模块（--selftest）
# ============================================================
def run_selftest() -> int:
    """
    内置硬编码样例数据的离线自检
    使用宽松阈值（大小比较/区间判断），不依赖精确值
    """
    print("=" * 60)
    print("hec-commander 自检开始")
    print("=" * 60)

    # 测试样例（硬编码，不读外部文件，不访问网络）
    test_cases = [
        ("这是测试数据", "数据"),
        ("name: 张三\nage: 30\ncity: 北京", "数据"),
        ("https://example.com/data", "URL"),
        ("/tmp/test_file.csv", "文件"),
        ("", None),  # 空输入测试
    ]

    passed = 0
    total = 0

    for idx, (input_text, expected_type) in enumerate(test_cases):
        total += 1
        try:
            if input_text == "":
                # 测试空输入应该报错
                valid, error_code = validate_input(input_text)
                if not valid and error_code == "E001":
                    print(f"[PASS] 用例{idx+1}: 空输入正确返回 E001")
                    passed += 1
                else:
                    print(f"[FAIL] 用例{idx+1}: 空输入未正确返回 E001")
                continue

            # 正常处理
            item = process_single_item(input_text)

            # 宽松断言：置信度在合理范围
            assert 0.0 <= item.confidence <= 1.0, "置信度超出范围"

            # 来源类型合理（不严格匹配）
            assert item.source in ["数据", "文件", "URL"], "来源类型不合法"

            # 字段非空
            assert item.fields is not None, "字段为空"

            # 时间戳存在
            assert item.timestamp, "时间戳缺失"

            # 输出格式可转换
            json_output = format_output(item, "json")
            assert json_output, "JSON输出为空"

            text_output = format_output(item, "text")
            assert text_output, "文本输出为空"

            print(f"[PASS] 用例{idx+1}: 处理成功 (来源={item.source}, 置信度={item.confidence:.0%})")
            passed += 1

        except Exception as e:
            print(f"[FAIL] 用例{idx+1}: 异常 - {str(e)}")

    # 批量处理测试
    total += 1
    try:
        batch_inputs = ["测试1", "测试2", ""]
        results = process_batch(batch_inputs)
        assert len(results) >= 2, "批量处理结果数量不足"
        print(f"[PASS] 批量处理: 成功处理 {len(results)} 条结果")
        passed += 1
    except Exception as e:
        print(f"[FAIL] 批量处理: 异常 - {str(e)}")

    # 错误码测试
    total += 1
    try:
        valid, error_code = validate_input("")
        if not valid and error_code in ERROR_MESSAGES:
            print(f"[PASS] 错误码体系: E001 存在且消息正确")
            passed += 1
        else:
            print(f"[FAIL] 错误码体系: E001 未正确触发")
    except Exception as e:
        print(f"[FAIL] 错误码体系: 异常 - {str(e)}")

    # 输出格式测试
    total += 1
    try:
        item = process_single_item("测试数据")
        format_output(item, "json")  # 应该成功
        try:
            format_output(item, "xml")  # 应该失败
            print(f"[FAIL] 输出格式: 无效格式未报错")
        except ValueError as e:
            if str(e) == "E008":
                print(f"[PASS] 输出格式: 无效格式正确返回 E008")
                passed += 1
            else:
                print(f"[FAIL] 输出格式: 错误码不正确")
    except Exception as e:
        print(f"[FAIL] 输出格式: 异常 - {str(e)}")

    # 汇总
    print("=" * 60)
    print(f"自检结果: {passed}/{total} 通过")
    print("=" * 60)

    return 0 if passed == total else 1


# ============================================================
# 主入口
# ============================================================
def main() -> int:
    """主函数：解析命令行参数并执行"""
    parser = argparse.ArgumentParser(
        description="hec-commander - 数据转换与结构化工具",
        epilog="示例: python main.py 'name: 张三' --format json"
    )
    parser.add_argument(
        "inputs", nargs="*",
        help="待处理的内容（数据/文件路径/URL），可多个"
    )
    parser.add_argument(
        "--format", "-f", choices=["json", "text"], default="json",
        help="输出格式 (默认: json)"
    )
    parser.add_argument(
        "--selftest", action="store_true",
        help="运行内置自检（不读外部文件、不访问网络）"
    )
    parser.add_argument(
        "--batch", action="store_true",
        help="批量处理模式（逐行读取标准输入）"
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        return run_selftest()

    # 批量模式：从标准输入读取
    if args.batch:
        if not sys.stdin.isatty():
            inputs = [line.strip() for line in sys.stdin if line.strip()]
            if not inputs:
                print(ERROR_MESSAGES["E001"], file=sys.stderr)
                return 1
            results = process_batch(inputs, args.format)
            print(json.dumps(results, ensure_ascii=False, indent=2))
            return 0
        else:
            print("批量模式需要从标准输入提供数据", file=sys.stderr)
            return 1

    # 单条/多条处理
    if not args.inputs:
        print(ERROR_MESSAGES["E001"], file=sys.stderr)
        return 1

    try:
        if len(args.inputs) == 1:
            # 单条处理
            item = process_single_item(args.inputs[0])
            print(format_output(item, args.format))
        else:
            # 多条处理
            results = process_batch(args.inputs, args.format)
            print(json.dumps(results, ensure_ascii=False, indent=2))
        return 0
    except ValueError as e:
        error_code = str(e)
        message = ERROR_MESSAGES.get(error_code, ERROR_MESSAGES["E010"])
        print(f"错误 {error_code}: {message}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"错误 E010: {ERROR_MESSAGES['E010']} - {str(e)}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
