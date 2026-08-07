#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
github-datasource 技能实现脚本（独立实现，clean-room 重写）

功能概述：
    将用户提供的数据/文件/URL 转换为结构化结果，识别关键信息，
    按约定格式输出，并对不确定项给出置信度提示。

仅依据功能规格设计，未参考或复制任何既有代码。
标准库实现，无第三方依赖。
"""

import argparse
import json
import os
import re
import sys
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 错误码定义（E001-E010）
# ============================================================
ERROR_CODES = {
    "E001": "输入为空",
    "E002": "关键信息缺失",
    "E003": "输入格式错误",
    "E004": "超出能力边界",
    "E005": "置信度过低",
    "E006": "内部处理异常",
    "E007": "参数校验失败",
    "E008": "文件读取失败",
    "E009": "URL 解析失败",
    "E010": "输出生成失败",
}

# 标准话术模板
ERROR_MESSAGES = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：{details}",
    "E003": "输入格式不符合要求，示例：{details}",
    "E004": "这超出了本工具的能力范围，建议：{details}",
    "E005": "结果无法确定，建议：{details}",
    "E006": "内部处理异常，请稍后重试",
    "E007": "参数校验失败：{details}",
    "E008": "文件读取失败：{details}",
    "E009": "URL 解析失败：{details}",
    "E010": "输出生成失败：{details}",
}


class SkillError(Exception):
    """技能异常基类，携带错误码"""

    def __init__(self, code: str, details: str = ""):
        self.code = code
        self.details = details
        message = ERROR_MESSAGES.get(code, "未知错误")
        if details:
            message = message.format(details=details)
        super().__init__(f"[{code}] {message}")


# ============================================================
# 核心处理逻辑
# ============================================================

# 关键字段识别正则（用于从文本中提取结构化信息）
_FIELD_PATTERNS = {
    "name": re.compile(r"(?:名称|名字|name)\s*[：:]\s*([^\s,，;；]+)"),
    "count": re.compile(r"(?:数量|个数|count)\s*[：:]\s*(\d+)"),
    "date": re.compile(r"(?:日期|时间|date)\s*[：:]\s*(\d{4}[-/]\d{2}[-/]\d{2})"),
    "url": re.compile(r"(?:链接|地址|url)\s*[：:]\s*(https?://\S+)"),
    "type": re.compile(r"(?:类型|类别|type)\s*[：:]\s*([^\s,，;；]+)"),
}


def validate_input(raw_input: Any) -> str:
    """
    校验输入内容，返回标准化文本。
    对应错误码：E001（输入为空）、E003（输入格式错误）
    
    宽松模式：接受任何类型的输入，尽量转换为文本
    """
    if raw_input is None:
        raise SkillError("E001")

    # 将各种类型转换为文本
    if isinstance(raw_input, (dict, list)):
        text = json.dumps(raw_input, ensure_ascii=False)
    elif isinstance(raw_input, bytes):
        try:
            text = raw_input.decode("utf-8")
        except UnicodeDecodeError:
            raise SkillError("E003", "内容编码不是 UTF-8")
    elif isinstance(raw_input, (str, int, float, bool)):
        text = str(raw_input).strip()
    else:
        # 其他类型尝试转换为字符串
        try:
            text = str(raw_input).strip()
        except Exception:
            raise SkillError("E003", f"无法转换的输入类型: {type(raw_input).__name__}")

    # 空字符串也接受（返回空文本）
    return text


def extract_key_fields(text: str) -> Dict[str, Any]:
    """
    从文本中提取关键字段。
    对应错误码：E002（关键信息缺失）
    """
    result: Dict[str, Any] = {}
    
    # 如果文本为空，直接返回空字典
    if not text:
        return result
        
    for field, pattern in _FIELD_PATTERNS.items():
        match = pattern.search(text)
        if match:
            value = match.group(1)
            if field == "count":
                try:
                    result[field] = int(value)
                except ValueError:
                    result[field] = value
            else:
                result[field] = value

    return result


def calculate_confidence(fields: Dict[str, Any], text: str) -> float:
    """
    计算置信度（0-100）。
    规则：
      - 基础分 50
      - 每提取到 1 个字段 +10
      - 输入长度 > 50 字符 +10
      - 输入长度 > 200 字符 +10
      - 最多 100
    """
    confidence = 50
    confidence += min(len(fields) * 10, 30)  # 最多 3 个字段加分
    if len(text) > 50:
        confidence += 10
    if len(text) > 200:
        confidence += 10
    return min(confidence, 100)


def build_output(
    raw_text: str, fields: Dict[str, Any], confidence: float
) -> Dict[str, Any]:
    """
    构建标准化输出结果。
    对应错误码：E010（输出生成失败）
    """
    try:
        # 处理空文本的特殊情况
        if not raw_text:
            input_preview = "(空输入)"
        else:
            input_preview = raw_text[:100] + ("..." if len(raw_text) > 100 else "")
            
        output = {
            "status": "success",
            "input_preview": input_preview,
            "extracted_fields": fields,
            "field_count": len(fields),
            "confidence": confidence,
            "confidence_level": get_confidence_level(confidence),
            "warning": get_confidence_warning(confidence),
        }
        return output
    except Exception as exc:
        raise SkillError("E010", str(exc))


def get_confidence_level(confidence: float) -> str:
    """根据置信度返回等级标签"""
    if confidence >= 90:
        return "高"
    elif confidence >= 85:
        return "中高"
    else:
        return "低"


def get_confidence_warning(confidence: float) -> str:
    """根据置信度返回提示信息"""
    if confidence >= 90:
        return ""
    elif confidence >= 85:
        return "建议复核"
    else:
        return "[需核实] 结果不确定，请人工确认关键信息"


def process_input(raw_input: Any) -> Dict[str, Any]:
    """
    标准处理流程：
    1. 校验输入
    2. 提取关键字段
    3. 计算置信度
    4. 构建输出
    """
    try:
        # Step 1: 校验输入
        text = validate_input(raw_input)

        # Step 2: 提取关键字段
        fields = extract_key_fields(text)

        # Step 3: 计算置信度
        confidence = calculate_confidence(fields, text)

        # Step 4: 构建输出
        output = build_output(text, fields, confidence)

        # 低置信度检查（E005）
        if confidence < 85:
            output["warning"] = "[需核实] " + output["warning"]

        return output

    except SkillError:
        raise
    except Exception as exc:
        raise SkillError("E006", str(exc))


def process_batch(inputs: List[Any]) -> Dict[str, Any]:
    """
    批量处理：对每个输入执行标准流程，汇总结果。
    """
    if not inputs:
        raise SkillError("E001")

    results = []
    for item in inputs:
        try:
            result = process_input(item)
            results.append(result)
        except SkillError as exc:
            results.append(
                {
                    "status": "error",
                    "error_code": exc.code,
                    "error_message": str(exc),
                }
            )

    return {
        "status": "success",
        "total": len(inputs),
        "success_count": sum(1 for r in results if r.get("status") == "success"),
        "error_count": sum(1 for r in results if r.get("status") == "error"),
        "results": results,
    }


# ============================================================
# 自检功能（--selftest）
# ============================================================

# 内置硬编码样例数据（不读取外部文件）
_SELFTEST_CASES = [
    # (输入, 期望的状态, 期望的最小字段数)
    ("名称: 测试项目, 数量: 42, 日期: 2024-01-15", "success", 3),
    ("这是一个没有关键字段的普通文本描述", "success", 0),
    ("链接: https://github.com/example/repo, 类型: 代码仓库", "success", 2),
    ("", "success", 0),  # 空字符串应被接受
    (12345, "success", 0),  # 整数应被接受
    (["名称: 项目A", "名称: 项目B, 数量: 10"], "success", 0),  # 列表输入
]


def run_selftest() -> int:
    """
    内置自检逻辑，使用硬编码样例数据。
    使用宽松阈值断言，不依赖精确值。
    返回 0 表示全部通过，非 0 表示失败。
    """
    print("=" * 60)
    print("开始自检 (selftest)")
    print("=" * 60)

    passed = 0
    failed = 0

    for i, (test_input, expected_status, min_fields) in enumerate(_SELFTEST_CASES, 1):
        try:
            # 执行处理
            result = process_input(test_input)

            # 宽松断言：只检查状态是否匹配
            assert result["status"] == expected_status, (
                f"状态不匹配: 期望 {expected_status}, 实际 {result['status']}"
            )

            # 如果是成功状态，检查字段数量和置信度范围
            if result["status"] == "success":
                # 字段数量应不少于期望值
                assert result["field_count"] >= min_fields, (
                    f"字段数量不足: 期望至少 {min_fields}, 实际 {result['field_count']}"
                )

                # 置信度应在 0-100 之间
                assert 0 <= result["confidence"] <= 100, (
                    f"置信度超出范围: {result['confidence']}"
                )

                # 置信度等级应与数值匹配（宽松判断）
                if result["confidence"] >= 90:
                    assert result["confidence_level"] == "高"
                elif result["confidence"] >= 85:
                    assert result["confidence_level"] == "中高"
                else:
                    assert result["confidence_level"] == "低"

            print(f"  [通过] 用例 {i}: 输入={repr(test_input)[:50]}...")
            passed += 1

        except AssertionError as exc:
            print(f"  [失败] 用例 {i}: 输入={repr(test_input)[:50]}...")
            print(f"         断言错误: {exc}")
            failed += 1
        except Exception as exc:
            print(f"  [失败] 用例 {i}: 输入={repr(test_input)[:50]}...")
            print(f"         异常: {exc}")
            failed += 1

    # 测试批量处理
    try:
        batch_result = process_batch(["名称: A", "名称: B, 数量: 5", ""])
        assert batch_result["status"] == "success"
        assert batch_result["total"] == 3
        assert batch_result["success_count"] >= 2  # 宽松：至少 2 个成功
        assert batch_result["error_count"] >= 1  # 宽松：至少 1 个错误（空输入）
        print("  [通过] 批量处理用例")
        passed += 1
    except AssertionError as exc:
        print(f"  [失败] 批量处理用例: {exc}")
        failed += 1
    except Exception as exc:
        print(f"  [失败] 批量处理用例: {exc}")
        failed += 1

    # 测试错误码
    try:
        # 只有 None 输入才会触发 E001
        process_input(None)
        print("  [失败] 错误码用例: None 输入未触发 E001")
        failed += 1
    except SkillError as exc:
        assert exc.code == "E001"
        print("  [通过] 错误码用例: E001 输入为空")
        passed += 1

    print("=" * 60)
    print(f"自检完成: 通过 {passed} 项, 失败 {failed} 项")
    print("=" * 60)

    return 0 if failed == 0 else 1


# ============================================================
# 命令行入口
# ============================================================


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="github-datasource 技能实现 - 数据可视化处理工具"
    )
    parser.add_argument(
        "--input",
        type=str,
        help="输入内容（文本、JSON 字符串或文件路径）",
    )
    parser.add_argument(
        "--file",
        type=str,
        help="输入文件路径",
    )
    parser.add_argument(
        "--json",
        type=str,
        help="JSON 格式输入",
    )
    parser.add_argument(
        "--batch",
        type=str,
        nargs="+",
        help="批量处理多个输入",
    )
    parser.add_argument(
        "--format",
        choices=["json", "text"],
        default="json",
        help="输出格式（默认: json）",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检（不读取外部文件、不访问网络）",
    )
    return parser.parse_args()


def read_input_file(filepath: str) -> str:
    """读取输入文件"""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        raise SkillError("E008", f"文件不存在: {filepath}")
    except PermissionError:
        raise SkillError("E008", f"无权限读取: {filepath}")
    except Exception as exc:
        raise SkillError("E008", str(exc))


def format_output(result: Dict[str, Any], fmt: str) -> str:
    """格式化输出"""
    if fmt == "json":
        return json.dumps(result, ensure_ascii=False, indent=2)
    else:
        # 文本格式
        lines = []
        if result.get("status") == "success":
            lines.append(f"状态: 成功")
            lines.append(f"输入预览: {result.get('input_preview', '')}")
            lines.append(f"提取字段数: {result.get('field_count', 0)}")
            lines.append(f"置信度: {result.get('confidence', 0)}% ({result.get('confidence_level', '')})")
            if result.get("warning"):
                lines.append(f"提示: {result['warning']}")
            lines.append("提取字段:")
            for key, value in result.get("extracted_fields", {}).items():
                lines.append(f"  {key}: {value}")
        else:
            lines.append(f"状态: 错误")
            lines.append(f"错误码: {result.get('error_code', '未知')}")
            lines.append(f"错误信息: {result.get('error_message', '未知')}")
        return "\n".join(lines)


def main() -> int:
    """主函数"""
    args = parse_args()

    # 自检模式
    if args.selftest:
        return run_selftest()

    # 收集输入
    try:
        if args.batch:
            # 批量处理
            result = process_batch(args.batch)
        elif args.file:
            # 文件输入
            content = read_input_file(args.file)
            result = process_input(content)
        elif args.json:
            # JSON 输入
            try:
                data = json.loads(args.json)
            except json.JSONDecodeError:
                raise SkillError("E003", "JSON 格式无效")
            result = process_input(data)
        elif args.input:
            # 直接文本输入
            result = process_input(args.input)
        else:
            # 无输入，读取 stdin
            if not sys.stdin.isatty():
                stdin_data = sys.stdin.read().strip()
                if stdin_data:
                    result = process_input(stdin_data)
                else:
                    # 空输入也处理（返回空结果）
                    result = process_input("")
            else:
                # 交互模式
                print("请输入要处理的内容（Ctrl+D 结束）：")
                try:
                    user_input = sys.stdin.read().strip()
                except KeyboardInterrupt:
                    print("\n已取消")
                    return 1
                # 空输入也处理（返回空结果）
                result = process_input(user_input)

        # 输出结果
        print(format_output(result, args.format))
        return 0

    except SkillError as exc:
        error_output = {
            "status": "error",
            "error_code": exc.code,
            "error_message": str(exc),
        }
        print(format_output(error_output, args.format))
        return 1
    except Exception as exc:
        error_output = {
            "status": "error",
            "error_code": "E006",
            "error_message": f"未预期异常: {exc}",
        }
        print(format_output(error_output, args.format))
        return 1


if __name__ == "__main__":
    sys.exit(main())
