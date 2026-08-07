#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
document-intelligence 技能实现
发票识别与文档智能处理平台（离线核心逻辑）
"""

import argparse
import json
import re
import sys
from typing import Dict, List, Any, Optional, Tuple


# ============================================================
# 错误码定义
# ============================================================
ERROR_CODES = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：...",
    "E003": "输入格式不符合要求，示例：...",
    "E004": "这超出了本工具的能力范围，建议...",
    "E005": "结果无法确定，建议：...",
    "E006": "内部处理错误，请重试或检查输入",
    "E007": "输出格式指定错误，支持：json/text",
    "E008": "批量处理时存在无效项",
    "E009": "置信度计算异常，请检查输入",
    "E010": "未知错误，请联系管理员",
}


# ============================================================
# 核心数据模型
# ============================================================
class InvoiceField:
    """发票字段定义"""
    # 发票关键字段（中文标签 -> 标准字段名）
    FIELD_MAP = {
        "发票号码": "invoice_no",
        "发票代码": "invoice_code",
        "开票日期": "date",
        "购买方名称": "buyer_name",
        "购买方税号": "buyer_tax_id",
        "销售方名称": "seller_name",
        "销售方税号": "seller_tax_id",
        "金额": "amount",
        "税额": "tax",
        "价税合计": "total",
        "商品名称": "item_name",
        "商品数量": "quantity",
        "商品单价": "unit_price",
    }

    # 必填字段（用于 E002 判断）
    REQUIRED_FIELDS = ["invoice_no", "date", "seller_name", "total"]


class DocumentIntelligence:
    """文档智能处理核心类"""

    def __init__(self):
        self.version = "1.0.0"
        self.skill_name = "document-intelligence"
        self.display_name = "发票识别"

    # --------------------------------------------------------
    # 主入口：处理单个输入
    # --------------------------------------------------------
    def process(self, input_data: str, output_format: str = "json") -> Dict[str, Any]:
        """
        处理单个输入，返回结构化结果
        
        Args:
            input_data: 用户提供的文本内容
            output_format: 输出格式（json/text）
            
        Returns:
            结构化结果字典
        """
        # 校验输入
        if not input_data or not input_data.strip():
            return self._make_error("E001")
        
        # 校验输出格式
        if output_format not in ("json", "text"):
            return self._make_error("E007")
        
        try:
            # 1. 解析输入，提取关键字段
            parsed = self._parse_input(input_data)
            
            # 2. 检查关键字段是否完整
            missing = self._check_required_fields(parsed)
            if missing:
                return self._make_error("E002", missing)
            
            # 3. 计算置信度
            confidence = self._calculate_confidence(parsed)
            
            # 4. 生成结果
            result = {
                "skill": self.skill_name,
                "version": self.version,
                "status": "success",
                "data": parsed,
                "confidence": confidence,
                "confidence_level": self._confidence_level(confidence),
                "warnings": self._generate_warnings(confidence),
            }
            
            # 5. 格式化输出
            if output_format == "text":
                return {"status": "success", "text": self._format_text(result)}
            
            return result
            
        except Exception as e:
            return self._make_error("E006", str(e))

    # --------------------------------------------------------
    # 批量处理
    # --------------------------------------------------------
    def process_batch(self, inputs: List[str], output_format: str = "json") -> Dict[str, Any]:
        """
        批量处理多个输入
        
        Args:
            inputs: 输入列表
            output_format: 输出格式
            
        Returns:
            批量处理结果
        """
        if not inputs:
            return self._make_error("E001")
        
        results = []
        errors = []
        
        for i, item in enumerate(inputs):
            result = self.process(item, output_format)
            if result.get("status") == "success":
                results.append({"index": i, "result": result})
            else:
                errors.append({"index": i, "error": result})
        
        # 如果全部失败，返回错误
        if not results:
            return self._make_error("E008")
        
        return {
            "status": "success",
            "total": len(inputs),
            "success_count": len(results),
            "error_count": len(errors),
            "results": results,
            "errors": errors if errors else None,
        }

    # --------------------------------------------------------
    # 内部解析逻辑
    # --------------------------------------------------------
    def _parse_input(self, text: str) -> Dict[str, Any]:
        """
        解析输入文本，提取发票关键字段
        
        使用正则表达式匹配常见发票格式
        """
        parsed: Dict[str, Any] = {}
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        
        # 逐行解析
        for line in lines:
            # 匹配 "字段名: 值" 或 "字段名：值" (支持中文和英文冒号)
            match = re.match(r'^([^:：]{1,20})[:：]\s*(.+)$', line)
            if match:
                field_label = match.group(1).strip()
                field_value = match.group(2).strip()
                
                # 映射字段名
                field_key = self.FIELD_MAP.get(field_label)
                if field_key:
                    parsed[field_key] = field_value
                else:
                    # 未识别字段，保留原始标签
                    parsed[f"raw_{field_label}"] = field_value
        
        # 如果关键字段缺失，尝试从自由文本中提取
        if "total" not in parsed:
            # 尝试匹配 "价税合计" 后的金额
            total_match = re.search(r'价税合计[:：]?\s*[¥￥]?\s*([\d,.]+)', text)
            if total_match:
                parsed["total"] = total_match.group(1)
        
        if "invoice_no" not in parsed:
            # 尝试匹配 "发票号码" 后的数字
            invoice_match = re.search(r'发票号码[:：]?\s*([\d]+)', text)
            if invoice_match:
                parsed["invoice_no"] = invoice_match.group(1)
        
        if "date" not in parsed:
            # 尝试匹配 "开票日期" 后的日期
            date_match = re.search(r'开票日期[:：]?\s*(\d{4}[-/]\d{1,2}[-/]\d{1,2})', text)
            if date_match:
                parsed["date"] = date_match.group(1)
        
        if "seller_name" not in parsed:
            # 尝试匹配 "销售方名称" 后的内容
            seller_match = re.search(r'销售方名称[:：]?\s*(.+)', text)
            if seller_match:
                parsed["seller_name"] = seller_match.group(1).strip()
        
        return parsed

    # --------------------------------------------------------
    # 字段完整性检查
    # --------------------------------------------------------
    def _check_required_fields(self, data: Dict[str, Any]) -> List[str]:
        """检查必填字段是否完整"""
        missing = []
        for field in self.REQUIRED_FIELDS:
            if field not in data or not data[field]:
                # 将标准字段名映射回中文标签
                for label, key in self.FIELD_MAP.items():
                    if key == field:
                        missing.append(label)
                        break
                else:
                    missing.append(field)
        return missing

    # --------------------------------------------------------
    # 置信度计算
    # --------------------------------------------------------
    def _calculate_confidence(self, data: Dict[str, Any]) -> float:
        """
        计算置信度（0-100）
        
        基于字段完整性和数据合理性：
        - 基础分 60
        - 每个必填字段 +5 分
        - 每个可选字段 +2 分
        - 金额合理性检查 +5 分
        """
        try:
            confidence = 60.0
            
            # 必填字段加分
            for field in self.REQUIRED_FIELDS:
                if field in data and data[field]:
                    confidence += 5.0
            
            # 可选字段加分
            optional_count = 0
            for key in data:
                if key not in self.REQUIRED_FIELDS and not key.startswith("raw_"):
                    optional_count += 1
            confidence += min(optional_count * 2.0, 10.0)
            
            # 金额合理性检查
            if "total" in data:
                total_str = data["total"].replace(",", "").replace("¥", "").replace("￥", "")
                try:
                    total = float(total_str)
                    if 0 < total < 1000000:  # 合理范围
                        confidence += 5.0
                except ValueError:
                    pass  # 金额格式异常，不加分
            
            # 限制在 0-100 范围
            return max(0.0, min(100.0, confidence))
            
        except Exception:
            return 0.0

    def _confidence_level(self, confidence: float) -> str:
        """根据置信度返回等级"""
        if confidence >= 90:
            return "高"
        elif confidence >= 85:
            return "中"
        else:
            return "低"

    def _generate_warnings(self, confidence: float) -> List[str]:
        """根据置信度生成警告"""
        warnings = []
        if confidence >= 90:
            warnings.append("置信度高，可直接使用")
        elif confidence >= 85:
            warnings.append("建议复核")
        else:
            warnings.append("[需核实] 置信度较低，请人工确认关键字段")
        return warnings

    # --------------------------------------------------------
    # 输出格式化
    # --------------------------------------------------------
    def _format_text(self, result: Dict[str, Any]) -> str:
        """将结果格式化为文本"""
        lines = []
        lines.append("=" * 40)
        lines.append(f"发票识别结果 (置信度: {result['confidence']:.1f}%)")
        lines.append(f"置信度等级: {result['confidence_level']}")
        lines.append("=" * 40)
        
        for key, value in result["data"].items():
            label = key
            for l, k in self.FIELD_MAP.items():
                if k == key:
                    label = l
                    break
            lines.append(f"{label}: {value}")
        
        if result["warnings"]:
            lines.append("-" * 40)
            lines.append("提示:")
            for warning in result["warnings"]:
                lines.append(f"  - {warning}")
        
        return "\n".join(lines)

    # --------------------------------------------------------
    # 错误处理
    # --------------------------------------------------------
    def _make_error(self, code: str, detail: str = None) -> Dict[str, Any]:
        """生成标准错误响应"""
        error = {
            "status": "error",
            "error_code": code,
            "message": ERROR_CODES.get(code, ERROR_CODES["E010"]),
        }
        if detail:
            error["detail"] = detail
        return error


# ============================================================
# 自测模块
# ============================================================
def run_selftest() -> bool:
    """
    内置自测：使用硬编码样例数据验证核心逻辑
    不依赖外部文件、网络或工作目录
    """
    print("=" * 50)
    print("开始自测 document-intelligence 技能...")
    print("=" * 50)
    
    engine = DocumentIntelligence()
    all_passed = True
    
    # 测试1: 正常发票解析
    print("\n[测试1] 正常发票解析")
    sample_invoice = """发票号码: 12345678
发票代码: 044001900111
开票日期: 2024-01-15
购买方名称: 测试科技有限公司
购买方税号: 91110108MA01XXXXX
销售方名称: 示例信息技术有限公司
销售方税号: 91110105MA02YYYYY
金额: 1000.00
税额: 60.00
价税合计: 1060.00
商品名称: 软件服务"""
    
    result = engine.process(sample_invoice)
    assert result["status"] == "success", f"测试1失败: 状态错误 {result}"
    assert "invoice_no" in result["data"], "测试1失败: 缺少发票号码"
    assert "seller_name" in result["data"], "测试1失败: 缺少销售方"
    assert "total" in result["data"], "测试1失败: 缺少金额"
    assert result["confidence"] >= 85, f"测试1失败: 置信度过低 {result['confidence']}"
    print(f"  ✓ 通过 (置信度: {result['confidence']:.1f}%)")
    
    # 测试2: 空输入错误处理
    print("\n[测试2] 空输入处理")
    result = engine.process("")
    assert result["status"] == "error", "测试2失败: 空输入应返回错误"
    assert result["error_code"] == "E001", f"测试2失败: 错误码应为E001, 实际 {result['error_code']}"
    print(f"  ✓ 通过 (错误码: {result['error_code']})")
    
    # 测试3: 缺失必填字段
    print("\n[测试3] 缺失必填字段")
    incomplete = "发票号码: 123\n开票日期: 2024-01-01"
    result = engine.process(incomplete)
    assert result["status"] == "error", "测试3失败: 应返回错误"
    assert result["error_code"] == "E002", f"测试3失败: 错误码应为E002, 实际 {result['error_code']}"
    print(f"  ✓ 通过 (错误码: {result['error_code']})")
    
    # 测试4: 批量处理
    print("\n[测试4] 批量处理")
    batch_inputs = [
        sample_invoice,
        "发票号码: 87654321\n开票日期: 2024-02-01\n销售方名称: 测试公司\n价税合计: 500.00",
        "",  # 无效输入
    ]
    result = engine.process_batch(batch_inputs)
    assert result["status"] == "success", "测试4失败: 批量处理应成功"
    assert result["success_count"] >= 2, "测试4失败: 至少应有2个成功"
    assert result["error_count"] >= 1, "测试4失败: 应有1个错误"
    print(f"  ✓ 通过 (成功: {result['success_count']}, 失败: {result['error_count']})")
    
    # 测试5: 置信度分级
    print("\n[测试5] 置信度分级")
    # 高置信度样例
    high_conf = engine.process(sample_invoice)
    assert high_conf["confidence_level"] in ("高", "中"), "测试5失败: 置信度等级不合理"
    
    # 低置信度样例（缺少多个字段）
    low_conf_input = "发票号码: 123\n销售方名称: 测试公司"
    low_conf = engine.process(low_conf_input)
    assert low_conf["status"] == "success", "测试5失败: 低置信度输入应可处理"
    assert low_conf["confidence"] < 85, f"测试5失败: 置信度应低于85, 实际 {low_conf['confidence']}"
    print(f"  ✓ 通过 (高: {high_conf['confidence']:.1f}%, 低: {low_conf['confidence']:.1f}%)")
    
    # 测试6: 文本输出格式
    print("\n[测试6] 文本输出格式")
    result = engine.process(sample_invoice, output_format="text")
    assert result["status"] == "success", "测试6失败: 文本格式处理失败"
    assert "text" in result, "测试6失败: 缺少文本输出"
    assert "发票识别结果" in result["text"], "测试6失败: 文本输出内容不正确"
    print("  ✓ 通过")
    
    # 测试7: 错误输出格式
    print("\n[测试7] 错误输出格式")
    result = engine.process(sample_invoice, output_format="xml")
    assert result["status"] == "error", "测试7失败: 应返回错误"
    assert result["error_code"] == "E007", f"测试7失败: 错误码应为E007, 实际 {result['error_code']}"
    print(f"  ✓ 通过 (错误码: {result['error_code']})")
    
    # 测试8: 金额格式解析
    print("\n[测试8] 金额格式解析")
    amount_invoice = """发票号码: 999
销售方名称: 测试公司
开票日期: 2024-03-01
价税合计: ¥1,234.56"""
    result = engine.process(amount_invoice)
    assert result["status"] == "success", "测试8失败: 金额解析失败"
    assert "total" in result["data"], "测试8失败: 缺少金额字段"
    print(f"  ✓ 通过 (金额: {result['data']['total']})")
    
    # 测试9: 边界情况
    print("\n[测试9] 边界情况")
    # 只包含必填字段
    minimal = "发票号码: 1\n开票日期: 2024-01-01\n销售方名称: 测试\n价税合计: 100.00"
    result = engine.process(minimal)
    assert result["status"] == "success", "测试9失败: 最小输入应成功"
    assert result["confidence"] >= 80, f"测试9失败: 最小输入置信度应>=80, 实际 {result['confidence']}"
    print(f"  ✓ 通过 (置信度: {result['confidence']:.1f}%)")
    
    # 测试10: 错误码完整性
    print("\n[测试10] 错误码完整性")
    for code in ["E001", "E002", "E003", "E004", "E005", "E006", "E007", "E008", "E009", "E010"]:
        assert code in ERROR_CODES, f"测试10失败: 缺少错误码 {code}"
    print(f"  ✓ 通过 (共 {len(ERROR_CODES)} 个错误码)")
    
    # 总结
    print("\n" + "=" * 50)
    if all_passed:
        print("✅ 所有自测通过！")
    else:
        print("❌ 存在测试失败！")
    print("=" * 50)
    
    return all_passed


# ============================================================
# 命令行入口
# ============================================================
def main():
    """命令行主入口"""
    parser = argparse.ArgumentParser(
        description="发票识别 - 文档智能处理平台",
        epilog="示例: python main.py --input '发票号码: 123' --output text"
    )
    
    parser.add_argument(
        "--input", "-i",
        type=str,
        help="输入文本内容（发票信息）",
        default=None
    )
    
    parser.add_argument(
        "--batch",
        type=str,
        help="批量输入，使用分号(;)分隔多个输入",
        default=None
    )
    
    parser.add_argument(
        "--output", "-o",
        type=str,
        choices=["json", "text"],
        default="json",
        help="输出格式 (默认: json)"
    )
    
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自测（使用硬编码样例，不依赖外部环境）"
    )
    
    parser.add_argument(
        "--version",
        action="version",
        version=f"document-intelligence v{DocumentIntelligence().version}"
    )
    
    args = parser.parse_args()
    
    # 自测模式
    if args.selftest:
        success = run_selftest()
        sys.exit(0 if success else 1)
    
    # 创建引擎
    engine = DocumentIntelligence()
    
    # 批量处理模式
    if args.batch:
        inputs = [item.strip() for item in args.batch.split(";") if item.strip()]
        result = engine.process_batch(inputs, args.output)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        sys.exit(0 if result.get("status") == "success" else 1)
    
    # 单条处理模式
    if args.input:
        result = engine.process(args.input, args.output)
        if args.output == "text" and result.get("status") == "success":
            print(result["text"])
        else:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        sys.exit(0 if result.get("status") == "success" else 1)
    
    # 无输入参数，显示帮助
    parser.print_help()


if __name__ == "__main__":
    main()
