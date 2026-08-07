#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
票据解析与字段抽取系统 - 独立实现
依据功能规格 clean-room 编写，仅使用标准库。

功能：
- 从文本/OCR 结果中抽取发票关键字段
- 输出结构化 JSON（含置信度标注）
- 支持批量处理
- 内置离线自检（--selftest）

错误码：
E001 参数错误
E002 文件不存在
E003 文件读取失败
E004 文件格式不支持
E005 内容为空
E006 解析失败
E007 输出写入失败
E008 批量处理中断
E009 自检失败
E010 未知错误
"""

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 常量定义
# ============================================================

# 字段名称映射（中英文）
FIELD_NAMES = {
    "invoice_no": "发票号码",
    "invoice_code": "发票代码",
    "date": "开票日期",
    "total_amount": "价税合计",
    "amount": "金额",
    "tax": "税额",
    "buyer_name": "购买方名称",
    "buyer_tax_id": "购买方税号",
    "seller_name": "销售方名称",
    "seller_tax_id": "销售方税号",
}

# 置信度阈值
HIGH_CONFIDENCE = 0.95
MEDIUM_CONFIDENCE = 0.80
LOW_CONFIDENCE = 0.60

# 最大处理页数
MAX_PAGES = 20

# 支持的文件扩展名
SUPPORTED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".txt"}


# ============================================================
# 核心数据结构
# ============================================================

class InvoiceData:
    """发票结构化数据容器"""
    
    def __init__(self) -> None:
        self.fields: Dict[str, str] = {}
        self.confidence: Dict[str, float] = {}
        self.source_file: str = ""
        self.processed_at: str = ""
        self.warnings: List[str] = []
    
    def set_field(self, name: str, value: str, confidence: float) -> None:
        """设置字段值及置信度"""
        if value and value.strip():
            self.fields[name] = value.strip()
            self.confidence[name] = max(0.0, min(1.0, confidence))
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "source_file": self.source_file,
            "processed_at": self.processed_at,
            "fields": self.fields,
            "confidence": self.confidence,
            "warnings": self.warnings,
        }
    
    def to_json(self) -> str:
        """转换为 JSON 字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


# ============================================================
# 解析引擎
# ============================================================

class InvoiceParser:
    """发票文本解析器"""
    
    def __init__(self) -> None:
        # 编译常用正则表达式
        self._patterns = {
            "invoice_no": re.compile(
                r"(?:发票号码|发票号|NO\.?|No\.?)\s*[:：]?\s*([0-9]{8,20})"
            ),
            "invoice_code": re.compile(
                r"(?:发票代码|代码)\s*[:：]?\s*([0-9]{10,12})"
            ),
            "date": re.compile(
                r"(?:开票日期|日期|Date)\s*[:：]?\s*(\d{4}[-/年]\d{1,2}[-/月]\d{1,2}日?)"
            ),
            "total_amount": re.compile(
                r"(?:价税合计|总计|合计)\s*[（(]?小写[)）]?\s*[:：]?\s*[¥￥]?\s*([0-9]+(?:\.\d{1,2})?)"
            ),
            "amount": re.compile(
                r"(?:金额|小写金额)\s*[:：]?\s*[¥￥]?\s*([0-9]+(?:\.\d{1,2})?)"
            ),
            "tax": re.compile(
                r"(?:税额|税率额)\s*[:：]?\s*[¥￥]?\s*([0-9]+(?:\.\d{1,2})?)"
            ),
            "buyer_name": re.compile(
                r"购买方\s*[:：]?\s*(?:名称\s*[:：]?\s*)?([^\s，,；;]{2,50})"
            ),
            "buyer_tax_id": re.compile(
                r"购买方.*?(?:纳税人识别号|税号|统一社会信用代码)\s*[:：]?\s*([0-9A-Za-z]{15,20})",
                re.DOTALL
            ),
            "seller_name": re.compile(
                r"销售方\s*[:：]?\s*(?:名称\s*[:：]?\s*)?([^\s，,；;]{2,50})"
            ),
            "seller_tax_id": re.compile(
                r"销售方.*?(?:纳税人识别号|税号|统一社会信用代码)\s*[:：]?\s*([0-9A-Za-z]{15,20})",
                re.DOTALL
            ),
        }
    
    def parse(self, text: str) -> Tuple[Dict[str, str], Dict[str, float]]:
        """
        解析文本，提取字段
        
        返回: (字段字典, 置信度字典)
        """
        if not text or not text.strip():
            raise ValueError("输入文本为空")
        
        fields: Dict[str, str] = {}
        confidence: Dict[str, float] = {}
        
        # 逐字段匹配
        for field_name, pattern in self._patterns.items():
            match = pattern.search(text)
            if match:
                value = match.group(1)
                if value:
                    fields[field_name] = value
                    # 根据匹配质量估算置信度
                    conf = self._estimate_confidence(field_name, value, text)
                    confidence[field_name] = conf
        
        # 交叉验证：价税合计 = 金额 + 税额
        self._cross_validate(fields, confidence, text)
        
        return fields, confidence
    
    def _estimate_confidence(self, field_name: str, value: str, context: str) -> float:
        """估算字段置信度"""
        base_conf = MEDIUM_CONFIDENCE
        
        # 字段特定规则
        if field_name == "invoice_no":
            base_conf = HIGH_CONFIDENCE if len(value) >= 8 else MEDIUM_CONFIDENCE
        elif field_name == "date":
            base_conf = HIGH_CONFIDENCE if re.match(r"^\d{4}[-/年]", value) else MEDIUM_CONFIDENCE
        elif field_name in ("total_amount", "amount", "tax"):
            base_conf = HIGH_CONFIDENCE if re.match(r"^\d+\.\d{2}$", value) else MEDIUM_CONFIDENCE
        elif field_name in ("buyer_name", "seller_name"):
            # 名称长度越长越可信
            base_conf = min(HIGH_CONFIDENCE, 0.70 + len(value) * 0.02)
        elif field_name in ("buyer_tax_id", "seller_tax_id"):
            base_conf = HIGH_CONFIDENCE if len(value) >= 18 else MEDIUM_CONFIDENCE
        
        return base_conf
    
    def _cross_validate(self, fields: Dict[str, str], confidence: Dict[str, float], 
                        context: str) -> None:
        """交叉验证字段一致性"""
        # 检查金额关系
        try:
            if "total_amount" in fields and "amount" in fields and "tax" in fields:
                total = float(fields["total_amount"])
                amount = float(fields["amount"])
                tax = float(fields["tax"])
                
                # 允许 ±0.01 的舍入误差
                if abs(total - (amount + tax)) <= 0.01:
                    # 增强置信度
                    for key in ("total_amount", "amount", "tax"):
                        if key in confidence:
                            confidence[key] = min(1.0, confidence[key] + 0.05)
        except (ValueError, TypeError):
            pass  # 数值转换失败则跳过验证


# ============================================================
# 文件处理
# ============================================================

class FileProcessor:
    """文件读取与处理"""
    
    def __init__(self, parser: Optional[InvoiceParser] = None) -> None:
        self.parser = parser or InvoiceParser()
    
    def process_file(self, file_path: str) -> InvoiceData:
        """处理单个文件"""
        path = Path(file_path)
        
        # 检查文件存在
        if not path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")
        
        # 检查扩展名
        ext = path.suffix.lower()
        if ext not in SUPPORTED_EXTENSIONS:
            raise ValueError(f"不支持的文件格式: {ext}")
        
        # 读取内容
        try:
            content = self._read_content(path)
        except Exception as e:
            raise IOError(f"文件读取失败: {e}") from e
        
        if not content.strip():
            raise ValueError("文件内容为空")
        
        # 解析
        try:
            fields, confidence = self.parser.parse(content)
        except Exception as e:
            raise RuntimeError(f"解析失败: {e}") from e
        
        # 构建结果
        result = InvoiceData()
        result.source_file = str(path)
        result.processed_at = datetime.now().isoformat()
        
        for key, value in fields.items():
            result.set_field(key, value, confidence.get(key, LOW_CONFIDENCE))
        
        # 添加警告
        if len(fields) < 4:
            result.warnings.append("提取字段少于4个，可能解析不完整")
        
        if not any(k in fields for k in ("buyer_name", "seller_name")):
            result.warnings.append("未识别到购买方或销售方信息")
        
        return result
    
    def process_batch(self, file_paths: List[str]) -> List[InvoiceData]:
        """批量处理文件"""
        results = []
        errors = []
        
        for file_path in file_paths:
            try:
                result = self.process_file(file_path)
                results.append(result)
            except Exception as e:
                errors.append({"file": file_path, "error": str(e)})
        
        if errors:
            # 将错误信息附加到结果中
            for error in errors:
                data = InvoiceData()
                data.source_file = error["file"]
                data.warnings.append(f"处理失败: {error['error']}")
                results.append(data)
        
        return results
    
    def _read_content(self, path: Path) -> str:
        """读取文件内容（文本文件直接读取，其他格式尝试提取文本）"""
        ext = path.suffix.lower()
        
        if ext == ".txt":
            # 直接读取文本文件
            for encoding in ("utf-8", "gbk", "gb2312", "big5"):
                try:
                    return path.read_text(encoding=encoding)
                except (UnicodeDecodeError, IOError):
                    continue
            # 尝试二进制读取
            return path.read_text(errors="ignore")
        else:
            # 对于 PDF/图片，实际生产环境会调用 OCR 库
            # 这里简化处理：尝试读取伴随的 .txt 文件
            txt_path = path.with_suffix(".txt")
            if txt_path.exists():
                return txt_path.read_text(encoding="utf-8", errors="ignore")
            
            # 无伴随文本文件时，返回空字符串
            # 实际生产环境应集成 OCR 引擎（如 Tesseract）
            raise ValueError(
                f"无法直接解析 {ext} 文件。请提供对应的 .txt 文本文件，"
                "或集成 OCR 引擎。"
            )


# ============================================================
# 输出处理
# ============================================================

def format_output(results: List[InvoiceData], output_format: str = "json") -> str:
    """格式化输出"""
    if output_format == "json":
        data = [r.to_dict() for r in results]
        return json.dumps(data, ensure_ascii=False, indent=2)
    elif output_format == "csv":
        return _to_csv(results)
    else:
        raise ValueError(f"不支持的输出格式: {output_format}")


def _to_csv(results: List[InvoiceData]) -> str:
    """转换为 CSV 格式"""
    if not results:
        return ""
    
    # 收集所有字段名
    all_fields = set()
    for result in results:
        all_fields.update(result.fields.keys())
    
    # 固定字段顺序
    ordered_fields = [
        "invoice_no", "invoice_code", "date", "total_amount",
        "amount", "tax", "buyer_name", "buyer_tax_id",
        "seller_name", "seller_tax_id"
    ]
    
    # 补充额外字段
    for field in all_fields:
        if field not in ordered_fields:
            ordered_fields.append(field)
    
    # 构建 CSV
    lines = []
    # 表头
    header = ["source_file"] + ordered_fields + ["warnings"]
    lines.append(",".join(header))
    
    # 数据行
    for result in results:
        row = [result.source_file]
        for field in ordered_fields:
            row.append(result.fields.get(field, ""))
        row.append("; ".join(result.warnings))
        # 转义 CSV
        escaped = []
        for cell in row:
            if "," in cell or '"' in cell or "\n" in cell:
                cell = '"' + cell.replace('"', '""') + '"'
            escaped.append(cell)
        lines.append(",".join(escaped))
    
    return "\n".join(lines)


def save_output(content: str, output_path: Optional[str]) -> None:
    """保存输出到文件"""
    if output_path:
        try:
            Path(output_path).write_text(content, encoding="utf-8")
        except IOError as e:
            raise IOError(f"输出写入失败: {e}") from e
    else:
        print(content)


# ============================================================
# 命令行入口
# ============================================================

def parse_args() -> argparse.Namespace:
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="票据解析与字段抽取系统",
        epilog="示例: python main.py invoice.txt -o result.json"
    )
    
    parser.add_argument(
        "files", nargs="*", help="输入文件路径（支持多个文件批量处理）"
    )
    parser.add_argument(
        "-o", "--output", help="输出文件路径（不指定则输出到控制台）"
    )
    parser.add_argument(
        "-f", "--format", choices=["json", "csv"], default="json",
        help="输出格式（默认: json）"
    )
    parser.add_argument(
        "--selftest", action="store_true",
        help="运行内置自检（不读取外部文件，不访问网络）"
    )
    
    return parser.parse_args()


def run_selftest() -> int:
    """运行内置自检"""
    print("开始自检...")
    
    # 内置测试数据
    test_cases = [
        {
            "name": "标准增值税发票",
            "text": """
增值税电子普通发票
发票代码：011001900111
发票号码：12345678
开票日期：2026年03月15日

购买方信息：
名称：示例科技有限公司
纳税人识别号：91110108MA01ABCDEF
地址电话：北京市海淀区示例路1号

货物或应税劳务名称：技术服务费
金额：¥1000.00
税率：6%
税额：¥60.00
价税合计（小写）：¥1060.00

销售方信息：
名称：服务提供商有限公司
纳税人识别号：91440300MA5ABCDEFX
""",
            "expected": {
                "invoice_no": "12345678",
                "invoice_code": "011001900111",
                "total_amount": "1060.00",
                "amount": "1000.00",
                "tax": "60.00",
            },
            "min_fields": 5,
            "min_avg_confidence": 0.70,
        },
        {
            "name": "简易收据",
            "text": """
收据
No. 20260315001
日期：2026-03-15
金额：¥500.00
收款单位：测试商店
""",
            "expected": {
                "invoice_no": "20260315001",
                "date": "2026-03-15",
            },
            "min_fields": 2,
            "min_avg_confidence": 0.60,
        },
        {
            "name": "空内容",
            "text": "",
            "expected": {},
            "min_fields": 0,
            "min_avg_confidence": 0.0,
            "expect_error": True,
        },
    ]
    
    parser = InvoiceParser()
    passed = 0
    
    for i, case in enumerate(test_cases, 1):
        print(f"\n测试用例 {i}: {case['name']}")
        
        try:
            # 解析
            fields, confidence = parser.parse(case["text"])
            
            # 检查是否期望错误
            if case.get("expect_error"):
                print(f"  [失败] 期望解析错误，但成功解析了 {len(fields)} 个字段")
                return 1
            
            # 检查字段数量
            if len(fields) < case["min_fields"]:
                print(f"  [失败] 字段数量不足: {len(fields)} < {case['min_fields']}")
                return 1
            
            # 检查期望字段
            for key, expected_value in case["expected"].items():
                if key not in fields:
                    print(f"  [失败] 缺少字段: {key}")
                    return 1
                actual = fields[key]
                # 宽松比较：允许字段值包含预期值（如金额可能带货币符号）
                if expected_value not in actual and actual not in expected_value:
                    print(f"  [失败] 字段值不匹配: {key} = '{actual}' (期望含 '{expected_value}')")
                    return 1
            
            # 检查平均置信度
            if confidence:
                avg_conf = sum(confidence.values()) / len(confidence)
                if avg_conf < case["min_avg_confidence"]:
                    print(f"  [失败] 平均置信度过低: {avg_conf:.2f} < {case['min_avg_confidence']}")
                    return 1
            
            print(f"  [通过] 解析成功，提取 {len(fields)} 个字段")
            passed += 1
            
        except ValueError as e:
            if case.get("expect_error"):
                print(f"  [通过] 正确拒绝空内容")
                passed += 1
            else:
                print(f"  [失败] 解析异常: {e}")
                return 1
        except Exception as e:
            print(f"  [失败] 未知异常: {e}")
            return 1
    
    # 测试输出格式化
    print("\n测试输出格式化...")
    try:
        data = InvoiceData()
        data.source_file = "test.txt"
        data.processed_at = "2026-01-01T00:00:00"
        data.set_field("invoice_no", "12345678", 0.95)
        data.set_field("total_amount", "1060.00", 0.90)
        
        json_out = format_output([data], "json")
        if "12345678" not in json_out:
            print("  [失败] JSON 输出缺少字段值")
            return 1
        
        csv_out = format_output([data], "csv")
        if "12345678" not in csv_out:
            print("  [失败] CSV 输出缺少字段值")
            return 1
        
        print("  [通过] JSON 和 CSV 输出正常")
        passed += 1
        
    except Exception as e:
        print(f"  [失败] 输出格式化异常: {e}")
        return 1
    
    # 测试批量处理
    print("\n测试批量处理...")
    try:
        processor = FileProcessor(parser)
        # 创建临时测试文件
        import tempfile
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", 
                                          encoding="utf-8", delete=False) as f:
            f.write("发票号码：99999999\n金额：¥100.00\n")
            temp_path = f.name
        
        try:
            results = processor.process_batch([temp_path, "/nonexistent/file.txt"])
            if len(results) != 2:
                print(f"  [失败] 批量处理应返回 2 个结果，实际 {len(results)}")
                return 1
            
            # 第一个应成功
            if not results[0].fields:
                print("  [失败] 第一个文件解析失败")
                return 1
            
            # 第二个应有错误警告
            if not any("失败" in w for w in results[1].warnings):
                print("  [失败] 第二个文件应包含错误信息")
                return 1
            
            print("  [通过] 批量处理正常")
            passed += 1
            
        finally:
            # 清理临时文件
            Path(temp_path).unlink(missing_ok=True)
            
    except Exception as e:
        print(f"  [失败] 批量处理异常: {e}")
        return 1
    
    print(f"\n自检完成: {passed} 项测试全部通过")
    return 0


def main() -> int:
    """主函数"""
    args = parse_args()
    
    # 自检模式
    if args.selftest:
        try:
            return run_selftest()
        except Exception as e:
            print(f"自检异常: {e}")
            return 9  # E009
    
    # 参数校验
    if not args.files:
        print("错误: 请指定输入文件路径（使用 --selftest 运行自检）")
        print("示例: python main.py invoice.txt -o result.json")
        return 1  # E001
    
    try:
        # 创建处理器
        processor = FileProcessor()
        
        # 批量处理
        results = processor.process_batch(args.files)
        
        # 格式化输出
        output = format_output(results, args.format)
        
        # 保存输出
        save_output(output, args.output)
        
        return 0
        
    except FileNotFoundError as e:
        print(f"错误 E002: {e}")
        return 2
    except ValueError as e:
        print(f"错误 E004: {e}")
        return 4
    except IOError as e:
        print(f"错误 E007: {e}")
        return 7
    except Exception as e:
        print(f"错误 E010: 未知错误 - {e}")
        return 10


if __name__ == "__main__":
    sys.exit(main())
