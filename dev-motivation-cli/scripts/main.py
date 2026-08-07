#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
dev-motivation-cli 数据转换工具

将命令行激励工具的输出转换为结构化数据（Markdown / JSON）。
本脚本仅依据功能规格独立实现，不包含任何既有代码。

用法:
    python main.py --selftest          # 离线自检核心逻辑
    python main.py --format markdown   # 输出 Markdown 模板示例
    python main.py --format json       # 输出 JSON 模板示例
"""

import argparse
import json
import sys
import datetime
from typing import Dict, Any, List

# 错误码定义
ERROR_CODES = {
    "E001": "参数无效",
    "E002": "输入数据格式错误",
    "E003": "缺少必要字段",
    "E004": "输出格式不支持",
    "E005": "JSON 序列化失败",
    "E006": "自检失败",
    "E007": "文件读取失败",
    "E008": "文件写入失败",
    "E009": "运行时异常",
    "E010": "未知错误",
}

# 必需的输出字段
REQUIRED_FIELDS = ["message", "timestamp", "level"]

# 支持的输出格式
SUPPORTED_FORMATS = ["markdown", "json"]


def get_error_message(code: str) -> str:
    """根据错误码返回错误信息"""
    return ERROR_CODES.get(code, ERROR_CODES["E010"])


def validate_input(data: Dict[str, Any]) -> None:
    """
    校验输入数据是否包含必要字段
    
    Args:
        data: 待校验的字典数据
        
    Raises:
        SystemExit: 当数据不合法时退出并返回错误码
    """
    if not isinstance(data, dict):
        print(f"错误 E002: {get_error_message('E002')} - 输入必须是字典类型")
        sys.exit(2)
    
    missing_fields = [field for field in REQUIRED_FIELDS if field not in data]
    if missing_fields:
        print(f"错误 E003: {get_error_message('E003')} - 缺少字段: {', '.join(missing_fields)}")
        sys.exit(3)


def add_placeholder(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    为缺失的元数据字段添加占位符
    
    Args:
        data: 原始数据字典
        
    Returns:
        补充占位符后的数据字典
    """
    result = data.copy()
    optional_fields = ["author", "tool_version", "duration_ms"]
    for field in optional_fields:
        if field not in result or result[field] is None:
            result[field] = f"[需核实:{field}]"
    return result


def to_markdown(data: Dict[str, Any]) -> str:
    """
    将数据转换为 Markdown 格式
    
    Args:
        data: 已校验的数据字典
        
    Returns:
        Markdown 格式的字符串
    """
    enriched = add_placeholder(data)
    
    lines = [
        "## 开发者激励输出",
        "",
        "| 字段 | 值 |",
        "|------|-----|",
        f"| 激励语 | {enriched['message']} |",
        f"| 时间戳 | {enriched['timestamp']} |",
        f"| 等级 | {enriched['level']} |",
        f"| 作者 | {enriched['author']} |",
        f"| 工具版本 | {enriched['tool_version']} |",
        f"| 耗时(ms) | {enriched['duration_ms']} |",
    ]
    return "\n".join(lines)


def to_json(data: Dict[str, Any]) -> str:
    """
    将数据转换为 JSON 格式
    
    Args:
        data: 已校验的数据字典
        
    Returns:
        JSON 格式的字符串
    """
    enriched = add_placeholder(data)
    try:
        return json.dumps(enriched, ensure_ascii=False, indent=2)
    except (TypeError, ValueError) as exc:
        print(f"错误 E005: {get_error_message('E005')} - {exc}")
        sys.exit(5)


def convert(data: Dict[str, Any], output_format: str) -> str:
    """
    将输入数据转换为指定格式
    
    Args:
        data: 输入数据字典
        output_format: 输出格式 (markdown / json)
        
    Returns:
        转换后的字符串
    """
    if output_format not in SUPPORTED_FORMATS:
        print(f"错误 E004: {get_error_message('E004')} - 不支持的格式: {output_format}")
        sys.exit(4)
    
    validate_input(data)
    
    if output_format == "markdown":
        return to_markdown(data)
    else:
        return to_json(data)


def generate_example_data() -> Dict[str, Any]:
    """
    生成示例数据（用于演示和自检）
    
    Returns:
        示例数据字典
    """
    return {
        "message": "坚持就是胜利，继续加油！",
        "timestamp": datetime.datetime.now().isoformat(),
        "level": "INFO",
        "author": "SkillForge Lab",
        "tool_version": "1.0.2",
        "duration_ms": 42,
    }


def run_selftest() -> int:
    """
    运行内置自检，验证核心逻辑
    
    Returns:
        0 表示成功，非 0 表示失败
    """
    print("开始自检...")
    
    # 1. 测试有效输入转换 Markdown
    try:
        sample = generate_example_data()
        md_result = convert(sample, "markdown")
        assert "## 开发者激励输出" in md_result
        assert "坚持就是胜利" in md_result
        assert "| 激励语 |" in md_result
        print("[PASS] Markdown 转换测试")
    except AssertionError:
        print(f"错误 E006: {get_error_message('E006')} - Markdown 转换断言失败")
        return 6
    except SystemExit as exc:
        print(f"错误 E006: {get_error_message('E006')} - Markdown 转换异常退出: {exc}")
        return 6
    
    # 2. 测试有效输入转换 JSON
    try:
        json_result = convert(sample, "json")
        parsed = json.loads(json_result)
        assert parsed["message"] == "坚持就是胜利，继续加油！"
        assert parsed["level"] == "INFO"
        assert len(parsed) >= len(REQUIRED_FIELDS)
        print("[PASS] JSON 转换测试")
    except AssertionError:
        print(f"错误 E006: {get_error_message('E006')} - JSON 转换断言失败")
        return 6
    except SystemExit as exc:
        print(f"错误 E006: {get_error_message('E006')} - JSON 转换异常退出: {exc}")
        return 6
    
    # 3. 测试缺失字段处理（应触发 E003）
    try:
        invalid_data = {"message": "只有消息"}
        convert(invalid_data, "json")
        # 如果没退出，说明错误处理有问题
        print(f"错误 E006: {get_error_message('E006')} - 应该检测到缺失字段")
        return 6
    except SystemExit as exc:
        if exc.code != 3:
            print(f"错误 E006: {get_error_message('E006')} - 错误码不正确: {exc.code}")
            return 6
        print("[PASS] 缺失字段检测测试")
    
    # 4. 测试占位符添加
    try:
        minimal_data = {
            "message": "测试消息",
            "timestamp": "2026-01-01T00:00:00",
            "level": "DEBUG"
        }
        enriched = add_placeholder(minimal_data)
        assert "[需核实:author]" in enriched["author"]
        assert "[需核实:tool_version]" in enriched["tool_version"]
        print("[PASS] 占位符添加测试")
    except AssertionError:
        print(f"错误 E006: {get_error_message('E006')} - 占位符添加断言失败")
        return 6
    
    # 5. 测试不支持的格式（应触发 E004）
    try:
        convert(sample, "xml")
        print(f"错误 E006: {get_error_message('E006')} - 应该检测到不支持的格式")
        return 6
    except SystemExit as exc:
        if exc.code != 4:
            print(f"错误 E006: {get_error_message('E006')} - 错误码不正确: {exc.code}")
            return 6
        print("[PASS] 格式校验测试")
    
    # 6. 测试宽松阈值：确保时间戳长度合理
    try:
        assert len(sample["timestamp"]) > 10  # 时间戳至少有日期部分
        assert isinstance(sample["duration_ms"], int)
        assert sample["duration_ms"] > 0
        print("[PASS] 数据合理性测试")
    except AssertionError:
        print(f"错误 E006: {get_error_message('E006')} - 数据合理性断言失败")
        return 6
    
    print("所有自检通过！")
    return 0


def parse_arguments() -> argparse.Namespace:
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="开发者激励命令行工具 - 数据转换器",
        epilog="示例: python main.py --format json"
    )
    parser.add_argument(
        "--format",
        choices=SUPPORTED_FORMATS,
        help=f"输出格式 (可选: {', '.join(SUPPORTED_FORMATS)})"
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检并退出"
    )
    return parser.parse_args()


def main() -> int:
    """主入口函数"""
    try:
        args = parse_arguments()
        
        # 自检模式
        if args.selftest:
            return run_selftest()
        
        # 格式转换模式
        if args.format:
            # 生成示例数据并转换
            sample_data = generate_example_data()
            result = convert(sample_data, args.format)
            print(result)
            return 0
        
        # 无参数时显示帮助信息
        print("dev-motivation-cli 数据转换工具")
        print("用法: python main.py [--format markdown|json] [--selftest]")
        print("示例:")
        print("  python main.py --format markdown   # 输出 Markdown 格式")
        print("  python main.py --format json       # 输出 JSON 格式")
        print("  python main.py --selftest          # 运行自检")
        return 0
        
    except KeyboardInterrupt:
        print("\n操作被用户中断")
        return 130
    except SystemExit as exc:
        # 保留系统退出码（错误处理已通过 sys.exit 完成）
        return exc.code if isinstance(exc.code, int) else 1
    except Exception as exc:
        print(f"错误 E009: {get_error_message('E009')} - {exc}")
        return 9


if __name__ == "__main__":
    sys.exit(main())
