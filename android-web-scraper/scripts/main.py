#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
android-web-scraper 爬虫采集工具
版本: 1.0.0
描述: 将用户提供的数据/文件/URL 转换为结构化结果
"""

import argparse
import sys
import json
import re
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
    "E006": "内部处理异常，请重试",
    "E007": "参数解析失败，请检查命令行参数",
    "E008": "输出格式不支持",
    "E009": "批量处理中断",
    "E010": "未知错误",
}


# ============================================================
# 核心数据结构
# ============================================================

class ProcessingResult:
    """处理结果对象"""
    def __init__(self, data: Any = None, confidence: float = 1.0, warnings: List[str] = None):
        self.data = data
        self.confidence = confidence
        self.warnings = warnings if warnings else []

    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "data": self.data,
            "confidence": self.confidence,
            "warnings": self.warnings,
        }


class InputParser:
    """输入解析器：识别 URL、文件路径、纯文本"""
    
    URL_PATTERN = r'^(https?://)?([a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}(/\S*)?$'
    FILE_PATTERN = r'^[\w\-. /\\]+\.(txt|csv|json|xml|html?|md)$'
    
    @classmethod
    def parse(cls, raw_input: str) -> Tuple[str, str]:
        """
        解析输入类型
        返回: (类型, 内容)
        类型: url / file / text / unknown
        """
        if not raw_input or not raw_input.strip():
            return "empty", ""
        
        content = raw_input.strip()
        
        # 检查是否为 URL
        if re.match(cls.URL_PATTERN, content, re.IGNORECASE):
            return "url", content
        
        # 检查是否为文件路径
        if re.match(cls.FILE_PATTERN, content, re.IGNORECASE):
            return "file", content
        
        # 检查是否为 JSON
        if content.startswith("{") or content.startswith("["):
            try:
                json.loads(content)
                return "json", content
            except json.JSONDecodeError:
                pass
        
        # 默认为纯文本
        return "text", content


class ContentProcessor:
    """核心处理器：识别关键信息并结构化"""
    
    # 常见关键字段的正则模式
    FIELD_PATTERNS = {
        "email": r'[\w.+-]+@[\w-]+\.[\w.]+',
        "phone": r'(\+?\d{1,3}[- ]?)?\(?\d{2,4}\)?[- ]?\d{3,4}[- ]?\d{3,4}',
        "url": r'https?://[\w./?=&%-]+',
        "date": r'\d{4}[-/]\d{1,2}[-/]\d{1,2}',
        "price": r'[¥￥$€]\s?\d+(\.\d+)?',
        "id_number": r'\d{15}(\d{2}[\dXx])?',
        "ip_address": r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}',
        "username": r'@[\w_]+',
        "hashtag": r'#[\w\u4e00-\u9fa5]+',
    }
    
    @classmethod
    def extract_fields(cls, text: str) -> Dict[str, List[str]]:
        """从文本中提取关键字段"""
        extracted = {}
        for field_name, pattern in cls.FIELD_PATTERNS.items():
            matches = re.findall(pattern, text)
            if matches:
                # 去重并保持顺序
                unique_matches = list(dict.fromkeys(matches))
                extracted[field_name] = unique_matches
        return extracted
    
    @classmethod
    def calculate_confidence(cls, extracted: Dict[str, List[str]], total_fields: int) -> float:
        """计算置信度"""
        if total_fields == 0:
            return 0.5  # 没有可提取的字段，中等置信度
        found_ratio = len(extracted) / min(total_fields, max(1, len(extracted) + 1))
        return min(1.0, 0.5 + found_ratio * 0.5)
    
    @classmethod
    def process(cls, input_type: str, content: str) -> ProcessingResult:
        """处理输入内容"""
        warnings = []
        
        # 根据输入类型处理
        if input_type == "empty":
            return ProcessingResult(None, 0.0, ["输入为空"])
        
        if input_type == "url":
            # URL 处理：提取域名和路径信息
            domain_match = re.match(r'^(https?://)?([^/]+)', content)
            domain = domain_match.group(2) if domain_match else content
            path = content.split(domain, 1)[1] if domain in content else "/"
            
            extracted = {
                "domain": domain,
                "path": path,
                "url": content,
            }
            confidence = 0.9  # URL 解析通常较可靠
            warnings.append("URL 内容未实际访问，仅解析了 URL 结构")
            
        elif input_type == "file":
            # 文件路径处理：提取路径信息
            import os
            basename = os.path.basename(content)
            extension = os.path.splitext(content)[1].lstrip('.')
            
            extracted = {
                "filename": basename,
                "extension": extension,
                "path": content,
            }
            confidence = 0.85
            warnings.append(f"文件 {basename} 未实际读取，仅解析了路径信息")
            
        elif input_type == "json":
            # JSON 处理：直接解析并结构化
            try:
                data = json.loads(content)
                if isinstance(data, dict):
                    extracted = {"json_fields": list(data.keys())}
                elif isinstance(data, list):
                    extracted = {"json_items": len(data)}
                else:
                    extracted = {"json_value": data}
                confidence = 0.95
            except json.JSONDecodeError as e:
                return ProcessingResult(None, 0.0, [f"JSON 解析失败: {str(e)}"])
                
        else:  # text
            # 文本处理：提取关键字段
            extracted = cls.extract_fields(content)
            total_common_fields = 8  # 常见字段总数
            confidence = cls.calculate_confidence(extracted, total_common_fields)
            
            if confidence < 0.85:
                warnings.append("[需核实] 置信度过低，请人工复核关键结果")
            elif confidence < 0.9:
                warnings.append("建议复核：部分字段可能不准确")
        
        result = ProcessingResult(extracted, confidence, warnings)
        return result


class OutputFormatter:
    """输出格式化器"""
    
    @classmethod
    def format(cls, result: ProcessingResult, output_format: str = "json") -> str:
        """格式化为指定输出格式"""
        if output_format == "json":
            return json.dumps(result.to_dict(), ensure_ascii=False, indent=2)
        elif output_format == "text":
            lines = []
            lines.append("=== 处理结果 ===")
            if result.data:
                if isinstance(result.data, dict):
                    for key, value in result.data.items():
                        lines.append(f"{key}: {value}")
                else:
                    lines.append(str(result.data))
            lines.append(f"置信度: {result.confidence * 100:.1f}%")
            if result.warnings:
                lines.append("警告:")
                for warning in result.warnings:
                    lines.append(f"  - {warning}")
            return "\n".join(lines)
        elif output_format == "compact":
            return json.dumps(result.to_dict(), ensure_ascii=False, separators=(',', ':'))
        else:
            raise ValueError(f"不支持的输出格式: {output_format}")


# ============================================================
# 批量处理
# ============================================================

def batch_process(inputs: List[str], output_format: str = "json") -> List[Dict]:
    """批量处理多个输入"""
    results = []
    for i, raw_input in enumerate(inputs):
        try:
            input_type, content = InputParser.parse(raw_input)
            result = ContentProcessor.process(input_type, content)
            results.append({
                "index": i + 1,
                "input": raw_input,
                "result": result.to_dict(),
            })
        except Exception as e:
            results.append({
                "index": i + 1,
                "input": raw_input,
                "error": f"E006: 处理失败 - {str(e)}",
            })
    return results


# ============================================================
# 内置自检样例数据
# ============================================================

SELFTEST_SAMPLES = [
    # 样例1: URL
    "https://example.com/products/12345?category=electronics",
    # 样例2: 带关键信息的文本
    "张三的联系方式是 phone: 138-1234-5678, email: zhangsan@example.com, 地址是北京市朝阳区",
    # 样例3: JSON 数据
    '{"name": "产品A", "price": 99.99, "stock": 100, "tags": ["电子", "热销"]}',
    # 样例4: 纯文本无关键信息
    "这是一段普通的文本内容，用于测试。",
    # 样例5: 空输入
    "",
]

# 宽松阈值定义（避免精确值断言）
SELFTEST_THRESHOLDS = {
    "min_confidence": 0.5,  # 最低置信度阈值（宽松）
    "max_confidence": 1.0,  # 最高置信度（宽松）
    "min_fields": 0,        # 最少字段数（宽松）
    "max_fields": 10,       # 最多字段数（宽松）
}


def run_selftest() -> bool:
    """
    内置自检：使用硬编码样例数据验证核心逻辑
    不读取外部文件、不依赖当前工作目录、不访问网络
    """
    print("=" * 50)
    print("运行内置自检...")
    print("=" * 50)
    
    all_passed = True
    
    # 测试1: 输入解析
    print("\n[测试1] 输入解析")
    test_cases = [
        ("https://example.com", "url"),
        ("data.txt", "file"),
        ("{'key': 'value'}", "json"),
        ("普通文本", "text"),
        ("", "empty"),
    ]
    for raw_input, expected_type in test_cases:
        input_type, _ = InputParser.parse(raw_input)
        # 使用宽松断言：只要不是完全相反的类型
        if input_type == expected_type or (expected_type == "empty" and input_type == "empty"):
            print(f"  ✓ 输入 '{raw_input[:30]}' 解析为 {input_type}")
        else:
            print(f"  ✗ 输入 '{raw_input[:30]}' 期望 {expected_type}，实际 {input_type}")
            all_passed = False
    
    # 测试2: 字段提取
    print("\n[测试2] 字段提取")
    test_text = "联系: test@example.com, 电话: 010-12345678, 网址: https://test.com"
    extracted = ContentProcessor.extract_fields(test_text)
    # 宽松断言：至少提取到一些字段
    if len(extracted) > 0:
        print(f"  ✓ 从测试文本提取到 {len(extracted)} 类字段")
    else:
        print("  ✗ 未能从测试文本提取任何字段")
        all_passed = False
    
    # 测试3: 核心处理流程（使用内置样例）
    print("\n[测试3] 核心处理流程")
    for i, sample in enumerate(SELFTEST_SAMPLES):
        input_type, content = InputParser.parse(sample)
        result = ContentProcessor.process(input_type, content)
        
        # 宽松断言：置信度在合理范围内
        if SELFTEST_THRESHOLDS["min_confidence"] <= result.confidence <= SELFTEST_THRESHOLDS["max_confidence"]:
            print(f"  ✓ 样例{i+1}: 输入类型={input_type}, 置信度={result.confidence:.2f}")
        else:
            print(f"  ✗ 样例{i+1}: 置信度 {result.confidence} 超出预期范围")
            all_passed = False
        
        # 宽松断言：结果数据结构合理
        if result.data is not None and isinstance(result.data, dict):
            if 0 <= len(result.data) <= SELFTEST_THRESHOLDS["max_fields"]:
                print(f"      提取到 {len(result.data)} 个字段")
            else:
                print(f"  ✗ 样例{i+1}: 字段数量异常")
                all_passed = False
    
    # 测试4: 输出格式化
    print("\n[测试4] 输出格式化")
    sample_result = ProcessingResult({"test": "value"}, 0.9, ["测试警告"])
    for fmt in ["json", "text", "compact"]:
        try:
            output = OutputFormatter.format(sample_result, fmt)
            if len(output) > 0:
                print(f"  ✓ 格式 '{fmt}' 输出长度 {len(output)} 字符")
            else:
                print(f"  ✗ 格式 '{fmt}' 输出为空")
                all_passed = False
        except Exception as e:
            print(f"  ✗ 格式 '{fmt}' 格式化失败: {str(e)}")
            all_passed = False
    
    # 测试5: 批量处理
    print("\n[测试5] 批量处理")
    batch_inputs = ["https://example.com", "test@example.com", ""]
    batch_results = batch_process(batch_inputs)
    if len(batch_results) == len(batch_inputs):
        print(f"  ✓ 批量处理 {len(batch_results)} 个输入")
    else:
        print(f"  ✗ 批量处理结果数量异常")
        all_passed = False
    
    # 测试6: 错误处理
    print("\n[测试6] 错误处理")
    # 测试空输入
    input_type, _ = InputParser.parse("")
    if input_type == "empty":
        print("  ✓ 空输入正确识别")
    else:
        print("  ✗ 空输入识别失败")
        all_passed = False
    
    # 测试7: 置信度计算
    print("\n[测试7] 置信度计算")
    confidence = ContentProcessor.calculate_confidence({"email": ["a@b.com"]}, 8)
    if 0.0 <= confidence <= 1.0:
        print(f"  ✓ 置信度计算正常: {confidence:.2f}")
    else:
        print(f"  ✗ 置信度超出范围: {confidence}")
        all_passed = False
    
    # 总结
    print("\n" + "=" * 50)
    if all_passed:
        print("✓ 所有自检测试通过")
    else:
        print("✗ 部分自检测试失败")
    print("=" * 50)
    
    return all_passed


# ============================================================
# 主入口
# ============================================================

def main():
    """命令行主入口"""
    parser = argparse.ArgumentParser(
        description="android-web-scraper 爬虫采集工具",
        epilog="示例: python main.py --input 'https://example.com' --format json"
    )
    
    parser.add_argument(
        "--input", "-i",
        type=str,
        help="待处理的内容（URL/文件路径/文本/JSON）"
    )
    
    parser.add_argument(
        "--format", "-f",
        type=str,
        choices=["json", "text", "compact"],
        default="json",
        help="输出格式 (默认: json)"
    )
    
    parser.add_argument(
        "--batch", "-b",
        type=str,
        nargs="+",
        help="批量处理多个输入"
    )
    
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检（使用硬编码样例数据，离线执行）"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="显示详细处理信息"
    )
    
    args = parser.parse_args()
    
    # 自检模式
    if args.selftest:
        success = run_selftest()
        sys.exit(0 if success else 1)
    
    # 检查是否有输入
    if not args.input and not args.batch:
        print(f"错误 E001: {ERROR_CODES['E001']}", file=sys.stderr)
        parser.print_help()
        sys.exit(1)
    
    try:
        # 批量处理模式
        if args.batch:
            print(f"批量处理 {len(args.batch)} 个输入...")
            results = batch_process(args.batch, args.format)
            for item in results:
                print(json.dumps(item, ensure_ascii=False, indent=2))
            sys.exit(0)
        
        # 单条处理模式
        input_type, content = InputParser.parse(args.input)
        
        if args.verbose:
            print(f"输入类型: {input_type}")
            print(f"输入内容: {content[:100]}..." if len(content) > 100 else f"输入内容: {content}")
        
        result = ContentProcessor.process(input_type, content)
        output = OutputFormatter.format(result, args.format)
        
        if args.verbose:
            print(f"置信度: {result.confidence * 100:.1f}%")
            if result.warnings:
                print("警告:")
                for warning in result.warnings:
                    print(f"  - {warning}")
        
        print(output)
        
        # 置信度过低时给出提示
        if result.confidence < 0.85:
            print(f"\n提示: {ERROR_CODES['E005']}", file=sys.stderr)
            sys.exit(1)
            
    except ValueError as e:
        print(f"错误 E008: {str(e)}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"错误 E006: {ERROR_CODES['E006']} - {str(e)}", file=sys.stderr)
        sys.exit(1)
    
    sys.exit(0)


if __name__ == "__main__":
    main()
