#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
backstage - Three-speed scripting language and task automation tool
独立实现脚本，仅依据功能规格编写（clean-room）。
"""

import argparse
import json
import sys
import os
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 错误码定义（E001-E010）
# ============================================================
ERROR_CODES = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：...",
    "E003": "输入格式不符合要求，示例：...",
    "E004": "这超出了本工具的能力范围，建议...",
    "E005": "结果无法确定，建议：...",
    "E006": "内部处理异常，请重试或检查输入",
    "E007": "输出格式生成失败",
    "E008": "批量处理中断",
    "E009": "参数校验失败",
    "E010": "未知错误",
}


def raise_error(code: str, detail: str = "") -> None:
    """抛出标准化错误信息"""
    msg = ERROR_CODES.get(code, ERROR_CODES["E010"])
    if detail:
        msg = f"{msg} | 详情: {detail}"
    print(f"[错误 {code}] {msg}")
    sys.exit(1)


# ============================================================
# 核心数据结构
# ============================================================
class InputData:
    """标准化输入数据容器"""

    def __init__(self, raw_content: str, source_type: str = "text"):
        self.raw_content = raw_content
        self.source_type = source_type
        self.parsed_fields: Dict[str, Any] = {}
        self.confidence: float = 0.0
        self.warnings: List[str] = []


class OutputResult:
    """标准化输出结果"""

    def __init__(self):
        self.fields: Dict[str, Any] = {}
        self.confidence: float = 0.0
        self.format: str = "json"
        self.timestamp: str = datetime.now().isoformat()


# ============================================================
# 核心处理逻辑
# ============================================================
def validate_input(raw_input: str) -> None:
    """校验输入有效性（E001/E003）"""
    if not raw_input or not raw_input.strip():
        raise_error("E001")
    if len(raw_input.strip()) < 2:
        raise_error("E003", "输入内容过短")


def parse_input(raw_input: str) -> InputData:
    """解析输入内容，识别关键信息"""
    data = InputData(raw_input.strip())

    # 检测输入类型
    if raw_input.strip().startswith(("{", "[")):
        try:
            data.parsed_fields = json.loads(raw_input.strip())
            data.source_type = "json"
        except json.JSONDecodeError:
            raise_error("E003", "JSON格式错误")
    elif os.path.isfile(raw_input.strip()):
        data.source_type = "file"
        try:
            with open(raw_input.strip(), "r", encoding="utf-8") as f:
                content = f.read()
            data.parsed_fields = {"file_path": raw_input.strip(), "content": content}
        except Exception:
            raise_error("E006", "文件读取失败")
    elif raw_input.strip().startswith(("http://", "https://")):
        data.source_type = "url"
        # 不访问网络，仅记录URL
        data.parsed_fields = {"url": raw_input.strip()}
    else:
        # 纯文本输入
        data.source_type = "text"
        data.parsed_fields = {"text": raw_input.strip()}

    return data


def extract_key_fields(data: InputData) -> Dict[str, Any]:
    """提取关键字段并结构化"""
    fields: Dict[str, Any] = {}

    if data.source_type == "json":
        # JSON输入直接使用
        fields = data.parsed_fields
    elif data.source_type == "file":
        # 文件输入提取基本信息
        fields = {
            "文件名": os.path.basename(data.parsed_fields.get("file_path", "")),
            "内容长度": len(data.parsed_fields.get("content", "")),
            "内容预览": data.parsed_fields.get("content", "")[:100],
        }
    elif data.source_type == "url":
        # URL输入仅记录
        fields = {"URL": data.parsed_fields.get("url", ""), "状态": "已记录（未访问）"}
    else:
        # 文本输入提取关键信息
        text = data.parsed_fields.get("text", "")
        # 提取可能的关键字段
        fields = {
            "文本内容": text,
            "字符数": len(text),
            "单词数": len(text.split()),
        }
        # 尝试提取关键词
        import re
        keywords = re.findall(r"[\u4e00-\u9fa5A-Za-z0-9]{2,}", text)
        if keywords:
            fields["关键词"] = list(dict.fromkeys(keywords))[:5]

    return fields


def calculate_confidence(data: InputData, fields: Dict[str, Any]) -> float:
    """计算置信度"""
    confidence = 0.0

    if not fields:
        return 0.0

    # 基础置信度
    if data.source_type == "json":
        confidence = 0.95
    elif data.source_type == "file":
        confidence = 0.90
    elif data.source_type == "url":
        confidence = 0.70  # 未访问网络，置信度低
    else:
        confidence = 0.80

    # 根据字段完整性调整
    if len(fields) >= 3:
        confidence += 0.05
    elif len(fields) < 2:
        confidence -= 0.10

    # 限制在0-1之间
    return max(0.0, min(1.0, confidence))


def generate_output(data: InputData, fields: Dict[str, Any], output_format: str = "json") -> OutputResult:
    """生成结构化输出"""
    result = OutputResult()
    result.fields = fields
    result.confidence = calculate_confidence(data, fields)
    result.format = output_format

    # 根据置信度添加标注
    if result.confidence < 0.85:
        result.fields["[需核实]"] = "部分信息无法完全确定，请人工复核"
    elif result.confidence < 0.90:
        result.fields["建议复核"] = "结果置信度中等，建议复核关键信息"

    return result


def format_output(result: OutputResult, output_format: str) -> str:
    """按指定格式输出结果"""
    try:
        if output_format == "json":
            return json.dumps(result.fields, ensure_ascii=False, indent=2)
        elif output_format == "text":
            lines = []
            for key, value in result.fields.items():
                lines.append(f"{key}: {value}")
            return "\n".join(lines)
        else:
            raise_error("E007", f"不支持的输出格式: {output_format}")
    except Exception:
        raise_error("E007", "输出格式化失败")


def process_input(raw_input: str, output_format: str = "json") -> str:
    """完整处理流程"""
    # Step 1: 校验输入
    validate_input(raw_input)

    # Step 2: 解析输入
    data = parse_input(raw_input)

    # Step 3: 提取关键字段
    fields = extract_key_fields(data)

    # Step 4: 生成输出
    result = generate_output(data, fields, output_format)

    # Step 5: 格式化输出
    return format_output(result, output_format)


# ============================================================
# 批量处理
# ============================================================
def batch_process(inputs: List[str], output_format: str = "json") -> List[str]:
    """批量处理多个输入"""
    results = []
    try:
        for i, item in enumerate(inputs):
            try:
                result = process_input(item, output_format)
                results.append(result)
            except SystemExit:
                results.append(f"[错误] 第{i+1}个输入处理失败")
    except Exception:
        raise_error("E008", "批量处理中断")

    return results


# ============================================================
# 内置自检数据（硬编码样例）
# ============================================================
SELFTEST_CASES = [
    {
        "input": "这是一个测试文本，包含关键词：编程、自动化、脚本",
        "expected_format": "json",
    },
    {
        "input": '{"name": "test", "type": "example", "value": 42}',
        "expected_format": "json",
    },
    {
        "input": "https://example.com/some/page",
        "expected_format": "json",
    },
]


def run_selftest() -> bool:
    """内置自检：使用硬编码样例验证核心逻辑"""
    print("=" * 60)
    print("自检开始（使用内置样例数据）")
    print("=" * 60)

    all_passed = True

    # 测试1: 正常文本处理
    print("\n[测试1] 文本输入处理")
    try:
        result = process_input(SELFTEST_CASES[0]["input"])
        parsed = json.loads(result)
        # 宽松断言：检查关键字段存在
        assert "文本内容" in parsed, "缺少文本内容字段"
        assert "字符数" in parsed, "缺少字符数字段"
        assert "单词数" in parsed, "缺少单词数字段"
        assert parsed["字符数"] > 0, "字符数应为正数"
        assert parsed["单词数"] > 0, "单词数应为正数"
        print("  ✓ 通过")
    except AssertionError as e:
        print(f"  ✗ 失败: {e}")
        all_passed = False
    except Exception as e:
        print(f"  ✗ 异常: {e}")
        all_passed = False

    # 测试2: JSON输入处理
    print("\n[测试2] JSON输入处理")
    try:
        result = process_input(SELFTEST_CASES[1]["input"])
        parsed = json.loads(result)
        # 宽松断言：检查关键字段存在
        assert "name" in parsed, "缺少name字段"
        assert "type" in parsed, "缺少type字段"
        assert "value" in parsed, "缺少value字段"
        assert parsed["value"] > 0, "value应为正数"
        print("  ✓ 通过")
    except AssertionError as e:
        print(f"  ✗ 失败: {e}")
        all_passed = False
    except Exception as e:
        print(f"  ✗ 异常: {e}")
        all_passed = False

    # 测试3: URL输入处理
    print("\n[测试3] URL输入处理")
    try:
        result = process_input(SELFTEST_CASES[2]["input"])
        parsed = json.loads(result)
        # 宽松断言：检查URL字段存在且包含http
        assert "URL" in parsed, "缺少URL字段"
        assert "http" in parsed["URL"], "URL字段应包含http"
        print("  ✓ 通过")
    except AssertionError as e:
        print(f"  ✗ 失败: {e}")
        all_passed = False
    except Exception as e:
        print(f"  ✗ 异常: {e}")
        all_passed = False

    # 测试4: 错误处理测试
    print("\n[测试4] 错误处理测试")
    try:
        process_input("")
        print("  ✗ 失败: 空输入未触发错误")
        all_passed = False
    except SystemExit:
        print("  ✓ 通过（空输入正确触发E001）")

    # 测试5: 置信度测试
    print("\n[测试5] 置信度测试")
    try:
        data = parse_input("短文本")
        fields = extract_key_fields(data)
        conf = calculate_confidence(data, fields)
        # 宽松断言：置信度在合理范围内
        assert 0.0 <= conf <= 1.0, "置信度应在0-1之间"
        assert conf > 0.5, "正常输入置信度应大于0.5"
        print(f"  ✓ 通过（置信度: {conf:.2f}）")
    except AssertionError as e:
        print(f"  ✗ 失败: {e}")
        all_passed = False
    except Exception as e:
        print(f"  ✗ 异常: {e}")
        all_passed = False

    print("\n" + "=" * 60)
    if all_passed:
        print("自检全部通过 ✓")
    else:
        print("自检存在失败项 ✗")
    print("=" * 60)

    return all_passed


# ============================================================
# 主入口
# ============================================================
def main():
    """命令行主入口"""
    parser = argparse.ArgumentParser(
        description="backstage - 三速脚本语言与任务自动化工具",
        epilog="示例: python main.py '处理这段文本' --format json",
    )

    # 输入参数
    parser.add_argument(
        "input",
        nargs="?",
        help="待处理的内容（文本/JSON/文件路径/URL）",
    )
    parser.add_argument(
        "--format",
        choices=["json", "text"],
        default="json",
        help="输出格式（默认: json）",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检（使用硬编码样例，不依赖外部文件）",
    )
    parser.add_argument(
        "--batch",
        nargs="*",
        help="批量处理多个输入",
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        success = run_selftest()
        sys.exit(0 if success else 1)

    # 批量处理模式
    if args.batch:
        results = batch_process(args.batch, args.format)
        for i, r in enumerate(results, 1):
            print(f"--- 结果 {i} ---")
            print(r)
            print()
        sys.exit(0)

    # 单次处理模式
    if not args.input:
        parser.print_help()
        raise_error("E001")

    try:
        result = process_input(args.input, args.format)
        print(result)
    except SystemExit:
        # 错误已在 raise_error 中打印
        sys.exit(1)


if __name__ == "__main__":
    main()
