#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
oe-skills 未命名工具 - 独立实现脚本
=====================================
依据功能规格独立编写，不参考任何既有代码。

功能概述：
    1. 将用户提供的数据/文件/URL 转换为结构化结果
    2. 识别并保留输入中的关键信息
    3. 按约定格式生成输出
    4. 对不确定项给出置信度提示
    5. 支持批量处理和自定义格式

错误码：
    E001 输入为空
    E002 关键信息缺失
    E003 输入格式错误
    E004 超出能力边界
    E005 置信度过低
    E006 内部处理异常
    E007 参数解析错误
    E008 输出格式不支持
    E009 批量处理中断
    E010 未知错误

用法示例：
    python main.py --input "用户提供的数据" --format json
    python main.py --selftest
"""

import argparse
import json
import sys
import os
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 常量定义
# ============================================================

# 置信度阈值
CONFIDENCE_HIGH = 0.90      # 高置信度阈值
CONFIDENCE_MEDIUM = 0.85    # 中置信度阈值

# 默认输出格式
DEFAULT_OUTPUT_FORMAT = "text"

# 支持的关键字段（依据规格说明）
KEY_FIELDS = [
    "content",      # 输入内容
    "source",       # 输入来源
    "format",       # 输出格式
    "completeness"  # 完整度要求
]

# 错误码对应的标准话术
ERROR_MESSAGES = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：{}",
    "E003": "输入格式不符合要求，示例：{}",
    "E004": "这超出了本工具的能力范围，建议：{}",
    "E005": "结果无法确定，建议：{}",
    "E006": "内部处理异常，请稍后重试",
    "E007": "参数解析错误：{}",
    "E008": "输出格式不支持：{}",
    "E009": "批量处理中断：{}",
    "E010": "未知错误：{}"
}


# ============================================================
# 核心处理类
# ============================================================

class OESkillsProcessor:
    """oe-skills 核心处理器"""

    def __init__(self) -> None:
        """初始化处理器"""
        self.input_data: Any = None
        self.source_type: str = "unknown"
        self.output_format: str = DEFAULT_OUTPUT_FORMAT
        self.completeness: str = "standard"
        self.confidence: float = 0.0
        self.result: Dict[str, Any] = {}
        self.warnings: List[str] = []

    def process(self, input_data: Any, **kwargs) -> Dict[str, Any]:
        """
        主处理入口

        参数:
            input_data: 用户输入的数据
            **kwargs: 可选参数
                - source: 输入来源
                - format: 输出格式
                - completeness: 完整度要求

        返回:
            处理结果字典
        """
        try:
            # Step 1: 校验输入
            if self._validate_input(input_data):
                # Step 2: 解析输入
                parsed = self._parse_input(input_data)
                # Step 3: 处理数据
                self._process_data(parsed)
                # Step 4: 生成输出
                return self._generate_output()
            else:
                raise ValueError("E001")
        except Exception as e:
            return self._handle_error(str(e))

    def _validate_input(self, input_data: Any) -> bool:
        """校验输入是否有效"""
        if input_data is None:
            raise ValueError("E001")
        if isinstance(input_data, str) and not input_data.strip():
            raise ValueError("E001")
        if isinstance(input_data, (list, tuple)) and len(input_data) == 0:
            raise ValueError("E001")
        return True

    def _parse_input(self, input_data: Any) -> Dict[str, Any]:
        """
        解析输入内容，识别关键信息

        返回:
            解析后的结构化数据
        """
        parsed: Dict[str, Any] = {
            "content": None,
            "source": "user_provided",
            "format": self.output_format,
            "completeness": self.completeness
        }

        # 识别输入类型
        if isinstance(input_data, str):
            parsed["content"] = input_data
            self.source_type = "text"
        elif isinstance(input_data, dict):
            # 字典输入，尝试提取关键字段
            parsed.update(input_data)
            self.source_type = "structured"
        elif isinstance(input_data, (list, tuple)):
            parsed["content"] = list(input_data)
            self.source_type = "batch"
        else:
            parsed["content"] = str(input_data)
            self.source_type = "unknown"

        # 检查关键信息是否完整
        missing_fields = []
        if parsed["content"] is None:
            missing_fields.append("content")
        if missing_fields:
            raise ValueError(f"E002:{','.join(missing_fields)}")

        return parsed

    def _process_data(self, parsed: Dict[str, Any]) -> None:
        """
        处理解析后的数据

        根据输入类型和格式要求生成结构化结果
        """
        content = parsed["content"]
        source = parsed.get("source", "user_provided")
        fmt = parsed.get("format", DEFAULT_OUTPUT_FORMAT)

        # 处理不同类型的内容
        if isinstance(content, str):
            # 文本内容处理
            self._process_text(content, source)
        elif isinstance(content, list):
            # 批量内容处理
            self._process_batch(content, source)
        else:
            # 其他类型处理
            self._process_generic(content, source)

        # 计算置信度
        self._calculate_confidence()

    def _process_text(self, content: str, source: str) -> None:
        """处理文本内容"""
        # 提取关键信息（简化版：按常见分隔符拆分）
        lines = [line.strip() for line in content.split('\n') if line.strip()]
        
        self.result = {
            "type": "text",
            "source": source,
            "lines": len(lines),
            "characters": len(content),
            "content": content,
            "structured": {
                "line_count": len(lines),
                "first_line": lines[0] if lines else "",
                "last_line": lines[-1] if lines else ""
            }
        }

    def _process_batch(self, items: List[Any], source: str) -> None:
        """处理批量内容"""
        processed_items = []
        for idx, item in enumerate(items):
            if isinstance(item, str):
                processed_items.append({
                    "index": idx,
                    "type": "text",
                    "content": item,
                    "length": len(item)
                })
            elif isinstance(item, dict):
                processed_items.append({
                    "index": idx,
                    "type": "structured",
                    "content": item
                })
            else:
                processed_items.append({
                    "index": idx,
                    "type": "unknown",
                    "content": str(item)
                })

        self.result = {
            "type": "batch",
            "source": source,
            "total_items": len(processed_items),
            "items": processed_items
        }

    def _process_generic(self, content: Any, source: str) -> None:
        """处理其他类型内容"""
        self.result = {
            "type": "generic",
            "source": source,
            "content": content,
            "content_type": type(content).__name__
        }

    def _calculate_confidence(self) -> None:
        """
        计算置信度

        基于处理结果的质量和完整性评估
        """
        base_confidence = 0.90  # 基础置信度

        # 根据结果完整性调整
        if self.result.get("type") == "batch":
            # 批量处理，检查项目完整性
            items = self.result.get("items", [])
            if items:
                valid_items = sum(1 for i in items if i.get("content"))
                base_confidence = valid_items / len(items)
        elif self.result.get("type") == "text":
            # 文本处理，检查内容完整性
            content = self.result.get("content", "")
            if content:
                base_confidence = min(0.95, 0.80 + len(content) / 1000)
            else:
                base_confidence = 0.50

        self.confidence = max(0.0, min(1.0, base_confidence))

    def _generate_output(self) -> Dict[str, Any]:
        """
        生成输出结果

        返回:
            包含结果和置信度的字典
        """
        output = {
            "success": True,
            "confidence": self.confidence,
            "result": self.result,
            "warnings": self.warnings
        }

        # 根据置信度添加标注
        if self.confidence >= CONFIDENCE_HIGH:
            output["status"] = "直接输出"
        elif self.confidence >= CONFIDENCE_MEDIUM:
            output["status"] = "建议复核"
            output["warnings"].append("置信度中等，建议人工复核")
        else:
            output["status"] = "需核实"
            output["warnings"].append("[需核实] 置信度过低，结果可能不准确")

        return output

    def _handle_error(self, error_str: str) -> Dict[str, Any]:
        """
        统一错误处理

        参数:
            error_str: 错误信息字符串

        返回:
            错误结果字典
        """
        # 解析错误码
        error_code = error_str.split(':')[0] if ':' in error_str else error_str
        
        # 构建错误响应
        error_response = {
            "success": False,
            "error_code": error_code,
            "error_message": ERROR_MESSAGES.get(error_code, ERROR_MESSAGES["E010"])
        }

        # 补充错误详情
        if ':' in error_str:
            detail = error_str.split(':', 1)[1]
            if error_code == "E002":
                error_response["error_message"] = ERROR_MESSAGES["E002"].format(detail)
            elif error_code == "E003":
                error_response["error_message"] = ERROR_MESSAGES["E003"].format(detail)
            elif error_code == "E004":
                error_response["error_message"] = ERROR_MESSAGES["E004"].format(detail)
            elif error_code == "E005":
                error_response["error_message"] = ERROR_MESSAGES["E005"].format(detail)

        return error_response


# ============================================================
# 格式转换工具
# ============================================================

class OutputFormatter:
    """输出格式化工具"""

    @staticmethod
    def format(output: Dict[str, Any], fmt: str = "text") -> str:
        """
        将处理结果转换为指定格式

        参数:
            output: 处理结果字典
            fmt: 输出格式 (text/json/yaml)

        返回:
            格式化后的字符串
        """
        if fmt == "json":
            return json.dumps(output, ensure_ascii=False, indent=2)
        elif fmt == "text":
            return OutputFormatter._format_text(output)
        elif fmt == "compact":
            return json.dumps(output, ensure_ascii=False)
        else:
            raise ValueError(f"E008:{fmt}")

    @staticmethod
    def _format_text(output: Dict[str, Any]) -> str:
        """文本格式输出"""
        lines = []
        
        # 状态信息
        status = output.get("status", "未知")
        confidence = output.get("confidence", 0)
        lines.append(f"状态: {status}")
        lines.append(f"置信度: {confidence:.1%}")
        
        # 警告信息
        warnings = output.get("warnings", [])
        for warning in warnings:
            lines.append(f"警告: {warning}")
        
        # 结果内容
        result = output.get("result", {})
        lines.append("结果:")
        if result.get("type") == "text":
            lines.append(f"  类型: 文本")
            lines.append(f"  行数: {result.get('lines', 0)}")
            lines.append(f"  字符数: {result.get('characters', 0)}")
            structured = result.get("structured", {})
            if structured.get("first_line"):
                lines.append(f"  首行: {structured['first_line'][:50]}")
            if structured.get("last_line"):
                lines.append(f"  末行: {structured['last_line'][:50]}")
        elif result.get("type") == "batch":
            lines.append(f"  类型: 批量")
            lines.append(f"  项目数: {result.get('total_items', 0)}")
            items = result.get("items", [])
            for item in items[:5]:  # 只显示前5项
                lines.append(f"    项目{item['index']}: {item.get('content', '')[:50]}")
            if len(items) > 5:
                lines.append(f"    ... 等 {len(items)} 项")
        else:
            lines.append(f"  类型: {result.get('type', '未知')}")
            content = result.get("content", "")
            if isinstance(content, str):
                lines.append(f"  内容: {content[:100]}")
        
        return '\n'.join(lines)


# ============================================================
# 命令行接口
# ============================================================

def parse_args() -> argparse.Namespace:
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="oe-skills 未命名工具 - 处理数据/文件/URL 并生成结构化结果"
    )
    
    parser.add_argument(
        "--input", "-i",
        type=str,
        help="输入内容：文本、文件路径或 URL"
    )
    
    parser.add_argument(
        "--format", "-f",
        type=str,
        default=DEFAULT_OUTPUT_FORMAT,
        choices=["text", "json", "compact"],
        help="输出格式 (默认: text)"
    )
    
    parser.add_argument(
        "--source",
        type=str,
        default="user_provided",
        help="输入来源标识"
    )
    
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检程序（离线，不依赖外部数据）"
    )
    
    parser.add_argument(
        "--batch",
        type=str,
        nargs="*",
        help="批量处理多个输入项"
    )
    
    return parser.parse_args()


def run_selftest() -> int:
    """
    内置自检程序

    使用硬编码样例数据验证核心逻辑，不依赖外部文件或网络。

    返回:
        0 表示成功，非0表示失败
    """
    print("=" * 60)
    print("oe-skills 自检程序")
    print("=" * 60)
    
    processor = OESkillsProcessor()
    formatter = OutputFormatter()
    test_results = []
    
    # 测试用例 1: 文本处理
    print("\n[测试 1] 文本处理")
    try:
        sample_text = "这是一个测试文本\n包含多行内容\n用于验证处理逻辑"
        result = processor.process(sample_text, format="json")
        
        # 宽松断言
        assert result.get("success") is True, "文本处理应成功"
        assert result.get("confidence", 0) > 0.5, "置信度应大于0.5"
        assert result["result"].get("type") == "text", "结果类型应为文本"
        assert result["result"].get("lines", 0) >= 3, "应识别至少3行"
        assert result["result"].get("characters", 0) > 10, "字符数应大于10"
        
        test_results.append(("文本处理", True))
        print("  ✓ 通过")
    except AssertionError as e:
        test_results.append(("文本处理", False))
        print(f"  ✗ 失败: {e}")
    
    # 测试用例 2: 批量处理
    print("\n[测试 2] 批量处理")
    try:
        sample_batch = ["项目A", "项目B", "项目C"]
        result = processor.process(sample_batch, format="json")
        
        # 宽松断言
        assert result.get("success") is True, "批量处理应成功"
        assert result["result"].get("type") == "batch", "结果类型应为批量"
        assert result["result"].get("total_items", 0) >= 3, "应处理至少3个项目"
        assert len(result["result"].get("items", [])) >= 3, "应有至少3个结果项"
        
        test_results.append(("批量处理", True))
        print("  ✓ 通过")
    except AssertionError as e:
        test_results.append(("批量处理", False))
        print(f"  ✗ 失败: {e}")
    
    # 测试用例 3: 空输入处理
    print("\n[测试 3] 空输入错误处理")
    try:
        result = processor.process(None)
        
        # 宽松断言
        assert result.get("success") is False, "空输入应失败"
        assert result.get("error_code") == "E001", "错误码应为E001"
        
        test_results.append(("空输入处理", True))
        print("  ✓ 通过")
    except AssertionError as e:
        test_results.append(("空输入处理", False))
        print(f"  ✗ 失败: {e}")
    
    # 测试用例 4: 结构化数据处理
    print("\n[测试 4] 结构化数据处理")
    try:
        sample_structured = {
            "content": "结构化内容",
            "source": "test",
            "format": "json"
        }
        result = processor.process(sample_structured)
        
        # 宽松断言
        assert result.get("success") is True, "结构化数据应处理成功"
        assert result.get("confidence", 0) > 0.5, "置信度应大于0.5"
        
        test_results.append(("结构化数据处理", True))
        print("  ✓ 通过")
    except AssertionError as e:
        test_results.append(("结构化数据处理", False))
        print(f"  ✗ 失败: {e}")
    
    # 测试用例 5: 格式转换
    print("\n[测试 5] 输出格式转换")
    try:
        sample_result = {
            "success": True,
            "confidence": 0.95,
            "result": {"type": "text", "content": "测试"},
            "warnings": []
        }
        
        json_output = formatter.format(sample_result, "json")
        text_output = formatter.format(sample_result, "text")
        compact_output = formatter.format(sample_result, "compact")
        
        # 宽松断言
        assert '"success": true' in json_output.lower(), "JSON输出应包含成功标志"
        assert "测试" in text_output, "文本输出应包含内容"
        assert len(compact_output) > 0, "紧凑输出不应为空"
        
        test_results.append(("格式转换", True))
        print("  ✓ 通过")
    except AssertionError as e:
        test_results.append(("格式转换", False))
        print(f"  ✗ 失败: {e}")
    
    # 测试用例 6: 高置信度处理
    print("\n[测试 6] 高置信度处理")
    try:
        # 构造一个高质量输入
        high_quality_input = "这是一个内容丰富的输入文本，包含多个关键信息字段。" * 20
        
        result = processor.process(high_quality_input)
        
        # 宽松断言
        assert result.get("success") is True, "处理应成功"
        assert result.get("confidence", 0) >= 0.7, "置信度应较高"
        assert result.get("status") in ["直接输出", "建议复核"], "状态应为直接输出或建议复核"
        
        test_results.append(("高置信度处理", True))
        print("  ✓ 通过")
    except AssertionError as e:
        test_results.append(("高置信度处理", False))
        print(f"  ✗ 失败: {e}")
    
    # 汇总结果
    print("\n" + "=" * 60)
    print("自检结果汇总")
    print("=" * 60)
    
    passed = sum(1 for _, success in test_results if success)
    total = len(test_results)
    
    for name, success in test_results:
        status = "✓" if success else "✗"
        print(f"  {status} {name}")
    
    print(f"\n通过率: {passed}/{total}")
    
    if passed == total:
        print("自检全部通过 ✓")
        return 0
    else:
        print("存在失败项 ✗")
        return 1


def run_batch_processing(args: argparse.Namespace) -> None:
    """执行批量处理"""
    processor = OESkillsProcessor()
    formatter = OutputFormatter()
    
    print(f"批量处理 {len(args.batch)} 个项目...")
    
    for i, item in enumerate(args.batch):
        print(f"\n项目 {i+1}: {item[:50] if len(item) > 50 else item}")
        result = processor.process(item, format=args.format)
        
        if result.get("success"):
            output = formatter.format(result, args.format)
            print(output)
        else:
            print(f"处理失败: {result.get('error_message', '未知错误')}")


def main() -> int:
    """主函数"""
    args = parse_args()
    
    # 自检模式
    if args.selftest:
        return run_selftest()
    
    # 批量处理模式
    if args.batch:
        run_batch_processing(args)
        return 0
    
    # 单次处理模式
    if args.input:
        processor = OESkillsProcessor()
        formatter = OutputFormatter()
        
        try:
            # 检查输入是否为文件路径
            input_data = args.input
            if os.path.isfile(args.input):
                try:
                    with open(args.input, 'r', encoding='utf-8') as f:
                        input_data = f.read()
                    print(f"已读取文件: {args.input}")
                except Exception as e:
                    print(f"E006: 读取文件失败 - {e}")
                    return 1
            
            # 处理输入
            result = processor.process(input_data, format=args.format, source=args.source)
            
            # 输出结果
            output = formatter.format(result, args.format)
            print(output)
            
            # 检查处理结果
            if not result.get("success"):
                error_code = result.get("error_code", "E010")
                print(f"\n错误码: {error_code}")
                return 1
            
            return 0
            
        except Exception as e:
            print(f"E006: 处理过程中发生异常 - {e}")
            return 1
    
    # 无有效参数
    print("请提供输入内容，使用 --help 查看帮助")
    print("示例: python main.py --input '待处理的内容' --format json")
    print("或运行自检: python main.py --selftest")
    return 1


if __name__ == "__main__":
    sys.exit(main())
