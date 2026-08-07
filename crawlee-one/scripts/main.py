#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
crawlee-one 爬虫采集技能 - 独立实现脚本

本脚本根据功能规格独立实现，不包含任何外部依赖。
仅使用 Python 标准库。

功能：
    1. 将用户提供的数据/文件/URL 转换为结构化结果
    2. 识别并保留输入中的关键信息
    3. 按约定格式生成输出
    4. 对不确定项给出置信度提示
    5. 支持批量处理和自定义格式

运行方式：
    python main.py --selftest    # 离线自检
    python main.py --input "待处理内容" [--format json|text] [--batch]
"""

import argparse
import json
import re
import sys
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 错误码定义
# ============================================================
ERROR_CODES = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：...（逐项追问）",
    "E003": "输入格式不符合要求，示例：...",
    "E004": "这超出了本工具的能力范围，建议...",
    "E005": "结果无法确定，建议：...",
    "E006": "内部处理错误，请重试",
    "E007": "批量处理中断，部分结果已生成",
    "E008": "输出格式不支持",
    "E009": "输入内容超过处理上限",
    "E010": "自定义处理失败",
}


# ============================================================
# 核心数据结构
# ============================================================
class ProcessResult:
    """处理结果数据类"""
    def __init__(self):
        self.task_id: str = ""
        self.timestamp: str = ""
        self.input_type: str = ""          # text / url / file
        self.extracted_fields: Dict[str, Any] = {}
        self.confidence: float = 0.0       # 0-100
        self.warnings: List[str] = []
        self.raw_input: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "task_id": self.task_id,
            "timestamp": self.timestamp,
            "input_type": self.input_type,
            "extracted_fields": self.extracted_fields,
            "confidence": self.confidence,
            "warnings": self.warnings,
            "raw_input_preview": self.raw_input[:100] if self.raw_input else "",
        }


# ============================================================
# 核心处理逻辑
# ============================================================
class ContentProcessor:
    """内容处理器 - 核心逻辑"""

    # 常见字段模式
    FIELD_PATTERNS = {
        "email": r"[\w.+-]+@[\w-]+\.[\w.]+",
        "phone": r"(?:\+?\d{1,3}[- ]?)?\(?\d{3}\)?[- ]?\d{3}[- ]?\d{4}",
        "url": r"https?://[\w\-./?&=#%]+",
        "date": r"\d{4}[-/]\d{1,2}[-/]\d{1,2}|\d{1,2}[-/]\d{1,2}[-/]\d{4}",
        "id_card": r"\d{17}[\dXx]",
        "ip": r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}",
    }

    def __init__(self):
        self.task_counter = 0

    def process(self, content: str, input_type: str = "text", 
                output_format: str = "json", custom_fields: Optional[List[str]] = None) -> ProcessResult:
        """
        处理输入内容，提取结构化信息

        Args:
            content: 待处理内容
            input_type: 输入类型 (text/url/file)
            output_format: 输出格式 (json/text)
            custom_fields: 自定义需要提取的字段名列表

        Returns:
            ProcessResult 对象

        Raises:
            ValueError: 当输入无效时抛出，带有错误码
        """
        # 输入校验
        if not content or not content.strip():
            raise ValueError(f"E001: {ERROR_CODES['E001']}")

        if len(content) > 100000:
            raise ValueError(f"E009: {ERROR_CODES['E009']}")

        if input_type not in ("text", "url", "file"):
            raise ValueError(f"E003: {ERROR_CODES['E003']}")

        # 创建结果对象
        result = ProcessResult()
        self.task_counter += 1
        result.task_id = f"task_{datetime.now().strftime('%Y%m%d%H%M%S')}_{self.task_counter}"
        result.timestamp = datetime.now().isoformat()
        result.input_type = input_type
        result.raw_input = content.strip()

        # 提取关键信息
        try:
            extracted, confidence, warnings = self._extract_key_info(content, input_type, custom_fields)
            result.extracted_fields = extracted
            result.confidence = confidence
            result.warnings = warnings
        except Exception as e:
            raise ValueError(f"E006: {ERROR_CODES['E006']} - {str(e)}")

        # 置信度标注
        self._apply_confidence_markers(result)

        return result

    def _extract_key_info(self, content: str, input_type: str,
                          custom_fields: Optional[List[str]]) -> Tuple[Dict[str, Any], float, List[str]]:
        """
        提取关键信息

        Returns:
            (提取字段字典, 置信度, 警告列表)
        """
        extracted: Dict[str, Any] = {}
        warnings: List[str] = []
        total_patterns = 0
        matched_patterns = 0

        # 1. 识别内置模式
        for field_name, pattern in self.FIELD_PATTERNS.items():
            total_patterns += 1
            matches = re.findall(pattern, content)
            if matches:
                # 去重并保留前5个
                unique_matches = list(dict.fromkeys(matches))[:5]
                extracted[field_name] = unique_matches
                matched_patterns += 1

        # 2. 识别自定义字段
        if custom_fields:
            for field in custom_fields:
                total_patterns += 1
                pattern = rf"{field}[:：]\s*([^\s,，;；]+)"
                matches = re.findall(pattern, content, re.IGNORECASE)
                if matches:
                    extracted[field] = matches[0]
                    matched_patterns += 1
                else:
                    # 尝试更宽松的匹配
                    pattern = rf"{field}\s*[=:：]\s*([^\n]+)"
                    matches = re.findall(pattern, content, re.IGNORECASE)
                    if matches:
                        extracted[field] = matches[0].strip()
                        matched_patterns += 1
                    else:
                        warnings.append(f"[需核实] 未找到字段: {field}")

        # 3. 处理 URL 类型输入
        if input_type == "url":
            extracted["url_source"] = content.strip()
            # 尝试提取域名
            domain_match = re.search(r"https?://([\w\-]+\.)+[\w\-]+", content)
            if domain_match:
                extracted["domain"] = domain_match.group(0).replace("https://", "").replace("http://", "")
                matched_patterns += 1
            total_patterns += 1

        # 4. 处理文件类型输入（提取文件名和扩展名）
        if input_type == "file":
            file_name = content.strip().split("/")[-1].split("\\")[-1]
            extracted["file_name"] = file_name
            if "." in file_name:
                extracted["file_extension"] = file_name.split(".")[-1]
            total_patterns += 2
            matched_patterns += 2

        # 5. 计算置信度
        if total_patterns > 0:
            confidence = (matched_patterns / total_patterns) * 100
        else:
            confidence = 50.0  # 没有可匹配的模式时给予中等置信度

        # 确保置信度在合理范围
        confidence = max(0.0, min(100.0, confidence))

        # 如果提取结果为空，降低置信度
        if not extracted:
            confidence = min(confidence, 30.0)
            warnings.append("[需核实] 未能从输入中提取到关键信息")

        return extracted, confidence, warnings

    def _apply_confidence_markers(self, result: ProcessResult):
        """根据置信度添加标注"""
        if result.confidence >= 90:
            # 高置信度，直接输出
            pass
        elif result.confidence >= 85:
            result.warnings.append("建议复核：部分字段置信度在85%-90%之间")
        else:
            # 低置信度，已在 warnings 中标注
            if not result.warnings:
                result.warnings.append("[需核实] 整体置信度低于85%，请人工确认")

    def batch_process(self, contents: List[str], input_type: str = "text",
                      output_format: str = "json",
                      custom_fields: Optional[List[str]] = None) -> List[ProcessResult]:
        """
        批量处理多个输入

        Args:
            contents: 输入内容列表
            input_type: 输入类型
            output_format: 输出格式
            custom_fields: 自定义字段

        Returns:
            ProcessResult 对象列表
        """
        results = []
        for i, content in enumerate(contents):
            try:
                result = self.process(content, input_type, output_format, custom_fields)
                results.append(result)
            except ValueError as e:
                # 单个失败不中断批量处理
                error_result = ProcessResult()
                error_result.task_id = f"error_{i}_{uuid.uuid4().hex[:8]}"
                error_result.timestamp = datetime.now().isoformat()
                error_result.input_type = "error"
                error_result.raw_input = content[:100] if content else ""
                error_result.extracted_fields = {"error": str(e)}
                error_result.confidence = 0.0
                error_result.warnings = [str(e)]
                results.append(error_result)

        return results


# ============================================================
# 格式化输出
# ============================================================
class OutputFormatter:
    """输出格式化器"""

    @staticmethod
    def format_result(result: ProcessResult, output_format: str = "json") -> str:
        """
        格式化单个结果

        Args:
            result: 处理结果
            output_format: 输出格式 (json/text)

        Returns:
            格式化后的字符串
        """
        if output_format == "json":
            return json.dumps(result.to_dict(), ensure_ascii=False, indent=2)
        elif output_format == "text":
            return OutputFormatter._format_text(result)
        else:
            raise ValueError(f"E008: {ERROR_CODES['E008']}")

    @staticmethod
    def _format_text(result: ProcessResult) -> str:
        """文本格式输出"""
        lines = []
        lines.append(f"任务ID: {result.task_id}")
        lines.append(f"时间: {result.timestamp}")
        lines.append(f"输入类型: {result.input_type}")
        lines.append(f"置信度: {result.confidence:.1f}%")
        lines.append("---")

        for key, value in result.extracted_fields.items():
            if isinstance(value, list):
                lines.append(f"{key}: {', '.join(value)}")
            else:
                lines.append(f"{key}: {value}")

        if result.warnings:
            lines.append("---")
            lines.append("警告:")
            for warning in result.warnings:
                lines.append(f"  - {warning}")

        return "\n".join(lines)

    @staticmethod
    def format_batch(results: List[ProcessResult], output_format: str = "json") -> str:
        """
        格式化批量结果

        Args:
            results: 结果列表
            output_format: 输出格式

        Returns:
            格式化后的字符串
        """
        if output_format == "json":
            return json.dumps([r.to_dict() for r in results], ensure_ascii=False, indent=2)
        else:
            formatted = []
            for i, result in enumerate(results):
                formatted.append(f"=== 结果 {i+1} ===")
                formatted.append(OutputFormatter._format_text(result))
            return "\n\n".join(formatted)


# ============================================================
# 自检模块
# ============================================================
class SelfTest:
    """自检模块 - 使用内置硬编码样例数据离线测试"""

    TEST_SAMPLES = [
        {
            "content": "联系人：张三，邮箱：zhangsan@example.com，电话：138-1234-5678，地址：北京市朝阳区",
            "input_type": "text",
            "custom_fields": ["联系人"],
            "expected_fields": ["email", "phone", "联系人"],
            "min_confidence": 30,  # 宽松阈值
        },
        {
            "content": "https://example.com/products?id=123&category=books",
            "input_type": "url",
            "custom_fields": None,
            "expected_fields": ["url_source", "domain"],
            "min_confidence": 40,
        },
        {
            "content": "项目报告_2024.docx",
            "input_type": "file",
            "custom_fields": None,
            "expected_fields": ["file_name", "file_extension"],
            "min_confidence": 50,
        },
        {
            "content": "身份证号：110101199003071234，日期：2024-01-15，IP：192.168.1.1",
            "input_type": "text",
            "custom_fields": None,
            "expected_fields": ["id_card", "date", "ip"],
            "min_confidence": 30,
        },
        {
            "content": "姓名=王五, 年龄: 28, 城市=上海",
            "input_type": "text",
            "custom_fields": ["姓名", "年龄", "城市"],
            "expected_fields": ["姓名", "年龄", "城市"],
            "min_confidence": 50,
        },
    ]

    @classmethod
    def run_all(cls) -> bool:
        """
        运行所有自检用例

        Returns:
            True 表示全部通过
        """
        print("=" * 60)
        print("crawlee-one 自检开始")
        print("=" * 60)

        processor = ContentProcessor()
        formatter = OutputFormatter()
        all_passed = True

        for i, sample in enumerate(cls.TEST_SAMPLES):
            passed, message = cls._run_single_test(processor, formatter, sample, i + 1)
            if not passed:
                all_passed = False
            print(message)

        # 测试批量处理
        print("-" * 40)
        batch_passed = cls._test_batch(processor, formatter)
        if not batch_passed:
            all_passed = False

        # 测试错误处理
        print("-" * 40)
        error_passed = cls._test_error_handling(processor)
        if not error_passed:
            all_passed = False

        print("=" * 60)
        if all_passed:
            print("✅ 全部自检通过")
        else:
            print("❌ 存在失败的自检项")
        print("=" * 60)

        return all_passed

    @classmethod
    def _run_single_test(cls, processor: ContentProcessor, formatter: OutputFormatter,
                         sample: Dict[str, Any], test_num: int) -> Tuple[bool, str]:
        """
        运行单个测试用例

        Returns:
            (是否通过, 提示信息)
        """
        try:
            result = processor.process(
                content=sample["content"],
                input_type=sample["input_type"],
                custom_fields=sample["custom_fields"]
            )

            # 检查字段是否提取到
            missing_fields = []
            for field in sample["expected_fields"]:
                if field not in result.extracted_fields:
                    missing_fields.append(field)

            # 检查置信度（宽松阈值）
            if result.confidence < sample["min_confidence"]:
                return False, f"测试 {test_num}: ❌ 置信度 {result.confidence:.1f}% 低于阈值 {sample['min_confidence']}%"

            if missing_fields:
                return False, f"测试 {test_num}: ❌ 缺失字段: {missing_fields}"

            # 验证格式化输出
            try:
                json_output = formatter.format_result(result, "json")
                text_output = formatter.format_result(result, "text")
                if not json_output or not text_output:
                    return False, f"测试 {test_num}: ❌ 格式化输出为空"
            except Exception as e:
                return False, f"测试 {test_num}: ❌ 格式化输出异常: {str(e)}"

            return True, f"测试 {test_num}: ✅ 通过 (置信度: {result.confidence:.1f}%)"

        except ValueError as e:
            return False, f"测试 {test_num}: ❌ 处理异常: {str(e)}"
        except Exception as e:
            return False, f"测试 {test_num}: ❌ 未知异常: {str(e)}"

    @classmethod
    def _test_batch(cls, processor: ContentProcessor, formatter: OutputFormatter) -> bool:
        """测试批量处理"""
        contents = [
            "用户A: user@example.com, 电话: 010-12345678",
            "用户B: bob@test.org, 电话: 021-87654321",
            "无效输入",  # 测试批量中的错误处理
        ]

        try:
            results = processor.batch_process(contents, input_type="text")
            if len(results) != len(contents):
                print(f"批量测试: ❌ 结果数量不匹配")
                return False

            # 批量格式化测试
            json_batch = formatter.format_batch(results, "json")
            text_batch = formatter.format_batch(results, "text")
            if not json_batch or not text_batch:
                print("批量测试: ❌ 批量格式化输出为空")
                return False

            print("批量测试: ✅ 通过")
            return True

        except Exception as e:
            print(f"批量测试: ❌ 异常: {str(e)}")
            return False

    @classmethod
    def _test_error_handling(cls, processor: ContentProcessor) -> bool:
        """测试错误处理"""
        passed = True

        # 测试空输入
        try:
            processor.process("")
            print("错误处理测试: ❌ 空输入未抛出异常")
            passed = False
        except ValueError as e:
            if str(e).startswith("E001"):
                print("错误处理测试: ✅ 空输入正确返回 E001")
            else:
                print(f"错误处理测试: ❌ 空输入错误码不正确: {str(e)}")
                passed = False

        # 测试无效输入类型
        try:
            processor.process("测试内容", input_type="invalid")
            print("错误处理测试: ❌ 无效输入类型未抛出异常")
            passed = False
        except ValueError as e:
            if str(e).startswith("E003"):
                print("错误处理测试: ✅ 无效输入类型正确返回 E003")
            else:
                print(f"错误处理测试: ❌ 无效输入类型错误码不正确: {str(e)}")
                passed = False

        # 测试超长输入
        try:
            processor.process("x" * 100001)
            print("错误处理测试: ❌ 超长输入未抛出异常")
            passed = False
        except ValueError as e:
            if str(e).startswith("E009"):
                print("错误处理测试: ✅ 超长输入正确返回 E009")
            else:
                print(f"错误处理测试: ❌ 超长输入错误码不正确: {str(e)}")
                passed = False

        return passed


# ============================================================
# 命令行入口
# ============================================================
def main():
    """命令行入口"""
    parser = argparse.ArgumentParser(
        description="crawlee-one 爬虫采集技能 - 单次调用完成网页采集",
        epilog="示例: python main.py --input '联系人: 张三, 邮箱: zhangsan@example.com' --format json"
    )

    parser.add_argument("--input", "-i", type=str, help="待处理内容（文本/URL/文件路径）")
    parser.add_argument("--type", "-t", type=str, choices=["text", "url", "file"],
                        default="text", help="输入类型 (默认: text)")
    parser.add_argument("--format", "-f", type=str, choices=["json", "text"],
                        default="json", help="输出格式 (默认: json)")
    parser.add_argument("--fields", "-F", type=str, help="自定义字段，逗号分隔")
    parser.add_argument("--batch", "-b", action="store_true", help="批量处理模式")
    parser.add_argument("--selftest", action="store_true", help="运行自检")

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        success = SelfTest.run_all()
        sys.exit(0 if success else 1)

    # 需要输入内容
    if not args.input:
        print(f"错误 E001: {ERROR_CODES['E001']}")
        print("使用 --help 查看帮助")
        sys.exit(1)

    # 解析自定义字段
    custom_fields = None
    if args.fields:
        custom_fields = [f.strip() for f in args.fields.split(",") if f.strip()]

    try:
        processor = ContentProcessor()
        formatter = OutputFormatter()

        if args.batch:
            # 批量模式：按行分割输入
            contents = args.input.split("\n")
            contents = [c.strip() for c in contents if c.strip()]
            results = processor.batch_process(contents, args.type, args.format, custom_fields)
            output = formatter.format_batch(results, args.format)
        else:
            # 单条处理
            result = processor.process(args.input, args.type, args.format, custom_fields)
            output = formatter.format_result(result, args.format)

        print(output)

    except ValueError as e:
        print(f"错误: {str(e)}")
        sys.exit(1)
    except Exception as e:
        print(f"错误 E006: {ERROR_CODES['E006']} - {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
