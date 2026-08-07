#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
发票识别 (ocr-invoice) - 控制台应用程序

功能：扫描用户的账单和收据，提取关键信息并结构化输出。
本脚本为 clean-room 独立实现，仅依据功能规格编写。

运行方式：
    python main.py --selftest    # 离线自检
    python main.py --help        # 显示帮助
"""

import sys
import json
import argparse
import re
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Any, Optional


# ============================================================
# 错误码定义（E001-E010）
# ============================================================
ERROR_CODES = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：...",
    "E003": "输入格式不符合要求，示例：...",
    "E004": "这超出了本工具的能力范围，建议...",
    "E005": "结果无法确定，建议：...",
    "E006": "输入内容无法解析为有效文本",
    "E007": "未识别到任何发票字段",
    "E008": "批量处理时输入列表为空",
    "E009": "输出格式不支持，仅支持 json/text",
    "E010": "内部处理异常，请稍后重试",
}


# ============================================================
# 数据模型
# ============================================================
@dataclass
class InvoiceField:
    """发票字段"""
    name: str          # 字段名
    value: str         # 字段值
    confidence: float  # 置信度 0-100
    source: str        # 来源（如：raw_text, regex, manual）
    note: str = ""     # 备注（如：需核实）


@dataclass
class InvoiceResult:
    """识别结果"""
    fields: List[InvoiceField] = field(default_factory=list)
    overall_confidence: float = 0.0
    warnings: List[str] = field(default_factory=list)
    raw_text: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "fields": [asdict(f) for f in self.fields],
            "overall_confidence": self.overall_confidence,
            "warnings": self.warnings,
            "raw_text": self.raw_text[:200] if self.raw_text else "",  # 截断
        }


# ============================================================
# 核心解析引擎
# ============================================================
class InvoiceParser:
    """
    发票解析器 - 从文本中提取发票关键字段。
    纯规则实现，不依赖外部服务。
    """

    # 常见发票字段的正则模式（增强版）
    PATTERNS = {
        "invoice_number": [
            r"发票号码\s*[:：]?\s*([A-Za-z0-9\-]+)",
            r"发票号\s*[:：]?\s*([A-Za-z0-9\-]+)",
            r"No\.?\s*[:：]?\s*([A-Za-z0-9\-]+)",
            r"NO\.?\s*[:：]?\s*([A-Za-z0-9\-]+)"
        ],
        "invoice_date": [
            r"开票日期\s*[:：]?\s*(\d{4}[-/]\d{1,2}[-/]\d{1,2})",
            r"日期\s*[:：]?\s*(\d{4}[-/]\d{1,2}[-/]\d{1,2})",
            r"Date\s*[:：]?\s*(\d{4}[-/]\d{1,2}[-/]\d{1,2})"
        ],
        "total_amount": [
            r"价税合计\s*[:：]?\s*[¥￥]?\s*([\d,]+\.?\d*)",
            r"合计金额\s*[:：]?\s*[¥￥]?\s*([\d,]+\.?\d*)",
            r"总金额\s*[:：]?\s*[¥￥]?\s*([\d,]+\.?\d*)",
            r"Amount\s*[:：]?\s*[¥￥]?\s*([\d,]+\.?\d*)",
            r"金额\s*[:：]?\s*[¥￥]?\s*([\d,]+\.?\d*)"
        ],
        "seller_name": [
            r"销售方[名称]?\s*[:：]?\s*([^\s,，;；]+)",
            r"销方[名称]?\s*[:：]?\s*([^\s,，;；]+)",
            r"卖方[名称]?\s*[:：]?\s*([^\s,，;；]+)",
            r"Seller\s*[:：]?\s*([^\s,，;；]+)"
        ],
        "buyer_name": [
            r"购买方[名称]?\s*[:：]?\s*([^\s,，;；]+)",
            r"购方[名称]?\s*[:：]?\s*([^\s,，;；]+)",
            r"买方[名称]?\s*[:：]?\s*([^\s,，;；]+)",
            r"Buyer\s*[:：]?\s*([^\s,，;；]+)"
        ],
    }

    def __init__(self):
        self.field_values: Dict[str, str] = {}
        self.confidences: Dict[str, float] = {}

    def parse(self, text: str) -> InvoiceResult:
        """解析文本，返回结构化结果"""
        if not text or not text.strip():
            raise ValueError("E001")

        result = InvoiceResult(raw_text=text.strip())
        
        # 重置状态
        self.field_values = {}
        self.confidences = {}
        
        # 逐行扫描提取字段
        for line in text.strip().splitlines():
            self._extract_from_line(line.strip())

        # 构建结果
        for name, value in self.field_values.items():
            conf = self.confidences.get(name, 60.0)
            note = ""
            if conf < 85:
                note = "[需核实]"
            elif conf < 90:
                note = "建议复核"

            result.fields.append(InvoiceField(
                name=name,
                value=value,
                confidence=conf,
                source="rule_based",
                note=note,
            ))

        if not result.fields:
            raise ValueError("E007")

        # 计算整体置信度（取平均值，宽松处理）
        result.overall_confidence = sum(f.confidence for f in result.fields) / len(result.fields)

        # 添加警告
        for f in result.fields:
            if f.confidence < 85:
                result.warnings.append(f"字段 '{f.name}' 置信度较低 ({f.confidence:.0f}%)")

        return result

    def _extract_from_line(self, line: str) -> None:
        """从单行文本提取字段"""
        if not line:
            return

        # 尝试匹配各字段的正则模式
        for field_name, patterns in self.PATTERNS.items():
            if field_name in self.field_values:
                continue  # 已提取过

            for pattern in patterns:
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    value = match.group(1).strip()
                    if value and len(value) < 100:  # 合理长度
                        self.field_values[field_name] = value
                        
                        # 置信度估计：
                        # 有明确关键字 + 有值 = 80-95
                        conf = 85.0
                        if len(pattern) > 20:  # 更完整的模式
                            conf += 5.0
                        if any(c.isdigit() for c in value):
                            conf += 5.0
                        self.confidences[field_name] = min(95.0, conf)
                        break

        # 额外尝试提取金额（数字+货币符号，但没有明确标签）
        if "total_amount" not in self.field_values:
            money_match = re.search(r"[¥￥]\s*([\d,]+\.?\d*)\s*元", line)
            if money_match:
                value = money_match.group(1)
                if value:
                    self.field_values["total_amount"] = value
                    self.confidences["total_amount"] = 75.0  # 置信度稍低，因为没有明确标签

        # 额外尝试提取日期（没有明确标签但符合日期格式）
        if "invoice_date" not in self.field_values:
            date_match = re.search(r"(\d{4}[-/]\d{1,2}[-/]\d{1,2})", line)
            if date_match:
                value = date_match.group(1)
                if value:
                    self.field_values["invoice_date"] = value
                    self.confidences["invoice_date"] = 70.0  # 置信度较低，因为没有明确标签


# ============================================================
# 批量处理
# ============================================================
class BatchProcessor:
    """批量处理多个输入"""

    def __init__(self, parser: InvoiceParser):
        self.parser = parser

    def process(self, inputs: List[str]) -> List[Dict[str, Any]]:
        """批量处理，返回结果列表"""
        if not inputs:
            raise ValueError("E008")

        results = []
        for text in inputs:
            try:
                result = self.parser.parse(text)
                results.append(result.to_dict())
            except ValueError as e:
                # 单个失败不中断批量
                results.append({
                    "error": str(e),
                    "raw_text": text[:100],
                })
        return results


# ============================================================
# 输出格式化
# ============================================================
class OutputFormatter:
    """输出格式化器"""

    @staticmethod
    def format(result: InvoiceResult, fmt: str = "json") -> str:
        """格式化输出"""
        if fmt == "json":
            return json.dumps(result.to_dict(), ensure_ascii=False, indent=2)
        elif fmt == "text":
            lines = []
            for f in result.fields:
                note = f" ({f.note})" if f.note else ""
                lines.append(f"{f.name}: {f.value} (置信度: {f.confidence:.0f}%){note}")
            if result.warnings:
                lines.append("\n[警告]")
                lines.extend(f"  - {w}" for w in result.warnings)
            return "\n".join(lines)
        else:
            raise ValueError("E009")


# ============================================================
# 自检模块（内置硬编码样例数据）
# ============================================================
class SelfTest:
    """内置自检，不依赖外部文件/网络/当前目录"""

    SAMPLE_INVOICE = """发票号码: 12345678
开票日期: 2025-01-15
销售方: 某某科技有限公司
购买方: 某某贸易有限公司
价税合计: ¥1,234.56
备注: 增值税普通发票"""

    SAMPLE_BASIC = """No. 98765
Date: 2025-03-20
Amount: 500.00
Seller: ABC Company"""

    @staticmethod
    def run() -> bool:
        """执行自检，返回是否通过"""
        print("=" * 50)
        print("自检开始 (ocr-invoice)")
        print("=" * 50)

        parser = InvoiceParser()
        formatter = OutputFormatter()

        # 测试样例1：完整发票
        print("\n[测试1] 完整发票样例")
        try:
            result1 = parser.parse(SelfTest.SAMPLE_INVOICE)
            assert len(result1.fields) >= 4, f"字段数应≥4，实际{len(result1.fields)}"
            assert result1.overall_confidence > 50, f"置信度应>50，实际{result1.overall_confidence}"

            # 检查关键字段存在
            field_names = [f.name for f in result1.fields]
            assert "invoice_number" in field_names, "缺少发票号码"
            assert "invoice_date" in field_names, "缺少开票日期"
            assert "total_amount" in field_names, "缺少金额"

            print(f"  ✓ 通过 (字段数: {len(result1.fields)}, 置信度: {result1.overall_confidence:.0f}%)")
        except Exception as e:
            print(f"  ✗ 失败: {e}")
            return False

        # 测试样例2：简化发票
        print("\n[测试2] 简化发票样例")
        try:
            result2 = parser.parse(SelfTest.SAMPLE_BASIC)
            assert len(result2.fields) >= 3, f"字段数应≥3，实际{len(result2.fields)}"
            assert result2.overall_confidence > 50, f"置信度应>50，实际{result2.overall_confidence}"
            print(f"  ✓ 通过 (字段数: {len(result2.fields)}, 置信度: {result2.overall_confidence:.0f}%)")
        except Exception as e:
            print(f"  ✗ 失败: {e}")
            return False

        # 测试3：输出格式化
        print("\n[测试3] 输出格式化")
        try:
            result = parser.parse(SelfTest.SAMPLE_INVOICE)
            json_out = formatter.format(result, "json")
            assert json_out, "JSON输出为空"
            # 验证JSON可解析
            parsed = json.loads(json_out)
            assert "fields" in parsed, "JSON缺少fields"
            assert "overall_confidence" in parsed, "JSON缺少overall_confidence"

            text_out = formatter.format(result, "text")
            assert text_out, "文本输出为空"
            assert "发票号码" in text_out or "invoice_number" in text_out, "文本输出缺少字段名"

            print("  ✓ 通过")
        except Exception as e:
            print(f"  ✗ 失败: {e}")
            return False

        # 测试4：错误处理
        print("\n[测试4] 错误处理")
        try:
            # 空输入
            try:
                parser.parse("")
                print("  ✗ 失败: 空输入应报错")
                return False
            except ValueError as e:
                assert "E001" in str(e), f"错误码应为E001，实际{str(e)}"

            # 无字段输入（确保不会误识别）
            no_field_texts = [
                "这是一段没有发票信息的普通文本，没有任何关键字。",
                "今天的天气很好，适合出去散步。",
                "hello world, this is a test message without any invoice data.",
            ]
            for no_field_text in no_field_texts:
                try:
                    parser.parse(no_field_text)
                    print(f"  ✗ 失败: 无字段应报错，但成功解析了: '{no_field_text[:30]}...'")
                    return False
                except ValueError as e:
                    assert "E007" in str(e), f"错误码应为E007，实际{str(e)}"

            print("  ✓ 通过")
        except Exception as e:
            print(f"  ✗ 失败: {e}")
            return False

        # 测试5：批量处理
        print("\n[测试5] 批量处理")
        try:
            processor = BatchProcessor(parser)
            results = processor.process([SelfTest.SAMPLE_INVOICE, SelfTest.SAMPLE_BASIC])
            assert len(results) == 2, f"批量结果数应=2，实际{len(results)}"
            assert all("fields" in r for r in results), "批量结果缺少fields"

            # 空列表
            try:
                processor.process([])
                print("  ✗ 失败: 空列表应报错")
                return False
            except ValueError as e:
                assert "E008" in str(e), f"错误码应为E008，实际{str(e)}"

            print("  ✓ 通过")
        except Exception as e:
            print(f"  ✗ 失败: {e}")
            return False

        print("\n" + "=" * 50)
        print("自检全部通过 ✓")
        print("=" * 50)
        return True


# ============================================================
# 主程序入口
# ============================================================
def main() -> int:
    """主入口"""
    parser = argparse.ArgumentParser(
        description="发票识别 (ocr-invoice) - 从文本中提取发票关键信息",
        epilog="示例: python main.py --text '发票号码: 12345'"
    )

    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检（无需外部依赖）"
    )
    parser.add_argument(
        "--text",
        type=str,
        help="待识别的发票文本（直接传入）"
    )
    parser.add_argument(
        "--format",
        type=str,
        choices=["json", "text"],
        default="json",
        help="输出格式 (默认: json)"
    )
    parser.add_argument(
        "--batch",
        type=str,
        help="批量处理，多个文本用 ';;' 分隔"
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        ok = SelfTest.run()
        return 0 if ok else 1

    # 正常处理模式
    try:
        if args.batch:
            # 批量处理
            texts = [t.strip() for t in args.batch.split(";;") if t.strip()]
            processor = BatchProcessor(InvoiceParser())
            results = processor.process(texts)
            print(json.dumps(results, ensure_ascii=False, indent=2))
        elif args.text:
            # 单条处理
            invoice_parser = InvoiceParser()
            result = invoice_parser.parse(args.text)
            formatter = OutputFormatter()
            print(formatter.format(result, args.format))
        else:
            # 无输入
            print(f"错误 [E001]: {ERROR_CODES['E001']}", file=sys.stderr)
            print("提示: 使用 --text 提供文本，或 --selftest 运行自检。", file=sys.stderr)
            return 1

        return 0

    except ValueError as e:
        error_msg = str(e)
        if error_msg in ERROR_CODES:
            print(f"错误 [{error_msg}]: {ERROR_CODES[error_msg]}", file=sys.stderr)
        else:
            print(f"错误: {error_msg}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"错误 [E010]: {ERROR_CODES['E010']} ({e})", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
