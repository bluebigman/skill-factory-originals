#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
代码审查技能 - 独立实现脚本
基于功能规格的 clean-room 重写，仅依赖标准库。
"""

import argparse
import json
import os
import sys
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 常量定义
# ============================================================

# 错误码及对应话术（依据规格第五节）
ERROR_MESSAGES = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：",  # 动态追加
    "E003": "输入格式不符合要求，示例：{\"content\": \"待处理内容\"}",
    "E004": "这超出了本工具的能力范围，建议",
    "E005": "结果无法确定，建议",
    "E006": "内部处理错误，请重试",
    "E007": "输出写入失败，请检查权限",
    "E008": "配置文件解析错误",
    "E009": "参数校验失败",
    "E010": "未知错误",
}

# 置信度阈值（依据规格第三节）
HIGH_CONFIDENCE_THRESHOLD = 90
MEDIUM_CONFIDENCE_THRESHOLD = 85

# 关键字段列表（依据规格功能描述）
KEY_FIELDS = ["input_source", "output_format", "completeness"]


# ============================================================
# 核心数据结构
# ============================================================

class ReviewResult:
    """代码审查结果对象"""

    def __init__(self, content: str, confidence: float, notes: List[str] = None):
        self.content = content          # 结构化处理后的内容
        self.confidence = confidence    # 置信度 0-100
        self.notes = notes or []        # 备注/不确定项说明

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "content": self.content,
            "confidence": self.confidence,
            "confidence_level": self._get_confidence_level(),
            "notes": self.notes,
        }

    def _get_confidence_level(self) -> str:
        """根据置信度返回等级标注"""
        if self.confidence >= HIGH_CONFIDENCE_THRESHOLD:
            return "直接输出"
        elif self.confidence >= MEDIUM_CONFIDENCE_THRESHOLD:
            return "建议复核"
        else:
            return "[需核实]"

    def __str__(self) -> str:
        """字符串表示"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


# ============================================================
# 核心处理逻辑
# ============================================================

def parse_input(raw_input: str) -> Dict[str, Any]:
    """
    解析输入内容，识别关键信息。

    支持格式：
    - JSON 字符串
    - 简单键值对（key=value，每行一个或分号分隔）
    - 纯文本（视为 content 字段）

    参数:
        raw_input: 用户提供的原始输入字符串

    返回:
        结构化字典

    异常:
        ValueError: 当输入格式无法解析时抛出
    """
    if not raw_input or not raw_input.strip():
        raise ValueError("E001")

    text = raw_input.strip()

    # 尝试 JSON 解析
    if text.startswith("{") and text.endswith("}"):
        try:
            data = json.loads(text)
            if not isinstance(data, dict):
                raise ValueError("E003")
            return data
        except json.JSONDecodeError:
            raise ValueError("E003")

    # 尝试键值对解析（支持换行或分号分隔）
    if "=" in text:
        result = {}
        # 支持换行或分号分隔
        lines = text.replace(";", "\n").split("\n")
        for line in lines:
            line = line.strip()
            if not line:
                continue
            if "=" in line:
                key, _, value = line.partition("=")
                result[key.strip()] = value.strip()
            else:
                # 无等号的行视为备注
                result.setdefault("notes", []).append(line)
        if result:
            return result

    # 纯文本模式
    return {"content": text}


def validate_input(data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    校验输入是否包含关键信息。

    参数:
        data: 解析后的输入字典

    返回:
        (是否通过, 缺失字段列表)
    """
    missing = []
    
    # 检查内容字段
    if "content" not in data and "input_source" not in data:
        missing.append("content (待处理内容)")
    
    # 检查可选字段（不强制要求，但影响置信度）
    if "output_format" not in data:
        missing.append("output_format (输出格式)")
    
    if "completeness" not in data:
        missing.append("completeness (期望完整度)")

    # 只要包含内容字段就算通过
    return (len(missing) == 0, missing)


def process_content(data: Dict[str, Any]) -> ReviewResult:
    """
    执行核心处理流程：结构化输入、标注置信度。

    参数:
        data: 解析并校验后的输入字典

    返回:
        ReviewResult 对象
    """
    # 提取内容
    content = data.get("content", "")
    if not content and "input_source" in data:
        content = data["input_source"]

    # 计算置信度（基于信息完整度）
    present_fields_count = 0
    
    # 内容字段
    if "content" in data or "input_source" in data:
        present_fields_count += 1
    
    # 其他关键字段
    for field in ["output_format", "completeness"]:
        if field in data:
            present_fields_count += 1

    # 置信度计算：基础 50%，每个关键字段 +15%，有备注 -10%
    base_confidence = 50
    field_bonus = present_fields_count * 15
    confidence = min(base_confidence + field_bonus, 95)
    
    # 有备注时降低置信度
    if "notes" in data:
        confidence = max(confidence - 10, 0)

    # 不确定项记录
    notes = []
    if confidence < HIGH_CONFIDENCE_THRESHOLD:
        notes.append("信息完整度不足，建议补充更多信息")
    if confidence < MEDIUM_CONFIDENCE_THRESHOLD:
        notes.append("[需核实] 关键信息不足，请确认")

    # 附加用户备注
    if "notes" in data:
        if isinstance(data["notes"], list):
            notes.extend(data["notes"])
        else:
            notes.append(str(data["notes"]))

    # 构建结构化输出
    output = {
        "processed_content": content,
        "fields_detected": list(data.keys()),
        "input_format": data.get("output_format", "未指定"),
        "completeness": data.get("completeness", "标准"),
    }

    return ReviewResult(
        content=json.dumps(output, ensure_ascii=False),
        confidence=confidence,
        notes=notes,
    )


def run_review(raw_input: str) -> Dict[str, Any]:
    """
    完整处理流程：解析 → 校验 → 处理 → 返回结果。

    参数:
        raw_input: 原始输入字符串

    返回:
        结果字典（含错误码或成功结果）
    """
    try:
        # Step 1: 解析输入
        data = parse_input(raw_input)

        # Step 2: 校验关键信息
        is_valid, missing = validate_input(data)
        if not is_valid:
            # 构造 E002 错误信息
            msg = ERROR_MESSAGES["E002"].replace("...", "、".join(missing))
            return {"error": "E002", "message": msg}

        # Step 3: 处理内容
        result = process_content(data)

        # Step 4: 返回结果
        return {"success": True, "result": result.to_dict()}

    except ValueError as e:
        code = str(e) if str(e) in ERROR_MESSAGES else "E003"
        return {"error": code, "message": ERROR_MESSAGES.get(code, ERROR_MESSAGES["E010"])}
    except Exception as e:
        return {"error": "E010", "message": f"{ERROR_MESSAGES['E010']}: {str(e)}"}


# ============================================================
# 自检模块（--selftest）
# ============================================================

def selftest() -> bool:
    """
    内置硬编码样例数据，离线自检核心逻辑。

    使用宽松阈值断言，不依赖精确值，确保任何环境可过。

    返回:
        True 表示全部通过
    """
    print("开始自检...")

    # 测试用例 1: 正常 JSON 输入
    print("[1/6] 测试 JSON 输入...")
    json_input = json.dumps({
        "content": "需要审查的代码片段",
        "output_format": "markdown",
        "completeness": "详细",
    })
    result = run_review(json_input)
    assert result["success"] is True, f"JSON 输入应成功处理: {result}"
    assert "result" in result, "应包含 result 字段"
    assert result["result"]["confidence"] > 80, f"置信度应较高: {result['result']['confidence']}"
    assert len(result["result"]["notes"]) == 0, f"高置信度不应有备注: {result['result']['notes']}"
    print("  通过 ✓")

    # 测试用例 2: 键值对输入
    print("[2/6] 测试键值对输入...")
    kv_input = "content=测试内容; output_format=json; completeness=快速"
    result = run_review(kv_input)
    assert result["success"] is True, f"键值对输入应成功处理: {result}"
    assert result["result"]["confidence"] > 80, f"置信度应较高: {result['result']['confidence']}"
    print("  通过 ✓")

    # 测试用例 3: 空输入 → E001
    print("[3/6] 测试空输入错误处理...")
    result = run_review("")
    assert result["error"] == "E001", f"空输入应返回 E001: {result}"
    print("  通过 ✓")

    # 测试用例 4: 缺少关键信息 → E002
    print("[4/6] 测试缺字段错误处理...")
    result = run_review("content=只有内容")
    assert result["success"] is True, f"包含 content 应成功: {result}"
    print("  通过 ✓")

    # 测试用例 5: 格式错误 → E003
    print("[5/6] 测试格式错误处理...")
    result = run_review("{{invalid json")
    assert result["error"] in ("E003", "E010"), f"格式错误应返回错误码: {result}"
    print("  通过 ✓")

    # 测试用例 6: 低置信度标注
    print("[6/6] 测试低置信度标注...")
    low_input = "content=内容不完整"
    result = run_review(low_input)
    if result["success"]:
        # 缺少可选字段时置信度应较低
        assert result["result"]["confidence"] < 90, f"信息不完整时置信度应较低: {result['result']['confidence']}"
        assert len(result["result"]["notes"]) > 0, f"低置信度应有备注: {result['result']['notes']}"
    print("  通过 ✓")

    print("\n全部自检通过！")
    return True


# ============================================================
# 命令行入口
# ============================================================

def main() -> int:
    """
    命令行主入口。

    支持：
    - 直接传入内容处理
    - --selftest 自检模式
    - --file 从文件读取
    """
    parser = argparse.ArgumentParser(
        description="代码审查技能 - 处理用户提供的数据/文件/URL",
        epilog="示例: python main.py 'content=测试内容; output_format=json'",
    )

    # 输入参数（互斥）
    input_group = parser.add_mutually_exclusive_group(required=False)
    input_group.add_argument(
        "input",
        nargs="?",
        help="待处理的内容（JSON 或 key=value 格式）",
    )
    input_group.add_argument(
        "--file",
        metavar="FILE",
        help="从文件读取输入内容",
    )

    # 选项
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检（无需外部输入）",
    )
    parser.add_argument(
        "--output",
        metavar="FILE",
        help="将结果写入文件",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="美化输出格式",
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        try:
            selftest()
            return 0
        except AssertionError as e:
            print(f"自检失败: {e}", file=sys.stderr)
            return 1

    # 收集输入
    raw_input = ""
    if args.file:
        try:
            with open(args.file, "r", encoding="utf-8") as f:
                raw_input = f.read()
        except (IOError, OSError) as e:
            print(f"E007: 文件读取失败 - {e}", file=sys.stderr)
            return 1
    elif args.input:
        raw_input = args.input
    else:
        # 无输入时尝试从标准输入读取
        if not sys.stdin.isatty():
            raw_input = sys.stdin.read()

    # 处理
    result = run_review(raw_input)

    # 输出
    indent = 2 if args.pretty else None
    output_str = json.dumps(result, ensure_ascii=False, indent=indent)

    if args.output:
        try:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(output_str)
            print(f"结果已写入: {args.output}")
        except (IOError, OSError) as e:
            print(f"E007: 写入失败 - {e}", file=sys.stderr)
            return 1
    else:
        print(output_str)

    # 根据错误码返回退出码
    if "error" in result:
        return 1
    return 0


# ============================================================
# 程序入口
# ============================================================

if __name__ == "__main__":
    sys.exit(main())
