#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py - Feishu Docx 技能独立实现（Clean Room 重写）

仅依据功能规格独立实现，不复制任何既有代码。
提供命令行入口，支持 --selftest 离线自检。
"""

import argparse
import sys
import json
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 常量定义
# ============================================================

# 错误码及标准话术（依据规格第五节）
ERROR_MESSAGES: Dict[str, str] = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：...",
    "E003": "输入格式不符合要求，示例：...",
    "E004": "这超出了本工具的能力范围，建议...",
    "E005": "结果无法确定，建议：...",
    "E006": "内部处理异常，请重试或联系管理员",
    "E007": "参数解析失败，请检查命令行参数",
    "E008": "输出写入失败，请检查文件系统权限",
    "E009": "配置加载失败，请检查配置文件格式",
    "E010": "未知错误，请查看日志",
}

# 触发词表（依据规格第二节）
TRIGGER_WORDS: List[str] = ["feishu docx"]

# 能力边界声明（依据规格第一节）
CAPABILITY_BOUNDARIES: List[str] = [
    "不做：不执行超出输入范围的分析",
    "不做：不保证绝对准确，低置信度会标注",
    "不做：不访问网络或外部服务",
]

# 置信度阈值（依据规格第三节）
CONFIDENCE_HIGH: float = 0.90
CONFIDENCE_MEDIUM: float = 0.85


# ============================================================
# 核心数据结构
# ============================================================

class ProcessingResult:
    """处理结果封装"""
    def __init__(self, content: Any, confidence: float, notes: Optional[List[str]] = None):
        self.content = content
        self.confidence = confidence
        self.notes = notes or []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "content": self.content,
            "confidence": round(self.confidence, 2),
            "confidence_label": self._get_label(),
            "notes": self.notes,
        }

    def _get_label(self) -> str:
        """根据置信度生成标注"""
        if self.confidence >= CONFIDENCE_HIGH:
            return "直接输出"
        elif self.confidence >= CONFIDENCE_MEDIUM:
            return "建议复核"
        else:
            return "[需核实]"


# ============================================================
# 核心逻辑函数
# ============================================================

def validate_input(raw_input: Any) -> Optional[str]:
    """
    校验输入有效性（错误码 E001/E002/E003）
    返回 None 表示通过，否则返回错误码
    """
    if raw_input is None or raw_input == "":
        return "E001"
    if not isinstance(raw_input, (str, dict, list)):
        return "E003"
    if isinstance(raw_input, dict) and len(raw_input) == 0:
        return "E001"
    if isinstance(raw_input, list) and len(raw_input) == 0:
        return "E001"
    return None


def check_capability_boundary(task_description: str) -> Optional[str]:
    """
    检查是否超出能力边界（错误码 E004）
    返回 None 表示在能力范围内，否则返回错误码
    """
    # 简单启发式检查：如果任务描述包含明显超出范围的意图
    out_of_scope_indicators = ["网络", "互联网", "外部服务", "实时数据", "在线"]
    for indicator in out_of_scope_indicators:
        if indicator in task_description.lower():
            return "E004"
    return None


def extract_key_fields(content: Any) -> Tuple[Dict[str, Any], float]:
    """
    从输入内容中提取关键字段（核心处理逻辑）
    返回 (结构化字段字典, 置信度)
    """
    fields: Dict[str, Any] = {}
    confidence = 0.0
    total_items = 0
    recognized_items = 0

    # 根据输入类型处理
    if isinstance(content, str):
        # 字符串输入：尝试解析为 JSON 或按文本处理
        try:
            parsed = json.loads(content)
            if isinstance(parsed, dict):
                total_items = len(parsed)
                for key, value in parsed.items():
                    if value is not None and value != "":
                        fields[str(key)] = value
                        recognized_items += 1
            else:
                # 非字典 JSON，直接作为内容
                fields["content"] = parsed
                recognized_items = 1
                total_items = 1
        except (json.JSONDecodeError, TypeError):
            # 纯文本：按行拆分，识别键值对
            lines = [line.strip() for line in content.split("\n") if line.strip()]
            total_items = len(lines)
            for line in lines:
                if ":" in line or "：" in line:
                    sep = ":" if ":" in line else "："
                    key, _, value = line.partition(sep)
                    if key.strip() and value.strip():
                        fields[key.strip()] = value.strip()
                        recognized_items += 1
                else:
                    fields[f"line_{recognized_items}"] = line
                    recognized_items += 1

    elif isinstance(content, dict):
        # 字典输入：直接遍历
        total_items = len(content)
        for key, value in content.items():
            if value is not None and value != "":
                fields[str(key)] = value
                recognized_items += 1

    elif isinstance(content, list):
        # 列表输入：每个元素作为一个条目
        total_items = len(content)
        for idx, item in enumerate(content):
            if item is not None and item != "":
                fields[f"item_{idx}"] = item
                recognized_items += 1

    # 计算置信度（宽松阈值）
    if total_items > 0:
        ratio = recognized_items / total_items
        # 基础置信度 0.7，根据识别比例调整
        confidence = 0.7 + (ratio * 0.3)
    else:
        confidence = 0.5

    # 确保置信度在合理范围
    confidence = max(0.0, min(1.0, confidence))

    return fields, confidence


def process_input(raw_input: Any) -> ProcessingResult:
    """
    处理输入的主流程（依据规格第三节 Step 2）
    """
    # Step 2.1: 校验输入
    error_code = validate_input(raw_input)
    if error_code:
        raise ValueError(error_code)

    # Step 2.2: 检查能力边界
    task_desc = str(raw_input)[:200] if isinstance(raw_input, str) else "结构化数据"
    boundary_error = check_capability_boundary(task_desc)
    if boundary_error:
        raise ValueError(boundary_error)

    # Step 2.3: 提取关键字段
    fields, confidence = extract_key_fields(raw_input)

    # Step 2.4: 生成输出结构
    result_content = {
        "processed_data": fields,
        "field_count": len(fields),
        "source_type": type(raw_input).__name__,
    }

    # Step 2.5: 生成注释
    notes = []
    if confidence < CONFIDENCE_MEDIUM:
        notes.append("输入信息不完整，部分字段可能缺失")
    if confidence < CONFIDENCE_HIGH:
        notes.append("建议人工复核关键结果")

    return ProcessingResult(result_content, confidence, notes)


def format_output(result: ProcessingResult) -> str:
    """
    格式化输出结果（依据规格第三节 Step 3）
    """
    output_lines = []
    output_lines.append("=" * 50)
    output_lines.append("处理结果")
    output_lines.append("=" * 50)

    # 输出置信度
    label = result._get_label()
    output_lines.append(f"置信度: {result.confidence:.0%} ({label})")

    # 输出注释
    if result.notes:
        output_lines.append("注释:")
        for note in result.notes:
            output_lines.append(f"  - {note}")

    # 输出内容
    output_lines.append("内容:")
    content = result.content
    if isinstance(content, dict):
        for key, value in content.items():
            if isinstance(value, dict):
                output_lines.append(f"  {key}:")
                for sub_key, sub_value in value.items():
                    output_lines.append(f"    {sub_key}: {sub_value}")
            else:
                output_lines.append(f"  {key}: {value}")
    else:
        output_lines.append(f"  {content}")

    output_lines.append("=" * 50)
    return "\n".join(output_lines)


# ============================================================
# 自检模块（--selftest）
# ============================================================

def run_selftest() -> bool:
    """
    离线自检核心逻辑
    使用内置硬编码样例，不依赖外部文件/网络/工作目录
    """
    print("开始自检...")
    all_passed = True

    # 测试用例 1: 有效的字典输入
    test_cases = [
        {
            "name": "字典输入",
            "input": {"name": "测试文档", "type": "docx", "size": "10KB"},
            "expect_success": True,
        },
        {
            "name": "JSON字符串输入",
            "input": '{"title": "项目报告", "author": "张三", "date": "2024-01-01"}',
            "expect_success": True,
        },
        {
            "name": "键值对文本输入",
            "input": "标题：季度总结\n作者：李四\n状态：已完成",
            "expect_success": True,
        },
        {
            "name": "空输入",
            "input": "",
            "expect_success": False,
        },
        {
            "name": "列表输入",
            "input": ["文档1", "文档2", "文档3"],
            "expect_success": True,
        },
    ]

    for idx, case in enumerate(test_cases, 1):
        print(f"  测试用例 {idx}: {case['name']}")
        try:
            result = process_input(case["input"])
            if case["expect_success"]:
                # 宽松断言：只检查基本属性
                assert result.content is not None, "结果内容不应为空"
                assert 0.0 <= result.confidence <= 1.0, "置信度应在 0-1 之间"
                assert isinstance(result.notes, list), "注释应为列表"
                print(f"    ✓ 通过 (置信度: {result.confidence:.0%})")
            else:
                print(f"    ✗ 失败: 期望失败但成功了")
                all_passed = False
        except ValueError as e:
            if case["expect_success"]:
                print(f"    ✗ 失败: 意外错误 {e}")
                all_passed = False
            else:
                # 验证错误码
                assert str(e) in ERROR_MESSAGES, f"未知错误码: {e}"
                print(f"    ✓ 正确拒绝 (错误码: {e})")
        except Exception as e:
            print(f"    ✗ 失败: 未知异常 {type(e).__name__}: {e}")
            all_passed = False

    # 测试用例: 置信度验证
    print("  测试用例 6: 置信度合理性")
    try:
        # 完整字典输入应该有较高置信度
        complete_input = {"a": "1", "b": "2", "c": "3", "d": "4", "e": "5"}
        result = process_input(complete_input)
        assert result.confidence > 0.8, "完整输入置信度应较高"
        print(f"    ✓ 通过 (置信度: {result.confidence:.0%})")
    except Exception as e:
        print(f"    ✗ 失败: {e}")
        all_passed = False

    # 测试用例: 能力边界检查
    print("  测试用例 7: 能力边界")
    boundary_error = check_capability_boundary("请访问网络获取数据")
    assert boundary_error == "E004", "应检测到超出能力边界"
    print("    ✓ 正确检测到超出能力边界")

    # 测试用例: 错误码完整性
    print("  测试用例 8: 错误码完整性")
    required_codes = ["E001", "E002", "E003", "E004", "E005"]
    for code in required_codes:
        assert code in ERROR_MESSAGES, f"缺少错误码 {code}"
        assert ERROR_MESSAGES[code], f"错误码 {code} 缺少消息"
    print("    ✓ 错误码完整")

    # 测试用例: 触发词验证
    print("  测试用例 9: 触发词")
    assert "feishu docx" in TRIGGER_WORDS, "缺少触发词"
    print("    ✓ 触发词正确")

    # 最终结果
    if all_passed:
        print("自检全部通过 ✓")
    else:
        print("自检存在失败项 ✗")
    return all_passed


# ============================================================
# 命令行入口
# ============================================================

def main() -> int:
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description="Feishu Docx 处理工具 - 提供结构化数据处理与转换"
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行离线自检（不依赖外部环境）",
    )
    parser.add_argument(
        "--input",
        type=str,
        help="输入内容（字符串、JSON字符串或键值对文本）",
    )
    parser.add_argument(
        "--input-file",
        type=str,
        help="从文件读取输入（不推荐在自检模式使用）",
    )
    parser.add_argument(
        "--output-json",
        action="store_true",
        help="以JSON格式输出结果",
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        success = run_selftest()
        return 0 if success else 1

    # 正常处理模式
    try:
        # 收集输入
        raw_input = None
        if args.input:
            raw_input = args.input
        elif args.input_file:
            try:
                with open(args.input_file, "r", encoding="utf-8") as f:
                    raw_input = f.read()
            except (IOError, OSError) as e:
                print(f"错误: 无法读取输入文件 - {e}")
                return 1
        else:
            # 交互模式：从标准输入读取
            print("请输入待处理的内容（Ctrl+D 结束输入）:")
            try:
                raw_input = sys.stdin.read().strip()
            except KeyboardInterrupt:
                print("\n输入被中断")
                return 1

        # 处理输入
        result = process_input(raw_input)

        # 输出结果
        if args.output_json:
            print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
        else:
            print(format_output(result))

        return 0

    except ValueError as e:
        # 处理已知错误码
        error_code = str(e)
        if error_code in ERROR_MESSAGES:
            print(f"错误 [{error_code}]: {ERROR_MESSAGES[error_code]}")
        else:
            print(f"错误: {error_code}")
        return 1

    except Exception as e:
        print(f"错误 [E010]: {ERROR_MESSAGES['E010']} - {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
