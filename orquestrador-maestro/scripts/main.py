#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
orquestrador-maestro - 技能实现脚本（独立重写）

本脚本根据功能规格实现一个通用的数据处理编排工具：
1. 接收用户提供的输入（文本/结构化数据）
2. 解析并识别关键信息
3. 按模板生成结构化输出
4. 标注置信度
5. 支持批量处理

仅使用 Python 标准库，无第三方依赖。
"""

import argparse
import json
import re
import sys
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 错误码定义（E001-E010）
# ============================================================
class ErrorCode:
    """错误码常量定义"""
    E001_INPUT_EMPTY = "E001"           # 输入为空
    E002_INFO_MISSING = "E002"          # 关键信息缺失
    E003_FORMAT_ERROR = "E003"          # 输入格式错误
    E004_OUT_OF_SCOPE = "E004"          # 超出能力边界
    E005_LOW_CONFIDENCE = "E005"        # 置信度过低
    E006_BATCH_EMPTY = "E006"           # 批量输入为空
    E007_INVALID_FIELD = "E007"         # 字段名无效
    E008_TEMPLATE_ERROR = "E008"        # 模板生成错误
    E009_INTERNAL_ERROR = "E009"        # 内部错误
    E010_UNSUPPORTED_FORMAT = "E010"    # 不支持的输出格式


# ============================================================
# 异常类
# ============================================================
class SkillError(Exception):
    """技能基础异常"""
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"[{code}] {message}")


# ============================================================
# 核心数据模型
# ============================================================
class ProcessedItem:
    """单项处理结果"""
    def __init__(self, raw_input: str, fields: Dict[str, Any],
                 confidence: float, warnings: List[str] = None):
        self.raw_input = raw_input
        self.fields = fields
        self.confidence = confidence
        self.warnings = warnings or []
        self.timestamp = datetime.now().isoformat()
        self.item_id = str(uuid.uuid4())[:8]

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.item_id,
            "timestamp": self.timestamp,
            "raw_input": self.raw_input,
            "fields": self.fields,
            "confidence": self.confidence,
            "confidence_label": self._confidence_label(),
            "warnings": self.warnings
        }

    def _confidence_label(self) -> str:
        """根据置信度生成标签"""
        if self.confidence >= 90:
            return "直接输出"
        elif self.confidence >= 85:
            return "建议复核"
        else:
            return "[需核实]"


# ============================================================
# 核心处理器
# ============================================================
class OrquestradorMaestro:
    """
    核心编排处理器

    负责：
    - 输入解析
    - 关键信息提取
    - 置信度评估
    - 结果生成
    """

    # 常见关键字段模式（用于识别输入中的信息）
    FIELD_PATTERNS = {
        "name": [r"姓名[：:\s]*([^\s,，；;]+)", r"名称[：:\s]*([^\s,，；;]+)"],
        "email": [r"邮箱[：:\s]*([\w.+-]+@[\w-]+\.[\w.]+)", 
                  r"email[：:\s]*([\w.+-]+@[\w-]+\.[\w.]+)"],
        "phone": [r"电话[：:\s]*([\d\-+() ]{7,})", 
                  r"手机[：:\s]*([\d\-+() ]{7,})"],
        "date": [r"日期[：:\s]*(\d{4}[-/]\d{1,2}[-/]\d{1,2})",
                 r"时间[：:\s]*(\d{4}[-/]\d{1,2}[-/]\d{1,2})"],
        "amount": [r"金额[：:\s]*([\d,]+\.?\d*)\s*(元|块|￥|¥)?"],
        "address": [r"地址[：:\s]*([^\n,，；;]+)"],
        "url": [r"网址[：:\s]*(https?://\S+)", 
                r"链接[：:\s]*(https?://\S+)"],
    }

    # 置信度影响因素
    CONFIDENCE_BASE = 75.0
    CONFIDENCE_PER_FIELD = 3.0
    CONFIDENCE_MAX = 98.0

    def __init__(self):
        """初始化处理器"""
        self.batch_mode = False
        self.output_format = "json"

    def process(self, user_input: str, output_format: str = "json") -> Dict[str, Any]:
        """
        处理单个输入

        Args:
            user_input: 用户提供的输入文本
            output_format: 输出格式（json/text）

        Returns:
            处理结果字典

        Raises:
            SkillError: 处理失败时抛出
        """
        # E001: 输入为空
        if not user_input or not user_input.strip():
            raise SkillError(ErrorCode.E001_INPUT_EMPTY,
                           "请提供待处理的内容，格式为：用户提供的数据/文件/URL")

        # E003: 输入格式检查（长度限制）
        if len(user_input) > 10000:
            raise SkillError(ErrorCode.E003_FORMAT_ERROR,
                           "输入内容过长（超过10000字符），请分段处理")

        # 解析输入
        fields = self._extract_fields(user_input)
        
        # E002: 关键信息缺失
        if not fields:
            raise SkillError(ErrorCode.E002_INFO_MISSING,
                           "无法从输入中识别出关键信息，请提供包含姓名、邮箱、电话等字段的内容")

        # 计算置信度
        confidence = self._calculate_confidence(fields, user_input)

        # E005: 置信度过低
        if confidence < 60:
            raise SkillError(ErrorCode.E005_LOW_CONFIDENCE,
                           "结果无法确定（置信度低于60%），建议：提供更完整的信息")

        # 生成警告
        warnings = self._generate_warnings(confidence, fields)

        # 创建结果
        item = ProcessedItem(user_input, fields, confidence, warnings)

        # 格式化输出
        if output_format == "json":
            return item.to_dict()
        elif output_format == "text":
            return self._format_text_output(item)
        else:
            raise SkillError(ErrorCode.E010_UNSUPPORTED_FORMAT,
                           f"不支持的输出格式: {output_format}，支持: json, text")

    def process_batch(self, inputs: List[str], output_format: str = "json") -> Dict[str, Any]:
        """
        批量处理多个输入

        Args:
            inputs: 输入列表
            output_format: 输出格式

        Returns:
            批量处理结果
        """
        # E006: 批量输入为空
        if not inputs:
            raise SkillError(ErrorCode.E006_BATCH_EMPTY,
                           "批量输入为空，请提供至少一个待处理项")

        results = []
        errors = []

        for i, user_input in enumerate(inputs):
            try:
                result = self.process(user_input, output_format)
                results.append(result)
            except SkillError as e:
                errors.append({
                    "index": i,
                    "error_code": e.code,
                    "error_message": e.message,
                    "raw_input": user_input
                })

        return {
            "batch_size": len(inputs),
            "success_count": len(results),
            "error_count": len(errors),
            "results": results,
            "errors": errors
        }

    def _extract_fields(self, text: str) -> Dict[str, Any]:
        """
        从输入文本中提取关键字段

        Args:
            text: 输入文本

        Returns:
            提取到的字段字典
        """
        fields = {}

        for field_name, patterns in self.FIELD_PATTERNS.items():
            for pattern in patterns:
                match = re.search(pattern, text)
                if match:
                    value = match.group(1).strip()
                    if value:
                        fields[field_name] = value
                        break

        # 额外检查：如果文本看起来像JSON，尝试解析
        if not fields and text.strip().startswith("{"):
            try:
                data = json.loads(text)
                if isinstance(data, dict):
                    for key, value in data.items():
                        if isinstance(value, (str, int, float, bool)):
                            fields[str(key)] = str(value)
            except json.JSONDecodeError:
                pass

        return fields

    def _calculate_confidence(self, fields: Dict[str, Any], raw_text: str) -> float:
        """
        计算置信度

        规则：
        - 基础置信度 75
        - 每个字段 +3
        - 字段数越多置信度越高
        - 有结构化标记（如JSON）额外加分
        - 上限 98

        Args:
            fields: 提取的字段
            raw_text: 原始文本

        Returns:
            置信度（0-100）
        """
        confidence = self.CONFIDENCE_BASE

        # 每个字段增加置信度
        field_count = len(fields)
        confidence += field_count * self.CONFIDENCE_PER_FIELD

        # 结构化数据加分
        if raw_text.strip().startswith("{"):
            confidence += 5

        # 字段完整性检查
        if "name" in fields:
            confidence += 2
        if "email" in fields:
            confidence += 2
        if "phone" in fields:
            confidence += 2

        # 限制上限
        confidence = min(confidence, self.CONFIDENCE_MAX)

        return round(confidence, 1)

    def _generate_warnings(self, confidence: float, fields: Dict[str, Any]) -> List[str]:
        """
        生成警告信息

        Args:
            confidence: 置信度
            fields: 提取的字段

        Returns:
            警告列表
        """
        warnings = []

        if confidence < 85:
            warnings.append("信息完整度较低，建议补充更多字段")

        if "email" in fields and not re.match(r"^[\w.+-]+@[\w-]+\.[\w.]+$", fields["email"]):
            warnings.append("邮箱格式可能不正确")

        if "phone" in fields and len(fields["phone"]) < 7:
            warnings.append("电话号码可能不完整")

        return warnings

    def _format_text_output(self, item: ProcessedItem) -> str:
        """
        格式化文本输出

        Args:
            item: 处理结果

        Returns:
            格式化文本
        """
        lines = [
            f"=== 处理结果 (ID: {item.item_id}) ===",
            f"时间: {item.timestamp}",
            f"置信度: {item.confidence}% ({item._confidence_label()})",
            "--- 提取字段 ---"
        ]

        for key, value in item.fields.items():
            lines.append(f"  {key}: {value}")

        if item.warnings:
            lines.append("--- 警告 ---")
            for warning in item.warnings:
                lines.append(f"  ⚠ {warning}")

        return "\n".join(lines)


# ============================================================
# 自检模块
# ============================================================
class SelfTest:
    """
    内置自检模块

    使用硬编码样例数据，不依赖外部文件/网络/当前目录
    """

    # 硬编码测试样例
    TEST_CASES = [
        {
            "name": "完整信息",
            "input": "姓名：张三，邮箱：zhangsan@example.com，电话：13812345678",
            "expected_fields": ["name", "email", "phone"],
            "min_confidence": 80
        },
        {
            "name": "部分信息",
            "input": "姓名：李四，邮箱：lisi@test.org",
            "expected_fields": ["name", "email"],
            "min_confidence": 75
        },
        {
            "name": "JSON格式",
            "input": '{"name": "王五", "age": 30, "city": "北京"}',
            "expected_fields": ["name", "age", "city"],
            "min_confidence": 80
        },
        {
            "name": "带金额信息",
            "input": "项目名称：开发，金额：15000元，日期：2025-06-15",
            "expected_fields": ["name", "amount", "date"],
            "min_confidence": 75
        },
    ]

    # 错误处理测试
    ERROR_TEST_CASES = [
        {
            "name": "空输入",
            "input": "",
            "expected_error": ErrorCode.E001_INPUT_EMPTY
        },
        {
            "name": "无关键信息",
            "input": "这是一段没有任何关键信息的普通文本",
            "expected_error": ErrorCode.E002_INFO_MISSING
        },
    ]

    # 批量处理测试
    BATCH_TEST_CASES = [
        "姓名：赵六，邮箱：zhaoliu@example.com",
        "姓名：孙七，电话：13912345678",
        "姓名：周八，邮箱：zhouba@test.org，电话：13712345678"
    ]

    @classmethod
    def run_all(cls) -> bool:
        """
        运行所有自检

        Returns:
            是否全部通过
        """
        print("=" * 60)
        print("orquestrador-maestro 自检开始")
        print("=" * 60)

        all_passed = True

        # 测试核心处理
        all_passed &= cls._test_core_processing()

        # 测试错误处理
        all_passed &= cls._test_error_handling()

        # 测试批量处理
        all_passed &= cls._test_batch_processing()

        # 测试输出格式
        all_passed &= cls._test_output_formats()

        print("=" * 60)
        if all_passed:
            print("✅ 所有自检通过")
        else:
            print("❌ 存在失败的自检项")
        print("=" * 60)

        return all_passed

    @classmethod
    def _test_core_processing(cls) -> bool:
        """测试核心处理逻辑"""
        print("\n--- 核心处理测试 ---")
        processor = OrquestradorMaestro()
        passed = True

        for test_case in cls.TEST_CASES:
            try:
                result = processor.process(test_case["input"], "json")
                
                # 检查字段
                for field in test_case["expected_fields"]:
                    if field not in result["fields"]:
                        print(f"  ❌ {test_case['name']}: 缺少字段 '{field}'")
                        passed = False
                        break

                # 检查置信度（宽松阈值）
                if result["confidence"] < test_case["min_confidence"]:
                    print(f"  ❌ {test_case['name']}: 置信度 {result['confidence']}% 低于阈值 {test_case['min_confidence']}%")
                    passed = False
                else:
                    print(f"  ✅ {test_case['name']}: 字段={list(result['fields'].keys())}, 置信度={result['confidence']}%")

            except SkillError as e:
                print(f"  ❌ {test_case['name']}: 意外错误 {e.code}: {e.message}")
                passed = False

        return passed

    @classmethod
    def _test_error_handling(cls) -> bool:
        """测试错误处理"""
        print("\n--- 错误处理测试 ---")
        processor = OrquestradorMaestro()
        passed = True

        for test_case in cls.ERROR_TEST_CASES:
            try:
                processor.process(test_case["input"], "json")
                print(f"  ❌ {test_case['name']}: 未抛出预期错误")
                passed = False
            except SkillError as e:
                if e.code == test_case["expected_error"]:
                    print(f"  ✅ {test_case['name']}: 正确抛出 {e.code}")
                else:
                    print(f"  ❌ {test_case['name']}: 期望 {test_case['expected_error']}, 实际 {e.code}")
                    passed = False

        return passed

    @classmethod
    def _test_batch_processing(cls) -> bool:
        """测试批量处理"""
        print("\n--- 批量处理测试 ---")
        processor = OrquestradorMaestro()
        passed = True

        try:
            result = processor.process_batch(cls.BATCH_TEST_CASES, "json")
            
            # 宽松断言：成功数量大于0
            if result["success_count"] > 0:
                print(f"  ✅ 批量处理: 成功={result['success_count']}, 失败={result['error_count']}")
            else:
                print(f"  ❌ 批量处理: 全部失败")
                passed = False

            # 检查错误处理
            if result["error_count"] == 0:
                print(f"  ✅ 批量处理: 无错误项")
            else:
                print(f"  ⚠ 批量处理: {result['error_count']} 个错误项（预期内）")

        except SkillError as e:
            print(f"  ❌ 批量处理: {e.code}: {e.message}")
            passed = False

        return passed

    @classmethod
    def _test_output_formats(cls) -> bool:
        """测试输出格式"""
        print("\n--- 输出格式测试 ---")
        processor = OrquestradorMaestro()
        passed = True

        # 测试文本输出
        try:
            text_result = processor.process("姓名：测试，邮箱：test@example.com", "text")
            if isinstance(text_result, str) and len(text_result) > 0:
                print(f"  ✅ 文本输出: 长度={len(text_result)}")
            else:
                print(f"  ❌ 文本输出: 格式不正确")
                passed = False
        except SkillError as e:
            print(f"  ❌ 文本输出: {e.code}")
            passed = False

        # 测试不支持的格式
        try:
            processor.process("姓名：测试", "xml")
            print(f"  ❌ 不支持的格式: 未抛出错误")
            passed = False
        except SkillError as e:
            if e.code == ErrorCode.E010_UNSUPPORTED_FORMAT:
                print(f"  ✅ 不支持的格式: 正确抛出 {e.code}")
            else:
                print(f"  ❌ 不支持的格式: 期望 E010, 实际 {e.code}")
                passed = False

        return passed


# ============================================================
# 命令行入口
# ============================================================
def main() -> int:
    """
    主入口函数

    Returns:
        退出码（0=成功，1=失败）
    """
    parser = argparse.ArgumentParser(
        description="orquestrador-maestro - 通用数据处理编排工具",
        epilog="示例: python main.py --input '姓名：张三，邮箱：zhangsan@example.com' --format json"
    )
    parser.add_argument("--input", "-i", help="待处理的输入内容")
    parser.add_argument("--format", "-f", choices=["json", "text"], default="json",
                       help="输出格式（默认: json）")
    parser.add_argument("--batch", "-b", nargs="+", help="批量处理多个输入")
    parser.add_argument("--selftest", action="store_true", help="运行内置自检")
    parser.add_argument("--version", action="version", version="orquestrador-maestro 1.0.0")

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        success = SelfTest.run_all()
        return 0 if success else 1

    # 创建处理器
    processor = OrquestradorMaestro()

    try:
        # 批量模式
        if args.batch:
            result = processor.process_batch(args.batch, args.format)
            if args.format == "json":
                print(json.dumps(result, ensure_ascii=False, indent=2))
            else:
                for item in result["results"]:
                    print(item)
                    print()
            return 0

        # 单条模式
        if args.input:
            result = processor.process(args.input, args.format)
            if args.format == "json":
                print(json.dumps(result, ensure_ascii=False, indent=2))
            else:
                print(result)
            return 0

        # 无输入参数
        parser.print_help()
        return 0

    except SkillError as e:
        print(f"错误 {e.code}: {e.message}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"错误 {ErrorCode.E009_INTERNAL_ERROR}: 内部错误: {str(e)}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
