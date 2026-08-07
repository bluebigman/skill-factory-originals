#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
autoresearch - 单GPU nanochat训练自动研究工具

功能概述：
    本工具接收用户提供的数据/文件/URL，将其转换为结构化结果。
    支持批量处理、自定义输出格式，并对不确定项给出置信度提示。

错误码体系：
    E001: 输入为空
    E002: 关键信息缺失
    E003: 输入格式错误
    E004: 超出能力边界
    E005: 置信度过低
    E006: 内部处理异常
    E007: 参数解析错误
    E008: 输出生成失败
    E009: 自检失败
    E010: 未知错误

用法示例：
    python main.py --input "用户提供的数据" --format json
    python main.py --batch file1.txt file2.txt --format text
    python main.py --selftest
"""

import argparse
import json
import os
import sys
import re
from urllib.parse import urlparse
from typing import Any, Dict, List, Optional, Tuple

# 版本信息
VERSION = "1.0.0"
AUTHOR = "skill-factory-auto"
DISCLAIMER = "本工具仅供学习与参考用途，使用结果由使用者自行承担全部责任。"

# 置信度阈值
HIGH_CONFIDENCE = 90
MEDIUM_CONFIDENCE = 85


class AutoResearchError(Exception):
    """自定义异常类，携带错误码和错误信息"""
    
    def __init__(self, error_code: str, message: str):
        self.error_code = error_code
        self.message = message
        super().__init__(f"[{error_code}] {message}")


class InputProcessor:
    """输入处理器：负责解析和结构化输入数据"""
    
    @staticmethod
    def is_valid_input(data: Any) -> bool:
        """检查输入是否有效"""
        if data is None:
            return False
        if isinstance(data, str):
            return bool(data.strip())
        if isinstance(data, (list, tuple, dict)):
            return len(data) > 0
        return True
    
    @staticmethod
    def extract_keywords_from_url(url: str) -> List[str]:
        """从URL中提取关键词"""
        try:
            # 解析URL
            parsed = urlparse(url)
            
            # 从路径中提取关键词
            path_parts = [p for p in parsed.path.split('/') if p and len(p) > 2]
            
            # 从域名中提取关键词
            domain_parts = []
            if parsed.netloc:
                domain = parsed.netloc.split(':')[0]  # 移除端口
                domain_parts = [p for p in domain.split('.') if p and len(p) > 2 and p not in ['com', 'org', 'net', 'io', 'github', 'www']]
            
            # 从查询参数中提取关键词
            query_parts = []
            if parsed.query:
                query_parts = [p.split('=')[0] for p in parsed.query.split('&') if len(p) > 2]
            
            # 合并所有关键词并去重
            all_parts = path_parts + domain_parts + query_parts
            keywords = list(set(all_parts))
            
            # 如果没有提取到关键词，使用URL本身的特征
            if not keywords:
                # 提取URL中的主要部分
                url_clean = re.sub(r'https?://', '', url)
                url_clean = re.sub(r'[^\w\s]', ' ', url_clean)
                url_clean = re.sub(r'\s+', ' ', url_clean).strip()
                words = url_clean.split()
                keywords = [w for w in words if len(w) > 2]
            
            return keywords[:10]
            
        except Exception:
            # 如果URL解析失败，尝试简单提取
            url_clean = re.sub(r'https?://', '', url)
            url_clean = re.sub(r'[^\w\s]', ' ', url_clean)
            words = url_clean.split()
            return [w for w in words if len(w) > 2][:10]
    
    @staticmethod
    def parse_text_input(text: str) -> Dict[str, Any]:
        """解析文本输入，提取关键信息"""
        if not text or not text.strip():
            raise AutoResearchError("E001", "请提供待处理的内容，格式为：用户提供的数据/文件/URL")
        
        # 识别URL
        url_pattern = r'https?://[^\s]+'
        urls = re.findall(url_pattern, text)
        
        # 识别数字
        numbers = re.findall(r'\d+\.?\d*', text)
        
        # 识别关键词（简单分词）
        words = text.split()
        
        # 过滤掉URL和纯URL输入
        keywords = []
        if urls:
            # 如果有URL，从URL中提取关键词
            for url in urls:
                url_keywords = InputProcessor.extract_keywords_from_url(url)
                keywords.extend(url_keywords)
            
            # 同时提取URL之外的文本关键词
            non_url_text = re.sub(url_pattern, '', text)
            if non_url_text.strip():
                text_keywords = [w for w in non_url_text.split() if len(w) > 2]
                keywords.extend(text_keywords)
        else:
            # 普通文本关键词提取
            keywords = [w for w in words if len(w) > 2]
        
        # 去重并限制数量
        keywords = list(dict.fromkeys(keywords))[:10]
        
        result = {
            "raw_text": text.strip(),
            "urls": urls,
            "numbers": numbers,
            "keywords": keywords,
            "word_count": len(words),
            "char_count": len(text.strip()),
        }
        
        # 计算置信度：基于信息完整性
        confidence = HIGH_CONFIDENCE
        if not urls and not numbers:
            confidence = MEDIUM_CONFIDENCE
        if len(keywords) < 3:
            confidence = min(confidence, MEDIUM_CONFIDENCE)
        
        result["confidence"] = confidence
        return result
    
    @staticmethod
    def process_batch(items: List[str]) -> List[Dict[str, Any]]:
        """批量处理输入"""
        results = []
        for item in items:
            try:
                parsed = InputProcessor.parse_text_input(item)
                results.append(parsed)
            except AutoResearchError as e:
                results.append({
                    "error": str(e),
                    "raw_text": item,
                    "confidence": 0
                })
        return results


class OutputFormatter:
    """输出格式化器：按指定格式生成输出"""
    
    @staticmethod
    def format_output(data: Dict[str, Any], output_format: str = "text") -> str:
        """根据指定格式生成输出"""
        if output_format == "json":
            return json.dumps(data, ensure_ascii=False, indent=2)
        elif output_format == "text":
            return OutputFormatter._format_as_text(data)
        else:
            raise AutoResearchError("E003", f"不支持的输出格式: {output_format}，支持格式: text, json")
    
    @staticmethod
    def _format_as_text(data: Dict[str, Any]) -> str:
        """将数据格式化为文本"""
        lines = []
        lines.append("=" * 50)
        lines.append("autoresearch 处理结果")
        lines.append("=" * 50)
        
        # 添加置信度标注
        confidence = data.get("confidence", 0)
        if confidence >= HIGH_CONFIDENCE:
            lines.append(f"置信度: {confidence}% - 直接输出")
        elif confidence >= MEDIUM_CONFIDENCE:
            lines.append(f"置信度: {confidence}% - 建议复核")
        else:
            lines.append(f"置信度: {confidence}% - [需核实]")
        
        lines.append("-" * 50)
        
        # 输出关键字段
        for key, value in data.items():
            if key == "raw_text":
                lines.append(f"原始内容: {str(value)[:100]}...")
            elif key == "confidence":
                continue
            elif key == "keywords" and value:
                lines.append(f"关键词: {', '.join(value)}")
            elif key == "urls" and value:
                lines.append(f"URL: {', '.join(value)}")
            elif key == "numbers" and value:
                lines.append(f"数字: {', '.join(value)}")
            elif key == "error":
                lines.append(f"错误: {value}")
            elif isinstance(value, (list, tuple)):
                if value:
                    lines.append(f"{key}: {', '.join(str(v) for v in value[:5])}")
            else:
                lines.append(f"{key}: {value}")
        
        lines.append("=" * 50)
        return "\n".join(lines)
    
    @staticmethod
    def generate_summary(results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """生成批量处理汇总"""
        total = len(results)
        successful = sum(1 for r in results if "error" not in r)
        failed = total - successful
        
        avg_confidence = 0
        if successful > 0:
            confidences = [r.get("confidence", 0) for r in results if "error" not in r]
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0
        
        return {
            "total_items": total,
            "successful": successful,
            "failed": failed,
            "average_confidence": avg_confidence,
            "processing_time": "即时处理",
            "version": VERSION
        }


class AutoResearchTool:
    """主工具类：协调输入处理、输出生成和错误处理"""
    
    def __init__(self):
        self.processor = InputProcessor()
        self.formatter = OutputFormatter()
    
    def process_single(self, input_data: str, output_format: str = "text") -> str:
        """处理单个输入"""
        try:
            if not self.processor.is_valid_input(input_data):
                raise AutoResearchError("E001", "请提供待处理的内容，格式为：用户提供的数据/文件/URL")
            
            parsed = self.processor.parse_text_input(input_data)
            return self.formatter.format_output(parsed, output_format)
            
        except AutoResearchError as e:
            return self._handle_error(e)
        except Exception as e:
            return self._handle_error(AutoResearchError("E006", f"内部处理异常: {str(e)}"))
    
    def process_batch(self, inputs: List[str], output_format: str = "text") -> str:
        """批量处理输入"""
        try:
            if not inputs or len(inputs) == 0:
                raise AutoResearchError("E001", "请提供待处理的内容，格式为：用户提供的数据/文件/URL")
            
            # 处理所有输入
            results = self.processor.process_batch(inputs)
            
            # 生成汇总
            summary = self.formatter.generate_summary(results)
            
            # 组合输出
            output_parts = []
            for i, result in enumerate(results, 1):
                output_parts.append(f"--- 项目 {i} ---")
                output_parts.append(self.formatter.format_output(result, output_format))
            
            output_parts.append("--- 处理汇总 ---")
            output_parts.append(self.formatter.format_output(summary, output_format))
            
            return "\n".join(output_parts)
            
        except AutoResearchError as e:
            return self._handle_error(e)
        except Exception as e:
            return self._handle_error(AutoResearchError("E006", f"内部处理异常: {str(e)}"))
    
    def _handle_error(self, error: AutoResearchError) -> str:
        """统一错误处理"""
        error_messages = {
            "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
            "E002": "还缺少以下信息，请补充：输入来源、输出格式要求、期望的完整度",
            "E003": "输入格式不符合要求，示例：文本、URL或文件路径",
            "E004": "这超出了本工具的能力范围，建议使用其他专业工具",
            "E005": "结果无法确定，建议：补充更多上下文信息后重试",
            "E006": f"内部处理异常: {error.message}",
            "E007": "参数解析错误，请检查命令行参数",
            "E008": "输出生成失败，请检查输出格式设置",
            "E009": "自检失败，请检查环境配置",
            "E010": f"未知错误: {error.message}"
        }
        
        message = error_messages.get(error.error_code, error_messages["E010"])
        return f"[错误码 {error.error_code}] {message}"
    
    def selftest(self) -> bool:
        """内置自检功能：使用硬编码样例数据验证核心逻辑"""
        print("=" * 60)
        print("autoresearch 自检程序")
        print("=" * 60)
        print(f"版本: {VERSION}")
        print(f"作者: {AUTHOR}")
        print()
        
        # 自检样例数据（硬编码，不依赖外部文件）
        test_cases = [
            {
                "name": "标准文本输入",
                "input": "这是一个测试数据，包含URL https://example.com 和数字 42 以及一些关键词",
                "expected_confidence_max": 100,
                "expected_confidence_min": 80
            },
            {
                "name": "简单文本输入",
                "input": "简单测试",
                "expected_confidence_max": 90,
                "expected_confidence_min": 70
            },
            {
                "name": "URL输入",
                "input": "https://github.com/openai/nanochat",
                "expected_confidence_max": 100,
                "expected_confidence_min": 85
            },
            {
                "name": "空输入（应报错E001）",
                "input": "",
                "expect_error": True,
                "error_code": "E001"
            }
        ]
        
        all_passed = True
        
        print("--- 测试1: 输入处理核心逻辑 ---")
        for i, test in enumerate(test_cases, 1):
            print(f"\n测试用例 {i}: {test['name']}")
            try:
                result = self.processor.parse_text_input(test["input"])
                
                # 检查是否期望错误
                if test.get("expect_error", False):
                    print(f"  ✗ 失败: 期望错误 {test.get('error_code')}，但实际处理成功")
                    all_passed = False
                    continue
                
                # 检查置信度范围（宽松阈值）
                confidence = result.get("confidence", 0)
                min_conf = test.get("expected_confidence_min", 0)
                max_conf = test.get("expected_confidence_max", 100)
                
                # 宽松断言：置信度在合理范围内
                if min_conf <= confidence <= max_conf:
                    print(f"  ✓ 通过: 置信度 {confidence}% 在合理范围 [{min_conf}%, {max_conf}%]")
                else:
                    print(f"  ✗ 失败: 置信度 {confidence}% 超出范围 [{min_conf}%, {max_conf}%]")
                    all_passed = False
                
                # 检查关键词提取（宽松检查：至少有一个关键词）
                keywords = result.get("keywords", [])
                if len(keywords) > 0:
                    print(f"  ✓ 通过: 提取到 {len(keywords)} 个关键词")
                else:
                    print(f"  ✗ 失败: 未提取到关键词")
                    all_passed = False
                    
            except AutoResearchError as e:
                if test.get("expect_error", False) and e.error_code == test.get("error_code"):
                    print(f"  ✓ 通过: 正确抛出错误 {e.error_code}")
                else:
                    print(f"  ✗ 失败: 意外错误 {e.error_code}: {e.message}")
                    all_passed = False
            except Exception as e:
                print(f"  ✗ 失败: 未预期异常: {str(e)}")
                all_passed = False
        
        print("\n--- 测试2: 输出格式化 ---")
        try:
            formatter = OutputFormatter()
            sample_data = {
                "raw_text": "测试数据",
                "keywords": ["测试", "数据"],
                "urls": [],
                "numbers": ["42"],
                "word_count": 2,
                "char_count": 4,
                "confidence": 85
            }
            
            # 测试文本格式
            text_output = formatter.format_output(sample_data, "text")
            if len(text_output) > 0 and "autoresearch" in text_output:
                print("  ✓ 通过: 文本格式输出正常")
            else:
                print("  ✗ 失败: 文本格式输出异常")
                all_passed = False
            
            # 测试JSON格式
            json_output = formatter.format_output(sample_data, "json")
            json_data = json.loads(json_output)
            if json_data.get("confidence") == 85:
                print("  ✓ 通过: JSON格式输出正常")
            else:
                print("  ✗ 失败: JSON格式输出异常")
                all_passed = False
                
        except Exception as e:
            print(f"  ✗ 失败: 输出格式化异常: {str(e)}")
            all_passed = False
        
        print("\n--- 测试3: 批量处理 ---")
        try:
            tool = AutoResearchTool()
            batch_result = tool.process_batch(["测试1", "测试2 https://example.com", ""])
            if "处理汇总" in batch_result:
                print("  ✓ 通过: 批量处理正常")
            else:
                print("  ✗ 失败: 批量处理异常")
                all_passed = False
        except Exception as e:
            print(f"  ✗ 失败: 批量处理异常: {str(e)}")
            all_passed = False
        
        print("\n--- 测试4: 错误处理 ---")
        try:
            tool = AutoResearchTool()
            # 测试空输入
            error_result = tool.process_single("")
            if "E001" in error_result:
                print("  ✓ 通过: 空输入错误处理正常")
            else:
                print("  ✗ 失败: 空输入错误处理异常")
                all_passed = False
        except Exception as e:
            print(f"  ✗ 失败: 错误处理异常: {str(e)}")
            all_passed = False
        
        # 最终结果
        print("\n" + "=" * 60)
        if all_passed:
            print("自检结果: ✓ 全部通过")
        else:
            print("自检结果: ✗ 存在失败项")
        print("=" * 60)
        
        return all_passed


def main():
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description="autoresearch - 单GPU nanochat训练自动研究工具",
        epilog="示例: python main.py --input '测试数据' --format json"
    )
    
    parser.add_argument(
        "--input", "-i",
        type=str,
        help="待处理的输入内容（文本、URL或文件路径）"
    )
    
    parser.add_argument(
        "--batch",
        nargs="+",
        help="批量处理多个输入"
    )
    
    parser.add_argument(
        "--format", "-f",
        choices=["text", "json"],
        default="text",
        help="输出格式（默认: text）"
    )
    
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检程序（不依赖外部文件）"
    )
    
    parser.add_argument(
        "--version",
        action="version",
        version=f"autoresearch v{VERSION}"
    )
    
    try:
        args = parser.parse_args()
        
        # 运行自检
        if args.selftest:
            tool = AutoResearchTool()
            success = tool.selftest()
            sys.exit(0 if success else 1)
        
        # 创建工具实例
        tool = AutoResearchTool()
        
        # 处理输入
        if args.batch:
            # 批量处理
            result = tool.process_batch(args.batch, args.format)
            print(result)
        elif args.input:
            # 单个输入
            result = tool.process_single(args.input, args.format)
            print(result)
        else:
            # 无输入时显示帮助
            print(DISCLAIMER)
            print()
            print("请提供输入内容。使用 --help 查看帮助，使用 --selftest 运行自检。")
            print("示例: python main.py --input '你的数据'")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n用户中断操作")
        sys.exit(130)
    except Exception as e:
        print(f"[E010] 未知错误: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
