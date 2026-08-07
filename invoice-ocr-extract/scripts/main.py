#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
invoice-ocr-extract 技能独立实现脚本
=====================================
根据功能规格从零实现，不复制任何既有代码（clean-room）。

功能：
- 解析模拟 OCR 的输入数据（图片/PDF 的模拟结果）
- 抽取发票关键字段，输出结构化表格
- 支持批量处理与置信度标注
- 提供 --selftest 离线自检

用法示例：
    python scripts/main.py --input sample.json --format json
    python scripts/main.py --selftest
"""

import argparse
import json
import sys
from typing import Any, Dict, List, Optional

# 错误码定义
ERR_SUCCESS = 0
ERR_INVALID_ARGS = "E001"       # 参数错误
ERR_FILE_NOT_FOUND = "E002"     # 文件不存在
ERR_INVALID_FORMAT = "E003"     # 输入格式错误
ERR_PROCESS_FAILED = "E004"     # 处理失败
ERR_OUTPUT_FAILED = "E005"      # 输出失败
ERR_SELFTEST_FAILED = "E006"    # 自检失败
ERR_UNSUPPORTED = "E007"        # 不支持的操作
ERR_INTERNAL = "E008"           # 内部错误
ERR_EMPTY_INPUT = "E009"        # 输入为空
ERR_FIELD_MISSING = "E010"      # 字段缺失


# ============================================================
# 核心数据结构
# ============================================================

class InvoiceField:
    """发票字段定义"""
    # 标准字段名列表（统一输出用）
    STANDARD_FIELDS = [
        "invoice_code",      # 发票代码
        "invoice_number",    # 发票号码
        "invoice_date",      # 开票日期
        "seller_name",       # 销售方名称
        "seller_tax_id",     # 销售方税号
        "buyer_name",        # 购买方名称
        "buyer_tax_id",      # 购买方税号
        "amount",            # 金额（不含税）
        "tax_amount",        # 税额
        "total_amount",      # 价税合计
        "invoice_type",      # 发票类型（专票/普票）
    ]

    # 必填字段（用于警告）
    REQUIRED_FIELDS = [
        "invoice_number",    # 发票号码
        "invoice_date",      # 开票日期
        "total_amount",      # 价税合计
    ]

    def __init__(self, name: str, value: str, confidence: float = 1.0):
        self.name = name
        self.value = value
        self.confidence = max(0.0, min(1.0, confidence))  # 限制在 0-1


class InvoiceResult:
    """单张发票的抽取结果"""

    def __init__(self, source: str = ""):
        self.source = source          # 来源标识（文件名/路径）
        self.fields: Dict[str, InvoiceField] = {}
        self.raw_text: str = ""       # 原始文本（模拟OCR输出）
        self.warnings: List[str] = [] # 警告信息

    def set_field(self, name: str, value: str, confidence: float = 1.0) -> None:
        """设置字段值"""
        self.fields[name] = InvoiceField(name, value, confidence)

    def get_field_value(self, name: str) -> str:
        """获取字段值，不存在返回空字符串"""
        if name in self.fields:
            return self.fields[name].value
        return ""

    def get_field_confidence(self, name: str) -> float:
        """获取字段置信度，不存在返回 0"""
        if name in self.fields:
            return self.fields[name].confidence
        return 0.0

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（含置信度标注）"""
        result = {
            "source": self.source,
            "fields": {},
            "warnings": self.warnings,
        }
        for field_name in InvoiceField.STANDARD_FIELDS:
            value = self.get_field_value(field_name)
            conf = self.get_field_confidence(field_name)
            # 低置信度标注
            if value and conf < 0.7:
                value = f"[需核实:{field_name}]{value}"
            result["fields"][field_name] = value
        return result


# ============================================================
# 核心抽取逻辑（基于模拟OCR输入）
# ============================================================

class InvoiceExtractor:
    """
    发票字段抽取器。
    输入为模拟 OCR 的结构化文本（键值对形式），
    输出标准化的发票字段。
    """

    # 字段映射规则（OCR标签 -> 标准字段名）
    FIELD_MAPPING = {
        "发票代码": "invoice_code",
        "代码": "invoice_code",
        "发票号码": "invoice_number",
        "号码": "invoice_number",
        "开票日期": "invoice_date",
        "日期": "invoice_date",
        "销售方名称": "seller_name",
        "销售方": "seller_name",
        "销方名称": "seller_name",
        "销售方税号": "seller_tax_id",
        "销方税号": "seller_tax_id",
        "购买方名称": "buyer_name",
        "购买方": "buyer_name",
        "购方名称": "buyer_name",
        "购买方税号": "buyer_tax_id",
        "购方税号": "buyer_tax_id",
        "金额": "amount",
        "不含税金额": "amount",
        "税额": "tax_amount",
        "价税合计": "total_amount",
        "合计": "total_amount",
        "发票类型": "invoice_type",
        "类型": "invoice_type",
    }

    # 发票类型关键词
    TYPE_KEYWORDS = {
        "增值税专用发票": "专票",
        "专用发票": "专票",
        "增值税普通发票": "普票",
        "普通发票": "普票",
        "电子发票": "电子票",
    }

    def extract(self, ocr_text: str, source: str = "") -> InvoiceResult:
        """
        从模拟OCR文本中抽取发票字段。

        参数:
            ocr_text: OCR识别的原始文本，格式为 "键:值" 每行一个
            source: 来源标识（文件名等）

        返回:
            InvoiceResult 对象
        """
        result = InvoiceResult(source=source)
        result.raw_text = ocr_text

        if not ocr_text or not ocr_text.strip():
            result.warnings.append("输入文本为空")
            return result

        # 解析键值对
        lines = ocr_text.strip().split("\n")
        parsed: Dict[str, str] = {}

        for line in lines:
            line = line.strip()
            if not line:
                continue
            # 支持冒号或等号分隔
            if ":" in line:
                key, _, value = line.partition(":")
            elif "=" in line:
                key, _, value = line.partition("=")
            else:
                continue

            key = key.strip()
            value = value.strip()
            if key and value:
                parsed[key] = value

        if not parsed:
            result.warnings.append("未能解析出任何键值对")
            return result

        # 字段映射
        for ocr_key, std_name in self.FIELD_MAPPING.items():
            if ocr_key in parsed:
                value = parsed[ocr_key]
                # 简单置信度评估：值非空且长度合理则置信度高
                confidence = self._evaluate_confidence(ocr_key, value)
                result.set_field(std_name, value, confidence)

        # 检测发票类型（从文本中查找关键词）
        self._detect_invoice_type(result, ocr_text)

        # 检查必填字段
        self._check_required_fields(result)

        return result

    def _evaluate_confidence(self, key: str, value: str) -> float:
        """
        评估字段置信度（0-1）。
        宽松规则：非空值基本可信，特殊字段按长度判断。
        """
        if not value:
            return 0.0

        # 税号类字段：长度较长则置信度高
        if "税号" in key:
            if len(value) >= 15:
                return 0.9
            return 0.5

        # 日期字段：包含年月日则置信度高
        if "日期" in key:
            if "年" in value or "-" in value or "/" in value:
                return 0.95
            return 0.6

        # 金额字段：包含数字则置信度高
        if "金额" in key or "税额" in key or "合计" in key:
            if any(c.isdigit() for c in value):
                return 0.9
            return 0.5

        # 其他字段：非空即高置信度
        return 0.85

    def _detect_invoice_type(self, result: InvoiceResult, text: str) -> None:
        """从文本中检测发票类型"""
        for keyword, type_name in self.TYPE_KEYWORDS.items():
            if keyword in text:
                result.set_field("invoice_type", type_name, 0.95)
                return
        # 未检测到类型
        result.set_field("invoice_type", "未知", 0.3)

    def _check_required_fields(self, result: InvoiceResult) -> None:
        """
        检查必填字段，缺失时添加警告。
        必填字段：发票号码、开票日期、价税合计
        """
        missing_fields = []
        for field in InvoiceField.REQUIRED_FIELDS:
            if not result.get_field_value(field):
                missing_fields.append(field)
        
        if missing_fields:
            result.warnings.append(f"缺少必填字段: {', '.join(missing_fields)}")


# ============================================================
# 批量处理与输出
# ============================================================

class BatchProcessor:
    """批量处理多个OCR输入"""

    def __init__(self, extractor: Optional[InvoiceExtractor] = None):
        self.extractor = extractor or InvoiceExtractor()

    def process_batch(self, items: List[Dict[str, str]]) -> List[InvoiceResult]:
        """
        批量处理。

        参数:
            items: 列表，每个元素为 {"source": str, "text": str}

        返回:
            InvoiceResult 列表
        """
        results = []
        for item in items:
            source = item.get("source", "")
            text = item.get("text", "")
            result = self.extractor.extract(text, source)
            results.append(result)
        return results

    def to_table(self, results: List[InvoiceResult], format: str = "json") -> str:
        """
        输出结构化表格。

        支持格式: json, csv, markdown
        """
        if format == "json":
            return json.dumps(
                [r.to_dict() for r in results],
                ensure_ascii=False,
                indent=2
            )
        elif format == "csv":
            return self._to_csv(results)
        elif format == "markdown":
            return self._to_markdown(results)
        else:
            raise ValueError(f"不支持的输出格式: {format}")

    def _to_csv(self, results: List[InvoiceResult]) -> str:
        """输出CSV格式"""
        fields = InvoiceField.STANDARD_FIELDS
        lines = ["source," + ",".join(fields)]
        for r in results:
            row = [r.source]
            for f in fields:
                row.append(r.get_field_value(f))
            lines.append(",".join(row))
        return "\n".join(lines)

    def _to_markdown(self, results: List[InvoiceResult]) -> str:
        """输出Markdown表格"""
        fields = InvoiceField.STANDARD_FIELDS
        header = "| 来源 | " + " | ".join(fields) + " |"
        separator = "|------|" + "|".join(["------"] * len(fields)) + "|"
        lines = [header, separator]
        for r in results:
            row = [r.source]
            for f in fields:
                row.append(r.get_field_value(f))
            lines.append("| " + " | ".join(row) + " |")
        return "\n".join(lines)


# ============================================================
# 自检模块（离线硬编码样例）
# ============================================================

def run_selftest() -> int:
    """
    内置硬编码样例数据，离线自检核心逻辑。
    不读取外部文件、不依赖当前工作目录、不访问网络。

    返回:
        0 表示成功，非 0 表示失败
    """
    print("开始自检...")

    # 硬编码测试数据（模拟OCR输出）
    test_cases = [
        {
            "source": "test_invoice_001.jpg",
            "text": """
发票代码: 031001900111
发票号码: 12345678
开票日期: 2026年03月15日
销售方名称: 北京测试科技有限公司
销售方税号: 91110108MA01XXXXX
购买方名称: 上海示例贸易有限公司
购买方税号: 91310115MA1XXXXXX
金额: 1000.00
税额: 130.00
价税合计: 1130.00
发票类型: 增值税专用发票
""",
        },
        {
            "source": "test_invoice_002.pdf",
            "text": """
发票代码=031001900222
发票号码=87654321
开票日期=2026-04-20
销售方=广州演示有限公司
销方税号=91440101MA5XXXXXX
购买方=深圳样例有限公司
购方税号=91440300MA5XXXXXX
不含税金额=500.50
税额=65.07
价税合计=565.57
""",
        },
        {
            "source": "test_invoice_003.png",
            "text": """
发票号码: 11223344
开票日期: 2026/05/01
销售方名称: 杭州测试公司
金额: 200.00
税额: 26.00
价税合计: 226.00
""",
        },
        {
            "source": "test_invoice_004.txt",
            "text": """
发票号码: 99887766
销售方名称: 测试缺失日期公司
金额: 300.00
""",
        },
    ]

    # 执行抽取
    extractor = InvoiceExtractor()
    processor = BatchProcessor(extractor)
    results = processor.process_batch(test_cases)

    # 断言检查（宽松阈值）
    try:
        # 检查第一张发票
        r1 = results[0]
        assert r1.get_field_value("invoice_code") == "031001900111", "发票代码提取错误"
        assert r1.get_field_value("invoice_number") == "12345678", "发票号码提取错误"
        assert "2026" in r1.get_field_value("invoice_date"), "开票日期提取错误"
        assert "北京" in r1.get_field_value("seller_name"), "销售方名称提取错误"
        assert r1.get_field_value("invoice_type") == "专票", "发票类型识别错误"
        assert float(r1.get_field_value("total_amount")) > 1000, "价税合计应大于1000"
        assert float(r1.get_field_value("total_amount")) < 2000, "价税合计应小于2000"

        # 检查第二张发票（使用等号分隔）
        r2 = results[1]
        assert r2.get_field_value("invoice_number") == "87654321", "第二张发票号码错误"
        assert "广州" in r2.get_field_value("seller_name"), "第二张销售方错误"
        assert float(r2.get_field_value("amount")) > 400, "金额应大于400"
        assert float(r2.get_field_value("amount")) < 600, "金额应小于600"

        # 检查第三张发票（缺少必填字段）
        r3 = results[2]
        assert r3.get_field_value("invoice_number") == "11223344", "第三张发票号码错误"
        assert r3.get_field_value("invoice_code") == "", "第三张不应有发票代码"
        assert len(r3.warnings) > 0, "缺少必填字段应产生警告"

        # 检查第四张发票（缺少多个必填字段）
        r4 = results[3]
        assert r4.get_field_value("invoice_number") == "99887766", "第四张发票号码错误"
        assert r4.get_field_value("invoice_date") == "", "第四张不应有开票日期"
        assert r4.get_field_value("total_amount") == "", "第四张不应有价税合计"
        assert len(r4.warnings) > 0, "缺少多个必填字段应产生警告"
        assert any("invoice_date" in w for w in r4.warnings), "应包含缺失日期的警告"
        assert any("total_amount" in w for w in r4.warnings), "应包含缺失价税合计的警告"

        # 检查批量处理数量
        assert len(results) == 4, "批量处理数量应为4"

        # 检查输出格式
        json_out = processor.to_table(results, "json")
        assert json_out is not None and len(json_out) > 0, "JSON输出为空"

        csv_out = processor.to_table(results, "csv")
        assert "invoice_number" in csv_out, "CSV应包含表头"

        md_out = processor.to_table(results, "markdown")
        assert "|" in md_out, "Markdown应包含表格分隔符"

        # 检查置信度标注
        result_dict = r1.to_dict()
        total_field = result_dict["fields"].get("total_amount", "")
        # 置信度大于0.7时不应有标注
        assert "[需核实" not in total_field or "total_amount" not in total_field, \
            "高置信度字段不应被标注"

        print("自检通过！所有断言成功。")
        return ERR_SUCCESS

    except AssertionError as e:
        print(f"自检失败: {e}")
        return 1
    except Exception as e:
        print(f"自检异常: {e}")
        return 1


# ============================================================
# 命令行入口
# ============================================================

def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="票据识别字段抽取工具（invoice-ocr-extract）"
    )
    parser.add_argument(
        "--input", "-i",
        type=str,
        help="输入文件路径（JSON格式，包含OCR文本列表）"
    )
    parser.add_argument(
        "--format", "-f",
        type=str,
        choices=["json", "csv", "markdown"],
        default="json",
        help="输出格式（默认: json）"
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行离线自检"
    )
    return parser.parse_args()


def load_input_file(path: str) -> List[Dict[str, str]]:
    """
    加载输入文件（JSON格式）。
    文件结构应为: [{"source": "...", "text": "..."}, ...]
    """
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"错误: 文件不存在 - {path}")
        sys.exit(ERR_FILE_NOT_FOUND)
    except json.JSONDecodeError:
        print(f"错误: 无效的JSON格式 - {path}")
        sys.exit(ERR_INVALID_FORMAT)

    if not isinstance(data, list):
        print("错误: 输入文件应为JSON数组")
        sys.exit(ERR_INVALID_FORMAT)

    items = []
    for item in data:
        if isinstance(item, dict):
            items.append({
                "source": str(item.get("source", "")),
                "text": str(item.get("text", "")),
            })
        else:
            print(f"警告: 跳过无效条目: {item}")

    if not items:
        print("错误: 输入为空")
        sys.exit(ERR_EMPTY_INPUT)

    return items


def main() -> int:
    """主入口"""
    args = parse_args()

    # 自检模式
    if args.selftest:
        return run_selftest()

    # 需要输入文件
    if not args.input:
        print("错误: 请提供 --input 参数或使用 --selftest")
        print("用法: python scripts/main.py --input <file.json> [--format json|csv|markdown]")
        print("      python scripts/main.py --selftest")
        return ERR_INVALID_ARGS

    # 加载输入
    items = load_input_file(args.input)

    # 处理
    try:
        processor = BatchProcessor()
        results = processor.process_batch(items)
        output = processor.to_table(results, args.format)
        print(output)
        return ERR_SUCCESS
    except Exception as e:
        print(f"处理失败: {e}")
        return ERR_PROCESS_FAILED


if __name__ == "__main__":
    sys.exit(main())
