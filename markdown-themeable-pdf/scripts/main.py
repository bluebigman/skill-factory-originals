#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF转文档 - 主题化 Markdown 转换器（离线核心逻辑）
版本: 1.1.0
架构: 标准库独立实现，无第三方依赖
"""

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 错误码定义
# ============================================================
ERROR_CODES = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：...",
    "E003": "输入格式不符合要求，示例：...",
    "E004": "这超出了本工具的能力范围，建议...",
    "E005": "结果无法确定，建议：...",
    "E006": "内部处理异常，请重试",
    "E007": "输出格式不支持，支持：json/text",
    "E008": "批量处理中断，请检查输入",
    "E009": "置信度计算失败，使用默认值",
    "E010": "未知错误，请联系管理员",
}


# ============================================================
# 数据模型
# ============================================================
@dataclass
class ConversionResult:
    """转换结果数据类"""
    success: bool
    output: str = ""
    confidence: float = 0.0
    warnings: List[str] = field(default_factory=list)
    error_code: Optional[str] = None
    error_message: str = ""


@dataclass
class InputItem:
    """输入项数据类"""
    raw_text: str
    source_type: str = "text"  # text / url / file
    meta: Dict[str, Any] = field(default_factory=dict)


# ============================================================
# 核心处理引擎
# ============================================================
class MarkdownConverter:
    """主题化 Markdown 转换器核心引擎"""

    # 关键字段识别模式（宽松匹配）
    FIELD_PATTERNS = {
        "标题": r"(?:^|\n)#{1,3}\s+(.+)",
        "作者": r"(?:作者|author)\s*[:：]\s*(.+)",
        "日期": r"(?:日期|date)\s*[:：]\s*(\d{4}[-/]\d{1,2}[-/]\d{1,2})",
        "关键词": r"(?:关键词|keywords?)\s*[:：]\s*(.+)",
        "摘要": r"(?:摘要|abstract|summary)\s*[:：]\s*(.+)",
    }

    def __init__(self) -> None:
        """初始化引擎"""
        self._field_patterns = self.FIELD_PATTERNS.copy()

    def process(self, items: List[InputItem], output_format: str = "text") -> List[ConversionResult]:
        """
        处理输入项列表，返回结果列表

        参数:
            items: 输入项列表
            output_format: 输出格式 (text / json)

        返回:
            处理结果列表
        """
        if not items:
            return [self._make_error_result("E001")]

        results = []
        try:
            for item in items:
                result = self._process_single(item, output_format)
                results.append(result)
        except Exception as exc:  # 防御性异常捕获
            results.append(self._make_error_result("E010", str(exc)))

        return results

    def _process_single(self, item: InputItem, output_format: str) -> ConversionResult:
        """处理单个输入项"""
        try:
            # 校验输入
            if not item.raw_text or not item.raw_text.strip():
                return self._make_error_result("E001")

            # 解析关键字段
            fields = self._extract_fields(item.raw_text)

            # 计算置信度
            confidence = self._calculate_confidence(item.raw_text, fields)

            # 生成输出
            if output_format == "json":
                output = self._format_json_output(item, fields, confidence)
            elif output_format == "text":
                output = self._format_text_output(item, fields, confidence)
            else:
                return self._make_error_result("E007")

            # 构建结果
            warnings = []
            if confidence < 0.6:
                warnings.append("低置信度：部分字段可能不准确，请人工复核")
            elif confidence < 0.8:
                warnings.append("建议复核：请确认关键字段")

            return ConversionResult(
                success=True,
                output=output,
                confidence=confidence,
                warnings=warnings,
            )

        except Exception as exc:
            return self._make_error_result("E006", str(exc))

    def _extract_fields(self, text: str) -> Dict[str, str]:
        """从文本中提取关键字段（宽松匹配）"""
        fields = {}
        for field_name, pattern in self._field_patterns.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                value = match.group(1).strip()
                if value:
                    fields[field_name] = value
        return fields

    @staticmethod
    def _calculate_confidence(text: str, fields: Dict[str, str]) -> float:
        """计算置信度（基于字段覆盖率和文本长度）"""
        try:
            # 基础置信度：字段覆盖率
            total_patterns = len(MarkdownConverter.FIELD_PATTERNS)
            matched_patterns = len(fields)
            field_ratio = matched_patterns / total_patterns if total_patterns > 0 else 0.0

            # 文本长度因子（使用更温和的评分）
            text_len = len(text.strip())
            # 调整长度因子，使其对短文本更宽容
            length_factor = min(1.0, text_len / 50.0 + 0.3)  # 30字符即有0.9，100字符即满

            # 综合置信度：提高字段覆盖率权重，降低长度权重
            confidence = 0.7 * field_ratio + 0.3 * length_factor
            
            # 确保最低置信度，只要输入非空就有基本置信度
            if text.strip():
                confidence = max(confidence, 0.3)
            
            return round(max(0.1, min(1.0, confidence)), 2)

        except Exception:
            return 0.5  # 默认中等置信度

    @staticmethod
    def _format_text_output(item: InputItem, fields: Dict[str, str], confidence: float) -> str:
        """生成文本格式输出"""
        lines = ["=== 转换结果 ==="]
        lines.append(f"来源类型: {item.source_type}")
        lines.append(f"置信度: {confidence * 100:.1f}%")

        if fields:
            lines.append("--- 提取字段 ---")
            for key, value in fields.items():
                lines.append(f"{key}: {value}")
        else:
            lines.append("未提取到结构化字段")

        # 置信度标注
        if confidence < 0.6:
            lines.append("[需核实] 部分内容存在不确定性，请人工复核")
        elif confidence < 0.8:
            lines.append("建议复核：请确认关键字段")

        return "\n".join(lines)

    @staticmethod
    def _format_json_output(item: InputItem, fields: Dict[str, str], confidence: float) -> str:
        """生成 JSON 格式输出"""
        data = {
            "source_type": item.source_type,
            "confidence": confidence,
            "fields": fields,
            "needs_review": confidence < 0.8,
        }
        return json.dumps(data, ensure_ascii=False, indent=2)

    @staticmethod
    def _make_error_result(error_code: str, detail: str = "") -> ConversionResult:
        """构造错误结果"""
        message = ERROR_CODES.get(error_code, ERROR_CODES["E010"])
        if detail:
            message = f"{message} ({detail})"
        return ConversionResult(
            success=False,
            error_code=error_code,
            error_message=message,
        )


# ============================================================
# 批量处理支持
# ============================================================
def batch_process(inputs: List[str], output_format: str = "text") -> Tuple[List[ConversionResult], int]:
    """
    批量处理输入

    参数:
        inputs: 输入文本列表
        output_format: 输出格式

    返回:
        (结果列表, 成功数量)
    """
    converter = MarkdownConverter()
    items = [InputItem(raw_text=text, source_type="text") for text in inputs]
    results = converter.process(items, output_format)
    success_count = sum(1 for r in results if r.success)
    return results, success_count


# ============================================================
# 内置自检（硬编码样例，不依赖外部资源）
# ============================================================
def run_selftest() -> int:
    """运行内置自检，返回退出码（0成功，非0失败）"""
    print("=== 自检开始 ===")
    test_passed = True

    # 测试样例（硬编码，保证任何环境可运行）
    test_cases = [
        {
            "name": "正常输入-完整字段",
            "input": [
                "# 测试文档标题\n",
                "作者: 张三\n",
                "日期: 2026-01-15\n",
                "关键词: 测试, 转换, PDF\n",
                "摘要: 这是一个用于自检的测试文档。\n",
            ],
            "expect_success": True,
            "expect_min_confidence": 0.5,
        },
        {
            "name": "正常输入-部分字段",
            "input": [
                "## 简单标题\n",
                "没有其他结构化信息。\n",
            ],
            "expect_success": True,
            "expect_min_confidence": 0.2,
        },
        {
            "name": "空输入",
            "input": [""],
            "expect_success": False,
            "expect_error": "E001",
        },
        {
            "name": "批量输入",
            "input": [
                "# 第一个文档\n作者: 李四\n日期: 2026-02-01",
                "# 第二个文档\n作者: 王五\n日期: 2026-03-01",
            ],
            "expect_success": True,
            "expect_min_confidence": 0.3,
        },
    ]

    converter = MarkdownConverter()

    for case in test_cases:
        print(f"\n--- 测试: {case['name']} ---")
        case_passed = True
        try:
            items = [InputItem(raw_text=t, source_type="text") for t in case["input"]]
            results = converter.process(items, "text")

            # 检查结果数量
            if len(results) != len(case["input"]):
                print(f"  失败: 结果数量不匹配 (期望 {len(case['input'])}, 实际 {len(results)})")
                test_passed = False
                case_passed = False
                continue

            # 检查每个结果
            for i, result in enumerate(results):
                if case["expect_success"]:
                    if not result.success:
                        print(f"  失败: 第{i+1}项期望成功，实际失败: {result.error_message}")
                        test_passed = False
                        case_passed = False
                        continue
                    if result.confidence < case["expect_min_confidence"]:
                        print(f"  失败: 第{i+1}项置信度过低: {result.confidence}")
                        test_passed = False
                        case_passed = False
                else:
                    if result.success:
                        print(f"  失败: 第{i+1}项期望失败，实际成功")
                        test_passed = False
                        case_passed = False
                        continue
                    if case.get("expect_error") and result.error_code != case["expect_error"]:
                        print(f"  失败: 第{i+1}项错误码不匹配 (期望 {case['expect_error']}, 实际 {result.error_code})")
                        test_passed = False
                        case_passed = False

            if case_passed:
                print("  通过")
        except Exception as exc:
            print(f"  失败: 测试执行异常: {exc}")
            test_passed = False

    # 测试 JSON 输出
    print("\n--- 测试: JSON输出格式 ---")
    try:
        items = [InputItem(raw_text="# 标题\n作者: 测试", source_type="text")]
        results = converter.process(items, "json")
        if results[0].success:
            json_data = json.loads(results[0].output)
            if "confidence" in json_data and "fields" in json_data:
                print("  通过")
            else:
                print("  失败: JSON 缺少必要字段")
                test_passed = False
        else:
            print(f"  失败: JSON 转换失败: {results[0].error_message}")
            test_passed = False
    except Exception as exc:
        print(f"  失败: JSON 测试异常: {exc}")
        test_passed = False

    # 测试批量处理
    print("\n--- 测试: 批量处理函数 ---")
    try:
        inputs = ["# 文档1", "# 文档2\n作者: 某人"]
        results, success_count = batch_process(inputs, "text")
        if success_count >= 1:
            print(f"  通过 (成功 {success_count}/{len(inputs)})")
        else:
            print("  失败: 批量处理全部失败")
            test_passed = False
    except Exception as exc:
        print(f"  失败: 批量处理异常: {exc}")
        test_passed = False

    # 测试错误码体系
    print("\n--- 测试: 错误码体系 ---")
    try:
        if len(ERROR_CODES) >= 10:  # E001-E010
            print("  通过")
        else:
            print("  失败: 错误码数量不足")
            test_passed = False
    except Exception as exc:
        print(f"  失败: 错误码测试异常: {exc}")
        test_passed = False

    print("\n=== 自检结束 ===")
    if test_passed:
        print("全部测试通过")
        return 0
    else:
        print("存在失败测试")
        return 1


# ============================================================
# 命令行入口
# ============================================================
def main() -> int:
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description="PDF转文档 - 主题化 Markdown 转换器",
        epilog="示例: python main.py --input '文本内容' --format text",
    )
    parser.add_argument(
        "--input", "-i",
        type=str,
        help="输入文本（支持多行，用引号包裹）",
    )
    parser.add_argument(
        "--format", "-f",
        type=str,
        choices=["text", "json"],
        default="text",
        help="输出格式 (默认: text)",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检",
    )
    parser.add_argument(
        "--batch",
        action="store_true",
        help="批量模式（输入按行分割）",
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        return run_selftest()

    # 正常处理模式
    if not args.input:
        print(f"错误 [E001]: {ERROR_CODES['E001']}", file=sys.stderr)
        return 1

    try:
        if args.batch:
            # 批量模式：按行分割
            inputs = [line.strip() for line in args.input.split("\n") if line.strip()]
            results, success_count = batch_process(inputs, args.format)
            print(f"处理完成: 成功 {success_count}/{len(inputs)}")
            for i, result in enumerate(results):
                print(f"\n--- 结果 {i+1} ---")
                if result.success:
                    print(result.output)
                else:
                    print(f"错误 [{result.error_code}]: {result.error_message}", file=sys.stderr)
        else:
            # 单条模式
            converter = MarkdownConverter()
            item = InputItem(raw_text=args.input, source_type="text")
            result = converter.process([item], args.format)[0]

            if result.success:
                print(result.output)
                if result.warnings:
                    for warning in result.warnings:
                        print(f"警告: {warning}", file=sys.stderr)
            else:
                print(f"错误 [{result.error_code}]: {result.error_message}", file=sys.stderr)
                return 1

        return 0

    except KeyboardInterrupt:
        print("\n用户中断", file=sys.stderr)
        return 130
    except Exception as exc:
        print(f"错误 [E010]: {ERROR_CODES['E010']} - {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
