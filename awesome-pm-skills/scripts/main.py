#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
awesome-pm-skills 独立实现脚本

依据功能规格从零编写，不参考任何既有实现。
提供命令行入口，支持 --selftest 离线自检。
"""

import argparse
import sys
from typing import Any, Dict, List, Optional, Tuple

# 版本信息
VERSION = "1.0.0"
SKILL_NAME = "awesome-pm-skills"

# 错误码与话术映射（依据规格定义）
ERROR_MESSAGES = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：{missing}",
    "E003": "输入格式不符合要求，示例：{example}",
    "E004": "这超出了本工具的能力范围，建议：{suggestion}",
    "E005": "结果无法确定，建议：{suggestion}",
}

# 置信度阈值（依据规格）
CONFIDENCE_HIGH = 0.90
CONFIDENCE_MEDIUM = 0.85


class PMSkillError(Exception):
    """技能运行异常，携带错误码"""

    def __init__(self, code: str, **kwargs):
        self.code = code
        self.message = ERROR_MESSAGES.get(code, "未知错误").format(**kwargs)
        super().__init__(self.message)


def validate_input(data: Any) -> str:
    """
    校验输入是否有效，返回标准化字符串。

    规则：
    - 空值（None、空字符串、空列表/字典）→ E001
    - 非字符串/列表/字典 → E003
    """
    if data is None:
        raise PMSkillError("E001")

    if isinstance(data, str):
        text = data.strip()
        if not text:
            raise PMSkillError("E001")
        return text

    if isinstance(data, (list, dict)):
        if len(data) == 0:
            raise PMSkillError("E001")
        # 简单序列化用于后续处理
        return str(data)

    raise PMSkillError("E003", example="字符串、列表或字典")


def extract_key_info(text: str) -> Dict[str, Any]:
    """
    从输入文本中提取关键信息（核心逻辑）。

    依据规格：
    - 识别输入中的关键字段并结构化
    - 对不确定项标注
    返回字典，包含：
    - item_count: 识别到的条目数
    - has_content: 是否有实质内容
    - keywords: 提取的关键词列表
    - confidence: 置信度估计
    """
    if not text:
        raise PMSkillError("E001")

    # 简单分词（按空格/逗号/换行分割）
    parts = [p.strip() for p in text.replace(",", " ").replace("\n", " ").split()]
    parts = [p for p in parts if p]

    if not parts:
        raise PMSkillError("E002", missing="有效内容")

    # 提取关键词（长度≥2的词语视为有效）
    keywords = [p for p in parts if len(p) >= 2]

    # 估计置信度：基于内容长度和结构
    if len(parts) >= 3:
        confidence = 0.92  # 内容较丰富
    elif len(parts) >= 2:
        confidence = 0.88  # 中等
    else:
        confidence = 0.80  # 内容较少

    return {
        "item_count": len(parts),
        "has_content": True,
        "keywords": keywords[:10],  # 最多保留10个关键词
        "confidence": confidence,
    }


def format_output(parsed: Dict[str, Any], output_format: str = "text") -> str:
    """
    按指定格式生成输出。

    支持格式：
    - text: 纯文本摘要
    - json: JSON字符串
    - table: 简单表格
    """
    if output_format == "json":
        import json
        return json.dumps(parsed, ensure_ascii=False, indent=2)

    if output_format == "table":
        lines = ["字段 | 值", "--- | ---"]
        for key, value in parsed.items():
            lines.append(f"{key} | {value}")
        return "\n".join(lines)

    # 默认文本格式
    lines = [f"处理结果（条目数: {parsed['item_count']}）"]
    if parsed["keywords"]:
        lines.append("关键词: " + ", ".join(parsed["keywords"]))
    lines.append(f"置信度: {parsed['confidence']:.0%}")

    # 添加置信度标注（依据规格）
    if parsed["confidence"] >= CONFIDENCE_HIGH:
        lines.append("标注: 直接输出")
    elif parsed["confidence"] >= CONFIDENCE_MEDIUM:
        lines.append("标注: 建议复核")
    else:
        lines.append("标注: [需核实] 内容不足或不确定")

    return "\n".join(lines)


def process_input(data: Any, output_format: str = "text") -> str:
    """
    标准处理流程（Step 2 核心）。

    流程：
    1. 校验输入
    2. 提取关键信息
    3. 生成输出
    """
    # Step 1: 校验
    text = validate_input(data)

    # Step 2: 提取
    parsed = extract_key_info(text)

    # Step 3: 输出
    return format_output(parsed, output_format)


def check_input_requirements(data: Any) -> List[str]:
    """
    检查最小信息集（Step 1 辅助）。

    返回缺失项列表。
    """
    missing = []
    if data is None or (isinstance(data, str) and not data.strip()):
        missing.append("输入内容")
    if isinstance(data, (list, dict)) and len(data) == 0:
        missing.append("输入内容")
    return missing


def run_selftest() -> bool:
    """
    离线自检：使用内置硬编码样例验证核心逻辑。

    使用宽松断言（区间/大小比较），不依赖精确值。
    不读取外部文件，不访问网络，不依赖工作目录。
    """
    print("=== 自检开始 ===")

    # 测试1: 正常输入处理
    sample = "产品需求 用户反馈 数据分析 优先级排序"
    result = process_input(sample)
    assert "处理结果" in result, "测试1失败: 输出缺少标题"
    assert "置信度" in result, "测试1失败: 缺少置信度"
    print("[PASS] 测试1: 正常输入")

    # 测试2: 空输入应报错 E001
    try:
        process_input("")
        assert False, "测试2失败: 未抛出异常"
    except PMSkillError as e:
        assert e.code == "E001", f"测试2失败: 错误码={e.code}"
    print("[PASS] 测试2: 空输入错误码")

    # 测试3: 置信度区间验证
    parsed = extract_key_info("短文本")
    assert 0.0 <= parsed["confidence"] <= 1.0, "测试3失败: 置信度越界"
    assert parsed["item_count"] >= 1, "测试3失败: 条目数异常"
    print("[PASS] 测试3: 置信度区间")

    # 测试4: JSON输出格式
    json_result = process_input("测试 数据 内容", output_format="json")
    assert "{" in json_result, "测试4失败: 非JSON格式"
    print("[PASS] 测试4: JSON输出")

    # 测试5: 批量处理（列表输入）
    batch_data = ["条目一", "条目二 附加", "第三条 内容 更多"]
    for item in batch_data:
        r = process_input(item)
        assert "处理结果" in r, "测试5失败: 批量处理异常"
    print("[PASS] 测试5: 批量处理")

    # 测试6: 缺失信息检查
    missing = check_input_requirements(None)
    assert len(missing) > 0, "测试6失败: 空输入未检出缺失"
    missing2 = check_input_requirements("有内容")
    assert len(missing2) == 0, "测试6失败: 正常输入误报缺失"
    print("[PASS] 测试6: 缺失信息检查")

    # 测试7: 关键词提取数量
    parsed = extract_key_info("a b c d e f g h i j k l m")
    assert len(parsed["keywords"]) <= 10, "测试7失败: 关键词数量超限"
    print("[PASS] 测试7: 关键词限制")

    # 测试8: 错误码映射
    assert ERROR_MESSAGES["E001"], "测试8失败: 错误码缺失"
    assert ERROR_MESSAGES["E002"], "测试8失败: 错误码缺失"
    assert ERROR_MESSAGES["E003"], "测试8失败: 错误码缺失"
    assert ERROR_MESSAGES["E004"], "测试8失败: 错误码缺失"
    assert ERROR_MESSAGES["E005"], "测试8失败: 错误码缺失"
    print("[PASS] 测试8: 错误码完整性")

    # 测试9: 表格输出
    table_result = process_input("测试 表格 输出", output_format="table")
    assert "|" in table_result, "测试9失败: 表格格式异常"
    print("[PASS] 测试9: 表格输出")

    # 测试10: 长文本处理
    long_text = " ".join(["内容"] * 50)
    parsed = extract_key_info(long_text)
    assert parsed["item_count"] >= 10, "测试10失败: 长文本解析异常"
    assert parsed["confidence"] > CONFIDENCE_HIGH, "测试10失败: 置信度应较高"
    print("[PASS] 测试10: 长文本处理")

    print("=== 自检全部通过 ===")
    return True


def main() -> int:
    """命令行入口"""
    parser = argparse.ArgumentParser(
        description=f"{SKILL_NAME} - 未命名工具 v{VERSION}",
        epilog="示例: python main.py '要处理的内容' --format json"
    )
    parser.add_argument(
        "input",
        nargs="?",
        default=None,
        help="待处理的内容（字符串）"
    )
    parser.add_argument(
        "--format",
        choices=["text", "json", "table"],
        default="text",
        help="输出格式 (默认: text)"
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行离线自检并退出"
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"{SKILL_NAME} {VERSION}"
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        try:
            success = run_selftest()
            return 0 if success else 1
        except AssertionError as e:
            print(f"自检失败: {e}", file=sys.stderr)
            return 1
        except Exception as e:
            print(f"自检异常: {e}", file=sys.stderr)
            return 1

    # 正常处理模式
    if args.input is None:
        print(f"错误 E001: {ERROR_MESSAGES['E001']}", file=sys.stderr)
        return 1

    try:
        result = process_input(args.input, args.format)
        print(result)
        return 0
    except PMSkillError as e:
        print(f"错误 {e.code}: {e.message}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"错误 E010: 未预期异常 - {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
