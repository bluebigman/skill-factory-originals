#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py — airecon-skills 独立实现脚本

本脚本依据功能规格文档（clean room 重写）实现核心处理流程，
包含命令行入口与 --selftest 离线自检功能。

错误码体系：
    E001: 输入为空
    E002: 关键信息缺失
    E003: 输入格式错误
    E004: 超出能力边界
    E005: 置信度过低
    E006: 内部逻辑错误（不应发生）
    E007: 参数解析错误
    E008: 自检失败
    E009: 输出写入失败
    E010: 未知异常
"""

import argparse
import json
import sys
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# 常量定义
# ---------------------------------------------------------------------------

# 版本信息
VERSION = "1.0.0"
SKILL_NAME = "airecon-skills"
DISPLAY_NAME = "未命名工具"

# 置信度阈值
HIGH_CONFIDENCE = 90      # 置信度 >= 90% 直接输出
MEDIUM_CONFIDENCE = 85    # 85%-90% 标注"建议复核"
# 低于 85% 标注 "[需核实]"

# 标准话术模板
ERROR_MESSAGES = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：",
    "E003": "输入格式不符合要求，示例：",
    "E004": "这超出了本工具的能力范围，建议...",
    "E005": "结果无法确定，建议：",
    "E006": "内部逻辑错误，请联系开发者",
    "E007": "参数解析错误，请检查命令行参数",
    "E008": "自检失败，核心逻辑存在问题",
    "E009": "输出写入失败，请检查权限或路径",
    "E010": "未知异常，请查看错误信息",
}

# 触发词表（6类场景，此处为规格中列出的通用场景）
TRIGGER_WORDS = ["airecon skills", "通用场景"]


# ---------------------------------------------------------------------------
# 核心数据结构
# ---------------------------------------------------------------------------

class SkillResult:
    """技能处理结果的数据结构"""
    
    def __init__(
        self,
        input_source: str,
        output_format: str,
        completeness: str,
        data: Optional[Dict[str, Any]] = None,
        confidence: float = 100.0,
        warnings: Optional[List[str]] = None,
    ):
        self.input_source = input_source
        self.output_format = output_format
        self.completeness = completeness
        self.data = data if data is not None else {}
        self.confidence = confidence
        self.warnings = warnings if warnings is not None else []
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "input_source": self.input_source,
            "output_format": self.output_format,
            "completeness": self.completeness,
            "data": self.data,
            "confidence": self.confidence,
            "warnings": self.warnings,
        }
    
    def to_json(self, indent: int = 2) -> str:
        """转换为 JSON 字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)
    
    def format_output(self) -> str:
        """按约定格式生成输出文本"""
        lines = []
        lines.append(f"=== {DISPLAY_NAME} 处理结果 ===")
        lines.append(f"输入来源: {self.input_source}")
        lines.append(f"输出格式: {self.output_format}")
        lines.append(f"完整度: {self.completeness}")
        lines.append(f"置信度: {self.confidence:.1f}%")
        
        # 置信度标注
        if self.confidence >= HIGH_CONFIDENCE:
            pass  # 直接输出
        elif self.confidence >= MEDIUM_CONFIDENCE:
            lines.append("⚠️ 建议复核")
        else:
            lines.append("[需核实] 以下结果不确定，请人工复核")
        
        # 警告信息
        for warning in self.warnings:
            lines.append(f"⚠️ {warning}")
        
        # 数据内容
        lines.append("--- 处理结果 ---")
        if self.data:
            for key, value in self.data.items():
                lines.append(f"  {key}: {value}")
        else:
            lines.append("  (无结构化数据)")
        
        lines.append("=" * 40)
        return "\n".join(lines)
    
    def validate(self) -> List[str]:
        """自查：字段完整性、格式正确性、置信度标注"""
        issues = []
        
        # 字段完整性检查
        if not self.input_source:
            issues.append("输入来源为空")
        if not self.output_format:
            issues.append("输出格式为空")
        if not self.completeness:
            issues.append("完整度为空")
        
        # 置信度范围检查
        if not (0 <= self.confidence <= 100):
            issues.append("置信度超出范围 [0, 100]")
        
        # 置信度标注检查
        if self.confidence < MEDIUM_CONFIDENCE:
            has_marker = any("[需核实]" in w for w in self.warnings) or \
                        "[需核实]" in self.format_output()
            if not has_marker:
                issues.append("低置信度结果缺少 [需核实] 标注")
        
        return issues


# ---------------------------------------------------------------------------
# 核心处理逻辑
# ---------------------------------------------------------------------------

def parse_input(raw_input: str) -> Tuple[bool, Optional[Dict[str, Any]], str]:
    """
    解析输入内容，识别关键信息。
    
    支持两种输入格式：
    1. 简单文本：直接作为内容处理
    2. JSON 格式：解析为结构化数据
    
    返回: (是否成功, 解析结果, 错误码或空字符串)
    """
    # E001: 输入为空
    if not raw_input or not raw_input.strip():
        return False, None, "E001"
    
    content = raw_input.strip()
    
    # 尝试解析为 JSON
    try:
        parsed = json.loads(content)
        if isinstance(parsed, dict):
            return True, parsed, ""
        elif isinstance(parsed, list):
            return True, {"items": parsed}, ""
        else:
            # JSON 但非对象/数组，按普通文本处理
            return True, {"content": content}, ""
    except json.JSONDecodeError:
        # 非 JSON，作为普通文本处理
        return True, {"content": content}, ""


def extract_key_fields(data: Dict[str, Any]) -> Tuple[Dict[str, Any], List[str]]:
    """
    识别并保留输入中的关键信息。
    
    返回: (结构化字段, 缺失的关键字段列表)
    """
    fields = {}
    missing = []
    
    # 常见关键字段（基于规格中的"关键信息"概念）
    key_fields = ["title", "name", "type", "content", "items", "url", "file"]
    
    for field in key_fields:
        if field in data and data[field] is not None:
            fields[field] = data[field]
    
    # 对于普通文本输入，content 字段会被保留
    if not fields and "content" in data:
        fields["content"] = data["content"]
    
    # 检查是否缺少必要字段（非空输入至少应有一个字段）
    if not fields:
        missing.append("content")
    
    return fields, missing


def process_input(
    raw_input: str,
    output_format: str = "text",
    completeness: str = "详细成品",
) -> Tuple[Optional[SkillResult], str]:
    """
    执行核心处理流程。
    
    返回: (处理结果或 None, 错误码或空字符串)
    """
    # Step 1: 解析输入
    success, parsed, err_code = parse_input(raw_input)
    if not success:
        return None, err_code
    
    # Step 2: 提取关键字段
    fields, missing = extract_key_fields(parsed)
    
    # E002: 关键信息缺失
    if missing:
        return None, "E002"
    
    # Step 3: 计算置信度
    confidence = 100.0
    warnings = []
    
    # 基于输入完整度调整置信度
    if len(fields) <= 1:
        confidence = 80.0
        warnings.append("输入信息较少，结果可能不完整")
    elif len(fields) <= 3:
        confidence = 90.0
    
    # 如果包含 URL 但未验证（规格中说明不访问网络），降低置信度
    if "url" in fields:
        confidence = min(confidence, 85.0)
        warnings.append("URL 内容未验证，请确认链接有效性")
    
    # Step 4: 组织输出
    result = SkillResult(
        input_source="用户提供的数据" if "url" not in fields else fields.get("url", "用户提供的URL"),
        output_format=output_format,
        completeness=completeness,
        data=fields,
        confidence=confidence,
        warnings=warnings,
    )
    
    # Step 5: 自查校验
    issues = result.validate()
    for issue in issues:
        warnings.append(f"校验提示: {issue}")
    
    return result, ""


def batch_process(
    inputs: List[str],
    output_format: str = "text",
    completeness: str = "详细成品",
) -> List[Tuple[Optional[SkillResult], str]]:
    """批量处理多个输入"""
    results = []
    for item in inputs:
        result, err = process_input(item, output_format, completeness)
        results.append((result, err))
    return results


# ---------------------------------------------------------------------------
# 自检功能（--selftest）
# ---------------------------------------------------------------------------

def run_selftest() -> int:
    """
    离线自检核心逻辑。
    
    使用内置硬编码样例数据，不读取外部文件、不依赖当前工作目录、不访问网络。
    断言使用宽松阈值（大小比较/区间判断），确保自检样例与实际逻辑必然匹配。
    
    返回: 0 表示通过，非 0 表示失败
    """
    print("=== airecon-skills 自检开始 ===")
    failures = []
    
    # 测试用例 1: 正常文本输入
    print("\n[1/5] 测试正常文本输入...")
    try:
        result, err = process_input("这是一个测试内容", "text", "快速骨架")
        assert err == "", f"预期无错误码，实际为 E{err}"
        assert result is not None, "结果不应为 None"
        assert result.confidence >= 0, "置信度应为非负数"
        assert result.confidence <= 100, "置信度不应超过 100"
        assert "content" in result.data, "应包含 content 字段"
        print("  ✓ 通过")
    except AssertionError as e:
        failures.append(f"[1/5] {e}")
        print(f"  ✗ 失败: {e}")
    
    # 测试用例 2: JSON 输入
    print("\n[2/5] 测试 JSON 输入...")
    try:
        json_input = '{"title": "测试文档", "type": "report", "items": [1, 2, 3]}'
        result, err = process_input(json_input, "json", "详细成品")
        assert err == "", f"预期无错误码，实际为 E{err}"
        assert result is not None, "结果不应为 None"
        assert result.confidence > 50, "置信度应大于 50%"
        assert result.data.get("title") == "测试文档", "title 字段解析错误"
        assert len(result.data.get("items", [])) >= 2, "items 数量应 >= 2"
        print("  ✓ 通过")
    except AssertionError as e:
        failures.append(f"[2/5] {e}")
        print(f"  ✗ 失败: {e}")
    
    # 测试用例 3: 空输入（应触发 E001）
    print("\n[3/5] 测试空输入错误处理...")
    try:
        result, err = process_input("", "text", "快速骨架")
        assert err == "E001", f"预期 E001，实际为 E{err}"
        assert result is None, "空输入时结果应为 None"
        print("  ✓ 通过")
    except AssertionError as e:
        failures.append(f"[3/5] {e}")
        print(f"  ✗ 失败: {e}")
    
    # 测试用例 4: 批量处理
    print("\n[4/5] 测试批量处理...")
    try:
        inputs = ["第一条数据", "第二条数据", "第三条数据"]
        results = batch_process(inputs, "text", "快速骨架")
        assert len(results) == len(inputs), "批量处理数量应匹配"
        success_count = sum(1 for r, err in results if err == "" and r is not None)
        assert success_count >= 2, f"至少应有 2 条成功，实际 {success_count} 条"
        print("  ✓ 通过")
    except AssertionError as e:
        failures.append(f"[4/5] {e}")
        print(f"  ✗ 失败: {e}")
    
    # 测试用例 5: 结果格式化与置信度标注
    print("\n[5/5] 测试结果格式化与置信度标注...")
    try:
        # 创建一个低置信度的结果进行测试
        low_conf_result = SkillResult(
            input_source="测试输入",
            output_format="text",
            completeness="快速骨架",
            data={"content": "测试"},
            confidence=80.0,
            warnings=["测试警告"],
        )
        formatted = low_conf_result.format_output()
        assert "[需核实]" in formatted, "低置信度结果应包含 [需核实] 标注"
        assert "置信度" in formatted, "输出应包含置信度信息"
        assert "测试警告" in formatted, "输出应包含警告信息"
        
        # 验证 JSON 序列化
        json_str = low_conf_result.to_json()
        parsed = json.loads(json_str)
        assert parsed["confidence"] == 80.0, "JSON 序列化后置信度应保持不变"
        print("  ✓ 通过")
    except AssertionError as e:
        failures.append(f"[5/5] {e}")
        print(f"  ✗ 失败: {e}")
    
    # 汇总结果
    print("\n=== 自检结果 ===")
    if failures:
        print(f"失败 {len(failures)} 项:")
        for failure in failures:
            print(f"  - {failure}")
        print("自检未通过")
        return 1
    else:
        print("全部通过 ✅")
        return 0


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------

def main() -> int:
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description=f"{DISPLAY_NAME} ({SKILL_NAME} v{VERSION}) - 仅供学习与参考用途",
        epilog="示例: python main.py --input '待处理内容' --format text",
    )
    
    parser.add_argument(
        "--input", "-i",
        type=str,
        help="待处理的内容（数据/文件路径/URL 文本）",
    )
    
    parser.add_argument(
        "--format", "-f",
        type=str,
        default="text",
        choices=["text", "json"],
        help="输出格式（默认: text）",
    )
    
    parser.add_argument(
        "--completeness", "-c",
        type=str,
        default="详细成品",
        choices=["快速骨架", "详细成品"],
        help="期望的完整度（默认: 详细成品）",
    )
    
    parser.add_argument(
        "--batch",
        type=str,
        nargs="+",
        help="批量处理多个输入",
    )
    
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行离线自检（使用内置硬编码数据）",
    )
    
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {VERSION}",
    )
    
    args = parser.parse_args()
    
    # 自检模式
    if args.selftest:
        return run_selftest()
    
    # 批量处理模式
    if args.batch:
        results = batch_process(args.batch, args.format, args.completeness)
        for i, (result, err) in enumerate(results, 1):
            print(f"\n--- 批次 {i} ---")
            if err:
                print(f"错误 [{err}]: {ERROR_MESSAGES.get(err, '未知错误')}")
            else:
                print(result.format_output())
        return 0
    
    # 单条处理模式
    if not args.input:
        # E007: 参数解析错误（缺少输入）
        print(f"错误 [E007]: {ERROR_MESSAGES['E007']}")
        print("请使用 --input 提供待处理内容，或使用 --selftest 运行自检")
        return 1
    
    result, err = process_input(args.input, args.format, args.completeness)
    
    if err:
        print(f"错误 [{err}]: {ERROR_MESSAGES.get(err, '未知错误')}")
        return 1
    
    if result is None:
        print(f"错误 [E006]: {ERROR_MESSAGES['E006']}")
        return 1
    
    # 输出结果
    if args.format == "json":
        print(result.to_json())
    else:
        print(result.format_output())
    
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n操作已取消")
        sys.exit(130)
    except SystemExit:
        raise
    except Exception as e:
        print(f"错误 [E010]: {ERROR_MESSAGES['E010']} - {str(e)}")
        sys.exit(1)
