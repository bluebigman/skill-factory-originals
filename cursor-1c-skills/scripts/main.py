#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py
===============

基于功能规格"cursor-1c-skills"的独立实现（clean-room 重写）。

本脚本提供：
1. 一个可复用的"未命名工具"核心处理流程，用于将用户输入内容
   （数据/文件/URL）解析为结构化结果，并按置信度分级输出。
2. 命令行入口，支持 --selftest 离线自检（不依赖外部文件/网络）。
3. 标准化的错误码体系（E001-E010）。

仅使用 Python 标准库，无第三方依赖。
"""

import argparse
import json
import sys
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# 常量定义
# ---------------------------------------------------------------------------

# 错误码及对应标准化话术（依据规格书第五节）
ERROR_MESSAGES: Dict[str, str] = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：输入来源、输出格式要求、期望的完整度",
    "E003": "输入格式不符合要求，示例：{\"source\": \"数据/文件/URL\", \"content\": \"...\"}",
    "E004": "这超出了本工具的能力范围，建议：简化输入或咨询专业人士",
    "E005": "结果无法确定，建议：人工复核关键结果，或补充更多上下文信息",
    # 以下为内部扩展错误码（E006-E010），用于更细粒度的错误定位
    "E006": "内部错误：输入解析失败（JSON 格式错误）",
    "E007": "内部错误：输出序列化失败",
    "E008": "内部错误：未知的置信度级别",
    "E009": "内部错误：缺少必要的处理模块",
    "E010": "内部错误：参数校验失败",
}

# 置信度阈值（依据规格书 Step 2）
HIGH_CONFIDENCE_THRESHOLD = 90.0
MEDIUM_CONFIDENCE_THRESHOLD = 85.0

# 支持的处理模式（对应规格书"进阶用法"）
SUPPORTED_MODES = {"single", "batch", "custom"}

# 无信息量的字段值（用于置信度计算）
LOW_INFO_VALUES = {"", "未知", "未知来源", "默认格式", "快速骨架"}


# ---------------------------------------------------------------------------
# 核心数据结构
# ---------------------------------------------------------------------------


class ProcessingResult:
    """一次处理的结果封装。"""

    def __init__(
        self,
        content: Any,
        confidence: float,
        fields: Optional[Dict[str, Any]] = None,
        warnings: Optional[List[str]] = None,
    ) -> None:
        """
        初始化处理结果。

        :param content: 结构化后的内容
        :param confidence: 置信度（0-100 浮点数）
        :param fields: 提取出的关键字段（可选）
        :param warnings: 警告/提示信息列表（可选）
        """
        self.content = content
        self.confidence = float(confidence)
        self.fields = fields if fields is not None else {}
        self.warnings = warnings if warnings is not None else []

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典，便于 JSON 序列化。"""
        return {
            "content": self.content,
            "confidence": self.confidence,
            "confidence_label": self._confidence_label(),
            "fields": self.fields,
            "warnings": self.warnings,
        }

    def _confidence_label(self) -> str:
        """
        根据置信度返回标签（依据规格书 Step 2 规则）。

        - >=90%: 直接输出（无特殊标注）
        - 85%-90%: 建议复核
        - <85%: [需核实]
        """
        if self.confidence >= HIGH_CONFIDENCE_THRESHOLD:
            return "直接输出"
        elif self.confidence >= MEDIUM_CONFIDENCE_THRESHOLD:
            return "建议复核"
        else:
            return "[需核实]"

    def __repr__(self) -> str:
        return f"ProcessingResult(confidence={self.confidence:.1f}%)"


# ---------------------------------------------------------------------------
# 核心处理引擎
# ---------------------------------------------------------------------------


class CoreProcessor:
    """
    核心处理引擎：负责将原始输入解析为结构化结果。

    设计原则：
    - 不访问网络、不读取外部文件（除非显式通过参数传入内容）。
    - 只处理传入的字符串/字典数据。
    - 对不确定项给出置信度提示。
    """

    # 需要提取的关键字段（依据规格书 Step 1 的最小信息集）
    REQUIRED_FIELDS = ["source", "format", "completeness"]

    def __init__(self) -> None:
        """初始化处理器。"""
        # 可扩展的字段提取规则（当前为演示用途）
        self._field_extractors = {
            "source": self._extract_source,
            "format": self._extract_format,
            "completeness": self._extract_completeness,
        }

    # ------------------------------------------------------------------
    # 对外主入口
    # ------------------------------------------------------------------

    def process(self, raw_input: Any, mode: str = "single") -> ProcessingResult:
        """
        处理输入内容，返回结构化结果。

        :param raw_input: 用户输入（字符串或已解析的字典）
        :param mode: 处理模式（single/batch/custom）
        :return: 处理结果
        :raises ValueError: 当输入无效或超出能力范围时，附带错误码
        """
        # 参数校验
        if mode not in SUPPORTED_MODES:
            raise ValueError(f"E010: 不支持的模式 '{mode}'，可选值: {sorted(SUPPORTED_MODES)}")

        # 输入为空检查（E001）
        if raw_input is None or (isinstance(raw_input, str) and not raw_input.strip()):
            raise ValueError("E001: " + ERROR_MESSAGES["E001"])

        # 解析输入（字符串 -> 字典）
        try:
            parsed = self._parse_input(raw_input)
        except ValueError as e:
            # 解析失败时，如果是空输入，返回 E001；否则 E003
            if "E001" in str(e):
                raise
            raise ValueError("E003: " + ERROR_MESSAGES["E003"]) from e

        # 检查关键信息是否完整（E002）
        missing = self._check_required_fields(parsed)
        if missing:
            raise ValueError(
                f"E002: {ERROR_MESSAGES['E002']} 缺失字段: {', '.join(missing)}"
            )

        # 检查是否超出能力边界（E004）
        if self._is_out_of_scope(parsed):
            raise ValueError("E004: " + ERROR_MESSAGES["E004"])

        # 执行核心处理流程
        try:
            result = self._execute_pipeline(parsed, mode)
        except Exception as e:
            # 处理过程中发生未预期错误，归类为 E009
            raise ValueError("E009: " + ERROR_MESSAGES["E009"]) from e

        # 置信度检查（E005）
        if result.confidence < MEDIUM_CONFIDENCE_THRESHOLD:
            result.warnings.append(ERROR_MESSAGES["E005"])

        return result

    # ------------------------------------------------------------------
    # 内部方法（私有）
    # ------------------------------------------------------------------

    def _parse_input(self, raw_input: Any) -> Dict[str, Any]:
        """
        将输入解析为字典。

        支持两种格式：
        1. 已经是字典（直接使用）
        2. 字符串（尝试 JSON 解析）
        """
        if isinstance(raw_input, dict):
            return raw_input

        if isinstance(raw_input, str):
            try:
                data = json.loads(raw_input)
                if not isinstance(data, dict):
                    raise ValueError("E003")
                return data
            except json.JSONDecodeError as e:
                raise ValueError("E003") from e

        # 其他类型不支持
        raise ValueError("E003")

    def _check_required_fields(self, data: Dict[str, Any]) -> List[str]:
        """检查必填字段，返回缺失字段列表。"""
        return [field for field in self.REQUIRED_FIELDS if field not in data]

    def _is_out_of_scope(self, data: Dict[str, Any]) -> bool:
        """
        判断输入是否超出能力边界（规格书"不做"部分）。

        当前规则：
        - 如果用户要求"分析"或"预测"，超出范围。
        - 如果用户要求访问网络，超出范围。
        """
        content = str(data.get("content", "")).lower()
        out_of_scope_keywords = ["分析趋势", "预测未来", "访问网络", "实时数据"]
        return any(keyword in content for keyword in out_of_scope_keywords)

    def _execute_pipeline(self, data: Dict[str, Any], mode: str) -> ProcessingResult:
        """
        执行核心处理流水线（规格书 Step 2）。

        步骤：
        1. 识别关键字段并结构化
        2. 按默认模板组织输出
        3. 标注置信度
        """
        # 1. 提取关键字段
        extracted_fields = {}
        for field, extractor in self._field_extractors.items():
            extracted_fields[field] = extractor(data)

        # 2. 组织输出内容
        output_content = self._organize_output(data, extracted_fields, mode)

        # 3. 计算置信度
        confidence = self._calculate_confidence(data, extracted_fields)

        # 生成警告信息
        warnings = self._generate_warnings(data, extracted_fields)

        return ProcessingResult(
            content=output_content,
            confidence=confidence,
            fields=extracted_fields,
            warnings=warnings,
        )

    def _extract_source(self, data: Dict[str, Any]) -> str:
        """提取输入来源。"""
        source = data.get("source", "")
        if not source:
            return "未知来源"
        return str(source)

    def _extract_format(self, data: Dict[str, Any]) -> str:
        """提取输出格式要求。"""
        format_req = data.get("format", "")
        if not format_req:
            return "默认格式"
        return str(format_req)

    def _extract_completeness(self, data: Dict[str, Any]) -> str:
        """提取期望的完整度。"""
        completeness = data.get("completeness", "")
        if not completeness:
            return "快速骨架"
        return str(completeness)

    def _organize_output(
        self, data: Dict[str, Any], fields: Dict[str, Any], mode: str
    ) -> Dict[str, Any]:
        """
        按默认模板组织输出结构。

        模板结构：
        {
            "summary": "处理摘要",
            "details": {...},
            "mode": "处理模式"
        }
        """
        content = data.get("content", "")
        source = fields["source"]
        format_req = fields["format"]
        completeness = fields["completeness"]

        # 根据完整度决定详细程度
        if completeness == "快速骨架":
            details = {
                "content_length": len(str(content)),
                "content_preview": str(content)[:50] + ("..." if len(str(content)) > 50 else ""),
            }
        else:  # 详细成品
            details = {
                "content_length": len(str(content)),
                "content_full": str(content),
                "source_type": source,
                "format_requirement": format_req,
            }

        return {
            "summary": f"已处理来自 {source} 的输入，输出格式: {format_req}",
            "details": details,
            "mode": mode,
        }

    def _calculate_confidence(
        self, data: Dict[str, Any], fields: Dict[str, Any]
    ) -> float:
        """
        计算置信度（0-100）。

        规则（依据规格书 Step 2）：
        - 基础置信度 80%
        - 如果所有必填字段都有有信息量的值，+10%
        - 如果内容非空，+5%
        - 如果格式明确（不是默认值），+5%
        - 上限 100%
        """
        confidence = 80.0

        # 检查所有必填字段是否有有信息量的值
        all_fields_meaningful = True
        for field in self.REQUIRED_FIELDS:
            value = str(fields.get(field, "")).strip()
            if value in LOW_INFO_VALUES:
                all_fields_meaningful = False
                break

        if all_fields_meaningful:
            confidence += 10.0

        # 内容非空
        content = data.get("content", "")
        if content and str(content).strip():
            confidence += 5.0

        # 格式明确（不是默认值）
        if fields["format"] not in LOW_INFO_VALUES:
            confidence += 5.0

        # 限制在 0-100 范围
        return max(0.0, min(100.0, confidence))

    def _generate_warnings(
        self, data: Dict[str, Any], fields: Dict[str, Any]
    ) -> List[str]:
        """生成警告信息列表。"""
        warnings = []

        # 如果来源是 URL，提示不访问网络
        if "url" in str(fields["source"]).lower() or "http" in str(fields["source"]).lower():
            warnings.append("检测到 URL 来源，本工具不访问网络，仅处理提供的文本内容。")

        # 如果内容包含敏感关键词，提示谨慎使用
        sensitive_keywords = ["合同", "税务", "投资", "医疗"]
        content_str = str(data.get("content", ""))
        if any(keyword in content_str for keyword in sensitive_keywords):
            warnings.append(
                "内容涉及专业领域（法律/财务/税务/投资/医疗），请咨询持证专业人士。"
            )

        return warnings


# ---------------------------------------------------------------------------
# 批处理支持（规格书"进阶用法"）
# ---------------------------------------------------------------------------


class BatchProcessor:
    """批量处理多个输入。"""

    def __init__(self, core: Optional[CoreProcessor] = None) -> None:
        """初始化批处理器。"""
        self.core = core if core is not None else CoreProcessor()

    def process_batch(self, items: List[Any]) -> List[Dict[str, Any]]:
        """
        批量处理输入列表。

        :param items: 输入列表
        :return: 结果字典列表（包含成功和失败项）
        """
        results = []
        for idx, item in enumerate(items):
            try:
                result = self.core.process(item, mode="batch")
                results.append(
                    {"index": idx, "success": True, "result": result.to_dict()}
                )
            except ValueError as e:
                # 提取错误码
                error_code = str(e).split(":")[0] if ":" in str(e) else "E009"
                results.append(
                    {
                        "index": idx,
                        "success": False,
                        "error_code": error_code,
                        "error_message": str(e),
                    }
                )
        return results


# ---------------------------------------------------------------------------
# 命令行接口
# ---------------------------------------------------------------------------


def run_selftest() -> int:
    """
    离线自检核心逻辑。

    使用内置硬编码样例数据，不读取外部文件、不依赖当前工作目录、不访问网络。
    断言使用宽松阈值（大小比较/区间判断），确保任何环境直接可过。

    :return: 0 表示全部通过，非 0 表示失败
    """
    print("=" * 60)
    print("开始离线自检（--selftest）...")
    print("=" * 60)

    processor = CoreProcessor()
    batch_processor = BatchProcessor(processor)

    # ------------------------------------------------------------------
    # 测试用例 1：正常处理（高置信度）
    # ------------------------------------------------------------------
    print("\n[测试 1] 正常输入处理（期望成功）")
    sample_input = {
        "source": "用户提供的数据",
        "format": "JSON",
        "completeness": "快速骨架",
        "content": "这是一个测试内容，用于验证核心处理逻辑是否正常工作。",
    }
    try:
        result = processor.process(sample_input)
        assert isinstance(result, ProcessingResult), "返回类型应为 ProcessingResult"
        assert result.confidence >= 85.0, f"置信度应 >=85%，实际: {result.confidence}"
        assert result.content is not None, "输出内容不能为空"
        assert "summary" in result.content, "输出应包含摘要"
        assert result.fields["source"] == "用户提供的数据", "来源字段提取错误"
        print(f"  ✓ 通过 (置信度: {result.confidence:.1f}%)")
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        return 1

    # ------------------------------------------------------------------
    # 测试用例 2：空输入（期望 E001）
    # ------------------------------------------------------------------
    print("\n[测试 2] 空输入处理（期望 E001）")
    try:
        processor.process("")
        print("  ✗ 失败: 应抛出 E001 错误")
        return 1
    except ValueError as e:
        assert "E001" in str(e), f"错误码应为 E001，实际: {e}"
        print(f"  ✓ 通过 (错误码: E001)")

    # ------------------------------------------------------------------
    # 测试用例 3：JSON 字符串输入（期望成功）
    # ------------------------------------------------------------------
    print("\n[测试 3] JSON 字符串输入处理（期望成功）")
    json_input = json.dumps(
        {
            "source": "文件",
            "format": "CSV",
            "completeness": "详细成品",
            "content": "文件内容示例",
        }
    )
    try:
        result = processor.process(json_input)
        assert result.confidence >= 90.0, f"置信度应 >=90%，实际: {result.confidence}"
        assert result.fields["format"] == "CSV", "格式字段提取错误"
        print(f"  ✓ 通过 (置信度: {result.confidence:.1f}%)")
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        return 1

    # ------------------------------------------------------------------
    # 测试用例 4：缺失必填字段（期望 E002）
    # ------------------------------------------------------------------
    print("\n[测试 4] 缺失必填字段（期望 E002）")
    try:
        processor.process({"content": "只有内容"})
        print("  ✗ 失败: 应抛出 E002 错误")
        return 1
    except ValueError as e:
        assert "E002" in str(e), f"错误码应为 E002，实际: {e}"
        print(f"  ✓ 通过 (错误码: E002)")

    # ------------------------------------------------------------------
    # 测试用例 5：超出能力边界（期望 E004）
    # ------------------------------------------------------------------
    print("\n[测试 5] 超出能力边界（期望 E004）")
    try:
        processor.process(
            {
                "source": "用户",
                "format": "文本",
                "completeness": "快速骨架",
                "content": "请帮我分析趋势并预测未来",
            }
        )
        print("  ✗ 失败: 应抛出 E004 错误")
        return 1
    except ValueError as e:
        assert "E004" in str(e), f"错误码应为 E004，实际: {e}"
        print(f"  ✓ 通过 (错误码: E004)")

    # ------------------------------------------------------------------
    # 测试用例 6：批量处理（期望混合结果）
    # ------------------------------------------------------------------
    print("\n[测试 6] 批量处理（期望混合结果）")
    batch_items = [
        {
            "source": "用户",
            "format": "文本",
            "completeness": "快速骨架",
            "content": "第一条批量数据",
        },
        {"content": "缺失字段的数据"},
        "无效输入",
    ]
    try:
        batch_results = batch_processor.process_batch(batch_items)
        assert len(batch_results) == 3, f"应返回 3 条结果，实际: {len(batch_results)}"
        assert batch_results[0]["success"] is True, "第一条应成功"
        assert batch_results[1]["success"] is False, "第二条应失败"
        assert batch_results[1]["error_code"] == "E002", "第二条错误码应为 E002"
        assert batch_results[2]["success"] is False, "第三条应失败"
        assert batch_results[2]["error_code"] == "E003", "第三条错误码应为 E003"
        print(f"  ✓ 通过 (成功: {sum(1 for r in batch_results if r['success'])} 条)")

    except Exception as e:
        print(f"  ✗ 失败: {e}")
        return 1

    # ------------------------------------------------------------------
    # 测试用例 7：低置信度场景（期望 E005 警告）
    # ------------------------------------------------------------------
    print("\n[测试 7] 低置信度场景（期望 E005 警告）")
    try:
        # 构造一个置信度低于 85% 的场景
        low_conf_input = {
            "source": "未知",
            "format": "默认格式",
            "completeness": "快速骨架",
            "content": "",
        }
        result = processor.process(low_conf_input)
        # 此时置信度应该较低（内容为空，-5%；格式默认，-5%；字段无信息量，-10%）
        assert result.confidence < 85.0, f"置信度应 <85%，实际: {result.confidence}"
        assert any("E005" in w or "无法确定" in w for w in result.warnings), "应包含 E005 相关警告"
        print(f"  ✓ 通过 (置信度: {result.confidence:.1f}%，含警告)")

    except Exception as e:
        print(f"  ✗ 失败: {e}")
        return 1

    # ------------------------------------------------------------------
    # 测试用例 8：错误码体系完整性
    # ------------------------------------------------------------------
    print("\n[测试 8] 错误码体系完整性")
    try:
        # 检查所有错误码都有对应话术
        expected_codes = [f"E{num:03d}" for num in range(1, 11)]
        for code in expected_codes:
            assert code in ERROR_MESSAGES, f"缺少错误码 {code} 的话术"
            assert ERROR_MESSAGES[code].strip(), f"错误码 {code} 的话术为空"
        print(f"  ✓ 通过 (共 {len(expected_codes)} 个错误码)")

    except Exception as e:
        print(f"  ✗ 失败: {e}")
        return 1

    # ------------------------------------------------------------------
    # 测试用例 9：批量处理器边界
    # ------------------------------------------------------------------
    print("\n[测试 9] 批量处理器边界")
    try:
        # 空列表
        empty_result = batch_processor.process_batch([])
        assert empty_result == [], "空列表应返回空结果"

        # 单个元素
        single_result = batch_processor.process_batch([{"source": "a", "format": "b", "completeness": "c", "content": "d"}])
        assert len(single_result) == 1, "单个元素应返回 1 条结果"
        assert single_result[0]["success"] is True, "单个有效元素应成功"

        print("  ✓ 通过 (空列表和单元素处理正常)")

    except Exception as e:
        print(f"  ✗ 失败: {e}")
        return 1

    # ------------------------------------------------------------------
    # 测试用例 10：结果序列化
    # ------------------------------------------------------------------
    print("\n[测试 10] 结果序列化")
    try:
        sample_result = ProcessingResult(
            content={"key": "value"},
            confidence=95.0,
            fields={"source": "测试"},
            warnings=["测试警告"],
        )
        serialized = json.dumps(sample_result.to_dict())
        assert serialized, "序列化结果不应为空"
        deserialized = json.loads(serialized)
        assert deserialized["confidence"] == 95.0, "反序列化后置信度应一致"
        assert deserialized["confidence_label"] == "直接输出", "置信度标签应为'直接输出'"
        print("  ✓ 通过 (JSON 序列化/反序列化正常)")

    except Exception as e:
        print(f"  ✗ 失败: {e}")
        return 1

    # ------------------------------------------------------------------
    # 汇总
    # ------------------------------------------------------------------
    print("\n" + "=" * 60)
    print("全部自检通过！✓")
    print("=" * 60)
    return 0


def main() -> int:
    """命令行入口函数。"""
    parser = argparse.ArgumentParser(
        description="未命名工具 - 基于 cursor-1c-skills 规格的独立实现",
        epilog="示例: python main.py --selftest",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行离线自检（使用内置硬编码数据，不依赖外部环境）",
    )
    parser.add_argument(
        "--input",
        type=str,
        help="输入 JSON 字符串（用于单次处理），格式: {'source': ..., 'format': ..., 'completeness': ..., 'content': ...}",
    )
    parser.add_argument(
        "--mode",
        type=str,
        default="single",
        choices=sorted(SUPPORTED_MODES),
        help="处理模式 (默认: single)",
    )
    parser.add_argument(
        "--batch",
        type=str,
        help="批量输入 JSON 数组字符串（用于批量处理）",
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        return run_selftest()

    # 单次处理模式
    if args.input:
        try:
            processor = CoreProcessor()
            result = processor.process(args.input, mode=args.mode)
            print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
            return 0
        except ValueError as e:
            print(f"错误: {e}", file=sys.stderr)
            return 1

    # 批量处理模式
    if args.batch:
        try:
            items = json.loads(args.batch)
            if not isinstance(items, list):
                raise ValueError("E003: 批量输入应为 JSON 数组")
            processor = BatchProcessor()
            results = processor.process_batch(items)
            print(json.dumps(results, ensure_ascii=False, indent=2))
            return 0
        except ValueError as e:
            print(f"错误: {e}", file=sys.stderr)
            return 1

    # 无参数时显示帮助
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
