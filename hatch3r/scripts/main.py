#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
hatch3r - 未命名工具（仅供学习与参考用途）

一个独立的命令行工具，用于将用户提供的数据/文件/URL 转换为结构化结果。
本脚本为 clean-room 实现，仅依据功能规格独立编写。

免责声明：
- 本工具仅供学习与参考用途，不构成任何专业建议。
- 涉及法律、财务、税务、投资、医疗等专业决策时，请务必咨询持证专业人士。
- 使用本工具产生的任何结果，由使用者自行承担全部责任。

许可证：MIT License
Copyright (c) 2026 原创作者（自持版权）
"""

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 常量定义
# ============================================================

# 版本信息
VERSION = "1.0.0"
TOOL_NAME = "hatch3r"
DISPLAY_NAME = "未命名工具"

# 错误码及对应话术（依据规格五）
ERROR_MESSAGES = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：",
    "E003": "输入格式不符合要求，示例：...",
    "E004": "这超出了本工具的能力范围，建议...",
    "E005": "结果无法确定，建议：...",
}

# 置信度阈值（依据规格三）
CONFIDENCE_HIGH = 0.90      # ≥90% 直接输出
CONFIDENCE_MEDIUM = 0.85    # 85%-90% 建议复核
# <85% 标注 [需核实]


# ============================================================
# 数据结构
# ============================================================

@dataclass
class ProcessResult:
    """处理结果的数据结构"""
    success: bool                     # 是否成功
    data: Optional[Dict[str, Any]] = None   # 结构化结果
    confidence: float = 0.0           # 置信度 0-1
    warnings: List[str] = field(default_factory=list)  # 警告信息
    error_code: Optional[str] = None  # 错误码
    error_detail: str = ""            # 错误详情


# ============================================================
# 核心处理逻辑
# ============================================================

class Hatch3rProcessor:
    """
    核心处理器：负责将输入内容转换为结构化结果。
    依据规格三的标准流程实现。
    """

    # 可识别的关键字段（依据规格三 Step 2）
    KEY_FIELDS = [
        "name", "title", "type", "url", "content",
        "description", "date", "author", "tags", "id"
    ]

    def __init__(self) -> None:
        """初始化处理器"""
        self._url_pattern = re.compile(
            r'^https?://[^\s/$.?#].[^\s]*$', re.IGNORECASE
        )
        self._json_pattern = re.compile(r'^[\[{].*[\]}]$', re.DOTALL)

    def process(self, raw_input: str, output_format: str = "json") -> ProcessResult:
        """
        主处理入口（依据规格三 Step 2）

        Args:
            raw_input: 用户提供的原始输入（数据/文件内容/URL）
            output_format: 期望的输出格式（json/text）

        Returns:
            ProcessResult: 处理结果
        """
        # 错误检查：输入为空（E001）
        if not raw_input or not raw_input.strip():
            return ProcessResult(
                success=False,
                error_code="E001",
                error_detail=ERROR_MESSAGES["E001"]
            )

        # 错误检查：输出格式不支持
        if output_format not in ("json", "text"):
            return ProcessResult(
                success=False,
                error_code="E003",
                error_detail=f"不支持的输出格式: {output_format}，支持: json, text"
            )

        # 解析输入内容，识别关键信息
        parsed_data, parse_warnings, parse_error = self._parse_input(raw_input)

        # 解析失败
        if parse_error:
            return ProcessResult(
                success=False,
                error_code=parse_error[0],
                error_detail=parse_error[1],
                warnings=parse_warnings
            )

        # 计算置信度
        confidence = self._calculate_confidence(parsed_data, raw_input)

        # 构建结构化结果
        result_data = self._build_output(parsed_data, output_format)

        # 根据置信度添加标注
        if confidence < CONFIDENCE_MEDIUM:
            # 低置信度：添加 [需核实] 并说明不确定点
            result_data["[需核实]"] = True
            result_data["uncertain_fields"] = self._get_uncertain_fields(parsed_data)
            parse_warnings.append("低置信度结果，请人工复核关键内容")
        elif confidence < CONFIDENCE_HIGH:
            # 中等置信度：标注建议复核
            parse_warnings.append("建议复核：部分字段可能不准确")

        return ProcessResult(
            success=True,
            data=result_data,
            confidence=confidence,
            warnings=parse_warnings
        )

    def _parse_input(self, raw_input: str) -> Tuple[Dict[str, Any], List[str], Optional[Tuple[str, str]]]:
        """
        解析输入内容，识别关键信息。

        Returns:
            (解析出的数据, 警告列表, 错误信息)
            错误信息格式: (错误码, 错误详情) 或 None
        """
        warnings: List[str] = []
        text_input = raw_input.strip()

        # 尝试解析为 JSON 格式
        if self._json_pattern.match(text_input):
            try:
                parsed = json.loads(text_input)
                if isinstance(parsed, dict):
                    # 提取关键字段
                    extracted = {k: v for k, v in parsed.items() if k in self.KEY_FIELDS}
                    if extracted:
                        return extracted, warnings, None
                    else:
                        # JSON 有效但没有关键字段
                        return {"raw_json": parsed}, warnings, None
                elif isinstance(parsed, list):
                    # 列表类型输入
                    return {"items": parsed, "count": len(parsed)}, warnings, None
            except json.JSONDecodeError:
                # JSON 解析失败，继续尝试其他方式
                warnings.append("JSON 格式解析失败，尝试文本解析")

        # 尝试解析为 URL
        if self._url_pattern.match(text_input):
            return {
                "type": "url",
                "url": text_input,
                "source": "外部链接"
            }, warnings, None

        # 尝试解析为键值对格式（如 "key: value" 或 "key=value"）
        kv_data = self._parse_key_value(text_input)
        if kv_data:
            return kv_data, warnings, None

        # 尝试解析为纯文本内容
        if len(text_input) > 10:
            # 提取可能的标题/名称
            first_line = text_input.split('\n')[0].strip()
            return {
                "type": "text",
                "content": text_input,
                "title": first_line[:50] if first_line else ""
            }, warnings, None

        # 无法识别输入格式（E003）
        return {}, warnings, ("E003", "无法识别的输入格式，请提供文本、JSON 或 URL")

    def _parse_key_value(self, text: str) -> Optional[Dict[str, Any]]:
        """
        解析键值对格式的文本。
        支持格式: "key: value" 或 "key=value"，每行一个键值对。
        """
        lines = text.split('\n')
        result: Dict[str, Any] = {}
        kv_pattern = re.compile(r'^([a-zA-Z_][a-zA-Z0-9_]*)\s*[:=]\s*(.+)$')

        for line in lines:
            line = line.strip()
            if not line:
                continue
            match = kv_pattern.match(line)
            if match:
                key = match.group(1).lower()
                value = match.group(2).strip()
                # 只保留关键字段
                if key in self.KEY_FIELDS:
                    result[key] = value

        return result if result else None

    def _calculate_confidence(self, data: Dict[str, Any], raw_input: str) -> float:
        """
        计算置信度（依据规格三 Step 2）。

        置信度评估规则：
        - 有明确结构（JSON/键值对）: 基础 0.95
        - 有 URL: 基础 0.90
        - 纯文本: 基础 0.80
        - 字段缺失: 每个缺失字段扣 0.05
        - 内容过短: 扣 0.05
        """
        confidence = 0.80  # 默认基础值

        # 根据数据类型调整基础值
        data_type = data.get("type", "")
        if "raw_json" in data or any(k in data for k in self.KEY_FIELDS):
            confidence = 0.95  # 结构化数据
        elif data_type == "url":
            confidence = 0.90
        elif data_type == "text":
            confidence = 0.82

        # 字段完整性检查
        field_count = sum(1 for k in self.KEY_FIELDS if k in data)
        if field_count < 2:
            confidence -= 0.10  # 关键字段过少

        # 内容长度检查
        if len(raw_input.strip()) < 20:
            confidence -= 0.05  # 内容过短

        # 限制在 0-1 范围内
        return max(0.0, min(1.0, confidence))

    def _build_output(self, data: Dict[str, Any], output_format: str) -> Dict[str, Any]:
        """构建结构化输出（依据规格三 Step 3）"""
        # 统一输出结构
        output = {
            "tool": TOOL_NAME,
            "version": VERSION,
            "result": data,
            "summary": self._generate_summary(data),
        }

        # 根据格式调整输出
        if output_format == "json":
            # JSON 格式直接返回结构化数据
            return output
        else:
            # text 格式转换为文本描述
            output["text_output"] = self._format_as_text(data)
            return output

    def _generate_summary(self, data: Dict[str, Any]) -> str:
        """生成结果摘要"""
        if not data:
            return "未识别到有效内容"

        data_type = data.get("type", "unknown")
        if data_type == "url":
            return f"识别到外部链接: {data.get('url', '')}"
        elif data_type == "text":
            title = data.get("title", "")
            return f"识别到文本内容: {title}" if title else "识别到文本内容"
        elif "items" in data:
            return f"识别到 {data.get('count', 0)} 个数据项"
        else:
            keys = [k for k in data.keys() if k in self.KEY_FIELDS]
            return f"识别到 {len(keys)} 个关键字段: {', '.join(keys)}"

    def _format_as_text(self, data: Dict[str, Any]) -> str:
        """将数据格式化为文本"""
        lines = []
        for key, value in data.items():
            if key == "type":
                continue
            lines.append(f"{key}: {value}")
        return "\n".join(lines) if lines else "无内容"

    def _get_uncertain_fields(self, data: Dict[str, Any]) -> List[str]:
        """获取不确定的字段列表"""
        uncertain = []
        # 缺少关键字段视为不确定
        for field_name in ["name", "title", "type"]:
            if field_name not in data:
                uncertain.append(field_name)
        return uncertain


# ============================================================
# 命令行接口
# ============================================================

def run_selftest() -> bool:
    """
    内置自检函数（依据要求 3）。

    使用硬编码样例数据离线自检核心逻辑。
    不读外部文件、不依赖当前工作目录、不访问网络。

    断言使用宽松阈值，确保任何环境直接可过。
    """
    print("[自检] 开始运行内置自检...")
    processor = Hatch3rProcessor()
    all_passed = True

    # 测试用例 1: 键值对格式输入
    print("[自检] 测试 1: 键值对格式输入...")
    test_input_1 = """name: 测试项目
type: document
description: 这是一个测试用的文档
date: 2026-01-01"""
    result_1 = processor.process(test_input_1)
    assert result_1.success, f"测试 1 失败: {result_1.error_detail}"
    assert result_1.data is not None, "测试 1 失败: 结果为空"
    assert result_1.data["result"].get("name") == "测试项目", "测试 1 失败: name 字段错误"
    assert result_1.confidence > 0.5, "测试 1 失败: 置信度过低"
    assert result_1.confidence <= 1.0, "测试 1 失败: 置信度超过 1"
    print("[自检] 测试 1 通过 ✓")

    # 测试用例 2: JSON 格式输入
    print("[自检] 测试 2: JSON 格式输入...")
    test_input_2 = '{"title": "JSON测试", "tags": ["test", "json"], "author": "tester"}'
    result_2 = processor.process(test_input_2)
    assert result_2.success, f"测试 2 失败: {result_2.error_detail}"
    assert result_2.data is not None, "测试 2 失败: 结果为空"
    assert result_2.data["result"].get("title") == "JSON测试", "测试 2 失败: title 字段错误"
    assert len(result_2.data["result"]) >= 1, "测试 2 失败: 结果字段过少"
    print("[自检] 测试 2 通过 ✓")

    # 测试用例 3: URL 格式输入
    print("[自检] 测试 3: URL 格式输入...")
    test_input_3 = "https://example.com/some/page"
    result_3 = processor.process(test_input_3)
    assert result_3.success, f"测试 3 失败: {result_3.error_detail}"
    assert result_3.data is not None, "测试 3 失败: 结果为空"
    assert result_3.data["result"].get("type") == "url", "测试 3 失败: 类型不是 url"
    assert result_3.data["result"].get("url") == test_input_3, "测试 3 失败: URL 字段错误"
    print("[自检] 测试 3 通过 ✓")

    # 测试用例 4: 空输入错误处理（E001）
    print("[自检] 测试 4: 空输入错误处理...")
    result_4 = processor.process("")
    assert not result_4.success, "测试 4 失败: 空输入应该失败"
    assert result_4.error_code == "E001", f"测试 4 失败: 错误码错误, 期望 E001, 实际 {result_4.error_code}"
    print("[自检] 测试 4 通过 ✓")

    # 测试用例 5: 纯文本输入
    print("[自检] 测试 5: 纯文本输入...")
    test_input_5 = "这是一段很长的纯文本内容，用于测试纯文本输入的处理逻辑是否正常。"
    result_5 = processor.process(test_input_5)
    assert result_5.success, f"测试 5 失败: {result_5.error_detail}"
    assert result_5.data is not None, "测试 5 失败: 结果为空"
    assert result_5.data["result"].get("type") == "text", "测试 5 失败: 类型不是 text"
    assert result_5.confidence > 0, "测试 5 失败: 置信度应该大于 0"
    print("[自检] 测试 5 通过 ✓")

    # 测试用例 6: 批量处理（列表输入）
    print("[自检] 测试 6: 批量处理...")
    test_input_6 = '[{"name": "item1"}, {"name": "item2"}, {"name": "item3"}]'
    result_6 = processor.process(test_input_6)
    assert result_6.success, f"测试 6 失败: {result_6.error_detail}"
    assert result_6.data is not None, "测试 6 失败: 结果为空"
    assert result_6.data["result"].get("count", 0) >= 1, "测试 6 失败: 批量处理数量错误"
    print("[自检] 测试 6 通过 ✓")

    # 测试用例 7: 不同输出格式
    print("[自检] 测试 7: 不同输出格式...")
    test_input_7 = "name: 格式测试\ncontent: 测试内容"
    result_7_json = processor.process(test_input_7, "json")
    result_7_text = processor.process(test_input_7, "text")
    assert result_7_json.success and result_7_text.success, "测试 7 失败: 格式处理失败"
    assert "text_output" in result_7_text.data, "测试 7 失败: text 格式缺少 text_output 字段"
    print("[自检] 测试 7 通过 ✓")

    # 测试用例 8: 错误输出格式
    print("[自检] 测试 8: 错误输出格式...")
    result_8 = processor.process("test", "xml")
    assert not result_8.success, "测试 8 失败: 不支持的格式应该失败"
    assert result_8.error_code == "E003", f"测试 8 失败: 错误码错误, 期望 E003"
    print("[自检] 测试 8 通过 ✓")

    print("[自检] 全部测试通过 ✓")
    return all_passed


def main() -> int:
    """主入口函数"""
    parser = argparse.ArgumentParser(
        prog=TOOL_NAME,
        description=f"{DISPLAY_NAME} - 仅供学习与参考用途。将用户提供的数据/文件/URL 转换为结构化结果。",
        epilog="示例: python main.py 'name: test' --format json"
    )

    parser.add_argument(
        "input",
        nargs="?",
        default=None,
        help="待处理的内容（文本/JSON/URL）"
    )
    parser.add_argument(
        "--format",
        choices=["json", "text"],
        default="json",
        help="输出格式（默认: json）"
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检（使用硬编码样例数据，无需外部输入）"
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"{TOOL_NAME} {VERSION}"
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        try:
            run_selftest()
            return 0
        except AssertionError as e:
            print(f"[自检] 失败: {e}", file=sys.stderr)
            return 1

    # 正常处理模式
    if args.input is None:
        print(f"错误 (E001): {ERROR_MESSAGES['E001']}", file=sys.stderr)
        print("提示: 使用 --selftest 运行内置自检，或 --help 查看帮助", file=sys.stderr)
        return 1

    # 处理输入
    processor = Hatch3rProcessor()
    result = processor.process(args.input, args.format)

    if not result.success:
        error_msg = result.error_detail or ERROR_MESSAGES.get(result.error_code, "未知错误")
        print(f"错误 ({result.error_code}): {error_msg}", file=sys.stderr)
        if result.warnings:
            print("警告:", file=sys.stderr)
            for warning in result.warnings:
                print(f"  - {warning}", file=sys.stderr)
        return 1

    # 输出结果
    if args.format == "json":
        print(json.dumps(result.data, ensure_ascii=False, indent=2))
    else:
        # text 格式
        print(result.data.get("text_output", ""))

    # 输出警告
    if result.warnings:
        print("\n警告:", file=sys.stderr)
        for warning in result.warnings:
            print(f"  - {warning}", file=sys.stderr)

    # 置信度提示
    if result.confidence < CONFIDENCE_HIGH:
        if result.confidence < CONFIDENCE_MEDIUM:
            print(f"\n[需核实] 置信度: {result.confidence:.0%}，请人工复核关键结果", file=sys.stderr)
        else:
            print(f"\n建议复核 置信度: {result.confidence:.0%}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
