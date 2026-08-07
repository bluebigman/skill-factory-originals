#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py - merb-core 独立实现（clean-room 重写）

本脚本依据功能规格独立实现，不包含任何既有代码。
提供命令行入口，支持 --selftest 离线自检。
"""

import argparse
import json
import re
import sys
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 错误码定义（E001-E010）
# ============================================================

ERROR_MESSAGES = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：输入来源、输出格式要求、期望完整度",
    "E003": "输入格式不符合要求，示例：JSON 对象或键值对文本",
    "E004": "这超出了本工具的能力范围，建议：简化输入或使用专业工具",
    "E005": "结果无法确定，建议：检查输入并重试",
    "E006": "内部处理错误，请检查输入数据是否合法",
    "E007": "输出序列化失败，请检查数据格式",
    "E008": "命令行参数错误，请检查参数",
    "E009": "输入内容过长，请精简后重试",
    "E010": "未知错误，请查看日志",
}


# ============================================================
# 核心数据模型
# ============================================================

class StructuredResult:
    """结构化输出结果"""
    
    def __init__(self) -> None:
        self.fields: Dict[str, Any] = {}
        self.confidence: float = 0.0
        self.notes: List[str] = []
        self.warnings: List[str] = []
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "fields": self.fields,
            "confidence": self.confidence,
            "notes": self.notes,
            "warnings": self.warnings,
        }


# ============================================================
# 核心处理逻辑
# ============================================================

class MerbCoreProcessor:
    """merb-core 核心处理器"""
    
    def __init__(self) -> None:
        self.max_input_length = 10000  # 输入长度上限
        self._key_patterns = {
            "name": r"(?:名称|姓名|名字|name)\s*[:：]\s*([^\s,，；;]+)",
            "id": r"(?:编号|ID|id)\s*[:：]\s*([^\s,，；;]+)",
            "type": r"(?:类型|类别|type)\s*[:：]\s*([^\s,，；;]+)",
            "amount": r"(?:数量|金额|amount|count)\s*[:：]\s*([0-9.]+)",
            "date": r"(?:日期|时间|date|time)\s*[:：]\s*([0-9\-/: ]+)",
        }
    
    def validate_input(self, raw_input: str) -> Optional[str]:
        """验证输入，返回错误码或 None"""
        if not raw_input or not raw_input.strip():
            return "E001"
        if len(raw_input.strip()) > self.max_input_length:
            return "E009"
        return None
    
    def parse_input(self, raw_input: str) -> Tuple[Dict[str, Any], float]:
        """
        解析输入内容，识别关键信息。
        返回 (字段字典, 置信度)
        """
        fields: Dict[str, Any] = {}
        text = raw_input.strip()
        
        # 尝试 JSON 解析
        try:
            data = json.loads(text)
            if isinstance(data, dict):
                fields = self._extract_from_dict(data)
            elif isinstance(data, list):
                fields = self._extract_from_list(data)
            else:
                return {}, 0.0
        except json.JSONDecodeError:
            # 非 JSON 格式，尝试键值对解析
            fields = self._extract_from_text(text)
        
        if not fields:
            return {}, 0.0
        
        # 计算置信度
        confidence = self._calculate_confidence(fields, text)
        return fields, confidence
    
    def _extract_from_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """从字典中提取关键字段"""
        result = {}
        for key, value in data.items():
            if isinstance(value, (str, int, float, bool)):
                result[str(key)] = value
            elif isinstance(value, list) and len(value) > 0:
                # 提取列表中的首个元素作为代表
                if isinstance(value[0], (str, int, float, bool)):
                    result[str(key)] = value[0]
                else:
                    result[str(key)] = value
            elif isinstance(value, dict):
                # 嵌套字典，尝试提取常见字段
                for sub_key in ("name", "id", "type", "value"):
                    if sub_key in value:
                        result[f"{key}_{sub_key}"] = value[sub_key]
                        break
        return result
    
    def _extract_from_list(self, data: List[Any]) -> Dict[str, Any]:
        """从列表中提取关键字段"""
        result = {}
        for i, item in enumerate(data[:5]):  # 最多处理前5项
            if isinstance(item, dict):
                for key, value in item.items():
                    if isinstance(value, (str, int, float, bool)):
                        result[f"item{i}_{key}"] = value
            elif isinstance(item, (str, int, float, bool)):
                result[f"item{i}"] = item
        return result
    
    def _extract_from_text(self, text: str) -> Dict[str, Any]:
        """从纯文本中提取关键字段"""
        result = {}
        
        # 尝试匹配键值对模式
        for key, pattern in self._key_patterns.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                value = match.group(1).strip()
                if value:
                    result[key] = value
        
        # 如果没有匹配到任何字段，尝试提取所有冒号分隔的键值对
        if not result:
            pairs = re.findall(r"([\u4e00-\u9fa5\w]+)\s*[:：]\s*([^\n\r]+)", text)
            for key, value in pairs[:10]:
                clean_value = value.strip()
                if clean_value and len(clean_value) < 100:
                    result[key.strip()] = clean_value
        
        return result
    
    def _calculate_confidence(self, fields: Dict[str, Any], original_text: str) -> float:
        """计算置信度"""
        if not fields:
            return 0.0
        
        # 基础置信度
        base_confidence = 0.9
        
        # 字段数量影响
        field_count = len(fields)
        if field_count == 0:
            return 0.0
        elif field_count < 3:
            base_confidence -= 0.1  # 字段少，置信度降低
        
        # 文本长度影响
        text_length = len(original_text)
        if text_length < 20:
            base_confidence -= 0.1  # 文本太短，可能信息不足
        
        # 特殊字符影响
        if re.search(r"[?？!！]", original_text):
            base_confidence -= 0.05  # 存在疑问语气
        
        # 确保置信度在合理范围
        return max(0.0, min(0.99, base_confidence))
    
    def process(self, raw_input: str) -> StructuredResult:
        """核心处理流程"""
        result = StructuredResult()
        
        # Step 1: 输入验证
        error_code = self.validate_input(raw_input)
        if error_code:
            result.warnings.append(ERROR_MESSAGES[error_code])
            result.confidence = 0.0
            return result
        
        # Step 2: 解析输入
        fields, confidence = self.parse_input(raw_input)
        
        if not fields:
            result.warnings.append(ERROR_MESSAGES["E003"])
            result.confidence = 0.0
            return result
        
        result.fields = fields
        result.confidence = confidence
        
        # Step 3: 置信度标注
        if confidence >= 0.9:
            result.notes.append("置信度≥90%，可直接使用")
        elif confidence >= 0.85:
            result.notes.append("置信度85%-90%，建议复核")
        else:
            result.notes.append("[需核实] 置信度<85%，请确认关键信息")
            if confidence < 0.7:
                result.warnings.append(ERROR_MESSAGES["E005"])
        
        return result
    
    def format_output(self, result: StructuredResult, fmt: str = "json") -> str:
        """格式化输出"""
        if fmt == "json":
            try:
                return json.dumps(result.to_dict(), ensure_ascii=False, indent=2)
            except (TypeError, ValueError):
                return json.dumps({"error": ERROR_MESSAGES["E007"]}, ensure_ascii=False)
        elif fmt == "text":
            lines = []
            for key, value in result.fields.items():
                lines.append(f"{key}: {value}")
            lines.append(f"---置信度: {result.confidence:.1%}---")
            for note in result.notes:
                lines.append(f"提示: {note}")
            for warning in result.warnings:
                lines.append(f"警告: {warning}")
            return "\n".join(lines)
        else:
            return json.dumps({"error": ERROR_MESSAGES["E008"]}, ensure_ascii=False)


# ============================================================
# 自检模块（--selftest）
# ============================================================

def run_selftest() -> bool:
    """运行内置自检，返回是否全部通过"""
    processor = MerbCoreProcessor()
    all_passed = True
    
    print("=" * 60)
    print("merb-core 自检开始")
    print("=" * 60)
    
    # 测试用例 1: 空输入
    print("\n[1] 测试空输入...")
    result = processor.process("")
    assert result.confidence == 0.0, "空输入置信度应为0"
    assert any(ERROR_MESSAGES["E001"] in w for w in result.warnings), "应包含E001错误"
    print("  ✓ 通过")
    
    # 测试用例 2: 基本键值对输入
    print("\n[2] 测试基本键值对输入...")
    test_input = "名称: 测试项目, 类型: 文档, 数量: 5"
    result = processor.process(test_input)
    assert len(result.fields) >= 2, "应提取至少2个字段"
    assert result.confidence > 0.5, "置信度应大于0.5"
    print("  ✓ 通过")
    
    # 测试用例 3: JSON 输入
    print("\n[3] 测试 JSON 输入...")
    test_json = '{"name": "项目A", "id": "P001", "type": "task", "count": 10}'
    result = processor.process(test_json)
    assert "name" in result.fields, "应提取name字段"
    assert "id" in result.fields, "应提取id字段"
    assert result.confidence > 0.5, "置信度应大于0.5"
    print("  ✓ 通过")
    
    # 测试用例 4: 中文键值对
    print("\n[4] 测试中文键值对提取...")
    test_cn = "姓名：张三，编号：ZH001，日期：2024-01-15"
    result = processor.process(test_cn)
    assert "姓名" in result.fields or "name" in result.fields, "应提取姓名"
    assert "编号" in result.fields or "id" in result.fields, "应提取编号"
    assert result.confidence > 0.5, "置信度应大于0.5"
    print("  ✓ 通过")
    
    # 测试用例 5: 列表输入
    print("\n[5] 测试列表输入...")
    test_list = '[{"name": "item1", "value": 100}, {"name": "item2", "value": 200}]'
    result = processor.process(test_list)
    assert len(result.fields) > 0, "应提取至少1个字段"
    assert result.confidence > 0.5, "置信度应大于0.5"
    print("  ✓ 通过")
    
    # 测试用例 6: 置信度分级
    print("\n[6] 测试置信度分级...")
    # 高置信度用例
    high_conf_input = "名称: 完整项目, 类型: 报告, 数量: 100, 日期: 2024-06-01, 备注: 详细信息"
    result_high = processor.process(high_conf_input)
    assert result_high.confidence >= 0.85, "完整输入置信度应较高"
    
    # 低置信度用例
    low_conf_input = "?"
    result_low = processor.process(low_conf_input)
    assert result_low.confidence < 0.85, "不完整输入置信度应较低"
    print("  ✓ 通过")
    
    # 测试用例 7: 输出格式
    print("\n[7] 测试输出格式...")
    test_input = "名称: 格式测试, 类型: 文档"
    result = processor.process(test_input)
    json_output = processor.format_output(result, "json")
    text_output = processor.format_output(result, "text")
    assert json_output.startswith("{"), "JSON输出应以{开头"
    assert "置信度" in text_output, "文本输出应包含置信度"
    print("  ✓ 通过")
    
    # 测试用例 8: 错误处理
    print("\n[8] 测试错误处理...")
    # 超长输入
    long_input = "x" * 20000
    result = processor.process(long_input)
    assert any(ERROR_MESSAGES["E009"] in w for w in result.warnings), "超长输入应返回E009"
    print("  ✓ 通过")
    
    # 测试用例 9: 批量处理概念验证
    print("\n[9] 测试批量处理...")
    test_inputs = [
        "名称: 项目1, 类型: 开发",
        "名称: 项目2, 类型: 测试",
        '{"name": "项目3", "type": "部署"}',
    ]
    results = [processor.process(inp) for inp in test_inputs]
    assert len(results) == 3, "应处理3个输入"
    assert all(r.confidence > 0 for r in results), "所有结果置信度应大于0"
    print("  ✓ 通过")
    
    # 测试用例 10: 自定义格式
    print("\n[10] 测试自定义格式...")
    test_input = "名称: 自定义, 类型: 格式"
    result = processor.process(test_input)
    custom_format = processor.format_output(result, "text")
    assert "名称" in custom_format or "name" in custom_format, "应包含名称字段"
    print("  ✓ 通过")
    
    print("\n" + "=" * 60)
    print(f"自检完成: {'全部通过' if all_passed else '存在失败项'}")
    print("=" * 60)
    
    return all_passed


# ============================================================
# 命令行入口
# ============================================================

def main() -> int:
    """主入口"""
    parser = argparse.ArgumentParser(
        description="merb-core: 结构化数据处理工具",
        epilog="示例: python main.py --input '名称: 项目, 类型: 报告' --format json"
    )
    
    parser.add_argument(
        "--input", "-i",
        type=str,
        help="待处理的输入内容（数据/文本/JSON）"
    )
    
    parser.add_argument(
        "--format", "-f",
        choices=["json", "text"],
        default="json",
        help="输出格式（默认: json）"
    )
    
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检（不读取外部文件，不访问网络）"
    )
    
    parser.add_argument(
        "--version",
        action="version",
        version="merb-core 1.0.0"
    )
    
    args = parser.parse_args()
    
    # 自检模式
    if args.selftest:
        success = run_selftest()
        return 0 if success else 1
    
    # 正常处理模式
    if not args.input:
        print(f"错误: {ERROR_MESSAGES['E001']}", file=sys.stderr)
        return 1
    
    processor = MerbCoreProcessor()
    result = processor.process(args.input)
    
    # 输出结果
    output = processor.format_output(result, args.format)
    print(output)
    
    # 如果有警告，输出到 stderr
    for warning in result.warnings:
        print(f"警告: {warning}", file=sys.stderr)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
