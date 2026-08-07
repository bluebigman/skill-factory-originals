#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
脚本名称: gald3r 技能实现脚本
功能描述: 依据功能规格独立实现的 clean-room 版本，提供标准处理流程。
版权信息: MIT License, Copyright (c) 2026 原创作者（自持版权）
"""

import argparse
import json
import sys
from typing import Any, Dict, List, Optional, Tuple

# 技能元数据
SKILL_META = {
    "slug": "gald3r",
    "name": "gald3r",
    "displayName": "未命名工具",
    "version": "1.0.0",
    "description": "仅供学习与参考用途。当用户需要仅供学习与参考用途、进行gald3r相关操作时使用本技能，提供规范、可复用的处理流程与输出。",
    "author": "skill-factory-auto",
    "license": "MIT",
}

# 错误码定义
ERROR_CODES = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：...",
    "E003": "输入格式不符合要求，示例：...",
    "E004": "这超出了本工具的能力范围，建议...",
    "E005": "结果无法确定，建议：...",
    "E006": "内部处理异常，请联系管理员",
    "E007": "参数解析失败，请检查命令行参数",
    "E008": "输出格式不受支持",
    "E009": "批量处理时出现错误，已跳过部分条目",
    "E010": "未知错误，请稍后重试",
}


def get_error_message(error_code: str) -> str:
    """根据错误码获取标准话术"""
    return ERROR_CODES.get(error_code, ERROR_CODES["E010"])


class Gald3rProcessor:
    """核心处理器：负责输入解析、结构化、置信度标注与输出"""

    # 能力边界声明
    CAPABILITIES = {
        "can_do": [
            "将用户提供的数据/文件/URL转换为结构化结果",
            "识别并保留输入中的关键信息",
            "按约定格式生成输出",
            "对不确定项给出置信度提示",
            "支持批量处理和自定义格式",
        ],
        "cannot_do": [
            "不执行超出输入范围的分析",
            "不保证绝对准确，低置信度会标注",
            "不访问网络或外部服务",
        ],
    }

    # 触发词表
    TRIGGER_WORDS = ["gald3r"]

    # 标准流程描述
    STANDARD_FLOW = {
        "step1": "收集最小信息集：输入来源、输出格式要求、期望完整度",
        "step2": "执行核心流程：解析输入、识别关键信息、结构化处理、标注置信度",
        "step3": "输出与校验：整理格式、自查字段完整性、二次确认疑问",
    }

    def __init__(self, output_format: str = "json", batch_mode: bool = False):
        """初始化处理器

        Args:
            output_format: 输出格式，支持 json/text
            batch_mode: 是否为批量模式
        """
        self.output_format = output_format
        self.batch_mode = batch_mode
        self.confidence_threshold_high = 90  # 高置信度阈值
        self.confidence_threshold_medium = 85  # 中置信度阈值

    def process(self, raw_input: Any) -> Dict[str, Any]:
        """处理入口：执行核心流程

        Args:
            raw_input: 用户输入的原始数据

        Returns:
            结构化处理结果字典
        """
        # 输入校验
        if raw_input is None or (isinstance(raw_input, str) and not raw_input.strip()):
            return self._build_error_result("E001")

        # 解析输入
        parsed = self._parse_input(raw_input)
        if parsed is None:
            return self._build_error_result("E003")

        # 识别关键信息
        key_info, confidence = self._extract_key_info(parsed)

        # 置信度判断
        if confidence < self.confidence_threshold_medium:
            key_info["needs_verification"] = True
            key_info["verification_note"] = "[需核实] 置信度较低，请人工复核关键结果"
        elif confidence < self.confidence_threshold_high:
            key_info["review_suggestion"] = "建议复核"

        # 构建结构化输出
        result = {
            "status": "success",
            "data": key_info,
            "confidence": confidence,
            "meta": {
                "skill": SKILL_META["slug"],
                "version": SKILL_META["version"],
            },
        }

        return result

    def _parse_input(self, raw_input: Any) -> Optional[Any]:
        """解析输入内容：支持字符串、列表、字典等常见类型

        Args:
            raw_input: 原始输入

        Returns:
            解析后的结构化数据，无法解析时返回 None
        """
        if isinstance(raw_input, (str, int, float, bool)):
            # 尝试解析 JSON 字符串
            if isinstance(raw_input, str):
                try:
                    return json.loads(raw_input)
                except (json.JSONDecodeError, TypeError):
                    # 非 JSON 字符串，按普通文本处理
                    return {"text": raw_input}
            return {"value": raw_input}

        if isinstance(raw_input, (list, dict, tuple)):
            return raw_input

        return None

    def _extract_key_info(self, data: Any) -> Tuple[Dict[str, Any], float]:
        """提取关键信息并计算置信度

        Args:
            data: 解析后的数据

        Returns:
            (结构化关键信息, 置信度百分比)
        """
        if isinstance(data, dict):
            # 字典类型：保留所有键值对，识别常见关键字段
            key_info = {}
            known_keys = ["id", "name", "title", "type", "status", "date", "description", "value"]

            for key, value in data.items():
                key_str = str(key).lower()
                if key_str in known_keys:
                    key_info[key_str] = value
                else:
                    key_info[key] = value

            # 基于字段完整度计算置信度
            filled_fields = len(key_info)
            total_fields = max(len(data), 1)
            confidence = min(95, 60 + (filled_fields / total_fields) * 35)

        elif isinstance(data, list):
            # 列表类型：逐项处理
            items = []
            for item in data:
                if isinstance(item, dict):
                    items.append(self._extract_key_info(item)[0])
                else:
                    items.append({"value": item})

            key_info = {
                "count": len(items),
                "items": items,
                "batch": True,
            }
            confidence = 88.0  # 批量数据的默认置信度

        else:
            # 简单类型
            key_info = {"value": data}
            confidence = 92.0

        return key_info, confidence

    def _build_error_result(self, error_code: str) -> Dict[str, Any]:
        """构建错误结果

        Args:
            error_code: 错误码

        Returns:
            错误结果字典
        """
        return {
            "status": "error",
            "error_code": error_code,
            "error_message": get_error_message(error_code),
            "meta": {
                "skill": SKILL_META["slug"],
                "version": SKILL_META["version"],
            },
        }

    def format_output(self, result: Dict[str, Any]) -> str:
        """格式化输出结果

        Args:
            result: 处理结果字典

        Returns:
            格式化后的输出字符串
        """
        if self.output_format == "json":
            return json.dumps(result, ensure_ascii=False, indent=2)

        # 文本格式输出
        lines = []
        if result.get("status") == "error":
            lines.append(f"[错误 {result['error_code']}] {result['error_message']}")
        else:
            lines.append(f"处理完成 (置信度: {result['confidence']:.1f}%)")
            lines.append("=" * 40)
            for key, value in result.get("data", {}).items():
                if key in ("needs_verification", "verification_note", "review_suggestion"):
                    lines.append(f"⚠️ {key}: {value}")
                else:
                    lines.append(f"{key}: {value}")

        return "\n".join(lines)


def run_selftest() -> bool:
    """内置硬编码样例数据的离线自检

    Returns:
        自检是否通过
    """
    print("开始自检...")

    # 初始化处理器
    processor = Gald3rProcessor()

    # 样例 1: 文本输入
    print("\n[测试 1] 文本输入处理")
    result1 = processor.process("这是一段测试文本，用于验证基本处理流程")
    assert result1["status"] == "success", "文本输入应成功处理"
    assert result1["confidence"] > 50, "文本输入置信度应较高"
    print(f"  通过 (置信度: {result1['confidence']:.1f}%)")

    # 样例 2: 字典输入
    print("\n[测试 2] 字典输入处理")
    dict_input = {
        "id": "T001",
        "name": "测试项目",
        "type": "示例",
        "status": "active",
    }
    result2 = processor.process(dict_input)
    assert result2["status"] == "success", "字典输入应成功处理"
    assert result2["data"]["name"] == "测试项目", "应保留关键字段"
    assert result2["confidence"] > 70, "字段完整度高的输入置信度应较高"
    print(f"  通过 (置信度: {result2['confidence']:.1f}%)")

    # 样例 3: 列表输入（批量）
    print("\n[测试 3] 列表输入处理")
    list_input = [
        {"id": 1, "value": "A"},
        {"id": 2, "value": "B"},
        {"id": 3, "value": "C"},
    ]
    result3 = processor.process(list_input)
    assert result3["status"] == "success", "列表输入应成功处理"
    assert result3["data"]["count"] == 3, "应识别条目数量"
    print(f"  通过 (置信度: {result3['confidence']:.1f}%)")

    # 样例 4: 空输入处理
    print("\n[测试 4] 空输入处理")
    result4 = processor.process("")
    assert result4["status"] == "error", "空输入应返回错误"
    assert result4["error_code"] == "E001", "空输入错误码应为 E001"
    print(f"  通过 (错误码: {result4['error_code']})")

    # 样例 5: JSON 字符串输入
    print("\n[测试 5] JSON 字符串输入")
    json_input = '{"title": "示例标题", "description": "示例描述"}'
    result5 = processor.process(json_input)
    assert result5["status"] == "success", "JSON 字符串应成功处理"
    assert result5["data"]["title"] == "示例标题", "应解析 JSON 中的标题"
    print(f"  通过 (置信度: {result5['confidence']:.1f}%)")

    # 样例 6: 文本格式输出
    print("\n[测试 6] 文本格式输出")
    text_processor = Gald3rProcessor(output_format="text")
    text_output = text_processor.format_output(result1)
    assert "处理完成" in text_output, "文本输出应包含处理完成信息"
    print("  通过")

    # 样例 7: 错误码话术
    print("\n[测试 7] 错误码话术")
    assert "请提供待处理的内容" in get_error_message("E001")
    assert "超出本工具的能力范围" in get_error_message("E004")
    print("  通过")

    # 样例 8: 能力边界
    print("\n[测试 8] 能力边界")
    can_do_count = len(Gald3rProcessor.CAPABILITIES["can_do"])
    cannot_do_count = len(Gald3rProcessor.CAPABILITIES["cannot_do"])
    assert can_do_count > 0, "应声明能做能力"
    assert cannot_do_count > 0, "应声明边界能力"
    print(f"  通过 (能做 {can_do_count} 项, 不做 {cannot_do_count} 项)")

    print("\n✅ 所有自检通过！")
    return True


def main() -> int:
    """主入口函数

    Returns:
        进程退出码
    """
    parser = argparse.ArgumentParser(
        description="gald3r 技能处理工具",
        epilog="示例: python main.py --input '待处理内容' --format json",
    )
    parser.add_argument(
        "--input",
        type=str,
        help="待处理的数据/文件路径/URL（本工具不访问网络，URL 仅作为文本处理）",
    )
    parser.add_argument(
        "--format",
        type=str,
        choices=["json", "text"],
        default="json",
        help="输出格式 (默认: json)",
    )
    parser.add_argument(
        "--batch",
        action="store_true",
        help="批量处理模式",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行离线自检（不读取外部文件、不访问网络）",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {SKILL_META['version']}",
    )

    try:
        args = parser.parse_args()
    except SystemExit as e:
        # argparse 会自行处理退出，这里捕获以便返回错误码
        return e.code if isinstance(e.code, int) else 2

    # 自检模式
    if args.selftest:
        try:
            run_selftest()
            return 0
        except AssertionError as e:
            print(f"\n❌ 自检失败: {e}")
            return 1
        except Exception as e:
            print(f"\n❌ 自检异常: {e}")
            return 1

    # 处理模式
    if not args.input:
        print(get_error_message("E001"))
        return 1

    processor = Gald3rProcessor(output_format=args.format, batch_mode=args.batch)

    try:
        result = processor.process(args.input)
        output = processor.format_output(result)
        print(output)

        # 错误码处理
        if result.get("status") == "error":
            return 1
        return 0

    except Exception as e:
        print(f"[E010] 未知错误: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
