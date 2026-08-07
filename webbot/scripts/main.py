#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
webbot - 爬虫采集技能实现脚本
版本: 1.0.0
许可证: MIT
"""

import argparse
import json
import sys
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# 错误码定义
# ---------------------------------------------------------------------------
ERROR_CODES = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：...",
    "E003": "输入格式不符合要求，示例：...",
    "E004": "这超出了本工具的能力范围，建议...",
    "E005": "结果无法确定，建议：...",
    "E006": "内部处理错误，请重试或检查输入",
    "E007": "输出格式不支持，可选: json/text",
    "E008": "批量输入格式错误，应为 JSON 数组",
    "E009": "字段提取失败，请检查输入内容",
    "E010": "置信度计算失败，请检查输入内容",
}


# ---------------------------------------------------------------------------
# 核心数据结构
# ---------------------------------------------------------------------------
class ProcessingResult:
    """处理结果数据类"""

    def __init__(self, success: bool, data: Optional[Dict] = None,
                 error_code: Optional[str] = None, message: str = ""):
        self.success = success
        self.data = data or {}
        self.error_code = error_code
        self.message = message

    def to_dict(self) -> Dict:
        """转换为字典"""
        result = {
            "success": self.success,
            "data": self.data,
            "message": self.message,
        }
        if self.error_code:
            result["error_code"] = self.error_code
        return result


# ---------------------------------------------------------------------------
# 核心处理逻辑
# ---------------------------------------------------------------------------
class WebbotProcessor:
    """爬虫采集核心处理器"""

    # 置信度阈值
    HIGH_CONFIDENCE = 0.90
    MEDIUM_CONFIDENCE = 0.85

    def __init__(self):
        """初始化处理器"""
        self.supported_keys = {"url", "title", "content", "tags", "date"}

    def process_single(self, input_data: Any, output_format: str = "json") -> ProcessingResult:
        """
        处理单个输入

        Args:
            input_data: 输入数据（字符串或字典）
            output_format: 输出格式（json/text）

        Returns:
            ProcessingResult: 处理结果
        """
        # 检查输入为空
        if input_data is None or (isinstance(input_data, str) and not input_data.strip()):
            return ProcessingResult(False, error_code="E001",
                                    message=ERROR_CODES["E001"])

        # 解析输入
        parsed_data, confidence = self._parse_input(input_data)

        if not parsed_data:
            return ProcessingResult(False, error_code="E003",
                                    message=ERROR_CODES["E003"])

        # 检查置信度
        if confidence < self.MEDIUM_CONFIDENCE:
            return ProcessingResult(False, error_code="E005",
                                    message=ERROR_CODES["E005"])

        # 生成输出
        result_data = self._format_output(parsed_data, confidence, output_format)

        return ProcessingResult(True, data=result_data)

    def process_batch(self, inputs: List[Any], output_format: str = "json") -> ProcessingResult:
        """
        批量处理输入

        Args:
            inputs: 输入列表
            output_format: 输出格式

        Returns:
            ProcessingResult: 处理结果
        """
        if not isinstance(inputs, list):
            return ProcessingResult(False, error_code="E008",
                                    message=ERROR_CODES["E008"])

        if not inputs:
            return ProcessingResult(False, error_code="E001",
                                    message=ERROR_CODES["E001"])

        results = []
        for item in inputs:
            result = self.process_single(item, output_format)
            results.append(result.to_dict())

        # 计算总体置信度（取平均值）
        total_confidence = 0.0
        success_count = 0
        for r in results:
            if r["success"]:
                success_count += 1
                if "confidence" in r["data"]:
                    total_confidence += r["data"]["confidence"]

        avg_confidence = total_confidence / success_count if success_count > 0 else 0.0

        batch_result = {
            "total": len(results),
            "success_count": success_count,
            "failed_count": len(results) - success_count,
            "avg_confidence": avg_confidence,
            "results": results,
        }

        return ProcessingResult(True, data=batch_result)

    def _parse_input(self, input_data: Any) -> Tuple[Optional[Dict], float]:
        """
        解析输入数据

        Args:
            input_data: 输入数据

        Returns:
            (解析后的数据, 置信度)
        """
        # 处理字符串输入
        if isinstance(input_data, str):
            return self._parse_text(input_data)

        # 处理字典输入
        if isinstance(input_data, dict):
            return self._parse_dict(input_data)

        return None, 0.0

    def _parse_text(self, text: str) -> Tuple[Optional[Dict], float]:
        """解析文本输入"""
        # 尝试解析 JSON
        try:
            data = json.loads(text)
            if isinstance(data, dict):
                return self._parse_dict(data)
        except json.JSONDecodeError:
            pass

        # 检查是否为 URL
        if text.startswith(("http://", "https://")):
            return {
                "url": text,
                "title": text.split("/")[-1] or text,
                "content": "",
                "tags": [],
                "date": "",
                "source_type": "url",
            }, 0.95

        # 普通文本处理（模拟）
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        if not lines:
            return None, 0.0

        # 提取关键信息（简化处理）
        data = {
            "title": lines[0] if lines else "",
            "content": " ".join(lines[1:]) if len(lines) > 1 else "",
            "tags": [],
            "date": self._extract_date(text),
            "source_type": "text",
        }

        # 计算置信度
        confidence = 0.85
        if data["title"] and data["content"]:
            confidence = 0.92
        elif data["title"]:
            confidence = 0.88

        return data, confidence

    def _parse_dict(self, data: Dict) -> Tuple[Optional[Dict], float]:
        """解析字典输入"""
        # 检查关键字段
        url = data.get("url", "")
        title = data.get("title", "")
        content = data.get("content", "")

        if not url and not title and not content:
            # 尝试从其他字段提取
            for key in data:
                if key.lower() in self.supported_keys:
                    break
            else:
                return None, 0.0

        # 提取支持的字段
        parsed = {
            "url": url,
            "title": title,
            "content": content,
            "tags": data.get("tags", []),
            "date": data.get("date", ""),
            "source_type": data.get("source_type", "structured"),
        }

        # 计算置信度
        confidence = 0.85
        if url and title and content:
            confidence = 0.95
        elif url and title:
            confidence = 0.90
        elif url or title:
            confidence = 0.87

        return parsed, confidence

    def _extract_date(self, text: str) -> str:
        """从文本中提取日期（简化实现）"""
        import re
        date_patterns = [
            r"\d{4}-\d{2}-\d{2}",
            r"\d{4}/\d{2}/\d{2}",
            r"\d{4}年\d{1,2}月\d{1,2}日",
        ]
        for pattern in date_patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(0)
        return ""

    def _format_output(self, data: Dict, confidence: float,
                       output_format: str) -> Dict:
        """格式化输出"""
        # 添加置信度标注
        if confidence >= self.HIGH_CONFIDENCE:
            data["confidence_label"] = "高置信度"
        elif confidence >= self.MEDIUM_CONFIDENCE:
            data["confidence_label"] = "建议复核"
        else:
            data["confidence_label"] = "[需核实]"

        data["confidence"] = round(confidence, 2)

        # 根据输出格式处理
        if output_format == "text":
            data["formatted_text"] = self._to_text(data)
        elif output_format == "json":
            pass  # 已经是 JSON 兼容格式
        else:
            raise ValueError(f"不支持的输出格式: {output_format}")

        return data

    def _to_text(self, data: Dict) -> str:
        """转换为文本格式"""
        lines = []
        if data.get("title"):
            lines.append(f"标题: {data['title']}")
        if data.get("url"):
            lines.append(f"URL: {data['url']}")
        if data.get("content"):
            lines.append(f"内容: {data['content']}")
        if data.get("tags"):
            lines.append(f"标签: {', '.join(data['tags'])}")
        if data.get("date"):
            lines.append(f"日期: {data['date']}")
        lines.append(f"置信度: {data.get('confidence', 0):.0%} "
                     f"({data.get('confidence_label', '')})")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# 自检功能
# ---------------------------------------------------------------------------
def run_selftest() -> bool:
    """
    运行内置自检

    Returns:
        bool: 自检是否通过
    """
    print("开始自检...")

    # 测试数据（硬编码，不依赖外部文件）
    test_cases = [
        # 基本文本输入
        {
            "input": "这是一个测试标题\n这是测试内容的第一行\n这是第二行",
            "expected": {"success": True, "min_confidence": 0.80}
        },
        # URL 输入
        {
            "input": "https://example.com/test-page",
            "expected": {"success": True, "min_confidence": 0.90}
        },
        # 字典输入
        {
            "input": {
                "url": "https://example.com/article",
                "title": "测试文章",
                "content": "这是文章内容",
                "tags": ["测试", "示例"]
            },
            "expected": {"success": True, "min_confidence": 0.85}
        },
        # 空输入（应返回错误）
        {
            "input": "",
            "expected": {"success": False, "error_code": "E001"}
        },
        # JSON 字符串输入
        {
            "input": json.dumps({
                "url": "https://example.com/json",
                "title": "JSON 测试",
                "content": "JSON 内容"
            }),
            "expected": {"success": True, "min_confidence": 0.85}
        },
    ]

    processor = WebbotProcessor()
    all_passed = True

    for i, test in enumerate(test_cases, 1):
        try:
            result = processor.process_single(test["input"])
            expected = test["expected"]

            if expected.get("success"):
                # 期望成功
                if not result.success:
                    print(f"  测试 {i} 失败: 期望成功但失败，错误码={result.error_code}")
                    all_passed = False
                else:
                    # 检查置信度（宽松阈值）
                    actual_conf = result.data.get("confidence", 0)
                    min_conf = expected.get("min_confidence", 0.50)
                    if actual_conf < min_conf:
                        print(f"  测试 {i} 失败: 置信度 {actual_conf:.2f} 低于阈值 {min_conf:.2f}")
                        all_passed = False
                    else:
                        print(f"  测试 {i} 通过: 置信度={actual_conf:.2f}")
            else:
                # 期望失败
                if result.success:
                    print(f"  测试 {i} 失败: 期望失败但成功")
                    all_passed = False
                elif expected.get("error_code") and result.error_code != expected["error_code"]:
                    print(f"  测试 {i} 失败: 错误码不匹配，期望 {expected['error_code']}，实际 {result.error_code}")
                    all_passed = False
                else:
                    print(f"  测试 {i} 通过: 正确拒绝输入，错误码={result.error_code}")

        except Exception as e:
            print(f"  测试 {i} 异常: {str(e)}")
            all_passed = False

    # 测试批量处理
    print("  测试批量处理...")
    try:
        batch_input = [
            "https://example.com/1",
            "https://example.com/2",
            {"url": "https://example.com/3", "title": "第三篇"},
        ]
        batch_result = processor.process_batch(batch_input)
        if batch_result.success:
            total = batch_result.data.get("total", 0)
            success_count = batch_result.data.get("success_count", 0)
            if total == 3 and success_count >= 2:
                print(f"  批量处理通过: {success_count}/{total} 成功")
            else:
                print(f"  批量处理失败: 成功数 {success_count}/{total} 不符合预期")
                all_passed = False
        else:
            print(f"  批量处理失败: {batch_result.message}")
            all_passed = False
    except Exception as e:
        print(f"  批量处理异常: {str(e)}")
        all_passed = False

    if all_passed:
        print("自检通过：所有测试用例均通过。")
    else:
        print("自检失败：存在未通过的测试用例。")

    return all_passed


# ---------------------------------------------------------------------------
# 主程序入口
# ---------------------------------------------------------------------------
def main() -> int:
    """主函数"""
    parser = argparse.ArgumentParser(
        description="webbot - 爬虫采集技能工具"
    )
    parser.add_argument(
        "--input", "-i",
        type=str,
        help="输入数据（文本、URL 或 JSON 字符串）"
    )
    parser.add_argument(
        "--format", "-f",
        type=str,
        choices=["json", "text"],
        default="json",
        help="输出格式 (默认: json)"
    )
    parser.add_argument(
        "--batch", "-b",
        type=str,
        help="批量输入（JSON 数组字符串）"
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检"
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        success = run_selftest()
        return 0 if success else 1

    # 创建处理器
    processor = WebbotProcessor()

    try:
        # 批量处理模式
        if args.batch:
            try:
                batch_data = json.loads(args.batch)
            except json.JSONDecodeError:
                print(json.dumps({
                    "success": False,
                    "error_code": "E008",
                    "message": ERROR_CODES["E008"]
                }, ensure_ascii=False))
                return 1

            result = processor.process_batch(batch_data, args.format)

        # 单条处理模式
        elif args.input:
            result = processor.process_single(args.input, args.format)

        # 无输入
        else:
            result = ProcessingResult(False, error_code="E001",
                                      message=ERROR_CODES["E001"])

        # 输出结果
        if args.format == "json":
            print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
        else:
            if result.success:
                print(result.data.get("formatted_text", "处理成功"))
            else:
                print(f"错误: {result.message}")

        return 0 if result.success else 1

    except Exception as e:
        # 通用错误处理
        print(json.dumps({
            "success": False,
            "error_code": "E006",
            "message": f"{ERROR_CODES['E006']} 详情: {str(e)}"
        }, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    sys.exit(main())
