#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py

爬虫采集（automate-download-freesound）独立实现脚本。

本脚本依据《功能规格》进行 clean-room 重写：
- 仅依赖 Python 标准库；
- 提供命令行解析、核心处理逻辑、错误码体系；
- 支持 --selftest 离线自检（内置硬编码样例，不访问网络/文件）。

用法示例：
    python scripts/main.py --input "待处理内容" --format json
    python scripts/main.py --selftest
"""

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# 错误码定义（E001-E010）
# ---------------------------------------------------------------------------
ERROR_CODES = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：...（逐项追问）",
    "E003": "输入格式不符合要求，示例：...",
    "E004": "这超出了本工具的能力范围，建议...",
    "E005": "结果无法确定，建议：...",
    "E006": "内部处理异常，请稍后重试。",
    "E007": "输出格式不支持，支持：json / text。",
    "E008": "批量处理时输入必须为列表。",
    "E009": "置信度计算参数异常。",
    "E010": "未知错误，请检查输入后重试。",
}


# ---------------------------------------------------------------------------
# 数据模型
# ---------------------------------------------------------------------------
@dataclass
class ProcessingResult:
    """结构化处理结果。"""

    content: Any = None
    confidence: float = 0.0
    fields: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    needs_review: bool = False
    needs_verification: bool = False


@dataclass
class InputPackage:
    """标准化输入包。"""

    source: Any = None
    source_type: str = "unknown"  # text / file / url / list
    format: str = "text"
    detail_level: str = "standard"  # quick / standard / detailed


# ---------------------------------------------------------------------------
# 核心处理逻辑
# ---------------------------------------------------------------------------
class CoreProcessor:
    """
    核心处理器：负责输入解析、关键信息识别、结构化输出、置信度计算。
    """

    # 可识别的关键字段（示例）
    KEY_FIELDS = [
        "id",
        "name",
        "type",
        "url",
        "description",
        "tags",
        "created_at",
        "author",
    ]

    # 字段权重（用于置信度计算）
    FIELD_WEIGHTS = {
        "id": 2.0,
        "name": 1.5,
        "type": 1.0,
        "url": 1.5,
        "description": 1.0,
        "tags": 0.5,
        "created_at": 0.5,
        "author": 0.5,
    }

    # 关键字段（缺失时会触发 E002 错误）
    CRITICAL_FIELDS = ["name", "type", "url"]

    def __init__(self) -> None:
        self._error_handler = ErrorHandler()

    def process(self, package: InputPackage) -> ProcessingResult:
        """执行核心流程。"""
        # 1. 输入校验
        if package.source is None or package.source == "":
            self._error_handler.raise_error("E001")

        # 2. 解析输入（根据来源类型）
        parsed_data = self._parse_input(package)

        # 3. 识别关键字段
        structured, missing = self._extract_fields(parsed_data)

        # 4. 检查关键信息是否缺失（仅在非列表输入时检查）
        if missing and package.source_type != "list":
            self._error_handler.raise_error("E002", details=", ".join(missing))

        # 5. 计算置信度
        confidence = self._calculate_confidence(structured, missing)

        # 6. 构建结果
        result = ProcessingResult(
            content=structured,
            confidence=confidence,
            fields=structured,
        )

        # 7. 置信度标注
        if confidence >= 0.90:
            pass  # 直接输出
        elif 0.85 <= confidence < 0.90:
            result.needs_review = True
            result.warnings.append("建议复核：置信度低于90%")
        else:
            result.needs_verification = True
            result.warnings.append("[需核实] 置信度低于85%，请人工确认")

        return result

    def _parse_input(self, package: InputPackage) -> Any:
        """根据输入类型解析原始数据。"""
        source = package.source

        if package.source_type == "text":
            # 文本输入：尝试解析为 JSON，否则按纯文本处理
            try:
                return json.loads(source) if isinstance(source, str) else source
            except (json.JSONDecodeError, TypeError):
                return source

        elif package.source_type == "url":
            # URL 输入：提取 URL 并构造基础结构（不访问网络）
            return {"url": source, "type": "url"}

        elif package.source_type == "file":
            # 文件输入：读取文件内容（不实际读取，仅示例）
            return {"filename": source, "type": "file"}

        elif package.source_type == "list":
            # 列表输入：逐项处理
            if not isinstance(source, list):
                self._error_handler.raise_error("E008")
            return source

        else:
            # 未知类型
            return source

    def _extract_fields(self, data: Any) -> Tuple[Dict[str, Any], List[str]]:
        """从解析后的数据中提取关键字段。"""
        structured: Dict[str, Any] = {}
        missing: List[str] = []

        if isinstance(data, dict):
            # 字典：直接提取已知字段
            for key in self.KEY_FIELDS:
                if key in data and data[key] is not None and data[key] != "":
                    structured[key] = data[key]
            
            # 检查关键字段
            for key in self.CRITICAL_FIELDS:
                if key not in structured:
                    missing.append(key)

        elif isinstance(data, str):
            # 纯文本：提取基本信息
            if data.strip():
                structured["content"] = data.strip()
                structured["type"] = "text"
                # 尝试提取 URL
                urls = re.findall(r'https?://[^\s]+', data)
                if urls:
                    structured["url"] = urls[0]
                    # 如果提取到URL，不再视为缺失
                    if "url" in missing:
                        missing.remove("url")
            else:
                missing.append("content")

        elif isinstance(data, list):
            # 列表：批量处理（此处仅统计）
            structured["items_count"] = len(data)
            structured["type"] = "list"
            if not data:
                missing.append("items")

        else:
            # 其他类型
            missing.append("content")

        return structured, missing

    def _calculate_confidence(
        self, structured: Dict[str, Any], missing: List[str]
    ) -> float:
        """基于字段完整度计算置信度。"""
        if not structured:
            return 0.0

        # 计算已提取字段的加权得分
        total_weight = 0.0
        earned_weight = 0.0

        for key, weight in self.FIELD_WEIGHTS.items():
            if key in structured and structured[key] is not None:
                earned_weight += weight
            total_weight += weight

        # 基础得分 = 字段覆盖率
        base_score = earned_weight / total_weight if total_weight > 0 else 0.0

        # 内容质量调整（简单启发式）
        content_bonus = 0.0
        content = structured.get("content", "")
        if isinstance(content, str) and len(content) > 10:
            content_bonus = 0.05

        # 缺失字段惩罚
        missing_penalty = 0.02 * len(missing)

        # 最终置信度
        confidence = min(0.99, max(0.0, base_score + content_bonus - missing_penalty))
        return round(confidence, 2)


# ---------------------------------------------------------------------------
# 错误处理
# ---------------------------------------------------------------------------
class ErrorHandler:
    """统一错误处理类。"""

    def __init__(self) -> None:
        self._codes = ERROR_CODES

    def get_message(self, code: str) -> str:
        """获取错误消息。"""
        return self._codes.get(code, ERROR_CODES["E010"])

    def raise_error(self, code: str, details: Optional[str] = None) -> None:
        """抛出标准化错误。"""
        message = self.get_message(code)
        if details:
            message = f"{message}（{details}）"
        raise ValueError(f"[{code}] {message}")


# ---------------------------------------------------------------------------
# 输出格式化
# ---------------------------------------------------------------------------
class OutputFormatter:
    """输出格式化器。"""

    @staticmethod
    def format(result: ProcessingResult, output_format: str = "json") -> str:
        """将处理结果格式化为指定格式。"""
        # 构建输出字典
        output: Dict[str, Any] = {
            "content": result.content,
            "confidence": result.confidence,
            "fields": result.fields,
            "warnings": result.warnings,
        }

        if result.needs_review:
            output["status"] = "建议复核"
        elif result.needs_verification:
            output["status"] = "需核实"
        else:
            output["status"] = "完成"

        # 格式化输出
        if output_format == "json":
            return json.dumps(output, ensure_ascii=False, indent=2)
        elif output_format == "text":
            lines = [
                f"状态: {output['status']}",
                f"置信度: {output['confidence']:.0%}",
                f"内容: {output['content']}",
            ]
            if output["warnings"]:
                lines.append(f"警告: {'; '.join(output['warnings'])}")
            return "\n".join(lines)
        else:
            raise ValueError(f"[E007] {ERROR_CODES['E007']}")


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------
def run_selftest() -> int:
    """
    离线自检：使用内置硬编码样例验证核心逻辑。

    返回 0 表示通过，非 0 表示失败。
    """
    print("开始离线自检...")
    processor = CoreProcessor()
    formatter = OutputFormatter()
    
    try:
        # 测试用例 1：结构化字典输入
        test_data_1 = {
            "id": "sample-001",
            "name": "测试音频",
            "type": "audio",
            "url": "https://example.com/audio.mp3",
            "description": "这是一个用于自检的测试音频文件",
            "tags": ["测试", "示例"],
            "author": "tester",
        }
        pkg1 = InputPackage(source=test_data_1, source_type="text", format="json")
        result1 = processor.process(pkg1)
        assert result1.confidence >= 0.8, f"测试1置信度异常: {result1.confidence}"
        assert result1.content is not None, "测试1内容为空"
        print(f"  测试1通过: 置信度={result1.confidence:.0%}")

        # 测试用例 2：纯文本输入
        test_data_2 = "这是一个描述音频文件的文本内容，包含 https://example.com/sound.wav 链接"
        pkg2 = InputPackage(source=test_data_2, source_type="text", format="text")
        result2 = processor.process(pkg2)
        assert result2.confidence > 0, "测试2置信度应为正数"
        assert result2.content is not None, "测试2内容为空"
        print(f"  测试2通过: 置信度={result2.confidence:.0%}")

        # 测试用例 3：列表输入
        test_data_3 = ["item1", "item2", "item3"]
        pkg3 = InputPackage(source=test_data_3, source_type="list", format="json")
        result3 = processor.process(pkg3)
        assert result3.content is not None, "测试3内容为空"
        assert result3.fields.get("items_count") == 3, "测试3数量错误"
        print(f"  测试3通过: 置信度={result3.confidence:.0%}")

        # 测试用例 4：错误处理
        try:
            bad_pkg = InputPackage(source=None, source_type="text", format="json")
            processor.process(bad_pkg)
            assert False, "测试4应抛出异常"
        except ValueError as e:
            assert "E001" in str(e), f"测试4错误码异常: {e}"
            print(f"  测试4通过: 错误码正确")

        # 测试用例 5：输出格式化
        formatted = formatter.format(result1, "json")
        assert formatted is not None and len(formatted) > 0, "测试5格式化失败"
        print(f"  测试5通过: 格式化输出正常")

        # 测试用例 6：批量处理
        batch_data = [
            {"name": "音频1", "type": "audio", "url": "http://example.com/1.mp3"},
            {"name": "音频2", "type": "audio", "url": "http://example.com/2.mp3"},
        ]
        pkg6 = InputPackage(source=batch_data, source_type="list", format="json")
        result6 = processor.process(pkg6)
        assert result6.fields.get("items_count") == 2, "测试6批量数量错误"
        print(f"  测试6通过: 批量处理正常")

        # 测试用例 7：边界情况——空字符串
        pkg7 = InputPackage(source="", source_type="text", format="text")
        try:
            processor.process(pkg7)
            assert False, "测试7应抛出异常"
        except ValueError as e:
            assert "E001" in str(e), f"测试7错误码异常: {e}"
            print(f"  测试7通过: 空输入处理正确")

        # 测试用例 8：URL 输入
        pkg8 = InputPackage(
            source="https://example.com/sample.mp3",
            source_type="url",
            format="json",
        )
        result8 = processor.process(pkg8)
        assert result8.content is not None, "测试8内容为空"
        assert result8.confidence > 0, "测试8置信度应为正数"
        print(f"  测试8通过: URL输入正常")

        print("\n所有自检通过！✅")
        return 0
        
    except Exception as e:
        print(f"自检失败: {e}", file=sys.stderr)
        return 1


def main() -> int:
    """主入口函数。"""
    parser = argparse.ArgumentParser(
        description="爬虫采集 - 通用数据处理工具",
        epilog="示例: python main.py --input 'data' --format json",
    )
    parser.add_argument(
        "--input",
        "-i",
        type=str,
        help="待处理的内容（文本/文件路径/URL）",
    )
    parser.add_argument(
        "--source-type",
        "-t",
        choices=["text", "file", "url", "list"],
        default="text",
        help="输入来源类型（默认: text）",
    )
    parser.add_argument(
        "--format",
        "-f",
        choices=["json", "text"],
        default="json",
        help="输出格式（默认: json）",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行离线自检（不读取外部文件、不访问网络）",
    )
    parser.add_argument(
        "--detail",
        choices=["quick", "standard", "detailed"],
        default="standard",
        help="期望的完整度（默认: standard）",
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        return run_selftest()

    # 正常处理模式
    if not args.input:
        print(f"[E001] {ERROR_CODES['E001']}", file=sys.stderr)
        return 1

    try:
        # 构造输入包
        package = InputPackage(
            source=args.input,
            source_type=args.source_type,
            format=args.format,
            detail_level=args.detail,
        )

        # 执行处理
        processor = CoreProcessor()
        result = processor.process(package)

        # 格式化输出
        formatter = OutputFormatter()
        output = formatter.format(result, args.format)
        print(output)

        return 0

    except ValueError as e:
        print(f"处理错误: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"[E010] {ERROR_CODES['E010']}: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
