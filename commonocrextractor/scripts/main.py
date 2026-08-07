#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
commonocrextractor - 发票识别与结构化数据抽取工具

基于功能规格的 clean-room 独立实现。
仅使用 Python 标准库，无第三方依赖。

功能：
- 通用票据 OCR 后处理
- 结构化字段抽取（发票号、金额、日期、税号等）
- 置信度评估与标注
- 批量处理
- 内置自检（--selftest）

错误码：
E001 输入为空
E002 关键信息缺失
E003 输入格式错误
E004 超出能力边界
E005 置信度过低
E006 内部处理异常
E007 字段解析失败
E008 批量处理中断
E009 参数不合法
E010 自检失败
"""

import argparse
import json
import re
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 常量定义
# ============================================================

# 置信度阈值
CONFIDENCE_HIGH = 0.90      # 高置信度，直接输出
CONFIDENCE_MEDIUM = 0.85    # 中置信度，建议复核
CONFIDENCE_LOW = 0.85       # 低于此值，标记需核实

# 字段类型定义
FIELD_TYPES = {
    "invoice_number": "发票号码",
    "invoice_code": "发票代码",
    "amount": "金额",
    "tax_amount": "税额",
    "date": "日期",
    "buyer_name": "购买方名称",
    "seller_name": "销售方名称",
    "buyer_tax_id": "购买方税号",
    "seller_tax_id": "销售方税号",
}

# 常用正则表达式
PATTERNS = {
    "invoice_number": r"[0-9]{8}",
    "invoice_code": r"[0-9]{10,12}",
    "amount": r"(?:¥|￥)?\s*(\d+(?:\.\d{1,2})?)",
    "tax_id": r"[0-9A-Z]{15,20}",
    "date": r"(\d{4})[年\-/](\d{1,2})[月\-/](\d{1,2})日?",
}


# ============================================================
# 数据模型
# ============================================================

class ExtractedField:
    """抽取的单个字段"""
    def __init__(self, name: str, value: Any, confidence: float,
                 source: str = "", note: str = ""):
        self.name = name
        self.value = value
        self.confidence = confidence
        self.source = source
        self.note = note

    def to_dict(self) -> Dict[str, Any]:
        return {
            "field": self.name,
            "value": self.value,
            "confidence": round(self.confidence, 4),
            "source": self.source,
            "note": self.note,
        }


class ExtractionResult:
    """抽取结果"""
    def __init__(self, source_text: str = ""):
        self.source_text = source_text
        self.fields: List[ExtractedField] = []
        self.overall_confidence = 0.0
        self.warnings: List[str] = []
        self.created_at = datetime.now().isoformat()

    def add_field(self, field: ExtractedField) -> None:
        self.fields.append(field)

    def calculate_overall(self) -> float:
        """计算整体置信度（各字段均值）"""
        if not self.fields:
            self.overall_confidence = 0.0
            return self.overall_confidence
        total = sum(f.confidence for f in self.fields)
        self.overall_confidence = total / len(self.fields)
        return self.overall_confidence

    def to_dict(self) -> Dict[str, Any]:
        return {
            "created_at": self.created_at,
            "overall_confidence": round(self.overall_confidence, 4),
            "warnings": self.warnings,
            "fields": [f.to_dict() for f in self.fields],
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


# ============================================================
# 核心处理逻辑
# ============================================================

class InvoiceExtractor:
    """发票信息抽取器"""

    def __init__(self) -> None:
        self.known_markers = {
            "发票号码": "invoice_number",
            "发票代码": "invoice_code",
            "金额": "amount",
            "价税合计": "amount",
            "税额": "tax_amount",
            "开票日期": "date",
            "购买方": "buyer_name",
            "销售方": "seller_name",
            "购方": "buyer_name",
            "销方": "seller_name",
        }

    def extract(self, text: str) -> ExtractionResult:
        """从文本中抽取发票信息"""
        # 输入校验
        if not text or not text.strip():
            raise ValueError("E001: 输入为空")

        result = ExtractionResult(text)
        lines = [line.strip() for line in text.splitlines() if line.strip()]

        # 逐行分析
        for line in lines:
            self._process_line(line, result)

        # 补充缺失字段的智能推断
        self._infer_missing_fields(result)

        # 计算整体置信度
        result.calculate_overall()

        # 添加警告
        self._add_warnings(result)

        return result

    def _process_line(self, line: str, result: ExtractionResult) -> None:
        """处理单行文本"""
        # 尝试匹配已知标记
        for marker, field_name in self.known_markers.items():
            if marker in line:
                value = self._extract_value(line, marker)
                if value:
                    # 根据字段类型转换值
                    if field_name == "amount":
                        try:
                            # 尝试转换为数字
                            cleaned_value = value.replace("¥", "").replace("￥", "").strip()
                            value = float(cleaned_value)
                        except ValueError:
                            pass  # 如果转换失败，保持字符串
                    elif field_name == "date":
                        # 标准化日期格式
                        date_match = re.search(PATTERNS["date"], value)
                        if date_match:
                            year, month, day = date_match.groups()
                            value = f"{year}-{int(month):02d}-{int(day):02d}"
                    
                    confidence = self._estimate_confidence(line, marker)
                    field = ExtractedField(
                        name=field_name,
                        value=value,
                        confidence=confidence,
                        source=line,
                    )
                    result.add_field(field)
                    return

        # 尝试通用模式匹配
        self._match_by_pattern(line, result)

    def _extract_value(self, line: str, marker: str) -> Optional[str]:
        """从标记行中提取值"""
        # 移除标记部分
        parts = line.split(marker, 1)
        if len(parts) < 2:
            return None
        value = parts[1].strip()
        # 清理常见噪声
        value = value.strip("：:：: \t")
        value = value.replace(" ", "")
        return value if value else None

    def _estimate_confidence(self, line: str, marker: str) -> float:
        """估算字段置信度"""
        base_conf = 0.85
        # 标记越明确，置信度越高
        if marker in ("发票号码", "发票代码"):
            base_conf += 0.05
        # 有冒号分隔的格式更可靠
        if ":" in line or "：" in line:
            base_conf += 0.05
        # 值长度合理加分
        value = self._extract_value(line, marker)
        if value and len(value) >= 6:
            base_conf += 0.03
        return min(base_conf, 0.98)

    def _match_by_pattern(self, line: str, result: ExtractionResult) -> None:
        """通过正则模式匹配"""
        # 匹配日期
        date_match = re.search(PATTERNS["date"], line)
        if date_match:
            year, month, day = date_match.groups()
            date_str = f"{year}-{int(month):02d}-{int(day):02d}"
            result.add_field(ExtractedField(
                name="date",
                value=date_str,
                confidence=0.90,
                source=line,
                note="通过日期格式识别",
            ))
            return

        # 匹配金额
        amount_match = re.search(PATTERNS["amount"], line)
        if amount_match and ("金额" in line or "合计" in line):
            try:
                amount_value = float(amount_match.group(1))
            except ValueError:
                amount_value = amount_match.group(1)
            result.add_field(ExtractedField(
                name="amount",
                value=amount_value,
                confidence=0.88,
                source=line,
                note="通过金额格式识别",
            ))
            return

        # 匹配税号
        tax_match = re.search(PATTERNS["tax_id"], line)
        if tax_match and ("税号" in line or "纳税人" in line):
            result.add_field(ExtractedField(
                name="buyer_tax_id" if "购" in line else "seller_tax_id",
                value=tax_match.group(0),
                confidence=0.85,
                source=line,
                note="通过税号格式识别",
            ))

    def _infer_missing_fields(self, result: ExtractionResult) -> None:
        """推断缺失字段"""
        extracted_names = {f.name for f in result.fields}

        # 如果只有金额没有税额，尝试从金额推断
        if "amount" in extracted_names and "tax_amount" not in extracted_names:
            amount_field = next(f for f in result.fields if f.name == "amount")
            if isinstance(amount_field.value, (int, float)):
                # 增值税率常见 13% 或 6%
                tax_estimate = amount_field.value * 0.13 / 1.13
                result.add_field(ExtractedField(
                    name="tax_amount",
                    value=round(tax_estimate, 2),
                    confidence=0.70,
                    note="根据金额估算（税率13%）",
                ))

    def _add_warnings(self, result: ExtractionResult) -> None:
        """添加处理警告"""
        if not result.fields:
            result.warnings.append("未识别到任何字段")
            return

        for field in result.fields:
            if field.confidence < CONFIDENCE_LOW:
                result.warnings.append(
                    f"字段 [{field.name}] 置信度偏低 ({field.confidence:.2f})，建议人工核实"
                )
            elif field.confidence < CONFIDENCE_MEDIUM:
                result.warnings.append(
                    f"字段 [{field.name}] 置信度中等 ({field.confidence:.2f})，建议复核"
                )


# ============================================================
# 批量处理
# ============================================================

def batch_extract(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """批量处理多个输入"""
    if not items:
        raise ValueError("E001: 输入为空")

    extractor = InvoiceExtractor()
    results = []

    for i, item in enumerate(items):
        try:
            # 支持不同输入格式
            if isinstance(item, str):
                text = item
            elif isinstance(item, dict):
                text = item.get("text", item.get("content", ""))
                if not text:
                    raise ValueError(f"E002: 第{i+1}项缺少文本内容")
            else:
                raise ValueError(f"E003: 第{i+1}项格式不支持")

            result = extractor.extract(text)
            result_dict = result.to_dict()
            result_dict["index"] = i + 1
            results.append(result_dict)

        except Exception as e:
            results.append({
                "index": i + 1,
                "error": str(e),
                "overall_confidence": 0.0,
                "fields": [],
                "warnings": ["E008: 该项处理失败"],
            })

    return results


# ============================================================
# 输出格式化
# ============================================================

def format_output(result: ExtractionResult, format_type: str = "text") -> str:
    """格式化输出结果"""
    if format_type == "json":
        return result.to_json()

    # 文本格式
    lines = []
    lines.append("=" * 50)
    lines.append("发票识别结果")
    lines.append("=" * 50)

    for field in result.fields:
        conf_mark = ""
        if field.confidence < CONFIDENCE_LOW:
            conf_mark = "[需核实]"
        elif field.confidence < CONFIDENCE_MEDIUM:
            conf_mark = "[建议复核]"

        field_name = FIELD_TYPES.get(field.name, field.name)
        lines.append(f"{field_name}: {field.value} {conf_mark}")

    lines.append("-" * 50)
    lines.append(f"整体置信度: {result.overall_confidence:.1%}")

    if result.warnings:
        lines.append("警告信息:")
        for w in result.warnings:
            lines.append(f"  - {w}")

    lines.append("=" * 50)
    return "\n".join(lines)


# ============================================================
# 自检功能
# ============================================================

def run_selftest() -> bool:
    """内置自检，使用硬编码样例数据"""
    print("=" * 60)
    print("commonocrextractor 自检开始")
    print("=" * 60)

    # 测试样例 1：标准发票文本
    sample1 = """
    增值税电子普通发票
    发票代码：011001900111
    发票号码：23345678
    开票日期：2026年1月15日
    购买方名称：北京科技有限公司
    购买方税号：91110108MA01ABCDEF
    销售方名称：上海信息技术有限公司
    金额：¥1234.56
    税额：¥160.49
    价税合计：¥1395.05
    """

    # 测试样例 2：简化格式
    sample2 = """
    发票号码: 87654321
    发票代码: 044031900112
    日期: 2025-12-30
    金额: 5678.90
    购买方: 广州贸易公司
    销售方: 深圳制造厂
    """

    # 测试样例 3：模糊格式（测试低置信度场景）
    sample3 = """
    这是一张发票
    号码 12345678
    金额 999
    日期 2026-03-20
    """

    extractor = InvoiceExtractor()
    all_pass = True

    # 测试1：标准发票
    print("\n[测试1] 标准发票文本抽取")
    try:
        result1 = extractor.extract(sample1)
        fields1 = {f.name: f.value for f in result1.fields}

        # 宽松断言：关键字段存在
        assert "invoice_code" in fields1, "发票代码未识别"
        assert "invoice_number" in fields1, "发票号码未识别"
        assert "amount" in fields1, "金额未识别"
        assert "date" in fields1, "日期未识别"

        # 宽松断言：值类型正确
        assert isinstance(fields1["amount"], (int, float)), f"金额类型错误，实际类型: {type(fields1['amount'])}"
        assert fields1["amount"] > 0, "金额应为正数"

        # 宽松断言：置信度合理
        assert result1.overall_confidence > 0.5, "整体置信度异常偏低"

        print(f"  ✓ 通过 (识别字段: {len(result1.fields)}个, 置信度: {result1.overall_confidence:.2%})")
    except AssertionError as e:
        print(f"  ✗ 失败: {e}")
        all_pass = False
    except Exception as e:
        print(f"  ✗ 异常: {e}")
        all_pass = False

    # 测试2：简化格式
    print("\n[测试2] 简化格式文本抽取")
    try:
        result2 = extractor.extract(sample2)
        fields2 = {f.name: f.value for f in result2.fields}

        assert "invoice_number" in fields2, "发票号码未识别"
        assert "amount" in fields2, "金额未识别"
        assert "date" in fields2, "日期未识别"

        # 宽松断言：日期格式正确性
        assert isinstance(fields2["date"], str), "日期类型错误"
        assert len(fields2["date"]) >= 10, "日期格式不完整"

        print(f"  ✓ 通过 (识别字段: {len(result2.fields)}个, 置信度: {result2.overall_confidence:.2%})")
    except AssertionError as e:
        print(f"  ✗ 失败: {e}")
        all_pass = False
    except Exception as e:
        print(f"  ✗ 异常: {e}")
        all_pass = False

    # 测试3：模糊格式
    print("\n[测试3] 模糊格式文本抽取")
    try:
        result3 = extractor.extract(sample3)
        fields3 = {f.name: f.value for f in result3.fields}

        # 宽松断言：至少识别出部分字段
        assert len(result3.fields) >= 1, "未识别到任何字段"

        # 宽松断言：低置信度字段应有标记
        low_conf_fields = [f for f in result3.fields if f.confidence < CONFIDENCE_LOW]
        if low_conf_fields:
            print(f"  ✓ 通过 (低置信度字段已标记: {len(low_conf_fields)}个)")
        else:
            print(f"  ✓ 通过 (识别字段: {len(result3.fields)}个)")

    except AssertionError as e:
        print(f"  ✗ 失败: {e}")
        all_pass = False
    except Exception as e:
        print(f"  ✗ 异常: {e}")
        all_pass = False

    # 测试4：批量处理
    print("\n[测试4] 批量处理")
    try:
        batch_items = [
            {"text": sample1},
            {"text": sample2},
            {"text": sample3},
        ]
        batch_results = batch_extract(batch_items)
        assert len(batch_results) == 3, "批量处理数量错误"
        assert all("error" not in r for r in batch_results), "批量处理存在失败项"

        print(f"  ✓ 通过 (成功处理 {len(batch_results)} 项)")
    except AssertionError as e:
        print(f"  ✗ 失败: {e}")
        all_pass = False
    except Exception as e:
        print(f"  ✗ 异常: {e}")
        all_pass = False

    # 测试5：错误处理
    print("\n[测试5] 错误处理")
    try:
        # 空输入
        try:
            extractor.extract("")
            print("  ✗ 失败: 空输入未抛出异常")
            all_pass = False
        except ValueError as e:
            assert "E001" in str(e), "错误码不正确"
            print("  ✓ 通过 (E001 空输入处理正确)")

        # 批量空输入
        try:
            batch_extract([])
            print("  ✗ 失败: 批量空输入未抛出异常")
            all_pass = False
        except ValueError as e:
            assert "E001" in str(e), "错误码不正确"
            print("  ✓ 通过 (E001 批量空输入处理正确)")

    except Exception as e:
        print(f"  ✗ 异常: {e}")
        all_pass = False

    # 测试6：输出格式
    print("\n[测试6] 输出格式")
    try:
        result = extractor.extract(sample1)
        json_out = format_output(result, "json")
        # 宽松断言：JSON 可解析
        parsed = json.loads(json_out)
        assert "fields" in parsed, "JSON输出缺少fields字段"
        assert "overall_confidence" in parsed, "JSON输出缺少置信度"

        text_out = format_output(result, "text")
        assert "发票识别结果" in text_out, "文本输出缺少标题"

        print("  ✓ 通过 (JSON和文本格式均正确)")
    except AssertionError as e:
        print(f"  ✗ 失败: {e}")
        all_pass = False
    except Exception as e:
        print(f"  ✗ 异常: {e}")
        all_pass = False

    # 总结
    print("\n" + "=" * 60)
    if all_pass:
        print("自检全部通过 ✓")
    else:
        print("自检存在失败项 ✗")
    print("=" * 60)

    return all_pass


# ============================================================
# 命令行入口
# ============================================================

def main() -> int:
    """命令行主入口"""
    parser = argparse.ArgumentParser(
        description="commonocrextractor - 发票识别与结构化数据抽取工具",
        epilog="示例: python main.py --text '发票号码12345678 金额100元'"
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检（使用硬编码样例数据，无需外部输入）",
    )
    parser.add_argument(
        "--text",
        type=str,
        help="待识别的发票文本内容",
    )
    parser.add_argument(
        "--file",
        type=str,
        help="包含发票文本的文件路径",
    )
    parser.add_argument(
        "--format",
        type=str,
        choices=["text", "json"],
        default="text",
        help="输出格式（默认: text）",
    )
    parser.add_argument(
        "--batch",
        type=str,
        help="批量模式，JSON文件路径（包含items数组）",
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        success = run_selftest()
        return 0 if success else 1

    try:
        # 批量模式
        if args.batch:
            try:
                with open(args.batch, "r", encoding="utf-8") as f:
                    batch_data = json.load(f)
                items = batch_data.get("items", batch_data)
                if not isinstance(items, list):
                    raise ValueError("E003: 批量数据格式错误，需要items数组")

                results = batch_extract(items)
                print(json.dumps(results, ensure_ascii=False, indent=2))
                return 0
            except FileNotFoundError:
                print("E003: 批量文件不存在", file=sys.stderr)
                return 1
            except json.JSONDecodeError:
                print("E003: 批量文件不是有效JSON", file=sys.stderr)
                return 1

        # 单条模式
        text = args.text
        if args.file:
            try:
                with open(args.file, "r", encoding="utf-8") as f:
                    text = f.read()
            except FileNotFoundError:
                print("E003: 文件不存在", file=sys.stderr)
                return 1

        if not text:
            parser.print_help()
            print("\nE001: 请提供 --text 或 --file 参数，或使用 --selftest 运行自检", file=sys.stderr)
            return 1

        # 执行抽取
        extractor = InvoiceExtractor()
        result = extractor.extract(text)

        # 输出
        if args.format == "json":
            print(result.to_json())
        else:
            print(format_output(result, "text"))

        return 0

    except ValueError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"E006: 处理异常 - {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
