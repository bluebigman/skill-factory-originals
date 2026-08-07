#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
signal-wiki 技能实现脚本（clean-room 重写版）

功能概述：
    将用户提供的数据/文件/URL 转换为结构化结果，识别关键信息，
    按约定格式输出，并对不确定项给出置信度提示。

能力边界：
    1. 不执行超出输入范围的分析
    2. 不保证绝对准确，低置信度会标注
    3. 不访问网络或外部服务

错误码：
    E001 输入为空
    E002 关键信息缺失
    E003 输入格式错误
    E004 超出能力边界
    E005 置信度过低
    E006 参数解析失败
    E007 文件读取失败
    E008 输出写入失败
    E009 内部处理异常
    E010 自检失败
"""

import argparse
import json
import os
import re
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ------------------------------------------------------------
# 常量定义
# ------------------------------------------------------------
SKILL_NAME = "signal-wiki"
SKILL_VERSION = "1.0.0"
DEFAULT_CONFIDENCE = 0.90          # 默认置信度阈值
REVIEW_CONFIDENCE = 0.85           # 建议复核阈值
MIN_CONFIDENCE = 0.30              # 最低置信度下限
SUPPORTED_EXTENSIONS = {".txt", ".json", ".csv", ".md", ".log"}  # 支持的文件类型

# 关键字段识别正则（用于从文本中提取结构化信息）
KEY_FIELD_PATTERNS = {
    "标题": r"(?:标题|题目|title)[:：]\s*(.+)",
    "作者": r"(?:作者|作者名|author)[:：]\s*(.+)",
    "日期": r"(?:日期|时间|date)[:：]\s*(\d{4}[-/]\d{1,2}[-/]\d{1,2})",
    "编号": r"(?:编号|ID|编号号)[:：]\s*([A-Za-z0-9\-_]+)",
    "关键词": r"(?:关键词|关键字|tags?)[:：]\s*([^,，]+(?:[,，][^,，]+)*)",
    "摘要": r"(?:摘要|简介|summary|abstract)[:：]\s*(.+)",
    "内容": r"(?:内容|正文|body|content)[:：]\s*(.+)",
}


# ------------------------------------------------------------
# 核心数据结构
# ------------------------------------------------------------
class ProcessResult:
    """处理结果封装类"""

    def __init__(self, data: Dict[str, Any], confidence: float, warnings: List[str]):
        self.data = data              # 结构化数据
        self.confidence = confidence  # 置信度 0.0~1.0
        self.warnings = warnings      # 警告列表

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式（含元信息）"""
        return {
            "success": True,
            "skill": SKILL_NAME,
            "version": SKILL_VERSION,
            "timestamp": datetime.now().isoformat(),
            "confidence": self.confidence,
            "confidence_level": self._confidence_level(),
            "warnings": self.warnings,
            "data": self.data,
        }

    def _confidence_level(self) -> str:
        """根据置信度返回等级标注"""
        if self.confidence >= DEFAULT_CONFIDENCE:
            return "直接输出"
        elif self.confidence >= REVIEW_CONFIDENCE:
            return "建议复核"
        else:
            return "[需核实]"


class SkillError(Exception):
    """技能自定义异常，携带错误码"""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


# ------------------------------------------------------------
# 核心处理逻辑
# ------------------------------------------------------------
def process_input(raw_input: str, output_format: str = "json") -> Dict[str, Any]:
    """
    核心处理入口：将原始输入转换为结构化结果

    参数:
        raw_input: 用户提供的原始输入（文本/文件路径/URL）
        output_format: 输出格式（json/text）

    返回:
        处理结果字典

    异常:
        SkillError: 携带错误码 E001-E005
    """
    # E001: 输入为空
    if not raw_input or not raw_input.strip():
        raise SkillError("E001", "请提供待处理的内容，格式为：用户提供的数据/文件/URL")

    # 判断输入类型并提取内容
    content, source_type = _extract_content(raw_input)

    # 识别关键信息
    fields, confidence, warnings = _extract_key_fields(content)

    # 组装结果（即使没有匹配到关键字段，也返回低置信度结果，而不是报错）
    result = ProcessResult(
        data={
            "source_type": source_type,
            "source_preview": _truncate(content, 100),
            "fields": fields if fields else {"原文": _truncate(content, 200)},
            "raw_content": content,  # 保留原始内容
        },
        confidence=confidence,
        warnings=warnings,
    )

    # 如果没有任何关键字段，添加提示
    if not fields:
        result.warnings.append("未能识别出明确的关键字段，请人工审核原始内容")
        result.warnings.append("提示：可使用'标题：xxx'、'作者：xxx'、'日期：xxxx-xx-xx'等格式提供信息")

    # E005: 置信度过低（但仍有基础信息）
    if confidence < REVIEW_CONFIDENCE:
        warnings.append("[需核实] 置信度低于85%，请人工复核关键结果")

    # 按格式输出
    if output_format == "text":
        return _format_text(result)
    else:
        return result.to_dict()


def _extract_content(raw_input: str) -> Tuple[str, str]:
    """
    从输入中提取实际文本内容

    返回:
        (内容文本, 来源类型)
    """
    # 判断是否为文件路径
    if _is_file_path(raw_input):
        try:
            path = Path(raw_input)
            if not path.exists():
                raise SkillError("E007", f"文件不存在: {raw_input}")
            if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
                raise SkillError("E003", f"不支持的文件类型: {path.suffix}，支持: {SUPPORTED_EXTENSIONS}")
            with open(path, "r", encoding="utf-8") as f:
                return f.read(), f"file:{path.suffix}"
        except OSError as e:
            raise SkillError("E007", f"文件读取失败: {e}")

    # 判断是否为 URL（仅识别，不访问网络）
    if re.match(r'^https?://', raw_input.strip()):
        # 边界声明：不访问网络
        raise SkillError("E004", "这超出了本工具的能力范围，本工具不访问网络或外部服务")

    # 默认为纯文本
    return raw_input, "text"


def _is_file_path(text: str) -> bool:
    """判断是否为文件路径"""
    # 去除引号
    text = text.strip().strip('"').strip("'")
    # 检查常见路径特征
    if os.path.sep in text or text.endswith(tuple(SUPPORTED_EXTENSIONS)):
        return True
    return False


def _extract_key_fields(content: str) -> Tuple[Dict[str, str], float, List[str]]:
    """
    从文本中提取关键字段

    返回:
        (字段字典, 置信度, 警告列表)
    """
    fields: Dict[str, str] = {}
    warnings: List[str] = []
    matched_count = 0
    total_patterns = len(KEY_FIELD_PATTERNS)

    for field_name, pattern in KEY_FIELD_PATTERNS.items():
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            value = match.group(1).strip()
            if value:
                fields[field_name] = value
                matched_count += 1

    # 计算置信度：基础0.5 + 每个匹配字段增加0.1，上限0.95
    # 如果没有匹配到任何字段，给予最低置信度
    if matched_count == 0:
        confidence = MIN_CONFIDENCE
        warnings.append("未识别到关键字段，置信度极低")
    else:
        confidence = min(0.5 + matched_count * 0.1, 0.95)

    # 检查内容长度（过短内容置信度降低）
    if len(content.strip()) < 20:
        confidence = max(MIN_CONFIDENCE, confidence - 0.2)
        warnings.append("输入内容过短，可能影响识别准确性")

    # 检查是否有"不确定"字样
    uncertain_patterns = ["不确定", "可能", "大概", "估计", "猜测"]
    if any(word in content for word in uncertain_patterns):
        confidence = max(MIN_CONFIDENCE, confidence - 0.15)
        warnings.append("输入中包含不确定性表述，置信度已下调")

    return fields, confidence, warnings


def _format_text(result: ProcessResult) -> Dict[str, Any]:
    """将结果格式化为文本形式"""
    lines = []
    lines.append("=" * 50)
    lines.append(f"处理结果 (置信度: {result.confidence:.0%})")
    lines.append("=" * 50)

    for field, value in result.data["fields"].items():
        lines.append(f"{field}: {value}")

    if result.warnings:
        lines.append("\n警告:")
        for w in result.warnings:
            lines.append(f"  - {w}")

    lines.append("\n置信度等级: " + result._confidence_level())
    lines.append("=" * 50)

    return {
        "success": True,
        "text": "\n".join(lines),
        "confidence": result.confidence,
        "warnings": result.warnings,
    }


def _truncate(text: str, length: int) -> str:
    """截断文本并添加省略号"""
    if len(text) <= length:
        return text
    return text[:length] + "..."


# ------------------------------------------------------------
# 批量处理
# ------------------------------------------------------------
def batch_process(inputs: List[str]) -> List[Dict[str, Any]]:
    """批量处理多个输入"""
    results = []
    for item in inputs:
        try:
            result = process_input(item)
            results.append(result)
        except SkillError as e:
            results.append({
                "success": False,
                "error_code": e.code,
                "error_message": e.message,
                "input": item[:50] + "..." if len(item) > 50 else item,
            })
    return results


# ------------------------------------------------------------
# 自检逻辑
# ------------------------------------------------------------
def run_selftest() -> bool:
    """
    内置自检：使用样例数据验证核心逻辑

    返回:
        True 通过，False 失败
    """
    print("=" * 60)
    print(f"{SKILL_NAME} v{SKILL_VERSION} 自检开始")
    print("=" * 60)

    tests_passed = 0
    tests_failed = 0

    # 测试用例1: 正常文本输入
    print("\n[测试1] 正常文本输入")
    sample1 = "标题：项目计划书\n作者：张三\n日期：2024-03-15\n关键词：规划,管理,执行\n摘要：本项目计划书旨在明确季度目标与执行方案。"
    try:
        result = process_input(sample1)
        assert result["success"] == True, "处理失败"
        assert "标题" in result["data"]["fields"], "缺少标题字段"
        assert result["confidence"] >= 0.8, f"置信度异常: {result['confidence']}"
        print("  ✓ 通过 - 结构化结果:", json.dumps(result["data"]["fields"], ensure_ascii=False))
        tests_passed += 1
    except AssertionError as e:
        print(f"  ✗ 失败: {e}")
        tests_failed += 1
    except SkillError as e:
        print(f"  ✗ 失败: 错误码 {e.code} - {e.message}")
        tests_failed += 1

    # 测试用例2: 空输入
    print("\n[测试2] 空输入处理")
    try:
        process_input("")
        print("  ✗ 失败: 未抛出 E001 错误")
        tests_failed += 1
    except SkillError as e:
        if e.code == "E001":
            print(f"  ✓ 通过 - 正确抛出 E001: {e.message}")
            tests_passed += 1
        else:
            print(f"  ✗ 失败: 错误码错误，期望 E001，实际 {e.code}")
            tests_failed += 1

    # 测试用例3: 文件输入
    print("\n[测试3] 文件输入处理")
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
        f.write("标题：测试文档\n作者：李四\n日期：2024-01-01\n内容：这是一个测试文件的内容。")
        temp_file = f.name
    try:
        result = process_input(temp_file)
        assert result["success"] == True, "文件处理失败"
        assert result["data"]["source_type"] == "file:.txt", "来源类型错误"
        print(f"  ✓ 通过 - 文件内容已解析: {result['data']['fields'].get('标题', 'N/A')}")
        tests_passed += 1
    except (AssertionError, SkillError) as e:
        print(f"  ✗ 失败: {e}")
        tests_failed += 1
    finally:
        os.unlink(temp_file)

    # 测试用例4: URL 输入（应拒绝）
    print("\n[测试4] URL 输入（边界检查）")
    try:
        process_input("https://example.com/page")
        print("  ✗ 失败: 未拒绝 URL 输入")
        tests_failed += 1
    except SkillError as e:
        if e.code == "E004":
            print(f"  ✓ 通过 - 正确拒绝 URL: {e.message}")
            tests_passed += 1
        else:
            print(f"  ✗ 失败: 错误码错误，期望 E004，实际 {e.code}")
            tests_failed += 1

    # 测试用例5: 低置信度标注
    print("\n[测试5] 低置信度标注")
    sample5 = "可能是一个测试，不确定内容"
    try:
        result = process_input(sample5)
        assert result["confidence"] < 0.85, f"置信度应低于0.85，实际 {result['confidence']}"
        assert any("需核实" in w for w in result["warnings"]), "缺少需核实标注"
        print(f"  ✓ 通过 - 置信度 {result['confidence']:.0%}，已标注需核实")
        tests_passed += 1
    except (AssertionError, SkillError) as e:
        print(f"  ✗ 失败: {e}")
        tests_failed += 1

    # 测试用例6: 批量处理
    print("\n[测试6] 批量处理")
    batch_inputs = [
        "标题：文档A\n作者：王五\n日期：2024-02-01",
        "",  # 空输入
        "标题：文档B\n作者：赵六\n日期：2024-02-15",
    ]
    try:
        results = batch_process(batch_inputs)
        assert len(results) == 3, "批量处理数量错误"
        assert results[0]["success"] == True, "第一条应成功"
        assert results[1]["success"] == False and results[1]["error_code"] == "E001", "第二条应失败 E001"
        assert results[2]["success"] == True, "第三条应成功"
        print(f"  ✓ 通过 - 成功 {sum(1 for r in results if r['success'])} 个，失败 {sum(1 for r in results if not r['success'])} 个")
        tests_passed += 1
    except (AssertionError, SkillError) as e:
        print(f"  ✗ 失败: {e}")
        tests_failed += 1

    # 汇总
    print("\n" + "=" * 60)
    print(f"自检完成: {tests_passed} 通过, {tests_failed} 失败")
    print("=" * 60)

    if tests_failed > 0:
        raise SkillError("E010", f"自检失败: {tests_failed} 个测试未通过")

    return True


# ------------------------------------------------------------
# 命令行入口
# ------------------------------------------------------------
def main() -> int:
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description=f"{SKILL_NAME} - 将数据/文件转换为结构化结果",
        epilog="示例: python main.py --input '标题：测试' --format json",
    )
    parser.add_argument("--input", "-i", help="输入内容（文本或文件路径）")
    parser.add_argument("--file", "-f", help="输入文件路径（与 --input 二选一）")
    parser.add_argument("--format", "-t", choices=["json", "text"], default="json", help="输出格式")
    parser.add_argument("--batch", "-b", nargs="+", help="批量处理多个输入")
    parser.add_argument("--selftest", action="store_true", help="运行自检并退出")
    parser.add_argument("--version", "-v", action="version", version=f"{SKILL_NAME} v{SKILL_VERSION}")

    try:
        args = parser.parse_args()
    except SystemExit as e:
        # argparse 在 -h 时正常退出，在参数错误时返回非零
        if e.code != 0:
            raise SkillError("E006", f"参数解析失败: {e}")
        raise

    # 自检模式
    if args.selftest:
        try:
            run_selftest()
            return 0
        except SkillError as e:
            print(f"错误 [{e.code}]: {e.message}")
            return 1

    # 批量模式
    if args.batch:
        try:
            results = batch_process(args.batch)
            print(json.dumps(results, ensure_ascii=False, indent=2))
            return 0
        except SkillError as e:
            print(f"错误 [{e.code}]: {e.message}")
            return 1

    # 单条处理模式
    input_content = args.input or args.file

    # E001: 无输入且非自检模式
    if not input_content:
        print("错误 [E001]: 请提供待处理的内容，格式为：用户提供的数据/文件/URL")
        print("提示: 使用 --input 或 --file 参数，或使用 --selftest 运行自检")
        return 1

    try:
        result = process_input(input_content, args.format)
        if args.format == "text":
            print(result.get("text", ""))
        else:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except SkillError as e:
        print(f"错误 [{e.code}]: {e.message}")
        return 1
    except Exception as e:
        print(f"错误 [E009]: 内部处理异常: {e}")
        return 1


# ------------------------------------------------------------
# 入口
# ------------------------------------------------------------
if __name__ == "__main__":
    sys.exit(main())
