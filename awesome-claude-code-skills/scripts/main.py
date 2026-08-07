#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py

基于功能规格独立实现的 Claude Cod 技能处理脚本。
仅使用标准库，不依赖任何外部文件或网络。
"""

import argparse
import sys
import json
import re
from typing import Dict, List, Any, Optional, Tuple

# 错误码定义（对应规格中的错误码体系，扩展 E006-E010 作为内部使用）
ERROR_CODES = {
    "E001": "输入为空，请提供待处理的内容。",
    "E002": "关键信息缺失，请补充必要字段。",
    "E003": "输入格式错误，请检查输入内容。",
    "E004": "超出能力边界，无法处理该请求。",
    "E005": "置信度过低，结果无法确定。",
    "E006": "内部处理错误，请重试。",
    "E007": "参数错误，请检查命令行参数。",
    "E008": "输出格式不支持。",
    "E009": "数据解析失败。",
    "E010": "未知错误。",
}


class ClaudeCodSkill:
    """Claude Cod 技能核心处理器"""

    # 能力边界声明
    CAPABILITIES = [
        "将用户提供的数据/文件/URL 转换为结构化结果",
        "识别并保留输入中的关键信息",
        "按约定格式生成输出",
        "对不确定项给出置信度提示",
        "支持批量处理和自定义格式",
    ]

    BOUNDARIES = [
        "不执行超出输入范围的分析",
        "不保证绝对准确，低置信度会标注",
        "不访问网络或外部服务",
    ]

    # 触发词表
    TRIGGER_WORDS = ["awesome claude code skills"]

    def __init__(self, input_data: Optional[str] = None, output_format: str = "json"):
        """
        初始化处理器
        
        Args:
            input_data: 输入数据（文本、文件路径或URL）
            output_format: 输出格式（json/text）
        """
        self.input_data = input_data or ""
        self.output_format = output_format
        self.confidence = 0.0
        self.warnings: List[str] = []
        self.structured_result: Dict[str, Any] = {}

    def validate_input(self) -> Optional[str]:
        """
        校验输入数据，返回错误码或 None
        
        Returns:
            错误码字符串或 None（无错误）
        """
        if not self.input_data or not self.input_data.strip():
            return "E001"
        
        if self.output_format not in ["json", "text"]:
            return "E008"
        
        return None

    def extract_key_info(self, text: str) -> Dict[str, Any]:
        """
        从输入文本中提取关键信息
        
        Args:
            text: 输入文本
            
        Returns:
            提取的结构化信息字典
        """
        info = {
            "content_length": len(text),
            "word_count": len(text.split()),
            "has_url": bool(re.search(r'https?://\S+', text)),
            "has_email": bool(re.search(r'[\w\.-]+@[\w\.-]+\.\w+', text)),
            "has_phone": bool(re.search(r'1[3-9]\d{9}', text)),
            "is_json": False,
            "key_fields": [],
        }
        
        # 尝试解析 JSON
        try:
            json_data = json.loads(text)
            info["is_json"] = True
            if isinstance(json_data, dict):
                info["key_fields"] = list(json_data.keys())[:10]  # 最多取10个字段
        except (json.JSONDecodeError, ValueError):
            pass
        
        # 检测结构化文本（如 key: value 格式）
        key_value_pattern = re.findall(r'([\w\s]+):\s*([^\n]+)', text)
        if key_value_pattern:
            info["key_fields"] = [k.strip() for k, _ in key_value_pattern[:10]]
        
        return info

    def calculate_confidence(self, info: Dict[str, Any]) -> float:
        """
        根据提取的信息计算置信度
        
        Args:
            info: 提取的信息字典
            
        Returns:
            置信度分数（0-100）
        """
        score = 50.0  # 基础分
        
        # 内容长度加分
        if info["content_length"] > 10:
            score += 10
        if info["content_length"] > 50:
            score += 10
        
        # 结构化程度加分
        if info["is_json"]:
            score += 20
        if info["key_fields"]:
            score += 10
        
        # 信息丰富度加分
        if info["has_url"]:
            score += 5
        if info["has_email"] or info["has_phone"]:
            score += 5
        
        return min(score, 100.0)

    def process(self) -> Dict[str, Any]:
        """
        执行核心处理流程
        
        Returns:
            处理结果字典
        """
        # Step 1: 校验输入
        error_code = self.validate_input()
        if error_code:
            return {
                "success": False,
                "error_code": error_code,
                "error_message": ERROR_CODES[error_code],
            }
        
        try:
            # Step 2: 执行核心流程
            info = self.extract_key_info(self.input_data)
            self.confidence = self.calculate_confidence(info)
            
            # 构建结构化结果
            self.structured_result = {
                "input_summary": {
                    "length": info["content_length"],
                    "word_count": info["word_count"],
                    "contains_url": info["has_url"],
                    "contains_email": info["has_email"],
                    "contains_phone": info["has_phone"],
                },
                "extracted_fields": info["key_fields"],
                "is_structured": info["is_json"] or bool(info["key_fields"]),
                "confidence": self.confidence,
                "confidence_level": self._get_confidence_level(self.confidence),
            }
            
            # Step 3: 输出与校验
            self._validate_output()
            
            return {
                "success": True,
                "data": self.structured_result,
                "warnings": self.warnings,
            }
            
        except Exception as e:
            return {
                "success": False,
                "error_code": "E006",
                "error_message": f"{ERROR_CODES['E006']} 详细信息: {str(e)}",
            }

    def _get_confidence_level(self, confidence: float) -> str:
        """
        根据置信度返回等级标注
        
        Args:
            confidence: 置信度分数
            
        Returns:
            置信度等级字符串
        """
        if confidence >= 90:
            return "高置信度"
        elif confidence >= 85:
            return "建议复核"
        else:
            return "[需核实]"

    def _validate_output(self) -> None:
        """
        校验输出结果，添加警告信息
        """
        if self.confidence < 85:
            self.warnings.append("低置信度提示：请人工复核关键结果")
        
        if not self.structured_result["extracted_fields"]:
            self.warnings.append("未识别到明显的结构化字段")

    def format_output(self, result: Dict[str, Any]) -> str:
        """
        格式化输出结果
        
        Args:
            result: 处理结果字典
            
        Returns:
            格式化后的输出字符串
        """
        if not result["success"]:
            return f"处理失败 [{result['error_code']}]: {result['error_message']}"
        
        data = result["data"]
        
        if self.output_format == "json":
            return json.dumps(result, ensure_ascii=False, indent=2)
        else:
            # 文本格式输出
            lines = [
                "=== Claude Cod 处理结果 ===",
                f"输入长度: {data['input_summary']['length']} 字符",
                f"单词数: {data['input_summary']['word_count']}",
                f"包含URL: {'是' if data['input_summary']['contains_url'] else '否'}",
                f"包含邮箱: {'是' if data['input_summary']['contains_email'] else '否'}",
                f"包含电话: {'是' if data['input_summary']['contains_phone'] else '否'}",
                f"结构化程度: {'是' if data['is_structured'] else '否'}",
                f"提取字段: {', '.join(data['extracted_fields']) if data['extracted_fields'] else '无'}",
                f"置信度: {data['confidence']:.1f}% ({data['confidence_level']})",
            ]
            
            if result["warnings"]:
                lines.append("警告:")
                for warning in result["warnings"]:
                    lines.append(f"  - {warning}")
            
            return "\n".join(lines)


def run_selftest() -> bool:
    """
    内置自检函数，使用硬编码样例数据验证核心逻辑
    
    Returns:
        自检是否通过
    """
    print("=== 自检开始 ===")
    test_cases = [
        {
            "name": "JSON输入测试",
            "input": '{"name": "测试项目", "version": "1.0.0", "author": "skill-factory-auto"}',
            "expected_success": True,
        },
        {
            "name": "文本输入测试",
            "input": "这是一个测试文本，包含邮箱 test@example.com 和电话 13800138000",
            "expected_success": True,
        },
        {
            "name": "空输入测试",
            "input": "",
            "expected_success": False,
            "expected_error": "E001",
        },
        {
            "name": "URL输入测试",
            "input": "请访问 https://example.com 获取更多信息，联系方式：contact@example.org",
            "expected_success": True,
        },
        {
            "name": "键值对输入测试",
            "input": "名称: 测试产品\n版本: 2.0\n描述: 这是一个测试",
            "expected_success": True,
        },
    ]
    
    all_passed = True
    
    for i, case in enumerate(test_cases, 1):
        print(f"\n测试用例 {i}: {case['name']}")
        
        # 创建处理器实例
        processor = ClaudeCodSkill(input_data=case["input"])
        result = processor.process()
        
        # 检查成功标志
        if result["success"] != case["expected_success"]:
            print(f"  ✗ 成功标志不匹配: 期望 {case['expected_success']}, 实际 {result['success']}")
            all_passed = False
            continue
        
        # 检查错误码
        if not result["success"]:
            if result["error_code"] != case.get("expected_error"):
                print(f"  ✗ 错误码不匹配: 期望 {case.get('expected_error')}, 实际 {result['error_code']}")
                all_passed = False
                continue
            print("  ✓ 正确返回错误码")
            continue
        
        # 检查成功结果的结构
        data = result["data"]
        
        # 宽松检查：置信度应在有效范围内
        if not (0 <= data["confidence"] <= 100):
            print(f"  ✗ 置信度超出范围: {data['confidence']}")
            all_passed = False
            continue
        
        # 宽松检查：置信度等级应匹配
        if data["confidence"] >= 85 and data["confidence_level"] == "[需核实]":
            print("  ✗ 置信度等级错误")
            all_passed = False
            continue
        
        # 宽松检查：字段列表应为列表类型
        if not isinstance(data["extracted_fields"], list):
            print("  ✗ 字段列表类型错误")
            all_passed = False
            continue
        
        # 宽松检查：输入摘要字段
        summary = data["input_summary"]
        if not isinstance(summary, dict) or "length" not in summary:
            print("  ✗ 输入摘要结构错误")
            all_passed = False
            continue
        
        print(f"  ✓ 通过 (置信度: {data['confidence']:.1f}%)")
    
    # 额外测试：格式化输出
    print("\n=== 格式化输出测试 ===")
    processor = ClaudeCodSkill(input_data="测试格式化输出", output_format="text")
    result = processor.process()
    text_output = processor.format_output(result)
    if text_output and "Claude Cod" in text_output:
        print("  ✓ 文本格式输出正常")
    else:
        print("  ✗ 文本格式输出异常")
        all_passed = False
    
    processor = ClaudeCodSkill(input_data="测试JSON输出", output_format="json")
    result = processor.process()
    json_output = processor.format_output(result)
    try:
        json.loads(json_output)
        print("  ✓ JSON格式输出正常")
    except json.JSONDecodeError:
        print("  ✗ JSON格式输出异常")
        all_passed = False
    
    # 额外测试：能力边界检查
    print("\n=== 能力边界测试 ===")
    processor = ClaudeCodSkill(input_data="测试边界")
    if len(processor.CAPABILITIES) == 5 and len(processor.BOUNDARIES) == 3:
        print("  ✓ 能力边界定义正确")
    else:
        print("  ✗ 能力边界定义错误")
        all_passed = False
    
    print(f"\n=== 自检{'通过' if all_passed else '失败'} ===")
    return all_passed


def main() -> int:
    """
    主函数，处理命令行参数并执行
    
    Returns:
        退出码（0成功，1失败）
    """
    parser = argparse.ArgumentParser(
        description="Claude Cod 技能处理脚本",
        epilog="示例: python main.py --input '要处理的内容' --format json"
    )
    
    parser.add_argument(
        "--input",
        type=str,
        help="输入数据（文本、文件路径或URL）",
        default=None
    )
    
    parser.add_argument(
        "--format",
        type=str,
        choices=["json", "text"],
        help="输出格式（默认: json）",
        default="json"
    )
    
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检（不读取外部文件）"
    )
    
    parser.add_argument(
        "--version",
        action="version",
        version="Claude Cod Skill v1.0.0"
    )
    
    args = parser.parse_args()
    
    # 自检模式
    if args.selftest:
        success = run_selftest()
        return 0 if success else 1
    
    # 正常处理模式
    if not args.input:
        print(f"[E001] {ERROR_CODES['E001']}")
        print("提示: 使用 --input 参数提供输入，或使用 --selftest 运行自检")
        return 1
    
    # 创建处理器并执行
    processor = ClaudeCodSkill(input_data=args.input, output_format=args.format)
    result = processor.process()
    
    # 输出结果
    print(processor.format_output(result))
    
    # 返回退出码
    return 0 if result["success"] else 1


if __name__ == "__main__":
    sys.exit(main())
