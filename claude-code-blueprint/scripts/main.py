#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
claude-code-blueprint 独立实现
基于功能规格的 clean-room 重写，不依赖任何既有代码。
"""

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
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
    "E007": "批量处理中某个条目失败，已跳过",
    "E008": "输出格式指定无效，支持：json/text",
    "E009": "置信度计算失败，使用默认值",
    "E010": "未知错误，请联系维护者",
}


# ============================================================
# 数据模型
# ============================================================
@dataclass
class ProcessedItem:
    """单个输入的处理结果"""
    raw: str
    structured: Dict[str, Any]
    confidence: float
    needs_review: bool
    uncertain_points: List[str] = field(default_factory=list)


@dataclass
class ProcessingResult:
    """整体处理结果"""
    items: List[ProcessedItem]
    success_count: int
    fail_count: int
    warnings: List[str] = field(default_factory=list)


# ============================================================
# 核心处理引擎
# ============================================================
class BlueprintEngine:
    """蓝图中定义的核心处理引擎"""

    # 关键字段正则模式（用于识别输入中的关键信息）
    FIELD_PATTERNS = {
        "email": r"[\w.+-]+@[\w-]+\.[\w.]+",
        "url": r"https?://[^\s]+",
        "phone": r"\+?\d[\d\s-]{7,}\d",
        "date": r"\d{4}[-/]\d{1,2}[-/]\d{1,2}",
        "amount": r"(?:￥|¥|RMB|CNY)\s?\d+(?:\.\d{1,2})?",
    }

    # 可识别的关键字段标签
    KEY_FIELDS = ["email", "url", "phone", "date", "amount"]

    def __init__(self) -> None:
        """初始化引擎"""
        # 置信度阈值
        self.high_threshold = 0.90
        self.mid_threshold = 0.85

    def process(self, inputs: List[str], output_format: str = "json") -> ProcessingResult:
        """
        核心处理流程：
        1. 解析输入内容，识别关键信息
        2. 按规则结构化处理
        3. 生成结果并标注置信度
        """
        if not inputs:
            raise ValueError("E001")

        if output_format not in ("json", "text"):
            raise ValueError("E008")

        items = []
        success = 0
        fail = 0
        warnings = []

        for raw_input in inputs:
            try:
                item = self._process_single(raw_input)
                items.append(item)
                success += 1
            except Exception as exc:
                fail += 1
                warnings.append(f"E007: {raw_input[:30]}... 处理失败: {str(exc)}")
                # 失败条目也记录，但标记为低置信度
                items.append(ProcessedItem(
                    raw=raw_input,
                    structured={},
                    confidence=0.0,
                    needs_review=True,
                    uncertain_points=[str(exc)],
                ))

        return ProcessingResult(
            items=items,
            success_count=success,
            fail_count=fail,
            warnings=warnings,
        )

    def _process_single(self, raw: str) -> ProcessedItem:
        """处理单个输入"""
        if not raw or not raw.strip():
            raise ValueError("E001")

        # 识别关键字段
        extracted = self._extract_fields(raw)

        # 计算置信度
        confidence, uncertain = self._calc_confidence(raw, extracted)

        # 判断是否需要复核
        needs_review = confidence < self.mid_threshold

        return ProcessedItem(
            raw=raw,
            structured=extracted,
            confidence=confidence,
            needs_review=needs_review,
            uncertain_points=uncertain,
        )

    def _extract_fields(self, text: str) -> Dict[str, Any]:
        """从输入文本中提取关键字段（规格 Step 2 核心逻辑）"""
        result = {}
        for field_name in self.KEY_FIELDS:
            pattern = self.FIELD_PATTERNS.get(field_name)
            if not pattern:
                continue
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                # 去重并保留顺序
                unique = list(dict.fromkeys(matches))
                result[field_name] = unique[0] if len(unique) == 1 else unique
        return result

    def _calc_confidence(self, raw: str, extracted: Dict[str, Any]) -> Tuple[float, List[str]]:
        """
        计算置信度（规则简化版）：
        - 基础分 0.5
        - 每个识别到的字段 +0.1
        - 输入长度适中（10-1000字符）+0.2
        - 输入包含明显噪声（如乱码）-0.2
        """
        uncertain = []
        score = 0.5

        # 字段识别加分
        field_bonus = min(len(extracted) * 0.1, 0.3)  # 最多加 0.3
        score += field_bonus

        # 长度适中加分
        length = len(raw)
        if 10 <= length <= 1000:
            score += 0.2
        else:
            uncertain.append("输入长度异常，可能不完整或包含冗余信息")

        # 噪声检测（简单规则：连续 3 个以上非 ASCII 可见字符）
        noise_pattern = r"[\x00-\x08\x0b\x0c\x0e-\x1f]{3,}"
        if re.search(noise_pattern, raw):
            score -= 0.2
            uncertain.append("检测到可疑控制字符")

        # 无关键字段时降低置信度
        if not extracted:
            score -= 0.1
            uncertain.append("未识别到明确的关键字段")

        # 限制在 0-1 范围
        confidence = max(0.0, min(1.0, score))
        return confidence, uncertain


# ============================================================
# 输出格式化
# ============================================================
class OutputFormatter:
    """输出格式化器"""

    @staticmethod
    def format_result(result: ProcessingResult, output_format: str) -> str:
        """将处理结果格式化为指定格式"""
        if output_format == "json":
            return OutputFormatter._to_json(result)
        elif output_format == "text":
            return OutputFormatter._to_text(result)
        else:
            raise ValueError("E008")

    @staticmethod
    def _to_json(result: ProcessingResult) -> str:
        """JSON 格式化"""
        payload = {
            "summary": {
                "total": len(result.items),
                "success": result.success_count,
                "fail": result.fail_count,
                "warnings": result.warnings,
            },
            "items": [
                {
                    "raw": item.raw,
                    "structured": item.structured,
                    "confidence": round(item.confidence, 3),
                    "needs_review": item.needs_review,
                    "uncertain_points": item.uncertain_points,
                }
                for item in result.items
            ],
        }
        return json.dumps(payload, ensure_ascii=False, indent=2)

    @staticmethod
    def _to_text(result: ProcessingResult) -> str:
        """文本格式化"""
        lines = []
        lines.append(f"处理完成：共 {len(result.items)} 条，成功 {result.success_count}，失败 {result.fail_count}")

        for idx, item in enumerate(result.items, 1):
            lines.append(f"\n--- 条目 {idx} ---")
            lines.append(f"输入: {item.raw[:50]}{'...' if len(item.raw) > 50 else ''}")
            if item.structured:
                for key, value in item.structured.items():
                    lines.append(f"  {key}: {value}")
            else:
                lines.append("  未识别到关键字段")
            lines.append(f"置信度: {item.confidence:.1%}")
            if item.needs_review:
                lines.append("[需核实]")
            if item.uncertain_points:
                lines.append(f"不确定点: {'; '.join(item.uncertain_points)}")

        if result.warnings:
            lines.append("\n警告:")
            for warn in result.warnings:
                lines.append(f"  - {warn}")

        return "\n".join(lines)


# ============================================================
# 自检模块（--selftest）
# ============================================================
class SelfTest:
    """内置硬编码样例数据的离线自检"""

    @staticmethod
    def run() -> bool:
        """运行自检，返回是否通过"""
        print("[自检] 开始...")

        # 硬编码测试数据（不读外部文件、不依赖目录、不访问网络）
        test_cases = [
            # (输入, 期望至少含有的字段, 期望最小置信度)
            (
                "请联系 support@example.com 或访问 https://example.com/docs 获取帮助，电话 138-1234-5678",
                ["email", "url", "phone"],
                0.7,
            ),
            (
                "订单金额 ￥1299.50，发货日期 2026-03-15",
                ["amount", "date"],
                0.7,
            ),
            (
                "这是一段普通文本，没有明显结构化信息",
                [],  # 不要求特定字段
                0.4,  # 置信度较低但不应为 0
            ),
            (
                "多个邮箱：a@test.com, b@test.com, c@test.com",
                ["email"],
                0.7,
            ),
        ]

        engine = BlueprintEngine()
        all_passed = True

        for idx, (raw_input, expected_fields, min_conf) in enumerate(test_cases, 1):
            try:
                item = engine._process_single(raw_input)
                print(f"\n[自检] 用例 {idx}: {raw_input[:40]}...")

                # 检查字段
                for field_name in expected_fields:
                    if field_name not in item.structured:
                        print(f"  [失败] 缺少字段: {field_name}")
                        all_passed = False
                    else:
                        print(f"  [通过] 字段 {field_name} = {item.structured[field_name]}")

                # 检查置信度（宽松阈值）
                if item.confidence < min_conf:
                    print(f"  [失败] 置信度 {item.confidence:.2f} < 最小要求 {min_conf}")
                    all_passed = False
                else:
                    print(f"  [通过] 置信度 {item.confidence:.2f} >= {min_conf}")

            except Exception as exc:
                print(f"  [失败] 处理异常: {exc}")
                all_passed = False

        # 测试批量处理
        print("\n[自检] 批量处理测试...")
        try:
            batch_inputs = [tc[0] for tc in test_cases]
            result = engine.process(batch_inputs, output_format="json")
            if result.success_count >= 3:  # 宽松阈值：至少 3 条成功
                print(f"  [通过] 批量处理成功 {result.success_count}/{len(batch_inputs)}")
            else:
                print(f"  [失败] 批量处理成功率过低: {result.success_count}/{len(batch_inputs)}")
                all_passed = False

            # 验证 JSON 输出可解析
            json_str = OutputFormatter.format_result(result, "json")
            parsed = json.loads(json_str)
            if "summary" in parsed and "items" in parsed:
                print("  [通过] JSON 输出结构完整")
            else:
                print("  [失败] JSON 输出缺少关键结构")
                all_passed = False

        except Exception as exc:
            print(f"  [失败] 批量处理异常: {exc}")
            all_passed = False

        # 测试错误处理
        print("\n[自检] 错误处理测试...")
        try:
            engine.process([])
            print("  [失败] 空输入未抛出 E001")
            all_passed = False
        except ValueError as exc:
            if str(exc) == "E001":
                print("  [通过] 空输入正确抛出 E001")
            else:
                print(f"  [失败] 错误码不匹配: {exc}")
                all_passed = False

        # 测试文本输出
        print("\n[自检] 文本输出测试...")
        try:
            text_out = OutputFormatter.format_result(result, "text")
            if "处理完成" in text_out:
                print("  [通过] 文本输出格式正确")
            else:
                print("  [失败] 文本输出缺少摘要")
                all_passed = False
        except Exception as exc:
            print(f"  [失败] 文本输出异常: {exc}")
            all_passed = False

        print(f"\n[自检] {'全部通过' if all_passed else '存在失败项'}")
        return all_passed


# ============================================================
# 命令行入口
# ============================================================
def main() -> int:
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description="claude-code-blueprint - 通用数据处理工具",
        epilog="示例: python main.py --input '联系 support@example.com' --output json",
    )
    parser.add_argument(
        "--input",
        action="append",
        help="待处理的输入内容（可多次指定，用于批量处理）",
    )
    parser.add_argument(
        "--output",
        choices=["json", "text"],
        default="json",
        help="输出格式（默认: json）",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检（不依赖外部文件/网络）",
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        ok = SelfTest.run()
        return 0 if ok else 1

    # 正常处理模式
    if not args.input:
        print(f"E001: {ERROR_CODES['E001']}", file=sys.stderr)
        return 1

    try:
        engine = BlueprintEngine()
        result = engine.process(args.input, output_format=args.output)
        output = OutputFormatter.format_result(result, args.output)
        print(output)

        # 输出警告到 stderr
        if result.warnings:
            for warn in result.warnings:
                print(f"警告: {warn}", file=sys.stderr)

        return 0

    except ValueError as exc:
        # 错误码处理
        code = str(exc)
        if code in ERROR_CODES:
            print(f"{code}: {ERROR_CODES[code]}", file=sys.stderr)
        else:
            print(f"E006: {ERROR_CODES['E006']}: {exc}", file=sys.stderr)
        return 1

    except Exception as exc:
        print(f"E010: {ERROR_CODES['E010']}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
