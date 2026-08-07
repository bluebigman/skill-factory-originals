#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
发票识别 (receipt-scanner-for-android) - 独立实现脚本

本脚本根据功能规格独立编写，不复制任何既有代码。
功能：将用户提供的发票/收据文本信息转换为结构化结果，并给出置信度提示。

用法示例：
    python scripts/main.py --selftest          # 运行内置自检
    python scripts/main.py --input "发票文本"   # 处理输入文本
    python scripts/main.py --help              # 显示帮助

错误码：
    E001 - 输入为空
    E002 - 关键信息缺失
    E003 - 输入格式错误
    E004 - 超出能力边界
    E005 - 置信度过低
    E006 - 未知错误
    E007 - 参数错误
    E008 - 文件读取失败
    E009 - 输出写入失败
    E010 - 自检失败
"""

import argparse
import json
import re
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 核心数据结构
# ============================================================

class ReceiptInfo:
    """发票/收据信息结构体"""
    
    def __init__(self) -> None:
        self.raw_text: str = ""           # 原始输入文本
        self.invoice_number: str = ""     # 发票号码
        self.date: str = ""               # 日期
        self.merchant: str = ""           # 商户名称
        self.total_amount: float = 0.0    # 总金额
        self.tax_amount: float = 0.0      # 税额
        self.items: List[Dict[str, Any]] = []  # 商品明细
        self.confidence: float = 0.0      # 整体置信度 (0-100)
        self.warnings: List[str] = []     # 警告信息


# ============================================================
# 核心逻辑函数
# ============================================================

def extract_invoice_number(text: str) -> Tuple[str, float]:
    """
    从文本中提取发票号码
    
    规则：
    - 匹配常见发票号码格式（字母+数字组合，长度>=8）
    - 返回 (号码, 置信度)
    """
    patterns = [
        r'(?:发票号码|发票号|invoice\s*(?:no|number)?)[:：\s]*([A-Za-z0-9\-]{8,})',
        r'\b([A-Z]{1,3}\d{8,})\b',
        r'\b(\d{8,12})\b',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            number = match.group(1)
            # 置信度基于匹配模式
            if '发票号码' in pattern or 'invoice' in pattern.lower():
                confidence = 95.0
            else:
                confidence = 85.0
            return number, confidence
    
    return "", 0.0


def extract_date(text: str) -> Tuple[str, float]:
    """
    从文本中提取日期
    
    支持格式：YYYY-MM-DD, YYYY/MM/DD, YYYY年MM月DD日
    """
    patterns = [
        r'(?:日期|开票日期|date)[:：\s]*(\d{4}[-/年]\d{1,2}[-/月]\d{1,2}日?)',
        r'(\d{4}[-/年]\d{1,2}[-/月]\d{1,2}日?)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            date_str = match.group(1)
            # 规范化日期格式
            date_str = date_str.replace('年', '-').replace('月', '-').replace('日', '')
            date_str = date_str.replace('/', '-')
            try:
                # 验证日期有效性
                datetime.strptime(date_str, '%Y-%m-%d')
                return date_str, 90.0
            except ValueError:
                continue
    
    return "", 0.0


def extract_merchant(text: str) -> Tuple[str, float]:
    """
    从文本中提取商户名称
    
    规则：
    - 匹配"商户名称/收款单位/销售方"等关键词后的内容
    """
    patterns = [
        r'(?:商户名称|收款单位|销售方|merchant)[:：\s]+([^\n\r，,。;；]+)',
        r'(?:商户|商家)[:：\s]+([^\n\r，,。;；]+)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            merchant = match.group(1).strip()
            if merchant and len(merchant) > 1:
                return merchant, 88.0
    
    return "", 0.0


def extract_amount(text: str, keyword: str = '') -> Tuple[float, float]:
    """
    从文本中提取金额
    
    参数：
        text: 输入文本
        keyword: 关键词（如"总计"、"税额"等），空则匹配任意金额
    
    返回：(金额, 置信度)
    """
    if keyword:
        pattern = rf'{keyword}[^0-9]*([0-9]+(?:\.[0-9]+)?)'
    else:
        pattern = r'([0-9]+(?:\.[0-9]+)?)'
    
    matches = re.findall(pattern, text)
    if matches:
        try:
            amount = float(matches[-1])  # 取最后一个匹配，通常是总金额
            return amount, 85.0
        except ValueError:
            pass
    
    return 0.0, 0.0


def extract_items(text: str) -> Tuple[List[Dict[str, Any]], float]:
    """
    从文本中提取商品明细
    
    规则：
    - 匹配"商品/项目"关键词后的内容
    - 每行格式：名称 数量 单价 金额
    """
    items = []
    lines = text.split('\n')
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # 尝试匹配商品行：名称 + 数量 + 单价 + 金额
        match = re.match(r'(.+?)\s+(\d+)\s+([0-9.]+)\s+([0-9.]+)', line)
        if match:
            name = match.group(1).strip()
            quantity = int(match.group(2))
            unit_price = float(match.group(3))
            total = float(match.group(4))
            
            items.append({
                'name': name,
                'quantity': quantity,
                'unit_price': unit_price,
                'total': total
            })
    
    if items:
        return items, 80.0
    return [], 0.0


def calculate_confidence(fields: Dict[str, Tuple[Any, float]]) -> float:
    """
    计算整体置信度
    
    按字段加权平均，重要字段权重更高
    """
    weights = {
        'invoice_number': 0.3,
        'date': 0.2,
        'merchant': 0.2,
        'total_amount': 0.3,
    }
    
    total_weight = 0.0
    weighted_sum = 0.0
    
    for field, (value, conf) in fields.items():
        if value and conf > 0:
            weight = weights.get(field, 0.1)
            total_weight += weight
            weighted_sum += conf * weight
    
    if total_weight == 0:
        return 0.0
    
    return weighted_sum / total_weight


def process_receipt(text: str) -> Dict[str, Any]:
    """
    处理发票文本，返回结构化结果
    
    参数：
        text: 发票文本内容
    
    返回：
        结构化结果字典
    """
    # 输入校验
    if not text or not text.strip():
        raise ValueError("E001: 输入为空")
    
    # 创建结果对象
    receipt = ReceiptInfo()
    receipt.raw_text = text.strip()
    
    # 提取各字段
    invoice_num, conf_inv = extract_invoice_number(text)
    date_str, conf_date = extract_date(text)
    merchant, conf_merchant = extract_merchant(text)
    total, conf_total = extract_amount(text, '总计')
    tax, conf_tax = extract_amount(text, '税额')
    items, conf_items = extract_items(text)
    
    # 填充结果
    receipt.invoice_number = invoice_num
    receipt.date = date_str
    receipt.merchant = merchant
    receipt.total_amount = total
    receipt.tax_amount = tax
    receipt.items = items
    
    # 计算整体置信度
    fields = {
        'invoice_number': (invoice_num, conf_inv),
        'date': (date_str, conf_date),
        'merchant': (merchant, conf_merchant),
        'total_amount': (total, conf_total),
    }
    receipt.confidence = calculate_confidence(fields)
    
    # 添加警告信息
    if not invoice_num:
        receipt.warnings.append("未识别到发票号码")
    if not date_str:
        receipt.warnings.append("未识别到日期")
    if not merchant:
        receipt.warnings.append("未识别到商户名称")
    if total == 0:
        receipt.warnings.append("未识别到总金额")
    
    # 根据置信度添加标注
    if receipt.confidence < 85:
        receipt.warnings.append("[需核实] 整体置信度较低，请人工复核")
    elif receipt.confidence < 90:
        receipt.warnings.append("建议复核")
    
    # 构建输出
    result = {
        "raw_text": receipt.raw_text,
        "invoice_number": receipt.invoice_number,
        "date": receipt.date,
        "merchant": receipt.merchant,
        "total_amount": receipt.total_amount,
        "tax_amount": receipt.tax_amount,
        "items": receipt.items,
        "confidence": round(receipt.confidence, 1),
        "warnings": receipt.warnings,
        "status": "success",
    }
    
    return result


# ============================================================
# 自检模块
# ============================================================

def run_selftest() -> bool:
    """
    运行内置自检
    
    使用硬编码样例数据，不依赖外部文件
    使用宽松阈值，避免精确匹配
    
    返回：True 表示自检通过
    """
    print("=" * 50)
    print("开始运行自检...")
    print("=" * 50)
    
    # 测试样例1：完整发票
    sample1 = """
    电子发票（普通发票）
    发票号码：123456789012
    开票日期：2024-03-15
    商户名称：测试科技有限公司
    商品明细：
    办公用品 2 50.00 100.00
    打印纸 1 30.00 30.00
    总计：130.00
    税额：7.80
    """
    
    # 测试样例2：简单收据
    sample2 = """
    收款收据
    收款单位：测试便利店
    日期：2024/01/20
    商品 A 1 25.50 25.50
    商品 B 3 10.00 30.00
    合计：55.50
    """
    
    # 测试样例3：空输入（应触发 E001）
    sample3 = ""
    
    # 测试样例4：不完整信息
    sample4 = """
    简单收据
    金额：99.00
    """
    
    test_cases = [
        {
            "name": "完整发票测试",
            "input": sample1,
            "checks": [
                lambda r: r["status"] == "success",
                lambda r: len(r["invoice_number"]) >= 8,
                lambda r: len(r["date"]) >= 8,
                lambda r: len(r["merchant"]) > 0,
                lambda r: r["total_amount"] > 0,
                lambda r: r["confidence"] >= 50,  # 宽松阈值
            ]
        },
        {
            "name": "简单收据测试",
            "input": sample2,
            "checks": [
                lambda r: r["status"] == "success",
                lambda r: r["total_amount"] > 0,
                lambda r: len(r["items"]) > 0,
            ]
        },
        {
            "name": "空输入错误测试",
            "input": sample3,
            "checks": [
                lambda r: isinstance(r, dict) and r.get("error_code") == "E001",
            ],
            "expect_error": True,
        },
        {
            "name": "不完整信息测试",
            "input": sample4,
            "checks": [
                lambda r: r["status"] == "success",
                lambda r: r["total_amount"] > 0,
                lambda r: len(r["warnings"]) > 0,  # 应有警告
            ]
        },
    ]
    
    all_passed = True
    
    for case in test_cases:
        print(f"\n测试: {case['name']}")
        try:
            result = process_receipt(case["input"])
            
            if case.get("expect_error"):
                print(f"  ✗ 预期错误但成功执行")
                all_passed = False
                continue
            
            # 运行所有检查
            check_results = []
            for check in case["checks"]:
                check_result = check(result)
                check_results.append(check_result)
                if not check_result:
                    print(f"  ✗ 检查失败: {check}")
                    all_passed = False
                    break
            else:
                print(f"  ✓ 通过")
                print(f"    发票号码: {result['invoice_number']}")
                print(f"    日期: {result['date']}")
                print(f"    商户: {result['merchant']}")
                print(f"    金额: {result['total_amount']}")
                print(f"    置信度: {result['confidence']}%")
                
        except ValueError as e:
            if case.get("expect_error"):
                error_code = str(e).split(":")[0]
                if error_code == "E001":
                    print(f"  ✓ 预期错误: {e}")
                else:
                    print(f"  ✗ 错误码不匹配: {e}")
                    all_passed = False
            else:
                print(f"  ✗ 意外错误: {e}")
                all_passed = False
        except Exception as e:
            print(f"  ✗ 未知异常: {e}")
            all_passed = False
    
    print("\n" + "=" * 50)
    if all_passed:
        print("✅ 所有自检通过")
    else:
        print("❌ 部分自检失败")
    print("=" * 50)
    
    return all_passed


# ============================================================
# 主程序
# ============================================================

def main() -> int:
    """
    主程序入口
    
    返回：退出码（0=成功，非0=失败）
    """
    parser = argparse.ArgumentParser(
        description="发票识别 - 将发票/收据文本转换为结构化数据",
        epilog="示例: python main.py --input '发票文本...'"
    )
    
    parser.add_argument(
        "--input", "-i",
        type=str,
        help="待处理的发票文本内容"
    )
    parser.add_argument(
        "--input-file", "-f",
        type=str,
        help="从文件读取发票文本"
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        help="输出结果到JSON文件"
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检并退出"
    )
    
    args = parser.parse_args()
    
    # 自检模式
    if args.selftest:
        try:
            passed = run_selftest()
            return 0 if passed else 1
        except Exception as e:
            print(f"E010: 自检执行失败 - {e}")
            return 1
    
    # 获取输入内容
    input_text = ""
    
    if args.input:
        input_text = args.input
    elif args.input_file:
        try:
            with open(args.input_file, 'r', encoding='utf-8') as f:
                input_text = f.read()
        except Exception as e:
            print(f"E008: 读取文件失败 - {e}")
            return 8
    else:
        # 提示用户输入
        print("请输入发票文本（Ctrl+D 结束输入）：")
        try:
            lines = []
            for line in sys.stdin:
                lines.append(line)
            input_text = "\n".join(lines)
        except KeyboardInterrupt:
            print("\nE001: 输入为空")
            return 1
    
    # 处理输入
    try:
        result = process_receipt(input_text)
        
        # 输出结果
        output_json = json.dumps(result, ensure_ascii=False, indent=2)
        
        if args.output:
            try:
                with open(args.output, 'w', encoding='utf-8') as f:
                    f.write(output_json)
                print(f"结果已保存到: {args.output}")
            except Exception as e:
                print(f"E009: 写入文件失败 - {e}")
                return 9
        else:
            print(output_json)
        
        return 0
        
    except ValueError as e:
        print(f"错误: {e}")
        return 1
    except Exception as e:
        print(f"E006: 未知错误 - {e}")
        return 6


if __name__ == "__main__":
    sys.exit(main())
