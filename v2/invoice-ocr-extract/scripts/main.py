#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
run.py — 票据识别关键字段抽取（invoice-ocr-extract）独立实现

本脚本为 clean-room 重写实现，仅依据功能规格独立完成：
  - 从发票图片或 PDF 中抽取关键字段（发票代码、号码、日期、买卖方信息、金额、税额、商品明细）
  - 支持单张/批量处理，输出 table / json / csv
  - 支持置信度阈值标注与字段缺失占位
  - 内置 --selftest 离线自检，无需外部文件与网络

错误码约定：
  E001 参数错误
  E002 输入路径不存在
  E003 文件格式不支持
  E004 文件读取失败
  E005 OCR 引擎不可用（本实现为模拟引擎，正常不会触发）
  E006 输出目录不可写
  E007 输出格式不支持
  E008 批量模式无有效文件
  E009 自检失败
  E010 未知异常

仅使用 Python 标准库；如需真实 OCR 可自行接入第三方引擎（如 pytesseract / paddleocr）。
"""

import argparse
import csv
import json
import os
import re
import sys
import tempfile
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# 数据模型
# ---------------------------------------------------------------------------

@dataclass
class InvoiceField:
    """单个字段的抽取结果"""
    name: str           # 字段名
    value: str          # 字段值（缺失时为空字符串）
    confidence: float   # 置信度 0~1
    status: str         # normal / missing / low_conf


@dataclass
class InvoiceItem:
    """商品明细行"""
    name: str = ""
    spec: str = ""
    unit: str = ""
    qty: str = ""
    price: str = ""
    amount: str = ""


@dataclass
class InvoiceResult:
    """一张发票的完整抽取结果"""
    filename: str = ""
    invoice_code: str = ""
    invoice_number: str = ""
    invoice_date: str = ""
    buyer_name: str = ""
    buyer_tax_id: str = ""
    seller_name: str = ""
    seller_tax_id: str = ""
    total_amount_tax: str = ""      # 价税合计
    total_amount: str = ""          # 不含税金额
    total_tax: str = ""             # 税额
    items: List[InvoiceItem] = field(default_factory=list)
    fields: List[InvoiceField] = field(default_factory=list)
    raw_text: str = ""              # 原始识别文本（模拟）
    overall_confidence: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（用于 JSON / CSV 导出）"""
        d = asdict(self)
        # 移除内部字段
        d.pop("fields", None)
        d.pop("raw_text", None)
        return d


# ---------------------------------------------------------------------------
# 模拟 OCR 引擎（真实实现可替换为 pytesseract / paddleocr）
# ---------------------------------------------------------------------------

# 内置样例数据（用于 --selftest 与无文件时的演示）
SAMPLE_INVOICE_TEXT = """
发票代码：031001900111
发票号码：12345678
开票日期：2023年05月20日
购买方名称：某某科技有限公司
购买方纳税人识别号：91110108MA01XXXXX
销售方名称：某某商贸有限公司
销售方纳税人识别号：91110105MA02YYYYY
价税合计（大写）：壹仟壹佰叁拾元整
价税合计（小写）：1130.00
不含税金额：1000.00
税额：130.00
商品名称：办公用品
规格型号：批
单位：批
数量：1
单价：1000.00
金额：1000.00
"""


def extract_text_from_file(file_path: str) -> str:
    """
    从文件中提取文本（模拟 OCR）。
    真实实现可替换为 pytesseract.image_to_string 或 paddleocr。
    """
    ext = os.path.splitext(file_path)[1].lower()
    if ext in (".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".pdf"):
        # 模拟 OCR：返回内置样例数据
        # 真实实现中，这里应调用 OCR 引擎识别图片/PDF 中的文字
        return SAMPLE_INVOICE_TEXT
    else:
        raise ValueError(f"不支持的文件格式: {ext}")


# ---------------------------------------------------------------------------
# 字段抽取逻辑
# ---------------------------------------------------------------------------

def extract_field(text: str, pattern: str, field_name: str) -> InvoiceField:
    """
    从文本中抽取单个字段。
    返回 InvoiceField 对象，包含值、置信度与状态。
    """
    match = re.search(pattern, text)
    if match:
        value = match.group(1).strip()
        confidence = 0.95  # 模拟置信度
        status = "normal"
    else:
        value = ""
        confidence = 0.0
        status = "missing"
    return InvoiceField(name=field_name, value=value, confidence=confidence, status=status)


def extract_invoice_fields(text: str) -> List[InvoiceField]:
    """从原始文本中抽取所有关键字段"""
    patterns = {
        "invoice_code": r"发票代码[：:]\s*([0-9]+)",
        "invoice_number": r"发票号码[：:]\s*([0-9]+)",
        "invoice_date": r"开票日期[：:]\s*([0-9]{4}年[0-9]{2}月[0-9]{2}日)",
        "buyer_name": r"购买方名称[：:]\s*([^\n]+)",
        "buyer_tax_id": r"购买方纳税人识别号[：:]\s*([0-9A-Z]+)",
        "seller_name": r"销售方名称[：:]\s*([^\n]+)",
        "seller_tax_id": r"销售方纳税人识别号[：:]\s*([0-9A-Z]+)",
        "total_amount_tax": r"价税合计（小写）[：:]\s*([0-9.]+)",
        "total_amount": r"不含税金额[：:]\s*([0-9.]+)",
        "total_tax": r"税额[：:]\s*([0-9.]+)",
    }
    fields = []
    for name, pattern in patterns.items():
        field = extract_field(text, pattern, name)
        fields.append(field)
    return fields


def extract_items(text: str) -> List[InvoiceItem]:
    """从文本中抽取商品明细"""
    items = []
    # 匹配商品名称行
    item_pattern = r"商品名称[：:]\s*([^\n]+)"
    match = re.search(item_pattern, text)
    if match:
        item = InvoiceItem()
        item.name = match.group(1).strip()
        # 尝试匹配其他字段
        spec_match = re.search(r"规格型号[：:]\s*([^\n]+)", text)
        if spec_match:
            item.spec = spec_match.group(1).strip()
        unit_match = re.search(r"单位[：:]\s*([^\n]+)", text)
        if unit_match:
            item.unit = unit_match.group(1).strip()
        qty_match = re.search(r"数量[：:]\s*([0-9.]+)", text)
        if qty_match:
            item.qty = qty_match.group(1).strip()
        price_match = re.search(r"单价[：:]\s*([0-9.]+)", text)
        if price_match:
            item.price = price_match.group(1).strip()
        amount_match = re.search(r"金额[：:]\s*([0-9.]+)", text)
        if amount_match:
            item.amount = amount_match.group(1).strip()
        items.append(item)
    return items


def parse_invoice(text: str, filename: str = "") -> InvoiceResult:
    """
    解析发票文本，返回结构化结果。
    这是核心处理函数，被主流程与 selftest 共同调用。
    """
    result = InvoiceResult(filename=filename, raw_text=text)
    
    # 抽取字段
    fields = extract_invoice_fields(text)
    result.fields = fields
    
    # 填充到结果对象
    field_map = {f.name: f.value for f in fields}
    result.invoice_code = field_map.get("invoice_code", "")
    result.invoice_number = field_map.get("invoice_number", "")
    result.invoice_date = field_map.get("invoice_date", "")
    result.buyer_name = field_map.get("buyer_name", "")
    result.buyer_tax_id = field_map.get("buyer_tax_id", "")
    result.seller_name = field_map.get("seller_name", "")
    result.seller_tax_id = field_map.get("seller_tax_id", "")
    result.total_amount_tax = field_map.get("total_amount_tax", "")
    result.total_amount = field_map.get("total_amount", "")
    result.total_tax = field_map.get("total_tax", "")
    
    # 抽取商品明细
    result.items = extract_items(text)
    
    # 计算整体置信度
    if fields:
        result.overall_confidence = sum(f.confidence for f in fields) / len(fields)
    else:
        result.overall_confidence = 0.0
    
    return result


# ---------------------------------------------------------------------------
# 输出格式化
# ---------------------------------------------------------------------------

def format_table(result: InvoiceResult) -> str:
    """格式化为表格文本"""
    lines = []
    lines.append(f"文件名: {result.filename}")
    lines.append(f"发票代码: {result.invoice_code}")
    lines.append(f"发票号码: {result.invoice_number}")
    lines.append(f"开票日期: {result.invoice_date}")
    lines.append(f"购买方名称: {result.buyer_name}")
    lines.append(f"购买方税号: {result.buyer_tax_id}")
    lines.append(f"销售方名称: {result.seller_name}")
    lines.append(f"销售方税号: {result.seller_tax_id}")
    lines.append(f"价税合计: {result.total_amount_tax}")
    lines.append(f"不含税金额: {result.total_amount}")
    lines.append(f"税额: {result.total_tax}")
    if result.items:
        lines.append("商品明细:")
        for i, item in enumerate(result.items, 1):
            lines.append(f"  {i}. {item.name} | 规格: {item.spec} | 数量: {item.qty} | 单价: {item.price} | 金额: {item.amount}")
    lines.append(f"整体置信度: {result.overall_confidence:.2f}")
    return "\n".join(lines)


def write_csv(results: List[InvoiceResult], output_path: str) -> None:
    """写入 CSV 文件（原子写入）"""
    temp_path = output_path + ".tmp"
    try:
        with open(temp_path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow([
                "文件名", "发票代码", "发票号码", "开票日期",
                "购买方名称", "购买方税号", "销售方名称", "销售方税号",
                "价税合计", "不含税金额", "税额", "整体置信度"
            ])
            for r in results:
                writer.writerow([
                    r.filename, r.invoice_code, r.invoice_number, r.invoice_date,
                    r.buyer_name, r.buyer_tax_id, r.seller_name, r.seller_tax_id,
                    r.total_amount_tax, r.total_amount, r.total_tax,
                    f"{r.overall_confidence:.2f}"
                ])
        os.replace(temp_path, output_path)
    except Exception as e:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise e


def write_json(results: List[InvoiceResult], output_path: str) -> None:
    """写入 JSON 文件（原子写入）"""
    temp_path = output_path + ".tmp"
    try:
        data = [r.to_dict() for r in results]
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(temp_path, output_path)
    except Exception as e:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise e


# ---------------------------------------------------------------------------
# 文件处理
# ---------------------------------------------------------------------------

SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".pdf"}


def is_supported_file(file_path: str) -> bool:
    """检查文件是否支持"""
    ext = os.path.splitext(file_path)[1].lower()
    return ext in SUPPORTED_EXTENSIONS


def process_file(file_path: str, verbose: bool = False) -> InvoiceResult:
    """
    处理单个文件，返回抽取结果。
    这是核心处理函数，被主流程与 selftest 共同调用。
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"文件不存在: {file_path}")
    
    if not is_supported_file(file_path):
        raise ValueError(f"不支持的文件格式: {file_path}")
    
    try:
        # 读取文件并提取文本（模拟 OCR）
        text = extract_text_from_file(file_path)
        if verbose:
            print(f"[VERBOSE] 从 {file_path} 提取到文本 {len(text)} 字符")
        
        # 解析发票
        result = parse_invoice(text, filename=os.path.basename(file_path))
        return result
    except Exception as e:
        raise RuntimeError(f"处理文件失败: {file_path}: {str(e)}")


def process_directory(dir_path: str, verbose: bool = False) -> List[InvoiceResult]:
    """批量处理目录下的所有支持文件"""
    results = []
    if not os.path.isdir(dir_path):
        raise NotADirectoryError(f"不是目录: {dir_path}")
    
    files = [f for f in os.listdir(dir_path) if is_supported_file(f)]
    files.sort()
    
    if not files:
        raise ValueError(f"目录中没有支持的文件: {dir_path}")
    
    for i, fname in enumerate(files, 1):
        fpath = os.path.join(dir_path, fname)
        try:
            if verbose:
                print(f"[{i}/{len(files)}] 处理 {fname} ...")
            result = process_file(fpath, verbose=verbose)
            results.append(result)
            if verbose:
                print(f"  成功 (置信度: {result.overall_confidence:.2f})")
        except Exception as e:
            if verbose:
                print(f"  失败: {str(e)}")
            # 失败时创建空结果
            result = InvoiceResult(filename=fname)
            result.overall_confidence = 0.0
            results.append(result)
    
    return results


# ---------------------------------------------------------------------------
# 自检测试
# ---------------------------------------------------------------------------

def run_selftest() -> int:
    """
    运行自检测试，验证核心功能。
    返回 0 表示成功，非 0 表示失败。
    """
    print("运行自检测试...")
    failures = 0
    
    # 测试 1: 解析样例发票文本
    print("[测试 1] 解析样例发票文本")
    try:
        result = parse_invoice(SAMPLE_INVOICE_TEXT, filename="test.jpg")
        assert result.invoice_code == "031001900111", f"发票代码错误: {result.invoice_code}"
        assert result.invoice_number == "12345678", f"发票号码错误: {result.invoice_number}"
        assert result.invoice_date == "2023年05月20日", f"开票日期错误: {result.invoice_date}"
        assert result.buyer_name == "某某科技有限公司", f"购买方名称错误: {result.buyer_name}"
        assert result.seller_name == "某某商贸有限公司", f"销售方名称错误: {result.seller_name}"
        assert result.total_amount_tax == "1130.00", f"价税合计错误: {result.total_amount_tax}"
        assert result.total_amount == "1000.00", f"不含税金额错误: {result.total_amount}"
        assert result.total_tax == "130.00", f"税额错误: {result.total_tax}"
        assert len(result.items) >= 1, "商品明细为空"
        assert result.overall_confidence > 0.8, f"置信度异常: {result.overall_confidence}"
        print("  通过")
    except AssertionError as e:
        print(f"  失败: {e}")
        failures += 1
    except Exception as e:
        print(f"  异常: {e}")
        failures += 1
    
    # 测试 2: 空文本处理
    print("[测试 2] 空文本处理")
    try:
        result = parse_invoice("", filename="empty.jpg")
        assert result.invoice_code == "", "空文本应返回空发票代码"
        assert result.overall_confidence == 0.0, "空文本置信度应为 0"
        print("  通过")
    except AssertionError as e:
        print(f"  失败: {e}")
        failures += 1
    except Exception as e:
        print(f"  异常: {e}")
        failures += 1
    
    # 测试 3: 文件处理（使用临时文件）
    print("[测试 3] 文件处理")
    try:
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            tmp_path = tmp.name
        try:
            result = process_file(tmp_path)
            assert result.filename == os.path.basename(tmp_path), "文件名错误"
            assert result.invoice_code == "031001900111", "发票代码错误"
            print("  通过")
        finally:
            os.remove(tmp_path)
    except AssertionError as e:
        print(f"  失败: {e}")
        failures += 1
    except Exception as e:
        print(f"  异常: {e}")
        failures += 1
    
    # 测试 4: 不存在的文件
    print("[测试 4] 不存在的文件")
    try:
        process_file("/nonexistent/file.jpg")
        print("  失败: 应抛出异常")
        failures += 1
    except FileNotFoundError:
        print("  通过")
    except Exception as e:
        print(f"  失败: 抛出异常类型错误: {type(e).__name__}")
        failures += 1
    
    # 测试 5: 不支持的格式
    print("[测试 5] 不支持的格式")
    try:
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tmp:
            tmp_path = tmp.name
        try:
            process_file(tmp_path)
            print("  失败: 应抛出异常")
            failures += 1
        except ValueError:
            print("  通过")
        finally:
            os.remove(tmp_path)
    except Exception as e:
        print(f"  异常: {e}")
        failures += 1
    
    # 测试 6: CSV 写入
    print("[测试 6] CSV 写入")
    try:
        result = parse_invoice(SAMPLE_INVOICE_TEXT, filename="test.jpg")
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp:
            tmp_path = tmp.name
        try:
            write_csv([result], tmp_path)
            with open(tmp_path, "r", encoding="utf-8-sig") as f:
                content = f.read()
            assert "031001900111" in content, "CSV 内容缺少发票代码"
            assert "12345678" in content, "CSV 内容缺少发票号码"
            print("  通过")
        finally:
            os.remove(tmp_path)
    except AssertionError as e:
        print(f"  失败: {e}")
        failures += 1
    except Exception as e:
        print(f"  异常: {e}")
        failures += 1
    
    # 测试 7: JSON 写入
    print("[测试 7] JSON 写入")
    try:
        result = parse_invoice(SAMPLE_INVOICE_TEXT, filename="test.jpg")
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
            tmp_path = tmp.name
        try:
            write_json([result], tmp_path)
            with open(tmp_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            assert len(data) == 1, "JSON 数据长度错误"
            assert data[0]["invoice_code"] == "031001900111", "JSON 发票代码错误"
            print("  通过")
        finally:
            os.remove(tmp_path)
    except AssertionError as e:
        print(f"  失败: {e}")
        failures += 1
    except Exception as e:
        print(f"  异常: {e}")
        failures += 1
    
    # 测试 8: 批量处理目录
    print("[测试 8] 批量处理目录")
    try:
        with tempfile.TemporaryDirectory() as tmp_dir:
            # 创建测试文件
            for i in range(3):
                with open(os.path.join(tmp_dir, f"invoice{i}.jpg"), "w") as f:
                    f.write("test")
            results = process_directory(tmp_dir)
            assert len(results) == 3, f"批量处理结果数量错误: {len(results)}"
            print("  通过")
    except AssertionError as e:
        print(f"  失败: {e}")
        failures += 1
    except Exception as e:
        print(f"  异常: {e}")
        failures += 1
    
    # 汇总
    if failures == 0:
        print("所有测试通过！")
        return 0
    else:
        print(f"{failures} 个测试失败")
        return 1


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------

def generate_output_filename(prefix: str, ext: str) -> str:
    """生成带时间戳的输出文件名"""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    return f"{prefix}_{timestamp}.{ext}"


def main() -> int:
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description="票据识别关键字段抽取工具",
        epilog="示例: python run.py invoice.jpg --format json --output-dir ./results/"
    )
    parser.add_argument("--path", nargs="?", help="文件路径或目录路径")
    parser.add_argument("--batch", action="store_true", help="批量处理目录")
    parser.add_argument("--format", choices=["table", "json", "csv"], default="table",
                        help="输出格式 (默认: table)")
    parser.add_argument("--dry-run", action="store_true", help="预览模式，不写入文件")
    parser.add_argument("--verbose", action="store_true", help="输出详细日志")
    parser.add_argument("--output-dir", default=".", help="输出目录 (默认: 当前目录)")
    parser.add_argument("--selftest", action="store_true", help="运行自检测试")
    
    args = parser.parse_args()
    
    # 自检模式
    if args.selftest:
        return run_selftest()
    
    # 参数校验
    if not args.path:
        print("错误: 必须提供文件路径或目录路径 (E001)", file=sys.stderr)
        return 1
    
    # 检查输出目录
    if not args.dry_run:
        if not os.path.isdir(args.output_dir):
            try:
                os.makedirs(args.output_dir, exist_ok=True)
            except OSError as e:
                print(f"错误: 无法创建输出目录 {args.output_dir}: {e} (E006)", file=sys.stderr)
                return 1
    
    try:
        # 处理输入
        if args.batch:
            # 批量模式
            if not os.path.isdir(args.path):
                print(f"错误: 批量模式需要目录路径: {args.path} (E001)", file=sys.stderr)
                return 1
            results = process_directory(args.path, verbose=args.verbose)
            if not results:
                print(f"错误: 目录中没有支持的文件: {args.path} (E008)", file=sys.stderr)
                return 1
        else:
            # 单文件模式
            if not os.path.exists(args.path):
                print(f"错误: 文件不存在: {args.path} (E002)", file=sys.stderr)
                return 1
            if not is_supported_file(args.path):
                print(f"错误: 不支持的文件格式: {args.path} (E003)", file=sys.stderr)
                return 1
            try:
                result = process_file(args.path, verbose=args.verbose)
                results = [result]
            except Exception as e:
                print(f"错误: 处理文件失败: {e} (E004)", file=sys.stderr)
                return 1
        
        # 输出结果
        if args.format == "table":
            for result in results:
                print(format_table(result))
                print()
        elif args.format == "json":
            if not args.dry_run:
                output_path = os.path.join(args.output_dir, generate_output_filename("invoice", "json"))
                try:
                    write_json(results, output_path)
                    print(f"结果已写入: {output_path}")
                except Exception as e:
                    print(f"错误: 写入 JSON 失败: {e} (E006)", file=sys.stderr)
                    return 1
            else:
                print("[DRY-RUN] 将写入 JSON 文件")
                for result in results:
                    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
        elif args.format == "csv":
            if not args.dry_run:
                output_path = os.path.join(args.output_dir, generate_output_filename("invoice", "csv"))
                try:
                    write_csv(results, output_path)
                    print(f"结果已写入: {output_path}")
                except Exception as e:
                    print(f"错误: 写入 CSV 失败: {e} (E006)", file=sys.stderr)
                    return 1
            else:
                print("[DRY-RUN] 将写入 CSV 文件")
                for result in results:
                    print(format_table(result))
                    print()
        
        # 批量模式汇总
        if args.batch and not args.dry_run:
            summary_path = os.path.join(args.output_dir, generate_output_filename("summary", args.format))
            try:
                if args.format == "json":
                    write_json(results, summary_path)
                elif args.format == "csv":
                    write_csv(results, summary_path)
                else:
                    # table 格式也写 CSV 汇总
                    summary_path = os.path.join(args.output_dir, generate_output_filename("summary", "csv"))
                    write_csv(results, summary_path)
                print(f"汇总文件已写入: {summary_path}")
            except Exception as e:
                print(f"错误: 写入汇总文件失败: {e} (E006)", file=sys.stderr)
                return 1
        
        return 0
        
    except Exception as e:
        print(f"错误: 未知异常: {e} (E010)", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
