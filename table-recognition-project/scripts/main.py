#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
发票识别 (Invoice Recognition) - 独立实现
==========================================
基于功能规格的 clean-room 实现，仅使用标准库。

核心能力:
1. 从文本/结构化输入中提取发票关键信息
2. 识别实体与关系，输出结构化结果
3. 提供置信度评估与标注
4. 支持批量处理

错误码:
    E001: 输入为空
    E002: 关键信息缺失
    E003: 输入格式错误
    E004: 超出能力边界
    E005: 置信度过低
    E006: 内部逻辑错误
    E007: 未知错误
    E008: 自检失败
    E009: 参数错误
    E010: 文件操作失败
"""

import argparse
import json
import re
import sys
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 数据模型
# ============================================================

@dataclass
class InvoiceEntity:
    """发票实体"""
    name: str
    value: str
    confidence: float = 1.0
    source: str = "input"
    note: str = ""


@dataclass
class InvoiceRelation:
    """实体间关系"""
    source: str
    target: str
    relation: str
    confidence: float = 1.0
    note: str = ""


@dataclass
class InvoiceResult:
    """结构化发票结果"""
    entities: List[InvoiceEntity] = field(default_factory=list)
    relations: List[InvoiceRelation] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    overall_confidence: float = 1.0
    raw_text: str = ""
    format: str = "json"


# ============================================================
# 核心解析逻辑
# ============================================================

class InvoiceParser:
    """
    发票解析器 - 从文本或结构化输入中提取发票信息
    """

    # 常见发票字段及其别名
    FIELD_ALIASES = {
        "发票号码": ["发票号码", "发票号", "invoice_no", "invoice_number", "no"],
        "发票代码": ["发票代码", "invoice_code", "code"],
        "开票日期": ["开票日期", "日期", "date", "issue_date"],
        "购买方名称": ["购买方名称", "购买方", "买方", "buyer_name", "buyer"],
        "购买方税号": ["购买方税号", "购买方纳税人识别号", "buyer_tax_id"],
        "销售方名称": ["销售方名称", "销售方", "卖方", "seller_name", "seller"],
        "销售方税号": ["销售方税号", "销售方纳税人识别号", "seller_tax_id"],
        "金额": ["金额", "价税合计", "total_amount", "amount", "total"],
        "税额": ["税额", "tax_amount", "tax"],
        "价税合计": ["价税合计", "总金额", "total_with_tax", "grand_total"],
    }

    # 必填字段（用于完整性检查）
    REQUIRED_FIELDS = ["发票号码", "开票日期", "购买方名称", "销售方名称", "金额"]

    # 金额字段（用于数字校验）
    MONEY_FIELDS = ["金额", "税额", "价税合计"]

    def __init__(self) -> None:
        """初始化解析器"""
        self._field_patterns = self._build_field_patterns()

    def _build_field_patterns(self) -> Dict[str, re.Pattern]:
        """构建字段匹配模式"""
        patterns = {}
        for canonical, aliases in self.FIELD_ALIASES.items():
            # 构建正则：字段名后跟冒号、等号或空白
            alias_patterns = [re.escape(a) for a in aliases]
            combined = "|".join(alias_patterns)
            patterns[canonical] = re.compile(
                rf"(?:{combined})\s*[:：=]?\s*(.+)",
                re.IGNORECASE
            )
        return patterns

    def parse(self, input_data: Any) -> InvoiceResult:
        """
        解析输入数据

        支持:
        - 字符串: 视为原始文本
        - 字典: 视为结构化字段
        - 列表: 批量处理（取第一个）

        Args:
            input_data: 输入数据

        Returns:
            InvoiceResult: 解析结果

        Raises:
            ValueError: 输入为空或格式错误
        """
        if input_data is None:
            raise ValueError("E001: 输入为空")

        if isinstance(input_data, list):
            if not input_data:
                raise ValueError("E001: 输入为空")
            input_data = input_data[0]

        if isinstance(input_data, dict):
            return self._parse_dict(input_data)
        elif isinstance(input_data, str):
            return self._parse_text(input_data)
        else:
            raise ValueError(f"E003: 输入格式错误，不支持类型 {type(input_data)}")

    def _parse_dict(self, data: Dict[str, Any]) -> InvoiceResult:
        """解析字典输入"""
        result = InvoiceResult()
        result.raw_text = json.dumps(data, ensure_ascii=False)

        # 提取实体
        for key, value in data.items():
            if value is None or value == "":
                continue
            canonical = self._find_canonical_field(key)
            if canonical:
                entity = InvoiceEntity(
                    name=canonical,
                    value=str(value),
                    confidence=0.95,
                    source="structured"
                )
                result.entities.append(entity)

        # 检查必填字段
        self._check_required_fields(result)
        self._validate_money_fields(result)
        self._compute_confidence(result)
        return result

    def _parse_text(self, text: str) -> InvoiceResult:
        """解析文本输入"""
        result = InvoiceResult()
        result.raw_text = text

        if not text.strip():
            raise ValueError("E001: 输入为空")

        # 逐行解析，尝试匹配字段
        lines = text.splitlines()
        for line in lines:
            line = line.strip()
            if not line:
                continue

            # 尝试匹配所有字段模式
            for canonical, pattern in self._field_patterns.items():
                match = pattern.search(line)
                if match:
                    value = match.group(1).strip()
                    if value:
                        entity = InvoiceEntity(
                            name=canonical,
                            value=value,
                            confidence=0.85,  # 文本解析置信度略低
                            source="text"
                        )
                        result.entities.append(entity)
                    break

        # 检查必填字段
        self._check_required_fields(result)
        self._validate_money_fields(result)
        self._compute_confidence(result)
        return result

    def _find_canonical_field(self, key: str) -> Optional[str]:
        """查找字段的标准名称"""
        key_lower = key.lower().strip()
        for canonical, aliases in self.FIELD_ALIASES.items():
            for alias in aliases:
                if alias.lower() == key_lower:
                    return canonical
        # 模糊匹配：包含关系
        for canonical, aliases in self.FIELD_ALIASES.items():
            for alias in aliases:
                if alias.lower() in key_lower or key_lower in alias.lower():
                    return canonical
        return None

    def _check_required_fields(self, result: InvoiceResult) -> None:
        """检查必填字段"""
        found = {e.name for e in result.entities}
        missing = [f for f in self.REQUIRED_FIELDS if f not in found]
        if missing:
            result.warnings.append(f"缺少必填字段: {', '.join(missing)} (E002)")

    def _validate_money_fields(self, result: InvoiceResult) -> None:
        """验证金额字段"""
        for entity in result.entities:
            if entity.name in self.MONEY_FIELDS:
                try:
                    # 去除货币符号和空格
                    cleaned = entity.value.replace("¥", "").replace("￥", "").strip()
                    float(cleaned)
                except ValueError:
                    entity.confidence = min(entity.confidence, 0.5)
                    entity.note = "金额格式异常"
                    result.warnings.append(f"字段[{entity.name}]金额格式异常 (E005)")

    def _compute_confidence(self, result: InvoiceResult) -> None:
        """计算整体置信度"""
        if not result.entities:
            result.overall_confidence = 0.0
            result.warnings.append("未识别到任何字段 (E005)")
            return

        # 基础置信度：字段覆盖率
        found = {e.name for e in result.entities}
        coverage = len(found) / len(self.REQUIRED_FIELDS)
        base_conf = min(1.0, coverage)

        # 平均实体置信度
        avg_entity_conf = sum(e.confidence for e in result.entities) / len(result.entities)

        # 综合置信度
        result.overall_confidence = (base_conf * 0.6 + avg_entity_conf * 0.4)

        # 根据置信度添加标注
        if result.overall_confidence < 0.85:
            result.warnings.append("整体置信度低于85%，建议人工复核 (E005)")


# ============================================================
# 输出格式化
# ============================================================

class ResultFormatter:
    """结果格式化器"""

    @staticmethod
    def format(result: InvoiceResult, output_format: str = "json") -> str:
        """
        格式化输出结果

        Args:
            result: 解析结果
            output_format: 输出格式 (json/text)

        Returns:
            格式化后的字符串
        """
        if output_format == "json":
            return ResultFormatter._to_json(result)
        elif output_format == "text":
            return ResultFormatter._to_text(result)
        else:
            raise ValueError(f"E009: 不支持的输出格式: {output_format}")

    @staticmethod
    def _to_json(result: InvoiceResult) -> str:
        """转换为 JSON 格式"""
        data = {
            "entities": [asdict(e) for e in result.entities],
            "relations": [asdict(r) for r in result.relations],
            "warnings": result.warnings,
            "overall_confidence": round(result.overall_confidence, 4),
            "raw_text_preview": result.raw_text[:200] if result.raw_text else "",
        }
        return json.dumps(data, ensure_ascii=False, indent=2)

    @staticmethod
    def _to_text(result: InvoiceResult) -> str:
        """转换为文本格式"""
        lines = []
        lines.append("=" * 40)
        lines.append("发票识别结果")
        lines.append("=" * 40)

        if result.entities:
            lines.append("\n[实体]")
            for entity in result.entities:
                conf_mark = ""
                if entity.confidence < 0.85:
                    conf_mark = " [需核实]"
                elif entity.confidence < 0.9:
                    conf_mark = " [建议复核]"
                lines.append(f"  {entity.name}: {entity.value}{conf_mark}")

        if result.relations:
            lines.append("\n[关系]")
            for relation in result.relations:
                lines.append(f"  {relation.source} -[{relation.relation}]-> {relation.target}")

        if result.warnings:
            lines.append("\n[警告]")
            for warning in result.warnings:
                lines.append(f"  ⚠ {warning}")

        lines.append(f"\n整体置信度: {result.overall_confidence:.1%}")
        lines.append("=" * 40)

        return "\n".join(lines)


# ============================================================
# 批量处理
# ============================================================

class BatchProcessor:
    """批量处理器"""

    def __init__(self, parser: InvoiceParser) -> None:
        self.parser = parser

    def process(self, items: List[Any], output_format: str = "json") -> List[Dict[str, Any]]:
        """
        批量处理多个输入

        Args:
            items: 输入列表
            output_format: 输出格式

        Returns:
            处理结果列表
        """
        results = []
        for i, item in enumerate(items):
            try:
                result = self.parser.parse(item)
                formatted = ResultFormatter.format(result, output_format)
                results.append({
                    "index": i,
                    "success": True,
                    "result": formatted,
                    "confidence": result.overall_confidence,
                })
            except ValueError as e:
                results.append({
                    "index": i,
                    "success": False,
                    "error": str(e),
                    "result": None,
                })
        return results


# ============================================================
# 自检功能
# ============================================================

def run_selftest() -> bool:
    """
    自检功能 - 使用内置硬编码样例数据

    测试覆盖:
    1. 文本解析
    2. 字典解析
    3. 必填字段检查
    4. 置信度计算
    5. 批量处理
    6. 格式化输出

    Returns:
        bool: 自检是否通过
    """
    print("开始自检...")
    parser = InvoiceParser()
    formatter = ResultFormatter()

    # 测试用例 1: 文本解析
    sample_text = """
    增值税发票
    发票号码: 12345678
    发票代码: 1100212345
    开票日期: 2024-01-15
    购买方名称: 某某科技有限公司
    购买方税号: 91110000MA01XXXXXX
    销售方名称: 某某商贸有限公司
    销售方税号: 91110000MA02YYYYYY
    金额: 1000.00
    税额: 130.00
    价税合计: 1130.00
    """
    try:
        result = parser.parse(sample_text)
        assert len(result.entities) >= 5, "E008: 文本解析实体数量不足"
        assert result.overall_confidence > 0.5, "E008: 置信度异常"
        print(f"  ✓ 文本解析通过 (实体数: {len(result.entities)}, 置信度: {result.overall_confidence:.1%})")
    except AssertionError as e:
        print(f"  ✗ 文本解析失败: {e}")
        return False
    except Exception as e:
        print(f"  ✗ 文本解析异常: {e}")
        return False

    # 测试用例 2: 字典解析
    sample_dict = {
        "发票号码": "87654321",
        "发票代码": "1100222333",
        "开票日期": "2024-02-20",
        "购买方名称": "测试采购有限公司",
        "销售方名称": "测试销售有限公司",
        "金额": "500.00",
        "税额": "65.00",
        "价税合计": "565.00",
    }
    try:
        result = parser.parse(sample_dict)
        assert len(result.entities) >= 5, "E008: 字典解析实体数量不足"
        assert result.overall_confidence > 0.5, "E008: 置信度异常"
        print(f"  ✓ 字典解析通过 (实体数: {len(result.entities)}, 置信度: {result.overall_confidence:.1%})")
    except AssertionError as e:
        print(f"  ✗ 字典解析失败: {e}")
        return False
    except Exception as e:
        print(f"  ✗ 字典解析异常: {e}")
        return False

    # 测试用例 3: 必填字段检查
    incomplete_dict = {
        "发票号码": "123",
        "开票日期": "2024-01-01",
        # 缺少购买方、销售方、金额
    }
    try:
        result = parser.parse(incomplete_dict)
        assert any("缺少必填字段" in w for w in result.warnings), "E008: 必填字段检查失败"
        print("  ✓ 必填字段检查通过")
    except AssertionError as e:
        print(f"  ✗ 必填字段检查失败: {e}")
        return False
    except Exception as e:
        print(f"  ✗ 必填字段检查异常: {e}")
        return False

    # 测试用例 4: 金额校验
    bad_money_dict = {
        "发票号码": "123",
        "开票日期": "2024-01-01",
        "购买方名称": "测试公司",
        "销售方名称": "测试公司2",
        "金额": "abc",  # 非法金额
    }
    try:
        result = parser.parse(bad_money_dict)
        assert any("金额格式异常" in w for w in result.warnings), "E008: 金额校验失败"
        print("  ✓ 金额校验通过")
    except AssertionError as e:
        print(f"  ✗ 金额校验失败: {e}")
        return False
    except Exception as e:
        print(f"  ✗ 金额校验异常: {e}")
        return False

    # 测试用例 5: 批量处理
    batch_items = [sample_dict, incomplete_dict, "发票号码: 999\n金额: 100.00"]
    try:
        processor = BatchProcessor(parser)
        results = processor.process(batch_items)
        assert len(results) == 3, "E008: 批量处理数量错误"
        assert results[0]["success"] and results[1]["success"] and results[2]["success"], "E008: 批量处理失败"
        print(f"  ✓ 批量处理通过 ({len(results)} items)")
    except AssertionError as e:
        print(f"  ✗ 批量处理失败: {e}")
        return False
    except Exception as e:
        print(f"  ✗ 批量处理异常: {e}")
        return False

    # 测试用例 6: 格式化输出
    try:
        result = parser.parse(sample_dict)
        json_out = formatter.format(result, "json")
        assert "entities" in json_out, "E008: JSON 格式化失败"
        text_out = formatter.format(result, "text")
        assert "发票识别结果" in text_out, "E008: 文本格式化失败"
        print("  ✓ 格式化输出通过")
    except AssertionError as e:
        print(f"  ✗ 格式化输出失败: {e}")
        return False
    except Exception as e:
        print(f"  ✗ 格式化输出异常: {e}")
        return False

    # 测试用例 7: 错误处理
    try:
        parser.parse(None)
        print("  ✗ 空输入错误处理失败")
        return False
    except ValueError as e:
        assert "E001" in str(e), "E008: 错误码不正确"
        print("  ✓ 空输入错误处理通过")

    try:
        parser.parse(12345)  # 不支持的输入类型
        print("  ✗ 输入类型错误处理失败")
        return False
    except ValueError as e:
        assert "E003" in str(e), "E008: 错误码不正确"
        print("  ✓ 输入类型错误处理通过")

    print("\n所有自检用例通过 ✓")
    return True


# ============================================================
# 主入口
# ============================================================

def main() -> int:
    """
    主入口函数

    Returns:
        int: 退出码 (0成功, 1失败)
    """
    parser = argparse.ArgumentParser(
        description="发票识别 - 从文本或结构化输入中提取发票信息",
        epilog="示例: python main.py --input '发票号码: 123\n金额: 100.00' --format json"
    )
    parser.add_argument(
        "--input", "-i",
        type=str,
        help="输入文本或 JSON 字符串"
    )
    parser.add_argument(
        "--file", "-f",
        type=str,
        help="输入文件路径"
    )
    parser.add_argument(
        "--format", "-fmt",
        type=str,
        choices=["json", "text"],
        default="json",
        help="输出格式 (默认: json)"
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行自检并退出"
    )
    parser.add_argument(
        "--version",
        action="version",
        version="invoice-recognition 1.0.0"
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        success = run_selftest()
        return 0 if success else 1

    # 输入来源处理
    input_data = None
    if args.input:
        # 尝试解析为 JSON
        try:
            input_data = json.loads(args.input)
        except json.JSONDecodeError:
            input_data = args.input
    elif args.file:
        try:
            with open(args.file, "r", encoding="utf-8") as f:
                content = f.read()
            try:
                input_data = json.loads(content)
            except json.JSONDecodeError:
                input_data = content
        except FileNotFoundError:
            print("E010: 文件不存在", file=sys.stderr)
            return 1
        except IOError as e:
            print(f"E010: 文件读取失败: {e}", file=sys.stderr)
            return 1
    else:
        # 从标准输入读取
        if not sys.stdin.isatty():
            content = sys.stdin.read().strip()
            if content:
                try:
                    input_data = json.loads(content)
                except json.JSONDecodeError:
                    input_data = content

    # 无输入时提示
    if input_data is None:
        print("E001: 请提供输入内容 (使用 --input, --file, 或管道输入)", file=sys.stderr)
        return 1

    # 执行解析
    try:
        invoice_parser = InvoiceParser()
        result = invoice_parser.parse(input_data)
        output = ResultFormatter.format(result, args.format)
        print(output)
        return 0
    except ValueError as e:
        print(str(e), file=sys.stderr)
        return 1
    except Exception as e:
        print(f"E007: 未知错误: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
