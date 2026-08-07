#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
laravel-ocr 发票识别技能 - 独立实现脚本
========================================
本脚本根据功能规格独立编写，不包含任何既有代码。
提供发票识别、结构化输出、置信度标注、批量处理等核心能力。

用法:
    python main.py --selftest          # 离线自检
    python main.py --input "文本内容"   # 处理单个输入
    python main.py --input "内容1" --input "内容2"  # 批量处理
    python main.py --format json       # 指定输出格式

错误码:
    E001: 输入为空
    E002: 关键信息缺失
    E003: 输入格式错误
    E004: 超出能力边界
    E005: 置信度过低
    E006: 参数解析错误
    E007: 文件读取失败
    E008: 输出格式不支持
    E009: 内部处理错误
    E010: 自检失败
"""

import argparse
import json
import re
import sys
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 核心数据结构
# ============================================================

class InvoiceData:
    """发票结构化数据模型"""
    
    def __init__(self):
        self.invoice_code: str = ""          # 发票代码
        self.invoice_number: str = ""        # 发票号码
        self.invoice_date: str = ""          # 开票日期
        self.seller_name: str = ""           # 销售方名称
        self.seller_tax_id: str = ""         # 销售方税号
        self.buyer_name: str = ""            # 购买方名称
        self.buyer_tax_id: str = ""          # 购买方税号
        self.total_amount: float = 0.0       # 价税合计
        self.tax_amount: float = 0.0         # 税额
        self.amount_without_tax: float = 0.0 # 不含税金额
        self.raw_text: str = ""              # 原始文本
        self.confidence: float = 0.0         # 整体置信度
        self.field_confidence: Dict[str, float] = {}  # 字段级置信度
        self.warnings: List[str] = []        # 警告信息
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "invoice_code": self.invoice_code,
            "invoice_number": self.invoice_number,
            "invoice_date": self.invoice_date,
            "seller_name": self.seller_name,
            "seller_tax_id": self.seller_tax_id,
            "buyer_name": self.buyer_name,
            "buyer_tax_id": self.buyer_tax_id,
            "total_amount": self.total_amount,
            "tax_amount": self.tax_amount,
            "amount_without_tax": self.amount_without_tax,
            "confidence": self.confidence,
            "field_confidence": self.field_confidence,
            "warnings": self.warnings,
            "raw_text_preview": self.raw_text[:200] if self.raw_text else ""
        }
    
    def to_json(self) -> str:
        """转换为JSON字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


# ============================================================
# 核心识别引擎
# ============================================================

class InvoiceRecognizer:
    """发票识别核心引擎"""
    
    # 常见字段模式
    PATTERNS = {
        "invoice_code": [
            r'发票代码[:：]?\s*([0-9]{10,12})',
            r'code[:：]?\s*([0-9]{10,12})',
        ],
        "invoice_number": [
            r'发票号码[:：]?\s*([0-9]{8,10})',
            r'number[:：]?\s*([0-9]{8,10})',
            r'No\.?\s*[:：]?\s*([0-9]{8,10})',
        ],
        "invoice_date": [
            r'开票日期[:：]?\s*(\d{4}[-/年]\d{1,2}[-/月]\d{1,2}日?)',
            r'date[:：]?\s*(\d{4}[-/]\d{1,2}[-/]\d{1,2})',
        ],
        "seller_name": [
            r'销售方信息[:：]?\s*名称[:：]?\s*([^\n\r]+)',
            r'销售方名称[:：]?\s*([^\n\r]+)',
            r'销售方[:：]?\s*名称[:：]?\s*([^\n\r]+)',
            r'seller\s*name[:：]?\s*([^\n\r]+)',
            r'seller[:：]?\s*([^\n\r]+)',
        ],
        "seller_tax_id": [
            r'销售方信息[:：]?\s*税号[:：]?\s*([0-9A-Z]{15,20})',
            r'销售方税号[:：]?\s*([0-9A-Z]{15,20})',
            r'销售方[:：]?\s*税号[:：]?\s*([0-9A-Z]{15,20})',
            r'seller\s*tax\s*id[:：]?\s*([0-9A-Z]{15,20})',
        ],
        "buyer_name": [
            r'购买方信息[:：]?\s*名称[:：]?\s*([^\n\r]+)',
            r'购买方名称[:：]?\s*([^\n\r]+)',
            r'购买方[:：]?\s*名称[:：]?\s*([^\n\r]+)',
            r'buyer\s*name[:：]?\s*([^\n\r]+)',
            r'buyer[:：]?\s*([^\n\r]+)',
        ],
        "buyer_tax_id": [
            r'购买方信息[:：]?\s*税号[:：]?\s*([0-9A-Z]{15,20})',
            r'购买方税号[:：]?\s*([0-9A-Z]{15,20})',
            r'购买方[:：]?\s*税号[:：]?\s*([0-9A-Z]{15,20})',
            r'buyer\s*tax\s*id[:：]?\s*([0-9A-Z]{15,20})',
        ],
        "total_amount": [
            r'价税合计[（(小写）)]?[:：]?\s*[¥￥]?\s*([0-9]+\.?[0-9]*)',
            r'total\s*amount[:：]?\s*[¥￥]?\s*([0-9]+\.?[0-9]*)',
            r'total[:：]?\s*[¥￥]?\s*([0-9]+\.?[0-9]*)',
        ],
        "tax_amount": [
            r'税额[:：]?\s*[¥￥]?\s*([0-9]+\.?[0-9]*)',
            r'tax\s*amount[:：]?\s*[¥￥]?\s*([0-9]+\.?[0-9]*)',
        ],
        "amount_without_tax": [
            r'不含税金额[:：]?\s*[¥￥]?\s*([0-9]+\.?[0-9]*)',
            r'amount\s*without\s*tax[:：]?\s*[¥￥]?\s*([0-9]+\.?[0-9]*)',
        ],
    }
    
    def __init__(self):
        """初始化识别器"""
        self.compiled_patterns = {}
        for field, patterns in self.PATTERNS.items():
            self.compiled_patterns[field] = [re.compile(p, re.IGNORECASE) for p in patterns]
    
    def recognize(self, text: str) -> InvoiceData:
        """
        识别发票文本内容
        
        Args:
            text: 发票文本内容
            
        Returns:
            InvoiceData: 结构化发票数据
        """
        result = InvoiceData()
        result.raw_text = text
        
        if not text or not text.strip():
            result.confidence = 0.0
            result.warnings.append("输入文本为空")
            return result
        
        # 逐字段识别
        found_fields = 0
        total_fields = len(self.compiled_patterns)
        
        for field, patterns in self.compiled_patterns.items():
            field_value, field_conf = self._extract_field(text, patterns)
            if field_value:
                found_fields += 1
                self._set_field(result, field, field_value)
                result.field_confidence[field] = field_conf
            else:
                result.field_confidence[field] = 0.0
        
        # 计算整体置信度
        if found_fields > 0:
            result.confidence = (found_fields / total_fields) * 100.0
        else:
            result.confidence = 0.0
        
        # 添加警告
        if result.confidence < 85.0:
            result.warnings.append("置信度低于85%，建议人工复核")
        if result.confidence < 90.0:
            result.warnings.append("部分字段未能识别或置信度较低")
        
        # 校验金额关系（如果都有值）
        self._validate_amounts(result)
        
        return result
    
    def _extract_field(self, text: str, patterns: List[re.Pattern]) -> Tuple[str, float]:
        """
        从文本中提取字段值
        
        Args:
            text: 输入文本
            patterns: 正则模式列表
            
        Returns:
            Tuple[值, 置信度]
        """
        for pattern in patterns:
            match = pattern.search(text)
            if match:
                value = match.group(1).strip()
                if value:
                    # 根据匹配长度和位置计算置信度
                    conf = min(95.0, 70.0 + len(value) * 2.0)
                    return value, conf
        return "", 0.0
    
    def _set_field(self, data: InvoiceData, field: str, value: str):
        """设置字段值"""
        if field in ("total_amount", "tax_amount", "amount_without_tax"):
            try:
                setattr(data, field, float(value))
            except ValueError:
                setattr(data, field, 0.0)
        else:
            setattr(data, field, value)
    
    def _validate_amounts(self, data: InvoiceData):
        """校验金额关系"""
        if data.total_amount > 0 and data.tax_amount > 0 and data.amount_without_tax > 0:
            expected_total = data.amount_without_tax + data.tax_amount
            if abs(expected_total - data.total_amount) > 0.01:
                data.warnings.append("金额校验不一致：价税合计与(不含税金额+税额)不匹配")


# ============================================================
# 输出格式化
# ============================================================

class OutputFormatter:
    """输出格式化器"""
    
    @staticmethod
    def format_text(data: InvoiceData) -> str:
        """文本格式输出"""
        lines = [
            "=" * 50,
            "发票识别结果",
            "=" * 50,
            f"发票代码: {data.invoice_code or '未识别'}",
            f"发票号码: {data.invoice_number or '未识别'}",
            f"开票日期: {data.invoice_date or '未识别'}",
            f"销售方: {data.seller_name or '未识别'}",
            f"销售方税号: {data.seller_tax_id or '未识别'}",
            f"购买方: {data.buyer_name or '未识别'}",
            f"购买方税号: {data.buyer_tax_id or '未识别'}",
            f"价税合计: {data.total_amount:.2f}" if data.total_amount else "价税合计: 未识别",
            f"税额: {data.tax_amount:.2f}" if data.tax_amount else "税额: 未识别",
            f"不含税金额: {data.amount_without_tax:.2f}" if data.amount_without_tax else "不含税金额: 未识别",
            "-" * 50,
            f"置信度: {data.confidence:.1f}%",
        ]
        
        if data.warnings:
            lines.append("-" * 50)
            lines.append("警告:")
            for warning in data.warnings:
                lines.append(f"  ⚠ {warning}")
        
        lines.append("=" * 50)
        return "\n".join(lines)
    
    @staticmethod
    def format_json(data: InvoiceData) -> str:
        """JSON格式输出"""
        return data.to_json()
    
    @staticmethod
    def format_compact(data: InvoiceData) -> str:
        """紧凑格式输出"""
        items = []
        if data.invoice_code:
            items.append(f"代码:{data.invoice_code}")
        if data.invoice_number:
            items.append(f"号码:{data.invoice_number}")
        if data.seller_name:
            items.append(f"销售方:{data.seller_name}")
        if data.total_amount:
            items.append(f"金额:{data.total_amount:.2f}")
        items.append(f"置信度:{data.confidence:.1f}%")
        return " | ".join(items)


# ============================================================
# 批量处理
# ============================================================

class BatchProcessor:
    """批量处理器"""
    
    def __init__(self, recognizer: InvoiceRecognizer):
        self.recognizer = recognizer
    
    def process_batch(self, texts: List[str]) -> List[InvoiceData]:
        """
        批量处理文本
        
        Args:
            texts: 文本列表
            
        Returns:
            List[InvoiceData]: 识别结果列表
        """
        results = []
        for text in texts:
            if text and text.strip():
                results.append(self.recognizer.recognize(text))
            else:
                # 空输入处理
                empty_result = InvoiceData()
                empty_result.confidence = 0.0
                empty_result.warnings.append("输入为空")
                results.append(empty_result)
        return results


# ============================================================
# 自检模块
# ============================================================

class SelfTest:
    """自检模块 - 使用内置硬编码样例数据"""
    
    # 内置测试样例
    SAMPLE_INVOICE = """
    增值税普通发票
    
    发票代码: 144032100110
    发票号码: 12345678
    开票日期: 2024年01月15日
    
    购买方信息:
    名称: 北京科技有限公司
    税号: 91110108MA01XXXXX
    
    销售方信息:
    名称: 上海贸易有限公司
    税号: 91310115MA1KXXXXX
    
    项目名称: 技术服务费
    金额: 10000.00
    税额: 600.00
    价税合计(小写): 10600.00
    
    备注: 测试发票
    """
    
    SAMPLE_INVOICE2 = """
    INVOICE
    
    Invoice Code: 144032100112
    Invoice Number: 87654321
    Date: 2024/03/20
    
    Seller: 广州制造有限公司
    Seller Tax ID: 91440101MA5XXXXX
    
    Buyer: 深圳采购有限公司
    Buyer Tax ID: 91440300MA5XXXXX
    
    Total Amount: 5000.00
    Tax Amount: 300.00
    Amount Without Tax: 4700.00
    """
    
    SAMPLE_INVALID = "这不是发票内容"
    
    @classmethod
    def run(cls) -> bool:
        """
        运行自检
        
        Returns:
            bool: 自检是否通过
        """
        print("=" * 60)
        print("laravel-ocr 发票识别 - 自检模式")
        print("=" * 60)
        
        recognizer = InvoiceRecognizer()
        
        # 测试1: 中文发票识别
        print("\n[测试1] 中文发票识别")
        result1 = recognizer.recognize(cls.SAMPLE_INVOICE)
        assert result1.invoice_code == "144032100110", "发票代码识别失败"
        assert result1.invoice_number == "12345678", "发票号码识别失败"
        assert "2024" in result1.invoice_date, "开票日期识别失败"
        assert "上海贸易" in result1.seller_name, f"销售方识别失败: {result1.seller_name}"
        assert result1.total_amount > 10000, "金额识别失败"
        assert result1.confidence > 50, "置信度过低"
        print(f"  ✓ 通过 (置信度: {result1.confidence:.1f}%)")
        
        # 测试2: 英文发票识别
        print("\n[测试2] 英文发票识别")
        result2 = recognizer.recognize(cls.SAMPLE_INVOICE2)
        assert result2.invoice_code == "144032100112", "发票代码识别失败"
        assert result2.invoice_number == "87654321", "发票号码识别失败"
        assert "广州制造" in result2.seller_name, f"销售方识别失败: {result2.seller_name}"
        assert result2.total_amount > 4000, "金额识别失败"
        assert result2.tax_amount > 200, "税额识别失败"
        print(f"  ✓ 通过 (置信度: {result2.confidence:.1f}%)")
        
        # 测试3: 无效输入处理
        print("\n[测试3] 无效输入处理")
        result3 = recognizer.recognize(cls.SAMPLE_INVALID)
        assert result3.confidence < 30, "无效输入置信度应较低"
        assert len(result3.warnings) > 0, "应有警告信息"
        print(f"  ✓ 通过 (置信度: {result3.confidence:.1f}%)")
        
        # 测试4: 空输入处理
        print("\n[测试4] 空输入处理")
        result4 = recognizer.recognize("")
        assert result4.confidence == 0.0, "空输入置信度应为0"
        print("  ✓ 通过")
        
        # 测试5: 批量处理
        print("\n[测试5] 批量处理")
        processor = BatchProcessor(recognizer)
        batch_results = processor.process_batch([cls.SAMPLE_INVOICE, cls.SAMPLE_INVOICE2, ""])
        assert len(batch_results) == 3, "批量处理数量错误"
        assert batch_results[0].invoice_number == "12345678", "批量处理结果1错误"
        assert batch_results[1].invoice_number == "87654321", "批量处理结果2错误"
        assert batch_results[2].confidence == 0.0, "批量处理空输入错误"
        print("  ✓ 通过")
        
        # 测试6: 输出格式化
        print("\n[测试6] 输出格式化")
        formatter = OutputFormatter()
        text_output = formatter.format_text(result1)
        assert "发票识别结果" in text_output, "文本输出格式错误"
        
        json_output = formatter.format_json(result1)
        json_data = json.loads(json_output)
        assert json_data["invoice_code"] == "144032100110", "JSON输出格式错误"
        
        compact_output = formatter.format_compact(result1)
        assert "置信度" in compact_output, "紧凑输出格式错误"
        print("  ✓ 通过")
        
        # 测试7: 错误处理
        print("\n[测试7] 错误处理")
        try:
            recognizer.recognize(None)  # type: ignore
            assert False, "None输入应抛出异常"
        except (TypeError, AttributeError):
            pass
        print("  ✓ 通过")
        
        # 测试8: 金额校验
        print("\n[测试8] 金额校验")
        result_with_amounts = recognizer.recognize(cls.SAMPLE_INVOICE)
        if result_with_amounts.total_amount > 0 and result_with_amounts.tax_amount > 0:
            assert result_with_amounts.total_amount > result_with_amounts.tax_amount, "总金额应大于税额"
        print("  ✓ 通过")
        
        print("\n" + "=" * 60)
        print("所有自检测试通过！")
        print("=" * 60)
        return True


# ============================================================
# 主程序
# ============================================================

def parse_arguments() -> argparse.Namespace:
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="laravel-ocr 发票识别 - 发票OCR与文档数据提取引擎",
        epilog="示例: python main.py --input '发票文本内容' --format json"
    )
    
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行离线自检"
    )
    
    parser.add_argument(
        "--input",
        action="append",
        help="输入文本内容（可多次指定进行批量处理）"
    )
    
    parser.add_argument(
        "--format",
        choices=["text", "json", "compact"],
        default="text",
        help="输出格式（默认: text）"
    )
    
    parser.add_argument(
        "--file",
        help="从文件读取输入"
    )
    
    return parser.parse_args()


def read_file(filepath: str) -> str:
    """
    读取文件内容
    
    Args:
        filepath: 文件路径
        
    Returns:
        str: 文件内容
    """
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        print(f"错误: 文件不存在: {filepath}")
        sys.exit(7)  # E007
    except Exception as e:
        print(f"错误: 读取文件失败: {e}")
        sys.exit(7)  # E007


def main() -> int:
    """主函数"""
    args = parse_arguments()
    
    # 自检模式
    if args.selftest:
        try:
            SelfTest.run()
            return 0
        except AssertionError as e:
            print(f"自检失败: {e}")
            return 10  # E010
        except Exception as e:
            print(f"自检异常: {e}")
            return 10  # E010
    
    # 收集输入
    inputs: List[str] = []
    
    if args.file:
        content = read_file(args.file)
        if content:
            inputs.append(content)
    
    if args.input:
        inputs.extend(args.input)
    
    # 检查输入
    if not inputs:
        print("错误: 请提供输入内容 (--input 或 --file)")
        print("E001: 输入为空")
        return 1
    
    # 创建识别器
    recognizer = InvoiceRecognizer()
    formatter = OutputFormatter()
    
    # 处理输入
    try:
        if len(inputs) == 1:
            # 单条处理
            result = recognizer.recognize(inputs[0])
            
            # 输出
            if args.format == "json":
                print(formatter.format_json(result))
            elif args.format == "compact":
                print(formatter.format_compact(result))
            else:
                print(formatter.format_text(result))
        else:
            # 批量处理
            processor = BatchProcessor(recognizer)
            results = processor.process_batch(inputs)
            
            if args.format == "json":
                output = [r.to_dict() for r in results]
                print(json.dumps(output, ensure_ascii=False, indent=2))
            elif args.format == "compact":
                for i, result in enumerate(results, 1):
                    print(f"[{i}] {formatter.format_compact(result)}")
            else:
                for i, result in enumerate(results, 1):
                    print(f"\n===== 第{i}条 =====")
                    print(formatter.format_text(result))
        
        return 0
        
    except Exception as e:
        print(f"处理失败: {e}")
        return 9  # E009


if __name__ == "__main__":
    sys.exit(main())
