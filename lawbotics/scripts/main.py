#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
lawbotics - 合同审查技能（独立实现）

仅依据功能规格设计，clean-room 实现。
仅供学习与参考用途，不构成法律建议。
"""

import argparse
import json
import re
import sys
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# 常量定义
# ---------------------------------------------------------------------------

# 错误码及对应话术（依据规格第四节）
ERROR_MESSAGES: Dict[str, str] = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：...",
    "E003": "输入格式不符合要求，示例：...",
    "E004": "这超出了本工具的能力范围，建议...",
    "E005": "结果无法确定，建议：...",
}

# 置信度阈值（依据规格第三节 Step 2.3）
CONFIDENCE_HIGH = 0.90      # >=90% 直接输出
CONFIDENCE_MEDIUM = 0.85    # 85%-90% 建议复核
# <85% 标注 [需核实]

# 输出字段默认模板
DEFAULT_FIELDS = ["party", "subject", "amount", "date", "clause"]


# ---------------------------------------------------------------------------
# 核心数据结构
# ---------------------------------------------------------------------------

class ContractData:
    """合同结构化数据模型"""
    
    def __init__(self) -> None:
        self.fields: Dict[str, Any] = {}
        self.confidence: float = 1.0
        self.notes: List[str] = []
    
    def set_field(self, key: str, value: Any, confidence: float = 1.0) -> None:
        """设置字段值并记录置信度"""
        self.fields[key] = value
        # 整体置信度取最低值（保守策略）
        self.confidence = min(self.confidence, confidence)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典输出"""
        return {
            "fields": self.fields,
            "confidence": round(self.confidence, 4),
            "notes": self.notes,
            "status": self._get_status(),
        }
    
    def _get_status(self) -> str:
        """根据置信度生成状态标注"""
        if self.confidence >= CONFIDENCE_HIGH:
            return "直接输出"
        elif self.confidence >= CONFIDENCE_MEDIUM:
            return "建议复核"
        else:
            return "[需核实]"


# ---------------------------------------------------------------------------
# 核心处理逻辑
# ---------------------------------------------------------------------------

class ContractProcessor:
    """合同审查处理器"""
    
    def __init__(self) -> None:
        # 常见合同条款关键词（用于识别）
        self.clause_keywords = [
            "违约责任", "争议解决", "保密条款", "终止条款",
            "付款方式", "交付时间", "知识产权", "不可抗力"
        ]
        
        # 常见金额标识 - 覆盖多种格式
        self.amount_patterns = [
            # 格式: 金额/价款/费用/价格 + 数字 + 单位
            r'(?:金额|价款|费用|价格|总价|合同金额)[:：]?\s*(?:人民币|RMB|CNY)?\s*([0-9,，.]+)\s*(?:元|万元|人民币|RMB|CNY)?',
            # 格式: 货币符号 + 数字
            r'(?:￥|¥|RMB|CNY)\s*([0-9,，.]+)\s*(?:元|万元)?',
            # 格式: 数字 + 元/万元
            r'([0-9,，.]+)\s*(?:元|万元|人民币|RMB|CNY)',
        ]
        
        # 日期模式
        self.date_patterns = [
            r'(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日',
            r'(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})',
            r'(\d{4})\s*年\s*(\d{1,2})\s*月',
        ]
    
    def process(self, raw_input: str, required_fields: Optional[List[str]] = None) -> ContractData:
        """
        处理合同文本，提取结构化信息
        
        Args:
            raw_input: 原始合同文本
            required_fields: 必需的字段列表，None 则使用默认模板
        
        Returns:
            ContractData: 结构化结果
        
        Raises:
            ValueError: 带错误码的异常
        """
        # E001: 输入为空
        if not raw_input or not raw_input.strip():
            raise ValueError("E001")
        
        # 检查必需字段
        fields = required_fields or DEFAULT_FIELDS
        result = ContractData()
        
        # 提取甲方/乙方（合同主体）
        self._extract_parties(raw_input, result)
        
        # 提取合同标的
        self._extract_subject(raw_input, result)
        
        # 提取金额
        self._extract_amount(raw_input, result)
        
        # 提取日期
        self._extract_date(raw_input, result)
        
        # 提取条款
        self._extract_clauses(raw_input, result)
        
        # E002: 关键信息缺失
        missing = [f for f in fields if f not in result.fields]
        if missing:
            # 不直接抛错，但记录提示
            result.notes.append(f"缺失字段: {', '.join(missing)}")
        
        # 置信度检查
        if result.confidence < CONFIDENCE_MEDIUM:
            result.notes.append("存在低置信度内容，请人工复核")
        
        return result
    
    def _extract_parties(self, text: str, result: ContractData) -> None:
        """提取合同主体（甲方/乙方）"""
        # 尝试匹配甲方、乙方
        party_a = re.search(r'甲方[：:]\s*([^\s，,。；;]+)', text)
        party_b = re.search(r'乙方[：:]\s*([^\s，,。；;]+)', text)
        
        if party_a:
            result.set_field("party_a", party_a.group(1).strip(), confidence=0.95)
        if party_b:
            result.set_field("party_b", party_b.group(1).strip(), confidence=0.95)
        
        # 如果只有一方，降低置信度
        if party_a and not party_b:
            result.confidence = min(result.confidence, 0.88)
            result.notes.append("仅识别到甲方，乙方信息待确认")
    
    def _extract_subject(self, text: str, result: ContractData) -> None:
        """提取合同标的/主题"""
        patterns = [
            r'(?:标的|主题|事项)[：:]\s*([^\n。]+)',
            r'(?:关于|涉及)\s*([^\n，。]+?)\s*的(?:合同|协议)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                subject = match.group(1).strip()
                if len(subject) > 2:  # 长度过滤
                    result.set_field("subject", subject, confidence=0.9)
                    return
        
        # 未找到明确标的，尝试从合同名称获取
        title_match = re.search(r'《([^》]+)》', text)
        if title_match:
            result.set_field("subject", title_match.group(1), confidence=0.7)
    
    def _extract_amount(self, text: str, result: ContractData) -> None:
        """提取合同金额 - 支持多种格式"""
        for pattern in self.amount_patterns:
            match = re.search(pattern, text)
            if match:
                amount = match.group(1).replace(',', '').replace('，', '')
                # 确定单位
                unit = "元"
                if "万元" in text[match.start():match.end()]:
                    unit = "万元"
                elif match.group(0).find("万元") >= 0:
                    unit = "万元"
                
                # 格式化金额数值
                try:
                    amount_num = float(amount)
                    if amount_num >= 10000 and unit == "元":
                        # 大额金额自动转换单位
                        amount = f"{amount_num/10000:.2f}"
                        unit = "万元"
                    else:
                        amount = f"{amount_num:.2f}"
                except ValueError:
                    pass
                
                result.set_field("amount", f"{amount} {unit}", confidence=0.92)
                return
        
        # 未找到金额，降低置信度
        result.confidence = min(result.confidence, 0.8)
        result.notes.append("未识别到明确金额")
    
    def _extract_date(self, text: str, result: ContractData) -> None:
        """提取合同日期"""
        for pattern in self.date_patterns:
            match = re.search(pattern, text)
            if match:
                groups = match.groups()
                if len(groups) == 3:
                    year, month, day = groups
                    result.set_field("date", f"{year}-{month.zfill(2)}-{day.zfill(2)}", confidence=0.95)
                elif len(groups) == 2:
                    year, month = groups
                    result.set_field("date", f"{year}-{month.zfill(2)}", confidence=0.90)
                return
        
        # 未找到日期
        result.confidence = min(result.confidence, 0.85)
        result.notes.append("未识别到明确日期")
    
    def _extract_clauses(self, text: str, result: ContractData) -> None:
        """提取合同条款"""
        found_clauses = []
        for keyword in self.clause_keywords:
            if keyword in text:
                found_clauses.append(keyword)
        
        if found_clauses:
            result.set_field("clauses", found_clauses, confidence=0.85)
        else:
            result.notes.append("未识别到标准合同条款")


# ---------------------------------------------------------------------------
# 输出格式化
# ---------------------------------------------------------------------------

class OutputFormatter:
    """输出格式化器"""
    
    @staticmethod
    def format_json(data: Dict[str, Any]) -> str:
        """格式化为 JSON"""
        return json.dumps(data, ensure_ascii=False, indent=2)
    
    @staticmethod
    def format_text(data: Dict[str, Any]) -> str:
        """格式化为可读文本"""
        lines = []
        fields = data.get("fields", {})
        for key, value in fields.items():
            lines.append(f"{key}: {value}")
        
        lines.append(f"置信度: {data.get('confidence', 0):.1%}")
        lines.append(f"状态: {data.get('status', '')}")
        
        notes = data.get("notes", [])
        if notes:
            lines.append("提示:")
            for note in notes:
                lines.append(f"  - {note}")
        
        return "\n".join(lines)
    
    @staticmethod
    def format(data: Dict[str, Any], fmt: str = "json") -> str:
        """统一格式化入口"""
        if fmt == "json":
            return OutputFormatter.format_json(data)
        elif fmt == "text":
            return OutputFormatter.format_text(data)
        else:
            raise ValueError(f"不支持的输出格式: {fmt}")


# ---------------------------------------------------------------------------
# 批量处理
# ---------------------------------------------------------------------------

def batch_process(inputs: List[str], processor: Optional[ContractProcessor] = None) -> List[Dict[str, Any]]:
    """
    批量处理多个合同文本
    
    Args:
        inputs: 合同文本列表
        processor: 处理器实例
    
    Returns:
        处理结果列表
    """
    proc = processor or ContractProcessor()
    results = []
    
    for i, text in enumerate(inputs, 1):
        try:
            data = proc.process(text)
            result = data.to_dict()
            result["index"] = i
            results.append(result)
        except ValueError as e:
            results.append({
                "index": i,
                "error": str(e),
                "message": ERROR_MESSAGES.get(str(e), "未知错误"),
            })
    
    return results


# ---------------------------------------------------------------------------
# 自检功能
# ---------------------------------------------------------------------------

def run_selftest() -> bool:
    """
    内置自检逻辑，使用硬编码样例数据
    
    Returns:
        True 表示全部通过
    """
    print("=" * 50)
    print("lawbotics 自检开始")
    print("=" * 50)
    
    # 创建处理器
    processor = ContractProcessor()
    
    # 测试样例（硬编码，不依赖外部文件）
    sample_contract = """
    采购合同
    
    甲方：北京某某科技有限公司
    乙方：上海某某供应链有限公司
    
    合同标的：办公设备采购
    合同金额：人民币 500,000 元
    签订日期：2024年3月15日
    
    合同条款：
    1. 违约责任：如乙方未能按时交付，需支付违约金。
    2. 争议解决：双方协商不成，提交北京仲裁委员会仲裁。
    3. 保密条款：双方应对合同内容保密。
    
    本合同一式两份，甲乙双方各执一份。
    """
    
    # 测试1: 正常处理
    print("\n[测试1] 正常合同处理")
    try:
        result = processor.process(sample_contract)
        data = result.to_dict()
        
        # 宽松断言：检查关键字段存在
        fields = data.get("fields", {})
        assert "party_a" in fields, "未识别甲方"
        assert "party_b" in fields, "未识别乙方"
        assert "amount" in fields, "未识别金额"
        assert "date" in fields, "未识别日期"
        
        # 检查金额格式
        amount_value = fields.get("amount", "")
        assert "500" in amount_value, f"金额识别错误: {amount_value}"
        
        # 检查置信度在合理范围
        conf = data.get("confidence", 0)
        assert 0 <= conf <= 1, f"置信度超出范围: {conf}"
        
        # 检查状态标注合理
        status = data.get("status", "")
        assert status in ["直接输出", "建议复核", "[需核实]"], f"状态异常: {status}"
        
        print(f"  ✓ 通过 (置信度: {conf:.1%}, 状态: {status})")
        print(f"    识别字段: {list(fields.keys())}")
        print(f"    金额: {amount_value}")
    except AssertionError as e:
        print(f"  ✗ 失败: {e}")
        return False
    except Exception as e:
        print(f"  ✗ 异常: {e}")
        return False
    
    # 测试2: 空输入错误处理
    print("\n[测试2] 空输入错误处理")
    try:
        processor.process("")
        print("  ✗ 失败: 空输入未抛出异常")
        return False
    except ValueError as e:
        assert str(e) == "E001", f"错误码错误: {e}"
        print(f"  ✓ 通过 (错误码: {e})")
    except Exception as e:
        print(f"  ✗ 异常: {e}")
        return False
    
    # 测试3: 批量处理
    print("\n[测试3] 批量处理")
    inputs = [
        sample_contract,
        "甲方：测试公司A\n乙方：测试公司B\n金额：10000元",
        "",  # 空输入测试
    ]
    results = batch_process(inputs, processor)
    assert len(results) == 3, f"批量处理数量错误: {len(results)}"
    assert results[0].get("fields"), "第一条结果无字段"
    assert results[2].get("error") == "E001", "第三条应为E001错误"
    print(f"  ✓ 通过 (共{len(results)}条, 错误处理正常)")
    
    # 测试4: 输出格式化
    print("\n[测试4] 输出格式化")
    sample_data = {
        "fields": {"party_a": "测试甲方"},
        "confidence": 0.95,
        "status": "直接输出",
        "notes": []
    }
    
    json_out = OutputFormatter.format(sample_data, "json")
    assert "party_a" in json_out, "JSON输出缺少字段"
    
    text_out = OutputFormatter.format(sample_data, "text")
    assert "测试甲方" in text_out, "文本输出缺少内容"
    
    print("  ✓ 通过 (JSON和文本格式均正常)")
    
    # 测试5: 低置信度场景
    print("\n[测试5] 低置信度场景")
    vague_input = "这是一份合同，内容不完整。"
    result = processor.process(vague_input)
    data = result.to_dict()
    assert data["confidence"] < CONFIDENCE_HIGH, "模糊输入置信度不应过高"
    print(f"  ✓ 通过 (置信度: {data['confidence']:.1%}, 已标注: {data['status']})")
    
    # 测试6: 错误码完整性
    print("\n[测试6] 错误码完整性")
    for code in ["E001", "E002", "E003", "E004", "E005"]:
        assert code in ERROR_MESSAGES, f"缺少错误码: {code}"
        assert ERROR_MESSAGES[code], f"错误码{code}话术为空"
    print("  ✓ 通过 (错误码体系完整)")
    
    # 测试7: 金额格式多样性
    print("\n[测试7] 金额格式多样性")
    test_amounts = [
        ("合同金额：500,000元", "500000"),
        ("总价：￥1,200,000", "1200000"),
        ("费用 8000元", "8000"),
        ("价款：人民币 300,000 元", "300000"),
    ]
    
    for test_text, expected in test_amounts:
        full_text = f"甲方：测试A\n乙方：测试B\n{test_text}"
        result = processor.process(full_text)
        data = result.to_dict()
        amount = data.get("fields", {}).get("amount", "")
        assert expected in amount.replace(",", "").replace("，", ""), f"金额格式未能识别: {test_text}"
    
    print("  ✓ 通过 (4种金额格式均正确识别)")
    
    # 全部通过
    print("\n" + "=" * 50)
    print("自检全部通过 ✓")
    print("=" * 50)
    return True


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------

def main() -> int:
    """主函数"""
    parser = argparse.ArgumentParser(
        description="lawbotics 合同审查工具（仅供学习参考）",
        epilog="示例: python main.py --input '合同文本...' --format json"
    )
    
    parser.add_argument(
        "--input", "-i",
        type=str,
        help="待处理的合同文本内容"
    )
    
    parser.add_argument(
        "--file", "-f",
        type=str,
        help="从文件读取合同文本"
    )
    
    parser.add_argument(
        "--format", "-fmt",
        type=str,
        choices=["json", "text"],
        default="json",
        help="输出格式 (默认: json)"
    )
    
    parser.add_argument(
        "--batch",
        type=str,
        help="批量处理：JSON数组字符串，如 '[text1, text2]'"
    )
    
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检"
    )
    
    args = parser.parse_args()
    
    # 自检模式
    if args.selftest:
        success = run_selftest()
        return 0 if success else 1
    
    # 处理输入
    processor = ContractProcessor()
    
    try:
        # 批量模式
        if args.batch:
            try:
                inputs = json.loads(args.batch)
                if not isinstance(inputs, list):
                    print("E003: 批量输入应为JSON数组", file=sys.stderr)
                    return 1
                results = batch_process(inputs, processor)
                print(json.dumps(results, ensure_ascii=False, indent=2))
                return 0
            except json.JSONDecodeError:
                print("E003: 批量输入JSON格式错误", file=sys.stderr)
                return 1
        
        # 单条模式
        text = args.input
        if args.file:
            try:
                with open(args.file, "r", encoding="utf-8") as f:
                    text = f.read()
            except IOError as e:
                print(f"E003: 文件读取失败 - {e}", file=sys.stderr)
                return 1
        
        if not text:
            print(f"E001: {ERROR_MESSAGES['E001']}", file=sys.stderr)
            return 1
        
        # 处理并输出
        result = processor.process(text)
        output = OutputFormatter.format(result.to_dict(), args.format)
        print(output)
        return 0
        
    except ValueError as e:
        code = str(e)
        message = ERROR_MESSAGES.get(code, f"未知错误（{code}）")
        print(f"{code}: {message}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"E999: 未预期错误 - {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
