#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
报销单据整理与核验工具
功能：发票逻辑校验、金额核对、费用归类、明细表生成
"""

import os
import re
import sys
import csv
import json
import shutil
import argparse
import datetime
from pathlib import Path

try:
    from openpyxl import Workbook, load_workbook
    HAS_OPENPYXL = True
except ImportError:
    HAS_OPENPYXL = False

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


# ==================== 核心业务逻辑 ====================

class InvoiceValidator:
    """发票逻辑校验器（非官方查验，仅格式与逻辑校验）"""
    
    @staticmethod
    def validate_code(invoice_code: str) -> bool:
        """校验发票代码：10位或12位数字"""
        return bool(re.match(r'^\d{10}$|^\d{12}$', invoice_code))
    
    @staticmethod
    def validate_number(invoice_number: str) -> bool:
        """校验发票号码：8位数字"""
        return bool(re.match(r'^\d{8}$', invoice_number))
    
    @staticmethod
    def validate_amount(amount: float) -> bool:
        """校验金额：正数且不超过100万"""
        return 0 < amount <= 1000000
    
    @staticmethod
    def validate_date(date_str: str) -> bool:
        """校验日期格式：YYYY-MM-DD"""
        try:
            datetime.datetime.strptime(date_str, '%Y-%m-%d')
            return True
        except ValueError:
            return False
    
    @staticmethod
    def checksum_verify(invoice_code: str, invoice_number: str) -> bool:
        """简单校验码验证（模拟，非官方）"""
        if not (InvoiceValidator.validate_code(invoice_code) and 
                InvoiceValidator.validate_number(invoice_number)):
            return False
        # 取发票代码后4位与号码后4位做简单运算
        code_tail = int(invoice_code[-4:])
        num_tail = int(invoice_number[-4:])
        return (code_tail + num_tail) % 7 == 0


class ExpenseCategorizer:
    """费用归类器"""
    
    CATEGORY_KEYWORDS = {
        '餐饮': ['餐', '饭', '食', '宴', '咖啡', '茶'],
        '交通': ['车', '出租', '地铁', '公交', '高铁', '飞机', '加油', '停车'],
        '住宿': ['酒店', '宾馆', '住宿', '房费'],
        '办公': ['办公', '文具', '打印', '耗材', '电脑', '软件'],
        '通讯': ['话费', '流量', '宽带', '通讯'],
        '差旅': ['差旅', '出差', '机票', '火车票'],
        '招待': ['招待', '客户', '送礼', '礼品'],
        '其他': []
    }
    
    @classmethod
    def categorize(cls, description: str) -> str:
        """根据描述关键词归类"""
        if not description:
            return '其他'
        for category, keywords in cls.CATEGORY_KEYWORDS.items():
            for kw in keywords:
                if kw in description:
                    return category
        return '其他'


class ExpenseProcessor:
    """报销单据处理器"""
    
    def __init__(self, input_dir: str, output_dir: str, declared_amount: float = None):
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.declared_amount = declared_amount
        self.invoices = []
        self.errors = []
    
    def parse_filename(self, filename: str) -> dict:
        """从文件名解析信息，格式：日期_类型_金额_备注"""
        pattern = r'^(\d{8})_([^_]+)_([\d.]+)_(.+)$'
        match = re.match(pattern, filename)
        if not match:
            return None
        
        date_str, category, amount_str, note = match.groups()
        try:
            amount = float(amount_str)
            date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"
        except ValueError:
            return None
        
        return {
            'date': date,
            'category': category,
            'amount': amount,
            'note': note,
            'filename': filename
        }
    
    def extract_invoice_info(self, filepath: Path) -> dict:
        """从文件中提取发票信息（模拟OCR/文本提取）"""
        info = self.parse_filename(filepath.stem)
        if not info:
            return None
        
        # 模拟从文件中读取发票代码和号码
        # 实际应用中这里应该调用OCR或PDF解析
        fake_code = f"031001900111{str(hash(filepath.stem))[-4:]}"
        fake_number = f"{abs(hash(filepath.name)) % 100000000:08d}"
        
        info['invoice_code'] = fake_code
        info['invoice_number'] = fake_number
        info['valid'] = (
            InvoiceValidator.validate_code(fake_code) and
            InvoiceValidator.validate_number(fake_number) and
            InvoiceValidator.validate_amount(info['amount']) and
            InvoiceValidator.validate_date(info['date'])
        )
        info['checksum'] = InvoiceValidator.checksum_verify(fake_code, fake_number)
        return info
    
    def process_directory(self) -> list:
        """处理目录下所有文件"""
        if not self.input_dir.exists():
            raise FileNotFoundError(f"输入目录不存在: {self.input_dir}")
        
        # 创建备份
        backup_dir = self.output_dir / f"backup_{datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d_%H%M%S')}"
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        supported_ext = {'.pdf', '.jpg', '.jpeg', '.png', '.txt', '.csv'}
        
        for filepath in self.input_dir.iterdir():
            if filepath.suffix.lower() not in supported_ext:
                continue
            
            # 备份文件
            shutil.copy2(filepath, backup_dir / filepath.name)
            
            # 提取信息
            info = self.extract_invoice_info(filepath)
            if info:
                self.invoices.append(info)
            else:
                self.errors.append(f"无法解析文件: {filepath.name}")
        
        return self.invoices
    
    def verify_amounts(self) -> list:
        """核对金额"""
        total = sum(inv['amount'] for inv in self.invoices)
        discrepancies = []
        
        if self.declared_amount is not None:
            diff = abs(total - self.declared_amount)
            if diff > 0.01:  # 1分钱误差
                discrepancies.append({
                    'type': '金额差异',
                    'expected': self.declared_amount,
                    'actual': total,
                    'difference': round(diff, 2)
                })
        
        return discrepancies
    
    def generate_report(self, format_type: str = 'csv') -> Path:
        """生成明细表"""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d_%H%M%S')
        
        if format_type == 'csv':
            output_file = self.output_dir / f"报销明细_{timestamp}.csv"
            self._write_csv(output_file)
        elif format_type == 'excel' and HAS_OPENPYXL:
            output_file = self.output_dir / f"报销明细_{timestamp}.xlsx"
            self._write_excel(output_file)
        elif format_type == 'markdown':
            output_file = self.output_dir / f"报销明细_{timestamp}.md"
            self._write_markdown(output_file)
        else:
            raise ValueError(f"不支持的输出格式: {format_type}")
        
        return output_file
    
    def _write_csv(self, output_file: Path):
        """写入CSV文件"""
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['日期', '类型', '金额', '备注', '发票代码', '发票号码', '校验状态'])
            for inv in self.invoices:
                writer.writerow([
                    inv['date'], inv['category'], inv['amount'], inv['note'],
                    inv['invoice_code'], inv['invoice_number'],
                    '通过' if inv['valid'] and inv['checksum'] else '异常'
                ])
    
    def _write_excel(self, output_file: Path):
        """写入Excel文件"""
        wb = Workbook()
        ws = wb.active
        ws.title = "报销明细"
        
        headers = ['日期', '类型', '金额', '备注', '发票代码', '发票号码', '校验状态']
        ws.append(headers)
        
        for inv in self.invoices:
            ws.append([
                inv['date'], inv['category'], inv['amount'], inv['note'],
                inv['invoice_code'], inv['invoice_number'],
                '通过' if inv['valid'] and inv['checksum'] else '异常'
            ])
        
        # 添加汇总
        ws.append([])
        ws.append(['合计', '', sum(inv['amount'] for inv in self.invoices)])
        
        wb.save(output_file)
    
    def _write_markdown(self, output_file: Path):
        """写入Markdown文件"""
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("# 报销明细表\n\n")
            f.write("| 日期 | 类型 | 金额 | 备注 | 发票代码 | 发票号码 | 校验 |\n")
            f.write("|------|------|------|------|----------|----------|------|\n")
            for inv in self.invoices:
                status = '✅' if inv['valid'] and inv['checksum'] else '❌'
                f.write(f"| {inv['date']} | {inv['category']} | {inv['amount']} | "
                       f"{inv['note']} | {inv['invoice_code']} | {inv['invoice_number']} | {status} |\n")
            
            total = sum(inv['amount'] for inv in self.invoices)
            f.write(f"\n**合计金额：{total:.2f} 元**\n")


# ==================== CLI 接口 ====================

def main():
    parser = argparse.ArgumentParser(
        description='报销单据整理与核验工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例:
  python run.py --input ./invoices --output ./result
  python run.py --input ./invoices --output ./result --declared 3500.00
  python run.py --input ./invoices --output ./result --format excel
  python run.py --selftest
        '''
    )
    
    parser.add_argument('--input', '-i', default=None, help='输入目录（包含发票文件）')
    parser.add_argument('--output', '-o', default=None, help='输出目录')
    parser.add_argument('--declared', '-d', type=float, help='申报金额（用于核对）')
    parser.add_argument('--format', '-f', choices=['csv', 'excel', 'markdown'], 
                       default='csv', help='输出格式（默认csv）')
    parser.add_argument('--selftest', action='store_true', help='运行自检')
    
    # 自检模式（优先，无需 --input/--output）
    if '--selftest' in sys.argv:
        selftest()
        return

    args = parser.parse_args()
    if args.selftest:
        selftest()
        return
    if not args.input or not args.output:
        parser.error('--input/-i 与 --output/-o 必填（示例: --input ./invoices --output ./result）')
    
    try:
        # 检查依赖
        if args.format == 'excel' and not HAS_OPENPYXL:
            print("错误: 需要安装 openpyxl 库来生成Excel文件")
            print("请运行: pip install openpyxl")
            exit(1)
        
        # 处理报销单据
        processor = ExpenseProcessor(args.input, args.output, args.declared)
        invoices = processor.process_directory()
        
        if not invoices:
            print(f"警告: 在 {args.input} 中没有找到可处理的文件")
            print("文件名格式应为: 日期_类型_金额_备注 (如 20250115_餐饮_350_客户午餐)")
            exit(1)
        
        # 金额核对
        discrepancies = processor.verify_amounts()
        
        # 生成报告
        output_file = processor.generate_report(args.format)
        
        # 输出结果
        print(f"✅ 处理完成！共处理 {len(invoices)} 张单据")
        print(f"📄 明细表已生成: {output_file}")
        
        total = sum(inv['amount'] for inv in invoices)
        print(f"💰 总金额: {total:.2f} 元")
        
        if discrepancies:
            print("\n⚠️ 金额核对发现差异:")
            for d in discrepancies:
                print(f"  - {d['type']}: 申报 {d['expected']} 元, 实际 {d['actual']} 元, 差异 {d['difference']} 元")
        else:
            print("✅ 金额核对通过")
        
        # 校验状态统计
        valid_count = sum(1 for inv in invoices if inv['valid'] and inv['checksum'])
        print(f"🔍 发票校验: {valid_count}/{len(invoices)} 通过")
        
        if processor.errors:
            print(f"\n⚠️ 有 {len(processor.errors)} 个文件处理失败:")
            for err in processor.errors:
                print(f"  - {err}")
        
    except FileNotFoundError as e:
        print(f"错误: {e}")
        exit(1)
    except PermissionError as e:
        print(f"错误: 权限不足 - {e}")
        exit(1)
    except Exception as e:
        print(f"错误: {e}")
        exit(1)


def selftest():
    """自检函数：验证核心功能"""
    print("🔧 运行自检...")
    
    # 1. 测试发票校验
    print("\n1. 测试发票校验器...")
    assert InvoiceValidator.validate_code("031001900111") == True
    assert InvoiceValidator.validate_code("12345") == False
    assert InvoiceValidator.validate_number("12345678") == True
    assert InvoiceValidator.validate_number("123") == False
    assert InvoiceValidator.validate_amount(100.50) == True
    assert InvoiceValidator.validate_amount(-10) == False
    assert InvoiceValidator.validate_date("2025-01-15") == True
    assert InvoiceValidator.validate_date("2025/01/15") == False
    print("   ✅ 发票校验器正常")
    
    # 2. 测试费用归类
    print("\n2. 测试费用归类器...")
    assert ExpenseCategorizer.categorize("客户午餐") == "餐饮"
    assert ExpenseCategorizer.categorize("出租车费") == "交通"
    assert ExpenseCategorizer.categorize("酒店住宿") == "住宿"
    assert ExpenseCategorizer.categorize("打印耗材") == "办公"
    assert ExpenseCategorizer.categorize("话费充值") == "通讯"
    assert ExpenseCategorizer.categorize("机票") == "差旅"
    assert ExpenseCategorizer.categorize("客户礼品") == "招待"
    assert ExpenseCategorizer.categorize("其他费用") == "其他"
    print("   ✅ 费用归类器正常")
    
    # 3. 测试文件名解析
    print("\n3. 测试文件名解析...")
    processor = ExpenseProcessor("./test_in", "./test_out")
    info = processor.parse_filename("20250115_餐饮_350_客户午餐")
    assert info is not None
    assert info['date'] == "2025-01-15"
    assert info['category'] == "餐饮"
    assert info['amount'] == 350.0
    assert info['note'] == "客户午餐"
    
    bad_info = processor.parse_filename("随便写的文件名")
    assert bad_info is None
    print("   ✅ 文件名解析正常")
    
    # 4. 测试完整流程（使用临时目录）
    print("\n4. 测试完整处理流程...")
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        input_dir = tmp / "input"
        output_dir = tmp / "output"
        input_dir.mkdir()
        
        # 创建测试文件
        test_files = [
            "20250115_餐饮_350_客户午餐.txt",
            "20250116_交通_120_出租车.txt",
            "20250117_办公_89.5_打印耗材.txt"
        ]
        for f in test_files:
            (input_dir / f).write_text("测试内容", encoding='utf-8')
        
        # 处理
        processor = ExpenseProcessor(str(input_dir), str(output_dir), declared_amount=559.5)
        invoices = processor.process_directory()
        assert len(invoices) == 3
        
        discrepancies = processor.verify_amounts()
        assert len(discrepancies) == 0  # 350 + 120 + 89.5 = 559.5
        
        # 生成CSV
        csv_file = processor.generate_report('csv')
        assert csv_file.exists()
        
        # 生成Markdown
        md_file = processor.generate_report('markdown')
        assert md_file.exists()
        
        # 测试金额不匹配
        processor2 = ExpenseProcessor(str(input_dir), str(output_dir), declared_amount=500)
        discrepancies2 = processor2.verify_amounts()
        assert len(discrepancies2) == 1
        
        print("   ✅ 完整流程正常")
    
    print("\n🎉 所有自检通过！")


if __name__ == "__main__":
    main()
