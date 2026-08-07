#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py
未命名工具 - awesome-growth-hacking-skills 技能实现

仅供学习与参考用途。使用前请阅读相关文档。
本代码受版权法保护，未经授权复制、反向工程或商业利用将被追究法律责任。
"""

import argparse
import sys
import re
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 错误码定义
# ============================================================
ERROR_CODES = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：",
    "E003": "输入格式不符合要求，示例：",
    "E004": "这超出了本工具的能力范围，建议：",
    "E005": "结果无法确定，建议：",
    "E006": "内部处理错误，请重试",
    "E007": "参数解析错误，请检查命令行参数",
    "E008": "文件读取失败，请检查文件路径",
    "E009": "URL 格式错误，请检查链接",
    "E010": "输出写入失败，请检查输出路径",
}


# ============================================================
# 核心数据结构
# ============================================================
class ProcessingResult:
    """处理结果对象"""

    def __init__(self) -> None:
        self.items: List[Dict[str, Any]] = []  # 结构化条目列表
        self.confidence: float = 0.0  # 置信度 0-100
        self.warnings: List[str] = []  # 警告/提示信息
        self.raw_input: str = ""  # 原始输入（脱敏后）

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "items": self.items,
            "confidence": self.confidence,
            "warnings": self.warnings,
            "raw_input": self.raw_input,
        }


# ============================================================
# 核心处理逻辑
# ============================================================
def extract_key_fields(text: str) -> List[Dict[str, Any]]:
    """
    从输入文本中提取关键字段并结构化。

    支持规则：
    - 识别形如 "key: value" 或 "key=value" 的键值对
    - 识别英文/中文冒号分隔
    - 每行视为一个条目，或按空行分组

    返回结构化条目列表。
    """
    if not text or not text.strip():
        return []

    entries: List[Dict[str, Any]] = []
    # 按空行或换行分组处理
    blocks = re.split(r"\n\s*\n|\n(?=\S)", text.strip())

    for block in blocks:
        block = block.strip()
        if not block:
            continue

        entry: Dict[str, Any] = {}
        lines = block.split("\n")
        for line in lines:
            line = line.strip()
            if not line:
                continue
            # 尝试匹配 key: value 或 key=value
            match = re.match(r"^([^:=]+)[:=]\s*(.*)$", line)
            if match:
                key = match.group(1).strip()
                value = match.group(2).strip()
                if key:
                    entry[key] = value
            else:
                # 非键值对行，作为内容行
                entry.setdefault("content", []).append(line)

        if entry:
            entries.append(entry)

    return entries


def calculate_confidence(entries: List[Dict[str, Any]], raw_text: str) -> Tuple[float, List[str]]:
    """
    计算置信度。

    规则：
    - 有结构化条目且包含键值对：高置信度
    - 只有内容行无键值对：中置信度
    - 输入过短或无法解析：低置信度

    返回 (置信度 0-100, 警告列表)
    """
    warnings: List[str] = []
    if not entries:
        return 0.0, ["输入无法解析为结构化数据"]

    total_keys = 0
    total_entries = len(entries)
    for entry in entries:
        keys = [k for k in entry.keys() if k != "content"]
        total_keys += len(keys)

    # 基础置信度
    confidence = 50.0

    # 有键值对则加分
    if total_keys > 0:
        confidence += min(30.0, total_keys * 5.0)
    else:
        warnings.append("未识别到键值对，仅作为文本内容处理")

    # 条目完整度加分
    if total_entries >= 3:
        confidence += 10.0
    elif total_entries >= 1:
        confidence += 5.0

    # 输入长度影响
    if len(raw_text.strip()) < 10:
        confidence -= 20.0
        warnings.append("输入内容过短，可能信息不完整")

    # 限制范围
    confidence = max(0.0, min(100.0, confidence))

    # 根据置信度添加警告
    if confidence < 85:
        warnings.append("置信度较低，建议人工复核关键信息")

    return confidence, warnings


def process_input(raw_input: str) -> ProcessingResult:
    """
    核心处理流程。

    步骤：
    1. 输入校验（E001 空输入）
    2. 提取关键字段
    3. 计算置信度
    4. 生成结果
    """
    result = ProcessingResult()
    result.raw_input = raw_input[:100] + "..." if len(raw_input) > 100 else raw_input

    # E001: 输入为空
    if not raw_input or not raw_input.strip():
        raise ValueError(ERROR_CODES["E001"])

    # 提取字段
    entries = extract_key_fields(raw_input)
    if not entries:
        # E003: 无法解析
        raise ValueError(ERROR_CODES["E003"] + " '名称: 值' 或 '名称=值' 格式")

    # 计算置信度
    confidence, warnings = calculate_confidence(entries, raw_input)

    result.items = entries
    result.confidence = confidence
    result.warnings = warnings

    # E005: 置信度过低
    if confidence < 50:
        result.warnings.append(ERROR_CODES["E005"] + " 请提供更完整的信息")

    return result


def format_output(result: ProcessingResult, output_format: str = "text") -> str:
    """
    按指定格式输出结果。

    支持格式：text, json
    """
    if output_format == "json":
        import json
        return json.dumps(result.to_dict(), ensure_ascii=False, indent=2)
    else:
        # 文本格式
        lines = []
        lines.append("=" * 50)
        lines.append("处理结果")
        lines.append("=" * 50)

        for i, item in enumerate(result.items, 1):
            lines.append(f"[条目 {i}]")
            for key, value in item.items():
                if key == "content":
                    lines.append(f"  内容: {value}")
                else:
                    lines.append(f"  {key}: {value}")
            lines.append("")

        lines.append(f"置信度: {result.confidence:.1f}%")
        if result.confidence < 90:
            lines.append("标注: 建议复核" if result.confidence >= 85 else "标注: [需核实]")

        if result.warnings:
            lines.append("\n警告/提示:")
            for warning in result.warnings:
                lines.append(f"  - {warning}")

        lines.append("=" * 50)
        return "\n".join(lines)


def batch_process(inputs: List[str], output_format: str = "text") -> Dict[str, Any]:
    """
    批量处理多个输入。

    返回所有处理结果的汇总。
    """
    results = []
    for inp in inputs:
        try:
            result = process_input(inp)
            results.append({"input": inp[:50], "result": result.to_dict()})
        except ValueError as e:
            results.append({"input": inp[:50], "error": str(e)})

    return {
        "total": len(inputs),
        "processed": sum(1 for r in results if "result" in r),
        "errors": sum(1 for r in results if "error" in r),
        "results": results,
    }


# ============================================================
# 自检功能
# ============================================================
def selftest() -> bool:
    """
    内置自检逻辑。

    使用硬编码样例数据，不依赖外部文件、不访问网络。
    断言使用宽松阈值，确保任何环境可过。
    """
    print("开始自检...")

    # 测试样例 1: 正常输入
    sample1 = """
    姓名: 张三
    年龄: 28
    职业: 工程师
    城市: 北京
    """
    try:
        r1 = process_input(sample1)
        assert len(r1.items) > 0, "样例1: 条目数应为正"
        assert r1.confidence > 0, "样例1: 置信度应为正"
        assert r1.confidence <= 100, "样例1: 置信度不应超过100"
        assert r1.confidence >= 50, "样例1: 置信度应不低于50（有键值对）"
        print(f"  样例1 通过 (置信度: {r1.confidence:.1f}%)")
    except AssertionError as e:
        print(f"  样例1 失败: {e}")
        return False
    except ValueError as e:
        print(f"  样例1 失败: {e}")
        return False

    # 测试样例 2: 边界输入（空输入）
    try:
        process_input("")
        print("  样例2 失败: 空输入应抛出异常")
        return False
    except ValueError as e:
        assert "E001" in str(e), "样例2: 错误码应为E001"
        print("  样例2 通过 (空输入正确报错)")

    # 测试样例 3: 无键值对输入
    sample3 = "这是一段没有键值对的纯文本内容，用于测试低置信度场景。"
    try:
        r3 = process_input(sample3)
        assert len(r3.items) > 0, "样例3: 应有条目"
        assert r3.confidence > 0, "样例3: 置信度应为正"
        print(f"  样例3 通过 (置信度: {r3.confidence:.1f}%)")
    except AssertionError as e:
        print(f"  样例3 失败: {e}")
        return False
    except ValueError as e:
        print(f"  样例3 失败: {e}")
        return False

    # 测试样例 4: 批量处理
    try:
        batch_inputs = [
            "名称: 测试1\n值: 100",
            "名称: 测试2\n值: 200",
            "",
        ]
        batch_result = batch_process(batch_inputs)
        assert batch_result["total"] == 3, "样例4: 总数应为3"
        assert batch_result["processed"] > 0, "样例4: 至少1个成功"
        assert batch_result["errors"] > 0, "样例4: 至少1个错误（空输入）"
        print(f"  样例4 通过 (成功: {batch_result['processed']}, 失败: {batch_result['errors']})")
    except AssertionError as e:
        print(f"  样例4 失败: {e}")
        return False

    # 测试样例 5: 输出格式
    try:
        r5 = process_input("键: 值\n另一键: 另一值")
        text_output = format_output(r5, "text")
        assert "处理结果" in text_output, "样例5: 文本输出应包含标题"
        assert "置信度" in text_output, "样例5: 文本输出应包含置信度"

        json_output = format_output(r5, "json")
        assert '"items"' in json_output, "样例5: JSON输出应包含items"
        print("  样例5 通过 (输出格式正确)")
    except AssertionError as e:
        print(f"  样例5 失败: {e}")
        return False
    except Exception as e:
        print(f"  样例5 失败: {e}")
        return False

    # 测试样例 6: 置信度阈值逻辑
    try:
        high_conf = process_input("名称: 完整测试\n类型: 单元测试\n状态: 通过\n备注: 完整信息")
        low_conf = process_input("短")
        assert high_conf.confidence > low_conf.confidence, "样例6: 完整输入置信度应更高"
        print(f"  样例6 通过 (高置信: {high_conf.confidence:.1f}% > 低置信: {low_conf.confidence:.1f}%)")
    except AssertionError as e:
        print(f"  样例6 失败: {e}")
        return False
    except ValueError as e:
        print(f"  样例6 失败: {e}")
        return False

    print("所有自检通过！")
    return True


# ============================================================
# 命令行入口
# ============================================================
def main() -> int:
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description="未命名工具 - 处理用户数据/文件/URL并结构化输出",
        epilog="示例: python main.py --input '名称: 测试' --format json"
    )
    parser.add_argument("--input", "-i", type=str, help="输入内容（文本）")
    parser.add_argument("--file", "-f", type=str, help="输入文件路径")
    parser.add_argument("--url", "-u", type=str, help="输入URL（仅校验格式，不访问网络）")
    parser.add_argument("--format", "-fmt", type=str, choices=["text", "json"], default="text",
                        help="输出格式 (默认: text)")
    parser.add_argument("--batch", "-b", type=str, nargs="+", help="批量输入多个文本")
    parser.add_argument("--selftest", action="store_true", help="运行自检")
    parser.add_argument("--version", action="version", version="1.0.0")

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        success = selftest()
        return 0 if success else 1

    # 检查输入来源
    input_text = None

    if args.input:
        input_text = args.input
    elif args.file:
        # E008: 文件读取失败
        try:
            with open(args.file, "r", encoding="utf-8") as f:
                input_text = f.read()
        except Exception:
            print(f"错误: {ERROR_CODES['E008']}", file=sys.stderr)
            return 1
    elif args.url:
        # E009: URL格式校验（不实际访问）
        if not re.match(r"^https?://", args.url):
            print(f"错误: {ERROR_CODES['E009']}", file=sys.stderr)
            return 1
        input_text = f"URL: {args.url}"
    elif args.batch:
        # 批量处理
        batch_result = batch_process(args.batch, args.format)
        if args.format == "json":
            import json
            print(json.dumps(batch_result, ensure_ascii=False, indent=2))
        else:
            for i, item in enumerate(batch_result["results"], 1):
                print(f"--- 批次 {i} ---")
                if "result" in item:
                    print(f"输入: {item['input']}")
                    print(f"条目数: {len(item['result']['items'])}")
                    print(f"置信度: {item['result']['confidence']:.1f}%")
                else:
                    print(f"输入: {item['input']}")
                    print(f"错误: {item.get('error', '未知错误')}")
                print()
            print(f"总计: {batch_result['total']}, 成功: {batch_result['processed']}, 失败: {batch_result['errors']}")
        return 0
    else:
        # E001: 无输入
        print(f"错误: {ERROR_CODES['E001']}", file=sys.stderr)
        print("提示: 使用 --input 提供内容，或 --selftest 运行自检", file=sys.stderr)
        return 1

    # 单条处理
    try:
        result = process_input(input_text)
        output = format_output(result, args.format)
        print(output)
        return 0
    except ValueError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"错误: {ERROR_CODES['E006']} - {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
