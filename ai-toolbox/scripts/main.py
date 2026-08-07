#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ai-toolbox 技能实现脚本
========================
依据功能规格独立实现（clean-room），提供核心处理能力：
- 输入解析与关键信息提取
- 结构化输出生成
- 置信度评估与标注
- 批量处理支持
- 离线自检（--selftest）

错误码体系：
    E001 输入为空
    E002 关键信息缺失
    E003 输入格式错误
    E004 超出能力边界
    E005 置信度过低
    E006 参数错误
    E007 文件读取失败
    E008 输出写入失败
    E009 内部逻辑错误
    E010 未支持的输入类型

仅使用 Python 标准库，无第三方依赖。
"""

import argparse
import json
import sys
import os
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 常量定义
# ============================================================

# 版本信息
VERSION = "1.0.0"
SKILL_NAME = "ai-toolbox"
SKILL_DISPLAY_NAME = "未命名工具"

# 置信度阈值
HIGH_CONFIDENCE = 0.90      # ≥90% 直接输出
MEDIUM_CONFIDENCE = 0.85    # 85%-90% 建议复核
LOW_CONFIDENCE = 0.0        # <85% 标注需核实

# 支持的关键字段（默认模板）
DEFAULT_FIELDS = ["title", "content", "tags", "source", "timestamp"]

# 输入类型
INPUT_TYPE_TEXT = "text"
INPUT_TYPE_JSON = "json"
INPUT_TYPE_FILE = "file"
INPUT_TYPE_URL = "url"


# ============================================================
# 错误处理模块
# ============================================================

class ToolboxError(Exception):
    """技能自定义异常，携带错误码。"""
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"[{code}] {message}")


def error_message(code: str) -> str:
    """根据错误码返回标准化话术。"""
    messages = {
        "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
        "E002": "还缺少以下信息，请补充：...",
        "E003": "输入格式不符合要求，示例：...",
        "E004": "这超出了本工具的能力范围，建议...",
        "E005": "结果无法确定，建议：...",
        "E006": "参数错误，请检查命令行参数。",
        "E007": "文件读取失败，请检查文件路径和权限。",
        "E008": "输出写入失败，请检查目标目录权限。",
        "E009": "内部逻辑错误，请联系开发者。",
        "E010": "暂不支持的输入类型，请提供文本、JSON或文件路径。",
    }
    return messages.get(code, "未知错误")


# ============================================================
# 核心处理模块
# ============================================================

def validate_input(data: Any) -> None:
    """Step 1 校验：输入不能为空。"""
    if data is None:
        raise ToolboxError("E001", error_message("E001"))
    if isinstance(data, str) and not data.strip():
        raise ToolboxError("E001", error_message("E001"))
    if isinstance(data, (list, dict)) and len(data) == 0:
        raise ToolboxError("E001", error_message("E001"))


def parse_input(raw_input: str) -> Tuple[str, Any]:
    """
    解析输入内容，识别输入类型。
    返回 (输入类型, 解析后的数据)。
    """
    if raw_input is None:
        raise ToolboxError("E001", error_message("E001"))

    raw_input = raw_input.strip()
    if not raw_input:
        raise ToolboxError("E001", error_message("E001"))

    # 尝试解析 JSON
    if raw_input.startswith(("{", "[")):
        try:
            data = json.loads(raw_input)
            return INPUT_TYPE_JSON, data
        except json.JSONDecodeError:
            # 不是合法 JSON，按文本处理
            pass

    # 检查是否为文件路径
    if os.path.isfile(raw_input):
        try:
            with open(raw_input, "r", encoding="utf-8") as f:
                content = f.read().strip()
            if not content:
                raise ToolboxError("E001", error_message("E001"))
            # 文件内容可能是 JSON 或纯文本
            if content.startswith(("{", "[")):
                try:
                    data = json.loads(content)
                    return INPUT_TYPE_FILE, data
                except json.JSONDecodeError:
                    pass
            return INPUT_TYPE_FILE, content
        except OSError:
            raise ToolboxError("E007", error_message("E007"))

    # 检查是否为 URL（仅识别格式，不访问网络）
    if raw_input.startswith(("http://", "https://")):
        # 边界声明：不访问网络，仅识别格式
        return INPUT_TYPE_URL, raw_input

    # 默认按文本处理
    return INPUT_TYPE_TEXT, raw_input


def extract_key_info(data: Any) -> Dict[str, Any]:
    """
    Step 2 核心流程：识别输入中的关键信息并结构化。
    """
    result: Dict[str, Any] = {}

    if isinstance(data, dict):
        # 字典输入：直接提取已知字段
        for field in DEFAULT_FIELDS:
            if field in data:
                result[field] = data[field]
        # 保留其他自定义字段
        for key, value in data.items():
            if key not in result:
                result[key] = value

    elif isinstance(data, list):
        # 列表输入：批量处理
        result["batch_items"] = []
        for item in data:
            if isinstance(item, dict):
                result["batch_items"].append(extract_key_info(item))
            else:
                result["batch_items"].append({"content": str(item)})
        result["batch_count"] = len(data)

    elif isinstance(data, str):
        # 文本输入：提取基本信息
        result["content"] = data
        result["length"] = len(data)
        # 简单标签提取：查找 #标签 格式
        tags = [word.strip("#") for word in data.split() if word.startswith("#")]
        if tags:
            result["tags"] = tags

    else:
        raise ToolboxError("E010", error_message("E010"))

    return result


def calculate_confidence(data: Any, extracted: Dict[str, Any]) -> float:
    """
    计算置信度（0.0 - 1.0）。
    规则：
    - 结构化数据（字典）且有明确字段：高置信度
    - 文本数据：根据长度和标签提取情况
    - 批量数据：根据完整率
    """
    if isinstance(data, dict):
        # 字典输入：字段覆盖率越高，置信度越高
        if not data:
            return 0.0
        known_fields = [f for f in DEFAULT_FIELDS if f in data]
        coverage = len(known_fields) / len(DEFAULT_FIELDS)
        # 基础 0.7 + 覆盖率加成，最高 0.98
        confidence = min(0.7 + coverage * 0.28, 0.98)
        return round(confidence, 2)

    elif isinstance(data, list):
        # 列表输入：根据成功解析比例
        if not data:
            return 0.0
        valid_items = sum(1 for item in data if item is not None and str(item).strip())
        ratio = valid_items / len(data)
        return round(0.5 + ratio * 0.45, 2)

    elif isinstance(data, str):
        # 文本输入
        if len(data) < 10:
            return 0.6  # 短文本，信息量少
        has_tags = "tags" in extracted
        has_content = len(data) > 50
        score = 0.7
        if has_tags:
            score += 0.1
        if has_content:
            score += 0.1
        return round(min(score, 0.95), 2)

    return 0.5


def format_output(data: Any, extracted: Dict[str, Any], confidence: float) -> Dict[str, Any]:
    """
    Step 3 输出与校验：生成带置信度标注的结构化结果。
    """
    result = {
        "skill": SKILL_NAME,
        "version": VERSION,
        "success": True,
        "confidence": confidence,
        "confidence_label": get_confidence_label(confidence),
        "data": extracted,
    }

    # 低置信度标注
    if confidence < LOW_CONFIDENCE:
        result["warning"] = "[需核实] 结果置信度过低，请人工复核关键信息"

    return result


def get_confidence_label(confidence: float) -> str:
    """根据置信度返回标注标签。"""
    if confidence >= HIGH_CONFIDENCE:
        return "直接输出"
    elif confidence >= MEDIUM_CONFIDENCE:
        return "建议复核"
    else:
        return "[需核实]"


def process_input(raw_input: str) -> Dict[str, Any]:
    """
    标准处理流程（Step 1 → Step 2 → Step 3）。
    """
    # Step 1: 解析输入
    input_type, data = parse_input(raw_input)
    validate_input(data)

    # 边界检查：URL 类型不访问网络
    if input_type == INPUT_TYPE_URL:
        # 仅识别格式，不实际访问
        extracted = {
            "url": data,
            "note": "URL 已识别，但本工具不访问网络，请提供内容或文件。"
        }
        confidence = 0.85  # 格式识别置信度
        return format_output(data, extracted, confidence)

    # Step 2: 提取关键信息
    extracted = extract_key_info(data)

    # 计算置信度
    confidence = calculate_confidence(data, extracted)

    # Step 3: 格式化输出
    return format_output(data, extracted, confidence)


def batch_process(inputs: List[str]) -> Dict[str, Any]:
    """
    批量处理多个输入。
    """
    results = []
    for raw_input in inputs:
        try:
            result = process_input(raw_input)
            results.append(result)
        except ToolboxError as e:
            results.append({
                "success": False,
                "error_code": e.code,
                "error_message": e.message,
            })

    return {
        "skill": SKILL_NAME,
        "version": VERSION,
        "success": True,
        "batch": True,
        "total": len(inputs),
        "success_count": sum(1 for r in results if r.get("success")),
        "results": results,
    }


# ============================================================
# 自检模块（--selftest）
# ============================================================

def run_selftest() -> bool:
    """
    内置硬编码样例数据离线自检。
    不读外部文件、不依赖当前工作目录、不访问网络。
    """
    print("=" * 60)
    print("ai-toolbox 自检开始")
    print("=" * 60)

    all_passed = True

    # --- 测试用例 1: 正常文本输入 ---
    print("\n[测试 1] 文本输入处理")
    try:
        text_input = "这是一段测试文本，包含 #重要 和 #紧急 两个标签，用于验证文本处理功能。"
        result = process_input(text_input)
        assert result["success"] is True, "文本处理应成功"
        assert "content" in result["data"], "应提取到内容"
        assert "tags" in result["data"], "应提取到标签"
        assert result["confidence"] > 0.5, "置信度应大于 0.5"
        print("  ✓ 文本输入处理正常")
        print(f"    置信度: {result['confidence']}, 标签: {result['data'].get('tags')}")
    except Exception as e:
        all_passed = False
        print(f"  ✗ 文本输入处理失败: {e}")

    # --- 测试用例 2: JSON 输入 ---
    print("\n[测试 2] JSON 输入处理")
    try:
        json_input = '{"title": "测试标题", "content": "测试内容", "tags": ["测试"]}'
        result = process_input(json_input)
        assert result["success"] is True, "JSON 处理应成功"
        assert result["data"].get("title") == "测试标题", "应提取到 title 字段"
        assert result["confidence"] >= 0.7, "结构化数据置信度应较高"
        print("  ✓ JSON 输入处理正常")
        print(f"    置信度: {result['confidence']}, 标题: {result['data'].get('title')}")
    except Exception as e:
        all_passed = False
        print(f"  ✗ JSON 输入处理失败: {e}")

    # --- 测试用例 3: 空输入错误处理 ---
    print("\n[测试 3] 空输入错误处理")
    try:
        process_input("")
        all_passed = False
        print("  ✗ 空输入应抛出 E001 错误")
    except ToolboxError as e:
        assert e.code == "E001", f"错误码应为 E001，实际为 {e.code}"
        print("  ✓ 空输入正确抛出 E001")
    except Exception as e:
        all_passed = False
        print(f"  ✗ 空输入处理异常: {e}")

    # --- 测试用例 4: 批量处理 ---
    print("\n[测试 4] 批量处理")
    try:
        batch_inputs = ["第一条测试内容", '{"key": "value"}', ""]
        result = batch_process(batch_inputs)
        assert result["success"] is True, "批量处理应成功"
        assert result["total"] == 3, f"总数应为 3，实际为 {result['total']}"
        assert result["success_count"] >= 2, "至少 2 条应处理成功"
        print(f"  ✓ 批量处理正常（成功 {result['success_count']}/{result['total']}）")
    except Exception as e:
        all_passed = False
        print(f"  ✗ 批量处理失败: {e}")

    # --- 测试用例 5: 置信度阈值 ---
    print("\n[测试 5] 置信度计算")
    try:
        # 结构化数据置信度应较高
        struct_data = {"title": "t", "content": "c", "tags": ["a"]}
        struct_conf = calculate_confidence(struct_data, extract_key_info(struct_data))
        assert struct_conf >= 0.7, f"结构化数据置信度应 >= 0.7，实际为 {struct_conf}"

        # 短文本置信度应较低
        short_text = "短"
        short_conf = calculate_confidence(short_text, extract_key_info(short_text))
        assert short_conf < struct_conf, "短文本置信度应低于结构化数据"

        print(f"  ✓ 置信度计算正常（结构化: {struct_conf}, 短文本: {short_conf}）")
    except Exception as e:
        all_passed = False
        print(f"  ✗ 置信度计算失败: {e}")

    # --- 测试用例 6: URL 输入边界 ---
    print("\n[测试 6] URL 输入边界处理")
    try:
        url_input = "https://example.com/some/page"
        result = process_input(url_input)
        assert result["success"] is True, "URL 识别应成功"
        assert "url" in result["data"], "应识别出 URL"
        assert "note" in result["data"], "应包含边界说明"
        print("  ✓ URL 边界处理正常（不访问网络）")
    except Exception as e:
        all_passed = False
        print(f"  ✗ URL 边界处理失败: {e}")

    # --- 测试用例 7: 错误码体系 ---
    print("\n[测试 7] 错误码体系")
    try:
        error_codes = ["E001", "E002", "E003", "E004", "E005"]
        for code in error_codes:
            msg = error_message(code)
            assert msg and len(msg) > 0, f"错误码 {code} 应有对应话术"
        print("  ✓ 错误码话术完整")
    except Exception as e:
        all_passed = False
        print(f"  ✗ 错误码检查失败: {e}")

    # --- 总结 ---
    print("\n" + "=" * 60)
    if all_passed:
        print("自检全部通过 ✓")
    else:
        print("自检存在失败项 ✗")
    print("=" * 60)

    return all_passed


# ============================================================
# 命令行入口
# ============================================================

def main() -> int:
    """命令行主入口。"""
    parser = argparse.ArgumentParser(
        description=f"{SKILL_DISPLAY_NAME} (ai-toolbox v{VERSION}) - AI 工作流自动化处理工具",
        epilog="示例: python main.py '要处理的文本' | python main.py --batch '输入1' '输入2'"
    )

    parser.add_argument(
        "input",
        nargs="*",
        help="待处理的内容（文本、JSON、文件路径或 URL），支持多个输入（自动批量处理）"
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置离线自检（不读取外部文件、不访问网络）"
    )
    parser.add_argument(
        "--version",
        action="store_true",
        help="显示版本信息"
    )
    parser.add_argument(
        "--json-output",
        action="store_true",
        help="以 JSON 格式输出结果"
    )

    args = parser.parse_args()

    # 版本信息
    if args.version:
        print(f"ai-toolbox v{VERSION}")
        return 0

    # 自检模式
    if args.selftest:
        success = run_selftest()
        return 0 if success else 1

    # 无输入参数
    if not args.input:
        parser.print_help()
        print("\n错误: 请提供待处理的内容。", file=sys.stderr)
        print(f"提示: {error_message('E001')}", file=sys.stderr)
        return 1

    try:
        # 单个输入
        if len(args.input) == 1:
            result = process_input(args.input[0])
        # 多个输入 → 批量处理
        else:
            result = batch_process(args.input)

        # 输出
        if args.json_output:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            # 人类可读输出
            if result.get("batch"):
                print(f"批量处理完成: {result['success_count']}/{result['total']} 成功")
                for i, r in enumerate(result["results"], 1):
                    status = "✓" if r.get("success") else "✗"
                    print(f"  {status} [{i}] ", end="")
                    if r.get("success"):
                        print(f"置信度 {r['confidence']} ({r['confidence_label']})")
                    else:
                        print(f"错误 {r.get('error_code')}: {r.get('error_message')}")
            else:
                print(f"处理完成: 置信度 {result['confidence']} ({result['confidence_label']})")
                if "warning" in result:
                    print(f"警告: {result['warning']}")
                if "data" in result:
                    for key, value in result["data"].items():
                        print(f"  {key}: {value}")

        return 0

    except ToolboxError as e:
        print(f"处理失败 [{e.code}]: {e.message}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"未预期错误: {e}", file=sys.stderr)
        print(f"提示: {error_message('E009')}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
