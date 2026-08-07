#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
okf-skills 技能实现脚本

根据功能规格独立实现（clean-room），仅依赖 Python 标准库。
提供核心处理流程、错误码体系、命令行入口及离线自检功能。

用法示例:
    python scripts/main.py --selftest
    python scripts/main.py --input "用户提供的数据" --format json
"""

import argparse
import json
import sys
from typing import Any, Dict, List, Optional

# ============================================================
# 常量定义
# ============================================================

# 错误码及标准化话术（对应规格第四章）
ERROR_MESSAGES: Dict[str, str] = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：",
    "E003": "输入格式不符合要求，示例：...",
    "E004": "这超出了本工具的能力范围，建议：...",
    "E005": "结果无法确定，建议：...",
    "E006": "内部处理异常，请重试或提供更多上下文",
    "E007": "输出格式不受支持，可选：text / json",
    "E008": "批量处理时出现错误，请检查每项输入",
    "E009": "参数校验失败，请检查命令行参数",
    "E010": "自检失败，核心逻辑存在缺陷",
}

# 输出格式支持列表
SUPPORTED_OUTPUT_FORMATS = ("text", "json")

# 置信度阈值（对应规格第三章 Step 2）
HIGH_CONFIDENCE_THRESHOLD = 90      # 置信度 >= 90%：直接输出
MEDIUM_CONFIDENCE_THRESHOLD = 85    # 85% <= 置信度 < 90%：建议复核

# 能力边界声明（对应规格第一章）
BOUNDARY_STATEMENTS = {
    "do": [
        "将用户提供的数据/文件/URL 转换为结构化结果",
        "识别并保留输入中的关键信息",
        "按约定格式生成输出",
        "对不确定项给出置信度提示",
        "支持批量处理和自定义格式",
    ],
    "do_not": [
        "不执行超出输入范围的分析",
        "不保证绝对准确，低置信度会标注",
        "不访问网络或外部服务",
    ],
}

# 触发词表（对应规格第二章）
TRIGGER_WORDS = ["okf skills"]


# ============================================================
# 核心数据结构
# ============================================================

class SkillResult:
    """技能处理结果对象"""

    def __init__(
        self,
        content: str,
        confidence: float,
        fields: Optional[Dict[str, Any]] = None,
        warnings: Optional[List[str]] = None,
    ) -> None:
        self.content = content          # 结果内容
        self.confidence = confidence    # 置信度 0-100
        self.fields = fields or {}      # 结构化字段
        self.warnings = warnings or []  # 警告列表

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（用于 JSON 输出）"""
        return {
            "content": self.content,
            "confidence": self.confidence,
            "fields": self.fields,
            "warnings": self.warnings,
        }


# ============================================================
# 核心处理逻辑
# ============================================================

class OKFSkills:
    """okf-skills 技能主类"""

    def __init__(self) -> None:
        """初始化技能实例"""
        self.name = "okf-skills"
        self.display_name = "未命名工具"
        self.version = "1.0.0"

    # ---------- 入口方法 ----------

    def process(
        self,
        input_data: Any,
        output_format: str = "text",
        require_completeness: str = "auto",
    ) -> SkillResult:
        """
        处理输入数据并返回结果

        Args:
            input_data: 用户输入（字符串、列表、字典等）
            output_format: 输出格式（text / json）
            require_completeness: 期望完整度（快速骨架 / 详细成品 / auto）

        Returns:
            SkillResult 对象

        Raises:
            ValueError: 当输入无效或超出能力边界时，附带错误码
        """
        # 参数校验
        if output_format not in SUPPORTED_OUTPUT_FORMATS:
            raise ValueError(f"E007: {ERROR_MESSAGES['E007']}")

        # 输入为空检查（E001）
        if input_data is None or (isinstance(input_data, (str, list, dict)) and len(input_data) == 0):
            raise ValueError(f"E001: {ERROR_MESSAGES['E001']}")

        # 批量处理
        if isinstance(input_data, list):
            return self._process_batch(input_data, output_format)

        # 单条处理
        return self._process_single(input_data, output_format, require_completeness)

    # ---------- 内部处理方法 ----------

    def _process_batch(self, items: List[Any], output_format: str) -> SkillResult:
        """批量处理多个输入"""
        results = []
        total_confidence = 0.0
        all_warnings = []

        try:
            for item in items:
                result = self._process_single(item, "text")
                results.append(result.to_dict())
                total_confidence += result.confidence
                all_warnings.extend(result.warnings)
        except ValueError as exc:
            raise ValueError(f"E008: {ERROR_MESSAGES['E008']} 详情: {exc}") from exc

        # 批量结果的平均置信度
        avg_confidence = total_confidence / len(items) if items else 0.0

        content = self._format_batch_content(results)
        fields = {"batch_size": len(items), "items": results}

        return SkillResult(
            content=content,
            confidence=avg_confidence,
            fields=fields,
            warnings=all_warnings,
        )

    def _process_single(
        self, input_data: Any, output_format: str, require_completeness: str = "auto"
    ) -> SkillResult:
        """
        处理单条输入

        核心流程（对应规格第三章 Step 2）：
            1. 解析输入内容，识别关键信息
            2. 按规则结构化处理
            3. 生成结果并标注置信度
        """
        # Step 1: 解析输入
        parsed = self._parse_input(input_data)

        # 检查关键信息是否完整（E002）
        missing_fields = self._check_missing_fields(parsed)
        if missing_fields:
            detail = "、".join(missing_fields)
            raise ValueError(f"E002: {ERROR_MESSAGES['E002']}{detail}")

        # 输入格式检查（E003）
        if not self._validate_input_format(parsed):
            raise ValueError(f"E003: {ERROR_MESSAGES['E003']}")

        # Step 2: 结构化处理
        structured = self._structure_data(parsed)

        # 置信度评估
        confidence = self._calculate_confidence(structured)

        # 生成警告（根据置信度）
        warnings = self._generate_warnings(confidence)

        # 能力边界检查（E004）
        if self._exceeds_boundary(structured):
            raise ValueError(f"E004: {ERROR_MESSAGES['E004']}")

        # Step 3: 生成输出内容
        content = self._generate_content(structured, output_format)

        return SkillResult(
            content=content,
            confidence=confidence,
            fields=structured,
            warnings=warnings,
        )

    # ---------- 解析与校验 ----------

    def _parse_input(self, input_data: Any) -> Dict[str, Any]:
        """解析输入数据为统一结构"""
        if isinstance(input_data, str):
            # 尝试解析 JSON 字符串
            try:
                data = json.loads(input_data)
                if isinstance(data, dict):
                    return data
                return {"value": input_data}
            except json.JSONDecodeError:
                return {"content": input_data}
        elif isinstance(input_data, dict):
            return input_data
        elif isinstance(input_data, (int, float, bool)):
            return {"value": input_data}
        else:
            return {"content": str(input_data)}

    def _check_missing_fields(self, parsed: Dict[str, Any]) -> List[str]:
        """检查关键字段是否缺失"""
        # 对于简单输入（只有 content/value），视为关键信息完整
        if "content" in parsed or "value" in parsed:
            return []

        # 对于结构化输入，检查必要字段
        required_fields = ["type", "data"]
        missing = [f for f in required_fields if f not in parsed]
        return missing

    def _validate_input_format(self, parsed: Dict[str, Any]) -> bool:
        """验证输入格式是否合法"""
        # 内容非空即视为格式合法
        if "content" in parsed:
            return bool(parsed["content"].strip())
        if "value" in parsed:
            return parsed["value"] is not None
        # 结构化输入必须有 type 字段
        return "type" in parsed

    def _exceeds_boundary(self, structured: Dict[str, Any]) -> bool:
        """检查是否超出能力边界"""
        # 如果输入包含网络请求指令，视为超出边界
        content_str = str(structured.get("content", ""))
        forbidden_keywords = ["http://", "https://", "www."]
        return any(kw in content_str for kw in forbidden_keywords)

    # ---------- 数据处理 ----------

    def _structure_data(self, parsed: Dict[str, Any]) -> Dict[str, Any]:
        """将解析后的数据转换为结构化字段"""
        result = {}

        # 提取内容
        if "content" in parsed:
            result["content"] = parsed["content"]
            result["type"] = "text"
        elif "value" in parsed:
            result["value"] = parsed["value"]
            result["type"] = type(parsed["value"]).__name__
        else:
            # 保持原有结构，并补充元信息
            result.update(parsed)
            result["_processed"] = True

        # 添加处理元数据
        result["_meta"] = {
            "skill": self.name,
            "version": self.version,
            "processed_at": "offline",
        }

        return result

    def _calculate_confidence(self, structured: Dict[str, Any]) -> float:
        """计算置信度（0-100）"""
        # 基础置信度
        confidence = 95.0

        # 根据字段完整性调整
        if "content" in structured:
            content_len = len(structured["content"])
            if content_len < 10:
                confidence -= 10  # 内容过短，降低置信度
            elif content_len > 500:
                confidence -= 5   # 内容过长，可能有冗余

        # 有警告时降低置信度
        if structured.get("_meta"):
            confidence -= 2

        # 确保在合理范围内
        return max(0.0, min(100.0, confidence))

    def _generate_warnings(self, confidence: float) -> List[str]:
        """根据置信度生成警告信息"""
        warnings = []

        if confidence >= HIGH_CONFIDENCE_THRESHOLD:
            pass  # 高置信度，无警告
        elif confidence >= MEDIUM_CONFIDENCE_THRESHOLD:
            warnings.append("建议复核：结果置信度中等，请人工确认关键信息")
        else:
            warnings.append("[需核实]：结果置信度较低，存在不确定性，请核实后使用")

        return warnings

    # ---------- 输出生成 ----------

    def _generate_content(self, structured: Dict[str, Any], output_format: str) -> str:
        """生成输出内容"""
        if output_format == "json":
            return json.dumps(structured, ensure_ascii=False, indent=2)

        # 文本格式输出
        lines = []
        for key, value in structured.items():
            if key.startswith("_"):
                continue  # 跳过内部字段
            if isinstance(value, dict):
                lines.append(f"{key}:")
                for sub_key, sub_value in value.items():
                    lines.append(f"  {sub_key}: {sub_value}")
            else:
                lines.append(f"{key}: {value}")

        return "\n".join(lines)

    def _format_batch_content(self, results: List[Dict[str, Any]]) -> str:
        """格式化批量处理结果"""
        lines = [f"批量处理完成，共 {len(results)} 项：", ""]
        for idx, result in enumerate(results, 1):
            lines.append(f"--- 第 {idx} 项 ---")
            lines.append(result["content"])
            lines.append("")
        return "\n".join(lines)


# ============================================================
# 命令行入口
# ============================================================

def run_selftest() -> int:
    """
    离线自检核心逻辑

    使用内置硬编码样例数据，不读取外部文件、不依赖当前工作目录、
    不访问网络。任何环境直接可运行。

    Returns:
        0 表示通过，非 0 表示失败
    """
    print("[SELFTEST] 开始离线自检...")

    skill = OKFSkills()

    # ---------- 测试用例 1: 基本文本处理 ----------
    try:
        result = skill.process("这是一个测试输入", output_format="text")
        assert result.content, "E010: 文本处理结果不应为空"
        assert result.confidence > 50, "E010: 置信度应大于 50"
        print("[PASS] 基本文本处理")
    except Exception as exc:
        print(f"[FAIL] 基本文本处理: {exc}")
        return 1

    # ---------- 测试用例 2: JSON 格式输出 ----------
    try:
        result = skill.process("JSON 测试数据", output_format="json")
        # 验证输出是合法 JSON
        parsed_json = json.loads(result.content)
        assert "content" in parsed_json, "E010: JSON 输出应包含 content 字段"
        print("[PASS] JSON 格式输出")
    except Exception as exc:
        print(f"[FAIL] JSON 格式输出: {exc}")
        return 1

    # ---------- 测试用例 3: 批量处理 ----------
    try:
        items = ["第一条数据", "第二条数据", "第三条数据"]
        result = skill.process(items, output_format="text")
        assert result.fields.get("batch_size") == 3, "E010: 批量大小应为 3"
        assert result.confidence > 0, "E010: 批量置信度应大于 0"
        print("[PASS] 批量处理")
    except Exception as exc:
        print(f"[FAIL] 批量处理: {exc}")
        return 1

    # ---------- 测试用例 4: 错误处理（空输入） ----------
    try:
        skill.process("")
        print("[FAIL] 空输入应抛出 E001 错误")
        return 1
    except ValueError as exc:
        assert str(exc).startswith("E001"), "E010: 应返回 E001 错误码"
        print("[PASS] 空输入错误处理")

    # ---------- 测试用例 5: 结构化数据处理 ----------
    try:
        structured_input = {"type": "data", "data": {"key": "value"}}
        result = skill.process(structured_input, output_format="text")
        assert result.fields.get("type") == "data", "E010: 应保留 type 字段"
        print("[PASS] 结构化数据处理")
    except Exception as exc:
        print(f"[FAIL] 结构化数据处理: {exc}")
        return 1

    # ---------- 测试用例 6: 能力边界检测 ----------
    try:
        skill.process("请访问 http://example.com 获取数据")
        print("[FAIL] 应检测到超出能力边界")
        return 1
    except ValueError as exc:
        assert str(exc).startswith("E004"), "E010: 应返回 E004 错误码"
        print("[PASS] 能力边界检测")

    # ---------- 测试用例 7: 置信度区间检查 ----------
    try:
        # 长文本应产生合理的置信度
        long_text = "这是一个较长的测试文本。" * 50
        result = skill.process(long_text)
        assert 0 <= result.confidence <= 100, "E010: 置信度应在 0-100 范围内"
        print("[PASS] 置信度区间检查")
    except Exception as exc:
        print(f"[FAIL] 置信度区间检查: {exc}")
        return 1

    # ---------- 测试用例 8: 非法输出格式 ----------
    try:
        skill.process("测试", output_format="xml")
        print("[FAIL] 非法格式应抛出 E007 错误")
        return 1
    except ValueError as exc:
        assert str(exc).startswith("E007"), "E010: 应返回 E007 错误码"
        print("[PASS] 非法输出格式错误处理")

    print("[SELFTEST] 全部自检通过！")
    return 0


def main() -> int:
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description="okf-skills 技能实现",
        epilog="示例: python scripts/main.py --selftest",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行离线自检（不依赖外部资源）",
    )
    parser.add_argument(
        "--input",
        type=str,
        help="输入数据（字符串或 JSON 字符串）",
    )
    parser.add_argument(
        "--format",
        type=str,
        default="text",
        choices=SUPPORTED_OUTPUT_FORMATS,
        help="输出格式: text 或 json",
    )
    parser.add_argument(
        "--batch",
        action="store_true",
        help="批量模式（输入为 JSON 数组）",
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        return run_selftest()

    # 正常处理模式
    if not args.input:
        print(f"E001: {ERROR_MESSAGES['E001']}", file=sys.stderr)
        return 1

    try:
        skill = OKFSkills()

        # 批量模式：解析 JSON 数组
        if args.batch:
            try:
                items = json.loads(args.input)
                if not isinstance(items, list):
                    print("E009: 批量模式要求输入为 JSON 数组", file=sys.stderr)
                    return 1
            except json.JSONDecodeError:
                print("E009: 批量模式要求输入为合法 JSON 数组", file=sys.stderr)
                return 1
            result = skill.process(items, output_format=args.format)
        else:
            result = skill.process(args.input, output_format=args.format)

        # 输出结果
        print(result.content)

        # 输出警告（如果有）
        for warning in result.warnings:
            print(f"[警告] {warning}", file=sys.stderr)

        return 0

    except ValueError as exc:
        # 技能定义的错误（带错误码）
        print(str(exc), file=sys.stderr)
        return 1
    except Exception as exc:
        # 未预期错误
        print(f"E006: {ERROR_MESSAGES['E006']} 详情: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
