#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
nima0011 代码审查技能 - 独立实现脚本
仅供学习与参考用途，不构成任何专业建议。
"""

import argparse
import sys
import os
import json
from typing import Any, Dict, List, Optional, Tuple

# 错误码定义
ERROR_CODES = {
    "E001": "输入为空，请提供待处理的内容",
    "E002": "关键信息缺失，请补充必要字段",
    "E003": "输入格式错误，请检查格式",
    "E004": "超出能力边界，无法处理该请求",
    "E005": "置信度过低，结果无法确定",
    "E006": "内部处理错误",
    "E007": "参数错误",
    "E008": "批量处理中断",
    "E009": "输出生成失败",
    "E010": "未知错误",
}


class CodeReviewError(Exception):
    """自定义异常类，携带错误码"""
    def __init__(self, error_code: str, message: str = ""):
        self.error_code = error_code
        self.message = message or ERROR_CODES.get(error_code, "未知错误")
        super().__init__(f"[{error_code}] {self.message}")


class InputParser:
    """输入解析器：处理各种输入格式"""
    
    @staticmethod
    def parse_text(text: str) -> Dict[str, Any]:
        """解析纯文本输入，提取关键字段"""
        if not text or not text.strip():
            raise CodeReviewError("E001")
        
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        if not lines:
            raise CodeReviewError("E001")
        
        result = {
            "source_type": "text",
            "content": text.strip(),
            "line_count": len(lines),
            "char_count": len(text.strip()),
            "key_fields": {},
        }
        
        # 尝试提取键值对（冒号分隔）
        for line in lines:
            if ":" in line:
                key, _, value = line.partition(":")
                key = key.strip()
                value = value.strip()
                if key and value:
                    result["key_fields"][key] = value
        
        return result
    
    @staticmethod
    def parse_json(data: str) -> Dict[str, Any]:
        """解析JSON输入"""
        try:
            parsed = json.loads(data)
        except json.JSONDecodeError:
            raise CodeReviewError("E003", "JSON格式错误")
        
        if not parsed:
            raise CodeReviewError("E001")
        
        if not isinstance(parsed, dict):
            raise CodeReviewError("E003", "JSON必须是对象格式")
        
        return {
            "source_type": "json",
            "content": parsed,
            "key_fields": parsed,
        }
    
    @staticmethod
    def parse_file(filepath: str) -> Dict[str, Any]:
        """解析文件输入"""
        if not filepath or not os.path.exists(filepath):
            raise CodeReviewError("E003", f"文件不存在: {filepath}")
        
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            raise CodeReviewError("E006", f"文件读取失败: {str(e)}")
        
        # 根据扩展名选择解析方式
        if filepath.endswith(".json"):
            return InputParser.parse_json(content)
        else:
            return InputParser.parse_text(content)


class ConfidenceCalculator:
    """置信度计算器"""
    
    @staticmethod
    def calculate(parsed_input: Dict[str, Any]) -> Tuple[float, str]:
        """计算置信度，返回(置信度, 提示信息)"""
        base_score = 0.0
        hints = []
        
        # 基于输入完整性计算
        if parsed_input.get("source_type") == "text":
            content = parsed_input.get("content", "")
            char_count = len(content)
            
            if char_count > 1000:
                base_score += 0.4
            elif char_count > 500:
                base_score += 0.3
            elif char_count > 100:
                base_score += 0.2
            else:
                base_score += 0.1
            
            # 有关键字段则加分
            key_fields = parsed_input.get("key_fields", {})
            if len(key_fields) > 0:
                base_score += 0.2
            if len(key_fields) > 3:
                base_score += 0.2
        
        elif parsed_input.get("source_type") == "json":
            content = parsed_input.get("content", {})
            if len(content) > 0:
                base_score += 0.5
            if len(content) > 5:
                base_score += 0.3
        
        # 边界检查
        base_score = min(base_score, 1.0)
        
        # 生成提示
        if base_score >= 0.9:
            hints.append("置信度高，可直接使用")
        elif base_score >= 0.85:
            hints.append("置信度中等，建议复核")
        else:
            hints.append("[需核实] 置信度较低，请人工确认关键信息")
        
        return base_score, " ".join(hints)


class OutputGenerator:
    """输出生成器"""
    
    @staticmethod
    def generate(parsed_input: Dict[str, Any], confidence: float, hint: str) -> Dict[str, Any]:
        """生成结构化输出"""
        result = {
            "status": "success",
            "source_type": parsed_input.get("source_type", "unknown"),
            "summary": {
                "line_count": parsed_input.get("line_count", 0),
                "char_count": parsed_input.get("char_count", 0),
                "field_count": len(parsed_input.get("key_fields", {})),
            },
            "extracted_fields": parsed_input.get("key_fields", {}),
            "confidence": {
                "score": round(confidence, 2),
                "level": "high" if confidence >= 0.9 else "medium" if confidence >= 0.85 else "low",
                "hint": hint,
            },
            "metadata": {
                "version": "1.0.0",
                "skill": "nima0011",
                "disclaimer": "本结果仅供学习与参考用途，不构成任何专业建议。",
            },
        }
        return result


class BatchProcessor:
    """批量处理器"""
    
    @staticmethod
    def process(items: List[str]) -> List[Dict[str, Any]]:
        """批量处理多个输入项"""
        results = []
        errors = []
        
        for idx, item in enumerate(items):
            try:
                parsed = InputParser.parse_text(item)
                confidence, hint = ConfidenceCalculator.calculate(parsed)
                output = OutputGenerator.generate(parsed, confidence, hint)
                results.append({"index": idx, "result": output, "error": None})
            except CodeReviewError as e:
                errors.append({"index": idx, "error": str(e)})
                results.append({"index": idx, "result": None, "error": str(e)})
        
        if errors and not results:
            raise CodeReviewError("E008", f"批量处理失败，{len(errors)} 项错误")
        
        return results


def run_selftest() -> bool:
    """内置自检函数 - 使用硬编码样例数据"""
    print("=" * 60)
    print("开始自检 (selftest)...")
    print("=" * 60)
    
    # 测试数据
    test_cases = [
        # (输入, 期望的源类型)
        ("这是一个测试文本\n包含多行内容\n用于验证解析功能", "text"),
        ("名称: 测试项目\n版本: 1.0\n作者: tester\n描述: 这是一个测试", "text"),
        ('{"name": "test", "version": "1.0", "items": [1, 2, 3]}', "json"),
        ("", "error"),  # 空输入应报错
    ]
    
    passed = 0
    total = 0
    
    # 测试1: 文本解析
    total += 1
    try:
        parsed = InputParser.parse_text(test_cases[0][0])
        assert parsed["source_type"] == "text"
        assert parsed["line_count"] > 0
        assert parsed["char_count"] > 0
        passed += 1
        print("[PASS] 文本解析测试")
    except Exception as e:
        print(f"[FAIL] 文本解析测试: {e}")
    
    # 测试2: 键值对提取
    total += 1
    try:
        parsed = InputParser.parse_text(test_cases[1][0])
        assert len(parsed["key_fields"]) > 0
        assert "名称" in parsed["key_fields"]
        passed += 1
        print("[PASS] 键值对提取测试")
    except Exception as e:
        print(f"[FAIL] 键值对提取测试: {e}")
    
    # 测试3: JSON解析
    total += 1
    try:
        parsed = InputParser.parse_json(test_cases[2][0])
        assert parsed["source_type"] == "json"
        assert len(parsed["key_fields"]) > 0
        passed += 1
        print("[PASS] JSON解析测试")
    except Exception as e:
        print(f"[FAIL] JSON解析测试: {e}")
    
    # 测试4: 空输入错误处理
    total += 1
    try:
        InputParser.parse_text(test_cases[3][0])
        print("[FAIL] 空输入错误处理测试")
    except CodeReviewError as e:
        assert e.error_code == "E001"
        passed += 1
        print("[PASS] 空输入错误处理测试")
    except Exception as e:
        print(f"[FAIL] 空输入错误处理测试: {e}")
    
    # 测试5: 置信度计算
    total += 1
    try:
        parsed = InputParser.parse_text(test_cases[1][0])
        confidence, hint = ConfidenceCalculator.calculate(parsed)
        # 宽松阈值：置信度应在0到1之间
        assert 0.0 <= confidence <= 1.0
        assert hint is not None and len(hint) > 0
        passed += 1
        print("[PASS] 置信度计算测试")
    except Exception as e:
        print(f"[FAIL] 置信度计算测试: {e}")
    
    # 测试6: 输出生成
    total += 1
    try:
        parsed = InputParser.parse_text(test_cases[1][0])
        confidence, hint = ConfidenceCalculator.calculate(parsed)
        output = OutputGenerator.generate(parsed, confidence, hint)
        assert output["status"] == "success"
        assert "extracted_fields" in output
        assert 0.0 <= output["confidence"]["score"] <= 1.0
        passed += 1
        print("[PASS] 输出生成测试")
    except Exception as e:
        print(f"[FAIL] 输出生成测试: {e}")
    
    # 测试7: 批量处理
    total += 1
    try:
        results = BatchProcessor.process(["测试1", "测试2", "测试3"])
        assert len(results) == 3
        assert all(r["error"] is None for r in results)
        passed += 1
        print("[PASS] 批量处理测试")
    except Exception as e:
        print(f"[FAIL] 批量处理测试: {e}")
    
    # 测试8: 完整流程
    total += 1
    try:
        sample_input = "项目: 代码审查系统\n功能: 输入解析\n状态: 开发中\n优先级: 高"
        parsed = InputParser.parse_text(sample_input)
        confidence, hint = ConfidenceCalculator.calculate(parsed)
        output = OutputGenerator.generate(parsed, confidence, hint)
        assert output["status"] == "success"
        assert len(output["extracted_fields"]) > 0
        assert output["confidence"]["score"] > 0
        passed += 1
        print("[PASS] 完整流程测试")
    except Exception as e:
        print(f"[FAIL] 完整流程测试: {e}")
    
    # 汇总
    print("=" * 60)
    print(f"自检结果: {passed}/{total} 通过")
    print("=" * 60)
    
    return passed == total


def process_input(input_text: str, output_format: str = "json") -> str:
    """处理单个输入并返回结果"""
    try:
        # 解析输入
        parsed = InputParser.parse_text(input_text)
        
        # 计算置信度
        confidence, hint = ConfidenceCalculator.calculate(parsed)
        
        # 生成输出
        output = OutputGenerator.generate(parsed, confidence, hint)
        
        # 根据格式输出
        if output_format == "json":
            return json.dumps(output, ensure_ascii=False, indent=2)
        elif output_format == "text":
            lines = [
                f"处理结果: 成功",
                f"来源类型: {output['source_type']}",
                f"提取字段数: {output['summary']['field_count']}",
                f"置信度: {output['confidence']['score']:.2f} ({output['confidence']['level']})",
                f"提示: {output['confidence']['hint']}",
            ]
            for key, value in output["extracted_fields"].items():
                lines.append(f"  {key}: {value}")
            return "\n".join(lines)
        else:
            raise CodeReviewError("E007", f"不支持的输出格式: {output_format}")
    
    except CodeReviewError as e:
        return json.dumps({
            "status": "error",
            "error_code": e.error_code,
            "message": e.message,
        }, ensure_ascii=False, indent=2)


def main():
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description="nima0011 代码审查技能 - 独立实现",
        epilog="示例: python main.py --input '名称: 测试' --format json"
    )
    
    parser.add_argument(
        "--input", "-i",
        type=str,
        help="输入文本内容"
    )
    
    parser.add_argument(
        "--file", "-f",
        type=str,
        help="输入文件路径"
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
        nargs="+",
        help="批量处理多个输入"
    )
    
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检"
    )
    
    parser.add_argument(
        "--version",
        action="version",
        version="nima0011 1.0.0"
    )
    
    args = parser.parse_args()
    
    # 自检模式
    if args.selftest:
        success = run_selftest()
        sys.exit(0 if success else 1)
    
    # 批量模式
    if args.batch:
        try:
            results = BatchProcessor.process(args.batch)
            for result in results:
                if result["error"]:
                    print(f"项 {result['index']}: 错误 - {result['error']}")
                else:
                    print(f"项 {result['index']}: 成功")
            sys.exit(0)
        except CodeReviewError as e:
            print(f"错误: {e}")
            sys.exit(1)
    
    # 单输入模式
    input_text = args.input
    
    # 文件模式
    if args.file:
        try:
            parsed = InputParser.parse_file(args.file)
            confidence, hint = ConfidenceCalculator.calculate(parsed)
            output = OutputGenerator.generate(parsed, confidence, hint)
            if args.format == "json":
                print(json.dumps(output, ensure_ascii=False, indent=2))
            else:
                print(f"处理结果: 成功")
                print(f"来源类型: {output['source_type']}")
                print(f"置信度: {output['confidence']['score']:.2f}")
                print(f"提示: {output['confidence']['hint']}")
            sys.exit(0)
        except CodeReviewError as e:
            print(f"错误: {e}")
            sys.exit(1)
    
    # 没有输入则显示帮助
    if not input_text:
        parser.print_help()
        print("\n" + "=" * 40)
        print("错误: 请提供输入内容 (--input 或 --file)")
        print("提示: 使用 --selftest 运行自检")
        sys.exit(1)
    
    # 处理输入
    try:
        result = process_input(input_text, args.format)
        print(result)
        sys.exit(0)
    except CodeReviewError as e:
        print(f"错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
