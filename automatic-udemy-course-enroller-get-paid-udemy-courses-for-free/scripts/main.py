#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py
爬虫采集技能 - 独立实现脚本

功能：将用户提供的数据/文件/URL 转换为结构化结果，识别关键信息，
      按约定格式输出，并标注置信度。

仅依据功能规格实现，独立编写，不复制任何既有代码。
"""

import argparse
import json
import sys
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# 错误码定义
# ---------------------------------------------------------------------------
ERROR_MESSAGES = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：输入来源 / 输出格式 / 期望完整度",
    "E003": "输入格式不符合要求，示例：提供文本、JSON 文件路径或 URL",
    "E004": "这超出了本工具的能力范围，建议使用专用工具或人工处理",
    "E005": "结果无法确定，建议：提供更多上下文或人工复核",
    "E006": "内部处理错误，请检查输入数据",
    "E007": "文件读取失败，请检查文件路径和权限",
    "E008": "JSON 解析失败，请检查文件内容格式",
    "E009": "输出写入失败，请检查输出路径和权限",
    "E010": "未知错误，请联系技术支持",
}


# ---------------------------------------------------------------------------
# 数据结构定义
# ---------------------------------------------------------------------------
@dataclass
class ProcessingResult:
    """处理结果数据结构"""
    status: str = "success"  # success / error
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    data: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0
    warnings: List[str] = field(default_factory=list)


@dataclass
class InputData:
    """输入数据封装"""
    source: str = ""
    content: Any = None
    output_format: str = "json"
    completeness: str = "detailed"  # quick / detailed


# ---------------------------------------------------------------------------
# 核心处理逻辑
# ---------------------------------------------------------------------------
class DataProcessor:
    """数据处理器：解析输入、识别关键信息、生成结构化输出"""

    # 可识别的关键字段（示例）
    KEY_FIELDS = [
        "title", "name", "description", "url", "price",
        "category", "author", "date", "status"
    ]

    def __init__(self):
        self.input_data: Optional[InputData] = None
        self.result = ProcessingResult()

    def process(self, input_data: InputData) -> ProcessingResult:
        """主处理入口"""
        self.input_data = input_data
        self.result = ProcessingResult()

        # Step 1: 验证输入
        if not input_data.source and not input_data.content:
            self._set_error("E001")
            return self.result

        # Step 2: 解析内容
        try:
            parsed = self._parse_input()
            if parsed is None:
                self._set_error("E003")
                return self.result

            # Step 3: 识别关键信息
            extracted = self._extract_key_info(parsed)

            # Step 4: 生成结构化输出
            structured = self._build_output(extracted)

            # Step 5: 计算置信度
            confidence = self._calculate_confidence(structured)

            self.result.status = "success"
            self.result.data = structured
            self.result.confidence = confidence

            # 根据置信度添加标注
            if confidence < 85:
                self.result.warnings.append("[需核实] 置信度低于85%，请人工复核关键结果")
            elif confidence < 90:
                self.result.warnings.append("建议复核：置信度在85%-90%之间")

        except Exception as e:
            self._set_error("E006", str(e))

        return self.result

    def _parse_input(self) -> Any:
        """解析输入内容"""
        if self.input_data.content is not None:
            return self.input_data.content

        source = self.input_data.source.strip()

        # 检查是否为 URL（简单判断）
        if source.startswith(("http://", "https://")):
            # 不访问网络，仅记录 URL 并返回基本结构
            return {"url": source, "note": "URL 输入，未进行网络访问"}

        # 检查是否为文件路径（JSON 文件）
        if source.endswith(".json"):
            try:
                with open(source, "r", encoding="utf-8") as f:
                    return json.load(f)
            except FileNotFoundError:
                self._set_error("E007")
                return None
            except json.JSONDecodeError:
                self._set_error("E008")
                return None
            except Exception:
                self._set_error("E007")
                return None

        # 尝试解析为 JSON 字符串
        try:
            return json.loads(source)
        except json.JSONDecodeError:
            pass

        # 按文本处理
        if source:
            return {"text": source}

        return None

    def _extract_key_info(self, parsed: Any) -> Dict[str, Any]:
        """从解析后的内容中提取关键信息"""
        extracted = {}

        if isinstance(parsed, dict):
            # 直接映射已知字段
            for field_name in self.KEY_FIELDS:
                if field_name in parsed:
                    extracted[field_name] = parsed[field_name]

            # 递归提取嵌套字段
            for key, value in parsed.items():
                if isinstance(value, dict):
                    nested = self._extract_key_info(value)
                    for nk, nv in nested.items():
                        if nk not in extracted:
                            extracted[nk] = nv
                elif isinstance(value, list) and value and isinstance(value[0], dict):
                    # 处理列表中的字典
                    first_item = value[0]
                    for field_name in self.KEY_FIELDS:
                        if field_name in first_item and field_name not in extracted:
                            extracted[field_name] = first_item[field_name]

        elif isinstance(parsed, list):
            # 处理列表
            if parsed and isinstance(parsed[0], dict):
                extracted = self._extract_key_info(parsed[0])
            extracted["_count"] = len(parsed)

        elif isinstance(parsed, str):
            # 纯文本，尝试识别简单模式
            extracted["text"] = parsed
            extracted["length"] = len(parsed)

        return extracted

    def _build_output(self, extracted: Dict[str, Any]) -> Dict[str, Any]:
        """构建结构化输出"""
        output = {
            "data": extracted,
            "metadata": {
                "source_type": self._detect_source_type(),
                "output_format": self.input_data.output_format if self.input_data else "json",
                "completeness": self.input_data.completeness if self.input_data else "detailed",
                "timestamp": self._get_timestamp(),
            }
        }

        # 根据完整度调整输出
        if self.input_data and self.input_data.completeness == "quick":
            # 快速骨架：只保留核心字段
            output["data"] = {k: v for k, v in extracted.items() if k in ["title", "name", "url"]}

        return output

    def _detect_source_type(self) -> str:
        """检测输入来源类型"""
        if not self.input_data:
            return "unknown"

        source = self.input_data.source
        if source.startswith(("http://", "https://")):
            return "url"
        if source.endswith(".json"):
            return "json_file"
        if self.input_data.content is not None:
            return "direct_input"
        return "text"

    def _calculate_confidence(self, output: Dict[str, Any]) -> float:
        """计算置信度（0-100）"""
        data = output.get("data", {})

        if not data:
            return 50.0  # 无数据时中等置信度

        # 基础置信度
        confidence = 60.0

        # 根据字段数量和质量调整
        field_count = len(data)
        if field_count > 0:
            confidence += min(field_count * 5, 20)  # 每个字段加5分，最多加20

        # 有核心字段（title/name）加分
        if "title" in data or "name" in data:
            confidence += 10

        # 有 URL 加分
        if "url" in data:
            confidence += 5

        # 有描述加分
        if "description" in data:
            confidence += 5

        # 限制在 0-100 范围
        return max(0, min(100, confidence))

    def _get_timestamp(self) -> str:
        """获取当前时间戳"""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def _set_error(self, code: str, detail: str = "") -> None:
        """设置错误信息"""
        self.result.status = "error"
        self.result.error_code = code
        base_msg = ERROR_MESSAGES.get(code, ERROR_MESSAGES["E010"])
        self.result.error_message = f"{base_msg} {detail}".strip()


# ---------------------------------------------------------------------------
# 输出格式化
# ---------------------------------------------------------------------------
class OutputFormatter:
    """输出格式化器"""

    @staticmethod
    def format(result: ProcessingResult, fmt: str = "json") -> str:
        """格式化输出"""
        if fmt == "json":
            return json.dumps(result.__dict__, ensure_ascii=False, indent=2)
        elif fmt == "text":
            return OutputFormatter._format_text(result)
        else:
            return json.dumps(result.__dict__, ensure_ascii=False, indent=2)

    @staticmethod
    def _format_text(result: ProcessingResult) -> str:
        """文本格式输出"""
        lines = []
        if result.status == "success":
            lines.append("处理成功")
            lines.append(f"置信度: {result.confidence:.1f}%")
            lines.append("\n数据内容:")
            for key, value in result.data.get("data", {}).items():
                lines.append(f"  {key}: {value}")

            if result.warnings:
                lines.append("\n警告:")
                for warning in result.warnings:
                    lines.append(f"  - {warning}")
        else:
            lines.append(f"处理失败 [{result.error_code}]")
            lines.append(f"错误信息: {result.error_message}")

        return "\n".join(lines)


# ---------------------------------------------------------------------------
# 自测功能
# ---------------------------------------------------------------------------
def run_selftest() -> bool:
    """内置自测：使用硬编码样例数据验证核心逻辑"""
    print("=" * 60)
    print("开始自测（使用内置硬编码数据）")
    print("=" * 60)

    processor = DataProcessor()
    all_passed = True

    # 测试用例 1: 字典输入
    print("\n[测试1] 字典输入")
    test_data = {
        "title": "Python 爬虫实战",
        "description": "学习爬虫开发",
        "url": "https://example.com/course/python",
        "price": 0,
        "category": "编程"
    }
    input_data = InputData(content=test_data, output_format="json", completeness="detailed")
    result = processor.process(input_data)

    # 宽松断言
    assert result.status == "success", f"测试1失败: 状态应为success"
    assert result.confidence > 50, f"测试1失败: 置信度应>50"
    assert result.data.get("data", {}).get("title") == "Python 爬虫实战", "测试1失败: title不匹配"
    print(f"  ✓ 通过 (置信度: {result.confidence:.1f}%)")

    # 测试用例 2: JSON 字符串输入
    print("\n[测试2] JSON字符串输入")
    json_str = '{"name": "测试课程", "author": "张三", "price": 99}'
    input_data = InputData(source=json_str, output_format="json", completeness="quick")
    result = processor.process(input_data)

    assert result.status == "success", f"测试2失败: 状态应为success"
    assert result.confidence > 50, f"测试2失败: 置信度应>50"
    assert result.data.get("data", {}).get("name") == "测试课程", "测试2失败: name不匹配"
    print(f"  ✓ 通过 (置信度: {result.confidence:.1f}%)")

    # 测试用例 3: URL 输入
    print("\n[测试3] URL输入")
    input_data = InputData(source="https://example.com/course/123", output_format="json", completeness="detailed")
    result = processor.process(input_data)

    assert result.status == "success", f"测试3失败: 状态应为success"
    assert result.confidence > 50, f"测试3失败: 置信度应>50"
    assert "url" in result.data.get("data", {}), "测试3失败: 应包含url"
    print(f"  ✓ 通过 (置信度: {result.confidence:.1f}%)")

    # 测试用例 4: 空输入（应报错）
    print("\n[测试4] 空输入错误处理")
    input_data = InputData(source="", content=None)
    result = processor.process(input_data)

    assert result.status == "error", f"测试4失败: 状态应为error"
    assert result.error_code == "E001", f"测试4失败: 错误码应为E001"
    print(f"  ✓ 通过 (错误码: {result.error_code})")

    # 测试用例 5: 列表输入
    print("\n[测试5] 列表输入")
    list_data = [
        {"title": "课程A", "price": 0},
        {"title": "课程B", "price": 10}
    ]
    input_data = InputData(content=list_data, output_format="json", completeness="detailed")
    result = processor.process(input_data)

    assert result.status == "success", f"测试5失败: 状态应为success"
    assert result.confidence > 50, f"测试5失败: 置信度应>50"
    assert result.data.get("data", {}).get("_count") == 2, "测试5失败: 应包含数量信息"
    print(f"  ✓ 通过 (置信度: {result.confidence:.1f}%, 数量: {result.data.get('data', {}).get('_count')})")

    # 测试用例 6: 文本输入
    print("\n[测试6] 文本输入")
    text_data = "这是一段纯文本内容，用于测试"
    input_data = InputData(content=text_data, output_format="text", completeness="detailed")
    result = processor.process(input_data)

    assert result.status == "success", f"测试6失败: 状态应为success"
    assert result.confidence > 50, f"测试6失败: 置信度应>50"
    assert result.data.get("data", {}).get("text") == text_data, "测试6失败: 文本不匹配"
    print(f"  ✓ 通过 (置信度: {result.confidence:.1f}%)")

    # 测试用例 7: 输出格式化
    print("\n[测试7] 输出格式化")
    test_data = {"title": "格式化测试"}
    input_data = InputData(content=test_data, output_format="json", completeness="detailed")
    result = processor.process(input_data)
    formatted = OutputFormatter.format(result, "json")

    parsed_output = json.loads(formatted)
    assert parsed_output["status"] == "success", "测试7失败: JSON格式输出错误"
    print("  ✓ 通过 (JSON格式输出)")

    formatted_text = OutputFormatter.format(result, "text")
    assert "处理成功" in formatted_text, "测试7失败: 文本格式输出错误"
    print("  ✓ 通过 (文本格式输出)")

    # 测试用例 8: 错误码完整性
    print("\n[测试8] 错误码完整性")
    expected_codes = ["E001", "E002", "E003", "E004", "E005", "E006", "E007", "E008", "E009", "E010"]
    for code in expected_codes:
        assert code in ERROR_MESSAGES, f"测试8失败: 缺少错误码 {code}"
    print(f"  ✓ 通过 (共 {len(expected_codes)} 个错误码)")

    print("\n" + "=" * 60)
    print(f"自测完成: {'全部通过' if all_passed else '存在失败'}")
    print("=" * 60)
    return all_passed


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------
def main() -> int:
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description="爬虫采集技能 - 数据处理工具",
        epilog="示例: python main.py --input '{\"title\": \"测试\"}' --format json"
    )

    parser.add_argument("--input", "-i", help="输入内容：文本、JSON字符串或文件路径")
    parser.add_argument("--file", "-f", help="输入文件路径（JSON格式）")
    parser.add_argument("--url", "-u", help="输入URL")
    parser.add_argument("--format", "-fmt", choices=["json", "text"], default="json", help="输出格式")
    parser.add_argument("--completeness", "-c", choices=["quick", "detailed"], default="detailed", help="输出完整度")
    parser.add_argument("--selftest", action="store_true", help="运行自测")

    args = parser.parse_args()

    # 自测模式
    if args.selftest:
        success = run_selftest()
        return 0 if success else 1

    # 构建输入
    input_data = InputData(output_format=args.format, completeness=args.completeness)

    if args.file:
        input_data.source = args.file
    elif args.url:
        input_data.source = args.url
    elif args.input:
        input_data.source = args.input
    else:
        print(f"错误 [E001]: {ERROR_MESSAGES['E001']}")
        print("使用 --help 查看帮助")
        return 1

    # 处理数据
    processor = DataProcessor()
    result = processor.process(input_data)

    # 输出结果
    formatted = OutputFormatter.format(result, args.format)
    print(formatted)

    return 0 if result.status == "success" else 1


if __name__ == "__main__":
    sys.exit(main())
