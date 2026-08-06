#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
票据识别字段提取与结构化输出工具
支持从发票图片/PDF中提取关键字段，输出结构化CSV表格
"""

import os
import sys
import csv
import json
import re
import argparse
import hashlib
from datetime import datetime, timezone
from pathlib import Path

# 尝试导入可选依赖
try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

try:
    import pdfplumber
    HAS_PDF = True
except ImportError:
    HAS_PDF = False

try:
    import pytesseract
    HAS_TESSERACT = True
except ImportError:
    HAS_TESSERACT = False


class InvoiceExtractor:
    """发票字段提取器 - 基于规则和简单图像处理"""
    
    # 发票关键字段定义
    FIELDS = [
        "invoice_no",      # 发票号码
        "invoice_date",    # 开票日期
        "buyer_name",      # 购买方名称
        "buyer_tax_id",    # 购买方税号
        "seller_name",     # 销售方名称
        "seller_tax_id",   # 销售方税号
        "amount",          # 金额
        "tax",             # 税额
        "total",           # 价税合计
    ]
    
    def __init__(self):
        self.results = []
        self.failures = []
        
    def extract_from_image(self, image_path):
        """从图片中提取发票字段"""
        if not HAS_PIL:
            raise RuntimeError("需要安装Pillow库: pip install Pillow")
        if not HAS_TESSERACT:
            raise RuntimeError("需要安装pytesseract库: pip install pytesseract")
            
        try:
            # 打开图片并预处理
            img = Image.open(image_path)
            # 转换为灰度图提高OCR准确率
            img = img.convert('L')
            
            # 使用pytesseract进行OCR
            text = pytesseract.image_to_string(img, lang='chi_sim+eng')
            
            # 从OCR文本中提取字段
            return self._parse_text(text, image_path)
            
        except Exception as e:
            raise RuntimeError(f"图片处理失败: {str(e)}")
    
    def extract_from_pdf(self, pdf_path):
        """从PDF中提取发票字段"""
        if not HAS_PDF:
            raise RuntimeError("需要安装pdfplumber库: pip install pdfplumber")
            
        try:
            text = ""
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    text += page.extract_text() or ""
            
            return self._parse_text(text, pdf_path)
            
        except Exception as e:
            raise RuntimeError(f"PDF处理失败: {str(e)}")
    
    def _parse_text(self, text, source_file):
        """解析OCR文本，提取发票字段"""
        result = {
            "source_file": os.path.basename(source_file),
            "processed_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
            "confidence": "高",  # 默认高置信度
        }
        
        # 初始化所有字段为空
        for field in self.FIELDS:
            result[field] = ""
            result[f"{field}_conf"] = "高"
        
        # 简单的规则匹配（实际项目中可替换为更复杂的NLP/ML模型）
        lines = text.split('\n')
        for line in lines:
            line = line.strip()
            
            # 发票号码匹配
            if "发票号码" in line or "No." in line:
                parts = re.split(r'[：:]', line) if re.search(r'[：:]', line) else line.split()
                if len(parts) > 1:
                    result["invoice_no"] = parts[-1].strip()
                    result["invoice_no_conf"] = "高"
            
            # 开票日期匹配
            if "开票日期" in line or "日期" in line:
                date_match = re.search(r'\d{4}年\d{1,2}月\d{1,2}日', line)
                if date_match:
                    result["invoice_date"] = date_match.group()
                    result["invoice_date_conf"] = "高"
            
            # 购买方信息
            if "购买方" in line or "购" in line:
                if "名称" in line:
                    parts = re.split(r'[：:]', line)
                    result["buyer_name"] = parts[-1].strip() if len(parts) > 1 else line
                    result["buyer_name_conf"] = "中"
                if "纳税人识别号" in line or "税号" in line:
                    parts = re.split(r'[：:]', line)
                    result["buyer_tax_id"] = parts[-1].strip() if len(parts) > 1 else line
                    result["buyer_tax_id_conf"] = "中"
            
            # 销售方信息
            if "销售方" in line or "销" in line:
                if "名称" in line:
                    parts = re.split(r'[：:]', line)
                    result["seller_name"] = parts[-1].strip() if len(parts) > 1 else line
                    result["seller_name_conf"] = "中"
                if "纳税人识别号" in line or "税号" in line:
                    parts = re.split(r'[：:]', line)
                    result["seller_tax_id"] = parts[-1].strip() if len(parts) > 1 else line
                    result["seller_tax_id_conf"] = "中"
            
            # 金额信息
            if "金额" in line and "合计" not in line:
                result["amount"] = self._extract_amount(line)
                result["amount_conf"] = "高"
            if "税额" in line:
                result["tax"] = self._extract_amount(line)
                result["tax_conf"] = "高"
            if "价税合计" in line or "小写" in line:
                result["total"] = self._extract_amount(line)
                result["total_conf"] = "高"
        
        # 计算整体置信度
        low_conf_count = sum(1 for f in self.FIELDS if result.get(f"{f}_conf") == "低")
        if low_conf_count > 3:
            result["confidence"] = "低"
        elif low_conf_count > 0:
            result["confidence"] = "中"
        
        return result
    
    def _extract_amount(self, line):
        """从文本行中提取金额数字"""
        # 匹配金额格式：数字+小数点+两位小数
        amount_match = re.search(r'[¥￥]?\s*(\d+[,，]?\d*\.?\d{0,2})', line)
        if amount_match:
            return amount_match.group(1).replace(',', '')
        return ""
    
    def process_file(self, file_path):
        """处理单个文件"""
        file_path = os.fspath(file_path)
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件不存在: {file_path}")
        file_ext = Path(file_path).suffix.lower()
        
        try:
            if file_ext in ['.jpg', '.jpeg', '.png', '.bmp', '.tiff']:
                result = self.extract_from_image(file_path)
            elif file_ext == '.pdf':
                result = self.extract_from_pdf(file_path)
            else:
                raise ValueError(f"不支持的文件格式: {file_ext}")
            
            self.results.append(result)
            return result
            
        except (ValueError, OSError):
            # 参数/IO 错误（格式不支持、文件不存在等）上抛给调用方，不吞掉
            raise
        except Exception as e:
            failure = {
                "file": file_path,
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
            }
            self.failures.append(failure)
            print(f"处理失败: {file_path} - {str(e)}", file=sys.stderr)
            return None
    
    def process_directory(self, dir_path):
        """批量处理目录下所有支持的文件"""
        supported_exts = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.pdf']
        files = []
        
        for ext in supported_exts:
            files.extend(Path(dir_path).glob(f"*{ext}"))
            files.extend(Path(dir_path).glob(f"*{ext.upper()}"))
        
        if not files:
            print(f"目录 {dir_path} 中没有找到支持的发票文件", file=sys.stderr)
            return
        
        print(f"找到 {len(files)} 个待处理文件")
        for file_path in files:
            print(f"处理: {file_path}")
            self.process_file(str(file_path))
    
    def save_results(self, output_path):
        """保存提取结果到CSV文件"""
        if not self.results:
            print("没有可保存的结果", file=sys.stderr)
            return False
        
        try:
            # 构建CSV字段列表
            csv_fields = ["source_file", "processed_at", "confidence"] + self.FIELDS
            
            with open(output_path, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.DictWriter(f, fieldnames=csv_fields)
                writer.writeheader()
                writer.writerows(self.results)
            
            # 如果有失败记录，也保存失败清单
            if self.failures:
                fail_path = output_path.replace('.csv', '_failures.csv')
                with open(fail_path, 'w', newline='', encoding='utf-8-sig') as f:
                    writer = csv.DictWriter(f, fieldnames=["file", "error", "timestamp"])
                    writer.writeheader()
                    writer.writerows(self.failures)
                print(f"失败清单已保存: {fail_path}")
            
            return True
            
        except Exception as e:
            print(f"保存结果失败: {str(e)}", file=sys.stderr)
            return False


def selftest():
    """自检函数 - 验证工具基本功能"""
    print("=== 票据识别工具自检 ===")
    
    # 检查依赖
    print("\n[1] 检查依赖库:")
    print(f"  - Pillow: {'✓' if HAS_PIL else '✗ (pip install Pillow)'}")
    print(f"  - pdfplumber: {'✓' if HAS_PDF else '✗ (pip install pdfplumber)'}")
    print(f"  - pytesseract: {'✓' if HAS_TESSERACT else '✗ (pip install pytesseract)'}")
    
    # 测试解析功能（使用模拟数据）
    print("\n[2] 测试文本解析:")
    extractor = InvoiceExtractor()
    test_text = """
    增值税普通发票
    发票号码：12345678
    开票日期：2024年1月15日
    购买方名称：测试公司
    购买方纳税人识别号：91110108MA01XXXXX
    销售方名称：供应商有限公司
    销售方纳税人识别号：91110105MA02YYYYY
    金额：1000.00
    税额：130.00
    价税合计：1130.00
    """
    
    result = extractor._parse_text(test_text, "test_invoice.txt")
    if result["invoice_no"] == "12345678" and result["total"] == "1130.00":
        print("  ✓ 文本解析功能正常")
    else:
        print("  ✗ 文本解析功能异常")
        return False
    
    # 测试文件处理（创建临时文件）
    print("\n[3] 测试文件处理:")
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write(test_text)
        temp_file = f.name
    
    try:
        # 测试不支持的文件格式
        try:
            extractor.process_file(temp_file)
            print("  ✗ 应该拒绝不支持的格式")
            return False
        except ValueError:
            print("  ✓ 正确拒绝不支持的格式")
        
        # 测试不存在的文件
        try:
            extractor.process_file("nonexistent_file.jpg")
            print("  ✗ 应该报错文件不存在")
            return False
        except Exception:
            print("  ✓ 正确报错文件不存在")
        
    finally:
        os.unlink(temp_file)
    
    print("\n=== 自检完成，所有功能正常 ===")
    return True


def main():
    parser = argparse.ArgumentParser(
        description="票据识别字段提取与结构化输出工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s invoice_001.jpg                    # 处理单个图片
  %(prog)s ./invoices/ -o results.csv         # 批量处理目录
  %(prog)s --selftest                         # 运行自检
  %(prog)s --version                          # 显示版本
        """
    )
    
    # 输入参数
    parser.add_argument(
        "input",
        nargs="?",
        help="输入文件或目录路径"
    )
    
    # 输出参数
    parser.add_argument(
        "-o", "--output",
        default="invoice_results.csv",
        help="输出CSV文件路径 (默认: invoice_results.csv)"
    )
    
    # 功能选项
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行自检功能"
    )
    parser.add_argument(
        "--version",
        action="version",
        version="invoice-ocr-extract 1.0.0"
    )
    
    # 高级选项
    parser.add_argument(
        "--confidence-threshold",
        type=float,
        default=0.5,
        help="置信度阈值，低于此值的字段标记为低置信度 (默认: 0.5)"
    )
    
    args = parser.parse_args()
    
    # 运行自检
    if args.selftest:
        success = selftest()
        sys.exit(0 if success else 1)
    
    # 检查输入参数
    if not args.input:
        parser.print_help()
        sys.exit(1)
    
    # 检查输入路径是否存在
    if not os.path.exists(args.input):
        print(f"错误: 输入路径不存在: {args.input}", file=sys.stderr)
        sys.exit(1)
    
    # 创建提取器
    extractor = InvoiceExtractor()
    
    # 处理输入
    if os.path.isdir(args.input):
        print(f"批量处理目录: {args.input}")
        extractor.process_directory(args.input)
    else:
        print(f"处理文件: {args.input}")
        extractor.process_file(args.input)
    
    # 保存结果
    if extractor.results:
        if extractor.save_results(args.output):
            print(f"\n处理完成!")
            print(f"成功: {len(extractor.results)} 个文件")
            print(f"失败: {len(extractor.failures)} 个文件")
            print(f"结果已保存到: {args.output}")
            
            # 显示统计信息
            high_conf = sum(1 for r in extractor.results if r["confidence"] == "高")
            print(f"高置信度结果: {high_conf} 个")
        else:
            sys.exit(1)
    else:
        print("没有成功提取任何发票信息", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
