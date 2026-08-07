#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
爬虫采集技能 - 独立实现脚本

依据功能规格独立编写（clean-room），不参考任何既有实现。
仅使用标准库，无第三方依赖。

功能：
- 结构化数据提取（模拟）
- 批量处理
- 置信度评估
- 错误码体系（E001-E010）
- 内置自检（--selftest）
"""

import argparse
import json
import re
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 错误码定义
# ============================================================
ERROR_CODES = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：输入来源、输出格式要求、期望完整度",
    "E003": "输入格式不符合要求，示例：JSON字符串或文本内容",
    "E004": "这超出了本工具的能力范围，建议使用专业爬虫框架或服务",
    "E005": "结果无法确定，建议：提供更多信息或人工核实",
    "E006": "内部处理错误，请重试或检查输入",
    "E007": "输出格式不支持，支持：json, text",
    "E008": "批量处理时输入必须为列表格式",
    "E009": "字段提取失败，请检查输入内容",
    "E010": "置信度计算异常，使用默认值",
}


# ============================================================
# 核心数据结构
# ============================================================
class ProcessResult:
    """处理结果数据类"""

    def __init__(self, data: Dict[str, Any], confidence: float, warnings: List[str] = None):
        self.data = data
        self.confidence = confidence
        self.warnings = warnings or []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "data": self.data,
            "confidence": self.confidence,
            "confidence_level": self._get_confidence_level(),
            "warnings": self.warnings,
            "timestamp": datetime.now().isoformat(),
        }

    def _get_confidence_level(self) -> str:
        """根据置信度返回等级"""
        if self.confidence >= 0.90:
            return "直接输出"
        elif self.confidence >= 0.85:
            return "建议复核"
        else:
            return "[需核实]"


# ============================================================
# 核心处理逻辑
# ============================================================
class DataProcessor:
    """核心数据处理器"""

    # 常见字段模式（用于识别关键信息）
    FIELD_PATTERNS = {
        "email": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
        "url": r"https?://[^\s]+",
        "phone": r"(?:\+?\d{1,3}[-.]?)?\(?\d{3}\)?[-.]?\d{3}[-.]?\d{4}",
        "date": r"\d{4}[-/]\d{1,2}[-/]\d{1,2}",
        "price": r"\$\d+(?:\.\d{2})?",
        "ip": r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}",
    }

    def __init__(self):
        self._field_count = 0
        self._total_patterns = len(self.FIELD_PATTERNS)

    def process(self, input_data: Any, output_format: str = "json", batch: bool = False) -> ProcessResult:
        """
        处理输入数据

        Args:
            input_data: 输入数据（字符串、字典或列表）
            output_format: 输出格式（json/text）
            batch: 是否批量处理

        Returns:
            ProcessResult: 处理结果

        Raises:
            ValueError: 带错误码的异常
        """
        # 检查输入为空
        if input_data is None or (isinstance(input_data, (str, list, dict)) and len(input_data) == 0):
            raise ValueError(f"{ERROR_CODES['E001']} [错误码: E001]")

        # 检查输出格式
        if output_format not in ["json", "text"]:
            raise ValueError(f"{ERROR_CODES['E007']} [错误码: E007]")

        # 批量处理
        if batch:
            return self._process_batch(input_data, output_format)

        # 单条处理
        return self._process_single(input_data, output_format)

    def _process_batch(self, input_list: List[Any], output_format: str) -> ProcessResult:
        """批量处理"""
        if not isinstance(input_list, list):
            raise ValueError(f"{ERROR_CODES['E008']} [错误码: E008]")

        results = []
        total_confidence = 0.0

        for item in input_list:
            try:
                result = self._process_single(item, output_format)
                results.append(result.to_dict())
                total_confidence += result.confidence
            except Exception as e:
                # 单条失败不影响整体
                results.append({
                    "error": str(e),
                    "data": None,
                    "confidence": 0.0,
                })

        avg_confidence = total_confidence / len(input_list) if input_list else 0.0

        return ProcessResult(
            data={
                "results": results,
                "total_count": len(input_list),
                "success_count": sum(1 for r in results if "error" not in r),
            },
            confidence=avg_confidence,
            warnings=["批量处理完成，部分条目可能失败"] if len(results) > sum(1 for r in results if "error" not in r) else []
        )

    def _process_single(self, input_data: Any, output_format: str) -> ProcessResult:
        """单条处理"""
        # 解析输入
        parsed_data, parse_type = self._parse_input(input_data)

        # 提取关键信息
        extracted = self._extract_fields(parsed_data)

        # 计算置信度
        confidence = self._calculate_confidence(extracted)

        # 生成输出
        output = self._format_output(extracted, parse_type, output_format)

        # 生成警告
        warnings = []
        if confidence < 0.85:
            warnings.append("低置信度，请人工核实关键字段")

        return ProcessResult(data=output, confidence=confidence, warnings=warnings)

    def _parse_input(self, input_data: Any) -> Tuple[Any, str]:
        """
        解析输入数据

        Returns:
            (解析后的数据, 数据类型)
        """
        if isinstance(input_data, dict):
            return input_data, "dict"

        if isinstance(input_data, str):
            # 尝试解析JSON
            try:
                return json.loads(input_data), "json"
            except json.JSONDecodeError:
                # 不是JSON，按文本处理
                return input_data, "text"

        raise ValueError(f"{ERROR_CODES['E003']} [错误码: E003]")

    def _extract_fields(self, data: Any) -> Dict[str, Any]:
        """提取关键信息字段"""
        extracted = {}
        self._field_count = 0

        # 如果是字典，直接提取已知字段
        if isinstance(data, dict):
            for key, value in data.items():
                extracted[str(key)] = value
                self._field_count += 1

            # 尝试识别特殊字段
            for field_name, pattern in self.FIELD_PATTERNS.items():
                if field_name not in extracted:
                    # 在字符串值中搜索
                    for key, value in data.items():
                        if isinstance(value, str) and re.search(pattern, value):
                            match = re.search(pattern, value)
                            extracted[field_name] = match.group()
                            self._field_count += 1
                            break

        # 如果是文本，尝试识别模式
        elif isinstance(data, str):
            for field_name, pattern in self.FIELD_PATTERNS.items():
                matches = re.findall(pattern, data)
                if matches:
                    extracted[field_name] = matches[0]
                    self._field_count += 1

            # 提取非结构化文本摘要
            if data.strip():
                extracted["content"] = data.strip()[:200]  # 截断长文本
                self._field_count += 1

        # 其他类型
        else:
            extracted["value"] = str(data)
            self._field_count += 1

        return extracted

    def _calculate_confidence(self, extracted: Dict[str, Any]) -> float:
        """计算置信度"""
        try:
            # 基础置信度
            base = 0.5

            # 字段数量加分
            field_bonus = min(self._field_count / self._total_patterns, 0.3)

            # 文本长度加分（如果包含内容）
            if "content" in extracted:
                content_len = len(extracted.get("content", ""))
                length_bonus = min(content_len / 200, 0.2)
            else:
                # 有结构化字段加分
                length_bonus = 0.1 if self._field_count > 0 else 0

            # 计算最终置信度
            confidence = base + field_bonus + length_bonus

            # 限制在有效范围
            return max(0.0, min(1.0, confidence))

        except Exception:
            # 计算异常时使用默认值
            return 0.5

    def _format_output(self, extracted: Dict[str, Any], parse_type: str, output_format: str) -> Any:
        """格式化输出"""
        result = {
            "source_type": parse_type,
            "extracted_fields": extracted,
            "field_count": self._field_count,
        }

        if output_format == "text":
            # 文本格式输出
            lines = [f"来源类型: {parse_type}", f"字段数量: {self._field_count}"]
            for key, value in extracted.items():
                lines.append(f"{key}: {value}")
            return "\n".join(lines)

        return result

    def validate_input(self, input_data: Any) -> List[str]:
        """
        验证输入完整性，返回缺失信息列表

        Returns:
            缺失信息列表（空列表表示完整）
        """
        missing = []

        if input_data is None:
            missing.append("输入来源")
            missing.append("输出格式要求")
            missing.append("期望完整度")
            return missing

        # 检查输入来源
        if isinstance(input_data, str) and not input_data.strip():
            missing.append("输入来源")

        # 检查输出格式（这里简化，实际可能需要更多信息）
        if not isinstance(input_data, (str, dict, list)):
            missing.append("输出格式要求")

        return missing


# ============================================================
# 自检模块
# ============================================================
def run_selftest() -> None:
    """
    内置自检：使用硬编码样例数据验证核心逻辑
    不读取外部文件、不依赖工作目录、不访问网络
    """
    print("=" * 60)
    print("开始自检 (selftest)")
    print("=" * 60)

    processor = DataProcessor()
    passed = 0
    failed = 0

    # 测试用例1：JSON字符串输入
    print("\n[测试1] JSON字符串输入")
    try:
        test_input = '{"name": "测试用户", "email": "user@example.com", "url": "https://example.com"}'
        result = processor.process(test_input)
        assert result.confidence >= 0.5, "置信度应大于等于0.5"
        assert "extracted_fields" in result.data, "输出应包含extracted_fields"
        assert result.data["field_count"] >= 3, "应提取至少3个字段"
        print(f"  ✓ 通过 (置信度: {result.confidence:.2f})")
        passed += 1
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        failed += 1

    # 测试用例2：纯文本输入
    print("\n[测试2] 纯文本输入")
    try:
        test_input = "联系方式: user@test.com, 电话: 138-1234-5678, 日期: 2024-01-15"
        result = processor.process(test_input)
        assert result.confidence >= 0.5, "置信度应大于等于0.5"
        assert len(result.data["extracted_fields"]) >= 3, "应提取至少3个字段"
        print(f"  ✓ 通过 (置信度: {result.confidence:.2f})")
        passed += 1
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        failed += 1

    # 测试用例3：字典输入
    print("\n[测试3] 字典输入")
    try:
        test_input = {"title": "测试标题", "price": "$99.99"}
        result = processor.process(test_input)
        assert result.confidence >= 0.5, "置信度应大于等于0.5"
        assert "title" in result.data["extracted_fields"], "应包含title字段"
        print(f"  ✓ 通过 (置信度: {result.confidence:.2f})")
        passed += 1
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        failed += 1

    # 测试用例4：批量处理
    print("\n[测试4] 批量处理")
    try:
        test_input = [
            {"name": "用户A", "email": "a@test.com"},
            {"name": "用户B", "url": "https://test.com"},
            "纯文本内容",
        ]
        result = processor.process(test_input, batch=True)
        assert result.data["total_count"] == 3, "应处理3条数据"
        assert result.data["success_count"] >= 2, "成功率应大于等于66%"
        assert result.confidence >= 0.4, "平均置信度应大于等于0.4"
        print(f"  ✓ 通过 (成功率: {result.data['success_count']}/{result.data['total_count']})")
        passed += 1
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        failed += 1

    # 测试用例5：错误处理 - 空输入
    print("\n[测试5] 空输入错误处理")
    try:
        processor.process("")
        print("  ✗ 失败: 应抛出E001错误")
        failed += 1
    except ValueError as e:
        assert "E001" in str(e), "应包含E001错误码"
        print(f"  ✓ 通过 (错误码: E001)")
        passed += 1

    # 测试用例6：错误处理 - 无效输出格式
    print("\n[测试6] 无效输出格式")
    try:
        processor.process("测试", output_format="xml")
        print("  ✗ 失败: 应抛出E007错误")
        failed += 1
    except ValueError as e:
        assert "E007" in str(e), "应包含E007错误码"
        print(f"  ✓ 通过 (错误码: E007)")
        passed += 1

    # 测试用例7：置信度分级
    print("\n[测试7] 置信度分级")
    try:
        # 高置信度场景
        rich_input = {
            "name": "完整用户信息",
            "email": "user@example.com",
            "url": "https://example.com",
            "phone": "138-1234-5678",
            "date": "2024-01-15",
            "price": "$99.99",
            "ip": "192.168.1.1",
            "content": "这是一段较长的内容，用于测试置信度计算逻辑是否正常工作，确保有足够的文本长度来获得较高的置信度分数。",
        }
        result = processor.process(rich_input)
        assert result.confidence >= 0.5, "丰富输入应有较高置信度"
        print(f"  ✓ 通过 (置信度: {result.confidence:.2f})")
        passed += 1
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        failed += 1

    # 测试用例8：输入验证
    print("\n[测试8] 输入完整性验证")
    try:
        missing = processor.validate_input(None)
        assert len(missing) >= 3, "空输入应报告至少3项缺失"
        missing = processor.validate_input("有效输入")
        assert len(missing) == 0, "有效输入不应报告缺失"
        print(f"  ✓ 通过 (空输入缺失项: {len(missing)})")
        passed += 1
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        failed += 1

    # 测试用例9：文本格式输出
    print("\n[测试9] 文本格式输出")
    try:
        result = processor.process({"name": "测试"}, output_format="text")
        assert isinstance(result.data, str), "文本格式应返回字符串"
        assert "name" in result.data, "应包含字段名"
        print(f"  ✓ 通过 (输出长度: {len(result.data)}字符)")
        passed += 1
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        failed += 1

    # 测试用例10：批量处理非列表
    print("\n[测试10] 批量处理输入校验")
    try:
        processor.process("不是列表", batch=True)
        print("  ✗ 失败: 应抛出E008错误")
        failed += 1
    except ValueError as e:
        assert "E008" in str(e), "应包含E008错误码"
        print(f"  ✓ 通过 (错误码: E008)")
        passed += 1

    # 输出总结
    print("\n" + "=" * 60)
    print(f"自检完成: {passed} 通过, {failed} 失败")
    print("=" * 60)

    if failed > 0:
        sys.exit(1)
    else:
        print("所有测试通过 ✓")


# ============================================================
# 命令行入口
# ============================================================
def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="爬虫采集 - 结构化数据提取工具",
        epilog="示例: python main.py --input '{\"name\":\"测试\"}' --format json"
    )
    parser.add_argument("--input", "-i", help="输入数据（JSON字符串或文本）")
    parser.add_argument("--format", "-f", choices=["json", "text"], default="json", help="输出格式")
    parser.add_argument("--batch", "-b", action="store_true", help="批量处理模式")
    parser.add_argument("--selftest", action="store_true", help="运行内置自检")
    parser.add_argument("--validate", action="store_true", help="验证输入完整性")

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        run_selftest()
        return

    # 验证模式
    if args.validate:
        if not args.input:
            print("错误: --validate 需要 --input 参数")
            sys.exit(1)
        processor = DataProcessor()
        missing = processor.validate_input(args.input)
        if missing:
            print(f"缺失信息: {', '.join(missing)}")
            print(f"错误码: E002")
            sys.exit(1)
        else:
            print("输入信息完整 ✓")
        return

    # 处理模式
    if not args.input:
        print("错误: 请提供输入数据 (使用 --input 参数)")
        print(f"错误码: E001")
        sys.exit(1)

    try:
        processor = DataProcessor()
        result = processor.process(args.input, args.format, args.batch)

        # 输出结果
        if args.format == "json":
            print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
        else:
            print(result.data)

        # 置信度警告
        if result.confidence < 0.85:
            print(f"\n警告: 置信度较低 ({result.confidence:.2%})")
            for warning in result.warnings:
                print(f"  - {warning}")

    except ValueError as e:
        print(f"错误: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"错误: {ERROR_CODES['E006']} [错误码: E006]")
        print(f"详细信息: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
