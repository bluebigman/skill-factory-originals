#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py - 未命名工具 (s3)

一个基于功能规格独立实现的伪 S3 协议处理工具。
仅依赖标准库，支持命令行调用与离线自检。

错误码:
    E001: 输入为空
    E002: 关键信息缺失
    E003: 输入格式错误
    E004: 超出能力边界
    E005: 置信度过低
    E006: 内部处理异常
    E007: 参数解析失败
    E008: 自检数据异常
    E009: 输出生成失败
    E010: 未知错误
"""

import argparse
import json
import re
import sys
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# 常量定义
# ---------------------------------------------------------------------------

# 能力边界声明
CAPABILITY_BOUNDARIES = [
    "不执行超出输入范围的分析",
    "不保证绝对准确，低置信度会标注",
    "不访问网络或外部服务",
]

# 置信度阈值
CONFIDENCE_HIGH = 0.90
CONFIDENCE_MEDIUM = 0.85

# 默认输出模板字段
DEFAULT_OUTPUT_FIELDS = [
    "id",
    "timestamp",
    "source",
    "content",
    "confidence",
    "status",
    "notes",
]

# 错误码与标准化话术映射
ERROR_MESSAGES = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：{details}",
    "E003": "输入格式不符合要求，示例：{example}",
    "E004": "这超出了本工具的能力范围，建议：{suggestion}",
    "E005": "结果无法确定，建议：{suggestion}",
    "E006": "内部处理异常，请重试或检查输入",
    "E007": "参数解析失败，请检查命令行参数",
    "E008": "自检数据异常，请联系开发者",
    "E009": "输出生成失败，请检查输出格式",
    "E010": "未知错误，请查看日志",
}


# ---------------------------------------------------------------------------
# 核心数据结构
# ---------------------------------------------------------------------------

class ProcessingResult:
    """处理结果的数据结构"""

    def __init__(
        self,
        result_id: str,
        timestamp: str,
        source: str,
        content: Any,
        confidence: float,
        status: str,
        notes: List[str],
    ):
        self.id = result_id
        self.timestamp = timestamp
        self.source = source
        self.content = content
        self.confidence = confidence
        self.status = status
        self.notes = notes

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "source": self.source,
            "content": self.content,
            "confidence": self.confidence,
            "status": self.status,
            "notes": self.notes,
        }

    def to_json(self) -> str:
        """转换为 JSON 字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# 核心处理逻辑
# ---------------------------------------------------------------------------

class S3Processor:
    """
    核心处理器：负责输入解析、结构化、置信度评估与输出生成。
    """

    def __init__(self):
        self._input_data: Optional[Any] = None
        self._source_type: str = "unknown"
        self._output_format: str = "json"
        self._completeness: str = "standard"

    def set_input(self, data: Any, source_type: str = "text") -> None:
        """设置输入数据"""
        self._input_data = data
        self._source_type = source_type

    def set_options(self, output_format: str = "json", completeness: str = "standard") -> None:
        """设置处理选项"""
        self._output_format = output_format
        self._completeness = completeness

    def process(self) -> ProcessingResult:
        """
        执行核心处理流程。

        流程:
            1. 校验输入
            2. 解析并结构化
            3. 计算置信度
            4. 生成结果

        Raises:
            RuntimeError: 当输入为空或格式错误时抛出，携带错误码
        """
        # 步骤 1: 输入校验
        if self._input_data is None or self._input_data == "":
            raise RuntimeError("E001")

        if self._source_type == "unknown":
            raise RuntimeError("E003")

        # 步骤 2: 解析输入
        try:
            parsed_content = self._parse_input()
        except ValueError as e:
            raise RuntimeError(f"E003:{str(e)}") from e

        # 步骤 3: 识别关键信息
        key_info = self._extract_key_info(parsed_content)

        # 步骤 4: 计算置信度
        confidence = self._calculate_confidence(key_info)

        # 步骤 5: 构建输出
        status, notes = self._evaluate_confidence(confidence)

        result = ProcessingResult(
            result_id=str(uuid.uuid4()),
            timestamp=datetime.now().isoformat(),
            source=self._source_type,
            content=key_info,
            confidence=confidence,
            status=status,
            notes=notes,
        )

        return result

    def _parse_input(self) -> Any:
        """
        解析输入数据。

        支持:
            - 文本: 原样返回
            - JSON 字符串: 解析为字典/列表
            - URL: 提取 URL 信息
            - 文件路径: 尝试读取文件内容

        Returns:
            解析后的数据

        Raises:
            ValueError: 输入格式错误
        """
        if self._source_type == "text":
            return self._input_data

        elif self._source_type == "json":
            try:
                return json.loads(self._input_data)
            except json.JSONDecodeError as e:
                raise ValueError(f"JSON 解析失败: {e}") from e

        elif self._source_type == "url":
            # 仅识别 URL 格式，不进行网络访问
            url_pattern = re.compile(
                r"^(https?://)?([a-zA-Z0-9.-]+)(:[0-9]+)?(/[^\s]*)?$"
            )
            if not url_pattern.match(self._input_data):
                raise ValueError("URL 格式不正确")
            return {"url": self._input_data, "type": "url"}

        elif self._source_type == "file":
            # 尝试读取本地文件
            try:
                with open(self._input_data, "r", encoding="utf-8") as f:
                    return f.read()
            except (IOError, OSError) as e:
                raise ValueError(f"文件读取失败: {e}") from e

        else:
            raise ValueError(f"不支持的输入类型: {self._source_type}")

    def _extract_key_info(self, data: Any) -> Dict[str, Any]:
        """
        从解析后的数据中提取关键信息。

        Args:
            data: 解析后的输入数据

        Returns:
            结构化关键信息
        """
        if isinstance(data, dict):
            # 字典输入：直接使用，但只保留常见字段
            allowed_keys = {"id", "name", "content", "type", "value", "url", "path"}
            filtered = {k: v for k, v in data.items() if k in allowed_keys}
            return filtered if filtered else {"content": data}

        elif isinstance(data, list):
            # 列表输入：批量处理
            items = []
            for item in data[:10]:  # 最多处理 10 条
                if isinstance(item, dict):
                    items.append(item)
                else:
                    items.append({"item": item})
            return {"items": items, "count": len(items)}

        elif isinstance(data, str):
            # 文本输入：识别关键字段
            return self._extract_from_text(data)

        else:
            return {"content": data}

    def _extract_from_text(self, text: str) -> Dict[str, Any]:
        """
        从纯文本中提取关键信息。

        识别:
            - 数字
            - 日期
            - 邮箱
            - 关键词

        Args:
            text: 输入文本

        Returns:
            提取的关键信息
        """
        info: Dict[str, Any] = {}

        # 识别数字
        numbers = re.findall(r"\d+(?:\.\d+)?", text)
        if numbers:
            info["numbers"] = numbers

        # 识别日期 (YYYY-MM-DD 或 YYYY/MM/DD)
        dates = re.findall(r"\d{4}[-/]\d{1,2}[-/]\d{1,2}", text)
        if dates:
            info["dates"] = dates

        # 识别邮箱
        emails = re.findall(r"[\w.+-]+@[\w-]+\.[\w.]+", text)
        if emails:
            info["emails"] = emails

        # 识别 URL
        urls = re.findall(r"https?://[^\s]+", text)
        if urls:
            info["urls"] = urls

        # 基本文本信息
        info["text_length"] = len(text)
        info["word_count"] = len(text.split())

        if not info:
            info["content"] = text

        return info

    def _calculate_confidence(self, key_info: Dict[str, Any]) -> float:
        """
        计算置信度。

        规则:
            - 信息完整度越高，置信度越高
            - 根据字段数量和数据丰富度评分

        Args:
            key_info: 提取的关键信息

        Returns:
            置信度 (0.0 - 1.0)
        """
        if not key_info:
            return 0.0

        score = 0.0
        total_weight = 0.0

        # 根据信息类型计算权重
        weights = {
            "numbers": 0.2,
            "dates": 0.2,
            "emails": 0.3,
            "urls": 0.3,
            "content": 0.1,
            "items": 0.3,
            "count": 0.1,
            "text_length": 0.05,
            "word_count": 0.05,
        }

        for key, value in key_info.items():
            weight = weights.get(key, 0.1)
            total_weight += weight

            if isinstance(value, list) and len(value) > 0:
                score += weight * min(1.0, len(value) / 3)
            elif isinstance(value, (int, float)) and value > 0:
                score += weight * min(1.0, value / 100)
            elif isinstance(value, str) and len(value) > 0:
                score += weight * min(1.0, len(value) / 50)
            elif isinstance(value, dict) and len(value) > 0:
                score += weight * 0.8
            else:
                score += weight * 0.5

        if total_weight == 0:
            return 0.5

        confidence = score / total_weight

        # 边界限制
        return max(0.0, min(1.0, confidence))

    def _evaluate_confidence(self, confidence: float) -> Tuple[str, List[str]]:
        """
        根据置信度评估结果状态。

        Args:
            confidence: 置信度值

        Returns:
            (状态, 备注列表)
        """
        if confidence >= CONFIDENCE_HIGH:
            return "ok", ["置信度较高，可直接使用"]

        elif confidence >= CONFIDENCE_MEDIUM:
            return "review", ["建议复核", f"置信度: {confidence:.0%}"]

        else:
            return "uncertain", [
                "[需核实]",
                f"置信度: {confidence:.0%}",
                "关键信息不完整，请人工确认",
            ]

    def format_output(self, result: ProcessingResult) -> str:
        """
        根据指定格式生成输出。

        Args:
            result: 处理结果

        Returns:
            格式化后的输出字符串

        Raises:
            RuntimeError: 输出格式不支持
        """
        if self._output_format == "json":
            return result.to_json()

        elif self._output_format == "text":
            lines = [
                f"ID: {result.id}",
                f"时间: {result.timestamp}",
                f"来源: {result.source}",
                f"状态: {result.status}",
                f"置信度: {result.confidence:.0%}",
                "---",
                "内容:",
                json.dumps(result.content, ensure_ascii=False, indent=2),
                "---",
                "备注:",
            ]
            lines.extend([f"  - {note}" for note in result.notes])
            return "\n".join(lines)

        elif self._output_format == "compact":
            # 紧凑格式
            return json.dumps(
                {
                    "id": result.id,
                    "status": result.status,
                    "confidence": round(result.confidence, 2),
                    "content": result.content,
                },
                ensure_ascii=False,
            )

        else:
            raise RuntimeError("E009")


# ---------------------------------------------------------------------------
# 自检功能
# ---------------------------------------------------------------------------

def run_selftest() -> bool:
    """
    运行内置自检，验证核心逻辑。

    测试用例:
        1. 正常文本输入
        2. JSON 输入
        3. 空输入（应报错 E001）
        4. 低置信度输入

    Returns:
        True 表示自检通过
    """
    print("开始自检...")
    processor = S3Processor()

    # 测试 1: 正常文本输入
    print("测试 1: 文本输入")
    processor.set_input("示例文本，包含 123 个数字和 test@example.com 邮箱", "text")
    result = processor.process()
    assert result.status == "ok" or result.status == "review", "文本输入处理失败"
    assert result.confidence > 0, "置信度不应为 0"
    print(f"  ✓ 通过 (置信度: {result.confidence:.0%})")

    # 测试 2: JSON 输入
    print("测试 2: JSON 输入")
    json_data = json.dumps({"name": "测试", "value": 42, "type": "sample"})
    processor.set_input(json_data, "json")
    result = processor.process()
    assert result.content.get("name") == "测试", "JSON 解析失败"
    print(f"  ✓ 通过 (置信度: {result.confidence:.0%})")

    # 测试 3: 空输入
    print("测试 3: 空输入")
    try:
        processor.set_input("", "text")
        processor.process()
        assert False, "空输入应抛出 E001"
    except RuntimeError as e:
        assert str(e) == "E001", f"错误码不正确: {e}"
        print("  ✓ 通过 (正确抛出 E001)")

    # 测试 4: 低置信度输入
    print("测试 4: 低置信度输入")
    processor.set_input("x", "text")
    result = processor.process()
    assert result.confidence < CONFIDENCE_MEDIUM, "简单输入置信度应较低"
    print(f"  ✓ 通过 (置信度: {result.confidence:.0%})")

    # 测试 5: 错误输入类型
    print("测试 5: 错误输入类型")
    try:
        processor.set_input("test", "unknown_type")
        processor.process()
        assert False, "未知类型应抛出 E003"
    except RuntimeError as e:
        assert str(e) == "E003", f"错误码不正确: {e}"
        print("  ✓ 通过 (正确抛出 E003)")

    # 测试 6: 批量处理
    print("测试 6: 批量处理")
    items = [{"id": i, "value": f"item_{i}"} for i in range(3)]
    processor.set_input(json.dumps(items), "json")
    result = processor.process()
    assert result.content.get("count") == 3, "批量处理失败"
    print(f"  ✓ 通过 (处理 {result.content['count']} 条)")

    print("\n所有自检通过!")
    return True


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------

def main() -> int:
    """
    命令行主入口。

    Returns:
        退出码 (0 成功, 非 0 失败)
    """
    parser = argparse.ArgumentParser(
        description="未命名工具 (s3) - 伪 S3 协议处理工具",
        epilog="示例: python main.py --input '示例文本' --source text",
    )

    parser.add_argument(
        "--input",
        type=str,
        help="输入数据（文本、JSON 字符串、URL 或文件路径）",
    )
    parser.add_argument(
        "--source",
        type=str,
        choices=["text", "json", "url", "file"],
        default="text",
        help="输入数据类型 (默认: text)",
    )
    parser.add_argument(
        "--format",
        type=str,
        choices=["json", "text", "compact"],
        default="json",
        help="输出格式 (默认: json)",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检并退出",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="s3 1.0.0",
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        try:
            run_selftest()
            return 0
        except AssertionError as e:
            print(f"自检失败: {e}", file=sys.stderr)
            return 1
        except Exception as e:
            print(f"自检异常: {e}", file=sys.stderr)
            return 2

    # 正常处理模式
    if not args.input:
        print(f"E001: {ERROR_MESSAGES['E001']}", file=sys.stderr)
        return 1

    try:
        processor = S3Processor()
        processor.set_input(args.input, args.source)
        processor.set_options(output_format=args.format)

        result = processor.process()
        output = processor.format_output(result)

        print(output)
        return 0

    except RuntimeError as e:
        error_code = str(e)
        message = ERROR_MESSAGES.get(error_code, ERROR_MESSAGES["E010"])

        # 处理带详细信息的错误码 (如 E003:xxx)
        if ":" in error_code:
            code, details = error_code.split(":", 1)
            message = ERROR_MESSAGES.get(code, ERROR_MESSAGES["E010"])
            message = message.format(example=details)

        print(f"{error_code}: {message}", file=sys.stderr)
        return 1

    except Exception as e:
        print(f"E010: {ERROR_MESSAGES['E010']} - {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
