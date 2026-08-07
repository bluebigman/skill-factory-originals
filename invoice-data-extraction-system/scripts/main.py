#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
发票数据提取系统 - 核心逻辑实现
基于功能规格独立开发，不依赖任何既有代码。
"""

import sys
import json
import argparse
import re
from typing import Dict, List, Any, Optional, Tuple


# ============================================================
# 常量定义
# ============================================================
ERROR_CODES = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：",
    "E003": "输入格式不符合要求，示例：...",
    "E004": "这超出了本工具的能力范围，建议...",
    "E005": "结果无法确定，建议：...",
}

# 发票字段配置（字段名 -> 提取规则）
INVOICE_FIELDS = {
    "invoice_number": {"name": "发票号码", "pattern": r"(?:发票号码|发票号)[:：]?\s*([A-Z]{2}\d{8})"},
    "invoice_date": {"name": "开票日期", "pattern": r"(?:开票日期|日期)[:：]?\s*(\d{4}[-/年]\d{1,2}[-/月]\d{1,2}日?)"},
    "buyer_name": {"name": "购买方名称", "pattern": r"(?:购买方名称|购买方)[:：]?\s*([^\n,，;；]+)"},
    "seller_name": {"name": "销售方名称", "pattern": r"(?:销售方名称|销售方)[:：]?\s*([^\n,，;；]+)"},
    "total_amount": {"name": "价税合计", "pattern": r"价税合计[（(大写)]?[:：]?\s*[￥¥]?\s*(\d+[.,]?\d*)"},
    "tax_amount": {"name": "税额", "pattern": r"税额[:：]?\s*[￥¥]?\s*(\d+[.,]?\d*)"},
}

# 置信度阈值定义
CONFIDENCE_HIGH = 0.90
CONFIDENCE_MEDIUM = 0.85

# 发票关键词（用于判断是否为发票）
INVOICE_KEYWORDS = [
    "发票",
    "invoice",
    "发票号码",
    "开票日期",
    "购买方",
    "销售方",
    "价税合计"
]


# ============================================================
# 核心数据结构
# ============================================================
class InvoiceData:
    """发票数据结构"""
    
    def __init__(self):
        self.fields: Dict[str, Dict[str, Any]] = {}
        self.confidence: float = 0.0
        self.warnings: List[str] = []
    
    def add_field(self, name: str, value: Any, confidence: float, source: str = "ocr"):
        """添加字段"""
        self.fields[name] = {
            "value": value,
            "confidence": confidence,
            "source": source
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        result = {
            "fields": {},
            "overall_confidence": self.confidence,
            "warnings": self.warnings
        }
        for field_name, field_data in self.fields.items():
            result["fields"][field_name] = {
                "value": field_data["value"],
                "confidence": field_data["confidence"]
            }
        return result


# ============================================================
# 核心处理引擎
# ============================================================
class InvoiceExtractor:
    """发票数据提取引擎"""
    
    def __init__(self):
        self.error_code: Optional[str] = None
        self.error_message: str = ""
    
    def extract(self, text: str) -> InvoiceData:
        """从文本中提取发票信息"""
        # 输入校验
        if not text or not text.strip():
            self.error_code = "E001"
            self.error_message = ERROR_CODES["E001"]
            raise ValueError(self.error_message)
        
        # 检查是否包含发票相关关键词（更严格）
        if not self._contains_invoice_keywords(text):
            self.error_code = "E003"
            self.error_message = ERROR_CODES["E003"] + "未检测到发票特征"
            raise ValueError(self.error_message)
        
        # 创建结果对象
        result = InvoiceData()
        
        # 逐字段提取
        extracted_count = 0
        total_fields = len(INVOICE_FIELDS)
        
        for field_name, config in INVOICE_FIELDS.items():
            field_value, confidence = self._extract_field(text, config)
            if field_value is not None:
                result.add_field(field_name, field_value, confidence)
                extracted_count += 1
            else:
                # 字段缺失，降低置信度
                result.warnings.append(f"未提取到{config['name']}")
        
        # 计算整体置信度
        if extracted_count > 0:
            avg_conf = sum(
                f["confidence"] 
                for f in result.fields.values()
            ) / len(result.fields)
            coverage_ratio = extracted_count / total_fields
            result.confidence = avg_conf * coverage_ratio
        else:
            result.confidence = 0.0
            self.error_code = "E005"
            self.error_message = ERROR_CODES["E005"]
        
        # 添加置信度相关警告
        self._add_confidence_warnings(result)
        
        return result
    
    def _contains_invoice_keywords(self, text: str) -> bool:
        """
        检查是否包含发票关键词
        要求至少包含2个关键词，且必须包含"发票"或"invoice"
        """
        text_lower = text.lower()
        
        # 必须包含"发票"或"invoice"
        if "发票" not in text_lower and "invoice" not in text_lower:
            return False
        
        # 统计其他关键词
        keyword_count = sum(
            1 for kw in INVOICE_KEYWORDS 
            if kw.lower() in text_lower
        )
        
        # 至少匹配2个关键词（包括"发票"本身）
        return keyword_count >= 2
    
    def _extract_field(self, text: str, config: Dict[str, str]) -> Tuple[Optional[str], float]:
        """提取单个字段"""
        pattern = config["pattern"]
        match = re.search(pattern, text, re.IGNORECASE)
        
        if not match:
            return None, 0.0
        
        # 提取值（如果有捕获组则用第一个捕获组）
        value = match.group(1) if match.groups() else match.group(0)
        value = value.strip()
        
        # 清理值（去除可能的标点）
        value = re.sub(r'[，,。；;：:]+$', '', value)  # 去除末尾标点
        
        # 计算置信度
        confidence = self._calculate_confidence(value, config["name"])
        
        return value, confidence
    
    def _calculate_confidence(self, value: str, field_name: str) -> float:
        """计算字段置信度"""
        confidence = 0.95  # 基础置信度
        
        # 根据字段类型调整
        if "金额" in field_name or "税额" in field_name:
            # 金额字段需要验证格式
            if re.match(r"^\d+[.,]?\d*$", value):
                confidence = 0.95
            else:
                confidence = 0.80
        elif "日期" in field_name:
            # 日期字段验证
            if re.match(r"\d{4}[-/年]\d{1,2}[-/月]\d{1,2}日?", value):
                confidence = 0.95
            else:
                confidence = 0.80
        elif "号码" in field_name:
            # 发票号码格式验证
            if re.match(r"[A-Z]{2}\d{8}", value):
                confidence = 0.95
            else:
                confidence = 0.85
        
        return confidence
    
    def _add_confidence_warnings(self, result: InvoiceData) -> None:
        """添加置信度相关警告"""
        if result.confidence >= CONFIDENCE_HIGH:
            pass  # 高置信度，无警告
        elif result.confidence >= CONFIDENCE_MEDIUM:
            result.warnings.append("建议复核：部分字段置信度较低")
        else:
            result.warnings.append("[需核实]：整体置信度偏低，请人工核实关键信息")


# ============================================================
# 输出格式化
# ============================================================
class OutputFormatter:
    """输出格式化器"""
    
    @staticmethod
    def format_json(data: InvoiceData) -> str:
        """JSON格式输出"""
        return json.dumps(data.to_dict(), ensure_ascii=False, indent=2)
    
    @staticmethod
    def format_text(data: InvoiceData) -> str:
        """纯文本格式输出"""
        lines = []
        lines.append("=== 发票信息提取结果 ===")
        lines.append(f"整体置信度: {data.confidence:.1%}")
        lines.append("")
        
        for field_name, field_data in data.fields.items():
            display_name = INVOICE_FIELDS.get(field_name, {}).get("name", field_name)
            conf_str = f"({field_data['confidence']:.0%})"
            lines.append(f"{display_name}: {field_data['value']} {conf_str}")
        
        if data.warnings:
            lines.append("")
            lines.append("警告:")
            for warning in data.warnings:
                lines.append(f"  - {warning}")
        
        return "\n".join(lines)


# ============================================================
# 内置自检样例数据
# ============================================================
SELFTEST_SAMPLES = [
    {
        "description": "标准增值税发票",
        "text": """
        增值税专用发票
        发票号码：AC12345678
        开票日期：2024年03月15日
        购买方名称：北京某某科技有限公司
        销售方名称：上海某某信息技术有限公司
        价税合计（大写）：壹万元整
        价税合计：￥10000.00
        税额：￥1290.32
        """,
        "expected_fields": ["invoice_number", "invoice_date", "buyer_name", "seller_name"]
    },
    {
        "description": "普通发票",
        "text": """
        普通发票
        发票号码：BD87654321
        开票日期：2024/06/20
        购买方：广州某某商贸有限公司
        销售方：深圳某某电子有限公司
        价税合计：￥5600.50
        税额：￥744.02
        """,
        "expected_fields": ["invoice_number", "invoice_date", "buyer_name", "seller_name"]
    },
    {
        "description": "不完整发票（缺少关键字段）",
        "text": """
        发票
        发票号码：CE13572468
        开票日期：2024年01月10日
        购买方名称：杭州某某网络有限公司
        """,
        "expected_fields": ["invoice_number", "invoice_date", "buyer_name"]
    },
    {
        "description": "非发票文本",
        "text": "这是一段普通的文本，不包含发票相关信息。",
        "expected_error": "E003"
    },
    {
        "description": "空文本",
        "text": "",
        "expected_error": "E001"
    }
]


# ============================================================
# 自检模块
# ============================================================
def run_selftest() -> bool:
    """运行内置自检"""
    print("=" * 60)
    print("执行自检...")
    print("=" * 60)
    
    extractor = InvoiceExtractor()
    formatter = OutputFormatter()
    all_passed = True
    
    for i, sample in enumerate(SELFTEST_SAMPLES, 1):
        print(f"\n测试用例 {i}: {sample['description']}")
        
        try:
            # 尝试提取
            result = extractor.extract(sample["text"])
            
            # 如果预期是错误
            if "expected_error" in sample:
                print(f"  [失败] 预期错误 {sample['expected_error']}，但提取成功")
                all_passed = False
                continue
            
            # 检查必填字段
            expected_fields = sample.get("expected_fields", [])
            missing_fields = []
            for field in expected_fields:
                if field not in result.fields:
                    missing_fields.append(field)
            
            if missing_fields:
                print(f"  [失败] 缺少字段: {missing_fields}")
                all_passed = False
            else:
                # 验证字段值非空
                empty_fields = [
                    field for field in expected_fields
                    if not result.fields[field]["value"]
                ]
                if empty_fields:
                    print(f"  [失败] 字段值为空: {empty_fields}")
                    all_passed = False
                else:
                    # 验证置信度在合理范围（宽松阈值）
                    conf_ok = (
                        0.0 < result.confidence <= 1.0 and
                        all(
                            0.5 < result.fields[field]["confidence"] <= 1.0
                            for field in expected_fields
                        )
                    )
                    if conf_ok:
                        print(f"  [通过] 字段提取成功，整体置信度: {result.confidence:.1%}")
                        # 输出部分结果（不打印完整结果，避免冗余）
                        print(f"         字段数: {len(result.fields)}")
                    else:
                        print(f"  [失败] 置信度不在合理范围: {result.confidence}")
                        all_passed = False
            
        except ValueError as e:
            if "expected_error" in sample:
                # 验证错误码
                if extractor.error_code == sample["expected_error"]:
                    print(f"  [通过] 正确抛出错误: {extractor.error_code}")
                else:
                    print(f"  [失败] 错误码不匹配: 预期 {sample['expected_error']}, 实际 {extractor.error_code}")
                    all_passed = False
            else:
                print(f"  [失败] 意外错误: {e}")
                all_passed = False
        except Exception as e:
            print(f"  [失败] 异常: {e}")
            all_passed = False
    
    # 测试格式化输出
    print("\n" + "=" * 60)
    print("测试输出格式化...")
    print("=" * 60)
    
    try:
        # 创建一个测试数据对象
        test_invoice = InvoiceData()
        test_invoice.add_field("test_field", "测试值", 0.95)
        test_invoice.confidence = 0.92
        
        # 测试JSON输出
        json_output = formatter.format_json(test_invoice)
        parsed_json = json.loads(json_output)
        if parsed_json.get("overall_confidence", 0) > 0.9:
            print("  [通过] JSON格式输出正常")
        else:
            print("  [失败] JSON格式输出异常")
            all_passed = False
        
        # 测试文本输出
        text_output = formatter.format_text(test_invoice)
        if "测试值" in text_output:
            print("  [通过] 文本格式输出正常")
        else:
            print("  [失败] 文本格式输出异常")
            all_passed = False
            
    except Exception as e:
        print(f"  [失败] 格式化测试异常: {e}")
        all_passed = False
    
    # 总结
    print("\n" + "=" * 60)
    if all_passed:
        print("自检全部通过！")
    else:
        print("自检存在失败项，请检查实现。")
    print("=" * 60)
    
    return all_passed


# ============================================================
# 命令行入口
# ============================================================
def main():
    """主入口"""
    parser = argparse.ArgumentParser(
        description="发票数据提取系统 - 从文本中提取发票关键信息"
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检（不读外部文件，不依赖网络）"
    )
    parser.add_argument(
        "--input",
        type=str,
        help="输入文本内容（发票文本）"
    )
    parser.add_argument(
        "--format",
        choices=["json", "text"],
        default="text",
        help="输出格式（默认: text）"
    )
    
    args = parser.parse_args()
    
    # 自检模式
    if args.selftest:
        success = run_selftest()
        sys.exit(0 if success else 1)
    
    # 处理输入
    if not args.input:
        print("错误: 请提供 --input 参数或使用 --selftest 运行自检", file=sys.stderr)
        print("错误码: E001", file=sys.stderr)
        print(ERROR_CODES["E001"], file=sys.stderr)
        sys.exit(1)
    
    # 执行提取
    extractor = InvoiceExtractor()
    formatter = OutputFormatter()
    
    try:
        result = extractor.extract(args.input)
        
        # 输出结果
        if args.format == "json":
            output = formatter.format_json(result)
        else:
            output = formatter.format_text(result)
        
        print(output)
        
        # 处理警告
        if result.warnings:
            print("\n警告信息:")
            for warning in result.warnings:
                print(f"  - {warning}")
        
        # 根据置信度决定退出码
        if result.confidence < 0.85:
            print("\n[需核实] 结果置信度较低，请人工核实关键信息", file=sys.stderr)
            sys.exit(2)
            
    except ValueError as e:
        print(f"错误: {e}", file=sys.stderr)
        if extractor.error_code:
            print(f"错误码: {extractor.error_code}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"未知错误: {e}", file=sys.stderr)
        print("错误码: E010", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
