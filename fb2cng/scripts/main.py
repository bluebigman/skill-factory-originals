#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fb2cng - PDF转文档 技能核心逻辑实现（独立重写版）

本脚本根据功能规格独立实现，不复制任何既有代码。
支持命令行调用与 --selftest 离线自检。
"""

import argparse
import json
import os
import re
import sys
import tempfile
import urllib.parse
from datetime import datetime
from pathlib import Path

# 错误码定义
ERROR_CODES = {
    "E001": "输入为空，请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "关键信息缺失，请补充必要字段",
    "E003": "输入格式不符合要求，请检查输入格式",
    "E004": "超出能力边界，无法处理该请求",
    "E005": "置信度过低，结果无法确定",
    "E006": "文件读取失败",
    "E007": "文件写入失败",
    "E008": "不支持的输出格式",
    "E009": "内部处理错误",
    "E010": "参数错误",
}


class FB2CNGError(Exception):
    """自定义异常类，携带错误码"""
    def __init__(self, error_code: str, message: str = ""):
        self.error_code = error_code
        self.message = message or ERROR_CODES.get(error_code, "未知错误")
        super().__init__(self.message)

    def __str__(self):
        return f"[{self.error_code}] {self.message}"


class DocumentProcessor:
    """文档处理核心类"""
    
    # 支持的输出格式
    SUPPORTED_FORMATS = {"epub2", "epub3", "kepub", "azw8", "kfx", "pdf", "txt", "md"}
    
    def __init__(self):
        """初始化处理器"""
        self.confidence_threshold_high = 0.90
        self.confidence_threshold_medium = 0.85
    
    def validate_input(self, input_data: str) -> bool:
        """验证输入是否有效
        
        Args:
            input_data: 输入内容
            
        Returns:
            是否有效
            
        Raises:
            FB2CNGError: E001 输入为空
        """
        if not input_data or not input_data.strip():
            raise FB2CNGError("E001")
        return True
    
    def detect_input_type(self, input_data: str) -> str:
        """检测输入类型
        
        Args:
            input_data: 输入内容
            
        Returns:
            输入类型: "url", "file", "text"
            
        Raises:
            FB2CNGError: E003 格式错误
        """
        # 检查是否为URL
        parsed = urllib.parse.urlparse(input_data.strip())
        if parsed.scheme in ("http", "https") and parsed.netloc:
            return "url"
        
        # 检查是否为文件路径
        if len(input_data) < 500 and os.path.isfile(input_data):
            return "file"
        
        # 默认为文本
        return "text"
    
    def extract_key_info(self, input_data: str) -> dict:
        """提取关键信息
        
        Args:
            input_data: 输入内容
            
        Returns:
            结构化信息字典
        """
        result = {
            "title": "",
            "author": "",
            "language": "zh",
            "content_length": 0,
            "paragraphs": [],
            "confidence": 1.0,
        }
        
        # 尝试提取标题（常见模式）
        title_match = re.search(r'(?:^|\n)\s*(?:《|【|\[)?\s*([^\n《》【】\[\]]{2,50})\s*(?:》|】|\])?\s*$', 
                              input_data, re.MULTILINE)
        if title_match:
            result["title"] = title_match.group(1).strip()
        
        # 尝试提取作者
        author_match = re.search(r'(?:作者|著者|by|author)\s*[:：]\s*([^\n]{2,30})', 
                               input_data, re.IGNORECASE)
        if author_match:
            result["author"] = author_match.group(1).strip()
        
        # 提取段落
        paragraphs = [p.strip() for p in input_data.split("\n") if p.strip()]
        result["paragraphs"] = paragraphs
        result["content_length"] = len(input_data)
        
        # 计算置信度
        if not result["title"]:
            result["confidence"] = min(result["confidence"], 0.8)
        if not result["author"]:
            result["confidence"] = min(result["confidence"], 0.9)
        if len(paragraphs) < 3:
            result["confidence"] = min(result["confidence"], 0.6)
        
        return result
    
    def calculate_confidence(self, info: dict) -> float:
        """计算置信度
        
        Args:
            info: 信息字典
            
        Returns:
            置信度值 (0-1)
        """
        return info.get("confidence", 0.5)
    
    def format_output(self, info: dict, output_format: str) -> str:
        """格式化输出
        
        Args:
            info: 信息字典
            output_format: 输出格式
            
        Returns:
            格式化后的输出内容
            
        Raises:
            FB2CNGError: E008 不支持的格式
        """
        fmt = output_format.lower()
        if fmt not in self.SUPPORTED_FORMATS:
            raise FB2CNGError("E008", f"不支持的输出格式: {output_format}")
        
        confidence = self.calculate_confidence(info)
        confidence_note = ""
        if confidence >= self.confidence_threshold_high:
            confidence_note = "置信度: 高"
        elif confidence >= self.confidence_threshold_medium:
            confidence_note = "置信度: 中 [建议复核]"
        else:
            confidence_note = "置信度: 低 [需核实]"
        
        # 生成基础内容
        lines = []
        lines.append(f"# {info.get('title', '未命名文档')}")
        if info.get("author"):
            lines.append(f"作者: {info['author']}")
        lines.append(f"语言: {info.get('language', 'zh')}")
        lines.append("")
        lines.append(confidence_note)
        lines.append("")
        lines.append("---")
        lines.append("")
        for para in info.get("paragraphs", []):
            lines.append(para)
            lines.append("")
        
        content = "\n".join(lines)
        
        # 根据格式调整输出
        if fmt in ("md", "txt"):
            return content
        elif fmt in ("pdf", "epub2", "epub3", "kepub", "azw8", "kfx"):
            # 简化处理，返回标记说明
            return f"[{fmt.upper()}格式内容]\n\n{content}"
        else:
            raise FB2CNGError("E008", f"不支持的输出格式: {output_format}")
    
    def process(self, input_data: str, output_format: str = "txt") -> dict:
        """处理输入内容
        
        Args:
            input_data: 输入内容
            output_format: 输出格式
            
        Returns:
            处理结果字典
            
        Raises:
            FB2CNGError: 各种错误
        """
        # 1. 验证输入
        self.validate_input(input_data)
        
        # 2. 检测输入类型
        input_type = self.detect_input_type(input_data)
        
        # 3. 根据类型处理
        content = input_data
        if input_type == "url":
            # 不访问网络，仅记录
            content = f"[URL输入] {input_data}"
        elif input_type == "file":
            # 读取文件内容
            try:
                with open(input_data, "r", encoding="utf-8") as f:
                    content = f.read()
            except (IOError, OSError) as e:
                raise FB2CNGError("E006", f"文件读取失败: {str(e)}")
        
        # 4. 提取关键信息
        info = self.extract_key_info(content)
        info["input_type"] = input_type
        
        # 5. 格式化输出
        output = self.format_output(info, output_format)
        
        # 6. 构建结果
        result = {
            "success": True,
            "input_type": input_type,
            "output_format": output_format,
            "output": output,
            "info": info,
            "confidence": self.calculate_confidence(info),
            "timestamp": datetime.now().isoformat(),
        }
        
        return result
    
    def batch_process(self, inputs: list, output_format: str = "txt") -> list:
        """批量处理
        
        Args:
            inputs: 输入列表
            output_format: 输出格式
            
        Returns:
            结果列表
        """
        results = []
        for item in inputs:
            try:
                result = self.process(item, output_format)
                results.append(result)
            except FB2CNGError as e:
                results.append({
                    "success": False,
                    "error": str(e),
                    "input": item
                })
        return results


class SelfTest:
    """自检功能类"""
    
    # 内置硬编码测试数据
    TEST_DATA = [
        {
            "input": "《Python编程入门》\n作者：张三\n\nPython是一种简洁而强大的编程语言。\n它广泛应用于数据分析、人工智能等领域。\n学习Python可以提高开发效率。",
            "expected_format": "txt",
            "min_confidence": 0.5,
            "must_contain": ["Python", "张三"]
        },
        {
            "input": "机器学习基础\n\n机器学习是人工智能的核心领域之一。\n它让计算机能够从数据中学习规律。",
            "expected_format": "md",
            "min_confidence": 0.3,
            "must_contain": ["机器学习"]
        },
        {
            "input": "https://example.com/sample",
            "expected_format": "txt",
            "min_confidence": 0.0,
            "must_contain": ["URL输入"]
        },
    ]
    
    def __init__(self):
        """初始化自检器"""
        self.processor = DocumentProcessor()
        self.passed = 0
        self.failed = 0
        
    def run_all(self) -> bool:
        """运行所有测试
        
        Returns:
            是否全部通过
        """
        print("=" * 60)
        print("fb2cng 自检程序启动")
        print("=" * 60)
        
        # 测试1: 正常文本处理
        self._test_valid_input()
        
        # 测试2: 空输入
        self._test_empty_input()
        
        # 测试3: 错误格式
        self._test_invalid_format()
        
        # 测试4: URL输入
        self._test_url_input()
        
        # 测试5: 批量处理
        self._test_batch()
        
        print("=" * 60)
        print(f"自检完成: 通过 {self.passed} 项, 失败 {self.failed} 项")
        print("=" * 60)
        
        return self.failed == 0
    
    def _check(self, name: str, condition: bool, detail: str = ""):
        """检查测试结果
        
        Args:
            name: 测试名称
            condition: 测试条件
            detail: 详细信息
        """
        if condition:
            self.passed += 1
            print(f"✓ {name}")
        else:
            self.failed += 1
            print(f"✗ {name}: {detail}")
    
    def _test_valid_input(self):
        """测试有效输入处理"""
        print("\n--- 测试1: 有效文本处理 ---")
        
        test_case = self.TEST_DATA[0]
        try:
            result = self.processor.process(test_case["input"], test_case["expected_format"])
            
            # 验证基本结构
            self._check("成功返回结果", result["success"])
            self._check("置信度达标", result["confidence"] >= test_case["min_confidence"],
                       f"置信度 {result['confidence']} < {test_case['min_confidence']}")
            
            # 验证内容包含
            output = result["output"]
            for keyword in test_case["must_contain"]:
                self._check(f"输出包含关键字: {keyword}", keyword in output,
                           f"输出中未找到 '{keyword}'")
            
            # 验证标题提取
            info = result["info"]
            self._check("提取到标题", len(info.get("title", "")) > 0,
                       f"标题为空")
            
        except FB2CNGError as e:
            self._check("无异常抛出", False, str(e))
    
    def _test_empty_input(self):
        """测试空输入"""
        print("\n--- 测试2: 空输入处理 ---")
        
        try:
            self.processor.process("")
            self._check("空输入应报错", False, "未抛出异常")
        except FB2CNGError as e:
            self._check("错误码为E001", e.error_code == "E001", f"错误码: {e.error_code}")
            self._check("错误消息非空", len(e.message) > 0)
    
    def _test_invalid_format(self):
        """测试无效格式"""
        print("\n--- 测试3: 无效格式处理 ---")
        
        try:
            self.processor.process("测试内容", "invalid_format")
            self._check("无效格式应报错", False, "未抛出异常")
        except FB2CNGError as e:
            self._check("错误码为E008", e.error_code == "E008", f"错误码: {e.error_code}")
    
    def _test_url_input(self):
        """测试URL输入"""
        print("\n--- 测试4: URL输入处理 ---")
        
        test_case = self.TEST_DATA[2]
        try:
            result = self.processor.process(test_case["input"], test_case["expected_format"])
            
            self._check("成功处理URL", result["success"])
            self._check("识别为URL类型", result["input_type"] == "url",
                       f"识别为: {result['input_type']}")
            self._check("包含URL标记", "URL输入" in result["output"])
            
        except FB2CNGError as e:
            self._check("URL处理无异常", False, str(e))
    
    def _test_batch(self):
        """测试批量处理"""
        print("\n--- 测试5: 批量处理 ---")
        
        inputs = [item["input"] for item in self.TEST_DATA]
        try:
            results = self.processor.batch_process(inputs, "txt")
            self._check("批量处理返回结果", len(results) == len(inputs),
                       f"返回 {len(results)} 条, 期望 {len(inputs)} 条")
            
            # 验证每个结果
            valid_results = [r for r in results if r.get("success")]
            self._check("至少有一条成功结果", len(valid_results) > 0,
                       "所有结果都失败")
            
        except Exception as e:
            self._check("批量处理无异常", False, str(e))


def run_selftest() -> int:
    """运行自检程序
    
    Returns:
        退出码 (0成功, 1失败)
    """
    test = SelfTest()
    success = test.run_all()
    return 0 if success else 1


def main() -> int:
    """主函数
    
    Returns:
        退出码
    """
    parser = argparse.ArgumentParser(
        description="fb2cng - PDF转文档 技能核心逻辑",
        epilog="示例: python main.py -i '输入内容' -f txt"
    )
    
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行离线自检程序（不依赖外部文件）"
    )
    
    parser.add_argument(
        "-i", "--input",
        type=str,
        help="输入内容（文本、文件路径或URL）"
    )
    
    parser.add_argument(
        "-f", "--format",
        type=str,
        default="txt",
        choices=sorted(DocumentProcessor.SUPPORTED_FORMATS),
        help="输出格式 (默认: txt)"
    )
    
    parser.add_argument(
        "--batch-file",
        type=str,
        help="批量处理的输入文件（每行一个输入）"
    )
    
    args = parser.parse_args()
    
    # 自检模式
    if args.selftest:
        return run_selftest()
    
    # 正常处理模式
    try:
        processor = DocumentProcessor()
        
        # 批量处理
        if args.batch_file:
            try:
                with open(args.batch_file, "r", encoding="utf-8") as f:
                    inputs = [line.strip() for line in f if line.strip()]
            except (IOError, OSError) as e:
                print(f"[E006] 批量文件读取失败: {str(e)}", file=sys.stderr)
                return 1
            
            results = processor.batch_process(inputs, args.format)
            for i, result in enumerate(results, 1):
                print(f"\n--- 结果 {i} ---")
                if result.get("success"):
                    print(result["output"])
                else:
                    print(f"错误: {result.get('error', '未知错误')}")
            return 0
        
        # 单条处理
        if not args.input:
            print("[E001] " + ERROR_CODES["E001"], file=sys.stderr)
            return 1
        
        result = processor.process(args.input, args.format)
        
        if result["success"]:
            print(result["output"])
            print(f"\n[处理信息] 类型: {result['input_type']}, "
                  f"置信度: {result['confidence']:.2f}")
            return 0
        else:
            print(f"处理失败: {result.get('error', '未知错误')}", file=sys.stderr)
            return 1
            
    except FB2CNGError as e:
        print(str(e), file=sys.stderr)
        return 1
    except Exception as e:
        print(f"[E009] 内部处理错误: {str(e)}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
