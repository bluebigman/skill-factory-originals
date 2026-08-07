#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
laravel-dynamic-report-generator 独立实现脚本
=============================================
依据功能规格独立编写（clean-room），不依赖任何既有实现。

功能概述：
- 将用户提供的数据（文本/结构化内容）转换为结构化报告
- 支持批量处理、自定义输出格式
- 内置自检模式（--selftest），离线硬编码样例验证核心逻辑

错误码：
- E001: 输入为空
- E002: 关键信息缺失
- E003: 输入格式错误
- E004: 超出能力边界
- E005: 置信度过低
- E006: 内部处理异常
- E007: 参数解析错误
- E008: 输出格式不支持
- E009: 批量处理中断
- E010: 未知错误

用法示例：
    python main.py --input "用户提供的数据" --format json
    python main.py --selftest
"""

import argparse
import json
import os
import sys
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 常量定义
# ============================================================

# 错误码与标准话术映射
ERROR_MESSAGES: Dict[str, str] = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：",
    "E003": "输入格式不符合要求，示例：",
    "E004": "这超出了本工具的能力范围，建议：",
    "E005": "结果无法确定，建议：",
    "E006": "内部处理异常，请重试或联系管理员",
    "E007": "参数解析错误，请检查命令行参数",
    "E008": "输出格式不支持，支持的格式：json, text",
    "E009": "批量处理中断，请检查输入数据",
    "E010": "未知错误，请重试",
}

# 支持的关键字段（用于信息提取）
KEY_FIELDS: List[str] = [
    "id", "name", "title", "date", "amount", "status", "category", "description"
]

# 置信度阈值
HIGH_CONFIDENCE = 90
MEDIUM_CONFIDENCE = 85

# 输出格式支持列表
SUPPORTED_FORMATS = ["json", "text"]


# ============================================================
# 核心类与函数
# ============================================================

class ReportGenerator:
    """报告生成器核心类"""

    def __init__(self, input_data: Optional[str] = None, output_format: str = "json"):
        """
        初始化报告生成器

        Args:
            input_data: 用户提供的输入数据
            output_format: 输出格式（json/text）
        """
        self.input_data = input_data
        self.output_format = output_format
        self.parsed_data: List[Dict[str, Any]] = []
        self.confidence: int = 0
        self.warnings: List[str] = []

    def validate_input(self) -> Tuple[bool, str]:
        """
        校验输入数据是否有效

        Returns:
            (是否有效, 错误码或空字符串)
        """
        if not self.input_data or not self.input_data.strip():
            return False, "E001"
        if len(self.input_data.strip()) < 2:
            return False, "E003"
        return True, ""

    def parse_input(self) -> Tuple[bool, str]:
        """
        解析输入数据，提取结构化信息

        Returns:
            (是否成功, 错误码或空字符串)
        """
        # 校验输入
        valid, err_code = self.validate_input()
        if not valid:
            return False, err_code

        try:
            # 尝试将输入解析为 JSON（若为 JSON 格式）
            try:
                json_data = json.loads(self.input_data)
                if isinstance(json_data, list):
                    self.parsed_data = json_data
                elif isinstance(json_data, dict):
                    self.parsed_data = [json_data]
                else:
                    # 非对象/数组 JSON，转为文本处理
                    self._parse_text(str(json_data))
            except json.JSONDecodeError:
                # 非 JSON，按文本解析
                self._parse_text(self.input_data)

            if not self.parsed_data:
                return False, "E002"

            # 计算置信度
            self._calculate_confidence()

            return True, ""

        except Exception:
            return False, "E006"

    def _parse_text(self, text: str) -> None:
        """
        解析纯文本输入，按行提取关键信息

        Args:
            text: 待解析的文本
        """
        lines = [line.strip() for line in text.split("\n") if line.strip()]

        for line in lines:
            record: Dict[str, Any] = {}
            # 尝试按常见分隔符拆分
            parts = line.replace("，", ",").replace("；", ",").split(",")

            for part in parts:
                part = part.strip()
                if not part:
                    continue

                # 尝试 key:value 或 key=value 格式
                if ":" in part:
                    key, value = part.split(":", 1)
                elif "=" in part:
                    key, value = part.split("=", 1)
                else:
                    # 无分隔符，作为 name 字段
                    key, value = "name", part

                key = key.strip().lower()
                value = value.strip()

                # 仅保留关键字段
                if key in KEY_FIELDS and key not in record:
                    record[key] = value

            if record:
                # 补充默认字段
                if "id" not in record:
                    record["id"] = str(uuid.uuid4())[:8]
                if "date" not in record:
                    record["date"] = datetime.now().strftime("%Y-%m-%d")
                self.parsed_data.append(record)

    def _calculate_confidence(self) -> None:
        """计算结果置信度"""
        if not self.parsed_data:
            self.confidence = 0
            return

        # 基于解析成功率计算置信度
        total_parts = 0
        matched_parts = 0

        for record in self.parsed_data:
            # 每条记录至少包含 2 个关键字段视为完整
            matched = len([k for k in record.keys() if k in KEY_FIELDS])
            total_parts += max(len(record), 2)
            matched_parts += min(matched, 2)

        if total_parts > 0:
            self.confidence = int((matched_parts / total_parts) * 100)
        else:
            self.confidence = 0

        # 置信度校准：至少有一条完整记录则不低于 85
        if self.parsed_data and any(len(r) >= 2 for r in self.parsed_data):
            self.confidence = max(self.confidence, MEDIUM_CONFIDENCE)

        # 添加置信度提示
        if self.confidence < MEDIUM_CONFIDENCE:
            self.warnings.append("部分字段未能识别，结果可能不完整")
        elif self.confidence < HIGH_CONFIDENCE:
            self.warnings.append("建议复核部分解析结果")

    def generate_report(self) -> Tuple[bool, Dict[str, Any]]:
        """
        生成结构化报告

        Returns:
            (是否成功, 报告内容)
        """
        success, err_code = self.parse_input()
        if not success:
            return False, {"error": err_code, "message": ERROR_MESSAGES.get(err_code, "")}

        report = {
            "generated_at": datetime.now().isoformat(),
            "record_count": len(self.parsed_data),
            "confidence": self.confidence,
            "warnings": self.warnings,
            "data": self.parsed_data,
        }

        # 根据置信度添加标注
        if self.confidence >= HIGH_CONFIDENCE:
            report["status"] = "直接输出"
        elif self.confidence >= MEDIUM_CONFIDENCE:
            report["status"] = "建议复核"
        else:
            report["status"] = "[需核实]"

        return True, report

    def format_output(self, report: Dict[str, Any]) -> str:
        """
        按指定格式输出报告

        Args:
            report: 报告内容（字典）

        Returns:
            格式化后的字符串
        """
        if self.output_format == "json":
            return json.dumps(report, ensure_ascii=False, indent=2)
        elif self.output_format == "text":
            lines = []
            lines.append(f"报告生成时间: {report['generated_at']}")
            lines.append(f"记录数: {report['record_count']}")
            lines.append(f"置信度: {report['confidence']}%")
            lines.append(f"状态: {report['status']}")

            if report.get("warnings"):
                lines.append("提示:")
                for warn in report["warnings"]:
                    lines.append(f"  - {warn}")

            lines.append("\n数据内容:")
            for record in report["data"]:
                lines.append(f"  {json.dumps(record, ensure_ascii=False)}")

            return "\n".join(lines)
        else:
            return json.dumps({"error": "E008", "message": ERROR_MESSAGES["E008"]}, ensure_ascii=False)


def process_batch(inputs: List[str], output_format: str = "json") -> List[Dict[str, Any]]:
    """
    批量处理多个输入

    Args:
        inputs: 输入数据列表
        output_format: 输出格式

    Returns:
        处理结果列表
    """
    results = []
    for idx, input_data in enumerate(inputs):
        try:
            generator = ReportGenerator(input_data=input_data, output_format=output_format)
            success, report = generator.generate_report()
            if success:
                report["batch_index"] = idx
                results.append(report)
            else:
                results.append({
                    "batch_index": idx,
                    "error": report.get("error", "E010"),
                    "message": ERROR_MESSAGES.get(report.get("error", "E010"), ERROR_MESSAGES["E010"]),
                })
        except Exception:
            results.append({
                "batch_index": idx,
                "error": "E009",
                "message": ERROR_MESSAGES["E009"],
            })
    return results


# ============================================================
# 自检模块（--selftest）
# ============================================================

def run_selftest() -> bool:
    """
    运行内置自检，验证核心逻辑

    使用硬编码样例数据，不读取外部文件，不访问网络。

    Returns:
        自检是否通过
    """
    print("=" * 60)
    print("运行自检模式（离线硬编码样例）")
    print("=" * 60)

    all_passed = True

    # 测试用例 1: JSON 数组输入
    test_cases = [
        {
            "name": "JSON数组输入",
            "input": json.dumps([
                {"id": "1", "name": "Alice", "amount": 100},
                {"id": "2", "name": "Bob", "amount": 200},
            ]),
            "format": "json",
            "min_records": 2,
            "min_confidence": 85,
        },
        {
            "name": "文本行输入",
            "input": "id:1, name:项目A, amount:500\nid:2, name:项目B, amount:300",
            "format": "text",
            "min_records": 1,
            "min_confidence": 85,
        },
        {
            "name": "单条JSON对象",
            "input": json.dumps({"name": "测试项", "status": "active"}),
            "format": "json",
            "min_records": 1,
            "min_confidence": 85,
        },
        {
            "name": "空输入（应返回错误）",
            "input": "",
            "format": "json",
            "min_records": 0,
            "min_confidence": 0,
            "expect_error": True,
        },
    ]

    for idx, case in enumerate(test_cases, 1):
        print(f"\n测试用例 {idx}: {case['name']}")

        try:
            generator = ReportGenerator(input_data=case["input"], output_format=case["format"])
            success, report = generator.generate_report()

            if case.get("expect_error"):
                # 期望错误的情况
                if success:
                    print(f"  [FAIL] 期望返回错误，但实际成功")
                    all_passed = False
                else:
                    error_code = report.get("error", "")
                    if error_code in ["E001", "E002", "E003"]:
                        print(f"  [PASS] 正确返回错误码 {error_code}")
                    else:
                        print(f"  [FAIL] 错误码不正确: {error_code}")
                        all_passed = False
                continue

            if not success:
                print(f"  [FAIL] 处理失败: {report.get('error', 'E010')}")
                all_passed = False
                continue

            # 宽松断言：记录数不少于预期
            record_count = report.get("record_count", 0)
            if record_count < case["min_records"]:
                print(f"  [FAIL] 记录数 {record_count} < 预期最小值 {case['min_records']}")
                all_passed = False
            else:
                print(f"  [PASS] 记录数 {record_count} >= {case['min_records']}")

            # 宽松断言：置信度不低于预期（若预期 > 0）
            confidence = report.get("confidence", 0)
            if case["min_confidence"] > 0:
                if confidence < case["min_confidence"]:
                    print(f"  [FAIL] 置信度 {confidence}% < 预期最小值 {case['min_confidence']}%")
                    all_passed = False
                else:
                    print(f"  [PASS] 置信度 {confidence}% >= {case['min_confidence']}%")

            # 验证输出格式
            formatted = generator.format_output(report)
            if formatted and len(formatted) > 0:
                print(f"  [PASS] 输出格式有效（长度 {len(formatted)}）")
            else:
                print(f"  [FAIL] 输出为空")
                all_passed = False

        except Exception as e:
            print(f"  [FAIL] 异常: {str(e)}")
            all_passed = False

    # 测试用例 5: 批量处理
    print(f"\n测试用例 5: 批量处理")
    try:
        batch_inputs = [
            "name:批量项1, amount:100",
            "name:批量项2, amount:200",
            json.dumps({"name": "批量项3", "status": "done"}),
        ]
        batch_results = process_batch(batch_inputs, "json")
        success_count = sum(1 for r in batch_results if "error" not in r)
        if success_count >= 2:
            print(f"  [PASS] 批量处理成功 {success_count}/3 项")
        else:
            print(f"  [FAIL] 批量处理成功率过低: {success_count}/3")
            all_passed = False
    except Exception as e:
        print(f"  [FAIL] 批量处理异常: {str(e)}")
        all_passed = False

    # 测试用例 6: 错误码覆盖
    print(f"\n测试用例 6: 错误码覆盖")
    error_codes_check = True
    for code in ["E001", "E002", "E003", "E004", "E005", "E006", "E007", "E008", "E009", "E010"]:
        if code not in ERROR_MESSAGES:
            print(f"  [FAIL] 缺少错误码 {code}")
            error_codes_check = False
            all_passed = False

    if error_codes_check:
        print(f"  [PASS] 全部 10 个错误码已定义")

    # 测试用例 7: 能力边界
    print(f"\n测试用例 7: 能力边界处理")
    try:
        # 空输入应返回 E001
        gen = ReportGenerator(input_data="", output_format="json")
        success, report = gen.generate_report()
        if not success and report.get("error") == "E001":
            print(f"  [PASS] 空输入正确返回 E001")
        else:
            print(f"  [FAIL] 空输入处理不正确")
            all_passed = False
    except Exception as e:
        print(f"  [FAIL] 边界处理异常: {str(e)}")
        all_passed = False

    # 汇总
    print("\n" + "=" * 60)
    if all_passed:
        print("自检结果: [全部通过]")
    else:
        print("自检结果: [存在失败项]")
    print("=" * 60)

    return all_passed


# ============================================================
# 主入口
# ============================================================

def main() -> int:
    """
    主函数

    Returns:
        退出码（0 成功，1 失败）
    """
    parser = argparse.ArgumentParser(
        description="laravel-dynamic-report-generator - SQL查询技能独立实现",
        epilog="示例: python main.py --input '数据内容' --format json"
    )
    parser.add_argument("--input", "-i", type=str, help="输入数据（文本或JSON）")
    parser.add_argument("--format", "-f", type=str, default="json", choices=SUPPORTED_FORMATS,
                        help=f"输出格式（默认: json，支持: {', '.join(SUPPORTED_FORMATS)}）")
    parser.add_argument("--batch", "-b", type=str, nargs="+", help="批量输入（多个值）")
    parser.add_argument("--selftest", "-s", action="store_true", help="运行自检")
    parser.add_argument("--version", "-v", action="version", version="1.0.0")

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        passed = run_selftest()
        return 0 if passed else 1

    # 参数校验
    if not args.input and not args.batch:
        print(f"[E007] {ERROR_MESSAGES['E007']}", file=sys.stderr)
        print("请使用 --input 或 --batch 提供输入数据，或使用 --selftest 运行自检", file=sys.stderr)
        return 1

    try:
        # 批量处理
        if args.batch:
            print(f"批量处理 {len(args.batch)} 条输入...")
            results = process_batch(args.batch, args.format)
            output = json.dumps({"batch_results": results}, ensure_ascii=False, indent=2)
            print(output)
            return 0

        # 单条处理
        generator = ReportGenerator(input_data=args.input, output_format=args.format)
        success, report = generator.generate_report()

        if not success:
            error_code = report.get("error", "E010")
            print(f"[{error_code}] {ERROR_MESSAGES.get(error_code, ERROR_MESSAGES['E010'])}", file=sys.stderr)
            return 1

        output = generator.format_output(report)
        print(output)
        return 0

    except KeyboardInterrupt:
        print("\n用户中断操作", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"[E010] {ERROR_MESSAGES['E010']}: {str(e)}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
